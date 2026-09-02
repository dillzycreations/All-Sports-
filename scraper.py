#!/usr/bin/env python3
"""
Sportzfy Dynamic Scraper - Uses Selenium to handle JavaScript
"""

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import TimeoutException
import json
import re
from datetime import datetime
import time
import os

class SportzfyDynamicScraper:
    def __init__(self):
        self.base_url = "https://sportzfy.my.id"
        self.driver = None
        
    def setup_driver(self):
        """Setup Chrome driver with options"""
        chrome_options = Options()
        chrome_options.add_argument("--headless")  # Run in background
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--window-size=1920,1080")
        chrome_options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36")
        
        self.driver = webdriver.Chrome(options=chrome_options)
        self.driver.set_page_load_timeout(30)
        
    def fetch_page(self):
        """Fetch page with JavaScript rendering"""
        print(f"📡 Fetching: {self.base_url}")
        self.driver.get(self.base_url)
        
        # Wait for match cards to load
        try:
            WebDriverWait(self.driver, 15).until(
                EC.presence_of_element_located((By.CLASS_NAME, "match-card"))
            )
            print("✅ Page loaded with JavaScript content")
            return self.driver.page_source
        except TimeoutException:
            print("⚠️ Timeout waiting for match cards")
            return None

    def extract_match_data(self, html):
        """Extract data from loaded HTML"""
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(html, 'html.parser')
        matches = []
        
        # Find all match cards
        match_cards = soup.find_all('div', class_='match-card')
        print(f"📊 Found {len(match_cards)} match cards")
        
        for card in match_cards:
            match_data = self.parse_card(card)
            if match_data:
                matches.append(match_data)
        
        return matches

    def parse_card(self, card):
        """Parse individual match card"""
        match_data = {
            'title': None,
            'league': None,
            'status': None,
            'sport': None,
            'viewers': None,
            'servers': None,
            'match_url': None
        }
        
        # Get status (handle 'recent' as live)
        status = card.get('data-status')
        match_data['status'] = 'live' if status == 'recent' else status
        match_data['sport'] = card.get('data-sport')
        
        # Title
        title_elem = card.find('div', class_='match-main-title')
        if title_elem:
            link = title_elem.find('a')
            if link:
                match_data['title'] = link.get_text(strip=True)
                match_data['match_url'] = link.get('href')
                if match_data['match_url'] and not match_data['match_url'].startswith('http'):
                    match_data['match_url'] = self.base_url + match_data['match_url']
        
        # League
        league_elem = card.find('div', class_='league-title')
        if league_elem:
            match_data['league'] = league_elem.get_text(strip=True)
        
        # Viewers
        view_text = card.find('span', class_='view-text')
        if view_text:
            match_data['viewers'] = view_text.get_text(strip=True)
        
        # Servers
        server_item = card.find('span', class_='meta-item')
        if server_item:
            server_text = server_item.get_text(strip=True)
            server_match = re.search(r'(\d+)\s*Serv', server_text)
            if server_match:
                match_data['servers'] = server_match.group(1)
        
        return match_data if match_data['title'] else None

    def scrape(self):
        """Main scraping method"""
        print("\n" + "="*60)
        print("🏏 SPORTZFY DYNAMIC SCRAPER")
        print("="*60 + "\n")
        
        try:
            self.setup_driver()
            html = self.fetch_page()
            
            if not html:
                print("❌ Failed to load page")
                return []
            
            matches = self.extract_match_data(html)
            
            if matches:
                # Save to JSON
                os.makedirs('data', exist_ok=True)
                with open('data/matches_dynamic.json', 'w', encoding='utf-8') as f:
                    json.dump(matches, f, indent=2, ensure_ascii=False)
                
                # Display results
                print(f"\n✅ Found {len(matches)} matches\n")
                print("📋 LIVE MATCHES:")
                print("-"*50)
                
                for i, match in enumerate(matches, 1):
                    if match['status'] == 'live':
                        print(f"{i}. {match['title']}")
                        print(f"   League: {match['league']}")
                        print(f"   Viewers: {match['viewers']}")
                        print(f"   URL: {match['match_url']}")
                        print()
            else:
                print("⚠️ No matches found")
            
            return matches
            
        except Exception as e:
            print(f"❌ Error: {e}")
            return []
        finally:
            if self.driver:
                self.driver.quit()

def main():
    scraper = SportzfyDynamicScraper()
    matches = scraper.scrape()
    
    if matches:
        live_matches = [m for m in matches if m['status'] == 'live']
        print(f"\n🎯 Total Live Matches: {len(live_matches)}")
    else:
        print("\n❌ No data scraped.")

if __name__ == "__main__":
    main()
