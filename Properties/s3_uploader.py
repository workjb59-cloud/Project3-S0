"""
S3 Uploader for Properties Data
Handles uploading processed JSON files to AWS S3
"""

import json
import logging
import boto3
from pathlib import Path
from typing import Tuple, Optional
from datetime import datetime
from botocore.exceptions import ClientError

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class S3Uploader:
    """Handles S3 operations for uploading property and member data"""
    
    # S3 folder structure constants
    PROPERTIES_BASE_PATH = "opensooq-data/properties"
    INFO_BASE_PATH = "opensooq-data/info-json"
    
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
    
    def upload_properties_file(self, local_file_path: str, properties_data: dict) -> Tuple[bool, str]:
        """
        Upload properties data file to S3
        Structure: opensooq-data/properties/{category_label}/year=YYYY/month=MM/day=DD/{subcategory}.json
        
        Args:
            local_file_path: Path to local JSON file (for reference)
            properties_data: Dictionary containing properties organized by subcategory
        
        Returns:
            Tuple of (success: bool, s3_key: str)
        """
        try:
            now = datetime.now()
            year = now.year
            month = f"{now.month:02d}"
            day = f"{now.day:02d}"
            
            # Create uploads for each category type found in data
            for subcategory, cat_data in properties_data.items():
                # Extract category type from first property if available
                properties = cat_data.get('properties', [])
                if properties:
                    # Use cat1_label from category field for top-level category
                    category_label = properties[0].get('category', {}).get('cat1_label', 'unknown')
                else:
                    category_label = 'unknown'
                
                s3_key = f"{self.PROPERTIES_BASE_PATH}/{category_label}/year={year}/month={month}/day={day}/{subcategory}.json"
                
                # Upload file
                self.s3_client.put_object(
                    Bucket=self.bucket_name,
                    Key=s3_key,
                    Body=json.dumps(cat_data, ensure_ascii=False, indent=2),
                    ContentType='application/json',
                    ServerSideEncryption='AES256'
                )
                
                logger.info(f"Uploaded properties to S3: s3://{self.bucket_name}/{s3_key}")
            
            return True, f"s3://{self.bucket_name}/{self.PROPERTIES_BASE_PATH}/"
            
        except ClientError as e:
            logger.error(f"Failed to upload properties to S3: {str(e)}")
            return False, str(e)
        except Exception as e:
            logger.error(f"Unexpected error uploading properties: {str(e)}")
            return False, str(e)
    
    def upload_images_to_s3(self, local_images_dir: str, s3_image_path: str, listing_id: int) -> Tuple[bool, int]:
        """
        Upload all images from a local directory to S3 with listing_id prefix
        
        Args:
            local_images_dir: Local directory containing images
            s3_image_path: S3 base path where images should be uploaded (e.g., opensooq-data/properties/category/year=.../month=.../day=.../images/subcategory/)
            listing_id: Listing ID to use as filename prefix
        
        Returns:
            Tuple of (success: bool, count_uploaded: int)
        """
        try:
            from pathlib import Path
            local_path = Path(local_images_dir)
            
            if not local_path.exists():
                logger.warning(f"Local images directory not found: {local_images_dir}")
                return True, 0
            
            uploaded_count = 0
            
            # Upload all image files with listing_id prefix
            for image_file in local_path.glob('*'):
                if image_file.is_file():
                    # Create new filename with listing_id prefix
                    # e.g., "275039437_image_001.jpg"
                    image_name = image_file.name
                    new_filename = f"{listing_id}_{image_name}"
                    
                    # Read file and upload
                    with open(image_file, 'rb') as f:
                        s3_key = f"{s3_image_path}{new_filename}"
                        self.s3_client.put_object(
                            Bucket=self.bucket_name,
                            Key=s3_key,
                            Body=f.read(),
                            ServerSideEncryption='AES256'
                        )
                        uploaded_count += 1
                        logger.debug(f"Uploaded image to S3: s3://{self.bucket_name}/{s3_key}")
            
            logger.info(f"Uploaded {uploaded_count} images to S3: s3://{self.bucket_name}/{s3_image_path}")
            return True, uploaded_count
            
        except ClientError as e:
            logger.error(f"Failed to upload images to S3: {str(e)}")
            return False, 0
        except Exception as e:
            logger.error(f"Unexpected error uploading images: {str(e)}")
            return False, 0
    
    def upload_members_file(self, members_data: dict) -> Tuple[bool, str]:
        """
        Upload members/member info data to S3
        Structure: opensooq-data/info-json/info.json (incremental)
        
        Args:
            members_data: Dictionary containing member information
        
        Returns:
            Tuple of (success: bool, s3_key: str)
        """
        try:
            s3_key = f"{self.INFO_BASE_PATH}/info.json"
            
            # Check if file already exists and merge if needed
            existing_data = self._load_existing_members_file(s3_key)
            
            if existing_data:
                # Merge new members with existing ones (by member_id)
                merged_data = self._merge_members_data(existing_data, members_data)
            else:
                merged_data = members_data
            
            # Upload merged file
            self.s3_client.put_object(
                Bucket=self.bucket_name,
                Key=s3_key,
                Body=json.dumps(merged_data, ensure_ascii=False, indent=2),
                ContentType='application/json',
                ServerSideEncryption='AES256'
            )
            
            logger.info(f"Uploaded members info to S3: s3://{self.bucket_name}/{s3_key}")
            logger.info(f"Total unique members: {merged_data.get('count', 0)}")
            
            return True, f"s3://{self.bucket_name}/{s3_key}"
            
        except ClientError as e:
            logger.error(f"Failed to upload members to S3: {str(e)}")
            return False, str(e)
        except Exception as e:
            logger.error(f"Unexpected error uploading members: {str(e)}")
            return False, str(e)
    
    def _load_existing_members_file(self, s3_key: str) -> Optional[dict]:
        """Load existing members file from S3"""
        try:
            response = self.s3_client.get_object(Bucket=self.bucket_name, Key=s3_key)
            content = response['Body'].read().decode('utf-8')
            return json.loads(content)
        except ClientError as e:
            if e.response['Error']['Code'] == 'NoSuchKey':
                logger.info(f"No existing members file found at {s3_key}")
                return None
            else:
                logger.warning(f"Error loading existing members file: {str(e)}")
                return None
        except Exception as e:
            logger.warning(f"Error reading existing members file: {str(e)}")
            return None
    
    def _merge_members_data(self, existing: dict, new: dict) -> dict:
        """
        Merge new member data with existing data, avoiding duplicates
        Updates existing members with new data if timestamps are newer
        """
        existing_members = {m['member_id']: m for m in existing.get('members', [])}
        new_members = {m['member_id']: m for m in new.get('members', [])}
        
        # Merge: new data overwrites existing data for same member_id
        merged_members = {**existing_members, **new_members}
        
        return {
            'count': len(merged_members),
            'scraped_at': new.get('scraped_at'),
            'members': sorted(
                merged_members.values(),
                key=lambda x: x.get('member_id', 0)
            ),
        }
    
    def upload_files(self, properties_file: str, members_file: str) -> Tuple[bool, dict]:
        """
        Upload both properties and members files to S3
        
        Args:
            properties_file: Path to properties JSON file
            members_file: Path to members JSON file
        
        Returns:
            Tuple of (success: bool, upload_results: dict)
        """
        results = {
            'properties': {'success': False, 'location': None},
            'members': {'success': False, 'location': None},
        }
        
        try:
            # Load properties data
            with open(properties_file, 'r', encoding='utf-8') as f:
                properties_data = json.load(f)
            
            # Load members data
            with open(members_file, 'r', encoding='utf-8') as f:
                members_data = json.load(f)
            
            # Upload properties
            prop_success, prop_location = self.upload_properties_file(properties_file, properties_data)
            results['properties']['success'] = prop_success
            results['properties']['location'] = prop_location
            
            # Upload members
            mem_success, mem_location = self.upload_members_file(members_data)
            results['members']['success'] = mem_success
            results['members']['location'] = mem_location
            
            return prop_success and mem_success, results
            
        except FileNotFoundError as e:
            logger.error(f"File not found: {str(e)}")
            return False, results
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON file: {str(e)}")
            return False, results
        except Exception as e:
            logger.error(f"Unexpected error during upload: {str(e)}")
            return False, results
    
    def test_connection(self) -> bool:
        """Test S3 connection"""
        try:
            self.s3_client.head_bucket(Bucket=self.bucket_name)
            logger.info(f"S3 connection test successful for bucket: {self.bucket_name}")
            return True
        except ClientError as e:
            logger.error(f"S3 connection test failed: {str(e)}")
            return False
