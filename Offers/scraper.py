import requests
import json
import os
from datetime import datetime
from urllib.parse import urlencode
import time
import logging

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
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
            # The URL pattern for Next.js data
            api_url = "https://kw.opensooq.com/_next/data/BUILD_ID/ar/العروض.json"
            
            # Try direct page request first
            response = self.session.get(self.BASE_URL)
            response.raise_for_status()
            
            # Extract Next.js data from the page
            if 'window.__NEXT_DATA__' in response.text:
                # Parse the script tag containing __NEXT_DATA__
                start_idx = response.text.find('window.__NEXT_DATA__ = ') + len('window.__NEXT_DATA__ = ')
                end_idx = response.text.find('</script>', start_idx)
                json_data = response.text[start_idx:end_idx].strip()
                
                # Remove trailing semicolon if present
                if json_data.endswith(';'):
                    json_data = json_data[:-1]
                
                data = json.loads(json_data)
                
                # Extract subcategories from pageProps
                if 'pageProps' in data and 'commercialOffersData' in data['pageProps']:
                    facets = data['pageProps']['commercialOffersData'].get('facets', [])
                    
                    subcategories = []
                    for facet in facets:
                        # Skip the "All" category
                        if facet.get('is_selected', False):
                            continue
                        
                        filters = facet.get('filters', {})
                        if 'reporting_name' in filters:
                            subcategories.append({
                                'reporting_name': filters['reporting_name'],
                                'title': facet.get('title', ''),
                                'is_selected': facet.get('is_selected', False)
                            })
                    
                    logger.info(f"Found {len(subcategories)} subcategories")
                    return subcategories
            
            logger.warning("Could not extract subcategories from page")
            return []
            
        except Exception as e:
            logger.error(f"Error fetching subcategories: {e}")
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
            
            # Extract Next.js data
            if 'window.__NEXT_DATA__' in response.text:
                start_idx = response.text.find('window.__NEXT_DATA__ = ') + len('window.__NEXT_DATA__ = ')
                end_idx = response.text.find('</script>', start_idx)
                json_data = response.text[start_idx:end_idx].strip()
                
                if json_data.endswith(';'):
                    json_data = json_data[:-1]
                
                data = json.loads(json_data)
                
                # Extract items and meta from pageProps
                if 'pageProps' in data and 'commercialOffersData' in data['pageProps']:
                    commercial_data = data['pageProps']['commercialOffersData']
                    
                    items = commercial_data.get('items', [])
                    meta = commercial_data.get('meta', {})
                    
                    logger.info(f"Fetched {len(items)} items from page {page}")
                    
                    return {
                        'items': items,
                        'meta': meta
                    }
            
            logger.warning(f"No data found for {reporting_name} page {page}")
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
    scraper = CommercialOffersScraper()
    data = scraper.scrape_all_offers()
    
    # Save to JSON for testing
    output_file = f"commercial_offers_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    
    logger.info(f"Data saved to {output_file}")
