"""网络搜索 Skill - 通过 MCP 执行网络搜索"""
from typing import Dict, List, Any
from app.capabilities.skill.protocol import Skill
from app.capabilities.mcp import MCPCapability


class WebSearchSkill(Skill):
    """网络搜索 Skill - 提供网络搜索能力
    
    该 Skill 通过 MCP 协议调用外部搜索服务，
    使 AI Agent 能够获取实时的网络信息。
    """
    
    def __init__(self):
        self.mcp_capability = MCPCapability()
        self._enabled = True
    
    def get_name(self) -> str:
        return "web_search"
    
    def get_description(self) -> str:
        return "执行网络搜索，获取实时信息。适用于需要最新信息的问题，如新闻、天气、技术文档等。"
    
    def get_parameters(self) -> List[Dict[str, Any]]:
        return [
            {
                "name": "query",
                "type": "string",
                "description": "搜索查询词",
                "required": True
            },
            {
                "name": "max_results",
                "type": "integer",
                "description": "最大返回结果数量，默认为3",
                "required": False
            }
        ]
    
    async def execute(self, **kwargs) -> Any:
        """执行网络搜索"""
        query = kwargs.get('query', '')
        max_results = kwargs.get('max_results', 3)
        
        if not query:
            return {"error": "搜索查询词不能为空"}
        
        mcp_config = self.mcp_capability.get_mcp_config()
        
        search_server = None
        for server_name in mcp_config.keys():
            if 'search' in server_name.lower():
                search_server = server_name
                break
        
        if not search_server:
            search_server = 'freesearch'
        
        tools = await self.mcp_capability.get_tools_by_server(search_server, mcp_config)
        
        search_tool_name = None
        for tool in tools:
            try:
                tool_name = getattr(tool, 'name', '').lower()
                if 'search' in tool_name:
                    search_tool_name = tool_name
                    break
            except Exception:
                pass
        
        if not search_tool_name and tools:
            search_tool_name = tools[0]
        
        if search_tool_name:
            search_params = {
                "query": query,
                "max_results": max_results
            }
            
            result = await self.mcp_capability.execute_tool(
                search_server,
                mcp_config,
                search_tool_name,
                **search_params
            )
            
            if result:
                return {"results": result}
        
        return {"results": []}
    
    def is_enabled(self) -> bool:
        return self._enabled
    
    def set_enabled(self, enabled: bool):
        self._enabled = enabled
    
    def get_category(self) -> str:
        return "search"