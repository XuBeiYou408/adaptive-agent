from pydantic import BaseModel

# ==================== 请求结构 ====================
class QueryRequest(BaseModel):
    question: str
