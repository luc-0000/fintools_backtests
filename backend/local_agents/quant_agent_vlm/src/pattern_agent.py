import json

from langchain_core.messages import ToolMessage, HumanMessage, SystemMessage, AIMessage
import time
from openai import RateLimitError
import asyncio

def invoke_tool_with_retry(tool_fn, tool_args, retries=3, wait_sec=4):
    """
    Invoke a tool function with retries if the result is missing an image.
    """
    for attempt in range(retries):
        result = tool_fn.invoke(tool_args)
        img_b64 = result.get("pattern_image")
        if img_b64:
            return result
        print(f"Tool returned no image, retrying in {wait_sec}s (attempt {attempt + 1}/{retries})...")
        time.sleep(wait_sec)
    raise RuntimeError("Tool failed to generate image after multiple retries")


def create_pattern_agent(tool_llm, graph_llm, tech_tools):
    """
    Create a pattern recognition agent node for candlestick pattern analysis.
    The agent uses an LLM and MCP chart generation tool to identify classic trading patterns.

    Args:
        tool_llm: Language model for tool usage
        graph_llm: Language model for graph analysis
        tech_tools: List of MCP tools (StructuredTool objects)
    """
    async def pattern_agent_node(state):
        # --- Tool and pattern definitions ---
        tools = tech_tools  # 已经是筛选过的工具列表
        time_frame = state['time_frame']
        pattern_text = """
        Please refer to the following classic candlestick patterns:

        1. Inverse Head and Shoulders: Three lows with the middle one being the lowest, symmetrical structure, typically indicates an upcoming upward trend.
        2. Double Bottom: Two similar low points with a rebound in between, forming a 'W' shape.
        3. Rounded Bottom: Gradual price decline followed by a gradual rise, forming a 'U' shape.
        4. Hidden Base: Horizontal consolidation followed by a sudden upward breakout.
        5. Falling Wedge: Price narrows downward, usually breaks out upward.
        6. Rising Wedge: Price rises slowly but converges, often breaks down.
        7. Ascending Triangle: Rising support line with a flat resistance on top, breakout often occurs upward.
        8. Descending Triangle: Falling resistance line with flat support at the bottom, typically breaks down.
        9. Bullish Flag: After a sharp rise, price consolidates downward briefly before continuing upward.
        10. Bearish Flag: After a sharp drop, price consolidates upward briefly before continuing downward.
        11. Rectangle: Price fluctuates between horizontal support and resistance.
        12. Island Reversal: Two price gaps in opposite directions forming an isolated price island.
        13. V-shaped Reversal: Sharp decline followed by sharp recovery, or vice versa.
        14. Rounded Top / Rounded Bottom: Gradual peaking or bottoming, forming an arc-shaped pattern.
        15. Expanding Triangle: Highs and lows increasingly wider, indicating volatile swings.
        16. Symmetrical Triangle: Highs and lows converge toward the apex, usually followed by a breakout.
        """


        # --- Retry wrapper for LLM invocation ---
        def invoke_with_retry(call_fn, *args, retries=3, wait_sec=8):
            for attempt in range(retries):
                try:
                    return call_fn(*args)
                except RateLimitError as e:
                    print(f"Rate limit hit, retrying in {wait_sec}s (attempt {attempt + 1}/{retries})...")
                    time.sleep(wait_sec)
                except Exception as e:
                    print(f"Other error: {e}, retrying in {wait_sec}s (attempt {attempt + 1}/{retries})...")
                    time.sleep(wait_sec)
            raise RuntimeError("Max retries exceeded")

        # --- Step 2: First LLM call to determine tool usage ---
        messages = state.get("messages", [])
        pattern_image_b64 = None

        # --- Step 3: Handle tool call (generate_kline_image) ---
        for call in tools:
            tool_args = {
                "kline_data": state["kline_data"]
            }
            tool_result = await call.ainvoke(tool_args)
            # MCP 工具返回的是 ToolMessage 列表，需要提取实际内容
            if isinstance(tool_result, list) and len(tool_result) > 0:
                tool_result = tool_result[0].get('text')

            pattern_image_b64 = json.loads(tool_result).get("pattern_image")

        # --- Step 4: Second call with image (Vision LLM expects image_url + context) ---
        if pattern_image_b64:
            image_prompt = [
                {
                    "type": "text",
                    "text": (
                        "You are a trading pattern recognition assistant tasked with identifying classical high-frequency trading patterns. "
                        f"This is a {time_frame} candlestick chart generated from recent OHLC market data:image/png;base64,{pattern_image_b64}.\n\n"
                        f"{pattern_text}\n\n"
                        "Determine whether the chart matches any of the patterns listed. "
                        "Clearly name the matched pattern(s), and explain your reasoning based on structure, trend, and symmetry."
                    )
                },
            ]

            final_response = invoke_with_retry(graph_llm.invoke, [
                SystemMessage(content="You are a trading pattern recognition assistant tasked with analyzing candlestick charts."),
                HumanMessage(content=image_prompt)
            ])
        else:
            # If no image was generated, fall back to reasoning with messages
            final_response = invoke_with_retry(tool_llm.invoke, messages)

        return {
            "messages": messages + [final_response],
            "pattern_report": final_response.content,
        }

    return pattern_agent_node
