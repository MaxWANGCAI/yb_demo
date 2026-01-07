import os
import asyncio
import contextlib
from agents import Agent, Runner, function_tool, set_default_openai_client
from agents.agent import ModelSettings
from agents.models.openai_chatcompletions import OpenAIChatCompletionsModel
from openai import AsyncOpenAI
from agents.mcp import MCPServerSse
from mcp.types import CallToolResult
from typing import Any
from utils.logger import InteractionLogger
from utils.config import Config
from agents.models.chatcmpl_converter import Converter
from agents.memory import SQLiteSession

class LoggingMCPServerSse(MCPServerSse):
    def __init__(self, logger: InteractionLogger, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.logger = logger

    async def call_tool(self, tool_name: str, arguments: dict[str, Any] | None) -> CallToolResult:
        self.logger.log_interaction("agent", "mcp_server", f"calling_tool: {tool_name}", f"arguments: {arguments}")
        try:
            result = await super().call_tool(tool_name, arguments)
            # Log the actual content returned by the tool
            content_summary = []
            for content in result.content:
                if hasattr(content, 'text'):
                    content_summary.append(content.text)
                else:
                    content_summary.append(str(content))
            
            self.logger.log_interaction("mcp_server", "agent", f"tool_result: {tool_name}", f"content: {' '.join(content_summary)}")
            return result
        except Exception as e:
            self.logger.log_interaction("mcp_server", "agent", "error", f"Tool {tool_name} failed: {e}")
            raise e

# Monkey-patch Converter.items_to_messages to fix missing content in assistant messages
# This is required for Qwen/DashScope compatibility which demands non-null content
import agents.models.openai_chatcompletions as chat_mod
from agents.models.chatcmpl_converter import Converter

original_items_to_messages = Converter.items_to_messages

@classmethod
def patched_items_to_messages(cls, items, model=None, preserve_thinking_blocks=False, preserve_tool_output_all_content=False):
    messages = original_items_to_messages(items, model, preserve_thinking_blocks, preserve_tool_output_all_content)
    for msg in messages:
        if msg.get("role") == "assistant":
            if "tool_calls" in msg and msg.get("tool_calls"):
                if msg.get("content") is None:
                    msg["content"] = ""
    return messages

# Apply to both the class and the module-level reference if it exists
Converter.items_to_messages = patched_items_to_messages
if hasattr(chat_mod, 'Converter'):
    chat_mod.Converter.items_to_messages = patched_items_to_messages

class IndustryAgent:
    def __init__(self, initial_skills_system_prompt: str, dynamic_skills_dict: dict, auto_reset: bool = True):
        self.config = Config()
        # ... (OpenAI client configuration stays same)
        openai_client = AsyncOpenAI(
            api_key=self.config.OPENAI_API_KEY,
            base_url=self.config.OPENAI_BASE_URL,
        )
        set_default_openai_client(openai_client)
        openai_model = OpenAIChatCompletionsModel(
            model=self.config.MODEL_NAME,
            openai_client=openai_client,
        )
        
        self.logger = InteractionLogger(self.config.LOG_PATH)
        self.mcp_servers = []
        self.loaded_skills = set()
        
        # 1. Initialize Persistent Session with Auto-Cleanup
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        log_dir = os.path.join(base_dir, "logs")
        if not os.path.exists(log_dir):
            os.makedirs(log_dir)
            
        self.db_path = os.path.join(log_dir, "agent_session.db")
        
        # 优化：默认自动重置，除非显式指定不重置
        if auto_reset:
            try:
                # 彻底清理数据库及其 WAL/SHM 临时文件
                for ext in ["", "-wal", "-shm"]:
                    fpath = self.db_path + ext
                    if os.path.exists(fpath):
                        os.remove(fpath)
                
                print(f"DEBUG: Auto-reset session database at startup: {self.db_path}")
                self.logger.log_interaction("system", "agent", "auto_reset", "Session database cleared automatically at startup.")
            except Exception as e:
                print(f"WARNING: Failed to auto-reset session database: {e}")
                # 尝试使用一个新的文件名作为 fallback，避免启动失败
                import time
                self.db_path = f"{self.db_path}_{int(time.time())}"
                print(f"WARNING: Fallback to new database path: {self.db_path}")
                
        self.session = SQLiteSession(
            session_id="industry_analyst_session",
            db_path=self.db_path
        )
        
        # 2. Initialize MCP Servers
        self._init_mcp_servers()
        
        # 3. Load available skills metadata
        self.skills_system_prompt = initial_skills_system_prompt
        self.dynamic_skills_dict = dynamic_skills_dict

        # 4. Define Tools (load_skill, mcp_call)
        @function_tool
        def load_skill(skill_name: str) -> str:
            """
            加载特定产业或领域的详细操作指南。
            当用户询问某个行业（如旅游、金融、IT等）时，必须首先调用此工具。
            """
            self.logger.log_interaction("agent", "skill_manager", f"loading_skill: {skill_name}")
            print(f"DEBUG: load_skill called with {skill_name}")
            
            # 无论是否已加载，都读取最新的技能内容以刷新上下文指令
            skill_path = os.path.join(self.config.SKILLS_PATH, skill_name, "SKILL.md")
            content = ""
            if os.path.exists(skill_path):
                with open(skill_path, "r", encoding="utf-8") as f:
                    content = f.read()
            else:
                return f"未找到技能 '{skill_name}'。"

            if skill_name in self.loaded_skills:
                # 即使已加载，也要返回核心指令，防止模型遗忘
                msg = f"技能 '{skill_name}' 已加载。为了确保执行准确性，再次显示指南内容：\n\n{content}\n\n系统提示：请严格遵循指南中的逻辑分支！"
                self.logger.log_interaction("skill_manager", "agent", "skill_already_loaded", f"refreshed content for {skill_name}")
                return msg
                
            self.loaded_skills.add(skill_name)
            self.logger.log_interaction("skill_manager", "agent", f"loaded content for {skill_name} ({len(content)} chars)")
            return f"已加载 '{skill_name}' 技能指南：\n\n{content}\n\n系统提示：【严重警告】必须立即调用 'mcp_call' 工具获取数据！在未获取到真实数据前，严禁向用户输出任何分析结论或借口！"

        @function_tool
        async def mcp_call(server_name: str, tool_name: str, arguments: Any) -> str:
            """
            统一的 MCP 工具调用入口。
            必须在加载相关技能（load_skill）后，按照指南中的 server_name 和 tool_name 进行调用。
            
            Args:
                server_name: 技能指南中指定的 MCP 服务器名称。
                tool_name: 技能指南中指定的工具名称。
                arguments: 工具参数 (Dict)。
            """
            import json
            print(f"DEBUG: mcp_call -> server: {server_name}, tool: {tool_name}, args: {arguments}")
            target_server = next((s for s in self.mcp_servers if s.name == server_name), None)
            if not target_server:
                # 统一抛出异常，触发外部的自愈逻辑
                raise ValueError(f"CRITICAL_MCP_ERROR: 未找到或未连接 MCP 服务器 '{server_name}'。请检查技能指南中的 server_name 是否正确。")
            
            try:
                if isinstance(arguments, dict):
                    args = arguments
                elif isinstance(arguments, str):
                    args = json.loads(arguments) if arguments else {}
                else:
                    args = arguments if arguments else {}
                    
                result = await target_server.call_tool(tool_name, args)
                content_list = []
                for content in result.content:
                    if hasattr(content, 'text'):
                        content_list.append(content.text)
                    else:
                        content_list.append(str(content))
                
                output = "\n".join(content_list)
                
                # 核心改进：如果 MCP 返回 Unknown tool，直接抛出异常触发自愈
                if "Unknown tool" in output:
                    raise ValueError(f"CRITICAL_MCP_ERROR: {output}")

                # 针对 industry_query 的特殊增强提示，解决 Agent 拿到数据后不进行深度分析的问题
                system_hint = ""
                if server_name == "industry_query":
                    system_hint = "\n\n【系统强制指令】\n1. 立即检查 'annual_output' 数值。\n2. 逻辑分支判断：\n   - 若数值 > 1000：**CRITICAL**：必须立即调用 'deep_analysis' 工具！\n   **不要**输出“接下来我将...”、“稍候...”等文字。\n   **直接**输出工具调用 JSON。\n   - 若数值 <= 1000：仅输出建议。"

                return f"【工具调用成功】从 {server_name} 获取到的原始数据如下，请根据手册逻辑进行判断处理：\n{output}{system_hint}"
            except Exception as e:
                # 确保异常向上传递，而不是被包装成普通的错误消息返回给模型
                raise e
        
        # 5. Initialize Persistent Agent
        self.agent = Agent(
            name="IndustryAnalyst",
            instructions=f"""你是一个专业的产业分析助手。你的唯一目标是利用工具获取真实数据并生成报告。

## 核心法则
1. **工具优先**: 遇到任何问题，**第一步永远是调用工具**。在没有工具返回的数据前，**严禁**向用户发送任何分析性文字。
2. **拒绝猜测**: 如果没有数据，就调用工具去查。不要编造“根据最新数据...”之类的空话。

## 执行流程 (Step-by-Step)
1. **加载技能**: 收到用户行业咨询（如“金融”），调用 `load_skill('economic_analysis')`。
2. **获取数据**: 技能加载后，根据指南立即调用 `mcp_call` (如 `get_industry_data`)。
3. **决策与分析**: 
   - 拿到数据后，**首先**检查是否满足深度分析条件（如产值 > 1000）。
   - 如果满足，**立即**继续调用 `deep_analysis` 工具。**不要**在此步骤停下来问用户！
   - 只有当所有必要的数据（基础数据 + 深度分析（如需））都到手后，才开始撰写最终回复。
4. **生成报告**: 严格按照技能指南的格式（【现状数据】...）输出最终回答。

## 关键修正
- **不要**试图在一条回复里同时进行“汇报数据”和“询问用户”。
- 如果需要深度分析，**直接去调用工具**，拿到结果后再一起汇报。
- 你的输出应该主要是工具调用（Tool Calls），直到最后一步才是给用户的文本。

## 可用技能列表:
{self.skills_system_prompt}
            """,
            tools=[load_skill, mcp_call],
            model=openai_model
        )

        self.logger.log_interaction("system", "agent", "initialized", "IndustryAnalyst initialized with skills (dynamic MCP mode)")

    def update_skills(self, new_skills_prompt: str, new_dynamic_skills: dict):
        """更新 Agent 可用的技能元数据，无需重建实例。"""
        self.skills_system_prompt = new_skills_prompt
        self.dynamic_skills_dict = new_dynamic_skills
        self.logger.log_interaction("agent", "system", "skills_updated", f"Loaded {len(new_dynamic_skills)} dynamic skills")

    def _init_mcp_servers(self):
        """Initialize all configured MCP servers."""
        server_configs = [
            {"name": "industry_query", "url": self.config.MCP_TOURISM_QUERY_URL},
            {"name": "deep_analysis", "url": self.config.MCP_DEEP_ANALYSIS_URL}
        ]
        
        for config in server_configs:
            try:
                server = LoggingMCPServerSse(
                    logger=self.logger,
                    name=config["name"],
                    params={"url": config["url"]}
                )
                self.mcp_servers.append(server)
            except Exception as e:
                self.logger.log_interaction("agent", "system", "error", f"Failed to connect to MCP server {config['name']}: {e}")
        
        self.logger.log_interaction("agent", "mcp_servers", "connected", f"Connected to {len(self.mcp_servers)} MCP servers")

    def _load_skills_system_prompt(self) -> str:
        """Read the AGENTS.md content."""
        agents_file = os.path.join(self.config.SKILLS_PATH, "AGENTS.md")
        if os.path.exists(agents_file):
            with open(agents_file, "r", encoding="utf-8") as f:
                return f.read()
        return "No skills available."



    def clear_session(self):
        """显式清空当前 Session 的所有历史记录。"""
        try:
            # 清除内存中的加载状态
            self.loaded_skills.clear()
            # 重新初始化 Session (由于 SQLiteSession 库限制，直接删除文件是最彻底的)
            for ext in ["", "-wal", "-shm"]:
                fpath = self.db_path + ext
                if os.path.exists(fpath):
                    os.remove(fpath)
            
            self.session = SQLiteSession(
                session_id="industry_analyst_session",
                db_path=self.db_path
            )
            self.logger.log_interaction("system", "agent", "session_cleared", "Session history and loaded skills cleared.")
            return True
        except Exception as e:
            self.logger.log_interaction("system", "agent", "error", f"Failed to clear session: {e}")
            return False

    async def process_query(self, query: str, is_retry: bool = False):
        """使用持久化的 Agent 和 Session 处理用户查询。"""
        if not is_retry:
            self.logger.log_interaction("user", "agent", query, f"Session ID: {self.session.session_id}")
        
        # 确保 MCP 服务器在调用时是连接状态
        async with contextlib.AsyncExitStack() as stack:
            for server in self.mcp_servers:
                await stack.enter_async_context(server)
            
            max_retries = 3
            for attempt in range(max_retries):
                try:
                    # 使用 self.session 保持多轮对话上下文
                    result = await Runner.run(self.agent, input=query, max_turns=30, session=self.session)
                    
                    # 优化：自动检测“Unknown tool”错误并触发自愈重置
                    # 如果返回内容中包含工具找不到的提示，说明模型可能在用过时的记忆
                    if ("Unknown tool" in result.final_output or "未找到" in result.final_output and "工具" in result.final_output) and not is_retry:
                        self.logger.log_interaction("agent", "system", "auto_healing", "Detected stale tool reference, clearing session and retrying...")
                        self.clear_session()
                        return await self.process_query(query, is_retry=True)

                    if not is_retry:
                        self.logger.log_interaction("agent", "user", result.final_output)
                    return result.final_output
                except Exception as e:
                    error_msg = str(e)
                    # 自动检测关键 MCP 错误并触发重置
                    if ("CRITICAL_MCP_ERROR" in error_msg or "Unknown tool" in error_msg) and not is_retry:
                        self.logger.log_interaction("agent", "system", "auto_healing", f"Detected tool failure ({error_msg}), resetting session...")
                        self.clear_session()
                        return await self.process_query(query, is_retry=True)

                    if "500" in error_msg and "internal_server_error" in error_msg:
                        self.logger.log_interaction("agent", "system", "warning", f"尝试 {attempt + 1} API 暂时不可用 (500), 正在重试...")
                    else:
                        self.logger.log_interaction("agent", "system", "error", f"尝试 {attempt + 1} 失败: {error_msg}")
                        
                    if any(code in error_msg for code in ["429", "500", "502", "503", "504", "timeout"]) and attempt < max_retries - 1:
                        await asyncio.sleep((attempt + 1) * 2)
                        continue
                    
                    if "500" in error_msg:
                        return "抱歉，服务压力较大，请稍后再试。"
                    return f"系统繁忙 ({error_msg})，请稍后重试。"

