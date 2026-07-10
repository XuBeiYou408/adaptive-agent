import os
import logging
from langchain_core.chat_history import BaseChatMessageHistory
from langchain_community.chat_message_histories import SQLChatMessageHistory, RedisChatMessageHistory

logger = logging.getLogger(__name__)

# ==================== 记忆配置 ====================
REDIS_URL = os.getenv("REDIS_URL", None)
LOCAL_DB_PATH = os.getenv("LOCAL_DB_PATH", "./faiss-db")
# 规范化 SQLite 路径，Windows 下需确保路径兼容性
sqlite_absolute_path = os.path.abspath(os.path.join(LOCAL_DB_PATH, "agent_memory.db"))
SQLITE_DB_URL = f"sqlite:///{sqlite_absolute_path.replace(os.sep, '/')}"

# ==================== 自适应获取会话记忆 ====================
def huode_huibao_jiliu(session_id: str) -> BaseChatMessageHistory:
    """
    根据配置自适应获取会话历史存储后端。
    1. 优先尝试 Redis（带 2 小时 TTL 自动过期，防爆缓存）。
    2. 若 Redis 未配置或连接失败，则安全降级为本地 SQLite 文件数据库，保证系统高可用。
    """
    if REDIS_URL:
        try:
            import redis
            # 建立临时的 Ping 测试，确保 Redis 服务真的活着
            pool = redis.ConnectionPool.from_url(REDIS_URL, socket_timeout=3)
            client = redis.Redis(connection_pool=pool)
            client.ping()
            
            logger.info(f"[Memory] 🚀 成功连接 Redis 会话缓存。Session: {session_id}")
            # 使用 Redis 作为后端并设置 TTL（7200秒/2小时）
            return RedisChatMessageHistory(
                session_id=f"agent:session:{session_id}",
                url=REDIS_URL,
                key_prefix="agent:session:",
                ttl=7200
            )
        except Exception as e:
            logger.warning(f"[Memory] ⚠️ Redis 配置存在但无法连接 ({type(e).__name__}): {e}。自动降级为 SQLite。")
            
    # SQLite 降级方案
    try:
        # 确保 DB 文件夹存在
        os.makedirs(os.path.dirname(sqlite_absolute_path), exist_ok=True)
        logger.info(f"[Memory] 💾 降级使用本地 SQLite 会话存储。DB: {sqlite_absolute_path}")
        return SQLChatMessageHistory(
            session_id=session_id,
            connection=SQLITE_DB_URL,
            table_name="message_store"
        )
    except Exception as e:
        logger.error(f"[Memory] ❌ SQLite 初始化失败：{e}。将降级为临时内存记忆。")
        from langchain_core.chat_history import InMemoryChatMessageHistory
        return InMemoryChatMessageHistory()

# ==================== 清空会话记忆 ====================
def qingkong_huibao_jiliu(session_id: str) -> bool:
    """
    手动清空指定会话的记忆数据。
    """
    try:
        history = huode_huibao_jiliu(session_id)
        history.clear()
        logger.info(f"[Memory] 🧹 已成功清空会话 {session_id} 的全部历史记忆。")
        return True
    except Exception as e:
        logger.error(f"[Memory] ❌ 清空会话 {session_id} 记忆失败: {e}")
        return False
