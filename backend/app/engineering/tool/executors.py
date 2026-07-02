"""工具执行器实现"""
import json
from typing import Dict, Any, Optional
from app.core.logger import logger
from app.core.service_container import service_container
from .data_structures import ToolCall, ToolResult, ToolExecutor, ToolType


class MCPToolExecutor:
    """MCP工具执行器"""
    
    def __init__(self):
        self.mcp_service = None
    
    async def _ensure_mcp_service(self):
        """确保MCP服务可用"""
        if not self.mcp_service:
            try:
                self.mcp_service = service_container.get_service('mcp_service')
                await self.mcp_service.initialize_mcp()
            except Exception as e:
                logger.error(f"初始化MCP服务失败: {e}")
    
    async def execute(self, tool_call: ToolCall) -> ToolResult:
        """执行MCP工具"""
        await self._ensure_mcp_service()
        
        if not self.mcp_service:
            return ToolResult.error_result(
                call_id=tool_call.call_id,
                error="MCP服务未初始化"
            )
        
        try:
            result = await self._run_mcp_tool(tool_call)
            return ToolResult.success_result(
                call_id=tool_call.call_id,
                content=result,
                tool_name=tool_call.tool_name,
                raw_result=result
            )
        except Exception as e:
            logger.error(f"MCP工具执行失败: {tool_call.tool_name}, 错误: {e}")
            return ToolResult.error_result(
                call_id=tool_call.call_id,
                error=str(e),
                tool_name=tool_call.tool_name
            )
    
    async def _run_mcp_tool(self, tool_call: ToolCall) -> str:
        """运行MCP工具"""
        try:
            mcp_client_manager = self.mcp_service.mcp_client_manager
            result = await mcp_client_manager.run_tool(
                tool_call.tool_name,
                tool_call.arguments
            )
            return self._format_result(result)
        except Exception as e:
            logger.error(f"运行MCP工具失败: {e}")
            raise
    
    def _format_result(self, result: Any) -> str:
        """格式化结果"""
        if isinstance(result, str):
            return result
        try:
            return json.dumps(result, ensure_ascii=False)
        except Exception:
            return str(result)
    
    def supports_tool(self, tool_name: str) -> bool:
        """检查是否支持该工具"""
        return True


class WebSearchToolExecutor:
    """网络搜索工具执行器"""
    
    def __init__(self):
        self.web_search_service = None
    
    async def _ensure_web_search_service(self):
        """确保网络搜索服务可用"""
        if not self.web_search_service:
            try:
                self.web_search_service = service_container.get_service('web_search_service')
            except Exception as e:
                logger.error(f"初始化网络搜索服务失败: {e}")
    
    async def execute(self, tool_call: ToolCall) -> ToolResult:
        """执行网络搜索"""
        await self._ensure_web_search_service()
        
        if not self.web_search_service:
            return ToolResult.error_result(
                call_id=tool_call.call_id,
                error="网络搜索服务未初始化"
            )
        
        try:
            query = tool_call.arguments.get('query', '')
            result = await self.web_search_service.perform_web_search(query)
            return ToolResult.success_result(
                call_id=tool_call.call_id,
                content=self._format_result(result),
                tool_name=tool_call.tool_name,
                raw_result=result
            )
        except Exception as e:
            logger.error(f"网络搜索失败: {e}")
            return ToolResult.error_result(
                call_id=tool_call.call_id,
                error=str(e),
                tool_name=tool_call.tool_name
            )
    
    def _format_result(self, result: Any) -> str:
        """格式化搜索结果"""
        if isinstance(result, dict) and 'results' in result:
            parts = []
            for i, r in enumerate(result['results'][:5]):
                title = r.get('title', '')
                snippet = r.get('snippet', '')
                url = r.get('url', '')
                parts.append(f"{i+1}. {title}\n{snippet}\n{url}")
            return "\n\n".join(parts)
        return str(result)
    
    def supports_tool(self, tool_name: str) -> bool:
        """检查是否支持该工具"""
        return tool_name.lower() in ['web_search', 'search', 'websearch']


class RAGToolExecutor:
    """RAG工具执行器 - 使用独立 KnowledgeBase Layer"""
    
    def __init__(self):
        self.knowledge_base_manager = None
    
    async def _ensure_knowledge_base(self):
        """确保知识库服务可用"""
        if not self.knowledge_base_manager:
            try:
                from app.knowledgebase import get_knowledge_base_manager
                self.knowledge_base_manager = get_knowledge_base_manager()
            except Exception as e:
                logger.error(f"初始化知识库服务失败: {e}")
    
    async def execute(self, tool_call: ToolCall) -> ToolResult:
        """执行RAG搜索"""
        await self._ensure_knowledge_base()
        
        if not self.knowledge_base_manager:
            return ToolResult.error_result(
                call_id=tool_call.call_id,
                error="知识库服务未初始化"
            )
        
        try:
            query = tool_call.arguments.get('query', '')
            top_k = tool_call.arguments.get('top_k', 3)
            folder_id = tool_call.arguments.get('folder_id', 'default')
            
            results = await self.knowledge_base_manager.search(
                query=query,
                collection_name=folder_id,
                limit=top_k
            )
            
            result = {
                'success': True,
                'results': [r.to_dict() for r in results],
                'result_count': len(results)
            }
            
            return ToolResult.success_result(
                call_id=tool_call.call_id,
                content=self._format_result(result),
                tool_name=tool_call.tool_name,
                raw_result=result
            )
        except Exception as e:
            logger.error(f"RAG搜索失败: {e}")
            return ToolResult.error_result(
                call_id=tool_call.call_id,
                error=str(e),
                tool_name=tool_call.tool_name
            )
    
    def _format_result(self, result: Any) -> str:
        """格式化RAG结果"""
        if isinstance(result, dict) and 'results' in result:
            parts = []
            for i, doc in enumerate(result['results']):
                if isinstance(doc, dict):
                    content = doc.get('content', '') or doc.get('page_content', '')
                else:
                    content = getattr(doc, 'page_content', '') or getattr(doc, 'content', '')
                parts.append(f"{i+1}. {content}")
            return "\n\n".join(parts)
        return str(result)
    
    def supports_tool(self, tool_name: str) -> bool:
        """检查是否支持该工具"""
        return tool_name.lower() in ['rag_search', 'document_search', 'knowledge_search']


class CompositeToolExecutor:
    """组合工具执行器"""
    
    def __init__(self):
        self.executors: Dict[str, ToolExecutor] = {}
    
    def add_executor(self, tool_type: ToolType, executor: ToolExecutor):
        """添加执行器"""
        self.executors[tool_type.value] = executor
    
    async def execute(self, tool_call: ToolCall) -> ToolResult:
        """执行工具"""
        for executor in self.executors.values():
            if executor.supports_tool(tool_call.tool_name):
                return await executor.execute(tool_call)
        
        return ToolResult.error_result(
            call_id=tool_call.call_id,
            error=f"未找到支持的执行器: {tool_call.tool_name}"
        )
    
    def supports_tool(self, tool_name: str) -> bool:
        """检查是否支持该工具"""
        return any(e.supports_tool(tool_name) for e in self.executors.values())