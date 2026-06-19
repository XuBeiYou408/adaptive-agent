# ==================== 1. 强力静音消红防御塔（必须放在最顶部） ====================
import utils.noise_suppressor # noqa: F401 — 必须在所有其他导入之前执行
from dotenv import load_dotenv, find_dotenv
load_dotenv(find_dotenv())  # 从脚本所在目录加载 .env，不依赖工作目录

# ==================== 测试运行（取消注释以测试） ====================
# if __name__ == "__main__":
#     user_query = {'input': input("请输入问题：")}
#     print("\nAI 正在思考并回答：\n" + "-" * 40)
#     for chunk in question_answer_chain.stream(user_query):
#         print(chunk, end="", flush=True)
#     print("\n" + "-" * 40)

# ==================== FastAPI 服务化启动 ====================
if __name__ == "__main__":
    import uvicorn
    from app.main import app
    uvicorn.run(app, host="0.0.0.0", port=8000)
