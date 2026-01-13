"""
Utility functions for opensooq.com scraper
"""
import json
import re
import os
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from bs4 import BeautifulSoup
import boto3
from io import BytesIO
import pandas as pd
import requests


def extract_json_from_html(html_content: str, json_key: str) -> Optional[Dict]:
    """
    Extract JSON data from HTML using BeautifulSoup
    
    Args:
        html_content: HTML content as string
        json_key: The key to look for in the JSON (e.g., 'pageProps')
    
    Returns:
        Extracted JSON data or None
    """
    try:
        soup = BeautifulSoup(html_content, 'html.parser')
        
        # Find the script tag containing __NEXT_DATA__
        script_tag = soup.find('script', {'id': '__NEXT_DATA__'})
        
        if not script_tag:
            print("Could not find __NEXT_DATA__ script tag")
            return None
        
        # Parse JSON from script content
        json_data = json.loads(script_tag.string)
        
        # Extract pageProps or specified key
        if 'props' in json_data and json_key in json_data['props']:
            return json_data['props'][json_key]
        
        return None
    except Exception as e:
        print(f"Error extracting JSON from HTML: {e}")
        return None


def is_yesterday_ad(posted_at: str) -> bool:
    """
    Check if an ad was posted in the last 24 hours (yesterday or today)
    
    Args:
        posted_at: Posted date string in Arabic (e.g., "قبل ساعة", "أمس", "قبل يوم")
    
    Returns:
        True if ad was posted in the last 24 hours
    """
    try:
        # Check for "أمس" (yesterday)
        if "أمس" in posted_at:
            return True
        
        # Check for "يوم" or "أيام" (days)
        if "قبل يوم" in posted_at or "قبل 1 يوم" in posted_at:
            return True
        
        # Check for "أيام" (multiple days) - if more than 1 day, reject
        days_match = re.search(r'قبل (\d+) (يوم|أيام)', posted_at)
        if days_match:
            days = int(days_match.group(1))
            # Only accept ads from yesterday (1 day ago)
            return days == 1
        
        # Check for hours - accept any ads posted within 24 hours
        hour_match = re.search(r'قبل (\d+) ساع', posted_at)
        if hour_match:
            hours = int(hour_match.group(1))
            # Accept ads posted in last 24 hours
            return hours <= 24
        
        # Check for single hour: "قبل ساعة" (1 hour ago)
        if "قبل ساعة" in posted_at and "ساعتان" not in posted_at and "ساعات" not in posted_at:
            return True
        
        # Check for "قبل ساعتان" (2 hours ago)
        if "قبل ساعتان" in posted_at or "قبل ساعتين" in posted_at:
            return True
        
        # Check for minutes - accept all recent ads (minutes ago)
        if "دقيقة" in posted_at or "دقائق" in posted_at:
            return True
        
        return False
    except Exception as e:
        print(f"Error checking date for '{posted_at}': {e}")
        return False


def filter_yesterday_ads(ads: List[Dict]) -> List[Dict]:
    """
    Filter ads to only include those posted yesterday
    
    Args:
        ads: List of ad dictionaries
    
    Returns:
        Filtered list of ads
    """
    yesterday_ads = []
    for ad in ads:
        if 'posted_at' in ad and is_yesterday_ad(ad['posted_at']):
            yesterday_ads.append(ad)
    
    return yesterday_ads


def download_image(image_url: str, timeout: int = 30) -> Optional[bytes]:
    """
    Download image from URL
    
    Args:
        image_url: URL of the image (can be full URL or just the hash path)
        timeout: Request timeout in seconds
    
    Returns:
        Image bytes or None if failed
    """
    try:
        # Construct full URL if not already complete
        if not image_url.startswith('http'):
            # Try with previews path first (common format)
            image_url = f"https://opensooq-images.os-cdn.com/previews/2048x0/{image_url}.webp"
        
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Accept': 'image/webp,image/apng,image/*,*/*;q=0.8',
            'Referer': 'https://kw.opensooq.com/'
        }
        
        response = requests.get(image_url, headers=headers, timeout=timeout)
        response.raise_for_status()
        return response.content
    
    except Exception as e:
        print(f"Error downloading image {image_url}: {e}")
        return None


def upload_image_to_s3(image_data: bytes, bucket_name: str, s3_key: str,
                       aws_access_key: str, aws_secret_key: str,
                       content_type: str = 'image/jpeg') -> bool:
    """
    Upload image bytes to S3
    
    Args:
        image_data: Image bytes
        bucket_name: S3 bucket name
        s3_key: S3 object key (path)
        aws_access_key: AWS access key
        aws_secret_key: AWS secret key
        content_type: Image content type
    
    Returns:
        True if successful, False otherwise
    """
    try:
        s3_client = boto3.client(
            's3',
            aws_access_key_id=aws_access_key,
            aws_secret_access_key=aws_secret_key
        )
        
        s3_client.put_object(
            Bucket=bucket_name,
            Key=s3_key,
            Body=image_data,
            ContentType=content_type
        )
        
        return True
    
    except Exception as e:
        print(f"Error uploading image to S3: {e}")
        return False


