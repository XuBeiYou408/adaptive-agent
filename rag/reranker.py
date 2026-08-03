import os
import logging
import torch
from typing import List
from langchain_core.documents import Document
from config import TOP_K_RERANK

logger = logging.getLogger(__name__)

reranker = None

def _ensure_reranker_loaded() -> None:
    global reranker
    if reranker is None:
        from FlagEmbedding import FlagReranker
        reranker_path = os.getenv('RERANKER_MODEL_PATH')
        try:
            if torch.cuda.is_available():
                reranker = FlagReranker(reranker_path, use_fp16=True)
                logger.info("BGE Reranker 模型使用 GPU (CUDA) 加载成功。")
            else:
                reranker = FlagReranker(reranker_path, use_fp16=False)
                logger.info("BGE Reranker 模型使用 CPU 加载成功。")
        except RuntimeError as e:
            if "out of memory" in str(e).lower() or "cuda" in str(e).lower():
                logger.warning("显存不足，BGE Reranker 正在安全降级到 CPU 加载...")
                torch.cuda.empty_cache()
                os.environ["CUDA_VISIBLE_DEVICES"] = ""
                reranker = FlagReranker(reranker_path, use_fp16=False)
                logger.info("BGE Reranker 降级到 CPU 加载完成。")
            else:
                raise e

# ==================== 定义重排（Rerank）行为 ====================
def reranker_doc(question: str, docs: List[Document], reranker_limit: int = 60) -> List[Document]:
    _ensure_reranker_loaded()
    if len(docs) > reranker_limit:
        logger.warning(f"召回文档数({len(docs)})超出安全水位，触发 {reranker_limit} 强截断。")
        docs = docs[:reranker_limit]
        
    valid_docs = [doc for doc in docs if doc.page_content and doc.page_content.strip()]
    if not valid_docs:
        return []
        
    bei_pinfenshuju = [[question, doc.page_content] for doc in valid_docs]
    fenshu = reranker.compute_score(bei_pinfenshuju, max_length=512)
    fsandsjbangding = list(zip(fenshu, valid_docs))
    fsandsjbangding.sort(key=lambda x: x[0], reverse=True)
    chongpai = [doc for _, doc in fsandsjbangding[:TOP_K_RERANK]]
    return chongpai

rerank_documents = reranker_doc
