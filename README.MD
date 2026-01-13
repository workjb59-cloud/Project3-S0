# OpenSooq Kuwait Scraper

Automated web scraper for opensooq.com (Kuwait) that extracts shop information and their advertisements, saving data to AWS S3 as Excel files.

## 🎯 Features

- ✅ Scrapes all shops from opensooq.com Kuwait متاجر section
- ✅ Filters and extracts **yesterday's ads only**
- ✅ Saves ad data as Excel files to AWS S3
- ✅ Maintains incremental shop info database
- ✅ Runs automatically via GitHub Actions (daily schedule)
- ✅ Uses BeautifulSoup for HTML parsing
- ✅ Respects server rate limits

## 📁 Project Structure

```
Project3-S0/
├── utils.py                    # Shared utilities (HTML parsing, S3, etc.)
├── requirements.txt            # Python dependencies
├── Shops/                      # Shops category scraper
│   ├── __init__.py
│   ├── config.py              # Category-specific configuration
│   ├── scraper.py             # Shops scraping logic
│   └── README.md
├── .github/
│   └── workflows/
│       └── scraper.yml        # Daily automation
└── README.MD
```

## 📁 S3 Data Structure

```
opensooq-data/
├── shops/                          # Shops category data
│   ├── year=2026/
│   │   ├── month=01/
│   │   │   ├── day=13/
│   │   │   │   ├── excel files/
│   │   │   │   │   ├── شركة_دار_الشويخ_العقارية.xlsx
│   │   │   │   │   ├── UNLIMITED_TEC.xlsx
│   │   │   │   │   └── ...
│   │   │   │   └── images/
│   │   │   │       ├── شركة_دار_الشويخ_العقارية/
│   │   │   │       │   ├── ad_275635211_main.jpg
│   │   │   │       │   └── ...
│   │   │   │       └── UNLIMITED_TEC/
│   │   │   │           └── ...
│   │   │   ├── day=14/
│   │   │   │   └── ...
│   │   └── month=02/
│   │       └── ...
├── cars/                           # Future: Cars category
│   └── year=2026/...
├── real-estate/                    # Future: Real estate category
│   └── year=2026/...
└── info/
    └── info.xlsx                   # Incremental shop details (all categories)
```

### Shops Folder (`opensooq-data/shops/`)
- **Format**: `year=YYYY/month=MM/day=DD/{shop_name}.xlsx` (Hive-style partitioning)
- **Content**: Yesterday's ads with basic shop info
- **Benefits**: Easy date-based querying, better organization for analytics
- **Columns**:
  - Shop: `shop_member_id`, `shop_name`
  - Ad: `ad_id`, `title`, `posted_at`, `price_amount`, `city_label`, `nhood_label`, etc.

### Info Folder (`opensooq-data/info/`)
- **File**: `info.xlsx`
- **Content**: Incremental database of all shops
- **Columns**: `member_id`, `shop_name`, `category_name`, `posts_count`, `views_count`, `average_rating`, `followers_count`, etc.
- **Updates**: Each row represents a shop; existing shops are updated with latest data

## 🚀 Setup

### 1. Clone Repository

```bash
git clone <your-repo-url>
cd Project3-S0
```

### 2. Install Dependencies

```bash
pip install -r requirements.txt
```

### 3. Configure AWS Credentials

#### For Local Testing:
Set environment variables:

```bash
# Windows (PowerShell)
$env:AWS_ACCESS_KEY_ID="your-access-key"
$env:AWS_SECRET_ACCESS_KEY="your-secret-key"
$env:AWS_BUCKET_NAME="your-bucket-name"

# Linux/Mac
export AWS_ACCESS_KEY_ID="your-access-key"
export AWS_SECRET_ACCESS_KEY="your-secret-key"
export AWS_BUCKET_NAME="your-bucket-name"
```

#### For GitHub Actions:
Add secrets to your GitHub repository:

1. Go to repository **Settings** → **Secrets and variables** → **Actions**
2. Click **New repository secret**
3. Add the following secrets:
   - `AWS_ACCESS_KEY_ID`
   - `AWS_SECRET_ACCESS_KEY`
   - `AWS_BUCKET_NAME`

### 4. Run Scraper

```bash
# Run Shops category scraper
python Shops/scraper.py

# Or as a module
python -m Shops.scraper
```

## ⚙️ GitHub Actions Workflow

The scraper runs automatically every day at 2:00 AM UTC.

**Workflow file**: [`.github/workflows/scraper.yml`](.github/workflows/scraper.yml)

### Schedule
```yaml
schedule:
  - cron: '0 2 * * *'  # Daily at 2:00 AM UTC
```

### Manual Trigger
You can also trigger the workflow manually from the **Actions** tab in GitHub.

## 📊 Data Fields

### Ad Data (shops/*.xlsx)

| Field | Description |
|-------|-------------|
| `shop_member_id` | Shop's unique member ID |
| `shop_name` | Name of the shop |
| `ad_id` | Advertisement ID |
| `title` | Ad title |
| `posted_at` | When ad was posted (Arabic format) |
| `expired_at` | Ad expiration date |
| `price_amount` | Price in KWD |
| `city_label` | City name (Arabic) |
| `nhood_label` | Neighborhood name (Arabic) |
| `cat1_label` | Main category |
| `cat2_label` | Sub-category |
| `highlights` | Key features |
| `masked_description` | Ad description |
| `post_url` | URL to ad detail page |
| `verification_level` | Shop verification level |
| `scraped_at` | Timestamp when scraped |

