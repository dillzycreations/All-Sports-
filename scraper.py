#!/usr/bin/env python3
"""
Sportzfy Scraper - Pure Requests + BeautifulSoup
No selenium, no requests-html needed
"""

import requests
from bs4 import BeautifulSoup
import json
import re
from datetime import datetime
import os
import time

class SportzfyScraper:
    def __init__(self):
        self.base_url = "https://sportzfy.my.id"
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.9',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'none',
            'Sec-Fetch-User': '?1',
            'Cache-Control': 'no-cache',
            'Pragma': 'no-cache'
        }
        self.session = requests.Session()
        self.session.headers.update(self.headers)
        
    def fetch_page(self):
        """Fetch the main page"""
        try:
            print(f"📡 Fetching: {self.base_url}")
            response = self.session.get(self.base_url, timeout=30)
            response.raise_for_status()
            print(f"✅ Status: {response.status_code}")
            
            # Check if we got content
            if 'match-card' not in response.text:
                print("⚠️ Match cards not found in response (likely JavaScript rendered)")
                # Try to find matches in the HTML anyway
                print("📝 Attempting to extract from raw HTML...")
            
            return response.text
        except requests.exceptions.RequestException as e:
            print(f"❌ Error: {e}")
            return None

    def extract_matches_direct(self, html):
        """Extract matches directly from HTML using regex and BeautifulSoup"""
        soup = BeautifulSoup(html, 'html.parser')
        matches = []
        
        # Method 1: Find all match cards
        match_cards = soup.find_all('div', class_='match-card')
        print(f"📊 Found {len(match_cards)} match cards using BeautifulSoup")
        
        if match_cards:
            for card in match_cards:
                match = self.parse_card(card)
                if match:
                    matches.append(match)
        else:
            # Method 2: Fallback - Use regex to find matches
            print("⚠️ No match cards found with BeautifulSoup, trying regex fallback...")
            matches = self.extract_with_regex(html)
        
        return matches
    
    def parse_card(self, card):
        """Parse a single match card"""
        match = {
            'title': None,
            'league': None,
            'status': None,
            'sport': None,
            'viewers': None,
            'viewers_type': None,
            'servers': None,
            'match_url': None,
            'match_id': None,
            'thumbnail': None,
            'timestamp': datetime.now().isoformat()
        }
        
        # Get data attributes
        status = card.get('data-status')
        match['status'] = 'live' if status == 'recent' else status
        match['sport'] = card.get('data-sport')
        match['match_id'] = card.get('data-match-id')
        
        # Extract league
        league_div = card.find('div', class_='league-title')
        if league_div:
            match['league'] = league_div.get_text(strip=True)
        
        # Extract title
        title_div = card.find('div', class_='match-main-title')
        if title_div:
            link = title_div.find('a')
            if link:
                match['title'] = link.get_text(strip=True)
                href = link.get('href')
                if href:
                    match['match_url'] = href if href.startswith('http') else self.base_url + href
        
        # Extract thumbnail
        thumb_box = card.find('a', class_='thumb-box')
        if thumb_box:
            img = thumb_box.find('img')
            if img:
                match['thumbnail'] = img.get('src')
        
        # Extract meta info
        meta_row = card.find('div', class_='match-meta-row')
        if meta_row:
            # Servers
            server_item = meta_row.find('span', class_='meta-item')
            if server_item:
                server_text = server_item.get_text(strip=True)
                server_match = re.search(r'(\d+)\s*Serv', server_text)
                if server_match:
                    match['servers'] = server_match.group(1)
            
            # Viewers
            view_pill = meta_row.find('span', class_='view-pill')
            if view_pill:
                view_text = view_pill.get_text(strip=True)
                view_match = re.search(r'(\d+)\s+(Watching|Waiting|Total)', view_text, re.IGNORECASE)
                if view_match:
                    match['viewers'] = view_match.group(1)
                    match['viewers_type'] = view_match.group(2)
                else:
                    # Try to just get numbers
                    num_match = re.search(r'(\d+)', view_text)
                    if num_match:
                        match['viewers'] = num_match.group(1)
        
        return match if match['title'] else None
    
    def extract_with_regex(self, html):
        """Fallback: Extract matches using regex"""
        matches = []
        
        # Pattern to find match cards
        card_pattern = r'<div[^>]*class="[^"]*match-card[^"]*"[^>]*data-status="([^"]*)"[^>]*data-sport="([^"]*)"[^>]*data-match-id="([^"]*)"[^>]*>(.*?)</div>\s*</div>\s*</div>\s*</div>\s*</div>'
        
        # Find all match cards
        import re
        cards = re.findall(card_pattern, html, re.DOTALL)
        
        print(f"🔍 Found {len(cards)} matches with regex")
        
        for status, sport, match_id, card_html in cards:
            match = {
                'title': None,
                'league': None,
                'status': 'live' if status == 'recent' else status,
                'sport': sport,
                'match_id': match_id,
                'viewers': None,
                'timestamp': datetime.now().isoformat()
            }
            
            # Extract title
            title_match = re.search(r'<div class="match-main-title">.*?<a[^>]*>([^<]+)</a>', card_html, re.DOTALL)
            if title_match:
                match['title'] = title_match.group(1).strip()
            
            # Extract league
            league_match = re.search(r'<div class="league-title">([^<]+)</div>', card_html)
            if league_match:
                match['league'] = league_match.group(1).strip()
            
            # Extract viewers
            viewers_match = re.search(r'<span class="view-text">([^<]+)</span>', card_html)
            if viewers_match:
                match['viewers'] = viewers_match.group(1).strip()
            
            if match['title']:
                matches.append(match)
        
        return matches
    
    def scrape(self):
        """Main scraping method"""
        print("\n" + "="*60)
        print("🏏 SPORTZFY SCRAPER (Pure Requests)")
        print("="*60 + "\n")
        
        # Fetch page
        html = self.fetch_page()
        if not html:
            print("❌ Failed to fetch page")
            return []
        
        # Create data directory
        os.makedirs('data', exist_ok=True)
        
        # Save raw HTML for debugging
        with open('data/sportzfy_raw.html', 'w', encoding='utf-8') as f:
            f.write(html)
        print("💾 Raw HTML saved to: data/sportzfy_raw.html")
        
        # Extract matches
        matches = self.extract_matches_direct(html)
        
        if matches:
            # Save to JSON
            output_file = 'data/matches.json'
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump({
                    'timestamp': datetime.now().isoformat(),
                    'total_matches': len(matches),
                    'matches': matches
                }, f, indent=2, ensure_ascii=False)
            
            # Display summary
            print(f"\n✅ Found {len(matches)} match(es)\n")
            
            live_matches = [m for m in matches if m.get('status') == 'live']
            upcoming_matches = [m for m in matches if m.get('status') == 'upcoming']
            completed_matches = [m for m in matches if m.get('status') == 'completed']
            
            print(f"📊 Live: {len(live_matches)}")
            print(f"📊 Upcoming: {len(upcoming_matches)}")
            print(f"📊 Completed: {len(completed_matches)}")
            
            if live_matches:
                print("\n📋 LIVE MATCHES:")
                print("-"*50)
                for i, match in enumerate(live_matches[:10], 1):
                    print(f"{i}. {match.get('title', 'N/A')}")
                    if match.get('league'):
                        print(f"   League: {match['league']}")
                    if match.get('viewers'):
                        print(f"   Viewers: {match['viewers']}")
                    print()
            
            print(f"💾 Data saved to: {output_file}")
        else:
            print("⚠️ No matches found")
            # Try to find match data in the HTML using simpler patterns
            print("\n🔍 Searching for match data in raw HTML...")
            self.debug_html(html)
        
        return matches
    
    def debug_html(self, html):
        """Debug function to analyze HTML content"""
        patterns = [
            ('match-card', r'<div[^>]*match-card'),
            ('league-title', r'league-title'),
            ('match-main-title', r'match-main-title'),
            ('viewers', r'\d+\s+(Watching|Waiting)'),
            ('live status', r'data-status="live"'),
            ('recent status', r'data-status="recent"'),
        ]
        
        print("🔍 Debug Info:")
        for name, pattern in patterns:
            count = len(re.findall(pattern, html))
            print(f"   {name}: {count} occurrences")
        
        # Try to find match titles directly
        titles = re.findall(r'<div class="match-main-title">.*?<a[^>]*>([^<]+)</a>', html, re.DOTALL)
        if titles:
            print(f"\n📝 Found {len(titles)} match titles in HTML:")
            for title in titles[:10]:
                print(f"   • {title.strip()}")

def main():
    scraper = SportzfyScraper()
    matches = scraper.scrape()
    
    if matches:
        live_matches = [m for m in matches if m.get('status') == 'live']
        print(f"\n🎯 Total Live Matches: {len(live_matches)}")
    else:
        print("\n❌ No matches found. Check data/sportzfy_raw.html for debugging.")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n⚠️ Scraping interrupted by user")
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
