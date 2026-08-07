"""
DrissionPage 浏览器管理器
单例模式 + 健康检查 + 反检测配置 + Cookie 持久化

参考: DrissionPage 文档 - ChromiumPage, ChromiumOptions
"""

from __future__ import annotations

import os
import json
import time
import atexit
from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:
    from DrissionPage import ChromiumPage

from config import (
    HEADLESS, WINDOW_WIDTH, WINDOW_HEIGHT, BROWSER_IDLE_TIMEOUT,
    COOKIE_DIR, PAGE_LOAD_TIMEOUT, logger, MIN_DELAY, MAX_DELAY,
)
from core.utils import random_ua, random_delay


class BrowserManager:
    """DrissionPage 浏览器单例管理器"""

    _instance: Optional["BrowserManager"] = None
    _page: Optional[ChromiumPage] = None
    _last_used: float = 0.0
    _headless: bool = HEADLESS

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            atexit.register(cls._atexit_close)
        return cls._instance

    @classmethod
    def _atexit_close(cls):
        """atexit 钩子：进程退出时自动关闭浏览器"""
        try:
            if cls._page is not None:
                cls._page.quit()
                cls._page = None
        except Exception:
            pass

    @classmethod
    def get_page(cls, headless: Optional[bool] = None) -> ChromiumPage:
        """
        获取或创建 ChromiumPage 实例
        自动健康检查：进程死了就重启
        """
        if headless is not None:
            cls._headless = headless

        # 检查现有实例是否存活
        if cls._page is not None:
            try:
                # 尝试轻量操作检测连接
                cls._page.run_js("1+1")
                cls._last_used = time.time()
                return cls._page
            except Exception:
                logger.warning("浏览器连接断开，重新启动...")
                cls._page = None

        # 创建新实例
        cls._page = cls._create_page()
        cls._last_used = time.time()
        return cls._page

    @classmethod
    def new_tab(cls) -> ChromiumPage:
        """
        创建新标签页（用于并行任务隔离）
        返回一个新的 ChromiumPage 标签页
        """
        page = cls.get_page()
        tab = page.new_tab()
        cls._configure_tab(tab)
        return tab

    @classmethod
    def close(cls) -> None:
        """关闭浏览器"""
        if cls._page is not None:
            try:
                cls._page.quit()
            except Exception:
                pass
            cls._page = None
            logger.info("浏览器已关闭")

    @classmethod
    def check_idle(cls) -> None:
        """检查空闲超时，超时则关闭"""
        if cls._page is not None:
            idle = time.time() - cls._last_used
            if idle > BROWSER_IDLE_TIMEOUT:
                logger.info(f"浏览器空闲 {idle:.0f}s，自动关闭")
                cls.close()

    @classmethod
    def save_cookies(cls, platform: str) -> None:
        """保存当前浏览器 Cookie 到文件"""
        if cls._page is None:
            return
        try:
            cookies = cls._page.cookies()
            cookie_file = os.path.join(COOKIE_DIR, f"{platform}.json")
            with open(cookie_file, "w", encoding="utf-8") as f:
                json.dump(cookies, f, ensure_ascii=False, indent=2)
            logger.info(f"Cookie 已保存: {cookie_file}")
        except Exception as e:
            logger.warning(f"保存 Cookie 失败: {e}")

    @classmethod
    def load_cookies(cls, platform: str) -> bool:
        """从文件加载 Cookie 到浏览器"""
        cookie_file = os.path.join(COOKIE_DIR, f"{platform}.json")
        if not os.path.exists(cookie_file):
            return False

        page = cls.get_page()
        try:
            with open(cookie_file, "r", encoding="utf-8") as f:
                cookies = json.load(f)
            for cookie in cookies:
                try:
                    page.set.cookies(cookie)
                except Exception:
                    pass
            logger.info(f"Cookie 已加载: {cookie_file}")
            return True
        except Exception as e:
            logger.warning(f"加载 Cookie 失败: {e}")
            return False

    # ── 内部方法 ──────────────────────────────────────

    @classmethod
    def _create_page(cls):
        """创建并配置 ChromiumPage 实例"""
        from DrissionPage import ChromiumPage, ChromiumOptions
        import random as _random
        co = ChromiumOptions()

        # 使用随机端口避免冲突
        port = _random.randint(9223, 9999)
        co.set_local_port(port)

        # ── 持久化用户数据目录（避免每次都像全新浏览器）──
        try:
            base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        except NameError:
            base = os.getcwd()
        user_data = os.path.join(base, "data", "browser_profile")
        os.makedirs(user_data, exist_ok=True)
        co.set_user_data_path(user_data)

        # ── 反自动化检测参数 ──
        co.set_argument("--disable-blink-features=AutomationControlled")
        co.set_argument("--disable-features=AutomationControlled")  # 关键！
        co.set_argument("--disable-features=TranslateUI")
        co.set_argument("--disable-ipc-flooding-protection")
        co.set_argument("--no-first-run")
        co.set_argument("--no-default-browser-check")
        co.set_argument("--disable-default-apps")
        co.set_argument("--disable-sync")
        co.set_argument("--disable-breakpad")
        co.set_argument("--disable-component-update")
        co.set_argument("--disable-domain-reliability")
        co.set_argument("--disable-client-side-phishing-detection")
        co.set_argument("--disable-notifications")

        # 无头模式 — 使用 co.headless() 方法让 DrissionPage 正确识别
        if cls._headless:
            co.headless(True)
            co.set_argument("--disable-gpu")

        # 窗口大小（模拟真实屏幕）
        co.set_argument(f"--window-size={WINDOW_WIDTH},{WINDOW_HEIGHT}")

        # 创建页面
        page = ChromiumPage(co)
        cls._configure_tab(page)
        logger.info(f"浏览器已启动 (headless={cls._headless}, port={port})")
        return page

    @staticmethod
    def _configure_tab(page: ChromiumPage) -> None:
        """配置标签页反检测参数（针对淘宝/1688 增强）"""
        # 随机 UA（模拟 macOS Chrome）
        ua = random_ua()
        page.set.user_agent(ua)

        # 设置页面加载超时
        page.set.timeouts(PAGE_LOAD_TIMEOUT)

        # ── 执行反检测 JS（在页面加载前注入）──
        anti_detect_js = """
        // 1. 隐藏 webdriver 标记
        Object.defineProperty(navigator, 'webdriver', {get: () => undefined});

        // 2. chrome.runtime
        window.chrome = {
            runtime: {},
            loadTimes: function() {},
            csi: function() {},
            app: {}
        };

        // 3. plugins 数量（正常浏览器 > 0）
        Object.defineProperty(navigator, 'plugins', {
            get: () => {
                var arr = [1, 2, 3, 4, 5];
                arr.item = function(i) { return this[i]; };
                arr.namedItem = function(name) { return null; };
                arr.refresh = function() {};
                return arr;
            }
        });

        // 4. languages
        Object.defineProperty(navigator, 'languages', {
            get: () => ['zh-CN', 'zh', 'en-US', 'en']
        });

        // 5. platform
        Object.defineProperty(navigator, 'platform', {
            get: () => 'MacIntel'
        });

        // 6. hardwareConcurrency
        Object.defineProperty(navigator, 'hardwareConcurrency', {
            get: () => 8
        });

        // 7. deviceMemory
        Object.defineProperty(navigator, 'deviceMemory', {
            get: () => 8
        });

        // 8. maxTouchPoints
        Object.defineProperty(navigator, 'maxTouchPoints', {
            get: () => 0
        });

        // 9. permissions
        var origQuery = window.navigator.permissions.query;
        window.navigator.permissions.query = function(parameters) {
            if (parameters.name === 'notifications') {
                return Promise.resolve({state: Notification.permission});
            }
            return origQuery.call(this, parameters);
        };

        // 10. 移除 PhantomJS 痕迹
        delete window.callPhantom;
        delete window._phantom;
        delete window.__phantomas;

        // 11. 修复 iframe contentWindow
        try {
            var iframe = document.createElement('iframe');
            iframe.style.display = 'none';
            document.body.appendChild(iframe);
            var frameObj = iframe.contentWindow;
            document.body.removeChild(iframe);
        } catch(e) {}
        """
        try:
            page.run_js(anti_detect_js)
        except Exception:
            pass
