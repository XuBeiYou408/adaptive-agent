from config import LOCAL_DB_PATH, folder_path
import os
import pickle
import json
import hashlib
import logging
from typing import Tuple, List, Dict, Any
from langchain_community.vectorstores import FAISS
from langchain_community.document_loaders import PyMuPDFLoader, TextLoader
from langchain_core.documents import Document
from rag.embeddings import embeddings
from rag.splitter import pdf_qingxi, md_qingxi

logger = logging.getLogger(__name__)

ANIFEST_PATH = os.path.join(LOCAL_DB_PATH, "manifest.json") if LOCAL_DB_PATH else "local_db/manifest.json"

# ==================== FAISS 手动存取兼容 ====================
def _faiss_save(xiangliangshujuku: FAISS, folder_path: str, index_name: str = "xby") -> None:
    folder_path = os.path.abspath(folder_path)
    os.makedirs(folder_path, exist_ok=True)
    import faiss
    cpu_index = xiangliangshujuku.index
    try:
        if hasattr(faiss, 'index_gpu_to_cpu') and hasattr(cpu_index, 'at'):
            cpu_index = faiss.index_gpu_to_cpu(cpu_index)
    except Exception:
        pass
    idx_path = os.path.join(folder_path, f"{index_name}.faiss")
    pkl_path = os.path.join(folder_path, f"{index_name}.pkl")
    faiss.write_index(cpu_index, idx_path)
    with open(pkl_path, "wb") as f:
        pickle.dump((xiangliangshujuku.docstore, xiangliangshujuku.index_to_docstore_id), f)
    logger.info(f"向量数据库成功持久化到本地目录: {folder_path}")

def _faiss_load(folder_path: str, index_name: str = "xby") -> FAISS:
    import faiss
    idx_path = os.path.join(folder_path, f"{index_name}.faiss")
    pkl_path = os.path.join(folder_path, f"{index_name}.pkl")
    index = faiss.read_index(idx_path)
    with open(pkl_path, "rb") as f:
        docstore, index_to_docstore_id = pickle.load(f)
    return FAISS(embeddings, index, docstore, index_to_docstore_id)

# ==================== 文件状态与哈希扫描器 ====================
def xiu_gai_jian_ce(filepath: str) -> str:
    hasher = hashlib.sha256()
    try:
        with open(filepath, 'rb') as f:
            while chunk := f.read(8192):
                hasher.update(chunk)
        return hasher.hexdigest()
    except Exception:
        return ''

def sao_miao_geng_xin(target_folder: str) -> Dict[str, Dict[str, Any]]:
    states = {}
    if not os.path.exists(target_folder):
        return states
    for root, _, files in os.walk(target_folder):
        for file in files:
            if file.endswith(('.pdf', '.md')):
                full_path = os.path.abspath(os.path.join(root, file))
                states[full_path] = {
                    'hash': xiu_gai_jian_ce(full_path),
                    'mtime': os.path.getmtime(full_path)
                }
    return states

# ==================== 全量重建和动态增量更新 ====================
def quan_liang_chong_jian(current_states: Dict[str, Dict[str, Any]]) -> Tuple[FAISS, List[Document]]:
    logger.info("正在全量重建向量数据库...")
    from rag.loader import load_all_documents
    pdf_list, md_list, _ = load_all_documents()
    result_pdf = pdf_qingxi(pdf_list)
    result_md = md_qingxi(md_list)
    result_all = result_pdf + result_md
    safe_docs = [d for d in result_all if d.page_content and d.page_content.strip()]
    if not safe_docs:
        raise ValueError("未检测到有效的文档，取消重构")
    db = FAISS.from_documents(safe_docs, embeddings)
    _faiss_save(db, LOCAL_DB_PATH)
    with open(ANIFEST_PATH, "w", encoding="utf-8") as f:
        json.dump(current_states, f, ensure_ascii=False, indent=4)
    return db, safe_docs

