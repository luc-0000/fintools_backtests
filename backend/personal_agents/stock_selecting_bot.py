import sys
import os
import asyncio
import json
from datetime import datetime

# Add project root to Python path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '../..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from mcp_servers.database_mcp_servers.get_database_mcp import get_database_tools_async
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from dotenv import load_dotenv

load_dotenv()


async def select_stocks(num_stocks):
    """
    Daily bot agent that:
    1. Calls get_indicating_stocks MCP function to get stocks with buy signals
    2. Uses LLM to analyze and choose multiple stocks to trade

    Args:
        num_stocks: Number of stocks to select

    Returns:
        List of selected stock dictionaries, each containing:
        - selected_stock_code
        - selected_stock_name
        - confidence
        - reasoning
        - key_metrics
        - risk_assessment
    """
    db_client = None
    try:
        # Get database MCP tools
        # db_mcp_path = os.path.join(project_root, 'mcp_servers/database_mcp_servers/get_database_mcp.py')
        db_client, db_tools = await get_database_tools_async()
        print(f"✓ Loaded {len(db_tools)} database MCP tools")

        # Find get_indicating_stocks tool
        get_stocks_tool = None
        for tool in db_tools:
            if tool.name == 'get_indicating_stocks':
                get_stocks_tool = tool
                print(f"✓ Found tool: {tool.name}")
                break

        if not get_stocks_tool:
            raise Exception("get_indicating_stocks tool not found")

        # Step 1: Call MCP function to get indicating stocks
        print("\n📊 Fetching indicating stocks...")
        stocks_result = await get_stocks_tool.ainvoke({})
        stocks_data = stocks_result[0].get('text')

        # Step 2: Use LLM to analyze and choose the best stocks
        print(f"\n🤖 Using LLM to analyze and select top {num_stocks} stocks...")

        # Initialize LLM
        llm = ChatOpenAI(
            model="deepseek-chat",
            api_key=os.getenv("DEEPSEEK_API_KEY"),
            base_url="https://api.deepseek.com",
            temperature=1.0
        )

        # Create prompt for stock selection
        system_prompt = """You are a professional Chinese stock market analyst specializing in A-shares and Hong Kong stocks.
Your task is to analyze the provided stock data and select the TOP {num_stocks} BEST stocks to trade today.

Analysis criteria:
1. **Performance Metrics**:
   - Prioritize stocks with higher earning_rate (win rate)
   - Consider avg_earn (average profit per trade)
   - Evaluate total earn (cumulative profit)
   - Look for sufficient trading_times (track record)

2. **Signal Freshness**:
   - Prefer more recent indicating_date (fresher signals)
   - Consider how long the signal has been active

3. **Model Quality**:
   - Evaluate rule_name and created_at to understand model maturity
   - Consider model consistency

4. **Risk Assessment**:
   - Balance high returns with win rate
   - Avoid stocks with too few trades (unreliable statistics)

5. **Diversification**:
   - Select stocks from different sectors/industries if possible
   - Balance different risk profiles

Current date: {current_date}

Return your analysis in the following JSON format with an array of {num_stocks} selected stocks:
{{
    "selected_stocks": [
        {{
            "selected_stock_code": "stock code",
            "selected_stock_name": "stock name",
            "confidence": "high/medium/low",
            "reasoning": "Brief explanation (2-3 sentences) of why this stock was chosen",
            "key_metrics": {{
                "earning_rate": "value",
                "avg_earn": "value",
                "total_earn": "value",
                "trading_times": "value"
            }},
            "risk_assessment": "Brief risk assessment (1-2 sentences)"
        }}
    ]
}}
"""

        prompt = ChatPromptTemplate.from_messages([
            ("system", system_prompt),
            ("user",
             "Here are the stocks with buy signals:\n\n{stocks_data}\n\nPlease analyze and select the top {num_stocks} best stocks to trade.")
        ])

        # Invoke LLM
        chain = prompt | llm
        current_date = datetime.now().strftime('%Y-%m-%d')
        response = await chain.ainvoke({
            "current_date": current_date,
            "num_stocks": num_stocks,
            "stocks_data": json.dumps(stocks_data, indent=2, ensure_ascii=False)
        })

        print("\n" + "=" * 80)
        print("📈 STOCK SELECTION RESULT")
        print("=" * 80)
        print(response.content)
        print("=" * 80 + "\n")

        # Parse the LLM response
        try:
            # Extract JSON from response (in case there's extra text)
            response_text = response.content
            start_idx = response_text.find('{')
            end_idx = response_text.rfind('}') + 1
            if start_idx >= 0 and end_idx > start_idx:
                json_text = response_text[start_idx:end_idx]
                parsed_result = json.loads(json_text)

                # Extract the array of selected stocks
                if 'selected_stocks' in parsed_result:
                    selected_stocks = parsed_result['selected_stocks']

                    print(f"\n✓ Successfully selected {len(selected_stocks)} stocks:")
                    for i, stock in enumerate(selected_stocks, 1):
                        print(f"\n  {i}. {stock['selected_stock_code']} - {stock['selected_stock_name']}")
                        print(f"     Confidence: {stock['confidence']}")
                        print(f"     Reasoning: {stock['reasoning']}")

                    return selected_stocks
                else:
                    print("⚠ 'selected_stocks' key not found in response")
                    return [{"raw_response": response.content}]
            else:
                print("⚠ Could not parse JSON from LLM response")
                return [{"raw_response": response.content}]

        except Exception as parse_err:
            print(f"⚠ Error parsing LLM response: {parse_err}")
            return [{"raw_response": response.content}]

    except Exception as e:
        print(f"❌ Error in daily_bot_main: {e}")
        import traceback
        traceback.print_exc()
        return None

    finally:
        # Cleanup MCP client
        if db_client is not None:
            print("🧹 Cleaning up MCP client...")
            del db_client
            import gc
            gc.collect()


if __name__ == "__main__":
    num_stocks = 3
    results = asyncio.run(select_stocks(num_stocks))
    print(results)

