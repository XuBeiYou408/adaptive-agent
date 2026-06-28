from langchain_core.prompts import ChatPromptTemplate

# ==================== 定义查询重写（Rewrite）提示词 ====================
rewrite_prompt = ChatPromptTemplate([
    ("system",
     "你是一个针对技术文档库的查询扩展助手。\n"
     "请基于用户问题，生成 3 个不同角度或语言的检索问题。\n"
     "要求：\n"
     "1. 保持语义高度相关。\n"
     "2. **中英双语扩展**：对于包含英文技术术语、代码概念或可能对应英文技术文档（如LangChain, Matplotlib, JSON, PyTorch等）的查询，生成的 3 个问题中必须包含 1-2 个针对性的英文检索词或检索短句（包括代码关键字或配置项，如 `langchain.debug = True` 或 `verbose=True`），以确保能够匹配英文原版文档。\n"
     "3. 每个检索问题用换行分隔，不要包含序号，不要解释。"),
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
