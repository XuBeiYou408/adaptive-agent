from config import LOCAL_DB_PATH, folder_path
import os
import pickle#保存docstore + 索引映射
import json
import hashlib#计算文件内容 → hash值，检测文件是否变化
from langchain_community.vectorstores import FAISS
from langchain_community.document_loaders import PyMuPDFLoader, TextLoader
from rag.embeddings import embeddings
from rag.splitter import pdf_qingxi, md_qingxi

ANIFEST_PATH = os.path.join(LOCAL_DB_PATH, "manifest.json") if LOCAL_DB_PATH else "local_db/manifest.json"

# ==================== FAISS 手动存取兼容 ====================
def _faiss_save(xiangliangshujuku, folder_path, index_name="xby"):
    folder_path = os.path.abspath(folder_path)# 将路径转化为绝对路径，防止相对路径在多线程/不同工作目录下失效
    os.makedirs(folder_path, exist_ok=True)# 如果 local_db 文件夹不存在，自动递归创建它
    import faiss# 延迟导入原生的 C++ FAISS 绑定的 Python 库
    cpu_index = xiangliangshujuku.index# 提取 LangChain 封装对象内部最核心的、存储高维向量的 C++ 索引对象
    try:
        # 如果当前索引运行在 GPU 上，将其转回 CPU，因为 GPU 索引无法直接序列化写盘
        if hasattr(faiss, 'index_gpu_to_cpu') and hasattr(cpu_index, 'at'):
            cpu_index = faiss.index_gpu_to_cpu(cpu_index)
    except Exception:
        pass
    idx_path = os.path.join(folder_path, f"{index_name}.faiss")# 拼接出向量索引文件的存储路径
    pkl_path = os.path.join(folder_path, f"{index_name}.pkl")# 拼接出文本映射文件的存储路径
    faiss.write_index(cpu_index, idx_path)
    with open(pkl_path, "wb") as f:#以 "wb"（二进制只写）模式打开 pkl 文件
        # 将 LangChain 内部的 docstore（文档商店）和 index_to_docstore_id（索引到ID的映射字典）打包成元组存入
        pickle.dump((xiangliangshujuku.docstore, xiangliangshujuku.index_to_docstore_id), f)
    print("向量数据库持久化到本地：", folder_path)

def _faiss_load(folder_path, index_name="xby"):
    import faiss
    idx_path = os.path.join(folder_path, f"{index_name}.faiss")
    pkl_path = os.path.join(folder_path, f"{index_name}.pkl")
    index = faiss.read_index(idx_path)
    with open(pkl_path, "rb") as f:# 以 "rb"（二进制只读）模式打开
        docstore, index_to_docstore_id = pickle.load(f)
    return FAISS(embeddings,index,docstore,index_to_docstore_id)

# ==================== 文件状态与哈希扫描器 ====================
def xiu_gai_jian_ce(filepath):
    hasher = hashlib.sha256()
    try:
        with open(filepath, 'rb') as f:
            while chunk := f.read(8192):# 采用海量数据分块流式读取（以 8KB 为一个缓冲区块）
                hasher.update( chunk)
        return hasher.hexdigest()
    except Exception:
        return ''

def sao_miao_geng_xin(target_folder):
    states ={}
    if not os.path.exists(target_folder):
        return states
    for root,_, files in os.walk(target_folder):# 深度优先递归遍历目标文件夹下的所有子目录和文件
        for file in files:
            if file.endswith(('.pdf', '.md')):
                full_path =os.path.abspath(os.path.join(root, file))# 生成该文件在当前操作系统下的绝对路径
                states[full_path] = {
                    'hash': xiu_gai_jian_ce(full_path),
                    'mtime': os.path.getmtime(full_path)
                }
    return  states

# ==================== 全量重建和动态增量更新 ====================
def quan_liang_chong_jian(current_states):
    try:
        print("🔄正在全量重建向量数据库...")
    except UnicodeEncodeError:
        print("[DB] 正在全量重建向量数据库...")
    from rag.loader import load_all_documents
    pdf_list ,md_list ,_ = load_all_documents()
    result_pdf = pdf_qingxi(pdf_list)
    result_md = md_qingxi(md_list)
    result_all = result_pdf + result_md
    safe_docs =[d for d in result_all if d.page_content and d.page_content.strip()]
    if not safe_docs:
        raise ValueError("未检测到有效的文档，取消重构")
    db =FAISS.from_documents(safe_docs, embeddings)
    _faiss_save(db, LOCAL_DB_PATH)
    with open(ANIFEST_PATH, "w",encoding="utf-8") as f:
        json.dump(current_states, f,ensure_ascii= False,indent=4)
    return  db,safe_docs

