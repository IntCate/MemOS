"""Tool引擎 - 工具系统的统一入口"""
import asyncio
from typing import Dict, Any, List, Optional
from app.core.logger import logger
from app.core.service_container import service_container
from .data_structures import (
    Tool, ToolType, ToolCategory, ToolCall, ToolResult,
    ToolStore, ToolExecutor
)
from .stores import InMemoryToolStore
from .executors import (
    MCPToolExecutor, WebSearchToolExecutor, RAGToolExecutor, CompositeToolExecutor
)


class ToolEngine:
    """工具引擎 - 即插即用的工具系统"""
    
    def __init__(self, config: Dict[str, Any] = None):
        self.config = config or {}
        
        self.store: ToolStore = self._create_store()
        self.executor: ToolExecutor = self._create_executor()
        
        self._initialized = False
    
    def _create_store(self) -> ToolStore:
        """创建工具存储"""
        return InMemoryToolStore()
    
    def _create_executor(self) -> ToolExecutor:
        """创建工具执行器"""
        composite = CompositeToolExecutor()
        
        if self.config.get('enable_mcp', True):
            composite.add_executor(ToolType.MCP, MCPToolExecutor())
        
        if self.config.get('enable_web_search', True):
            composite.add_executor(ToolType.WEB_SEARCH, WebSearchToolExecutor())
        
        if self.config.get('enable_rag', True):
            composite.add_executor(ToolType.RAG, RAGToolExecutor())
        
        return composite
    
    async def initialize(self):
        """初始化工具引擎"""
        if self._initialized:
            return
        
        await self._load_tools_from_mcp()
        await self._load_tools_from_config()
        
        self._initialized = True
        logger.info(f"[ToolEngine] 初始化完成，共注册 {await self.store.get_tool_count()} 个工具")
    
    async def _load_tools_from_mcp(self):
        """从MCP加载工具"""
        try:
            mcp_service = service_container.get_service('mcp_service')
            await mcp_service.initialize_mcp()
            
            servers = mcp_service.get_mcp_servers()
            for server in servers:
                tools = await mcp_service.get_mcp_tools_by_server(server['name'])
                for tool_info in tools:
                    tool = Tool(
                        name=tool_info['name'],
                        description=tool_info.get('description', ''),
                        tool_type=ToolType.MCP,
                        category=self._get_category_from_name(tool_info['name']),
                        tags=[server['name']]
                    )
                    await self.store.register_tool(tool)
        except Exception as e:
            logger.warning(f"从MCP加载工具失败: {e}")
    
    async def _load_tools_from_config(self):
        """从配置加载工具"""
        tools_config = self.config.get('tools', [])
        for tool_config in tools_config:
            tool = Tool(
                name=tool_config['name'],
                description=tool_config.get('description', ''),
                tool_type=ToolType(tool_config.get('type', 'custom')),
                category=ToolCategory(tool_config.get('category', 'other')),
                parameters=tool_config.get('parameters', {}),
                tags=tool_config.get('tags', [])
            )
            await self.store.register_tool(tool)
    
    def _get_category_from_name(self, tool_name: str) -> ToolCategory:
        """根据工具名推断类别"""
        name_lower = tool_name.lower()
        if any(keyword in name_lower for keyword in ['search', 'find', 'lookup']):
            return ToolCategory.SEARCH
        if any(keyword in name_lower for keyword in ['file', 'read', 'write', 'save']):
            return ToolCategory.FILE
        if any(keyword in name_lower for keyword in ['code', 'python', 'execute']):
            return ToolCategory.CODE
        if any(keyword in name_lower for keyword in ['api', 'http', 'request']):
            return ToolCategory.DATA
        return ToolCategory.OTHER
    
    async def register_tool(self, tool: Tool):
        """注册工具"""
        await self.store.register_tool(tool)
    
    async def unregister_tool(self, tool_name: str):
        """注销工具"""
        await self.store.unregister_tool(tool_name)
    
    async def get_tool(self, tool_name: str) -> Optional[Tool]:
        """获取工具"""
        return await self.store.get_tool(tool_name)
    
    async def list_tools(self, tool_type: Optional[ToolType] = None,
                         category: Optional[ToolCategory] = None) -> List[Tool]:
        """列出工具"""
        return await self.store.list_tools(tool_type, category)
    
    async def execute(self, tool_call: ToolCall) -> ToolResult:
        """执行工具"""
        if not self._initialized:
            await self.initialize()
        
        tool = await self.store.get_tool(tool_call.tool_name)
        if not tool:
            return ToolResult.error_result(
                call_id=tool_call.call_id,
                error=f"工具不存在: {tool_call.tool_name}"
            )
        
        return await self.executor.execute(tool_call)
    
    async def execute_batch(self, tool_calls: List[ToolCall]) -> List[ToolResult]:
        """批量执行工具"""
        if not self._initialized:
            await self.initialize()
        
        tasks = [self.execute(call) for call in tool_calls]
        return await asyncio.gather(*tasks)
    
    async def execute_sequential(self, tool_calls: List[ToolCall],
                                  inject_results: bool = True) -> List[ToolResult]:
        """顺序执行工具（支持结果注入）"""
        if not self._initialized:
            await self.initialize()
        
        results = []
        context = {}
        
        for i, tool_call in enumerate(tool_calls):
            if inject_results and context:
                tool_call.arguments = self._inject_variables(tool_call.arguments, context)
            
            result = await self.execute(tool_call)
            results.append(result)
            
            if inject_results and result.success:
                context[f"tool_{i}"] = result.content
        
        return results
    
    def _inject_variables(self, args: Dict[str, Any], context: Dict[str, str]) -> Dict[str, Any]:
        """将参数中的占位符 {{tool_N}} 替换为实际值"""
        import json
        
        args_str = json.dumps(args, ensure_ascii=False)
        for key, value in context.items():
            placeholder = "{{" + key + "}}"
            if placeholder in args_str:
                args_str = args_str.replace(placeholder, str(value))
        
        return json.loads(args_str)
    
    async def get_stats(self) -> Dict[str, Any]:
        """获取工具统计"""
        total = await self.store.get_tool_count()
        by_type = {}
        for tool_type in ToolType:
            count = len(await self.store.list_tools(tool_type=tool_type))
            if count > 0:
                by_type[tool_type.value] = count
        
        return {
            'total_tools': total,
            'by_type': by_type
        }
    
    async def clear(self):
        """清空所有工具"""
        await self.store.clear()
        self._initialized = False
    
    def set_store(self, store: ToolStore):
        """设置工具存储"""
        self.store = store
    
    def set_executor(self, executor: ToolExecutor):
        """设置工具执行器"""
        self.executor = executor