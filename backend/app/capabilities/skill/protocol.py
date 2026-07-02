"""Skill 协议 - 定义 AI Agent 可调用的外部能力接口

Skill 是 AI Agent 可以调用的外部能力模块，遵循统一协议接口。
常见的 Skill 包括：网络搜索、计算器、文件操作、代码执行等。

设计原则：
1. 每个 Skill 都是独立的模块，可按需加载
2. Skill 实现统一的协议接口，便于 AI Agent 调用
3. Skill 可以通过配置启用/禁用
4. Skill 的执行结果需要符合 AI Agent 的期望格式
"""
from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Any


class Skill(ABC):
    """Skill 抽象基类 - 定义所有 Skill 必须实现的接口"""
    
    @abstractmethod
    def get_name(self) -> str:
        """获取 Skill 名称"""
        pass
    
    @abstractmethod
    def get_description(self) -> str:
        """获取 Skill 描述"""
        pass
    
    @abstractmethod
    def get_parameters(self) -> List[Dict[str, Any]]:
        """获取 Skill 参数定义
        
        返回格式示例：
        [
            {
                "name": "query",
                "type": "string",
                "description": "搜索查询词",
                "required": true
            }
        ]
        """
        pass
    
    @abstractmethod
    async def execute(self, **kwargs) -> Any:
        """执行 Skill
        
        Args:
            **kwargs: Skill 所需的参数
            
        Returns:
            执行结果，需要符合 AI Agent 的期望格式
        """
        pass
    
    def is_enabled(self) -> bool:
        """检查 Skill 是否启用"""
        return True
    
    def get_category(self) -> str:
        """获取 Skill 分类
        
        分类示例：search, tools, code, system, etc.
        """
        return "general"


class SkillManager(ABC):
    """Skill 管理器抽象基类 - 管理所有 Skill 的注册和调用"""
    
    @abstractmethod
    def register_skill(self, skill: Skill) -> None:
        """注册一个 Skill"""
        pass
    
    @abstractmethod
    def unregister_skill(self, skill_name: str) -> None:
        """注销一个 Skill"""
        pass
    
    @abstractmethod
    def get_skill(self, skill_name: str) -> Optional[Skill]:
        """获取指定名称的 Skill"""
        pass
    
    @abstractmethod
    def get_all_skills(self) -> Dict[str, Skill]:
        """获取所有注册的 Skill"""
        pass
    
    @abstractmethod
    def get_enabled_skills(self) -> Dict[str, Skill]:
        """获取所有启用的 Skill"""
        pass
    
    @abstractmethod
    async def execute_skill(self, skill_name: str, **kwargs) -> Any:
        """执行指定的 Skill"""
        pass
    
    @abstractmethod
    def get_skill_specs(self) -> List[Dict[str, Any]]:
        """获取所有启用 Skill 的规格描述，用于 AI Agent 工具调用"""
        pass