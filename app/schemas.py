from pydantic import BaseModel

# ==================== 请求结构 ====================
class QueryRequest(BaseModel):
    question: str

class AgentQueryRequest(BaseModel):
    question: str
    session_id: str = "default_session"

