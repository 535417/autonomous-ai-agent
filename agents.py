"""
Multi-Agent Framework - supports DeepSeek, GLM, Groq, Mistral, SiliconFlow
Chain-of-thought design: each agent's output feeds into the next agent
"""

import json
import os
import sys
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any, Dict, List, Optional
from zoneinfo import ZoneInfo

from dotenv import load_dotenv

TZ = ZoneInfo('Asia/Shanghai')


class ThinkingChainLogger:
    """Maintains the full chain-of-thought log"""

    def __init__(self):
        self.chain = []

    def log(self, agent_name: str, input_data: Any, output_data: Any, reasoning: str = ""):
        """Record an agent's reasoning step"""
        entry = {
            'timestamp': datetime.now(TZ).isoformat(),
            'agent': agent_name,
            'input': input_data if isinstance(input_data, (str, dict, list)) else str(input_data),
            'output': output_data if isinstance(output_data, (str, dict, list)) else str(output_data),
            'reasoning': reasoning
        }
        self.chain.append(entry)
        summary = reasoning[:80] + "..." if len(reasoning) > 80 else reasoning
        print(f"[{agent_name}] {summary}")

    def export_to_file(self, filename: str = "thinking_chain.json"):
        """Export chain-of-thought log"""
        dirname = os.path.dirname(filename)
        if dirname:
            os.makedirs(dirname, exist_ok=True)
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(self.chain, f, indent=2, ensure_ascii=False)
        print(f"Thinking chain exported to {filename}")

    def get_context(self) -> str:
        """Get current chain-of-thought summary"""
        summary = []
        for entry in self.chain[-3:]:
            summary.append(f"{entry['agent']}: {entry['reasoning']}")
        return "\n".join(summary)


thinking_logger = ThinkingChainLogger()


class Agent(ABC):
    """Base Agent class"""

    def __init__(self, name: str, model: str, api_key: Optional[str], base_url: Optional[str] = None):
        self.name = name
        self.model = model
        self.api_key = api_key
        self.base_url = base_url

    @property
    def is_available(self) -> bool:
        return self.api_key is not None

    @abstractmethod
    def execute(self, prompt: str, system_prompt: str = "") -> str:
        """Execute the agent's core logic"""
        pass


class OpenAICompatibleAgent(Agent):
    """Generic OpenAI-compatible API agent — single implementation for all providers"""

    def __init__(self, name: str, model: str, api_key: Optional[str], base_url: str):
        super().__init__(name, model, api_key, base_url)

    def call_llm(self, messages: List[Dict[str, str]]) -> str:
        if not self.api_key:
            raise RuntimeError(f"API key not configured for {self.name}")
        from openai import OpenAI
        client = OpenAI(api_key=self.api_key, base_url=self.base_url)
        response = client.chat.completions.create(
            model=self.model,
            messages=messages,
            temperature=0.7,
            max_tokens=4096
        )
        return response.choices[0].message.content

    def execute(self, prompt: str, system_prompt: str = "") -> str:
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})
        return self.call_llm(messages)


# ---- Agent factory functions ----

def create_deepseek_agent(name: str = "DeepSeekAgent") -> Optional[OpenAICompatibleAgent]:
    load_dotenv()
    api_key = os.getenv('DEEPSEEK_API_KEY')
    if not api_key:
        print(f"警告：DEEPSEEK_API_KEY 未找到，{name} 将被跳过")
        return None
    return OpenAICompatibleAgent(name, "deepseek-chat", api_key, "https://api.deepseek.com/v1")


def create_glm_agent(name: str = "GLMAgent") -> Optional[OpenAICompatibleAgent]:
    load_dotenv()
    api_key = os.getenv('GLM_API_KEY')
    if not api_key:
        print(f"警告：GLM_API_KEY 未找到，{name} 将被跳过")
        return None
    return OpenAICompatibleAgent(name, "glm-4", api_key, "https://open.bigmodel.cn/api/paas/v4")


