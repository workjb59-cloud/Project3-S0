"""
Main execution script for Properties scraping workflow
"""

import os
import sys
import logging
import argparse
from typing import Optional
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
        """Fetch detailed member information for all sellers in listings using member_link (username)"""
        member_details = {}
        unique_usernames = set()
        for listing in listings:
            seller = listing.get('seller', {})
            member_link = seller.get('member_link')
            if member_link:
                # Extract username from member_link (e.g., '/ar/mid/member-USERNAME')
                if 'member-' in member_link:
                    username = member_link.split('member-')[-1].strip('/')
                    if username:
                        unique_usernames.add(username)

        logger.info(f"Fetching detailed info for {len(unique_usernames)} unique members...")

        for i, username in enumerate(unique_usernames, 1):
            if username in member_details:
                continue

            logger.info(f"Fetching member {i}/{len(unique_usernames)}: {username}")
            try:
                member_data = self.scraper.fetch_member_profile(username)
                if member_data:
                    full_info = self.processor.extract_member_full_info(member_data)
                    if full_info:
                        member_details[username] = full_info
                    else:
                        logger.warning(f"Could not extract member info for {username}")
            except Exception as e:
                logger.error(f"Error fetching member {username}: {str(e)}")

        logger.info(f"Successfully fetched details for {len(member_details)} members")
        return member_details
    
    def process_and_save(self, all_listings: list, member_details: dict) -> tuple:
        """Process listings and save to local files"""
        logger.info("Processing listings and member data...")
        
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
        
        return properties_file, members_file
    
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
            
            # Process and save locally
            properties_file, members_file = self.process_and_save(all_listings, member_details)
            
            # Upload to S3
            upload_success = self.upload_to_s3(properties_file, members_file)
            
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
