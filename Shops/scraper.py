"""
OpenSooq Shops Scraper

This script scrapes shop data and their ads from opensooq.com (Kuwait)
متاجر category and saves them to AWS S3 as Excel files.
"""
import os
import sys
import time
import requests
from datetime import datetime
from typing import List, Dict, Optional
import pandas as pd

# Add parent directory to path to import utils
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils import (
    extract_json_from_html,
    filter_yesterday_ads,
    upload_to_s3,
    download_from_s3,
    prepare_shop_info_row,
    prepare_ad_data,
    update_incremental_info,
    get_partitioned_s3_path,
    save_ad_images_to_s3
)
from Shops.config import (
    CATEGORY_URL,
    CATEGORY_NAME_AR,
    S3_CATEGORY_PATH,
    DELAY_BETWEEN_SHOPS,
    DELAY_BETWEEN_PAGES,
    MAX_RETRIES,
    REQUEST_TIMEOUT
)


# AWS Configuration from environment
BUCKET_NAME = os.environ.get('AWS_BUCKET_NAME', 'your-bucket-name')
AWS_ACCESS_KEY = os.environ.get('AWS_ACCESS_KEY_ID', '')
AWS_SECRET_KEY = os.environ.get('AWS_SECRET_ACCESS_KEY', '')
S3_BASE_PATH = "opensooq-data"

# Request headers to mimic a browser
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
    'Accept-Language': 'ar,en-US;q=0.7,en;q=0.3',
    'Accept-Encoding': 'gzip, deflate, br',
    'Connection': 'keep-alive',
    'Upgrade-Insecure-Requests': '1'
}


def get_html_content(url: str, max_retries: int = MAX_RETRIES) -> Optional[str]:
    """
    Fetch HTML content from URL with retry logic
    
    Args:
        url: URL to fetch
        max_retries: Maximum number of retry attempts
    
    Returns:
        HTML content as string or None
    """
    for attempt in range(max_retries):
        try:
            print(f"Fetching: {url} (attempt {attempt + 1}/{max_retries})")
            response = requests.get(url, headers=HEADERS, timeout=REQUEST_TIMEOUT)
            response.raise_for_status()
            return response.text
        except requests.exceptions.RequestException as e:
            print(f"Error fetching {url}: {e}")
            if attempt < max_retries - 1:
                wait_time = (attempt + 1) * 2
                print(f"Retrying in {wait_time} seconds...")
                time.sleep(wait_time)
            else:
                print(f"Failed to fetch {url} after {max_retries} attempts")
                return None


def get_shops_list(page: int = 1) -> Optional[Dict]:
    """
    Get list of shops from shops listing page
    
    Args:
        page: Page number to fetch
    
    Returns:
        Dictionary with shops data
    """
    try:
        url = f"{CATEGORY_URL}?page={page}" if page > 1 else CATEGORY_URL
        html = get_html_content(url)
        
        if not html:
            return None
        
        # Extract JSON data from HTML
        page_props = extract_json_from_html(html, 'pageProps')
        
        if not page_props:
            print(f"Could not extract pageProps from page {page}")
            return None
        
        return page_props
    
    except Exception as e:
        print(f"Error getting shops list for page {page}: {e}")
        return None


def get_shop_details_and_ads(shop_url: str) -> Optional[Dict]:
    """
    Get shop details and its ads
    
    Args:
        shop_url: Shop URL slug (e.g., "شركة-دار-الشويخ-العقارية-75063309")
    
    Returns:
        Dictionary with shop data and listings
    """
    try:
        base_url = CATEGORY_URL.rsplit('/', 1)[0]  # Get base URL without /متاجر
        url = f"{base_url}/{CATEGORY_NAME_AR}/{shop_url}"
        html = get_html_content(url)
        
        if not html:
            return None
        
        # Extract JSON data from HTML
        page_props = extract_json_from_html(html, 'pageProps')
        
        if not page_props:
            print(f"Could not extract pageProps from shop: {shop_url}")
            return None
        
        return page_props
    
    except Exception as e:
        print(f"Error getting shop details for {shop_url}: {e}")
        return None


def scrape_all_shops() -> List[Dict]:
    """
    Scrape all shops from all pages
    
    Returns:
        List of shop dictionaries
    """
    all_shops = []
    page = 1
    
    print("=" * 60)
    print(f"Fetching {CATEGORY_NAME_AR} list...")
    print("=" * 60)
    
    while True:
        print(f"\nFetching shops page {page}...")
        shops_data = get_shops_list(page)
        
        if not shops_data:
            print(f"No data returned for page {page}")
            break
        
        # Get metadata
        shops_response = shops_data.get('shopsListingResponse', {})
        meta = shops_response.get('meta', {})
        shops_items = shops_data.get('shopsListingItems', [])
        
        if not shops_items:
            print(f"No shops found on page {page}")
            break
        
        all_shops.extend(shops_items)
        print(f"Found {len(shops_items)} shops on page {page}")
        
        # Check if there are more pages
        current_page = meta.get('current_page', page)
        total_pages = meta.get('pages', 1)
        
        print(f"Progress: Page {current_page} of {total_pages}")
        
        if current_page >= total_pages:
            print(f"\nReached last page. Total shops: {len(all_shops)}")
            break
        
        page += 1
        time.sleep(DELAY_BETWEEN_PAGES)
    
    return all_shops


