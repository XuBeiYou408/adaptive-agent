import logging
from typing import Literal
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from rag.llm import rewrite_llm
from utils.resilience import with_retry

logger = logging.getLogger(__name__)

# ==================== 意图识别路由 Prompt ====================
luyou_prompt = ChatPromptTemplate([
    ("system",
     "你是一个智能路由助手，负责将用户的技术提问分类到最合适的处理路径。\n"
     "你必须根据用户问题，只返回以下三个类别名之一，不要包含任何其他字符（如引号、句号、空格或任何解释说明）：\n\n"
     "1. 'simple_rag'：关于知识库中某个具体事实、配置、概念的简单单步查询，不需要复杂分析。\n"
     "   - 示例：'什么是FAISS'，'如何安装PyTorch'，'Chroma的本地路径是什么'\n"
     "2. 'summarize'：明确要求对某个主题、某技术领域的所有内容进行系统性概括、总结、整理或生成大纲的请求。\n"
     "   - 示例：'总结一下关于BGE的所有内容'，'帮我梳理一篇Python教程大纲'，'概括文档的核心要点'\n"
     "3. 'agent'：需要多步推理、调用计算器进行数学计算、需要联网检索最新互联网事实、或者涉及复杂多视角分析的提问。\n"
     "   - 示例：'计算 2**20 * 4 结果是多少'，'知识库外提问：今年高考时间'，'如何调试LangChain？对比并举例说明'\n\n"
     "请严格只输出以下三个字符串之一：'simple_rag'、'summarize'、'agent'。"),
    ("user", "{question}")
])

# ==================== 系统路由逻辑 (T9: 渐进式重试与自愈降级) ====================
@with_retry(max_retries=2, timeout=10.0, fallback="agent")
async def xitong_luyou(question: str) -> Literal["simple_rag", "summarize", "agent"]:
    """
    轻量快速的意图分类路由器，带 3 层容灾保护。
    """
    luyou_chain = luyou_prompt | rewrite_llm | StrOutputParser()
    res = await luyou_chain.ainvoke({"question": question})
    
    category = res.strip().lower().replace("'", "").replace('"', "").replace("`", "")
    for cat in ["simple_rag", "summarize", "agent"]:
        if cat in category:
            return cat
            
    return "agent"
