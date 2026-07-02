"""工具存储实现"""
from typing import Dict, List, Optional
from app.core.logger import logger
from .data_structures import Tool, ToolType, ToolCategory, ToolStore


class InMemoryToolStore:
    """内存工具存储"""
    
    def __init__(self):
        self.tools: Dict[str, Tool] = {}
    
    async def register_tool(self, tool: Tool):
        """注册工具"""
        self.tools[tool.name] = tool
        logger.info(f"[ToolStore] 注册工具: {tool.name}")
    
    async def unregister_tool(self, tool_name: str):
        """注销工具"""
        if tool_name in self.tools:
            del self.tools[tool_name]
            logger.info(f"[ToolStore] 注销工具: {tool_name}")
    
    async def get_tool(self, tool_name: str) -> Optional[Tool]:
        """获取工具"""
        return self.tools.get(tool_name)
    
    async def list_tools(self, tool_type: Optional[ToolType] = None, 
                         category: Optional[ToolCategory] = None) -> List[Tool]:
        """列出工具"""
        result = []
        for tool in self.tools.values():
            if not tool.enabled:
                continue
            if tool_type and tool.tool_type != tool_type:
                continue
            if category and tool.category != category:
                continue
            result.append(tool)
        return result
    
    async def get_tool_count(self) -> int:
        """获取工具数量"""
        return len([t for t in self.tools.values() if t.enabled])
    
    async def clear(self):
        """清空工具"""
        self.tools = {}
        logger.info("[ToolStore] 清空所有工具")