def create_groq_agent(name: str = "GroqAgent") -> Optional[OpenAICompatibleAgent]:
    load_dotenv()
    api_key = os.getenv('GROQ_API_KEY')
    if not api_key:
        print(f"警告：GROQ_API_KEY 未找到，{name} 将被跳过")
        return None
    return OpenAICompatibleAgent(name, "mixtral-8x7b-32768", api_key, "https://api.groq.com/openai/v1")


def create_mistral_agent(name: str = "MistralAgent") -> Optional[OpenAICompatibleAgent]:
    load_dotenv()
    api_key = os.getenv('MISTRAL_API_KEY')
    if not api_key:
        print(f"警告：MISTRAL_API_KEY 未找到，{name} 将被跳过")
        return None
    return OpenAICompatibleAgent(name, "mistral-large-latest", api_key, "https://api.mistral.ai/v1")


def create_siliconflow_agent(name: str = "SiliconFlowAgent") -> Optional[OpenAICompatibleAgent]:
    load_dotenv()
    api_key = os.getenv('SILICONFLOW_API_KEY')
    if not api_key:
        print(f"警告：SILICONFLOW_API_KEY 未找到，{name} 将被跳过")
        return None
    return OpenAICompatibleAgent(name, "Qwen2-72B-Instruct", api_key, "https://api.siliconflow.cn/v1")


# ---- Pipeline Agents ----

class CollectorAgent:
    """Agent 1: Collector - fetch and summarize news"""

    def __init__(self, agent: Agent):
        self.agent = agent
        self.name = "Collector"

    def execute(self, news_items: List[str]) -> Dict[str, Any]:
        prompt = f"""
        你是一位专业的 AI 行业分析师。请仔细阅读以下 {len(news_items)} 条 AI 行业新闻，为每条新闻做详细处理。

        {chr(10).join(f"- {item}" for item in news_items[:20])}

        对每条新闻，请完成以下工作：
        1. 将标题翻译为流畅的中文
        2. 撰写 2-3 句详细摘要，涵盖：新闻背景、核心要点、行业意义
        3. 根据内容判断新闻所属领域（大模型技术/产品发布/融资并购/学术研究/行业应用/开源生态/政策监管）

        请以 JSON 格式返回：
        {{"enriched_news": [{{"title_cn": "中文标题", "title_en": "原始英文标题", "summary": "2-3句详细中文摘要", "domain": "领域"}}]}}

        注意：摘要必须具体、有信息量，不要泛泛而谈。
        """

        result = self.agent.execute(prompt)
        thinking_logger.log(self.name, news_items, result, "已采集并初步总结新闻内容")
        return {"raw_news": news_items, "enriched_result": result}


class ClassifierAgent:
    """Agent 2: Classifier - classify news importance"""

    def __init__(self, agent: Agent):
        self.agent = agent
        self.name = "Classifier"

    def execute(self, collector_output: Dict[str, Any]) -> Dict[str, Any]:
        previous_context = thinking_logger.get_context()

        prompt = f"""
        你是一位 AI 行业资深编辑。基于采集步骤已处理的新闻，请对以下每条新闻进行深度分类和评估：

        {collector_output['enriched_result']}

        前序推理上下文：
        {previous_context}

        对每条新闻，请给出：
        1. 重要性评分（1-10 分，基于技术创新度、行业影响力、商业价值综合判断）
        2. 领域分类（大模型技术/产品发布/融资并购/学术研究/行业应用/开源生态/政策监管）
        3. 热度评估（高/中/低）
        4. 一句话说明评分理由

        请以 JSON 格式返回：
        {{"classified_news": [{{"title": "...", "importance": X, "domain": "...", "heat": "...", "reason": "评分理由"}}]}}
        """

        result = self.agent.execute(prompt)
        thinking_logger.log(self.name, collector_output, result, "已完成新闻分类和评分")
        return {"collector_output": collector_output, "classified_result": result}


