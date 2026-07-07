"""路径解析器 - 统一处理技能路径，支持两级目录互斥规则

核心功能：
- 支持两种技能目录规范：skills/<name>/SKILL.md 和 skills/<category>/<name>/SKILL.md
- 严格互斥模式：一级目录有 SKILL.md 时不再扫描其子目录
- skill_name = SKILL.md 所在目录的叶子名（路径即为唯一标识来源）
- 内置 name→path 缓存，支持仅凭 name 查找文件路径
"""
import os
from typing import List, Optional, Tuple, Dict

from app.core.logger import logger


class SkillPathResolver:
    """统一处理技能路径解析，支持两级分类（最多 category/skill），二级优先

    skill_name 规则：
      - 一级目录：skills/web_search/SKILL.md → skill_name = "web_search"
      - 二级目录：skills/tools/file_manager/SKILL.md → skill_name = "file_manager"
      - skill_name 全局唯一（二级优先规则 + 注册中心双重保障）

    二级优先规则：
      - 一级和二级都有 SKILL.md → 加载二级，写入警告
      - 一级有 SKILL.md，二级目录不存在 → 加载一级
      - 一级有 SKILL.md，二级目录存在但为空 → 加载一级，写入警告
      - 一级无 SKILL.md，二级有 SKILL.md → 加载二级
      - 一级和二级都无 SKILL.md → 无技能，写入警告
    """

    def __init__(self, skills_dir: str, skill_file_name: str = "SKILL.md"):
        self.skills_dir = os.path.abspath(skills_dir)
        self.skill_file_name = skill_file_name
        # name → 相对路径 缓存（从 skills_dir 出发）
        self._name_cache: Dict[str, str] = {}

    def _build_name_cache(self):
        """重建 name→relpath 缓存（扫描整个 skills 目录）"""
        self._name_cache.clear()
        entries = self._scan_all_entries()
        for name, rel_path in entries:
            self._name_cache[name] = rel_path

    def _scan_all_entries(self) -> List[Tuple[str, str]]:
        """扫描所有技能，返回 [(skill_name, rel_path), ...]

        二级优先规则：
          - 一级目录有 SKILL.md，二级目录也有 SKILL.md → 加载二级，写入警告
          - 一级目录有 SKILL.md，二级目录不存在 → 加载一级
          - 一级目录有 SKILL.md，二级目录存在但为空 → 加载一级，写入警告
          - 一级目录无 SKILL.md，二级目录有 SKILL.md → 加载二级
          - 一级和二级都无 SKILL.md → 无技能，写入警告
        """
        results: List[Tuple[str, str]] = []
        if not os.path.exists(self.skills_dir):
            return results

        try:
            with os.scandir(self.skills_dir) as top_entries:
                for entry in top_entries:
                    if not entry.is_dir() or entry.name.startswith('.'):
                        continue

                    has_top_md = False
                    top_md_path = os.path.join(entry.path, self.skill_file_name)
                    if os.path.isfile(top_md_path):
                        has_top_md = True

                    sub_skills = []
                    has_sub_dirs = False
                    try:
                        with os.scandir(entry.path) as sub_entries:
                            for sub in sub_entries:
                                if not sub.is_dir() or sub.name.startswith('.'):
                                    continue
                                if sub.name in ('references', 'scripts'):
                                    continue
                                has_sub_dirs = True
                                sub_md = os.path.join(sub.path, self.skill_file_name)
                                if os.path.isfile(sub_md):
                                    rel = f"{entry.name}/{sub.name}"
                                    sub_skills.append((sub.name, rel))
                                else:
                                    self._check_deep_nesting(sub.path, entry.name)
                    except PermissionError:
                        logger.warning(f"[Skill] 无权限访问子目录: {entry.path}")

                    if sub_skills:
                        results.extend(sub_skills)
                        if has_top_md:
                            logger.warning(
                                f"[Skill] 冲突检测：一级目录 {entry.name}/SKILL.md 与二级目录技能共存，"
                                f"已加载二级技能，一级技能被忽略（二级优先）"
                            )
                    else:
                        if has_top_md:
                            results.append((entry.name, entry.name))
                            if has_sub_dirs:
                                logger.warning(
                                    f"[Skill] 一级目录 {entry.name}/SKILL.md 存在，但二级目录为空，"
                                    f"建议删除空二级目录或在二级目录创建 SKILL.md"
                                )
                        else:
                            if has_sub_dirs:
                                logger.warning(
                                    f"[Skill] 目录 {entry.name}/ 下无有效技能（一级和二级都没有 SKILL.md），已忽略"
                                )
        except PermissionError:
            logger.warning(f"[Skill] 无权限访问目录: {self.skills_dir}")

        return results

    def _check_deep_nesting(self, dir_path: str, category: str):
        """检查是否存在深度 > 2 的嵌套目录（静默忽略问题）"""
        try:
            with os.scandir(dir_path) as entries:
                for entry in entries:
                    if not entry.is_dir() or entry.name.startswith('.'):
                        continue
                    md_path = os.path.join(entry.path, self.skill_file_name)
                    if os.path.isfile(md_path):
                        rel_path = os.path.relpath(entry.path, self.skills_dir)
                        logger.error(
                            f"[Skill] 深度嵌套技能被忽略: {rel_path}/SKILL.md "
                            f"(系统仅支持最多两级目录: skills/<category>/<name>/SKILL.md)"
                        )
                    else:
                        self._check_deep_nesting(entry.path, category)
        except PermissionError:
            pass

    # ── name → path 查询 ──────────────────────────────

    def get_skill_md_path(self, skill_name: str) -> Optional[str]:
        """根据 skill_name 查找 SKILL.md 的绝对路径"""
        if not self._name_cache:
            self._build_name_cache()
        rel = self._name_cache.get(skill_name)
        if rel:
            return os.path.join(self.skills_dir, rel, self.skill_file_name)
        return None

    def get_skill_dir(self, skill_name: str) -> Optional[str]:
        """根据 skill_name 查找技能目录的绝对路径"""
        if not self._name_cache:
            self._build_name_cache()
        rel = self._name_cache.get(skill_name)
        if rel:
            return os.path.join(self.skills_dir, rel)
        return None

    # ── 路径 → name ──────────────────────────────────

    def extract_skill_name(self, path: str) -> Optional[str]:
        """从文件路径提取 skill_name（= SKILL.md 所在目录叶子名）

        只返回叶子目录名，不包含 category 前缀。
        例如：
          /skills/tools/file_manager/SKILL.md → "file_manager"
          /skills/web_search/SKILL.md → "web_search"
        """
        abs_path = os.path.abspath(path)
        if not abs_path.startswith(self.skills_dir + os.sep):
            return None

        # 找到 SKILL.md 所在的目录
        if abs_path.endswith(os.sep + self.skill_file_name):
            skill_dir = os.path.dirname(abs_path)
        elif os.path.isdir(abs_path) and os.path.isfile(
            os.path.join(abs_path, self.skill_file_name)
        ):
            skill_dir = abs_path
        else:
            return None

        rel = os.path.relpath(skill_dir, self.skills_dir)
        if rel == '.':
            return None

        # 只取叶子名
        return os.path.basename(rel)

    # ── 兼容旧接口 ────────────────────────────────────

    def extract_skill_id(self, path: str) -> Optional[str]:
        """兼容旧接口：返回 skill_name"""
        return self.extract_skill_name(path)

    def extract_category_and_skill(self, path: str) -> Optional[Tuple[Optional[str], str]]:
        """提取 (category, skill_name)"""
        abs_path = os.path.abspath(path)
        if not abs_path.startswith(self.skills_dir + os.sep):
            return None

        if abs_path.endswith(os.sep + self.skill_file_name):
            skill_dir = os.path.dirname(abs_path)
        elif os.path.isdir(abs_path) and os.path.isfile(
            os.path.join(abs_path, self.skill_file_name)
        ):
            skill_dir = abs_path
        else:
            return None

        rel = os.path.relpath(skill_dir, self.skills_dir)
        if rel == '.':
            return None

        parts = rel.split(os.sep)
        if len(parts) == 1:
            return (None, parts[0])
        elif len(parts) == 2:
            return (parts[0], parts[1])
        else:
            logger.error(
                f"[Skill] 深度嵌套技能被忽略: {rel}/SKILL.md "
                f"(系统仅支持最多两级目录: skills/<category>/<name>/SKILL.md)"
            )
            return None

    # ── 工具方法 ──────────────────────────────────────

    def is_skill_md(self, path: str) -> bool:
        return path.endswith(self.skill_file_name)

    def is_temp_file(self, path: str) -> bool:
        temp_extensions = ('.swp', '.swx', '~', '.tmp', '.pyc')
        return any(path.endswith(ext) for ext in temp_extensions)

    def skill_exists(self, skill_name: str) -> bool:
        p = self.get_skill_md_path(skill_name)
        return p is not None and os.path.exists(p)

    def list_skill_names(self) -> List[str]:
        """返回所有 skill_name（叶子名）"""
        if not self._name_cache:
            self._build_name_cache()
        return list(self._name_cache.keys())

    def list_skill_dirs(self) -> List[str]:
        """兼容旧接口：返回 skill_name 列表"""
        return self.list_skill_names()

    def invalidate_cache(self):
        """使缓存失效（目录结构变化时调用）"""
        self._name_cache.clear()