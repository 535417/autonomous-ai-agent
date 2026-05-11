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
        print(f"Warning: DEEPSEEK_API_KEY not found, {name} will be skipped")
        return None
    return OpenAICompatibleAgent(name, "deepseek-chat", api_key, "https://api.deepseek.com/v1")


def create_glm_agent(name: str = "GLMAgent") -> Optional[OpenAICompatibleAgent]:
    load_dotenv()
    api_key = os.getenv('GLM_API_KEY')
    if not api_key:
        print(f"Warning: GLM_API_KEY not found, {name} will be skipped")
        return None
    return OpenAICompatibleAgent(name, "glm-4", api_key, "https://open.bigmodel.cn/api/paas/v4")


def create_groq_agent(name: str = "GroqAgent") -> Optional[OpenAICompatibleAgent]:
    load_dotenv()
    api_key = os.getenv('GROQ_API_KEY')
    if not api_key:
        print(f"Warning: GROQ_API_KEY not found, {name} will be skipped")
        return None
    return OpenAICompatibleAgent(name, "mixtral-8x7b-32768", api_key, "https://api.groq.com/openai/v1")


def create_mistral_agent(name: str = "MistralAgent") -> Optional[OpenAICompatibleAgent]:
    load_dotenv()
    api_key = os.getenv('MISTRAL_API_KEY')
    if not api_key:
        print(f"Warning: MISTRAL_API_KEY not found, {name} will be skipped")
        return None
    return OpenAICompatibleAgent(name, "mistral-large-latest", api_key, "https://api.mistral.ai/v1")


