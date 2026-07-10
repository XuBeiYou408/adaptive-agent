import os
import subprocess
import sys
from dotenv import load_dotenv

# ==================== CUDA 安全检测与自动降级 ====================
# 原理：
# 1. 优先检测是否处于 Antigravity 沙箱后台测试环境（通过特征环境变量识别），如果是，直接强制使用 CPU 运行以防显存崩溃。
# 2. 否则，通过派生子进程预测试 CUDA 实际是否可用。若测试失败（显存不足/驱动故障），同样安全降级为 CPU。
def _jian_ce_cuda_anquan() -> bool:
    # 识别智能体后台测试运行特征
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

# 定义一个本地文件夹路径，数据库文件会自动创建并保存在这里
LOCAL_DB_PATH = os.getenv('LOCAL_DB_PATH')
