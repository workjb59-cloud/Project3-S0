"""
Properties Data Processor
Structures scraped property data and member information into separate JSON files
"""

import json
import logging
from datetime import datetime
from typing import Dict, List, Tuple
from pathlib import Path
import hashlib

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class PropertiesProcessor:
    """Processes and structures property data"""
    
    def __init__(self, temp_dir: str = "/tmp"):
        """Initialize processor with temporary directory for staging"""
        self.temp_dir = Path(temp_dir)
        self.temp_dir.mkdir(exist_ok=True)
        self.processed_members = {}  # Track unique members by ID
        self.timestamp = datetime.now().isoformat()
    
    def get_member_hash(self, member_id: int) -> str:
        """Generate hash for member to check if already processed"""
        return hashlib.md5(str(member_id).encode()).hexdigest()
    
    def extract_member_full_info(self, member_data: Dict) -> Dict:
        """
        Extract full member information from member profile data
        This includes ratings, tags, and all detailed information
        """
        if not member_data:
            return {}
        
        member_info = member_data.get('info', {}).get('member', {})
        rating = member_info.get('rating', {})
        
        return {
            'member_id': member_info.get('id'),
            'name': member_info.get('branding', {}).get('name'),
            'is_shop': member_info.get('is_shop'),
            'has_membership': member_info.get('has_membership'),
            'member_since': member_info.get('member_since'),
            'posts_count': member_info.get('posts_count'),
            'views_count': member_info.get('views_count'),
            'followers_count': member_info.get('following', {}).get('followers_count'),
            'following_count': member_info.get('following', {}).get('followings_count'),
            'rating': {
                'average': rating.get('average_rating'),
                'count': rating.get('number_of_rating'),
                'reviews_count': rating.get('number_of_reviews'),
                'stats': rating.get('stats', {}),
                'tags': rating.get('tags', []),
            },
            'verification_level': member_info.get('verification_level'),
            'authorised_seller': member_info.get('authorised_seller'),
            'avatar_uri': member_info.get('branding', {}).get('avatar'),
            'extracted_at': self.timestamp,
        }
    
    def extract_property_by_subcategory(self, listings: List[Dict]) -> Dict[str, List[Dict]]:
        """
        Group property listings by subcategory
        Returns dict with subcategory as key and list of properties as value
        """
        grouped = {}
        
        for listing in listings:
            cat2_label = listing.get('cat2_label', 'unknown')
            
            if cat2_label not in grouped:
                grouped[cat2_label] = []
            
            grouped[cat2_label].append(listing)
        
        return grouped
    
    def prepare_properties_json(self, listings: List[Dict]) -> Dict[str, List[Dict]]:
        """
        Prepare properties data grouped by subcategory
        Each property includes details and basic seller info
        """
        grouped_properties = self.extract_property_by_subcategory(listings)
        result = {}
        
        for subcategory, properties in grouped_properties.items():
            result[subcategory] = {
                'count': len(properties),
                'scraped_at': self.timestamp,
                'properties': properties,
            }
        
        return result
    
    def prepare_members_json(self, member_data_list: List[Dict]) -> List[Dict]:
        """
        Prepare incremental member information JSON
        Each entry represents unique member data with all rating information
        """
        unique_members = {}
        
        for member_data in member_data_list:
            if not member_data:
                continue
            
            member_id = member_data.get('member_id')
            if not member_id:
                continue
            
            # Store only if not already processed or if newer data
            if member_id not in unique_members:
                unique_members[member_id] = member_data
        
        # Convert to list and sort by member_id
        members_list = sorted(
            unique_members.values(),
            key=lambda x: x.get('member_id', 0)
        )
        
        return {
            'count': len(members_list),
            'scraped_at': self.timestamp,
            'members': members_list,
        }
    
    def save_properties_locally(self, properties_by_category: Dict) -> Tuple[str, int]:
        """
        Save properties data to local JSON file
        Returns tuple of (file_path, total_properties)
        """
        filename = self.temp_dir / f"properties_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        
        total_props = sum(
            len(cat_data.get('properties', []))
            for cat_data in properties_by_category.values()
        )
        
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(properties_by_category, f, ensure_ascii=False, indent=2)
        
        logger.info(f"Saved {total_props} properties to {filename}")
        return str(filename), total_props
    
    def save_members_locally(self, members_data: Dict) -> Tuple[str, int]:
        """
        Save members/member information to local JSON file
        Returns tuple of (file_path, total_members)
        """
        filename = self.temp_dir / f"members_info_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(members_data, f, ensure_ascii=False, indent=2)
        
        total_members = members_data.get('count', 0)
        logger.info(f"Saved {total_members} members to {filename}")
        return str(filename), total_members
    
    def process_listings(self, listings: List[Dict], member_details: Dict[int, Dict]) -> Tuple[Dict, Dict]:
        """
        Main processing function
        Takes scraped listings and member details, returns structured data for upload
        
        Args:
            listings: List of property listings
            member_details: Dict of member_id -> full member data
        
        Returns:
            Tuple of (properties_data, members_data)
        """
        # Prepare properties by category
        properties_data = self.prepare_properties_json(listings)
        
        # Prepare member information
        member_list = list(member_details.values())
        members_data = self.prepare_members_json(member_list)
        
        logger.info(f"Processing complete: {sum(cat['count'] for cat in properties_data.values())} properties, {members_data['count']} members")
        
        return properties_data, members_data


class DataValidator:
    """Validates scraped and processed data"""
    
    @staticmethod
    def validate_property(property_data: Dict) -> bool:
        """Validate required fields in property data"""
        required_fields = ['listing_id', 'title', 'price_amount', 'category']
        return all(field in property_data for field in required_fields)
    
    @staticmethod
    def validate_member(member_data: Dict) -> bool:
        """Validate required fields in member data"""
        required_fields = ['member_id', 'name']
        return all(field in member_data for field in required_fields)
    
    @staticmethod
    def validate_listings(listings: List[Dict]) -> Tuple[int, int]:
        """
        Validate all listings, return (valid_count, invalid_count)
        """
        valid = 0
        invalid = 0
        
        for listing in listings:
            if DataValidator.validate_property(listing):
                valid += 1
            else:
                invalid += 1
                logger.warning(f"Invalid property data: {listing.get('id', 'unknown')}")
        
        return valid, invalid
