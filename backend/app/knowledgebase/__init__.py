"""Knowledge Base - 独立知识库服务

本模块是独立的能力服务，不依赖于 Program 层或 AI Engineering 层。
与 Memory 层是对等关系，由 Runtime（协调器）统一调度。

核心组件：
- Protocol: 统一协议定义（KnowledgeBaseStore, KnowledgeBaseManager）
- Stores: 存储实现（LanceDB, Chroma, Pinecone, Weaviate）
- Embeddings: 嵌入模型（HuggingFace, OpenAI, Ollama）
- Loaders: 文档加载器
- Splitters: 文本分割器

使用方式：
    from app.knowledgebase import get_knowledge_base_manager, Document, KBStats
    kb = get_knowledge_base_manager()
    await kb.add_documents([Document(id="1", content="...")])
    results = await kb.search("查询词")
"""
from .protocol import (
    KnowledgeBaseStore,
    KnowledgeBaseManager as KnowledgeBaseManagerProtocol,
    Document,
    SearchResult,
    KBStats,
    KBStoreType
)
from .manager import KnowledgeBaseManager, get_knowledge_base_manager
from .embeddings import get_embedding_model

__all__ = [
    'KnowledgeBaseStore',
    'KnowledgeBaseManagerProtocol',
    'KnowledgeBaseManager',
    'get_knowledge_base_manager',
    'Document',
    'SearchResult',
    'KBStats',
    'KBStoreType',
    'get_embedding_model'
]