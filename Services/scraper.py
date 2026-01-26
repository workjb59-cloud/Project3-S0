"""
Main Scraper for OpenSooq Services Category
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
import time

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from utils import extract_json_from_html
from .config import (
    BASE_URL, SERVICES_URL, HEADERS,
    REQUEST_TIMEOUT, LISTINGS_PER_PAGE, MAX_RETRIES, RETRY_DELAY
)
from .processor import ServicesProcessor, ServicesDataManager
from .s3_uploader import ServicesS3Uploader

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class ServicesScraper:
    """Main scraper class for Services listings"""
    
    def __init__(self, s3_uploader: ServicesS3Uploader):
        """
        Initialize scraper
        
        Args:
            s3_uploader: S3Uploader instance for uploading data
        """
        self.s3_uploader = s3_uploader
        self.session = requests.Session()
        self.session.headers.update(HEADERS)
        self.data_manager = ServicesDataManager()
        self.target_date = (datetime.now() - timedelta(days=1)).date()  # Yesterday's date
        self.processor = ServicesProcessor()

    def fetch_page(self, url: str, retry_count: int = 0) -> Optional[str]:
        """
        Fetch a page and return HTML content
        
        Args:
            url: URL to fetch
            retry_count: Current retry attempt
        
        Returns:
            HTML content or None if failed
        """
        try:
            logger.info(f"Fetching: {url}")
            response = self.session.get(url, timeout=REQUEST_TIMEOUT)
            response.raise_for_status()
            return response.text
        except Exception as e:
            if retry_count < MAX_RETRIES:
                logger.warning(f"Error fetching {url}: {e}. Retrying in {RETRY_DELAY}s...")
                time.sleep(RETRY_DELAY)
                return self.fetch_page(url, retry_count + 1)
            logger.error(f"Error fetching {url} after {MAX_RETRIES} retries: {e}")
            return None

    def get_main_categories(self) -> List[Dict]:
        """
        Get main service categories from the Services main page
        
        Returns:
            List of main categories with details
        """
        html = self.fetch_page(SERVICES_URL)
        if not html:
            logger.error("Failed to fetch main Services page")
            return []
        
        try:
            page_props = extract_json_from_html(html, 'pageProps')
            if not page_props:
                logger.error("Failed to extract JSON from Services page")
                return []
            
            # Extract categories from facets
            facets = page_props.get('serpApiResponse', {}).get('facets', {})
            categories = facets.get('items', [])
            
            logger.info(f"Found {len(categories)} main service categories")
            return categories
        except Exception as e:
            logger.error(f"Error parsing main categories: {e}")
            return []

    def get_subcategories(self, category_url: str, category_label: str) -> List[Dict]:
        """
        Get subcategories for a main category
        
        Args:
            category_url: URL path of main category
            category_label: Label of main category
        
        Returns:
            List of subcategories with details
        """
        # Build full URL
        full_url = f"{BASE_URL}/{category_url}"
        html = self.fetch_page(full_url)
        
        if not html:
            logger.error(f"Failed to fetch subcategories for {category_label}")
            return []
        
        try:
            page_props = extract_json_from_html(html, 'pageProps')
            if not page_props:
                logger.error(f"Failed to extract JSON from {category_label}")
                return []
            
            # Extract subcategories from facets
            facets = page_props.get('serpApiResponse', {}).get('facets', {})
            subcategories = facets.get('items', [])
            
            logger.info(f"Found {len(subcategories)} subcategories for {category_label}")
            return subcategories
        except Exception as e:
            logger.error(f"Error parsing subcategories for {category_label}: {e}")
            return []

    def get_listings_page(self, subcategory_url: str, page: int = 1) -> Tuple[List[Dict], Dict]:
        """
        Get listings for a subcategory page
        
        Args:
            subcategory_url: URL path of subcategory
            page: Page number
        
        Returns:
            Tuple of (listings list, metadata dict)
        """
        # Build URL with page parameter if needed
        if page > 1:
            full_url = f"{BASE_URL}/{subcategory_url}?page={page}"
        else:
            full_url = f"{BASE_URL}/{subcategory_url}"
        
        html = self.fetch_page(full_url)
        if not html:
            return [], {}
        
        try:
            page_props = extract_json_from_html(html, 'pageProps')
            if not page_props:
                return [], {}
            
            # Extract listings
            serp_data = page_props.get('serpApiResponse', {})
            listings_data = serp_data.get('listings', {})
            listings = listings_data.get('items', [])
            metadata = listings_data.get('meta', {})
            
            logger.info(f"Found {len(listings)} listings on page {page}")
            return listings, metadata
        except Exception as e:
            logger.error(f"Error parsing listings: {e}")
            return [], {}

    def get_listing_detail(self, listing_id: int) -> Optional[Dict]:
        """
        Get detailed information for a specific listing
        
        Args:
            listing_id: Listing ID
        
        Returns:
            Dict with listing and seller data, or None if failed
        """
        detail_url = f"{BASE_URL}/search/{listing_id}"
        html = self.fetch_page(detail_url)
        
        if not html:
            return None
        
        try:
            page_props = extract_json_from_html(html, 'pageProps')
            if not page_props:
                return None
            
            # Extract post data
            post_data = page_props.get('postData', {})
            
            return {
                'listing': post_data.get('listing', {}),
                'seller': post_data.get('seller', {})
            }
        except Exception as e:
            logger.error(f"Error parsing listing detail {listing_id}: {e}")
            return None

    def get_member_info(self, member_link: str) -> Optional[Dict]:
        """
        Get detailed member information
        
        Args:
            member_link: Member profile URL path
        
        Returns:
            Dict with member info, or None if failed
        """
        # Build full URL
        full_url = f"{BASE_URL}{member_link}"
        html = self.fetch_page(full_url)
        
        if not html:
            return None
        
        try:
            page_props = extract_json_from_html(html, 'pageProps')
            if not page_props:
                return None
            
            # Extract member info
            user_info = page_props.get('userInfo', {})
            member_data = user_info.get('member', {})
            
            return member_data
        except Exception as e:
            logger.error(f"Error parsing member info {member_link}: {e}")
            return None

    def scrape_subcategory(self, category_label: str, subcategory: Dict) -> int:
        """
        Scrape all yesterday's listings from a subcategory
        
        Args:
            category_label: Main category label
            subcategory: Subcategory data dict
        
        Returns:
            Number of listings scraped
        """
        subcategory_url = subcategory.get('url_ar', '')
        subcategory_label = subcategory.get('label', '')
        
        logger.info(f"Scraping subcategory: {category_label} -> {subcategory_label}")
        
        # Get first page to check metadata
        listings, metadata = self.get_listings_page(subcategory_url, page=1)
        
        total_pages = metadata.get('pages', 1)
        total_count = metadata.get('count', 0)
        
        logger.info(f"Total listings: {total_count}, Total pages: {total_pages}")
        
        all_listings = []
        
        # Scrape all pages
        for page in range(1, total_pages + 1):
            if page > 1:
                listings, _ = self.get_listings_page(subcategory_url, page)
            
            for listing in listings:
                # Check if posted yesterday
                posted_at = listing.get('posted_at', '')
                if not self.processor.is_yesterday_ad(posted_at):
                    logger.debug(f"Skipping listing {listing.get('id')} - not from yesterday")
                    continue
                
                # Get detail page
                listing_id = listing.get('id')
                detail_data = self.get_listing_detail(listing_id)
                
                if detail_data:
                    # Add to collection
                    all_listings.append(detail_data)
                    
                    # Process member info
                    seller = detail_data.get('seller', {})
                    member_link = seller.get('member_link', '')
                    member_id = seller.get('id')
                    
                    if member_link and member_id:
                        # Get member info
                        member_info = self.get_member_info(member_link)
                        if member_info:
                            # Add to data manager for incremental storage
                            self.data_manager.add_member_info(member_id, member_info)
                
                # Rate limiting
                time.sleep(0.5)
        
        # Save subcategory data
        if all_listings:
            self.data_manager.add_subcategory_data(category_label, subcategory_label, all_listings)
            logger.info(f"Scraped {len(all_listings)} yesterday's listings for {subcategory_label}")
        
        return len(all_listings)

    def scrape_category(self, category: Dict) -> int:
        """
        Scrape all subcategories of a main category
        
        Args:
            category: Main category data dict
        
        Returns:
            Total number of listings scraped
        """
        category_label = category.get('label', '')
        category_url = category.get('url_ar', '')
        
        logger.info(f"Scraping main category: {category_label}")
        
        # Get subcategories
        subcategories = self.get_subcategories(category_url, category_label)
        
        total_listings = 0
        
        for subcategory in subcategories:
            count = self.scrape_subcategory(category_label, subcategory)
            total_listings += count
        
        return total_listings

    def scrape_all_services(self):
        """
        Main method to scrape all service categories
        """
        logger.info(f"Starting Services scrape for date: {self.target_date}")
        
        # Get all main categories
        categories = self.get_main_categories()
        
        if not categories:
            logger.error("No categories found. Exiting.")
            return
        
        total_listings = 0
        
        # Scrape each category
        for category in categories:
            try:
                count = self.scrape_category(category)
                total_listings += count
            except Exception as e:
                logger.error(f"Error scraping category {category.get('label')}: {e}")
                continue
        
        # Upload to S3
        logger.info(f"Total listings scraped: {total_listings}")
        logger.info("Uploading data to S3...")
        
        try:
            self.s3_uploader.upload_all_data(
                self.data_manager,
                self.target_date
            )
            logger.info("Successfully uploaded all data to S3")
        except Exception as e:
            logger.error(f"Error uploading to S3: {e}")
            raise


def main():
    """Main entry point for the scraper"""
    # Get credentials from environment
    bucket_name = os.getenv('S3_BUCKET_NAME', 'opensooq-data')
    aws_access_key = os.getenv('AWS_ACCESS_KEY_ID')
    aws_secret_key = os.getenv('AWS_SECRET_ACCESS_KEY')
    aws_region = os.getenv('AWS_REGION', 'us-east-1')
    
    if not aws_access_key or not aws_secret_key:
        logger.error("AWS credentials not found in environment variables")
        sys.exit(1)
    
    # Initialize S3 uploader
    s3_uploader = ServicesS3Uploader(
        bucket_name=bucket_name,
        aws_access_key=aws_access_key,
        aws_secret_key=aws_secret_key,
        region=aws_region
    )
    
    # Initialize and run scraper
    scraper = ServicesScraper(s3_uploader)
    scraper.scrape_all_services()


if __name__ == "__main__":
    main()
