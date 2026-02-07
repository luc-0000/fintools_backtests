"""
基本面分析师 - 统一工具架构版本
使用统一工具自动识别股票类型并调用相应数据源
"""

from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
# from local_agents.tauric_mcp.agents.utils.message_formatter import format_messages


def create_fundamentals_analyst(llm, mcp_tools):
    def fundamentals_analyst_node(state):
        print(f"📊 [DEBUG] ===== 基本面分析师节点开始 =====")

        current_date = state["trade_date"]
        ticker = state["company_of_interest"]
        # start_date = '2025-05-28'

        print(f"📊 [DEBUG] 输入参数: ticker={ticker}, date={current_date}")
        print(f"📊 [DEBUG] 当前状态中的消息数量: {len(state.get('messages', []))}")
        print(f"📊 [DEBUG] 现有基本面报告: {state.get('fundamentals_report', 'None')[:100]}...")

        # 获取股票市场信息
        from mcp_servers.tools.stock_utils import StockUtils
        print(f"📊 [基本面分析师] 正在分析股票: {ticker}")

        market_info = StockUtils.get_market_info(ticker)

        # 从 mcp_tools 列表中查找需要的工具
        tools = []
        for tool in mcp_tools:
            if tool.name == 'get_stock_fundamentals_data':
                tools.append(tool)

        # 统一的系统提示，适用于所有股票类型
        system_message = (
            f"你是一位专业的股票基本面分析师。"
            f"⚠️ 绝对强制要求：你必须调用工具获取真实数据！不允许任何假设或编造！"
            f"任务：分析股票代码 {ticker} ({market_info['market_name']})"
            # f"🔴 立即调用 get_stock_fundamentals_unified 工具"
            # f"参数：ticker='{ticker}', start_date='{start_date}', end_date='{current_date}', curr_date='{current_date}'"
            "📊 分析要求："
            "- 基于真实数据进行深度基本面分析"
            f"- 计算并提供合理价位区间（使用{market_info['currency_name']}{market_info['currency_symbol']}）"
            "- 分析当前股价是否被低估或高估"
            "- 提供基于基本面的目标价位建议"
            "- 包含PE、PB、PEG等估值指标分析"
            "- 结合市场特点进行分析"
            "🌍 语言和货币要求："
            "- 所有分析内容必须使用中文"
            "- 投资建议必须使用中文：买入、持有、卖出"
            "- 绝对不允许使用英文：buy、hold、sell"
            f"- 货币单位使用：{market_info['currency_name']}（{market_info['currency_symbol']}）"
            "🚫 严格禁止："
            "- 不允许说'我将调用工具'"
            "- 不允许假设任何数据"
            "- 不允许编造公司信息"
            "- 不允许直接回答而不调用工具"
            "- 不允许回复'无法确定价位'或'需要更多信息'"
            "- 不允许使用英文投资建议（buy/hold/sell）"
            "✅ 你必须："
            "- 立即调用统一基本面分析工具"
            "- 等待工具返回真实数据"
            "- 基于真实数据进行分析"
            "- 提供具体的价位区间和目标价"
            "- 使用中文投资建议（买入/持有/卖出）"
            "现在立即开始调用工具！不要说任何其他话！"
        )

        # 系统提示模板
        system_prompt = (
            "🔴 强制要求：你必须调用工具获取真实数据！"
            "🚫 绝对禁止：不允许假设、编造或直接回答任何问题！"
            "✅ 你必须：立即调用提供的工具获取真实数据，然后基于真实数据进行分析。"
            "可用工具：{tool_names}。\n{system_message}"
            "当前日期：{current_date}。分析目标：{ticker}。"
        )

        # 创建提示模板
        prompt = ChatPromptTemplate.from_messages([
            ("system", system_prompt),
            MessagesPlaceholder(variable_name="messages"),
        ])

        prompt = prompt.partial(system_message=system_message)
        prompt = prompt.partial(tool_names=", ".join([tool.name for tool in tools]))
        prompt = prompt.partial(current_date=current_date)
        prompt = prompt.partial(ticker=ticker)

        chain = prompt | llm.bind_tools(tools)

        # Ensure messages are properly formatted
        # formatted_messages = format_messages(state["messages"])
        result = chain.invoke(state['messages'])

        report = ""

        if len(result.tool_calls) == 0:
            report = result.content

        return {
            "messages": [result],
            "fundamentals_report": report,
        }



    return fundamentals_analyst_node
