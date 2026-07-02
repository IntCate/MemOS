"""MemoryManager - 记忆管理器统一入口

这是对外暴露的唯一接口，Program层和Engineering层都通过此接口访问记忆。
"""
from typing import Dict, List, Optional, Any

from .protocol import (
    MemoryManager as MemoryManagerProtocol,
    MemoryStore,
    MemoryRetriever,
    MemoryEntry,
    MemoryType,
    MemoryContext,
    MemoryStats
)
from .stores.local_store import LocalMemoryStore
from .stores.vector_store import VectorMemoryStore
from .retrievers.similarity_retriever import SimilarityMemoryRetriever


class MemoryManager(MemoryManagerProtocol):
    """记忆管理器实现 - 统一入口"""
    
    def __init__(self, config: Dict[str, Any] = None):
        self.config = config or {}
        self._init_components()
    
    def _init_components(self):
        """初始化存储和检索组件"""
        store_type = self.config.get('store', 'local')
        
        if store_type == 'vector':
            self._store: MemoryStore = VectorMemoryStore(self.config.get('store_config', {}))
        else:
            self._store: MemoryStore = LocalMemoryStore(self.config.get('store_config', {}))
        
        self._retriever: MemoryRetriever = SimilarityMemoryRetriever(
            self._store,
            self.config.get('retriever_config', {})
        )
    
    async def add_memory(
        self,
        content: str,
        memory_type: MemoryType = MemoryType.WORKING,
        session_id: str = "",
        user_id: str = "",
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        return await self._store.add(content, memory_type, session_id, user_id, metadata)
    
    async def add_working_memory(
        self,
        content: str,
        session_id: str,
        user_id: str = "",
        role: str = "user",
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        combined_metadata = {
            'role': role,
            **(metadata or {})
        }
        return await self._store.add(
            content=content,
            memory_type=MemoryType.WORKING,
            session_id=session_id,
            user_id=user_id,
            metadata=combined_metadata
        )
    
    async def get_memory(self, memory_id: str) -> Optional[MemoryEntry]:
        return await self._store.get(memory_id)
    
    async def update_memory(
        self,
        memory_id: str,
        content: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> bool:
        return await self._store.update(memory_id, content, metadata)
    
    async def delete_memory(self, memory_id: str) -> bool:
        return await self._store.delete(memory_id)
    
    async def delete_session(self, session_id: str) -> bool:
        return await self._store.delete_by_session(session_id)
    
    async def search(
        self,
        query: str,
        session_id: Optional[str] = None,
        memory_type: Optional[MemoryType] = None,
        limit: int = 10,
        threshold: float = 0.5
    ) -> MemoryContext:
        return await self._retriever.search(query, session_id, memory_type, limit, threshold)
    
    async def get_context(
        self,
        session_id: str,
        limit: int = 10,
        query: str = ""
    ) -> MemoryContext:
        return await self._retriever.get_context(session_id, limit, query)
    
    async def get_chat_history(
        self,
        session_id: str,
        selected_ids: Optional[List[str]] = None
    ) -> List[MemoryEntry]:
        return await self._retriever.get_chat_history(session_id, selected_ids)
    
    async def list_memories(
        self,
        session_id: Optional[str] = None,
        memory_type: Optional[MemoryType] = None,
        limit: int = 100
    ) -> List[MemoryEntry]:
        return await self._store.list(session_id, memory_type, limit)
    
    async def get_stats(self) -> MemoryStats:
        return await self._store.get_stats()


_memory_manager_instance: Optional[MemoryManager] = None


def get_memory_manager(config: Dict[str, Any] = None) -> MemoryManager:
    """获取记忆管理器单例实例
    
    Args:
        config: 配置参数（可选，首次调用时使用）
    
    Returns:
        MemoryManager: 记忆管理器实例
    """
    global _memory_manager_instance
    if _memory_manager_instance is None:
        _memory_manager_instance = MemoryManager(config)
    return _memory_manager_instance