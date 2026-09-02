#!/usr/bin/env python3
"""
Sportzfy Cricket Scraper - Working Version
Extracts match data from the HTML structure
"""

import requests
from bs4 import BeautifulSoup
import json
import re
from datetime import datetime
import os

class SportzfyScraper:
    def __init__(self):
        self.base_url = "https://sportzfy.my.id"
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.6099.230 Mobile Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
        }
        self.session = requests.Session()
        self.session.headers.update(self.headers)
        
    def fetch_page(self):
        """Fetch the main page"""
        try:
            print(f"📡 Fetching: {self.base_url}")
            response = self.session.get(self.base_url, timeout=15)
            response.raise_for_status()
            print(f"✅ Status: {response.status_code}")
            return response.text
        except requests.exceptions.RequestException as e:
            print(f"❌ Error: {e}")
            return None

    def extract_match_data(self, html):
        """Extract match information from HTML"""
        soup = BeautifulSoup(html, 'html.parser')
        matches = []
        
        # Find all match cards - direct class selector
        match_cards = soup.select('div.match-card')
        
        if not match_cards:
            print("⚠️ No match cards found. Trying alternative selectors...")
            # Try by data attributes
            match_cards = soup.find_all('div', attrs={'data-match-id': True})
        
        if not match_cards:
            print("⚠️ Still no matches. Checking if HTML is loaded...")
            # Check if we have any content
            if soup.find('div', class_='match-grid'):
                print("✅ Found match-grid container but no cards")
            return []
        
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
            'teams': None,
            'league': None,
            'sport': None,
            'status': None,
            'runtime': None,
            'viewers': None,
            'viewers_type': None,
            'servers': None,
            'date': None,
            'time': None,
            'match_url': None,
            'thumbnail': None,
            'match_id': None,
            'timestamp': datetime.now().isoformat()
        }
        
        # Get data attributes
        match_data['match_id'] = card.get('data-match-id')
        match_data['status'] = card.get('data-status')
        match_data['sport'] = card.get('data-sport')
        
        # Extract league title
        league_div = card.find('div', class_='league-title')
        if league_div:
            match_data['league'] = league_div.get_text(strip=True)
        
        # Extract match title/teams
        title_div = card.find('div', class_='match-main-title')
        if title_div:
            link = title_div.find('a')
            if link:
                match_data['title'] = link.get_text(strip=True)
                match_data['teams'] = match_data['title']
                href = link.get('href')
                if href and href != 'javascript:void(0)':
                    if href.startswith('/'):
                        match_data['match_url'] = self.base_url + href
                    elif href.startswith('http'):
                        match_data['match_url'] = href
        
        # Extract thumbnail
        thumb_box = card.find('a', class_='thumb-box')
        if thumb_box:
            img = thumb_box.find('img')
            if img:
                match_data['thumbnail'] = img.get('src')
        
        # Extract meta info
        meta_row = card.find('div', class_='match-meta-row')
        if meta_row:
            # Extract servers
            server_item = meta_row.find('span', class_='meta-item')
            if server_item:
                server_text = server_item.get_text(strip=True)
                server_match = re.search(r'(\d+)\s*Serv', server_text)
                if server_match:
                    match_data['servers'] = server_match.group(1)
            
            # Extract viewers
            view_pill = meta_row.find('span', class_='view-pill')
            if view_pill:
                view_text = view_pill.get_text(strip=True)
                view_match = re.search(r'(\d+)\s+(Watching|Waiting|Total)', view_text)
                if view_match:
                    match_data['viewers'] = view_match.group(1)
                    match_data['viewers_type'] = view_match.group(2)
                else:
                    # Just get the number
                    num_match = re.search(r'(\d+)', view_text)
                    if num_match:
                        match_data['viewers'] = num_match.group(1)
            
            # Extract date and time
            time_items = meta_row.find_all('span', class_='meta-item')
            for item in time_items:
                item_text = item.get_text(strip=True)
                # Date
                date_match = re.search(r'(\d{1,2}\s+[A-Za-z]{3,}\s*,\s*\d{4})', item_text)
                if date_match:
                    match_data['date'] = date_match.group(1).strip()
                # Time
                time_match = re.search(r'(\d{1,2}:\d{2}\s*(?:AM|PM))', item_text, re.IGNORECASE)
                if time_match:
                    match_data['time'] = time_match.group(1).strip()
        
        # Extract runtime for live matches
        if match_data['status'] == 'live':
            live_boxes = card.find_all('div', class_='header-cd-box')
            if len(live_boxes) >= 3:
                hours = live_boxes[0].find('div', class_='header-cd-num')
                mins = live_boxes[1].find('div', class_='header-cd-num')
                secs = live_boxes[2].find('div', class_='header-cd-num')
                if hours and mins and secs:
                    h = hours.get_text(strip=True)
                    m = mins.get_text(strip=True)
                    s = secs.get_text(strip=True)
                    match_data['runtime'] = f"{h}h {m}m {s}s"
        
        # For upcoming matches, get countdown
        if match_data['status'] == 'upcoming':
            overlay = card.find('div', class_='thumb-countdown-overlay')
            if overlay:
                cd_boxes = overlay.find_all('div', class_='cd-box')
                if len(cd_boxes) >= 3:
                    hours = cd_boxes[0].find('div', class_='cd-num')
                    mins = cd_boxes[1].find('div', class_='cd-num')
                    secs = cd_boxes[2].find('div', class_='cd-num')
                    if hours and mins and secs:
                        h = hours.get_text(strip=True)
                        m = mins.get_text(strip=True)
                        s = secs.get_text(strip=True)
                        match_data['runtime'] = f"{h}h {m}m {s}s"
        
        # Check if we have at least some data
        if match_data['title'] or match_data['league'] or match_data['match_id']:
            return match_data
        
        return None

    def scrape(self):
        """Main scraping method"""
        print("\n" + "="*60)
        print("🏏 SPORTZFY SCRAPER")
        print("="*60 + "\n")
        
        html = self.fetch_page()
        if not html:
            print("❌ Failed to fetch page")
            return []
        
        # Save raw HTML
        os.makedirs('data', exist_ok=True)
        with open('data/sportzfy_raw.html', 'w', encoding='utf-8') as f:
            f.write(html)
        print("💾 Raw HTML saved to: data/sportzfy_raw.html")
        
        # Extract matches
        matches = self.extract_match_data(html)
        
        if matches:
            print(f"\n✅ Found {len(matches)} match(es)\n")
            self.display_matches(matches)
            self.save_data(matches)
        else:
            print("⚠️ No matches found.")
            # Try to parse from the HTML directly using regex as fallback
            matches = self.fallback_extract(html)
            if matches:
                print(f"\n✅ Found {len(matches)} match(es) using fallback\n")
                self.display_matches(matches)
                self.save_data(matches)
            else:
                self.save_empty_data()
        
        return matches

    def fallback_extract(self, html):
        """Fallback extraction using regex"""
        matches = []
        
        # Find all match cards in the HTML string
        card_pattern = r'<div class="match-card"[^>]*data-status="([^"]*)"[^>]*data-sport="([^"]*)"[^>]*data-match-id="([^"]*)"[^>]*>'
        cards = re.findall(card_pattern, html)
        
        for status, sport, match_id in cards:
            match_data = {
                'match_id': match_id,
                'status': status,
                'sport': sport,
                'title': None,
                'teams': None,
                'league': None,
                'runtime': None,
                'viewers': None,
                'servers': None,
                'date': None,
                'time': None,
                'timestamp': datetime.now().isoformat()
            }
            
            # Find the league title
            league_pattern = r'<div class="league-title">([^<]+)</div>'
            league_matches = re.findall(league_pattern, html)
            if league_matches:
                match_data['league'] = league_matches[0].strip()
            
            # Find team names
            title_pattern = r'<div class="match-main-title">\s*<a[^>]*>([^<]+)</a>'
            title_matches = re.findall(title_pattern, html)
            if title_matches:
                match_data['title'] = title_matches[0].strip()
                match_data['teams'] = match_data['title']
            
            # Find servers
            server_pattern = r'(\d+)\s*Serv'
            server_match = re.search(server_pattern, html)
            if server_match:
                match_data['servers'] = server_match.group(1)
            
            # Find viewers
            viewer_pattern = r'(\d+)\s+(Watching|Waiting|Total)'
            viewer_match = re.search(viewer_pattern, html)
            if viewer_match:
                match_data['viewers'] = viewer_match.group(1)
                match_data['viewers_type'] = viewer_match.group(2)
            
            # Find date
            date_pattern = r'(\d{1,2}\s+[A-Za-z]{3,}\s*,\s*\d{4})'
            date_match = re.search(date_pattern, html)
            if date_match:
                match_data['date'] = date_match.group(1).strip()
            
            # Find time
            time_pattern = r'(\d{1,2}:\d{2}\s*(?:AM|PM))'
            time_match = re.search(time_pattern, html, re.IGNORECASE)
            if time_match:
                match_data['time'] = time_match.group(1).strip()
            
            # Find runtime for live matches
            if status == 'live':
                runtime_pattern = r'(\d+)\s*HOURS?\s*(\d+)\s*MINS?\s*(\d+)\s*SECS?'
                runtime_match = re.search(runtime_pattern, html, re.IGNORECASE)
                if runtime_match:
                    h, m, s = runtime_match.groups()
                    match_data['runtime'] = f"{h}h {m}m {s}s"
            
            if match_data['title'] or match_data['match_id']:
                matches.append(match_data)
        
        # Remove duplicates
        unique_matches = []
        seen_ids = set()
        for match in matches:
            if match['match_id'] not in seen_ids:
                seen_ids.add(match['match_id'])
                unique_matches.append(match)
        
        return unique_matches

    def display_matches(self, matches):
        """Display matches in formatted output"""
        for i, match in enumerate(matches, 1):
            print(f"📌 MATCH #{i}")
            print(f"   🏷️  Title: {match.get('title', 'N/A')}")
            print(f"   ⚔️  Teams: {match.get('teams', 'N/A')}")
            print(f"   🏆  League: {match.get('league', 'N/A')}")
            print(f"   📡  Status: {match.get('status', 'N/A').upper() if match.get('status') else 'N/A'}")
            print(f"   ⏱️  Runtime: {match.get('runtime', 'N/A')}")
            print(f"   👁️  Viewers: {match.get('viewers', 'N/A')} {match.get('viewers_type', '')}")
            print(f"   🌐  Servers: {match.get('servers', 'N/A')}")
            print(f"   📅  Date: {match.get('date', 'N/A')}")
            print(f"   🕐  Time: {match.get('time', 'N/A')}")
            print(f"   🏏  Sport: {match.get('sport', 'N/A')}")
            print(f"   🆔  Match ID: {match.get('match_id', 'N/A')}")
            if match.get('match_url'):
                print(f"   🔗  URL: {match['match_url']}")
            print("-"*50)

    def save_data(self, matches):
        """Save data to files"""
        os.makedirs('data', exist_ok=True)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        summary = {
            'timestamp': datetime.now().isoformat(),
            'total_matches': len(matches),
            'live_count': sum(1 for m in matches if m.get('status') == 'live'),
            'upcoming_count': sum(1 for m in matches if m.get('status') == 'upcoming'),
            'completed_count': sum(1 for m in matches if m.get('status') == 'completed'),
            'matches': matches
        }
        
        # Save main JSON
        json_file = 'data/matches.json'
        with open(json_file, 'w', encoding='utf-8') as f:
            json.dump(summary, f, indent=2, ensure_ascii=False)
        print(f"💾 JSON saved to: {json_file}")
        
        # Save historical JSON
        history_file = f'data/matches_{timestamp}.json'
        with open(history_file, 'w', encoding='utf-8') as f:
            json.dump(summary, f, indent=2, ensure_ascii=False)
        print(f"💾 Historical JSON saved to: {history_file}")

    def save_empty_data(self):
        """Save empty data placeholder"""
        os.makedirs('data', exist_ok=True)
        
        empty_data = {
            'timestamp': datetime.now().isoformat(),
            'total_matches': 0,
            'matches': [],
            'message': 'No matches found. Website might be down or structure changed.'
        }
        
        with open('data/matches.json', 'w', encoding='utf-8') as f:
            json.dump(empty_data, f, indent=2, ensure_ascii=False)
        print("💾 Empty data placeholder saved")

def main():
    scraper = SportzfyScraper()
    matches = scraper.scrape()
    
    if matches:
        print(f"\n✅ Scraping complete! Found {len(matches)} matches.")
        print("📁 All data saved in 'data/' directory")
    else:
        print("\n❌ No data scraped.")
        print("💡 Check data/sportzfy_raw.html for the raw HTML")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n⚠️ Scraping interrupted by user")
    except Exception as e:
        print(f"\n❌ Error: {e}")
