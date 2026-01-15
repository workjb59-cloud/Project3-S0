"""
OpenSooq Properties Scraper Package

A comprehensive solution for scraping property listings from OpenSooq Kuwait,
organized by subcategory, with incremental member information storage.

Features:
  - Scrapes yesterday's listings only
  - 42+ property subcategories (rental + sale)
  - Full member ratings and statistics
  - Automated daily execution via GitHub Actions
  - Organized S3 storage structure
  - Incremental member data (no duplicates)
  - BeautifulSoup-based HTML parsing
  - Complete error handling and logging

Usage:
  python -m Properties --categories rental sale
  python -m Properties --categories rental  # rental only
  python -m Properties --categories sale    # sale only

Environment Variables:
  AWS_S3_BUCKET      - S3 bucket name
  AWS_ACCESS_KEY     - AWS access key ID
  AWS_SECRET_KEY     - AWS secret access key

Author: OpenSooq Data Project
License: Proprietary
"""

__version__ = '1.0.0'
__author__ = 'OpenSooq Data Team'
__all__ = [
    'PropertiesScraper',
    'PropertiesProcessor',
    'DataValidator',
    'S3Uploader',
    'PropertyConfig',
    'PropertiesScraperWorkflow',
]

# Import main classes for easy access
try:
    from .scraper import PropertiesScraper
    from .processor import PropertiesProcessor, DataValidator
    from .s3_uploader import S3Uploader
    from .config import PropertyConfig, HelperFunctions, LoggerSetup
    from .__main__ import PropertiesScraperWorkflow
except ImportError:
    # Allow package to load even if imports fail
    pass
