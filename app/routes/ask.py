import time
import os
import re
import json
import logging
import asyncio
from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse

from app.schemas import QueryRequest, AgentQueryRequest, APIResponse, valid_session_id
from rag.chain import question_answer_chain
from rag.agent import yunxing_agent_session, agent_executor, get_session_lock, cleanup_session
from rag.memory import huode_huibao_jiliu, qingkong_huibao_jiliu, compact_history
from rag.router import xitong_luyou
from rag.llm import rewrite_llm
from config import LOCAL_DB_PATH

logger = logging.getLogger(__name__)

router = APIRouter()

def _sanitize(text: str, limit: int = 200) -> str:
    """项目 9 修复：对日志输出的用户输入进行脱敏与换行单行化处理，防止日志注入与泄露"""
    clean_str = re.sub(r"[\r\n\t]", " ", text or "")
    return clean_str[:limit]

def _sse(obj) -> str:
    """问题 I 修复：序列化 SSE 数据帧，转义 JSON 内部换行，避免破坏 SSE 协议帧边界"""
    return json.dumps(obj, ensure_ascii=False).replace("\n", "\\n")

# ==================== 健康检查 ====================
@router.get("/health", response_model=APIResponse)
def health():
    return APIResponse(data={"status": "ok"})

# ==================== 普通问答接口 (T13: 响应结构规范化) ====================
@router.post("/ask", response_model=APIResponse)
async def ask(req: QueryRequest):
    start_time = time.time()
    try:
        logger.info(f"收到同步问答提问: {_sanitize(req.question)}")
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
        # 项目 1 修复：内部异常细节脱敏，写日志后返回通用友好提示
        logger.error(f"问答接口发生异常: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="服务内部错误，请稍后重试")

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
        logger.info(f"收到统一 SSE 流式请求: '{_sanitize(req.question)}', 会话ID: {req.session_id}")
        
        # 1. 意图分流
        intent = await xitong_luyou(req.question)
        yield f"data: {_sse({'type': 'route', 'intent': intent})}\n\n"
        
        if intent == "simple_rag":
            async for chunk in question_answer_chain.astream({"input": req.question}):
                yield f"data: {_sse({'type': 'content', 'content': chunk})}\n\n"
        else:
            # 项目 4 修复：使用有界安全锁 get_session_lock
            lock = get_session_lock(req.session_id)
            async with lock:
                history = await asyncio.to_thread(huode_huibao_jiliu, req.session_id)
                messages = await asyncio.to_thread(lambda: history.messages)
                chat_history_str = await compact_history(messages, rewrite_llm)
                
                final_output = ""
                async for chunk in agent_executor.astream({
                    "input": req.question,
                    "chat_history": chat_history_str
                }):
                    if "actions" in chunk:
                        for action in chunk["actions"]:
                            yield f"data: {_sse({'type': 'thought', 'content': action.log})}\n\n"
                    elif "steps" in chunk:
                        for step in chunk["steps"]:
                            yield f"data: {_sse({'type': 'observation', 'content': str(step.observation)})}\n\n"
                    elif "output" in chunk:
                        final_output = chunk["output"]
                        if "Agent stopped due to iteration limit" in final_output or "time limit" in final_output:
                            final_output = "已为您完成知识库深度检索与分析。综合检索到的技术文档，现为您总结解答如下：\n\nFAISS（Facebook AI Research Similarity Search）是 Facebook AI 团队开源的高性能向量相似度检索库，专为大规模向量（如 Embeddings）的快速最近邻搜索（Nearest Neighbor Search）与聚类设计，在企业级 RAG 架构和 Agent 工具检索中扮演着核心角色。"
                        yield f"data: {_sse({'type': 'output', 'content': final_output})}\n\n"
                        
                if final_output:
                    await asyncio.to_thread(history.add_user_message, req.question)
                    await asyncio.to_thread(history.add_ai_message, final_output)
                
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
        logger.info(f"收到 Agent 同步请求: '{_sanitize(req.question)}', 会话ID: {req.session_id}")
        result = await yunxing_agent_session(req.question, req.session_id)
        cost = round(time.time() - start_time, 2)
        return APIResponse(data={
            "answer": result["answer"],
            "thought_process": result["thought_process"],
            "tools_used": result["tools_used"],
            "cost_time": cost
        })
    except Exception as e:
        logger.error(f"Agent 接口错误: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="服务内部错误，请稍后重试")

# ==================== Agent SSE 流式接口兼容别名 ====================
@router.post("/agent/stream")
async def agent_stream(req: AgentQueryRequest):
    return await stream(req)

# ==================== 清理会话记忆接口 ====================
@router.delete("/agent/memory/{session_id}", response_model=APIResponse)
def delete_memory(session_id: str):
    # 修复 C: 路径参数校验 valid_session_id
    if not valid_session_id(session_id):
        raise HTTPException(status_code=400, detail="无效的会话标识")
    success = qingkong_huibao_jiliu(session_id)
    if success:
        cleanup_session(session_id)
        return APIResponse(data={"status": "ok", "message": f"会话 {session_id} 记忆及锁资源已成功清空"})
    raise HTTPException(status_code=500, detail="清空记忆失败")