def zeng_liang_zhui_jia(added_files,current_states,old_manifest):
    try:
        print(f"🚀发现{len(added_files)}个新入库的文件，正在更新数据库")
    except UnicodeEncodeError:
        print(f"[DB] 发现{len(added_files)}个新入库的文件，正在更新数据库")
    db = _faiss_load(LOCAL_DB_PATH)# 先将本地已有的、健康的向量数据库加载到内存中
    new_chunks =[]
    for file_path in added_files:# 只循环处理新加入的绝对路径列表
        try:
            if file_path.endswith('.pdf'):
                loader = PyMuPDFLoader(file_path)# 单点触发针对该文件的专属 Loader
                new_chunks.extend(pdf_qingxi(loader.load()))
            elif file_path.endswith('.md'):
                loader = TextLoader(file_path,encoding='utf-8')
                new_chunks.extend(md_qingxi(loader.load()))
        except Exception as e:
            try:
                print(f'⚠️新文件加入失败{os.path.basename(file_path)}:{e}')
            except UnicodeEncodeError:
                print(f'[WARN] 新文件加入失败{os.path.basename(file_path)}:{e}')
    safe_new_chunks =[d for d in new_chunks if d.page_content and d.page_content.strip()]
    if safe_new_chunks:#工业级核心算子：只为新增加的知识节点计算 Embedding，并在原有的向量空间矩阵中做追加，零开销、免重构
        db.add_documents(safe_new_chunks)
        _faiss_save(db, LOCAL_DB_PATH)# 追加完成，立刻持久化覆盖本地老索引文件
        try:
            print(f"🚀更新向量数据库成功，已加入{len(safe_new_chunks)}个新文件")
        except UnicodeEncodeError:
            print(f"[DB] 更新向量数据库成功，已加入{len(safe_new_chunks)}个新文件")
    for f in added_files:
        old_manifest[f] = current_states[f]
    with open(ANIFEST_PATH, "w",encoding="utf-8") as f:
        json.dump(old_manifest, f,ensure_ascii= False,indent=4)
    return db

# ==================== 主干状态路由入口 ====================
def qi_dong_lu_jin():
    os.makedirs(LOCAL_DB_PATH, exist_ok=True)# 确保本地数据库目录存在
    current_states = sao_miao_geng_xin(folder_path)
    old_manifest ={}
    if os.path.exists(ANIFEST_PATH):
        try:
            with open(ANIFEST_PATH, "r",encoding="utf-8") as f:
                old_manifest = json.load(f)
        except Exception:
            old_manifest= {}
    db_exists = os.path.exists(os.path.join(LOCAL_DB_PATH, "xby.faiss"))# 检查本地是否已经有向量索引文件
    added_files = [f for f in current_states if f not in old_manifest ]# 1. 新增文件：在当前扫描结果里，但不在历史账本里
    deleted_files = [f for f in old_manifest if f not in current_states]# 2. 删除文件：在历史账本里，但现在从物理文件夹里消失了
    modified_files = [f for f in current_states if f in old_manifest and old_manifest[f]['hash']!=current_states[f]['hash']]# 3. 修改文件：两边都在，但比对两边的 SHA-256 哈希签名，发现内容对不上了
    if not db_exists or modified_files or deleted_files:
        # 触发全量重建红线：数据库丢失、或者发生了文件被篡改/文件被删除
        # 为什么删除/修改要全量重建？因为 FAISS 原生对底层单个向量的删除/改写支持代价极高，
        # 重建可以彻底清洗掉残留的“孤立子块”，保证向量空间百分之百的纯净与数据对齐。
        db,safe_docs = quan_liang_chong_jian(current_states)
    elif added_files:
        db = zeng_liang_zhui_jia(added_files,current_states,old_manifest)
        from rag.loader import load_all_documents
        pdf_list ,md_list ,_ = load_all_documents()
        safe_docs = pdf_qingxi(pdf_list) + md_qingxi(md_list)
    else:
        try:
            print("🚀向量数据库已存在且无需更新，急速加载中.....")
        except UnicodeEncodeError:
            print("[DB] 向量数据库已存在且无需更新，急速加载中.....")
        db = _faiss_load(LOCAL_DB_PATH)
        from rag.loader import load_all_documents
        pdf_list ,md_list ,_ = load_all_documents()
        safe_docs = pdf_qingxi(pdf_list)+ md_qingxi(md_list)
    return db,safe_docs
xiangliangshujuku,safe_all_wenjian = qi_dong_lu_jin()
