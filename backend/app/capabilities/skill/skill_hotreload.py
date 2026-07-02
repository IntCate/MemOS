"""Skill 目录热加载器 — 基于 watchdog 的文件系统事件监听

替代原 SkillWatcher 的 5 秒轮询方案，实现即改即生效。

工作原理：
  1. 使用 watchdog.Observer 监听 skills/ 目录
  2. 检测到 SKILL.md 的创建/修改/删除事件时立即触发
  3. 内置防抖机制（debounce 300ms），避免编辑器保存时的连续事件
  4. 通过 asyncio 事件循环集成，与 FastAPI 应用协程兼容
"""
import asyncio
import os
from typing import Dict, Optional, Set

from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler, FileModifiedEvent, FileCreatedEvent, FileDeletedEvent

from app.core.logger import logger
from app.capabilities.skill.skill_loader import get_skill_loader


def _notify_selector_update(skill_name: str = None):
    """通知 SkillSelector 更新索引"""
    try:
        from app.capabilities.skill.skill_selector import get_skill_selector
        selector = get_skill_selector()
        if skill_name:
            selector.update_skill_embedding(skill_name)
        else:
            selector.build_index()
    except Exception:
        pass


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
        # 移动到 skills 目录内 = 新增
        if self._is_skill_md(event.dest_path):
            self.reloader._schedule_event('created', event.dest_path)
        # 从 skills 目录移出 = 删除
        if self._is_skill_md(event.src_path):
            self.reloader._schedule_event('deleted', event.src_path)

    @staticmethod
    def _is_skill_md(path: str) -> bool:
        return os.path.basename(path) == 'SKILL.md'


