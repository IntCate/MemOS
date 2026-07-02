"""Memory Protocol - 统一的记忆系统接口定义

本协议遵循行业标准，与 MemGPT / Letta / Zep / LangMem 等记忆系统保持一致。
所有记忆系统实现必须实现以下接口，实现"可替换记忆系统"的架构目标。

核心概念：
- Session: 会话，对应一个对话（chat_id）
- Message: 消息，包含角色、内容、时间戳
- MemoryEntry: 记忆条目，包含类型、内容、元数据
- Context: 上下文，检索到的记忆片段集合

协议接口：
- MemoryStore: 存储接口 - 负责记忆的增删改查
- MemoryRetriever: 检索接口 - 负责记忆的相似度检索
- MemoryManager: 管理接口 - 统一入口，组合存储和检索
"""
from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Any, AsyncGenerator
from datetime import datetime
from enum import Enum


class MemoryType(Enum):
    WORKING = "working"
    EPISODIC = "episodic"
    SEMANTIC = "semantic"
    PROCEDURAL = "procedural"
    LONG_TERM = "long_term"


class MemoryEntry:
    """统一的记忆条目数据结构"""
    
    def __init__(
        self,
        id: str,
        content: str,
        memory_type: MemoryType,
        timestamp: datetime,
        metadata: Optional[Dict[str, Any]] = None,
        relevance_score: float = 1.0
    ):
        self.id = id
        self.content = content
        self.memory_type = memory_type
        self.timestamp = timestamp
        self.metadata = metadata or {}
        self.relevance_score = relevance_score
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'id': self.id,
            'content': self.content,
            'memory_type': self.memory_type.value,
            'timestamp': self.timestamp.isoformat(),
            'metadata': self.metadata,
            'relevance_score': self.relevance_score
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'MemoryEntry':
        return cls(
            id=data['id'],
            content=data['content'],
            memory_type=MemoryType(data['memory_type']),
            timestamp=datetime.fromisoformat(data['timestamp']),
            metadata=data.get('metadata', {}),
            relevance_score=data.get('relevance_score', 1.0)
        )


class MemoryContext:
    """记忆上下文 - 检索到的记忆片段集合"""
    
    def __init__(
        self,
        session_id: str,
        entries: List[MemoryEntry],
        query: str = ""
    ):
        self.session_id = session_id
        self.entries = entries
        self.query = query
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'session_id': self.session_id,
            'query': self.query,
            'count': len(self.entries),
            'entries': [e.to_dict() for e in self.entries]
        }


class MemoryStats:
    """记忆统计信息"""
    
    def __init__(
        self,
        total_memories: int = 0,
        by_type: Optional[Dict[str, int]] = None,
        total_size: int = 0,
        total_sessions: int = 0
    ):
        self.total_memories = total_memories
        self.by_type = by_type or {}
        self.total_size = total_size
        self.total_sessions = total_sessions
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'total_memories': self.total_memories,
            'by_type': self.by_type,
            'total_size': self.total_size,
            'total_sessions': self.total_sessions
        }


