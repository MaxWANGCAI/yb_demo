import streamlit as st
import asyncio
import os
import random
import requests
import uuid
import subprocess # For local openskills CLI interaction

from agent.agent import IndustryAgent
from utils.config import Config
from utils.logger import InteractionLogger

# Environment detection
IS_STREAMLIT_CLOUD = os.getenv("STREAMLIT_CLOUD", "false").lower() == "true"

@st.cache_resource
def clear_logs_on_startup():
    """Clears all log files in the logs directory on startup."""
    log_dir = os.path.join(os.getcwd(), "logs")
    if os.path.exists(log_dir):
        import shutil
        for filename in os.listdir(log_dir):
            file_path = os.path.join(log_dir, filename)
            try:
                if os.path.isfile(file_path) or os.path.islink(file_path):
                    os.unlink(file_path)
                elif os.path.isdir(file_path):
                    shutil.rmtree(file_path)
            except Exception as e:
                print(f"Failed to delete {file_path}. Reason: {e}")
    else:
        os.makedirs(log_dir)
    return True

# Clear logs once per application run
clear_logs_on_startup()

# Set page config
st.set_page_config(
    page_title="产业发展分析智能体",
    page_icon="📊",
    layout="wide"
)

# Custom CSS for a more professional look and smooth transitions
st.markdown("""
    <style>
    /* 移除可能导致遮挡的 CSS 规则 */
    /* .stApp > div:first-child { visibility: visible !important; opacity: 1 !important; } */
    
    /* 隐藏右上角的运行状态小图标 */
    div[data-testid="stStatusWidget"] {
        display: none !important;
    }
    
    /* 仅针对加载块容器强制显示，防止闪烁 */
    [data-testid="stAppViewBlockContainer"] {
        opacity: 1 !important;
    }

    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    
    /* 对话框样式 */
    .stChatMessage {
        border-radius: 10px;
        padding: 10px;
        margin-bottom: 10px;
        border: 1px solid #e0e4e8;
    }
    
    /* 侧边栏和分栏样式优化 */
    .log-container {
        background-color: #1e1e1e;
        color: #d4d4d4;
        padding: 15px;
        border-radius: 5px;
        font-family: 'Courier New', Courier, monospace;
        font-size: 0.85em;
        height: 600px;
        overflow-y: auto;
    }
    
    /* 禁用变暗效果 */
    [data-testid="stStatusWidget"] {
        display: none;
    }
    </style>
    """, unsafe_allow_html=True)

@st.cache_data
def _generate_skills_prompt(existing_agents_md_path, dynamic_skills_dict, is_cloud_env):
    """Generates the combined skills system prompt from AGENTS.md and dynamic skills."""
    combined_skills_xml = ""
    logger = InteractionLogger(Config().LOG_PATH)
    
    # Add existing skills from AGENTS.md
    if os.path.exists(existing_agents_md_path):
        logger.log_interaction("system", "agent", "loading_skills", f"Reading skills from {existing_agents_md_path}")
        with open(existing_agents_md_path, "r", encoding="utf-8") as f:
            content = f.read()
            # Extract content between <available_skills> tags
            start_tag = "<available_skills>"
            end_tag = "</available_skills>"
            start_index = content.find(start_tag)
            end_index = content.find(end_tag)
            if start_index != -1 and end_index != -1:
                combined_skills_xml += content[start_index + len(start_tag):end_index].strip()
                logger.log_interaction("system", "agent", "skills_loaded", "Successfully loaded skills from AGENTS.md")
    else:
        logger.log_interaction("system", "agent", "warning", f"AGENTS.md not found at {existing_agents_md_path}")
    
    # Add dynamic skills ONLY if in cloud environment
    if is_cloud_env:
        for skill_id, skill_data in dynamic_skills_dict.items():
            combined_skills_xml += f"""
<skill>
<name>{skill_data['name']}</name>
<description>{skill_data['description']}</description>
<location>session_memory</location>
</skill>"""
            
    return f"""<available_skills>
{combined_skills_xml}
</available_skills>"""

@st.cache_resource
def log_once(sender, receiver, content, msg_type="info"):
    """Logs a message only once per application process lifetime."""
    config = Config()
    logger = InteractionLogger(config.LOG_PATH)
    logger.log_interaction(sender, receiver, content, msg_type)
    return True

