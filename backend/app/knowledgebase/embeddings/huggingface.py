"""HuggingFace 嵌入模型实现"""
from typing import List, Dict, Any
from .base import EmbeddingModel


class HuggingFaceEmbedding(EmbeddingModel):
    """HuggingFace 嵌入模型实现"""
    
    def __init__(self, model_name: str, model_kwargs: Dict[str, Any] = None, encode_kwargs: Dict[str, Any] = None):
        self._model_name = model_name
        self._model_kwargs = model_kwargs or {'device': 'cpu'}
        self._encode_kwargs = encode_kwargs or {'normalize_embeddings': True}
        self._embeddings = None
        self._dimension = None
        self._initialize_model()
    
    def _initialize_model(self):
        try:
            try:
                from langchain_huggingface import HuggingFaceEmbeddings
            except ImportError:
                from langchain_community.embeddings import HuggingFaceEmbeddings
            
            self._embeddings = HuggingFaceEmbeddings(
                model_name=self._model_name,
                model_kwargs=self._model_kwargs,
                encode_kwargs=self._encode_kwargs
            )
            
            test_vector = self.embed_query("测试文本")
            self._dimension = len(test_vector)
        except Exception as e:
            raise ValueError(f"初始化 HuggingFace 嵌入模型失败: {str(e)}")
    
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