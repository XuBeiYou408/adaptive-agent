import os
import subprocess
import sys
from dotenv import load_dotenv

# ==================== CUDA 安全检测与自动降级 ====================
def _jian_ce_cuda_anquan() -> bool:
    if "ANTIGRAVITY_TRAJECTORY_ID" in os.environ or "ANTIGRAPVITY_TRAJECTORY_ID" in os.environ:
        return False
    try:
        res = subprocess.run(
            [sys.executable, "-c", "import torch; torch.zeros(1).cuda()"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            timeout=3
        )
        return res.returncode == 0
    except Exception:
        return False

if not _jian_ce_cuda_anquan():
    os.environ["CUDA_VISIBLE_DEVICES"] = "-1"
    if sys.platform == "win32":
        try:
            import ctypes
            ctypes.windll.kernel32.SetEnvironmentVariableW("CUDA_VISIBLE_DEVICES", "-1")
        except Exception:
            pass

# 解决 Windows 上多个 OpenMP DLL (libiomp5md.dll) 冲突导致的 process exit(1) 闪退
os.environ["KMP_DUPLICATE_LIB_OK"] = "TRUE"

# ==================== 本地数据的读取 ====================
load_dotenv()
folder_path = os.getenv('YUAN_SUCAI_PATH')
LOCAL_DB_PATH = os.getenv('LOCAL_DB_PATH', './faiss-db')

# ==================== 统一系统超参数配置区 ====================
# 检索链路配置
TOP_K_RECALL: int = 35          # 向量/BM25 单路召回数
TOP_K_RERANK: int = 5           # Reranker 精排后保留数
RERANK_LIMIT: int = 45          # Reranker 输入截断水位线
REWRITE_QUERY_COUNT: int = 2    # 查询重写扩展视角数

# Agent 调度配置
AGENT_MAX_ITERATIONS: int = 8   # Agent 最大推理步数
AGENT_TIMEOUT: int = 120        # Agent 单次会话总超时（秒）

# 记忆与上下文配置 (Claude Code 风格微压缩)
REDIS_TTL: int = 7200           # Redis 会话缓存 TTL（秒）
CONTEXT_MAX_TOKENS: int = 4000  # 上下文窗口总 Token 预算
COMPACTION_THRESHOLD: int = 3000 # 触发微压缩的 Token 阈值

# 模型推理与网络配置
EMBEDDING_BATCH_SIZE: int = 64  # Embedding 推理批次大小
LLM_REQUEST_TIMEOUT: int = 30   # LLM API 超时（秒）
