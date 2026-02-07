import logging
import os
from uuid import uuid4
import httpx
from a2a.client import A2ACardResolver, A2AClient
from a2a.types import SendStreamingMessageRequest, MessageSendParams
from dotenv import load_dotenv
load_dotenv()


async def run_trading_agent_client(stock_code, base_url) -> bool:
    """
    Run the remote trading agent and return whether it's indicating.

    Args:
        stock_code: Stock code to analyze
        base_url: Base URL of the A2A agent service

    Returns:
        bool: True if indicating (建议买入), False otherwise
    """
    # Configure logging to show INFO level messages
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger(__name__)

    # 设置更长的 timeout，特别是 read timeout
    # read=None 表示不超时，适合长时间 streaming
    timeout = httpx.Timeout(
        connect=10.0,   # 连接超时 10 秒
        read=None,      # 读取不超时，streaming 需要
        write=60.0,     # 写入超时 60 秒
        pool=60.0       # 连接池超时 60 秒
    )
    fintools_access_token = os.getenv('FINTOOLS_ACCESS_TOKEN', 'your-secret-token-here')
    print(f'Start Connecting to remote a2a server: {base_url}...(30~60s)')

    # Collect all text output for analysis
    all_text = []

    async with httpx.AsyncClient(timeout=timeout, headers={'Authorization': f'Bearer {fintools_access_token}'} ) as httpx_client:
        # 获取 agent card
        resolver = A2ACardResolver(httpx_client=httpx_client, base_url=base_url)
        agent_card = await resolver.get_agent_card()
        logger.info(f'Agent card fetched: {agent_card.name}')

        # 创建 client
        # 覆盖 url，指向代理而不是云端内部地址
        client = A2AClient(
            httpx_client=httpx_client,
            agent_card=agent_card,
            url=base_url  # 使用代理地址
        )
        logger.info('A2AClient initialized.')

        # 构造消息
        payload = {
            "message": {
                "role": "user",
                "parts": [
                    {
                        "kind": "text",
                        "text": "test request",
                        "metadata": {"stock_code": stock_code}
                    }
                ],
                "messageId": uuid4().hex,
            }
        }

        # 创建 SendStreamingMessageRequest
        req = SendStreamingMessageRequest(
            id=str(uuid4()),
            params=MessageSendParams(**payload),
        )

        # 使用 send_message_streaming 进行 streaming
        print("\n=== Streaming response ===")
        try:
            event_count = 0
            text_count = 0
            async for chunk in client.send_message_streaming(req):
                event_count += 1

                # 提取并打印 text 部分
                chunk_dict = chunk.model_dump(mode="json", exclude_none=True)

                # 调试：打印事件类型
                if 'result' in chunk_dict and chunk_dict['result']:
                    result = chunk_dict['result']
                    event_kind = result.get('kind', 'unknown')
                    print(f"[DEBUG] Event {event_count}: kind={event_kind}", flush=True)

                    # TaskStatusUpdateEvent 有 status.message
                    if 'status' in result and result['status']:
                        status = result['status']
                        if 'message' in status and status['message']:
                            message = status['message']
                            if 'parts' in message and message['parts']:
                                for part in message['parts']:
                                    if 'text' in part:
                                        text_count += 1
                                        text = part['text']
                                        print(text)
                                        all_text.append(text)
                    # Task 事件（没有 message，跳过）

            print(f"\n=== 总共收到 {event_count} 个事件，{text_count} 个文本消息 ===")

        except Exception as e:
            print(f"\n!!! 异常: {e}")
            import traceback
            traceback.print_exc()
            return False

    # Analyze the output to determine if indicating
    full_output = ''.join(all_text)
    print(f"\n=== Analyzing agent output ===")
    print(f"Full output length: {len(full_output)} characters")

    # Default to indicating if successful execution
    # You can customize this logic based on your agent's output format
    # For example, check for specific keywords:
    indicating_keywords = ['买入', '建议买入', 'indicating', 'buy', '建议']
    not_indicating_keywords = ['不买', '不买入', 'not indicating', 'not buy', '观望']

    full_output_lower = full_output.lower()

    # Check for not_indicating keywords first
    for keyword in not_indicating_keywords:
        if keyword.lower() in full_output_lower:
            print(f"Found keyword '{keyword}' -> NOT indicating")
            return False

    # Check for indicating keywords
    for keyword in indicating_keywords:
        if keyword.lower() in full_output_lower:
            print(f"Found keyword '{keyword}' -> INDICATING")
            return True

    # If no keywords found, default to indicating (successful execution)
    print("No clear keywords found, defaulting to INDICATING")
    return True


if __name__ == '__main__':
    import asyncio
    stock_code = '600519'
    base_url = 'http://8.153.13.5:8000/api/v1/agents/62/a2a/'
    result = asyncio.run(run_trading_agent_client(stock_code, base_url))
    print(f"\n=== Final Result: {'INDICATING' if result else 'NOT INDICATING'} ===")