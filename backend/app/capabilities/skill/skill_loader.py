"""Skill 文件系统加载器

扫描 skills/ 目录结构，自动发现并注册 FileBasedSkill。

目录结构：
  skills/                          ← skills_root
  ├── search/                      ← 分类目录（单技能/多技能类别名）
  │   ├── SKILL.md                 ← 技能指令文件
  │   ├── scripts/                 ← 可选：脚本
  │   └── references/              ← 可选：参考文档
  │       └── api_docs.md
  ├── code/
  │   ├── SKILL.md
  │   └── scripts/
  │       └── run_python.sh
  └── tools/                       ← 多技能类别目录
      ├── calculator/
      │   └── SKILL.md
      └── file_manager/
          └── SKILL.md
"""
import os
import yaml
from typing import Dict, List, Optional

from app.capabilities.skill.protocol import Skill
from app.capabilities.skill.manager import skill_manager
from app.capabilities.skill.file_skill import FileBasedSkill, parse_skill_md
from app.core.logger import logger


class SkillLoader:
    """Skill 文件系统加载器

    扫描指定根目录，发现所有包含 SKILL.md 的子目录，
    将每个子目录解析为一个 FileBasedSkill 并注册到 SkillManager。
    """

    def __init__(self, skills_root: str):
        self.skills_root = skills_root
        self._loaded: Dict[str, FileBasedSkill] = {}

    def get_skills_root(self) -> str:
        return self.skills_root

    def load_all(self) -> int:
        """扫描并加载所有 Skill

        Returns:
            成功加载的 Skill 数量
        """
        self._ensure_root()
        count = 0

        for entry in sorted(os.listdir(self.skills_root)):
            entry_path = os.path.join(self.skills_root, entry)
            if not os.path.isdir(entry_path):
                continue

            # 检查直接包含 SKILL.md（单技能类别目录）
            skill_md_path = os.path.join(entry_path, 'SKILL.md')
            if os.path.isfile(skill_md_path):
                skill = self._load_single(entry_path, skill_md_path)
                if skill:
                    self._register(skill)
                    count += 1
                continue

            # 多技能类别目录：扫描子目录
            for sub_entry in sorted(os.listdir(entry_path)):
                sub_path = os.path.join(entry_path, sub_entry)
                if not os.path.isdir(sub_path):
                    continue
                skill_md_path = os.path.join(sub_path, 'SKILL.md')
                if os.path.isfile(skill_md_path):
                    skill = self._load_single(sub_path, skill_md_path)
                    if skill:
                        self._register(skill)
                        count += 1

        logger.info(f"[SkillLoader] 加载完成: 共发现 {count} 个 Skill")
        return count

    def add_skill(self, skill_dir: str) -> Optional[FileBasedSkill]:
        """增量添加单个 Skill

        Args:
            skill_dir: Skill 目录路径

        Returns:
            成功返回 FileBasedSkill，失败返回 None
        """
        skill_md_path = os.path.join(skill_dir, 'SKILL.md')
        if not os.path.isfile(skill_md_path):
            logger.warning(f"[SkillLoader] 目录中无 SKILL.md: {skill_dir}")
            return None

        skill = self._load_single(skill_dir, skill_md_path)
        if skill:
            self._register(skill)
            logger.info(f"[SkillLoader] 热添加 Skill: {skill.get_name()}")
        return skill

    def remove_skill(self, name: str):
        """增量移除单个 Skill

        Args:
            name: Skill 名称
        """
        if name in self._loaded:
            skill_manager.unregister_skill(name)
            del self._loaded[name]
            logger.info(f"[SkillLoader] 热移除 Skill: {name}")

    def reload(self) -> int:
        """重新加载所有 Skill（先卸载再加载）

        Returns:
            成功加载的 Skill 数量
        """
        self.unload_all()
        return self.load_all()

    def unload_all(self):
        """卸载所有已加载的 Skill"""
        for name in list(self._loaded.keys()):
            skill_manager.unregister_skill(name)
        self._loaded.clear()
        logger.info("[SkillLoader] 已卸载所有 Skill")

    def get_loaded_skills(self) -> Dict[str, FileBasedSkill]:
        """获取所有已加载的 Skill"""
        return self._loaded.copy()

    def scan_skill_dirs(self) -> Dict[str, tuple]:
        """扫描 skills_root 下所有 SKILL.md，返回 {name: (dir_path, mtime)}

        用于与上次快照对比，检测新增/修改/删除。
        """
        self._ensure_root()
        current: Dict[str, tuple] = {}
        for entry in sorted(os.listdir(self.skills_root)):
            entry_path = os.path.join(self.skills_root, entry)
            if not os.path.isdir(entry_path):
                continue
            skill_md = os.path.join(entry_path, 'SKILL.md')
            if os.path.isfile(skill_md):
                name = self._read_skill_name(skill_md)
                if name:
                    current[name] = (entry_path, os.path.getmtime(skill_md))
                continue
            for sub in sorted(os.listdir(entry_path)):
                sub_path = os.path.join(entry_path, sub)
                if not os.path.isdir(sub_path):
                    continue
                skill_md = os.path.join(sub_path, 'SKILL.md')
                if os.path.isfile(skill_md):
                    name = self._read_skill_name(skill_md)
                    if name:
                        current[name] = (sub_path, os.path.getmtime(skill_md))
        return current

    def _read_skill_name(self, skill_md_path: str) -> str:
        """快速读取 SKILL.md 中的 name 字段（不完整解析）"""
        try:
            with open(skill_md_path, 'r', encoding='utf-8') as f:
                content = f.read()
            if content.startswith('---'):
                parts = content.split('---', 2)
                if len(parts) >= 3:
                    frontmatter = yaml.safe_load(parts[1]) or {}
                    return frontmatter.get('name', '')
        except Exception:
            pass
        return ''

    def _load_single(self, skill_dir: str, skill_md_path: str) -> Optional[FileBasedSkill]:
        """加载单个 Skill 目录"""
        config = parse_skill_md(skill_md_path)
        if not config or not config.get('name'):
            logger.warning(f"[SkillLoader] 跳过无效 SKILL.md: {skill_md_path}")
            return None

        skill = FileBasedSkill(skill_dir, config)
        logger.info(
            f"[SkillLoader] 发现 Skill: name={skill.get_name()}, "
            f"category={skill.get_category()}, dir={os.path.basename(skill_dir)}"
        )
        return skill

    def _register(self, skill: FileBasedSkill):
        """注册 Skill 到全局管理器"""
        skill_manager.register_skill(skill)
        self._loaded[skill.get_name()] = skill

    def _ensure_root(self):
        """确保 skills 根目录存在"""
        os.makedirs(self.skills_root, exist_ok=True)


# 全局 SkillLoader 实例（延迟初始化）
_skill_loader: Optional[SkillLoader] = None


def get_skill_loader(skills_root: str = None) -> SkillLoader:
    """获取 SkillLoader 单例

    Args:
        skills_root: skills 根目录路径（首次调用时指定）
    """
    global _skill_loader
    if _skill_loader is None:
        if skills_root is None:
            from app.utils.path_manager import PathManager
            skills_root = os.path.join(PathManager.get_user_data_dir(), 'skills')
        _skill_loader = SkillLoader(skills_root)
    return _skill_loader


def load_skills_from_filesystem(skills_root: str = None) -> int:
    """便捷函数：从文件系统加载所有 Skill

    Args:
        skills_root: skills 根目录路径

    Returns:
        成功加载的 Skill 数量
    """
    loader = get_skill_loader(skills_root)
    return loader.load_all()
