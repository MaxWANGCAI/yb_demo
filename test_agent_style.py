import asyncio
import os
from agent.agent import IndustryAgent
from utils.config import Config

async def test_style():
    config = Config()
    # 模拟初始技能提示词
    with open(os.path.join(config.SKILLS_PATH, "AGENTS.md"), "r") as f:
        skills_prompt = f.read()
    
    agent = IndustryAgent(initial_skills_system_prompt=skills_prompt, dynamic_skills_dict={}, auto_reset=True)
    
    test_queries = [
        "本地的旅游产业发展如何？",
        "本地金融业发展如何？"
    ]
    
    for query in test_queries:
        print(f"\nTesting Query: {query}")
        response = await agent.process_query(query)
        print(f"Agent Response:\n{response}")
        print("-" * 30)

if __name__ == "__main__":
    asyncio.run(test_style())
