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
            temperature=0.7
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
        分析以下 {len(news_items)} 条 AI 行业新闻标题，为每条新闻补充一句简短的中文摘要：

        {chr(10).join(f"- {item}" for item in news_items[:15])}

        请以 JSON 格式返回：{{"enriched_news": [{{"title": "...", "summary": "..."}}]}}
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

        报告结构（Markdown 格式）：
        # AI 行业日报 - {report_date}

        ## 今日核心动态（Top 5）
        [列出 5 条最重要的新闻 + 来源 + 行业意义]

        ## 技术趋势分析
        [基于分析结果展开 5-8 条趋势观察，每一条需要有具体判断而非泛泛列举]

        ## 值得关注的项目（Top 3）
        [筛选今日最有价值的论文/产品/融资事件，说明为什么重要]

        ## 行业观察结论
        [总结当前行业阶段、加速方向、潜在机遇]
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
    'mistral': create_mistral_agent,
    'siliconflow': create_siliconflow_agent,
}


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
            print("降级模式：基于新闻标题生成基础报告")
            # Generate a basic report from raw news items
            raw_items = news_items[:20]
            news_list = "\n".join(f"- {item}" for item in raw_items)
            degraded_report = f"""# AI 行业日报 - {report_date}

## 今日采集新闻标题

{news_list}

---
*注：本报告为未启用 LLM Agent 的基础版本（可能原因：API 密钥未配置）。请在 GitHub Secrets 中配置至少一个 API 密钥以获得 AI 驱动的完整分析报告。*
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
