"""
轻量级多 Agent 框架 - 支持 DeepSeek、GLM、Groq、Mistral、硅基流动
推理链设计：每个 Agent 的输出作为后续 Agent 的输入
"""

import json
import os
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any, Dict, List
from zoneinfo import ZoneInfo

import requests
from dotenv import load_dotenv

TZ = ZoneInfo('Asia/Shanghai')


class ThinkingChainLogger:
    """维护完整的推理链日志"""
    
    def __init__(self):
        self.chain = []
    
    def log(self, agent_name: str, input_data: Any, output_data: Any, reasoning: str = ""):
        """记录 Agent 的推理过程"""
        entry = {
            'timestamp': datetime.now(TZ).isoformat(),
            'agent': agent_name,
            'input': input_data if isinstance(input_data, (str, dict, list)) else str(input_data),
            'output': output_data if isinstance(output_data, (str, dict, list)) else str(output_data),
            'reasoning': reasoning
        }
        self.chain.append(entry)
        print(f"[{agent_name}] {reasoning[:80]}...")
    
    def export_to_file(self, filename: str = "thinking_chain.json"):
        """导出推理链日志"""
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(self.chain, f, indent=2, ensure_ascii=False)
        print(f"Thinking chain exported to {filename}")
    
    def get_context(self) -> str:
        """获取当前推理链摘要作为上文"""
        summary = []
        for entry in self.chain[-3:]:  # 最后 3 个步骤
            summary.append(f"{entry['agent']}: {entry['reasoning']}")
        return "\n".join(summary)


# 全局推理链日志
thinking_logger = ThinkingChainLogger()


class Agent(ABC):
    """Agent 基类"""
    
    def __init__(self, name: str, model: str, api_key: str, base_url: str = None):
        self.name = name
        self.model = model
        self.api_key = api_key
        self.base_url = base_url
    
    @abstractmethod
    def execute(self, prompt: str, system_prompt: str = "") -> str:
        """执行 Agent 的核心逻辑"""
        pass
    
    def call_llm(self, messages: List[Dict[str, str]]) -> str:
        """统一的 LLM 调用接口"""
        raise NotImplementedError


class DeepSeekAgent(Agent):
    """DeepSeek Agent"""
    
    def __init__(self, name: str = "DeepSeekAgent"):
        load_dotenv()
        api_key = os.getenv('DEEPSEEK_API_KEY')
        if not api_key:
            raise RuntimeError('Missing DEEPSEEK_API_KEY')
        super().__init__(name, "deepseek-chat", api_key, "https://api.deepseek.com/v1")
    
    def call_llm(self, messages: List[Dict[str, str]]) -> str:
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


class GLMAgent(Agent):
    """GLM Agent (智谱)"""
    
    def __init__(self, name: str = "GLMAgent"):
        load_dotenv()
        api_key = os.getenv('GLM_API_KEY')
        if not api_key:
            raise RuntimeError('Missing GLM_API_KEY')
        super().__init__(name, "glm-4", api_key, "https://open.bigmodel.cn/api/paas/v4")
    
    def call_llm(self, messages: List[Dict[str, str]]) -> str:
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


class GroqAgent(Agent):
    """Groq Agent"""
    
    def __init__(self, name: str = "GroqAgent"):
        load_dotenv()
        api_key = os.getenv('GROQ_API_KEY')
        if not api_key:
            raise RuntimeError('Missing GROQ_API_KEY')
        super().__init__(name, "mixtral-8x7b-32768", api_key, "https://api.groq.com/openai/v1")
    
    def call_llm(self, messages: List[Dict[str, str]]) -> str:
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


class MistralAgent(Agent):
    """Mistral Agent"""
    
    def __init__(self, name: str = "MistralAgent"):
        load_dotenv()
        api_key = os.getenv('MISTRAL_API_KEY')
        if not api_key:
            raise RuntimeError('Missing MISTRAL_API_KEY')
        super().__init__(name, "mistral-large-latest", api_key, "https://api.mistral.ai/v1")
    
    def call_llm(self, messages: List[Dict[str, str]]) -> str:
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


class SiliconFlowAgent(Agent):
    """硅基流动 Agent"""
    
    def __init__(self, name: str = "SiliconFlowAgent"):
        load_dotenv()
        api_key = os.getenv('SILICONFLOW_API_KEY')
        if not api_key:
            raise RuntimeError('Missing SILICONFLOW_API_KEY')
        super().__init__(name, "Qwen2-72B-Instruct", api_key, "https://api.siliconflow.cn/v1")
    
    def call_llm(self, messages: List[Dict[str, str]]) -> str:
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


class CollectorAgent:
    """Agent 1: 采集器 - 抓取新闻内容"""
    
    def __init__(self, agent: Agent):
        self.agent = agent
        self.name = "Collector"
    
    def execute(self, news_items: List[str]) -> Dict[str, Any]:
        prompt = f"""
        分析以下 {len(news_items)} 条 AI 行业新闻标题，为每条新闻补充一句话的简短摘要：
        
        {chr(10).join(f"- {item}" for item in news_items[:15])}
        
        返回 JSON 格式：{{"enriched_news": [{{title: "...", summary: "..."}}]}}
        """
        
        result = self.agent.execute(prompt)
        thinking_logger.log(self.name, news_items, result, "已采集并初步总结新闻内容")
        return {"raw_news": news_items, "enriched_result": result}


