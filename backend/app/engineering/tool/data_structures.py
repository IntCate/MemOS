"""Tool工程数据结构定义"""
from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional, Protocol, Callable
from enum import Enum
from datetime import datetime


class ToolType(Enum):
    MCP = "mcp"
    FUNCTION = "function"
    API = "api"
    WEB_SEARCH = "web_search"
    RAG = "rag"
    CUSTOM = "custom"


class ToolCategory(Enum):
    SEARCH = "search"
    DATA = "data"
    CODE = "code"
    FILE = "file"
    COMMUNICATION = "communication"
    SYSTEM = "system"
    OTHER = "other"


@dataclass
class Tool:
    """工具定义"""
    
    name: str
    description: str
    tool_type: ToolType
    category: ToolCategory
    
    parameters: Dict[str, Any] = field(default_factory=dict)
    returns: Optional[Dict[str, Any]] = None
    
    tags: List[str] = field(default_factory=list)
    enabled: bool = True
    
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    @property
    def schema(self) -> Dict[str, Any]:
        """获取工具schema"""
        return {
            "name": self.name,
            "description": self.description,
            "parameters": self.parameters,
            "returns": self.returns
        }


@dataclass
class ToolCall:
    """工具调用请求"""
    
    tool_name: str
    arguments: Dict[str, Any] = field(default_factory=dict)
    
    call_id: str = field(default_factory=lambda: str(hash(datetime.now())))
    timestamp: datetime = field(default_factory=datetime.now)
    
    context: Dict[str, Any] = field(default_factory=dict)
    
    @property
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "name": self.tool_name,
            "args": self.arguments,
            "id": self.call_id
        }


@dataclass
class ToolResult:
    """工具执行结果"""
    
    call_id: str
    success: bool
    content: str
    
    tool_name: Optional[str] = None
    error: Optional[str] = None
    
    raw_result: Any = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    timestamp: datetime = field(default_factory=datetime.now)
    
    @classmethod
    def success_result(cls, call_id: str, content: str, **kwargs) -> 'ToolResult':
        """创建成功结果"""
        return cls(call_id=call_id, success=True, content=content, **kwargs)
    
    @classmethod
    def error_result(cls, call_id: str, error: str, **kwargs) -> 'ToolResult':
        """创建错误结果"""
        return cls(call_id=call_id, success=False, content="", error=error, **kwargs)


class ToolStore(Protocol):
    """工具存储接口"""
    
    async def register_tool(self, tool: Tool):
        ...
    
    async def unregister_tool(self, tool_name: str):
        ...
    
    async def get_tool(self, tool_name: str) -> Optional[Tool]:
        ...
    
    async def list_tools(self, tool_type: Optional[ToolType] = None, 
                         category: Optional[ToolCategory] = None) -> List[Tool]:
        ...
    
    async def get_tool_count(self) -> int:
        ...
    
    async def clear(self):
        ...


class ToolExecutor(Protocol):
    """工具执行器接口"""
    
    async def execute(self, tool_call: ToolCall) -> ToolResult:
        ...
    
    def supports_tool(self, tool_name: str) -> bool:
        ...


class ToolFilter(Protocol):
    """工具过滤器接口"""
    
    async def filter(self, tools: List[Tool], context: Dict[str, Any]) -> List[Tool]:
        ...