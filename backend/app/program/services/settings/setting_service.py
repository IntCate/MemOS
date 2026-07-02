"""设置相关业务逻辑服务 - 使用基础设施层

业务服务（Business Service）：包含业务规则和业务流程
基础设施服务（Infrastructure Service）：提供通用能力，不包含业务逻辑

本服务依赖：
- DataInfrastructure: 数据基础设施（数据库访问）
"""
from app.program.services.base_service import BaseService
from app.utils import handle_db_errors
from app.infrastructure import DataInfrastructure


class SettingService(BaseService):
    """设置服务类，封装所有设置相关的业务逻辑"""
    
    def __init__(self):
        """初始化设置服务"""
        super().__init__()
        self.data_infra = DataInfrastructure()
    
    @handle_db_errors(default_return={})
    def get_settings(self):
        """获取所有设置"""
        settings = self.data_infra.get_settings()
        
        return settings
    
    @handle_db_errors(default_return=None)
    def get_setting(self, setting_key):
        """获取单个设置"""
        return self.data_infra.get_setting(setting_key)
    
    @handle_db_errors(default_return=False)
    def update_settings(self, settings):
        """更新设置"""
        for key, value in settings.items():
            self.data_infra.update_setting(key, value)
        
        return True
    
    @handle_db_errors(default_return=False)
    def reset_settings(self):
        """重置设置"""
        self.data_infra.delete_all_settings()
        
        return True