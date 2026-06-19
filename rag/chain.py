from operator import itemgetter
from langchain_core.output_parsers import StrOutputParser

from rag.llm import llm
from rag.prompts import llm_prompt
from rag.retriever import zhaohui_and_rerank

# ==================== 问答链的组装 ====================
question_answer_chain = (
        {
            'context': zhaohui_and_rerank,  # 检索 + 重排
            'input': itemgetter('input')  # 用户输入
        }
        | llm_prompt  # Prompt模板
        | llm  # LLM调用
        | StrOutputParser()  # StrOutputParser 用于解析输出为字符串
)
