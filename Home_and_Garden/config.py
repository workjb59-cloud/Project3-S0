"""
Configuration for Home and Garden Scraper
"""

# URLs
BASE_URL = "https://kw.opensooq.com"
MAIN_CATEGORY_URL = f"{BASE_URL}/ar/المنزل-والحديقة"

# Main categories to scrape (facets)
MAIN_CATEGORIES = {
    "الأثاث": "المنزل-والحديقة/الأثاث",
    "ديكور المنزل وإكسسواراته": "المنزل-والحديقة/ديكور-المنزل-وإكسسواراته",
    "المنزل والحديقة أخرى": "المنزل-والحديقة/شراء-الأثاث-المستعمل",
    "أواني وأطباق المطبخ": "المنزل-والحديقة/أواني-وأطباق-المطبخ",
    "أثاث الحدائق والخارج": "المنزل-والحديقة/أثاث-الحدائق-والخارج",
    "أبواب ونوافذ وبوابات": "المنزل-والحديقة/أبواب-شباببيك-ألمنيوم",
    "نباتات": "المنزل-والحديقة/نباتات",
    "إضاءة": "المنزل-والحديقة/الإضاءة",
    "الحمامات وإكسسواراتها": "المنزل-والحديقة/حمامات",
    "بلاط وأرضيات": "المنزل-والحديقة/بلاط-أرضيات-باركيه",
    "مسابح وساونا": "المنزل-والحديقة/مسابح-وساونا",
}

# S3 Configuration
S3_BASE_BUCKET = "opensooq-data"
S3_HOME_GARDEN_DATA_PATH = "home-garden"
S3_PROPERTIES_DATA_PATH = "properties"
S3_IMAGES_FOLDER = "images"
S3_INFO_JSON_PATH = "properties/info-json"

# Pagination
LISTINGS_PER_PAGE = 30

# Request headers
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8',
    'Accept-Language': 'ar-SA,ar;q=0.9,en-US;q=0.8,en;q=0.7',
    'Accept-Encoding': 'gzip, deflate, br',
    'DNT': '1',
    'Connection': 'keep-alive',
    'Upgrade-Insecure-Requests': '1',
    'Sec-Fetch-Dest': 'document',
    'Sec-Fetch-Mode': 'navigate',
    'Sec-Fetch-Site': 'none',
    'Cache-Control': 'max-age=0',
}

# Date format
DATE_FORMAT = "%Y-%m-%d"
PARTITION_FORMAT = "year={year}/month={month:02d}/day={day:02d}"

# Timeout
REQUEST_TIMEOUT = 30
