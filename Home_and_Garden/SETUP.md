# Setup Guide - Home and Garden Scraper

## Quick Start

### 1. Prerequisites
- Python 3.11+
- AWS Account with S3 bucket
- GitHub Account with repository access
- Git installed locally

### 2. Local Setup

#### Step 1: Clone Repository
```bash
cd c:\Users\KimoStore\Desktop\Project3-S0
```

#### Step 2: Install Dependencies
```bash
pip install -r requirements.txt
```

#### Step 3: Create AWS Credentials
1. Go to AWS IAM Console
2. Create an IAM user with S3 access
3. Generate Access Key and Secret Key
4. Note down:
   - Access Key ID
   - Secret Access Key
   - S3 Bucket Name
   - AWS Region (e.g., us-east-1)

#### Step 4: Set Environment Variables (Local Testing)
Create a `.env` file in project root:
```bash
AWS_S3_BUCKET_NAME=your-bucket-name
AWS_ACCESS_KEY_ID=your-access-key
AWS_SECRET_ACCESS_KEY=your-secret-key
AWS_REGION=us-east-1
```

Then load it:
```bash
# Windows PowerShell
$env:AWS_S3_BUCKET_NAME = "your-bucket-name"
$env:AWS_ACCESS_KEY_ID = "your-access-key"
$env:AWS_SECRET_ACCESS_KEY = "your-secret-key"
$env:AWS_REGION = "us-east-1"

# Or use python-dotenv
python -m dotenv run python -m "Home and Garden"
```

#### Step 5: Test Locally
```bash
python -m "Home and Garden"
```

Check console output for:
```
Starting OpenSooq Home and Garden scraper
Successfully connected to S3 bucket: your-bucket-name
Starting scrape for: الأثاث
...
Scraping completed!
Total listings processed: XX
```

---

### 3. GitHub Actions Setup

#### Step 1: Add GitHub Secrets
1. Go to your GitHub repository
2. Settings → Secrets and variables → Actions
3. Click "New repository secret"
4. Add these secrets:

| Secret Name | Value |
|------------|-------|
| `AWS_S3_BUCKET_NAME` | your-bucket-name |
| `AWS_ACCESS_KEY_ID` | your-access-key-id |
| `AWS_SECRET_ACCESS_KEY` | your-secret-access-key |
| `AWS_REGION` | us-east-1 |

#### Step 2: Verify Workflow File
The workflow is located at: `.github/workflows/home-garden-scraper.yml`

It will:
- ✅ Run automatically every day at 21:00 UTC (12:00 AM Kuwait time)
- ✅ Allow manual trigger from GitHub Actions
- ✅ Use Python 3.11
- ✅ Cache pip dependencies
- ✅ Upload logs on failure
- ✅ Timeout after 2 hours

#### Step 3: Test Workflow
1. Push changes to GitHub
2. Go to repository → Actions
3. Click "OpenSooq Home and Garden Daily Scraper"
4. Click "Run workflow" → "Run workflow" button
5. Wait for execution
6. Check logs for success/failure

---

### 4. AWS S3 Configuration

#### Create S3 Bucket Structure
The scraper automatically creates:
```
s3://your-bucket/
├── opensooq-data/
│   ├── home-garden/              # Daily listings
│   │   ├── year=2026/month=01/day=25/
│   │   ├── year=2026/month=01/day=26/
│   │   └── ...
│   └── properties/               # Property data (without seller)
│       ├── year=2026/month=01/day=25/
│       ├── info-json/
│       │   └── members-info.json # Incremental member data
│       └── ...
```

#### Set Bucket Lifecycle Policy (Optional)
To automatically delete old data after 90 days:

1. AWS S3 Console → Your Bucket → Lifecycle rules
2. Create rule with:
   - Prefix: `opensooq-data/`
   - Days: 90
   - Action: Delete versions

#### Enable Versioning (Recommended)
1. AWS S3 Console → Your Bucket → Properties
2. Enable Versioning
3. This protects against accidental overwrites

#### Set Public Access Block
Keep all public access blocked:
1. AWS S3 Console → Your Bucket → Permissions
2. Ensure all "Block public access" are enabled ✓

---

### 5. IAM Permissions Setup

#### Minimum Required Permissions
Create an IAM policy with:
```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "s3:GetObject",
        "s3:PutObject",
        "s3:ListBucket",
        "s3:GetObjectVersion"
      ],
      "Resource": [
        "arn:aws:s3:::your-bucket-name",
        "arn:aws:s3:::your-bucket-name/*"
      ]
    }
  ]
}
```

#### Attach to User
1. AWS IAM Console → Users
2. Select the user
3. Attach the policy above
4. Generate Access Keys
5. Add to GitHub Secrets

---

### 6. Monitoring & Troubleshooting

#### Check Workflow Status
GitHub Actions → OpenSooq Home and Garden Daily Scraper

