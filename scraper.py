#!/usr/bin/env python3
"""
Sportzfy Full Scraper - Fetches all live matches with server URLs
"""

import requests
from bs4 import BeautifulSoup
import json
import re
import base64
from datetime import datetime
import os
import time
from urllib.parse import urljoin

class SportzfyFullScraper:
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
        
    def fetch_page(self, url, retries=3):
        """Fetch a page with retries"""
        for attempt in range(retries):
            try:
                print(f"📡 Fetching: {url} (Attempt {attempt+1}/{retries})")
                response = self.session.get(url, timeout=30)
                response.raise_for_status()
                print(f"✅ Status: {response.status_code}")
                return response.text
            except requests.exceptions.RequestException as e:
                print(f"❌ Error fetching {url}: {e}")
                if attempt < retries - 1:
                    time.sleep(2)
        return None

    def decode_server_url(self, encoded_string):
        """Decode server URL using multiple methods"""
        try:
            # Method 1: Base64 decode
            base64_decoded = base64.b64decode(encoded_string).decode('utf-8')
            
            # Method 2: ROT13 decode
            import codecs
            rot13_decoded = codecs.decode(base64_decoded, 'rot_13')
            
            # Clean up the URL
            if rot13_decoded.startswith('http'):
                return rot13_decoded
            else:
                # Try to find URL in the decoded string
                url_match = re.search(r'(https?://[^\s"\']+)', rot13_decoded)
                if url_match:
                    return url_match.group(1)
                    
        except Exception as e:
            # Try alternative method
            try:
                # Just base64 decode
                decoded = base64.b64decode(encoded_string).decode('utf-8')
                url_match = re.search(r'(https?://[^\s"\']+)', decoded)
                if url_match:
                    return url_match.group(1)
            except:
                pass
        
        return None

    def extract_server_urls(self, html):
        """Extract server URLs from match page"""
        soup = BeautifulSoup(html, 'html.parser')
        server_urls = []
        
        # Method 1: Look for encServerList in JavaScript
        scripts = soup.find_all('script')
        for script in scripts:
            if script.string:
                # Look for encServerList array
                match = re.search(r'const\s+encServerList\s*=\s*\[([^\]]+)\]', script.string, re.DOTALL)
                if match:
                    encoded_strings = re.findall(r'"([^"]+)"', match.group(1))
                    print(f"🔍 Found {len(encoded_strings)} encoded server URLs")
                    for enc in encoded_strings:
                        decoded = self.decode_server_url(enc)
                        if decoded and decoded not in server_urls:
                            server_urls.append(decoded)
                            print(f"   ✅ Decoded: {decoded[:50]}...")
                    break
                
                # Method 2: Look for serverList array
                match = re.search(r'const\s+serverList\s*=\s*\[([^\]]+)\]', script.string, re.DOTALL)
                if match:
                    urls = re.findall(r'"([^"]+)"', match.group(1))
                    for url in urls:
                        if url.startswith('http') and url not in server_urls:
                            server_urls.append(url)
                            print(f"🔍 Found server URL: {url[:50]}...")
        
        # Method 3: Look for stream URLs in the page
        if not server_urls:
            stream_patterns = [
                r'(https?://[^\s"\']+\.m3u8[^\s"\']*)',
                r'(https?://[^\s"\']+\.mpd[^\s"\']*)',
                r'(https?://[^\s"\']+stream[^\s"\']+)',
                r'(https?://[^\s"\']+\.mp4[^\s"\']*)',
                r'(https?://[^\s"\']+\.ts[^\s"\']*)',
            ]
            for pattern in stream_patterns:
                matches = re.findall(pattern, html)
                for url in matches:
                    if url not in server_urls:
                        server_urls.append(url)
                        print(f"🔍 Found stream URL: {url[:50]}...")
        
        return server_urls

    def extract_match_data(self, html):
        """Extract all match data from HTML"""
        soup = BeautifulSoup(html, 'html.parser')
        matches = []
        match_cards = soup.find_all('div', class_='match-card')
        
        print(f"📊 Found {len(match_cards)} total match cards")
        
        for card in match_cards:
            match_data = self.parse_match_card(card)
            if match_data:
                matches.append(match_data)
        
        return matches

    def parse_match_card(self, card):
        """Parse individual match card - FIXED for 'recent' status"""
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
            'server_urls': [],
            'last_updated': datetime.now().isoformat()
        }
        
        # Get data attributes - FIX: Convert 'recent' to 'live'
        status = card.get('data-status')
        if status == 'recent':
            match_data['status'] = 'live'  # Important fix!
        else:
            match_data['status'] = status
            
        match_data['match_id'] = card.get('data-match-id')
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
                view_match = re.search(r'(\d+)\s+(Watching|Waiting|Total)', view_text, re.IGNORECASE)
                if view_match:
                    match_data['viewers'] = view_match.group(1)
                    match_data['viewers_type'] = view_match.group(2)
                else:
                    num_match = re.search(r'(\d+)', view_text)
                    if num_match:
                        match_data['viewers'] = num_match.group(1)
            
            # Extract date and time
            time_items = meta_row.find_all('span', class_='meta-item')
            for item in time_items:
                item_text = item.get_text(strip=True)
                date_match = re.search(r'(\d{1,2}\s+[A-Za-z]{3,}\s*,\s*\d{4})', item_text)
                if date_match:
                    match_data['date'] = date_match.group(1).strip()
                time_match = re.search(r'(\d{1,2}:\d{2}\s*(?:AM|PM))', item_text, re.IGNORECASE)
                if time_match:
                    match_data['time'] = time_match.group(1).strip()
        
        # Extract runtime for live matches
        if match_data['status'] == 'live':
            # Look for header runtime boxes
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
        
        # Construct match URL
        if match_data['title'] and match_data['match_id']:
            match_data['match_url'] = self.construct_match_url(
                match_data['title'], 
                match_data['match_id']
            )
        
        # If match is live, fetch server URLs
        if match_data['status'] == 'live' and match_data.get('match_url'):
            print(f"\n🔍 Fetching server URLs for: {match_data['title'][:40]}...")
            match_html = self.fetch_page(match_data['match_url'])
            if match_html:
                server_urls = self.extract_server_urls(match_html)
                if server_urls:
                    match_data['server_urls'] = server_urls
                    print(f"✅ Found {len(server_urls)} server URLs")
                else:
                    print(f"⚠️ No server URLs found")
            time.sleep(1)  # Rate limiting
        
        return match_data if match_data['title'] or match_data['league'] else None

    def construct_match_url(self, title, match_id):
        """Construct match URL from title and ID"""
        if not title or not match_id:
            return None
        
        # Clean title for URL
        url_title = title.lower()
        url_title = re.sub(r'[^a-z0-9\s-]', '', url_title)
        url_title = re.sub(r'\s+', '-', url_title)
        url_title = re.sub(r'-+', '-', url_title)
        url_title = url_title.strip('-')
        
        return f"{self.base_url}/live/{url_title}-{match_id}"

    def load_existing_data(self):
        """Load existing matches.json if it exists"""
        json_file = 'data/matches.json'
        if os.path.exists(json_file):
            try:
                with open(json_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    print(f"📂 Loaded existing data with {data.get('total_matches', 0)} matches")
                    return data
            except Exception as e:
                print(f"⚠️ Could not load existing data: {e}")
        return None

    def update_data(self, existing_data, new_matches):
        """Update existing data with new matches"""
        if not existing_data:
            return {
                'timestamp': datetime.now().isoformat(),
                'total_matches': len(new_matches),
                'live_count': sum(1 for m in new_matches if m.get('status') == 'live'),
                'upcoming_count': sum(1 for m in new_matches if m.get('status') == 'upcoming'),
                'completed_count': sum(1 for m in new_matches if m.get('status') == 'completed'),
                'recent_count': sum(1 for m in new_matches if m.get('status') == 'recent'),
                'matches': new_matches
            }
        
        # Create lookup by match_id
        existing_matches = {m.get('match_id'): m for m in existing_data.get('matches', []) if m.get('match_id')}
        
        # Update existing matches with new data
        for new_match in new_matches:
            match_id = new_match.get('match_id')
            if match_id and match_id in existing_matches:
                # Preserve server_urls if new one doesn't have them
                if not new_match.get('server_urls') and existing_matches[match_id].get('server_urls'):
                    new_match['server_urls'] = existing_matches[match_id]['server_urls']
                # Update timestamp
                new_match['last_updated'] = datetime.now().isoformat()
                existing_matches[match_id] = new_match
            elif match_id:
                existing_matches[match_id] = new_match
        
        # Convert back to list
        updated_matches = list(existing_matches.values())
        
        return {
            'timestamp': datetime.now().isoformat(),
            'total_matches': len(updated_matches),
            'live_count': sum(1 for m in updated_matches if m.get('status') == 'live'),
            'upcoming_count': sum(1 for m in updated_matches if m.get('status') == 'upcoming'),
            'completed_count': sum(1 for m in updated_matches if m.get('status') == 'completed'),
            'recent_count': sum(1 for m in updated_matches if m.get('status') == 'recent'),
            'matches': updated_matches
        }

    def scrape(self, fetch_servers=True):
        """Main scraping method"""
        print("\n" + "="*60)
        print("🏏 SPORTZFY FULL SCRAPER")
        print("="*60 + "\n")
        
        # Fetch main page
        html = self.fetch_page(self.base_url)
        if not html:
            print("❌ Failed to fetch page")
            return []
        
        # Create data directory
        os.makedirs('data', exist_ok=True)
        
        # Save raw HTML for debugging
        with open('data/sportzfy_raw.html', 'w', encoding='utf-8') as f:
            f.write(html)
        
        # Extract matches
        print("\n🔍 Extracting match data...")
        matches = self.extract_match_data(html)
        
        if matches:
            print(f"\n✅ Found {len(matches)} match(es)\n")
            
            # Load existing data
            existing_data = self.load_existing_data()
            
            # Update with new data
            updated_data = self.update_data(existing_data, matches)
            
            # Display matches
            print("\n📋 MATCH SUMMARY:")
            print("-"*60)
            
            for i, match in enumerate(updated_data['matches'], 1):
                status = match.get('status', 'N/A').upper()
                if status == 'RECENT':
                    status = 'LIVE'  # Display as LIVE
                    
                print(f"\n{i}. {match.get('title', 'N/A')}")
                print(f"   📊 League: {match.get('league', 'N/A')}")
                print(f"   📡 Status: {status}")
                print(f"   👁️ Viewers: {match.get('viewers', 'N/A')} {match.get('viewers_type', '')}")
                print(f"   🖥️ Servers: {len(match.get('server_urls', []))}")
                if match.get('server_urls'):
                    for idx, url in enumerate(match['server_urls'][:3], 1):
                        print(f"      Server {idx}: {url[:80]}...")
                print(f"   🔗 URL: {match.get('match_url', 'N/A')}")
            
            # Save to JSON
            json_file = 'data/matches.json'
            with open(json_file, 'w', encoding='utf-8') as f:
                json.dump(updated_data, f, indent=2, ensure_ascii=False)
            
            print("\n" + "="*60)
            print(f"💾 Updated JSON saved to: {json_file}")
            print(f"📊 Total matches: {updated_data['total_matches']}")
            print(f"📊 Live: {updated_data['live_count']}")
            print(f"📊 Upcoming: {updated_data['upcoming_count']}")
            print(f"📊 Completed: {updated_data['completed_count']}")
            print("="*60)
        else:
            print("⚠️ No matches found.")
        
        return matches

def main():
    scraper = SportzfyFullScraper()
    matches = scraper.scrape(fetch_servers=True)
    
    if matches:
        print(f"\n✅ Scraping complete! Found {len(matches)} matches.")
        print("📁 Data updated in 'data/matches.json'")
        
        # Show live matches specifically
        live_matches = [m for m in matches if m.get('status') == 'live']
        if live_matches:
            print(f"\n🎯 LIVE MATCHES ({len(live_matches)}):")
            for match in live_matches:
                print(f"  • {match.get('title')} - {match.get('viewers')} viewers")
    else:
        print("\n❌ No data scraped.")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n⚠️ Scraping interrupted by user")
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
