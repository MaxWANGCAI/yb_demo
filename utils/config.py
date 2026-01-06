import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    MCP_TOURISM_QUERY_PORT = int(os.getenv("MCP_TOURISM_QUERY_PORT", 8001))
    MCP_DEEP_ANALYSIS_PORT = int(os.getenv("MCP_DEEP_ANALYSIS_PORT", 8002))
    # Note: FastMCP default uses SSE transport for HTTP
    MCP_TOURISM_QUERY_URL = os.getenv("MCP_TOURISM_QUERY_URL", "http://localhost:8001/sse")
    MCP_DEEP_ANALYSIS_URL = os.getenv("MCP_DEEP_ANALYSIS_URL", "http://localhost:8002/sse")
    
    LOG_PATH = os.getenv("LOG_PATH", "logs/interactions.log")
    SKILLS_PATH = os.getenv("SKILLS_PATH", "skills")
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
