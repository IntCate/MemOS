"""存储基类实现"""
import uuid
from datetime import datetime
from typing import Dict, List, Optional, Any

from ..protocol import MemoryStore, MemoryEntry, MemoryType, MemoryStats


class BaseMemoryStore(MemoryStore):
    """存储基类 - 提供通用功能"""
    
    def __init__(self, config: Dict[str, Any] = None):
        self.config = config or {}
        self._memories: Dict[str, MemoryEntry] = {}
    
    def _generate_id(self) -> str:
        return str(uuid.uuid4())
    
    def _create_entry(
        self,
        content: str,
        memory_type: MemoryType,
        session_id: str,
        user_id: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> MemoryEntry:
        return MemoryEntry(
            id=self._generate_id(),
            content=content,
            memory_type=memory_type,
            timestamp=datetime.now(),
            metadata={
                'session_id': session_id,
                'user_id': user_id,
                **(metadata or {})
            },
            relevance_score=1.0
        )
    
    async def add(
        self,
        content: str,
        memory_type: MemoryType = MemoryType.WORKING,
        session_id: str = "",
        user_id: str = "",
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        entry = self._create_entry(content, memory_type, session_id, user_id, metadata)
        self._memories[entry.id] = entry
        return entry.id
    
    async def get(self, memory_id: str) -> Optional[MemoryEntry]:
        return self._memories.get(memory_id)
    
    async def update(
        self,
        memory_id: str,
        content: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> bool:
        if memory_id not in self._memories:
            return False
        
        entry = self._memories[memory_id]
        if content is not None:
            entry.content = content
        if metadata is not None:
            entry.metadata.update(metadata)
        
        return True
    
    async def delete(self, memory_id: str) -> bool:
        if memory_id in self._memories:
            del self._memories[memory_id]
            return True
        return False
    
    async def delete_by_session(self, session_id: str) -> bool:
        deleted = False
        to_delete = [
            mid for mid, entry in self._memories.items()
            if entry.metadata.get('session_id') == session_id
        ]
        for mid in to_delete:
            del self._memories[mid]
            deleted = True
        return deleted
    
    async def list(
        self,
        session_id: Optional[str] = None,
        memory_type: Optional[MemoryType] = None,
        limit: int = 100
    ) -> List[MemoryEntry]:
        entries = list(self._memories.values())
        
        if session_id is not None:
            entries = [
                e for e in entries
                if e.metadata.get('session_id') == session_id
            ]
        
        if memory_type is not None:
            entries = [
                e for e in entries
                if e.memory_type == memory_type
            ]
        
        entries.sort(key=lambda e: e.timestamp, reverse=True)
        return entries[:limit]
    
    async def get_stats(self) -> MemoryStats:
        by_type: Dict[str, int] = {}
        sessions = set()
        total_size = 0
        
        for entry in self._memories.values():
            by_type[entry.memory_type.value] = by_type.get(entry.memory_type.value, 0) + 1
            if 'session_id' in entry.metadata:
                sessions.add(entry.metadata['session_id'])
            total_size += len(entry.content.encode('utf-8'))
        
        return MemoryStats(
            total_memories=len(self._memories),
            by_type=by_type,
            total_size=total_size,
            total_sessions=len(sessions)
        )