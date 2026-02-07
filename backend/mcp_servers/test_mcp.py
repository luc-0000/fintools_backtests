import os
import sys


project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
if project_root in sys.path:
    sys.path.remove(project_root)
sys.path.insert(0, project_root)

from end_points.init_global import init_global
from end_points.config.global_var import global_var
from mcp_servers.database_mcp_servers.get_database_mcp import get_database_tools_async
from langchain_openai import ChatOpenAI  # 使用 OpenAI 兼容接口
import asyncio
import dotenv
dotenv.load_dotenv()

async def run_mcp():
    # client = MultiServerMCPClient(
    #     {
    #         "DatabaseTool": {
    #             "command": "python",
    #             "args": ["/Users/lu/development/ai/ai_money/am_backend/mcp_servers/database_mcp_servers/get_database_mcp.py"],
    #             "transport": "stdio",
    #         },
    #     }
    # )

    tools = await get_database_tools_async()

    model = ChatOpenAI(
        model="deepseek-chat",
        api_key=os.getenv("DEEPSEEK_API_KEY"),
        base_url="https://api.deepseek.com"
    )

    simple_message = [{"role": "user", "content": f"use tool to get database results for all indicating results"}]
    chain = model.bind_tools(tools)
    response = chain.invoke(simple_message)
    tool_calls = response.tool_calls

    final_results = []
    for tool_call in tool_calls:
        tool_name = tool_call["name"]
        tool_args = tool_call["args"]

        # 从 tools 列表中找到对应的工具并调用
        for tool in tools:
            if tool.name == tool_name:
                # 调用工具
                result = await tool.ainvoke(tool_args)
                final_results.append(result)
                print(f"Tool {tool_name} result: {result}")
                break

    print(f"Final results: {final_results}")


if __name__ == "__main__":
    env_dist = os.environ
    config_file = env_dist.get('CFG_PATH', '../service.conf')
    init_global(config_file)
    db = global_var["db"]
    asyncio.run(run_mcp())
