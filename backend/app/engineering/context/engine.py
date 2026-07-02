"""Context引擎 - 上下文系统的统一入口"""
import uuid
from datetime import datetime, timedelta
from typing import Dict, Any, Optional

from app.core.logger import logger
from app.memory import MemoryManager, MemoryType, get_memory_manager
from app.knowledgebase import KnowledgeBaseManager, get_knowledge_base_manager
from .data_structures import (
    Context, ContextSource, ContextBuilder, ContextManager, ContextEnhancer
)
from app.engineering.data_structures import Message, ChannelType


class DefaultContextBuilder:
    """默认上下文构建器"""
    
    def __init__(self):
        self.sources: Dict[ContextSource, Any] = {}
    
    def add_source(self, source: ContextSource, data: Any):
        """添加上下文来源"""
        self.sources[source] = data
    
    async def build(self, message: Message, **kwargs) -> Context:
        """构建上下文"""
        context = Context(
            message=message,
            chat_id=message.chat_id or str(uuid.uuid4()),
            user_id=message.user_id or "",
            channel=message.channel or ChannelType.DIRECT
        )
        
        context.user_info = kwargs.get('user_info', {})
        context.chat_state = kwargs.get('chat_state', {})
        context.environment_info = kwargs.get('environment_info', {})
        context.chat_history = kwargs.get('chat_history', [])
        context.custom_data = kwargs.get('custom_data', {})
        
        if ContextSource.RAG in self.sources:
            context.rag_context = self._format_rag_context(self.sources[ContextSource.RAG])
        
        if ContextSource.MEMORY in self.sources:
            context.memory_context = self._format_memory_context(self.sources[ContextSource.MEMORY])
        
        if ContextSource.WEB_SEARCH in self.sources:
            context.web_search_context = self._format_web_search_context(self.sources[ContextSource.WEB_SEARCH])
        
        if ContextSource.TOOL in self.sources:
            context.tool_context = self._format_tool_context(self.sources[ContextSource.TOOL])
        
        return context
    
    def _format_rag_context(self, rag_data) -> str:
        """格式化RAG上下文"""
        if isinstance(rag_data, list):
            parts = []
            for i, doc in enumerate(rag_data):
                if isinstance(doc, dict):
                    doc_content = doc.get('content', '') or doc.get('page_content', '')
                else:
                    doc_content = getattr(doc, 'page_content', '') or getattr(doc, 'content', '')
                parts.append(f"{i+1}. {doc_content}")
            return "\n\n".join(parts)
        return str(rag_data)
    
    def _format_memory_context(self, memory_data) -> str:
        """格式化记忆上下文"""
        if isinstance(memory_data, list):
            parts = []
            for i, mem in enumerate(memory_data):
                content = mem.content if hasattr(mem, 'content') else str(mem)
                parts.append(f"{i+1}. {content}")
            return "\n\n".join(parts)
        return str(memory_data)
    
    def _format_web_search_context(self, search_data) -> str:
        """格式化搜索上下文"""
        if isinstance(search_data, dict) and 'results' in search_data:
            parts = []
            for i, result in enumerate(search_data['results']):
                if isinstance(result, dict):
                    title = result.get('title', '未命名')
                    snippet = result.get('snippet', '')
                    url = result.get('url', '')
                    parts.append(f"{i+1}. {title}\n{snippet}\n{url}")
                else:
                    parts.append(f"{i+1}. {str(result)}")
            return "\n\n".join(parts)
        return str(search_data)
    
    def _format_tool_context(self, tool_data) -> str:
        """格式化工具上下文"""
        return str(tool_data)


class InMemoryContextManager:
    """内存上下文管理器"""
    
    def __init__(self):
        self.contexts: Dict[str, Context] = {}
    
    async def get_context(self, chat_id: str, user_id: str = "") -> Optional[Context]:
        """获取上下文"""
        return self.contexts.get(chat_id)
    
    async def save_context(self, context: Context):
        """保存上下文"""
        self.contexts[context.chat_id] = context
    
    async def update_context(self, chat_id: str, updates: Dict[str, Any]):
        """更新上下文"""
        context = self.contexts.get(chat_id)
        if context:
            for key, value in updates.items():
                if hasattr(context, key):
                    setattr(context, key, value)
    
    async def clear_context(self, chat_id: str):
        """清除上下文"""
        if chat_id in self.contexts:
            del self.contexts[chat_id]
    
    async def prune_old_contexts(self, max_age_days: int = 30):
        """清理旧上下文"""
        cutoff_time = datetime.now() - timedelta(days=max_age_days)
        old_keys = [
            key for key, ctx in self.contexts.items()
            if ctx.timestamp < cutoff_time
        ]
        for key in old_keys:
            del self.contexts[key]
        return len(old_keys)


