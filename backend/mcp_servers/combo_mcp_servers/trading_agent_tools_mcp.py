import os
import sys
from fastmcp import FastMCP

# Add project root to Python path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from mcp_servers.tools.stock_utils import StockUtils

from mcp_servers.utils import get_mcp_studio_tools_async
from mcp_servers.combo_mcp_servers.trading_agent_tools_mcp_utils import *
from datetime import datetime, timedelta

tool_kit_name = 'TradingAgentTools'
trading_agent_tools_mcp = FastMCP(tool_kit_name)

class TradingAgentTools:

    @staticmethod
    @trading_agent_tools_mcp.tool()
    def get_stock_market_data(
        ticker: Annotated[str, "股票代码（支持A股、港股、美股）"],
        start_date: Annotated[str, "开始日期，格式：YYYY-MM-DD"],
        end_date: Annotated[str, "结束日期，格式：YYYY-MM-DD"]
    ) -> str:
        """
        调用股票数据源获取价格和技术指标数据

        Args:
            ticker: 股票代码（如：000001、0700.HK、AAPL）
            start_date: 开始日期（格式：YYYY-MM-DD）
            end_date: 结束日期（格式：YYYY-MM-DD）

        Returns:
            str: 市场数据和技术分析报告
        """
        try:
            market_info = StockUtils.get_market_info(ticker)
            result_data = []
            try:
                stock_data = get_china_stock_data_tushare(ticker, start_date, end_date)
                result_data.append(f"## A股市场数据\n{stock_data}")
                cash_flow_data = get_china_stock_cash_flow_tushare(ticker, start_date, end_date)
                result_data.append(f"## A股现金流数据\n{cash_flow_data}")
                tech_data = get_china_stock_tech_tushare(ticker, start_date, end_date)
                result_data.append(f"## A股技术面数据\n{tech_data}")
            except Exception as e:
                result_data.append(f"## A股市场数据\n获取失败: {e}")


            # 组合所有数据
            combined_result = f"""# {ticker} 市场数据分析
**股票类型**: {market_info['market_name']}
**货币**: {market_info['currency_name']} ({market_info['currency_symbol']})
**分析期间**: {start_date} 至 {end_date}
{chr(10).join(result_data)}
---
*数据来源: 根据股票类型自动选择最适合的数据源*
"""
            print(f"📈 [统一市场工具] 数据获取完成，总长度: {len(combined_result)}")
            return combined_result

        except Exception as e:
            error_msg = f"统一市场数据工具执行失败: {str(e)}"
            print(f"❌ [统一市场工具] {error_msg}")
            return error_msg


    @staticmethod
    @trading_agent_tools_mcp.tool()
    def get_stock_fundamentals_data(
        ticker: Annotated[str, "股票代码（支持A股、港股、美股）"],
        start_date: Annotated[str, "开始日期，格式：YYYY-MM-DD"] = None,
        end_date: Annotated[str, "结束日期，格式：YYYY-MM-DD"] = None,
        curr_date: Annotated[str, "当前日期，格式：YYYY-MM-DD"] = None
    ) -> str:
        """
        统一的股票基本面分析工具

        Args:
            ticker: 股票代码（如：000001、0700.HK、AAPL）
            start_date: 开始日期（可选，格式：YYYY-MM-DD）
            end_date: 结束日期（可选，格式：YYYY-MM-DD）
            curr_date: 当前日期（可选，格式：YYYY-MM-DD）

        Returns:
            str: 基本面分析数据和报告
        """

        print(f"📊 [统一基本面工具] 分析股票: {ticker}")

        try:
            # 自动识别股票类型
            market_info = StockUtils.get_market_info(ticker)

            # 设置默认日期
            if not curr_date:
                curr_date = datetime.now().strftime('%Y-%m-%d')
            if not start_date:
                start_date = (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d')
            if not end_date:
                end_date = curr_date

            result_data = []
            print(f"🇨🇳 [统一基本面工具] 处理A股数据...")

            try:
                stock_data = get_china_stock_data_tushare(ticker, start_date, end_date)
                result_data.append(f"## A股价格数据\n{stock_data}")
            except Exception as e:
                result_data.append(f"## A股价格数据\n获取失败: {e}")

            try:
                fundamentals_result = get_fundamentals(ticker)
                result_data.append(f"## A股基本面数据\n{fundamentals_result}")
            except Exception as e:
                result_data.append(f"## A股基本面数据\n获取失败: {e}")

            # 组合所有数据
            combined_result = f"""# {ticker} 基本面分析数据
**股票类型**: {market_info['market_name']}
**货币**: {market_info['currency_name']} ({market_info['currency_symbol']})
**分析日期**: {curr_date}

{chr(10).join(result_data)}

---
*数据来源: 根据股票类型自动选择最适合的数据源*
"""

            print(f"📊 [统一基本面工具] 数据获取完成，总长度: {len(combined_result)}")
            return combined_result

        except Exception as e:
            error_msg = f"统一基本面分析工具执行失败: {str(e)}"
            print(f"❌ [统一基本面工具] {error_msg}")
            return error_msg


async def get_trading_agent_tools_mcp_async():
    current_file_path = os.path.abspath(__file__)
    client, all_tools = await get_mcp_studio_tools_async(current_file_path, tool_kit_name)
    return client, all_tools


if __name__ == '__main__':
    trading_agent_tools_mcp.run(transport="stdio")
