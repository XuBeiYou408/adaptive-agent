import time
import os
import json
from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse

from app.schemas import QueryRequest
from rag.chain import question_answer_chain
from app.main import logger
from config import LOCAL_DB_PATH

# ==================== 创建路由 ====================
router = APIRouter()

# ==================== 健康检查 ====================
@router.get("/health")
def health():
    return {"status": "ok"}

# ==================== 普通问答接口 ====================
@router.post("/ask")
async def ask(req: QueryRequest):
    start_time = time.time()
    try:
        logger.info(f"收到问题: {req.question}")
        result = await question_answer_chain.ainvoke({
            "input": req.question
        })
        cost = round(time.time() - start_time, 2)
        logger.info(f"回答完成，耗时: {cost}s")
        return {
            "answer": result,
            "cost_time": cost
        }
    except Exception as e:
        logger.error(f"接口报错: {str(e)}")
        raise HTTPException(status_code=500, detail="内部错误")

# ==================== 流式接口（SSE标准） ====================
@router.post("/stream")
async  def stream(req: QueryRequest):#定义一个异步生成器函数
    async def generate():
        logger.info(f"异步流式请求: {req.question}")
        # 使用 astream 异步流式调用链
        async for chunk in question_answer_chain.astream({"input": req.question}):#从RAG链中一块一块拿生成结果
            yield f"data: {chunk}\n\n"
    return StreamingResponse(generate(), media_type="text/event-stream")#把生成器包装成 HTTP 响应
# ==================== 评估结果接口 ====================
@router.get("/evaluation/results")
def get_evaluation_results():
    path = os.path.join(LOCAL_DB_PATH, "evaluation_results.json")
    if not os.path.exists(path):
        raise HTTPException(status_code=404, detail="评估结果不存在，请先运行评估")
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

@router.get("/evaluation/dataset")
def get_dataset_info():
    path = os.path.join(LOCAL_DB_PATH, "golden_dataset.json")
    if not os.path.exists(path):
        raise HTTPException(status_code=404, detail="测试集不存在")
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    return {"count": len(data), "exists": True}