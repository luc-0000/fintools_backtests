import asyncio
from uuid import uuid4
from a2a.server.events import EventQueue
from a2a.types import (
    Task, TaskStatus, TaskState,
    TaskStatusUpdateEvent,
    Message, TextPart,
)

class StreamingStdout:
    """自定义 stdout 捕获器，实时发送输出到客户端"""
    def __init__(self, queue: EventQueue, loop, task_id: str, context_id: str):
        self.queue = queue
        self.buffer = ""
        self.loop = loop  # 保存事件循环引用
        self.task_id = task_id
        self.context_id = context_id

    def write(self, text: str) -> int:
        """捕获 print 输出并实时发送"""
        self.buffer += text

        # 如果遇到换行符，发送一条消息
        if '\n' in self.buffer:
            lines = self.buffer.split('\n')
            # 发送除了最后一个不完整行之外的所有行
            for line in lines[:-1]:
                if line.strip():  # 只发送非空行
                    # 创建 TaskStatusUpdateEvent
                    evt = TaskStatusUpdateEvent(
                        task_id=self.task_id,
                        context_id=self.context_id,
                        status=TaskStatus(
                            state=TaskState.working,
                            message=Message(
                                role="agent",
                                parts=[TextPart(text=f"📝 {line}")],
                                messageId=uuid4().hex,
                            ),
                        ),
                        final=False,  # 中间消息，不是最终结果
                    )
                    # 在事件循环中安排发送任务
                    asyncio.run_coroutine_threadsafe(
                        self.queue.enqueue_event(evt),
                        self.loop
                    )
            self.buffer = lines[-1]
        return len(text)

def flush(self):
    """实现 flush 方法以兼容 stdout 接口"""
    pass
