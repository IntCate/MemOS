"""Channel引擎 - 程序层与AI层的通信桥梁"""
import uuid
from datetime import datetime
from typing import Dict, Any, Optional, AsyncGenerator, List

from app.core.logger import logger
from ..data_structures import Message, Response, ChannelType
from ..harness.engine import HarnessEngine


class ChannelEngine:
    """消息通道引擎 - 程序层与AI层的通信桥梁"""
    
    def __init__(self, config: Dict[str, Any] = None):
        self.config = config or {}
        self.harness_engine = HarnessEngine(self.config.get('harness', {}))
    
    async def process_message(
        self,
        content: str,
        chat_id: str = "",
        user_id: str = "",
        channel_type: str = "api",
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """处理用户消息，返回AI响应"""
        logger.info(f"[ChannelEngine] 收到消息: chat_id={chat_id}, user_id={user_id}, content={content[:50]}...")
        
        if not chat_id:
            chat_id = str(uuid.uuid4())
        
        message = Message(
            message_id=str(uuid.uuid4()),
            channel=ChannelType(channel_type),
            user_id=user_id,
            chat_id=chat_id,
            content=content,
            timestamp=datetime.now(),
            metadata=metadata or {}
        )
        
        response = await self.harness_engine.process(message)
        
        return {
            'success': response.success,
            'content': response.content,
            'message_id': response.message_id,
            'chat_id': response.chat_id,
            'error': response.error,
            'metadata': response.metadata
        }
    
    async def process_streaming(
        self,
        content: str,
        chat_id: str = "",
        user_id: str = "",
        channel_type: str = "api",
        metadata: Optional[Dict[str, Any]] = None
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """流式处理用户消息"""
        logger.info(f"[ChannelEngine] 收到流式消息: chat_id={chat_id}, user_id={user_id}")
        
        if not chat_id:
            chat_id = str(uuid.uuid4())
        
        message = Message(
            message_id=str(uuid.uuid4()),
            channel=ChannelType(channel_type),
            user_id=user_id,
            chat_id=chat_id,
            content=content,
            timestamp=datetime.now(),
            metadata=metadata or {}
        )
        
        async for chunk in self.harness_engine.process_streaming(message):
            if chunk.startswith('error:'):
                yield {
                    'success': False,
                    'content': "",
                    'error': chunk[6:],
                    'chat_id': chat_id
                }
            else:
                yield {
                    'success': True,
                    'content': chunk,
                    'chat_id': chat_id
                }
    
    async def sync_chat_history(self, chat_id: str, messages: List[Dict[str, Any]]) -> bool:
        """同步对话历史到工作区记忆"""
        logger.info(f"[ChannelEngine] 同步对话历史: chat_id={chat_id}, message_count={len(messages)}")
        
        try:
            for msg in messages:
                await self.harness_engine.memory_manager.add_working_memory(
                    content=msg.get('content', ''),
                    session_id=chat_id,
                    user_id=msg.get('user_id', ''),
                    role=msg.get('role', 'user'),
                    metadata={
                        'message_id': msg.get('id', ''),
                        'timestamp': msg.get('timestamp', '')
                    }
                )
            
            return True
        except Exception as e:
            logger.error(f"[ChannelEngine] 同步对话历史失败: {e}")
            return False
    
    async def clear_chat_memory(self, chat_id: str) -> bool:
        """清除指定对话的工作区记忆"""
        logger.info(f"[ChannelEngine] 清除对话工作区记忆: chat_id={chat_id}")
        
        try:
            return await self.harness_engine.memory_manager.delete_session(chat_id)
        except Exception as e:
            logger.error(f"[ChannelEngine] 清除对话工作区记忆失败: {e}")
            return False