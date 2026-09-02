#!/usr/bin/env python3
"""
Sportzfy Cricket Scraper - Fixed Version
Scrapes live match data from sportzfy.my.id
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
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
            'Cache-Control': 'no-cache'
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
        
        # Find all match cards - using class_ with multiple classes
        match_cards = soup.find_all('div', class_=lambda x: x and 'match-card' in x.split())
        
        if not match_cards:
            # Alternative: find div with match-card in class
            match_cards = soup.select('div.match-card')
        
        if not match_cards:
            print("⚠️ No match cards found. Trying alternative selectors...")
            # Try to find by data attributes
            match_cards = soup.find_all('div', attrs={'data-match-id': True})
        
        if not match_cards:
            print("⚠️ Still no matches found. Checking page structure...")
            # Check if we got the page
            title = soup.title.string if soup.title else "No title"
            print(f"📝 Page title: {title}")
            
            # Look for any cricket-related content
            cricket_text = soup.find_all(string=re.compile(r'cricket|t20|league|match', re.I))
            if cricket_text:
                print(f"🔍 Found {len(cricket_text)} cricket-related text elements")
                # Try to extract from text
                matches = self.extract_from_text(soup.get_text())
            return matches
        
        print(f"📊 Found {len(match_cards)} match cards")
        
        for card in match_cards:
            match_data = self.parse_match_card(card)
            if match_data:
                matches.append(match_data)
        
        return matches

    def extract_from_text(self, text):
        """Extract match data from raw text"""
        matches = []
        
        # Find match patterns
        # Pattern: Team1 vs Team2 with details
        patterns = [
            r'([A-Za-z\s]+)\s+vs\s+([A-Za-z\s]+).*?(\d+)\s*Watching',
            r'([A-Za-z\s]+)\s+vs\s+([A-Za-z\s]+).*?(\d+)\s*Serv',
            r'([A-Za-z\s]+)\s+vs\s+([A-Za-z\s]+)',
        ]
        
        for pattern in patterns:
            matches_found = re.findall(pattern, text, re.IGNORECASE | re.DOTALL)
            for match in matches_found:
                if len(match) >= 2:
                    match_data = {
                        'title': f"{match[0].strip()} vs {match[1].strip()}",
                        'teams': f"{match[0].strip()} vs {match[1].strip()}",
                        'status': 'Unknown',
                        'timestamp': datetime.now().isoformat()
                    }
                    
                    # Check for live indicators
                    if 'LIVE' in text or 'Stream is active' in text:
                        match_data['status'] = 'live'
                    
                    # Try to extract viewers
                    viewers_match = re.search(r'(\d+)\s*Watching', text)
                    if viewers_match:
                        match_data['viewers'] = viewers_match.group(1)
                    
                    # Try to extract servers
                    servers_match = re.search(r'(\d+)\s*Serv', text)
                    if servers_match:
                        match_data['servers'] = servers_match.group(1)
                    
                    if match_data not in matches:
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
            'servers': None,
            'date': None,
            'time': None,
            'match_url': None,
            'thumbnail': None,
            'match_id': None,
            'timestamp': datetime.now().isoformat()
        }
        
        # Get match ID and status from data attributes
        match_id = card.get('data-match-id')
        status = card.get('data-status')
        sport = card.get('data-sport')
        match_data['match_id'] = match_id
        match_data['status'] = status
        match_data['sport'] = sport
        
        # Extract league title
        league_title = card.find('div', class_=lambda x: x and 'league-title' in x.split() if x else False)
        if not league_title:
            league_title = card.find('div', class_='league-title')
        if league_title:
            match_data['league'] = league_title.get_text(strip=True)
        
        # Extract teams from main title
        title_div = card.find('div', class_=lambda x: x and 'match-main-title' in x.split() if x else False)
        if not title_div:
            title_div = card.find('div', class_='match-main-title')
        
        if title_div:
            title_link = title_div.find('a')
            if title_link:
                match_data['title'] = title_link.get_text(strip=True)
                match_data['teams'] = match_data['title']
                # Get match URL
                match_url = title_link.get('href')
                if match_url and match_url != 'javascript:void(0)':
                    if match_url.startswith('/'):
                        match_data['match_url'] = self.base_url + match_url
                    else:
                        match_data['match_url'] = match_url
        
        # Extract thumbnail
        thumb_box = card.find('a', class_=lambda x: x and 'thumb-box' in x.split() if x else False)
        if not thumb_box:
            thumb_box = card.find('a', class_='thumb-box')
        if thumb_box:
            img = thumb_box.find('img')
            if img:
                match_data['thumbnail'] = img.get('src')
        
        # Extract meta info (servers, viewers, date, time)
        meta_row = card.find('div', class_=lambda x: x and 'match-meta-row' in x.split() if x else False)
        if not meta_row:
            meta_row = card.find('div', class_='match-meta-row')
        
        if meta_row:
            # Extract servers
            server_span = meta_row.find('span', class_=lambda x: x and 'meta-item' in x.split() if x else False)
            if server_span:
                server_text = server_span.get_text(strip=True)
                server_match = re.search(r'(\d+)\s*Serv', server_text)
                if server_match:
                    match_data['servers'] = server_match.group(1)
            
            # Extract viewers
            view_pill = meta_row.find('span', class_=lambda x: x and 'view-pill' in x.split() if x else False)
            if not view_pill:
                view_pill = meta_row.find('span', class_='view-pill')
            if view_pill:
                view_text = view_pill.get_text(strip=True)
                view_match = re.search(r'(\d+)\s+(Watching|Waiting|Total)', view_text)
                if view_match:
                    match_data['viewers'] = view_match.group(1)
                else:
                    view_match = re.search(r'(\d+)', view_text)
                    if view_match:
                        match_data['viewers'] = view_match.group(1)
            
            # Extract date and time
            time_spans = meta_row.find_all('span', class_=lambda x: x and 'meta-item' in x.split() if x else False)
            if not time_spans:
                time_spans = meta_row.find_all('span', class_='meta-item')
            for span in time_spans:
                span_text = span.get_text(strip=True)
                # Look for date pattern
                date_match = re.search(r'(\d{1,2}\s+[A-Za-z]{3,}\s*,\s*\d{4})', span_text)
                if date_match:
                    match_data['date'] = date_match.group(1).strip()
                # Look for time pattern
                time_match = re.search(r'(\d{1,2}:\d{2}\s*(?:AM|PM))', span_text, re.IGNORECASE)
                if time_match:
                    match_data['time'] = time_match.group(1).strip()
        
        # Extract runtime for live matches
        if status == 'live':
            # Try to get runtime from header live boxes
            live_boxes = card.find_all('div', class_=lambda x: x and 'header-cd-box' in x.split() if x else False)
            if not live_boxes:
                live_boxes = card.find_all('div', class_='header-cd-box')
            if len(live_boxes) >= 3:
                hours = live_boxes[0].find('div', class_=lambda x: x and 'header-cd-num' in x.split() if x else False)
                mins = live_boxes[1].find('div', class_=lambda x: x and 'header-cd-num' in x.split() if x else False)
                secs = live_boxes[2].find('div', class_=lambda x: x and 'header-cd-num' in x.split() if x else False)
                if hours and mins and secs:
                    h = hours.get_text(strip=True)
                    m = mins.get_text(strip=True)
                    s = secs.get_text(strip=True)
                    match_data['runtime'] = f"{h}h {m}m {s}s"
        
        # For upcoming matches, get countdown from overlay
        if status == 'upcoming':
            overlay = card.find('div', class_=lambda x: x and 'thumb-countdown-overlay' in x.split() if x else False)
            if not overlay:
                overlay = card.find('div', class_='thumb-countdown-overlay')
            if overlay:
                cd_boxes = overlay.find_all('div', class_=lambda x: x and 'cd-box' in x.split() if x else False)
                if not cd_boxes:
                    cd_boxes = overlay.find_all('div', class_='cd-box')
                if len(cd_boxes) >= 3:
                    hours = cd_boxes[0].find('div', class_=lambda x: x and 'cd-num' in x.split() if x else False)
                    mins = cd_boxes[1].find('div', class_=lambda x: x and 'cd-num' in x.split() if x else False)
                    secs = cd_boxes[2].find('div', class_=lambda x: x and 'cd-num' in x.split() if x else False)
                    if hours and mins and secs:
                        h = hours.get_text(strip=True)
                        m = mins.get_text(strip=True)
                        s = secs.get_text(strip=True)
                        match_data['runtime'] = f"{h}h {m}m {s}s"
        
        # Check if we have at least some data
        if match_data['title'] or match_data['league']:
            return match_data
        
        return None

    def scrape(self):
        """Main scraping method"""
        print("\n" + "="*60)
        print("🏏 SPORTZFY SCRAPER - COMPLETE")
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
        
        matches = self.extract_match_data(html)
        
        if matches:
            print(f"\n✅ Found {len(matches)} match(es)\n")
            self.display_matches(matches)
            self.save_data(matches)
        else:
            print("⚠️ No matches found.")
            # Try to save raw text for debugging
            soup = BeautifulSoup(html, 'html.parser')
            text = soup.get_text()
            with open('data/page_text.txt', 'w', encoding='utf-8') as f:
                f.write(text[:5000])  # Save first 5000 chars
            print("💾 Page text saved to: data/page_text.txt")
            self.save_empty_data()
        
        return matches

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
            print(f"   🆔  Match ID: {match.get('match_id', 'N/A')}")
            if match.get('match_url'):
                print(f"   🔗  URL: {match['match_url']}")
            if match.get('thumbnail'):
                print(f"   🖼️  Thumbnail: {match['thumbnail'][:50]}...")
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
        
        # Save HTML report
        self.save_html_report(matches, timestamp)
        
        # Save Markdown report
        self.save_markdown_report(matches, timestamp)

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

    def save_html_report(self, matches, timestamp):
        """Save HTML report"""
        html_file = f'data/report_{timestamp}.html'
        
        html_content = f"""<!DOCTYPE html>
