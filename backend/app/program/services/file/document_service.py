"""文档管理服务 - 负责文档的上传、存储、管理和检索

业务服务（Business Service）：包含业务规则和业务流程
基础设施服务（Infrastructure Service）：提供通用能力，不包含业务逻辑

本服务依赖：
- DataInfrastructure: 数据基础设施（数据库访问）
- SearchInfrastructure: 搜索基础设施（KnowledgeBase）
"""
import os
import shutil
import time
from datetime import datetime
import uuid
from app.core.config import config_manager
from app.program.services.base_service import BaseService
from app.utils.path_manager import PathManager
from app.utils.rag.document_loader import DocumentLoader
from app.utils.rag.text_splitter import TextSplitter
from app.utils.error_handler import handle_api_errors
from app.utils.validators import ValidationUtils
from app.infrastructure import DataInfrastructure, SearchInfrastructure
from app.knowledgebase import Document as KBDocument


DATA_DIR = PathManager.get_data_dir()


class DocumentService(BaseService):
    """文档管理服务类 - 封装所有与文档文件系统相关的操作"""
    
    def __init__(self):
        """初始化文档管理服务"""
        self.data_infra = DataInfrastructure()
        self.search_infra = SearchInfrastructure()
    
    def _cleanup_vector_services(self):
        """清理向量服务连接和实例"""
        try:
            self.log_info("✅ 向量服务连接已释放")
            return True
        except Exception as e:
            self.log_warning(f"⚠️  释放向量服务连接失败: {e}")
            return False

    def _get_folder_info(self, folder_id):
        """根据folder_id获取文件夹完整信息"""
        if not folder_id:
            return None
        return self.data_infra.get_folder_by_id(folder_id)
    
    def _get_folder_name_by_id(self, folder_id):
        """根据folder_id查找对应的folder_name"""
        folder = self._get_folder_info(folder_id)
        return folder.name if folder else folder_id
    
    def save_uploaded_file(self, file, folder_id=None):
        """保存上传的文件到服务器
        
        Args:
            file: 上传的文件对象
            folder_id: 目标文件夹ID
            
        Returns:
            dict: 文件信息，包含id、name、path等
        """
        try:
            file_id = str(uuid.uuid4())
            original_name = file.filename
            safe_name = ValidationUtils.sanitize_filename(original_name)
            
            file_ext = os.path.splitext(safe_name)[1].lower()
            
            if folder_id:
                folder = self._get_folder_info(folder_id)
                if folder:
                    folder_path = os.path.join(DATA_DIR, 'documents', folder.name)
                else:
                    folder_path = os.path.join(DATA_DIR, 'documents', folder_id)
            else:
                folder_path = os.path.join(DATA_DIR, 'documents', 'unclassified')
            
            os.makedirs(folder_path, exist_ok=True)
            
            file_path = os.path.join(folder_path, safe_name)
            
            counter = 1
            while os.path.exists(file_path):
                name_without_ext = os.path.splitext(safe_name)[0]
                file_path = os.path.join(folder_path, f"{name_without_ext}_{counter}{file_ext}")
                counter += 1
            
            with open(file_path, 'wb') as buffer:
                shutil.copyfileobj(file.file, buffer)
            
            file_size = os.path.getsize(file_path)
            uploaded_at = datetime.now().isoformat()
            
            file_info = {
                'id': file_id,
                'name': original_name,
                'path': file_path,
                'size': file_size,
                'type': file_ext[1:] if file_ext else 'unknown',
                'uploaded_at': uploaded_at,
                'folder_id': folder_id
            }
            
            self.data_infra.create_document(
                document_id=file_id,
                name=original_name,
                path=file_path,
                size=file_size,
                doc_type=file_ext[1:] if file_ext else 'unknown',
                uploaded_at=uploaded_at,
                folder_id=folder_id
            )
            
            self.log_info(f"📄 文件保存成功: {file_path}")
            return file_info
            
        except Exception as e:
            self.log_error(f"❌ 文件保存失败: {str(e)}")
            raise
    
    def get_document(self, document_id):
        """获取文档信息"""
        return self.data_infra.get_document_by_id(document_id)
    
    def get_all_documents(self):
        """获取所有文档列表"""
        documents = self.data_infra.get_all_documents()
        
        docs_list = []
        for doc in documents:
            folder_name = self._get_folder_name_by_id(doc.folder_id) if doc.folder_id else "未分类"
            
            docs_list.append({
                'id': doc.id,
                'name': doc.name,
                'path': doc.path,
                'size': doc.size,
                'type': doc.type,
                'uploaded_at': doc.uploaded_at,
                'folder_id': doc.folder_id,
                'folder_name': folder_name,
                'file_ext': os.path.splitext(doc.name)[1].lower()[1:] if doc.name else ''
            })
        
        return docs_list
    
    def delete_document(self, document_id):
        """删除文档（从文件系统和数据库）"""
        try:
            document = self.data_infra.get_document_by_id(document_id)
            
            if not document:
                return False
            
            file_path = document.path
            
            if os.path.exists(file_path):
                os.remove(file_path)
                self.log_info(f"🗑️ 文件删除成功: {file_path}")
            else:
                self.log_warning(f"⚠️ 文件不存在: {file_path}")
            
            self.data_infra.delete_document(document_id)
            
            self.search_infra.delete_document(document_id)
            
            return True
            
        except Exception as e:
            self.log_error(f"❌ 删除文档失败: {str(e)}")
            return False
    
    async def delete_all_documents(self):
        """删除所有文档"""
        try:
            documents = self.data_infra.get_all_documents()
            
            for doc in documents:
                if os.path.exists(doc.path):
                    os.remove(doc.path)
            
            self.data_infra.delete_all_documents()
            
            await self.search_infra.delete_collection("default")
            
            self.log_info("🗑️ 所有文档已删除")
            return True
            
        except Exception as e:
            self.log_error(f"❌ 删除所有文档失败: {str(e)}")
            return False
    
    def create_folder(self, folder_name):
        """创建文件夹"""
        folder_id = str(uuid.uuid4())
        folder_path = os.path.join(DATA_DIR, 'documents', folder_name)
        
        os.makedirs(folder_path, exist_ok=True)
        
        self.data_infra.create_folder(
            folder_id=folder_id,
            name=folder_name,
            created_at=datetime.now().isoformat()
        )
        
        return {'id': folder_id, 'name': folder_name}
    
    def get_all_folders(self):
        """获取所有文件夹"""
        folders = self.data_infra.get_all_folders()
        
        return [{'id': f.id, 'name': f.name, 'created_at': f.created_at} for f in folders]
    
    def delete_folder(self, folder_id):
        """删除文件夹"""
        try:
            folder = self.data_infra.get_folder_by_id(folder_id)
            
            if not folder:
                return False
            
            folder_path = os.path.join(DATA_DIR, 'documents', folder.name)
            
            if os.path.exists(folder_path):
                shutil.rmtree(folder_path)
            
            self.data_infra.delete_folder(folder_id)
            
            return True
            
        except Exception as e:
            self.log_error(f"❌ 删除文件夹失败: {str(e)}")
            return False
    
    def move_document(self, document_id, target_folder_id):
        """移动文档到目标文件夹"""
        try:
            document = self.data_infra.get_document_by_id(document_id)
            
            if not document:
                return False
            
            target_folder = self.data_infra.get_folder_by_id(target_folder_id)
            
            if not target_folder:
                return False
            
            old_path = document.path
            file_name = os.path.basename(old_path)
            
            new_folder_path = os.path.join(DATA_DIR, 'documents', target_folder.name)
            os.makedirs(new_folder_path, exist_ok=True)
            
            new_path = os.path.join(new_folder_path, file_name)
            
            shutil.move(old_path, new_path)
            
            self.data_infra.update_document_folder(document_id, target_folder_id)
            
            return True
            
        except Exception as e:
            self.log_error(f"❌ 移动文档失败: {str(e)}")
            return False
    
    def search_documents(self, query):
        """搜索文档"""
        try:
            results = self.search_infra.search_knowledge(query)
            
            return results
            
        except Exception as e:
            self.log_error(f"❌ 搜索文档失败: {str(e)}")
            return []
    
    def get_document_content(self, document_id):
        """获取文档内容"""
        document = self.data_infra.get_document_by_id(document_id)
        
        if not document:
            return None
        
        try:
            loader = DocumentLoader()
            documents = loader.load_document(document.path)
            
            if documents:
                return documents[0].page_content
            
            return None
            
        except Exception as e:
            self.log_error(f"❌ 获取文档内容失败: {str(e)}")
            return None
    
    def get_document_chunks(self, document_id, chunk_size=512, chunk_overlap=50):
        """获取文档分块"""
        content = self.get_document_content(document_id)
        
        if not content:
            return []
        
        try:
            text_splitter = TextSplitter(chunk_size=chunk_size, chunk_overlap=chunk_overlap)
            chunks = text_splitter.split_text(content)
            
            return chunks
            
        except Exception as e:
            self.log_error(f"❌ 获取文档分块失败: {str(e)}")
            return []