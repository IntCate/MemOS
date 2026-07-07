"""Skill 系统单元测试

测试覆盖：
- 热更新机制：文件创建/修改/删除时技能自动加载
- 注册机制：技能注册、查询、删除
- 互斥规则：两级目录互斥
- 文件监控：watchdog 事件处理
- 渐进性披露：Level 0/1/2/3
"""
import os
import sys
import tempfile
import shutil
import time
import asyncio
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.capabilities.skill.skill_model import Skill
from app.capabilities.skill.path_resolver import SkillPathResolver
from app.capabilities.skill.registry import SkillRegistry
from app.capabilities.skill.skill_hotreload import SkillHotReloader


class TestSkillModel:
    """测试技能数据模型"""

    def test_from_markdown(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            skill_dir = os.path.join(tmpdir, 'test_skill')
            os.makedirs(skill_dir)
            content = """---
name: test_skill
description: 测试技能
category: test
version: 1.0.0
author: Test
enabled: true
parameters:
  - name: query
    type: string
    description: 查询词
    required: true
---
# 指令内容
这是测试技能的指令。
"""
            with open(os.path.join(skill_dir, 'SKILL.md'), 'w') as f:
                f.write(content)
            
            skill = Skill.from_markdown(content, 'test_skill', skill_dir)
            assert skill is not None
            assert skill.name == 'test_skill'
            assert skill.description == '测试技能'
            assert skill.category == 'test'
            assert skill.version == '1.0.0'
            assert skill.enabled == True
            assert len(skill.get_parameters()) == 1
            assert skill.get_parameters()[0]['name'] == 'query'
            assert skill.get_level2_instructions() == '# 指令内容\n这是测试技能的指令。'

    def test_level0_name(self):
        skill = Skill(
            name='test_skill',
            description='测试技能描述',
            path='/tmp/test',
            category='test'
        )
        name = skill.get_level0_name()
        assert name == 'test_skill'

    def test_level1_spec(self):
        skill = Skill(
            name='test_skill',
            description='测试技能描述',
            path='/tmp/test',
            category='test'
        )
        spec = skill.get_level1_spec()
        assert 'name' in spec
        assert 'description' in spec
        assert 'category' in spec
        assert 'parameters' in spec
        assert spec['name'] == 'test_skill'
        assert spec['description'] == '测试技能描述'

    def test_level2_instructions(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            skill_dir = os.path.join(tmpdir, 'test_skill')
            os.makedirs(skill_dir)
            with open(os.path.join(skill_dir, 'SKILL.md'), 'w') as f:
                f.write("""---
name: test_skill
---
完整指令内容
""")
            
            skill = Skill(
                name='test_skill',
                description='测试',
                path=skill_dir
            )
            assert skill.get_level2_instructions() == '完整指令内容'

    def test_level3_references(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            skill_dir = os.path.join(tmpdir, 'test_skill')
            os.makedirs(skill_dir)
            with open(os.path.join(skill_dir, 'SKILL.md'), 'w') as f:
                f.write("""---
name: test_skill
---
指令
""")
            
            ref_dir = os.path.join(skill_dir, 'references')
            os.makedirs(ref_dir)
            with open(os.path.join(ref_dir, 'api.md'), 'w') as f:
                f.write('# API 文档')
            
            skill = Skill(
                name='test_skill',
                description='测试',
                path=skill_dir
            )
            refs = skill.get_level3_references()
            assert 'api.md' in refs
            assert refs['api.md'] == '# API 文档'


class TestPathResolver:
    """测试路径解析器"""

    def test_extract_skill_id(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            resolver = SkillPathResolver(tmpdir)
            
            skill_dir = os.path.join(tmpdir, 'test_skill')
            os.makedirs(skill_dir)
            with open(os.path.join(skill_dir, 'SKILL.md'), 'w') as f:
                f.write('test')
            
            assert resolver.extract_skill_id(os.path.join(skill_dir, 'SKILL.md')) == 'test_skill'
            assert resolver.extract_skill_id(skill_dir) == 'test_skill'

    def test_extract_category_and_skill(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            resolver = SkillPathResolver(tmpdir)
            
            cat_dir = os.path.join(tmpdir, 'category', 'skill_name')
            os.makedirs(cat_dir)
            with open(os.path.join(cat_dir, 'SKILL.md'), 'w') as f:
                f.write('test')
            
            result = resolver.extract_category_and_skill(os.path.join(cat_dir, 'SKILL.md'))
            assert result == ('category', 'skill_name')

    def test_list_skill_dirs_single_level(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            resolver = SkillPathResolver(tmpdir)
            
            os.makedirs(os.path.join(tmpdir, 'skill1'))
            with open(os.path.join(tmpdir, 'skill1', 'SKILL.md'), 'w') as f:
                f.write('test1')
            
            os.makedirs(os.path.join(tmpdir, 'skill2'))
            with open(os.path.join(tmpdir, 'skill2', 'SKILL.md'), 'w') as f:
                f.write('test2')
            
            skill_dirs = resolver.list_skill_dirs()
            assert len(skill_dirs) == 2
            assert 'skill1' in skill_dirs
            assert 'skill2' in skill_dirs

    def test_list_skill_dirs_two_levels(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            resolver = SkillPathResolver(tmpdir)
            
            os.makedirs(os.path.join(tmpdir, 'category1', 'skill1'))
            with open(os.path.join(tmpdir, 'category1', 'skill1', 'SKILL.md'), 'w') as f:
                f.write('test1')
            
            os.makedirs(os.path.join(tmpdir, 'category2', 'skill2'))
            with open(os.path.join(tmpdir, 'category2', 'skill2', 'SKILL.md'), 'w') as f:
                f.write('test2')
            
            skill_dirs = resolver.list_skill_dirs()
            assert len(skill_dirs) == 2
            # 新设计：list_skill_dirs 返回叶子名（skill_name）
            assert 'skill1' in skill_dirs
            assert 'skill2' in skill_dirs


class TestSkillRegistry:
    """测试技能注册中心"""

    def test_load_all_skills(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            resolver = SkillPathResolver(tmpdir)
            registry = SkillRegistry(resolver)
            
            os.makedirs(os.path.join(tmpdir, 'skill1'))
            with open(os.path.join(tmpdir, 'skill1', 'SKILL.md'), 'w') as f:
                f.write("""---
name: skill1
description: 技能1
---
指令1
""")
            
            count = registry.load_all_skills()
            assert count == 1
            assert 'skill1' in registry.get_skill_names()

    def test_add_and_get_skill(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            resolver = SkillPathResolver(tmpdir)
            registry = SkillRegistry(resolver)
            
            skill_dir = os.path.join(tmpdir, 'test_skill')
            os.makedirs(skill_dir)
            with open(os.path.join(skill_dir, 'SKILL.md'), 'w') as f:
                f.write("""---
name: test_skill
---
指令
""")
            
            skill = Skill(
                name='test_skill',
                description='测试',
                path=skill_dir
            )
            registry.add_skill(skill)
            
            retrieved = registry.get_skill('test_skill')
            assert retrieved is not None
            assert retrieved.name == 'test_skill'

    def test_remove_skill(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            resolver = SkillPathResolver(tmpdir)
            registry = SkillRegistry(resolver)
            
            skill_dir = os.path.join(tmpdir, 'test_skill')
            os.makedirs(skill_dir)
            with open(os.path.join(skill_dir, 'SKILL.md'), 'w') as f:
                f.write("""---
name: test_skill
---
指令
""")
            
            skill = Skill(
                name='test_skill',
                description='测试',
                path=skill_dir
            )
            registry.add_skill(skill)
            assert registry.get_skill('test_skill') is not None
            
            registry.remove_skill('test_skill')
            assert registry.get_skill('test_skill') is None

    def test_exclusive_rule_single_level(self):
        """测试二级优先规则：一级和二级都有 SKILL.md 时，加载二级并警告"""
        with tempfile.TemporaryDirectory() as tmpdir:
            resolver = SkillPathResolver(tmpdir)
            registry = SkillRegistry(resolver)
            
            os.makedirs(os.path.join(tmpdir, 'category'))
            with open(os.path.join(tmpdir, 'category', 'SKILL.md'), 'w') as f:
                f.write("""---
name: category
description: 分类技能
---
指令
""")
            
            os.makedirs(os.path.join(tmpdir, 'category', 'sub_skill'))
            with open(os.path.join(tmpdir, 'category', 'sub_skill', 'SKILL.md'), 'w') as f:
                f.write("""---
name: sub_skill
description: 子技能
---
指令
""")
            
            registry.load_all_skills()
            skills = registry.get_skill_names()
            assert 'sub_skill' in skills
            assert 'category' not in skills

    def test_exclusive_rule_two_levels(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            resolver = SkillPathResolver(tmpdir)
            registry = SkillRegistry(resolver)
            
            os.makedirs(os.path.join(tmpdir, 'category', 'sub_skill'))
            with open(os.path.join(tmpdir, 'category', 'sub_skill', 'SKILL.md'), 'w') as f:
                f.write("""---
name: sub_skill
description: 子技能
---
指令
""")
            
            registry.load_all_skills()
            skills = registry.get_skill_names()
            # 新设计：注册表 key = skill_name（叶子名）
            assert 'sub_skill' in skills
            assert len(skills) == 1

    def test_no_skill_in_both_levels(self):
        """测试场景1：一级和二级都没有 SKILL.md"""
        with tempfile.TemporaryDirectory() as tmpdir:
            resolver = SkillPathResolver(tmpdir)
            registry = SkillRegistry(resolver)
            
            os.makedirs(os.path.join(tmpdir, 'empty_category', 'empty_sub'))
            
            registry.load_all_skills()
            skills = registry.get_skill_names()
            assert len(skills) == 0

    def test_top_level_with_empty_subdirs(self):
        """测试场景5：一级有 SKILL.md，二级目录存在但为空"""
        with tempfile.TemporaryDirectory() as tmpdir:
            resolver = SkillPathResolver(tmpdir)
            registry = SkillRegistry(resolver)
            
            os.makedirs(os.path.join(tmpdir, 'category', 'empty_sub'))
            with open(os.path.join(tmpdir, 'category', 'SKILL.md'), 'w') as f:
                f.write("""---
name: category
description: 分类技能
---
指令
""")
            
            registry.load_all_skills()
            skills = registry.get_skill_names()
            assert 'category' in skills
            assert len(skills) == 1

    def test_top_level_only(self):
        """测试场景3：一级有 SKILL.md，二级目录不存在"""
        with tempfile.TemporaryDirectory() as tmpdir:
            resolver = SkillPathResolver(tmpdir)
            registry = SkillRegistry(resolver)
            
            os.makedirs(os.path.join(tmpdir, 'standalone_skill'))
            with open(os.path.join(tmpdir, 'standalone_skill', 'SKILL.md'), 'w') as f:
                f.write("""---
name: standalone_skill
description: 独立技能
---
指令
""")
            
            registry.load_all_skills()
            skills = registry.get_skill_names()
            assert 'standalone_skill' in skills
            assert len(skills) == 1

    def test_second_level_only(self):
        """测试场景2：一级无 SKILL.md，二级有 SKILL.md"""
        with tempfile.TemporaryDirectory() as tmpdir:
            resolver = SkillPathResolver(tmpdir)
            registry = SkillRegistry(resolver)
            
            os.makedirs(os.path.join(tmpdir, 'category', 'sub_skill'))
            with open(os.path.join(tmpdir, 'category', 'sub_skill', 'SKILL.md'), 'w') as f:
                f.write("""---
name: sub_skill
description: 子技能
---
指令
""")
            
            registry.load_all_skills()
            skills = registry.get_skill_names()
            assert 'sub_skill' in skills
            assert len(skills) == 1

    def test_search_skills(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            resolver = SkillPathResolver(tmpdir)
            registry = SkillRegistry(resolver)
            
            os.makedirs(os.path.join(tmpdir, 'web_search'))
            with open(os.path.join(tmpdir, 'web_search', 'SKILL.md'), 'w') as f:
                f.write("""---
name: web_search
description: 网络搜索技能
---
指令
""")
            
            os.makedirs(os.path.join(tmpdir, 'file_search'))
            with open(os.path.join(tmpdir, 'file_search', 'SKILL.md'), 'w') as f:
                f.write("""---
name: file_search
description: 文件搜索技能
---
指令
""")
            
            registry.load_all_skills()
            results = registry.search_skills('search')
            assert len(results) == 2
            
            results = registry.search_skills('web')
            assert len(results) == 1
            assert results[0].name == 'web_search'


class TestSkillHotReloader:
    """测试热加载器"""

    def test_start_stop(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            async def run():
                reloader = SkillHotReloader(tmpdir)
                await reloader.start()
                assert reloader.is_running == True
                await reloader.stop()
                assert reloader.is_running == False
            asyncio.run(run())

    def test_initial_load(self):
        """测试初始化时加载技能"""
        with tempfile.TemporaryDirectory() as tmpdir:
            os.makedirs(os.path.join(tmpdir, 'skill1'))
            with open(os.path.join(tmpdir, 'skill1', 'SKILL.md'), 'w') as f:
                f.write("""---
name: skill1
description: 测试技能
---
指令
""")
            
            async def run():
                reloader = SkillHotReloader(tmpdir)
                await reloader.start()
                
                skills = reloader.registry.get_skill_names()
                assert 'skill1' in skills
                
                await reloader.stop()
            asyncio.run(run())

    def test_registry_access(self):
        """测试通过热加载器访问注册中心"""
        with tempfile.TemporaryDirectory() as tmpdir:
            async def run():
                reloader = SkillHotReloader(tmpdir)
                await reloader.start()
                
                assert reloader.registry is not None
                assert reloader.path_resolver is not None
                
                await reloader.stop()
            asyncio.run(run())


class TestSkillSelector:
    """测试技能选择器（BM25 L0 筛选）"""

    def test_get_level0_names_bm25_filtering(self):
        """测试 BM25 在 L0 阶段筛选技能名称"""
        with tempfile.TemporaryDirectory() as tmpdir:
            os.makedirs(os.path.join(tmpdir, 'web_search'))
            with open(os.path.join(tmpdir, 'web_search', 'SKILL.md'), 'w') as f:
                f.write("""---
name: web_search
description: 执行网络搜索，获取实时信息
category: search
parameters:
  - name: query
    type: string
    description: 搜索查询词
    required: true
---
指令内容
""")
            
            os.makedirs(os.path.join(tmpdir, 'file_search'))
            with open(os.path.join(tmpdir, 'file_search', 'SKILL.md'), 'w') as f:
                f.write("""---
name: file_search
description: 在本地文件中搜索内容
category: tools
parameters:
  - name: keyword
    type: string
    description: 搜索关键词
    required: true
---
指令内容
""")
            
            os.makedirs(os.path.join(tmpdir, 'data_analyzer'))
            with open(os.path.join(tmpdir, 'data_analyzer', 'SKILL.md'), 'w') as f:
                f.write("""---
name: data_analyzer
description: 分析结构化数据文件
category: data
parameters:
  - name: file_path
    type: string
    description: 数据文件路径
    required: true
---
指令内容
""")
            
            from app.capabilities.skill import SkillSystem
            
            skill_system = SkillSystem(skills_dir=tmpdir)
            asyncio.run(skill_system.start())
            
            names = skill_system.get_skill_names('搜索网络信息', top_k=2)
            assert len(names) <= 2
            assert 'web_search' in names
            
            names = skill_system.get_skill_names('分析数据', top_k=2)
            assert len(names) <= 2
            assert 'data_analyzer' in names

    def test_get_level0_names_empty_query(self):
        """测试空查询时返回空列表"""
        with tempfile.TemporaryDirectory() as tmpdir:
            os.makedirs(os.path.join(tmpdir, 'web_search'))
            with open(os.path.join(tmpdir, 'web_search', 'SKILL.md'), 'w') as f:
                f.write("""---
name: web_search
description: 网络搜索
---
指令
""")
            
            from app.capabilities.skill import SkillSystem
            
            skill_system = SkillSystem(skills_dir=tmpdir)
            
            names = skill_system.get_skill_names('')
            assert len(names) == 0

    def test_manager_get_level0_skill_names(self):
        """测试 manager 的 L0 技能名称筛选"""
        with tempfile.TemporaryDirectory() as tmpdir:
            os.makedirs(os.path.join(tmpdir, 'web_search'))
            with open(os.path.join(tmpdir, 'web_search', 'SKILL.md'), 'w') as f:
                f.write("""---
name: web_search
description: 网络搜索
---
指令
""")
            
            from app.capabilities.skill import SkillSystem
            
            skill_system = SkillSystem(skills_dir=tmpdir)
            asyncio.run(skill_system.start())
            
            names = skill_system.get_skill_names('搜索')
            assert 'web_search' in names


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
