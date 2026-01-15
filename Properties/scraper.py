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
    
    def fetch_member_profile(self, member_id: int) -> Optional[Dict]:
        """
        Fetch member profile page with all rating info
        """
        try:
            # Member link format: /ar/mid/member-{username}
            # We need to get the username from listing, but we can use member_id
            url = f"{self.BASE_URL}/mid/member-{member_id}"
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
            logger.error(f"Error fetching member {member_id}: {str(e)}")
            return None
    
    def scrape_category(self, category_type: str, category_url: str) -> List[Dict]:
        """
        Scrape all listings from a category, filtering for yesterday's posts only
        Returns list of listing dictionaries with details and seller info
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
            
            # Filter for yesterday's listings
            for listing in listings:
                if self.is_yesterday_by_date(listing.get('inserted_date', '')):
                    listing['category_type'] = category_type
                    all_listings.append(listing)
            
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
        """Extract seller/member basic info from listing"""
        return {
            'member_id': listing.get('member_id'),
            'member_display_name': listing.get('member_display_name'),
            'member_user_name': listing.get('member_user_name'),
            'member_avatar_uri': listing.get('member_avatar_uri'),
            'member_rating_avg': listing.get('member_rating_avg'),
            'member_rating_count': listing.get('member_rating_count'),
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
        }
