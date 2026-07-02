"""API路由模块"""
from app.program.api.chats_router import router as chats_router
from app.program.api.files_router import router as files_router
from app.program.api.health_router import router as health_router
from app.program.api.models_router import router as models_router
from app.program.api.mcp_router import router as mcp_router
from app.program.api.embedding_models_router import router as embedding_models_router
from app.program.api.settings_router import router as settings_router
from app.program.api.messages_router import router as messages_router
from app.program.api.memory_router import router as memory_router

__all__ = ['register_routes']

def register_routes(app):
    """注册所有FastAPI路由"""
    app.include_router(health_router, tags=['health'])
    app.include_router(chats_router, tags=['chats'])
    app.include_router(messages_router, prefix='/api/chats', tags=['messages'])
    app.include_router(files_router, tags=['files'])
    app.include_router(models_router, tags=['models'])
    app.include_router(mcp_router, tags=['mcp'])
    app.include_router(embedding_models_router, tags=['embedding-models'])
    app.include_router(settings_router, tags=['settings'])
    app.include_router(memory_router, tags=['memory'])