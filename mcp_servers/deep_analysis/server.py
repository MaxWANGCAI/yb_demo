from fastmcp import FastMCP
from typing import Dict

# Create MCP server
mcp = FastMCP("DeepAnalysis")

@mcp.tool()
def deep_analyze(data: Dict) -> str:
    """对旅游业数据进行深入分析"""
    annual_output = data.get("annual_output", 0)

    if annual_output > 1000:
        return "深入分析：本地旅游业发展成熟，产业链完整，对区域经济贡献显著，建议继续投资基础设施建设。"
    else:
        return "深入分析：当前产业规模较小，建议集中资源打造核心景点，提升知名度。"

if __name__ == "__main__":
    # Use SSE transport for compatibility with most clients over HTTP
    # Listen on all interfaces
    mcp.run(transport="sse", host="0.0.0.0", port=8002)
