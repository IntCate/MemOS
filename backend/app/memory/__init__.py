"""Memory Layer - 独立记忆基础设施层

这是一个独立于 Program 层和 Engineering 层的基础设施层，
供 UI 层显示和 AI 层使用，实现"可替换记忆系统"的架构目标。

核心组件：
- MemoryProtocol: 统一接口定义（兼容 MemGPT/Letta/Zep/LangMem）
- MemoryManager: 统一入口，组合存储和检索
- MemoryStore: 存储接口（本地YAML/向量存储）
- MemoryRetriever: 检索接口（相似度检索）

使用方式：
    from app.memory import get_memory_manager, MemoryType
    
    memory_manager = get_memory_manager()
    await memory_manager.add_working_memory("用户消息内容", "chat_id_001", "user_001")
    context = await memory_manager.get_context("chat_id_001")
"""
from .protocol import (
    MemoryType,
    MemoryEntry,
    MemoryContext,
    MemoryStats,
    MemoryStore,
    MemoryRetriever,
    MemoryManager as MemoryManagerProtocol
)
from .manager import MemoryManager, get_memory_manager
from .stores.local_store import LocalMemoryStore
from .stores.vector_store import VectorMemoryStore
from .retrievers.similarity_retriever import SimilarityMemoryRetriever


__all__ = [
    'MemoryType',
    'MemoryEntry',
    'MemoryContext',
    'MemoryStats',
    'MemoryStore',
    'MemoryRetriever',
    'MemoryManagerProtocol',
    'MemoryManager',
    'get_memory_manager',
    'LocalMemoryStore',
    'VectorMemoryStore',
    'SimilarityMemoryRetriever'
]