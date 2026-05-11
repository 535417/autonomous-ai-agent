"""
Multi-Agent Framework - supports DeepSeek, GLM, Groq, SiliconFlow
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
            max_tokens=8192
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
        2. 撰写 8-10 句详细摘要，涵盖：新闻背景、核心要点、行业意义
        3. 加上通俗解释，内容要充实，让大学生也看得懂
        4. 根据内容判断新闻所属领域（大模型技术/产品发布/融资并购/学术研究/行业应用/开源生态/政策监管）
        5. 只关注与 AI 技术相关的新闻，过滤掉纯商业营销或非技术动态的新闻
        6. 如果新闻内容过于简单或信息量不足，可以适当补充相关背景信息，但必须基于事实，不要无中生有。
        7.  每个英文必须有中文翻译，或者直接输出中文。

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
        基于采集步骤的结果，对以下新闻进行分类与重要性打分（1-10 分）：

        {collector_output['enriched_result']}

        前序推理上下文：
        {previous_context}

        分类维度：
        1. 重要性（1-10 分）
        2. 领域分类（大模型/产品发布/融资/学术研究/应用落地）
        3. 热度（高/中/低）

        请以 JSON 格式返回：{{"classified_news": [{{"title": "...", "importance": X, "domain": "...", "heat": "..."}}]}}
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
        基于已分类的新闻数据，识别当前 AI 行业的主要技术趋势和深度洞察：

        {classifier_output['classified_result']}

        推理链上下文：
        {previous_context}

        分析角度：
        1. 当前主流技术方向及其演进
        2. 融资热点与创业机会
        3. 开源生态变化与重要项目
        4. 市场机遇与潜在风险

        请以中文返回详细趋势分析（5-8 条核心观察）。
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
        基于前面的分类和分析结果，生成一份结构化的 AI 行业日报（Markdown 格式，全程中文）：

        分析结果：
        {analyst_output['analysis_result']}

        前序推理上下文：
        {previous_context}

        严格按以下结构输出（Markdown 格式）：

        # AI行业技术情报日报 | {report_date}

        **日期：{report_date}**

        ---

        ## 1. 今日AI核心动态（Top 5）
        [列出 5 条最重要的新闻，每条包含：标题、来源类型、行业意义]

        ## 2. 技术趋势分析
        [5-8 条趋势观察，每条需要有明确的趋势判断，而非简单新闻列举]

        ## 3. 值得关注的研究/项目（Top 3）
        [筛选今日最有价值的论文/产品/融资事件，说明为什么重要及可能影响的方向]

        ## 4. 行业观察结论
        [总结当前行业阶段、加速方向、潜在机遇与风险]
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
        请审核以下 AI 行业日报的质量，检查是否满足以下标准：
        1. 是否包含具体的数据或案例？
        2. 是否有明确的趋势判断（而非简单列举）？
        3. 是否覆盖了大模型/产品/融资/学术等主要维度？
        4. 是否有可操作的行业洞察？

        原始报告：
        {writer_output['report_markdown']}

        推理链摘要：
        {previous_context}

        如果报告质量需要改进，请指出具体问题并建议修改方案。
        如果报告质量良好，直接返回优化后的最终版本。

        最后返回最终版本报告（中文 Markdown）。
        """

        result = self.agent.execute(prompt)
        thinking_logger.log(self.name, writer_output, result, "已完成质量审核和最终优化")
        return result


# ---- Agent factory registry ----

AGENT_FACTORIES = {
    'deepseek': create_deepseek_agent,
    'glm': create_glm_agent,
    'groq': create_groq_agent,
    'siliconflow': create_siliconflow_agent,
}


class Orchestrator:
    """Orchestrator - manages the 5-agent workflow"""

    # Default agent assignments for each pipeline stage, with fallback order
    PIPELINE_CONFIG = [
        ('collector', ['glm', 'deepseek', 'groq', 'siliconflow']),
        ('classifier', ['groq', 'deepseek', 'siliconflow', 'glm']),
        ('analyst', ['deepseek', 'glm', 'groq', 'siliconflow']),
        ('writer', ['deepseek', 'glm', 'siliconflow', 'groq']),
        ('reviewer', ['siliconflow', 'deepseek', 'glm', 'groq']),
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
            raw_items = news_items[:20]
            news_list = "\n".join(
                f"{i+1}. {item}" for i, item in enumerate(raw_items)
            )
            degraded_report = f"""# AI行业技术情报日报 | {report_date}

---

## 1. 今日AI核心动态（Top 5）

{chr(10).join(f"{i+1}. {item.split(' (via ')[0] if ' (via ' in item else item}{'  [' + item.split('(via ')[1].rstrip(')') + ']' if '(via ' in item else ''}" for i, item in enumerate(raw_items[:5]))}

---

## 2. 技术趋势分析

本日采集覆盖了以下主要方向的技术动态，包括但不限于：大模型训练与推理基础设施、AI Agent 与多智能体系统、开源模型生态演进、AI 产品化与商业化落地、学术前沿研究等。

> **注意**：趋势深度分析需启用 LLM Agent。当前为基础新闻采集模式，下文列出全部采集到的新闻标题供参考。

---

## 3. 今日采集全部新闻标题

{news_list}

---

## 4. 行业观察说明

本报告当前处于**降级运行模式**，仅完成新闻采集与聚合，未进行 AI 驱动的深度分析。

如需获取包含**趋势判断、技术洞察与投资方向建议**的完整版 AI 行业技术情报日报，请：
1. 将 `.env.example` 复制为 `.env` 并填入至少一个 LLM 提供商的 API 密钥
2. 或在 GitHub Actions Secrets 中配置相应的 API 密钥

---

> *本报告由 AI Research Agent 自动生成于 {report_date}*
"""
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
