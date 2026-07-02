"""Context工程数据结构定义"""
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Protocol
from datetime import datetime
from enum import Enum

from app.engineering.data_structures import Message, ChannelType


class ContextSource(Enum):
    USER = "user"
    SYSTEM = "system"
    RAG = "rag"
    MEMORY = "memory"
    WEB_SEARCH = "web_search"
    TOOL = "tool"
    CHAT_HISTORY = "chat_history"


@dataclass
class Context:
    """统一的上下文对象"""
    
    message: Message
    chat_id: str
    user_id: str
    channel: ChannelType
    
    timestamp: datetime = field(default_factory=datetime.now)
    
    user_info: Dict[str, Any] = field(default_factory=dict)
    chat_state: Dict[str, Any] = field(default_factory=dict)
    environment_info: Dict[str, Any] = field(default_factory=dict)
    
    rag_context: str = ""
    memory_context: str = ""
    web_search_context: str = ""
    tool_context: str = ""
    
    chat_history: List[Dict[str, Any]] = field(default_factory=list)
    
    custom_data: Dict[str, Any] = field(default_factory=dict)
    
    @property
    def combined_context(self) -> str:
        """获取组合上下文字符串"""
        parts = []
        if self.memory_context:
            parts.append(f"记忆信息:\n{self.memory_context}")
        if self.rag_context:
            parts.append(f"参考文档:\n{self.rag_context}")
        if self.web_search_context:
            parts.append(f"搜索结果:\n{self.web_search_context}")
        if self.tool_context:
            parts.append(f"工具信息:\n{self.tool_context}")
        return "\n\n".join(parts)
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            'message_id': self.message.message_id,
            'user_id': self.user_id,
            'chat_id': self.chat_id,
            'channel': self.channel.value,
            'timestamp': self.timestamp.isoformat(),
            'user_info': self.user_info,
            'chat_state': self.chat_state,
            'environment_info': self.environment_info,
            'rag_context': self.rag_context,
            'memory_context': self.memory_context,
            'web_search_context': self.web_search_context,
            'tool_context': self.tool_context,
            'chat_history': self.chat_history,
            'custom_data': self.custom_data
        }


class ContextBuilder(Protocol):
    """上下文构建器协议"""
    
    async def build(self, message: Message, **kwargs) -> Context:
        ...
    
    def add_source(self, source: ContextSource, data: Any):
        ...


class ContextManager(Protocol):
    """上下文管理器协议"""
    
    async def get_context(self, chat_id: str, user_id: str) -> Optional[Context]:
        ...
    
    async def save_context(self, context: Context):
        ...
    
    async def update_context(self, chat_id: str, updates: Dict[str, Any]):
        ...
    
    async def clear_context(self, chat_id: str):
        ...
    
    async def prune_old_contexts(self, max_age_days: int = 30):
        ...


class ContextEnhancer(Protocol):
    """上下文增强器协议"""
    
    async def enhance(self, context: Context, **kwargs) -> Context:
        ...