class AnalystAgent:
    """Agent 3: Analyst - deep trend analysis"""

    def __init__(self, agent: Agent):
        self.agent = agent
        self.name = "Analyst"

    def execute(self, classifier_output: Dict[str, Any]) -> Dict[str, Any]:
        previous_context = thinking_logger.get_context()

        prompt = f"""
        你是一位顶级 AI 行业分析师。基于已分类的高质量新闻数据，请进行深度趋势分析，挖掘行业信号。

        {classifier_output['classified_result']}

        推理链上下文：
        {previous_context}

        请从以下四个维度进行深度分析，每个维度至少输出 2 条具体观察（每条 150 字以上）：

        ## 1. 当前主流技术方向及其演进
        - 今天出现了哪些值得关注的技术突破或新方法？
        - 哪些技术路线正在获得更多关注？哪些在降温？
        - 请结合具体新闻给出你的判断依据。

        ## 2. 融资热点与创业机会
        - 哪些细分赛道获得了资本重点关注？
        - 创业公司的产品思路有什么共性或创新点？
        - 对创业者和投资者有什么启示？

        ## 3. 开源生态变化与重要项目
        - 开源社区有哪些值得关注的新项目或更新？
        - 开源与商业方案的竞争格局有何变化？
        - 对开发者生态有什么影响？

        ## 4. 市场机遇与潜在风险
        - 哪些方向可能成为下一阶段的增长点？
        - 存在哪些需要警惕的风险信号？
        - 对从业者有什么可操作的建议？

        注意：必须基于具体新闻进行分析，每条观点必须有新闻事实支撑。避免空洞的套话和泛泛而谈。
        请以中文返回详细分析结果。
        """

        result = self.agent.execute(prompt)
        thinking_logger.log(self.name, classifier_output, result, "已完成深度趋势分析")
        return {"classifier_output": classifier_output, "analysis_result": result}


class WriterAgent:
    """Agent 4: Writer - organize into report"""

    def __init__(self, agent: Agent):
        self.agent = agent
        self.name = "Writer"

    def execute(self, analyst_output: Dict[str, Any], report_date: str) -> Dict[str, Any]:
        previous_context = thinking_logger.get_context()

        prompt = f"""
        你是一位资深的 AI 行业媒体主编。请基于前面的深度分析结果，撰写一份高质量的 AI 行业技术情报日报。

        分析结果：
        {analyst_output['analysis_result']}

        前序推理上下文：
        {previous_context}

        ---
        ## 报告要求

        严格按以下结构输出（Markdown 格式，全程中文）。每个章节必须内容充实，拒绝空洞套话。

        # AI行业技术情报日报 | {report_date}

        **日期：{report_date}**

        ---

        ## 1. 今日AI核心动态（Top 5）

        从新闻中精选 5 条最重要的动态，每条按以下格式详细展开（每条至少 200 字）：

        ### 1.1 [中文标题]
        - **来源**：[来源名称与链接]
        - **事件概述**：用 2-3 句话描述发生了什么
        - **行业意义**：为什么这件事值得关注？它会如何影响行业格局？
        - **相关背景**：补充必要的背景信息帮助读者理解

        （以此类推，共 5 条）

        ## 2. 技术趋势分析

        基于今天的新闻，提炼 5-8 条具体趋势（不是概括，而是有论据支撑的判断）。每条至少 150 字：
        - **趋势 N**：[一句话趋势判断]
          - 支撑新闻：[引用具体新闻]
          - 趋势分析：[展开论述，说明这个趋势的前因后果和未来走向]

        ## 3. 值得关注的研究/项目（Top 3）

        筛选今天最有价值的 3 个论文/产品/融资事件/开源项目：
        - **为什么重要**：技术突破性在哪？或商业价值多大？
        - **可能影响的方向**：会影响哪些领域？
        - **建议关注人群**：研究者/开发者/创业者/投资者

        ## 4. 行业观察结论

        总结当前 AI 行业所处阶段，指出：
        - 正在加速的方向（2-3 个）
        - 正在降温的方向（1-2 个）
        - 下一步可能爆发的领域（1-2 个具体判断）
        - 对从业者的建议（至少 2 条可操作建议）

        ---
        注意：全文必须基于今天的具体新闻，不要写泛泛而谈的套话。每个结论都要有新闻事实支撑。
        如果内容长度不足，请补充更多的背景分析、数据或行业对比。
        """

        result = self.agent.execute(prompt)
        thinking_logger.log(self.name, analyst_output, result, "已生成结构化报告")
        return {"analyst_output": analyst_output, "report_markdown": result}


