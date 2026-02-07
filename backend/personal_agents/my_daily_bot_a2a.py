import sys
import os
import asyncio
import json

# Add project root to Python path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '../..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from dotenv import load_dotenv
from personal_agents.daily_bot.stock_selecting_bot import select_stocks
from a2a.trading_agent_client import run_trading_agent_client


load_dotenv()

async def daily_bot_main():
    """
    Main function that:
    Selects multiple stocks using LLM
    Runs trading agent client to analyze each selected stock
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
            print(f"Analyzing: {stock_code} - {stock_name}")
            print(f"{'='*80}")

            analysis_result = await run_trading_agent_client(stock_code)

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
    result = asyncio.run(daily_bot_main())
    if result:
        print(f"\n✅ Daily bot completed successfully")
        print(f"📊 Final result: {json.dumps(result, indent=2, ensure_ascii=False)}")
    else:
        print("\n❌ Daily bot failed")
