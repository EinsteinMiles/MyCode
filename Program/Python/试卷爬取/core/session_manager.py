"""
HTTP Session 管理器 — UA轮换、Cookie持久化、请求头管理。
"""

import os
import pickle
import threading
from pathlib import Path
from typing import Optional

import requests

logger = __import__("logging").getLogger(__name__)


class SessionManager:
    """管理每个站点的 requests.Session，支持 UA 轮换和 Cookie 持久化。"""

    def __init__(self, config=None):
        """
        Args:
            config: Config 对象或 dict
        """
        self.config = config
        self._sessions: dict[str, requests.Session] = {}
        self._lock = threading.Lock()

        # 加载 UA 列表
        self._user_agents = self._load_user_agents()
        self._ua_index = 0

        # Cookie 存储目录
        self._cookie_dir = Path(
            config.get("general", {}).get("cookie_dir", "./cookies")
            if hasattr(config, "get") else "./cookies"
        )

    def _load_user_agents(self) -> list[str]:
        """从配置加载 User-Agent 列表。"""
        defaults = [
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        ]
        if self.config and hasattr(self.config, "get"):
            return self.config.get("user_agents", defaults)
        return defaults

    def _next_ua(self) -> str:
        """轮换获取下一个 User-Agent。"""
        ua = self._user_agents[self._ua_index % len(self._user_agents)]
        self._ua_index += 1
        return ua

    def get_session(self, site_name: str) -> requests.Session:
        """获取或创建站点的 Session。"""
        with self._lock:
            if site_name not in self._sessions:
                session = requests.Session()
                session.headers.update({
                    "User-Agent": self._next_ua(),
                    "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
                    "Accept": "text/html,application/xhtml+xml,"
                              "application/xml;q=0.9,image/webp,*/*;q=0.8",
                    "Accept-Encoding": "gzip, deflate",
                    "Connection": "keep-alive",
                })

                # 加载持久化的 Cookie
                cookie_file = self._cookie_dir / f"{site_name}.pkl"
                if cookie_file.exists():
                    try:
                        with open(cookie_file, "rb") as f:
                            cookies = pickle.load(f)
                            for name, value in cookies.items():
                                session.cookies.set(name, value)
                        logger.info(f"已加载 {site_name} 的 Cookie")
                    except Exception as e:
                        logger.warning(f"加载 {site_name} Cookie 失败: {e}")

                self._sessions[site_name] = session

            # 每次获取时轮换 UA
            self._sessions[site_name].headers["User-Agent"] = self._next_ua()
            return self._sessions[site_name]

    def save_cookies(self, site_name: str):
        """持久化站点的 Cookie。"""
        session = self._sessions.get(site_name)
        if session:
            self._cookie_dir.mkdir(parents=True, exist_ok=True)
            try:
                with open(self._cookie_dir / f"{site_name}.pkl", "wb") as f:
                    pickle.dump(session.cookies.get_dict(), f)
                logger.info(f"已保存 {site_name} 的 Cookie")
            except Exception as e:
                logger.warning(f"保存 {site_name} Cookie 失败: {e}")

    def set_cookie(self, site_name: str, name: str, value: str):
        """手动设置某个站点的 Cookie。"""
        session = self.get_session(site_name)
        session.cookies.set(name, value)

    def set_cookies_from_string(self, site_name: str, cookie_string: str):
        """从浏览器复制的 Cookie 字符串设置 Cookie。"""
        session = self.get_session(site_name)
        for item in cookie_string.split(";"):
            item = item.strip()
            if "=" in item:
                name, value = item.split("=", 1)
                session.cookies.set(name.strip(), value.strip())

    def close_all(self):
        """关闭所有 Session。"""
        for session in self._sessions.values():
            session.close()
        self._sessions.clear()
