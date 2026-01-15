"""
Configuration and utilities for Properties module
"""

import logging
from typing import Dict, List
from datetime import datetime

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class PropertyConfig:
    """Configuration constants for property scraping and processing"""
    
    # OpenSooq Base Configuration
    BASE_URL = "https://kw.opensooq.com/ar"
    REQUEST_TIMEOUT = 10
    MAX_RETRIES = 3
    
    # Category configurations
    RENTAL_CATEGORY_URL = "عقارات/عقارات-للإيجار"
    SALE_CATEGORY_URL = "عقارات/عقارات-للبيع"
    
    # Rent Subcategories
    RENT_SUBCATEGORIES = {
        8001: "شقق-للايجار",
        12447: "شقق-وأجنحة-فندقية-للايجار",
        12487: "غرف-وسكن-مشترك-للايجار",
        8003: "فلل-وقصور-للايجار",
        12696: "بيوت-ومنازل-للايجار",
        8009: "عمارة-سكنية-للايجار",
        12813: "أراضي-للايجار",
        12893: "مزارع-وشاليهات-للايجار",
        16735: "مكاتب-للايجار",
        16775: "محلات-للايجار",
        16815: "معارض-للايجار",
        16855: "مخازن-للايجار",
        16895: "طابق-كامل-للايجار",
        16935: "مجمعات-للايجار",
        16975: "فلل-تجارية-للايجار",
        17015: "مطاعم-وكافيهات-للايجار",
        17055: "سوبرماركت-للايجار",
        17095: "عيادات-للايجار",
        17135: "مصانع-للايجار",
        17175: "سكن-موظفين-للايجار",
        17215: "فنادق-للايجار",
        11339: "عقارات-أجنبية-للايجار",
    }
    
    # Sale Subcategories
    SALE_SUBCATEGORIES = {
        7683: "شقق-للبيع",
        7685: "فلل-وقصور-للبيع",
        12658: "أراضي-للبيع",
        12853: "بيوت-ومنازل-للبيع",
        12933: "عمارات-للبيع",
        7689: "عقارات-تجارية-للبيع",
        16215: "مكاتب-للبيع",
        16255: "محلات-للبيع",
        16295: "معارض-للبيع",
        16335: "مخازن-للبيع",
        16375: "طابق-كامل-للبيع",
        16415: "مجمعات-للبيع",
        16455: "فلل-تجارية-للبيع",
        16495: "مطاعم-وكافيهات-للبيع",
        16535: "سوبرماركت-للبيع",
        16575: "عيادات-للبيع",
        16615: "مصانع-للبيع",
        16655: "بنوك-للبيع",
        16695: "فنادق-للبيع",
        11337: "عقارات-أجنبية-للبيع",
    }
    
    # S3 Configuration
    S3_BUCKET_REGION = 'us-east-1'
    PROPERTIES_S3_PATH = "opensooq-data/properties"
    INFO_S3_PATH = "opensooq-data/info-json"
    
    # Scraping Configuration
    SCRAPE_CATEGORIES = ['rental', 'sale']  # Which categories to scrape
    SCRAPE_DAYS_BACK = 1  # Only scrape last N days (1 = yesterday only)
    MAX_PAGES_PER_CATEGORY = 100
    
    # Logging
    LOG_LEVEL = 'INFO'


class HelperFunctions:
    """Utility functions for properties module"""
    
    @staticmethod
    def format_s3_key(path_segments: List[str]) -> str:
        """
        Format S3 key from path segments
        
        Args:
            path_segments: List of path components
        
        Returns:
            Formatted S3 key
        """
        return '/'.join(str(seg).strip('/') for seg in path_segments if seg)
    
    @staticmethod
    def get_date_string(date_format: str = '%Y-%m-%d') -> str:
        """Get current date as string"""
        return datetime.now().strftime(date_format)
    
    @staticmethod
    def safe_get(data: dict, key_path: str, default=None):
        """
        Safely get value from nested dictionary using dot notation
        
        Example: safe_get(data, 'rating.average', 0)
        """
        keys = key_path.split('.')
        value = data
        
        for key in keys:
            if isinstance(value, dict):
                value = value.get(key)
            else:
                return default
        
        return value if value is not None else default
    
    @staticmethod
    def normalize_category_name(name: str) -> str:
        """Normalize category name for use in filenames/paths"""
        # Remove special characters, replace spaces with underscores
        normalized = name.replace(' ', '_').replace('/', '_')
        # Keep only alphanumeric, underscores, and hyphens
        normalized = ''.join(c for c in normalized if c.isalnum() or c in '_-')
        return normalized.lower()
    
    @staticmethod
    def truncate_string(s: str, max_length: int = 100) -> str:
        """Truncate string to max length"""
        return s[:max_length] if len(s) > max_length else s


class LoggerSetup:
    """Setup logging for the properties module"""
    
    @staticmethod
    def setup_logger(name: str, log_level: str = 'INFO') -> logging.Logger:
        """
        Setup logger with standard format
        
        Args:
            name: Logger name (usually __name__)
            log_level: Logging level
        
        Returns:
            Configured logger instance
        """
        logger_obj = logging.getLogger(name)
        logger_obj.setLevel(getattr(logging, log_level.upper()))
        
        # Only add handler if not already present
        if not logger_obj.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                datefmt='%Y-%m-%d %H:%M:%S'
            )
            handler.setFormatter(formatter)
            logger_obj.addHandler(handler)
        
        return logger_obj
