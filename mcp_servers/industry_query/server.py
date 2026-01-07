from fastmcp import FastMCP
import random
from typing import Dict, Any

# Create MCP server - 使用更明确的名字
mcp = FastMCP("industry_query_server")

@mcp.tool()
def get_industry_data(industry: str = "tourism", industry_name: str = None) -> Dict[str, Any]:
    """获取本地行业的发展数据。
    
    Args:
        industry: 行业名称 (如 tourism, finance, it)
        industry_name: 兼容性参数，行业名称的另一种写法
    """
    # 兼容性处理
    actual_industry = industry_name if industry_name else industry
    
    location = "本地"
    # 始终从预设的随机产值中选择
    annual_output = random.choice([60, 80, 140, 1200, 2000])
    # annual_output = 2000 # Force 2000 for testing deep_analysis logic

    return {
        "location": location,
        "industry": actual_industry,
        "annual_output": annual_output,
        "unit": "万元",
        "description": f"{location}{actual_industry}行业年度总产值"
    }

if __name__ == "__main__":
    # Use SSE transport
    mcp.run(transport="sse", host="0.0.0.0", port=8001)
