"""Prompt引擎：Prompt工程的统一入口"""
from typing import Dict, List, Optional, Any
from .data_structures import (
    PromptTemplate, PromptType, PromptMode, PromptRenderResult,
    PromptVariable
)
from .template_engine import TemplateEngine
from .version_manager import VersionManager


class PromptEngine:
    """Prompt引擎 - Prompt工程的统一入口"""
    
    def __init__(self, config: Dict[str, Any] = None):
        self.config = config or {}
        self.template_engine = TemplateEngine(self.config.get('template_dir'))
        self.version_manager = VersionManager(self.config.get('version_dir'))
        self._initialize_default_templates()
    
    def _initialize_default_templates(self):
        if not self.template_engine.templates:
            default_templates = [
                PromptTemplate(
                    id="system_agent",
                    name="智能体系统提示词",
                    type=PromptType.SYSTEM,
                    mode=PromptMode.AGENT,
                    content="你是MemOS，一个强大的AI智能体助手。你的任务是分析用户问题，制定执行计划，并在需要时调用工具来获取信息或执行操作，最终为用户提供准确、详细、友好的回答。\n\n你的工作流程（ReAct模式）：\n1. 思考：分析用户问题，判断是否需要调用工具或参考历史信息\n2. 行动：如果需要，调用合适的工具获取信息\n3. 观察：分析工具返回的结果和历史信息\n4. 回答：基于所有信息给出最终回答\n\n记忆使用规则：\n- 你拥有长期记忆能力，可以记住用户的偏好、背景信息和历史对话内容\n- 在回答时，请结合记忆中的信息提供个性化的服务\n- 如果用户提到之前讨论过的话题，请参考记忆内容给出连贯的回答\n- 记忆信息会在用户消息中提供，请注意查看\n\n重要规则：\n1. 始终用中文回答用户\n2. 只有在需要时才调用工具，简单问题可以直接回答\n3. 工具调用完成后，必须基于结果给出自然语言回答\n4. 如果工具调用失败，尝试其他方法或告知用户\n5. 不要捏造信息，如果不知道答案就说不知道\n6. 保持回答简洁明了，避免重复",
                    variables=[],
                    description="统一的智能体系统提示词，工具列表通过API tools参数传递",
                    tags=["agent", "default"]
                ),
                PromptTemplate(
                    id="user_chat",
                    name="聊天用户提示词",
                    type=PromptType.USER,
                    mode=PromptMode.CHAT,
                    content="{{query}}",
                    variables=[
                        PromptVariable(
                            name="query",
                            description="用户查询内容",
                            required=True
                        )
                    ],
                    description="标准聊天模式的用户提示词模板",
                    tags=["chat", "user"]
                )
            ]
            
            for template in default_templates:
                self.template_engine.save_template(template)
    
    def render(self, template_id: str, **kwargs) -> PromptRenderResult:
        return self.template_engine.render(template_id, **kwargs)
    
    def render_by_mode(self, mode: PromptMode, **kwargs) -> PromptRenderResult:
        templates = self.template_engine.get_templates_by_mode(mode)
        if not templates:
            return PromptRenderResult(
                success=False,
                error=f"未找到 {mode.value} 模式的模板"
            )
        
        template = templates[0]
        return self.template_engine.render_template(template, **kwargs)
    
    def get_template(self, template_id: str) -> Optional[PromptTemplate]:
        return self.template_engine.get_template(template_id)
    
    def get_templates(self) -> List[PromptTemplate]:
        return list(self.template_engine.templates.values())
    
    def save_template(self, template: PromptTemplate) -> bool:
        success = self.template_engine.save_template(template)
        if success:
            self.version_manager.create_version(
                template.id,
                template.content,
                notes=f"模板 {template.name} 更新"
            )
        return success
    
    def create_template(self, **kwargs) -> PromptTemplate:
        template = self.template_engine.create_template(**kwargs)
        self.template_engine.save_template(template)
        self.version_manager.create_version(
            template.id,
            template.content,
            notes=f"创建模板 {template.name}"
        )
        return template
    
    def create_ab_test(self, template_id: str, variants: List[str], weights: List[float], **kwargs) -> bool:
        return self.version_manager.create_ab_test(template_id, variants, weights, **kwargs)
    
    def select_variant(self, template_id: str) -> Optional[str]:
        return self.version_manager.select_variant(template_id)
    
    def get_latest_version(self, template_id: str):
        return self.version_manager.get_latest_version(template_id)
    
    def build_messages(self, query: str, **kwargs) -> List[Dict[str, str]]:
        messages = []
        
        system_template = self.template_engine.get_template("system_agent")
        if system_template:
            system_result = self.template_engine.render_template(system_template, **kwargs)
            if system_result.success:
                messages.append({
                    'role': 'system',
                    'content': system_result.content
                })
        
        chat_history = kwargs.get('chat_history', [])
        if chat_history:
            messages.extend(chat_history)
        
        context_messages = self._build_context_messages(query=query, **kwargs)
        messages.extend(context_messages)
        
        user_template = self.template_engine.get_template("user_chat")
        if user_template:
            user_result = self.template_engine.render_template(user_template, query=query)
            if user_result.success:
                messages.append({
                    'role': 'user',
                    'content': user_result.content
                })
        
        return messages
    
    def _build_context_messages(self, query: str = '', **kwargs) -> List[Dict[str, str]]:
        context_messages = []
        
        # ── Level 0: 相似度筛选后的技能摘要 ──
        skill_ctx = self._build_skill_context(query)
        if skill_ctx:
            context_messages.append({
                'role': 'user',
                'content': skill_ctx,
            })
        
        rag_context = kwargs.get('context') or kwargs.get('rag_context')
        if rag_context:
            context_messages.append({
                'role': 'user',
                'content': f"【参考文档】\n{rag_context}"
            })
        
        web_search_results = kwargs.get('search_results') or kwargs.get('web_search_results')
        if web_search_results:
            context_messages.append({
                'role': 'user',
                'content': f"【网络搜索结果】\n{web_search_results}"
            })
        
        return context_messages
    
    def _build_skill_context(self, query: str) -> str:
        """Level 0 渐进式披露：根据查询语义选择最相关的技能，仅注入摘要
        
        Returns:
            格式化的技能摘要文本，或空字符串
        """
        if not query:
            return ''
        
        try:
            from app.core.service_container import service_container
            selector = service_container.get_service('skill_selector')
            selected = selector.get_selected_skills_context(query)
            
            if not selected:
                return ''
            
            lines = ['【可用技能】以下技能可能对当前任务有帮助：']
            for i, s in enumerate(selected, 1):
                lines.append(
                    f"{i}. **{s['name']}** [{s.get('category', 'general')}] "
                    f"— {s['description']}"
                )
            return '\n'.join(lines)
        except Exception:
            return ''