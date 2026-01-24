"""
OpenSooq Properties Scraper Module
Scrapes property listings from OpenSooq website for yesterday's data only
"""

import requests
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
import json
from typing import List, Dict, Optional
import logging
from pathlib import Path
import urllib.parse
from concurrent.futures import ThreadPoolExecutor, as_completed

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class PropertiesScraper:
    """Scrapes property data from OpenSooq"""
    
    BASE_URL = "https://kw.opensooq.com/ar"
    
    # Property category IDs for rental and sale
    PROPERTY_CATEGORIES = {
        "property-for-rent": "عقارات/عقارات-للإيجار",
        "property-for-sale": "عقارات/عقارات-للبيع"
    }
    
    # Subcategory mappings (id -> url_name)
    RENT_SUBCATEGORIES = {
        8001: "عقارات/شقق-للايجار",  # Apartments for Rent
        12447: "عقارات/شقق-وأجنحة-فندقية-للايجار",  # Hotel Apartments
        12487: "عقارات/غرف-وسكن-مشترك-للايجار",  # Shared Rooms
        8003: "عقارات/فلل-وقصور-للايجار",  # Villas/Palaces
        12696: "عقارات/بيوت-ومنازل-للايجار",  # Townhouses
        8009: "عقارات/عمارة-سكنية-للايجار",  # Whole Building
        12813: "عقارات/أراضي-للايجار",  # Lands
        12893: "عقارات/مزارع-وشاليهات-للايجار",  # Farms & Chalets
        16735: "عقارات/مكاتب-للايجار",  # Offices
        16775: "عقارات/محلات-للايجار",  # Shops
        16815: "عقارات/معارض-للايجار",  # Showrooms
        16855: "عقارات/مخازن-للايجار",  # Warehouses
        16895: "عقارات/طابق-كامل-للايجار",  # Full Floors
        16935: "عقارات/مجمعات-للايجار",  # Complexes
        16975: "عقارات/فلل-تجارية-للايجار",  # Commercial Villas
        17015: "عقارات/مطاعم-وكافيهات-للايجار",  # Restaurants & Cafes
        17055: "عقارات/سوبرماركت-للايجار",  # Supermarkets
        17095: "عقارات/عيادات-للايجار",  # Clinics
        17135: "عقارات/مصانع-للايجار",  # Factories
        17175: "عقارات/سكن-موظفين-للايجار",  # Staff Housing
        17215: "عقارات/فنادق-للايجار",  # Hotels
        11339: "عقارات/عقارات-أجنبية-للايجار",  # Foreign Properties
    }
    
    SALE_SUBCATEGORIES = {
        7683: "عقارات/شقق-للبيع",  # Apartments for Sale
        7685: "عقارات/فلل-وقصور-للبيع",  # Villas/Palaces
        12658: "عقارات/أراضي-للبيع",  # Lands
        12853: "عقارات/بيوت-ومنازل-للبيع",  # Townhouses
        12933: "عقارات/عمارات-للبيع",  # Buildings
        7689: "عقارات/عقارات-تجارية-للبيع",  # Commercial Properties
        16215: "عقارات/مكاتب-للبيع",  # Offices
        16255: "عقارات/محلات-للبيع",  # Shops
        16295: "عقارات/معارض-للبيع",  # Showrooms
        16335: "عقارات/مخازن-للبيع",  # Warehouses
        16375: "عقارات/طابق-كامل-للبيع",  # Full Floors
        16415: "عقارات/مجمعات-للبيع",  # Complexes
        16455: "عقارات/فلل-تجارية-للبيع",  # Commercial Villas
        16495: "عقارات/مطاعم-وكافيهات-للبيع",  # Restaurants & Cafes
        16535: "عقارات/سوبرماركت-للبيع",  # Supermarkets
        16575: "عقارات/عيادات-للبيع",  # Clinics
        16615: "عقارات/مصانع-للبيع",  # Factories
        16655: "عقارات/بنوك-للبيع",  # Banks
        16695: "عقارات/فنادق-للبيع",  # Hotels
        11337: "عقارات/عقارات-أجنبية-للبيع",  # Foreign Properties
    }
    
    def __init__(self):
        """Initialize scraper with requests session"""
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
        self.yesterday = (datetime.now() - timedelta(days=1)).date()
        self.images_dir = Path("/tmp/opensooq_images")
        self.images_dir.mkdir(exist_ok=True, parents=True)
    
    def download_image(self, image_url: str, save_path: str) -> bool:
        """
        Download a single image from URL to local path
        Returns True if successful, False otherwise
        """
        try:
            response = self.session.get(image_url, timeout=10)
            response.raise_for_status()
            
            # Ensure directory exists
            Path(save_path).parent.mkdir(parents=True, exist_ok=True)
            
            with open(save_path, 'wb') as f:
                f.write(response.content)
            
            logger.debug(f"Downloaded image to {save_path}")
            return True
        except Exception as e:
            logger.warning(f"Failed to download image {image_url}: {str(e)}")
            return False
    
    def download_listing_images(self, listing_id: int, listing_detail: Dict = None, listing: Dict = None) -> Dict[str, str]:
        """
        Download all images for a listing
        Returns dict mapping image filenames to their local paths
        
        Args:
            listing_id: OpenSooq listing ID
            listing_detail: Listing detail data from fetch_listing_detail (optional)
            listing: Original listing data (optional, fallback)
        
        Returns:
            Dict of {image_filename: local_path}
        """
        downloaded_images = {}
        
        try:
            logger.info(f"Attempting to download images for listing {listing_id}")
            
            # Navigate through the listing detail structure to find images
            images_data = []
            
            # Log what we received
            if listing_detail is None:
                logger.warning(f"listing_detail is None for listing {listing_id}")
            elif not isinstance(listing_detail, dict):
                logger.warning(f"listing_detail is not a dict for listing {listing_id}, type: {type(listing_detail)}")
            else:
                logger.info(f"listing_detail keys for {listing_id}: {list(listing_detail.keys())}")
            
            # Try multiple possible paths where images might be stored
            if listing_detail and isinstance(listing_detail, dict):
                # NEW: Check postData.listing.media (the actual structure)
                if 'postData' in listing_detail:
                    post_data = listing_detail['postData']
                    if isinstance(post_data, dict) and 'listing' in post_data:
                        listing_obj = post_data['listing']
                        if isinstance(listing_obj, dict) and 'media' in listing_obj:
                            images_data = listing_obj['media']
                            logger.info(f"✓ Found images in postData['listing']['media']: {len(images_data)} items")
                
                # Fallback paths
                if not images_data and 'listing' in listing_detail and isinstance(listing_detail['listing'], dict):
                    if 'images' in listing_detail['listing']:
                        images_data = listing_detail['listing']['images']
                        logger.info(f"✓ Found images in listing_detail['listing']['images']: {len(images_data)} items")
                if not images_data and 'images' in listing_detail:
                    images_data = listing_detail['images']
                    logger.info(f"✓ Found images in listing_detail['images']: {len(images_data)} items")
                if not images_data and 'serpApiResponse' in listing_detail:
                    api_response = listing_detail['serpApiResponse']
                    if isinstance(api_response, dict) and 'images' in api_response:
                        images_data = api_response['images']
                        logger.info(f"✓ Found images in listing_detail['serpApiResponse']['images']: {len(images_data)} items")
            
            # Fallback to original listing if available and no images found
            if not images_data and listing and isinstance(listing, dict):
                logger.info(f"Checking original listing for images, keys: {list(listing.keys())}")
                if 'images' in listing:
                    images_data = listing.get('images', [])
                    logger.info(f"✓ Found images in listing['images']: {len(images_data)} items")
                elif 'image_urls' in listing:
                    images_data = listing.get('image_urls', [])
                    logger.info(f"✓ Found images in listing['image_urls']: {len(images_data)} items")
            
            if not images_data:
                logger.warning(f"✗ No images found for listing {listing_id} - checked all possible locations")
                # Log sample of what was in listing_detail for debugging
                if listing_detail and isinstance(listing_detail, dict):
                    logger.info(f"  Available top-level keys: {list(listing_detail.keys())}")
                    if 'listing' in listing_detail:
                        logger.info(f"  Keys in listing_detail['listing']: {list(listing_detail['listing'].keys()) if isinstance(listing_detail['listing'], dict) else 'not a dict'}")
                return {}
            
            # Create listing-specific directory
            listing_images_dir = self.images_dir / f"{listing_id}"
            listing_images_dir.mkdir(exist_ok=True, parents=True)
            
            logger.info(f"Found {len(images_data)} images for listing {listing_id}")
            
            # Log sample of first image to understand structure
            if images_data:
                logger.info(f"  Sample image data type: {type(images_data[0])}")
                if isinstance(images_data[0], dict):
                    logger.info(f"  Sample image keys: {list(images_data[0].keys())}")
            
            # Download each image
            for idx, image_info in enumerate(images_data, 1):
                if isinstance(image_info, dict):
                    # Get image URI and convert to full URL
                    image_uri = image_info.get('uri')
                    
                    # Try multiple keys where image URL might be
                    image_url = (image_uri or
                                image_info.get('original') or 
                                image_info.get('full') or 
                                image_info.get('url') or
                                image_info.get('src') or
                                image_info.get('image_url'))
                    
                    # If we found a URI (relative path), convert to full URL
                    if image_uri and not image_url.startswith('http'):
                        # OpenSooq CDN URL format: https://opensooq-images.os-cdn.com/previews/0x720/{uri}.webp
                        image_url = f"https://opensooq-images.os-cdn.com/previews/0x720/{image_uri}.webp"
                        logger.debug(f"Converted URI to full URL: {image_url}")
                    
                    if not image_url:
                        logger.info(f"  Image {idx} has no URL key - available keys: {list(image_info.keys())}")
                else:
                    image_url = str(image_info)
                
                if not image_url:
                    logger.warning(f"No URL found for image {idx} in listing {listing_id}")
                    continue
                
                # Generate filename
                file_ext = '.jpg'  # Default extension
                if '.' in image_url.split('/')[-1]:
                    file_ext = '.' + image_url.split('.')[-1].split('?')[0]
                
                filename = f"image_{idx:03d}{file_ext}"
                save_path = listing_images_dir / filename
                
                if self.download_image(image_url, str(save_path)):
                    downloaded_images[filename] = str(save_path)
            
            logger.info(f"Downloaded {len(downloaded_images)} images for listing {listing_id}")
            
        except Exception as e:
            logger.error(f"Error downloading images for listing {listing_id}: {str(e)}", exc_info=True)
        
        return downloaded_images
    
    def is_yesterday_posting(self, posted_at_text: str) -> bool:
        """
        Check if posting is from yesterday based on posted_at text
        Expected formats: "قبل X ساعة", "قبل X دقيقة", "أمس", etc.
        """
        if not posted_at_text:
            return False
        
        posted_at = posted_at_text.lower().strip()
        
        # Check for yesterday indicator
        if "أمس" in posted_at:
            return True
        
        # If posted less than 24 hours ago, assume it could be yesterday
        # This is approximate - we also check against inserted_date in the data
        return False
    
    def is_yesterday_by_date(self, date_str: str) -> bool:
        """
        Check if date string matches yesterday's date
        Expected format: "2026-01-14" or "14-01-2026"
        """
        if not date_str:
            return False
        
        try:
            # Try format YYYY-MM-DD
            date_obj = datetime.strptime(date_str, "%Y-%m-%d").date()
            if date_obj == self.yesterday:
                return True
            
            # Try format DD-MM-YYYY
            date_obj = datetime.strptime(date_str, "%d-%m-%Y").date()
            return date_obj == self.yesterday
        except ValueError:
            return False
    
    def fetch_category_page(self, category_url: str, page: int = 1) -> Optional[Dict]:
        """
        Fetch category page and extract listings from API response in pageProps
        """
        try:
            url = f"{self.BASE_URL}/{category_url}"
            if page > 1:
                url += f"?page={page}"
            
            logger.info(f"Fetching: {url}")
            response = self.session.get(url, timeout=10)
            response.raise_for_status()
            
            # Parse HTML to extract JSON from __NEXT_DATA__
            soup = BeautifulSoup(response.content, 'html.parser')
            script_tag = soup.find('script', {'id': '__NEXT_DATA__'})
            
            if script_tag:
                data = json.loads(script_tag.string)
                return data.get('props', {}).get('pageProps', {})
            
            return None
        except Exception as e:
            logger.error(f"Error fetching {url}: {str(e)}")
            return None
    
    def fetch_listing_detail(self, listing_id: int) -> Optional[Dict]:
        """
        Fetch detailed listing data including full member info
        """
        try:
            url = f"{self.BASE_URL}/search/{listing_id}"
            logger.info(f"Fetching listing detail: {url}")
            
            response = self.session.get(url, timeout=10)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'html.parser')
            script_tag = soup.find('script', {'id': '__NEXT_DATA__'})
            
            if script_tag:
                data = json.loads(script_tag.string)
                return data.get('props', {}).get('pageProps', {})
            
            return None
        except Exception as e:
            logger.error(f"Error fetching listing {listing_id}: {str(e)}")
            return None
    
    def fetch_member_profile(self, member_link: str) -> Optional[Dict]:
        """
        Fetch member profile page with all rating info using the full member_link path
        """
        try:
            # member_link is a full path like '/ar/mid/member-152681542881'
            url = f"https://kw.opensooq.com{member_link}"
            logger.info(f"Fetching member profile: {url}")

            response = self.session.get(url, timeout=10)
            response.raise_for_status()

            soup = BeautifulSoup(response.content, 'html.parser')
            script_tag = soup.find('script', {'id': '__NEXT_DATA__'})

            if script_tag:
                data = json.loads(script_tag.string)
                return data.get('props', {}).get('pageProps', {})

            return None
        except Exception as e:
            logger.error(f"Error fetching member {member_link}: {str(e)}")
            return None
    
    def scrape_category(self, category_type: str, category_url: str) -> List[Dict]:
        """
        Scrape all listings from a category, filtering for yesterday's posts only.
        Returns list of processed listing dictionaries with details and seller info.
        """
        all_listings = []
        page = 1
        max_pages = 100  # Safety limit

        while page <= max_pages:
            page_data = self.fetch_category_page(category_url, page)

            if not page_data or 'serpApiResponse' not in page_data:
                logger.warning(f"No data found for {category_url} page {page}")
                break

            listings = page_data['serpApiResponse'].get('listings', {}).get('items', [])

            if not listings:
                logger.info(f"No listings on page {page}")
                break

            # Filter for yesterday's listings and process them
            for listing in listings:
                if self.is_yesterday_by_date(listing.get('inserted_date', '')):
                    listing['category_type'] = category_type
                    processed = self.extract_property_details(listing)
                    all_listings.append(processed)

            # Check pagination
            meta = page_data['serpApiResponse'].get('listings', {}).get('meta', {})
            total_pages = meta.get('pages', 1)
            current_page = meta.get('current_page', 1)

            if current_page >= total_pages:
                break

            page += 1

        logger.info(f"Found {len(all_listings)} listings from {category_type}")
        return all_listings
    
    def get_seller_info(self, listing: Dict) -> Dict:
        """Extract seller/member basic info from listing, including member_link for profile fetching"""
        return {
            'member_id': listing.get('member_id'),
            'member_display_name': listing.get('member_display_name'),
            'member_user_name': listing.get('member_user_name'),
            'member_avatar_uri': listing.get('member_avatar_uri'),
            'member_rating_avg': listing.get('member_rating_avg'),
            'member_rating_count': listing.get('member_rating_count'),
            'member_link': listing.get('member_link'),
        }
    
    def extract_property_details(self, listing: Dict) -> Dict:
        """Extract property details and seller info from listing"""
        return {
            'listing_id': listing.get('id'),
            'title': listing.get('title'),
            'description': listing.get('masked_description'),
            'price_amount': listing.get('price_amount'),
            'price_currency': listing.get('price_currency_iso'),
            'category': {
                'cat1_code': listing.get('cat1_code'),
                'cat1_label': listing.get('cat1_label'),
                'cat2_code': listing.get('cat2_code'),
                'cat2_label': listing.get('cat2_label'),
            },
            'location': {
                'city_id': listing.get('city_id'),
                'city_label': listing.get('city_label'),
                'nhood_id': listing.get('nhood_id'),
                'nhood_label': listing.get('nhood_label'),
            },
            'details': listing.get('highlightsObject', {}),
            'images_count': listing.get('image_count'),
            'posted_at': listing.get('posted_at'),
            'inserted_date': listing.get('inserted_date'),
            'is_active': listing.get('is_active'),
            'verification_level': listing.get('verification_level'),
            'seller': self.get_seller_info(listing),
            'local_images_dir': None,  # Will be populated after image download
            's3_image_path': None,  # Will be populated during processing
        }
