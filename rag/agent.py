import logging
import asyncio
from typing import Dict, Any, List
from langchain_core.prompts import PromptTemplate
try:
    from langchain.agents import create_react_agent, AgentExecutor
except ImportError:
    from langchain_classic.agents import create_react_agent, AgentExecutor

from config import AGENT_MAX_ITERATIONS, AGENT_TIMEOUT
from rag.llm import llm, rewrite_llm
from rag.tools import xiangliang_and_bm25_zhaohui, jisuanqi_tool, wangye_sousuo_tool, wendang_zhaiyao_tool
from rag.memory import huode_huibao_jiliu, compact_history

logger = logging.getLogger(__name__)

# ==================== 注册所有 Agent 工具 ====================
gongju_list = [xiangliang_and_bm25_zhaohui, jisuanqi_tool, wangye_sousuo_tool, wendang_zhaiyao_tool]

# ==================== 定义 ReAct Prompt 模板 ====================
react_prompt = PromptTemplate.from_template(
    "你是一个全能的企业级 AI 技术导师，专门解答技术、架构与开发相关问题。\n"
    "为了圆满解答用户的问题，你可以分步骤思考并调用以下工具：\n\n"
    "{tools}\n\n"
    "请**严格**按照以下格式书写你的推理过程（每一行必须以标记词开始，不要有任何偏差）：\n\n"
    "Thought: 思考你目前需要做什么，或者是否已经可以直接回答问题。\n"
    "Action: 要调用的工具名称，必须是 [{tool_names}] 之一。\n"
    "Action Input: 传入工具的参数值（直接写，不要带引号或括号）。\n"
    "Observation: 工具执行返回的真实结果（你将会接收到该结果，不用自己生成）。\n"
    "...（上述 Thought/Action/Action Input/Observation 过程可以重复多次）\n"
    "Thought: 我现在已经掌握了所有必要的信息，可以回答用户了。\n"
    "Final Answer: 最终给用户的详实、准确且有条理的解答。\n\n"
    "现在开始！\n\n"
    "历史对话上下文：\n"
    "{chat_history}\n\n"
    "Question: {input}\n"
    "Thought: {agent_scratchpad}"
)

# ==================== 创建 Agent 执行器 ====================
agent = create_react_agent(llm, gongju_list, react_prompt)

agent_executor = AgentExecutor(
    agent=agent,
    tools=gongju_list,
    verbose=True,
    max_iterations=AGENT_MAX_ITERATIONS,
    handle_parsing_errors=True,
    return_intermediate_steps=True
)

# ==================== 会话执行包装函数 ====================
async def yunxing_agent_session(question: str, session_id: str) -> Dict[str, Any]:
    """
    负责执行多步 Agent 推理，带 Claude Code 同款就地微压缩与 120 秒超时熔断保护。
    """
    history = huode_huibao_jiliu(session_id)
    
    # 1. 优化点 (T4): Claude Code 同款就地微压缩 + 强约束摘要
    chat_history_str = await compact_history(history.messages, rewrite_llm)
    logger.info(f"[Agent] 开始处理会话 {session_id}，历史已微压缩")

    # 2. 优化点 (T10): asyncio.timeout 超时熔断机制
    try:
        async with asyncio.timeout(AGENT_TIMEOUT):
            response = await agent_executor.ainvoke({
                "input": question,
                "chat_history": chat_history_str
            })
    except asyncio.TimeoutError:
        logger.warning(f"[Agent] 会话 {session_id} 执行超时 ({AGENT_TIMEOUT}s)，触发超时熔断降级")
        return {
            "answer": "抱歉，由于问题复杂度较高或推理时间过长，触发了系统 120 秒安全超时限制。建议简化提示词或分步骤提问。",
            "thought_process": [],
            "tools_used": []
        }
    except Exception as e:
        logger.error(f"[Agent] 推理过程发生异常: {e}")
        return {
            "answer": f"系统推理发生异常: {str(e)}",
            "thought_process": [],
            "tools_used": []
        }
    
    final_output = response.get("output", "")
    intermediate_steps = response.get("intermediate_steps", [])
    
    thought_process = []
    for action, obs in intermediate_steps:
        log = action.log
        thought = log
        if "Action:" in log:
            thought = log.split("Action:")[0].replace("Thought:", "").strip()
            
        thought_process.append({
            "thought": thought,
            "tool": action.tool,
            "tool_input": action.tool_input,
            "observation": str(obs)
        })
        
    history.add_user_message(question)
    history.add_ai_message(final_output)
    
    return {
        "answer": final_output,
        "thought_process": thought_process,
        "tools_used": list(set([step["tool"] for step in thought_process]))
    }
