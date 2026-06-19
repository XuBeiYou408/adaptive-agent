# ====================  embedding模型 ====================
import os
from sentence_transformers import SentenceTransformer
import torch
from typing import List
from langchain_core.embeddings import Embeddings

class BGEEmbeddings(Embeddings):
    def __init__(self, model_name=None):
        if model_name is None:
            # 优先使用本地路径，避免 HF Hub 缓存解析问题
            model_name = os.getenv('BGE_MODEL_PATH', 'BAAI/bge-base-zh-v1.5')
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        self.model = SentenceTransformer(model_name, device=self.device)

    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        return self.model.encode(texts, normalize_embeddings=True).tolist()

    def embed_query(self, text: str) -> List[float]:
        return self.model.encode([text], normalize_embeddings=True)[
            0].tolist()  # normalize_embeddings=True向量归一化（让所有向量模长变为 1）方便向量数据库在后面计算相似度时直接做点积相乘加快检索速度;.tolist()将高维度的 NumPy 数组转换成 LangChain 认识的 Python 基础列表

embeddings = BGEEmbeddings()
print(f'✅ 本地BGE Embedding 模型加载完成。')
