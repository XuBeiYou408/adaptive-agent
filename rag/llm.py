import os
from langchain_openai import ChatOpenAI

# ==================== DeepSeek 直连（国内网络无需代理）====================

# 查询重写 LLM
rewrite_llm = ChatOpenAI(
    model="deepseek-chat",
    api_key=os.getenv('DEEPSEEK_API_KEY'),
    base_url=os.getenv('DEEPSEEK_API_URL'),
    temperature=0,
    max_tokens=150,
    request_timeout=30,
)

# 主 LLM（问答链用）
llm = ChatOpenAI(
    model="deepseek-chat",
    api_key=os.getenv('DEEPSEEK_API_KEY'),
    base_url=os.getenv('DEEPSEEK_API_URL'),
    temperature=0,
    streaming=True,
    max_tokens=2048,  # R2-L1 修复：提升 Token 限制防止回答截断
    request_timeout=30,
)
