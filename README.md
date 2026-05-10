# AI Research Digest Agent

AI Research Digest Agent 是一个开源的 AI 行业情报自动化产出系统，能够每日抓取主流 AI 资讯、生成分析型趋势报告，并通过 GitHub Actions 自动执行。

该项目适合用于申请 Xiaomi MiMo-V2.5 开源计划与 Orbit Token 计划，重点在于：

- 轻量级、可复现的 AI 趋势分析管道
- 与 OpenAI 兼容的 API 调用结构，易于接入 Token 计划
- 日志化研究报告输出，适合学术与企业评估

## 📋 项目文档

- **[详细项目报告](PROJECT_REPORT.md)** - 中文版完整技术文档
- **[English Project Report](PROJECT_REPORT_EN.md)** - 英文版项目报告
- **[Agent 协作指南](AGENTS_GUIDE.md)** - 多 Agent 系统详细说明

## 核心功能

- 自动抓取 AI 行业 RSS 新闻源
- 多源内容去重与融合
- 使用 DeepSeek/OpenAI 风格的聊天模型生成中文分析报告
- 输出 Markdown 报告到 `reports/`
- 可选 Email 分发与 GitHub Actions 定时自动化

## 适用场景

- AI 研究情报日报
- 行业趋势分析与项目筛选
- 开源项目展示与演示
- Xiaomi MiMo-V2.5 / Orbit 免费 Token 计划的申请案例

## 快速开始

1. 克隆仓库：
   ```bash
   git clone https://github.com/<your-username>/ai-research-agent.git
   cd ai-research-agent
   ```
2. 创建 Python 虚拟环境：
   ```bash
   python -m venv .venv
   .venv\Scripts\activate
   ```
3. 安装依赖：
   ```bash
   pip install -r requirements.txt
   ```
4. 创建 `.env` 文件，配置以下变量：
   ```text
   DEEPSEEK_API_KEY=your_token_here
   SMTP_SERVER=smtp.example.com
   SMTP_PORT=587
   SMTP_USERNAME=your_email@example.com
   SMTP_PASSWORD=your_password
   EMAIL_RECIPIENTS=team@example.com
   ```
5. 运行项目：
   ```bash
   python main.py
   ```

## GitHub Actions 自动化

仓库已配置 `.github/workflows/daily.yml`，支持每日定时生成报告并推送到仓库，同时可选 Email 通知。只需在 GitHub Secrets 中配置：

- `DEEPSEEK_API_KEY`
- `SMTP_SERVER`
- `SMTP_PORT`
- `SMTP_USERNAME`
- `SMTP_PASSWORD`
- `EMAIL_RECIPIENTS`

## 代码组织

- `main.py`：主执行入口
- `requirements.txt`：依赖列表
- `reports/`：每日生成的 Markdown 报告目录
- `.github/workflows/daily.yml`：自动化调度与报告提交流程

## 贡献与申请说明

欢迎基于本项目继续完善：

- 增加更多 AI 数据源
- 改进趋势分析结构
- 扩展报告模板至多语言支持
- 优化模型调用与 Token 使用效率

本仓库已具备开源申请基础，适合在 MiMo-V2.5 和 Orbit 项目中展示项目落地能力与自动化研究价值。

## 许可证

本项目使用 MIT 许可证。详情见 `LICENSE`。