class ClassifierAgent:
    """Agent 2: 分类器 - 分类新闻重要性"""
    
    def __init__(self, agent: Agent):
        self.agent = agent
        self.name = "Classifier"
    
    def execute(self, collector_output: Dict[str, Any]) -> Dict[str, Any]:
        previous_context = thinking_logger.get_context()
        
        prompt = f"""
        基于前置采集步骤的结果，对以下新闻进行分类（重要性评分 1-10）：
        
        {collector_output['enriched_result']}
        
        前置上下文：
        {previous_context}
        
        分类维度：
        1. 重要性（1-10）
        2. 领域（模型/产品/融资/学术/应用）
        3. 热度（高/中/低）
        
        返回 JSON 格式：{{"classified_news": [{{title: "...", importance: X, domain: "...", heat: "..."}}]}}
        """
        
        result = self.agent.execute(prompt)
        thinking_logger.log(self.name, collector_output, result, "已完成新闻分类和评分")
        return {"collector_output": collector_output, "classified_result": result}


class AnalystAgent:
    """Agent 3: 分析师 - 深度趋势分析"""
    
    def __init__(self, agent: Agent):
        self.agent = agent
        self.name = "Analyst"
    
    def execute(self, classifier_output: Dict[str, Any]) -> Dict[str, Any]:
        previous_context = thinking_logger.get_context()
        
        prompt = f"""
        基于已分类的新闻数据，识别主要的技术趋势和行业洞察：
        
        {classifier_output['classified_result']}
        
        前置推理链：
        {previous_context}
        
        分析角度：
        1. 当前主流技术方向
        2. 融资热点与创业方向
        3. 开源生态演进
        4. 可能的市场机遇
        
        返回详细的中文趋势分析（5-8 条核心观察）
        """
        
        result = self.agent.execute(prompt)
        thinking_logger.log(self.name, classifier_output, result, "已完成趋势深度分析")
        return {"classifier_output": classifier_output, "analysis_result": result}


class WriterAgent:
    """Agent 4: 撰写师 - 组织成报告"""
    
    def __init__(self, agent: Agent):
        self.agent = agent
        self.name = "Writer"
    
    def execute(self, analyst_output: Dict[str, Any], report_date: str) -> Dict[str, Any]:
        previous_context = thinking_logger.get_context()
        
        prompt = f"""
        基于前置的分类和分析结果，生成一份结构化的 AI 行业日报（Markdown）：
        
        分析结果：
        {analyst_output['analysis_result']}
        
        前置上下文：
        {previous_context}
        
        报告结构（Markdown 格式）：
        # AI Research Report - {report_date}
        
        ## 今日核心动态（Top 5）
        [列出 5 条最重要新闻 + 来源 + 意义]
        
        ## 技术趋势分析
        [基于分析结果展开 5-8 条趋势观察]
        
        ## 值得关注的项目（Top 3）
        [筛选最有价值的论文/产品/融资事件]
        
        ## 行业观察结论
        [总结当前阶段、加速方向、可能机遇]
        """
        
        result = self.agent.execute(prompt)
        thinking_logger.log(self.name, analyst_output, result, "已生成结构化报告")
        return {"analyst_output": analyst_output, "report_markdown": result}


class ReviewerAgent:
    """Agent 5: 评审师 - 质量审核与补充"""
    
    def __init__(self, agent: Agent):
        self.agent = agent
        self.name = "Reviewer"
    
    def execute(self, writer_output: Dict[str, Any]) -> str:
        previous_context = thinking_logger.get_context()
        
        prompt = f"""
        审核以下 AI 行业日报的质量，检查是否存在以下问题：
        1. 是否包含足够的具体数据/案例
        2. 是否有明确的趋势判断（而非简单列举）
        3. 是否涵盖模型/产品/融资/学术等主要维度
        4. 是否有可操作的行业洞察
        
        原始报告：
        {writer_output['report_markdown']}
        
        推理链摘要：
        {previous_context}
        
        如果报告质量需要改进，请指出具体问题并建议改进方案。
        如果报告质量良好，直接返回改进后的最终版本。
        
        最后返回最终版本报告（Markdown）。
        """
        
        result = self.agent.execute(prompt)
        thinking_logger.log(self.name, writer_output, result, "已完成质量审核和最终优化")
        return result


class Orchestrator:
    """协调器 - 管理 5 个 Agent 的工作流"""
    
    def __init__(self):
        # 初始化 5 个 Agent（可配置使用不同模型）
        self.collector = CollectorAgent(GLMAgent("GLM-Collector"))
        self.classifier = ClassifierAgent(GroqAgent("Groq-Classifier"))
        self.analyst = AnalystAgent(DeepSeekAgent("DeepSeek-Analyst"))
        self.writer = WriterAgent(MistralAgent("Mistral-Writer"))
        self.reviewer = ReviewerAgent(SiliconFlowAgent("SiliconFlow-Reviewer"))
    
    def run(self, news_items: List[str], report_date: str) -> str:
        """执行完整的 5 Agent 协作流程"""
        print(f"\n{'='*60}")
        print(f"启动多 Agent 协作流程，共 5 个步骤")
        print(f"{'='*60}\n")
        
        # Step 1: 采集
        print("[Step 1/5] 采集器处理中...")
        collector_output = self.collector.execute(news_items)
        
        # Step 2: 分类
        print("[Step 2/5] 分类器处理中...")
        classifier_output = self.classifier.execute(collector_output)
        
        # Step 3: 分析
        print("[Step 3/5] 分析师处理中...")
        analyst_output = self.analyst.execute(classifier_output)
        
        # Step 4: 撰写
        print("[Step 4/5] 撰写师处理中...")
        writer_output = self.writer.execute(analyst_output, report_date)
        
        # Step 5: 审核
        print("[Step 5/5] 评审师处理中...")
        final_report = self.reviewer.execute(writer_output)
        
        print(f"\n{'='*60}")
        print("多 Agent 协作流程完成！")
        print(f"{'='*60}\n")
        
        # 导出推理链日志
        thinking_logger.export_to_file(f"logs/thinking_chain_{report_date}.json")
        
        return final_report
