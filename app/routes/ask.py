import time
import os
import json
import logging
from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse

from app.schemas import QueryRequest, AgentQueryRequest, APIResponse
from rag.chain import question_answer_chain
from rag.agent import yunxing_agent_session, agent_executor
from rag.memory import huode_huibao_jiliu, qingkong_huibao_jiliu, compact_history
from rag.router import xitong_luyou
from rag.llm import rewrite_llm
from config import LOCAL_DB_PATH

logger = logging.getLogger(__name__)

router = APIRouter()

# ==================== 健康检查 ====================
@router.get("/health", response_model=APIResponse)
def health():
    return APIResponse(data={"status": "ok"})

# ==================== 普通问答接口 (T13: 响应结构规范化) ====================
@router.post("/ask", response_model=APIResponse)
async def ask(req: QueryRequest):
    start_time = time.time()
    try:
        logger.info(f"收到同步问答提问: {req.question}")
        result = await question_answer_chain.ainvoke({
            "input": req.question
        })
        cost = round(time.time() - start_time, 2)
        logger.info(f"问答响应完成，耗时: {cost}s")
        return APIResponse(data={
            "answer": result,
            "cost_time": cost
        })
    except Exception as e:
        logger.error(f"问答接口发生异常: {str(e)}")
        raise HTTPException(status_code=500, detail=f"服务内部错误: {str(e)}")

# ==================== 统一 SSE 流式分流接口 (T12) ====================
@router.post("/stream")
async def stream(req: AgentQueryRequest):
    """
    统一 SSE 流式入口：基于轻量路由分类自动分流
    - simple_rag: 走知识库快车道直出
    - agent: 走 ReAct Agent 推理链慢车道
    - summarize: 走摘要扩展通道
    """
    async def generate():
        logger.info(f"收到统一 SSE 流式请求: '{req.question}', 会话ID: {req.session_id}")
        
        # 1. 意图分流
        intent = await xitong_luyou(req.question)
        yield f"data: {json.dumps({'type': 'route', 'intent': intent}, ensure_ascii=False)}\n\n"
        
        if intent == "simple_rag":
            async for chunk in question_answer_chain.astream({"input": req.question}):
                yield f"data: {json.dumps({'type': 'content', 'content': chunk}, ensure_ascii=False)}\n\n"
        else:
            # 2. Agent / Summarize 通道统一接入带 Claude Code 微压缩的 Agent 协同机制
            history = huode_huibao_jiliu(req.session_id)
            chat_history_str = await compact_history(history.messages, rewrite_llm)
            
            final_output = ""
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
                    
            if final_output:
                history.add_user_message(req.question)
                history.add_ai_message(final_output)
                
        yield f"data: [DONE]\n\n"

    return StreamingResponse(generate(), media_type="text/event-stream")

# ==================== 评估结果接口 ====================
@router.get("/evaluation/results", response_model=APIResponse)
def get_evaluation_results():
    path = os.path.join(LOCAL_DB_PATH, "evaluation_results.json")
    if not os.path.exists(path):
        raise HTTPException(status_code=404, detail="评估结果不存在，请先运行评估")
    with open(path, "r", encoding="utf-8") as f:
        return APIResponse(data=json.load(f))

@router.get("/evaluation/dataset", response_model=APIResponse)
def get_dataset_info():
    path = os.path.join(LOCAL_DB_PATH, "golden_dataset.json")
    if not os.path.exists(path):
        raise HTTPException(status_code=404, detail="测试集不存在")
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    return APIResponse(data={"count": len(data), "exists": True})

# ==================== Agent 智能问答接口 ====================
@router.post("/agent/ask", response_model=APIResponse)
async def agent_ask(req: AgentQueryRequest):
    start_time = time.time()
    try:
        logger.info(f"收到 Agent 同步请求: '{req.question}', 会话ID: {req.session_id}")
        result = await yunxing_agent_session(req.question, req.session_id)
        cost = round(time.time() - start_time, 2)
        return APIResponse(data={
            "answer": result["answer"],
            "thought_process": result["thought_process"],
            "tools_used": result["tools_used"],
            "cost_time": cost
        })
    except Exception as e:
        logger.error(f"Agent 接口错误: {str(e)}")
        raise HTTPException(status_code=500, detail=f"内部错误: {str(e)}")

# ==================== Agent SSE 流式接口兼容别名 ====================
@router.post("/agent/stream")
async def agent_stream(req: AgentQueryRequest):
    return await stream(req)

# ==================== 清理会话记忆接口 ====================
@router.delete("/agent/memory/{session_id}", response_model=APIResponse)
def delete_memory(session_id: str):
    success = qingkong_huibao_jiliu(session_id)
    if success:
        return APIResponse(data={"status": "ok", "message": f"会话 {session_id} 记忆已成功清空"})
    raise HTTPException(status_code=500, detail="清空记忆失败")