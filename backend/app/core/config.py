"""应用配置管理"""
import os

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

DEFAULT_VECTOR_TOP_K = 3
DEFAULT_VECTOR_SCORE_THRESHOLD = 0.7
DEFAULT_LLM_TOP_K = 50

# 默认配置
DEFAULT_CONFIG = {
    'vector': {
        'retrieval_mode': 'vector',
        'top_k': DEFAULT_VECTOR_TOP_K,
        'score_threshold': DEFAULT_VECTOR_SCORE_THRESHOLD,
        'vector_db_path': None,
        'embedder_model': None,
        'chunk_size': 1000,
        'chunk_overlap': 200
    },
    'llm': {
        'top_k': DEFAULT_LLM_TOP_K
    },
    'mcp': {
        'enabled': False,
        'server_address': '',
        'server_port': 8080,
        'timeout': 30
    },
    'notification': {
        'enabled': True,
        'newMessage': True,
        'sound': True,
        'system': True,
        'displayTime': '5秒'
    },
    'app': {
        'debug': True,
        'host': '0.0.0.0',
        'port': 5000
    }
}

class ConfigManager:
    """配置管理器"""
    _instance = None
    _config = None
    
    @classmethod
    def get_instance(cls):
        """获取单例实例"""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance
    
    def __init__(self):
        """初始化配置管理器"""
        if ConfigManager._instance is not None:
            raise Exception("配置管理器是单例模式，请使用get_instance()方法获取实例")
        ConfigManager._instance = self
        self.load_config()
    
    def load_config(self):
        """加载配置"""
        self._config = DEFAULT_CONFIG.copy()
        self._ensure_directories()
        
    def _ensure_directories(self):
        """确保应用所需的目录结构存在，与配置加载解耦"""
        user_data_dir = self.get_user_data_dir()
        directories = [
            os.path.join(user_data_dir, 'config'),
            os.path.join(user_data_dir, 'models', 'embedding'),
            os.path.join(user_data_dir, 'Retrieval-Augmented Generation', 'files'),
            os.path.join(user_data_dir, 'Retrieval-Augmented Generation', 'vector_db'),
        ]
        for d in directories:
            os.makedirs(d, exist_ok=True)
        
    def get_user_data_dir(self):
        """获取用户数据目录"""
        user_data_dir = os.path.join(PROJECT_ROOT, 'data')
        os.makedirs(user_data_dir, exist_ok=True)
        return user_data_dir
    
    def get(self, key_path, default=None):
        """获取配置值，支持点号分隔的路径"""
        keys = key_path.split('.')
        value = self._config
        
        for key in keys:
            if isinstance(value, dict) and key in value:
                value = value[key]
            else:
                return default
        
        return value
    
    def set(self, key_path, value):
        """设置配置值"""
        keys = key_path.split('.')
        config = self._config
        
        # 导航到最后一个键的父级
        for key in keys[:-1]:
            if key not in config or not isinstance(config[key], dict):
                config[key] = {}
            config = config[key]
        
        # 设置值
        config[keys[-1]] = value
        return True
    
    
    def validate_vector_config(self) -> tuple[bool, list[str]]:
        """验证向量系统配置
        
        Returns:
            tuple[bool, list[str]]: (是否验证通过, 错误信息列表)
        """
        errors = []
        
        # 检查向量数据库路径
        vector_db_path = self.get('vector.vector_db_path')
        if not vector_db_path:
            errors.append("缺少 vector.vector_db_path 配置")
        
        # 检查嵌入模型
        embedder_model = self.get('vector.embedder_model')
        if not embedder_model:
            errors.append("缺少 vector.embedder_model 配置")
        
        return len(errors) == 0, errors

# 创建全局配置实例
config_manager = ConfigManager.get_instance()