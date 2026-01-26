"""
S3 Uploader for Services Data
Handles uploading JSON data to AWS S3 with date partitioning
"""

import json
import logging
import boto3
from pathlib import Path
from typing import Optional, Dict, List
from datetime import datetime, date
from botocore.exceptions import ClientError

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class ServicesS3Uploader:
    """Handles S3 operations for services listings and member data"""
    
    def __init__(self, bucket_name: str, aws_access_key: str, aws_secret_key: str, region: str = 'us-east-1'):
        """
        Initialize S3 uploader with AWS credentials
        
        Args:
            bucket_name: S3 bucket name
            aws_access_key: AWS access key ID
            aws_secret_key: AWS secret access key
            region: AWS region
        """
        self.bucket_name = bucket_name
        self.region = region
        
        try:
            self.s3_client = boto3.client(
                's3',
                region_name=region,
                aws_access_key_id=aws_access_key,
                aws_secret_access_key=aws_secret_key
            )
            # Test connection
            self.s3_client.head_bucket(Bucket=bucket_name)
            logger.info(f"Successfully connected to S3 bucket: {bucket_name}")
        except ClientError as e:
            logger.error(f"Failed to connect to S3 bucket {bucket_name}: {str(e)}")
            raise

    @staticmethod
    def build_s3_key(base_folder: str, target_date: date, category: str = None, 
                     subcategory: str = None, is_info: bool = False) -> str:
        """
        Build S3 key with date partitioning
        
        Args:
            base_folder: Base folder name (e.g., 'services')
            target_date: Date for partitioning
            category: Category name (optional)
            subcategory: Subcategory name (optional)
            is_info: Whether this is member info data
        
        Returns:
            S3 key path
        """
        year = target_date.year
        month = f"{target_date.month:02d}"
        day = f"{target_date.day:02d}"
        
        if is_info:
            # Member info path: info-json/info.json (at root level)
            return "info-json/info.json"
        else:
            # Listings path: services/year=2026/month=01/day=25/json-files/Category/subcategory.json
            safe_category = category.replace('/', '_').replace(' ', '_')
            safe_subcategory = subcategory.replace('/', '_').replace(' ', '_')
            return f"{base_folder}/year={year}/month={month}/day={day}/json-files/{safe_category}/{safe_subcategory}.json"

    def upload_json(self, data: Dict or List, s3_key: str) -> bool:
        """
        Upload JSON data to S3
        
        Args:
            data: Data to upload (dict or list)
            s3_key: S3 key path
        
        Returns:
            True if successful, False otherwise
        """
        try:
            json_data = json.dumps(data, ensure_ascii=False, indent=2)
            
            self.s3_client.put_object(
                Bucket=self.bucket_name,
                Key=s3_key,
                Body=json_data.encode('utf-8'),
                ContentType='application/json',
                ContentEncoding='utf-8'
            )
            
            logger.info(f"Successfully uploaded to s3://{self.bucket_name}/{s3_key}")
            return True
        except ClientError as e:
            logger.error(f"Error uploading {s3_key}: {str(e)}")
            return False

    def check_if_exists(self, s3_key: str) -> bool:
        """
        Check if a file exists in S3
        
        Args:
            s3_key: S3 key path
        
        Returns:
            True if exists, False otherwise
        """
        try:
            self.s3_client.head_object(Bucket=self.bucket_name, Key=s3_key)
            return True
        except ClientError:
            return False

    def download_json(self, s3_key: str) -> Optional[Dict or List]:
        """
        Download and parse JSON from S3
        
        Args:
            s3_key: S3 key path
        
        Returns:
            Parsed JSON data or None if failed
        """
        try:
            response = self.s3_client.get_object(Bucket=self.bucket_name, Key=s3_key)
            json_data = response['Body'].read().decode('utf-8')
            return json.loads(json_data)
        except ClientError as e:
            logger.warning(f"Error downloading {s3_key}: {str(e)}")
            return None

    def upload_subcategory_data(self, category: str, subcategory: str, listings: List[Dict], 
                                target_date: date) -> bool:
        """
        Upload subcategory listings to S3
        
        Args:
            category: Main category name
            subcategory: Subcategory name
            listings: List of listings data
            target_date: Target date for partitioning
        
        Returns:
            True if successful
        """
        s3_key = self.build_s3_key(
            base_folder='services',
            target_date=target_date,
            category=category,
            subcategory=subcategory,
            is_info=False
        )
        
        logger.info(f"Uploading {len(listings)} listings to {s3_key}")
        return self.upload_json(listings, s3_key)

    def upload_member_info(self, member_data: List[Dict], target_date: date) -> bool:
        """
        Upload member info to S3 (incremental)
        
        Args:
            member_data: List of member information dicts
            target_date: Target date for partitioning
        
        Returns:
            True if successful
        """
        s3_key = self.build_s3_key(
            base_folder='services',
            target_date=target_date,
            is_info=True
        )
        
        # Check if file exists
        existing_data = []
        if self.check_if_exists(s3_key):
            logger.info(f"Found existing member info file, downloading for merge...")
            existing_data = self.download_json(s3_key) or []
        
        # Merge with existing data (incremental)
        existing_ids = {member.get('id') for member in existing_data}
        new_members = [m for m in member_data if m.get('id') not in existing_ids]
        
        if new_members:
            combined_data = existing_data + new_members
            logger.info(f"Uploading {len(new_members)} new members (total: {len(combined_data)})")
            return self.upload_json(combined_data, s3_key)
        else:
            logger.info("No new members to upload")
            return True

    def upload_all_data(self, data_manager, target_date: date) -> bool:
        """
        Upload all scraped data to S3
        
        Args:
            data_manager: ServicesDataManager instance with scraped data
            target_date: Target date for partitioning
        
        Returns:
            True if all uploads successful
        """
        success = True
        
        # Upload subcategory data
        subcategory_data = data_manager.get_subcategory_data()
        for category, subcategories in subcategory_data.items():
            for subcategory, listings in subcategories.items():
                if not self.upload_subcategory_data(category, subcategory, listings, target_date):
                    success = False
        
        # Upload member info (incremental)
        member_info = data_manager.get_member_info_list()
        if member_info:
            if not self.upload_member_info(member_info, target_date):
                success = False
        
        # Log statistics
        stats = data_manager.get_stats()
        logger.info(f"Upload complete. Stats: {stats}")
        
        return success

    def list_files(self, prefix: str) -> List[str]:
        """
        List files in S3 bucket with given prefix
        
        Args:
            prefix: S3 key prefix
        
        Returns:
            List of S3 keys
        """
        try:
            response = self.s3_client.list_objects_v2(
                Bucket=self.bucket_name,
                Prefix=prefix
            )
            
            files = []
            if 'Contents' in response:
                files = [obj['Key'] for obj in response['Contents']]
            
            return files
        except ClientError as e:
            logger.error(f"Error listing files with prefix {prefix}: {str(e)}")
            return []