def process_shop(shop_item: Dict) -> bool:
    """
    Process a single shop: fetch details, filter yesterday ads, and save to S3
    
    Args:
        shop_item: Shop item from shops list
    
    Returns:
        True if successful, False otherwise
    """
    try:
        shop_url = shop_item.get('shop_url')
        member_id = shop_item.get('member_id')
        shop_name = shop_item.get('title')
        
        if not shop_url:
            print(f"No shop URL for shop: {shop_name}")
            return False
        
        print(f"\nProcessing shop: {shop_name} (ID: {member_id})")
        print(f"URL: {shop_url}")
        
        # Get shop details and ads
        shop_data = get_shop_details_and_ads(shop_url)
        
        if not shop_data:
            print(f"Could not fetch shop data for: {shop_name}")
            return False
        
        # Extract listings from serpApiResponse
        serp_data = shop_data.get('serpApiResponse', {})
        listings = serp_data.get('listings', {})
        all_ads = listings.get('items', [])
        
        if not all_ads:
            print(f"No ads found for shop: {shop_name}")
            return False
        
        # Filter yesterday's ads
        yesterday_ads = filter_yesterday_ads(all_ads)
        
        print(f"Total ads: {len(all_ads)}, Yesterday's ads: {len(yesterday_ads)}")
        
        if not yesterday_ads:
            print(f"No yesterday ads for shop: {shop_name}")
            return True  # Not an error, just no new ads
        
        # Prepare shop basic info
        shop_basic_info = {
            'member_id': member_id,
            'shop_name': shop_name
        }
        
        # Download and save ad images to S3
        print(f"Downloading images for {len(yesterday_ads)} ads...")
        ad_images_map = save_ad_images_to_s3(
            ads=yesterday_ads,
            shop_name=shop_name,
            member_id=member_id,
            bucket_name=BUCKET_NAME,
            s3_base_path=S3_BASE_PATH,
            category_path=S3_CATEGORY_PATH,
            aws_access_key=AWS_ACCESS_KEY,
            aws_secret_key=AWS_SECRET_KEY
        )
        print(f"Saved {len(ad_images_map)} ad images")
        
        # Prepare ads DataFrame with image paths
        ads_df = prepare_ad_data(yesterday_ads, shop_basic_info, ad_images_map)
        
        if ads_df.empty:
            print(f"Failed to prepare ads data for: {shop_name}")
            return False
        
        # Upload ads to S3 with partitioned path
        partitioned_path = get_partitioned_s3_path(member_id, shop_name, folder='excel files')
        s3_ads_key = f"{S3_BASE_PATH}/{S3_CATEGORY_PATH}/{partitioned_path}"
        
        upload_success = upload_to_s3(
            data=ads_df,
            bucket_name=BUCKET_NAME,
            s3_key=s3_ads_key,
            aws_access_key=AWS_ACCESS_KEY,
            aws_secret_key=AWS_SECRET_KEY
        )
        
        if not upload_success:
            print(f"Failed to upload ads for: {shop_name}")
            return False
        
        # Update incremental shop info
        shop_info_row = prepare_shop_info_row(shop_data.get('data', {}))
        
        if shop_info_row:
            update_shop_info(shop_info_row)
        
        print(f"✓ Successfully processed shop: {shop_name}")
        return True
    
    except Exception as e:
        print(f"Error processing shop: {e}")
        return False


def update_shop_info(new_shop_info: Dict) -> bool:
    """
    Update the incremental shop info Excel file in S3
    
    Args:
        new_shop_info: New shop info dictionary
    
    Returns:
        True if successful, False otherwise
    """
    try:
        s3_info_key = f"{S3_BASE_PATH}/info/info.xlsx"
        
        # Download existing info file
        existing_df = download_from_s3(
            bucket_name=BUCKET_NAME,
            s3_key=s3_info_key,
            aws_access_key=AWS_ACCESS_KEY,
            aws_secret_key=AWS_SECRET_KEY
        )
        
        # Update with new shop info
        updated_df = update_incremental_info(existing_df, new_shop_info)
        
        # Upload updated file
        return upload_to_s3(
            data=updated_df,
            bucket_name=BUCKET_NAME,
            s3_key=s3_info_key,
            aws_access_key=AWS_ACCESS_KEY,
            aws_secret_key=AWS_SECRET_KEY
        )
    
    except Exception as e:
        print(f"Error updating shop info: {e}")
        return False


def main():
    """Main scraper function"""
    print("=" * 60)
    print(f"OpenSooq {CATEGORY_NAME_AR} Scraper - Starting")
    print(f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)
    
    # Validate environment variables
    if not AWS_ACCESS_KEY or not AWS_SECRET_KEY:
        print("ERROR: AWS credentials not found in environment variables")
        print("Please set AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY")
        sys.exit(1)
    
    if not BUCKET_NAME or BUCKET_NAME == 'your-bucket-name':
        print("ERROR: AWS_BUCKET_NAME not set in environment variables")
        sys.exit(1)
    
    # Step 1: Get all shops
    shops = scrape_all_shops()
    
    if not shops:
        print("\nNo shops found. Exiting.")
        sys.exit(1)
    
    print(f"\nTotal shops to process: {len(shops)}")
    
    # Step 2: Process each shop
    print("\n" + "=" * 60)
    print("Processing shops and their ads...")
    print("=" * 60)
    
    success_count = 0
    error_count = 0
    
    for idx, shop in enumerate(shops, 1):
        print(f"\n[{idx}/{len(shops)}]", end=" ")
        
        if process_shop(shop):
            success_count += 1
        else:
            error_count += 1
        
        # Be respectful to the server
        time.sleep(DELAY_BETWEEN_SHOPS)
    
    # Summary
    print("\n" + "=" * 60)
    print("Scraping Complete!")
    print("=" * 60)
    print(f"Total shops: {len(shops)}")
    print(f"Successfully processed: {success_count}")
    print(f"Errors: {error_count}")
    print(f"Completion time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)


if __name__ == "__main__":
    main()
