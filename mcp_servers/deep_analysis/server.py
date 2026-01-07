from fastmcp import FastMCP
from typing import Dict

# Create MCP server
mcp = FastMCP("DeepAnalysis")

@mcp.tool()
def deep_analysis(data: Dict) -> str:
    """对行业数据进行深入分析"""
    annual_output = data.get("annual_output", 0)

    if annual_output > 1000:
        return """【深度分析报告】
1. 产业地位：该行业已进入成熟发展期，产值突破千万级大关，是本地经济的重要支柱。
2. 竞争优势：具备完整的产业链条和较高的技术壁垒，市场占有率稳居区域前列。
3. 发展建议：
   - 建议加大研发投入，推动数字化转型。
   - 拓展国际市场，提升品牌全球影响力。
   - 关注可持续发展，优化能源结构。"""
    else:
        return """【基础分析建议】
1. 现状评估：产业规模尚处起步阶段，增长潜力巨大但基础薄弱。
2. 关键短板：缺乏龙头企业带动，产业链配套不完善。
3. 改进措施：
   - 聚焦细分市场，打造特色品牌。
   - 争取政策扶持，完善基础设施建设。"""

if __name__ == "__main__":
    # Use SSE transport for compatibility with most clients over HTTP
    # Listen on all interfaces
    mcp.run(transport="sse", host="0.0.0.0", port=8002)
