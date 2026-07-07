"""Skill 数据模型 - 基于文件系统的技能定义

核心设计原则：
  - name = SKILL.md 所在目录叶子名，是唯一标识
  - frontmatter 的 name 字段仅用于显示，不承担标识作用
  - 路径是 name 的唯一来源
"""
import os
import yaml
import logging
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field

from app.capabilities.skill.protocol import Skill as SkillABC

logger = logging.getLogger(__name__)


@dataclass
class Skill(SkillABC):
    """技能数据结构 - 实现 Skill ABC 接口

    name = 文件路径叶子名（唯一标识）
    frontmatter name 字段仅作显示用途，不参与标识逻辑。
    """

    name: str           # 唯一标识 = 路径叶子名
    description: str
    path: str           # 技能目录绝对路径
    version: str = "1.0.0"
    author: str = "Unknown"
    category: str = "general"
    enabled: bool = True
    metadata: Dict[str, Any] = field(default_factory=dict)

    def get_name(self) -> str:
        return self.name

    def get_level0_name(self) -> str:
        """Level 0：返回 name（同时也是 function.name）"""
        return self.name

    def get_description(self) -> str:
        return self.description

    def get_category(self) -> str:
        return self.category

    def is_enabled(self) -> bool:
        return self.enabled

    def get_parameters(self) -> List[Dict[str, Any]]:
        return self.metadata.get('parameters', [])

    def get_level1_spec(self) -> Dict[str, Any]:
        return {
            'name': self.name,
            'description': self.description,
            'category': self.category,
            'parameters': self.get_parameters(),
        }

    def build_tool_spec(self) -> Dict[str, Any]:
        """构建 OpenAI Tools 格式的工具规格

        function.name = self.name（= 路径叶子名 = 注册表 key）
        确保 LLM 调用时 function.name 与注册表 key 完全一致。
        """
        spec = self.get_level1_spec()
        params = spec['parameters']
        properties = {}
        required = []

        for param in params:
            properties[param['name']] = {
                'type': param['type'],
                'description': param['description'],
            }
            if param.get('required', False):
                required.append(param['name'])

        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": spec['description'],
                "parameters": {
                    "type": "object",
                    "properties": properties,
                    "required": required,
                }
            },
            "category": spec.get('category', 'general'),
        }

    def get_level2_instructions(self) -> str:
        """Level 2：按需从文件系统读取完整指令内容"""
        md_path = os.path.join(self.path, 'SKILL.md')
        with open(md_path, 'r', encoding='utf-8') as f:
            content = f.read()
        _, body = self._parse_frontmatter(content)
        return body.strip()

    def get_usage_examples(self) -> List[str]:
        return self.metadata.get('usage_examples', [])

    def get_level3_references(self) -> Dict[str, str]:
        refs: Dict[str, str] = {}
        ref_dir = os.path.join(self.path, 'references')
        if os.path.isdir(ref_dir):
            for fname in os.listdir(ref_dir):
                if fname.endswith('.md'):
                    fpath = os.path.join(ref_dir, fname)
                    with open(fpath, 'r', encoding='utf-8') as f:
                        refs[fname] = f.read()
        return refs

    def list_scripts(self) -> List[str]:
        scripts_dir = os.path.join(self.path, 'scripts')
        if os.path.isdir(scripts_dir):
            return sorted(os.listdir(scripts_dir))
        return []

    async def execute(self, **kwargs) -> Any:
        return {
            'skill_name': self.name,
            'instructions': self.get_level2_instructions(),
            'references': self.get_level3_references(),
            'scripts': self.list_scripts(),
            'parameters': self.get_parameters(),
        }

    # ── 工厂方法 ──────────────────────────────────────

    @classmethod
    def from_markdown(
        cls,
        content: str,
        skill_name: str,
        skill_dir: str,
    ) -> Optional['Skill']:
        """从 SKILL.md 内容创建 Skill 实例

        Args:
            content: SKILL.md 文件内容
            skill_name: 技能名（= 目录叶子名，唯一标识）
            skill_dir: 技能目录绝对路径

        frontmatter 的 name 字段仅验证一致性，不承担标识作用。
        """
        metadata, body = cls._parse_frontmatter(content)

        frontmatter_name = metadata.get('name', '')
        if frontmatter_name and frontmatter_name != skill_name:
            logger.warning(
                f"[Skill] frontmatter name='{frontmatter_name}' "
                f"与路径名='{skill_name}' 不一致，已忽略（路径名为准）"
            )

        return cls(
            name=skill_name,
            description=metadata.get('description', ''),
            path=skill_dir,
            version=metadata.get('version', '1.0.0'),
            author=metadata.get('author', 'Unknown'),
            category=metadata.get('category', 'general'),
            enabled=metadata.get('enabled', True),
            metadata=metadata,
        )

    @staticmethod
    def _parse_frontmatter(content: str) -> Tuple[Dict, str]:
        if not content.startswith('---'):
            return {}, content

        parts = content.split('---', 2)
        if len(parts) < 3:
            return {}, content

        frontmatter = parts[1].strip()
        body = parts[2].strip()
        metadata = yaml.safe_load(frontmatter) or {}

        return metadata, body

    def to_dict(self) -> Dict:
        return {
            'name': self.name,
            'description': self.description,
            'path': self.path,
            'version': self.version,
            'author': self.author,
            'category': self.category,
            'enabled': self.enabled,
            'metadata': self.metadata,
        }

    def get_summary(self) -> Dict:
        return {
            "name": self.name,
            "description": self.description,
            "category": self.category,
            "version": self.version,
        }
