import re
import traceback
from rag.llm import rewrite_llm
from rag.prompts import rewrite_prompt

# ==================== 定义查询重写（Rewrite）行为 ====================

async def question_rewriter(question):
    try:
        response = await rewrite_llm.ainvoke(rewrite_prompt.format_messages(question=question))
        raw_text = response.content
    except Exception as e:
        print(f"[Rewriter] ❌ LLM调用失败: {type(e).__name__}: {e}")
        traceback.print_exc()
        print(f"[Rewriter] ⚠️ 降级为原始问题，不做重写")
        return [question]

    rewrites = raw_text.strip().split('\n')
    cleaned_rewrites = []
    for rew in rewrites:
        rew_str = rew.strip()
        if rew_str and not rew_str.startswith(("好的", "这是", "以下", "要求")):
            # 去除可能存在的行首数字标记（例如 "1. ", "2) ", "3、" 等）
            cleaned_q = re.sub(r'^\d+[\s\.\)、\-]*', '', rew_str).strip()
            if cleaned_q:
                cleaned_rewrites.append(cleaned_q)
    queries = [question] + cleaned_rewrites[:2]

    if len(queries) <= 1:
        print(f"[Rewriter] ⚠️ 重写结果为空！原始响应:\n{raw_text}")
    else:
        # 简洁输出：只显示原始问题 + 生成视角数
        short_q = question[:40] + "..." if len(question) > 40 else question
        print(f"[Rewriter] \"{short_q}\" → {len(queries)} 个视角")

    return queries
