"""模型相关业务逻辑服务 - 使用基础设施层

业务服务（Business Service）：包含业务规则和业务流程
基础设施服务（Infrastructure Service）：提供通用能力，不包含业务逻辑

本服务依赖：
- DataInfrastructure: 数据基础设施（数据库访问）
"""
from app.program.services.base_service import BaseService
from app.utils import handle_db_errors
from app.infrastructure import DataInfrastructure


class ModelService(BaseService):
    """模型服务类，封装所有模型相关的业务逻辑"""
    
    def __init__(self):
        """初始化模型服务"""
        super().__init__()
        self.data_infra = DataInfrastructure()
    
    @handle_db_errors(default_return=[])
    def get_models(self):
        """获取所有模型"""
        models = self.data_infra.get_models()
        
        return models
    
    def add_model(self, model_data):
        """添加模型"""
        try:
            model = self.data_infra.create_model(
                model_name=model_data.get('name'),
                api_key=model_data.get('apiKey', ''),
                base_url=model_data.get('baseUrl', ''),
                provider=model_data.get('provider', ''),
                context_window=model_data.get('contextWindow', 4096),
                description=model_data.get('description', '')
            )
            
            return model
        except Exception as e:
            self.log_error(f"添加模型失败: {str(e)}")
            return None
    
    def update_model(self, model_name, model_data):
        """更新模型"""
        try:
            model = self.data_infra.get_model_by_name(model_name)
            if not model:
                return None
            
            self.data_infra.update_model(
                model_name=model_name,
                api_key=model_data.get('apiKey'),
                base_url=model_data.get('baseUrl'),
                context_window=model_data.get('contextWindow'),
                description=model_data.get('description')
            )
            
            return model_data
        except Exception as e:
            self.log_error(f"更新模型失败: {str(e)}")
            return None
    
    @handle_db_errors(default_return=False)
    def delete_model(self, model_name):
        """删除模型"""
        return self.data_infra.delete_model(model_name)