"""本地YAML存储实现"""
import os
import yaml
from datetime import datetime
from typing import Dict, List, Optional, Any

from ..protocol import MemoryStore, MemoryEntry, MemoryType, MemoryStats
from .base import BaseMemoryStore


class LocalMemoryStore(BaseMemoryStore):
    """本地YAML文件存储实现
    
    每个会话（session_id）对应一个YAML文件，存储在 data/memory/ 目录下。
    """
    
    def __init__(self, config: Dict[str, Any] = None):
        super().__init__(config)
        self.data_dir = self.config.get('data_dir', self._default_data_dir())
        os.makedirs(self.data_dir, exist_ok=True)
        self._load_from_yaml()
    
    def _default_data_dir(self) -> str:
        from app.utils.path_manager import PathManager
        return PathManager.get_memory_root()
    
    def _get_file_path(self, session_id: str) -> str:
        return os.path.join(self.data_dir, f"{session_id}.yaml")
    
    def _load_from_yaml(self):
        """从YAML文件加载所有记忆"""
        if not os.path.exists(self.data_dir):
            return
        
        files = [f for f in os.listdir(self.data_dir) if f.endswith('.yaml')]
        for file in files:
            session_id = file[:-5]
            file_path = self._get_file_path(session_id)
            try:
                with open(file_path, 'r') as f:
                    data = yaml.safe_load(f)
                    if data and 'messages' in data:
                        for msg_data in data['messages']:
                            entry = MemoryEntry.from_dict(msg_data)
                            self._memories[entry.id] = entry
            except Exception:
                pass
    
    def _save_to_yaml(self, session_id: str):
        """将指定会话的记忆保存到YAML文件"""
        entries = [
            entry for entry in self._memories.values()
            if entry.metadata.get('session_id') == session_id
        ]
        
        entries.sort(key=lambda e: e.timestamp)
        
        data = {
            'chat_id': session_id,
            'updated_at': datetime.now().isoformat(),
            'message_count': len(entries),
            'messages': [entry.to_dict() for entry in entries]
        }
        
        file_path = self._get_file_path(session_id)
        with open(file_path, 'w') as f:
            yaml.dump(data, f, default_flow_style=False, allow_unicode=True)
    
    async def add(
        self,
        content: str,
        memory_type: MemoryType = MemoryType.WORKING,
        session_id: str = "",
        user_id: str = "",
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        entry_id = await super().add(content, memory_type, session_id, user_id, metadata)
        if session_id:
            self._save_to_yaml(session_id)
        return entry_id
    
    async def update(
        self,
        memory_id: str,
        content: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> bool:
        if memory_id not in self._memories:
            return False
        
        entry = self._memories[memory_id]
        session_id = entry.metadata.get('session_id')
        
        result = await super().update(memory_id, content, metadata)
        
        if result and session_id:
            self._save_to_yaml(session_id)
        
        return result
    
    async def delete(self, memory_id: str) -> bool:
        if memory_id not in self._memories:
            return False
        
        entry = self._memories[memory_id]
        session_id = entry.metadata.get('session_id')
        
        result = await super().delete(memory_id)
        
        if result and session_id:
            self._save_to_yaml(session_id)
        
        return result
    
    async def delete_by_session(self, session_id: str) -> bool:
        result = await super().delete_by_session(session_id)
        
        file_path = self._get_file_path(session_id)
        if os.path.exists(file_path):
            os.remove(file_path)
        
        return result