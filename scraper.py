#!/usr/bin/env python3
"""
Sportzfy Cricket Scraper - With Stream URL Extraction
Scrapes match data and extracts live stream URLs
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
            'User-Agent': 'Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.6099.230 Mobile Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Referer': 'https://sportzfy.my.id/'
        }
        self.session = requests.Session()
        self.session.headers.update(self.headers)
        
    def fetch_page(self, url=None):
        """Fetch a page"""
        if url is None:
            url = self.base_url
        try:
            print(f"📡 Fetching: {url}")
            response = self.session.get(url, timeout=15)
            response.raise_for_status()
            print(f"✅ Status: {response.status_code}")
            return response.text
        except requests.exceptions.RequestException as e:
            print(f"❌ Error: {e}")
            return None

    def extract_stream_url(self, html):
        """Extract stream URL from match page"""
        soup = BeautifulSoup(html, 'html.parser')
        stream_url = None
        
        # Method 1: Look for iframe src
        iframe = soup.find('iframe')
        if iframe and iframe.get('src'):
            stream_url = iframe.get('src')
            if stream_url.startswith('//'):
                stream_url = 'https:' + stream_url
            print(f"🎥 Found stream URL in iframe: {stream_url[:50]}...")
            return stream_url
        
        # Method 2: Look for video source
        video = soup.find('video')
        if video:
            source = video.find('source')
            if source and source.get('src'):
                stream_url = source.get('src')
                print(f"🎥 Found stream URL in video source: {stream_url[:50]}...")
                return stream_url
        
        # Method 3: Look for data-stream attribute
        stream_elem = soup.find(attrs={'data-stream': True})
        if stream_elem:
            stream_url = stream_elem.get('data-stream')
            print(f"🎥 Found stream URL in data-stream: {stream_url[:50]}...")
            return stream_url
        
        # Method 4: Search for stream URL in scripts
        scripts = soup.find_all('script')
        for script in scripts:
            if script.string:
                # Look for stream URL patterns
                patterns = [
                    r'["\'](https?://[^"\']+\.m3u8[^"\']*)["\']',
                    r'["\'](https?://[^"\']+\.mp4[^"\']*)["\']',
                    r'["\'](https?://[^"\']+stream[^"\']+)["\']',
                    r'streamUrl\s*[:=]\s*["\']([^"\']+)["\']',
                    r'videoSrc\s*[:=]\s*["\']([^"\']+)["\']',
                    r'src\s*[:=]\s*["\']([^"\']+\.m3u8[^"\']+)["\']',
                ]
                for pattern in patterns:
                    match = re.search(pattern, script.string)
                    if match:
                        stream_url = match.group(1)
                        if stream_url.startswith('//'):
                            stream_url = 'https:' + stream_url
                        print(f"🎥 Found stream URL in script: {stream_url[:50]}...")
                        return stream_url
        
        # Method 5: Look for embedded player URL
        player_div = soup.find('div', class_=re.compile(r'player|video|stream'))
        if player_div:
            # Look for any URL in onclick or data attributes
            for attr in ['onclick', 'data-url', 'data-src', 'data-href']:
                if player_div.get(attr):
                    url_match = re.search(r'(https?://[^\s"\']+)', player_div.get(attr))
                    if url_match:
                        stream_url = url_match.group(1)
                        print(f"🎥 Found stream URL in player div: {stream_url[:50]}...")
                        return stream_url
        
        # Method 6: Check for player configuration
        player_config = re.search(r'player\s*[:=]\s*\{[^}]*src\s*[:=]\s*["\']([^"\']+)["\']', str(soup), re.IGNORECASE)
        if player_config:
            stream_url = player_config.group(1)
            print(f"🎥 Found stream URL in player config: {stream_url[:50]}...")
            return stream_url
        
        print("⚠️ No stream URL found in page")
        return None

    def get_match_stream(self, match_url):
        """Get stream URL for a specific match"""
        if not match_url:
            return None
        
        print(f"\n🔍 Fetching stream for: {match_url}")
        html = self.fetch_page(match_url)
        if not html:
            return None
        
        # Save match page HTML for debugging
        os.makedirs('data', exist_ok=True)
        match_id = re.search(r'-(\d+)$', match_url)
        if match_id:
            filename = f"data/match_{match_id.group(1)}.html"
            with open(filename, 'w', encoding='utf-8') as f:
                f.write(html)
            print(f"💾 Match page saved to: {filename}")
        
        stream_url = self.extract_stream_url(html)
        return stream_url

    def extract_match_data(self, html):
        """Extract match information from HTML"""
        soup = BeautifulSoup(html, 'html.parser')
        matches = []
        
        # Find all match cards
        match_cards = soup.select('div.match-card')
        
        if not match_cards:
            print("⚠️ No match cards found")
            return matches
        
        print(f"📊 Found {len(match_cards)} match cards")
        
        for card in match_cards:
            match_data = self.parse_match_card(card)
            if match_data:
                # Get stream URL for this match
                if match_data.get('match_url'):
                    stream_url = self.get_match_stream(match_data['match_url'])
                    if stream_url:
                        match_data['stream_url'] = stream_url
                        print(f"✅ Stream URL found for {match_data['title'][:30]}...")
                    else:
                        match_data['stream_url'] = None
                        print(f"⚠️ No stream URL for {match_data['title'][:30]}...")
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
            'stream_url': None,
            'last_updated': datetime.now().isoformat()
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

    def load_existing_data(self):
        """Load existing matches.json if it exists"""
        json_file = 'data/matches.json'
        if os.path.exists(json_file):
            try:
                with open(json_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    print(f"📂 Loaded existing data with {data.get('total_matches', 0)} matches")
                    return data
            except:
                print("⚠️ Could not load existing data, creating new")
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
                'matches': new_matches
            }
        
        # Create lookup by match_id
        existing_matches = {m.get('match_id'): m for m in existing_data.get('matches', []) if m.get('match_id')}
        
        # Update existing matches with new data
        for new_match in new_matches:
            match_id = new_match.get('match_id')
            if match_id and match_id in existing_matches:
                # Preserve stream_url if it exists and new one doesn't have it
                if not new_match.get('stream_url') and existing_matches[match_id].get('stream_url'):
                    new_match['stream_url'] = existing_matches[match_id]['stream_url']
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
            'matches': updated_matches
        }

    def scrape(self):
        """Main scraping method"""
        print("\n" + "="*60)
        print("🏏 SPORTZFY SCRAPER - WITH STREAM URLS")
        print("="*60 + "\n")
        
        # Fetch main page
        html = self.fetch_page()
        if not html:
            print("❌ Failed to fetch page")
            return []
        
        # Create data directory
        os.makedirs('data', exist_ok=True)
        
        # Save raw HTML
        with open('data/sportzfy_raw.html', 'w', encoding='utf-8') as f:
            f.write(html)
        print("💾 Raw HTML saved to: data/sportzfy_raw.html")
        
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
            for i, match in enumerate(updated_data['matches'], 1):
                print(f"📌 MATCH #{i}")
                print(f"   🏷️  Title: {match.get('title', 'N/A')}")
                print(f"   📡  Status: {match.get('status', 'N/A').upper() if match.get('status') else 'N/A'}")
                print(f"   🎥  Stream: {match.get('stream_url', 'Not available')[:60] + '...' if match.get('stream_url') else 'Not available'}")
                print(f"   👁️  Viewers: {match.get('viewers', 'N/A')} {match.get('viewers_type', '')}")
                print(f"   🆔  Match ID: {match.get('match_id', 'N/A')}")
                print("-"*50)
            
            # Save to same file
            json_file = 'data/matches.json'
            with open(json_file, 'w', encoding='utf-8') as f:
                json.dump(updated_data, f, indent=2, ensure_ascii=False)
            print(f"💾 Updated JSON saved to: {json_file}")
            print(f"📊 Total matches: {updated_data['total_matches']}")
            print(f"📊 Live: {updated_data['live_count']}, Upcoming: {updated_data['upcoming_count']}, Completed: {updated_data['completed_count']}")
        else:
            print("⚠️ No matches found.")
        
        return matches

def main():
    scraper = SportzfyScraper()
    matches = scraper.scrape()
    
    if matches:
        print(f"\n✅ Scraping complete! Found {len(matches)} matches.")
        print("📁 Data updated in 'data/matches.json'")
    else:
        print("\n❌ No data scraped.")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n⚠️ Scraping interrupted by user")
    except Exception as e:
        print(f"\n❌ Error: {e}")
