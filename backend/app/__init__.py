"""MemOS应用主包"""
import os
import sys
from fastapi.staticfiles import StaticFiles

def register_services():
    """注册所有服务到服务容器
    
    服务分类：
    - Infrastructure Services: 基础设施服务（通用能力，无业务逻辑）
      - DataInfrastructure, SearchInfrastructure
      - MemoryManager, KnowledgeBaseManager
    - Business Services: 业务服务（包含业务规则和流程）
      - ChatService, MessageService, DocumentService 等
    - AI Engineering: AI工程层服务
      - HarnessEngine, ChannelEngine, InferenceEngine 等
    """
    from app.core.service_container import service_container
    
    from app.core.config import ConfigManager
    service_container.register_service('config_manager', ConfigManager.get_instance)
    
    from app.infrastructure import DataInfrastructure, SearchInfrastructure
    service_container.register_service('data_infrastructure', DataInfrastructure)
    service_container.register_service('search_infrastructure', SearchInfrastructure)
    
    from app.memory import get_memory_manager
    from app.knowledgebase import get_knowledge_base_manager
    service_container.register_service('memory_manager', get_memory_manager)
    service_container.register_service('knowledge_base_manager', get_knowledge_base_manager)
    
    from app.program.repositories.chat_repository import ChatRepository
    from app.program.repositories.message_repository import MessageRepository
    from app.program.repositories.model_repository import ModelRepository
    from app.program.repositories.setting_repository import SettingRepository
    from app.program.repositories.embedding_model_repository import EmbeddingModelRepository
    from app.program.repositories.document_repository import DocumentRepository
    from app.program.repositories.folder_repository import FolderRepository
    
    service_container.register_service('chat_repository', ChatRepository)
    service_container.register_service('message_repository', MessageRepository)
    service_container.register_service('model_repository', ModelRepository)
    service_container.register_service('setting_repository', SettingRepository)
    service_container.register_service('embedding_model_repository', EmbeddingModelRepository)
    service_container.register_service('document_repository', DocumentRepository)
    service_container.register_service('folder_repository', FolderRepository)
    
    from app.capabilities import MCPCapability, skill_manager, init_skills
    service_container.register_service('mcp_capability', MCPCapability)
    service_container.register_service('skill_manager', lambda: skill_manager)
    init_skills()
    
    from app.program.services.chat.chat_service import ChatService
    from app.program.services.model.model_service import ModelService
    from app.program.services.model.embedding_model_service import EmbeddingModelService
    from app.program.services.settings.setting_service import SettingService
    from app.program.services.file.document_service import DocumentService
    from app.program.services.message.message_service import MessageService
    
    service_container.register_service('chat_service', ChatService)
    service_container.register_service('model_service', ModelService, 'model_repository')
    service_container.register_service('embedding_model_service', EmbeddingModelService)
    service_container.register_service('setting_service', SettingService, 'setting_repository')
    service_container.register_service('document_service', DocumentService)
    service_container.register_service('message_service', MessageService, 'chat_service')
    
    from app.engineering.harness.engine import HarnessEngine
    from app.engineering.inference.engine import InferenceEngine
    from app.engineering.prompt.engine import PromptEngine
    from app.engineering.context.engine import ContextEngine
    from app.engineering.channel.engine import ChannelEngine
    
    service_container.register_service('harness_engine', HarnessEngine)
    service_container.register_service('inference_engine', InferenceEngine)
    service_container.register_service('prompt_engine', PromptEngine)
    service_container.register_service('context_engine', ContextEngine)
    service_container.register_service('channel_engine', ChannelEngine)

def create_app(lifespan=None):
    """创建FastAPI应用实例"""
    from fastapi import FastAPI
    from fastapi.middleware.cors import CORSMiddleware
    from app.core.logger import logger
    
    register_services()
    
    app = FastAPI(
        title="MemOS API",
        description="MemOS后端API服务",
        version="1.0.0",
        docs_url="/api/docs",
        redoc_url="/api/redoc",
        lifespan=lifespan
    )
    
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    from app.program.api import register_routes
    register_routes(app)
    
    _configure_static_files(app, logger)
    
    return app

def _configure_static_files(app, logger):
    """配置静态文件服务"""
    if hasattr(sys, '_MEIPASS'):
        base_dir = sys._MEIPASS
        logger.info(f"PyInstaller环境: {base_dir}")
        possible_paths = [base_dir]
        path_names = ["PyInstaller基础目录"]
    else:
        current_dir = os.path.dirname(os.path.abspath(__file__))
        base_dir = os.path.abspath(os.path.join(current_dir, "..", ".."))
        logger.info(f"开发环境: {base_dir}")
        possible_paths = [os.path.join(base_dir, "web_dist")]
        path_names = ["开发环境路径"]
    
    frontend_dist = None
    selected_path = ""
    
    for i, path in enumerate(possible_paths):
        if os.path.exists(path) and os.path.exists(os.path.join(path, "index.html")):
            frontend_dist = path
            selected_path = path_names[i]
            break
    
    if frontend_dist:
        logger.info(f"静态文件目录: {frontend_dist} ({selected_path})")
        app.mount("", StaticFiles(directory=frontend_dist, html=True), name="static")
        logger.info("静态文件服务已配置")
    else:
        logger.error("未找到包含index.html的静态文件目录")
        logger.error(f"尝试的路径: {possible_paths}")