import asyncio
import logging
from functools import wraps
from typing import Callable, Any

logger = logging.getLogger(__name__)

def with_retry(
    max_retries: int = 3,
    base_delay: float = 1.0,
    timeout: float = 30.0,
    fallback: Any = None
) -> Callable:
    """
    渐进式重试装饰器：
    Layer 1: asyncio.timeout 超时控制
    Layer 2: 指数退避重试（1s → 2s → 4s）
    Layer 3: 返回 fallback 降级兜底值
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs) -> Any:
            last_err = None
            for attempt in range(max_retries):
                try:
                    async with asyncio.timeout(timeout):
                        return await func(*args, **kwargs)
                except (asyncio.TimeoutError, Exception) as e:
                    last_err = e
                    if attempt < max_retries - 1:
                        delay = base_delay * (2 ** attempt)
                        logger.warning(f"[Retry] {func.__name__} 第 {attempt+1} 次尝试异常: {e}，将在 {delay}s 后重试...")
                        await asyncio.sleep(delay)
            
            logger.error(f"[Retry] {func.__name__} 经过 {max_retries} 次尝试全部失败: {last_err}")
            if fallback is not None:
                logger.info(f"[Retry] 触发降级兜底返回方案")
                return fallback() if callable(fallback) else fallback
            raise last_err
        return wrapper
    return decorator