class ReviewerAgent:
    """Agent 5: Reviewer - quality review and supplement"""

    def __init__(self, agent: Agent):
        self.agent = agent
        self.name = "Reviewer"

    def execute(self, writer_output: Dict[str, Any]) -> str:
        previous_context = thinking_logger.get_context()

        prompt = f"""
        你是 AI 行业日报的最终审稿人。请严格审核以下报告，确保质量达到专业媒体水准：

        原始报告：
        {writer_output['report_markdown']}

        推理链摘要：
        {previous_context}

        审核清单（逐项检查）：
        1. 每条核心动态是否包含：具体事件描述、行业意义、相关背景？信息密度是否足够？
        2. 技术趋势分析是否有明确的趋势判断（而非简单新闻罗列）？是否有具体论据支撑？
        3. 是否覆盖了大模型/产品/融资/学术/开源/应用等主要维度？
        4. 行业观察是否有可操作的洞察和建议（而非泛泛总结）？
        5. 全文长度是否充实？如果某章节内容偏短，请补充扩展。

        修改原则：
        - 如果报告质量良好但某些部分不够深入，请在保留原有结构的基础上补充扩展
        - 如果存在明显遗漏（如某条重要新闻未被覆盖），请补充
        - 如果内容空洞、套话过多，请重写相关段落，注入具体信息和判断
        - 保持中文表达的专业性和可读性

        最终输出完整的、经过审核优化的最终版本报告（中文 Markdown）。
        """

        result = self.agent.execute(prompt)
        thinking_logger.log(self.name, writer_output, result, "已完成质量审核和最终优化")
        return result


# ---- Agent factory registry ----

AGENT_FACTORIES = {
    'deepseek': create_deepseek_agent,
    'glm': create_glm_agent,
    'groq': create_groq_agent,
    'mistral': create_mistral_agent,
    'siliconflow': create_siliconflow_agent,
}


