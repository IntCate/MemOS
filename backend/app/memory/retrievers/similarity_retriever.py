"""相似度检索器实现"""
from typing import Dict, List, Optional, Any

from ..protocol import MemoryRetriever, MemoryContext, MemoryEntry, MemoryType
from .base import BaseMemoryRetriever


class SimilarityMemoryRetriever(BaseMemoryRetriever):
    """相似度检索器实现
    
    支持基于向量的语义相似度检索。
    """
    
    def __init__(self, store, config: Dict[str, Any] = None):
        super().__init__(store, config)
        self._init_embedding()
    
    def _init_embedding(self):
        """初始化嵌入模型"""
        try:
            from app.engineering.llm.instance_manager import InstanceManager
            self._embedding = InstanceManager.get('embedding')
        except ImportError:
            self._embedding = None
    
    async def search(
        self,
        query: str,
        session_id: Optional[str] = None,
        memory_type: Optional[MemoryType] = None,
        limit: int = 10,
        threshold: float = 0.5
    ) -> MemoryContext:
        if self._embedding:
            return await self._vector_search(query, session_id, memory_type, limit, threshold)
        else:
            return await super().search(query, session_id, memory_type, limit, threshold)
    
    async def _vector_search(
        self,
        query: str,
        session_id: Optional[str] = None,
        memory_type: Optional[MemoryType] = None,
        limit: int = 10,
        threshold: float = 0.5
    ) -> MemoryContext:
        """基于向量的语义搜索"""
        try:
            query_embedding = await self._embedding.embed(query)
        except Exception:
            return await super().search(query, session_id, memory_type, limit, threshold)
        
        entries = await self.store.list(
            session_id=session_id,
            memory_type=memory_type,
            limit=limit * 5
        )
        
        results = []
        for entry in entries:
            try:
                content_embedding = await self._embedding.embed(entry.content)
                similarity = self._cosine_similarity(query_embedding, content_embedding)
                entry.relevance_score = similarity
                if similarity >= threshold:
                    results.append(entry)
            except Exception:
                pass
        
        results.sort(key=lambda e: e.relevance_score, reverse=True)
        
        return MemoryContext(
            session_id=session_id or "",
            entries=results[:limit],
            query=query
        )
    
    def _cosine_similarity(self, vec1: List[float], vec2: List[float]) -> float:
        """计算余弦相似度"""
        dot_product = sum(a * b for a, b in zip(vec1, vec2))
        magnitude1 = sum(a * a for a in vec1) ** 0.5
        magnitude2 = sum(b * b for b in vec2) ** 0.5
        
        if magnitude1 == 0 or magnitude2 == 0:
            return 0.0
        
        return dot_product / (magnitude1 * magnitude2)