"""向量相关API路由 - 使用独立 KnowledgeBase 层"""
from fastapi import APIRouter, Query, Body
from app.knowledgebase import get_knowledge_base_manager, KnowledgeBaseManager
from app.utils.error_handler import handle_api_errors

router = APIRouter(prefix='/api/vectors')


def get_kb_manager() -> KnowledgeBaseManager:
    return get_knowledge_base_manager()


@router.get("/search", tags=["vectors"])
@handle_api_errors()
async def search_vectors(query: str = Query(..., description="查询文本"), k: int = 5, collection_name: str = "default"):
    """根据查询向量检索相关文档"""
    kb = get_kb_manager()
    results = await kb.search(query, collection_name=collection_name, limit=k)
    
    return {
        "success": True,
        "results": [r.to_dict() for r in results],
        "result_count": len(results)
    }


@router.post("/search-documents", tags=["vectors"])
@handle_api_errors()
async def search_documents(
    query: str = Query(..., description="查询文本"), 
    k: int = 3, 
    score_threshold: float = 0.0, 
    search_type: str = "similarity", 
    collection_name: str = "default"
):
    """搜索相关文档"""
    kb = get_kb_manager()
    
    if search_type == "keyword":
        results = await kb.keyword_search(query, collection_name=collection_name, limit=k)
    else:
        results = await kb.search(query, collection_name=collection_name, limit=k, score_threshold=score_threshold)
    
    return {"success": True, "results": [r.to_dict() for r in results], "result_count": len(results)}


@router.get("/collections", tags=["vectors"])
@handle_api_errors()
async def list_collections():
    """列出所有集合"""
    kb = get_kb_manager()
    collections = await kb.list_collections()
    return {"success": True, "collections": collections}


@router.get("/stats", tags=["vectors"])
@handle_api_errors()
async def get_stats(collection_name: str = Query(None, description="集合名称")):
    """获取知识库统计信息"""
    kb = get_kb_manager()
    stats = await kb.get_stats(collection_name)
    return {"success": True, "stats": stats.to_dict()}