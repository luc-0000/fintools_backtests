import sys
import os

# Add project root to Python path - MUST be before any project imports
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
if project_root in sys.path:
    sys.path.remove(project_root)
sys.path.insert(0, project_root)

from mcp_servers.news_mcp_servers.news_tools_mcp import get_news_mcp_tools_async
from datetime import datetime
from local_agents.tauric_mcp.graph import TradingAgentsGraph
import asyncio
from local_agents.tauric_mcp.default_config import DEFAULT_CONFIG
from mcp_servers.combo_mcp_servers.trading_agent_tools_mcp import get_trading_agent_tools_mcp_async
from dotenv import load_dotenv
load_dotenv()

# get config info
config = DEFAULT_CONFIG.copy()


async def tauric_main(stock_code):
    ta = None
    trading_client = None
    news_client = None
    try:
        # 获取 MCP 工具和客户端
        trading_client, trading_mcp_tools = await get_trading_agent_tools_mcp_async()
        news_client, news_mcp_tools = await get_news_mcp_tools_async()
        mcp_tools = trading_mcp_tools + news_mcp_tools
        print(f"已加载 {len(mcp_tools)} 个 MCP 工具")

        # # Initialize with custom config
        ta = TradingAgentsGraph(debug=True, config=config, mcp_tools=mcp_tools)
        analyze_date = datetime.now().strftime('%Y-%m-%d')
        # forward propagate
        decision = await ta.propagate(stock_code, analyze_date)
        print(decision)

        # Memorize mistakes and reflect
        # ta.reflect_and_remember(1000) # parameter is the position returns

        return str(decision)
    except KeyboardInterrupt:
        print("分析被用户中断", "Ctrl+C")
        return -1
    except Exception as e:
        print(f"分析过程中发生错误: {str(e)}")
        import traceback
        traceback.print_exc()
        return -1
    finally:
        # Clean up resources to prevent warnings
        if ta:
            try:
                # Force cleanup of any remaining async resources
                import gc
                gc.collect()

                # Give time for cleanup
                await asyncio.sleep(0.1)
            except:
                pass

        # 清理 MCP clients
        print("clearning MCP clients...")
        if trading_client is not None:
            del trading_client
        if news_client is not None:
            del news_client
        import gc
        gc.collect()
        print("MCP clients has been clearned!")


if __name__ == "__main__":
    stock_code = '600519'
    result = asyncio.run(tauric_main(stock_code))
    print(result)
