#!/usr/bin/env python3
"""
OpenSooq Properties Scraper - System Architecture Overview

ASCII Diagrams and system flow documentation
"""

# ============================================================================
# SYSTEM ARCHITECTURE DIAGRAM
# ============================================================================

SYSTEM_ARCHITECTURE = """
┌─────────────────────────────────────────────────────────────────────────┐
│                    OpenSooq Properties Scraper                          │
│                        System Architecture                              │
└─────────────────────────────────────────────────────────────────────────┘

┌──────────────────────────────────┐
│      GitHub Actions              │
│  (Daily at 2:00 AM UTC)         │
│  or Manual Trigger              │
└────────────┬─────────────────────┘
             │
             ▼
┌──────────────────────────────────┐
│   Setup Python Environment       │
│   (Python 3.11)                 │
│   Install Dependencies          │
└────────────┬─────────────────────┘
             │
             ▼
┌──────────────────────────────────────────────────────────────────────────┐
│                         __main__.py                                      │
│                 PropertiesScraperWorkflow                               │
│                    (Orchestrator)                                       │
└────────────┬──────────────────────────────────────────┬─────────────────┘
             │                                          │
             ▼                                          ▼
    ┌─────────────────┐                    ┌──────────────────────┐
    │   scraper.py    │                    │   processor.py       │
    │ PropertiesScraper│                    │ PropertiesProcessor │
    │                 │                    │ DataValidator       │
    │  - fetch_pages  │                    │ - validate data     │
    │  - date_filter  │                    │ - group by cat      │
    │  - fetch_member │                    │ - organize JSON     │
    │                 │                    │ - merge members     │
    └────────┬────────┘                    └──────────┬──────────┘
             │                                       │
             ▼                                       ▼
    ┌──────────────────────────────────────────────────┐
    │         Local Temporary Files                    │
    │  - properties_YYYYMMDD_HHMMSS.json              │
    │  - members_info_YYYYMMDD_HHMMSS.json            │
    └────────────────┬─────────────────────────────────┘
                     │
                     ▼
    ┌──────────────────────────────────┐
    │       s3_uploader.py             │
    │         S3Uploader               │
    │   - upload_properties()          │
    │   - upload_members()             │
    │   - merge_incremental()          │
    └────────────────┬─────────────────┘
                     │
                     ▼
    ┌──────────────────────────────────────────────────┐
    │           AWS S3 Bucket                          │
    │  opensooq-data/                                 │
    │  ├── properties/                                │
    │  │   ├── rental/2026-01-15/                    │
    │  │   │   ├── شقق-للايجار.json                │
    │  │   │   ├── فلل-وقصور-للايجار.json          │
    │  │   │   └── ...22 total categories           │
    │  │   └── sale/2026-01-15/                      │
    │  │       ├── شقق-للبيع.json                  │
    │  │       ├── فلل-وقصور-للبيع.json            │
    │  │       └── ...20 total categories           │
    │  └── info-json/                                │
    │      └── info.json (incremental)               │
    └──────────────────────────────────────────────────┘
"""

# ============================================================================
# DATA FLOW DIAGRAM
# ============================================================================

