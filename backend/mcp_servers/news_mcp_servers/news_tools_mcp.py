import os
import sys

# Add project root to Python path - MUST be before any project imports
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from typing import List
from fastmcp import FastMCP
from mcp_servers.news_mcp_servers.news_tools_mcp_utils import format_news_report, deduplicate_news
from mcp_servers.tools.web_search import baidu_search, bocha_ai_search
from local_agents.tauric_mcp.agents.utils.utils import NewsItem
from mcp_servers.utils import get_mcp_studio_tools_async


tool_kit_name = 'NewsToolsMCP'
trading_agent_tools_mcp = FastMCP(tool_kit_name)

class NewsToolsMCP:

    @staticmethod
    @trading_agent_tools_mcp.tool()
    def get_realtime_stock_news(ticker: str) -> List[NewsItem]:
        """
        获取实时股票新闻
        优先级：专业API > 新闻API > 搜索引擎
        Args:
            ticker: 股票代码（如：000001、0700.HK、AAPL）

        Returns:
            str: 股票新闻分析报告
        """

        all_news = []

        newsapi_baidu = baidu_search(ticker)
        all_news.extend(newsapi_baidu)

        newsapi_bocha_ai = bocha_ai_search(ticker)
        all_news.extend(newsapi_bocha_ai)

        # 去重和排序
        unique_news = deduplicate_news(all_news)

        report = format_news_report(unique_news, ticker)
        return report


    @staticmethod
    @trading_agent_tools_mcp.tool()
    def get_stock_news_sentiment(ticker: str) -> List[NewsItem]:
        """
        获取实时股票新闻
        优先级：专业API > 新闻API > 搜索引擎
        Args:
            ticker: 股票代码（如：000001、0700.HK、AAPL）

        Returns:
            str: 股票新闻分析报告
        """

        all_news = []
        query = f'搜索中国社交媒体和财经平台上关于股票{ticker}的情绪分析和讨论热度。整合雪球、东方财富股吧、新浪财经等平台的数据。'

        newsapi_baidu = baidu_search(query)
        all_news.extend(newsapi_baidu)

        newsapi_bocha_ai = bocha_ai_search(query)
        all_news.extend(newsapi_bocha_ai)

        # 去重和排序
        unique_news = deduplicate_news(all_news)

        report = format_news_report(unique_news, ticker)
        return report


async def get_news_mcp_tools_async():
    current_file_path = os.path.abspath(__file__)
    client, all_tools = await get_mcp_studio_tools_async(current_file_path, tool_kit_name)
    return client, all_tools


if __name__ == '__main__':
    # run_trading_agent_tools_mcp()
    trading_agent_tools_mcp.run(transport="stdio")
