"""Skill 模块 - AI Agent 外部能力系统

整合 skill.py 的核心组件（互斥规则、路径解析、注册中心）与集成版的
渐进式披露、BM25 语义筛选、asyncio 热加载机制。

目录结构：
  data/skills/
  ├── search/
  │   ├── SKILL.md
  │   ├── scripts/        ← Python/Node.js 脚本（可选）
  │   └── references/     ← 参考文档（可选）
  └── code/
      ├── SKILL.md
      └── scripts/

支持两级目录互斥规则：
  - skills/<name>/SKILL.md          （单技能）
  - skills/<category>/<name>/SKILL.md （分类技能）

渐进式披露（Progressive Disclosure）四级模型：
  Level 0 - 名称：仅 name，最轻量
  Level 1 - 规格：name + description + parameters，用于 BM25 语义匹配
  Level 2 - 完整指令：完整的 markdown 指令内容
  Level 3 - 参考文档：references/ 目录下的文档
"""
from app.capabilities.skill.protocol import Skill, SkillManager
from app.capabilities.skill.skill_model import Skill as FileBasedSkill
from app.capabilities.skill.manager import SkillManagerImpl, skill_manager
from app.capabilities.skill.path_resolver import SkillPathResolver
from app.capabilities.skill.registry import SkillRegistry
from app.capabilities.skill.skill_hotreload import (
    SkillHotReloader, get_skill_system, start_skill_hotreload, stop_skill_hotreload,
)
from app.capabilities.skill.skill_selector import SkillSelector, get_skill_selector


def init_skills() -> bool:
    """初始化 Skill 系统：从文件系统加载所有 Skill + 构建 BM25 索引

    内部 build_index() 已处理可预期降级（bm25s 未安装、无技能）。
    此处只捕获不可预期的意外错误，记录日志但不阻断应用启动。

    Returns:
        bool: 初始化成功返回 True，失败返回 False
    """
    try:
        from app.core.logger import logger as _logger
        from app.capabilities.skill.skill_selector import get_skill_selector
        selector = get_skill_selector()
        count = selector.build_index()
        _logger.info(f"[Skill] BM25 索引初始化完成: {count} 个技能")
        return True
    except ImportError as e:
        # 模块级别的导入错误（如循环依赖）——阻断性问题，必须暴露
        from app.core.logger import logger as _logger
        _logger.error(f"[Skill] 初始化失败（导入错误）: {e}", exc_info=True)
        return False
    except Exception as e:
        # 其他不可预期的错误——记录但不阻断启动
        from app.core.logger import logger as _logger
        _logger.error(f"[Skill] 初始化失败（未知错误）: {e}", exc_info=True)
        return False
