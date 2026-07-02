"""对话数据访问类"""
import json
from sqlalchemy import desc
from app.program.repositories.base_repository import BaseRepository
from app.models.database.models import Chat, Message

class ChatRepository(BaseRepository):
    """对话数据访问类，处理对话相关的数据访问"""
    
    def __init__(self, db=None):
        """初始化对话仓库
        
        Args:
            db: SQLAlchemy会话对象，用于依赖注入
        """
        super().__init__(db)
    
    def _convert_chat_to_dict(self, chat):
        """将Chat对象转换为字典"""
        if isinstance(chat, dict):
            return chat
        
        return {
            'id': chat.id,
            'title': chat.title,
            'preview': chat.preview,
            'createdAt': chat.created_at,
            'updatedAt': chat.updated_at,
            'pinned': bool(chat.pinned),
            'messages': []
        }
    
    def _convert_message_to_dict(self, message):
        """将Message对象转换为字典"""
        if isinstance(message, dict):
            return message
        
        files = []
        if message.files:
            try:
                files = json.loads(message.files)
            except:
                files = []
        
        return {
            'id': message.id,
            'role': message.role,
            'content': message.content,
            'reasoning_content': message.reasoning_content,
            'createdAt': message.created_at,
            'model': message.model,
            'files': files,
            'agent_node': message.agent_node or '',
            'agent_step': message.agent_step or 0,
            'agent_metadata': message.agent_metadata
        }
    
    def get_all_chats(self):
        """获取所有对话"""
        db = self.get_db()
        try:
            chats = db.query(Chat).order_by(desc(Chat.updated_at)).all()
            return [self._convert_chat_to_dict(chat) for chat in chats]
        finally:
            if not hasattr(self, '_db') or not self._db:
                db.close()
    
    def get_chat_by_id(self, chat_id):
        """根据ID获取对话"""
        db = self.get_db()
        try:
            chat = db.query(Chat).filter(Chat.id == chat_id).first()
            if chat:
                return self._convert_chat_to_dict(chat)
            return None
        finally:
            if not hasattr(self, '_db') or not self._db:
                db.close()
    
    def create_chat(self, chat_id, title, preview, created_at, updated_at):
        """创建新对话"""
        db = self.get_db()
        try:
            existing_chat = db.query(Chat).filter(Chat.id == chat_id).first()
            if existing_chat:
                return self._convert_chat_to_dict(existing_chat)
            
            chat = Chat(
                id=chat_id,
                title=title,
                preview=preview,
                created_at=created_at,
                updated_at=updated_at
            )
            chat = self.add(chat)
            
            return self._convert_chat_to_dict(chat)
        finally:
            if not hasattr(self, '_db') or not self._db:
                db.close()
    
    def update_chat(self, chat_id, title, preview, updated_at, pinned=0):
        """更新对话"""
        db = self.get_db()
        try:
            chat = db.query(Chat).filter(Chat.id == chat_id).first()
            if chat:
                chat.title = title
                chat.preview = preview
                chat.updated_at = updated_at
                chat.pinned = pinned
                chat = self.update(chat)
                
                return self._convert_chat_to_dict(chat)
            return None
        finally:
            if not hasattr(self, '_db') or not self._db:
                db.close()
    
    def delete_chat(self, chat_id):
        """删除对话"""
        db = self.get_db()
        try:
            chat = db.query(Chat).filter(Chat.id == chat_id).first()
            if chat:
                db.query(Message).filter(Message.chat_id == chat_id).delete()
                db.delete(chat)
                db.commit()
            return True
        finally:
            if not hasattr(self, '_db') or not self._db:
                db.close()
    
    def delete_all_chats(self):
        """删除所有对话"""
        db = self.get_db()
        try:
            db.query(Message).delete()
            db.query(Chat).delete()
            db.commit()
            return True
        finally:
            if not hasattr(self, '_db') or not self._db:
                db.close()
    
    def get_chat_with_messages(self, chat_id):
        """获取对话及其所有消息"""
        db = self.get_db()
        try:
            chat = db.query(Chat).filter(Chat.id == chat_id).first()
            if chat:
                chat_dict = self._convert_chat_to_dict(chat)
                
                messages = db.query(Message).filter(Message.chat_id == chat_id).order_by(Message.created_at).all()
                chat_dict['messages'] = [self._convert_message_to_dict(msg) for msg in messages]
                
                return chat_dict
            
            return None
        finally:
            if not hasattr(self, '_db') or not self._db:
                db.close()