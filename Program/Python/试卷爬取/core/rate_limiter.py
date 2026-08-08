"""
令牌桶限速器 — 按域名控制请求频率，线程安全。
"""

import time
import threading
import logging

logger = logging.getLogger(__name__)


class RateLimiter:
    """按域名进行令牌桶限速。"""

    def __init__(self, config: dict = None):
        """
        Args:
            config: Config 对象或 dict，需支持 get_site_config(domain) 方法
        """
        self.config = config
        self._buckets: dict = {}       # domain -> bucket dict
        self._last_request: dict = {}  # domain -> timestamp
        self._lock = threading.Lock()

        # 默认配置
        self._default_delay = 3.0
        self._default_rpm = 10

    def wait(self, domain: str):
        """
        阻塞直到可以对 domain 发起请求。

        Args:
            domain: 站点域名（如 "shijuan1.com"）
        """
        # 获取站点配置
        delay = self._default_delay
        rpm = self._default_rpm

        if self.config:
            try:
                site_cfg = self.config.get_site_config(domain)
                delay = site_cfg.get("delay_between_requests_sec", delay)
                rpm = site_cfg.get("requests_per_minute", rpm)
            except Exception:
                pass

        with self._lock:
            # 令牌桶逻辑
            if domain not in self._buckets:
                self._buckets[domain] = {
                    "tokens": rpm,
                    "max_tokens": rpm,
                    "last_refill": time.time(),
                }

            bucket = self._buckets[domain]
            now = time.time()

            # 补充令牌
            elapsed = now - bucket["last_refill"]
            refill = elapsed * (rpm / 60.0)
            bucket["tokens"] = min(bucket["max_tokens"], bucket["tokens"] + refill)
            bucket["last_refill"] = now

            if bucket["tokens"] >= 1:
                bucket["tokens"] -= 1
            else:
                # 等待一个令牌
                wait_time = (1 - bucket["tokens"]) * (60.0 / rpm)
                bucket["tokens"] = 0
            wait_time_need = max(0, (1 - bucket["tokens"]) * (60.0 / rpm))
            if wait_time_need > 0:
                # release lock during sleep
                pass  # we hold the lock briefly, sleep below

        # 在锁外进行 sleep
        if bucket["tokens"] < 0:
            sleep_time = abs(bucket["tokens"]) * (60.0 / rpm)
            time.sleep(sleep_time)

        # 最小请求间隔
        if delay > 0:
            last = self._last_request.get(domain, 0)
            elapsed_since = time.time() - last
            if elapsed_since < delay:
                time.sleep(delay - elapsed_since)
            self._last_request[domain] = time.time()

    def reset(self, domain: str = None):
        """重置限速状态。"""
        with self._lock:
            if domain:
                self._buckets.pop(domain, None)
                self._last_request.pop(domain, None)
            else:
                self._buckets.clear()
                self._last_request.clear()
