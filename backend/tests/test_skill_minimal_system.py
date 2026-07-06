"""Skill 最小系统测试 - 持续运行，用于手动测试

使用方式：
    python tests/test_skill_minimal_system.py [技能目录路径]
    
功能：
- 启动完整的技能热加载系统
- 监听文件变化，实时显示技能列表
- 提供交互式命令：
  - list: 列出已启用的技能
  - registry: 显示注册表完整状态（全部技能+统计）
  - info <name>: 显示技能详细信息
  - level0 <name>: 显示 Level 0 摘要
  - level1 <name>: 显示 Level 1 完整指令
  - level2 <name>: 显示 Level 2 参考文档
  - search <keyword>: 搜索技能
  - help: 显示帮助
  - exit: 退出
"""
import os
import sys
import asyncio
import threading
import readline

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.capabilities.skill.skill_hotreload import SkillHotReloader


class SkillSystemTester:
    """技能系统测试器"""

    def __init__(self, skills_dir):
        self.skills_dir = skills_dir
        self.reloader = None
        self.running = False
        self.loop = None

    async def start(self):
        """启动技能系统"""
        self.reloader = SkillHotReloader(self.skills_dir)
        await self.reloader.start()
        self.running = True
        print(f"✅ 技能系统已启动")
        print(f"📁 监控目录: {self.reloader.path_resolver.skills_dir}")
        print(f"⏱️  防抖时间: {self.reloader.debounce_seconds}s")
        print()
        self._show_skills()

    async def stop(self):
        """停止技能系统"""
        if self.reloader:
            await self.reloader.stop()
        self.running = False
        print("\n✅ 技能系统已停止")

    def _show_skills(self):
        """显示当前技能列表"""
        if not self.reloader:
            return
        
        skills = self.reloader.registry.get_enabled_skills()
        if not skills:
            print("📭 当前无可用技能")
            return
        
        print(f"📚 当前已加载 {len(skills)} 个技能:")
        for i, (name, skill) in enumerate(sorted(skills.items()), 1):
            status = "✅" if skill.is_enabled() else "❌"
            print(f"  {i}. {status} {name} [{skill.category}] - {skill.description}")

    def _show_registry(self):
        """显示注册表完整状态"""
        if not self.reloader:
            return
        
        all_skills = self.reloader.registry.get_all_skills()
        enabled = self.reloader.registry.get_enabled_skills()
        
        print(f"\n📋 注册表状态")
        print(f"  总技能数: {len(all_skills)}")
        print(f"  已启用: {len(enabled)}")
        print(f"  已禁用: {len(all_skills) - len(enabled)}")
        print(f"  技能名称列表: {list(all_skills.keys())}")
        
        if all_skills:
            print(f"\n  全部技能详情:")
            for i, (name, skill) in enumerate(sorted(all_skills.items()), 1):
                status = "✅" if skill.is_enabled() else "❌"
                level = "L0/L1/L2" if skill.get_references() else ("L0/L1" if skill.content else "L0")
                print(f"  {i}. {status} {name}")
                print(f"     分类: {skill.category} | 版本: {skill.version}")
                print(f"     披露级别: {level} | 预估Token: {skill.get_level0_summary().get('estimated_tokens', 0)}")
                print(f"     路径: {skill.path}")
                if skill.description:
                    print(f"     描述: {skill.description}")

    def _show_skill_info(self, name):
        """显示技能详细信息"""
        if not self.reloader:
            return
        
        skill = self.reloader.registry.get_skill(name)
        if not skill:
            print(f"❌ 技能 '{name}' 不存在")
            return
        
        print(f"\n📋 技能详情: {skill.name}")
        print(f"  描述: {skill.description}")
        print(f"  分类: {skill.category}")
        print(f"  版本: {skill.version}")
        print(f"  作者: {skill.author}")
        print(f"  启用: {'是' if skill.is_enabled() else '否'}")
        print(f"  路径: {skill.path}")
        print(f"  参数: {len(skill.get_parameters())} 个")
        for param in skill.get_parameters():
            req = "*" if param.get('required', False) else " "
            print(f"    {req} {param['name']} ({param['type']}): {param['description']}")
        print(f"  指令长度: {len(skill.content)} 字符")
        print(f"  参考文档: {len(skill.get_references())} 个")
        print(f"  脚本文件: {skill.list_scripts()}")

    def _show_level0(self, name):
        """显示 Level 0 摘要"""
        if not self.reloader:
            return
        
        skill = self.reloader.registry.get_skill(name)
        if not skill:
            print(f"❌ 技能 '{name}' 不存在")
            return
        
        summary = skill.get_level0_summary()
        print(f"\n🎯 Level 0 摘要 - {name}")
        print(f"  名称: {summary['name']}")
        print(f"  描述: {summary['description']}")
        print(f"  分类: {summary['category']}")
        print(f"  参数: {summary['parameters']}")
        print(f"  估算 Token: {summary['estimated_tokens']}")

    def _show_level1(self, name):
        """显示 Level 1 完整指令"""
        if not self.reloader:
            return
        
        skill = self.reloader.registry.get_skill(name)
        if not skill:
            print(f"❌ 技能 '{name}' 不存在")
            return
        
        instructions = skill.get_instructions()
        if not instructions:
            print(f"📭 技能 '{name}' 无指令内容")
            return
        
        print(f"\n📖 Level 1 完整指令 - {name}")
        print("-" * 60)
        print(instructions)
        print("-" * 60)

    def _show_level2(self, name):
        """显示 Level 2 参考文档"""
        if not self.reloader:
            return
        
        skill = self.reloader.registry.get_skill(name)
        if not skill:
            print(f"❌ 技能 '{name}' 不存在")
            return
        
        refs = skill.get_references()
        if not refs:
            print(f"📭 技能 '{name}' 无参考文档")
            return
        
        print(f"\n📚 Level 2 参考文档 - {name}")
        print("-" * 60)
        for fname, content in refs.items():
            print(f"【{fname}】")
            print(content)
            print("-" * 60)

    def _search_skills(self, keyword):
        """搜索技能"""
        if not self.reloader:
            return
        
        results = self.reloader.registry.search_skills(keyword)
        if not results:
            print(f"📭 未找到包含 '{keyword}' 的技能")
            return
        
        print(f"\n🔍 搜索结果 '{keyword}' - 找到 {len(results)} 个技能:")
        for i, skill in enumerate(results, 1):
            print(f"  {i}. {skill.name} [{skill.category}] - {skill.description}")

    def _print_help(self):
        """显示帮助"""
        print("\n📝 可用命令:")
        print("  list              - 列出已启用的技能")
        print("  registry          - 显示注册表完整状态（全部技能+统计）")
        print("  info <name>       - 显示技能详细信息")
        print("  level0 <name>     - 显示 Level 0 摘要")
        print("  level1 <name>     - 显示 Level 1 完整指令")
        print("  level2 <name>     - 显示 Level 2 参考文档")
        print("  search <keyword>  - 搜索技能")
        print("  watch             - 监控文件变化（后台）")
        print("  help              - 显示帮助")
        print("  exit              - 退出")

    def handle_command(self, cmd):
        """处理用户命令"""
        cmd = cmd.strip()
        if not cmd:
            return
        
        parts = cmd.split(' ', 1)
        command = parts[0].lower()
        args = parts[1].strip() if len(parts) > 1 else ''
        
        if command == 'list':
            self._show_skills()
        elif command == 'registry':
            self._show_registry()
        elif command == 'info':
            if args:
                self._show_skill_info(args)
            else:
                print("❌ 请指定技能名称: info <name>")
        elif command == 'level0':
            if args:
                self._show_level0(args)
            else:
                print("❌ 请指定技能名称: level0 <name>")
        elif command == 'level1':
            if args:
                self._show_level1(args)
            else:
                print("❌ 请指定技能名称: level1 <name>")
        elif command == 'level2':
            if args:
                self._show_level2(args)
            else:
                print("❌ 请指定技能名称: level2 <name>")
        elif command == 'search':
            if args:
                self._search_skills(args)
            else:
                print("❌ 请指定搜索关键词: search <keyword>")
        elif command == 'watch':
            print("👁️  文件监控已在后台运行，修改 SKILL.md 会自动更新")
        elif command == 'help':
            self._print_help()
        elif command == 'exit':
            self.running = False
        else:
            print(f"❌ 未知命令 '{command}'，输入 help 查看可用命令")


async def async_main(skills_dir):
    """异步主函数"""
    tester = SkillSystemTester(skills_dir)
    await tester.start()
    
    def input_loop():
        """输入循环（在单独线程运行）"""
        readline.set_history_length(100)
        while tester.running:
            try:
                cmd = input("\n> ")
                tester.handle_command(cmd)
            except EOFError:
                tester.running = False
            except KeyboardInterrupt:
                tester.running = False
    
    input_thread = threading.Thread(target=input_loop, daemon=True)
    input_thread.start()
    
    while tester.running:
        await asyncio.sleep(0.1)
    
    await tester.stop()


def main():
    """主入口"""
    skills_dir = sys.argv[1] if len(sys.argv) > 1 else os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        'data', 'skills'
    )
    
    skills_dir = os.path.abspath(skills_dir)
    
    print("=" * 60)
    print("🎯 MemOS Skill System - 最小系统测试")
    print("=" * 60)
    print(f"技能目录: {skills_dir}")
    print()
    
    if not os.path.exists(skills_dir):
        print(f"📁 创建技能目录: {skills_dir}")
        os.makedirs(skills_dir)
    
    asyncio.run(async_main(skills_dir))


if __name__ == '__main__':
    main()