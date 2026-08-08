import os
from langchain_openai import ChatOpenAI

def huode_dongtai_llm(
    provider: str = "cloud",
    model_name: str = "deepseek-chat",
    streaming: bool = False,
    temperature: float = 0,
    max_tokens: int = 2048
) -> ChatOpenAI:
    """
    动态 LLM 工厂方法：根据前端传入的 provider ("cloud" / "local") 和 model_name 动态实例化 LangChain LLM
    """
    prov = (provider or "cloud").lower().strip()
    target_model = model_name or ("deepseek-chat" if prov == "cloud" else "qwen2.5:7b")

    if prov == "local":
        # 🏠 本地端侧部署 (Ollama 11434 端口)
        return ChatOpenAI(
            model=target_model,
            api_key="ollama",
            base_url="http://127.0.0.1:11434/v1",
            temperature=temperature,
            streaming=streaming,
            max_tokens=max_tokens,
            request_timeout=60,
        )
    else:
        # ☁️ 云端 API 模式 (DeepSeek / OpenAI 兼容协议)
        api_key = os.getenv('DEEPSEEK_API_KEY') or "sk-placeholder"
        base_url = os.getenv('DEEPSEEK_API_URL', 'https://api.deepseek.com')
        return ChatOpenAI(
            model=target_model,
            api_key=api_key,
            base_url=base_url,
            temperature=temperature,
            streaming=streaming,
            max_tokens=max_tokens,
            request_timeout=30,
        )

# 默认全局实例 (保持向后兼容)
rewrite_llm = huode_dongtai_llm(provider="cloud", model_name="deepseek-chat", streaming=False, max_tokens=150)
llm = huode_dongtai_llm(provider="cloud", model_name="deepseek-chat", streaming=True, max_tokens=2048)

