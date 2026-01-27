"""
Properties Package
OpenSooq Properties Scraper
"""

__version__ = '1.0.0'
__author__ = 'OpenSooq Scraper Team'

from .scraper import PropertiesScraper
from .processor import PropertiesProcessor, PropertiesDataManager
from .s3_uploader import PropertiesS3Uploader

__all__ = [
    'PropertiesScraper',
    'PropertiesProcessor',
    'PropertiesDataManager',
    'PropertiesS3Uploader'
]
