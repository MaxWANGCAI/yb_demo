import streamlit as st
import asyncio
import os
import random
import requests
from agent.agent import TourismAgent
from utils.config import Config
from utils.logger import InteractionLogger

# Set page config
st.set_page_config(
    page_title="Tourism Agent Demo",
    page_icon="🤖",
    layout="wide"
)

# Initialize Session State
if "messages" not in st.session_state:
    st.session_state.messages = []

if "agent" not in st.session_state:
    with st.spinner("Initializing Agent..."):
        st.session_state.agent = TourismAgent()

if "logger" not in st.session_state:
    st.session_state.logger = InteractionLogger()

# Helper Functions
def check_mcp_status(url):
    try:
        # FastMCP usually has a health check or we can just check if connection works
        # Since it uses SSE, a GET might hang or return 404/405 if not correct endpoint, 
        # but connection refused is the key.
        # We'll try to connect.
        requests.get(url, timeout=1)
        return True
    except requests.exceptions.ConnectionError:
        return False
    except:
        return True # Other errors might mean it's up but returning 404 etc.

def add_random_skill():
    skill_name = f"random_skill_{random.randint(1000, 9999)}"
    skill_desc = "这是一个随机生成的测试技能。"
    
    # 1. Update AGENTS.md
    agents_path = os.path.join(Config.SKILLS_PATH, "AGENTS.md")
    new_skill_xml = f"""
<skill>
<name>{skill_name}</name>
<description>{skill_desc}</description>
<location>project</location>
</skill>
"""
    # Insert before </available_skills>
    if os.path.exists(agents_path):
        with open(agents_path, "r", encoding="utf-8") as f:
            content = f.read()
        
        if "</available_skills>" in content:
            new_content = content.replace("</available_skills>", f"{new_skill_xml}\n</available_skills>")
            with open(agents_path, "w", encoding="utf-8") as f:
                f.write(new_content)
            st.success(f"Added skill: {skill_name}")
            
            # Create dummy SKILL.md
            skill_dir = os.path.join(Config.SKILLS_PATH, skill_name)
            os.makedirs(skill_dir, exist_ok=True)
            with open(os.path.join(skill_dir, "SKILL.md"), "w", encoding="utf-8") as f:
                f.write(f"# {skill_name}\n\nThis is a random skill.")
                
            # Reload agent skills prompt
            st.session_state.agent.skills_system_prompt = st.session_state.agent._load_skills_system_prompt()
            st.session_state.agent.agent.instructions += f"\n\n[System Update] New skills available. Check <available_skills>."
        else:
            st.error("Invalid AGENTS.md format")

# Sidebar
with st.sidebar:
    st.title("System Status")
    
    # MCP Status
    st.subheader("MCP Servers")
    col1, col2 = st.columns(2)
    
    tourism_status = check_mcp_status("http://localhost:8001") # Port only check basically
    deep_status = check_mcp_status("http://localhost:8002")
    
    with col1:
        st.metric("Tourism Query", "Running" if tourism_status else "Stopped", delta_color="normal" if tourism_status else "inverse")
    with col2:
        st.metric("Deep Analysis", "Running" if deep_status else "Stopped", delta_color="normal" if deep_status else "inverse")

    # Skills
    st.subheader("Skills Management")
    if st.button("Add Random Skill"):
        add_random_skill()
        st.rerun()
        
    st.markdown("### Loaded Skills")
    if hasattr(st.session_state.agent, 'loaded_skills'):
        for skill in st.session_state.agent.loaded_skills:
            st.code(skill)
    else:
        st.write("No skills loaded yet.")

# Main Chat Interface
st.title("Tourism Analysis Agent")

# Display Chat History
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# Input
if prompt := st.chat_input("Ask about tourism..."):
    # Add user message
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    # Generate Response
    with st.chat_message("assistant"):
        with st.spinner("Thinking..."):
            # Run async loop in synchronous streamlit
            response = asyncio.run(st.session_state.agent.process_query(prompt))
            st.markdown(response)
            
    st.session_state.messages.append({"role": "assistant", "content": response})

# Log Viewer (Expander)
with st.expander("Interaction Logs (Live)", expanded=True):
    # Auto-refresh logs button or just rely on streamlit reruns
    if st.button("Refresh Logs"):
        pass # Rerun
        
    logs = st.session_state.logger.read_logs()
    st.text_area("Logs", logs, height=300)

