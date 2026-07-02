"""向量存储实现 - 用于语义检索"""
import os
from typing import Dict, List, Optional, Any

from ..protocol import MemoryStore, MemoryEntry, MemoryType, MemoryStats
from .base import BaseMemoryStore


class VectorMemoryStore(BaseMemoryStore):
    """向量存储实现
    
    使用向量数据库进行语义检索，适用于长期记忆和语义记忆。
    """
    
    def __init__(self, config: Dict[str, Any] = None):
        super().__init__(config)
        self._vector_index: Dict[str, List[float]] = {}
        self._collection_name = self.config.get('collection_name', 'memories')
        self._init_vector_db()
    
    def _init_vector_db(self):
        """初始化向量数据库"""
        try:
            from app.engineering.vector.vector_db import VectorDB
            self._vector_db = VectorDB(self.config.get('vector', {}))
        except ImportError:
            self._vector_db = None
    
    async def add(
        self,
        content: str,
        memory_type: MemoryType = MemoryType.WORKING,
        session_id: str = "",
        user_id: str = "",
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        entry_id = await super().add(content, memory_type, session_id, user_id, metadata)
        
        if self._vector_db:
            await self._vector_db.add(
                id=entry_id,
                text=content,
                metadata={
                    'session_id': session_id,
                    'user_id': user_id,
                    'memory_type': memory_type.value,
                    **(metadata or {})
                }
            )
        
        return entry_id
    
    async def delete(self, memory_id: str) -> bool:
        if self._vector_db:
            await self._vector_db.delete(memory_id)
        
        return await super().delete(memory_id)
    
    async def delete_by_session(self, session_id: str) -> bool:
        if self._vector_db:
            await self._vector_db.delete_by_metadata({'session_id': session_id})
        
        return await super().delete_by_session(session_id)