DATA_FLOW = """
┌─────────────────────────────────────────────────────────────────────────┐
│                           Data Flow                                     │
└─────────────────────────────────────────────────────────────────────────┘

1. SCRAPING PHASE
   ┌────────────┐
   │ OpenSooq   │
   │ Website    │
   └─────┬──────┘
         │ BeautifulSoup
         │ (HTML Parsing)
         ▼
   ┌──────────────────────────────┐
   │ Extract from __NEXT_DATA__   │
   │ JSON embedded in HTML        │
   └─────┬────────────────────────┘
         │
         ▼
   ┌──────────────────────────────┐
   │ Category Pages               │
   │ (Rental & Sale)             │
   │ Pagination handling         │
   └─────┬────────────────────────┘
         │
         ▼
   ┌──────────────────────────────┐
   │ Filter Yesterday's Posts     │
   │ (by inserted_date)          │
   └─────┬────────────────────────┘
         │
         ▼
   ┌──────────────────────────────────┐
   │ Listings Collection              │
   │ - 200-500+ properties per day    │
   │ - Basic seller info included    │
   └─────┬──────────────────────────┘
         │
         ▼
   ┌──────────────────────────────────────┐
   │ Fetch Member Profiles                │
   │ - Full ratings & statistics         │
   │ - Rating tags (politeness, pro, etc) │
   │ - Followers & following             │
   └─────┬────────────────────────────────┘
         │
         ▼
   ┌──────────────────────────────┐
   │ Complete Listing Data        │
   │ + Full Member Info          │
   └─────┬────────────────────────┘

2. PROCESSING PHASE
         │
         ▼
   ┌──────────────────────────────┐
   │ Data Validation              │
   │ - Check required fields     │
   │ - Verify structure          │
   │ - Invalid: Log & continue   │
   └─────┬────────────────────────┘
         │
         ▼
   ┌──────────────────────────────┐
   │ Group by Subcategory        │
   │ (22 rental + 20 sale)       │
   └─────┬────────────────────────┘
         │
         ▼
   ┌──────────────────────────────┐
   │ Create JSON Structures       │
   │ - Properties file           │
   │ - Members file              │
   └─────┬────────────────────────┘
         │
         ▼
   ┌──────────────────────────────┐
   │ Incremental Member Merge    │
   │ (Update existing, add new)  │
   └─────┬────────────────────────┘

3. UPLOAD PHASE
         │
         ▼
   ┌──────────────────────────────────────┐
   │ Save to Local Temp Files             │
   │ - properties_YYYYMMDD_HHMMSS.json   │
   │ - members_info_YYYYMMDD_HHMMSS.json │
   └─────┬────────────────────────────────┘
         │
         ▼
   ┌──────────────────────────────────┐
   │ Upload to S3                      │
   │ - Add encryption (AES256)        │
   │ - Create folder structure        │
   │ - Organize by date/category      │
   └─────┬──────────────────────────────┘
         │
         ▼
   ┌──────────────────────────────────┐
   │ Merge Incremental Data           │
   │ (members only - properties new) │
   └─────┬──────────────────────────────┘
         │
         ▼
   ┌──────────────────────────────────┐
   │ S3 Bucket Storage                │
   │ ✓ Ready for Analysis            │
   │ ✓ Ready for Integration         │
   └──────────────────────────────────┘
"""

# ============================================================================
# MODULE DEPENDENCIES
# ============================================================================

DEPENDENCIES = """
┌─────────────────────────────────────────────────────────────────────────┐
│                      Module Dependencies                                │
└─────────────────────────────────────────────────────────────────────────┘

__main__.py
├── scraper.py
│   ├── requests (HTTP)
│   ├── BeautifulSoup (HTML parsing)
│   └── datetime (date operations)
│
├── processor.py
│   ├── json (JSON operations)
│   ├── logging (logging)
│   └── datetime (timestamps)
│
├── s3_uploader.py
│   ├── boto3 (AWS S3)
│   ├── json (JSON operations)
│   └── logging (logging)
│
└── config.py
    ├── logging (setup)
    └── datetime (utilities)

External Dependencies:
├── requests              (HTTP client)
├── beautifulsoup4        (HTML parser)
├── boto3                 (AWS SDK)
└── python-dateutil       (Date utilities)
"""

# ============================================================================
# FILE ORGANIZATION
# ============================================================================

FILE_ORGANIZATION = """
┌─────────────────────────────────────────────────────────────────────────┐
│                     File Organization                                   │
└─────────────────────────────────────────────────────────────────────────┘

Properties/                        [Directory]
│
├── CORE MODULES                   [Execution]
│   ├── __init__.py               - Package initialization
│   ├── __main__.py               - Workflow orchestrator
│   ├── scraper.py                - Web scraper
│   ├── processor.py              - Data processor
│   ├── s3_uploader.py            - S3 handler
│   └── config.py                 - Configuration
│
├── CONFIGURATION & TESTING        [Setup]
│   ├── requirements.txt           - Python packages
│   └── test_extraction.py         - Test suite
│
└── DOCUMENTATION                  [Reference]
    ├── README.md                  - Main documentation
    ├── SETUP.md                   - Setup guide
    ├── QUICK_REFERENCE.md         - Quick reference
    └── _ARCHIVE_/
        └── (documentation backups)

.github/workflows/                [CI/CD]
└── opensooq-properties-scraper.yml - GitHub Actions

Root/
├── PROPERTIES_IMPLEMENTATION_SUMMARY.md  - Implementation summary
├── COMPLETE_FILE_LISTING.md             - File listing
└── ARCHITECTURE.md                      - This file
"""