@st.cache_resource
def ensure_mcp_servers_running():
    """Starts the MCP servers using subprocess, ensuring global singleton execution."""
    import sys
    import time
    config = Config()
    # Using local logger for process-level events
    logger = InteractionLogger(config.LOG_PATH)
    cwd = os.getcwd()
    
    # 智能选择 Python 解释器
    # 优先尝试从环境路径中寻找，避免硬编码绝对路径
    python_exec = sys.executable
    
    # 如果在本地环境，尝试寻找特定的 conda 环境 python
    # 我们不再使用绝对路径 /Users/max.xu/...，而是尝试通过相对逻辑或环境名查找
    if not IS_STREAMLIT_CLOUD:
        # 尝试寻找相对于用户主目录的路径 (相对通用的做法)
        home = os.path.expanduser("~")
        potential_conda_python = os.path.join(home, "anaconda3", "envs", "yuanbao_env", "bin", "python")
        if os.path.exists(potential_conda_python):
            python_exec = potential_conda_python
        
    print(f"DEBUG: ensure_mcp_servers_running called. CWD: {cwd}, Executable: {python_exec}")
    
    # Ensure logs directory exists
    log_dir = os.path.join(cwd, "logs")
    if not os.path.exists(log_dir):
        os.makedirs(log_dir)
    
    mcp_log_path = os.path.join(log_dir, "mcp_startup.log")
    
    # Helper to check if a port is in use
    import socket
    def is_port_in_use(port):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(0.1)
            return s.connect_ex(('127.0.0.1', port)) == 0

    def kill_port_process(port):
        try:
            # macOS command to kill process on port
            subprocess.run(f"lsof -ti:{port} | xargs kill -9", shell=True, stderr=subprocess.DEVNULL, stdout=subprocess.DEVNULL)
            time.sleep(0.5) # Wait for release
        except:
            pass

    # Start servers
    for name, port, script_rel_path in [
        ("Industry Query", 8001, "mcp_servers/industry_query/server.py"),
        ("Deep Analysis", 8002, "mcp_servers/deep_analysis/server.py")
    ]:
        # 1. 检查端口是否已被占用
        if is_port_in_use(port):
            log_once("system", "mcp_server", f"{name} MCP Server already running on port {port}. Skipping startup.", "info")
            continue

        # 2. 如果未运行，尝试新启
        # 确保没有残留进程占用端口（虽然上面检查了，但为了保险起见，可以尝试清理一下）
        kill_port_process(port)
        
        script_path = os.path.join(cwd, script_rel_path)
        try:
            with open(mcp_log_path, "a") as log_file:
                log_file.write(f"\n--- Starting {name} Server at {uuid.uuid4()} ---\n")
                subprocess.Popen([python_exec, script_path], 
                                 stdout=log_file, 
                                 stderr=log_file,
                                 cwd=cwd)
            
            # 多轮循环等待启动成功（最多 5 秒）
            success = False
            for _ in range(5):
                time.sleep(1)
                if is_port_in_use(port):
                    success = True
                    break
            
            if success:
                log_once("system", "mcp_server", f"{name} MCP Server started on port {port}", "started")
            else:
                log_once("system", "mcp_server", f"{name} MCP Server timeout (5s) on port {port}. Please check logs/mcp_startup.log", "warning")
        except Exception as e:
            logger.log_interaction("system", "mcp_server", "error", f"Failed to launch {name} MCP Server: {e}")
    
    return True

# Initialize Session State
if "messages" not in st.session_state:
    st.session_state.messages = []

if "dynamic_skills" not in st.session_state:
    st.session_state.dynamic_skills = {}

# Initialize MCP servers ONLY once per process using st.cache_resource
ensure_mcp_servers_running()


if "agent" not in st.session_state:
    with st.spinner("正在初始化智能体..."):
        # Generate the combined skills prompt for initial agent setup
        initial_combined_skills_prompt = _generate_skills_prompt(
            os.path.join(Config().SKILLS_PATH, "AGENTS.md"),
            st.session_state.dynamic_skills,
            IS_STREAMLIT_CLOUD
        )
        st.session_state.agent = IndustryAgent(
            initial_skills_system_prompt=initial_combined_skills_prompt,
            dynamic_skills_dict=st.session_state.dynamic_skills if IS_STREAMLIT_CLOUD else {},
            auto_reset=True
        )

if "logger" not in st.session_state:
    config = Config()
    st.session_state.logger = InteractionLogger(config.LOG_PATH)

# --- Fragments ---
@st.fragment(run_every=3)
def status_monitor():
    """独立的 MCP 状态监控组件，每3秒自动刷新"""
    st.subheader("🖥️ 实时监控")
    
    # MCP Status in Monitor area
    status_container = st.container()
    with status_container:
        m1, m2 = st.columns(2)
        tourism_status = check_mcp_status(8001)
        deep_status = check_mcp_status(8002)
        with m1:
            st.metric("行业查询", "运行中" if tourism_status else "已停止")
        with m2:
            st.metric("深度分析", "运行中" if deep_status else "已停止")
    st.markdown("---")

