"""
Main execution script for Properties scraping workflow
"""

import os
import sys
import logging
import argparse
from typing import Optional, Tuple
from datetime import datetime

from scraper import PropertiesScraper
from processor import PropertiesProcessor, DataValidator
from s3_uploader import S3Uploader
from config import PropertyConfig, LoggerSetup

logger = LoggerSetup.setup_logger(__name__)


class PropertiesScraperWorkflow:
    """Main workflow orchestrator for properties scraping"""
    
    def __init__(self, bucket_name: str, aws_access_key: str, aws_secret_key: str):
        """Initialize workflow with S3 credentials"""
        self.scraper = PropertiesScraper()
        self.processor = PropertiesProcessor()
        self.s3_uploader = S3Uploader(bucket_name, aws_access_key, aws_secret_key)
        self.bucket_name = bucket_name
    
    def scrape_category(self, category_type: str, category_url: str) -> list:
        """Scrape listings from a category"""
        logger.info(f"Starting scrape for {category_type}...")
        listings = self.scraper.scrape_category(category_type, category_url)
        logger.info(f"Found {len(listings)} listings for {category_type}")
        return listings
    
    def fetch_member_details(self, listings: list) -> dict:
        """Fetch detailed member information for all sellers in listings using full member_link"""
        member_details = {}
        unique_links = set()
        for listing in listings:
            seller = listing.get('seller', {})
            member_link = seller.get('member_link')
            if member_link:
                unique_links.add(member_link)

        logger.info(f"Fetching detailed info for {len(unique_links)} unique members...")

        for i, member_link in enumerate(unique_links, 1):
            if member_link in member_details:
                continue

            logger.info(f"Fetching member {i}/{len(unique_links)}: {member_link}")
            try:
                member_data = self.scraper.fetch_member_profile(member_link)
                if member_data:
                    full_info = self.processor.extract_member_full_info(member_data)
                    if full_info:
                        member_details[member_link] = full_info
                    else:
                        logger.warning(f"Could not extract member info for {member_link}")
            except Exception as e:
                logger.error(f"Error fetching member {member_link}: {str(e)}")

        logger.info(f"Successfully fetched details for {len(member_details)} members")
        return member_details
    
    def download_listing_images(self, listings: list) -> dict:
        """
        Download images for all listings
        Returns dict mapping listing_id to local images directory
        
        Note: Listings already contain complete data from detail pages with postData.listing
        """
        logger.info("Downloading images for listings...")
        
        listings_with_images = {}
        skipped_no_images = 0
        
        for i, listing in enumerate(listings, 1):
            listing_id = listing.get('listing_id')
            if not listing_id:
                continue
            
            # Check if listing has images - look for media array or image_count
            has_media = bool(listing.get('media'))  # Detail page has media array
            image_count = listing.get('image_count') or listing.get('images_count') or 0
            has_list_images = bool(image_count) and image_count > 0
            
            # Skip only if definitely no images
            if not has_media and not has_list_images:
                skipped_no_images += 1
                logger.debug(f"Skipping listing {listing_id} - no media array and image_count=0")
                continue
            
            try:
                logger.debug(f"Processing listing {listing_id} - has_media={has_media}, image_count={image_count}")
                
                # Create listing_detail structure with the complete listing data
                # The listing is already the complete object from postData.listing
                listing_detail = {
                    'postData': {
                        'listing': listing
                    }
                }
                
                # Download images using the complete listing data
                downloaded = self.scraper.download_listing_images(listing_id, listing_detail, listing)
                if downloaded:
                    local_dir = str(self.scraper.images_dir / f"{listing_id}")
                    listings_with_images[listing_id] = local_dir
                    logger.info(f"✓ Downloaded {len(downloaded)} images for listing {listing_id} ({i}/{len(listings)})")
                else:
                    logger.warning(f"✗ No images downloaded for listing {listing_id} despite has_media={has_media}, image_count={image_count}")
                
            except Exception as e:
                logger.error(f"Error downloading images for listing {listing_id}: {str(e)}", exc_info=True)
        
        logger.info(f"Image download summary: {len(listings_with_images)} succeeded, {skipped_no_images} skipped (no images), total processed: {len(listings)}")
        return listings_with_images
    
    def process_and_save(self, all_listings: list, member_details: dict, listings_with_images: dict = None) -> tuple:
        """Process listings and save to local files"""
        logger.info("Processing listings and member data...")
        
        # Add local_images_dir to listings if available
        if listings_with_images:
            for listing in all_listings:
                listing_id = listing.get('listing_id')
                if listing_id in listings_with_images:
                    listing['local_images_dir'] = listings_with_images[listing_id]
        
        # Validate listings
        valid_count, invalid_count = DataValidator.validate_listings(all_listings)
        logger.info(f"Validation: {valid_count} valid, {invalid_count} invalid listings")
        
        # Process data
        properties_data, members_data = self.processor.process_listings(
            all_listings,
            member_details
        )
        
        # Save locally
        properties_file, prop_count = self.processor.save_properties_locally(properties_data)
        members_file, mem_count = self.processor.save_members_locally(members_data)
        
        logger.info(f"Saved {prop_count} properties and {mem_count} members locally")
        
        return properties_file, members_file, properties_data
    
    def upload_images_to_s3(self, properties_data: dict, listings_with_images: dict) -> Tuple[int, int]:
        """
        Upload all listing images to S3
        Returns tuple of (total_uploaded, total_failed)
        """
        logger.info("Uploading images to S3...")
        
        total_uploaded = 0
        total_failed = 0
        total_skipped = 0
        
        for subcategory, cat_data in properties_data.items():
            for prop in cat_data.get('properties', []):
                listing_id = prop.get('listing_id')
                s3_image_path = prop.get('s3_image_path')
                
                if listing_id in listings_with_images and s3_image_path:
                    local_dir = listings_with_images[listing_id]
                    logger.debug(f"Uploading images for listing {listing_id} to {s3_image_path}")
                    success, count = self.s3_uploader.upload_images_to_s3(local_dir, s3_image_path, listing_id)
                    
                    if success:
                        total_uploaded += count
                        if count > 0:
                            logger.info(f"✓ Uploaded {count} images for listing {listing_id}")
                    else:
                        total_failed += 1
                        logger.error(f"✗ Failed to upload images for listing {listing_id}")
                else:
                    total_skipped += 1
                    if not (listing_id in listings_with_images):
                        logger.debug(f"No images downloaded for listing {listing_id}")
                    if not s3_image_path:
                        logger.debug(f"No S3 path for listing {listing_id}")
        
        logger.info(f"Image upload summary: {total_uploaded} uploaded, {total_failed} failed, {total_skipped} skipped")
        return total_uploaded, total_failed

    def upload_to_s3(self, properties_file: str, members_file: str) -> bool:
        """Upload processed files to S3"""
        logger.info("Uploading to S3...")
        
        success, results = self.s3_uploader.upload_files(properties_file, members_file)
        
        if success:
            logger.info("Successfully uploaded to S3")
            logger.info(f"Properties: {results['properties']['location']}")
            logger.info(f"Members: {results['members']['location']}")
        else:
            logger.error("Failed to upload to S3")
            logger.error(f"Results: {results}")
        
        return success
    
    def run(self, categories: Optional[list] = None) -> bool:
        """
        Execute full workflow
        
        Args:
            categories: List of categories to scrape ('rental', 'sale', or both)
        
        Returns:
            bool: True if workflow completed successfully
        """
        try:
            if categories is None:
                categories = PropertyConfig.SCRAPE_CATEGORIES
            
            # Scrape all categories
            all_listings = []
            
            if 'rental' in categories:
                rental_listings = self.scrape_category(
                    'rental',
                    PropertyConfig.RENTAL_CATEGORY_URL
                )
                all_listings.extend(rental_listings)
            
            if 'sale' in categories:
                sale_listings = self.scrape_category(
                    'sale',
                    PropertyConfig.SALE_CATEGORY_URL
                )
                all_listings.extend(sale_listings)
            
            if not all_listings:
                logger.warning("No listings found. Exiting.")
                return False
            
            logger.info(f"Total listings scraped: {len(all_listings)}")
            
            # Fetch member details
            member_details = self.fetch_member_details(all_listings)
            
            # Download listing images
            listings_with_images = self.download_listing_images(all_listings)
            
            # Process and save locally
            properties_file, members_file, properties_data = self.process_and_save(
                all_listings, 
                member_details,
                listings_with_images
            )
            
            # Upload data to S3
            upload_success = self.upload_to_s3(properties_file, members_file)
            
            # Upload images to S3
            if listings_with_images:
                images_uploaded, images_failed = self.upload_images_to_s3(
                    properties_data,
                    listings_with_images
                )
            
            if upload_success:
                logger.info("✓ Workflow completed successfully")
                return True
            else:
                logger.error("✗ Workflow failed during S3 upload")
                return False
            
        except Exception as e:
            logger.error(f"Workflow failed with error: {str(e)}", exc_info=True)
            return False


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(description='OpenSooq Properties Scraper Workflow')
    parser.add_argument(
        '--categories',
        nargs='+',
        choices=['rental', 'sale'],
        default=['rental', 'sale'],
        help='Categories to scrape (default: both)'
    )
    parser.add_argument(
        '--bucket',
        required=False,
        help='S3 bucket name (if not provided, will use AWS_S3_BUCKET env var)'
    )
    parser.add_argument(
        '--key',
        required=False,
        help='AWS access key (if not provided, will use AWS_ACCESS_KEY env var)'
    )
    parser.add_argument(
        '--secret',
        required=False,
        help='AWS secret key (if not provided, will use AWS_SECRET_KEY env var)'
    )
    
    args = parser.parse_args()
    
    # Get S3 credentials from arguments or environment
    bucket_name = args.bucket or os.getenv('AWS_S3_BUCKET')
    aws_access_key = args.key or os.getenv('AWS_ACCESS_KEY')
    aws_secret_key = args.secret or os.getenv('AWS_SECRET_KEY')
    
    if not all([bucket_name, aws_access_key, aws_secret_key]):
        logger.error("Missing S3 credentials. Please provide via arguments or environment variables:")
        logger.error("  - AWS_S3_BUCKET")
        logger.error("  - AWS_ACCESS_KEY")
        logger.error("  - AWS_SECRET_KEY")
        sys.exit(1)
    
    # Run workflow
    workflow = PropertiesScraperWorkflow(bucket_name, aws_access_key, aws_secret_key)
    success = workflow.run(categories=args.categories)
    
    sys.exit(0 if success else 1)


if __name__ == '__main__':
    main()