def _build_degraded_report(news_items, report_date):
    """Build a structured Chinese report from raw news items without LLM assistance."""
    import re

    # Parse items into (title, source) pairs
    parsed = []
    for item in news_items[:30]:
        # Parse: "Title | 来源：[Name](url) (link)"
        title_part = item
        source_name = ""
        source_url = ""

        # Try to extract source info from the new format
        source_match = re.search(r'\|\s*来源：\[([^\]]+)\]\(([^)]+)\)', item)
        if source_match:
            title_part = item[:source_match.start()].strip()
            source_name = source_match.group(1)
            source_url = source_match.group(2)
        elif ' (via ' in item:
            title_part = item.split(' (via ')[0]
            source_name = item.split('(via ')[1].rstrip(')')
        parsed.append({
            'title': title_part,
            'source_name': source_name,
            'source_url': source_url,
        })

    # Group by source
    from collections import defaultdict
    by_source = defaultdict(list)
    for p in parsed:
        by_source[p['source_name'] or '其他来源'].append(p)

    # Build sections
    # Section 1: Top 5
    top5_lines = []
    for i, p in enumerate(parsed[:5], 1):
        src = f"[{p['source_name']}]({p['source_url']})" if p['source_url'] else p['source_name']
        top5_lines.append(f"{i}. **{p['title']}**\n   - 来源：{src}")
    top5_section = "\n\n".join(top5_lines)

    # Section 2: All items by source
    by_source_lines = []
    for source, items in by_source.items():
        by_source_lines.append(f"### {source}（{len(items)} 条）")
        for item in items:
            by_source_lines.append(f"- {item['title']}")
    by_source_section = "\n\n".join(by_source_lines)

    # Section 3: Full list
    full_list = "\n".join(
        f"{i+1}. {p['title']}  "
        f"{'([' + p['source_name'] + '](' + p['source_url'] + '))' if p['source_url'] else ''}"
        for i, p in enumerate(parsed)
    )

    # Detect topic keywords for rough categorization
    keywords_map = {
        '大模型与训练': ['LLM', 'GPT', 'Claude', 'Gemini', 'Llama', 'model', 'training', 'pretraining', 'RL', 'MoE', 'mixture of experts', '大模型', '预训练', '微调'],
        'AI Agent 与系统': ['Agent', 'agentic', 'Multi-Agent', 'tool', 'orchestration', '工作流', '自动化'],
        '开源与工具': ['Open', 'open source', 'GitHub', 'Hugging Face', 'vLLM', '开源', '框架', '工具'],
        'AI 产品与商业化': ['product', 'enterprise', 'scaling', 'customer', 'Parloa', '企业', '产品', '服务'],
        '基础设施与算力': ['GPU', 'AMD', 'MI300X', 'infrastructure', 'Cloud', '算力', '数据中心', '部署'],
    }
    topic_counts = {k: 0 for k in keywords_map}
    for p in parsed:
        title_lower = p['title'].lower()
        for topic, kws in keywords_map.items():
            if any(kw.lower() in title_lower for kw in kws):
                topic_counts[topic] += 1

    topic_lines = []
    for topic, count in sorted(topic_counts.items(), key=lambda x: -x[1]):
        if count > 0:
            topic_lines.append(f"- **{topic}**：{count} 条相关新闻")
    topic_section = "\n".join(topic_lines) if topic_lines else "今日新闻覆盖多个 AI 细分领域。"

    return f"""# AI行业技术情报日报 | {report_date}

**日期：{report_date}**

---

## 1. 今日AI核心动态（Top 5）

{top5_section}

---

## 2. 技术趋势分析

> **注意**：当前为降级运行模式，以下趋势方向基于关键词自动识别，仅供参考。深度分析需启用 LLM Agent。

本日采集覆盖的主要技术方向：

{topic_section}

---

## 3. 按来源分类的新闻汇总

{by_source_section}

---

## 4. 今日采集全部新闻标题

{full_list}

---

## 5. 行业观察说明

本报告当前处于**降级运行模式**，已完成新闻采集、聚合与初步分类，但未进行 AI 驱动的深度分析。

如需获取包含以下内容的完整版 AI 行业技术情报日报：
- 每条新闻的深度解读与行业影响分析
- 具体的技术趋势判断（有论据支撑）
- 投资与创业方向建议
- 值得关注的论文/项目/产品推荐

请配置 LLM API 密钥：
1. 本地运行：将 `.env.example` 复制为 `.env` 并填入至少一个 API 密钥
2. GitHub Actions：在仓库 Settings > Secrets 中配置相应的 API 密钥

---

> *本报告由 AI Research Agent 自动生成于 {report_date}*
> *共采集 {len(news_items)} 条新闻，覆盖 {len(by_source)} 个来源*
"""


