"""
Data Processor for Home and Garden Listings
Processes raw API data and prepares for S3 upload
"""

import json
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
import re

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class ListingProcessor:
    """Processes listing data and extracts relevant information"""
    
    @staticmethod
    def is_yesterday_ad(posted_at: str) -> bool:
        """
        Check if an ad was posted yesterday (in the last 24 hours starting from yesterday)
        
        Args:
            posted_at: Posted date string in Arabic (e.g., "قبل ساعة", "أمس", "قبل يوم")
        
        Returns:
            True if ad was posted yesterday
        """
        try:
            # Check for "أمس" (yesterday)
            if "أمس" in posted_at:
                return True
            
            # Check for "يوم" (1 day ago)
            if "قبل يوم" in posted_at or "قبل 1 يوم" in posted_at:
                return True
            
            # Reject "أيام" (multiple days)
            if re.search(r'قبل \d+ أيام', posted_at):
                return False
            
            # Check for hours - accept if within 24 hours
            hour_match = re.search(r'قبل (\d+) ساع', posted_at)
            if hour_match:
                hours = int(hour_match.group(1))
                return hours <= 24
            
            # Check for single hour: "قبل ساعة"
            if "قبل ساعة" in posted_at:
                return True
            
            # Check for minutes
            if "دقيقة" in posted_at or "دقائق" in posted_at:
                return True
            
            return False
        except Exception as e:
            logger.error(f"Error checking date for '{posted_at}': {e}")
            return False

    @staticmethod
    def extract_listing_details(detail_page_data: Dict) -> Dict:
        """
        Extract relevant listing details from detail page response
        
        Args:
            detail_page_data: Full response from detail page API
        
        Returns:
            Processed listing details
        """
        try:
            listing = detail_page_data.get('postData', {}).get('listing', {})
            
            processed = {
                'listing_id': listing.get('listing_id'),
                'title': listing.get('title'),
                'description': listing.get('masked_description'),
                'price': listing.get('price_amount'),
                'currency': listing.get('price', {}).get('currencies', [{}])[0].get('currency_code', 'KWD'),
                'city': listing.get('city', {}).get('label'),
                'city_id': listing.get('city', {}).get('id'),
                'neighborhood': listing.get('neighborhood', {}).get('label'),
                'neighborhood_id': listing.get('neighborhood', {}).get('id'),
                'posted_date': listing.get('posted_date'),
                'publish_date': listing.get('publish_date'),
                'price_valid_until': listing.get('price_valid_until'),
                'main_category': listing.get('category', {}).get('label'),
                'main_category_id': listing.get('category', {}).get('id'),
                'sub_category': listing.get('sub_category', {}).get('label'),
                'sub_category_id': listing.get('sub_category', {}).get('id'),
                'has_delivery': listing.get('has_delivery_service', False),
                'member_id': listing.get('member_id'),
                'condition': None,
                'images': [],
                's3_image_paths': [],
            }
            
            # Extract condition
            basic_info = listing.get('basic_info', [])
            for info in basic_info:
                if info.get('field_name') == 'ConditionUsed':
                    processed['condition'] = info.get('option_label')
                    break
            
            # Extract images
            media = listing.get('media', [])
            for idx, media_item in enumerate(media):
                processed['images'].append({
                    'id': media_item.get('id'),
                    'uri': media_item.get('uri'),
                    'type': media_item.get('mime_type', 'image/jpeg')
                })
            
            return processed
        except Exception as e:
            logger.error(f"Error extracting listing details: {e}")
            return {}

    @staticmethod
    def extract_member_info(detail_page_data: Dict) -> Dict:
        """
        Extract member/seller information from detail page
        
        Args:
            detail_page_data: Full response from detail page API
        
        Returns:
            Member information
        """
        try:
            seller = detail_page_data.get('postData', {}).get('listing', {}).get('seller', {})
            
            member_info = {
                'member_id': seller.get('id'),
                'full_name': seller.get('full_name'),
                'rating_avg': seller.get('rating_avg'),
                'number_of_ratings': seller.get('number_of_ratings'),
                'member_since': seller.get('member_since'),
                'is_shop': seller.get('is_shop', False),
                'response_time': seller.get('response_time'),
                'authorised_seller': seller.get('authorised_seller', False),
                'verification_level': seller.get('verification_level', 0),
                'is_pro_buyer': seller.get('is_pro_buyer', False),
                'member_link': seller.get('member_link'),
                'profile_picture': seller.get('profile_picture'),
                'last_updated': datetime.now().isoformat(),
                'listings_count': None  # Can be updated if needed
            }
            
            return {k: v for k, v in member_info.items() if v is not None}
        except Exception as e:
            logger.error(f"Error extracting member info: {e}")
            return {}

    @staticmethod
    def extract_property_info(detail_page_data: Dict) -> Dict:
        """
        Extract property information (without seller info)
        
        Args:
            detail_page_data: Full response from detail page API
        
        Returns:
            Property information
        """
        listing = detail_page_data.get('postData', {}).get('listing', {})
        
        property_info = ListingProcessor.extract_listing_details(detail_page_data)
        
        # Remove member_id from property info (it goes to seller separately)
        if 'member_id' in property_info:
            del property_info['member_id']
        
        return property_info


class ScraperDataManager:
    """Manages data collection and batch processing"""
    
    def __init__(self):
        self.listings_batch: List[Dict] = []
        self.members_batch: List[Dict] = []
        self.properties_batch: List[Dict] = []
        self.images_to_download: List[Dict] = []

    def add_listing(self, listing: Dict, member: Dict, images: List[Dict]):
        """Add listing with related data"""
        self.listings_batch.append(listing)
        self.members_batch.append(member)
        self.images_to_download.extend(images)

    def get_unique_members(self) -> List[Dict]:
        """Get unique members from batch"""
        seen = set()
        unique = []
        for member in self.members_batch:
            member_id = member.get('member_id')
            if member_id and member_id not in seen:
                seen.add(member_id)
                unique.append(member)
        return unique

    def clear_batches(self):
        """Clear all batches"""
        self.listings_batch = []
        self.members_batch = []
        self.properties_batch = []
        self.images_to_download = []

    def get_batch_summary(self) -> Dict:
        """Get summary of current batch"""
        return {
            'listings_count': len(self.listings_batch),
            'unique_members': len(self.get_unique_members()),
            'images_to_download': len(self.images_to_download),
        }
