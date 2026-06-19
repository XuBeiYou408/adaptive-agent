from langchain_core.prompts import ChatPromptTemplate

# ==================== 定义查询重写（Rewrite）提示词 ====================
rewrite_prompt = ChatPromptTemplate([
    ("system",
     "你是一个查询扩展助手。\n"
     "请基于用户问题，生成 3 个不同角度的检索问题。\n"
     "要求：\n"
     "1. 保持语义相关\n"
     "2. 每个问题侧重点不同\n"
     "3. 用换行分隔\n"
     "4. 不要解释"),
    ("user", "{question}")
])

# ==================== LLM的提示词 ====================
system_prompt = (
    "你是一个专业的 AI 技术导师。\n"
    "请严格基于以下从用户知识库中检索到的资料回答问题。\n"
    "如果没有相关内容，请回答：抱歉，在知识库中未找到。\n\n"
    "【参考资料】:\n{context}"
)

llm_prompt = ChatPromptTemplate([
    ('system', system_prompt),
    ('user', '{input}')
])
