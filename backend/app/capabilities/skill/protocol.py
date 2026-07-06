"""Skill 协议 - 定义 AI Agent 可调用的外部能力接口

Skill 是 AI Agent 可以调用的外部能力模块，遵循统一协议接口。
常见的 Skill 包括：网络搜索、计算器、文件操作、代码执行等。

设计原则：
1. 每个 Skill 都是独立的模块，可按需加载
2. Skill 实现统一的协议接口，便于 AI Agent 调用
3. Skill 可以通过配置启用/禁用
4. Skill 的执行结果需要符合 AI Agent 的期望格式

渐进式披露（Progressive Disclosure）四级模型：
  Level 0 - 名称：仅 name，最轻量，用于技能列表展示和选择
  Level 1 - 规格：name + description + parameters，用于 BM25 语义匹配
  Level 2 - 完整指令：get_instructions()，仅在 Agent 决定调用该 Skill 时加载
  Level 3 - 参考文档：get_references()，仅在需要深入理解 Skill 时按需加载
"""
from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Any


class Skill(ABC):
    """Skill 抽象基类 - 定义所有 Skill 必须实现的接口"""
    
    # ── Level 0: 名称（最轻量，用于技能列表）──
    
    @abstractmethod
    def get_name(self) -> str:
        """获取 Skill 名称"""
        pass
    
    def get_level0_name(self) -> str:
        """Level 0: 返回 Skill 名称（最轻量）
        
        Returns:
            str: 技能名称
        """
        return self.get_name()
    
    # ── Level 1: 规格（用于语义匹配和工具定义）──
    
    @abstractmethod
    def get_description(self) -> str:
        """获取 Skill 描述（Level 1 规格的一部分）"""
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
    
    def get_level1_spec(self) -> Dict[str, Any]:
        """Level 1: 返回 Skill 规格信息（name + description + parameters）
        
        用于 BM25 语义匹配和 OpenAI Tools 格式工具定义。

        Returns:
            {
                "name": str,
                "description": str,
                "category": str,
                "parameters": List[Dict],
            }
        """
        return {
            'name': self.get_name(),
            'description': self.get_description(),
            'category': self.get_category(),
            'parameters': self.get_parameters(),
        }
    
    # ── Level 2: 完整指令（Agent 决定调用后加载）──
    
    def get_level2_instructions(self) -> str:
        """Level 2: 返回 Skill 的完整指令内容
        
        仅在 Agent 决定调用该 Skill 时加载，不入常驻 Prompt。
        """
        return ''
    
    def get_usage_examples(self) -> List[str]:
        """返回使用示例列表"""
        return []
    
    # ── Level 3: 参考文档（深度参考时按需加载）──
    
    def get_level3_references(self) -> Dict[str, str]:
        """Level 3: 返回参考文档 {文件名: 内容}，按需加载"""
        return {}
    
    # ── 执行与状态 ──
    
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
    def unregister_skill(self, skill_id: str) -> None:
        """注销一个 Skill"""
        pass
    
    @abstractmethod
    def get_skill(self, skill_id: str) -> Optional[Skill]:
        """获取指定 skill_id 的 Skill"""
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
    async def execute_skill(self, skill_id: str, **kwargs) -> Any:
        """执行指定的 Skill"""
        pass
    
    # ── 渐进式披露方法（四级模型）──
    
    def get_skill_names(self) -> List[str]:
        """Level 0: 获取所有启用 Skill 的名称列表（最轻量）
        
        Returns:
            List[str]: 技能名称列表
        """
        return [skill.get_level0_name() for skill in self.get_enabled_skills().values()]
    
    @abstractmethod
    def get_skill_specs(self) -> List[Dict[str, Any]]:
        """Level 1: 获取所有启用 Skill 的规格（name + description + parameters）

        适用于 BM25 语义匹配和 OpenAI Tools 格式工具定义。
        """
        pass
    
    @abstractmethod
    def get_skill_full_instructions(self, skill_id: str) -> Optional[str]:
        """Level 2: 获取指定 Skill 的完整指令

        仅在 Agent 决定调用该 Skill 时使用。
        """
        pass
    
    @abstractmethod
    def get_skill_references(self, skill_id: str) -> Dict[str, str]:
        """Level 3: 获取指定 Skill 的参考文档

        仅在需要深入理解 Skill 时按需加载。
        """
        pass