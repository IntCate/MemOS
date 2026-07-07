"""Skill 目录热加载器 — 基于 watchdog 的文件系统事件监听

工作原理：
  1. 使用 watchdog.Observer 监听 skills/ 目录
  2. 检测到 SKILL.md 的创建/修改/删除事件时立即触发
  3. 内置防抖机制（debounce 300ms），避免编辑器保存时的连续事件
  4. 通过 asyncio 事件循环集成，与 FastAPI 应用协程兼容
  5. 热更新时通过回调通知外部更新索引

必须通过 SkillSystem 门面类创建，不支持全局单例。
"""
import asyncio
import os
import threading
from typing import Dict, Optional, Set, Callable

from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

from app.core.logger import logger
from app.capabilities.skill.path_resolver import SkillPathResolver
from app.capabilities.skill.registry import SkillRegistry


class _SkillFileHandler(FileSystemEventHandler):
    """watchdog 事件处理器 — 仅在 SKILL.md 变化时触发"""

    def __init__(self, reloader: 'SkillHotReloader'):
        super().__init__()
        self.reloader = reloader

    def on_created(self, event):
        if self._is_skill_md(event.src_path):
            self.reloader._schedule_event('created', event.src_path)

    def on_modified(self, event):
        if self._is_skill_md(event.src_path):
            self.reloader._schedule_event('modified', event.src_path)

    def on_deleted(self, event):
        if self._is_skill_md(event.src_path):
            self.reloader._schedule_event('deleted', event.src_path)

    def on_moved(self, event):
        if self._is_skill_md(event.dest_path):
            self.reloader._schedule_event('created', event.dest_path)
        if self._is_skill_md(event.src_path):
            self.reloader._schedule_event('deleted', event.src_path)

    @staticmethod
    def _is_skill_md(path: str) -> bool:
        return os.path.basename(path) == 'SKILL.md'


class SkillHotReloader:
    """基于 watchdog 的 Skill 即时热加载器

    响应延迟 < 500ms，替代旧版 5 秒轮询。

    使用方式：必须通过 SkillSystem 门面类创建，不支持单独使用。
    
    通过回调机制通知外部更新索引：
    - on_skill_updated(skill_name): 技能更新时调用
    - on_skill_removed(skill_name): 技能移除时调用
    - on_skills_reloaded(): 全量重载时调用
    """

    def __init__(self, skills_dir: str, debounce_seconds: float = 0.3,
                 on_skill_updated: Optional[Callable[[str], None]] = None,
                 on_skill_removed: Optional[Callable[[str], None]] = None,
                 on_skills_reloaded: Optional[Callable[[], None]] = None):
        self.debounce_seconds = debounce_seconds
        self._observer: Optional[Observer] = None
        self._handler: Optional[_SkillFileHandler] = None

        self._path_resolver = SkillPathResolver(skills_dir)
        self._registry = SkillRegistry(self._path_resolver)

        os.makedirs(skills_dir, exist_ok=True)
        self._registry.load_all_skills()

        self._pending_reloads: Set[str] = set()
        self._pending_removes: Set[str] = set()
        self._pending_creates: Set[str] = set()
        self._debounce_lock = threading.Lock()
        self._debounce_timer: Optional[threading.Timer] = None

        self._running = False
        self._loop: Optional[asyncio.AbstractEventLoop] = None

        self._on_skill_updated = on_skill_updated
        self._on_skill_removed = on_skill_removed
        self._on_skills_reloaded = on_skills_reloaded

    @property
    def is_running(self) -> bool:
        return self._running

    @property
    def registry(self) -> SkillRegistry:
        return self._registry

    @property
    def path_resolver(self) -> SkillPathResolver:
        return self._path_resolver

    async def start(self):
        if self.is_running:
            logger.info("[Skill] 热加载器已在运行，跳过")
            return

        try:
            self._loop = asyncio.get_running_loop()
        except RuntimeError:
            self._loop = None
            logger.warning("[Skill] 未检测到运行中的事件循环，热加载通知将无法触发异步回调")

        self._handler = _SkillFileHandler(self)
        self._observer = Observer()
        self._observer.schedule(
            self._handler,
            path=self._path_resolver.skills_dir,
            recursive=True
        )
        self._observer.start()
        self._running = True

        logger.info(f"[Skill] 热加载器已启动（watchdog 文件监听，防抖 {self.debounce_seconds}s）")
        logger.info(f"[Skill] 监听目录: {self._path_resolver.skills_dir}")

    async def stop(self):
        self._running = False

        with self._debounce_lock:
            if self._debounce_timer:
                self._debounce_timer.cancel()
                self._debounce_timer = None
            self._pending_reloads.clear()
            self._pending_removes.clear()
            self._pending_creates.clear()

        if self._observer and self._observer.is_alive():
            self._observer.stop()
            self._observer.join(timeout=2.0)
            self._observer = None
            logger.info("[Skill] 热加载器已停止")

    def _schedule_event(self, event_type: str, path: str):
        """调度文件事件（带防抖）"""
        if self._path_resolver.is_temp_file(path):
            return

        skill_name = self._path_resolver.extract_skill_name(path)
        if not skill_name:
            logger.info("[Skill] 检测到未知路径变化，执行全量重载")
            self._schedule_full_reload()
            return

        is_md = self._path_resolver.is_skill_md(path)

        with self._debounce_lock:
            if event_type == 'deleted':
                self._pending_removes.add(skill_name)
            elif is_md:
                self._pending_reloads.add(skill_name)
            elif os.path.isdir(path):
                self._pending_creates.add(skill_name)

            self._reset_debounce_timer()

    def _schedule_full_reload(self):
        """调度全量重载"""
        with self._debounce_lock:
            self._pending_reloads.clear()
            self._pending_removes.clear()
            self._pending_creates.clear()
            self._reset_debounce_timer()

        self._registry.load_all_skills()
        if self._on_skills_reloaded:
            self._on_skills_reloaded()

    def _reset_debounce_timer(self):
        if self._debounce_timer:
            self._debounce_timer.cancel()
        self._debounce_timer = threading.Timer(
            self.debounce_seconds,
            self._flush_pending_events
        )
        self._debounce_timer.start()

    def _flush_pending_events(self):
        """防抖后执行实际的 Skill 增/改/删操作"""
        with self._debounce_lock:
            reloads = self._pending_reloads.copy()
            removes = self._pending_removes.copy()
            creates = self._pending_creates.copy()

            self._pending_reloads.clear()
            self._pending_removes.clear()
            self._pending_creates.clear()

        to_remove = removes - reloads - creates
        to_reload = reloads | creates

        removed_names = []
        for skill_name in to_remove:
            if self._registry.remove_skill(skill_name):
                removed_names.append(skill_name)

        updated_names = []
        for skill_name in to_reload:
            if self._registry.reload_skill(skill_name):
                skill = self._registry.get_skill(skill_name)
                if skill:
                    updated_names.append(skill.name)

        if removed_names and self._on_skill_removed:
            for name in removed_names:
                self._on_skill_removed(name)

        if updated_names and self._on_skill_updated:
            for name in updated_names:
                self._on_skill_updated(name)