def zeng_liang_zhui_jia(added_files: List[str], current_states: Dict[str, Dict[str, Any]], old_manifest: Dict[str, Any]) -> FAISS:
    logger.info(f"发现 {len(added_files)} 个新入库的文件，正在更新数据库")
    db = _faiss_load(LOCAL_DB_PATH)
    new_chunks = []
    for file_path in added_files:
        try:
            if file_path.endswith('.pdf'):
                loader = PyMuPDFLoader(file_path)
                new_chunks.extend(pdf_qingxi(loader.load()))
            elif file_path.endswith('.md'):
                loader = TextLoader(file_path, encoding='utf-8')
                new_chunks.extend(md_qingxi(loader.load()))
        except Exception as e:
            logger.warning(f"新文件加入失败 {os.path.basename(file_path)}: {e}")
            
    safe_new_chunks = [d for d in new_chunks if d.page_content and d.page_content.strip()]
    if safe_new_chunks:
        db.add_documents(safe_new_chunks)
        _faiss_save(db, LOCAL_DB_PATH)
        logger.info(f"更新向量数据库成功，已加入 {len(safe_new_chunks)} 个新文件")
        
    for f in added_files:
        old_manifest[f] = current_states[f]
    with open(ANIFEST_PATH, "w", encoding="utf-8") as f:
        json.dump(old_manifest, f, ensure_ascii=False, indent=4)
    return db

# ==================== 主干状态路由与损坏自愈 (T7) ====================
def qi_dong_lu_jin() -> Tuple[FAISS, List[Document]]:
    os.makedirs(LOCAL_DB_PATH, exist_ok=True)
    current_states = sao_miao_geng_xin(folder_path)
    old_manifest = {}
    if os.path.exists(ANIFEST_PATH):
        try:
            with open(ANIFEST_PATH, "r", encoding="utf-8") as f:
                old_manifest = json.load(f)
        except Exception:
            old_manifest = {}
            
    db_exists = os.path.exists(os.path.join(LOCAL_DB_PATH, "xby.faiss"))
    added_files = [f for f in current_states if f not in old_manifest]
    deleted_files = [f for f in old_manifest if f not in current_states]
    modified_files = [f for f in current_states if f in old_manifest and old_manifest[f]['hash'] != current_states[f]['hash']]
    
    if not db_exists or modified_files or deleted_files:
        db, safe_docs = quan_liang_chong_jian(current_states)
    elif added_files:
        db = zeng_liang_zhui_jia(added_files, current_states, old_manifest)
        from rag.loader import load_all_documents
        pdf_list, md_list, _ = load_all_documents()
        safe_docs = pdf_qingxi(pdf_list) + md_qingxi(md_list)
    else:
        logger.info("向量数据库已存在且无需更新，尝试加载...")
        try:
            db = _faiss_load(LOCAL_DB_PATH)
        except Exception as e:
            # 优化点 (T7): 向量库损坏自愈
            logger.warning(f"本地向量库文件损坏 ({e})，触发自动全量重建自愈机制...")
            db, safe_docs = quan_liang_chong_jian(current_states)
            return db, safe_docs
            
        from rag.loader import load_all_documents
        pdf_list, md_list, _ = load_all_documents()
        safe_docs = pdf_qingxi(pdf_list) + md_qingxi(md_list)
        
    return db, safe_docs

# ==================== 优化点 (T1): 惰性初始化工厂与单例缓存 ====================
_db_instance: FAISS | None = None
_safe_docs_cache: List[Document] | None = None

def get_vector_store() -> Tuple[FAISS, List[Document]]:
    """
    惰性初始化工厂：在调用时触发数据库与文档加载，
    消灭模块导入阶段（import vector_store）即触发的巨石构建耗时。
    """
    global _db_instance, _safe_docs_cache
    if _db_instance is None or _safe_docs_cache is None:
        _db_instance, _safe_docs_cache = qi_dong_lu_jin()
    return _db_instance, _safe_docs_cache

# 动态属性/魔术加载以兼容原有的全局变量引用
class _LazyVectorDBProxy:
    def __getattr__(self, name):
        db, _ = get_vector_store()
        return getattr(db, name)

class _LazyDocsProxy(list):
    def __init__(self):
        super().__init__()
    def _ensure_loaded(self):
        if not self:
            _, docs = get_vector_store()
            self.extend(docs)
    def __iter__(self):
        self._ensure_loaded()
        return super().__iter__()
    def __len__(self):
        self._ensure_loaded()
        return super().__len__()
    def __getitem__(self, item):
        self._ensure_loaded()
        return super().__getitem__(item)

xiangliangshujuku = _LazyVectorDBProxy()
safe_all_wenjian = _LazyDocsProxy()