class SkillHotReloader:
    """基于 watchdog 的 Skill 即时热加载器

    替代 SkillWatcher 的 5 秒轮询，响应延迟 < 500ms。
    """

    def __init__(self, debounce_seconds: float = 0.3):
        self.debounce_seconds = debounce_seconds
        self._observer: Optional[Observer] = None
        self._handler: Optional[_SkillFileHandler] = None
        self._loader = get_skill_loader()
        self._pending_events: Dict[str, asyncio.Task] = {}
        self._running = False
        self._loop: Optional[asyncio.AbstractEventLoop] = None

    @property
    def is_running(self) -> bool:
        return self._running

    async def start(self):
        """启动文件系统监听

        如果已有观察者在运行则跳过（幂等）。
        """
        if self.is_running:
            logger.info("[SkillHotReload] 已在运行，跳过")
            return

        # 捕获主事件循环（watchdog 回调在后台线程中，需要跨线程调度）
        self._loop = asyncio.get_running_loop()

        skills_root = self._loader.get_skills_root()
        os.makedirs(skills_root, exist_ok=True)

        self._handler = _SkillFileHandler(self)
        self._observer = Observer()
        self._observer.schedule(self._handler, skills_root, recursive=True)
        self._observer.start()
        self._running = True

        logger.info(f"[SkillHotReload] 已启动（watchdog 文件监听，防抖 {self.debounce_seconds}s）")
        logger.info(f"[SkillHotReload] 监听目录: {skills_root}")

    async def stop(self):
        """停止文件系统监听"""
        self._running = False
        # 取消所有待处理的防抖 Future
        for future in self._pending_events.values():
            future.cancel()
        self._pending_events.clear()

        if self._observer and self._observer.is_alive():
            self._observer.stop()
            self._observer.join(timeout=2.0)
            self._observer = None
            logger.info("[SkillHotReload] 已停止")

    def _schedule_event(self, event_type: str, path: str):
        """调度文件事件（带防抖）

        同一文件在 debounce_seconds 内的多次变化合并为一次处理。
        注意：此方法在 watchdog 的后台线程中调用，必须用 run_coroutine_threadsafe 跨线程调度。
        """
        skill_dir = os.path.dirname(path)

        # 取消该 skill 的旧防抖任务（主线程操作，通过 run_coroutine_threadsafe）
        if skill_dir in self._pending_events:
            old_task = self._pending_events[skill_dir]
            if self._loop and self._loop.is_running():
                self._loop.call_soon_threadsafe(old_task.cancel)

        # 跨线程调度：在事件循环线程中创建新的防抖协程
        if self._loop and self._loop.is_running():
            future = asyncio.run_coroutine_threadsafe(
                self._handle_debounced(event_type, skill_dir),
                self._loop
            )
            self._pending_events[skill_dir] = future

    async def _handle_debounced(self, event_type: str, skill_dir: str):
        """防抖后执行实际的 Skill 增/改/删操作"""
        try:
            await asyncio.sleep(self.debounce_seconds)

            if event_type == 'deleted':
                self._handle_removed(skill_dir)
            else:
                # created 或 modified → 检查文件是否确实存在后重新加载
                skill_md = os.path.join(skill_dir, 'SKILL.md')
                if os.path.isfile(skill_md):
                    self._handle_upsert(skill_dir)
                else:
                    self._handle_removed(skill_dir)

        except asyncio.CancelledError:
            pass
        except Exception as e:
            logger.error(f"[SkillHotReload] 处理文件事件异常: {e}", exc_info=True)
        finally:
            self._pending_events.pop(skill_dir, None)

    def _handle_upsert(self, skill_dir: str):
        """新增或修改 Skill"""
        # 先移除旧版本（如果存在）
        old_name = self._find_skill_name_by_dir(skill_dir)
        if old_name:
            self._loader.remove_skill(old_name)
            logger.info(f"[SkillHotReload] 🔄 检测到 Skill 变更: {old_name}")

        # 重新加载
        skill = self._loader.add_skill(skill_dir)
        if skill:
            logger.info(
                f"[SkillHotReload] ✅ Skill 已更新: name={skill.get_name()}, "
                f"category={skill.get_category()}"
            )
            # 通知 SkillSelector 更新该技能索引
            _notify_selector_update(skill.get_name())

    def _handle_removed(self, skill_dir: str):
        """移除 Skill"""
        old_name = self._find_skill_name_by_dir(skill_dir)
        if old_name:
            self._loader.remove_skill(old_name)
            logger.info(f"[SkillHotReload] ❌ 检测到 Skill 移除: {old_name}")
            # 通知 SkillSelector 移除该技能索引
            try:
                from app.capabilities.skill.skill_selector import get_skill_selector
                get_skill_selector().remove_skill_embedding(old_name)
            except Exception:
                pass

    def _find_skill_name_by_dir(self, skill_dir: str) -> Optional[str]:
        """根据目录路径查找已注册的 Skill 名称"""
        for name, skill in self._loader.get_loaded_skills().items():
            if hasattr(skill, 'skill_dir') and skill.skill_dir == skill_dir:
                return name
        return None


# ── 全局单例 ──

_hotreloader: Optional[SkillHotReloader] = None


def get_skill_hotreloader(debounce_seconds: float = 0.3) -> SkillHotReloader:
    """获取 SkillHotReloader 单例

    Args:
        debounce_seconds: 防抖时间（秒），默认 300ms
    """
    global _hotreloader
    if _hotreloader is None:
        _hotreloader = SkillHotReloader(debounce_seconds)
    return _hotreloader


async def start_skill_hotreload(debounce_seconds: float = 0.3):
    """启动 Skill 即时热加载（便捷函数，在 app lifespan 中调用）

    替代旧的 start_skill_watcher()
    """
    reloader = get_skill_hotreloader(debounce_seconds)
    await reloader.start()


async def stop_skill_hotreload():
    """停止 Skill 即时热加载（在 app shutdown 中调用）

    替代旧的 stop_skill_watcher()
    """
    global _hotreloader
    if _hotreloader is not None:
        await _hotreloader.stop()
