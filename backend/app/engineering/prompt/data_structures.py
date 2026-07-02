"""Prompt工程数据结构定义"""
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any
from datetime import datetime
from enum import Enum


class PromptType(Enum):
    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"
    TOOL = "tool"


class PromptMode(Enum):
    CHAT = "chat"
    RAG = "rag"
    AGENT = "agent"
    MIXED = "mixed"
    WEB_SEARCH = "web_search"


@dataclass
class PromptVariable:
    name: str
    description: str
    required: bool = False
    default: Optional[Any] = None
    type: str = "string"


@dataclass
class PromptTemplate:
    id: str
    name: str
    type: PromptType
    mode: PromptMode
    content: str
    variables: List[PromptVariable] = field(default_factory=list)
    description: str = ""
    version: str = "1.0.0"
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    tags: List[str] = field(default_factory=list)
    is_active: bool = True


@dataclass
class PromptVersion:
    template_id: str
    version: str
    content: str
    variables: List[PromptVariable] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.now)
    created_by: str = "system"
    notes: str = ""


@dataclass
class PromptRenderResult:
    success: bool
    content: str = ""
    template_id: str = ""
    version: str = ""
    used_variables: List[str] = field(default_factory=list)
    missing_variables: List[str] = field(default_factory=list)
    error: str = ""


@dataclass
class PromptEvaluation:
    template_id: str
    version: str
    score: float
    criteria: Dict[str, float] = field(default_factory=dict)
    feedback: str = ""
    evaluated_at: datetime = field(default_factory=datetime.now)


@dataclass
class ABTestConfig:
    template_id: str
    variants: List[str]
    weights: List[float]
    enabled: bool = True
    goal_metric: str = "quality"
    sample_size: int = 100