<html>
<head>
    <title>Sportzfy Matches Report</title>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <style>
        body {{ font-family: -apple-system, Arial, sans-serif; background: #0b0e1a; color: #e0e8ff; padding: 20px; margin: 0; }}
        .container {{ max-width: 1000px; margin: 0 auto; }}
        .header {{ background: linear-gradient(135deg, #1e3a8a, #3b82f6); padding: 20px; border-radius: 12px; margin-bottom: 20px; }}
        h1 {{ margin: 0; color: white; }}
        .timestamp {{ color: #9ca3af; font-size: 14px; }}
        .stats {{ display: flex; gap: 20px; margin: 15px 0; flex-wrap: wrap; }}
        .stat-box {{ background: #151e30; padding: 10px 20px; border-radius: 8px; }}
        .stat-label {{ color: #9ca3af; font-size: 12px; }}
        .stat-value {{ font-size: 20px; font-weight: bold; color: #60a5fa; }}
        .match {{ background: #151e30; border-radius: 12px; padding: 15px; margin: 15px 0; border-left: 4px solid #3b82f6; }}
        .match.live {{ border-left-color: #ef4444; }}
        .match.upcoming {{ border-left-color: #38bdf8; }}
        .match.completed {{ border-left-color: #64748b; }}
        .title {{ color: #60a5fa; font-size: 18px; font-weight: bold; }}
        .label {{ color: #9ca3af; font-weight: 600; }}
        .value {{ color: #e0e8ff; }}
        .status-live {{ color: #34d399; font-weight: bold; }}
        .status-upcoming {{ color: #38bdf8; font-weight: bold; }}
        .status-completed {{ color: #64748b; font-weight: bold; }}
        .status-unknown {{ color: #fbbf24; font-weight: bold; }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🏏 Sportzfy Match Data</h1>
            <p class="timestamp">Scraped: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
        </div>
        <div class="stats">
            <div class="stat-box">
                <div class="stat-label">Total Matches</div>
                <div class="stat-value">{len(matches)}</div>
            </div>
            <div class="stat-box">
                <div class="stat-label">Live</div>
                <div class="stat-value" style="color:#34d399;">{sum(1 for m in matches if m.get('status') == 'live')}</div>
            </div>
            <div class="stat-box">
                <div class="stat-label">Upcoming</div>
                <div class="stat-value" style="color:#38bdf8;">{sum(1 for m in matches if m.get('status') == 'upcoming')}</div>
            </div>
            <div class="stat-box">
                <div class="stat-label">Completed</div>
                <div class="stat-value" style="color:#64748b;">{sum(1 for m in matches if m.get('status') == 'completed')}</div>
            </div>
        </div>
"""
        
        for match in matches:
            status_class = match.get('status', 'unknown')
            status_display = status_class.upper() if status_class else 'UNKNOWN'
            html_content += f"""
        <div class="match {status_class}">
            <div class="title">{match.get('title', 'Unknown Match')}</div>
            <div><span class="label">Teams:</span> <span class="value">{match.get('teams', 'N/A')}</span></div>
            <div><span class="label">League:</span> <span class="value">{match.get('league', 'N/A')}</span></div>
            <div><span class="label">Status:</span> <span class="status-{status_class}">{status_display}</span></div>
            <div><span class="label">Runtime:</span> <span class="value">{match.get('runtime', 'N/A')}</span></div>
            <div><span class="label">Viewers:</span> <span class="value">{match.get('viewers', 'N/A')}</span></div>
            <div><span class="label">Servers:</span> <span class="value">{match.get('servers', 'N/A')}</span></div>
            <div><span class="label">Date:</span> <span class="value">{match.get('date', 'N/A')}</span></div>
            <div><span class="label">Time:</span> <span class="value">{match.get('time', 'N/A')}</span></div>
            <div><span class="label">Sport:</span> <span class="value">{match.get('sport', 'N/A')}</span></div>
            <div><span class="label">Match ID:</span> <span class="value">{match.get('match_id', 'N/A')}</span></div>
            {f'<div><span class="label">URL:</span> <span class="value"><a href="{match["match_url"]}" style="color:#60a5fa;">{match["match_url"]}</a></span></div>' if match.get('match_url') else ''}
        </div>
"""
        
        html_content += """
    </div>
</body>
</html>
"""
        
        with open(html_file, 'w', encoding='utf-8') as f:
            f.write(html_content)
        print(f"📄 HTML report saved to: {html_file}")

    def save_markdown_report(self, matches, timestamp):
        """Save Markdown report"""
        md_file = f'data/report_{timestamp}.md'
        
        md_content = f"""# Sportzfy Match Report

**Scraped:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}  
**Total Matches:** {len(matches)}

## Summary

- Live: {sum(1 for m in matches if m.get('status') == 'live')}
- Upcoming: {sum(1 for m in matches if m.get('status') == 'upcoming')}
- Completed: {sum(1 for m in matches if m.get('status') == 'completed')}

---
"""
        
        for i, match in enumerate(matches, 1):
            md_content += f"""
## Match #{i}

- **Title:** {match.get('title', 'N/A')}
- **Teams:** {match.get('teams', 'N/A')}
- **League:** {match.get('league', 'N/A')}
- **Status:** {match.get('status', 'N/A').upper() if match.get('status') else 'N/A'}
- **Runtime:** {match.get('runtime', 'N/A')}
- **Viewers:** {match.get('viewers', 'N/A')}
- **Servers:** {match.get('servers', 'N/A')}
- **Date:** {match.get('date', 'N/A')}
- **Time:** {match.get('time', 'N/A')}
- **Sport:** {match.get('sport', 'N/A')}
- **Match ID:** {match.get('match_id', 'N/A')}
{f"- **URL:** {match['match_url']}" if match.get('match_url') else ""}

---
"""
        
        with open(md_file, 'w', encoding='utf-8') as f:
            f.write(md_content)
        print(f"📝 Markdown report saved to: {md_file}")

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
