"""搜索基础设施服务 - 封装 Memory 和 KnowledgeBase

这是基础设施服务，统一封装搜索相关的能力：
- Memory 检索：对话上下文、工作区记忆
- KnowledgeBase 检索：文档向量搜索

业务服务应通过此服务进行搜索，而不是直接使用 MemoryManager 或 KnowledgeBaseManager。
"""
from typing import List, Optional, Dict, Any

from app.memory import get_memory_manager, MemoryManager, MemoryType
from app.knowledgebase import get_knowledge_base_manager, KnowledgeBaseManager, Document as KBDocument


class SearchInfrastructure:
    """搜索基础设施服务"""
    
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        
        self.memory_manager: MemoryManager = get_memory_manager()
        self.knowledge_base_manager: KnowledgeBaseManager = get_knowledge_base_manager()
        
        self._initialized = True
    
    # === Memory Operations ===
    async def add_working_memory(self, content: str, session_id: str, user_id: str = '', 
                                  role: str = 'user', metadata: Optional[Dict[str, Any]] = None):
        """添加工作区记忆"""
        return await self.memory_manager.add_working_memory(
            content=content,
            session_id=session_id,
            user_id=user_id,
            role=role,
            metadata=metadata
        )
    
    async def get_chat_history(self, session_id: str) -> List[Any]:
        """获取对话历史"""
        return await self.memory_manager.get_chat_history(session_id)
    
    async def get_context(self, session_id: str, limit: int = 10) -> Any:
        """获取上下文"""
        return await self.memory_manager.get_context(session_id, limit)
    
    async def search_memory(self, query: str, memory_type: MemoryType = MemoryType.EPISODIC,
                            session_id: str = '', limit: int = 5, threshold: float = 0.3) -> Any:
        """搜索记忆"""
        return await self.memory_manager.search(
            query=query,
            memory_type=memory_type,
            session_id=session_id,
            limit=limit,
            threshold=threshold
        )
    
    async def delete_memory(self, memory_id: str) -> bool:
        """删除记忆"""
        return await self.memory_manager.delete_memory(memory_id)
    
    async def delete_session(self, session_id: str) -> bool:
        """删除会话"""
        return await self.memory_manager.delete_session(session_id)
    
    # === KnowledgeBase Operations ===
    async def add_documents(self, documents: List[KBDocument], collection_name: str = "default") -> List[str]:
        """添加文档到知识库"""
        return await self.knowledge_base_manager.add_documents(documents, collection_name)
    
    async def search_knowledge(self, query: str, collection_name: str = "default",
                                limit: int = 5, score_threshold: float = 0.0) -> List[Any]:
        """搜索知识库"""
        return await self.knowledge_base_manager.search(
            query=query,
            collection_name=collection_name,
            limit=limit,
            score_threshold=score_threshold
        )
    
    async def keyword_search(self, query: str, collection_name: str = "default",
                             limit: int = 10) -> List[Any]:
        """关键词搜索"""
        return await self.knowledge_base_manager.keyword_search(query, collection_name, limit)
    
    async def get_document(self, document_id: str, collection_name: str = "default") -> Optional[KBDocument]:
        """获取文档"""
        return await self.knowledge_base_manager.get_document(document_id, collection_name)
    
    async def delete_document(self, document_id: str, collection_name: str = "default") -> bool:
        """删除文档"""
        return await self.knowledge_base_manager.delete_document(document_id, collection_name)
    
    async def delete_collection(self, collection_name: str) -> bool:
        """删除集合"""
        return await self.knowledge_base_manager.delete_collection(collection_name)
    
    async def list_documents(self, collection_name: str = "default", limit: int = 100) -> List[KBDocument]:
        """列出文档"""
        return await self.knowledge_base_manager.list_documents(collection_name, limit)
    
    async def list_collections(self) -> List[str]:
        """列出集合"""
        return await self.knowledge_base_manager.list_collections()
    
    async def get_kb_stats(self, collection_name: Optional[str] = None) -> Any:
        """获取知识库统计信息"""
        return await self.knowledge_base_manager.get_stats(collection_name)