"""Prompt版本管理器：负责版本控制和A/B测试"""
import json
import os
import random
from typing import Dict, List, Optional, Any
from datetime import datetime
from .data_structures import PromptVersion, ABTestConfig, PromptEvaluation
from app.utils.path_manager import PathManager


class VersionManager:
    """Prompt版本管理器"""
    
    def __init__(self, version_dir: str = None):
        self.version_dir = version_dir or PathManager.get_prompt_version_dir()
        self.versions: Dict[str, List[PromptVersion]] = {}
        self.ab_tests: Dict[str, ABTestConfig] = {}
        self._ensure_version_dir()
        self._load_versions()
        self._load_ab_tests()
    
    def _ensure_version_dir(self):
        self.full_version_dir = PathManager.ensure_dir(self.version_dir)
    
    def _load_versions(self):
        if not os.path.exists(self.full_version_dir):
            return
        
        versions_file = os.path.join(self.full_version_dir, "versions.json")
        if os.path.exists(versions_file):
            try:
                with open(versions_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    for template_id, version_list in data.items():
                        self.versions[template_id] = [
                            PromptVersion(
                                template_id=v['template_id'],
                                version=v['version'],
                                content=v['content'],
                                created_at=datetime.fromisoformat(v['created_at']),
                                created_by=v.get('created_by', 'system'),
                                notes=v.get('notes', '')
                            ) for v in version_list
                        ]
            except Exception as e:
                print(f"加载版本文件失败: {e}")
    
    def _load_ab_tests(self):
        ab_test_file = os.path.join(self.full_version_dir, "ab_tests.json")
        if os.path.exists(ab_test_file):
            try:
                with open(ab_test_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    for template_id, ab_config in data.items():
                        self.ab_tests[template_id] = ABTestConfig(
                            template_id=template_id,
                            variants=ab_config['variants'],
                            weights=ab_config['weights'],
                            enabled=ab_config.get('enabled', True),
                            goal_metric=ab_config.get('goal_metric', 'quality'),
                            sample_size=ab_config.get('sample_size', 100)
                        )
            except Exception as e:
                print(f"加载A/B测试配置失败: {e}")
    
    def _save_versions(self):
        versions_file = os.path.join(self.full_version_dir, "versions.json")
        try:
            data = {}
            for template_id, version_list in self.versions.items():
                data[template_id] = [
                    {
                        'template_id': v.template_id,
                        'version': v.version,
                        'content': v.content,
                        'created_at': v.created_at.isoformat(),
                        'created_by': v.created_by,
                        'notes': v.notes
                    } for v in version_list
                ]
            
            with open(versions_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"保存版本文件失败: {e}")
    
    def _save_ab_tests(self):
        ab_test_file = os.path.join(self.full_version_dir, "ab_tests.json")
        try:
            data = {}
            for template_id, ab_config in self.ab_tests.items():
                data[template_id] = {
                    'variants': ab_config.variants,
                    'weights': ab_config.weights,
                    'enabled': ab_config.enabled,
                    'goal_metric': ab_config.goal_metric,
                    'sample_size': ab_config.sample_size
                }
            
            with open(ab_test_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"保存A/B测试配置失败: {e}")
    
    def create_version(self, template_id: str, content: str, created_by: str = "system", notes: str = "") -> str:
        if template_id not in self.versions:
            self.versions[template_id] = []
        
        existing_versions = [v.version for v in self.versions[template_id]]
        new_version = self._generate_next_version(existing_versions)
        
        version = PromptVersion(
            template_id=template_id,
            version=new_version,
            content=content,
            created_by=created_by,
            notes=notes
        )
        
        self.versions[template_id].append(version)
        self._save_versions()
        
        return new_version
    
    def _generate_next_version(self, existing_versions: List[str]) -> str:
        if not existing_versions:
            return "1.0.0"
        
        max_major, max_minor, max_patch = 0, 0, 0
        for v in existing_versions:
            parts = v.split('.')
            if len(parts) >= 3:
                try:
                    major, minor, patch = int(parts[0]), int(parts[1]), int(parts[2])
                    if major > max_major:
                        max_major, max_minor, max_patch = major, minor, patch
                    elif major == max_major and minor > max_minor:
                        max_minor, max_patch = minor, patch
                    elif major == max_major and minor == max_minor and patch >= max_patch:
                        max_patch = patch
                except ValueError:
                    continue
        
        return f"{max_major}.{max_minor}.{max_patch + 1}"
    
    def get_version(self, template_id: str, version: str) -> Optional[PromptVersion]:
        versions = self.versions.get(template_id, [])
        for v in versions:
            if v.version == version:
                return v
        return None
    
    def get_latest_version(self, template_id: str) -> Optional[PromptVersion]:
        versions = self.versions.get(template_id, [])
        if not versions:
            return None
        
        return versions[-1]
    
    def list_versions(self, template_id: str) -> List[PromptVersion]:
        return self.versions.get(template_id, [])
    
    def rollback(self, template_id: str, version: str) -> bool:
        version_obj = self.get_version(template_id, version)
        if version_obj:
            new_version = self.create_version(
                template_id,
                version_obj.content,
                created_by="rollback",
                notes=f"回滚到版本 {version}"
            )
            return True
        return False
    
    def create_ab_test(self, template_id: str, variants: List[str], weights: List[float], **kwargs) -> bool:
        if len(variants) != len(weights):
            return False
        
        if sum(weights) != 1.0:
            return False
        
        ab_config = ABTestConfig(
            template_id=template_id,
            variants=variants,
            weights=weights,
            **kwargs
        )
        
        self.ab_tests[template_id] = ab_config
        self._save_ab_tests()
        return True
    
    def get_ab_test(self, template_id: str) -> Optional[ABTestConfig]:
        return self.ab_tests.get(template_id)
    
    def select_variant(self, template_id: str) -> Optional[str]:
        ab_test = self.ab_tests.get(template_id)
        if not ab_test or not ab_test.enabled:
            return None
        
        return random.choices(ab_test.variants, weights=ab_test.weights)[0]
    
    def disable_ab_test(self, template_id: str) -> bool:
        if template_id in self.ab_tests:
            self.ab_tests[template_id].enabled = False
            self._save_ab_tests()
            return True
        return False
    
    def add_evaluation(self, template_id: str, version: str, score: float, **kwargs) -> bool:
        evaluation_file = os.path.join(self.full_version_dir, f"{template_id}_evaluations.json")
        evaluations = []
        
        if os.path.exists(evaluation_file):
            try:
                with open(evaluation_file, 'r', encoding='utf-8') as f:
                    evaluations = json.load(f)
            except Exception:
                evaluations = []
        
        evaluation = {
            'template_id': template_id,
            'version': version,
            'score': score,
            'criteria': kwargs.get('criteria', {}),
            'feedback': kwargs.get('feedback', ''),
            'evaluated_at': datetime.now().isoformat()
        }
        
        evaluations.append(evaluation)
        
        try:
            with open(evaluation_file, 'w', encoding='utf-8') as f:
                json.dump(evaluations, f, ensure_ascii=False, indent=2)
            return True
        except Exception:
            return False