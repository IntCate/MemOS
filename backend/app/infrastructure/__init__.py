"""基础设施服务层 - Infrastructure Services

本层包含 AI Agent 相关的基础设施服务：
- Memory: 记忆工程服务（YAML/JSON 文件存储）
- KnowledgeBase: 知识库服务（LanceDB 向量存储）

基础设施服务（Infrastructure Service） vs 业务服务（Business Service）：
- Infrastructure Service: AI Agent 能力服务，可替换实现
  - MemoryManager、KnowledgeBaseManager
- Business Service: 包含业务规则和业务流程
  - ChatService、MessageService、DocumentService 等

依赖关系：
- Business Service → Infrastructure Service（通过接口）
- 基础设施服务内部相互独立，由 Runtime 统一调度
"""
from .data import DataInfrastructure
from .search import SearchInfrastructure

__all__ = [
    'DataInfrastructure',
    'SearchInfrastructure'
]