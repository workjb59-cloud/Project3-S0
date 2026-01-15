"""
Test script for Properties scraper
Validates setup and tests basic functionality
"""

import sys
import json
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

from scraper import PropertiesScraper
from processor import PropertiesProcessor, DataValidator
from config import PropertyConfig, LoggerSetup

logger = LoggerSetup.setup_logger(__name__)


def test_imports():
    """Test that all imports work"""
    logger.info("✓ Testing imports...")
    try:
        from scraper import PropertiesScraper
        from processor import PropertiesProcessor, DataValidator
        from s3_uploader import S3Uploader
        from config import PropertyConfig
        logger.info("✓ All imports successful")
        return True
    except Exception as e:
        logger.error(f"✗ Import failed: {str(e)}")
        return False


def test_scraper_init():
    """Test scraper initialization"""
    logger.info("✓ Testing scraper initialization...")
    try:
        scraper = PropertiesScraper()
        logger.info(f"✓ Scraper initialized successfully")
        logger.info(f"  - Base URL: {scraper.BASE_URL}")
        logger.info(f"  - Yesterday date: {scraper.yesterday}")
        logger.info(f"  - Rent subcategories: {len(scraper.RENT_SUBCATEGORIES)}")
        logger.info(f"  - Sale subcategories: {len(scraper.SALE_SUBCATEGORIES)}")
        return True
    except Exception as e:
        logger.error(f"✗ Scraper init failed: {str(e)}")
        return False


def test_processor_init():
    """Test processor initialization"""
    logger.info("✓ Testing processor initialization...")
    try:
        processor = PropertiesProcessor()
        logger.info(f"✓ Processor initialized successfully")
        logger.info(f"  - Temp directory: {processor.temp_dir}")
        logger.info(f"  - Timestamp: {processor.timestamp}")
        return True
    except Exception as e:
        logger.error(f"✗ Processor init failed: {str(e)}")
        return False


def test_date_filtering():
    """Test date filtering logic"""
    logger.info("✓ Testing date filtering...")
    scraper = PropertiesScraper()
    
    test_cases = [
        ("2026-01-14", True),    # Yesterday (assuming today is 2026-01-15)
        ("2026-01-13", False),   # Two days ago
        ("2026-01-15", False),   # Today
    ]
    
    passed = 0
    for date_str, expected in test_cases:
        result = scraper.is_yesterday_by_date(date_str)
        status = "✓" if result == expected else "✗"
        logger.info(f"  {status} {date_str}: {result} (expected {expected})")
        if result == expected:
            passed += 1
    
    logger.info(f"  Result: {passed}/{len(test_cases)} tests passed")
    return passed == len(test_cases)


def test_data_structures():
    """Test data structure creation"""
    logger.info("✓ Testing data structures...")
    
    try:
        # Create sample property data
        sample_listing = {
            'id': 123456,
            'title': 'Test Property',
            'price_amount': '1000',
            'price_currency_iso': 'KWD',
            'cat1_code': 'RealEstateForRent',
            'cat1_label': 'عقارات للايجار',
            'cat2_code': 'ApartmentsForRent',
            'cat2_label': 'شقق للايجار',
            'city_id': '48',
            'city_label': 'حولي',
            'nhood_id': '7429',
            'nhood_label': 'السالمية',
            'member_id': '123',
            'member_display_name': 'Test User',
            'member_rating_avg': 4.5,
            'member_rating_count': 10,
        }
        
        scraper = PropertiesScraper()
        property_data = scraper.extract_property_details(sample_listing)
        
        logger.info(f"  ✓ Property data structure created")
        logger.info(f"    - Keys: {len(property_data)}")
        logger.info(f"    - Has listing_id: {'listing_id' in property_data}")
        logger.info(f"    - Has category: {'category' in property_data}")
        logger.info(f"    - Has seller: {'seller' in property_data}")
        
        # Validate structure
        valid = DataValidator.validate_property(property_data)
        logger.info(f"  ✓ Validation result: {valid}")
        
        return valid
    except Exception as e:
        logger.error(f"✗ Data structure test failed: {str(e)}")
        return False


def test_config():
    """Test configuration loading"""
    logger.info("✓ Testing configuration...")
    
    try:
        logger.info(f"  ✓ Base URL: {PropertyConfig.BASE_URL}")
        logger.info(f"  ✓ Request timeout: {PropertyConfig.REQUEST_TIMEOUT}s")
        logger.info(f"  ✓ Rental category: {PropertyConfig.RENTAL_CATEGORY_URL}")
        logger.info(f"  ✓ Sale category: {PropertyConfig.SALE_CATEGORY_URL}")
        logger.info(f"  ✓ S3 bucket region: {PropertyConfig.S3_BUCKET_REGION}")
        logger.info(f"  ✓ Properties S3 path: {PropertyConfig.PROPERTIES_S3_PATH}")
        logger.info(f"  ✓ Info S3 path: {PropertyConfig.INFO_S3_PATH}")
        logger.info(f"  ✓ Scrape categories: {PropertyConfig.SCRAPE_CATEGORIES}")
        
        return True
    except Exception as e:
        logger.error(f"✗ Config test failed: {str(e)}")
        return False


def run_all_tests():
    """Run all tests"""
    logger.info("\n" + "="*60)
    logger.info("OpenSooq Properties Scraper - Test Suite")
    logger.info("="*60 + "\n")
    
    tests = [
        ("Imports", test_imports),
        ("Scraper Init", test_scraper_init),
        ("Processor Init", test_processor_init),
        ("Date Filtering", test_date_filtering),
        ("Data Structures", test_data_structures),
        ("Configuration", test_config),
    ]
    
    results = []
    for test_name, test_func in tests:
        logger.info(f"\n[Test] {test_name}")
        logger.info("-" * 40)
        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            logger.error(f"✗ Test crashed: {str(e)}")
            results.append((test_name, False))
    
    # Summary
    logger.info("\n" + "="*60)
    logger.info("Test Summary")
    logger.info("="*60)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for test_name, result in results:
        status = "✓ PASS" if result else "✗ FAIL"
        logger.info(f"  {status}: {test_name}")
    
    logger.info("-" * 60)
    logger.info(f"Total: {passed}/{total} tests passed")
    logger.info("="*60)
    
    if passed == total:
        logger.info("\n✓ All tests passed! Setup is ready.")
        return 0
    else:
        logger.warning(f"\n✗ {total - passed} test(s) failed. Please review.")
        return 1


if __name__ == '__main__':
    exit_code = run_all_tests()
    sys.exit(exit_code)
