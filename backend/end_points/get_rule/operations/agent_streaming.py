import asyncio
import json
import logging
import os
from datetime import datetime
from typing import AsyncGenerator
from dotenv import load_dotenv

# Load .env file
load_dotenv()

from db.mysql.db_schemas import Rule, RulePool, PoolStock


logger = logging.getLogger(__name__)


async def stream_agent_execution(db, rule_id: int) -> AsyncGenerator[dict, None]:
    """
    Stream agent execution logs for all stocks in the rule's pools.

    Yields:
        dict: Log events with type and data
    """
    logger.info(f"=== Starting agent execution for rule_id={rule_id} ===")
    try:
        # Get rule information
        rule_record = db.session.query(Rule).filter(Rule.id == rule_id).first()
        if not rule_record:
            logger.error(f"Rule {rule_id} not found")
            yield {
                "type": "error",
                "message": f"Rule {rule_id} not found"
            }
            return

        logger.info(f"Found rule: {rule_record.name}, type: {rule_record.type}")
        yield {
            "type": "start",
            "message": f"Starting execution for rule: {rule_record.name} (ID: {rule_id})",
            "timestamp": datetime.now().isoformat()
        }

        yield {
            "type": "start",
            "message": f"Starting execution for rule: {rule_record.name} (ID: {rule_id})",
            "timestamp": datetime.now().isoformat()
        }

        # Get all stocks from pools
        pool_ids = db.session.query(RulePool.pool_id)\
            .filter(RulePool.rule_id == rule_id)\
            .distinct()\
            .all()

        pool_ids = [p[0] for p in pool_ids if p[0]]

        if not pool_ids:
            yield {
                "type": "warning",
                "message": "No pools found for this rule"
            }
            return

        # Get all stock codes
        stocks = db.session.query(PoolStock.stock_code)\
            .filter(PoolStock.pool_id.in_(pool_ids))\
            .distinct()\
            .all()

        # Strip exchange suffix (e.g., '000001.SZ' -> '000001')
        stock_list = [s.split('.')[0] if '.' in s else s for (s,) in stocks]

        if not stock_list:
            yield {
                "type": "warning",
                "message": "No stocks found in pools"
            }
            return

        yield {
            "type": "info",
            "message": f"Found {len(stock_list)} stocks to process",
            "stocks": stock_list
        }

        # Process each stock
        for i, stock_code in enumerate(stock_list, 1):
            yield {
                "type": "stock_start",
                "message": f"[{i}/{len(stock_list)}] Processing {stock_code}...",
                "stock_code": stock_code,
                "progress": f"{i}/{len(stock_list)}"
            }

            try:
                # For remote agents, we want to capture streaming logs
                if rule_record.type == 'remote_agent':
                    async for log_entry in stream_remote_agent_logs(db, rule_id, stock_code):
                        yield log_entry
                else:
                    # For local agents, execute directly in async context
                    from end_points.get_rule.operations.agent_utils import get_agent_func
                    from end_points.common.const.consts import Trade
                    import sys
                    import threading

                    logger.info(f"Starting local agent execution for {stock_code}, rule_id={rule_id}")

                    # Create structures to capture stdout
                    captured_lines = []
                    buffer_lock = threading.Lock()
                    last_sent_count = 0

                    class OutputCapture:
                        def __init__(self, original_stdout, lines, lock):
                            self.original_stdout = original_stdout
                            self.lines = lines
                            self.lock = lock

                        def write(self, text):
                            # Write to original stdout
                            self.original_stdout.write(text)
                            # Capture non-empty lines
                            with self.lock:
                                if '\n' in text:
                                    self.lines.append(text.rstrip('\n'))

                        def flush(self):
                            self.original_stdout.flush()

                    yield {
                        "type": "log",
                        "message": f"Starting local agent execution for {stock_code} (may take a few minutes)...",
                        "stock_code": stock_code
                    }

                    try:
                        module_path = rule_record.info
                        if not module_path:
                            raise ValueError(f"Local agent {rule_id} must have a module path in info field")

                        agent_func = get_agent_func(module_path)
                        if agent_func is None:
                            raise ValueError(f"Failed to import agent from module path: {module_path}")

                        # Redirect stdout to capture agent output
                        original_stdout = sys.stdout
                        sys.stdout = OutputCapture(original_stdout, captured_lines, buffer_lock)

                        # Call the agent function
                        result_or_coro = agent_func(stock_code)

                        if asyncio.iscoroutine(result_or_coro):
                            # For async agents, run with output streaming and heartbeat
                            agent_task = asyncio.create_task(result_or_coro)

                            # Check every 5 seconds
                            check_count = 0
                            while not agent_task.done():
                                try:
                                    await asyncio.wait_for(asyncio.shield(agent_task), timeout=5.0)
                                    break
                                except asyncio.TimeoutError:
                                    check_count += 1

                                    # Send new captured output
                                    with buffer_lock:
                                        current_count = len(captured_lines)
                                        new_lines = captured_lines[last_sent_count:current_count]
                                        last_sent_count = current_count

                                        for line in new_lines:
                                            # Filter meaningful lines
                                            stripped = line.strip()
                                            if stripped and len(stripped) > 3:
                                                yield {
                                                    "type": "log",
                                                    "message": line,
                                                    "stock_code": stock_code
                                                }

                                    # Heartbeat every 30 seconds (6 checks)
                                    if check_count % 6 == 0:
                                        elapsed = check_count * 5
                                        yield {
                                            "type": "log",
                                            "message": f"Agent still running... ({elapsed}s elapsed)",
                                            "stock_code": stock_code
                                        }

                            # Get result
                            result = await agent_task

                            # Send remaining output
                            with buffer_lock:
                                for line in captured_lines[last_sent_count:]:
                                    stripped = line.strip()
                                    if stripped and len(stripped) > 3:
                                        yield {
                                            "type": "log",
                                            "message": line,
                                            "stock_code": stock_code
                                        }
                        else:
                            result = result_or_coro

                        # Restore stdout
                        sys.stdout = original_stdout

                        # Convert result to trade type
                        indicating = Trade.indicating if result is True else Trade.not_indicating
                        indicating_date = datetime.now().date()

                        # Update trading record
                        from end_points.get_rule.operations.agent_utils import update_rule_trading
                        update_rule_trading(db, rule_id, indicating, stock_code, indicating_date)

                        yield {
                            "type": "log",
                            "message": f"Local agent execution completed for {stock_code}: {indicating}",
                            "stock_code": stock_code
                        }

                        yield {
                            "type": "stock_complete",
                            "message": f"✓ {stock_code}: {indicating}",
                            "stock_code": stock_code,
                            "result": {'indicating': indicating, 'result': result}
                        }

                    except Exception as e:
                        logger.error(f"Error running local agent for {stock_code}: {e}")
                        import traceback
                        traceback.print_exc()
                        yield {
                            "type": "stock_error",
                            "message": f"✗ {stock_code}: {str(e)}",
                            "stock_code": stock_code,
                            "error": str(e)
                        }
            except Exception as e:
                logger.error(f"Error processing {stock_code}: {e}")
                yield {
                    "type": "stock_error",
                    "message": f"✗ {stock_code}: {str(e)}",
                    "stock_code": stock_code,
                    "error": str(e)
                }

        yield {
            "type": "complete",
            "message": f"Execution complete for rule {rule_id}",
            "timestamp": datetime.now().isoformat()
        }

    except Exception as e:
        logger.error(f"Error in stream_agent_execution: {e}")
        yield {
            "type": "error",
            "message": f"Fatal error: {str(e)}"
        }


