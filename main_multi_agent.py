"""
AI Research Digest Agent - 主程序
集成多 Agent 协作系统，支持 5 个不同的 LLM 提供商
"""

import os
from datetime import datetime
from zoneinfo import ZoneInfo

import feedparser
import requests
from bs4 import BeautifulSoup
from dotenv import load_dotenv

from agents import Orchestrator, thinking_logger

TZ = ZoneInfo('Asia/Shanghai')

RSS_URLS = [
    'https://www.chatbotnews.ai/',
    'https://www.the500feed.com/',
    'https://ainewshub.io/',
    'https://venturebeat.com/ai/',
    'https://techcrunch.com/category/artificial-intelligence/',
    'https://www.technologyreview.com/topic/artificial-intelligence/',
    'https://huggingface.co/blog',
    'https://openai.com/news/',
    'https://www.anthropic.com/news',
    'https://deepmind.google/discover/blog/'
]

REPORT_PATH = 'reports'


def fetch_html_titles(url, max_titles=3):
    try:
        response = requests.get(
            url,
            timeout=12,
            headers={
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 '
                              '(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36'
            }
        )
        response.raise_for_status()
    except requests.RequestException:
        return []

    soup = BeautifulSoup(response.text, 'html.parser')
    titles = []

    # Try page title and open graph title
    page_title = (soup.find('meta', property='og:title') or soup.find('title'))
    if page_title:
        raw_title = page_title.get('content') if page_title.has_attr('content') else page_title.text
        if raw_title:
            titles.append(raw_title.strip())

    # Collect headings from the page
    for selector in ['article h1', 'article h2', 'article h3', 'h1', 'h2', 'h3']:
        for element in soup.select(selector):
            text = element.get_text(separator=' ', strip=True)
            if text and text not in titles:
                titles.append(text)
            if len(titles) >= max_titles:
                break
        if len(titles) >= max_titles:
            break

    # Fallback: collect meaningful links with text
    if len(titles) < max_titles:
        for link in soup.select('a[href]'):
            text = link.get_text(separator=' ', strip=True)
            if text and len(text) > 20 and text not in titles:
                titles.append(text)
            if len(titles) >= max_titles:
                break

    return titles[:max_titles]


def fetch_news_items(urls, max_per_source=5, max_total=50):
    """获取新闻（支持 RSS 和 HTML 解析双链路）"""
    news_items = []
    
    for url in urls:
        feed = feedparser.parse(url)
        source_title = url
        
        if hasattr(feed, 'feed') and isinstance(feed.feed, dict):
            source_title = feed.feed.get('title', url) or url

        entries = []
        if getattr(feed, 'entries', None):
            entries = [entry.get('title', '').strip() for entry in feed.entries 
                      if entry.get('title', '').strip()]

        if not entries:
            entries = fetch_html_titles(url, max_per_source)

        for title in entries[:max_per_source]:
            item = f"{title} ({source_title})"
            if item not in news_items:
                news_items.append(item)
            if len(news_items) >= max_total:
                break
        
        if len(news_items) >= max_total:
            break

    if not news_items:
        raise RuntimeError('未从配置的数据源中获取到任何新闻，请检查信息源是否可用。')
    
    return news_items[:max_total]


def create_report_file(report_date, report_body):
    """保存报告到本地"""
    os.makedirs(REPORT_PATH, exist_ok=True)
    os.makedirs('logs', exist_ok=True)
    
    filename = os.path.join(REPORT_PATH, f'{report_date}.md')
    header = f"# AI Research Report - {report_date}\n\n**报告日期：** {report_date}\n\n"
    
    with open(filename, 'w', encoding='utf-8') as f:
        f.write(header + report_body)
    
    return filename


def main():
    load_dotenv()
    
    report_date_display = datetime.now(TZ).strftime('%Y年%m月%d日')
    report_date = datetime.now(TZ).strftime('%Y-%m-%d')

    print(f"\n{'='*70}")
    print(f"AI Research Digest Agent - 多 Agent 协作版本")
    print(f"报告日期：{report_date_display}")
    print(f"{'='*70}\n")

    # 第一阶段：采集新闻
    print("[阶段 1/2] 采集新闻源中...")
    try:
        news_items = fetch_news_items(RSS_URLS)
        print(f"✓ 成功采集 {len(news_items)} 条新闻")
    except Exception as e:
        print(f"✗ 新闻采集失败：{e}")
        return

    # 第二阶段：多 Agent 协作生成报告
    print(f"\n[阶段 2/2] 启动多 Agent 协作系统...")
    try:
        orchestrator = Orchestrator()
        final_report = orchestrator.run(news_items, report_date)
        
        # 保存报告
        filename = create_report_file(report_date, final_report)
        print(f"\n✓ 报告已保存：{filename}")
        print(f"✓ 推理链日志已保存至 logs/thinking_chain_{report_date}.json")
        
    except Exception as e:
        print(f"✗ 报告生成失败：{e}")
        raise


if __name__ == '__main__':
    main()
