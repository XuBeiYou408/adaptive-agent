from operator import itemgetter
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import RunnableLambda

from rag.llm import llm
from rag.prompts import llm_prompt, huode_llm_prompt
from rag.retriever import zhaohui_and_rerank

# ==================== 问答链的组装 ====================
def create_qa_chain(target_llm=None, provider="cloud", model_name="deepseek-chat"):
    use_llm = target_llm or llm
    dynamic_prompt = huode_llm_prompt(provider, model_name)
    return (
        {
            'context': RunnableLambda(lambda inp: zhaohui_and_rerank({'input': inp.get('input') if isinstance(inp, dict) else str(inp), 'target_llm': use_llm})),
            'input': RunnableLambda(lambda inp: inp.get('input') if isinstance(inp, dict) else str(inp))
        }
        | dynamic_prompt
        | use_llm
        | StrOutputParser()
    )

# 默认兼容实例
question_answer_chain = create_qa_chain(llm)
