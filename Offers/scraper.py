import requests
import json
import os
from datetime import datetime
from urllib.parse import urlencode, parse_qs, urlparse
import time
import logging
from bs4 import BeautifulSoup
import re

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('commercial_offers_scraper.log', encoding='utf-8')
    ]
)
logger = logging.getLogger(__name__)


class CommercialOffersScraper:
    """Scraper for OpenSooq Commercial Offers"""
    
    BASE_URL = "https://kw.opensooq.com/ar/العروض"
    
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'application/json',
            'Accept-Language': 'ar,en-US;q=0.9,en;q=0.8'
        })
        
    def get_subcategories(self):
        """
        Fetch all subcategories from the main offers page
        Returns: List of subcategory dictionaries with reporting_name and title
        """
        logger.info("Fetching subcategories...")
        
        try:
            # Fetch the page
            response = self.session.get(self.BASE_URL)
            response.raise_for_status()
            
            logger.info(f"Response status: {response.status_code}")
            
            # Method 1: Try to parse __NEXT_DATA__ from script tag
            soup = BeautifulSoup(response.text, 'html.parser')
            next_data_script = soup.find('script', {'id': '__NEXT_DATA__', 'type': 'application/json'})
            
            if next_data_script and next_data_script.string:
                logger.info("Found __NEXT_DATA__ script tag")
                try:
                    data = json.loads(next_data_script.string)
                    logger.info("Successfully parsed __NEXT_DATA__")
                    
                    # Check if it's in props
                    if 'props' in data and 'pageProps' not in data:
                        # The structure might be different
                        logger.info(f"Data keys: {list(data.keys())}")
                    
                    # Navigate through the data structure
                    # Based on the structure, data seems to be at root level
                    # Since we can see categories in the HTML, let's parse them directly
                    
                except json.JSONDecodeError as e:
                    logger.error(f"JSON decode error: {e}")
            
            # Method 2: Parse HTML directly for category links
            logger.info("Parsing HTML for category links...")
            category_links = soup.find_all('a', href=re.compile(r'reporting_name='))
            
            logger.info(f"Found {len(category_links)} category links")
            
            subcategories = []
            seen_names = set()
            
            for link in category_links:
                href = link.get('href', '')
                title = link.get_text(strip=True)
                
                # Parse the URL to extract reporting_name
                parsed = urlparse(href)
                params = parse_qs(parsed.query)
                
                if 'reporting_name' in params:
                    reporting_name = params['reporting_name'][0]
                    
                    # Avoid duplicates
                    if reporting_name not in seen_names:
                        seen_names.add(reporting_name)
                        subcategories.append({
                            'reporting_name': reporting_name,
                            'title': title,
                            'is_selected': False
                        })
                        logger.debug(f"Added subcategory: {title} ({reporting_name})")
            
            logger.info(f"Found {len(subcategories)} unique subcategories")
            return subcategories
            
        except Exception as e:
            logger.error(f"Error fetching subcategories: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return []
    
    def get_offers_by_category(self, reporting_name, page=1):
        """
        Fetch offers for a specific category
        
        Args:
            reporting_name: The category reporting name (e.g., 'CarRental')
            page: Page number (default: 1)
            
        Returns:
            Dictionary containing items and meta information
        """
        logger.info(f"Fetching offers for category: {reporting_name}, page: {page}")
        
        try:
            # Build the URL
            url = self.BASE_URL
            params = {'reporting_name': reporting_name}
            if page > 1:
                params['page'] = page
            
            # Make request to get the page
            response = self.session.get(url, params=params)
            response.raise_for_status()
            
            # Parse with BeautifulSoup
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Try to extract from __NEXT_DATA__ script tag
            next_data_script = soup.find('script', {'id': '__NEXT_DATA__', 'type': 'application/json'})
            
            if next_data_script and next_data_script.string:
                try:
                    data = json.loads(next_data_script.string)
                    logger.debug("Successfully parsed __NEXT_DATA__")
                    
                    # The data structure can vary, try multiple paths
                    commercial_data = None
                    
                    # Try path 1: props.pageProps.commercialOffersData
                    if 'props' in data and 'pageProps' in data['props']:
                        commercial_data = data['props']['pageProps'].get('commercialOffersData')
                    
                    # Try path 2: pageProps.commercialOffersData (direct)
                    elif 'pageProps' in data:
                        commercial_data = data['pageProps'].get('commercialOffersData')
                    
                    if commercial_data:
                        items = commercial_data.get('items', [])
                        meta = commercial_data.get('meta', {})
                        
                        logger.info(f"Fetched {len(items)} items from page {page}")
                        
                        return {
                            'items': items,
                            'meta': meta
                        }
                    else:
                        logger.warning(f"commercialOffersData not found in __NEXT_DATA__")
                        
                except json.JSONDecodeError as e:
                    logger.error(f"JSON decode error: {e}")
            
            logger.warning(f"No data found for {reporting_name} page {page}")
            return {'items': [], 'meta': {}}
            return {'items': [], 'meta': {}}
            
        except Exception as e:
            logger.error(f"Error fetching offers for {reporting_name} page {page}: {e}")
            return {'items': [], 'meta': {}}
    
    def get_all_offers_by_category(self, reporting_name, category_title):
        """
        Fetch all offers for a category across all pages
        
        Args:
            reporting_name: The category reporting name
            category_title: The category title in Arabic
            
        Returns:
            List of all items for the category
        """
        logger.info(f"Fetching all offers for: {category_title} ({reporting_name})")
        
        all_items = []
        page = 1
        
        while True:
            result = self.get_offers_by_category(reporting_name, page)
            items = result.get('items', [])
            meta = result.get('meta', {})
            
            if not items:
                break
            
            all_items.extend(items)
            
            # Check if there are more pages
            current_page = meta.get('currentPage', page)
            page_count = meta.get('pageCount', 1)
            
            logger.info(f"Page {current_page}/{page_count} - Total items collected: {len(all_items)}")
            
            if current_page >= page_count:
                break
            
            page += 1
            time.sleep(1)  # Be respectful to the server
        
        logger.info(f"Total items for {category_title}: {len(all_items)}")
        return all_items
    
    def scrape_all_offers(self):
        """
        Scrape all offers from all subcategories
        
        Returns:
            Dictionary with subcategory names as keys and items as values
        """
        logger.info("Starting to scrape all commercial offers...")
        
        # Get all subcategories
        subcategories = self.get_subcategories()
        
        if not subcategories:
            logger.error("No subcategories found. Exiting.")
            return {}
        
        all_data = {}
        
        for subcategory in subcategories:
            reporting_name = subcategory['reporting_name']
            title = subcategory['title']
            
            # Fetch all offers for this category
            items = self.get_all_offers_by_category(reporting_name, title)
            
            if items:
                all_data[reporting_name] = {
                    'title': title,
                    'items': items
                }
            
            time.sleep(2)  # Be respectful between categories
        
        logger.info(f"Scraping complete. Collected data for {len(all_data)} categories")
        return all_data


if __name__ == "__main__":
    import sys
    
    scraper = CommercialOffersScraper()
    
    # Debug mode: save HTML
    if len(sys.argv) > 1 and sys.argv[1] == '--debug':
        logger.info("Debug mode: Fetching page HTML...")
        response = scraper.session.get(scraper.BASE_URL)
        
        html_file = f"commercial_offers_page_{datetime.now().strftime('%Y%m%d_%H%M%S')}.html"
        with open(html_file, 'w', encoding='utf-8') as f:
            f.write(response.text)
        logger.info(f"HTML saved to {html_file}")
        
        # Also save just the __NEXT_DATA__ if it exists
        if 'window.__NEXT_DATA__' in response.text:
            start_idx = response.text.find('window.__NEXT_DATA__ = ') + len('window.__NEXT_DATA__ = ')
            end_idx = response.text.find('</script>', start_idx)
            json_data = response.text[start_idx:end_idx].strip()
            if json_data.endswith(';'):
                json_data = json_data[:-1]
            
            json_file = f"commercial_offers_data_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            with open(json_file, 'w', encoding='utf-8') as f:
                f.write(json_data)
            logger.info(f"__NEXT_DATA__ saved to {json_file}")
        
        sys.exit(0)
    
    # Normal mode
    data = scraper.scrape_all_offers()
    
    # Save to JSON for testing
    output_file = f"commercial_offers_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    
    logger.info(f"Data saved to {output_file}")