@st.fragment(run_every=1)
def log_viewer():
    """独立的日志查看组件，每1秒自动刷新一次"""
    st.subheader("📜 交互日志")
    logs = st.session_state.logger.read_logs()
    
    # 使用 HTML/CSS 渲染日志，避免 st.text_area 的状态问题
    # 对 logs 进行简单的 HTML 转义，防止 HTML 注入
    import html
    safe_logs = html.escape(logs).replace("\n", "<br>")
    
    st.markdown(f"""
        <div class="log-container">{safe_logs}</div>
        <script>
            // 尝试自动滚动到底部 (注意：Streamlit 的 script 注入限制较多，这可能不一定生效，主要依赖 CSS)
            var logContainer = document.querySelector('.log-container');
            if(logContainer) {{
                logContainer.scrollTop = logContainer.scrollHeight;
            }}
        </script>
    """, unsafe_allow_html=True)

# Helper Functions
def check_mcp_status(port):
    import socket
    for host in ['127.0.0.1', 'localhost']:
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.settimeout(0.2)
                if s.connect_ex((host, port)) == 0:
                    return True
        except:
            continue
    return False



def _add_random_skill_in_memory():
    skill_id = str(uuid.uuid4())
    skill_name = f"cloud_skill_{random.randint(1000, 9999)}"
    nonsense_descriptions = [
        "此技能可以计算彩虹的重量，并预测独角兽的飞行轨迹。",
        "该技能能够将思绪转化为可食用的云朵，并分析其营养成分。",
        "这是一个用于与平行宇宙的袜子交流的技能，解决袜子失踪之谜。",
        "此技能专注于解读猫咪的梦境，并将其转化为史诗般的诗歌。",
        "该技能可以控制时间的流速，但仅限于观察蜗牛赛跑。",
        "这是一个用于将负面情绪转化为闪亮金币的技能，但金币是虚拟的。",
        "此技能能够与植物进行心灵感应，了解它们的八卦。",
        "该技能可以预测下雨时水滴的形状，并为其命名。",
        "这是一个用于在太空中种植巨型蔬菜的技能，但需要特殊的宇宙肥料。",
        "此技能专注于将无聊的会议转化为激动人心的海盗冒险。"
    ]
    skill_description = random.choice(nonsense_descriptions) + " 它可以在会话中被Agent发现和加载。"
    
    st.session_state.dynamic_skills[skill_id] = {
        "name": skill_name,
        "description": skill_description
    }
    st.success(f"已添加动态技能: {skill_name}")
    
    # Update existing agent with new skills
    with st.spinner("正在同步新技能..."):
        combined_skills_prompt = _generate_skills_prompt(
            os.path.join(Config().SKILLS_PATH, "AGENTS.md"),
            st.session_state.dynamic_skills,
            IS_STREAMLIT_CLOUD
        )
        st.session_state.agent.update_skills(
            new_skills_prompt=combined_skills_prompt,
            new_dynamic_skills=st.session_state.dynamic_skills
        )
    st.rerun()

def _add_random_skill_local():
    skill_name = f"local_skill_{random.randint(1000, 9999)}"
    meaningful_descriptions = [
        "这是一个用于分析市场趋势的技能，可以提供数据洞察。",
        "此技能专注于客户行为预测，帮助优化营销策略。",
        "该技能能够进行财务报表分析，评估企业健康状况。",
        "这是一个用于管理项目进度的技能，确保任务按时完成。",
        "此技能提供法律咨询服务，解答常见法律问题。",
        "该技能可以进行多语言翻译，支持全球沟通。",
        "这是一个用于数据清洗和预处理的技能，提高数据质量。",
        "此技能专注于社交媒体情绪分析，了解公众舆论。",
        "该技能能够进行供应链优化，提高物流效率。",
        "这是一个用于智能推荐系统的技能，提升用户体验。"
    ]
    skill_desc = random.choice(meaningful_descriptions) + " 它将写入文件系统并使用openskills CLI同步。"
    
    # 1. Create dummy SKILL.md
    skill_dir = os.path.join(Config().SKILLS_PATH, skill_name)
    os.makedirs(skill_dir, exist_ok=True)
    skill_md_path = os.path.join(skill_dir, "SKILL.md")
    with open(skill_md_path, "w", encoding="utf-8") as f:
        f.write(f"# {skill_name}\n\n{skill_desc}")
    
    # 2. Update AGENTS.md (via openskills CLI)
    agents_path = os.path.join(Config().SKILLS_PATH, "AGENTS.md")
    new_skill_xml_entry = f"""
<skill>
<name>{skill_name}</name>
<description>{skill_desc}</description>
<location>project</location>
</skill>"""
    
    if os.path.exists(agents_path):
        with open(agents_path, "r", encoding="utf-8") as f:
            content = f.read()
        
        if "</available_skills>" in content:
            new_content = content.replace("</available_skills>", f"{new_skill_xml_entry}\n</available_skills>")
            with open(agents_path, "w", encoding="utf-8") as f:
                f.write(new_content)
            st.success(f"Added skill file and updated AGENTS.md for: {skill_name}")
            
            # 3. Run openskills sync
            try:
                result = subprocess.run(["openskills", "sync"], cwd=Config().SKILLS_PATH, capture_output=True, text=True, check=True)
                st.success(f"openskills sync successful: {result.stdout}")
            except subprocess.CalledProcessError as e:
                st.error(f"openskills sync failed: {e.stderr}")
            except FileNotFoundError:
                st.error("openskills CLI tool not found. Please install it globally (npm install -g openskills).")
            
            # Update existing agent with new skills
            with st.spinner("正在同步新技能..."):
                combined_skills_prompt = _generate_skills_prompt(
                    os.path.join(Config().SKILLS_PATH, "AGENTS.md"),
                    st.session_state.dynamic_skills,
                    IS_STREAMLIT_CLOUD
                )
                st.session_state.agent.update_skills(
                    new_skills_prompt=combined_skills_prompt,
                    new_dynamic_skills=st.session_state.dynamic_skills
                )
            st.rerun()
        else:
            st.error("Invalid AGENTS.md format: Missing </available_skills> tag.")
    else:
        st.error("AGENTS.md not found. Cannot add skill locally.")