#### View Logs
1. Click the latest workflow run
2. Click "Scrape" job
3. Expand "Run Home and Garden Scraper" to see logs

#### Common Issues & Fixes

**Issue**: `ModuleNotFoundError: No module named 'Home and Garden'`
**Solution**: 
```bash
# Reinstall with quotes
pip install -r requirements.txt
# Use correct import
python -m "Home and Garden"
```

**Issue**: `Missing AWS credentials`
**Solution**: 
1. Verify secrets in GitHub Settings
2. Check secret names match exactly
3. Regenerate access keys in AWS IAM

**Issue**: `ClientError: 403 Forbidden`
**Solution**:
1. Check IAM permissions
2. Verify bucket exists
3. Test credentials locally first

**Issue**: Script runs but uploads nothing
**Solution**: 
1. Check if website returned 0 listings
2. Verify filter: only yesterday's ads
3. Check time - scraper may run when no recent listings exist

#### Helpful Commands

```bash
# Test S3 connection
python -c "import boto3; boto3.client('s3', aws_access_key_id='XXX', aws_secret_access_key='XXX').head_bucket(Bucket='your-bucket')"

# List S3 contents
aws s3 ls s3://your-bucket/opensooq-data/home-garden/

# Download a file
aws s3 cp s3://your-bucket/opensooq-data/home-garden/year=2026/month=01/day=25/الأثاث/أثاث-غرف-جلوس/276167705.json .

# Check member data
aws s3 cp s3://your-bucket/opensooq-data/properties/info-json/members-info.json .
cat members-info.json | jq '.' | head -50
```

---

### 7. Workflow Schedule

The scraper runs at **21:00 UTC** (12:00 AM Kuwait Time).

To change the schedule, edit `.github/workflows/home-garden-scraper.yml`:

```yaml
on:
  schedule:
    - cron: '0 21 * * *'  # Change the first two numbers (hour minute)
```

Cron format: `minute hour day month weekday`

Examples:
- `0 12 * * *` → Every day at 12:00 PM UTC
- `0 0 * * 1` → Every Monday at 12:00 AM UTC
- `30 15 * * *` → Every day at 3:30 PM UTC

---

### 8. Data Access

#### View Listings (Home and Garden)
```bash
# List all categories
aws s3 ls s3://your-bucket/opensooq-data/home-garden/year=2026/month=01/day=25/

# List subcategories
aws s3 ls s3://your-bucket/opensooq-data/home-garden/year=2026/month=01/day=25/الأثاث/

# List listings
aws s3 ls s3://your-bucket/opensooq-data/home-garden/year=2026/month=01/day=25/الأثاث/أثاث-غرف-جلوس/

# View a specific listing
aws s3 cp s3://your-bucket/opensooq-data/home-garden/year=2026/month=01/day=25/الأثاث/أثاث-غرف-جلوس/276167705.json -
```

#### View Property Data
```bash
aws s3 cp s3://your-bucket/opensooq-data/properties/year=2026/month=01/day=25/الأثاث/أثاث-غرف-جلوس/276167705.json -
```

#### View Member Info
```bash
aws s3 cp s3://your-bucket/opensooq-data/properties/info-json/members-info.json - | jq '.' | head -100
```

#### Query with Python
```python
import boto3
import json

s3 = boto3.client('s3')

# List objects
response = s3.list_objects_v2(
    Bucket='your-bucket',
    Prefix='opensooq-data/home-garden/year=2026/month=01/day=25/'
)

# Download file
response = s3.get_object(
    Bucket='your-bucket',
    Key='opensooq-data/home-garden/year=2026/month=01/day=25/الأثاث/أثاث-غرف-جلوس/276167705.json'
)
data = json.loads(response['Body'].read())
print(data)
```

---

### 9. Performance Notes

- **First run**: 30-60 minutes (initial index creation)
- **Subsequent runs**: 15-30 minutes (depends on daily posting)
- **S3 costs**: ~$0.10-1.00 per day (depends on file size and API calls)
- **Network**: ~50-200 MB per day

---

### 10. Support

For issues:
1. Check logs in `.github/workflows/` runs
2. Test locally first
3. Verify AWS credentials
4. Check OpenSooq website availability
5. Review error messages in workflow output

---

## Summary Checklist

- [ ] Python 3.11+ installed
- [ ] `requirements.txt` dependencies installed
- [ ] AWS S3 bucket created
- [ ] IAM user with S3 permissions created
- [ ] Access keys generated
- [ ] GitHub secrets configured (4 secrets)
- [ ] Workflow file present at `.github/workflows/home-garden-scraper.yml`
- [ ] Local test successful
- [ ] GitHub workflow test successful
- [ ] S3 data visible in bucket
- [ ] Schedule verified (21:00 UTC daily)

✅ You're ready to go!
