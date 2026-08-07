"""
拼多多爬虫
反爬极强，PC 网页功能有限，使用移动端 UA 模拟

搜索 URL: https://mobile.yangkeduo.com/search_result.html?search_key={keyword}
"""

from __future__ import annotations

import time
import re
from typing import TYPE_CHECKING, List, Optional

if TYPE_CHECKING:
    from DrissionPage import ChromiumPage

from config import (
    PINDUODUO_SEARCH_URL, PINDUODUO_SELECTORS,
    MAX_REVIEW_PAGES, logger,
)
from scrapers.base import BaseScraper
from core.models import Product, Review, HotRanking
from core.utils import (
    random_delay, page_delay, parse_price, parse_sales,
    clean_text, now_str,
)


class PinduoduoScraper(BaseScraper):
    """拼多多平台爬虫"""

    platform = "pinduoduo"

    # ── 搜索商品 ──────────────────────────────────────

    def search_products(
        self, keyword: str, max_pages: int = 3, category: str = ""
    ) -> List[Product]:
        """
        搜索拼多多商品（移动端视图）
        注意：拼多多 PC 网页极弱，仅尝试移动端
        """
        max_pages = min(max_pages, 5)
        all_products: List[Product] = []
        page = self._get_page()

        search_url = PINDUODUO_SEARCH_URL.format(keyword=keyword)
        logger.info(f"[拼多多] 开始搜索: {keyword}")
        logger.warning("[拼多多] PC 网页版功能有限，仅抓取可见列表")

        # 加载 Cookie
        self.browser_mgr.load_cookies("pinduoduo")

        try:
            page.get(search_url)
            time.sleep(4)

            for pg in range(1, max_pages + 1):
                logger.info(f"[拼多多] 正在抓取第 {pg}/{max_pages} 页...")
                self._rate_limit()
                self._scroll_to_load(page, times=4)

                products = self._parse_search_results(page, keyword, category)
                all_products.extend(products)
                logger.info(f"[拼多多] 第 {pg} 页提取 {len(products)} 个商品")

                if pg < max_pages:
                    if not self._go_next_page(page):
                        break
                    page_delay()

        except Exception as e:
            logger.error(f"[拼多多] 搜索异常: {e}")

        return all_products

    def _parse_search_results(
        self, page, keyword: str, category: str
    ) -> List[Product]:
        """解析拼多多搜索结果"""
        products = []

        item_selectors = [
            ".goods-item", "[class*='goods']", "[class*='item']",
            ".search-result-item", ".card-item",
        ]

        items = []
        for sel in item_selectors:
            items = self._safe_extract_list(page, sel, timeout=3)
            if len(items) > 1:
                break

        for item in items:
            try:
                # 标题
                title = self._safe_extract(
                    item,
                    [".goods-title", "[class*='title']", "[class*='name']", "a"],
                    default="",
                )
                if not title or len(title) < 3:
                    continue

                # 价格（拼多多用分或元）
                price_text = self._safe_extract(
                    item,
                    [".goods-price", "[class*='price']", "[class*='Price']"],
                    default="",
                )
                price = parse_price(price_text) if price_text else 0.0

                # 销量
                sales_text = self._safe_extract(
                    item,
                    [".goods-sales", "[class*='sale']", "[class*='sold']"],
                    default="",
                )
                sales_count = parse_sales(sales_text) if sales_text else 0

                # 店铺
                shop_name = self._safe_extract(
                    item,
                    [".mall-name", "[class*='shop']", "[class*='mall']"],
                    default="",
                )

                # 链接
                url = ""
                try:
                    link_el = item.ele("a[href*='yangkeduo']", timeout=1) or item.ele("a", timeout=1)
                    if link_el:
                        url = link_el.attr("href") or ""
                except Exception:
                    pass

                product_id = ""
                if url:
                    m = re.search(r'goods_id=(\d+)', url) or re.search(r'/goods/(\d+)', url)
                    if m:
                        product_id = m.group(1)

                products.append(self._new_product(
                    product_id=product_id,
                    title=title,
                    price=price,
                    price_range=price_text,
                    sales_count=sales_count,
                    sales_text=sales_text,
                    shop_name=shop_name,
                    category=category or keyword,
                    url=url,
                ))

            except Exception:
                continue

        return products

    # ── 商品详情 ──────────────────────────────────────

    def get_product_detail(self, url: str) -> Optional[Product]:
        """获取拼多多商品详情（移动端）"""
        page = self._get_page()
        self._rate_limit()

        try:
            page.get(url)
            time.sleep(3)
            self._scroll_to_load(page, times=4)

            title = self._safe_extract(
                page,
                [".goods-name", "h1", "[class*='title']"],
                default="未知商品",
            )

            price_text = self._safe_extract(
                page,
                [".goods-price", "[class*='price']", ".price"],
                default="0",
            )
            price = parse_price(price_text) if price_text else 0.0

            sales_text = self._safe_extract(
                page,
                [".goods-sales", "[class*='sale']", "[class*='sold']"],
                default="",
            )
            sales_count = parse_sales(sales_text) if sales_text else 0

            return self._new_product(
                title=clean_text(title),
                price=price,
                price_range=price_text,
                sales_count=sales_count,
                sales_text=sales_text,
                url=url,
            )

        except Exception as e:
            logger.error(f"[拼多多] 获取详情失败: {url} - {e}")
            return None

    # ── 评论 ──────────────────────────────────────────

    def get_reviews(
        self, product_url: str, max_pages: int = MAX_REVIEW_PAGES
    ) -> List[Review]:
        """拼多多评论（PC 网页基本不可用）"""
        logger.warning("[拼多多] PC 网页评论功能受限，仅尝试基础抓取")
        reviews: List[Review] = []
        page = self._get_page()

        try:
            page.get(product_url)
            time.sleep(3)

            items = self._safe_extract_list(page, "[class*='comment']", timeout=3)
            if not items:
                items = self._safe_extract_list(page, "[class*='review']", timeout=3)

            for item in items:
                content = self._safe_extract(item, ["p", "span", "[class*='content']"], default="")
                if content:
                    reviews.append(Review(
                        product_db_id=0,
                        content=clean_text(content),
                        rating=5,
                        review_date=now_str(),
                        scraped_at=now_str(),
                    ))
        except Exception as e:
            logger.error(f"[拼多多] 抓取评论失败: {e}")

        return reviews

    # ── 热销排行 ──────────────────────────────────────

    def get_hot_ranking(self, category: str, top_n: int = 50) -> List[HotRanking]:
        """拼多多热销排行"""
        logger.warning("[拼多多] 热销排行功能受限")
        return []

    def _go_next_page(self, page) -> bool:
        """拼多多翻页"""
        for sel in ["[class*='next']", "a:contains('下一页')", ".pagination-next"]:
            try:
                btn = page.ele(sel, timeout=3)
                if btn:
                    btn.click()
                    time.sleep(3)
                    return True
            except Exception:
                continue
        return False