class DefaultContextEnhancer:
    """默认上下文增强器"""
    
    def __init__(self, memory_manager: MemoryManager = None, knowledge_base_manager: KnowledgeBaseManager = None, web_search_service=None):
        self.memory_manager = memory_manager or get_memory_manager()
        self.knowledge_base_manager = knowledge_base_manager or get_knowledge_base_manager()
        self.web_search_service = web_search_service
    
    async def enhance(self, context: Context, **kwargs) -> Context:
        """增强上下文"""
        user_query = context.message.content
        metadata = context.message.metadata or {}
        
        if self.memory_manager:
            try:
                memory_context = await self.memory_manager.search(
                    query=user_query,
                    memory_type=MemoryType.EPISODIC,
                    limit=5,
                    threshold=0.3
                )
                if memory_context.entries:
                    context.memory_context = self._format_memory_results(memory_context.entries)
            except Exception as e:
                logger.warning(f"上下文增强 - 记忆检索失败: {e}", exc_info=True)
        
        if self.knowledge_base_manager and metadata.get('rag_enabled', False):
            try:
                rag_config = metadata.get('rag_config', {})
                collection_name = rag_config.get('folder_id', 'default')
                search_results = await self.knowledge_base_manager.search(
                    query=user_query,
                    collection_name=collection_name,
                    limit=rag_config.get('top_k', 3),
                    score_threshold=rag_config.get('score_threshold', 0.0)
                )
                if search_results:
                    context.rag_context = self._format_rag_results(search_results)
            except Exception as e:
                logger.warning(f"上下文增强 - 知识库检索失败: {e}", exc_info=True)
        
        if self.web_search_service and metadata.get('web_search_enabled', False):
            try:
                search_result = await self.web_search_service.perform_web_search(user_query)
                if search_result:
                    context.web_search_context = self._format_web_search_results(search_result)
            except Exception as e:
                logger.warning(f"上下文增强 - 网络搜索失败: {e}", exc_info=True)
        
        return context
    
    def _format_memory_results(self, memories) -> str:
        """格式化记忆结果"""
        parts = []
        for i, mem in enumerate(memories):
            content = mem.content if hasattr(mem, 'content') else str(mem)
            parts.append(f"{i+1}. {content}")
        return "\n\n".join(parts)
    
    def _format_rag_results(self, search_results) -> str:
        """格式化知识库搜索结果"""
        parts = []
        for i, result in enumerate(search_results):
            if hasattr(result, 'document'):
                doc_content = result.document.content
            elif isinstance(result, dict):
                doc_content = result.get('content', '') or result.get('page_content', '')
            else:
                doc_content = getattr(result, 'page_content', '') or getattr(result, 'content', '')
            parts.append(f"{i+1}. {doc_content}")
        return "\n\n".join(parts)
    
    def _format_web_search_results(self, search_result) -> str:
        """格式化搜索结果"""
        if isinstance(search_result, dict) and 'results' in search_result:
            parts = []
            for i, result in enumerate(search_result['results']):
                if isinstance(result, dict):
                    title = result.get('title', '未命名')
                    snippet = result.get('snippet', '')
                    url = result.get('url', '')
                    parts.append(f"{i+1}. {title}\n{snippet}\n{url}")
            return "\n\n".join(parts)
        return str(search_result)


class ContextEngine:
    """上下文引擎 - 即插即用的上下文系统"""
    
    def __init__(self, config: Dict[str, Any] = None):
        self.config = config or {}
        
        self.builder: ContextBuilder = self._create_builder()
        self.manager: ContextManager = self._create_manager()
        self.enhancer: ContextEnhancer = self._create_enhancer()
    
    def _create_builder(self) -> ContextBuilder:
        """创建上下文构建器"""
        return DefaultContextBuilder()
    
    def _create_manager(self) -> ContextManager:
        """创建上下文管理器"""
        return InMemoryContextManager()
    
    def _create_enhancer(self) -> ContextEnhancer:
        """创建上下文增强器"""
        return DefaultContextEnhancer()
    
    async def create_context(self, message: Message, **kwargs) -> Context:
        """创建上下文"""
        return await self.builder.build(message, **kwargs)
    
    async def get_or_create_context(self, message: Message, **kwargs) -> Context:
        """获取或创建上下文"""
        context = await self.manager.get_context(message.chat_id, message.user_id)
        if context:
            context.message = message
            context.timestamp = datetime.now()
            return context
        return await self.create_context(message, **kwargs)
    
    async def enhance_context(self, context: Context, **kwargs) -> Context:
        """增强上下文"""
        return await self.enhancer.enhance(context, **kwargs)
    
    async def save_context(self, context: Context):
        """保存上下文"""
        await self.manager.save_context(context)
    
    async def update_context(self, chat_id: str, updates: Dict[str, Any]):
        """更新上下文"""
        await self.manager.update_context(chat_id, updates)
    
    async def clear_context(self, chat_id: str):
        """清除上下文"""
        await self.manager.clear_context(chat_id)
    
    async def prune_old_contexts(self, max_age_days: int = 30) -> int:
        """清理旧上下文"""
        return await self.manager.prune_old_contexts(max_age_days)
    
    def set_builder(self, builder: ContextBuilder):
        """设置上下文构建器"""
        self.builder = builder
    
    def set_manager(self, manager: ContextManager):
        """设置上下文管理器"""
        self.manager = manager
    
    def set_enhancer(self, enhancer: ContextEnhancer):
        """设置上下文增强器"""
        self.enhancer = enhancer
    
    def set_dependencies(self, memory_manager=None, knowledge_base_manager=None, web_search_service=None):
        """设置依赖服务"""
        if isinstance(self.enhancer, DefaultContextEnhancer):
            self.enhancer.memory_manager = memory_manager or get_memory_manager()
            self.enhancer.knowledge_base_manager = knowledge_base_manager or get_knowledge_base_manager()
            self.enhancer.web_search_service = web_search_service