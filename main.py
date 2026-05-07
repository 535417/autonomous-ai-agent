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

rss_url = "https://hnrss.org/frontpage"

# 获取新闻

feed = feedparser.parse(rss_url)

news_items = []

# 提取前5条新闻

for entry in feed.entries[:5]:
    news_items.append(entry.title)

# 合并新闻内容

combined_news = "\n".join(news_items)

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

# 获取日期

today = datetime.now().strftime("%Y-%m-%d")

# 创建 reports 文件夹

os.makedirs("reports", exist_ok=True)

# 写入 Markdown 文件

with open(f"reports/{today}.md", "w", encoding="utf-8") as f:
    f.write(result)

print("AI report generated successfully!")
