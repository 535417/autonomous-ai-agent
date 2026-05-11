"""
AI Research Digest Agent - Main Program
Integrates multi-agent collaboration system with 5 different LLM providers
"""

import os
import sys

# Fix Windows GBK encoding issue - force UTF-8 output
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

from datetime import datetime
from zoneinfo import ZoneInfo

import feedparser
import requests
from bs4 import BeautifulSoup
from dotenv import load_dotenv

from agents import Orchestrator, thinking_logger

TZ = ZoneInfo('Asia/Shanghai')

# News sources: RSS feed URLs and HTML fallback URLs
RSS_SOURCES = [
    'https://huggingface.co/blog/feed.xml',
    'https://openai.com/news/rss.xml',
    'https://www.anthropic.com/news/feed.xml',
    'https://deepmind.google/discover/blog/feed.xml',
]

HTML_SOURCES = [
    'https://venturebeat.com/ai/',
    'https://techcrunch.com/category/artificial-intelligence/',
    'https://www.technologyreview.com/topic/artificial-intelligence/',
    'https://www.chatbotnews.ai/',
    'https://ainewshub.io/',
]

REPORT_PATH = 'reports'


def fetch_html_titles(url, max_titles=5):
    """Scrape article titles from HTML pages (fallback when RSS unavailable)"""
    try:
        response = requests.get(
            url,
            timeout=15,
            headers={
                'User-Agent': (
                    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 '
                    '(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36'
                )
            }
        )
        response.raise_for_status()
    except requests.RequestException as e:
        print(f"  WARNING: Failed to fetch {url}: {e}")
        return []

    soup = BeautifulSoup(response.text, 'html.parser')
    titles = []

    # Try page title and open graph title first
    page_title = soup.find('meta', property='og:title') or soup.find('title')
    if page_title:
        raw_title = page_title.get('content') if page_title.has_attr('content') else page_title.text
        if raw_title:
            titles.append(raw_title.strip())

    # Collect headings
    for selector in ['article h1', 'article h2', 'article h3', 'h1', 'h2', 'h3']:
        for element in soup.select(selector):
            text = element.get_text(separator=' ', strip=True)
            if text and len(text) > 15 and text not in titles:
                titles.append(text)
            if len(titles) >= max_titles:
                break
        if len(titles) >= max_titles:
            break

    # Fallback: collect meaningful link text
    if len(titles) < max_titles:
        for link in soup.select('a[href]'):
            text = link.get_text(separator=' ', strip=True)
            if text and len(text) > 20 and text not in titles:
                titles.append(text)
            if len(titles) >= max_titles:
                break

    return titles[:max_titles]


def fetch_news_items(rss_urls, html_urls, max_per_source=5, max_total=50):
    """Fetch news from RSS feeds and HTML pages"""
    news_items = []

    # Phase 1: Try RSS feeds
    for url in rss_urls:
        try:
            feed = feedparser.parse(url)
            source_title = url
            if hasattr(feed, 'feed') and isinstance(feed.feed, dict):
                source_title = feed.feed.get('title', url) or url

            entries = []
            if getattr(feed, 'entries', None):
                entries = [entry.get('title', '').strip() for entry in feed.entries
                          if entry.get('title', '').strip()]

            for title in entries[:max_per_source]:
                item = f"{title} (via {source_title})"
                if item not in news_items:
                    news_items.append(item)
                if len(news_items) >= max_total:
                    break

            if entries:
                print(f"  RSS: {len(entries[:max_per_source])} items from {source_title}")
            else:
                print(f"  RSS: No entries from {url}")
        except Exception as e:
            print(f"  RSS ERROR: {url} - {e}")

        if len(news_items) >= max_total:
            break

    # Phase 2: Scrape HTML sources
    for url in html_urls:
        if len(news_items) >= max_total:
            break
        titles = fetch_html_titles(url, max_per_source)
        for title in titles:
            item = f"{title} (via {url})"
            if item not in news_items:
                news_items.append(item)
            if len(news_items) >= max_total:
                break
        if titles:
            print(f"  HTML: {len(titles)} items from {url}")

    if not news_items:
        raise RuntimeError(
            'No news items fetched from any source. Please check your network connection '
            'or try again later.'
        )

    return news_items[:max_total]


def create_report_file(report_date, report_body):
    """Save report to local file"""
    os.makedirs(REPORT_PATH, exist_ok=True)
    os.makedirs('logs', exist_ok=True)

    filename = os.path.join(REPORT_PATH, f'{report_date}.md')
    header = f"# AI Research Report - {report_date}\n\n**Report Date:** {report_date}\n\n"

    with open(filename, 'w', encoding='utf-8') as f:
        f.write(header + report_body)

    return filename


def check_env():
    """Check if .env file exists and has at least one API key configured"""
    if not os.path.exists('.env'):
        print("=" * 70)
        print("WARNING: .env file not found!")
        print("The program needs at least one LLM API key to function.")
        print("Please copy .env.example to .env and fill in your API keys:")
        print("  cp .env.example .env")
        print("=" * 70)
        print()
        return False
    return True


def main():
    load_dotenv()
    check_env()

    report_date_display = datetime.now(TZ).strftime('%Y-%m-%d')
    report_date = datetime.now(TZ).strftime('%Y-%m-%d')

    print(f"\n{'='*70}")
    print(f"AI Research Digest Agent - Multi-Agent Collaboration")
    print(f"Report Date: {report_date_display}")
    print(f"{'='*70}\n")

    # Phase 1: Collect news
    print("[Phase 1/2] Fetching news sources...")
    try:
        news_items = fetch_news_items(RSS_SOURCES, HTML_SOURCES)
        print(f"[OK] Successfully collected {len(news_items)} news items\n")
    except Exception as e:
        print(f"[ERROR] News collection failed: {e}")
        return

    # Phase 2: Multi-Agent Collaboration
    print("[Phase 2/2] Starting multi-agent collaboration system...")
    try:
        orchestrator = Orchestrator()
        final_report = orchestrator.run(news_items, report_date)

        # Save report
        filename = create_report_file(report_date, final_report)
        print(f"\n[OK] Report saved: {filename}")
        print(f"[OK] Chain-of-thought log saved: logs/thinking_chain_{report_date}.json")

    except Exception as e:
        print(f"[ERROR] Report generation failed: {e}")
        import traceback
        traceback.print_exc()


if __name__ == '__main__':
    main()
