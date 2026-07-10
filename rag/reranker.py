import os
import torch

reranker = None

def _ensure_reranker_loaded():
    global reranker
    if reranker is None:
        from FlagEmbedding import FlagReranker
        import torch
        reranker_path = os.getenv('RERANKER_MODEL_PATH')
        try:
            if torch.cuda.is_available():
                reranker = FlagReranker(reranker_path, use_fp16=True)
                try:
                    print(" BGE Reranker 模型使用 GPU (CUDA) 加载成功。")
                except UnicodeEncodeError:
                    print("[Reranker] BGE Reranker model loaded successfully on GPU (CUDA).")
            else:
                reranker = FlagReranker(reranker_path, use_fp16=False)
                try:
                    print(" BGE Reranker 模型使用 CPU 加载成功。")
                except UnicodeEncodeError:
                    print("[Reranker] BGE Reranker model loaded successfully on CPU.")
        except RuntimeError as e:
            if "out of memory" in str(e).lower() or "cuda" in str(e).lower():
                try:
                    print("⚠️ 显存不足，BGE Reranker 正在安全降级到 CPU 加载...")
                except UnicodeEncodeError:
                    print("[Reranker] Out of VRAM. Falling back to CPU...")
                
                # 临时将 CUDA 屏蔽，强迫 PyTorch 使用 CPU
                old_cuda = os.environ.get("CUDA_VISIBLE_DEVICES", None)
                os.environ["CUDA_VISIBLE_DEVICES"] = "-1"
                reranker = FlagReranker(reranker_path, use_fp16=False)
                
                # 恢复 CUDA 环境变量
                if old_cuda is not None:
                    os.environ["CUDA_VISIBLE_DEVICES"] = old_cuda
                else:
                    del os.environ["CUDA_VISIBLE_DEVICES"]
                    
                try:
                    print(" BGE Reranker 降级到 CPU 加载完成。")
                except UnicodeEncodeError:
                    print("[Reranker] Loaded successfully on CPU fallback.")
            else:
                raise e

# ==================== 定义重排（Rerank）行为 ====================
TOP_K_RERANK = 5 # 与 retriever.FINAL_TOP_K 保持一致，确保消融实验公平对比

def reranker_doc(question, docs,reranker_limit= 60):
    _ensure_reranker_loaded()
    if len(docs) > reranker_limit:
        try:
            print(f"⚠️ [Warning] 召回文档数({len(docs)})异常超过安全水位，触发 {reranker_limit} 强截断。")
        except UnicodeEncodeError:
            print(f"[Warning] Recall docs count ({len(docs)}) exceeded safe level, truncating to {reranker_limit}.")
        docs = docs[:reranker_limit]
    valid_docs = [doc for doc in docs if doc.page_content and doc.page_content.strip()]  # 对召回 of document 数据进行 "" 或 None 排除
    bei_pinfenshuju = [[question, doc.page_content] for doc in valid_docs]
    fenshu = reranker.compute_score(bei_pinfenshuju, max_length=512)  # compute_score 内部指定 max_length=512
    fsandsjbangding = list(zip(fenshu, valid_docs))
    fsandsjbangding.sort(key=lambda x: x[0], reverse=True)
    chongpai = [doc for _, doc in fsandsjbangding[:TOP_K_RERANK]]
    return chongpai
