import boto3
import os
import logging
from datetime import datetime
from io import BytesIO
import requests
from botocore.exceptions import ClientError

logger = logging.getLogger(__name__)


class S3Uploader:
    """Handle S3 uploads for commercial offers data"""
    
    def __init__(self, bucket_name, aws_access_key_id=None, aws_secret_access_key=None):
        """
        Initialize S3 client
        
        Args:
            bucket_name: S3 bucket name
            aws_access_key_id: AWS Access Key (if None, uses environment variable)
            aws_secret_access_key: AWS Secret Key (if None, uses environment variable)
        """
        self.bucket_name = bucket_name
        
        # Get credentials from parameters or environment
        access_key = aws_access_key_id or os.getenv('AWS_ACCESS_KEY_ID')
        secret_key = aws_secret_access_key or os.getenv('AWS_SECRET_ACCESS_KEY')
        
        if not access_key or not secret_key:
            raise ValueError("AWS credentials not provided")
        
        self.s3_client = boto3.client(
            's3',
            aws_access_key_id=access_key,
            aws_secret_access_key=secret_key
        )
        
        logger.info(f"S3 client initialized for bucket: {bucket_name}")
    
    def get_date_partition_path(self, base_folder, date=None):
        """
        Generate date-partitioned path
        
        Args:
            base_folder: Base folder name (e.g., 'commercial-offers')
            date: Date object (default: today)
            
        Returns:
            String path like 'opensooq-data/commercial-offers/year=2026/month=01/day=14/'
        """
        if date is None:
            date = datetime.now()
        
        path = f"opensooq-data/{base_folder}/year={date.year}/month={date.month:02d}/day={date.day:02d}/"
        return path
    
    def upload_file(self, file_path, s3_key):
        """
        Upload a file to S3
        
        Args:
            file_path: Local file path
            s3_key: S3 object key (path in bucket)
            
        Returns:
            S3 URL of uploaded file
        """
        try:
            self.s3_client.upload_file(file_path, self.bucket_name, s3_key)
            s3_url = f"s3://{self.bucket_name}/{s3_key}"
            logger.info(f"Uploaded {file_path} to {s3_url}")
            return s3_url
        except ClientError as e:
            logger.error(f"Error uploading file {file_path}: {e}")
            return None
    
    def upload_bytes(self, data_bytes, s3_key, content_type='application/octet-stream'):
        """
        Upload bytes data to S3
        
        Args:
            data_bytes: Bytes data to upload
            s3_key: S3 object key
            content_type: Content type for the file
            
        Returns:
            S3 URL of uploaded file
        """
        try:
            self.s3_client.put_object(
                Bucket=self.bucket_name,
                Key=s3_key,
                Body=data_bytes,
                ContentType=content_type
            )
            s3_url = f"s3://{self.bucket_name}/{s3_key}"
            logger.info(f"Uploaded bytes to {s3_url}")
            return s3_url
        except ClientError as e:
            logger.error(f"Error uploading bytes to {s3_key}: {e}")
            return None
    
    def download_and_upload_image(self, image_url, s3_key, timeout=30):
        """
        Download image from URL and upload to S3
        
        Args:
            image_url: URL of the image to download
            s3_key: S3 object key for the uploaded image
            timeout: Request timeout in seconds
            
        Returns:
            S3 URL of uploaded image or None if failed
        """
        try:
            # Download image
            response = requests.get(image_url, timeout=timeout, stream=True)
            response.raise_for_status()
            
            # Get content type
            content_type = response.headers.get('Content-Type', 'image/jpeg')
            
            # Upload to S3
            image_bytes = response.content
            s3_url = self.upload_bytes(image_bytes, s3_key, content_type)
            
            return s3_url
            
        except Exception as e:
            logger.error(f"Error downloading/uploading image {image_url}: {e}")
            return None
    
    def upload_excel(self, excel_bytes, date=None):
        """
        Upload Excel file to S3 with date partitioning
        
        Args:
            excel_bytes: Excel file as bytes
            date: Date for partitioning (default: today)
            
        Returns:
            S3 URL of uploaded Excel file
        """
        if date is None:
            date = datetime.now()
        
        # Generate S3 key
        date_path = self.get_date_partition_path('commercial-offers', date)
        s3_key = f"{date_path}excel files/commercialoffers.xlsx"
        
        # Upload
        return self.upload_bytes(
            excel_bytes, 
            s3_key, 
            content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
    
    def get_image_s3_key(self, offer_id, subcategory, date=None):
        """
        Generate S3 key for an offer image
        
        Args:
            offer_id: Offer ID
            subcategory: Subcategory reporting name
            date: Date for partitioning (default: today)
            
        Returns:
            S3 key for the image
        """
        if date is None:
            date = datetime.now()
        
        date_path = self.get_date_partition_path('commercial-offers', date)
        s3_key = f"{date_path}images/{subcategory}/offer_{offer_id}.jpg"
        
        return s3_key


if __name__ == "__main__":
    # Test S3 connection
    logging.basicConfig(level=logging.INFO)
    
    try:
        uploader = S3Uploader(
            bucket_name=os.getenv('S3_BUCKET_NAME', 'your-bucket-name'),
            aws_access_key_id=os.getenv('AWS_ACCESS_KEY_ID'),
            aws_secret_access_key=os.getenv('AWS_SECRET_ACCESS_KEY')
        )
        logger.info("S3 connection successful!")
    except Exception as e:
        logger.error(f"S3 connection failed: {e}")
