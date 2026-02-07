import asyncio
from uuid import uuid4
from a2a.server.agent_execution import AgentExecutor, RequestContext
from a2a.server.events import EventQueue
from a2a.types import (
    Task, TaskStatus, TaskState,
    TaskStatusUpdateEvent,
    Message, TextPart,
)
from local_agents.quant_agent_vlm.main import qa_main
from local_agents.tauric_mcp.main import tauric_main
from remote_agents_a2a.utils import StreamingStdout



class StreamingAgentExecutor(AgentExecutor):
    """
    Agent Executor with streaming progress updates
    捕获 agent 的 stdout 输出并实时返回
    """
    def __init__(self, agent_name):
        self.agent = agent_name

    async def execute(self, context: RequestContext, event_queue: EventQueue) -> None:
        print("[SERVER] TauricStreamingAgentExecutor execute() 开始")

        stock_code = None
        if context.message.parts:
            p0 = context.message.parts[0]
            if isinstance(p0.root, TextPart):
                stock_code = (p0.root.metadata or {}).get("stock_code")

        # 使用 handler 生成的 task_id，不要自己生成
        task_id = context.task_id
        context_id = context.context_id or uuid4().hex
        print(f"[SERVER] task_id = {task_id}, context_id = {context_id}")

        # 1) 先发送 Task 事件
        print("[SERVER] 发送 Task")
        task = Task(
            id=task_id,
            context_id=context_id,
            status=TaskStatus(state=TaskState.working),
        )
        await event_queue.enqueue_event(task)
        print("[SERVER] Task 已入队")

        # 辅助函数：发送进度更新
        async def send_progress(text: str, final: bool = False, state: TaskState = TaskState.working):
            print(f"[SERVER] 发送进度: {text} (final={final})")
            evt = TaskStatusUpdateEvent(
                task_id=task_id,
                context_id=context_id,
                status=TaskStatus(
                    state=state,
                    message=Message(
                        role="agent",
                        parts=[TextPart(text=text)],
                        messageId=uuid4().hex,  # 必填字段
                    ),
                ),
                final=final,
            )
            await event_queue.enqueue_event(evt)
            print(f"[SERVER] 进度已入队")

        try:
            # stock_code = "600519"

            # 2) 发送开始消息 (final=False)
            await send_progress(f"🚀 开始分析股票 {stock_code}...", final=False)

            # 3) 使用自定义 stdout 捕获输出
            import sys
            original_stdout = sys.stdout
            loop = asyncio.get_event_loop()
            captured_stdout = StreamingStdout(event_queue, loop, task_id, context_id)
            sys.stdout = captured_stdout
            result = None

            try:
                await send_progress(f"⏳ 正在调用Trading Agent...", final=False)
                if self.agent == 'tauric':
                    result = await tauric_main(stock_code)
                elif self.agent == 'qa':
                    result = await qa_main(stock_code)
                await send_progress(f"✓ Trading Agent 执行完成", final=False)

            except Exception as exec_err:
                await send_progress(
                    f"⚠️ Trading Agent 执行异常: {exec_err}",
                    final=True,
                    state=TaskState.failed
                )
                raise
            finally:
                # 恢复原始 stdout
                sys.stdout = original_stdout

                # 发送剩余的缓冲内容
                if captured_stdout.buffer.strip():
                    await send_progress(f"📝 {captured_stdout.buffer}", final=False)

            # 4) 发送最终结果 (final=True, state=completed)
            await send_progress(
                f"✅ 分析完成！决策结果：{result}",
                final=True,
                state=TaskState.completed
            )

        except Exception as e:
            print(f"[SERVER] 异常: {e}")
            await send_progress(
                f"❌ 执行失败: {e!r}",
                final=True,
                state=TaskState.failed
            )
            raise

        print("[SERVER] TauricStreamingAgentExecutor execute() 结束")

    async def cancel(
            self, context: RequestContext, event_queue: EventQueue
    ) -> None:
        raise Exception('cancel not supported')