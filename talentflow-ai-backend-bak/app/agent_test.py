import logging

# --- 日志配置 ---
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("langgraph-agent")

# --- FastMCP 客户端 (用于连接外部工具) ---
from fastmcp import Client

# =================================================================
# 全局 MCP 配置 (统一管理)
# =================================================================
MCP_SERVER_URL = "http://127.0.0.1:8002/mcp" 

async def get_mcp_tools():
    """
    动态建立与 MCP Server 的连接并获取工具列表
    """
    try:
        async with Client(MCP_SERVER_URL) as client:
            tools_list = await client.list_tools()
            
            # 将工具列表转换为字典 {工具名: 工具对象}
            tools_dict = {tool.name: tool for tool in tools_list}
            
            logger.info(f"成功从 MCP Server 获取工具: {list(tools_dict.keys())}")
            return tools_dict
            
    except Exception as e:
        logger.error(f"连接 MCP Server 失败: {e}")
        return {}