def create_siliconflow_agent(name: str = "SiliconFlowAgent") -> Optional[OpenAICompatibleAgent]:
    load_dotenv()
    api_key = os.getenv('SILICONFLOW_API_KEY')
    if not api_key:
        print(f"Warning: SILICONFLOW_API_KEY not found, {name} will be skipped")
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
        Analyze the following {len(news_items)} AI industry news titles, add a one-sentence summary for each:

        {chr(10).join(f"- {item}" for item in news_items[:15])}

        Return JSON format: {{"enriched_news": [{{title: "...", summary: "..."}}]}}
        """

        result = self.agent.execute(prompt)
        thinking_logger.log(self.name, news_items, result, "Collected and summarized news items")
        return {"raw_news": news_items, "enriched_result": result}


class ClassifierAgent:
    """Agent 2: Classifier - classify news importance"""

    def __init__(self, agent: Agent):
        self.agent = agent
        self.name = "Classifier"

    def execute(self, collector_output: Dict[str, Any]) -> Dict[str, Any]:
        previous_context = thinking_logger.get_context()

        prompt = f"""
        Based on the collector step results, classify the following news (importance score 1-10):

        {collector_output['enriched_result']}

        Previous context:
        {previous_context}

        Classification dimensions:
        1. Importance (1-10)
        2. Domain (Model/Product/Funding/Academic/Application)
        3. Heat (High/Medium/Low)

        Return JSON format: {{"classified_news": [{{title: "...", importance: X, domain: "...", heat: "..."}}]}}
        """

        result = self.agent.execute(prompt)
        thinking_logger.log(self.name, collector_output, result, "Completed news classification and scoring")
        return {"collector_output": collector_output, "classified_result": result}


class AnalystAgent:
    """Agent 3: Analyst - deep trend analysis"""

    def __init__(self, agent: Agent):
        self.agent = agent
        self.name = "Analyst"

    def execute(self, classifier_output: Dict[str, Any]) -> Dict[str, Any]:
        previous_context = thinking_logger.get_context()

        prompt = f"""
        Based on the classified news data, identify key technology trends and industry insights:

        {classifier_output['classified_result']}

        Chain-of-thought context:
        {previous_context}

        Analysis angles:
        1. Current mainstream technology directions
        2. Funding hotspots and startup trends
        3. Open-source ecosystem evolution
        4. Potential market opportunities

        Return detailed trend analysis in Chinese (5-8 key observations)
        """

        result = self.agent.execute(prompt)
        thinking_logger.log(self.name, classifier_output, result, "Completed deep trend analysis")
        return {"classifier_output": classifier_output, "analysis_result": result}


class WriterAgent:
    """Agent 4: Writer - organize into report"""

    def __init__(self, agent: Agent):
        self.agent = agent
        self.name = "Writer"

    def execute(self, analyst_output: Dict[str, Any], report_date: str) -> Dict[str, Any]:
        previous_context = thinking_logger.get_context()

        prompt = f"""
        Based on the classification and analysis results, generate a structured AI industry daily report (Markdown):

        Analysis results:
        {analyst_output['analysis_result']}

        Previous context:
        {previous_context}

        Report structure (Markdown format):
        # AI Research Report - {report_date}

        ## Today's Core Developments (Top 5)
        [List 5 most important news + source + significance]

        ## Technology Trend Analysis
        [Expand 5-8 trend observations based on analysis results]

        ## Projects Worth Watching (Top 3)
        [Filter most valuable papers/products/funding events]

        ## Industry Observations & Conclusions
        [Summarize current phase, acceleration directions, potential opportunities]
        """

        result = self.agent.execute(prompt)
        thinking_logger.log(self.name, analyst_output, result, "Generated structured report")
        return {"analyst_output": analyst_output, "report_markdown": result}


class ReviewerAgent:
    """Agent 5: Reviewer - quality review and supplement"""

    def __init__(self, agent: Agent):
        self.agent = agent
        self.name = "Reviewer"

    def execute(self, writer_output: Dict[str, Any]) -> str:
        previous_context = thinking_logger.get_context()

        prompt = f"""
        Review the quality of the following AI industry daily report, check for these issues:
        1. Does it include specific data/cases?
        2. Are there clear trend judgments (not just simple lists)?
        3. Does it cover major dimensions like Model/Product/Funding/Academic?
        4. Are there actionable industry insights?

        Original report:
        {writer_output['report_markdown']}

        Chain summary:
        {previous_context}

        If the report quality needs improvement, point out specific issues and suggest improvements.
        If the report quality is good, return the improved final version directly.

        Finally return the final version report (Markdown).
        """

        result = self.agent.execute(prompt)
        thinking_logger.log(self.name, writer_output, result, "Completed quality review and final optimization")
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
            print("WARNING: No LLM agents available. Running in fully degraded mode.")
            print("To enable AI-powered reports, copy .env.example to .env and set at least one API key.")
        else:
            print(f"Initialized agents: {available}")

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

        print(f"Warning: No API key available for {role} agent, it will use degraded mode")
        return None

    def run(self, news_items: List[str], report_date: str) -> str:
        """Execute the complete 5-agent collaboration workflow"""
        print(f"\n{'='*60}")
        print("Starting Multi-Agent Collaboration Workflow")
        print(f"{'='*60}\n")

        # Step 1: Collector
        print("[Step 1/5] Collector processing...")
        if self.agents['collector']:
            collector_output = self.agents['collector'].execute(news_items)
        else:
            print("Degraded mode: skipping collector, using raw news")
            collector_output = {"raw_news": news_items, "enriched_result": "\n".join(news_items)}

        # Step 2: Classifier
        print("[Step 2/5] Classifier processing...")
        if self.agents['classifier']:
            classifier_output = self.agents['classifier'].execute(collector_output)
        else:
            print("Degraded mode: skipping classifier")
            classifier_output = {"collector_output": collector_output, "classified_result": "Classification unavailable"}

        # Step 3: Analyst
        print("[Step 3/5] Analyst processing...")
        if self.agents['analyst']:
            analyst_output = self.agents['analyst'].execute(classifier_output)
        else:
            print("Degraded mode: skipping analyst")
            analyst_output = {"classifier_output": classifier_output, "analysis_result": "Trend analysis unavailable"}

        # Step 4: Writer
        print("[Step 4/5] Writer processing...")
        if self.agents['writer']:
            writer_output = self.agents['writer'].execute(analyst_output, report_date)
        else:
            print("Degraded mode: generating basic report from news headlines")
            # Generate a basic report from raw news items
            raw_items = news_items[:20]
            news_list = "\n".join(f"- {item}" for item in raw_items)
            degraded_report = f"""# AI Research Report - {report_date}

## Collected News Headlines

{news_list}

---
*Note: This is a basic report generated without LLM agents. Configure API keys in .env for AI-powered analysis.*
"""
            writer_output = {"analyst_output": analyst_output, "report_markdown": degraded_report}

        # Step 5: Reviewer
        print("[Step 5/5] Reviewer processing...")
        if self.agents['reviewer']:
            final_report = self.agents['reviewer'].execute(writer_output)
        else:
            print("Degraded mode: skipping reviewer")
            final_report = writer_output['report_markdown']

        print(f"\n{'='*60}")
        print("Multi-Agent Collaboration Workflow Complete!")
        print(f"{'='*60}\n")

        # Export chain-of-thought log
        thinking_logger.export_to_file(f"logs/thinking_chain_{report_date}.json")

        return final_report