### Shop Info (info/info.xlsx)

| Field | Description |
|-------|-------------|
| `member_id` | Shop's unique member ID |
| `shop_name` | Name of the shop |
| `category_name` | Shop category |
| `posts_count` | Total number of posts |
| `views_count` | Total views |
| `response_time` | Average response time |
| `member_since` | Registration date |
| `followers_count` | Number of followers |
| `average_rating` | Average rating (out of 5) |
| `number_of_rating` | Total ratings |
| `city_name` | Shop location |
| `latitude` / `longitude` | GPS coordinates |
| `verification_level` | Verification level (0-2) |
| `scraped_at` | Last update timestamp |

## 🔍 How It Works

1. **Fetch Shops List**: Scrapes all pages of the shops listing
2. **Parse HTML**: Uses BeautifulSoup to extract JSON data from `__NEXT_DATA__` script tag
3. **Filter Yesterday's Ads**: Checks `posted_at` field for "أمس", "قبل يوم", or hours/minutes
4. **Download Images**: Downloads ad images from opensooq CDN
5. **Save to S3**:
   - Ad data → `opensooq-data/shops/year=YYYY/month=MM/day=DD/excel files/{shop_name}.xlsx`
   - Ad images → `opensooq-data/shops/year=YYYY/month=MM/day=DD/images/{shop_name}/ad_{id}_main.jpg`
   - Shop info → `opensooq-data/info/info.xlsx` (incremental)
6. **Rate Limiting**: 2-3 second delays between requests

## 🛠️ Key Functions

### `utils.py` (Shared utilities)

- `extract_json_from_html()` - Extract JSON from Next.js HTML
- `is_yesterday_ad()` - Check if ad was posted yesterday
- `filter_yesterday_ads()` - Filter ads list
- `get_partitioned_s3_path()` - Generate Hive-style partitioned S3 paths
- `download_image()` - Download image from URL
- `upload_image_to_s3()` - Upload image bytes to S3
- `save_ad_images_to_s3()` - Download and save all ad images
- `upload_to_s3()` - Upload DataFrame to S3 as Excel
- `download_from_s3()` - Download Excel from S3
- `update_incremental_info()` - Update shop info incrementally

### `Shops/scraper.py` (Category-specific)

- `get_shops_list()` - Fetch shops from listing page
- `get_shop_details_and_ads()` - Fetch individual shop data
- `process_shop()` - Process shop and save to S3
- `main()` - Orchestrate entire scraping process

### `Shops/config.py` (Category configuration)

- Category URLs and names
- S3 paths
- Scraping delays and settings
- Field definition
- `get_shops_list()` - Fetch shops from listing page
- `get_shop_details_and_ads()` - Fetch individual shop data
- `process_shop()` - Process shop and save to S3
- `main()` - Orchestrate entire scraping process

## 📝 Example Output

```
============================================================
OpenSooq Scraper - Starting
Date: 2026-01-13 14:30:00
============================================================
Fetching shops list...
============================================================

Fetching shops page 1...
Found 30 shops on page 1
Progress: Page 1 of 3

Fetching shops page 2...
Found 30 shops on page 2
Progress: Page 2 of 3

Fetching shops page 3...
Found 8 shops on page 3
Progress: Page 3 of 3

Reached last page. Total shops: 68

Total shops to process: 68

============================================================
Processing shops and their ads...
============================================================

[1/68] Processing shop: شركة دار الشويخ العقارية (ID: 75063309)
URL: شركة-دار-الشويخ-العقارية-75063309
Total ads: 25, Yesterday's ads: 3
Successfully uploaded to s3://your-bucket/opensooq-data/shops/year=2026/month=01/day=13/شركة_دار_الشويخ_العقارية.xlsx
✓ Successfully processed shop: شركة دار الشويخ العقارية

...

============================================================
Scraping Complete!
============================================================
Total shops: 68
Successfully processed: 65
Errors: 3
Completion time: 2026-01-13 14:45:30
============================================================
```

## 🔒 Security Notes

- Never commit AWS credentials to the repository
- Use GitHub Secrets for sensitive data
- E🔄 Adding New Categories

The project is structured to easily support multiple categories:

1. **Create category folder** (e.g., `Cars/`, `RealEstate/`)
2. **Copy structure from `Shops/`**:
   ```
   Cars/
   ├── __init__.py
   ├── config.py        # Update URLs, category name, S3 path
   ├── scraper.py       # Customize if needed (or reuse)
   └── README.md
   ```
3. **Update `config.py`** with category-specific settings
4. **Add to GitHub Actions** workflow
5. **Shared utilities** in root `utils.py` work for all categories

### Example: Adding Cars Category

```python
# Cars/config.py
CATEGORY = "cars"
CATEGORY_NAME_AR = "سيارات"
CATEGORY_URL = "https://kw.opensooq.com/ar/cars"
S3_CATEGORY_PATH = "cars"
```

Then update workflow:
```yaml
- name: Run Cars scraper
  run: python Cars/scraper.py
```

## nsure S3 bucket has proper access policies
- Consider using IAM roles instead of access keys for production

## 📄 License

This project is for educational purposes. Please respect opensooq.com's terms of service and robots.txt.

## 🤝 Contributing

Feel free to open issues or submit pull requests for improvements.

---

**Last Updated**: January 13, 2026

