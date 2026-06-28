from concurrent.futures import ThreadPoolExecutor  # 从 Python 标准库中导入线程池执行器
from langchain_community.retrievers import BM25Retriever
import asyncio
from rag.vector_store import xiangliangshujuku, safe_all_wenjian
from rag.rewriter import question_rewriter
from rag.reranker import reranker_doc
from rag.dedup import deduplicate_docs
from langchain_core.documents import Document

# ==================== 定义检索（retriever）召回行为采用混合检索（Hybrid） ====================
TOP_K_RECALL = 35       # 每次检索召回的候选文档数
FINAL_TOP_K = 5          # 消融实验统一最终返回给评估器的文档数
zhaohui = xiangliangshujuku.as_retriever(search_kwargs={"k": TOP_K_RECALL})  # 召回的是Document数据

try:
    import rank_bm25
    bm25 = BM25Retriever.from_documents(safe_all_wenjian)  # BM25关键词检索
    bm25.k = TOP_K_RECALL
    print(" BM25 模型加载完成。")
except Exception as e:
    bm25 = None
    print(f"BM25 模型加载失败：{e}")

# ==================== 定义上下文如何拼接 ====================
def huidalaiyuan(docs):
    results = []
    for i, doc in enumerate(docs, start=1):
        source = doc.metadata.get('source', '未知')
        content = doc.page_content
        results.append(f"[文档{i}] 来源: {source}\n{content}")
    return "\n\n".join(results)

# ==================== 进行检索召回和重排及去重 ====================
def retrieve_single(q):  # 负责针对某一个具体的问题，同时去向量数据库和传统的 BM25 里捞数据
    docs_vector = zhaohui.invoke(q)
    docs_bm25 = bm25.invoke(q)[:6] if bm25 else []
    for d in docs_vector:
        d.metadata["retriever"] = "vector"
    for d in docs_bm25:
        d.metadata["retriever"] = "bm25"
    return docs_vector + docs_bm25

executor = ThreadPoolExecutor(max_workers=5)# 并行查询(开启线程池)
async def zhaohui_and_rerank(inputs ,rerank_limit=45,return_documents=False):
    if isinstance(inputs, dict):
        question = inputs['input']
    elif isinstance(inputs, str):
        question = inputs
    else:
        raise TypeError("zhaohui_and_rerank 接收到的 inputs 类型不合法，须为 dict 或 str")
    
    # 投机/并发检索：并行执行查询重写与对原始问题的第一次检索
    rewriter_task = asyncio.create_task(question_rewriter(question))
    original_retrieval_task = asyncio.to_thread(retrieve_single, question)
    
    queries, original_docs = await asyncio.gather(rewriter_task, original_retrieval_task)
    
    other_queries = [q for q in queries if q != question]
    if other_queries:
        other_results = await asyncio.to_thread(
            lambda: list(executor.map(retrieve_single, other_queries))
        )
        other_docs = [doc for sublist in other_results for doc in sublist]
        all_docs = original_docs + other_docs
    else:
        all_docs = original_docs

    all_docs = deduplicate_docs(all_docs)  # 文档去重
    chongpaishuju = await asyncio.to_thread(reranker_doc, question, all_docs, rerank_limit)
    expanded_docs =[]
    for doc in chongpaishuju:
        if 'dad_content' in doc.metadata:
            dad_doc = Document(
                page_content =doc.metadata['dad_content'],
                metadata = doc.metadata
            )
            expanded_docs.append(dad_doc)
        else:
            expanded_docs.append(doc)
    final_docs = deduplicate_docs(expanded_docs)
    if return_documents:
        return final_docs  # 如果是评测脚本调用，返回原装 List[Document]，保留 metadata 供判定命中
    return huidalaiyuan(final_docs)#如果是纯字符串输入，说明是 evaluator 本地评测脚本在调用返回原始的 Document 列表，供评测大盘顺畅读取 .page_content 并计算 Hit Rate / MRR
#输入一个用户问题 → 生成多个查询 → 并行检索文档 → 去重 → Rerank → 返回最终结果。