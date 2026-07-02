"""嵌入模型基类"""
from abc import ABC, abstractmethod
from typing import List


class EmbeddingModel(ABC):
    """嵌入模型基类"""
    
    @abstractmethod
    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        """对文档列表进行嵌入
        
        Args:
            texts: 文本列表
        
        Returns:
            List[List[float]]: 嵌入向量列表
        """
        pass
    
    @abstractmethod
    def embed_query(self, text: str) -> List[float]:
        """对查询文本进行嵌入
        
        Args:
            text: 查询文本
        
        Returns:
            List[float]: 嵌入向量
        """
        pass