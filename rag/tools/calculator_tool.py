import math
from langchain.tools import tool

# ==================== 安全的数学计算命名空间 ====================
anquan_mingzi = {
    k: v for k, v in math.__dict__.items() if not k.startswith("__")
}
# 补充一些常用的基本代数名称
anquan_mingzi.update({
    'abs': abs,
    'round': round,
    'pow': pow,
    'min': min,
    'max': max
})

# ==================== 封装计算器工具为 Tool ====================
@tool
def jisuanqi_tool(expression: str) -> str:
    """
    一个用于计算数学表达式的计算器工具。
    适用于：需要精确数值计算、公式求值、内存字节计算、模型参数量相乘等场景。
    输入：标准的 Python 数学表达式，例如 "2**10" 或 "1024 * 1024 * 4"。
    输出：计算结果。
    """
    try:
        clean_expr = expression.strip()
        
        # 限制表达式长度防止拒绝服务
        if len(clean_expr) > 100:
            return "计算失败：表达式超出长度限制（最大 100 字符）。"
            
        # 安全沙箱求值
        result = eval(clean_expr, {"__builtins__": None}, anquan_mingzi)
        return str(result)
    except Exception as e:
        return f"计算错误：{str(e)}。请确保输入是合法的 Python 数学表达式，例如 '2 ** 10'。"
