"""
Configuration for Shops category scraper
"""

# Category-specific configuration
CATEGORY = "shops"
CATEGORY_NAME_AR = "متاجر"
CATEGORY_URL = "https://kw.opensooq.com/ar/متاجر"

# S3 paths
S3_CATEGORY_PATH = "shops"  # Will be used in: opensooq-data/{S3_CATEGORY_PATH}/year=...

# Scraping settings
DELAY_BETWEEN_SHOPS = 3  # seconds
DELAY_BETWEEN_PAGES = 2  # seconds
MAX_RETRIES = 3
REQUEST_TIMEOUT = 30

# Data fields to extract from shop listing
SHOP_LISTING_FIELDS = [
    'member_id',
    'title',
    'logo',
    'city_id',
    'post_count',
    'rating',
    'city',
    'shop_url',
    'authorised_seller',
    'verification_level'
]

# Data fields to extract from ads
AD_FIELDS = [
    'id',
    'title',
    'posted_at',
    'expired_at',
    'price_amount',
    'price_currency_iso',
    'city_id',
    'city_label',
    'nhood_id',
    'nhood_label',
    'cat1_code',
    'cat1_label',
    'cat2_code',
    'cat2_label',
    'image_uri',
    'image_count',
    'has_video',
    'has_360',
    'highlights',
    'masked_description',
    'post_url',
    'phone_number',
    'member_rating_avg',
    'member_rating_count',
    'verification_level',
    'listing_status'
]
