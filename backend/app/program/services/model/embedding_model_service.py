"""嵌入模型相关业务逻辑服务 - 使用基础设施层

业务服务（Business Service）：包含业务规则和业务流程
基础设施服务（Infrastructure Service）：提供通用能力，不包含业务逻辑

本服务依赖：
- DataInfrastructure: 数据基础设施（数据库访问）
- EmbeddingModelManager: AI工程层嵌入模型管理器
"""
import threading
from typing import List, Optional, Dict, Any
from app.program.services.base_service import BaseService
from app.engineering.llm.managers.embedding_model_manager import EmbeddingModelManager
from app.infrastructure import DataInfrastructure


class EmbeddingModelService(BaseService):
    """嵌入模型服务类，管理嵌入模型的业务逻辑"""
    
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls):
        """单例模式实现"""
        with cls._lock:
            if cls._instance is None:
                cls._instance = super(EmbeddingModelService, cls).__new__(cls)
                cls._instance.__init__()
        return cls._instance
    
    def __init__(self):
        """初始化嵌入模型服务"""
        if hasattr(self, '_initialized') and self._initialized:
            return
        
        super().__init__()
        self._initialized = False
        self.embedding_model_manager = EmbeddingModelManager()
        self.data_infra = DataInfrastructure()
        self._initialized = True
        self.log_info("嵌入模型服务初始化成功")
    
    def initialize_models(self) -> List[Dict[str, Any]]:
        """初始化嵌入模型，创建默认的模型提供商"""
        try:
            self.log_info("嵌入模型初始化完成")
            return []
        except Exception as e:
            self.log_error(f"初始化嵌入模型失败: {str(e)}", exc_info=True)
            return []
    
    def get_all_models(self, enabled_only: bool = False) -> List[Dict[str, Any]]:
        """获取所有嵌入模型"""
        try:
            models = self.data_infra.get_embedding_models(enabled_only)
            
            model_list = []
            for model in models:
                versions = self.data_infra.get_embedding_model_versions(model.id)
                model_list.append({
                'id': model.id,
                'name': model.name,
                'description': model.description,
                'type': model.type,
                'configured': model.configured,
                'versions': [
                    {
                        'id': version.id,
                        'version_name': version.version_name,
                        'custom_name': version.custom_name,
                        'api_key': version.api_key,
                        'api_base_url': version.api_base_url,
                        'model_path': version.model_path,
                        'dimension': version.dimension,
                        'enabled': version.enabled
                    }
                    for version in versions
                ]
            })
            
            return model_list
        except Exception as e:
            self.log_error(f"获取嵌入模型列表失败: {str(e)}", exc_info=True)
            return []
    
    def get_model_by_name(self, model_name: str) -> Optional[Dict[str, Any]]:
        """根据名称获取嵌入模型"""
        try:
            model = self.data_infra.get_embedding_model_by_name(model_name)
            
            if not model:
                return None
            
            versions = self.data_infra.get_embedding_model_versions(model.id)
            return {
                'id': model.id,
                'name': model.name,
                'description': model.description,
                'type': model.type,
                'configured': model.configured,
                'versions': [
                    {
                        'id': version.id,
                        'version_name': version.version_name,
                        'custom_name': version.custom_name,
                        'api_key': version.api_key,
                        'api_base_url': version.api_base_url,
                        'model_path': version.model_path,
                        'dimension': version.dimension,
                        'enabled': version.enabled
                    }
                    for version in versions
                ]
            }
        except Exception as e:
            self.log_error(f"获取嵌入模型失败: {str(e)}", exc_info=True)
            return None
    
    def get_configured_models(self) -> List[Dict[str, Any]]:
        """获取已配置的嵌入模型"""
        try:
            return self.data_infra.get_configured_embedding_models()
        except Exception as e:
            self.log_error(f"获取已配置嵌入模型失败: {str(e)}", exc_info=True)
            return []
    
    def configure_model(self, model_name: str, version_name: str, config: Dict[str, Any]) -> bool:
        """配置嵌入模型"""
        try:
            return self.data_infra.configure_embedding_model(model_name, version_name, config)
        except Exception as e:
            self.log_error(f"配置嵌入模型失败: {str(e)}", exc_info=True)
            return False
    
    def add_custom_model(self, model_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """添加自定义嵌入模型"""
        try:
            return self.data_infra.create_embedding_model(model_data)
        except Exception as e:
            self.log_error(f"添加自定义嵌入模型失败: {str(e)}", exc_info=True)
            return None
    
    def delete_model(self, model_name: str) -> bool:
        """删除嵌入模型"""
        try:
            return self.data_infra.delete_embedding_model(model_name)
        except Exception as e:
            self.log_error(f"删除嵌入模型失败: {str(e)}", exc_info=True)
            return False