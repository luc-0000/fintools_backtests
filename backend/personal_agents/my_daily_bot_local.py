import sys
import os
import asyncio
import json

from common.consts import Agents
from local_agents.quant_agent_vlm.main import qa_main
from local_agents.tauric_mcp.main import tauric_main

# Add project root to Python path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '../..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from dotenv import load_dotenv
from personal_agents.daily_bot.stock_selecting_bot import select_stocks

load_dotenv()

async def daily_bot_main(trading_agent_name):
    """
    Main function that:
    Selects multiple stocks using LLM
    Runs trading agent locally to analyze each selected stock
    """
    try:
        print("\n" + "="*80)
        print("STEP 1: STOCK SELECTION")
        print("="*80)
        num_stocks = 3
        selection_results = await select_stocks(num_stocks)

        if not selection_results or len(selection_results) == 0:
            print("❌ Failed to select stocks")
            return None

        results = []
        for i, stock_selection in enumerate(selection_results, 1):
            stock_code = stock_selection.get('selected_stock_code')
            stock_name = stock_selection.get('selected_stock_name')
            print(f"\n{'='*80}")
            print(f"STEP 2: TRADING AGENT ANALYSIS ({i}/{len(selection_results)})")
            print(f"Agent: {trading_agent_name}")
            print(f"Analyzing: {stock_code} - {stock_name}")
            print(f"{'='*80}")

            analysis_result = None
            if trading_agent_name == Agents.tauric:
                analysis_result = await tauric_main(stock_code)
            elif trading_agent_name == Agents.quant_agent:
                analysis_result = await qa_main(stock_code)

            results.append({
                "stock_selection": stock_selection,
                "stock_code": stock_code,
                "stock_name": stock_name,
                "analysis_result": analysis_result,
                "status": "completed"
            })

        return {
            "total_stocks_analyzed": len(results),
            "results": results,
            "status": "completed"
        }

    except Exception as e:
        print(f"\n❌ Error in daily_bot_main: {e}")
        import traceback
        traceback.print_exc()
        return None


if __name__ == "__main__":
    trading_agent_name = Agents.tauric
    result = asyncio.run(daily_bot_main(trading_agent_name))
    if result:
        print(f"\n✅ Daily bot completed successfully")
        print(f"📊 Final result: {json.dumps(result, indent=2, ensure_ascii=False)}")
    else:
        print("\n❌ Daily bot failed")
