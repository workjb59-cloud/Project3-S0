#!/usr/bin/env python3
"""
Test script for Home and Garden Scraper
Helps verify setup and test individual components
"""

import sys
import os
import json
from pathlib import Path
from datetime import datetime

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from Home_and_Garden.config import BASE_URL, MAIN_CATEGORIES, HEADERS
from Home_and_Garden.s3_uploader import HomeGardenS3Uploader
from Home_and_Garden.processor import ListingProcessor, ScraperDataManager
from utils import extract_json_from_html
import requests
from bs4 import BeautifulSoup


def test_imports():
    """Test if all imports work"""
    print("\n" + "="*60)
    print("TEST 1: Checking Imports")
    print("="*60)
    try:
        from Home_and_Garden import (
            HomeGardenScraper,
            HomeGardenS3Uploader,
            ListingProcessor,
            config
        )
        print("✅ All imports successful")
        return True
    except ImportError as e:
        print(f"❌ Import error: {e}")
        return False


def test_environment():
    """Test if environment variables are set"""
    print("\n" + "="*60)
    print("TEST 2: Checking Environment Variables")
    print("="*60)
    
    required_vars = [
        'AWS_S3_BUCKET_NAME',
        'AWS_ACCESS_KEY_ID',
        'AWS_SECRET_ACCESS_KEY',
    ]
    
    all_set = True
    for var in required_vars:
        value = os.getenv(var)
        if value:
            masked = value[:10] + '...' if len(value) > 10 else value
            print(f"✅ {var} = {masked}")
        else:
            print(f"❌ {var} not set")
            all_set = False
    
    aws_region = os.getenv('AWS_REGION', 'us-east-1')
    print(f"✅ AWS_REGION = {aws_region}")
    
    return all_set


def test_s3_connection():
    """Test S3 connection"""
    print("\n" + "="*60)
    print("TEST 3: Testing S3 Connection")
    print("="*60)
    
    try:
        bucket_name = os.getenv('AWS_S3_BUCKET_NAME')
        aws_access_key = os.getenv('AWS_ACCESS_KEY_ID')
        aws_secret_key = os.getenv('AWS_SECRET_ACCESS_KEY')
        
        if not all([bucket_name, aws_access_key, aws_secret_key]):
            print("❌ Missing AWS credentials")
            return False
        
        uploader = HomeGardenS3Uploader(bucket_name, aws_access_key, aws_secret_key)
        print(f"✅ Successfully connected to S3 bucket: {bucket_name}")
        return True
    except Exception as e:
        print(f"❌ S3 connection failed: {e}")
        return False


def test_network():
    """Test network connectivity"""
    print("\n" + "="*60)
    print("TEST 4: Testing Network Connectivity")
    print("="*60)
    
    try:
        response = requests.get(BASE_URL, headers=HEADERS, timeout=10)
        if response.status_code == 200:
            print(f"✅ Successfully reached {BASE_URL}")
            return True
        else:
            print(f"❌ Got status code {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Network error: {e}")
        return False


def test_json_extraction():
    """Test JSON extraction from HTML"""
    print("\n" + "="*60)
    print("TEST 5: Testing JSON Extraction from HTML")
    print("="*60)
    
    try:
        url = f"{BASE_URL}/ar/المنزل-والحديقة"
        print(f"Fetching {url}...")
        response = requests.get(url, headers=HEADERS, timeout=15)
        response.raise_for_status()
        
        data = extract_json_from_html(response.text, 'pageProps')
        
        if data:
            # Check for facets
            facets = data.get('serpApiResponse', {}).get('facets', {}).get('items', [])
            if facets:
                print(f"✅ Successfully extracted JSON")
                print(f"✅ Found {len(facets)} subcategories:")
                for i, facet in enumerate(facets[:3], 1):
                    label = facet.get('label', 'N/A')
                    count = facet.get('count', 0)
                    print(f"   {i}. {label} ({count} items)")
                return True
            else:
                print("❌ No facets found in response")
                return False
        else:
            print("❌ Could not extract JSON from HTML")
            return False
    except Exception as e:
        print(f"❌ JSON extraction error: {e}")
        return False


def test_listing_filter():
    """Test yesterday's listing filter"""
    print("\n" + "="*60)
    print("TEST 6: Testing Listing Filter")
    print("="*60)
    
    test_cases = [
        ("قبل ساعة", True, "1 hour ago"),
        ("قبل 2 ساعات", True, "2 hours ago"),
        ("قبل 12 ساعات", True, "12 hours ago"),
        ("قبل 24 ساعة", True, "24 hours ago"),
        ("قبل 48 ساعة", False, "48 hours ago"),
        ("أمس", True, "yesterday"),
        ("قبل يوم", True, "1 day ago"),
        ("قبل 2 أيام", False, "2 days ago"),
        ("قبل دقيقة", True, "1 minute ago"),
        ("دقائق قليلة", True, "few minutes ago"),
    ]
    
    print("Testing date filter:")
    all_pass = True
    for posted_at, expected, description in test_cases:
        result = ListingProcessor.is_yesterday_ad(posted_at)
        status = "✅" if result == expected else "❌"
        all_pass = all_pass and (result == expected)
        print(f"{status} '{posted_at}' ({description}): {result} (expected {expected})")
    
    return all_pass


