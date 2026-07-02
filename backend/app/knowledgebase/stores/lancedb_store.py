"""LanceDB知识库存储实现"""
import os
from typing import Dict, List, Optional, Any

from app.knowledgebase.protocol import (
    KnowledgeBaseStore, Document, SearchResult, KBStats
)
from app.core.logger import logger
from app.utils.path_manager import PathManager


class LanceDBStore(KnowledgeBaseStore):
    """LanceDB知识库存储实现"""
    
    def __init__(self, config: Dict[str, Any] = None):
        self.config = config or {}
        self.conn = None
        self._vector_store = None
        self._embedding = None
        self._db_path = self.config.get('db_path', PathManager.get_vector_db_root())
        os.makedirs(self._db_path, exist_ok=True)
    
    async def _ensure_connection(self):
        """确保连接到LanceDB"""
        if self.conn is None:
            import lancedb
            self.conn = lancedb.connect(self._db_path)
    
    async def _ensure_embedding(self):
        """确保加载嵌入模型"""
        if self._embedding is None:
            from app.knowledgebase.embeddings import get_embedding_model
            self._embedding = get_embedding_model(self.config.get('embedding_model', 'all-MiniLM-L6-v2'))
    
    async def _get_table(self, collection_name: str):
        """获取或创建表"""
        await self._ensure_connection()
        await self._ensure_embedding()
        
        from langchain_community.vectorstores import LanceDB
        from langchain_core.vectorstores import VectorStore
        
        table_names = self.conn.table_names()
        table_exists = collection_name in table_names
        
        if table_exists:
            self._vector_store = LanceDB(
                connection=self.conn,
                embedding=self._embedding,
                table_name=collection_name
            )
        else:
            import pyarrow as pa
            schema = pa.schema([
                ("vector", pa.list_(pa.float32())),
                ("text", pa.string()),
                ("metadata", pa.map_(pa.string(), pa.string()))
            ])
            self.conn.create_table(collection_name, schema=schema)
            self._vector_store = LanceDB(
                connection=self.conn,
                embedding=self._embedding,
                table_name=collection_name
            )
            
            try:
                table = self.conn.open_table(collection_name)
                table.create_fts_index("text", replace=True)
            except Exception as e:
                logger.warning(f"创建全文搜索索引失败: {e}")
        
        return self._vector_store
    
    async def add_documents(
        self,
        documents: List[Document],
        collection_name: str = "default",
        **kwargs
    ) -> List[str]:
        """添加文档到知识库"""
        await self._get_table(collection_name)
        
        langchain_docs = []
        for doc in documents:
            from langchain_core.documents import Document as LangChainDocument
            langchain_docs.append(LangChainDocument(
                page_content=doc.content,
                metadata=doc.metadata
            ))
        
        self._vector_store.add_documents(langchain_docs)
        return [doc.id for doc in documents]
    
    async def search(
        self,
        query: str,
        collection_name: str = "default",
        limit: int = 5,
        score_threshold: float = 0.0,
        **kwargs
    ) -> List[SearchResult]:
        """相似度搜索"""
        await self._get_table(collection_name)
        
        results = self._vector_store.similarity_search_with_score(query, k=limit)
        
        filtered_results = []
        for doc, score in results:
            if score >= score_threshold:
                filtered_results.append(SearchResult(
                    document=Document(
                        id=doc.metadata.get('document_id', ''),
                        content=doc.page_content,
                        metadata=doc.metadata
                    ),
                    score=score
                ))
        
        return filtered_results
    
    async def keyword_search(
        self,
        query: str,
        collection_name: str = "default",
        limit: int = 10,
        **kwargs
    ) -> List[SearchResult]:
        """关键词搜索"""
        await self._get_table(collection_name)
        
        if not hasattr(self._vector_store, "table"):
            return []
        
        table = self._vector_store.table
        
        def convert_to_docs(df):
            docs = []
            from langchain_core.documents import Document
            for _, row in df.iterrows():
                content = row.get('text', '') or row.get('page_content', '')
                doc = Document(
                    page_content=content,
                    metadata={k: v for k, v in row.items() if k not in ['text', 'page_content', 'vector']}
                )
                docs.append(doc)
            return docs
        
        from lancedb.query import MatchQuery
        
        fuzzy_query = MatchQuery(query, "text", fuzziness=2)
        fuzzy_results = table.search(fuzzy_query).limit(limit).to_pandas()
        fuzzy_docs = convert_to_docs(fuzzy_results)
        
        results = []
        for doc in fuzzy_docs:
            results.append(SearchResult(
                document=Document(
                    id=doc.metadata.get('document_id', ''),
                    content=doc.page_content,
                    metadata=doc.metadata
                ),
                score=0.0
            ))
        
        return results
    
    async def get_document(self, document_id: str, collection_name: str = "default") -> Optional[Document]:
        """根据ID获取文档"""
        await self._get_table(collection_name)
        
        if not hasattr(self._vector_store, "table"):
            return None
        
        table = self._vector_store.table
        try:
            results = table.search(f"document_id = '{document_id}'").limit(1).to_pandas()
            if len(results) > 0:
                row = results.iloc[0]
                return Document(
                    id=document_id,
                    content=row.get('text', '') or row.get('page_content', ''),
                    metadata={k: v for k, v in row.items() if k not in ['text', 'page_content', 'vector']}
                )
        except Exception as e:
            logger.warning(f"获取文档失败: {e}")
        
        return None
    
    async def delete_document(self, document_id: str, collection_name: str = "default") -> bool:
        """删除文档"""
        await self._get_table(collection_name)
        
        if hasattr(self._vector_store, "table"):
            try:
                self._vector_store.table.delete(f"document_id = '{document_id}'")
                return True
            except Exception as e:
                logger.warning(f"删除文档失败: {e}")
        
        return False
    
    async def delete_collection(self, collection_name: str) -> bool:
        """删除集合"""
        await self._ensure_connection()
        
        try:
            self.conn.drop_table(collection_name)
            return True
        except Exception as e:
            logger.warning(f"删除集合失败: {e}")
            return False
    
    async def list_documents(
        self,
        collection_name: str = "default",
        limit: int = 100
    ) -> List[Document]:
        """列出文档"""
        await self._get_table(collection_name)
        
        if not hasattr(self._vector_store, "table"):
            return []
        
        table = self._vector_store.table
        try:
            results = table.to_pandas().head(limit)
            documents = []
            for _, row in results.iterrows():
                documents.append(Document(
                    id=row.get('document_id', ''),
                    content=row.get('text', '') or row.get('page_content', ''),
                    metadata={k: v for k, v in row.items() if k not in ['text', 'page_content', 'vector']}
                ))
            return documents
        except Exception as e:
            logger.warning(f"列出文档失败: {e}")
            return []
    
    async def list_collections(self) -> List[str]:
        """列出所有集合"""
        await self._ensure_connection()
        return self.conn.table_names()
    
    async def get_stats(self, collection_name: Optional[str] = None) -> KBStats:
        """获取统计信息"""
        await self._ensure_connection()
        
        if collection_name:
            await self._get_table(collection_name)
            if hasattr(self._vector_store, "table"):
                return KBStats(
                    total_documents=self._vector_store.table.count_rows(),
                    total_vectors=self._vector_store.table.count_rows(),
                    collections=[collection_name]
                )
            return KBStats()
        
        all_collections = self.conn.table_names()
        total_docs = 0
        for col in all_collections:
            try:
                table = self.conn.open_table(col)
                total_docs += table.count_rows()
            except Exception:
                pass
        
        return KBStats(
            total_documents=total_docs,
            total_vectors=total_docs,
            collections=all_collections
        )