"""
Configuration for OpenSooq Businesses & Industrial Scraper
"""

# Base URLs
BASE_URL = "https://kw.opensooq.com/ar"
BUSINESSES_URL = f"{BASE_URL}/شركات-صناعية"

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
S3_BASE_FOLDER = 'businesses-industrial'
S3_LISTINGS_SUBFOLDER = 'json-files'
S3_IMAGES_SUBFOLDER = 'images'
S3_MEMBER_INFO_SUBFOLDER = 'info-json'

# Expected Categories (reference)
EXPECTED_CATEGORIES = [
    'Equipment for Businesses',
    'Ready Businesses & Investments'
]
