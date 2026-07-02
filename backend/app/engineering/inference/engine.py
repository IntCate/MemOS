"""推理引擎 - 独立的LLM调用层"""
from typing import Dict, Any, List, AsyncGenerator, Optional
from app.core.logger import logger
from .executors import RegularExecutor, StreamingExecutor, AgentExecutor
from ..data_structures import InferenceResult
from app.utils.error_handler import async_handle_errors


class InferenceEngine:
    """推理引擎 - 独立的LLM调用层"""
    
    def __init__(self, config: Dict[str, Any] = None):
        self.config = config or {}
        self.regular_executor = RegularExecutor(self.config)
        self.streaming_executor = StreamingExecutor(self.config)
        self.agent_executor = AgentExecutor(self.config)
    
    @async_handle_errors(default_return=InferenceResult(success=False, error="调用失败"))
    async def chat(self, messages: List[Dict[str, str]], model_name: str, 
                   model_params: Dict[str, Any] = None, model_config: Dict[str, Any] = None,
                   version_config: Dict[str, Any] = None) -> InferenceResult:
        """非流式调用"""
        logger.info(f"[InferenceEngine] 开始非流式调用，模型: {model_name}")
        result = await self.regular_executor.execute(
            messages, model_name, model_params or {}, 
            model_config or {}, version_config or {}
        )
        return InferenceResult(
            success=True,
            content=result.get('content', ''),
            model_name=model_name,
            metadata=result.get('metadata', {})
        )
    
    async def chat_streaming(self, messages: List[Dict[str, str]], model_name: str, 
                             model_params: Dict[str, Any] = None, model_config: Dict[str, Any] = None,
                             version_config: Dict[str, Any] = None) -> AsyncGenerator[str, None]:
        """流式调用"""
        logger.info(f"[InferenceEngine] 开始流式调用，模型: {model_name}")
        try:
            async for chunk in self.streaming_executor.execute(
                messages, model_name, model_params or {},
                model_config or {}, version_config or {}
            ):
                yield chunk
        except Exception as e:
            logger.error(f"[InferenceEngine] 流式调用失败: {str(e)}")
            yield f"error: {str(e)}"
    
    @async_handle_errors(default_return=InferenceResult(success=False, error="智能体调用失败"))
    async def agent_invoke(self, llm_with_tools, agent_state, workflow) -> InferenceResult:
        """智能体调用"""
        logger.info("[InferenceEngine] 开始智能体调用")
        result = await self.agent_executor.execute(llm_with_tools, agent_state, workflow)
        return InferenceResult(
            success=True,
            content=result.get('content', ''),
            model_name=result.get('model_name', ''),
            metadata=result.get('metadata', {})
        )