async def stream_remote_agent_logs(db, rule_id: int, stock_code: str) -> AsyncGenerator[dict, None]:
    """
    Stream logs from remote A2A agent execution.

    Args:
        db: Database session
        rule_id: Rule ID
        stock_code: Stock code to analyze

    Yields:
        dict: Log events
    """
    import os
    import httpx
    from uuid import uuid4
    from a2a.client import A2ACardResolver, A2AClient
    from a2a.types import SendStreamingMessageRequest, MessageSendParams
    from end_points.common.const.consts import Trade
    from end_points.get_rule.operations.agent_utils import update_rule_trading
    from datetime import datetime

    rule_record = db.session.query(Rule).filter(Rule.id == rule_id).first()

    # Parse info field - it could be a JSON string with base_url and access_token
    # or just a plain URL string
    info = rule_record.info
    base_url = info
    access_token = os.getenv('FINTOOLS_ACCESS_TOKEN', 'your-secret-token-here')

    # Try to parse as JSON
    try:
        info_dict = json.loads(info)
        if isinstance(info_dict, dict):
            base_url = info_dict.get('base_url', base_url)
            access_token = info_dict.get('access_token', access_token)
    except (json.JSONDecodeError, TypeError):
        # Not JSON, use as plain URL
        pass

    logger.info(f"Using base_url: {base_url}")
    if access_token == 'your-secret-token-here':
        logger.warning("FINTOOLS_ACCESS_TOKEN not set, using default token")

    try:
        yield {
            "type": "log",
            "message": f"Connecting to remote agent at {base_url}...it may take 30~60s...",
            "stock_code": stock_code
        }

        # 设置更长的 timeout
        timeout = httpx.Timeout(
            connect=10.0,
            read=None,
            write=60.0,
            pool=60.0
        )

        all_text = []

        async with httpx.AsyncClient(timeout=timeout, headers={'Authorization': f'Bearer {access_token}'}) as httpx_client:
            # 获取 agent card
            resolver = A2ACardResolver(httpx_client=httpx_client, base_url=base_url)
            agent_card = await resolver.get_agent_card()

            yield {
                "type": "log",
                "message": f"Agent: {agent_card.name}",
                "stock_code": stock_code
            }

            # 创建 client
            client = A2AClient(
                httpx_client=httpx_client,
                agent_card=agent_card,
                url=base_url
            )

            # Strip stock exchange suffix before sending to agent
            clean_stock_code = stock_code.split('.')[0] if '.' in stock_code else stock_code

            # 构造消息
            payload = {
                "message": {
                    "role": "user",
                    "parts": [
                        {
                            "kind": "text",
                            "text": "test request",
                            "metadata": {"stock_code": clean_stock_code}
                        }
                    ],
                    "messageId": uuid4().hex,
                }
            }

            req = SendStreamingMessageRequest(
                id=str(uuid4()),
                params=MessageSendParams(**payload),
            )

            yield {
                "type": "log",
                "message": f"Starting analysis for {stock_code}...",
                "stock_code": stock_code
            }

            # Streaming response
            event_count = 0
            text_count = 0
            async for chunk in client.send_message_streaming(req):
                event_count += 1
                chunk_dict = chunk.model_dump(mode="json", exclude_none=True)

                if 'result' in chunk_dict and chunk_dict['result']:
                    result = chunk_dict['result']

                    if 'status' in result and result['status']:
                        status = result['status']
                        if 'message' in status and status['message']:
                            message = status['message']
                            if 'parts' in message and message['parts']:
                                for part in message['parts']:
                                    if 'text' in part:
                                        text_count += 1
                                        text = part['text']
                                        all_text.append(text)

                                        # Stream text to frontend
                                        yield {
                                            "type": "streaming_text",
                                            "message": text,
                                            "stock_code": stock_code
                                        }

            yield {
                "type": "log",
                "message": f"Received {event_count} events, {text_count} text messages",
                "stock_code": stock_code
            }

        # Analyze the output
        full_output = ''.join(all_text)

        indicating_keywords = ['买入', '建议买入', 'indicating', 'buy', '建议']
        not_indicating_keywords = ['不买', '不买入', 'not indicating', 'not buy', '观望']

        full_output_lower = full_output.lower()
        is_indicating = True  # Default

        # Check for not_indicating keywords first
        for keyword in not_indicating_keywords:
            if keyword.lower() in full_output_lower:
                is_indicating = False
                break

        # Check for indicating keywords
        for keyword in indicating_keywords:
            if keyword.lower() in full_output_lower:
                is_indicating = True
                break

        # Update trading record
        indicating_date = datetime.now().date()
        indicating = Trade.indicating if is_indicating else Trade.not_indicating
        update_rule_trading(db, rule_id, indicating, stock_code, indicating_date)

        result_msg = f"Decision: {'INDICATING' if is_indicating else 'NOT INDICATING'}"
        yield {
            "type": "remote_result",
            "message": result_msg,
            "stock_code": stock_code,
            "indicating": is_indicating
        }

        # Also yield stock_complete for tracking
        yield {
            "type": "stock_complete",
            "message": f"✓ {stock_code}: {result_msg}",
            "stock_code": stock_code
        }

    except Exception as e:
        logger.error(f"Error running remote agent: {e}")
        import traceback
        traceback.print_exc()
        yield {
            "type": "error",
            "message": f"Remote agent error: {str(e)}",
            "stock_code": stock_code
        }


