"""
Agent for trend analysis in high-frequency trading (HFT) context.
Uses LLM and toolkit to generate and interpret trendline charts for short-term prediction.
"""
from langchain_core.messages import ToolMessage, HumanMessage, SystemMessage
import json
import time
from openai import RateLimitError

# --- Retry wrapper for LLM invocation ---
def invoke_with_retry(call_fn, *args, retries=3, wait_sec=4):
    """
    Retry a function call with exponential backoff for rate limits or errors.
    """
    for attempt in range(retries):
        try:
            result = call_fn(*args)
            return result
        except RateLimitError:
            print(f"Rate limit hit, retrying in {wait_sec}s (attempt {attempt + 1}/{retries})...")
        except Exception as e:
            print(f"Other error: {e}, retrying in {wait_sec}s (attempt {attempt + 1}/{retries})...")
        # Only sleep if not the last attempt
        if attempt < retries - 1:
            time.sleep(wait_sec)
    raise RuntimeError("Max retries exceeded")


def create_trend_agent(tool_llm, graph_llm, tech_tools):
    """
    Create a trend analysis agent node for HFT. The agent uses LLM and MCP chart tool to analyze trendlines and predict short-term direction.

    Args:
        tool_llm: Language model for tool usage
        graph_llm: Language model for graph analysis
        tech_tools: List of MCP tools (StructuredTool objects)
    """
    async def trend_agent_node(state):
        # --- Tool definitions ---
        tools = tech_tools  # 已经是筛选过的工具列表
        time_frame = state['time_frame']

        # --- System prompt for LLM ---
        system_prompt = (
            "You are a K-line trend pattern recognition assistant operating in a high-frequency trading context. "
            "According to the chart generated, analyze the image for support/resistance trendlines and known candlestick patterns. "
            "Only then should you proceed to make a prediction about the short-term trend (upward, downward, or sideways). "
        )
        #
        # # --- Compose messages for the first round ---
        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=f"Here is the recent kline data:\n{json.dumps(state['kline_data'], indent=2)}")
        ]

        trend_image_b64 = None
        for call in tools:
            tool_args = {
                "kline_data": state["kline_data"]
            }
            tool_result = await call.ainvoke(tool_args)
            # MCP 工具返回的是 ToolMessage 列表，需要提取实际内容
            if isinstance(tool_result, list) and len(tool_result) > 0:
                tool_result = tool_result[0].get('text')

            trend_image_b64 = json.loads(tool_result).get("trend_image")
            # trend_image_b64 = tool_result.get("trend_image")

        # --- Step 3: Second call with image (Vision LLM expects image_url + context) ---
        if trend_image_b64:
            image_prompt = [
                {
                    "type": "text",
                    "text": (
                        f"This candlestick ({time_frame} K-line) chart includes automated trendlines: the **blue line** is support, and the **red line** is resistance, both derived from recent closing prices.\n\n"
                        "Analyze how price interacts with these lines — are candles bouncing off, breaking through, or compressing between them?\n\n"
                        "Based on trendline slope, spacing, and recent K-line behavior, predict the likely short-term trend: **upward**, **downward**, or **sideways**. "
                        "Support your prediction with respect to prediction, reasoning, signals."
                    )
                },
                {
                    "type": "image_url",
                    "image_url": {
                        "url": f"data:image/png;base64,{trend_image_b64}"
                    }
                }
            ]

            final_response = invoke_with_retry(graph_llm.invoke, [
                SystemMessage(content="You are a K-line trend pattern recognition assistant operating in a high-frequency trading context. "
                "Your task is to analyze candlestick charts annotated with support and resistance trendlines."),
                HumanMessage(content=image_prompt)
            ])
        else:
            # If no image was generated, fall back to reasoning with messages
            final_response = invoke_with_retry(tool_llm.invoke, messages)

        return {
            "messages": messages + [final_response],
            "trend_report": final_response.content,
            "trend_image_base64": trend_image_b64
        }

    return trend_agent_node