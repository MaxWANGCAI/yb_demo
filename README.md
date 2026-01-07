# Yuanbao Demo - 产业分析助手

本项目是一个基于 Streamlit 和 AI Agent 的产业分析助手，利用 MCP (Micro-Component Protocol) 架构集成了产业查询和深度分析能力。

## 核心功能

- **产业查询**：通过 `industry_query` 服务获取特定行业的年度产值等核心指标。
- **深度分析**：当行业产值超过 1000（单位：亿元）时，系统自动触发 `deep_analysis` 服务进行多维度的产业洞察。
- **客观冷静的 AI Persona**：Agent 遵循 `SKILL.md` 中定义的专业、客观的人格设定。

## 技术栈

- **Frontend**: Streamlit
- **Agent Framework**: 自研 Agent 类（基于 OpenAI 兼容接口）
- **Communication**: MCP (Micro-Component Protocol)
- **Database**: SQLite (用于会话状态和日志)
- **Models**: 支持 Qwen 系列模型（推荐 `qwen1.5-14b-chat` 以获得稳定的工具调用能力）

## 快速开始

### 1. 环境配置

创建并激活虚拟环境：
```bash
conda create -n yuanbao_env python=3.10
conda activate yuanbao_env
pip install -r requirements.txt
```

### 2. 环境变量

在根目录创建 `.env` 文件，并配置以下内容：
```env
OPENAI_API_KEY=您的API_KEY
OPENAI_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1
MODEL_NAME=qwen1.5-14b-chat
```

### 3. 启动应用

```bash
streamlit run app.py
```
应用启动时会自动检测并启动 `mcp_servers` 目录下的所有 MCP 服务。

## 开发与调试

- **调试日志**：所有 Agent 交互和 MCP 调用日志均记录在 `logs/` 目录下。
- **手动测试**：可以运行 `python test_agent.py` 进行 Agent 逻辑的单元测试。
- **技能定义**：Agent 的行为逻辑由 `skills/economic_analysis/SKILL.md` 定义。

## 项目结构

```text
├── agent/              # Agent 核心逻辑
├── mcp_servers/        # MCP 服务实现（产业查询、深度分析）
├── skills/             # 业务技能定义 (SKILL.md)
├── utils/              # 通用工具类（日志、数据库）
├── app.py              # Streamlit 界面
├── test_agent.py       # 测试脚本
└── requirements.txt    # 依赖项
```

## 部署说明

在 Streamlit Cloud 部署时，请确保在 Secrets 中配置 `.env` 文件中的所有变量。
