#!/usr/bin/env python3
"""
Sportzfy Cricket Scraper
Scrapes live match data and saves to JSON files
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
        """Extract match information"""
        soup = BeautifulSoup(html, 'html.parser')
        matches = []
        
        # Get all text
        text = soup.get_text()
        
        # Find match sections
        match_sections = []
        
        # Look for cricket match indicators
        cricket_matches = soup.find_all(string=re.compile(r'CRICKET MATCH|T20|League|Wolves|Rockers|Belfast|Edinburgh', re.I))
        
        for match_text in cricket_matches:
            parent = match_text.parent
            if parent:
                section_text = parent.get_text(separator=' ', strip=True)
                match_sections.append(section_text)
        
        # If no sections found, try regex on full text
        if not match_sections:
            sections = re.split(r'CRICKET MATCH|T20 LEAGUE', text, flags=re.I)
            for section in sections:
                if 'vs' in section.lower() or 'watching' in section.lower():
                    match_sections.append(section.strip())
        
        # Process each section
        for section in match_sections:
            match_data = self.parse_section(section)
            if match_data:
                matches.append(match_data)
        
        # If still no matches, try to find team names
        if not matches:
            teams_pattern = r'([A-Za-z\s]+)\s+vs\s+([A-Za-z\s]+)'
            teams = re.findall(teams_pattern, text)
            
            if teams:
                for team1, team2 in teams[:3]:
                    match_data = {
                        'title': f"{team1.strip()} vs {team2.strip()}",
                        'teams': f"{team1.strip()} vs {team2.strip()}",
                        'league': 'Cricket Match',
                        'status': 'LIVE' if 'live' in text.lower() else 'Unknown',
                        'timestamp': datetime.now().isoformat()
                    }
                    matches.append(match_data)
        
        return matches

    def parse_section(self, section_text):
        """Parse a section of text for match data"""
        match_data = {
            'title': None,
            'teams': None,
            'league': None,
            'runtime': None,
            'viewers': None,
            'servers': None,
            'date': None,
            'time': None,
            'status': None,
            'timestamp': datetime.now().isoformat()
        }
        
        # Extract teams
        teams_match = re.search(r'([A-Za-z\s]+)\s+vs\s+([A-Za-z\s]+)', section_text, re.I)
        if teams_match:
            match_data['teams'] = f"{teams_match.group(1).strip()} vs {teams_match.group(2).strip()}"
            match_data['title'] = match_data['teams']
        
        # Extract league
        league_patterns = [
            r'(EUROPEAN T20 PREMIER LEAGUE|ETPL)',
            r'(Sher-E-Punjab T20 League)',
            r'([A-Z\s]+LEAGUE)'
        ]
        for pattern in league_patterns:
            league_match = re.search(pattern, section_text, re.I)
            if league_match:
                match_data['league'] = league_match.group(1).strip()
                break
        
        # Extract runtime
        runtime_match = re.search(r'(\d+)\s*HOURS?\s*(\d+)\s*MINS?\s*(\d+)\s*SECS?', section_text, re.I)
        if runtime_match:
            h, m, s = runtime_match.groups()
            match_data['runtime'] = f"{h}h {m}m {s}s"
        
        # Extract viewers
        viewers_match = re.search(r'(\d+)\s*Watching', section_text, re.I)
        if viewers_match:
            match_data['viewers'] = viewers_match.group(1)
        
        # Extract servers
        servers_match = re.search(r'(\d+)\s*Serv', section_text, re.I)
        if servers_match:
            match_data['servers'] = servers_match.group(1)
        
        # Extract date
        date_match = re.search(r'(\d{1,2}\s+[A-Za-z]{3,}\s*,\s*\d{4})', section_text)
        if date_match:
            match_data['date'] = date_match.group(1).strip()
        
        # Extract time
        time_match = re.search(r'(\d{1,2}:\d{2}\s*(?:AM|PM))', section_text, re.I)
        if time_match:
            match_data['time'] = time_match.group(1).strip()
        
        # Check if any data was extracted
        if match_data['title'] or match_data['teams'] or match_data['league']:
            if 'Stream is active' in section_text or 'LIVE' in section_text.upper():
                match_data['status'] = 'LIVE'
            else:
                match_data['status'] = 'Unknown'
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
        
        matches = self.extract_match_data(html)
        
        if matches:
            print(f"✅ Found {len(matches)} match(es)\n")
            for i, match in enumerate(matches, 1):
                print(f"📌 MATCH #{i}")
                print(f"   🏷️  Title: {match.get('title', 'N/A')}")
                print(f"   ⚔️  Teams: {match.get('teams', 'N/A')}")
                print(f"   🏆  League: {match.get('league', 'N/A')}")
                print(f"   ⏱️  Runtime: {match.get('runtime', 'N/A')}")
                print(f"   👁️  Viewers: {match.get('viewers', 'N/A')}")
                print(f"   🌐  Servers: {match.get('servers', 'N/A')}")
                print(f"   📅  Date: {match.get('date', 'N/A')}")
                print(f"   🕐  Time: {match.get('time', 'N/A')}")
                print(f"   📡  Status: {match.get('status', 'N/A')}")
                print("-"*50)
            
            # Save to data directory
            self.save_data(matches)
        else:
            print("⚠️ No matches found.")
        
        return matches

    def save_data(self, matches):
        """Save data to files"""
        # Create data directory if it doesn't exist
        os.makedirs('data', exist_ok=True)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Save main JSON file
        json_file = 'data/matches.json'
        with open(json_file, 'w', encoding='utf-8') as f:
            json.dump({
                'timestamp': datetime.now().isoformat(),
                'total_matches': len(matches),
                'matches': matches
            }, f, indent=2, ensure_ascii=False)
        print(f"💾 JSON saved to: {json_file}")
        
        # Save historical data with timestamp
        history_file = f'data/matches_{timestamp}.json'
        with open(history_file, 'w', encoding='utf-8') as f:
            json.dump({
                'timestamp': datetime.now().isoformat(),
                'matches': matches
            }, f, indent=2, ensure_ascii=False)
        print(f"💾 Historical JSON saved to: {history_file}")
        
        # Save HTML report
        self.save_html_report(matches, timestamp)
        
        # Save markdown report
        self.save_markdown_report(matches, timestamp)

    def save_html_report(self, matches, timestamp):
        """Save HTML report"""
        html_file = f'data/report_{timestamp}.html'
        
        html_content = f"""<!DOCTYPE html>
