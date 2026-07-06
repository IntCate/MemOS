"""SkillSelector — 基于 bm25s 的技能自动筛选

使用 bm25s（基于稀疏矩阵的高速 BM25 实现）替代 rank_bm25，
索引构建速度提升 10-100 倍，即使全量重建也能满足热加载需求。

工作原理：
  1. 使用 bm25s.tokenize() 对所有 Skill 的 Level 1 数据进行分词
  2. 使用 BM25.index() 建立稀疏矩阵索引
  3. 收到用户查询时，使用 BM25.retrieve() 获取 top_k 结果
  4. 热加载时更新 corpus 并重建索引（bm25s 重建速度极快）

集成方式：
  AI Subsystem → assemble_prompt 阶段调用 SkillSelector
  → 仅将筛选后的技能注入为 OpenAI Tools 格式
"""
import os
import threading
from typing import Dict, List, Optional, Any

from app.core.logger import logger
from app.capabilities.skill.manager import skill_manager
from app.capabilities.skill.protocol import Skill


class SkillSelector:
    """基于 bm25s 的技能筛选器

    使用 bm25s 实现高速 BM25 匹配，支持中文分词（jieba）和英文分词。
    线程安全设计，支持热加载场景。
    """

    def __init__(self, top_k: int = 5, score_threshold: float = 0.01):
        """
        Args:
            top_k: 最多返回的技能数
            score_threshold: BM25 分数阈值，低于此值的技能被丢弃
        """
        self.top_k = top_k
        self.score_threshold = score_threshold
        self._bm25 = None
        self._skill_names: List[str] = []
        self._corpus_tokens = None
        self._lock = threading.RLock()

    @property
    def _tokenizer(self):
        """延迟加载分词器"""
        try:
            import jieba
            return jieba.lcut
        except ImportError:
            logger.warning("[SkillSelector] jieba 未安装，使用字符级分词")
            return lambda text: list(text)

    def _tokenize(self, text: str) -> List[str]:
        """分词处理（支持中英文）"""
        tokenizer = self._tokenizer
        tokens = tokenizer(text.lower())
        return [t for t in tokens if len(t) >= 2]

    def build_index(self) -> int:
        """为所有已注册 Skill 构建 BM25 索引

        Returns:
            成功索引的技能数量
        """
        with self._lock:
            skills = skill_manager.get_enabled_skills()
            if not skills:
                return 0

            try:
                import bm25s
            except ImportError:
                logger.warning("[SkillSelector] bm25s 未安装，无法构建索引")
                return 0

            self._skill_names = list(skills.keys())
            
            corpus_texts = []
            for name, skill in skills.items():
                spec = skill.get_level1_spec()
                text = f"{spec['name']} {spec['description']}"
                for param in spec.get('parameters', []):
                    text += f" {param.get('name', '')} {param.get('description', '')}"
                corpus_texts.append(text)

            self._corpus_tokens = bm25s.tokenize(corpus_texts)
            self._bm25 = bm25s.BM25()
            self._bm25.index(self._corpus_tokens)

            logger.info(f"[SkillSelector] BM25 索引完成: {len(self._skill_names)} 个 Skill")
            return len(self._skill_names)

    def update_skill_index(self, skill_name: str) -> bool:
        """热加载时更新单个 Skill 的索引

        使用 bm25s 重建索引（比 rank_bm25 快 10-100 倍），
        虽然是全量重建，但速度足够快，满足热加载需求。

        Args:
            skill_name: 技能名称

        Returns:
            bool: 是否成功更新
        """
        with self._lock:
            skill = skill_manager.get_skill(skill_name)
            if not skill:
                return False

            if self._bm25 is None:
                return self.build_index() > 0

            if not skill.is_enabled():
                self.remove_skill_index(skill_name)
                return True

            try:
                idx = self._skill_names.index(skill_name)
                spec = skill.get_level1_spec()
                text = f"{spec['name']} {spec['description']}"
                for param in spec.get('parameters', []):
                    text += f" {param.get('name', '')} {param.get('description', '')}"
                
                import bm25s
                self._corpus_tokens[idx] = bm25s.tokenize([text])[0]
                self._bm25.index(self._corpus_tokens)
                
                logger.info(f"[SkillSelector] 技能索引已更新: {skill_name}")
                return True
            except ValueError:
                self.build_index()
                return True
            except Exception as e:
                logger.error(f"[SkillSelector] 更新技能索引失败 {skill_name}: {e}", exc_info=True)
                return False

    def remove_skill_index(self, skill_name: str):
        """热卸载时移除 Skill 索引"""
        with self._lock:
            if self._bm25 is None or not self._skill_names:
                return

            try:
                idx = self._skill_names.index(skill_name)
                self._skill_names.pop(idx)
                self.build_index()
                logger.info(f"[SkillSelector] 技能索引已移除: {skill_name}")
            except ValueError:
                pass
            except Exception as e:
                logger.error(f"[SkillSelector] 移除技能索引失败 {skill_name}: {e}", exc_info=True)

    def _rank_by_bm25(self, query: str) -> List[Dict[str, Any]]:
        """基于 BM25 分数排序 Skills"""
        with self._lock:
            if self._bm25 is None:
                return self._rank_by_keyword(query)

            if not self._skill_names:
                return []

            try:
                import bm25s
                query_tokens = bm25s.tokenize([query])
                if query_tokens[0].size == 0:
                    return []

                results, scores = self._bm25.retrieve(query_tokens, k=len(self._skill_names))
                
                ranked = []
                for i in range(results.shape[1]):
                    doc_idx = int(results[0, i])
                    if doc_idx < len(self._skill_names):
                        ranked.append({
                            'skill_name': self._skill_names[doc_idx],
                            'similarity': float(scores[0, i]),
                        })

                return ranked
            except Exception as e:
                logger.error(f"[SkillSelector] BM25 排序失败: {e}", exc_info=True)
                return self._rank_by_keyword(query)

    def _rank_by_keyword(self, query: str) -> List[Dict[str, Any]]:
        """关键词匹配回退方案（无 bm25s 库时）"""
        query_lower = query.lower()
        results = []

        for name, skill in skill_manager.get_enabled_skills().items():
            spec = skill.get_level1_spec()
            desc_lower = spec.get('description', '').lower()
            name_lower = spec.get('name', '').lower()
            
            score = 0.0

            for term in name_lower.replace('_', ' ').split():
                if len(term) >= 2 and term in query_lower:
                    score += 0.5

            desc_clean = desc_lower.replace('，', ' ').replace('、', ' ').replace('。', ' ')
            for term in desc_clean.split():
                if len(term) >= 2 and term in query_lower:
                    score += 0.3

            for size in (4, 3, 2):
                for i in range(len(query_lower) - size + 1):
                    sub = query_lower[i:i+size]
                    if sub in desc_lower or sub in name_lower:
                        score += 0.15 * (size / 4.0)
                        break

            score = min(score, 1.0)
            if score > 0:
                results.append({
                    'skill_name': name,
                    'similarity': round(score, 4),
                })

        results.sort(key=lambda x: x['similarity'], reverse=True)
        return results

    def get_level0_names(self, query: str, top_k: int = None, threshold: float = None) -> List[str]:
        """Level 0: 根据查询筛选最相关的 Skill 名称列表（最轻量）

        BM25 匹配基于 Level 1 数据（name + description + parameters）构建的索引，
        但仅返回匹配的 skill name，用于最小化 Prompt token 消耗。

        Args:
            query: 用户查询文本
            top_k: 最多返回几个（覆盖全局设置）
            threshold: BM25 分数阈值（覆盖全局设置）

        Returns:
            List[str]: 匹配的技能名称列表（如 ["web_search", "data_analyzer"]）
        """
        k = top_k or self.top_k
        th = threshold or self.score_threshold

        ranked = self._rank_by_bm25(query)

        names = []
        for item in ranked:
            if item['similarity'] < th:
                continue
            skill_name = item['skill_name']
            skill = skill_manager.get_skill(skill_name)
            if skill and skill.is_enabled():
                names.append(skill.get_level0_name())
            if len(names) >= k:
                break

        return names

    def select(self, query: str, top_k: int = None, threshold: float = None) -> List[Dict[str, Any]]:
        """Level 1: 根据查询选择最相关的 Skills（含 Level 1 specs）

        Args:
            query: 用户查询文本
            top_k: 最多返回几个（覆盖全局设置）
            threshold: BM25 分数阈值（覆盖全局设置）

        Returns:
            [
                {
                    "skill_name": "web_search",
                    "similarity": 0.85,
                    "level1_spec": { ... },   // OpenAI Tools 格式规格
                }
            ]
        """
        k = top_k or self.top_k
        th = threshold or self.score_threshold

        ranked = self._rank_by_bm25(query)

        selected = []
        for item in ranked:
            if item['similarity'] < th:
                continue
            skill_name = item['skill_name']
            skill = skill_manager.get_skill(skill_name)
            if skill and skill.is_enabled():
                item['level1_spec'] = self._build_level1_spec(skill)
                selected.append(item)
            if len(selected) >= k:
                break

        return selected

    def get_level1_specs(self, query: str, top_k: int = None, threshold: float = None) -> List[Dict[str, Any]]:
        """Level 1: 便捷方法，直接返回 OpenAI Tools 格式的 Level 1 规格列表

        当 Agent 决定调用技能时使用。
        """
        selected = self.select(query, top_k, threshold)
        return [s['level1_spec'] for s in selected if 'level1_spec' in s]

    def get_level2_instructions(self, skill_name: str) -> Optional[str]:
        """Level 1→2 展开：获取指定 Skill 的完整指令"""
        return skill_manager.get_skill_full_instructions(skill_name)

    def get_level3_references(self, skill_name: str) -> Dict[str, str]:
        """Level 2→3 展开：获取指定 Skill 的参考文档"""
        return skill_manager.get_skill_references(skill_name)

    def get_selected_skills_context(self, query: str, top_k: int = None, threshold: float = None) -> List[Dict[str, Any]]:
        """返回筛选后的 Level 1 规格（自然语言格式，用于 system prompt 注入）

        Returns:
            [
                {
                    "name": "web_search",
                    "description": "...",
                    "similarity": 0.85,
                    "category": "...",
                }
            ]
        """
        selected = self.select(query, top_k, threshold)
        return [
            {
                'name': s['skill_name'],
                'similarity': s['similarity'],
                **self._get_skill_spec(s['skill_name']),
            }
            for s in selected
        ]

    def _build_level1_spec(self, skill: Skill) -> Dict[str, Any]:
        """为单个 Skill 构建 OpenAI Tools 格式的 Level 1 规格

        function.name = skill.name（= 路径叶子名 = 注册表 key），
        确保 LLM 调用与注册表直接命中。
        """
        spec = skill.get_level1_spec()
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
                "name": skill.name,
                "description": spec['description'],
                "parameters": {
                    "type": "object",
                    "properties": properties,
                    "required": required,
                }
            },
            "category": spec.get('category', 'general'),
        }

    def _get_skill_spec(self, skill_name: str) -> Dict[str, Any]:
        skill = skill_manager.get_skill(skill_name)
        if not skill:
            return {}
        s = skill.get_level1_spec()
        return {
            'description': s.get('description', ''),
            'category': s.get('category', ''),
        }


_skill_selector: Optional[SkillSelector] = None


def get_skill_selector(
    top_k: int = 5,
    score_threshold: float = 0.01,
) -> SkillSelector:
    global _skill_selector
    if _skill_selector is None:
        _skill_selector = SkillSelector(top_k, score_threshold)
    return _skill_selector