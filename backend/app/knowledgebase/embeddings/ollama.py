"""Ollama 嵌入模型实现"""
from typing import List
from .base import EmbeddingModel


class OllamaEmbedding(EmbeddingModel):
    """Ollama 嵌入模型实现"""
    
    def __init__(self, model_name: str, base_url: str = None):
        self._model_name = model_name
        self._base_url = base_url
        self._embeddings = None
        self._dimension = None
        self._initialize_model()
    
    def _initialize_model(self):
        try:
            try:
                from langchain_ollama import OllamaEmbeddings
            except ImportError:
                from langchain_community.embeddings import OllamaEmbeddings
            
            params = {
                'model': self._model_name
            }
            
            if self._base_url:
                params['base_url'] = self._base_url
            
            self._embeddings = OllamaEmbeddings(**params)
            
            test_vector = self.embed_query("测试文本")
            self._dimension = len(test_vector)
        except ImportError as e:
            raise ValueError(f"未安装必要的包: {str(e)}")
        except Exception as e:
            raise ValueError(f"初始化 Ollama 嵌入模型失败: {str(e)}")
    
    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        if not self._embeddings:
            raise ValueError("模型未初始化")
        return self._embeddings.embed_documents(texts)
    
    def embed_query(self, text: str) -> List[float]:
        if not self._embeddings:
            raise ValueError("模型未初始化")
        return self._embeddings.embed_query(text)
    
    @property
    def model_name(self) -> str:
        return self._model_name
    
    @property
    def dimension(self) -> int:
        return self._dimension