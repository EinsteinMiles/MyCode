"""
指数退避重试装饰器。

处理: 连接错误, HTTP 429/5xx, 超时
不重试: HTTP 404, 403 (权限错误)
"""

import functools
import time
import random
import logging

logger = logging.getLogger(__name__)

# 可重试的 HTTP 状态码
RETRIABLE_STATUSES = {429, 500, 502, 503, 504}

# 可重试的异常类型
RETRIABLE_EXCEPTIONS = (
    ConnectionError,
    TimeoutError,
    OSError,
)


def retry(
    max_attempts: int = 3,
    base_delay: float = 1.0,
    max_delay: float = 60.0,
    backoff_factor: float = 2.0,
    jitter: bool = True,
    retriable_statuses: set = None,
):
    """
    指数退避重试装饰器。

    Args:
        max_attempts: 最大尝试次数
        base_delay: 基础延迟（秒）
        max_delay: 最大延迟上限（秒）
        backoff_factor: 退避因子
        jitter: 是否添加随机抖动
        retriable_statuses: 可重试的 HTTP 状态码集合
    """
    statuses = retriable_statuses or RETRIABLE_STATUSES

    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            last_exception = None
            for attempt in range(1, max_attempts + 1):
                try:
                    return func(*args, **kwargs)
                except RETRIABLE_EXCEPTIONS as e:
                    last_exception = e
                    logger.debug(f"[{func.__name__}] 尝试 {attempt}/{max_attempts} 失败: {e}")
                except Exception as e:
                    # 检查是否是 HTTPError（来自 requests 库）
                    if hasattr(e, 'response') and e.response is not None:
                        status = e.response.status_code
                        if status in statuses:
                            last_exception = e
                            logger.debug(
                                f"[{func.__name__}] HTTP {status}, "
                                f"尝试 {attempt}/{max_attempts}"
                            )
                        else:
                            raise  # 不可重试的状态码，立即抛出
                    else:
                        raise  # 未知异常，立即抛出

                if attempt == max_attempts:
                    break

                delay = min(base_delay * (backoff_factor ** (attempt - 1)), max_delay)
                if jitter:
                    delay = delay * (0.5 + random.random())

                logger.debug(f"[{func.__name__}] {delay:.1f}s 后重试...")
                time.sleep(delay)

            logger.error(f"[{func.__name__}] 重试 {max_attempts} 次后仍然失败")
            raise last_exception

        return wrapper
    return decorator


class RetryableError(Exception):
    """标记一个异常为可重试的。"""
    pass
