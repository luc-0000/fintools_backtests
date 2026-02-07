"""
DeepSeek LLM适配器，支持Token使用统计
"""

import os
import time
from typing import Any, Dict, List, Optional, Union
from langchain_core.messages import BaseMessage, AIMessage, HumanMessage, SystemMessage, ToolMessage
from langchain_core.outputs import ChatResult
from langchain_openai import ChatOpenAI
from langchain_core.callbacks import CallbackManagerForLLMRun

# 导入token跟踪器
try:
    from local_agents.tauric_mcp.config.config_manager import token_tracker
    TOKEN_TRACKING_ENABLED = True
except ImportError:
    TOKEN_TRACKING_ENABLED = False
    print("⚠️ Token跟踪功能未启用")


class ChatDeepSeek(ChatOpenAI):
    """
    DeepSeek聊天模型适配器，支持Token使用统计
    
    继承自ChatOpenAI，添加了Token使用量统计功能
    """
    
    def __init__(
        self,
        model: str = "deepseek-chat",
        api_key: Optional[str] = None,
        base_url: str = "https://api.deepseek.com",
        temperature: float = 0.1,
        max_tokens: Optional[int] = None,
        **kwargs
    ):
        """
        初始化DeepSeek适配器
        
        Args:
            model: 模型名称，默认为deepseek-chat
            api_key: API密钥，如果不提供则从环境变量DEEPSEEK_API_KEY获取
            base_url: API基础URL
            temperature: 温度参数
            max_tokens: 最大token数
            **kwargs: 其他参数
        """
        
        # 获取API密钥
        if api_key is None:
            api_key = os.getenv("DEEPSEEK_API_KEY")
            if not api_key:
                raise ValueError("DeepSeek API密钥未找到。请设置DEEPSEEK_API_KEY环境变量或传入api_key参数。")
        
        # 初始化父类
        super().__init__(
            model=model,
            openai_api_key=api_key,
            openai_api_base=base_url,
            temperature=temperature,
            max_tokens=max_tokens,
            **kwargs
        )
        
        self.model_name = model
        
    def _generate(
        self,
        messages: List[BaseMessage],
        stop: Optional[List[str]] = None,
        run_manager: Optional[CallbackManagerForLLMRun] = None,
        **kwargs: Any,
    ) -> ChatResult:
        """
        生成聊天响应，并记录token使用量
        """

        # 记录开始时间
        start_time = time.time()

        # 提取并移除自定义参数，避免传递给父类
        session_id = kwargs.pop('session_id', None)
        analysis_type = kwargs.pop('analysis_type', None)

        try:
            # Debug: Print message types
            print(f"🔍 [DeepSeek] Input type: {type(messages)}")

            # Handle ChatPromptValue which contains messages
            if hasattr(messages, 'messages'):
                actual_messages = messages.messages
                print(f"🔍 [DeepSeek] Extracted messages from ChatPromptValue")
            else:
                actual_messages = messages

            if hasattr(actual_messages, '__len__'):
                print(f"🔍 [DeepSeek] Processing {len(actual_messages)} messages")
                for i, msg in enumerate(actual_messages):
                    print(f"🔍 [DeepSeek] Message {i}: type={type(msg)}, content={type(msg.content) if hasattr(msg, 'content') else 'N/A'}")
            else:
                print(f"🔍 [DeepSeek] Messages object: {actual_messages}")

            # 转换消息格式以确保兼容性
            converted_messages = []
            for msg in actual_messages:
                # Handle tuple messages
                if isinstance(msg, tuple):
                    role, content = msg
                    if role == "human":
                        converted_messages.append(HumanMessage(content=content))
                    elif role == "system":
                        converted_messages.append(SystemMessage(content=content))
                    elif role == "ai" or role == "assistant":
                        converted_messages.append(AIMessage(content=content))
                    else:
                        converted_messages.append(HumanMessage(content=str(content)))
                elif isinstance(msg, BaseMessage):
                    if isinstance(msg.content, list):
                        # 如果内容是一个列表，提取文本内容
                        text_content = ""
                        for item in msg.content:
                            if isinstance(item, dict) and item.get("type") == "text":
                                text_content += item.get("text", "")
                        # 创建新的消息对象
                        if isinstance(msg, HumanMessage):
                            converted_messages.append(HumanMessage(content=text_content))
                        elif isinstance(msg, AIMessage):
                            converted_messages.append(AIMessage(content=text_content))
                        elif isinstance(msg, SystemMessage):
                            converted_messages.append(SystemMessage(content=text_content))
                        elif isinstance(msg, ToolMessage):
                            # ToolMessage 需要保留 tool_call_id
                            converted_messages.append(ToolMessage(
                                content=text_content,
                                tool_call_id=msg.tool_call_id
                            ))
                        else:
                            converted_messages.append(HumanMessage(content=text_content))
                    else:
                        converted_messages.append(msg)
                else:
                    # Handle unexpected message types
                    print(f"⚠️ [DeepSeek] Unexpected message type: {type(msg)}")
                    converted_messages.append(HumanMessage(content=str(msg)))

            # 使用转换后的消息调用父类方法
            result = super()._generate(converted_messages, stop, run_manager, **kwargs)
            
            # 提取token使用量
            input_tokens = 0
            output_tokens = 0
            
            # 尝试从响应中提取token使用量
            if hasattr(result, 'llm_output') and result.llm_output:
                token_usage = result.llm_output.get('token_usage', {})
                if token_usage:
                    input_tokens = token_usage.get('prompt_tokens', 0)
                    output_tokens = token_usage.get('completion_tokens', 0)
            
            # 如果没有获取到token使用量，进行估算
            if input_tokens == 0 and output_tokens == 0:
                input_tokens = self._estimate_input_tokens(messages)
                output_tokens = self._estimate_output_tokens(result)
                print(f"🔍 [DeepSeek] 使用估算token: 输入={input_tokens}, 输出={output_tokens}")
            else:
                print(f"📊 [DeepSeek] 实际token使用: 输入={input_tokens}, 输出={output_tokens}")
            
            # 记录token使用量
            if TOKEN_TRACKING_ENABLED and (input_tokens > 0 or output_tokens > 0):
                try:
                    # 使用提取的参数或生成默认值
                    if session_id is None:
                        session_id = f"deepseek_{hash(str(messages))%10000}"
                    if analysis_type is None:
                        analysis_type = 'stock_analysis'

                    # 记录使用量
                    usage_record = token_tracker.track_usage(
                        provider="deepseek",
                        model_name=self.model_name,
                        input_tokens=input_tokens,
                        output_tokens=output_tokens,
                        session_id=session_id,
                        analysis_type=analysis_type
                    )

                    if usage_record:
                        if usage_record.cost == 0.0:
                            print(f"⚠️ [DeepSeek] 成本计算为0，可能配置有问题")
                        else:
                            print(f"💰 [DeepSeek] 本次调用成本: ¥{usage_record.cost:.6f}")
                        print(f"📊 [DeepSeek] 实际token使用: 输入={input_tokens}, 输出={output_tokens}")
                    else:
                        print(f"⚠️ [DeepSeek] 未创建使用记录")

                except Exception as track_error:
                    print(f"⚠️ [DeepSeek] Token统计失败: {track_error}")
                    import traceback
                    traceback.print_exc()
            
            return result
            
        except Exception as e:
            print(f"❌ [DeepSeek] 调用失败: {e}")
            raise
    
    def _convert_messages_to_deepseek_format(self, messages: List[BaseMessage]) -> List[Dict[str, str]]:
        """
        将LangChain消息转换为DeepSeek API格式

        Args:
            messages: LangChain消息列表

        Returns:
            DeepSeek API格式的消息列表
        """
        deepseek_messages = []

        for message in messages:
            # 确定角色
            if isinstance(message, SystemMessage):
                role = "system"
            elif isinstance(message, AIMessage):
                role = "assistant"
            elif isinstance(message, HumanMessage):
                role = "user"
            else:
                # 默认作为用户消息处理
                role = "user"

            # 处理消息内容
            content = message.content
            if isinstance(content, list):
                # 处理多模态内容，提取文本部分
                text_content = ""
                for item in content:
                    if isinstance(item, dict) and item.get("type") == "text":
                        text_content += item.get("text", "")
                content = text_content

            # 确保内容是字符串
            deepseek_messages.append({
                "role": role,
                "content": str(content)
            })

        return deepseek_messages

    def _estimate_input_tokens(self, messages: List[BaseMessage]) -> int:
        """
        估算输入token数量
        
        Args:
            messages: 输入消息列表
            
        Returns:
            估算的输入token数量
        """
        total_chars = 0
        for message in messages:
            if hasattr(message, 'content'):
                total_chars += len(str(message.content))
        
        # 粗略估算：中文约1.5字符/token，英文约4字符/token
        # 这里使用保守估算：2字符/token
        estimated_tokens = max(1, total_chars // 2)
        return estimated_tokens
    
    def _estimate_output_tokens(self, result: ChatResult) -> int:
        """
        估算输出token数量
        
        Args:
            result: 聊天结果
            
        Returns:
            估算的输出token数量
        """
        total_chars = 0
        for generation in result.generations:
            if hasattr(generation, 'message') and hasattr(generation.message, 'content'):
                total_chars += len(str(generation.message.content))
        
        # 粗略估算：2字符/token
        estimated_tokens = max(1, total_chars // 2)
        return estimated_tokens
    
    def invoke(
        self,
        input: Union[str, List[BaseMessage]],
        config: Optional[Dict] = None,
        **kwargs: Any,
    ) -> AIMessage:
        """
        调用模型生成响应
        
        Args:
            input: 输入消息
            config: 配置参数
            **kwargs: 其他参数（包括session_id和analysis_type）
            
        Returns:
            AI消息响应
        """
        
        # 处理输入
        if isinstance(input, str):
            messages = [HumanMessage(content=input)]
        else:
            messages = input
        
        # 调用生成方法
        result = self._generate(messages, **kwargs)
        
        # 返回第一个生成结果的消息
        if result.generations:
            return result.generations[0].message
        else:
            return AIMessage(content="")


def create_deepseek_llm(
    model: str = "deepseek-chat",
    temperature: float = 0.1,
    max_tokens: Optional[int] = None,
    **kwargs
) -> ChatDeepSeek:
    """
    创建DeepSeek LLM实例的便捷函数
    
    Args:
        model: 模型名称
        temperature: 温度参数
        max_tokens: 最大token数
        **kwargs: 其他参数
        
    Returns:
        ChatDeepSeek实例
    """
    return ChatDeepSeek(
        model=model,
        temperature=temperature,
        max_tokens=max_tokens,
        **kwargs
    )


# 为了向后兼容，提供别名
DeepSeekLLM = ChatDeepSeek
