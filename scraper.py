#!/usr/bin/env python3
"""
Sportzfy Scraper - Using Playwright for JavaScript rendering
Works in GitHub Actions
"""

import asyncio
from playwright.async_api import async_playwright
import json
import re
from datetime import datetime
import os

class SportzfyScraper:
    def __init__(self):
        self.base_url = "https://sportzfy.my.id"
        
    async def scrape(self):
        """Main scraping method using Playwright"""
        print("\n" + "="*60)
        print("🏏 SPORTZFY SCRAPER (Playwright)")
        print("="*60 + "\n")
        
        async with async_playwright() as p:
            # Launch browser
            browser = await p.chromium.launch(headless=True)
            page = await browser.new_page()
            
            # Go to page
            print(f"📡 Fetching: {self.base_url}")
            await page.goto(self.base_url, wait_until='networkidle')
            
            # Wait for match cards to load
            try:
                await page.wait_for_selector('.match-card', timeout=15000)
                print("✅ Page loaded with JavaScript content")
            except:
                print("⚠️ Timeout waiting for match cards")
            
            # Get HTML content
            html = await page.content()
            
            # Extract matches
            matches = await self.extract_matches(page)
            
            await browser.close()
            
            if matches:
                # Save to JSON
                os.makedirs('data', exist_ok=True)
                with open('data/matches.json', 'w', encoding='utf-8') as f:
                    json.dump({
                        'timestamp': datetime.now().isoformat(),
                        'total_matches': len(matches),
                        'matches': matches
                    }, f, indent=2, ensure_ascii=False)
                
                # Display summary
                live_matches = [m for m in matches if m.get('status') == 'live']
                print(f"\n✅ Found {len(matches)} matches")
                print(f"📊 Live: {len(live_matches)}")
                
                print("\n📋 LIVE MATCHES:")
                for i, match in enumerate(live_matches[:10], 1):
                    print(f"{i}. {match.get('title')}")
                    print(f"   League: {match.get('league')}")
                    print(f"   Viewers: {match.get('viewers')}")
                    print()
                
                return matches
            else:
                print("❌ No matches found")
                return []
    
    async def extract_matches(self, page):
        """Extract match data using JavaScript evaluation"""
        matches = await page.evaluate('''
            () => {
                const cards = document.querySelectorAll('.match-card');
                const results = [];
                
                cards.forEach(card => {
                    const status = card.dataset.status;
                    const match = {
                        title: null,
                        league: null,
                        status: status === 'recent' ? 'live' : status,
                        sport: card.dataset.sport || null,
                        viewers: null,
                        match_url: null,
                        match_id: card.dataset.matchId || null
                    };
                    
                    // Get title
                    const titleDiv = card.querySelector('.match-main-title');
                    if (titleDiv) {
                        const link = titleDiv.querySelector('a');
                        if (link) {
                            match.title = link.textContent.trim();
                            match.match_url = link.href || null;
                        }
                    }
                    
                    // Get league
                    const leagueDiv = card.querySelector('.league-title');
                    if (leagueDiv) {
                        match.league = leagueDiv.textContent.trim();
                    }
                    
                    // Get viewers
                    const viewText = card.querySelector('.view-text');
                    if (viewText) {
                        match.viewers = viewText.textContent.trim();
                    }
                    
                    results.push(match);
                });
                
                return results;
            }
        ''')
        
        return matches

async def main():
    scraper = SportzfyScraper()
    matches = await scraper.scrape()
    
    if matches:
        live_matches = [m for m in matches if m.get('status') == 'live']
        print(f"\n🎯 Total Live Matches: {len(live_matches)}")
    else:
        print("\n❌ No matches found")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n⚠️ Interrupted")
    except Exception as e:
        print(f"\n❌ Error: {e}")
