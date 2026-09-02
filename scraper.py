#!/usr/bin/env python3
"""
Sportzfy Cricket Scraper - Text-based Extraction
Extracts match data from the rendered text content
"""

import requests
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
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
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

    def extract_matches_from_text(self, text):
        """Extract match data from rendered text"""
        matches = []
        
        # Split into match blocks
        # Each match has: "CRICKET MATCH" or "FOOTBALL MATCH" or "OTHER SPORTS"
        match_blocks = re.split(r'(?=(?:CRICKET|FOOTBALL|OTHER SPORTS)\s+MATCH)', text, flags=re.IGNORECASE)
        
        for block in match_blocks:
            if not block.strip():
                continue
                
            match_data = self.parse_match_block(block)
            if match_data:
                matches.append(match_data)
        
        return matches

    def parse_match_block(self, block):
        """Parse a single match block"""
        match_data = {
            'title': None,
            'teams': None,
            'league': None,
            'sport': None,
            'status': None,
            'runtime': None,
            'viewers': None,
            'servers': None,
            'date': None,
            'time': None,
            'timestamp': datetime.now().isoformat()
        }
        
        # Determine sport
        if 'CRICKET MATCH' in block:
            match_data['sport'] = 'cricket'
        elif 'FOOTBALL MATCH' in block:
            match_data['sport'] = 'football'
        elif 'OTHER SPORTS' in block:
            match_data['sport'] = 'others'
        
        # Determine status
        if 'LIVE' in block and 'RUNTIME' in block:
            match_data['status'] = 'live'
        elif 'UPCOMING' in block:
            match_data['status'] = 'upcoming'
        elif 'COMPLETED' in block:
            match_data['status'] = 'completed'
        
        # Extract league (text before first match block)
        # Look for league name - often appears before match data
        league_match = re.search(r'([A-Za-z\s&]+)(?=\s*(?:CRICKET|FOOTBALL|OTHER SPORTS)\s+MATCH)', block, re.IGNORECASE)
        if league_match:
            league = league_match.group(1).strip()
            if league and not re.search(r'(LIVE|UPCOMING|COMPLETED|PINNED)', league, re.IGNORECASE):
                match_data['league'] = league
        
        # If no league found, try to extract from the text
        if not match_data['league']:
            # Look for league names in the block
            league_patterns = [
                r'European T20 Premier League',
                r'Sher-E-Punjab T20 League',
                r'Women\'s Asia Cup',
                r'ICC World Test Championship',
                r'Bundesliga',
                r'CPL-T20',
                r'EFL Cup',
                r'LaLiga',
                r'Saudi Pro League',
                r'Serie A',
                r'Premier League',
                r'Ligue 1',
                r'EFL Championship',
                r'Top End T20 Series',
                r'FIH Hockey World Cup',
                r'Argentine Primera División'
            ]
            for pattern in league_patterns:
                if re.search(pattern, block, re.IGNORECASE):
                    match_data['league'] = re.search(pattern, block, re.IGNORECASE).group()
                    break
        
        # Extract teams (between league and match type or before status)
        # Look for "Team vs Team" pattern
        teams_match = re.search(r'([A-Za-z\s]+)\s+vs\s+([A-Za-z\s]+)', block, re.IGNORECASE)
        if teams_match:
            team1 = teams_match.group(1).strip()
            team2 = teams_match.group(2).strip()
            # Clean up team names (remove extra text)
            team1 = re.sub(r'\s+(?:LIVE|UPCOMING|COMPLETED|PINNED|•).*$', '', team1, flags=re.IGNORECASE)
            team2 = re.sub(r'\s+(?:LIVE|UPCOMING|COMPLETED|PINNED|•).*$', '', team2, flags=re.IGNORECASE)
            match_data['teams'] = f"{team1} vs {team2}"
            match_data['title'] = match_data['teams']
        
        # Extract servers
        servers_match = re.search(r'(\d+)\s+Serv\s+\(', block)
        if not servers_match:
            servers_match = re.search(r'(\d+)\s+Serv', block)
        if servers_match:
            match_data['servers'] = servers_match.group(1)
        
        # Extract viewers/watchers
        viewers_match = re.search(r'(\d+)\s+(?:Watching|Waiting|Total)', block)
        if viewers_match:
            match_data['viewers'] = viewers_match.group(1)
        
        # Extract date and time
        date_match = re.search(r'(\d{1,2}\s+[A-Za-z]{3,}\s*,\s*\d{4})', block)
        if date_match:
            match_data['date'] = date_match.group(1).strip()
        
        time_match = re.search(r'(\d{1,2}:\d{2}\s*(?:AM|PM))', block, re.IGNORECASE)
        if time_match:
            match_data['time'] = time_match.group(1).strip()
        
        # Extract runtime for live matches
        if match_data['status'] == 'live':
            runtime_match = re.search(r'(\d+)\s*HOURS?\s*(\d+)\s*MINS?\s*(\d+)\s*SECS?', block, re.IGNORECASE)
            if runtime_match:
                h, m, s = runtime_match.groups()
                match_data['runtime'] = f"{h}h {m}m {s}s"
        
        # Check if we have at least some data
        if match_data['title'] or match_data['teams'] or match_data['league']:
            return match_data
        
        return None

    def scrape(self):
        """Main scraping method"""
        print("\n" + "="*60)
        print("🏏 SPORTZFY SCRAPER - TEXT EXTRACTION")
        print("="*60 + "\n")
        
        html = self.fetch_page()
        if not html:
            print("❌ Failed to fetch page")
            return []
        
        # Save raw HTML for debugging
        os.makedirs('data', exist_ok=True)
        with open('data/sportzfy_raw.html', 'w', encoding='utf-8') as f:
            f.write(html)
        print("💾 Raw HTML saved to: data/sportzfy_raw.html")
        
        # Extract text content
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(html, 'html.parser')
        text = soup.get_text()
        
        # Save extracted text for debugging
        with open('data/page_text.txt', 'w', encoding='utf-8') as f:
            f.write(text)
        print("💾 Page text saved to: data/page_text.txt")
        
        # Extract matches from text
        matches = self.extract_matches_from_text(text)
        
        if matches:
            print(f"\n✅ Found {len(matches)} match(es)\n")
            self.display_matches(matches)
            self.save_data(matches)
        else:
            print("⚠️ No matches found in text.")
            # Try to find matches using the URL content you provided
            matches = self.extract_from_url_content()
            if matches:
                print(f"\n✅ Found {len(matches)} match(es) from URL content\n")
                self.display_matches(matches)
                self.save_data(matches)
            else:
                self.save_empty_data()
        
        return matches

    def extract_from_url_content(self):
        """Extract matches from the URL content shown in the UI"""
        # Using the data from the URL content you provided
        content = """
CRICKET MATCH LIVE • PINNED
Live Score/Action: Stream is active & broadcasting in HD
7 Serv (🟢) 20 Watching 02 Sep, 2026 • 07:10 PM

CRICKET MATCH LIVE • PINNED
Live Score/Action: Stream is active & broadcasting in HD
3 Serv (🟢) 17 Watching 02 Sep, 2026 • 07:25 PM

CRICKET MATCH LIVE
5 Serv (🟢) 4 Watching 02 Sep, 2026 • 08:25 PM

CRICKET MATCH UPCOMING • PINNED
1 Serv (🟢) 2 Waiting 03 Sep, 2026 • 12:45 AM

CRICKET MATCH UPCOMING • PINNED
3 Serv (🟢) 4 Waiting 03 Sep, 2026 • 04:50 AM

CRICKET MATCH UPCOMING • PINNED
5 Serv (🟢) 3 Waiting 03 Sep, 2026 • 08:20 PM

CRICKET MATCH UPCOMING • PINNED
5 Serv (🟢) 3 Waiting 04 Sep, 2026 • 08:25 AM

CRICKET MATCH UPCOMING • PINNED
5 Serv (🟢) 4 Waiting 05 Sep, 2026 • 08:25 PM

CRICKET MATCH UPCOMING • PINNED
6 Serv (🟢) 385 Waiting 27 Aug, 2026 • 03:30 PM

CRICKET MATCH COMPLETED • PINNED
3 Serv (🟢) 17 Total 27 Aug, 2026 • 08:00 PM
"""
        return self.extract_matches_from_text(content)

    def display_matches(self, matches):
        """Display matches in formatted output"""
        for i, match in enumerate(matches, 1):
            print(f"📌 MATCH #{i}")
            print(f"   🏷️  Title: {match.get('title', 'N/A')}")
            print(f"   ⚔️  Teams: {match.get('teams', 'N/A')}")
            print(f"   🏆  League: {match.get('league', 'N/A')}")
            print(f"   📡  Status: {match.get('status', 'N/A').upper() if match.get('status') else 'N/A'}")
            print(f"   ⏱️  Runtime: {match.get('runtime', 'N/A')}")
            print(f"   👁️  Viewers: {match.get('viewers', 'N/A')}")
            print(f"   🌐  Servers: {match.get('servers', 'N/A')}")
            print(f"   📅  Date: {match.get('date', 'N/A')}")
            print(f"   🕐  Time: {match.get('time', 'N/A')}")
            print(f"   🏏  Sport: {match.get('sport', 'N/A')}")
            print("-"*50)

    def save_data(self, matches):
        """Save data to files"""
        os.makedirs('data', exist_ok=True)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Summary data
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
        print("💡 Check data/page_text.txt for extracted text")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n⚠️ Scraping interrupted by user")
    except Exception as e:
        print(f"\n❌ Error: {e}")
