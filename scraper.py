#!/usr/bin/env python3
"""
Sportzfy Scraper - Using requests-html for JavaScript rendering
"""

import os
import json
import re
from datetime import datetime
from requests_html import HTMLSession
from bs4 import BeautifulSoup
import time

class SportzfyScraper:
    def __init__(self):
        self.base_url = "https://sportzfy.my.id"
        self.session = HTMLSession()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.9',
        })
        
    def fetch_page_with_render(self):
        """Fetch page with JavaScript rendering"""
        try:
            print(f"📡 Fetching: {self.base_url}")
            response = self.session.get(self.base_url, timeout=30)
            
            # Render JavaScript (this handles dynamic content)
            print("⏳ Rendering JavaScript...")
            response.html.render(timeout=20, sleep=3)
            
            print("✅ Page rendered successfully")
            return response.html.html
        except Exception as e:
            print(f"❌ Error rendering page: {e}")
            # Fallback: try without rendering
            try:
                print("🔄 Attempting fallback without rendering...")
                response = self.session.get(self.base_url, timeout=30)
                return response.text
            except:
                return None
    
    def extract_match_data(self, html):
        """Extract match data from HTML"""
        soup = BeautifulSoup(html, 'html.parser')
        matches = []
        
        # Find all match cards
        match_cards = soup.find_all('div', class_='match-card')
        print(f"📊 Found {len(match_cards)} match cards")
        
        for card in match_cards:
            match_data = self.parse_match_card(card)
            if match_data:
                matches.append(match_data)
        
        return matches
    
    def parse_match_card(self, card):
        """Parse individual match card"""
        match_data = {
            'title': None,
            'league': None,
            'status': None,
            'sport': None,
            'viewers': None,
            'viewers_type': None,
            'servers': None,
            'match_url': None,
            'match_id': None,
            'timestamp': datetime.now().isoformat()
        }
        
        # Get data attributes
        status = card.get('data-status')
        match_data['status'] = 'live' if status == 'recent' else status
        match_data['sport'] = card.get('data-sport')
        match_data['match_id'] = card.get('data-match-id')
        
        # Extract league
        league_div = card.find('div', class_='league-title')
        if league_div:
            match_data['league'] = league_div.get_text(strip=True)
        
        # Extract title
        title_div = card.find('div', class_='match-main-title')
        if title_div:
            link = title_div.find('a')
            if link:
                match_data['title'] = link.get_text(strip=True)
                match_data['match_url'] = link.get('href')
                if match_data['match_url'] and not match_data['match_url'].startswith('http'):
                    match_data['match_url'] = self.base_url + match_data['match_url']
        
        # Extract viewers from meta row
        meta_row = card.find('div', class_='match-meta-row')
        if meta_row:
            # Viewers
            view_pill = meta_row.find('span', class_='view-pill')
            if view_pill:
                view_text = view_pill.get_text(strip=True)
                view_match = re.search(r'(\d+)\s+(Watching|Waiting|Total)', view_text, re.IGNORECASE)
                if view_match:
                    match_data['viewers'] = view_match.group(1)
                    match_data['viewers_type'] = view_match.group(2)
            
            # Servers
            server_item = meta_row.find('span', class_='meta-item')
            if server_item:
                server_text = server_item.get_text(strip=True)
                server_match = re.search(r'(\d+)\s*Serv', server_text)
                if server_match:
                    match_data['servers'] = server_match.group(1)
        
        return match_data if match_data['title'] else None
    
    def scrape(self):
        """Main scraping method"""
        print("\n" + "="*60)
        print("🏏 SPORTZFY SCRAPER (requests-html)")
        print("="*60 + "\n")
        
        # Fetch page with JavaScript rendering
        html = self.fetch_page_with_render()
        if not html:
            print("❌ Failed to fetch page")
            return []
        
        # Save raw HTML for debugging
        os.makedirs('data', exist_ok=True)
        with open('data/sportzfy_rendered.html', 'w', encoding='utf-8') as f:
            f.write(html)
        
        # Extract matches
        matches = self.extract_match_data(html)
        
        if matches:
            # Save to JSON
            with open('data/matches.json', 'w', encoding='utf-8') as f:
                json.dump(matches, f, indent=2, ensure_ascii=False)
            
            # Display summary
            print(f"\n✅ Found {len(matches)} match(es)\n")
            
            live_matches = [m for m in matches if m['status'] == 'live']
            upcoming_matches = [m for m in matches if m['status'] == 'upcoming']
            completed_matches = [m for m in matches if m['status'] == 'completed']
            
            print(f"📊 Live: {len(live_matches)}")
            print(f"📊 Upcoming: {len(upcoming_matches)}")
            print(f"📊 Completed: {len(completed_matches)}")
            
            print("\n📋 LIVE MATCHES:")
            print("-"*50)
            for i, match in enumerate(live_matches, 1):
                print(f"{i}. {match['title']}")
                print(f"   League: {match['league']}")
                print(f"   Viewers: {match['viewers']} {match['viewers_type']}")
                print(f"   Sport: {match['sport']}")
                print()
            
            print(f"💾 Data saved to: data/matches.json")
        else:
            print("⚠️ No matches found. Trying alternative method...")
            # Try parsing from the raw HTML directly
            matches = self.parse_raw_html(html)
            if matches:
                print(f"✅ Found {len(matches)} matches using fallback method")
        
        return matches
    
    def parse_raw_html(self, html):
        """Fallback: Parse matches directly from raw HTML"""
        matches = []
        
        # Look for match patterns in the HTML
        patterns = [
            r'<div[^>]*data-status="([^"]*)"[^>]*>',
            r'<div class="match-main-title">.*?<a[^>]*>([^<]+)</a>',
            r'<div class="league-title">([^<]+)</div>',
            r'(\d+)\s+(Watching|Waiting|Total)',
        ]
        
        # Simple parsing without BeautifulSoup
        soup = BeautifulSoup(html, 'html.parser')
        match_cards = soup.find_all('div', class_='match-card')
        
        for card in match_cards:
            match = {
                'title': None,
                'league': None,
                'status': None,
                'viewers': None
            }
            
            # Get status
            status = card.get('data-status')
            match['status'] = 'live' if status == 'recent' else status
            
            # Get title
            title_elem = card.find('div', class_='match-main-title')
            if title_elem:
                link = title_elem.find('a')
                if link:
                    match['title'] = link.get_text(strip=True)
            
            # Get league
            league_elem = card.find('div', class_='league-title')
            if league_elem:
                match['league'] = league_elem.get_text(strip=True)
            
            # Get viewers
            view_text = card.find('span', class_='view-text')
            if view_text:
                match['viewers'] = view_text.get_text(strip=True)
            
            if match['title']:
                matches.append(match)
        
        return matches

def main():
    scraper = SportzfyScraper()
    matches = scraper.scrape()
    
    if matches:
        live_matches = [m for m in matches if m.get('status') == 'live']
        print(f"\n🎯 Total Live Matches: {len(live_matches)}")
        print(f"📁 Output saved to: data/matches.json")
    else:
        print("\n❌ No matches found")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n⚠️ Scraping interrupted by user")
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
