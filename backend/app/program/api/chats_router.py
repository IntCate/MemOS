"""对话相关API路由 - 使用独立 Memory Layer"""
from fastapi import APIRouter, Body, Path, HTTPException, Depends
from app.program.services.chat.chat_service import ChatService
from app.utils.error_handler import handle_api_errors
from app.dependencies import get_chat_service
from app.models.schemas.pydantic_models import (
    ChatListResponse, ChatResponse,
    PinUpdateRequest, PinUpdateResponse, DeleteChatResponse,
    SuccessResponse
)

router = APIRouter(prefix='/api/chats')


@router.get('', response_model=ChatListResponse)
@handle_api_errors()
def get_chats(chat_service: ChatService = Depends(get_chat_service)):
    """获取所有对话（仅元数据）"""
    chats = chat_service.get_chats()
    return ChatListResponse(chats=chats)


@router.get('/{chat_id}', response_model=ChatResponse)
@handle_api_errors()
async def get_chat(chat_id: str = Path(...), chat_service: ChatService = Depends(get_chat_service)):
    """获取单个对话记录（按ID），包含消息"""
    chat = await chat_service.get_chat_with_messages(chat_id)
    if not chat:
        raise HTTPException(status_code=404, detail='对话不存在')
    return ChatResponse(chat=chat)


@router.delete('/delete-all', response_model=SuccessResponse)
@handle_api_errors()
async def delete_all_chats(chat_service: ChatService = Depends(get_chat_service)):
    """删除所有对话记录及其记忆"""
    await chat_service.delete_all_chats_with_memory()
    return SuccessResponse(success=True, message='所有对话已删除')


@router.delete('/{chat_id}', response_model=DeleteChatResponse)
@handle_api_errors()
async def delete_chat(chat_id: str = Path(...), chat_service: ChatService = Depends(get_chat_service)):
    """删除单个对话记录（按ID）及其记忆"""
    success = await chat_service.delete_chat_with_memory(chat_id)
    if not success:
        raise HTTPException(status_code=404, detail='对话不存在')
    
    return DeleteChatResponse(success=True, message='对话已删除')


@router.patch('/{chat_id}/pin', response_model=PinUpdateResponse)
@handle_api_errors()
def update_chat_pin(chat_id: str = Path(...), data: PinUpdateRequest = Body(...), chat_service: ChatService = Depends(get_chat_service)):
    """更新对话置顶状态"""
    pinned = data.pinned
    
    success = chat_service.update_chat_pin(chat_id, pinned)
    if not success:
        raise HTTPException(status_code=404, detail='对话不存在')
    
    return PinUpdateResponse(success=True, message=f'对话已{"置顶" if pinned else "取消置顶"}')


@router.post('')
@handle_api_errors()
def create_chat(title: str = Body(None), chat_service: ChatService = Depends(get_chat_service)):
    """创建新对话"""
    title = title or '新对话'
    chat = chat_service.create_chat(title)
    return ChatResponse(chat=chat)


@router.patch('/{chat_id}/title')
@handle_api_errors()
def update_chat_title(chat_id: str = Path(...), title: str = Body(...), chat_service: ChatService = Depends(get_chat_service)):
    """更新对话标题"""
    success = chat_service.update_chat_title(chat_id, title)
    if not success:
        raise HTTPException(status_code=404, detail='对话不存在')
    return SuccessResponse(success=True, message='标题已更新')