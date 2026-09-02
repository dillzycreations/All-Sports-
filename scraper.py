#!/usr/bin/env python3
"""
Sportzfy Cricket Scraper - With Server URL Extraction
Scrapes match data and extracts live server URLs from match pages
"""

import requests
from bs4 import BeautifulSoup
import json
import re
import base64
from datetime import datetime, timedelta
import os
import codecs

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
        
    def fetch_page(self, url):
        """Fetch a page"""
        try:
            print(f"📡 Fetching: {url}")
            response = self.session.get(url, timeout=15)
            response.raise_for_status()
            print(f"✅ Status: {response.status_code}")
            return response.text
        except requests.exceptions.RequestException as e:
            print(f"❌ Error fetching {url}: {e}")
            return None

    def decode_server_url(self, encoded_string):
        """Decode server URL using Base64 decode → ROT13"""
        try:
            base64_decoded = base64.b64decode(encoded_string).decode('utf-8')
            rot13_decoded = codecs.decode(base64_decoded, 'rot_13')
            return rot13_decoded
        except:
            try:
                import string
                rot13 = str.maketrans(
                    "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz",
                    "NOPQRSTUVWXYZABCDEFGHIJKLMNOPQRSTUVWXYZABCDEFGHIJKLMNOPQRSTUVWXYZ"
                )
                return base64_decoded.translate(rot13)
            except:
                return None

    def extract_server_urls(self, html):
        """Extract server URLs from match page"""
        soup = BeautifulSoup(html, 'html.parser')
        server_urls = []
        
        scripts = soup.find_all('script')
        for script in scripts:
            if script.string:
                match = re.search(r'const\s+encServerList\s*=\s*\[([^\]]+)\]', script.string, re.DOTALL)
                if match:
                    encoded_strings = re.findall(r'"([^"]+)"', match.group(1))
                    for enc in encoded_strings:
                        decoded = self.decode_server_url(enc)
                        if decoded:
                            server_urls.append(decoded)
                    break
        
        if not server_urls:
            match = re.search(r'const\s+serverList\s*=\s*\[([^\]]+)\]', str(soup), re.DOTALL)
            if match:
                server_urls = re.findall(r'"([^"]+)"', match.group(1))
        
        return server_urls

    def determine_match_status(self, card, match_date, match_time):
        """Determine the actual status of a match"""
        # Get status from data attribute
        status = card.get('data-status')
        
        # If it's already live, keep it as live
        if status == 'live':
            return 'live'
        
        # For upcoming/completed, check the date and time
        if match_date and match_time:
            try:
                # Parse the match date/time
                match_datetime_str = f"{match_date} {match_time}"
                # Remove ordinal suffixes like 'nd', 'rd', 'th'
                match_datetime_str = re.sub(r'(\d+)(st|nd|rd|th)', r'\1', match_datetime_str)
                # Parse the datetime
                match_datetime = datetime.strptime(match_datetime_str, "%d %b, %Y %I:%M %p")
                now = datetime.now()
                
                # If match time is in the past (more than 4 hours ago), it's completed
                if now - match_datetime > timedelta(hours=4):
                    return 'completed'
                # If match time is in the future, it's upcoming
                elif now < match_datetime:
                    return 'upcoming'
                # If match is within the last 4 hours, it might still be live
                else:
                    # Check if there are server URLs (if we fetched them)
                    return 'live'
            except:
                pass
        
        # If status is 'upcoming' but we have server URLs, it might actually be live
        if status == 'upcoming':
            # Check if there's a live runtime box (indicates match has started)
            live_runtime = card.find('div', class_='header-live-boxes-container')
            if live_runtime and live_runtime.find('div', class_='header-boxes-row'):
                return 'live'
        
        # Check for completed indicators in the card
        if 'COMPLETED' in str(card) or 'ended-tag' in str(card) or 'Completed' in str(card):
            return 'completed'
        
        # Check for live indicators
        if 'LIVE' in str(card) or 'live-tag' in str(card) or 'Stream is active' in str(card):
            return 'live'
        
        # If status is 'upcoming' and no live indicators, keep as upcoming
        if status == 'upcoming':
            return 'upcoming'
        
        # Default to the status from data attribute
        return status

    def extract_match_data(self, html):
        """Extract match information from HTML - Only RECENT and LIVE matches"""
        soup = BeautifulSoup(html, 'html.parser')
        matches = []
        
        match_cards = soup.select('div.match-card')
        
        if not match_cards:
            print("⚠️ No match cards found")
            return matches
        
        print(f"📊 Found {len(match_cards)} total match cards")
        
        # Filter: Only include matches that are 'live' (RECENT tab shows live matches)
        # Also include 'upcoming' matches for the UPCOMING tab
        filtered_cards = []
        for card in match_cards:
            status = card.get('data-status')
            # RECENT tab shows live matches, UPCOMING tab shows upcoming matches
            if status == 'live' or status == 'upcoming':
                filtered_cards.append(card)
        
        print(f"📊 Found {len(filtered_cards)} recent/live/upcoming matches")
        
        for card in filtered_cards:
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
            'server_urls': [],
            'last_updated': datetime.now().isoformat()
        }
        
        # Get data attributes
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
        if card.get('data-status') == 'live':
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
        if card.get('data-status') == 'upcoming':
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
        
        # Determine actual status (this fixes the "completed showing as live" issue)
        match_data['status'] = self.determine_match_status(card, match_data.get('date'), match_data.get('time'))
        
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
                    # If no server URLs found, it might be completed
                    print(f"⚠️ No server URLs found, marking as completed")
                    match_data['status'] = 'completed'
        
        # Check if we have at least some data
        if match_data['title'] or match_data['league'] or match_data['match_id']:
            return match_data
        
        return None

    def construct_match_url(self, title, match_id):
        """Construct match URL from title and ID"""
        if not title or not match_id:
            return None
        
        url_title = title.lower()
        url_title = re.sub(r'[^a-z0-9\s-]', '', url_title)
        url_title = re.sub(r'\s+', '-', url_title)
        url_title = re.sub(r'-+', '-', url_title)
        
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
            'matches': updated_matches
        }

    def scrape(self):
        """Main scraping method"""
        print("\n" + "="*60)
        print("🏏 SPORTZFY SCRAPER - WITH STATUS FIX")
        print("="*60 + "\n")
        
        html = self.fetch_page(self.base_url)
        if not html:
            print("❌ Failed to fetch page")
            return []
        
        os.makedirs('data', exist_ok=True)
        
        with open('data/sportzfy_raw.html', 'w', encoding='utf-8') as f:
            f.write(html)
        
        print("\n🔍 Extracting match data...")
        matches = self.extract_match_data(html)
        
        if matches:
            print(f"\n✅ Found {len(matches)} match(es)\n")
            
            existing_data = self.load_existing_data()
            updated_data = self.update_data(existing_data, matches)
            
            for i, match in enumerate(updated_data['matches'], 1):
                print(f"📌 MATCH #{i}")
                print(f"   🏷️  Title: {match.get('title', 'N/A')}")
                print(f"   📡  Status: {match.get('status', 'N/A').upper() if match.get('status') else 'N/A'}")
                print(f"   🎥  Servers: {len(match.get('server_urls', []))} found")
                print("-"*50)
            
            json_file = 'data/matches.json'
            with open(json_file, 'w', encoding='utf-8') as f:
                json.dump(updated_data, f, indent=2, ensure_ascii=False)
            print(f"\n💾 Updated JSON saved to: {json_file}")
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
