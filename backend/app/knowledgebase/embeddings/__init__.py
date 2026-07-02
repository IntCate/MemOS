"""嵌入模型模块 - 知识库专用的嵌入模型管理"""
from .base import EmbeddingModel
from .huggingface import HuggingFaceEmbedding
from .openai import OpenAIEmbedding
from .ollama import OllamaEmbedding


def get_embedding_model(model_name: str = "all-MiniLM-L6-v2") -> EmbeddingModel:
    """获取嵌入模型实例
    
    Args:
        model_name: 模型名称，支持格式:
            - huggingface-all-MiniLM-L6-v2
            - openai-text-embedding-3-small
            - ollama-nomic-embed-text
    
    Returns:
        EmbeddingModel: 嵌入模型实例
    """
    if '-' in model_name:
        parts = model_name.split('-', 1)
        vendor = parts[0].lower()
        name = parts[1]
        
        if vendor == 'huggingface' or vendor == 'hf':
            return HuggingFaceEmbedding(name)
        elif vendor == 'openai' or vendor == 'oai':
            return OpenAIEmbedding(name)
        elif vendor == 'ollama':
            return OllamaEmbedding(name)
    
    return HuggingFaceEmbedding(model_name)