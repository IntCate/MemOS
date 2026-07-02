"""检索器基类"""
from typing import Dict, List, Optional, Any

from ..protocol import MemoryRetriever, MemoryContext, MemoryEntry, MemoryType


class BaseMemoryRetriever(MemoryRetriever):
    """检索器基类"""
    
    def __init__(self, store, config: Dict[str, Any] = None):
        self.store = store
        self.config = config or {}
    
    async def search(
        self,
        query: str,
        session_id: Optional[str] = None,
        memory_type: Optional[MemoryType] = None,
        limit: int = 10,
        threshold: float = 0.5
    ) -> MemoryContext:
        entries = await self.store.list(
            session_id=session_id,
            memory_type=memory_type,
            limit=limit * 2
        )
        
        results = []
        for entry in entries:
            if self._calculate_relevance(entry, query) >= threshold:
                results.append(entry)
        
        results.sort(key=lambda e: e.relevance_score, reverse=True)
        
        return MemoryContext(
            session_id=session_id or "",
            entries=results[:limit],
            query=query
        )
    
    def _calculate_relevance(self, entry: MemoryEntry, query: str) -> float:
        """计算相关性分数（简单实现）"""
        query_lower = query.lower()
        content_lower = entry.content.lower()
        
        if query_lower in content_lower:
            return 0.9
        elif any(word in content_lower for word in query_lower.split()):
            return 0.7
        else:
            return 0.3
    
    async def get_context(
        self,
        session_id: str,
        limit: int = 10,
        query: str = ""
    ) -> MemoryContext:
        entries = await self.store.list(
            session_id=session_id,
            memory_type=MemoryType.WORKING,
            limit=limit
        )
        return MemoryContext(session_id=session_id, entries=entries, query=query)
    
    async def get_chat_history(
        self,
        session_id: str,
        selected_ids: Optional[List[str]] = None
    ) -> List[MemoryEntry]:
        entries = await self.store.list(
            session_id=session_id,
            memory_type=MemoryType.WORKING,
            limit=100
        )
        
        if selected_ids:
            selected_set = set(selected_ids)
            entries = [e for e in entries if e.id in selected_set]
        
        return entries