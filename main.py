import os
import requests
import feedparser
from openai import OpenAI
from datetime import datetime
from dotenv import load_dotenv

# 加载环境变量

load_dotenv()

# 初始化 DeepSeek 客户端

client = OpenAI(
api_key=os.getenv("DEEPSEEK_API_KEY"),
base_url="https://api.deepseek.com"
)

# RSS 新闻源

rss_urls = [
    "https://venturebeat.com/category/ai/feed/",
    "https://www.theverge.com/ai/rss/index.xml",
    "https://export.arxiv.org/rss/cs.AI",
    "https://openai.com/blog/rss/"
]

news_items = []

# 获取新闻

for url in rss_urls:
    feed = feedparser.parse(url)
    source_title = feed.feed.get("title", url)
    for entry in feed.entries[:3]:
        title = entry.get("title", "").strip()
        if title:
            item = f"{title} ({source_title})"
            if item not in news_items:
                news_items.append(item)

# 合并新闻内容

combined_news = "\n".join(news_items[:15])

# 获取日期

today = datetime.now().strftime("%Y-%m-%d")
report_date_display = datetime.now().strftime("%Y年%m月%d日")

# Prompt

prompt = f"""
你是 AI 行业研究员。

请基于以下 AI 行业新闻：

{combined_news}

完成：

1. 中文摘要
2. 技术趋势分析
3. 商业价值判断
4. 风险分析

请将报告日期固定为 {report_date_display}，不要生成其他日期。

输出 Markdown 格式。
"""

# 调用 DeepSeek API

response = client.chat.completions.create(
    model="deepseek-chat",
    messages=[
        {
            "role": "user",
            "content": prompt
        }
    ]
)

# 获取 AI 输出结果

result = response.choices[0].message.content

# 创建 reports 文件夹

os.makedirs("reports", exist_ok=True)

# 写入 Markdown 文件

report_header = f"# AI Research Report - {today}\n\n**报告日期：** {report_date_display}\n\n"
with open(f"reports/{today}.md", "w", encoding="utf-8") as f:
    f.write(report_header + result)

print("AI report generated successfully!")
