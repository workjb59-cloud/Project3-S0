# Quick Reference - Home and Garden Scraper

## File Structure
```
Home and Garden/
├── scraper.py           # Main scraper class
├── s3_uploader.py       # S3 upload operations
├── processor.py         # Data processing
├── config.py            # Configuration & URLs
├── __init__.py          # Package initialization
├── __main__.py          # Entry point
├── README.md            # Full documentation
├── SETUP.md             # Setup instructions
└── QUICK_REFERENCE.md   # This file
```

## Running the Scraper

### Local Execution
```bash
# Set environment variables first
$env:AWS_S3_BUCKET_NAME = "your-bucket"
$env:AWS_ACCESS_KEY_ID = "your-key"
$env:AWS_SECRET_ACCESS_KEY = "your-secret"
$env:AWS_REGION = "us-east-1"

# Run scraper
python -m "Home and Garden"
```

### GitHub Actions
- Runs automatically daily at **21:00 UTC** (12:00 AM Kuwait time)
- Workflow: `.github/workflows/home-garden-scraper.yml`
- Manual trigger: GitHub Actions → Run workflow

## Output Structure

### S3 Locations

**Listings Data** (includes all details):
```
s3://bucket/opensooq-data/home-garden/year=2026/month=01/day=25/{category}/{subcategory}/{id}.json
```

**Property Data** (listing without seller info):
```
s3://bucket/opensooq-data/properties/year=2026/month=01/day=25/{category}/{subcategory}/{id}.json
```

**Images**:
```
s3://bucket/opensooq-data/home-garden/year=2026/month=01/day=25/{category}/{subcategory}/images/{id}_{image_id}.jpg
```

**Member Info** (incremental):
```
s3://bucket/opensooq-data/properties/info-json/members-info.json
```

## Key Classes

### HomeGardenScraper
Main scraper class
```python
scraper = HomeGardenScraper(s3_uploader)
result = scraper.run()  # Returns: {'status': 'success', 'total_listings_processed': N, ...}
```

### HomeGardenS3Uploader
S3 operations
```python
uploader = HomeGardenS3Uploader(bucket_name, access_key, secret_key)
uploader.upload_listing_json(data, category, subcategory, date, listing_id)
uploader.upload_image(image_url, category, subcategory, date, listing_id, image_id)
uploader.upload_member_info_batch([member_data])
```

### ListingProcessor
Data extraction
```python
processor.is_yesterday_ad(posted_at)  # True if ad posted in last 24hrs
processor.extract_listing_details(api_response)
processor.extract_member_info(api_response)
processor.extract_property_info(api_response)
```

## Configuration (config.py)

### Main Categories (auto-scraped)
1. الأثاث (Furniture)
2. ديكور المنزل وإكسسواراته (Home Decor)
3. المنزل والحديقة أخرى (Other)
4. أواني وأطباق المطبخ (Kitchen)
5. أثاث الحدائق والخارج (Outdoor)
6. أبواب ونوافذ وبوابات (Doors/Windows)
7. نباتات (Plants)
8. إضاءة (Lighting)
9. الحمامات وإكسسواراتها (Bathrooms)
10. بلاط وأرضيات (Tiles)
11. مسابح وساونا (Pools)

### URLs
```python
BASE_URL = "https://kw.opensooq.com"
MAIN_CATEGORY_URL = f"{BASE_URL}/ar/المنزل-والحديقة"
```

## Environment Variables

Required:
- `AWS_S3_BUCKET_NAME` - S3 bucket name
- `AWS_ACCESS_KEY_ID` - AWS access key
- `AWS_SECRET_ACCESS_KEY` - AWS secret key
- `AWS_REGION` - AWS region (default: us-east-1)

## Logging

All logs go to console with timestamps:
```
2026-01-25 12:00:00 - Home and Garden.scraper - INFO - Starting OpenSooq Home and Garden scraper
```

Log levels:
- INFO: Normal operations
- WARNING: Non-critical issues
- ERROR: Failures that don't stop execution
- DEBUG: (can be enabled with logging.DEBUG)

## Data Retention

No automatic cleanup. To delete old data:

```bash
# Delete listings older than 30 days
aws s3 rm s3://bucket/opensooq-data/home-garden/year=2025/ --recursive

# Delete properties older than 60 days
aws s3 rm s3://bucket/opensooq-data/properties/year=2025/ --recursive
```

Or set up S3 Lifecycle rule for automatic deletion.

## Common Commands

### List All Data from Latest Day
```bash
# Get latest date folder
aws s3 ls s3://bucket/opensooq-data/home-garden/ --recursive | tail -20

# List a specific day
aws s3 ls s3://bucket/opensooq-data/home-garden/year=2026/month=01/day=25/ --recursive
```

### Count Listings
```bash
# Count JSON files for a day
aws s3 ls s3://bucket/opensooq-data/home-garden/year=2026/month=01/day=25/ --recursive | grep ".json$" | wc -l
```

### Download All Data for a Day
```bash
aws s3 sync s3://bucket/opensooq-data/home-garden/year=2026/month=01/day=25/ ./local-backup/
```

### View a Listing
```bash
aws s3 cp s3://bucket/opensooq-data/home-garden/year=2026/month=01/day=25/الأثاث/أثاث-غرف-جلوس/276167705.json - | jq '.'
```

### Get Listing Count by Category
```bash
# Using AWS CLI and Python
aws s3 ls s3://bucket/opensooq-data/home-garden/year=2026/month=01/day=25/ --recursive | \
  awk -F/ '{print $(NF-1)}' | sort | uniq -c
```

## Troubleshooting

| Error | Cause | Fix |
|-------|-------|-----|
| `ModuleNotFoundError` | Python path issue | Run from project root with `python -m` |
| `Missing AWS credentials` | Env vars not set | Check GitHub Secrets or local env vars |
| `ClientError 403` | Permissions issue | Update IAM policy |
| `No listings found` | No data available | Normal - try next day |
| `TimeoutError` | Network slow | Check internet, increase timeout |

## Performance

- **Listings per day**: 1,000-3,000
- **Images per listing**: 2-4
- **Total runtime**: 20-60 minutes
- **S3 API calls**: ~10,000-30,000
- **Data size**: 50-200 MB

## First Run Checklist

- [ ] Dependencies installed
- [ ] AWS credentials configured
- [ ] S3 bucket created
- [ ] GitHub secrets added
- [ ] Test locally successful
- [ ] Workflow triggered successfully
- [ ] Data visible in S3
- [ ] Member info JSON created

## Next Steps

1. **Monitor first run** - Check GitHub Actions logs
2. **Verify S3 data** - Browse bucket structure
3. **Check member info** - View members-info.json
4. **Analyze listings** - Query JSON files
5. **Set up backup** - Download to local storage
6. **Configure cleanup** - Set S3 lifecycle policy

## Support Resources

- GitHub Issues - Report bugs
- README.md - Full documentation
- SETUP.md - Detailed setup guide
- config.py - Configuration options
- scraper.py - Main logic and comments

---

**Last Updated**: January 25, 2026
**Version**: 1.0.0
