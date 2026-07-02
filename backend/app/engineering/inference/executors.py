"""推理执行器 - 具体的LLM调用实现"""
from typing import Dict, Any, List, AsyncGenerator
from app.core.logger import logger
from app.engineering.llm.managers.model_manager import ModelManager


class RegularExecutor:
    """常规执行器 - 非流式LLM调用"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.model_manager = ModelManager()
    
    async def execute(self, messages: List[Dict[str, str]], model_name: str, 
                      model_params: Dict[str, Any], model_config: Dict[str, Any] = None, 
                      version_config: Dict[str, Any] = None) -> Dict[str, Any]:
        """执行非流式调用"""
        logger.debug(f"[RegularExecutor] 执行非流式调用: {model_name}")
        
        response = await self.model_manager.chat(
            model_name,
            model_config or {},
            version_config or {},
            messages,
            model_params
        )
        
        return {
            'content': response.get('content', ''),
            'metadata': response.get('metadata', {})
        }


class StreamingExecutor:
    """流式执行器 - 流式LLM调用"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.model_manager = ModelManager()
    
    async def execute(self, messages: List[Dict[str, str]], model_name: str, 
                      model_params: Dict[str, Any], model_config: Dict[str, Any] = None, 
                      version_config: Dict[str, Any] = None) -> AsyncGenerator[str, None]:
        """执行流式调用"""
        logger.debug(f"[StreamingExecutor] 执行流式调用: {model_name}")
        
        model_params_with_stream = {**model_params, 'stream': True}
        
        async for chunk in self.model_manager.chat(
            model_name,
            model_config or {},
            version_config or {},
            messages,
            model_params_with_stream
        ):
            yield chunk


class AgentExecutor:
    """智能体执行器 - LangGraph智能体调用"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
    
    async def execute(self, llm_with_tools, agent_state, workflow) -> Dict[str, Any]:
        """执行智能体调用"""
        logger.debug("[AgentExecutor] 执行智能体调用")
        
        result = await workflow.ainvoke(agent_state)
        
        return {
            'content': result.get('messages', [{}])[-1].get('content', ''),
            'metadata': {'agent_result': result}
        }