"""Skill 模块 - AI Agent 外部能力系统

所有 Skill 统一通过文件系统加载：每个 Skill 对应一个磁盘目录，
包含 SKILL.md（元数据+指令）和可选的 scripts/、references/ 子目录。
scripts/ 下的脚本可以是 Python、Node.js 等任意可执行语言。

目录结构：
  data/skills/
  ├── search/
  │   ├── SKILL.md
  │   ├── scripts/        ← Python/Node.js 脚本（可选）
  │   └── references/     ← 参考文档（可选）
  └── code/
      ├── SKILL.md
      └── scripts/
"""
from app.capabilities.skill.protocol import Skill, SkillManager
from app.capabilities.skill.manager import SkillManagerImpl, skill_manager
from app.capabilities.skill.file_skill import FileBasedSkill, parse_skill_md
from app.capabilities.skill.skill_loader import SkillLoader, get_skill_loader, load_skills_from_filesystem
from app.capabilities.skill.skill_watcher import SkillWatcher, get_skill_watcher, start_skill_watcher, stop_skill_watcher


def init_skills():
    """初始化 Skill 系统：从文件系统加载所有 Skill"""
    return load_skills_from_filesystem()
