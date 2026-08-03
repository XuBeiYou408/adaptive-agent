from operator import itemgetter
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import RunnableLambda

from rag.llm import llm
from rag.prompts import llm_prompt
from rag.retriever import zhaohui_and_rerank

# ==================== 问答链的组装 ====================
# 修复：itemgetter 与 zhaohui_and_rerank 均为普通可调用对象，需用 RunnableLambda
# 包装后才支持 LangChain 的 `|` 管道组合（Runnable 协议）
question_answer_chain = (
        {
            'context': RunnableLambda(itemgetter('input')) | RunnableLambda(zhaohui_and_rerank),  # 显式提取 input 字符串后检索
            'input': RunnableLambda(itemgetter('input'))  # 用户输入
        }
        | llm_prompt  # Prompt模板
        | llm  # LLM调用
        | StrOutputParser()  # StrOutputParser 用于解析输出为字符串
)
