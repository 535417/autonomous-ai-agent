import os
import requests
import feedparser
from openai import OpenAI
from datetime import datetime
from datetime import datetime
from zoneinfo import ZoneInfo

tz = ZoneInfo("Asia/Shanghai")
today = datetime.now(tz).strftime("%Y-%m-%d")
report_date_display = datetime.now(tz).strftime("%Y年%m月%d日")
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
你是一个专业的AI技术情报分析助手，负责基于以下 AI 行业新闻：

{combined_news}整理为高质量技术趋势报告。

## 输入说明
你将收到经过处理的AI新闻列表，这些新闻已经：
- 来自多个信息源（VentureBeat / The Verge / arXiv / OpenAI Blog）
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


