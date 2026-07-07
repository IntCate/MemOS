"""Skill 模块 - AI Agent 外部能力系统

整合 skill.py 的核心组件（二级优先规则、路径解析、注册中心）与集成版的
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

支持两级目录二级优先规则：
  - skills/<name>/SKILL.md          （单技能）
  - skills/<category>/<name>/SKILL.md （分类技能）
  - 二级优先：当一级和二级都有 SKILL.md 时，加载二级并写入警告

渐进式披露（Progressive Disclosure）四级模型：
  Level 0 - 名称：仅 name，最轻量
  Level 1 - 规格：name + description + parameters，用于 BM25 语义匹配
  Level 2 - 完整指令：完整的 markdown 指令内容
  Level 3 - 参考文档：references/ 目录下的文档

使用方式（可插拔集成）：
  from app.capabilities.skill import SkillSystem
  
  skill_system = SkillSystem(skills_dir='data/skills')
  await skill_system.start()
  
  # 获取技能上下文（用于 Prompt 注入）
  context = skill_system.get_skills_context('搜索网络信息')
  
  # 获取工具规格（OpenAI Tools 格式）
  tools = skill_system.get_tool_specs()
  
  # 执行技能
  result = await skill_system.execute('search', query='人工智能')
  
  await skill_system.stop()

注意：本模块已移除所有全局单例，必须通过 SkillSystem 门面类使用。
"""
from typing import Dict, List, Optional, Any, Tuple

from app.capabilities.skill.protocol import Skill, SkillManager
from app.capabilities.skill.skill_model import Skill as FileBasedSkill
from app.capabilities.skill.manager import SkillManagerImpl
from app.capabilities.skill.path_resolver import SkillPathResolver
from app.capabilities.skill.registry import SkillRegistry
from app.capabilities.skill.skill_hotreload import SkillHotReloader
from app.capabilities.skill.skill_selector import SkillSelector


class SkillContext:
    """技能上下文结果
    
    用于将技能信息注入到 Agent 的 Prompt 中。
    """
    def __init__(self, names: List[str], descriptions: List[Dict[str, Any]], 
                 tool_specs: List[Dict[str, Any]], context_text: str):
        self.names = names
        self.descriptions = descriptions
        self.tool_specs = tool_specs
        self.context_text = context_text


class SkillExecutionResult:
    """技能执行结果"""
    def __init__(self, success: bool, skill_name: str, data: Any = None, 
                 error: str = None):
        self.success = success
        self.skill_name = skill_name
        self.data = data
        self.error = error


