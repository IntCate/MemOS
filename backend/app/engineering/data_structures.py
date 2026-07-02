"""工程化模块数据结构定义"""
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Literal
from datetime import datetime
from enum import Enum


class ChannelType(Enum):
    WEB = "web"
    WECHAT = "wechat"
    QQ = "qq"
    FEISHU = "feishu"
    TELEGRAM = "telegram"
    DISCORD = "discord"
    API = "api"


class PromptMode(Enum):
    CHAT = "chat"
    AGENT = "agent"


class PromptType(Enum):
    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"
    TOOL = "tool"


@dataclass
class Message:
    message_id: str
    channel: ChannelType
    user_id: str
    content: str
    chat_id: str = ""
    timestamp: Optional[datetime] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Decision:
    use_streaming: bool = False
    selected_model: str = ""
    model_params: Dict[str, Any] = field(default_factory=dict)
    tool_list: List[str] = field(default_factory=list)


@dataclass
class Response:
    message_id: str
    channel: ChannelType
    user_id: str
    content: str
    success: bool
    error: str = ""
    chat_id: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class InferenceResult:
    success: bool
    content: str = ""
    error: str = ""
    model_name: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class PipelineResult:
    success: bool
    content: str = ""
    error: str = ""
    tool_results: List[Dict[str, Any]] = field(default_factory=list)
    reflection: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)