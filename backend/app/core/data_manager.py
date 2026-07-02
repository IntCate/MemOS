"""数据管理模块"""
import os
import yaml
from app.core.config import config_manager, DEFAULT_VECTOR_TOP_K, DEFAULT_VECTOR_SCORE_THRESHOLD
from app.utils.data.converters import convert_models_to_list, convert_embedding_models_to_list
from app.core.database import get_db, init_alembic_db
from app.core.logger import logger


def _load_yaml(filename: str) -> dict:
    """从 data/defaults/ 目录加载 YAML 配置文件"""
    current_dir = os.path.dirname(os.path.abspath(__file__))
    yaml_path = os.path.join(current_dir, '..', '..', 'data', 'defaults', filename)
    with open(yaml_path, 'r', encoding='utf-8') as f:
        return yaml.safe_load(f)


def _load_icon_blob(icon_name: str | None) -> str | None:
    """加载模型图标 SVG 内容，找不到时返回 None"""
    if not icon_name:
        return None
    backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    project_root = os.path.dirname(backend_dir)
    icon_dir = os.path.join(project_root, 'icon')

    for filename in [
        f'{icon_name}.svg',
        f'{icon_name.lower()}.svg',
        f'{icon_name.capitalize()}.svg',
    ]:
        icon_path = os.path.join(icon_dir, filename)
        if os.path.exists(icon_path):
            with open(icon_path, 'r', encoding='utf-8') as f:
                return f.read()
    return None


def ensure_data_dir():
    """确保数据目录存在"""
    user_data_dir = config_manager.get_user_data_dir()
    return user_data_dir


def init_db():
    """初始化SQLite数据库，创建表结构"""
    user_data_dir = ensure_data_dir()
    db_path = os.path.join(user_data_dir, 'config', 'memos.db')
    
    os.makedirs(os.path.dirname(db_path), exist_ok=True)
    
    init_alembic_db()
    logger.info(f"SQLite数据库初始化成功，数据库文件: {db_path}")


def init_vector_db():
    """初始化向量数据库，确保数据库文件存在"""
    try:
        from app.utils.path_manager import PathManager
        import lancedb
        
        vector_db_root = PathManager.get_vector_db_root()
        db = lancedb.connect(vector_db_root)
        table_names = db.table_names()
        
        logger.info(f"向量数据库初始化成功，路径: {vector_db_root}，现有表: {table_names}")
        return True, db
        
    except Exception as e:
        logger.error(f"向量数据库初始化失败: {str(e)}")
        return False, None


def insert_default_embedding_models():
    """插入默认嵌入模型数据到SQLite数据库"""
    logger.info("正在插入默认嵌入模型数据...")

    data = _load_yaml('default_embedding_models.yaml')
    default_embedding_providers = data.get('embedding_models', [])

    try:
        from app.program.repositories.embedding_model_repository import EmbeddingModelRepository

        db_session = next(get_db())
        embedding_model_repo = EmbeddingModelRepository(db_session)

        for provider in default_embedding_providers:
            model_data = {
                'name': provider['name'],
                'description': provider['description'],
                'type': provider['type'],
                'configured': False,
                'icon_url': f"/api/models/icons/{provider['name']}.svg",
                'icon_blob': _load_icon_blob(provider.get('icon_name')),
            }

            model_obj = embedding_model_repo.create_model(model_data)
            model_id = model_obj.id

            for version in provider.get('versions', []):
                version_data = {
                    'model_id': model_id,
                    'version_name': version['version_name'],
                    'custom_name': version.get('custom_name', ''),
                    'api_key': version.get('api_key', ''),
                    'api_base_url': version.get('api_base_url', ''),
                    'model_path': version.get('model_path', ''),
                    'dimension': version.get('dimension', 0),
                    'enabled': version.get('enabled', False),
                }
                embedding_model_repo.create_model_version(version_data)

        logger.info("默认嵌入模型数据插入完成")

    except Exception as e:
        logger.error(f"插入默认嵌入模型数据失败: {str(e)}")
        raise


def insert_default_models():
    """插入默认模型数据到SQLite数据库"""
    logger.info("正在插入默认模型数据...")

    data = _load_yaml('default_models.yaml')
    default_models = data.get('models', [])

    try:
        from app.program.repositories.model_repository import ModelRepository

        db_session = next(get_db())
        model_repo = ModelRepository(db_session)

        for model in default_models:
            model_obj = model_repo.create_or_update_model(
                name=model['name'],
                description=model['description'],
                configured=False,
                icon_url=f"/api/models/icons/{model['name']}.svg",
                icon_blob=_load_icon_blob(model.get('icon_name')),
            )

            model_id = model_obj.id

            for version in model.get('versions', []):
                model_repo.create_or_update_model_version(
                    model_id=model_id,
                    version_name=version['version_name'],
                    custom_name=version.get('custom_name', ''),
                    api_key=version.get('api_key', ''),
                    api_base_url=version.get('api_base_url', ''),
                    streaming_config=version.get('streaming_config', False),
                    enabled=version.get('enabled', False),
                )

        logger.info("默认模型数据插入完成")

    except Exception as e:
        logger.error(f"插入默认模型数据失败: {str(e)}")
        raise


def load_data():
    """加载数据"""
    user_data_dir = ensure_data_dir()
    
    db_path = os.path.join(user_data_dir, 'config', 'memos.db')
    db_file_exists = os.path.exists(db_path)
    
    try:
        init_db()
        init_vector_db()
        
        if not db_file_exists:
            logger.info("首次运行，插入默认数据...")
            insert_default_models()
            insert_default_embedding_models()
        else:
            logger.info("数据库文件已存在，跳过默认数据插入")
        
        logger.info("必要数据初始化成功")
    except Exception as e:
        logger.error(f"初始化数据时出错: {str(e)}")