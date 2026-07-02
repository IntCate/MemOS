"""Skill 目录热更新监听器

通过 asyncio 背景轮询实现文件系统级别的 Skill 热拔插。
无需新依赖，基于 mtime 比对检测变化。

工作原理：
  1. 启动时记录所有 SKILL.md 的 {name: (dir_path, mtime)} 快照
  2. 每隔 interval 秒重新扫描目录
  3. 对比快照 → 增量 add / remove，无需重启
"""
import asyncio
from typing import Dict, Optional

from app.core.logger import logger
from app.capabilities.skill.skill_loader import get_skill_loader


class SkillWatcher:
    """Skill 目录热更新监听器

    作为 asyncio 背景任务运行，监听 data/skills/ 目录变化。
    """

    def __init__(self, interval: float = 5.0):
        self.interval = interval
        self._task: Optional[asyncio.Task] = None
        self._snapshot: Dict[str, tuple] = {}
        self._loader = get_skill_loader()

    @property
    def is_running(self) -> bool:
        return self._task is not None and not self._task.done()

    async def start(self):
        """启动后台监听

        如果已有任务在运行则跳过（幂等）。
        """
        if self.is_running:
            logger.info("[SkillWatcher] 已在运行，跳过")
            return
        self._task = asyncio.create_task(self._watch_loop())
        logger.info(f"[SkillWatcher] 已启动（轮询间隔 {self.interval}s）")

    async def stop(self):
        """停止后台监听"""
        if self._task and not self._task.done():
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
            self._task = None
            logger.info("[SkillWatcher] 已停止")

    async def _watch_loop(self):
        """主轮询循环"""
        # 初始快照
        self._snapshot = self._loader.scan_skill_dirs()
        logger.info(
            f"[SkillWatcher] 初始快照: {len(self._snapshot)} 个 Skill "
            f"({', '.join(self._snapshot.keys()) or '无'})"
        )

        while True:
            try:
                await asyncio.sleep(self.interval)
                await self._poll()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"[SkillWatcher] 轮询异常: {e}", exc_info=True)

    async def _poll(self):
        """单次轮询：对比快照 → 增量更新"""
        current = self._loader.scan_skill_dirs()
        old_names = set(self._snapshot.keys())
        new_names = set(current.keys())

        # 新增
        added = new_names - old_names
        for name in added:
            dir_path, _ = current[name]
            skill = self._loader.add_skill(dir_path)
            if skill:
                logger.info(f"[SkillWatcher] 🔥 检测到新 Skill: {name}")

        # 修改（mtime 变化）
        modified = {
            name for name in (new_names & old_names)
            if current[name][1] != self._snapshot[name][1]
        }
        for name in modified:
            dir_path, _ = current[name]
            self._loader.remove_skill(name)
            self._loader.add_skill(dir_path)
            logger.info(f"[SkillWatcher] 🔄 检测到 Skill 变更: {name}")

        # 删除
        removed = old_names - new_names
        for name in removed:
            self._loader.remove_skill(name)
            logger.info(f"[SkillWatcher] ❌ 检测到 Skill 移除: {name}")

        # 更新快照
        if added or modified or removed:
            self._snapshot = current


# 全局单例
_watcher: Optional[SkillWatcher] = None


def get_skill_watcher(interval: float = 5.0) -> SkillWatcher:
    """获取 SkillWatcher 单例

    Args:
        interval: 轮询间隔（秒）
    """
    global _watcher
    if _watcher is None:
        _watcher = SkillWatcher(interval)
    return _watcher


async def start_skill_watcher(interval: float = 5.0):
    """启动 Skill 热更新监听（便捷函数，在 app lifespan 中调用）"""
    watcher = get_skill_watcher(interval)
    await watcher.start()


async def stop_skill_watcher():
    """停止 Skill 热更新监听（在 app shutdown 中调用）"""
    global _watcher
    if _watcher is not None:
        await _watcher.stop()
