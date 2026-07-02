"""MCP 能力服务 - Model Context Protocol

这是一个独立的能力服务，提供 MCP 客户端管理和工具调用能力。
MCP 配置使用 YAML 文件存储，便于编辑和版本控制。
"""
from typing import Dict, List, Any
import os
import json
import yaml
from app.core.instance_manager import InstanceManager
from app.utils.path_manager import PathManager
from app.core.logger import logger


class MCPCapability:
    """MCP 能力服务 - 管理 MCP 客户端生命周期和工具调用"""
    
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(MCPCapability, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        
        self._config_path = self._get_config_path()
        self._initialized = True
    
    def _get_config_path(self) -> str:
        """获取MCP配置文件路径"""
        data_dir = PathManager.get_data_dir()
        config_dir = os.path.join(data_dir, 'config')
        os.makedirs(config_dir, exist_ok=True)
        return os.path.join(config_dir, 'mcp_config.yaml')
    
    def _generate_cache_key(self, mcp_config: Dict, server_name: str = None) -> str:
        if server_name and server_name in mcp_config:
            single_server_config = {server_name: mcp_config[server_name]}
            return json.dumps(single_server_config, sort_keys=True)
        return json.dumps(mcp_config, sort_keys=True)
    
    def is_available(self, mcp_config: Dict = None) -> bool:
        if mcp_config:
            cache_key = self._generate_cache_key(mcp_config)
            return InstanceManager().has_instance('mcp', cache_key)
        return False
    
    async def get_tools_by_server(self, server_name: str, mcp_config: Dict) -> List[Any]:
        if server_name not in mcp_config:
            return []
        
        try:
            from mcp import Client, Transport
            server_config = mcp_config[server_name]
            transport_type = server_config.get('transport', 'stdio')
            
            if transport_type == 'stdio':
                command = server_config.get('command')
                args = server_config.get('args', [])
                
                transport = Transport(command=command, args=args)
                async with Client(transport) as client:
                    return list(client.tools.keys())
            
            return []
        except ImportError:
            return []
        except Exception as e:
            logger.error(f"[MCPCapability] 获取工具列表失败 server={server_name}: {e}", exc_info=True)
            return []
    
    async def execute_tool(self, server_name: str, mcp_config: Dict, tool_name: str, **kwargs) -> Any:
        if server_name not in mcp_config:
            return None
        
        try:
            from mcp import Client, Transport
            server_config = mcp_config[server_name]
            transport_type = server_config.get('transport', 'stdio')
            
            if transport_type == 'stdio':
                command = server_config.get('command')
                args = server_config.get('args', [])
                
                transport = Transport(command=command, args=args)
                async with Client(transport) as client:
                    if tool_name in client.tools:
                        result = await client.call(tool_name, **kwargs)
                        return result
                    
            return None
        except ImportError:
            return None
        except Exception as e:
            logger.error(f"[MCPCapability] 执行工具失败 server={server_name} tool={tool_name}: {e}", exc_info=True)
            return None
    
    def get_default_config(self) -> Dict:
        base_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..'))
        
        return {
            "filesystem": {
                "transport": "stdio",
                "command": "npx",
                "args": ["-y", "@modelcontextprotocol/server-filesystem", base_path]
            },
            "freesearch": {
                "transport": "stdio",
                "command": "npx",
                "args": ["freesearch-mcpserver@latest"]
            }
        }
    
    def get_mcp_config(self) -> Dict:
        """从YAML文件读取MCP配置"""
        try:
            if os.path.exists(self._config_path):
                with open(self._config_path, 'r', encoding='utf-8') as f:
                    return yaml.safe_load(f)
            return self.get_default_config()
        except Exception as e:
            logger.error(f"[MCPCapability] 读取MCP配置失败: {e}", exc_info=True)
            return self.get_default_config()
    
    def save_mcp_config(self, config: Dict) -> bool:
        """保存MCP配置到YAML文件"""
        try:
            with open(self._config_path, 'w', encoding='utf-8') as f:
                yaml.dump(config, f, default_flow_style=False, allow_unicode=True)
            return True
        except Exception as e:
            logger.error(f"[MCPCapability] 保存MCP配置失败: {e}", exc_info=True)
            return False