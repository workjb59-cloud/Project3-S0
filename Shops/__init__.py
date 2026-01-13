"""
Shops category scraper module
"""
from .scraper import main as run_scraper
from .config import CATEGORY_NAME_AR, S3_CATEGORY_PATH

__all__ = ['run_scraper', 'CATEGORY_NAME_AR', 'S3_CATEGORY_PATH']
