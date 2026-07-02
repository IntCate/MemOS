"""OpenAI 嵌入模型实现"""
from typing import List
from .base import EmbeddingModel


class OpenAIEmbedding(EmbeddingModel):
    """OpenAI 嵌入模型实现"""
    
    def __init__(self, model_name: str, api_key: str = None, api_base_url: str = None):
        self._model_name = model_name
        self._api_key = api_key
        self._api_base_url = api_base_url
        self._embeddings = None
        self._dimension = None
        self._initialize_model()
    
    def _initialize_model(self):
        try:
            from langchain_openai import OpenAIEmbeddings
            
            params = {
                'model': self._model_name
            }
            
            if self._api_key:
                params['api_key'] = self._api_key
            
            if self._api_base_url:
                params['base_url'] = self._api_base_url
            
            self._embeddings = OpenAIEmbeddings(**params)
            
            test_vector = self.embed_query("测试文本")
            self._dimension = len(test_vector)
        except ImportError:
            raise ValueError("未安装 langchain-openai 包")
        except Exception as e:
            raise ValueError(f"初始化 OpenAI 嵌入模型失败: {str(e)}")
    
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