# ============================================================================
# EXECUTION FLOW
# ============================================================================

EXECUTION_FLOW = """
┌─────────────────────────────────────────────────────────────────────────┐
│                       Execution Flow                                    │
└─────────────────────────────────────────────────────────────────────────┘

START
 │
 ▼
┌─────────────────────────────────┐
│ Initialize PropertiesScraper    │
│ - Setup session                 │
│ - Calculate yesterday           │
│ - Load config                   │
└────────┬────────────────────────┘
         │
         ▼
┌──────────────────────────────────────┐
│ Scrape Rental Properties             │
│ - Fetch pages (pagination)           │
│ - Filter yesterday's posts           │
│ - Extract basic info                 │
└────────┬─────────────────────────────┘
         │
         ▼
┌──────────────────────────────────────┐
│ Scrape Sale Properties               │
│ - Fetch pages (pagination)           │
│ - Filter yesterday's posts           │
│ - Extract basic info                 │
└────────┬─────────────────────────────┘
         │
         ▼
┌──────────────────────────────────────┐
│ Combine All Listings                 │
│ Total: 200-500+ properties           │
└────────┬─────────────────────────────┘
         │
         ▼
┌──────────────────────────────────────────┐
│ Fetch Member Details (for each unique)   │
│ - Full ratings                           │
│ - Rating tags                            │
│ - Followers                              │
│ Total: 50-200+ members                   │
└────────┬─────────────────────────────────┘
         │
         ▼
┌──────────────────────────────────────┐
│ Validate All Data                    │
│ - Check required fields              │
│ - Count valid/invalid                │
│ - Continue with valid data           │
└────────┬─────────────────────────────┘
         │
         ▼
┌──────────────────────────────────────┐
│ Process Properties                   │
│ - Group by subcategory               │
│ - Add timestamps                     │
│ - Create JSON structure              │
└────────┬─────────────────────────────┘
         │
         ▼
┌──────────────────────────────────────┐
│ Process Members                      │
│ - Prepare incremental data           │
│ - Remove duplicates                  │
│ - Add timestamps                     │
└────────┬─────────────────────────────┘
         │
         ▼
┌──────────────────────────────────────┐
│ Save to Local Files                  │
│ - properties_YYYYMMDD.json           │
│ - members_info_YYYYMMDD.json         │
└────────┬─────────────────────────────┘
         │
         ▼
┌──────────────────────────────────────┐
│ Upload to S3                         │
│ - Properties by category/date        │
│ - Members incremental                │
│ - Test connection first              │
│ - Handle encryption                  │
└────────┬─────────────────────────────┘
         │
         ▼
┌──────────────────────────────────────┐
│ Log Summary                          │
│ - Files uploaded                     │
│ - S3 locations                       │
│ - Data counts                        │
│ - Execution time                     │
└────────┬─────────────────────────────┘
         │
         ▼
COMPLETE
"""

# ============================================================================
# MAIN EXECUTION
# ============================================================================

if __name__ == '__main__':
    print(SYSTEM_ARCHITECTURE)
    print("\n")
    print(DATA_FLOW)
    print("\n")
    print(DEPENDENCIES)
    print("\n")
    print(FILE_ORGANIZATION)
    print("\n")
    print(EXECUTION_FLOW)
    
    print("\n" + "="*75)
    print("OpenSooq Properties Scraper - Architecture Documentation")
    print("="*75)
    print("""
For detailed information:
- Setup Guide: SETUP.md
- Quick Reference: QUICK_REFERENCE.md
- Module Documentation: README.md
- Implementation Summary: PROPERTIES_IMPLEMENTATION_SUMMARY.md
- Complete Files: COMPLETE_FILE_LISTING.md

Status: ✅ Production Ready
    """)
