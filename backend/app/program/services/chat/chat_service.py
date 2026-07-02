"""对话相关业务逻辑服务 - 使用基础设施层

业务服务（Business Service）：包含业务规则和业务流程
基础设施服务（Infrastructure Service）：提供通用能力，不包含业务逻辑

本服务依赖：
- DataInfrastructure: 数据基础设施（数据库访问）
- SearchInfrastructure: 搜索基础设施（Memory + KnowledgeBase）
"""
from app.program.services.base_service import BaseService
from app.utils import handle_errors, handle_db_errors
from app.infrastructure import DataInfrastructure, SearchInfrastructure


class ChatService(BaseService):
    """对话服务类，封装所有对话相关的业务逻辑
    
    职责划分：
    - 对话元数据管理（标题、时间戳、置顶状态）→ DataInfrastructure → SQLite
    - 对话消息管理（消息内容）→ SearchInfrastructure → Memory Layer
    """
    
    def __init__(self):
        """初始化对话服务"""
        super().__init__()
        self.data_infra = DataInfrastructure()
        self.search_infra = SearchInfrastructure()
    
    @handle_errors(default_return=[])
    def get_chats(self):
        """获取所有对话（包含消息）"""
        chats = self.data_infra.get_chats()
        for chat in chats:
            chat['messages'] = []
        
        return chats
    
    def get_chat(self, chat_id):
        """获取单个对话记录（按ID），包含消息"""
        chat = self.data_infra.get_chat_by_id(chat_id)
        if chat:
            chat['messages'] = []
        
        return chat
    
    async def get_chat_with_messages(self, chat_id):
        """获取对话及其所有消息"""
        chat = self.data_infra.get_chat_by_id(chat_id)
        if not chat:
            return None
        
        messages = await self.search_infra.get_chat_history(chat_id)
        chat['messages'] = [
            {
                'id': m.id,
                'role': m.metadata.get('role', 'user'),
                'content': m.content,
                'createdAt': m.timestamp.isoformat(),
                'metadata': m.metadata
            }
            for m in messages
        ]
        
        return chat
    
    @handle_db_errors(default_return=False)
    def delete_chat(self, chat_id):
        """删除单个对话记录（按ID）"""
        self.data_infra.delete_chat(chat_id)
        
        return True
    
    async def delete_chat_with_memory(self, chat_id):
        """删除对话及其所有记忆"""
        self.data_infra.delete_chat(chat_id)
        await self.search_infra.delete_session(chat_id)
        
        return True
    
    @handle_db_errors(default_return=False)
    def delete_all_chats(self):
        """删除所有对话记录"""
        self.data_infra.delete_all_chats()
        
        return True
    
    async def delete_all_chats_with_memory(self):
        """删除所有对话及其记忆"""
        self.data_infra.delete_all_chats()
        
        return True
    
    @handle_db_errors(default_return=False)
    def update_chat_pin(self, chat_id, pinned):
        """更新对话置顶状态"""
        chat = self.data_infra.get_chat_by_id(chat_id)
        if not chat:
            return False
        
        updated_at = self.get_current_timestamp()
        self.data_infra.update_chat(
            chat_id=chat_id,
            pinned=int(pinned),
            updated_at=updated_at
        )
        
        return True
    
    def create_chat(self, title='新对话'):
        """创建新对话"""
        import uuid
        chat_id = str(uuid.uuid4())
        now = self.get_current_timestamp()
        
        self.data_infra.create_chat(
            chat_id=chat_id,
            title=title,
            preview='',
            created_at=now,
            updated_at=now
        )
        
        return {
            'id': chat_id,
            'title': title,
            'preview': '',
            'createdAt': now,
            'updatedAt': now,
            'pinned': False,
            'messages': []
        }
    
    def update_chat_title(self, chat_id, title):
        """更新对话标题"""
        chat = self.data_infra.get_chat_by_id(chat_id)
        if not chat:
            return False
        
        self.data_infra.update_chat(
            chat_id=chat_id,
            title=title,
            updated_at=self.get_current_timestamp()
        )
        
        return True
    
    def update_chat_preview(self, chat_id, preview):
        """更新对话预览"""
        chat = self.data_infra.get_chat_by_id(chat_id)
        if not chat:
            return False
        
        self.data_infra.update_chat(
            chat_id=chat_id,
            preview=preview[:50] + (preview[50:] and '...'),
            updated_at=self.get_current_timestamp()
        )
        
        return True