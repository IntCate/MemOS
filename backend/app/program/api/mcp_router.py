"""MCP工具相关API路由"""
from fastapi import APIRouter, Depends, Body
from typing import List, Dict, Any
from app.capabilities import MCPCapability
from app.dependencies import get_mcp_capability
from app.utils.error_handler import handle_api_errors

router = APIRouter(prefix='/api/mcp')

@router.get('/tools', response_model=List[Dict[str, Any]])
@handle_api_errors()
def get_mcp_tools(mcp_capability: MCPCapability = Depends(get_mcp_capability)):
    """获取所有MCP服务器的工具列表"""
    mcp_config = mcp_capability.get_mcp_config()
    tools = []
    for server_name in mcp_config:
        server_config = mcp_config.get(server_name, {})
        tools.append({
            'server_name': server_name,
            'tool_name': '',
            'description': '',
            'config': server_config
        })
    return tools

@router.get('/tools/{server_name}', response_model=List[Dict[str, Any]])
@handle_api_errors()
async def get_mcp_tools_by_server(server_name: str, mcp_capability: MCPCapability = Depends(get_mcp_capability)):
    """根据服务器名称获取MCP工具列表"""
    mcp_config = mcp_capability.get_mcp_config()
    if server_name not in mcp_config:
        return []
    tools = await mcp_capability.get_tools_by_server(server_name, mcp_config)
    return [
        {
            'server_name': server_name,
            'tool_name': tool,
            'description': '',
            'config': mcp_config.get(server_name, {})
        }
        for tool in tools
    ]

@router.get('/servers', response_model=List[Dict[str, Any]])
@handle_api_errors()
def get_mcp_servers(mcp_capability: MCPCapability = Depends(get_mcp_capability)):
    """获取MCP服务器列表"""
    mcp_config = mcp_capability.get_mcp_config()
    servers = []
    for server_name, config in mcp_config.items():
        servers.append({
            'name': server_name,
            'transport': config.get('transport', 'stdio'),
            'command': config.get('command', ''),
            'args': config.get('args', []),
            'available': mcp_capability.is_available(mcp_config)
        })
    return servers

@router.get('/config', response_model=Dict[str, Any])
@handle_api_errors()
def get_mcp_config(mcp_capability: MCPCapability = Depends(get_mcp_capability)):
    """获取MCP配置文件"""
    return mcp_capability.get_mcp_config()

@router.post('/config', response_model=Dict[str, str])
@handle_api_errors()
def save_mcp_config(config: dict = Body(...), mcp_capability: MCPCapability = Depends(get_mcp_capability)):
    """保存MCP配置文件"""
    success = mcp_capability.save_mcp_config(config)
    if success:
        return {'status': 'success', 'message': '配置保存成功'}
    else:
        return {'status': 'error', 'message': '配置保存失败'}