class SkillSystem:
    """Skill 系统统一门面
    
    提供单一入口点，封装内部组件的复杂性，支持依赖注入。
    
    设计目标：
    - 单一入口：所有操作通过一个类完成
    - 黑盒集成：使用者无需了解内部结构
    - 依赖注入：支持测试时替换实现
    - 清晰契约：输入输出类型明确
    
    使用示例：
        # 基本用法
        skill_system = SkillSystem(skills_dir='data/skills')
        await skill_system.start()
        
        # 获取技能上下文
        context = skill_system.get_skills_context('搜索网络信息')
        
        # 执行技能
        result = await skill_system.execute('search', query='xxx')
        
        await skill_system.stop()
    
    测试时替换：
        skill_system = SkillSystem(
            system=MockSkillHotReloader(),
            selector=MockSkillSelector(),
            manager=MockSkillManager()
        )
    """
    
    def __init__(self, skills_dir: str = None, 
                 system: SkillHotReloader = None,
                 selector: SkillSelector = None,
                 manager: SkillManagerImpl = None):
        """
        Args:
            skills_dir: 技能目录路径（默认使用用户数据目录）
            system: SkillHotReloader 实例（可选，用于测试）
            selector: SkillSelector 实例（可选，用于测试）
            manager: SkillManagerImpl 实例（可选，用于测试）
        """
        self._skills_dir = skills_dir
        
        if manager is not None:
            self._manager = manager
            if system is None:
                raise ValueError("如果提供了 manager，必须同时提供 system")
            self._system = system
        else:
            if system is not None:
                self._system = system
                self._manager = SkillManagerImpl(system=self._system)
            else:
                if skills_dir is None:
                    import os
                    from app.utils.path_manager import PathManager
                    skills_dir = os.path.join(PathManager.get_user_data_dir(), 'skills')
                
                self._system = SkillHotReloader(
                    skills_dir=skills_dir,
                    on_skill_updated=self._on_skill_updated,
                    on_skill_removed=self._on_skill_removed,
                    on_skills_reloaded=self._on_skills_reloaded
                )
                self._manager = SkillManagerImpl(system=self._system)
        
        if selector is not None:
            self._selector = selector
        else:
            self._selector = SkillSelector(manager=self._manager)
        
        self._started = False
    
    def _on_skill_updated(self, skill_name: str):
        """技能更新回调：同步更新 BM25 索引"""
        if self._started:
            self._selector.update_skill_index(skill_name)
    
    def _on_skill_removed(self, skill_name: str):
        """技能移除回调：从 BM25 索引中移除"""
        if self._started:
            self._selector.remove_skill_index(skill_name)
    
    def _on_skills_reloaded(self):
        """全量重载回调：重建 BM25 索引"""
        if self._started:
            self._selector.build_index()
    
    @property
    def system(self) -> SkillHotReloader:
        """获取 SkillHotReloader 实例"""
        return self._system
    
    @property
    def manager(self) -> SkillManagerImpl:
        """获取 SkillManagerImpl 实例"""
        return self._manager
    
    @property
    def selector(self) -> SkillSelector:
        """获取 SkillSelector 实例"""
        return self._selector
    
    async def start(self):
        """启动技能系统
        
        - 启动热加载监听
        - 构建 BM25 索引
        """
        if self._started:
            return
        
        await self._system.start()
        self._selector.build_index()
        self._started = True
    
    async def stop(self):
        """停止技能系统"""
        if not self._started:
            return
        
        await self._system.stop()
        self._started = False
    
    def get_skills_context(self, query: str, top_k: int = 5, 
                          threshold: float = 0.01) -> SkillContext:
        """获取技能上下文（用于 Prompt 注入）
        
        Args:
            query: 用户查询文本
            top_k: 最多返回的技能数量
            threshold: BM25 分数阈值
        
        Returns:
            SkillContext: 包含技能名称、描述、工具规格和上下文文本
        """
        names = self._selector.get_level0_names(query, top_k, threshold)
        descriptions = self._selector.get_selected_skills_context(query, top_k, threshold)
        tool_specs = self._selector.get_level1_specs(query, top_k, threshold)
        
        lines = ['【可用技能】以下技能可能对当前任务有帮助：']
        for i, desc in enumerate(descriptions, 1):
            lines.append(
                f"{i}. **{desc['name']}** [{desc.get('category', 'general')}] "
                f"— {desc['description']}"
            )
        context_text = '\n'.join(lines)
        
        return SkillContext(
            names=names,
            descriptions=descriptions,
            tool_specs=tool_specs,
            context_text=context_text
        )
    
    def get_tool_specs(self, query: str = None, top_k: int = None, 
                       threshold: float = None) -> List[Dict[str, Any]]:
        """获取工具规格（OpenAI Tools 格式）
        
        Args:
            query: 用户查询文本（可选，不提供则返回所有启用技能）
            top_k: 最多返回的技能数量
            threshold: BM25 分数阈值
        
        Returns:
            List[Dict]: OpenAI Tools 格式的工具规格列表
        """
        if query:
            return self._selector.get_level1_specs(query, top_k, threshold)
        return self._manager.get_skill_specs()
    
    def get_skill_names(self, query: str = None, top_k: int = None, 
                        threshold: float = None) -> List[str]:
        """获取技能名称列表
        
        Args:
            query: 用户查询文本（可选，不提供则返回所有启用技能，空字符串返回空列表）
            top_k: 最多返回的技能数量
            threshold: BM25 分数阈值
        
        Returns:
            List[str]: 技能名称列表
        """
        if query is None:
            return self._manager.get_skill_names()
        if not query:
            return []
        return self._selector.get_level0_names(query, top_k, threshold)
    
    def get_skill(self, skill_name: str) -> Optional[Skill]:
        """获取技能对象
        
        Args:
            skill_name: 技能名称
        
        Returns:
            Skill: 技能对象，如果不存在返回 None
        """
        return self._manager.get_skill(skill_name)
    
    def get_skill_full_instructions(self, skill_name: str) -> Optional[str]:
        """获取技能完整指令（Level 2）
        
        Args:
            skill_name: 技能名称
        
        Returns:
            str: 完整指令文本，如果技能不存在返回 None
        """
        return self._manager.get_skill_full_instructions(skill_name)
    
    def get_skill_references(self, skill_name: str) -> Dict[str, str]:
        """获取技能参考文档（Level 3）
        
        Args:
            skill_name: 技能名称
        
        Returns:
            Dict[str, str]: 参考文档字典，键为文件名，值为内容
        """
        return self._manager.get_skill_references(skill_name)
    
    async def execute(self, skill_name: str, **kwargs) -> SkillExecutionResult:
        """执行技能
        
        Args:
            skill_name: 技能名称
            **kwargs: 技能参数
        
        Returns:
            SkillExecutionResult: 执行结果
        """
        try:
            result = await self._manager.execute_skill(skill_name, **kwargs)
            if result is None:
                return SkillExecutionResult(
                    success=False,
                    skill_name=skill_name,
                    error=f"技能 {skill_name} 不存在或未启用"
                )
            return SkillExecutionResult(
                success=True,
                skill_name=skill_name,
                data=result
            )
        except Exception as e:
            return SkillExecutionResult(
                success=False,
                skill_name=skill_name,
                error=str(e)
            )
    
    def get_all_skills(self) -> Dict[str, Skill]:
        """获取所有技能（包括已禁用的）
        
        Returns:
            Dict[str, Skill]: 技能名称到技能对象的映射
        """
        return self._manager.get_all_skills()
    
    def get_enabled_skills(self) -> Dict[str, Skill]:
        """获取所有启用的技能
        
        Returns:
            Dict[str, Skill]: 技能名称到技能对象的映射
        """
        return self._manager.get_enabled_skills()
    
    def reload_skill(self, skill_name: str) -> bool:
        """重新加载单个技能
        
        Args:
            skill_name: 技能名称
        
        Returns:
            bool: 是否成功重新加载
        """
        success = self._system.registry.reload_skill(skill_name)
        if success:
            self._selector.update_skill_index(skill_name)
        return success
    
    def remove_skill(self, skill_name: str) -> bool:
        """移除技能
        
        Args:
            skill_name: 技能名称
        
        Returns:
            bool: 是否成功移除
        """
        self._system.registry.remove_skill(skill_name)
        self._selector.remove_skill_index(skill_name)
        return True
    
    def load_all_skills(self) -> int:
        """重新加载所有技能
        
        Returns:
            int: 加载的技能数量
        """
        count = self._system.registry.load_all_skills()
        self._selector.build_index()
        return count



