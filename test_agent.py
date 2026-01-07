
import asyncio
import os
import sys
from agent.agent import IndustryAgent
from utils.config import Config

async def test():
    # Ensure logs directory exists
    if not os.path.exists("logs"):
        os.makedirs("logs")
    
    # Clear logs to start fresh
    log_path = "logs/interactions.log"
    if os.path.exists(log_path):
        with open(log_path, "w") as f:
            f.write("")

    config = Config()
    
    # Mock skills prompt
    skills_prompt = """
<available_skills>
<skill>
<name>economic_analysis</name>
<description>专注于“行业发展”的综合分析技能。当用户询问任何行业的现状、产值数据或发展前景时，必须加载此技能以获取核心分析逻辑和 MCP 工具调用权限。</description>
<location>project</location>
</skill>
</available_skills>
"""
    
    agent = IndustryAgent(
        initial_skills_system_prompt=skills_prompt,
        dynamic_skills_dict={},
        auto_reset=True
    )
    
    query = "本地金融业发展如何？"
    print(f"Running query: {query}")
    response = await agent.process_query(query)
    print("\nAgent Response:")
    print(response)
    
    print("\nLogs:")
    with open(log_path, "r") as f:
        print(f.read())

if __name__ == "__main__":
    asyncio.run(test())