def test_data_processing():
    """Test data processing"""
    print("\n" + "="*60)
    print("TEST 7: Testing Data Processing")
    print("="*60)
    
    try:
        # Create mock data
        mock_data = {
            'postData': {
                'listing': {
                    'listing_id': 276167705,
                    'title': 'طقم قنفات للبيع',
                    'masked_description': 'للبيع قنفات جديدة',
                    'price_amount': 300,
                    'city': {'label': 'الفروانية', 'id': 47},
                    'neighborhood': {'label': 'العارضية', 'id': 7449},
                    'category': {'label': 'منزل وحديقة', 'id': 1911},
                    'sub_category': {'label': 'أثاث غرف جلوس', 'id': 39281},
                    'posted_date': 'قبل 8 ساعات',
                    'media': [
                        {'id': 1, 'uri': 'image1.jpg', 'mime_type': 'image/jpeg'},
                        {'id': 2, 'uri': 'image2.jpg', 'mime_type': 'image/jpeg'},
                    ],
                    'seller': {
                        'id': 18802169,
                        'full_name': 'شيخه',
                        'rating_avg': 0,
                        'number_of_ratings': 0,
                        'member_since': '18-07-2017',
                        'is_shop': False,
                    },
                    'basic_info': [
                        {'field_name': 'ConditionUsed', 'option_label': 'جديد'}
                    ]
                }
            }
        }
        
        # Test extraction
        listing = ListingProcessor.extract_listing_details(mock_data)
        member = ListingProcessor.extract_member_info(mock_data)
        
        if listing and member:
            print("✅ Listing extraction successful")
            print(f"   Title: {listing.get('title')}")
            print(f"   Price: {listing.get('price')} {listing.get('currency')}")
            print(f"   Images: {len(listing.get('images', []))}")
            
            print("✅ Member extraction successful")
            print(f"   Name: {member.get('full_name')}")
            print(f"   Since: {member.get('member_since')}")
            
            return True
        else:
            print("❌ Data extraction failed")
            return False
    except Exception as e:
        print(f"❌ Data processing error: {e}")
        return False


def test_data_manager():
    """Test data manager"""
    print("\n" + "="*60)
    print("TEST 8: Testing Data Manager")
    print("="*60)
    
    try:
        manager = ScraperDataManager()
        
        # Add test data
        listing = {'listing_id': 1, 'title': 'Test'}
        member1 = {'member_id': 100, 'full_name': 'Member 1'}
        member2 = {'member_id': 101, 'full_name': 'Member 2'}
        images = [{'uri': 'img1.jpg'}, {'uri': 'img2.jpg'}]
        
        manager.add_listing(listing, member1, images)
        manager.add_listing(listing, member2, [])
        
        unique_members = manager.get_unique_members()
        
        if len(unique_members) == 2:
            print("✅ Data manager working correctly")
            print(f"   Listings: {len(manager.listings_batch)}")
            print(f"   Unique members: {len(unique_members)}")
            print(f"   Images: {len(manager.images_to_download)}")
            return True
        else:
            print(f"❌ Expected 2 unique members, got {len(unique_members)}")
            return False
    except Exception as e:
        print(f"❌ Data manager error: {e}")
        return False


def print_summary(results):
    """Print test summary"""
    print("\n" + "="*60)
    print("TEST SUMMARY")
    print("="*60)
    
    passed = sum(1 for result in results.values() if result)
    total = len(results)
    
    for test_name, result in results.items():
        status = "✅" if result else "❌"
        print(f"{status} {test_name}")
    
    print("-" * 60)
    print(f"Passed: {passed}/{total}")
    
    if passed == total:
        print("\n🎉 All tests passed! Ready to scrape.")
    else:
        print(f"\n⚠️  {total - passed} test(s) failed. Please fix and try again.")
    
    return passed == total


def main():
    """Run all tests"""
    print("\n" + "="*80)
    print("HOME AND GARDEN SCRAPER - TEST SUITE")
    print("="*80)
    
    results = {
        "Imports": test_imports(),
        "Environment Variables": test_environment(),
        "S3 Connection": test_s3_connection(),
        "Network Connectivity": test_network(),
        "JSON Extraction": test_json_extraction(),
        "Listing Filter": test_listing_filter(),
        "Data Processing": test_data_processing(),
        "Data Manager": test_data_manager(),
    }
    
    all_pass = print_summary(results)
    
    print("\n" + "="*80)
    return 0 if all_pass else 1


if __name__ == '__main__':
    exit(main())
