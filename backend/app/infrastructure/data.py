"""数据基础设施服务 - 封装所有数据库访问操作

这是基础设施服务，不包含业务逻辑，仅提供数据访问能力。
业务服务应通过此服务访问数据库，而不是直接使用 Repository。
"""
from typing import Dict, Any, Optional, List

from app.program.repositories.chat_repository import ChatRepository
from app.program.repositories.model_repository import ModelRepository
from app.program.repositories.setting_repository import SettingRepository
from app.program.repositories.embedding_model_repository import EmbeddingModelRepository
from app.program.repositories.document_repository import DocumentRepository
from app.program.repositories.folder_repository import FolderRepository
from app.core.database import get_db
from app.utils.data.converters import convert_model_to_dict, convert_models_to_list


class DataInfrastructure:
    """数据基础设施服务"""
    
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        
        self.db_session = next(get_db())
        self.chat_repo = ChatRepository(self.db_session)
        self.model_repo = ModelRepository(self.db_session)
        self.setting_repo = SettingRepository(self.db_session)
        self.embedding_model_repo = EmbeddingModelRepository(self.db_session)
        self.document_repo = DocumentRepository()
        self.folder_repo = FolderRepository()
        
        self._initialized = True
    
    # === Chat Operations ===
    def get_chats(self) -> List[Dict[str, Any]]:
        """获取所有对话"""
        chats = self.chat_repo.get_all_chats()
        chats.sort(key=lambda x: (not x.get('pinned', False), x.get('updatedAt', '')), reverse=True)
        return chats
    
    def get_chat_by_id(self, chat_id: str) -> Optional[Dict[str, Any]]:
        """根据ID获取对话"""
        return self.chat_repo.get_chat_by_id(chat_id)
    
    def create_chat(self, chat_id: str, title: str, preview: str = '', 
                    created_at: str = '', updated_at: str = ''):
        """创建对话"""
        self.chat_repo.create_chat(
            chat_id=chat_id,
            title=title,
            preview=preview,
            created_at=created_at,
            updated_at=updated_at
        )
    
    def update_chat(self, chat_id: str, title: str = None, preview: str = None, 
                    updated_at: str = None, pinned: int = None):
        """更新对话"""
        self.chat_repo.update_chat(
            chat_id=chat_id,
            title=title,
            preview=preview,
            updated_at=updated_at,
            pinned=pinned
        )
    
    def delete_chat(self, chat_id: str) -> bool:
        """删除对话"""
        return self.chat_repo.delete_chat(chat_id)
    
    def delete_all_chats(self) -> bool:
        """删除所有对话"""
        return self.chat_repo.delete_all_chats()
    
    # === Model Operations ===
    def get_all_models(self) -> List[Dict[str, Any]]:
        """获取所有模型"""
        db_models = self.model_repo.get_all_models()
        return convert_models_to_list(db_models, self.model_repo)
    
    def get_model_by_name(self, model_name: str) -> Optional[Dict[str, Any]]:
        """根据名称获取模型"""
        db_model = self.model_repo.get_model_by_name(model_name)
        if db_model:
            versions = self.model_repo.get_model_versions(db_model.id)
            return convert_model_to_dict(db_model, versions)
        return None
    
    def update_model(self, name: str, description: str = None, configured: bool = None,
                     icon_url: str = None, icon_blob: bytes = None):
        """更新模型"""
        self.model_repo.update_model(
            name=name,
            description=description,
            configured=configured,
            icon_url=icon_url,
            icon_blob=icon_blob
        )
    
    # === Setting Operations ===
    def get_system_setting(self) -> Optional[Dict[str, Any]]:
        """获取系统设置"""
        system_setting = self.setting_repo.get_system_setting()
        if system_setting:
            return {
                'darkMode': system_setting.dark_mode,
                'streamingEnabled': system_setting.streaming_enabled,
                'chatStyle': system_setting.chat_style,
                'viewMode': system_setting.view_mode,
                'vector_db_path': system_setting.vector_db_path,
                'default_top_k': system_setting.default_top_k,
                'default_score_threshold': system_setting.default_score_threshold,
                'newMessage': system_setting.new_message,
                'sound': system_setting.sound,
                'system': system_setting.system,
                'displayTime': system_setting.display_time
            }
        return None
    
    def create_or_update_system_setting(self, settings: Dict[str, Any]):
        """创建或更新系统设置"""
        system_db_data = {
            'dark_mode': settings.get('darkMode', False),
            'streaming_enabled': settings.get('streamingEnabled', True),
            'chat_style': settings.get('chatStyle', 'bubble'),
            'view_mode': settings.get('viewMode', 'grid'),
            'vector_db_path': settings.get('vector_db_path', ''),
            'default_top_k': settings.get('default_top_k', 3),
            'default_score_threshold': settings.get('default_score_threshold', 0.5),
            'new_message': settings.get('newMessage', True),
            'sound': settings.get('sound', False),
            'system': settings.get('system', True),
            'display_time': settings.get('displayTime', '5秒')
        }
        self.setting_repo.create_or_update_system_setting(system_db_data)
    
    # === Embedding Model Operations ===
    def get_all_embedding_models(self, enabled_only: bool = False) -> List[Any]:
        """获取所有嵌入模型"""
        return self.embedding_model_repo.get_all_models(enabled_only)
    
    def get_embedding_model_by_name(self, model_name: str) -> Optional[Any]:
        """根据名称获取嵌入模型"""
        return self.embedding_model_repo.get_model_by_name(model_name)
    
    def get_embedding_model_by_id(self, model_id: int) -> Optional[Any]:
        """根据ID获取嵌入模型"""
        return self.embedding_model_repo.get_model_by_id(model_id)
    
    def create_embedding_model(self, model_data: Dict[str, Any]) -> Any:
        """创建嵌入模型"""
        return self.embedding_model_repo.create_model(model_data)
    
    def update_embedding_model(self, model_id: int, model_data: Dict[str, Any]) -> bool:
        """更新嵌入模型"""
        return self.embedding_model_repo.update_model(model_id, model_data)
    
    def delete_embedding_model(self, model_id: int) -> bool:
        """删除嵌入模型"""
        return self.embedding_model_repo.delete_model(model_id)
    
    def get_default_embedding_model(self) -> Optional[Any]:
        """获取默认嵌入模型"""
        return self.embedding_model_repo.get_default_model()
    
    # === Folder Operations ===
    def get_all_folders(self) -> List[Any]:
        """获取所有文件夹"""
        return self.folder_repo.get_all_folders()
    
    def get_folder_by_id(self, folder_id: str) -> Optional[Any]:
        """根据ID获取文件夹"""
        return self.folder_repo.get_folder_by_id(folder_id)
    
    def get_folder_by_name(self, folder_name: str) -> Optional[Any]:
        """根据名称获取文件夹"""
        return self.folder_repo.get_folder_by_name(folder_name)
    
    def create_folder(self, folder_id: str, name: str, created_at: str, **kwargs) -> Any:
        """创建文件夹"""
        return self.folder_repo.create_folder(folder_id, name, created_at, **kwargs)
    
    def delete_folder(self, folder_id: str) -> bool:
        """删除文件夹"""
        return self.folder_repo.delete_folder(folder_id)
    
    def delete_all_folders(self) -> bool:
        """删除所有文件夹"""
        return self.folder_repo.delete_all_folders()
    
    # === Document Operations ===
    def get_all_documents(self) -> List[Any]:
        """获取所有文档"""
        return self.document_repo.get_all_documents()
    
    def get_documents_by_folder_id(self, folder_id: str) -> List[Any]:
        """根据文件夹ID获取文档"""
        return self.document_repo.get_documents_by_folder_id(folder_id)
    
    def get_document_by_name(self, name: str) -> Optional[Any]:
        """根据名称获取文档"""
        return self.document_repo.get_document_by_name(name)
    
    def create_document(self, document_id: str, name: str, path: str, size: int, 
                        doc_type: str, uploaded_at: str, folder_id: str, **kwargs) -> Any:
        """创建文档"""
        return self.document_repo.create_document(document_id, name, path, size, 
                                                  doc_type, uploaded_at, folder_id, **kwargs)
    
    def delete_document(self, document_id: str) -> bool:
        """删除文档"""
        return self.document_repo.delete_document(document_id)
    
    def delete_all_documents(self) -> bool:
        """删除所有文档"""
        return self.document_repo.delete_all_documents()
    
    def get_document_by_id(self, document_id: str) -> Optional[Any]:
        """根据ID获取文档"""
        return self.document_repo.get_document_by_id(document_id)
    
    def update_document_folder(self, document_id: str, folder_id: str) -> bool:
        """更新文档所属文件夹"""
        return self.document_repo.update_document_folder(document_id, folder_id)
    
    # === Embedding Model Operations ===
    def get_embedding_models(self, enabled_only: bool = False) -> List[Any]:
        """获取所有嵌入模型"""
        return self.embedding_model_repo.get_all_models(enabled_only)
    
    def get_embedding_model_by_name(self, model_name: str) -> Optional[Any]:
        """根据名称获取嵌入模型"""
        return self.embedding_model_repo.get_model_by_name(model_name)
    
    def get_embedding_model_versions(self, model_id: int) -> List[Any]:
        """获取嵌入模型版本"""
        return self.embedding_model_repo.get_model_versions(model_id)
    
    def get_configured_embedding_models(self) -> List[Dict[str, Any]]:
        """获取已配置的嵌入模型"""
        return self.embedding_model_repo.get_configured_models()
    
    def configure_embedding_model(self, model_name: str, version_name: str, config: Dict[str, Any]) -> bool:
        """配置嵌入模型"""
        return self.embedding_model_repo.configure_model(model_name, version_name, config)
    
    def create_embedding_model(self, model_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """创建嵌入模型"""
        return self.embedding_model_repo.create_custom_model(model_data)
    
    def delete_embedding_model(self, model_name: str) -> bool:
        """删除嵌入模型"""
        return self.embedding_model_repo.delete_model(model_name)