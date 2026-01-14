# Commercial Offers Scraper - Quick Setup Guide

## Prerequisites

- Python 3.11+
- AWS S3 bucket
- AWS credentials (Access Key ID and Secret Access Key)

## Step 1: Install Dependencies

```bash
pip install -r requirements.txt
```

## Step 2: Set Environment Variables

### Windows (PowerShell)
```powershell
$env:S3_BUCKET_NAME="your-bucket-name"
$env:AWS_ACCESS_KEY_ID="your-access-key"
$env:AWS_SECRET_ACCESS_KEY="your-secret-key"
```

### Linux/Mac
```bash
export S3_BUCKET_NAME="your-bucket-name"
export AWS_ACCESS_KEY_ID="your-access-key"
export AWS_SECRET_ACCESS_KEY="your-secret-key"
```

## Step 3: Run the Scraper

```bash
cd Offers
python processor.py
```

## Step 4: Configure GitHub Actions (Optional)

For automated daily runs:

1. Go to your GitHub repository
2. Navigate to **Settings** → **Secrets and variables** → **Actions**
3. Add the following secrets:
   - `S3_BUCKET_NAME`
   - `AWS_ACCESS_KEY_ID`
   - `AWS_SECRET_ACCESS_KEY`

The workflow will run automatically every day at 12:00 AM UTC.

## Testing Individual Components

### Test Scraper Only
```bash
cd Offers
python scraper.py
```
This will save data to a local JSON file without uploading to S3.

### Test S3 Connection
```bash
cd Offers
python s3_uploader.py
```

## Output

### S3 Structure
```
opensooq-data/
└── commercial-offers/
    └── year=2026/
        └── month=01/
            └── day=14/
                ├── excel files/
                │   └── commercialoffers.xlsx
                └── images/
                    ├── CarRental/
                    │   ├── offer_1673.jpg
                    │   └── ...
                    ├── DomesticCare/
                    └── ...
```

### Excel File
- Multi-sheet workbook
- One sheet per subcategory
- Columns: offer_id, image_url, s3_image_path, whatsapp_number, call_number, etc.

## Subcategories Scraped

- تأجير سيارات (CarRental)
- عمالة منزلية (DomesticCare)
- سيارات ومركبات (CarsVehicles)
- شحن / نقل عفش (ShippingMovingFurniture)
- أثاث ونشتري ألأثاث (FurnitureBuyFurniture)
- مقاولات وحرف (GeneralContractingCrafts)
- ستالايت وكاميرات مراقبة (SatelliteSurveillanceCameras)
- تكييف وتصليح اجهزة (HardwareAndAccessories)
- أصباغ (Pigments)
- متفرقات متنوعة (MixAds)
- تنظيف وغسيل (CleaningLaundry)
- مكافحة الحشرات (PestControl)

## Troubleshooting

### Issue: AWS credentials not found
**Solution**: Make sure environment variables are set correctly

### Issue: S3 upload fails
**Solution**: 
- Check your AWS credentials have write permissions to the bucket
- Verify the bucket name is correct
- Ensure the bucket exists in your AWS account

### Issue: No data scraped
**Solution**:
- Check your internet connection
- The website might be temporarily unavailable
- Check the logs for specific errors

## Logging

The scraper provides detailed logs:
- INFO: General progress information
- WARNING: Non-critical issues
- ERROR: Critical failures

Logs are printed to console during execution.
