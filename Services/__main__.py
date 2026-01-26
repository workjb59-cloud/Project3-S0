"""
Main entry point for Services scraper
Run with: python -m Services
"""

import sys
import os
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from Services.scraper import main

if __name__ == "__main__":
    main()