class MemoryStore(ABC):
    """记忆存储协议 - 所有记忆存储实现必须实现此接口
    
    兼容标准：
    - MemGPT: add_messages, get_message_history, delete_messages
    - Letta: store, retrieve, delete
    - Zep: add, search, get
    - LangMem: add_memory, get_memory, delete_memory
    """
    
    @abstractmethod
    async def add(
        self,
        content: str,
        memory_type: MemoryType = MemoryType.WORKING,
        session_id: str = "",
        user_id: str = "",
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """添加记忆条目
        
        Args:
            content: 记忆内容
            memory_type: 记忆类型
            session_id: 会话ID（对话ID）
            user_id: 用户ID
            metadata: 附加元数据
        
        Returns:
            str: 记忆条目ID
        """
        pass
    
    @abstractmethod
    async def get(self, memory_id: str) -> Optional[MemoryEntry]:
        """根据ID获取记忆条目
        
        Args:
            memory_id: 记忆条目ID
        
        Returns:
            Optional[MemoryEntry]: 记忆条目，不存在返回None
        """
        pass
    
    @abstractmethod
    async def update(
        self,
        memory_id: str,
        content: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> bool:
        """更新记忆条目
        
        Args:
            memory_id: 记忆条目ID
            content: 新内容（可选）
            metadata: 新元数据（可选）
        
        Returns:
            bool: 是否更新成功
        """
        pass
    
    @abstractmethod
    async def delete(self, memory_id: str) -> bool:
        """删除记忆条目
        
        Args:
            memory_id: 记忆条目ID
        
        Returns:
            bool: 是否删除成功
        """
        pass
    
    @abstractmethod
    async def delete_by_session(self, session_id: str) -> bool:
        """删除指定会话的所有记忆
        
        Args:
            session_id: 会话ID
        
        Returns:
            bool: 是否删除成功
        """
        pass
    
    @abstractmethod
    async def list(
        self,
        session_id: Optional[str] = None,
        memory_type: Optional[MemoryType] = None,
        limit: int = 100
    ) -> List[MemoryEntry]:
        """列出记忆条目
        
        Args:
            session_id: 会话ID（可选，过滤指定会话）
            memory_type: 记忆类型（可选，过滤指定类型）
            limit: 返回数量限制
        
        Returns:
            List[MemoryEntry]: 记忆条目列表
        """
        pass
    
    @abstractmethod
    async def get_stats(self) -> MemoryStats:
        """获取记忆统计信息
        
        Returns:
            MemoryStats: 统计信息
        """
        pass


class MemoryRetriever(ABC):
    """记忆检索协议 - 所有记忆检索实现必须实现此接口"""
    
    @abstractmethod
    async def search(
        self,
        query: str,
        session_id: Optional[str] = None,
        memory_type: Optional[MemoryType] = None,
        limit: int = 10,
        threshold: float = 0.5
    ) -> MemoryContext:
        """相似度搜索
        
        Args:
            query: 查询文本
            session_id: 会话ID（可选，限制搜索范围）
            memory_type: 记忆类型（可选，限制搜索类型）
            limit: 返回数量限制
            threshold: 相似度阈值
        
        Returns:
            MemoryContext: 检索结果上下文
        """
        pass
    
    @abstractmethod
    async def get_context(
        self,
        session_id: str,
        limit: int = 10,
        query: str = ""
    ) -> MemoryContext:
        """获取会话上下文（工作区记忆）
        
        Args:
            session_id: 会话ID
            limit: 返回数量限制
            query: 查询文本（可选，用于相关性裁剪）
        
        Returns:
            MemoryContext: 上下文
        """
        pass
    
    @abstractmethod
    async def get_chat_history(
        self,
        session_id: str,
        selected_ids: Optional[List[str]] = None
    ) -> List[MemoryEntry]:
        """获取对话历史
        
        Args:
            session_id: 会话ID
            selected_ids: 选中的消息ID列表（可选）
        
        Returns:
            List[MemoryEntry]: 对话历史消息列表
        """
        pass


class MemoryManager(ABC):
    """记忆管理器协议 - 统一入口，组合存储和检索
    
    这是对外暴露的唯一接口，Program层和Engineering层都通过此接口访问记忆。
    """
    
    @abstractmethod
    async def add_memory(
        self,
        content: str,
        memory_type: MemoryType = MemoryType.WORKING,
        session_id: str = "",
        user_id: str = "",
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """添加记忆"""
        pass
    
    @abstractmethod
    async def add_working_memory(
        self,
        content: str,
        session_id: str,
        user_id: str = "",
        role: str = "user",
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """添加工作区记忆（对话上下文）"""
        pass
    
    @abstractmethod
    async def get_memory(self, memory_id: str) -> Optional[MemoryEntry]:
        """获取记忆条目"""
        pass
    
    @abstractmethod
    async def update_memory(
        self,
        memory_id: str,
        content: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> bool:
        """更新记忆条目"""
        pass
    
    @abstractmethod
    async def delete_memory(self, memory_id: str) -> bool:
        """删除记忆条目"""
        pass
    
    @abstractmethod
    async def delete_session(self, session_id: str) -> bool:
        """删除会话记忆"""
        pass
    
    @abstractmethod
    async def search(
        self,
        query: str,
        session_id: Optional[str] = None,
        memory_type: Optional[MemoryType] = None,
        limit: int = 10,
        threshold: float = 0.5
    ) -> MemoryContext:
        """搜索相关记忆"""
        pass
    
    @abstractmethod
    async def get_context(
        self,
        session_id: str,
        limit: int = 10,
        query: str = ""
    ) -> MemoryContext:
        """获取会话上下文"""
        pass
    
    @abstractmethod
    async def get_chat_history(
        self,
        session_id: str,
        selected_ids: Optional[List[str]] = None
    ) -> List[MemoryEntry]:
        """获取对话历史"""
        pass
    
    @abstractmethod
    async def list_memories(
        self,
        session_id: Optional[str] = None,
        memory_type: Optional[MemoryType] = None,
        limit: int = 100
    ) -> List[MemoryEntry]:
        """列出记忆"""
        pass
    
    @abstractmethod
    async def get_stats(self) -> MemoryStats:
        """获取统计信息"""
        pass