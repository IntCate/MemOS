"""SkillSelector — 基于语义相似度的技能自动筛选

在每次对话中，根据用户查询自动选择最相关的 Skills 注入 Prompt，
而不是将所有 Skills 全量加载。这是渐进式披露 Level 0 的核心筛选机制。

工作原理：
  1. 预计算所有 Skill 描述的 embedding 向量（启动时 + 热加载时更新）
  2. 收到用户查询时，计算 query embedding
  3. 通过 cosine_similarity 排序所有 Skill，取 top_k 个
  4. 低于 similarity_threshold 的技能被丢弃

集成方式：
  AI Subsystem → assemble_prompt 阶段调用 SkillSelector
  → 仅将筛选后的技能注入为 OpenAI Tools 格式
"""
import asyncio
import math
import os
from typing import Dict, List, Optional, Any

from app.core.logger import logger
from app.capabilities.skill.manager import skill_manager
from app.capabilities.skill.protocol import Skill


class SkillSelector:
    """基于语义相似度的技能筛选器

    使用 embedding 相似度对当前查询匹配最相关的 Skills。
    """

    def __init__(self, top_k: int = 5, similarity_threshold: float = 0.3):
        """
        Args:
            top_k: 最多返回的技能数
            similarity_threshold: cosine 相似度阈值（0~1），低于此值的技能被丢弃
        """
        self.top_k = top_k
        self.similarity_threshold = similarity_threshold
        self._skill_embeddings: Dict[str, List[float]] = {}  # {skill_name: embedding_vec}
        self._embedding_model: Any = None

    @property
    def _embedder(self):
        """延迟加载 embedding 模型"""
        if self._embedding_model is not None:
            return self._embedding_model

        # 尝试加载已配置的嵌入模型
        try:
            from app.knowledgebase.embeddings import get_embedding_model
            self._embedding_model = get_embedding_model()
            if self._embedding_model is not None:
                return self._embedding_model
        except Exception:
            pass

        # 尝试加载 sentence-transformers
        try:
            os.environ.setdefault('TF_CPP_MIN_LOG_LEVEL', '3')
            from sentence_transformers import SentenceTransformer
            self._embedding_model = SentenceTransformer(
                'sentence-transformers/all-MiniLM-L6-v2',
                device='cpu'
            )
            return self._embedding_model
        except Exception as e:
            logger.warning(f"[SkillSelector] 无法加载 embedding 模型: {e}，将使用关键词匹配回退")
            return None

    # ── Embedding 管理 ──

    def build_index(self) -> int:
        """为所有已注册 Skill 计算描述 embedding 并缓存

        Returns:
            成功索引的技能数量
        """
        skills = skill_manager.get_enabled_skills()
        if not skills:
            return 0

        embedder = self._embedder
        if embedder is None:
            logger.warning("[SkillSelector] 无 embedding 模型，跳过索引")
            return 0

        descriptions = [s.get_description() for s in skills.values()]
        names = list(skills.keys())

        try:
            if hasattr(embedder, 'embed_documents'):
                embeddings = embedder.embed_documents(descriptions)
            else:
                embeddings = embedder.encode(descriptions, convert_to_numpy=True).tolist()
        except Exception as e:
            logger.error(f"[SkillSelector] 计算 embeddings 失败: {e}")
            return 0

        self._skill_embeddings = {}
        for name, emb in zip(names, embeddings):
            self._skill_embeddings[name] = emb

        logger.info(f"[SkillSelector] 索引完成: {len(self._skill_embeddings)} 个 Skill")
        return len(self._skill_embeddings)

    def update_skill_embedding(self, skill_name: str) -> bool:
        """热加载时更新单个 Skill 的 embedding（增量）"""
        skill = skill_manager.get_skill(skill_name)
        if not skill:
            return False

        embedder = self._embedder
        if embedder is None:
            return False

        try:
            if hasattr(embedder, 'embed_documents'):
                emb = embedder.embed_documents([skill.get_description()])[0]
            else:
                emb = embedder.encode([skill.get_description()], convert_to_numpy=True).tolist()[0]
            self._skill_embeddings[skill_name] = emb
            return True
        except Exception:
            return False

    def remove_skill_embedding(self, skill_name: str):
        """热卸载时移除 Skill embedding"""
        self._skill_embeddings.pop(skill_name, None)

    # ── 相似度计算 ──

    @staticmethod
    def _cosine_similarity(vec_a: List[float], vec_b: List[float]) -> float:
        """计算两个向量的 cosine 相似度"""
        dot = sum(a * b for a, b in zip(vec_a, vec_b))
        norm_a = math.sqrt(sum(a * a for a in vec_a))
        norm_b = math.sqrt(sum(b * b for b in vec_b))
        if norm_a == 0 or norm_b == 0:
            return 0.0
        return dot / (norm_a * norm_b)

    def _rank_by_embedding(self, query: str) -> List[Dict[str, Any]]:
        """基于 embedding 相似度排序 Skills"""
        embedder = self._embedder

        # 计算 query embedding
        try:
            if hasattr(embedder, 'embed_query'):
                query_vec = embedder.embed_query(query)
            else:
                query_vec = embedder.encode([query], convert_to_numpy=True).tolist()[0]
        except Exception as e:
            logger.warning(f"[SkillSelector] query embedding 失败: {e}")
            return []

        # 计算每个 Skill 的相似度
        results = []
        for name, skill_vec in self._skill_embeddings.items():
            similarity = self._cosine_similarity(query_vec, skill_vec)
            results.append({
                'skill_name': name,
                'similarity': round(similarity, 4),
            })

        # 排序
        results.sort(key=lambda x: x['similarity'], reverse=True)
        return results

    def _rank_by_keyword(self, query: str) -> List[Dict[str, Any]]:
        """关键词匹配回退方案（无 embedding 模型时）
        
        对中文使用子串匹配（因为中文没有空格分词），对英文使用单词级匹配。
        """
        query_lower = query.lower()
        results = []

        for name, skill in skill_manager.get_enabled_skills().items():
            desc_lower = skill.get_description().lower()
            name_lower = name.lower()
            
            score = 0.0

            # 名称匹配：下划线分隔的单词/拼音
            for term in name_lower.replace('_', ' ').split():
                if len(term) >= 2 and term in query_lower:
                    score += 0.5

            # 描述匹配：空格/标点分隔
            desc_clean = desc_lower.replace('，', ' ').replace('、', ' ').replace('。', ' ')
            for term in desc_clean.split():
                if len(term) >= 2 and term in query_lower:
                    score += 0.3

            # 反向匹配：查询子串是否在描述中（中文字符级）
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

    # ── 公共 API ──

    def select(self, query: str, top_k: int = None, threshold: float = None) -> List[Dict[str, Any]]:
        """根据查询选择最相关的 Skills（Level 0 summaries）

        Args:
            query: 用户查询文本
            top_k: 最多返回几个（覆盖全局设置）
            threshold: 相似度阈值（覆盖全局设置）

        Returns:
            [
                {
                    "skill_name": "web_search",
                    "similarity": 0.85,
                    "level0_spec": { ... },   // OpenAI Tools 格式摘要
                }
            ]
        """
        k = top_k or self.top_k
        th = threshold or self.similarity_threshold

        if self._skill_embeddings and self._embedder is not None:
            ranked = self._rank_by_embedding(query)
        else:
            ranked = self._rank_by_keyword(query)

        # 筛选 + 取 top_k
        selected = []
        for item in ranked:
            if item['similarity'] < th:
                continue
            skill_name = item['skill_name']
            skill = skill_manager.get_skill(skill_name)
            if skill and skill.is_enabled():
                item['level0_spec'] = self._build_level0_spec(skill)
                selected.append(item)
            if len(selected) >= k:
                break

        return selected

    def get_level0_specs(self, query: str, top_k: int = None, threshold: float = None) -> List[Dict[str, Any]]:
        """便捷方法：直接返回 OpenAI Tools 格式的 Level 0 规格列表

        用于直接注入到 LLM 的 tools 参数。
        """
        selected = self.select(query, top_k, threshold)
        return [s['level0_spec'] for s in selected if 'level0_spec' in s]

    def get_level1_instructions(self, skill_name: str) -> Optional[str]:
        """Level 0→1 展开：获取指定 Skill 的完整指令"""
        return skill_manager.get_skill_full_instructions(skill_name)

    def get_level2_references(self, skill_name: str) -> Dict[str, str]:
        """Level 1→2 展开：获取指定 Skill 的参考文档"""
        return skill_manager.get_skill_references(skill_name)

    def get_selected_skills_context(self, query: str, top_k: int = None, threshold: float = None) -> List[Dict[str, Any]]:
        """返回筛选后的 Level 0 摘要（自然语言格式，用于 system prompt 注入）

        与 get_level0_specs 的区别：后者是 OpenAI function calling 格式，
        这个是自然语言描述，适合注入到 system prompt 的 "可用技能" 段落。

        Returns:
            [
                {
                    "name": "web_search",
                    "description": "...",
                    "similarity": 0.85,
                    "estimated_tokens": 150,
                }
            ]
        """
        selected = self.select(query, top_k, threshold)
        return [
            {
                'name': s['skill_name'],
                'similarity': s['similarity'],
                **self._get_skill_summary(s['skill_name']),
            }
            for s in selected
        ]

    def _build_level0_spec(self, skill: Skill) -> Dict[str, Any]:
        """为单个 Skill 构建 OpenAI Tools 格式的 Level 0 规格"""
        summary = skill.get_level0_summary()
        params = summary['parameters']
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
                "name": summary['name'],
                "description": summary['description'],
                "parameters": {
                    "type": "object",
                    "properties": properties,
                    "required": required,
                }
            },
            "estimated_tokens": summary.get('estimated_tokens', 0),
        }

    def _get_skill_summary(self, skill_name: str) -> Dict[str, Any]:
        skill = skill_manager.get_skill(skill_name)
        if not skill:
            return {}
        s = skill.get_level0_summary()
        return {
            'description': s.get('description', ''),
            'category': s.get('category', ''),
            'estimated_tokens': s.get('estimated_tokens', 0),
        }


# ── 全局单例 ──

_skill_selector: Optional[SkillSelector] = None


def get_skill_selector(
    top_k: int = 5,
    similarity_threshold: float = 0.3,
) -> SkillSelector:
    global _skill_selector
    if _skill_selector is None:
        _skill_selector = SkillSelector(top_k, similarity_threshold)
    return _skill_selector
