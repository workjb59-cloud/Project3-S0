"""
Main entry point for Businesses & Industrial scraper
Run with: python -m Businesses_Industrial
"""

import sys
import os
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from Businesses_Industrial.scraper import main

if __name__ == "__main__":
    main()
