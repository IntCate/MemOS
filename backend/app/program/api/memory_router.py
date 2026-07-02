"""Memory API路由 - 使用独立 Memory Layer"""
from fastapi import APIRouter, Depends, HTTPException
from typing import List, Dict, Optional, Any
from enum import Enum

from app.memory import get_memory_manager, MemoryManager, MemoryType, MemoryStats


router = APIRouter(prefix="/api/memory", tags=["memory"])


def get_memory_manager_dep() -> MemoryManager:
    return get_memory_manager()


class MemoryTypeEnum(str, Enum):
    EPISODIC = "episodic"
    SEMANTIC = "semantic"
    PROCEDURAL = "procedural"
    WORKING = "working"
    LONG_TERM = "long_term"


@router.post("/remember")
async def remember(
    content: str,
    memory_type: MemoryTypeEnum = MemoryTypeEnum.EPISODIC,
    metadata: Optional[Dict[str, Any]] = None,
    manager: MemoryManager = Depends(get_memory_manager_dep)
):
    memory_id = await manager.add_memory(
        content=content,
        memory_type=MemoryType(memory_type.value),
        metadata=metadata
    )
    
    if not memory_id:
        raise HTTPException(status_code=400, detail="记忆存储失败")
    
    return {"success": True, "memory_id": memory_id}


@router.post("/working")
async def add_working_memory(
    content: str,
    session_id: str,
    user_id: str = "",
    role: str = "user",
    metadata: Optional[Dict[str, Any]] = None,
    manager: MemoryManager = Depends(get_memory_manager_dep)
):
    memory_id = await manager.add_working_memory(
        content=content,
        session_id=session_id,
        user_id=user_id,
        role=role,
        metadata=metadata
    )
    
    if not memory_id:
        raise HTTPException(status_code=400, detail="工作区记忆存储失败")
    
    return {"success": True, "memory_id": memory_id}


@router.get("/recall")
async def recall(
    query: str,
    memory_type: Optional[MemoryTypeEnum] = None,
    limit: int = 5,
    threshold: Optional[float] = None,
    manager: MemoryManager = Depends(get_memory_manager_dep)
):
    threshold = threshold or 0.5
    context = await manager.search(
        query=query,
        memory_type=MemoryType(memory_type.value) if memory_type else None,
        limit=limit,
        threshold=threshold
    )
    
    return {
        "success": True,
        "query": context.query,
        "count": len(context.entries),
        "total_count": len(context.entries),
        "memories": [
            {
                "id": m.id,
                "content": m.content,
                "memory_type": m.memory_type.value,
                "timestamp": m.timestamp.isoformat(),
                "metadata": m.metadata,
                "relevance_score": m.relevance_score
            }
            for m in context.entries
        ]
    }


@router.delete("/forget/{memory_id}")
async def forget(
    memory_id: str,
    manager: MemoryManager = Depends(get_memory_manager_dep)
):
    success = await manager.delete_memory(memory_id)
    
    if not success:
        raise HTTPException(status_code=404, detail="记忆不存在")
    
    return {"success": True, "memory_id": memory_id}


@router.delete("/session/{session_id}")
async def delete_session(
    session_id: str,
    manager: MemoryManager = Depends(get_memory_manager_dep)
):
    success = await manager.delete_session(session_id)
    
    if not success:
        raise HTTPException(status_code=404, detail="会话不存在")
    
    return {"success": True, "session_id": session_id}


@router.put("/update/{memory_id}")
async def update(
    memory_id: str,
    content: Optional[str] = None,
    metadata: Optional[Dict[str, Any]] = None,
    manager: MemoryManager = Depends(get_memory_manager_dep)
):
    success = await manager.update_memory(memory_id, content, metadata)
    
    if not success:
        raise HTTPException(status_code=404, detail="记忆不存在")
    
    return {"success": True, "memory_id": memory_id}


@router.get("/memory/{memory_id}")
async def get_memory(
    memory_id: str,
    manager: MemoryManager = Depends(get_memory_manager_dep)
):
    memory = await manager.get_memory(memory_id)
    
    if not memory:
        raise HTTPException(status_code=404, detail="记忆不存在")
    
    return {
        "id": memory.id,
        "content": memory.content,
        "memory_type": memory.memory_type.value,
        "timestamp": memory.timestamp.isoformat(),
        "metadata": memory.metadata,
        "relevance_score": memory.relevance_score
    }


@router.get("/context/{session_id}")
async def get_context(
    session_id: str,
    limit: int = 10,
    manager: MemoryManager = Depends(get_memory_manager_dep)
):
    context = await manager.get_context(session_id=session_id, limit=limit)
    
    return {
        "session_id": context.session_id,
        "count": len(context.entries),
        "entries": [
            {
                "id": e.id,
                "content": e.content,
                "memory_type": e.memory_type.value,
                "timestamp": e.timestamp.isoformat(),
                "metadata": e.metadata,
                "relevance_score": e.relevance_score
            }
            for e in context.entries
        ]
    }


@router.get("/chat_history/{session_id}")
async def get_chat_history(
    session_id: str,
    manager: MemoryManager = Depends(get_memory_manager_dep)
):
    history = await manager.get_chat_history(session_id=session_id)
    
    return [
        {
            "id": h.id,
            "content": h.content,
            "memory_type": h.memory_type.value,
            "timestamp": h.timestamp.isoformat(),
            "metadata": h.metadata,
            "relevance_score": h.relevance_score
        }
        for h in history
    ]


@router.get("/list")
async def list_memories(
    memory_type: Optional[MemoryTypeEnum] = None,
    limit: int = 100,
    manager: MemoryManager = Depends(get_memory_manager_dep)
):
    memories = await manager.list_memories(
        memory_type=MemoryType(memory_type.value) if memory_type else None,
        limit=limit
    )
    
    return [
        {
            "id": m.id,
            "content": m.content,
            "memory_type": m.memory_type.value,
            "timestamp": m.timestamp.isoformat(),
            "metadata": m.metadata,
            "relevance_score": m.relevance_score
        }
        for m in memories
    ]


@router.get("/stats")
async def get_stats(
    manager: MemoryManager = Depends(get_memory_manager_dep)
):
    stats = await manager.get_stats()
    
    return {
        "total_memories": stats.total_memories,
        "by_type": stats.by_type,
        "total_size": stats.total_size,
        "total_sessions": stats.total_sessions
    }