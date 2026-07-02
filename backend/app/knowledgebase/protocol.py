"""Knowledge Base Protocol - 统一的知识库接口定义

本协议遵循行业标准，与 LangChain、LanceDB、Chroma、Pinecone、Weaviate 等知识库系统保持一致。
所有知识库实现必须实现以下接口，实现"可替换知识库系统"的架构目标。

核心概念：
- Collection: 集合，对应一个知识库（folder_id）
- Document: 文档，包含内容和元数据
- Embedding: 向量嵌入，用于相似度检索

协议接口：
- KnowledgeBaseStore: 存储接口 - 负责文档的增删改查
- KnowledgeBaseManager: 管理接口 - 统一入口，组合存储和嵌入

注意：Knowledge Base 与 Memory 是独立的对等服务，不应互相引用。
它们由 Runtime（协调器）统一调度。
"""
from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Any
from enum import Enum


class KBStoreType(Enum):
    LANCEDB = "lancedb"
    CHROMA = "chroma"
    PINECONE = "pinecone"
    WEAVIATE = "weaviate"


class Document:
    """统一的文档数据结构"""
    
    def __init__(
        self,
        id: str,
        content: str,
        metadata: Optional[Dict[str, Any]] = None
    ):
        self.id = id
        self.content = content
        self.metadata = metadata or {}
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'id': self.id,
            'content': self.content,
            'metadata': self.metadata
        }


class KBStats:
    """知识库统计信息"""
    
    def __init__(
        self,
        total_documents: int = 0,
        total_vectors: int = 0,
        collections: Optional[List[str]] = None,
        total_size: int = 0
    ):
        self.total_documents = total_documents
        self.total_vectors = total_vectors
        self.collections = collections or []
        self.total_size = total_size
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'total_documents': self.total_documents,
            'total_vectors': self.total_vectors,
            'collections': self.collections,
            'total_size': self.total_size
        }


class SearchResult:
    """搜索结果"""
    
    def __init__(
        self,
        document: Document,
        score: float = 0.0,
        metadata: Optional[Dict[str, Any]] = None
    ):
        self.document = document
        self.score = score
        self.metadata = metadata or {}
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'content': self.document.content,
            'metadata': {**self.document.metadata, **self.metadata},
            'score': self.score
        }


class KnowledgeBaseStore(ABC):
    """知识库存储协议 - 所有知识库存储实现必须实现此接口
    
    兼容标准：
    - LangChain VectorStore: add_documents, similarity_search, delete
    - LanceDB: add, search, delete
    - Chroma: add_documents, similarity_search, delete
    - Pinecone: upsert, query, delete
    """
    
    @abstractmethod
    async def add_documents(
        self,
        documents: List[Document],
        collection_name: str = "default",
        **kwargs
    ) -> List[str]:
        """添加文档到知识库
        
        Args:
            documents: 文档列表
            collection_name: 集合名称（对应folder_id）
        
        Returns:
            List[str]: 添加的文档ID列表
        """
        pass
    
    @abstractmethod
    async def search(
        self,
        query: str,
        collection_name: str = "default",
        limit: int = 5,
        score_threshold: float = 0.0,
        **kwargs
    ) -> List[SearchResult]:
        """相似度搜索
        
        Args:
            query: 查询文本
            collection_name: 集合名称
            limit: 返回数量限制
            score_threshold: 相似度阈值
        
        Returns:
            List[SearchResult]: 搜索结果列表
        """
        pass
    
    @abstractmethod
    async def keyword_search(
        self,
        query: str,
        collection_name: str = "default",
        limit: int = 10,
        **kwargs
    ) -> List[SearchResult]:
        """关键词搜索
        
        Args:
            query: 查询关键词
            collection_name: 集合名称
            limit: 返回数量限制
        
        Returns:
            List[SearchResult]: 搜索结果列表
        """
        pass
    
    @abstractmethod
    async def get_document(self, document_id: str, collection_name: str = "default") -> Optional[Document]:
        """根据ID获取文档
        
        Args:
            document_id: 文档ID
            collection_name: 集合名称
        
        Returns:
            Optional[Document]: 文档，不存在返回None
        """
        pass
    
    @abstractmethod
    async def delete_document(self, document_id: str, collection_name: str = "default") -> bool:
        """删除文档
        
        Args:
            document_id: 文档ID
            collection_name: 集合名称
        
        Returns:
            bool: 是否删除成功
        """
        pass
    
    @abstractmethod
    async def delete_collection(self, collection_name: str) -> bool:
        """删除集合
        
        Args:
            collection_name: 集合名称
        
        Returns:
            bool: 是否删除成功
        """
        pass
    
    @abstractmethod
    async def list_documents(
        self,
        collection_name: str = "default",
        limit: int = 100
    ) -> List[Document]:
        """列出文档
        
        Args:
            collection_name: 集合名称
            limit: 返回数量限制
        
        Returns:
            List[Document]: 文档列表
        """
        pass
    
    @abstractmethod
    async def list_collections(self) -> List[str]:
        """列出所有集合
        
        Returns:
            List[str]: 集合名称列表
        """
        pass
    
    @abstractmethod
    async def get_stats(self, collection_name: Optional[str] = None) -> KBStats:
        """获取统计信息
        
        Args:
            collection_name: 集合名称（可选，为空则获取全局统计）
        
        Returns:
            KBStats: 统计信息
        """
        pass


class KnowledgeBaseManager(ABC):
    """知识库管理器协议 - 统一入口，组合存储和嵌入
    
    这是对外暴露的唯一接口，Program层和Engineering层都通过此接口访问知识库。
    
    重要：Knowledge Base 与 Memory 是独立服务，不应互相引用。
    """
    
    @abstractmethod
    async def add_documents(
        self,
        documents: List[Document],
        collection_name: str = "default",
        **kwargs
    ) -> List[str]:
        """添加文档"""
        pass
    
    @abstractmethod
    async def search(
        self,
        query: str,
        collection_name: str = "default",
        limit: int = 5,
        score_threshold: float = 0.0,
        **kwargs
    ) -> List[SearchResult]:
        """相似度搜索"""
        pass
    
    @abstractmethod
    async def keyword_search(
        self,
        query: str,
        collection_name: str = "default",
        limit: int = 10,
        **kwargs
    ) -> List[SearchResult]:
        """关键词搜索"""
        pass
    
    @abstractmethod
    async def get_document(self, document_id: str, collection_name: str = "default") -> Optional[Document]:
        """获取文档"""
        pass
    
    @abstractmethod
    async def delete_document(self, document_id: str, collection_name: str = "default") -> bool:
        """删除文档"""
        pass
    
    @abstractmethod
    async def delete_collection(self, collection_name: str) -> bool:
        """删除集合"""
        pass
    
    @abstractmethod
    async def list_documents(
        self,
        collection_name: str = "default",
        limit: int = 100
    ) -> List[Document]:
        """列出文档"""
        pass
    
    @abstractmethod
    async def list_collections(self) -> List[str]:
        """列出集合"""
        pass
    
    @abstractmethod
    async def get_stats(self, collection_name: Optional[str] = None) -> KBStats:
        """获取统计信息"""
        pass