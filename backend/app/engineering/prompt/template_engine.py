"""Prompt模板引擎：负责模板加载、渲染和验证"""
import re
import json
import os
from typing import Dict, List, Optional, Any
from datetime import datetime
from .data_structures import (
    PromptTemplate, PromptVariable, PromptType, PromptMode,
    PromptRenderResult
)
from app.utils.path_manager import PathManager


class TemplateEngine:
    """Prompt模板引擎"""
    
    def __init__(self, template_dir: str = None):
        self.template_dir = template_dir or PathManager.get_prompt_template_dir()
        self.templates: Dict[str, PromptTemplate] = {}
        self._ensure_template_dir()
        self._load_templates()
    
    def _ensure_template_dir(self):
        self.full_template_dir = PathManager.ensure_dir(self.template_dir)
    
    def _load_templates(self):
        if not os.path.exists(self.full_template_dir):
            return
        
        for filename in os.listdir(self.full_template_dir):
            if filename.endswith('.json'):
                template_path = os.path.join(self.full_template_dir, filename)
                try:
                    with open(template_path, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                        template = self._deserialize_template(data)
                        self.templates[template.id] = template
                except Exception as e:
                    print(f"加载模板失败 {filename}: {e}")
    
    def _deserialize_template(self, data: Dict[str, Any]) -> PromptTemplate:
        variables = []
        for var_data in data.get('variables', []):
            variables.append(PromptVariable(
                name=var_data['name'],
                description=var_data.get('description', ''),
                required=var_data.get('required', False),
                default=var_data.get('default'),
                type=var_data.get('type', 'string')
            ))
        
        return PromptTemplate(
            id=data['id'],
            name=data['name'],
            type=PromptType(data['type']),
            mode=PromptMode(data['mode']),
            content=data['content'],
            variables=variables,
            description=data.get('description', ''),
            version=data.get('version', '1.0.0'),
            tags=data.get('tags', []),
            is_active=data.get('is_active', True)
        )
    
    def _serialize_template(self, template: PromptTemplate) -> Dict[str, Any]:
        variables_data = []
        for var in template.variables:
            variables_data.append({
                'name': var.name,
                'description': var.description,
                'required': var.required,
                'default': var.default,
                'type': var.type
            })
        
        return {
            'id': template.id,
            'name': template.name,
            'type': template.type.value,
            'mode': template.mode.value,
            'content': template.content,
            'variables': variables_data,
            'description': template.description,
            'version': template.version,
            'tags': template.tags,
            'is_active': template.is_active
        }
    
    def save_template(self, template: PromptTemplate) -> bool:
        try:
            filename = f"{template.id}.json"
            filepath = os.path.join(self.full_template_dir, filename)
            
            data = self._serialize_template(template)
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            
            self.templates[template.id] = template
            return True
        except Exception as e:
            print(f"保存模板失败 {template.id}: {e}")
            return False
    
    def get_template(self, template_id: str) -> Optional[PromptTemplate]:
        return self.templates.get(template_id)
    
    def get_templates_by_mode(self, mode: PromptMode) -> List[PromptTemplate]:
        return [t for t in self.templates.values() if t.mode == mode and t.is_active]
    
    def get_templates_by_type(self, template_type: PromptType) -> List[PromptTemplate]:
        return [t for t in self.templates.values() if t.type == template_type and t.is_active]
    
    def render(self, template_id: str, **kwargs) -> PromptRenderResult:
        template = self.templates.get(template_id)
        if not template:
            return PromptRenderResult(
                success=False,
                error=f"模板不存在: {template_id}"
            )
        
        return self.render_template(template, **kwargs)
    
    def render_template(self, template: PromptTemplate, **kwargs) -> PromptRenderResult:
        try:
            content = template.content
            used_variables = []
            missing_variables = []
            
            for var in template.variables:
                if var.name in kwargs:
                    value = kwargs[var.name]
                    content = content.replace(f"{{{{{var.name}}}}}", str(value))
                    used_variables.append(var.name)
                elif var.required:
                    missing_variables.append(var.name)
                elif var.default is not None:
                    content = content.replace(f"{{{{{var.name}}}}}", str(var.default))
                    used_variables.append(var.name)
            
            if missing_variables:
                return PromptRenderResult(
                    success=False,
                    content=content,
                    template_id=template.id,
                    version=template.version,
                    used_variables=used_variables,
                    missing_variables=missing_variables,
                    error=f"缺少必需变量: {', '.join(missing_variables)}"
                )
            
            return PromptRenderResult(
                success=True,
                content=content,
                template_id=template.id,
                version=template.version,
                used_variables=used_variables
            )
        except Exception as e:
            return PromptRenderResult(
                success=False,
                error=f"渲染模板失败: {e}"
            )
    
    def validate_template(self, template: PromptTemplate) -> List[str]:
        errors = []
        
        if not template.id:
            errors.append("模板ID不能为空")
        
        if not template.name:
            errors.append("模板名称不能为空")
        
        if not template.content:
            errors.append("模板内容不能为空")
        
        for var in template.variables:
            if not var.name:
                errors.append("变量名称不能为空")
        
        return errors
    
    def extract_variables(self, content: str) -> List[str]:
        pattern = r"\{\{(\w+)\}\}"
        matches = re.findall(pattern, content)
        return list(set(matches))
    
    def create_template(self, **kwargs) -> PromptTemplate:
        template = PromptTemplate(
            id=kwargs.get('id', ''),
            name=kwargs.get('name', ''),
            type=kwargs.get('type', PromptType.SYSTEM),
            mode=kwargs.get('mode', PromptMode.CHAT),
            content=kwargs.get('content', ''),
            variables=kwargs.get('variables', []),
            description=kwargs.get('description', ''),
            version=kwargs.get('version', '1.0.0'),
            tags=kwargs.get('tags', [])
        )
        
        if not template.id:
            template.id = self._generate_id(template.name)
        
        return template
    
    def _generate_id(self, name: str) -> str:
        return re.sub(r'[^a-zA-Z0-9]', '_', name.lower()).strip('_')