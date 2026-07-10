import logging
from langchain_core.prompts import PromptTemplate
try:
    from langchain.agents import create_react_agent, AgentExecutor
except ImportError:
    from langchain_classic.agents import create_react_agent, AgentExecutor

from rag.llm import llm
from rag.tools import xiangliang_and_bm25_zhaohui, jisuanqi_tool, wangye_sousuo_tool, wendang_zhaiyao_tool
from rag.memory import huode_huibao_jiliu

logger = logging.getLogger(__name__)

# ==================== 注册所有 Agent 工具 ====================
gongju_list = [xiangliang_and_bm25_zhaohui, jisuanqi_tool, wangye_sousuo_tool, wendang_zhaiyao_tool]

# ==================== 定义 ReAct Prompt 模板 ====================
# 重点：提示词中明确规范了 Thought, Action, Action Input, Observation, Final Answer 格式，
# 这是 ReAct Agent 进行多步推理和工具调用的基石。
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

# ==================== 创建 Agent ====================
agent = create_react_agent(llm, gongju_list, react_prompt)

# ==================== 创建 Agent 执行器 ====================
agent_executor = AgentExecutor(
    agent=agent,
    tools=gongju_list,
    verbose=True,
    max_iterations=8,                    # 限制最大步数，防死循环
    handle_parsing_errors=True,          # 容错机制，解析出错时让大模型自我修正
    return_intermediate_steps=True       # 开启中间步骤返回，支持思维链展示
)

# ==================== 会话执行包装函数 ====================
async def yunxing_agent_session(question: str, session_id: str) -> dict:
    """
    负责执行多步 Agent 推理，处理多轮对话记忆，并返回结构化的思考过程和最终答案。
    """
    # 1. 获取会话的记忆实例（自动适配 Redis/SQLite）
    history = huode_huibao_jiliu(session_id)
    
    # 2. 格式化历史消息为纯文本，注入 Prompt
    messages = history.messages
    chat_history_str = ""
    for msg in messages:
        role = "User" if msg.type == "human" else "AI"
        chat_history_str += f"{role}: {msg.content}\n"
        
    logger.info(f"[Agent] 开始处理会话 {session_id}，历史消息长度: {len(messages)}")
    
    # 3. 调用 Agent 执行器进行多步思考
    response = await agent_executor.ainvoke({
        "input": question,
        "chat_history": chat_history_str
    })
    
    final_output = response.get("output", "")
    intermediate_steps = response.get("intermediate_steps", [])
    
    # 4. 结构化解析思维链步骤
    thought_process = []
    for action, obs in intermediate_steps:
        # 尝试从 action.log 中提取 Thought 部分
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
        
    # 5. 更新会话历史（双向存入）
    history.add_user_message(question)
    history.add_ai_message(final_output)
    
    return {
        "answer": final_output,
        "thought_process": thought_process,
        "tools_used": list(set([step["tool"] for step in thought_process]))
    }
