"""Skill 管理器 - 管理所有 Skill 的注册和调用"""
from typing import Dict, List, Optional, Any
from app.capabilities.skill.protocol import Skill, SkillManager


class SkillManagerImpl(SkillManager):
    """Skill 管理器具体实现
    
    支持渐进式披露（Progressive Disclosure）：
    - get_skill_specs()          → Level 0: 摘要信息（注入每轮 Prompt）
    - get_skill_full_instructions() → Level 1: 完整指令（按需加载）
    - Skill.get_references()     → Level 2: 参考文档（深度参考时加载）
    """
    
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(SkillManagerImpl, cls).__new__(cls)
            cls._instance._skills: Dict[str, Skill] = {}
        return cls._instance
    
    def register_skill(self, skill: Skill) -> None:
        """注册一个 Skill"""
        self._skills[skill.get_name()] = skill
    
    def unregister_skill(self, skill_name: str) -> None:
        """注销一个 Skill"""
        if skill_name in self._skills:
            del self._skills[skill_name]
    
    def get_skill(self, skill_name: str) -> Optional[Skill]:
        """获取指定名称的 Skill"""
        return self._skills.get(skill_name)
    
    def get_all_skills(self) -> Dict[str, Skill]:
        """获取所有注册的 Skill"""
        return self._skills.copy()
    
    def get_enabled_skills(self) -> Dict[str, Skill]:
        """获取所有启用的 Skill"""
        return {name: skill for name, skill in self._skills.items() if skill.is_enabled()}
    
    def get_skill_full_instructions(self, skill_name: str) -> Optional[str]:
        """Level 1: 获取指定 Skill 的完整指令
        
        仅在 Agent 决定调用该 Skill 时使用，不入常驻 Prompt。
        """
        skill = self.get_skill(skill_name)
        if skill and skill.is_enabled():
            return skill.get_instructions()
        return None
    
    def get_skill_references(self, skill_name: str) -> Dict[str, str]:
        """Level 2: 获取指定 Skill 的参考文档，按需加载"""
        skill = self.get_skill(skill_name)
        if skill and skill.is_enabled():
            return skill.get_references()
        return {}
    
    async def execute_skill(self, skill_name: str, **kwargs) -> Any:
        """执行指定的 Skill"""
        skill = self.get_skill(skill_name)
        if skill and skill.is_enabled():
            return await skill.execute(**kwargs)
        return None
    
    def get_skill_specs(self) -> List[Dict[str, Any]]:
        """Level 0: 获取所有启用 Skill 的摘要规格（OpenAI Tools 格式）
        
        仅包含 name + description + parameters，不包含完整指令。
        适用于每次 Prompt 注入的轻量级工具列表。
        
        返回格式符合 OpenAI Tools 规范：
        [
            {
                "type": "function",
                "function": {
                    "name": "skill_name",
                    "description": "skill_description",
                    "parameters": {...}
                },
                "estimated_tokens": 150  // Level 1 估算 token 数
            }
        ]
        """
        specs = []
        for skill in self.get_enabled_skills().values():
            summary = skill.get_level0_summary()
            params = summary['parameters']
            properties = {}
            required = []
            
            for param in params:
                properties[param['name']] = {
                    'type': param['type'],
                    'description': param['description']
                }
                if param.get('required', False):
                    required.append(param['name'])
            
            spec = {
                "type": "function",
                "function": {
                    "name": summary['name'],
                    "description": summary['description'],
                    "parameters": {
                        "type": "object",
                        "properties": properties,
                        "required": required
                    }
                },
                "estimated_tokens": summary.get('estimated_tokens', 0),
                "category": summary.get('category', 'general'),
            }
            specs.append(spec)
        
        return specs
    
    def get_skill_summaries(self) -> List[Dict[str, Any]]:
        """Level 0: 获取所有启用 Skill 的纯摘要列表（非 OpenAI Tools 格式）
        
        用于在 System Prompt 中注入简要技能列表，让 Agent 知道有哪些能力可用。
        包含 estimated_tokens 字段，Agent 可根据此判断是否值得调用。
        """
        return [s.get_level0_summary() for s in self.get_enabled_skills().values()]


skill_manager = SkillManagerImpl()