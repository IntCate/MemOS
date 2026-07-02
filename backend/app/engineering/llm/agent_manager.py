from typing import Dict, Any, List, AsyncIterator

from app.engineering.llm.base.base_model import BaseModel
from app.engineering.llm.agent.agent_state import AgentState
from app.engineering.llm.agent.agent_nodes import AgentNodes
from app.core.logger import logger


class AgentManager:
    """智能体管理器"""
    
    def __init__(self, base_model: BaseModel):
        """
        初始化智能体管理器
        
        Args:
            base_model: 基础模型实例
        """
        self.base_model = base_model
        self.llm = base_model.llm
        self.llm_with_tools = self.llm
        self.graph = None
        self.is_initialized = False
        self.agent_nodes = None
    
    async def initialize(self):
        """
        初始化智能体
        
        工具绑定功能已迁移至 capabilities 层，后续可通过 MCPCapability 提供工具绑定。
        """
        if self.is_initialized:
            return
        
        # 工具绑定功能已迁移至 capabilities 层
        self.agent_nodes = AgentNodes(self.llm_with_tools)
        
        self.graph = self._build_graph()
        self.is_initialized = True
    
    def _build_graph(self):
        """
        构建智能体状态图
        
        Returns:
            编译后的状态图
        """
        # 动态导入langgraph
        from langgraph.graph import StateGraph, END
        
        builder = StateGraph(AgentState)
        builder.add_node("reasoning", self.agent_nodes.reasoning_node)
        builder.add_node("execute_linear", self.agent_nodes.execute_linear_node)
        builder.add_node("execute_nonlinear", self.agent_nodes.execute_nonlinear_node)
        builder.add_node("reflect", self.agent_nodes.reflect_node)
        
        builder.set_entry_point("reasoning")
        builder.add_conditional_edges("reasoning", self.agent_nodes.should_continue, {
            "execute_linear": "execute_linear",
            "execute_nonlinear": "execute_nonlinear",
            END: END
        })
        builder.add_edge("execute_linear", "reflect")
        builder.add_edge("execute_nonlinear", "reflect")
        builder.add_edge("reflect", "reasoning")
        
        return builder.compile()
    
    def _prepare_agent(self, model_params: Dict[str, Any]):
        """
        准备智能体执行环境

        Args:
            model_params: 模型参数字典
        """
        call_kwargs = self.base_model._prepare_call_kwargs(model_params)
        self.llm_with_tools = self.llm.bind_tools([], **call_kwargs)
        self.agent_nodes = AgentNodes(self.llm_with_tools)
        self.graph = self._build_graph()

    async def chat_stream(
        self, 
        messages: List[Dict[str, str]], 
        model_params: Dict[str, Any]
    ) -> AsyncIterator[Dict[str, Any]]:
        """
        智能体流式聊天接口

        Args:
            messages: 消息列表
            model_params: 模型参数字典

        Yields:
            流式输出的事件
        """
        if not self.is_initialized:
            await self.initialize()

        # 准备智能体执行环境
        self._prepare_agent(model_params)

        prepared_messages = await self._prepare_messages(messages)
        logger.debug(f"[Agent] 初始消息: {[msg.content[:100] + '...' if len(msg.content) > 100 else msg.content for msg in prepared_messages]}")
        
        # 智能体模式
        initial_state = {
            "messages": prepared_messages,
            "loop_count": 0
        }
        
        # 节点执行步骤计数和当前节点跟踪
        agent_step = 0
        current_node = None
        
        try:
            async for event in self.graph.astream_events(initial_state, version="v2"):
                kind = event.get('event')
                metadata = event.get('metadata', {})
                node = metadata.get('langgraph_node', '')
                
                # 当节点变化时增加步骤计数
                if node != current_node and node:
                    agent_step += 1
                    current_node = node

                if kind == "on_chat_model_stream":
                    chunk = event.get('data', {}).get('chunk')
                    if chunk:
                        # 提取 reasoning_content
                        reasoning_content = None
                        if hasattr(chunk, 'additional_kwargs') and isinstance(chunk.additional_kwargs, dict):
                            reasoning_content = chunk.additional_kwargs.get('reasoning_content')
                        
                        if chunk.content or reasoning_content is not None:
                            # 重点：此处输出包含 <thought> 标签和 reasoning_content，前端可根据此标签渲染 UI
                            yield {
                                'event': 'on_chat_model_stream',
                                'node': node,
                                'agent_step': agent_step,
                                'data': {
                                    'content': chunk.content,
                                    'reasoning_content': reasoning_content
                                }
                            }
                    
                    if chunk and hasattr(chunk, 'tool_call_chunks') and chunk.tool_call_chunks:
                        yield {
                            'event': 'on_tool_call_stream',
                            'node': node,
                            'agent_step': agent_step,
                            'data': {'tool_calls': chunk.tool_call_chunks}
                        }

                elif kind == "on_tool_start":
                    tool_name = event.get('name', '')
                    yield {
                        'event': 'on_tool_start',
                        'node': node,
                        'agent_step': agent_step,
                        'name': tool_name,
                        'data': {'input': event.get('data', {}).get('input', {})}
                    }
                elif kind == "on_tool_end":
                    tool_name = event.get('name', '')
                    yield {
                        'event': 'on_tool_end',
                        'node': node,
                        'agent_step': agent_step,
                        'name': tool_name,
                        'data': {'output': event.get('data', {}).get('output', {})}
                    }

        except Exception as e:
            logger.error(f"[Agent] Stream Error: {str(e)}")
            yield {"event": "on_error", "data": str(e)}
    
    async def _prepare_messages(self, messages: List[Dict[str, str]]) -> List:
        """
        准备消息格式
        
        Args:
            messages: 原始消息列表
        
        Returns:
            格式化后的消息列表
        """
        from app.utils.message import MessageSystem
        
        return MessageSystem.convert_to_langchain_messages(messages)
    
    async def chat(
        self, 
        messages: List[Dict[str, str]], 
        model_params: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        智能体非流式聊天接口

        Args:
            messages: 消息列表
            model_params: 模型参数字典

        Returns:
            包含content和reasoning_content的字典
        """
        if not self.is_initialized:
            await self.initialize()

        # 准备智能体执行环境
        self._prepare_agent(model_params)

        prepared_messages = await self._prepare_messages(messages)
        
        # 智能体模式
        initial_state = {
            "messages": prepared_messages,
            "loop_count": 0
        }
        
        try:
            # 动态导入AIMessage
            from langchain_core.messages import AIMessage
            
            # 执行智能体图
            final_state = await self.graph.ainvoke(initial_state)
            
            # 从最终状态中获取回复
            if final_state and "messages" in final_state:
                for message in reversed(final_state["messages"]):
                    if isinstance(message, AIMessage):
                        # 提取reasoning_content
                        reasoning_content = None
                        if hasattr(message, 'additional_kwargs') and isinstance(message.additional_kwargs, dict):
                            reasoning_content = message.additional_kwargs.get('reasoning_content')
                        return {
                            'content': message.content,
                            'reasoning_content': reasoning_content
                        }
            
            return {
                'content': "智能体处理完成，但未生成回复",
                'reasoning_content': None
            }
        except Exception as e:
            logger.error(f"[Agent] Chat Error: {str(e)}")
            return {
                'content': f"智能体处理失败: {str(e)}",
                'reasoning_content': None
            }

    def __getattr__(self, name):
        """
        代理获取基础模型的属性
        
        Args:
            name: 属性名
        
        Returns:
            基础模型的属性
        """
        return getattr(self.base_model, name)