def add_random_skill():
    if IS_STREAMLIT_CLOUD:
        _add_random_skill_in_memory()
    else:
        _add_random_skill_local()

# Layout: Main Chat and Sidebar/Monitor
col_chat, col_monitor = st.columns([0.65, 0.35])

with col_monitor:
    # 调用独立的监控组件
    status_monitor()
    # 调用自动刷新的日志组件
    log_viewer()

with col_chat:
    st.title("📊 产业分析智能体")
    
    # Display Chat History
    chat_container = st.container()
    with chat_container:
        for message in st.session_state.messages:
            with st.chat_message(message["role"]):
                st.markdown(message["content"])

    # Input area
    st.markdown("---")
    input_prompt = st.chat_input("询问产业发展相关问题...")
    
    # Use callback for quick questions to avoid flickering
    def set_prompt(p):
        st.session_state.current_prompt = p

    if "current_prompt" not in st.session_state:
        st.session_state.current_prompt = None

    # Quick Questions
    cq1, cq2, cq3 = st.columns(3)
    with cq1:
        st.button("旅游业分析", use_container_width=True, on_click=set_prompt, args=("本地的旅游产业发展如何？",))
    with cq2:
        st.button("金融业分析", use_container_width=True, on_click=set_prompt, args=("本地金融业发展如何？",))
    with cq3:
        st.button("IT行业分析", use_container_width=True, on_click=set_prompt, args=("本地IT行业发展如何？",))

    prompt = st.session_state.current_prompt or input_prompt
    if prompt:
        # Clear the state to avoid repeated triggers on next run
        st.session_state.current_prompt = None

    if prompt:
        # 1. User Message
        if not st.session_state.messages or st.session_state.messages[-1]["content"] != prompt:
            st.session_state.messages.append({"role": "user", "content": prompt})
        
        with chat_container:
            with st.chat_message("user"):
                st.markdown(prompt)

        # 2. Assistant Response
        with chat_container:
            with st.chat_message("assistant"):
                resp_placeholder = st.empty()
                with resp_placeholder.container():
                    st.markdown("⏳ *思考中...*")
                
                # Run agent
                response = asyncio.run(st.session_state.agent.process_query(prompt))
                
                # Final display
                resp_placeholder.markdown(response)
        
        st.session_state.messages.append({"role": "assistant", "content": response})
        # 移除 st.rerun()，改用 session_state 保持状态，减少闪烁

# Sidebar: Skills only
with st.sidebar:
    st.header("⚙️ 技能配置")
    
    # Skills
    st.subheader("技能管理")
    if st.button("添加随机技能", use_container_width=True):
        add_random_skill()
        
    if IS_STREAMLIT_CLOUD:
        st.markdown("### 动态技能")
        if st.session_state.dynamic_skills:
            for skill_id, skill_data in st.session_state.dynamic_skills.items():
                st.code(skill_data['name'])
    else:
        st.markdown("### 本地技能")
        agents_file = os.path.join(Config().SKILLS_PATH, "AGENTS.md")
        if os.path.exists(agents_file):
            with open(agents_file, "r", encoding="utf-8") as f:
                content = f.read()
                import re
                skill_names = re.findall(r'<name>(.*?)</name>', content)
                if skill_names:
                    for name in skill_names:
                        st.code(name)
        
    st.markdown("### 已加载技能")
    if hasattr(st.session_state.agent, 'loaded_skills') and st.session_state.agent.loaded_skills:
        for skill in st.session_state.agent.loaded_skills:
            st.code(skill)
    else:
        st.write("尚未加载。")
