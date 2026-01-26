"""
Configuration for OpenSooq Services Scraper
"""

# Base URLs
BASE_URL = "https://kw.opensooq.com/ar"
SERVICES_URL = f"{BASE_URL}/الخدمات"

# HTTP Headers
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
    'Accept-Language': 'ar,en-US;q=0.9,en;q=0.8',
    'Accept-Encoding': 'gzip, deflate, br',
    'Connection': 'keep-alive',
    'Upgrade-Insecure-Requests': '1',
    'Sec-Fetch-Dest': 'document',
    'Sec-Fetch-Mode': 'navigate',
    'Sec-Fetch-Site': 'none',
    'Cache-Control': 'max-age=0'
}

# Request settings
REQUEST_TIMEOUT = 30  # seconds
MAX_RETRIES = 3
RETRY_DELAY = 5  # seconds

# Pagination
LISTINGS_PER_PAGE = 30

# S3 Settings
S3_BASE_FOLDER = 'services'
S3_LISTINGS_SUBFOLDER = 'json-files'
S3_MEMBER_INFO_SUBFOLDER = 'info-json'

# Service Categories (will be fetched dynamically)
# This is a reference of expected categories
EXPECTED_CATEGORIES = [
    'Education & Training',
    'Maintenance & Handyman',
    'Construction & Contracting',
    'Transportation, Moving & Delivery',
    'Electronics & Appliances Repair',
    'Cleaning & Laundry',
    'Business & Professional',
    'Motors',
    'Healthcare & Beauty',
    'Events & Occasions',
    'Gardening & Landscaping',
    'Domestic & Childcare',
    'Pet Care'
]