class Orchestrator:
    """Orchestrator - manages the 5-agent workflow"""

    # Default agent assignments for each pipeline stage, with fallback order
    PIPELINE_CONFIG = [
        ('collector', ['glm', 'deepseek', 'groq', 'mistral', 'siliconflow']),
        ('classifier', ['groq', 'deepseek', 'siliconflow', 'mistral', 'glm']),
        ('analyst', ['deepseek', 'glm', 'mistral', 'groq', 'siliconflow']),
        ('writer', ['mistral', 'deepseek', 'glm', 'siliconflow', 'groq']),
        ('reviewer', ['siliconflow', 'deepseek', 'glm', 'groq', 'mistral']),
    ]

    def __init__(self):
        self.agents: Dict[str, Any] = {}

        for role, provider_order in self.PIPELINE_CONFIG:
            agent = self._try_create_agent(role, provider_order)
            self.agents[role] = agent

        available = [k for k, v in self.agents.items() if v is not None]
        if not available:
            print("警告：无可用 LLM Agent，将在完全降级模式下运行。")
            print("如需启用 AI 驱动报告，请在 .env 或 GitHub Secrets 中配置至少一个 API 密钥。")
        else:
            print(f"已初始化的 Agent：{available}")

    def _try_create_agent(self, role: str, provider_order: List[str]):
        """Try to create an agent for a role, falling back through the provider list"""
        pipeline_cls_map = {
            'collector': CollectorAgent,
            'classifier': ClassifierAgent,
            'analyst': AnalystAgent,
            'writer': WriterAgent,
            'reviewer': ReviewerAgent,
        }
        pipeline_cls = pipeline_cls_map[role]

        for provider in provider_order:
            factory = AGENT_FACTORIES.get(provider)
            if not factory:
                continue
            agent = factory(f"{provider}-{role}")
            if agent is not None:
                return pipeline_cls(agent)

        print(f"警告：{role} Agent 无可用 API 密钥，将使用降级模式")
        return None

    def run(self, news_items: List[str], report_date: str) -> str:
        """Execute the complete 5-agent collaboration workflow"""
        print(f"\n{'='*60}")
        print("启动多 Agent 协作流程")
        print(f"{'='*60}\n")

        # Step 1: Collector
        print("[步骤 1/5] 采集器处理中...")
        if self.agents['collector']:
            collector_output = self.agents['collector'].execute(news_items)
        else:
            print("降级模式：跳过采集器，使用原始新闻")
            collector_output = {"raw_news": news_items, "enriched_result": "\n".join(news_items)}

        # Step 2: Classifier
        print("[步骤 2/5] 分类器处理中...")
        if self.agents['classifier']:
            classifier_output = self.agents['classifier'].execute(collector_output)
        else:
            print("降级模式：跳过分类器")
            classifier_output = {"collector_output": collector_output, "classified_result": "新闻分类功能不可用"}

        # Step 3: Analyst
        print("[步骤 3/5] 分析师处理中...")
        if self.agents['analyst']:
            analyst_output = self.agents['analyst'].execute(classifier_output)
        else:
            print("降级模式：跳过分析师")
            analyst_output = {"classifier_output": classifier_output, "analysis_result": "趋势分析功能不可用"}

        # Step 4: Writer
        print("[步骤 4/5] 撰写师处理中...")
        if self.agents['writer']:
            writer_output = self.agents['writer'].execute(analyst_output, report_date)
        else:
            print("降级模式：基于新闻标题生成中文结构化基础报告")
            degraded_report = _build_degraded_report(news_items, report_date)
            writer_output = {"analyst_output": analyst_output, "report_markdown": degraded_report}

        # Step 5: Reviewer
        print("[步骤 5/5] 评审师处理中...")
        if self.agents['reviewer']:
            final_report = self.agents['reviewer'].execute(writer_output)
        else:
            print("降级模式：跳过评审师")
            final_report = writer_output['report_markdown']

        print(f"\n{'='*60}")
        print("多 Agent 协作流程完成！")
        print(f"{'='*60}\n")

        # Export chain-of-thought log
        thinking_logger.export_to_file(f"logs/thinking_chain_{report_date}.json")

        return final_report
