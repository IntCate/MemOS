"""KnowledgeBaseManager - 知识库管理器统一入口

这是对外暴露的唯一接口，Program层和Engineering层都通过此接口访问知识库。

重要：Knowledge Base 与 Memory 是独立服务，不应互相引用。
它们由 Runtime（协调器）统一调度。
"""
from typing import Dict, List, Optional, Any
from app.knowledgebase.protocol import (
    KnowledgeBaseManager as KnowledgeBaseManagerProtocol,
    KnowledgeBaseStore, Document, SearchResult, KBStats, KBStoreType
)
from app.knowledgebase.stores.lancedb_store import LanceDBStore
from app.core.logger import logger


class KnowledgeBaseManager(KnowledgeBaseManagerProtocol):
    """知识库管理器 - 统一入口"""
    
    _instance = None
    
    def __new__(cls, config: Dict[str, Any] = None):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self, config: Dict[str, Any] = None):
        if self._initialized:
            return
        
        self.config = config or {}
        self._store: KnowledgeBaseStore = self._create_store()
        self._initialized = True
    
    def _create_store(self) -> KnowledgeBaseStore:
        """创建存储实例"""
        store_type = self.config.get('store_type', 'lancedb')
        
        if store_type == 'lancedb' or store_type == KBStoreType.LANCEDB.value:
            return LanceDBStore(self.config.get('store', {}))
        
        raise ValueError(f"不支持的知识库存储类型: {store_type}")
    
    @property
    def store(self) -> KnowledgeBaseStore:
        return self._store
    
    async def add_documents(
        self,
        documents: List[Document],
        collection_name: str = "default",
        **kwargs
    ) -> List[str]:
        return await self._store.add_documents(documents, collection_name, **kwargs)
    
    async def search(
        self,
        query: str,
        collection_name: str = "default",
        limit: int = 5,
        score_threshold: float = 0.0,
        **kwargs
    ) -> List[SearchResult]:
        return await self._store.search(query, collection_name, limit, score_threshold, **kwargs)
    
    async def keyword_search(
        self,
        query: str,
        collection_name: str = "default",
        limit: int = 10,
        **kwargs
    ) -> List[SearchResult]:
        return await self._store.keyword_search(query, collection_name, limit, **kwargs)
    
    async def get_document(self, document_id: str, collection_name: str = "default") -> Optional[Document]:
        return await self._store.get_document(document_id, collection_name)
    
    async def delete_document(self, document_id: str, collection_name: str = "default") -> bool:
        return await self._store.delete_document(document_id, collection_name)
    
    async def delete_collection(self, collection_name: str) -> bool:
        return await self._store.delete_collection(collection_name)
    
    async def list_documents(
        self,
        collection_name: str = "default",
        limit: int = 100
    ) -> List[Document]:
        return await self._store.list_documents(collection_name, limit)
    
    async def list_collections(self) -> List[str]:
        return await self._store.list_collections()
    
    async def get_stats(self, collection_name: Optional[str] = None) -> KBStats:
        return await self._store.get_stats(collection_name)


def get_knowledge_base_manager(config: Dict[str, Any] = None) -> KnowledgeBaseManager:
    """获取知识库管理器实例"""
    return KnowledgeBaseManager(config)