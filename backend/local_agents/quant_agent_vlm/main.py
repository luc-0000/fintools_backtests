import sys
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).resolve().parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from mcp_servers.tech_mcp_servers.tech_tools_mcp import get_tech_tools_mcp_async
import asyncio
from datetime import datetime, timedelta
from local_agents.common.utils import output_results
from local_agents.quant_agent_vlm.src.analyzer import WebTradingAnalyzer
from dotenv import load_dotenv
from common.consts import Agents

load_dotenv()

async def qa_main(symbol):
    tech_client = None
    try:
        # 动态获取 tech_tools 并重新设置 graph
        tech_client, tech_tools = await get_tech_tools_mcp_async()
        analyzer = WebTradingAnalyzer(tech_tools)

        timeframe = '1h'
        end_dt = datetime.now().strftime('%Y%m%d')
        start_dt = (datetime.now() - timedelta(days=30)).strftime('%Y%m%d')
        df = analyzer.fetch_my_data_with_date(symbol, start_dt, end_dt, timeframe)
        # df = pd.DataFrame([])
        if df.empty:
            return {"error": "No data available for the specified parameters"}

        results = await analyzer.run_analysis(df, symbol, timeframe)
        formatted_results = analyzer.extract_analysis_results(results)
        final_decision = formatted_results.get('final_decision').get('decision')
        final_decision = extract_decision(final_decision)
        output_path = Path(__file__).resolve().parent/f'reports/{datetime.now().strftime("%Y-%m-%d")}/'
        output_results(formatted_results, symbol, output_path, Agents.quant_agent)
        print(f'The final decision is {final_decision}')
        return final_decision
    except Exception as e:
        print(e)
        return {"error": str(e)}
    finally:
        # 清理 MCP client
        print("清理 MCP clients...")
        if tech_client is not None:
            del tech_client
        import gc
        gc.collect()
        print("MCP clients 已清理")

def extract_decision(decision):
    final_decision = False
    if decision == 'LONG':
        final_decision = True
    return final_decision


if __name__ == '__main__':
    asyncio.run(qa_main('600519.SH'))
