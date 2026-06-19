import os
# ==================== 重排模型导入 ====================
from FlagEmbedding import FlagReranker
reranker_path = os.getenv('RERANKER_MODEL_PATH')
reranker = FlagReranker(reranker_path, use_fp16=True)

# ==================== 定义重排（Rerank）行为 ====================
TOP_K_RERANK = 5 # 与 retriever.FINAL_TOP_K 保持一致，确保消融实验公平对比

def reranker_doc(question, docs,reranker_limit= 60):
    if len(docs) > reranker_limit:
        print(f"⚠️ [Warning] 召回文档数({len(docs)})异常超过安全水位，触发 {reranker_limit} 强截断。")
        docs = docs[:reranker_limit]
    valid_docs = [doc for doc in docs if doc.page_content and doc.page_content.strip()]  # 对召回的document数据进行"" 或 None排除
    bei_pinfenshuju = [[question, doc.page_content] for doc in valid_docs]
    fenshu = reranker.compute_score(bei_pinfenshuju, max_length=512)  # compute_score 内部指定 max_length=512
    fsandsjbangding = list(zip(fenshu, valid_docs))
    fsandsjbangding.sort(key=lambda x: x[0], reverse=True)
    chongpai = [doc for _, doc in fsandsjbangding[:TOP_K_RERANK]]
    return chongpai
