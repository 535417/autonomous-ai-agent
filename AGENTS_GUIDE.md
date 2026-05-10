# 多 Agent 协作系统指南

## 概述

这是一个**轻量级、可扩展的多 Agent 框架**，支持 5 个不同的 LLM 提供商：

| Agent | 角色 | 使用模型 | LLM 提供商 |
|-------|------|---------|----------|
| **Collector** | 采集器 | GLM-4 | 智谱 (GLM) |
| **Classifier** | 分类器 | Mixtral 8x7B | Groq |
| **Analyst** | 分析师 | DeepSeek Chat | DeepSeek |
| **Writer** | 撰写师 | Mistral Large | Mistral |
| **Reviewer** | 评审师 | Qwen2 72B | 硅基流动 |

---

## 架构优势

### 1. **长链推理（Thinking Chain）**
每个 Agent 的输出作为后续 Agent 的输入，形成完整的推理链。日志自动保存到 `logs/thinking_chain_YYYY-MM-DD.json`，可追溯每个决策的上下文。

### 2. **多模型负载均衡**
- 采用不同能力的模型分工
- 充分利用各家的免费额度
- 降低单一供应商的依赖

### 3. **工作流透明**
```
采集 → 分类 → 分析 → 撰写 → 审核 → 最终报告
 ↓     ↓     ↓     ↓     ↓
推理链日志（完整记录）
```

---

## 快速开始

### 1. 安装依赖
```bash
pip install -r requirements.txt
```

### 2. 配置 API Keys

在 `.env` 文件中配置各 LLM 的 API Key：

```bash
# DeepSeek (已配置)
DEEPSEEK_API_KEY=your_key_here

# GLM (智谱 AI)
GLM_API_KEY=your_key_here

# Groq
GROQ_API_KEY=your_key_here

# Mistral
MISTRAL_API_KEY=your_key_here

# 硅基流动 (SiliconFlow)
SILICONFLOW_API_KEY=your_key_here
```

### 3. 运行多 Agent 系统

```bash
# 方式 1：使用多 Agent 协作版本（推荐）
python main_multi_agent.py

# 方式 2：使用原始单 Agent 版本
python main.py
```

### 4. 查看结果

- **报告**：`reports/2026-05-10.md`
- **推理链日志**：`logs/thinking_chain_2026-05-10.json`

---

## 各 LLM 提供商配置指南

### 1. **DeepSeek** (已有)
- API 端点：`https://api.deepseek.com`
- 模型：`deepseek-chat`
- 获取方式：已购买 Token

### 2. **GLM (智谱 AI)** - 免费额度
- **官网**：https://open.bigmodel.cn
- **API 端点**：`https://open.bigmodel.cn/api/paas/v4`
- **模型**：`glm-4`
- **获取方式**：
  1. 官网注册账户
  2. 创建 API Key
  3. 复制 `APIKEY` 到 `.env`

**注**：GLM 新用户通常有 100 万 token 的初始免费额度。

### 3. **Groq** - 免费
- **官网**：https://console.groq.com
- **API 端点**：`https://api.groq.com/openai/v1`
- **模型**：`mixtral-8x7b-32768`
- **获取方式**：
  1. https://console.groq.com/keys 获取 API Key
  2. Groq 免费模式完全免费（无额度限制，仅限速）

**优势**：速度最快，适合分类任务。

### 4. **Mistral** - 免费额度
- **官网**：https://console.mistral.ai
- **API 端点**：`https://api.mistral.ai/v1`
- **模型**：`mistral-large-latest`
- **获取方式**：
  1. 官网注册
  2. 创建 API Key
  3. 新用户通常有 5 美元的初始免费额度

### 5. **硅基流动 (SiliconFlow)** - 免费
- **官网**：https://cloud.siliconflow.cn
- **API 端点**：`https://api.siliconflow.cn/v1`
- **模型**：`Qwen2-72B-Instruct`
- **获取方式**：
  1. 官网注册
  2. 进入 API Keys 页面
  3. 创建新密钥
  4. 复制到 `.env`

**优势**：完全免费，支持高质量模型（Qwen2 72B）。

---

## 使用场景示例

### 场景 1：完整多 Agent 流程
```bash
python main_multi_agent.py
```

**输出**：
- `reports/2026-05-10.md` - 完整的日报
- `logs/thinking_chain_2026-05-10.json` - 5 个 Agent 的完整推理链

### 场景 2：仅使用某个 Agent

```python
from agents import DeepSeekAgent, AnalystAgent

agent = AnalystAgent(DeepSeekAgent())
output = agent.execute({...})
```

---

## 推理链日志格式

每个 Agent 的执行都会记录为一个 JSON 条目：

```json
{
  "timestamp": "2026-05-10T20:00:00+08:00",
  "agent": "Collector",
  "input": ["新闻1", "新闻2", ...],
  "output": "enriched news list",
  "reasoning": "已采集并初步总结新闻内容"
}
```

通过这个日志，可以：
- 追溯每个决策的依据
- 识别模型的瓶颈
- 改进 prompt 设计

---

## 常见问题

### Q1：如何只使用某个 LLM？
在 `.env` 中配置该 LLM 的 API Key 即可，其他可留空。如果某个 Agent 无法连接，系统会报错提示。

### Q2：如何修改 Agent 的分工？
编辑 `agents.py` 中的 `Orchestrator` 类，重新分配 Agent 和模型的对应关系：

```python
class Orchestrator:
    def __init__(self):
        self.collector = CollectorAgent(DeepSeekAgent())  # 改用 DeepSeek
        self.classifier = ClassifierAgent(GLMAgent())     # 改用 GLM
        # ...
```

### Q3：如何扩展新的 Agent？
1. 继承 `Agent` 基类
2. 在 `Orchestrator.__init__` 中实例化
3. 在 `run()` 方法中调用

### Q4：推理链日志如何导入后续分析？
```python
import json

with open('logs/thinking_chain_2026-05-10.json', 'r') as f:
    chain = json.load(f)

# 遍历链上的每个步骤
for entry in chain:
    print(f"{entry['agent']}: {entry['reasoning']}")
```

---

## 优化建议

1. **调整 max_total**：在 `main_multi_agent.py` 中修改 `max_total=50` 来控制新闻数量
2. **修改温度参数**：在各 `Agent` 类中调整 `temperature` 参数（0.0 = 确定性，1.0 = 创意性）
3. **自定义 prompt**：在各 Agent 类的 `execute()` 方法中修改 system/user prompt

---

## GitHub Actions 集成

如果希望在 GitHub Actions 中使用多 Agent 版本，更新 `.github/workflows/daily.yml`：

```yaml
- name: Run Multi-Agent System
  env:
    DEEPSEEK_API_KEY: ${{ secrets.DEEPSEEK_API_KEY }}
    GLM_API_KEY: ${{ secrets.GLM_API_KEY }}
    GROQ_API_KEY: ${{ secrets.GROQ_API_KEY }}
    MISTRAL_API_KEY: ${{ secrets.MISTRAL_API_KEY }}
    SILICONFLOW_API_KEY: ${{ secrets.SILICONFLOW_API_KEY }}
  run: python main_multi_agent.py
```

然后在 GitHub Secrets 中配置所有 5 个 API Key。

---

## 许可证

MIT License - 详见 `LICENSE`