<html>
<head>
    <title>Sportzfy Matches</title>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <style>
        body {{ font-family: -apple-system, Arial, sans-serif; background: #0b0e1a; color: #e0e8ff; padding: 20px; margin: 0; }}
        .container {{ max-width: 800px; margin: 0 auto; }}
        .header {{ background: linear-gradient(135deg, #1e3a8a, #3b82f6); padding: 20px; border-radius: 12px; margin-bottom: 20px; }}
        h1 {{ margin: 0; color: white; }}
        .timestamp {{ color: #9ca3af; font-size: 14px; }}
        .match {{ background: #151e30; border-radius: 12px; padding: 15px; margin: 15px 0; border-left: 4px solid #3b82f6; }}
        .title {{ color: #60a5fa; font-size: 18px; font-weight: bold; }}
        .label {{ color: #9ca3af; font-weight: 600; }}
        .value {{ color: #e0e8ff; }}
        .status-live {{ color: #34d399; font-weight: bold; }}
        .status-unknown {{ color: #fbbf24; }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🏏 Sportzfy Match Data</h1>
            <p class="timestamp">Scraped: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
            <p class="timestamp">Total Matches: {len(matches)}</p>
        </div>
"""
        
        for match in matches:
            status_class = "status-live" if match.get('status') == 'LIVE' else "status-unknown"
            html_content += f"""
        <div class="match">
            <div class="title">{match.get('title', 'Unknown Match')}</div>
            <div><span class="label">Teams:</span> <span class="value">{match.get('teams', 'N/A')}</span></div>
            <div><span class="label">League:</span> <span class="value">{match.get('league', 'N/A')}</span></div>
            <div><span class="label">Runtime:</span> <span class="value">{match.get('runtime', 'N/A')}</span></div>
            <div><span class="label">Viewers:</span> <span class="value">{match.get('viewers', 'N/A')}</span></div>
            <div><span class="label">Servers:</span> <span class="value">{match.get('servers', 'N/A')}</span></div>
            <div><span class="label">Date:</span> <span class="value">{match.get('date', 'N/A')}</span></div>
            <div><span class="label">Time:</span> <span class="value">{match.get('time', 'N/A')}</span></div>
            <div><span class="label">Status:</span> <span class="{status_class}">{match.get('status', 'Unknown')}</span></div>
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

---

"""
        
        for i, match in enumerate(matches, 1):
            md_content += f"""
## Match #{i}

- **Title:** {match.get('title', 'N/A')}
- **Teams:** {match.get('teams', 'N/A')}
- **League:** {match.get('league', 'N/A')}
- **Runtime:** {match.get('runtime', 'N/A')}
- **Viewers:** {match.get('viewers', 'N/A')}
- **Servers:** {match.get('servers', 'N/A')}
- **Date:** {match.get('date', 'N/A')}
- **Time:** {match.get('time', 'N/A')}
- **Status:** {match.get('status', 'Unknown')}

---
"""
        
        with open(md_file, 'w', encoding='utf-8') as f:
            f.write(md_content)
        print(f"📝 Markdown report saved to: {md_file}")

def main():
    scraper = SportzfyScraper()
    scraper.scrape()

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"❌ Error: {e}")
        # Create error log
        with open('error.log', 'w') as f:
            f.write(f"Error at {datetime.now().isoformat()}: {str(e)}")
