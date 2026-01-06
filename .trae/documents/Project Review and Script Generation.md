# 重构项目以集成 OpenAI Agents, FastMCP 和 OpenSkills

本计划旨在重构现有代码库，以实现一个真正的 ReAct Agent，该 Agent 能够动态发现和加载技能，并通过 MCP 协议与后端服务交互。

## 1. 项目清理与配置
*   **清理文件**:
    *   删除空文件/未使用的文件：`agent/skill_manager.py` (将被新的 Agent 逻辑取代), `agent/__init__.py`, `logs/interactions.log`, `utils/__init__.py`.
*   **配置管理**:
    *   创建 `.env` 文件，定义 MCP 服务器端口 (8001, 8002) 和 URL。
    *   更新 `utils/config.py` 以加载环境变量。
    *   更新 `utils/logger.py` 以支持人类可读的日志格式（时间戳、发送者、接收者、内容）。

## 2. MCP 服务器重构 (FastMCP)
*   **目标**: 解决端口冲突，规范化启动。
*   **Tourism Query Server (`mcp_servers/tourism_query/server.py`)**:
    *   使用 `fastmcp`。
    *   端口: 8001。
    *   逻辑: 随机返回 60万 或 2000万。
*   **Deep Analysis Server (`mcp_servers/deep_analysis/server.py`)**:
    *   使用 `fastmcp`。
    *   端口: 8002。
    *   逻辑: 返回固定文本 "深入分析：..."。
*   **脚本**:
    *   `start_mcp_services.sh`: 启动两个服务器。
    *   `stop_mcp_services.sh`: 关闭两个服务器 (通过 `pkill` 或 PID 文件)。

## 3. 技能系统 (基于 OpenSkills)
*   **元数据**:
    *   重建 `skills/AGENTS.md`，使用符合 OpenSkills 标准的 XML 格式 (`<available_skills>...`)，包含 `economic_analysis` 技能。
*   **技能内容**:
    *   保留并验证 `skills/economic_analysis/SKILL.md`，确保其包含指导 Agent 调用 MCP 工具的明确指令。
*   **动态加载**:
    *   在 Agent 中实现 `load_skill(skill_name)` 工具，该工具读取对应的 `SKILL.md` 内容并将其注入到当前对话上下文中。

## 4. Agent 实现 (OpenAI Agents SDK)
*   **`agent/agent.py`**:
    *   使用 `openai-agents` 的 `Agent` 和 `Runner` 类。
    *   **初始化**:
        *   自动连接到配置的 MCP 服务器。
        *   读取 `skills/AGENTS.md` 中的 `<available_skills>` 并添加到系统指令中。
    *   **工具集**:
        *   注册 `load_skill` 本地函数。
        *   注册从 MCP 服务器发现的所有工具 (`get_tourism_data`, `deep_analyze`)。
    *   **ReAct 循环**:
        *   移除硬编码的 `while` 循环。利用 SDK 内置的推理循环，Agent 将自动决定：查看技能列表 -> 调用 `load_skill` -> 阅读指令 -> 调用 MCP 工具 -> 生成回答。

## 5. 前端交互 (Streamlit)
*   **`app.py`**:
    *   **聊天界面**: 标准的对话历史展示。
    *   **侧边栏**:
        *   **MCP 状态**: 显示两个服务器的连接状态 (通过简单的 ping 检测)。
        *   **已加载技能**: 显示 Agent 当前已加载的技能。
        *   **添加技能**: 按钮 "Add Random Skill"，点击后向 `AGENTS.md` 追加一个新的随机技能条目 (模拟 `openskills install`)。
    *   **日志面板**: 读取并展示格式化的交互日志，支持自动刷新。
    *   **启动脚本**: `start_app.sh`。

## 6. 交互流程说明
在代码实现完成后，将提供详细的文本文档，解释 User, Streamlit, Agent, Skill Manager, MCP Servers 之间的交互时序和数据流。

## 7. 执行顺序
1.  清理文件。
2.  创建配置文件和日志工具。
3.  重写 MCP 服务器。
4.  创建 Shell 脚本。
5.  重写 Agent 逻辑。
6.  重写 Streamlit 前端。
7.  验证全流程。