def upload_to_s3(data: pd.DataFrame, bucket_name: str, s3_key: str, 
                 aws_access_key: str, aws_secret_key: str) -> bool:
    """
    Upload DataFrame to S3 as Excel file
    
    Args:
        data: Pandas DataFrame to upload
        bucket_name: S3 bucket name
        s3_key: S3 object key (path)
        aws_access_key: AWS access key
        aws_secret_key: AWS secret key
    
    Returns:
        True if successful, False otherwise
    """
    try:
        # Create S3 client
        s3_client = boto3.client(
            's3',
            aws_access_key_id=aws_access_key,
            aws_secret_access_key=aws_secret_key
        )
        
        # Convert DataFrame to Excel in memory
        excel_buffer = BytesIO()
        with pd.ExcelWriter(excel_buffer, engine='openpyxl') as writer:
            data.to_excel(writer, index=False, sheet_name='Data')
        
        excel_buffer.seek(0)
        
        # Upload to S3
        s3_client.put_object(
            Bucket=bucket_name,
            Key=s3_key,
            Body=excel_buffer.getvalue(),
            ContentType='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
        
        print(f"Successfully uploaded to s3://{bucket_name}/{s3_key}")
        return True
    
    except Exception as e:
        print(f"Error uploading to S3: {e}")
        return False


def download_from_s3(bucket_name: str, s3_key: str, 
                      aws_access_key: str, aws_secret_key: str) -> Optional[pd.DataFrame]:
    """
    Download Excel file from S3 and return as DataFrame
    
    Args:
        bucket_name: S3 bucket name
        s3_key: S3 object key (path)
        aws_access_key: AWS access key
        aws_secret_key: AWS secret key
    
    Returns:
        DataFrame or None if file doesn't exist
    """
    try:
        s3_client = boto3.client(
            's3',
            aws_access_key_id=aws_access_key,
            aws_secret_access_key=aws_secret_key
        )
        
        # Download file
        response = s3_client.get_object(Bucket=bucket_name, Key=s3_key)
        excel_data = response['Body'].read()
        
        # Read Excel data
        df = pd.read_excel(BytesIO(excel_data))
        return df
    
    except s3_client.exceptions.NoSuchKey:
        print(f"File not found: s3://{bucket_name}/{s3_key}")
        return None
    except Exception as e:
        print(f"Error downloading from S3: {e}")
        return None


def prepare_shop_info_row(shop_data: Dict) -> Dict:
    """
    Prepare shop info for the info.xlsx file - extracts ALL available fields
    
    Args:
        shop_data: Shop data dictionary
    
    Returns:
        Dictionary with comprehensive shop info for Excel row
    """
    try:
        member = shop_data.get('info', {}).get('member', {})
        branding = member.get('branding', {})
        rating = member.get('rating', {})
        location = branding.get('location', {})
        following = member.get('following', {})
        share = branding.get('share', {})
        
        # Build comprehensive shop info dictionary
        shop_info = {
            # Basic info
            'member_id': member.get('id'),
            'shop_name': branding.get('name'),
            'is_shop': member.get('is_shop'),
            'has_membership': member.get('has_membership'),
            
            # Category
            'category_id': branding.get('category_id'),
            'category_name': branding.get('category_name'),
            'description': branding.get('description'),
            
            # Location
            'city_name': branding.get('city_name'),
            'address': location.get('address'),
            'has_location': location.get('has_location'),
            'is_location_requested': location.get('is_location_requested'),
            'latitude': location.get('lat'),
            'longitude': location.get('long'),
            
            # Stats
            'posts_count': member.get('posts_count'),
            'views_count': member.get('views_count'),
            'response_time': member.get('response_time'),
            'member_since': member.get('member_since'),
            
            # Contact
            'mobile_number': member.get('mobile_number'),
            'reveal_key': member.get('reveal_key'),
            'call_anytime': branding.get('call_anytime'),
            'enable_login_before_call': member.get('enable_login_before_call'),
            
            # Following/Social
            'is_followed': following.get('is_followed'),
            'followers_count': following.get('followers_count'),
            'followings_count': following.get('followings_count'),
            
            # Rating
            'average_rating': rating.get('average_rating'),
            'number_of_rating': rating.get('number_of_rating'),
            'number_of_reviews': rating.get('number_of_reviews'),
            'buyer_to_seller_rate': rating.get('buyer_to_seller_rate'),
            'enable_rating_form': rating.get('enable_rating_form'),
            'show_rating_after_interaction': rating.get('show_rating_after_interaction'),
            
            # Rating stats
            'n_star_1_percentage': rating.get('stats', {}).get('n_star_1_percentage'),
            'n_star_2_percentage': rating.get('stats', {}).get('n_star_2_percentage'),
            'n_star_3_percentage': rating.get('stats', {}).get('n_star_3_percentage'),
            'n_star_4_percentage': rating.get('stats', {}).get('n_star_4_percentage'),
            'n_star_5_percentage': rating.get('stats', {}).get('n_star_5_percentage'),
            
            # Media
            'avatar': branding.get('avatar'),
            'cover_photo': branding.get('cover_photo'),
            
            # Share links
            'share_title': share.get('title'),
            'share_link': share.get('link'),
            'share_deeplink': share.get('share_deeplink'),
            
            # Verification & Status
            'authorised_seller': member.get('authorised_seller'),
            'verification_level': member.get('verification_level'),
            'is_reported': member.get('is_reported'),
            'show_reporting': member.get('show_reporting'),
            'is_reels_enabled': member.get('is_reels_enabled'),
            'show_sold_listings': member.get('show_sold_listings'),
            
            # Metadata
            'scraped_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }
        
        # Add open hours if available
        open_hours = branding.get('open_hours', [])
        if open_hours:
            # Store open hours as JSON string for each day
            for hour in open_hours:
                dow = hour.get('dow')
                dow_label = hour.get('dow_label', f'day_{dow}')
                shop_info[f'open_hours_{dow_label}'] = f"{hour.get('open_time')} - {hour.get('close_time')}"
        
        return shop_info
        
    except Exception as e:
        print(f"Error preparing shop info: {e}")
        return {}


def prepare_ad_data(ads: List[Dict], shop_basic_info: Dict, ad_images_map: Optional[Dict[int, List[str]]] = None) -> pd.DataFrame:
    """
    Prepare ads data for Excel export with basic shop info
    
    Args:
        ads: List of ad dictionaries
        shop_basic_info: Basic shop info to include with each ad
        ad_images_map: Optional dict mapping ad_id to list of S3 image paths
    
    Returns:
        DataFrame with ads data
    """
    try:
        rows = []
        for ad in ads:
            row = {
                # Shop basic info
                'shop_member_id': shop_basic_info.get('member_id'),
                'shop_name': shop_basic_info.get('shop_name'),
                
                # Ad info
                'ad_id': ad.get('id'),
                'title': ad.get('title'),
                'posted_at': ad.get('posted_at'),
                'expired_at': ad.get('expired_at'),
                'price_amount': ad.get('price_amount'),
                'price_currency_iso': ad.get('price_currency_iso'),
                'city_id': ad.get('city_id'),
                'city_label': ad.get('city_label'),
                'nhood_id': ad.get('nhood_id'),
                'nhood_label': ad.get('nhood_label'),
                'cat1_code': ad.get('cat1_code'),
                'cat1_label': ad.get('cat1_label'),
                'cat2_code': ad.get('cat2_code'),
                'cat2_label': ad.get('cat2_label'),
                'image_uri': ad.get('image_uri'),
                'image_count': ad.get('image_count'),
                'has_video': ad.get('has_video'),
                'has_360': ad.get('has_360'),
                'highlights': ad.get('highlights'),
                'masked_description': ad.get('masked_description'),
                'post_url': ad.get('post_url'),
                'phone_number': ad.get('phone_number'),
                'member_rating_avg': ad.get('member_rating_avg'),
                'member_rating_count': ad.get('member_rating_count'),
                'verification_level': ad.get('verification_level'),
                'listing_status': ad.get('listing_status'),
                'scraped_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                's3_image_path': '; '.join(ad_images_map.get(ad.get('id'), [])) if ad_images_map else None
            }
            rows.append(row)
        
        return pd.DataFrame(rows)
    
    except Exception as e:
        print(f"Error preparing ad data: {e}")
        return pd.DataFrame()


def save_ad_images_to_s3(ads: List[Dict], shop_name: str, member_id: int,
                         bucket_name: str, s3_base_path: str, category_path: str,
                         aws_access_key: str, aws_secret_key: str,
                         date: datetime = None) -> Dict[int, List[str]]:
    """
    Download and save ad images to S3
    
    Args:
        ads: List of ad dictionaries
        shop_name: Shop name
        member_id: Shop member ID
        bucket_name: S3 bucket name
        s3_base_path: Base S3 path (e.g., "opensooq-data")
        category_path: Category path (e.g., "shops")
        aws_access_key: AWS access key
        aws_secret_key: AWS secret key
        date: Date for partitioning
    
    Returns:
        Dictionary mapping ad_id to list of S3 image paths
    """
    if date is None:
        date = datetime.now()
    
    year = date.strftime('%Y')
    month = date.strftime('%m')
    day = date.strftime('%d')
    
    # Clean shop name for folder
    safe_shop_name = re.sub(r'[^\w\s-]', '', shop_name)
    safe_shop_name = re.sub(r'[-\s]+', '_', safe_shop_name).strip('_')
    if len(safe_shop_name) > 50:
        safe_shop_name = safe_shop_name[:50]
    if not safe_shop_name:
        safe_shop_name = f"shop_{member_id}"
    
    ad_images_map = {}
    
    for ad in ads:
        ad_id = ad.get('id')
        if not ad_id:
            continue
        
        # Get image URI
        image_uri = ad.get('image_uri')
        if not image_uri:
            continue
        
        # Download image
        image_data = download_image(image_uri)
        if not image_data:
            continue
        
        # Determine file extension from URI
        ext = 'jpg'
        if '.png' in image_uri.lower():
            ext = 'png'
        elif '.webp' in image_uri.lower():
            ext = 'webp'
        
        # Generate S3 path for image
        image_filename = f"ad_{ad_id}_main.{ext}"
        s3_image_key = f"{s3_base_path}/{category_path}/year={year}/month={month}/day={day}/images/{safe_shop_name}/{image_filename}"
        
        # Upload to S3
        content_type = f"image/{ext}"
        if ext == 'jpg':
            content_type = 'image/jpeg'
        
        success = upload_image_to_s3(
            image_data=image_data,
            bucket_name=bucket_name,
            s3_key=s3_image_key,
            aws_access_key=aws_access_key,
            aws_secret_key=aws_secret_key,
            content_type=content_type
        )
        
        if success:
            if ad_id not in ad_images_map:
                ad_images_map[ad_id] = []
            ad_images_map[ad_id].append(s3_image_key)
            print(f"  ✓ Saved image for ad {ad_id}")
    
    return ad_images_map


def get_partitioned_s3_path(member_id: int, shop_name: str, date: datetime = None, 
                            folder: str = 'excel files') -> str:
    """
    Generate partitioned S3 path for shop data
    Format: opensooq-data/shops/year=YYYY/month=MM/day=DD/{folder}/shopname.xlsx
    
    Args:
        member_id: Shop member ID
        shop_name: Shop name
        date: Date for partitioning (defaults to today)
    
    Returns:
        S3 path string
    """
    if date is None:
        date = datetime.now()
    
    # Clean shop name for filename (remove special characters)
    safe_shop_name = re.sub(r'[^\w\s-]', '', shop_name)
    safe_shop_name = re.sub(r'[-\s]+', '_', safe_shop_name).strip('_')
    
    # Limit filename length
    if len(safe_shop_name) > 50:
        safe_shop_name = safe_shop_name[:50]
    
    # If shop name is empty or only special chars, use member_id
    if not safe_shop_name:
        safe_shop_name = f"shop_{member_id}"
    
    year = date.strftime('%Y')
    month = date.strftime('%m')
    day = date.strftime('%d')
    
    return f"year={year}/month={month}/day={day}/{folder}/{safe_shop_name}.xlsx"


def update_incremental_info(existing_df: Optional[pd.DataFrame], 
                             new_shop_info: Dict) -> pd.DataFrame:
    """
    Update incremental info file with new shop data
    
    Args:
        existing_df: Existing DataFrame (or None if new file)
        new_shop_info: New shop info dictionary
    
    Returns:
        Updated DataFrame
    """
    try:
        new_row_df = pd.DataFrame([new_shop_info])
        
        if existing_df is None or existing_df.empty:
            return new_row_df
        
        # Check if shop already exists
        member_id = new_shop_info.get('member_id')
        if member_id and 'member_id' in existing_df.columns:
            # Update existing row or append new
            existing_mask = existing_df['member_id'] == member_id
            if existing_mask.any():
                # Update existing shop info - use .update() to avoid dtype warnings
                idx = existing_df.index[existing_mask][0]
                for col in new_row_df.columns:
                    existing_df.at[idx, col] = new_row_df[col].values[0]
                return existing_df
        
        # Append new shop using _append (recommended way in newer pandas)
        # Fill missing columns with None to avoid FutureWarning
        for col in existing_df.columns:
            if col not in new_row_df.columns:
                new_row_df[col] = None
        for col in new_row_df.columns:
            if col not in existing_df.columns:
                existing_df[col] = None
        
        return pd.concat([existing_df, new_row_df], ignore_index=True, sort=False)
    
    except Exception as e:
        print(f"Error updating incremental info: {e}")
        return existing_df if existing_df is not None else pd.DataFrame()
