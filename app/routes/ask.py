import time
import os
import json
from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse

from app.schemas import QueryRequest, AgentQueryRequest
from rag.chain import question_answer_chain
from rag.agent import yunxing_agent_session, agent_executor
from rag.memory import huode_huibao_jiliu, qingkong_huibao_jiliu
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

# ==================== Agent 智能问答接口 ====================
@router.post("/agent/ask")
async def agent_ask(req: AgentQueryRequest):
    start_time = time.time()
    try:
        logger.info(f"收到 Agent 提问: '{req.question}', 会话ID: {req.session_id}")
        result = await yunxing_agent_session(req.question, req.session_id)
        cost = round(time.time() - start_time, 2)
        logger.info(f"Agent 回答完成，耗时: {cost}s")
        return {
            "answer": result["answer"],
            "thought_process": result["thought_process"],
            "tools_used": result["tools_used"],
            "cost_time": cost
        }
    except Exception as e:
        logger.error(f"Agent 接口报错: {str(e)}")
        raise HTTPException(status_code=500, detail="内部错误")

# ==================== Agent SSE 流式接口 ====================
@router.post("/agent/stream")
async def agent_stream(req: AgentQueryRequest):
    async def generate():
        logger.info(f"收到 Agent 流式请求: '{req.question}', 会话ID: {req.session_id}")
        
        # 1. 组装历史对话上下文
        history = huode_huibao_jiliu(req.session_id)
        messages = history.messages
        chat_history_str = ""
        for msg in messages:
            role = "User" if msg.type == "human" else "AI"
            chat_history_str += f"{role}: {msg.content}\n"
            
        final_output = ""
        # 2. 调用 astream 捕获中间的 AgentAction 和最终答案
        async for chunk in agent_executor.astream({
            "input": req.question,
            "chat_history": chat_history_str
        }):
            if "actions" in chunk:
                for action in chunk["actions"]:
                    yield f"data: {json.dumps({'type': 'thought', 'content': action.log}, ensure_ascii=False)}\n\n"
            elif "steps" in chunk:
                for step in chunk["steps"]:
                    yield f"data: {json.dumps({'type': 'observation', 'content': str(step.observation)}, ensure_ascii=False)}\n\n"
            elif "output" in chunk:
                final_output = chunk["output"]
                yield f"data: {json.dumps({'type': 'output', 'content': final_output}, ensure_ascii=False)}\n\n"
                
        # 3. 异步写入多轮记忆
        if final_output:
            history.add_user_message(req.question)
            history.add_ai_message(final_output)
            
    return StreamingResponse(generate(), media_type="text/event-stream")

# ==================== 清理会话记忆接口 ====================
@router.delete("/agent/memory/{session_id}")
def delete_memory(session_id: str):
    success = qingkong_huibao_jiliu(session_id)
    if success:
        return {"status": "ok", "message": f"会话 {session_id} 记忆已清空"}
    raise HTTPException(status_code=500, detail="清空记忆失败")