"""Skill 管理器 - 管理所有 Skill 的注册和调用

整合 SkillRegistry 作为数据存储层，提供统一的技能管理入口。
支持渐进式披露四级模型（Level 0/1/2/3）。

核心保证：function.name = skill_name = 注册表 key
"""
from typing import Dict, List, Optional, Any

from app.core.logger import logger
from app.capabilities.skill.protocol import Skill, SkillManager
from app.capabilities.skill.skill_hotreload import get_skill_system


class SkillManagerImpl(SkillManager):
    """Skill 管理器具体实现

    渐进式披露（Progressive Disclosure）四级模型：
    - get_skill_names()          → Level 0：仅名称
    - get_skill_specs()          → Level 1：规格
    - get_skill_full_instructions() → Level 2：完整指令
    - get_skill_references()     → Level 3：参考文档
    """

    def register_skill(self, skill: Skill) -> None:
        system = get_skill_system()
        system.registry.add_skill(skill)

    def unregister_skill(self, skill_name: str) -> None:
        system = get_skill_system()
        system.registry.remove_skill(skill_name)

    def get_skill(self, skill_name: str) -> Optional[Skill]:
        system = get_skill_system()
        return system.registry.get_skill(skill_name)

    def get_all_skills(self) -> Dict[str, Skill]:
        system = get_skill_system()
        return system.registry.get_all_skills()

    def get_enabled_skills(self) -> Dict[str, Skill]:
        system = get_skill_system()
        return system.registry.get_enabled_skills()

    def get_skill_names(self) -> List[str]:
        """Level 0：获取所有启用 Skill 的名称列表"""
        return [skill.get_level0_name() for skill in self.get_enabled_skills().values()]

    def get_level0_skill_names(self, query: str, top_k: int = 5, threshold: float = 0.01) -> List[str]:
        """Level 0：使用 BM25 根据查询筛选相关的 Skill 名称列表"""
        try:
            from app.capabilities.skill.skill_selector import get_skill_selector
            selector = get_skill_selector()
            return selector.get_level0_names(query, top_k, threshold)
        except Exception as e:
            logger.error(f"[Skill] BM25 筛选失败，回退到全量技能列表: {e}", exc_info=True)
            return self.get_skill_names()[:top_k]

    def get_skill_specs(self) -> List[Dict[str, Any]]:
        """Level 1：获取所有启用 Skill 的规格（OpenAI Tools 格式）"""
        return [skill.build_tool_spec() for skill in self.get_enabled_skills().values()]

    def get_skill_full_instructions(self, skill_name: str) -> Optional[str]:
        """Level 2：获取指定 Skill 的完整指令"""
        skill = self.get_skill(skill_name)
        if skill and skill.is_enabled():
            return skill.get_level2_instructions()
        return None

    def get_skill_references(self, skill_name: str) -> Dict[str, str]:
        """Level 3：获取指定 Skill 的参考文档"""
        skill = self.get_skill(skill_name)
        if skill and skill.is_enabled():
            return skill.get_level3_references()
        return {}

    async def execute_skill(self, skill_name: str, **kwargs) -> Any:
        """执行 Skill

        skill_name 即为 function.name（= 路径叶子名 = 注册表 key），
        直接查找注册表即可命中，无需任何映射。
        """
        skill = self.get_skill(skill_name)
        if skill and skill.is_enabled():
            return await skill.execute(**kwargs)
        return None

    def get_skill_summaries(self) -> List[Dict[str, Any]]:
        """获取所有启用 Skill 的 Level 1 规格列表"""
        return [skill.get_level1_spec() for skill in self.get_enabled_skills().values()]


skill_manager = SkillManagerImpl()
