"""
Main Scraper for OpenSooq Home and Garden Category
Fetches listings and detail pages from OpenSooq Kuwait
Saves data to S3 with proper partitioning
"""

import json
import logging
import requests
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from pathlib import Path
import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from utils import extract_json_from_html
from .config import (
    BASE_URL, MAIN_CATEGORY_URL, MAIN_CATEGORIES, HEADERS,
    REQUEST_TIMEOUT, LISTINGS_PER_PAGE
)
from .processor import ListingProcessor, ScraperDataManager
from .s3_uploader import HomeGardenS3Uploader

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class HomeGardenScraper:
    """Main scraper class for Home and Garden listings"""
    
    def __init__(self, s3_uploader: HomeGardenS3Uploader):
        """
        Initialize scraper
        
        Args:
            s3_uploader: S3Uploader instance for uploading data
        """
        self.s3_uploader = s3_uploader
        self.session = requests.Session()
        self.session.headers.update(HEADERS)
        self.data_manager = ScraperDataManager()
        self.target_date = datetime.now().date()  # Will scrape today's and yesterday's ads

    def fetch_page(self, url: str) -> Optional[str]:
        """
        Fetch a page and return HTML content
        
        Args:
            url: URL to fetch
        
        Returns:
            HTML content or None if failed
        """
        try:
            logger.info(f"Fetching: {url}")
            response = self.session.get(url, timeout=REQUEST_TIMEOUT)
            response.raise_for_status()
            return response.text
        except Exception as e:
            logger.error(f"Error fetching {url}: {e}")
            return None

    def get_subcategories(self, main_category_name: str, main_category_url: str) -> List[Dict]:
        """
        Get subcategories for a main category
        
        Args:
            main_category_name: Name of main category
            main_category_url: URL path of main category
        
        Returns:
            List of subcategories with details
        """
        try:
            url = f"{BASE_URL}/ar/{main_category_url}"
            html = self.fetch_page(url)
            
            if not html:
                return []
            
            # Extract JSON from HTML
            data = extract_json_from_html(html, 'pageProps')
            if not data:
                logger.warning(f"Could not extract JSON for {main_category_name}")
                return []
            
            # Get facets (subcategories)
            facets = data.get('serpApiResponse', {}).get('facets', {}).get('items', [])
            
            subcategories = []
            for facet in facets:
                subcategory = {
                    'name': facet.get('label', '').strip(),
                    'url': facet.get('url', ''),
                    'url_ar': facet.get('url_ar', ''),
                    'count': facet.get('count', 0),
                    'icon': facet.get('icon', ''),
                }
                if subcategory['name'] and subcategory['url']:
                    subcategories.append(subcategory)
            
            logger.info(f"Found {len(subcategories)} subcategories for {main_category_name}")
            return subcategories
        except Exception as e:
            logger.error(f"Error getting subcategories for {main_category_name}: {e}")
            return []

    def get_listings(self, category_url: str, page: int = 1) -> Tuple[List[Dict], int]:
        """
        Get listings for a category
        
        Args:
            category_url: URL path of category
            page: Page number (1-indexed)
        
        Returns:
            Tuple of (listings list, total pages)
        """
        try:
            url = f"{BASE_URL}/ar/{category_url}?page={page}"
            html = self.fetch_page(url)
            
            if not html:
                return [], 0
            
            data = extract_json_from_html(html, 'pageProps')
            if not data:
                logger.warning(f"Could not extract JSON for listings at {category_url}")
                return [], 0
            
            # Get listings
            listings_data = data.get('serpApiResponse', {}).get('listings', {})
            items = listings_data.get('items', [])
            meta = listings_data.get('meta', {})
            total_pages = meta.get('pages', 1)
            
            # Filter for yesterday's ads
            filtered_listings = []
            for listing in items:
                if ListingProcessor.is_yesterday_ad(listing.get('posted_at', '')):
                    filtered_listings.append(listing)
            
            logger.info(f"Found {len(filtered_listings)} yesterday's ads out of {len(items)} on {category_url} page {page}")
            return filtered_listings, total_pages
        except Exception as e:
            logger.error(f"Error getting listings for {category_url}: {e}")
            return [], 0

    def get_listing_details(self, listing_id: str) -> Optional[Dict]:
        """
        Get detailed information for a listing
        
        Args:
            listing_id: Listing/post ID
        
        Returns:
            Listing details or None if failed
        """
        try:
            url = f"{BASE_URL}/ar/search/{listing_id}"
            html = self.fetch_page(url)
            
            if not html:
                return None
            
            data = extract_json_from_html(html, 'pageProps')
            return data
        except Exception as e:
            logger.error(f"Error getting details for listing {listing_id}: {e}")
            return None

    def process_listing(
        self,
        listing: Dict,
        main_category: str,
        sub_category: str,
        scrape_date: datetime
    ) -> bool:
        """
        Process a single listing: fetch details, download images, prepare for upload
        
        Args:
            listing: Listing data from listings API
            main_category: Main category name
            sub_category: Subcategory name
            scrape_date: Date when scraping
        
        Returns:
            True if successful, False otherwise
        """
        try:
            listing_id = listing.get('id')
            if not listing_id:
                logger.warning("Listing without ID found")
                return False
            
            # Get detail page
            detail_data = self.get_listing_details(str(listing_id))
            if not detail_data:
                logger.warning(f"Could not fetch details for listing {listing_id}")
                return False
            
            # Extract processed data
            listing_details = ListingProcessor.extract_listing_details(detail_data)
            member_info = ListingProcessor.extract_member_info(detail_data)
            
            if not listing_details or not member_info:
                logger.warning(f"Failed to extract details for listing {listing_id}")
                return False
            
            # Add S3 paths and images
            images_data = []
            for idx, image in enumerate(listing_details.get('images', [])):
                images_data.append({
                    'image_id': image.get('id'),
                    'uri': image.get('uri'),
                    'type': image.get('type'),
                    'index': idx
                })
            
            # Upload listing JSON (contains all data including member_id)
            listing_details['scrape_date'] = scrape_date.isoformat()
            listing_json_path = self.s3_uploader.upload_listing_json(
                listing_details,
                main_category,
                sub_category,
                scrape_date,
                str(listing_id)
            )
            logger.info(f"Uploaded listing JSON for {listing_id}")
            
            # Upload images
            image_paths = []
            
            for image_data in images_data:
                image_uri = image_data.get('uri')
                if not image_uri:
                    continue
                
                s3_image_path = self.s3_uploader.upload_image(
                    image_uri,  # Pass just the URI, s3_uploader will construct full URL
                    main_category,
                    sub_category,
                    scrape_date,
                    str(listing_id),
                    str(image_data.get('image_id', image_data.get('index')))
                )
                
                if s3_image_path:
                    image_paths.append(s3_image_path)
            
            # Add S3 image paths to listing details
            listing_details['s3_image_paths'] = image_paths
            
            # Update listing JSON with image paths
            if image_paths:
                listing_details_with_images = listing_details.copy()
                listing_details_with_images['s3_image_paths'] = image_paths
                self.s3_uploader.upload_listing_json(
                    listing_details_with_images,
                    main_category,
                    sub_category,
                    scrape_date,
                    str(listing_id)
                )
            
            logger.info(f"Processed listing {listing_id}: {len(image_paths)} images uploaded")
            
            # Add to data manager
            self.data_manager.add_listing(listing_details, member_info, images_data)
            
            return True
        except Exception as e:
            logger.error(f"Error processing listing {listing.get('id')}: {e}")
            return False

    def scrape_category(self, main_category: str, main_category_url: str) -> int:
        """
        Scrape all subcategories and listings for a main category
        
        Args:
            main_category: Main category name
            main_category_url: Main category URL path
        
        Returns:
            Number of listings processed
        """
        try:
            logger.info(f"\n{'='*60}")
            logger.info(f"Starting scrape for: {main_category}")
            logger.info(f"{'='*60}")
            
            # Get subcategories
            subcategories = self.get_subcategories(main_category, main_category_url)
            if not subcategories:
                logger.warning(f"No subcategories found for {main_category}")
                return 0
            
            total_processed = 0
            scrape_date = datetime.now()
            
            # Process each subcategory
            for sub_cat in subcategories:
                sub_cat_name = sub_cat['name']
                sub_cat_url = sub_cat['url_ar']
                
                logger.info(f"\nProcessing subcategory: {sub_cat_name}")
                
                # Get listings from first page to determine total pages
                listings, total_pages = self.get_listings(sub_cat_url, page=1)
                
                if not listings:
                    logger.info(f"No yesterday's listings found for {sub_cat_name}")
                    continue
                
                # Process listings from first page
                for listing in listings:
                    if self.process_listing(listing, main_category, sub_cat_name, scrape_date):
                        total_processed += 1
                
                # Process remaining pages (only if we found listings on page 1)
                if total_pages > 1:
                    for page in range(2, total_pages + 1):
                        logger.info(f"Fetching page {page}/{total_pages} for {sub_cat_name}")
                        
                        listings, _ = self.get_listings(sub_cat_url, page=page)
                        if not listings:
                            break  # No more yesterday's ads
                        
                        for listing in listings:
                            if self.process_listing(listing, main_category, sub_cat_name, scrape_date):
                                total_processed += 1
            
            logger.info(f"\nCompleted scraping {main_category}: {total_processed} listings processed")
            return total_processed
        except Exception as e:
            logger.error(f"Error scraping category {main_category}: {e}")
            return 0

    def upload_member_batch(self):
        """Upload all collected member data to S3"""
        try:
            unique_members = self.data_manager.get_unique_members()
            if unique_members:
                self.s3_uploader.upload_member_info_batch(unique_members)
                logger.info(f"Uploaded {len(unique_members)} unique members")
        except Exception as e:
            logger.error(f"Error uploading member batch: {e}")

    def run(self) -> Dict:
        """
        Run the complete scraping process
        
        Returns:
            Summary of scraping results
        """
        try:
            logger.info("Starting OpenSooq Home and Garden scraper")
            logger.info(f"Target date: {self.target_date}")
            
            total_listings = 0
            
            # Scrape each main category
            for category_name, category_url in MAIN_CATEGORIES.items():
                count = self.scrape_category(category_name, category_url)
                total_listings += count
            
            # Upload member data
            self.upload_member_batch()
            
            summary = {
                'status': 'success',
                'total_listings_processed': total_listings,
                'scrape_date': self.target_date.isoformat(),
                'batch_summary': self.data_manager.get_batch_summary(),
                'timestamp': datetime.now().isoformat()
            }
            
            logger.info(f"\n{'='*60}")
            logger.info(f"Scraping completed!")
            logger.info(f"Total listings processed: {total_listings}")
            logger.info(f"Summary: {summary}")
            logger.info(f"{'='*60}")
            
            return summary
        except Exception as e:
            logger.error(f"Fatal error during scraping: {e}")
            return {
                'status': 'error',
                'error': str(e),
                'timestamp': datetime.now().isoformat()
            }


def main():
    """Main entry point"""
    try:
        # Get AWS credentials from environment
        bucket_name = os.getenv('AWS_S3_BUCKET')
        aws_access_key = os.getenv('AWS_ACCESS_KEY')
        aws_secret_key = os.getenv('AWS_SECRET_KEY')
        aws_region = os.getenv('AWS_REGION', 'us-east-1')
        
        if not all([bucket_name, aws_access_key, aws_secret_key]):
            raise ValueError("Missing AWS credentials in environment variables")
        
        # Initialize S3 uploader
        s3_uploader = HomeGardenS3Uploader(bucket_name, aws_access_key, aws_secret_key, aws_region)
        
        # Initialize and run scraper
        scraper = HomeGardenScraper(s3_uploader)
        result = scraper.run()
        
        # Return result for workflow
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0 if result.get('status') == 'success' else 1
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        print(json.dumps({
            'status': 'error',
            'error': str(e),
            'timestamp': datetime.now().isoformat()
        }, ensure_ascii=False, indent=2))
        return 1


if __name__ == '__main__':
    exit(main())
