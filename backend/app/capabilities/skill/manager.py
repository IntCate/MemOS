"""Skill 管理器 - 管理所有 Skill 的注册和调用"""
from typing import Dict, List, Optional, Any
from app.capabilities.skill.protocol import Skill, SkillManager


class SkillManagerImpl(SkillManager):
    """Skill 管理器具体实现"""
    
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
    
    async def execute_skill(self, skill_name: str, **kwargs) -> Any:
        """执行指定的 Skill"""
        skill = self.get_skill(skill_name)
        if skill and skill.is_enabled():
            return await skill.execute(**kwargs)
        return None
    
    def get_skill_specs(self) -> List[Dict[str, Any]]:
        """获取所有启用 Skill 的规格描述，用于 AI Agent 工具调用
        
        返回格式符合 OpenAI Tools 规范：
        [
            {
                "type": "function",
                "name": "skill_name",
                "description": "skill_description",
                "parameters": {
                    "type": "object",
                    "properties": {...},
                    "required": [...]
                }
            }
        ]
        """
        specs = []
        for skill in self.get_enabled_skills().values():
            params = skill.get_parameters()
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
                "name": skill.get_name(),
                "description": skill.get_description(),
                "parameters": {
                    "type": "object",
                    "properties": properties,
                    "required": required
                }
            }
            specs.append(spec)
        
        return specs


skill_manager = SkillManagerImpl()