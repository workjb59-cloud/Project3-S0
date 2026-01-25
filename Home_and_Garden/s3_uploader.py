"""
S3 Uploader for Home and Garden Data
Handles uploading JSON and images to AWS S3 with date partitioning
"""

import json
import logging
import boto3
from pathlib import Path
from typing import Optional, Dict, List
from datetime import datetime
from botocore.exceptions import ClientError
import requests
from io import BytesIO

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class HomeGardenS3Uploader:
    """Handles S3 operations for home-garden listings and member data"""
    
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
    def _get_partition_path(date: datetime) -> str:
        """
        Generate partition path based on date
        
        Args:
            date: datetime object
        
        Returns:
            Partition path string (year=2026/month=01/day=25)
        """
        return f"year={date.year}/month={date.month:02d}/day={date.day:02d}"

    def upload_listing_json(
        self,
        listing_data: Dict,
        main_category: str,
        sub_category: str,
        date: datetime,
        listing_id: str
    ) -> str:
        """
        Upload listing JSON to S3 with proper partitioning
        
        Args:
            listing_data: Dictionary containing listing details
            main_category: Main category (e.g., "الأثاث")
            sub_category: Subcategory (e.g., "أثاث غرف جلوس")
            date: Date object for partitioning
            listing_id: Unique listing ID
        
        Returns:
            S3 path where the file was uploaded
        """
        try:
            partition = self._get_partition_path(date)
            s3_key = f"opensooq-data/home-garden/{partition}/json files/{main_category}/{sub_category}/{listing_id}.json"
            
            json_content = json.dumps(listing_data, ensure_ascii=False, indent=2)
            
            self.s3_client.put_object(
                Bucket=self.bucket_name,
                Key=s3_key,
                Body=json_content.encode('utf-8'),
                ContentType='application/json'
            )
            
            logger.info(f"Uploaded listing JSON: {s3_key}")
            return s3_key
        except ClientError as e:
            logger.error(f"Failed to upload listing JSON {listing_id}: {str(e)}")
            raise

    def upload_image(
        self,
        image_url: str,
        main_category: str,
        sub_category: str,
        date: datetime,
        listing_id: str,
        image_id: str
    ) -> Optional[str]:
        """
        Download image from URL and upload to S3
        
        Args:
            image_url: URL of the image
            main_category: Main category
            sub_category: Subcategory
            date: Date object for partitioning
            listing_id: Listing ID
            image_id: Unique image ID
        
        Returns:
            S3 path where the image was uploaded, or None if failed
        """
        try:
            # Construct proper image URL if needed (convert to webp preview format)
            if 'previews' not in image_url:
                # Convert uri to full CDN URL with preview
                image_url = f"https://opensooq-images.os-cdn.com/previews/300x0/{image_url}.webp"
            
            # Download image
            response = requests.get(image_url, timeout=10)
            response.raise_for_status()
            
            # Determine file extension from URL
            if '.webp' in image_url:
                ext = 'webp'
            elif '.png' in image_url:
                ext = 'png'
            else:
                ext = 'jpg'
            
            # Generate S3 key
            partition = self._get_partition_path(date)
            s3_key = f"opensooq-data/home-garden/{partition}/images/{main_category}/{sub_category}/{listing_id}_{image_id}.{ext}"
            
            # Upload to S3
            self.s3_client.put_object(
                Bucket=self.bucket_name,
                Key=s3_key,
                Body=response.content,
                ContentType=content_type
            )
            
            logger.info(f"Uploaded image: {s3_key}")
            return f"s3://{self.bucket_name}/{s3_key}"
        except Exception as e:
            logger.error(f"Failed to upload image from {image_url}: {str(e)}")
            return None

    def upload_member_info_batch(self, member_data: List[Dict]) -> str:
        """
        Upload or append member info to incremental JSON file
        
        Args:
            member_data: List of member info dictionaries
        
        Returns:
            S3 path where the file was uploaded
        """
        try:
            s3_key = f"opensooq-data/properties/info-json/members-info.json"
            
            # Try to get existing data
            existing_data = []
            try:
                response = self.s3_client.get_object(Bucket=self.bucket_name, Key=s3_key)
                existing_data = json.loads(response['Body'].read().decode('utf-8'))
                if not isinstance(existing_data, list):
                    existing_data = []
            except self.s3_client.exceptions.NoSuchKey:
                # File doesn't exist yet
                existing_data = []
            except Exception as e:
                logger.warning(f"Could not read existing member data: {str(e)}")
                existing_data = []
            
            # Add new data (avoid duplicates by member_id)
            existing_member_ids = {member.get('member_id') for member in existing_data}
            new_members = 0
            
            for member in member_data:
                if member.get('member_id') not in existing_member_ids:
                    existing_data.append(member)
                    new_members += 1
            
            # Upload updated file
            json_content = json.dumps(existing_data, ensure_ascii=False, indent=2)
            
            self.s3_client.put_object(
                Bucket=self.bucket_name,
                Key=s3_key,
                Body=json_content.encode('utf-8'),
                ContentType='application/json'
            )
            
            logger.info(f"Uploaded {new_members} new member records to: {s3_key}")
            return s3_key
        except ClientError as e:
            logger.error(f"Failed to upload member info: {str(e)}")
            raise

    def upload_property_json(
        self,
        property_data: Dict,
        main_category: str,
        sub_category: str,
        date: datetime,
        listing_id: str
    ) -> str:
        """
        Upload property JSON to Properties folder
        
        Args:
            property_data: Dictionary containing property details (without seller info)
            main_category: Main category
            sub_category: Subcategory
            date: Date object
            listing_id: Listing ID
        
        Returns:
            S3 path where the file was uploaded
        """
        try:
            partition = self._get_partition_path(date)
            s3_key = f"opensooq-data/properties/{partition}/{main_category}/{sub_category}/{listing_id}.json"
            
            json_content = json.dumps(property_data, ensure_ascii=False, indent=2)
            
            self.s3_client.put_object(
                Bucket=self.bucket_name,
                Key=s3_key,
                Body=json_content.encode('utf-8'),
                ContentType='application/json'
            )
            
            logger.info(f"Uploaded property JSON: {s3_key}")
            return s3_key
        except ClientError as e:
            logger.error(f"Failed to upload property JSON {listing_id}: {str(e)}")
            raise
