import pandas as pd
from datetime import datetime
import logging
from io import BytesIO
from scraper import CommercialOffersScraper
from s3_uploader import S3Uploader
import os
import time

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class CommercialOffersProcessor:
    """Process commercial offers data and upload to S3"""
    
    def __init__(self, bucket_name, aws_access_key_id=None, aws_secret_access_key=None):
        """
        Initialize processor
        
        Args:
            bucket_name: S3 bucket name
            aws_access_key_id: AWS Access Key
            aws_secret_access_key: AWS Secret Key
        """
        self.scraper = CommercialOffersScraper()
        self.s3_uploader = S3Uploader(bucket_name, aws_access_key_id, aws_secret_access_key)
        self.date = datetime.now()
    
    def process_image_url(self, image_url):
        """
        Process image URL to get actual URL (replace {size} placeholder)
        
        Args:
            image_url: Image URL with {size} placeholder
            
        Returns:
            Actual image URL
        """
        # Replace {size} with appropriate size for downloading
        return image_url.replace('{size}', '700x0_offer')
    
    def download_and_upload_images(self, items, subcategory):
        """
        Download and upload images for all items in a subcategory
        
        Args:
            items: List of offer items
            subcategory: Subcategory reporting name
            
        Returns:
            Dictionary mapping offer_id to S3 image path
        """
        logger.info(f"Processing images for {subcategory}...")
        
        image_paths = {}
        
        for idx, item in enumerate(items, 1):
            offer_id = item.get('id')
            image_url = item.get('image', '')
            
            if not image_url:
                logger.warning(f"No image URL for offer {offer_id}")
                image_paths[offer_id] = ''
                continue
            
            # Process the image URL
            actual_image_url = self.process_image_url(image_url)
            
            # Generate S3 key for this image
            s3_key = self.s3_uploader.get_image_s3_key(offer_id, subcategory, self.date)
            
            # Download and upload
            s3_url = self.s3_uploader.download_and_upload_image(actual_image_url, s3_key)
            
            if s3_url:
                image_paths[offer_id] = s3_url
                logger.info(f"Uploaded image {idx}/{len(items)} for offer {offer_id}")
            else:
                image_paths[offer_id] = ''
                logger.error(f"Failed to upload image for offer {offer_id}")
            
            # Small delay between image downloads
            if idx % 10 == 0:
                time.sleep(1)
        
        return image_paths
    
    def create_dataframe_for_subcategory(self, items, image_paths):
        """
        Create DataFrame for a subcategory
        
        Args:
            items: List of offer items
            image_paths: Dictionary mapping offer_id to S3 image path
            
        Returns:
            pandas DataFrame
        """
        data = []
        
        for item in items:
            offer_id = item.get('id')
            
            row = {
                'offer_id': offer_id,
                'image_url': self.process_image_url(item.get('image', '')),
                's3_image_path': image_paths.get(offer_id, ''),
                'whatsapp_number': item.get('whats_phone_number', {}).get('phone_number', ''),
                'call_number': item.get('call_phone_number', {}).get('phone_number', ''),
                'deeplink': item.get('deeplink', ''),
                'share_deeplink': item.get('share_deeplink', ''),
                'is_external': item.get('is_external', False),
                'is_pinned': item.get('is_pinned', False),
                'deeplink_button_text': item.get('deeplink_button_text', ''),
                'views_count': item.get('views_count', 0),
                'scraped_at': self.date.strftime('%Y-%m-%d %H:%M:%S')
            }
            
            data.append(row)
        
        df = pd.DataFrame(data)
        return df
    
    def create_excel_file(self, all_data):
        """
        Create Excel file with multiple sheets for each subcategory
        
        Args:
            all_data: Dictionary with subcategory data and image paths
            
        Returns:
            BytesIO object containing Excel file
        """
        logger.info("Creating Excel file...")
        
        output = BytesIO()
        
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            for subcategory, data in all_data.items():
                items = data['items']
                image_paths = data['image_paths']
                title = data['title']
                
                # Create DataFrame
                df = self.create_dataframe_for_subcategory(items, image_paths)
                
                # Sanitize sheet name - remove invalid characters: / \ ? * [ ]
                # Excel sheet name limit is 31 characters
                sheet_name = title
                invalid_chars = ['/', '\\', '?', '*', '[', ']', ':']
                for char in invalid_chars:
                    sheet_name = sheet_name.replace(char, '-')
                
                # Truncate if too long
                sheet_name = sheet_name[:31] if len(sheet_name) > 31 else sheet_name
                
                # Write to Excel
                df.to_excel(writer, sheet_name=sheet_name, index=False)
                logger.info(f"Added sheet '{sheet_name}' with {len(df)} rows")
        
        output.seek(0)
        logger.info("Excel file created successfully")
        return output
    
    def process_and_upload(self):
        """
        Main process: scrape data, download images, create Excel, upload to S3
        """
        logger.info("="*60)
        logger.info("Starting Commercial Offers processing...")
        logger.info(f"Date: {self.date.strftime('%Y-%m-%d %H:%M:%S')}")
        logger.info("="*60)
        
        # Step 1: Scrape all offers
        logger.info("\n[Step 1/4] Scraping offers from OpenSooq...")
        all_offers = self.scraper.scrape_all_offers()
        
        if not all_offers:
            logger.error("No offers found. Exiting.")
            return False
        
        # Step 2: Download and upload images
        logger.info("\n[Step 2/4] Downloading and uploading images to S3...")
        all_data = {}
        
        for subcategory, data in all_offers.items():
            items = data['items']
            title = data['title']
            
            # Download and upload images
            image_paths = self.download_and_upload_images(items, subcategory)
            
            all_data[subcategory] = {
                'title': title,
                'items': items,
                'image_paths': image_paths
            }
        
        # Step 3: Create Excel file
        logger.info("\n[Step 3/4] Creating Excel file...")
        excel_bytes = self.create_excel_file(all_data)
        
        # Step 4: Upload Excel to S3
        logger.info("\n[Step 4/4] Uploading Excel file to S3...")
        excel_s3_url = self.s3_uploader.upload_excel(excel_bytes.getvalue(), self.date)
        
        if excel_s3_url:
            logger.info(f"Excel file uploaded successfully: {excel_s3_url}")
        else:
            logger.error("Failed to upload Excel file")
            return False
        
        # Summary
        logger.info("\n" + "="*60)
        logger.info("Processing completed successfully!")
        logger.info(f"Total subcategories: {len(all_data)}")
        total_offers = sum(len(data['items']) for data in all_data.values())
        logger.info(f"Total offers: {total_offers}")
        logger.info(f"Excel file: {excel_s3_url}")
        logger.info("="*60)
        
        return True


def main():
    """Main entry point"""
    # Get S3 credentials from environment variables
    bucket_name = os.getenv('S3_BUCKET_NAME')
    aws_access_key = os.getenv('AWS_ACCESS_KEY_ID')
    aws_secret_key = os.getenv('AWS_SECRET_ACCESS_KEY')
    
    if not bucket_name:
        logger.error("S3_BUCKET_NAME environment variable not set")
        return
    
    if not aws_access_key or not aws_secret_key:
        logger.error("AWS credentials not set")
        return
    
    # Create processor and run
    processor = CommercialOffersProcessor(
        bucket_name=bucket_name,
        aws_access_key_id=aws_access_key,
        aws_secret_access_key=aws_secret_key
    )
    
    success = processor.process_and_upload()
    
    if success:
        logger.info("All done!")
    else:
        logger.error("Process failed!")
        exit(1)


if __name__ == "__main__":
    main()
