# ====================  embedding模型 ====================
import os
import torch
from typing import List
from langchain_core.embeddings import Embeddings

class BGEEmbeddings(Embeddings):
    def __init__(self, model_name=None):
        self.model_name = model_name
        self.model = None
        self.device = "cuda" if torch.cuda.is_available() else "cpu"

    def _ensure_model_loaded(self):
        if self.model is None:
            from sentence_transformers import SentenceTransformer
            model_name = self.model_name
            if model_name is None:
                # 优先使用本地路径，避免 HF Hub 缓存解析问题
                model_name = os.getenv('BGE_MODEL_PATH', 'BAAI/bge-base-zh-v1.5')
            self.model = SentenceTransformer(model_name, device=self.device)
            try:
                print(f'✅ 本地BGE Embedding 模型已成功加载到内存中。')
            except UnicodeEncodeError:
                print(f'[OK] 本地BGE Embedding 模型已成功加载到内存中。')

    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        self._ensure_model_loaded()
        return self.model.encode(texts, normalize_embeddings=True).tolist()

    def embed_query(self, text: str) -> List[float]:
        self._ensure_model_loaded()
        return self.model.encode([text], normalize_embeddings=True)[
            0].tolist()  # normalize_embeddings=True向量归一化（让所有向量模长变为 1）方便向量数据库在后面计算相似度时直接做点积相乘加快检索速度;.tolist()将高维度的 NumPy 数组转换成 LangChain 认识 of Python 基础列表

embeddings = BGEEmbeddings()

