import logging
import os
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

# ==================== 日志系统 ====================
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ==================== 创建API ====================
app = FastAPI(
    title="RAG问答系统",
    description="BGE + Chroma + Rerank + FastAPI",
    version="2.0"
)

# ==================== 注册路由 ====================
from app.routes.ask import router
app.include_router(router)

# ==================== 静态文件托管（需在路由注册之后） ====================
STATIC_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "frontend", "dist")
if os.path.isdir(STATIC_DIR):
    app.mount("/", StaticFiles(directory=STATIC_DIR, html=True), name="static")
