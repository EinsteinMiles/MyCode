"""
爬虫基类
定义平台无关的通用搜索/详情/评论/排行框架
"""

from __future__ import annotations

import time
from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, List, Optional

if TYPE_CHECKING:
    from DrissionPage import ChromiumPage

from config import (
    REST_EVERY_N, REST_MIN, REST_MAX, logger,
)
from core.models import Product, Review, HotRanking
from core.utils import random_delay, page_delay, clean_text, now_str


class BaseScraper(ABC):
    """平台爬虫抽象基类"""

    platform: str = ""  # 子类必须定义

    def __init__(self, browser_manager):
        from core.browser import BrowserManager
        self.browser_mgr: BrowserManager = browser_manager
        self._request_count = 0

    # ── 抽象方法（子类实现）───────────────────────────

    @abstractmethod
    def search_products(
        self, keyword: str, max_pages: int = 5, category: str = ""
    ) -> List[Product]:
        """搜索商品列表"""
        ...

    @abstractmethod
    def get_product_detail(self, url: str) -> Optional[Product]:
        """获取商品详情"""
        ...

    @abstractmethod
    def get_reviews(
        self, product_url: str, max_pages: int = 10
    ) -> List[Review]:
        """获取商品评论"""
        ...

    @abstractmethod
    def get_hot_ranking(self, category: str, top_n: int = 50) -> List[HotRanking]:
        """获取热销排行"""
        ...

    # ── 通用辅助方法 ──────────────────────────────────

    def _get_page(self) -> ChromiumPage:
        """获取浏览器页面实例"""
        return self.browser_mgr.get_page()

    def _rate_limit(self) -> None:
        """请求限速：随机延迟 + 长休息"""
        self._request_count += 1
        random_delay()

        if self._request_count > 0 and self._request_count % REST_EVERY_N == 0:
            import random
            rest = random.uniform(REST_MIN, REST_MAX)
            logger.info(f"长休息 {rest:.0f}s ... (已请求 {self._request_count} 次)")
            time.sleep(rest)

    def _safe_extract(
        self,
        page: ChromiumPage,
        selectors: List[str],
        default: str = "",
        attribute: str = "text",
    ) -> str:
        """
        多选择器降级提取
        依次尝试 selectors 中的选择器，返回第一个匹配的内容
        """
        for sel in selectors:
            try:
                el = page.ele(sel, timeout=2)
                if el:
                    if attribute == "text":
                        return clean_text(el.text) or default
                    else:
                        return el.attr(attribute) or default
            except Exception:
                continue
        return default

    def _safe_extract_list(
        self, page: ChromiumPage, selector: str, timeout: int = 5
    ) -> list:
        """安全提取元素列表"""
        try:
            return page.eles(selector, timeout=timeout)
        except Exception:
            return []

    def _scroll_to_load(self, page: ChromiumPage, times: int = 3) -> None:
        """滚动页面触发懒加载"""
        for i in range(times):
            try:
                page.scroll.to_half()
                time.sleep(0.5)
                page.scroll.to_bottom()
                time.sleep(0.8)
                page.scroll.to_top()
                time.sleep(0.3)
            except Exception:
                break

    def _wait_for_element(
        self, page: ChromiumPage, selector: str, timeout: int = 10
    ) -> bool:
        """等待元素出现"""
        try:
            page.wait.ele_displayed(selector, timeout=timeout)
            return True
        except Exception:
            return False

    def _check_captcha(self, page: ChromiumPage) -> bool:
        """检测是否出现验证码"""
        captcha_keywords = ["验证码", "滑块验证", "请按住滑块", "请完成安全验证"]
        try:
            html = page.html[:5000]
            for kw in captcha_keywords:
                if kw in html:
                    logger.warning(f"检测到验证码: {kw}")
                    return True
        except Exception:
            pass
        return False

    def _new_product(
        self,
        product_id: str = "",
        title: str = "",
        price: float = 0.0,
        url: str = "",
        **kwargs,
    ) -> Product:
        """创建 Product 实例的快捷方法"""
        now = now_str()
        return Product(
            platform=self.platform,
            product_id=product_id,
            title=title,
            price=price,
            url=url,
            first_seen=now,
            last_updated=now,
            **kwargs,
        )
