"""
Data Processor for Properties Listings
Processes raw API data and prepares for S3 upload
"""

import json
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import re

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class PropertiesProcessor:
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
            
            # Check for hours - accept if within 24 hours (yesterday's ads)
            hour_match = re.search(r'قبل (\d+) ساع', posted_at)
            if hour_match:
                hours = int(hour_match.group(1))
                # Accept ads posted within last 24-48 hours as "yesterday"
                return 24 <= hours <= 48
            
            # Check for single hour: "قبل ساعة"
            if "قبل ساعة" in posted_at:
                return False  # Too recent
            
            # Check for minutes - reject (too recent)
            if "دقيقة" in posted_at or "دقائق" in posted_at:
                return False
            
            # Check for "الآن" (now)
            if "الآن" in posted_at:
                return False
            
            return False
        except Exception as e:
            logger.warning(f"Error parsing date '{posted_at}': {e}")
            return False
    
    @staticmethod
    def clean_listing_data(listing: Dict, s3_image_paths: List[str] = None) -> Dict:
        """
        Clean and normalize listing data
        
        Args:
            listing: Raw listing data
            s3_image_paths: List of S3 paths for uploaded images
        
        Returns:
            Cleaned listing data
        """
        return {
            'listing_id': listing.get('listing_id'),
            'title': listing.get('title'),
            'description': listing.get('masked_description'),
            'price': listing.get('price'),
            'price_amount': listing.get('price_amount'),
            'city': listing.get('city'),
            'neighborhood': listing.get('neighborhood'),
            'category': listing.get('category'),
            'sub_category': listing.get('sub_category'),
            'posted_date': listing.get('posted_date'),
            'publish_date': listing.get('publish_date'),
            'media': listing.get('media', []),
            's3_image_paths': s3_image_paths or [],
            'basic_info': listing.get('basic_info', []),
            'post_url': listing.get('post_url'),
            'member_id': listing.get('member_id'),
            'has_video': listing.get('has_video'),
            'has_360': listing.get('has_360'),
            'services': listing.get('services', []),
            'listing_status': listing.get('listing_status'),
            'is_active': listing.get('is_active')
        }
    
    @staticmethod
    def clean_seller_data(seller: Dict) -> Dict:
        """
        Clean and normalize seller data
        
        Args:
            seller: Raw seller data
        
        Returns:
            Cleaned seller data
        """
        return {
            'id': seller.get('id'),
            'full_name': seller.get('full_name'),
            'profile_picture': seller.get('profile_picture'),
            'member_since': seller.get('member_since'),
            'rating_avg': seller.get('rating_avg'),
            'number_of_ratings': seller.get('number_of_ratings'),
            'response_time': seller.get('response_time'),
            'is_shop': seller.get('is_shop'),
            'member_link': seller.get('member_link'),
            'verification_level': seller.get('verification_level')
        }


class PropertiesDataManager:
    """Manages scraped data and organizes it for S3 upload"""
    
    def __init__(self):
        """Initialize data storage"""
        self.subcategory_data = {}  # {category: {subcategory: [listings]}}
        self.member_info = {}  # {member_id: member_data}
        self.processor = PropertiesProcessor()
    
    def add_subcategory_data(self, category: str, subcategory: str, listings: List[Dict]):
        """
        Add listings for a subcategory
        
        Args:
            category: Main category name
            subcategory: Subcategory name
            listings: List of listing data dicts (with s3_image_paths)
        """
        if category not in self.subcategory_data:
            self.subcategory_data[category] = {}
        
        if subcategory not in self.subcategory_data[category]:
            self.subcategory_data[category][subcategory] = []
        
        # Clean and add listings
        for listing_data in listings:
            s3_image_paths = listing_data.get('s3_image_paths', [])
            cleaned_listing = self.processor.clean_listing_data(
                listing_data.get('listing', {}),
                s3_image_paths
            )
            cleaned_seller = self.processor.clean_seller_data(listing_data.get('seller', {}))
            
            self.subcategory_data[category][subcategory].append({
                'listing': cleaned_listing,
                'seller': cleaned_seller
            })
    
    def add_member_info(self, member_id: int, member_data: Dict):
        """
        Add member information (incremental)
        
        Args:
            member_id: Member ID
            member_data: Member information dict
        """
        if member_id not in self.member_info:
            self.member_info[member_id] = {
                'id': member_id,
                'name': member_data.get('branding', {}).get('name'),
                'avatar': member_data.get('branding', {}).get('avatar'),
                'posts_count': member_data.get('posts_count'),
                'views_count': member_data.get('views_count'),
                'member_since': member_data.get('member_since'),
                'response_time': member_data.get('response_time'),
                'rating': member_data.get('rating', {}),
                'following': member_data.get('following', {}),
                'verification_level': member_data.get('verification_level'),
                'is_shop': member_data.get('is_shop'),
                'mobile_number': member_data.get('mobile_number'),
                'authorised_seller': member_data.get('authorised_seller')
            }
    
    def get_subcategory_data(self) -> Dict:
        """Get all subcategory data"""
        return self.subcategory_data
    
    def get_member_info_list(self) -> List[Dict]:
        """Get member info as a list"""
        return list(self.member_info.values())
    
    def get_stats(self) -> Dict:
        """Get scraping statistics"""
        total_categories = len(self.subcategory_data)
        total_subcategories = sum(len(subs) for subs in self.subcategory_data.values())
        total_listings = sum(
            len(listings) 
            for category in self.subcategory_data.values()
            for listings in category.values()
        )
        total_members = len(self.member_info)
        
        return {
            'total_categories': total_categories,
            'total_subcategories': total_subcategories,
            'total_listings': total_listings,
            'total_members': total_members
        }
