"""消息相关业务逻辑服务 - 使用基础设施层

业务服务（Business Service）：包含业务规则和业务流程
基础设施服务（Infrastructure Service）：提供通用能力，不包含业务逻辑

本服务依赖：
- ChatService: 对话业务服务
- WebSearchService: 网络搜索业务服务
- SearchInfrastructure: 搜索基础设施（Memory + KnowledgeBase）
- ChannelEngine: AI工程层通道
"""
import uuid
from datetime import datetime
from app.program.services.base_service import BaseService
from app.utils import FileUtils
from app.infrastructure import SearchInfrastructure


class MessageService(BaseService):
    """消息服务类，封装所有消息相关的业务逻辑
    
    职责划分：
    - 消息发送 → ChannelEngine → AI Engineering
    - 消息存储 → SearchInfrastructure → Memory Layer（由 HarnessEngine 内部处理）
    - 对话元数据更新 → ChatService → DataInfrastructure → SQLite
    """
    
    def __init__(self, chat_service):
        """初始化消息服务"""
        super().__init__()
        self.chat_service = chat_service
        self._channel_engine = None
        self.search_infra = SearchInfrastructure()
    
    @property
    def channel_engine(self):
        """延迟获取 ChannelEngine，避免循环依赖"""
        if self._channel_engine is None:
            from app.core.service_container import service_container
            self._channel_engine = service_container.get_service('channel_engine')
        return self._channel_engine
    
    def process_uploaded_files(self, files):
        """处理上传的文件，保存到临时目录并提取内容"""
        return FileUtils.process_uploaded_files(files)
    
    def _parse_request_data(self, data):
        """解析请求数据"""
        message_text = data.get('message')
        model_name = data.get('model', '')
        user_model_params = data.get('modelParams', {})
        rag_config = data.get('ragConfig', {})
        rag_enabled = rag_config.get('enabled', False)
        stream = data.get('stream', False)
        reasoning = data.get('reasoning', False)
        web_search_enabled = data.get('webSearchEnabled', False)
        files = data.get('files', [])
        selected_message_ids = data.get('selectedMessageIds', None)
        
        self.log_debug(f"完整请求数据: {data}")
        self.log_debug(f"后端接收参数: message={message_text[:50]}{'...' if len(message_text) > 50 else ''}, model={model_name}, files={len(files)} 个文件, selectedMessageIds={selected_message_ids}, webSearchEnabled={web_search_enabled}")
        
        return {
            'message_text': message_text,
            'model_name': model_name,
            'user_model_params': user_model_params,
            'rag_enabled': rag_enabled,
            'rag_config': rag_config,
            'stream': stream,
            'reasoning': reasoning,
            'web_search_enabled': web_search_enabled,
            'files': files,
            'selected_message_ids': selected_message_ids
        }
    
    async def send_message(self, chat_id, data):
        """发送消息（应用层）"""
        parsed_data = self._parse_request_data(data)
        message_text = parsed_data['message_text']
        stream = parsed_data.get('stream', False)
        
        file_contents = self.process_uploaded_files(parsed_data.get('files', []))
        full_message_text = message_text
        if file_contents:
            full_message_text += "\n\n" + "\n\n".join(file_contents)
        
        if stream:
            return self.channel_engine.process_streaming(
                content=full_message_text,
                chat_id=chat_id,
                user_id=parsed_data.get('user_id', 'anonymous'),
                channel_type='api',
                metadata={
                    'model_name': parsed_data.get('model_name', ''),
                    'model_params': parsed_data.get('user_model_params', {}),
                    'rag_enabled': parsed_data.get('rag_enabled', False),
                    'rag_config': parsed_data.get('rag_config', {}),
                    'web_search_enabled': parsed_data.get('web_search_enabled', False),
                    'selected_message_ids': parsed_data.get('selected_message_ids')
                }
            )
        else:
            response = await self.channel_engine.process_message(
                content=full_message_text,
                chat_id=chat_id,
                user_id=parsed_data.get('user_id', 'anonymous'),
                channel_type='api',
                metadata={
                    'model_name': parsed_data.get('model_name', ''),
                    'model_params': parsed_data.get('user_model_params', {}),
                    'rag_enabled': parsed_data.get('rag_enabled', False),
                    'rag_config': parsed_data.get('rag_config', {}),
                    'web_search_enabled': parsed_data.get('web_search_enabled', False),
                    'selected_message_ids': parsed_data.get('selected_message_ids')
                }
            )
            
            if response.get('success', True):
                content = response.get('content', '')
                
                self.chat_service.update_chat_preview(chat_id, message_text)
                
                if response.get('chat_id') != chat_id:
                    chat_id = response.get('chat_id', chat_id)
                
                return {
                    'content': content,
                    'messageId': response.get('message_id', str(uuid.uuid4())),
                    'chatId': chat_id,
                    'metadata': response.get('metadata', {})
                }, 200
            else:
                return {'error': response.get('error', 'Unknown error')}, 500
    
    async def get_messages(self, chat_id):
        """获取对话的所有消息"""
        chat = await self.chat_service.get_chat_with_messages(chat_id)
        if not chat:
            return []
        return chat.get('messages', [])
    
    async def delete_message(self, chat_id, message_id):
        """删除单条消息"""
        try:
            await self.search_infra.delete_memory(message_id)
            return True
        except Exception as e:
            self.log_error(f"删除消息失败: {str(e)}")
            return False
    
    async def clear_messages(self, chat_id):
        """清除对话的所有消息"""
        try:
            await self.search_infra.delete_session(chat_id)
            return True
        except Exception as e:
            self.log_error(f"清除消息失败: {str(e)}")
            return False