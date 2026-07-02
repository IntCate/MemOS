# app/llm/vendors/openai_model.py
from typing import Dict, Any
from app.engineering.llm.base.base_model import BaseModel

class OpenAIModel(BaseModel):
    """OpenAI模型驱动 (使用langchain)"""
    
    def _initialize_llm(self) -> None:
        """初始化langchain的OpenAI LLM实例"""
        from langchain_openai import ChatOpenAI
        
        selected_version = self._get_selected_version('gpt-3.5-turbo')
        api_key = self.version_config.get('api_key')
        base_url = self.version_config.get('base_url', None)
        
        if not api_key:
            raise Exception('OpenAI API密钥未配置')
        
        self.llm = ChatOpenAI(
            model=selected_version,
            api_key=api_key,
            base_url=base_url,
            timeout=180
        )
    
    def _prepare_call_kwargs(self, model_params: Dict[str, Any]) -> Dict[str, Any]:
        """
        预处理调用参数，移除OpenAI API不支持的参数
        """
        # OpenAI API不支持top_k参数
        filtered_params = {}
        for key, value in model_params.items():
            if key != 'top_k':
                filtered_params[key] = value
        return filtered_params
