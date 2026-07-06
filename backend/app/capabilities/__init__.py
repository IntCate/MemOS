"""能力服务层 - Capabilities

本层包含 AI Agent 的外部能力服务，这些服务是可替换的：
- MCP: Model Context Protocol 客户端管理
- Skill: AI Agent 可调用的外部能力模块

所有 Skill 统一通过文件系统加载（SKILL.md + scripts/ + references/），
支持渐进式披露（Level 0/1/2）和 watchdog 即时热加载。

设计原则：
- 每个能力服务都是独立的，可单独替换
- 能力服务通过统一接口对外提供服务
- 业务服务通过能力服务访问外部能力
"""
from .mcp import MCPCapability
from .skill import (
    Skill, SkillManager, SkillManagerImpl, skill_manager,
    FileBasedSkill,
    SkillPathResolver,
    SkillRegistry,
    SkillHotReloader, get_skill_system, start_skill_hotreload, stop_skill_hotreload,
    SkillSelector, get_skill_selector,
    init_skills,
)

__all__ = [
    'MCPCapability',
    'Skill',
    'SkillManager',
    'SkillManagerImpl',
    'skill_manager',
    'FileBasedSkill',
    'SkillPathResolver',
    'SkillRegistry',
    'SkillHotReloader',
    'get_skill_system',
    'start_skill_hotreload',
    'stop_skill_hotreload',
    'SkillSelector',
    'get_skill_selector',
    'init_skills',
]