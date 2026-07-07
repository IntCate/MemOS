"""技能注册中心 - 纯数据管理，自动维护互斥规则

核心功能：
- 线程安全的技能注册、查询、删除
- 注册表 key = skill_name（路径叶子名，全局唯一）
- 支持变更事件监听（用于热加载通知）
"""
import os
import threading
from typing import Dict, List, Optional, Callable, Any

from app.core.logger import logger
from app.capabilities.skill.skill_model import Skill
from app.capabilities.skill.path_resolver import SkillPathResolver


class SkillRegistry:
    """技能注册中心

    注册表以 skill_name 为 key，与 function.name 一致，
    确保 LLM 调用时 function.name 直接命中注册表。
    """

    def __init__(self, path_resolver: SkillPathResolver):
        self.path_resolver = path_resolver
        self.skills: Dict[str, Skill] = {}
        self._lock = threading.RLock()
        self._listeners: List[Callable] = []

    def _atomic_replace_skill(self, skill_name: str) -> Optional[Skill]:
        with self._lock:
            old_existed = skill_name in self.skills
            self.skills.pop(skill_name, None)

            skill_md_path = self.path_resolver.get_skill_md_path(skill_name)
            if not skill_md_path or not os.path.exists(skill_md_path):
                if old_existed:
                    logger.info(f"[Skill] 技能文件不存在，已移除: {skill_name}")
                    self._notify_listeners("remove", skill_name)
                return None

            skill_dir = self.path_resolver.get_skill_dir(skill_name)
            if not skill_dir:
                return None

            with open(skill_md_path, 'r', encoding='utf-8') as f:
                content = f.read()

            skill = Skill.from_markdown(content, skill_name, skill_dir)
            if not skill:
                logger.warning(f"[Skill] 技能解析失败: {skill_name}")
                return None

            self.skills[skill_name] = skill

            event_type = "reload" if old_existed else "add"
            logger.info(f"[Skill] 技能已{'更新' if old_existed else '添加'}: {skill_name}")
            self._notify_listeners(event_type, skill_name)
            return skill

    def _atomic_remove_skill(self, skill_name: str) -> bool:
        with self._lock:
            if skill_name in self.skills:
                del self.skills[skill_name]
                logger.info(f"[Skill] 移除技能: {skill_name}")
                self._notify_listeners("remove", skill_name)
                return True
            return False

    def load_all_skills(self) -> int:
        self.path_resolver.invalidate_cache()
        skill_names = self.path_resolver.list_skill_names()

        with self._lock:
            self.skills.clear()
            loaded_count = 0

            for skill_name in skill_names:
                skill = self._atomic_replace_skill(skill_name)
                if skill:
                    loaded_count += 1

            logger.info(f"[Skill] 共加载 {loaded_count} 个技能")
            self._notify_listeners("load_all", loaded_count)
            return loaded_count

    def reload_skill(self, skill_name: str) -> bool:
        """重载指定技能（热加载时调用）"""
        self.path_resolver.invalidate_cache()
        skill = self._atomic_replace_skill(skill_name)
        return skill is not None

    def add_skill(self, skill: Skill) -> None:
        with self._lock:
            self.skills[skill.name] = skill
            logger.info(f"[Skill] 手动添加技能: {skill.name}")
            self._notify_listeners("add", skill.name)

    def remove_skill(self, skill_name: str) -> bool:
        return self._atomic_remove_skill(skill_name)

    def get_skill(self, skill_name: str) -> Optional[Skill]:
        with self._lock:
            return self.skills.get(skill_name)

    def get_all_skills(self) -> Dict[str, Skill]:
        with self._lock:
            return self.skills.copy()

    def get_enabled_skills(self) -> Dict[str, Skill]:
        with self._lock:
            return {name: skill for name, skill in self.skills.items() if skill.is_enabled()}

    def get_skill_content(self, skill_name: str) -> Optional[str]:
        skill = self.get_skill(skill_name)
        return skill.get_level2_instructions() if skill else None

    def get_skill_list(self) -> List[Dict]:
        with self._lock:
            return [skill.get_summary() for skill in self.skills.values()]

    def get_skill_names(self) -> List[str]:
        with self._lock:
            return list(self.skills.keys())

    def search_skills(self, keyword: str) -> List[Skill]:
        keyword_lower = keyword.lower()
        with self._lock:
            return [
                skill for skill in self.skills.values()
                if keyword_lower in skill.name.lower()
                or keyword_lower in skill.description.lower()
            ]

    def register_listener(self, callback: Callable) -> None:
        self._listeners.append(callback)

    def unregister_listener(self, callback: Callable) -> None:
        if callback in self._listeners:
            self._listeners.remove(callback)

    def _notify_listeners(self, event_type: str, data: Any) -> None:
        for listener in self._listeners:
            try:
                listener(event_type, data)
            except Exception as e:
                logger.error(f"监听器执行失败: {e}", exc_info=True)
