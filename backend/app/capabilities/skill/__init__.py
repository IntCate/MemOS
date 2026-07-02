"""Skill 模块 - AI Agent 外部能力系统

Skill 是 AI Agent 可以调用的外部能力模块，遵循统一协议接口。
通过 SkillManager 管理所有 Skill 的注册和调用。

内置 Skill：
- WebSearchSkill: 网络搜索能力
"""
from app.capabilities.skill.protocol import Skill, SkillManager
from app.capabilities.skill.manager import SkillManagerImpl, skill_manager
from app.capabilities.skill.skills.web_search import WebSearchSkill


def init_skills():
    """初始化内置 Skill"""
    skill_manager.register_skill(WebSearchSkill())
