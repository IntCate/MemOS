"""Harness引擎 - Agent的控制中心"""
import uuid
from datetime import datetime
from typing import Dict, Any, List, AsyncGenerator

from app.core.logger import logger
from app.memory import MemoryManager, MemoryType, get_memory_manager
from app.knowledgebase import KnowledgeBaseManager, get_knowledge_base_manager
from ..data_structures import (
    Message, Decision, Response
)
from ..prompt.engine import PromptEngine
from ..inference.engine import InferenceEngine
from ..context.engine import ContextEngine
from ..context.data_structures import Context


class HarnessEngine:
    """Harness引擎 - Agent的控制中心"""
    
    def __init__(self, config: Dict[str, Any] = None):
        self.config = config or {}
        self.prompt_engine = PromptEngine(self.config.get('prompt', {}))
        self.inference_engine = InferenceEngine(self.config.get('inference', {}))
        self.memory_manager: MemoryManager = get_memory_manager(self.config.get('memory', {}))
        self.knowledge_base_manager: KnowledgeBaseManager = get_knowledge_base_manager(self.config.get('knowledge_base', {}))
        self.context_engine = ContextEngine(self.config.get('context', {}))
    
    async def process(self, message: Message) -> Response:
        """处理消息的统一入口"""
        logger.info(f"[HarnessEngine] 开始处理消息: channel={message.channel.value}, user={message.user_id}, content={message.content[:100]}...")
        
        try:
            context = await self.context_engine.get_or_create_context(message)
            
            decision = Decision(use_streaming=False)
            model_config = context.to_dict().get('model_config', {})
            decision.selected_model = model_config.get('model_name', '')
            decision.model_params = model_config.get('model_params', {})
            
            chat_context = await self._get_chat_context(message)
            
            context = await self.context_engine.enhance_context(context)
            
            model_messages = await self._prepare_model_input(message, context, chat_context)
            
            inference_result = await self.inference_engine.chat(
                messages=model_messages,
                model_name=decision.selected_model,
                model_params=decision.model_params,
                model_config=model_config,
                version_config=model_config.get('version_config', {})
            )
            
            await self._store_memory(message, inference_result)
            
            await self._sync_working_memory(message, inference_result)
            
            return self._build_response(message, inference_result)
        
        except Exception as e:
            logger.error(f"[HarnessEngine] 处理消息失败: {str(e)}", exc_info=True)
            return Response(
                message_id=str(uuid.uuid4()),
                channel=message.channel,
                user_id=message.user_id,
                content="",
                success=False,
                error=str(e),
                chat_id=message.chat_id
            )
    
    async def process_streaming(self, message: Message) -> AsyncGenerator[str, None]:
        """流式处理消息"""
        logger.info(f"[HarnessEngine] 开始流式处理消息: {message.content[:100]}...")
        
        try:
            context = await self.context_engine.get_or_create_context(message)
            
            decision = Decision(use_streaming=False)
            model_config = context.to_dict().get('model_config', {})
            decision.selected_model = model_config.get('model_name', '')
            decision.model_params = model_config.get('model_params', {})
            
            chat_context = await self._get_chat_context(message)
            
            context = await self.context_engine.enhance_context(context)
            
            model_messages = await self._prepare_model_input(message, context, chat_context)
            
            decision.use_streaming = True
            
            chunks: List[str] = []
            async for chunk in self.inference_engine.chat_streaming(
                messages=model_messages,
                model_name=decision.selected_model,
                model_params=decision.model_params,
                model_config=model_config,
                version_config=model_config.get('version_config', {})
            ):
                chunks.append(chunk)
                yield chunk

            # 流式完成后持久化记忆（与非流式 process() 行为一致）
            import types
            result = types.SimpleNamespace(
                content="".join(chunks),
                success=True,
                error="",
                model_name=decision.selected_model
            )
            await self._store_memory(message, result)
            await self._sync_working_memory(message, result)
            
        except Exception as e:
            logger.error(f"[HarnessEngine] 流式处理失败: {str(e)}", exc_info=True)
            yield f"error: {str(e)}"
    
    async def _get_chat_context(self, message: Message) -> Dict[str, Any]:
        """获取对话上下文 - 从工作区记忆中获取"""
        chat_id = message.chat_id
        
        if not chat_id:
            chat_id = str(uuid.uuid4())
            message.chat_id = chat_id
        
        working_memories = await self.memory_manager.get_chat_history(chat_id)
        
        messages = []
        for memory in working_memories:
            messages.append({
                'role': memory.metadata.get('role', 'user'),
                'content': memory.content,
                'id': memory.id,
                'timestamp': memory.timestamp.isoformat()
            })
        
        return {
            'id': chat_id,
            'messages': messages,
            'title': message.content[:30] if message.content else "新对话"
        }
    
    async def _prepare_model_input(self, message: Message, 
                                  context: Context, chat_context: Dict[str, Any]) -> List[Dict[str, str]]:
        """准备模型输入"""
        chat_history = chat_context.get('messages', [])
        
        render_kwargs = {
            'query': message.content,
            'chat_history': chat_history
        }
        
        if context.memory_context:
            render_kwargs['memory_context'] = context.memory_context
        
        if context.rag_context:
            render_kwargs['context'] = context.rag_context
        
        if context.web_search_context:
            render_kwargs['search_results'] = context.web_search_context
        
        return self.prompt_engine.build_messages(message.content, **render_kwargs)
    
    async def _store_memory(self, message: Message, result):
        """存储长期记忆"""
        try:
            await self.memory_manager.add_memory(
                content=f"用户: {message.content}\nAI: {result.content}",
                memory_type=MemoryType.EPISODIC,
                session_id=message.chat_id,
                user_id=message.user_id,
                metadata={
                    'chat_id': message.chat_id,
                    'user_id': message.user_id,
                    'timestamp': datetime.now().isoformat(),
                    'interaction_type': 'chat'
                }
            )
        except Exception as e:
            logger.warning(f"存储记忆失败: {e}")
    
    async def _sync_working_memory(self, message: Message, result):
        """同步工作区记忆 - 存储对话上下文"""
        if message.chat_id:
            await self.memory_manager.add_working_memory(
                content=message.content,
                session_id=message.chat_id,
                user_id=message.user_id,
                role='user'
            )
            
            if result.content:
                await self.memory_manager.add_working_memory(
                    content=result.content,
                    session_id=message.chat_id,
                    user_id=message.user_id,
                    role='assistant'
                )
    
    def _build_response(self, message: Message, result) -> Response:
        """构建响应"""
        return Response(
            message_id=str(uuid.uuid4()),
            channel=message.channel,
            user_id=message.user_id,
            content=result.content,
            success=result.success,
            error=result.error,
            chat_id=message.chat_id,
            metadata={
                'model_name': result.model_name,
                'response_time': datetime.now().isoformat()
            }
        )