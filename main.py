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
        print(f"  警告：抓取失败 {url}：{e}")
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
                print(f"  RSS： {len(entries[:max_per_source])} items from {source_title}")
            else:
                print(f"  RSS：无条目 {url}")
        except Exception as e:
            print(f"  RSS 错误： {url} - {e}")

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
            print(f"  HTML： {len(titles)} items from {url}")

    if not news_items:
        raise RuntimeError(
            '未从任何来源获取到新闻，请检查网络连接或稍后重试。'
        )

    return news_items[:max_total]


def create_report_file(report_date, report_body):
    """Save report to local file"""
    os.makedirs(REPORT_PATH, exist_ok=True)
    os.makedirs('logs', exist_ok=True)

    filename = os.path.join(REPORT_PATH, f'{report_date}.md')
    header = f"# AI 行业日报 - {report_date}\n\n**报告日期：** {report_date}\n\n"

    with open(filename, 'w', encoding='utf-8') as f:
        f.write(header + report_body)

    return filename


def check_env():
    """Check if .env file exists and has at least one API key configured"""
    if not os.path.exists('.env'):
        print("=" * 70)
        print("警告：未找到 .env 文件！")
        print("本程序至少需要一个 LLM API 密钥才能运行。")
        print("请复制 .env.example 到 .env 并填写你的 API 密钥：")
        print("  cp .env.example .env")
        print("（GitHub Actions 中请直接配置 Secrets，无需 .env 文件）")
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
    print(f"AI Research Digest Agent - 多 Agent 协作模式")
    print(f"报告日期：{report_date_display}")
    print(f"{'='*70}\n")

    # Phase 1: Collect news
    print("[阶段 1/2] 抓取新闻源中...")
    try:
        news_items = fetch_news_items(RSS_SOURCES, HTML_SOURCES)
        print(f"[完成] 成功采集 {len(news_items)} 条新闻\n")
    except Exception as e:
        print(f"[错误] 新闻采集失败：{e}")
        return

    # Phase 2: Multi-Agent Collaboration
    print("[阶段 2/2] 启动多 Agent 协作系统...")
    try:
        orchestrator = Orchestrator()
        final_report = orchestrator.run(news_items, report_date)

        # Save report
        filename = create_report_file(report_date, final_report)
        print(f"\n[完成] 报告已保存：{filename}")
        print(f"[完成] 推理链日志已保存：logs/thinking_chain_{report_date}.json")

    except Exception as e:
        print(f"[错误] 报告生成失败：{e}")
        import traceback
        traceback.print_exc()


if __name__ == '__main__':
    main()
