"""
DrissionPage Browser Manager — Cross-Border Edition
Singleton + health check + anti-detection + Cookie persistence
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
    COOKIE_DIR, PAGE_LOAD_TIMEOUT, logger,
)
from core.utils import random_ua


class BrowserManager:
    """DrissionPage browser singleton manager"""

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
        try:
            if cls._page is not None:
                cls._page.quit()
                cls._page = None
        except Exception:
            pass
        # Force-kill any lingering Chrome processes using our profile
        try:
            import subprocess
            subprocess.run(
                ["pkill", "-f", "user-data-dir=.*browser_profile"],
                capture_output=True, timeout=10
            )
        except Exception:
            pass

    @classmethod
    def get_page(cls, headless: Optional[bool] = None) -> ChromiumPage:
        """Get or create ChromiumPage (auto health check)"""
        if headless is not None:
            cls._headless = headless

        if cls._page is not None:
            try:
                cls._page.run_js("1+1")
                cls._last_used = time.time()
                return cls._page
            except Exception:
                logger.warning("Browser disconnected, restarting...")
                cls._page = None

        cls._page = cls._create_page()
        cls._last_used = time.time()
        return cls._page

    @classmethod
    def new_tab(cls) -> ChromiumPage:
        """Create a new tab"""
        page = cls.get_page()
        tab = page.new_tab()
        cls._configure_tab(tab)
        return tab

    @classmethod
    def close(cls) -> None:
        if cls._page is not None:
            try:
                cls._page.quit()
            except Exception:
                pass
            cls._page = None
            logger.info("Browser closed")

    @classmethod
    def check_idle(cls) -> None:
        if cls._page is not None:
            idle = time.time() - cls._last_used
            if idle > BROWSER_IDLE_TIMEOUT:
                logger.info(f"Browser idle {idle:.0f}s, auto-closing")
                cls.close()

    @classmethod
    def save_cookies(cls, platform: str) -> None:
        if cls._page is None:
            return
        try:
            cookies = cls._page.cookies()
            cookie_file = os.path.join(COOKIE_DIR, f"{platform}.json")
            with open(cookie_file, "w", encoding="utf-8") as f:
                json.dump(cookies, f, ensure_ascii=False, indent=2)
            logger.info(f"Cookies saved: {cookie_file}")
        except Exception as e:
            logger.warning(f"Save cookies failed: {e}")

    @classmethod
    def load_cookies(cls, platform: str) -> bool:
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
            logger.info(f"Cookies loaded: {cookie_file}")
            return True
        except Exception as e:
            logger.warning(f"Load cookies failed: {e}")
            return False

    # ── Browser creation ─────────────────────────────

    @classmethod
    def _create_page(cls):
        """Create and configure ChromiumPage with fallback strategies"""
        from DrissionPage import ChromiumPage, ChromiumOptions

        co = ChromiumOptions()

        # ── Persistent user data directory (builds browser trust over time) ──
        try:
            base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        except NameError:
            base = os.getcwd()
        user_data = os.path.join(base, "data", "browser_profile")
        os.makedirs(user_data, exist_ok=True)
        co.set_user_data_path(user_data)

        # ── Port ──
        import random as _random
        port = _random.randint(9223, 9999)
        co.set_local_port(port)
        co.set_argument(f"--remote-debugging-port={port}")

        # ── Stability flags only (avoid anti-detection flags — they're fingerprints) ──
        co.set_argument("--no-sandbox")
        co.set_argument("--disable-dev-shm-usage")

        # ── Normal Chrome behavior flags ──
        co.set_argument("--no-first-run")
        co.set_argument("--no-default-browser-check")
        co.set_argument("--disable-default-apps")
        co.set_argument("--disable-sync")
        co.set_argument("--disable-breakpad")
        co.set_argument("--disable-component-update")
        co.set_argument("--disable-notifications")

        co.set_argument(f"--window-size={WINDOW_WIDTH},{WINDOW_HEIGHT}")

        if cls._headless:
            co.headless(True)

        # ── Attempt to launch, killing stale instances if needed ──
        for attempt in range(3):
            try:
                page = ChromiumPage(co)
                cls._configure_tab(page)
                logger.info(f"Browser started (headless={cls._headless}, port={port})")
                return page
            except Exception as e:
                err_msg = str(e)
                if attempt < 2:
                    logger.warning(f"Launch attempt {attempt + 1} failed ({e}), retrying...")
                    # Kill any stale Chrome using our profile
                    try:
                        import subprocess
                        subprocess.run(
                            ["pkill", "-f", f"user-data-dir=.*browser_profile"],
                            capture_output=True, timeout=10
                        )
                    except Exception:
                        pass
                    time.sleep(2)
                    port = _random.randint(9223, 9999)
                    co.set_local_port(port)
                    co.set_argument(f"--remote-debugging-port={port}")
                else:
                    raise

    # ── Tab configuration ────────────────────────────

    @staticmethod
    def _configure_tab(page: ChromiumPage) -> None:
        """Inject comprehensive anti-detection JS and configure tab"""
        ua = random_ua()
        page.set.user_agent(ua)
        page.set.timeouts(PAGE_LOAD_TIMEOUT)

        anti_detect_js = """
        // ── Core anti-detection ──
        // Set webdriver to false (NOT undefined — modern detection checks both)
        Object.defineProperty(navigator, 'webdriver', {get: () => false});

        // Fake Chrome runtime (CDP detection uses this)
        window.chrome = {
            runtime: { connect: function() {}, sendMessage: function() {}, onConnect: {addListener: function(){}, removeListener: function(){}} },
            loadTimes: function() { return {}; },
            csi: function() { return {}; },
            app: { isInstalled: false, InstallState: { DISABLED: 'disabled', INSTALLED: 'installed', NOT_INSTALLED: 'not_installed' }, RunningState: { CANNOT_RUN: 'cannot_run', READY_TO_RUN: 'ready_to_run', RUNNING: 'running' } }
        };

        // ── Fake plugins (Chrome's real built-in plugins) ──
        (function() {
            var makePlugin = function(name, filename, description) {
                return {
                    name: name, filename: filename, description: description,
                    length: 0, item: function() { return null; }, namedItem: function() { return null; }
                };
            };
            var plugins = [
                makePlugin('Chrome PDF Plugin', 'internal-pdf-viewer', 'Portable Document Format'),
                makePlugin('Chrome PDF Viewer', 'mhjfbmdgcfjbbpaeojofohoefgiehjai', ''),
                makePlugin('Native Client', 'internal-nacl-plugin', ''),
            ];
            plugins.item = function(i) { return this[i] || null; };
            plugins.namedItem = function(n) { for (var i=0;i<this.length;i++) { if (this[i].name===n) return this[i]; } return null; };
            plugins.refresh = function() {};
            Object.defineProperty(navigator, 'plugins', { get: function() { return plugins; } });

            var mimeTypes = [
                { type: 'application/pdf', suffixes: 'pdf', description: 'Portable Document Format', enabledPlugin: plugins[0] },
                { type: 'text/pdf', suffixes: 'pdf', description: 'Portable Document Format', enabledPlugin: plugins[0] },
            ];
            mimeTypes.item = function(i) { return this[i] || null; };
            mimeTypes.namedItem = function(n) { for (var i=0;i<this.length;i++) { if (this[i].type===n) return this[i]; } return null; };
            Object.defineProperty(navigator, 'mimeTypes', { get: function() { return mimeTypes; } });
        })();

        // ── Navigator properties ──
        Object.defineProperty(navigator, 'languages', { get: () => ['en-US', 'en'] });
        Object.defineProperty(navigator, 'language', { get: () => 'en-US' });
        Object.defineProperty(navigator, 'platform', { get: () => 'MacIntel' });
        Object.defineProperty(navigator, 'hardwareConcurrency', { get: () => 8 });
        Object.defineProperty(navigator, 'deviceMemory', { get: () => 8 });
        Object.defineProperty(navigator, 'maxTouchPoints', { get: () => 0 });
        Object.defineProperty(navigator, 'cookieEnabled', { get: () => true });
        Object.defineProperty(navigator, 'doNotTrack', { get: () => null });
        Object.defineProperty(navigator, 'vendor', { get: () => 'Google Inc.' });
        Object.defineProperty(navigator, 'vendorSub', { get: () => '' });
        Object.defineProperty(navigator, 'productSub', { get: () => '20030107' });
        Object.defineProperty(navigator, 'appVersion', { get: () => navigator.userAgent.replace('Mozilla/', '') });

        // ── Permissions ──
        var origQuery = window.navigator.permissions.query;
        window.navigator.permissions.query = function(params) {
            if (params.name === 'notifications' || params.name === 'clipboard-read' || params.name === 'clipboard-write') {
                return Promise.resolve({ state: Notification.permission === 'granted' ? 'granted' : 'prompt', onchange: null });
            }
            return origQuery.call(this, params);
        };

        // ── Remove automation traces ──
        delete window.callPhantom;
        delete window._phantom;
        delete window.__phantomas;
        delete window.__nightmare;
        delete window.domAutomation;
        delete window.domAutomationController;
        delete window._selenium;
        delete window.callSelenium;
        delete window._Selenium_IDE_Recorder;
        delete window.__webdriver_evaluate;
        delete window.__webdriver_script_function;
        delete window.__webdriver_script_func;
        delete window.__webdriver_script_fn;
        delete window.__fxdriver_evaluate;
        delete window.__driver_unwrapped;
        delete window.__webdriver_unwrapped;
        delete window.__driver_evaluate;
        delete window.__webdriver_evaluate;
        delete window.__selenium_evaluate;
        delete window.__fxdriver_evaluate;
        delete window.__driver_unwrapped;
        delete window.__webdriver_unwrapped;
        delete window.__webdriver_script_fn;
        delete window.__webdriver_script_func;
        delete window.__webdriver_script_function;
        delete window.__lastWatirAlert;
        delete window.__lastWatirConfirm;
        delete window.__lastWatirPrompt;

        // ── Block CDP detection in iframes ──
        Element.prototype._attachShadow = Element.prototype.attachShadow;
        Element.prototype.attachShadow = function(init) { return this._attachShadow({ mode: 'open', ...(init||{}) }); };
        """
        try:
            page.run_js(anti_detect_js)
        except Exception:
            pass
