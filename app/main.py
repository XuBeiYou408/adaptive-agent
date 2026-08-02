import os
import logging
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from utils.logging_setup import setup_logging
from app.schemas import APIResponse

# 统一初始化安全结构化日志
setup_logging()
logger = logging.getLogger(__name__)

app = FastAPI(
    title="企业级自适应问答 Agent 系统",
    description="基于 LangChain + DeepSeek + FAISS + ReAct Agent + 混合检索的高可用企业知识库系统",
    version="2.1"
)

# 全局异常捕获处理 (T13)
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"全局未捕获异常: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content=APIResponse(code=500, message=f"服务器内部异常: {str(exc)}").model_dump()
    )

from app.routes.ask import router
app.include_router(router)

STATIC_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "frontend", "dist")
if os.path.isdir(STATIC_DIR):
    app.mount("/", StaticFiles(directory=STATIC_DIR, html=True), name="static")