async def stream_single_stock_execution(db, rule_id: int, stock_code: str) -> AsyncGenerator[dict, None]:
    """
    Stream agent execution logs for a single stock.

    This is the single source of truth for single stock execution.
    It handles both local and remote agents.

    Args:
        db: Database session
        rule_id: Rule ID
        stock_code: Stock code to analyze

    Yields:
        dict: Log events
    """
    try:
        # Get rule information
        rule_record = db.session.query(Rule).filter(Rule.id == rule_id).first()
        if not rule_record:
            yield {
                "type": "error",
                "message": f"Rule {rule_id} not found"
            }
            return

        logger.info(f"Starting single stock execution for rule_id={rule_id}, stock_code={stock_code}, type={rule_record.type}")

        yield {
            "type": "start",
            "message": f"Running {stock_code} for rule: {rule_record.name} (ID: {rule_id})",
            "timestamp": datetime.now().isoformat(),
            "stock_code": stock_code
        }

        # Route to appropriate agent type
        if rule_record.type == 'remote_agent':
            # Use the reusable streaming function
            async for log_entry in stream_remote_agent_logs(db, rule_id, stock_code):
                yield log_entry
        else:
            # For local agents, execute directly in async context
            from end_points.get_rule.operations.agent_utils import get_agent_func
            from end_points.common.const.consts import Trade
            import sys
            import threading

            # Create structures to capture stdout
            captured_lines = []
            buffer_lock = threading.Lock()
            last_sent_count = 0

            class OutputCapture:
                def __init__(self, original_stdout, lines, lock):
                    self.original_stdout = original_stdout
                    self.lines = lines
                    self.lock = lock

                def write(self, text):
                    self.original_stdout.write(text)
                    with self.lock:
                        if '\n' in text:
                            self.lines.append(text.rstrip('\n'))

                def flush(self):
                    self.original_stdout.flush()

            try:
                yield {
                    "type": "log",
                    "message": f"Starting agent execution (may take a few minutes)...",
                    "stock_code": stock_code
                }

                module_path = rule_record.info
                if not module_path:
                    raise ValueError(f"Local agent {rule_id} must have a module path in info field")

                agent_func = get_agent_func(module_path)
                if agent_func is None:
                    raise ValueError(f"Failed to import agent from module path: {module_path}")

                # Redirect stdout to capture agent output
                original_stdout = sys.stdout
                sys.stdout = OutputCapture(original_stdout, captured_lines, buffer_lock)

                # Call the agent function
                result_or_coro = agent_func(stock_code)

                if asyncio.iscoroutine(result_or_coro):
                    # For async agents, run with output streaming and heartbeat
                    agent_task = asyncio.create_task(result_or_coro)

                    # Check every 5 seconds
                    check_count = 0
                    while not agent_task.done():
                        try:
                            await asyncio.wait_for(asyncio.shield(agent_task), timeout=5.0)
                            break
                        except asyncio.TimeoutError:
                            check_count += 1

                            # Send new captured output
                            with buffer_lock:
                                current_count = len(captured_lines)
                                new_lines = captured_lines[last_sent_count:current_count]
                                last_sent_count = current_count

                                for line in new_lines:
                                    stripped = line.strip()
                                    if stripped and len(stripped) > 3:
                                        yield {
                                            "type": "log",
                                            "message": line,
                                            "stock_code": stock_code
                                        }

                            # Heartbeat every 30 seconds
                            if check_count % 6 == 0:
                                elapsed = check_count * 5
                                yield {
                                    "type": "log",
                                    "message": f"Agent still running... ({elapsed}s elapsed)",
                                    "stock_code": stock_code
                                }

                    result = await agent_task

                    # Send remaining output
                    with buffer_lock:
                        for line in captured_lines[last_sent_count:]:
                            stripped = line.strip()
                            if stripped and len(stripped) > 3:
                                yield {
                                    "type": "log",
                                    "message": line,
                                    "stock_code": stock_code
                                }
                else:
                    result = result_or_coro

                # Restore stdout
                sys.stdout = original_stdout

                # Convert result to trade type
                indicating = Trade.indicating if result is True else Trade.not_indicating
                indicating_date = datetime.now().date()

                # Update trading record
                from end_points.get_rule.operations.agent_utils import update_rule_trading
                update_rule_trading(db, rule_id, indicating, stock_code, indicating_date)

                yield {
                    "type": "log",
                    "message": f"Agent execution completed: {indicating}",
                    "stock_code": stock_code
                }

                yield {
                    "type": "stock_complete",
                    "message": f"✓ {stock_code}: {indicating}",
                    "stock_code": stock_code,
                    "result": {'indicating': indicating, 'result': result}
                }

            except Exception as e:
                # Restore stdout on error
                sys.stdout = original_stdout
                logger.error(f"Error running local agent for {stock_code}: {e}")
                import traceback
                traceback.print_exc()
                yield {
                    "type": "error",
                    "message": f"✗ {stock_code}: {str(e)}",
                    "stock_code": stock_code,
                    "error": str(e)
                }

        yield {
            "type": "complete",
            "message": f"Execution complete for {stock_code}",
            "timestamp": datetime.now().isoformat(),
            "stock_code": stock_code
        }

    except Exception as e:
        logger.error(f"Error in stream_single_stock_execution: {e}")
        import traceback
        traceback.print_exc()
        yield {
            "type": "error",
            "message": f"Fatal error: {str(e)}",
            "stock_code": stock_code
        }
