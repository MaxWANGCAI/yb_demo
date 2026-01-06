from fastmcp import FastMCP
import random
from typing import Dict

# Create MCP server
mcp = FastMCP("TourismDataQuery")

@mcp.tool()
def get_tourism_data() -> Dict:
    """获取旅游业年产值数据，随机返回60万或2000万"""
    # Randomly choose between 60 (low) and 2000 (high)
    annual_output = random.choice([60, 2000])

    return {
        "annual_output": annual_output,
        "unit": "万元",
        "description": "本地旅游业年度总产值"
    }

if __name__ == "__main__":
    # Use SSE transport
    mcp.run(transport="sse", host="0.0.0.0", port=8001)
