import os
from datetime import datetime
from zoneinfo import ZoneInfo

import feedparser
import requests
from bs4 import BeautifulSoup
from dotenv import load_dotenv
from openai import OpenAI

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


def load_api_key() -> str:
    load_dotenv()
    api_key = os.getenv('DEEPSEEK_API_KEY')
    if not api_key:
        raise RuntimeError('Missing required environment variable: DEEPSEEK_API_KEY')
    return api_key


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


def fetch_news_items(urls, max_per_source=3, max_total=15):
    news_items = []
    for url in urls:
        feed = feedparser.parse(url)
        source_title = url
        if hasattr(feed, 'feed') and isinstance(feed.feed, dict):
            source_title = feed.feed.get('title', url) or url

        entries = []
        if getattr(feed, 'entries', None):
            entries = [entry.get('title', '').strip() for entry in feed.entries if entry.get('title', '').strip()]

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


def build_prompt(news_items, report_date_display):
    combined_news = '\n'.join(news_items)
    return f"""
你是一个专业的AI技术情报分析助手，负责基于以下 AI 行业新闻：

{combined_news}整理为高质量技术趋势报告。

## 输入说明
你将收到经过处理的AI新闻列表，这些新闻已经：
- 来自十个 AI 行业来源（Chatbot News / The500Feed / AI News Hub / VentureBeat AI / TechCrunch AI / MIT Technology Review AI / Hugging Face Blog / OpenAI News / Anthropic News / DeepMind Discover Blog）
- 每个源已提取前3条新闻
- 已完成去重与合并
- 最终保留约15条最重要内容

这些内容可能包含标题、摘要或链接信息。

---

## 你的任务

请基于这些信息生成一份“AI行业技术情报日报”，要求不仅是摘要，而是分析型报告。

---

## 输出结构（必须严格遵守）

### 1. 今日AI核心动态（Top 5）
- 提炼最重要的5条新闻
- 每条必须包含：
  - 事件标题（简洁）
  - 来源类型（论文 / 公司动态 / 产品 / 行业新闻）
  - 一句话解释其意义（重点）

---

### 2. 技术趋势分析（必须有判断）
从以下角度归纳趋势：
- 模型能力演进（如 reasoning / multimodal / agent）
- 开源生态变化
- AI产品化方向
- 学术研究热点

要求：
- 不只是总结，要有“趋势判断”
- 可以合并多个新闻形成一个趋势

---

### 3. 值得关注的研究 / 项目（Top 3）
筛选最有价值的：
- arXiv论文
- 开源项目
- 技术突破

每条包括：
- 名称
- 为什么重要（技术意义）
- 可能影响的方向

---

### 4. 行业观察结论（必须输出）
用 5-8 句话总结：
- 当前AI行业处于什么阶段
- 哪些方向在加速
- 哪些方向在降温
- 下一步可能爆发的领域

要求：
- 必须是“分析”，不是复述新闻

---

## 风格要求
- 中文输出
- 专业、简洁
- 避免新闻列表堆砌
- 强调“趋势 + 判断 + 影响”
- 不要重复原始新闻内容

---

## 额外规则
如果信息不足：
- 可以合并分析
- 不允许空输出
- 不要编造不存在的新闻
请将报告日期固定为 {report_date_display}，不要生成其他日期。

输出 Markdown 格式。
"""


def create_report_file(report_date, report_body):
    os.makedirs(REPORT_PATH, exist_ok=True)
    filename = os.path.join(REPORT_PATH, f'{report_date}.md')
    header = f"# AI Research Report - {report_date}\n\n**报告日期：** {report_date}\n\n"
    with open(filename, 'w', encoding='utf-8') as f:
        f.write(header + report_body)
    return filename


def main():
    api_key = load_api_key()
    client = OpenAI(api_key=api_key, base_url='https://api.deepseek.com')

    news_items = fetch_news_items(RSS_URLS)
    report_date_display = datetime.now(TZ).strftime('%Y年%m月%d日')
    report_date = datetime.now(TZ).strftime('%Y-%m-%d')

    prompt = build_prompt(news_items, report_date_display)
    response = client.chat.completions.create(
        model='deepseek-chat',
        messages=[{'role': 'user', 'content': prompt}]
    )
    result = response.choices[0].message.content

    filename = create_report_file(report_date, result)
    print(f'AI report generated successfully: {filename}')


if __name__ == '__main__':
    main()
