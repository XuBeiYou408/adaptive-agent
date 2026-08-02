from pydantic import BaseModel
from typing import Optional, Any

# ==================== 请求结构 ====================
class QueryRequest(BaseModel):
    question: str

class AgentQueryRequest(BaseModel):
    question: str
    session_id: str = "default_session"

# ==================== 优化点 (T13): 统一 API 响应模型 ====================
class APIResponse(BaseModel):
    code: int = 200
    message: str = "ok"
    data: Optional[Any] = None
