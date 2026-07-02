"""基于文件系统的 Skill 实现

每个 Skill 对应一个目录，目录下包含：
  - SKILL.md（必需）：YAML frontmatter + Markdown 指令
  - scripts/（可选）：可执行脚本
  - references/（可选）：参考文档
"""
import os
import yaml
from typing import Dict, List, Any
from app.capabilities.skill.protocol import Skill
from app.core.logger import logger


class FileBasedSkill(Skill):
    """从文件系统目录加载的 Skill

    SKILL.md 格式（YAML frontmatter + Markdown body）：
    ---
    name: skill_name
    description: Skill 描述
    category: search
    parameters:
      - name: query
        type: string
        description: 查询参数
        required: true
    enabled: true
    ---

    # 指令
    具体的行为指令内容...
    """

    def __init__(self, skill_dir: str, skill_config: Dict[str, Any]):
        self.skill_dir = skill_dir
        self._name = skill_config.get('name', os.path.basename(skill_dir))
        self._description = skill_config.get('description', '')
        self._category = skill_config.get('category', 'general')
        self._parameters = skill_config.get('parameters', [])
        self._enabled = skill_config.get('enabled', True)
        self._instructions = skill_config.get('instructions', '')

    def get_name(self) -> str:
        return self._name

    def get_description(self) -> str:
        return self._description

    def get_parameters(self) -> List[Dict[str, Any]]:
        return self._parameters

    def get_category(self) -> str:
        return self._category

    def is_enabled(self) -> bool:
        return self._enabled

    def set_enabled(self, enabled: bool):
        self._enabled = enabled

    def get_instructions(self) -> str:
        """获取 SKILL.md 中的指令内容"""
        return self._instructions

    def get_references(self) -> Dict[str, str]:
        """读取 references/ 目录下的所有 .md 参考文档"""
        refs: Dict[str, str] = {}
        ref_dir = os.path.join(self.skill_dir, 'references')
        if os.path.isdir(ref_dir):
            for fname in os.listdir(ref_dir):
                if fname.endswith('.md'):
                    fpath = os.path.join(ref_dir, fname)
                    try:
                        with open(fpath, 'r', encoding='utf-8') as f:
                            refs[fname] = f.read()
                    except Exception as e:
                        logger.warning(f"[FileBasedSkill] 读取参考文档失败 {fpath}: {e}")
        return refs

    def list_scripts(self) -> List[str]:
        """列出 scripts/ 目录下的所有脚本文件"""
        scripts_dir = os.path.join(self.skill_dir, 'scripts')
        if os.path.isdir(scripts_dir):
            return sorted(os.listdir(scripts_dir))
        return []

    async def execute(self, **kwargs) -> Any:
        """执行 Skill

        FileBasedSkill 将指令 + 参考文档作为上下文返回，
        实际的工具调用由 AI Agent 结合 MCP 等能力层完成。
        """
        context = {
            'skill_name': self._name,
            'instructions': self._instructions,
            'references': self.get_references(),
            'scripts': self.list_scripts(),
            'parameters': self._parameters,
        }
        return context


def parse_skill_md(file_path: str) -> Dict[str, Any]:
    """解析 SKILL.md 文件，分离 YAML frontmatter 和 Markdown body

    Args:
        file_path: SKILL.md 文件路径

    Returns:
        Dict 包含 name, description, category, parameters, enabled, instructions
        解析失败返回空 dict
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
    except Exception as e:
        logger.error(f"[SkillLoader] 读取 SKILL.md 失败 {file_path}: {e}")
        return {}

    frontmatter = {}
    body = content

    # 解析 YAML frontmatter（--- 分隔）
    if content.startswith('---'):
        parts = content.split('---', 2)
        if len(parts) >= 3:
            try:
                frontmatter = yaml.safe_load(parts[1]) or {}
            except yaml.YAMLError as e:
                logger.error(f"[SkillLoader] 解析 SKILL.md frontmatter 失败 {file_path}: {e}")
                return {}
            body = parts[2].strip()

    return {
        'name': frontmatter.get('name', ''),
        'description': frontmatter.get('description', ''),
        'category': frontmatter.get('category', 'general'),
        'parameters': frontmatter.get('parameters', []),
        'enabled': frontmatter.get('enabled', True),
        'instructions': body,
    }
