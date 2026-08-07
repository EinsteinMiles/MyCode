"""
AliExpress 爬虫
AJAX 重度网站 — 需要等待 JS 渲染 + 滚动触发懒加载 + 多策略提取
类名是哈希化的，主要靠通用选择器和 JS 枚举元素
"""

from __future__ import annotations

import re
import time
import json
import os
import random
from typing import TYPE_CHECKING, List, Optional, Set
from urllib.parse import quote

if TYPE_CHECKING:
    from DrissionPage import ChromiumPage

from config import ALIEXPRESS_SEARCH_URL, ALIEXPRESS_ITEM_URL, MAX_REVIEW_PAGES, OUTPUT_DIR, logger
from scrapers.base import BaseScraper
from core.models import Product, Review, HotRanking
from core.utils import (
    random_delay, page_delay, parse_price, parse_currency,
    parse_sales, parse_rating, clean_text, now_str,
)


class AliExpressScraper(BaseScraper):
    """AliExpress 平台爬虫"""

    platform = "aliexpress"

    # ── Session Warm-Up ───────────────────────────────

    _warmed_up = False

    def _warm_up(self, page) -> None:
        """Visit AliExpress homepage first to establish cookies before searching."""
        if AliExpressScraper._warmed_up:
            return

        logger.info("[AliExpress] Warming up — visiting homepage first...")
        try:
            page.get("https://www.aliexpress.com/")
            time.sleep(5)
            # Dismiss popups (currency, shipping country, coupons)
            self._dismiss_popups(page)
            AliExpressScraper._warmed_up = True
            logger.info("[AliExpress] Warm-up complete")
        except Exception as e:
            logger.warning(f"[AliExpress] Warm-up failed: {e}")

    # ── 搜索商品 ──────────────────────────────────────

    def search_products(
        self, keyword: str, max_pages: int = 5, category: str = ""
    ) -> List[Product]:
        max_pages = min(max_pages, 10)
        all_products: List[Product] = []
        page = self._get_page()

        search_url = ALIEXPRESS_SEARCH_URL.format(keyword=quote(keyword))
        logger.info(f"[AliExpress] 搜索: {keyword} (最多 {max_pages} 页)")

        try:
            # Warm up: visit homepage first
            self._warm_up(page)

            page.get(search_url)
            time.sleep(5)  # AliExpress AJAX 渲染很慢

            # 处理可能的弹窗（地区选择、货币选择、优惠券弹窗）
            self._dismiss_popups(page)

            # 检查 CAPTCHA
            if self._check_captcha(page):
                logger.error("[AliExpress] ⚠️ 触发验证码")
                return all_products

            # 区域设置 — 设置为美国/美元
            self._ensure_us_settings(page)

            for pg in range(1, max_pages + 1):
                logger.info(f"[AliExpress] 解析第 {pg}/{max_pages} 页...")
                self._rate_limit()

                # AliExpress 商品是懒加载的，必须深度滚动
                self._deep_scroll(page, times=5)

                # JS 提取（AliExpress 类名全部哈希化）
                products = self._extract_by_js(page, keyword, category)
                all_products.extend(products)
                logger.info(f"[AliExpress] 第 {pg} 页提取 {len(products)} 个商品")

                if pg < max_pages:
                    if not self._go_next_page(page):
                        logger.info("[AliExpress] 无下一页")
                        break
                    time.sleep(random.uniform(4, 7))
                    self._dismiss_popups(page)

        except Exception as e:
            logger.error(f"[AliExpress] 搜索异常: {e}")
            import traceback
            traceback.print_exc()

        logger.info(f"[AliExpress] 搜索完成: 共 {len(all_products)} 个商品")
        return all_products

    def _extract_by_js(self, page, keyword: str, category: str) -> List[Product]:
        """通过 JS 提取 AliExpress 商品数据"""
        products: List[Product] = []
        seen_ids: Set[str] = set()

        try:
            items = page.run_js("""
                // AliExpress 使用 hash 类名，通过 DOM 结构枚举所有可能的商品卡片
                var results = [];
                var seen = new Set();

                // 遍历所有 <a> 标签找到商品链接
                var links = document.querySelectorAll('a[href*="/item/"]');
                links.forEach(function(link) {
                    var href = link.href || '';
                    // 提取 item ID
                    var idMatch = href.match(/\\/item\\/(\\d+)\\.html/) || href.match(/\\/item\\/[^/]+?-(\\d+)\\.html/);
                    var itemId = idMatch ? idMatch[1] : '';
                    if (!itemId || seen.has(itemId)) return;

                    // 找最近的卡片容器
                    var card = link.closest('[class*="card"], [class*="item"], [class*="list--"], div');
                    if (!card) return;

                    var cardText = (card.textContent || '').trim();
                    // 跳过非商品元素（文字太少）
                    if (cardText.length < 30) return;

                    var title = (link.textContent || '').trim();
                    if (title.length < 10) {
                        // 尝试从各种 title 元素获取
                        var titleEl = card.querySelector('[class*="title"]');
                        if (titleEl) title = (titleEl.textContent || '').trim();
                    }
                    if (title.length < 10) return;

                    // 价格 — 查找包含 $ 的元素
                    var price = '';
                    var priceEls = card.querySelectorAll('[class*="price"], span');
                    for (var i = 0; i < priceEls.length; i++) {
                        var txt = (priceEls[i].textContent || '').trim();
                        if (txt.match(/\\$\\s*\\d+[.,\\d]*/)) {
                            price = txt;
                            break;
                        }
                    }

                    // 原始价格 (划线价)
                    var origPrice = '';
                    var origEls = card.querySelectorAll('[class*="orig"], [class*="original"], del, s');
                    for (var i = 0; i < origEls.length; i++) {
                        var txt = (origEls[i].textContent || '').trim();
                        if (txt.match(/\\$\\s*\\d+/)) {
                            origPrice = txt;
                            break;
                        }
                    }

                    // 销量/订单数
                    var orders = '';
                    var ordersEl = card.querySelector('[class*="trade"], [class*="sold"], [class*="order"]');
                    if (ordersEl) orders = (ordersEl.textContent || '').trim();

                    // 评分
                    var rating = '';
                    var ratingEl = card.querySelector('[class*="rating"], [class*="star"]');
                    if (ratingEl) rating = (ratingEl.textContent || '').trim();

                    // 店铺名
                    var store = '';
                    var storeEl = card.querySelector('[class*="store"], [class*="seller"], [class*="shop"]');
                    if (storeEl) store = (storeEl.textContent || '').trim();

                    // 图片
                    var imgEl = card.querySelector('img');
                    var image = imgEl ? (imgEl.src || imgEl.dataset.src || '') : '';

                    seen.add(itemId);
                    results.push({
                        itemId: itemId,
                        title: title,
                        url: href,
                        price: price,
                        origPrice: origPrice,
                        orders: orders,
                        rating: rating,
                        store: store,
                        image: image
                    });
                });
                return results.slice(0, 60);
            """)

            if not items:
                return products

            for item in items:
                item_id = item.get("itemId", "")
                if item_id in seen_ids:
                    continue
                seen_ids.add(item_id)

                price_text = item.get("price", "")
                orders_text = item.get("orders", "")

                rating = parse_rating(item.get("rating", ""))
                sales_count = parse_sales(orders_text)
                # AliExpress "orders" 通常显示为 "1,234 sold" 或 "5K+ sold"
                if sales_count == 0 and orders_text:
                    try:
                        sales_count = int(re.sub(r'[^\d]', '', orders_text.replace(',', '')) or 0)
                    except ValueError:
                        pass

                products.append(self._new_product(
                    product_id=item_id,
                    title=clean_text(item.get("title", "")),
                    price=parse_price(price_text),
                    price_range=price_text,
                    original_price=parse_price(item.get("origPrice", "")),
                    currency=parse_currency(price_text) if price_text else "USD",
                    rating=rating,
                    review_count=sales_count,  # AliExpress 用 orders 近似
                    sales_count=sales_count,
                    sales_text=orders_text,
                    shop_name=clean_text(item.get("store", "")),
                    condition="New",
                    category=category or keyword,
                    image_url=item.get("image", ""),
                    url=item.get("url", ""),
                ))

                if len(products) >= 60:
                    break

        except Exception as e:
            logger.error(f"[AliExpress] JS 提取失败: {e}")

        return products

    # ── 商品详情 ──────────────────────────────────────

    def get_product_detail(self, url: str) -> Optional[Product]:
        page = self._get_page()
        self._rate_limit()

        try:
            page.get(url)
            time.sleep(4)
            self._dismiss_popups(page)
            self._deep_scroll(page, times=2)

            data = page.run_js("""
                var result = {};

                var titleEl = document.querySelector('h1[class*="title"], h1');
                result.title = titleEl ? titleEl.textContent.trim() : document.title;

                // 价格
                var priceEl = document.querySelector('[class*="price--current"], [class*="product-price-current"], [class*="price"]');
                if (priceEl) result.price = priceEl.textContent.trim();

                // 评分
                var ratingEl = document.querySelector('[class*="rating--num"], [class*="reviewer-average"]');
                if (ratingEl) result.rating = ratingEl.textContent.trim();

                // 订单数
                var ordersEl = document.querySelector('[class*="order--number"], [class*="trade"]');
                if (ordersEl) result.orders = ordersEl.textContent.trim();

                // 店铺
                var storeEl = document.querySelector('[class*="store--name"], [class*="seller"]');
                if (storeEl) result.store = storeEl.textContent.trim();

                return result;
            """)

            if data and data.get("title"):
                item_id = ""
                m = re.search(r'/item/(\d+)', url)
                if m:
                    item_id = m.group(1)

                price_text = data.get("price", "")
                return self._new_product(
                    product_id=item_id,
                    title=clean_text(data.get("title", "")),
                    price=parse_price(price_text),
                    price_range=price_text,
                    currency=parse_currency(price_text) if price_text else "USD",
                    rating=parse_rating(data.get("rating", "")),
                    sales_text=data.get("orders", ""),
                    sales_count=parse_sales(data.get("orders", "")),
                    shop_name=clean_text(data.get("store", "")),
                    url=url,
                )

        except Exception as e:
            logger.error(f"[AliExpress] 详情获取失败: {e}")

        return None

    # ── 评论抓取 ──────────────────────────────────────

    def get_reviews(
        self, product_url: str, max_pages: int = MAX_REVIEW_PAGES
    ) -> List[Review]:
        """抓取 AliExpress 评论"""
        reviews: List[Review] = []

        page = self._get_page()
        try:
            page.get(product_url)
            time.sleep(4)
            self._dismiss_popups(page)

            # 点击评论 tab
            try:
                review_tab = page.ele('[class*="tab"][class*="review"], [class*="feedback"], a[href*="feedback"]', timeout=3)
                if review_tab:
                    review_tab.click()
                    time.sleep(3)
            except Exception:
                pass

            for pg in range(1, min(max_pages, 5) + 1):
                self._deep_scroll(page, times=3)

                items = page.run_js("""
                    var reviews = document.querySelectorAll('[class*="review-item"], [class*="feedback-item"], [class*="comment"]');
                    var result = [];
                    reviews.forEach(function(r) {
                        var text = (r.textContent || '').trim();
                        if (text.length < 20 || text.length > 3000) return;

                        var ratingEl = r.querySelector('img[alt*="star"], [class*="star"]');
                        var rating = 5;

                        // 图片 URL 提取
                        var imgs = [];
                        r.querySelectorAll('img').forEach(function(img) {
                            var src = img.src || img.dataset.src || '';
                            if (src && !src.includes('star') && src.startsWith('http')) {
                                imgs.push(src);
                            }
                        });

                        result.push({
                            content: text,
                            rating: rating,
                            images: imgs
                        });
                    });
                    return result;
                """)

                for item in (items or []):
                    reviews.append(Review(
                        product_db_id=0,
                        content=clean_text(item.get("content", "")),
                        rating=item.get("rating", 5),
                        review_date=now_str(),
                        scraped_at=now_str(),
                    ))

                if len(reviews) >= 50:
                    break
                page_delay()

        except Exception as e:
            logger.error(f"[AliExpress] 评论抓取失败: {e}")

        return reviews

    # ── 热销排行 ──────────────────────────────────────

    def get_hot_ranking(self, category: str, top_n: int = 50) -> List[HotRanking]:
        """AliExpress Best Selling"""
        rankings: List[HotRanking] = []
        page = self._get_page()

        url = ALIEXPRESS_SEARCH_URL.format(keyword=quote(category)) + "&SortType=total_tranpro_desc"
        try:
            page.get(url)
            time.sleep(5)
            self._dismiss_popups(page)
            self._deep_scroll(page, times=3)

            items = page.run_js("""
                var links = document.querySelectorAll('a[href*="/item/"]');
                var result = [];
                var seen = new Set();
                var rank = 1;
                links.forEach(function(link) {
                    var href = link.href || '';
                    var idMatch = href.match(/\\/item\\/(\\d+)\\.html/);
                    var itemId = idMatch ? idMatch[1] : '';
                    if (!itemId || seen.has(itemId)) return;
                    seen.add(itemId);

                    var title = (link.textContent || '').trim();
                    if (title.length < 10) return;

                    var card = link.closest('[class*="card"], [class*="item"], [class*="list--"]') || link.parentElement;
                    var cardText = card ? (card.textContent || '').trim() : '';

                    var price = '';
                    var pm = cardText.match(/\\$\\s*\\d+[.,\\d]*/);
                    if (pm) price = pm[0];

                    result.push({title: title, price: price, rank: rank++});
                    if (rank > 50) return;
                });
                return result;
            """)

            for item in (items or []):
                rankings.append(HotRanking(
                    platform=self.platform,
                    category=category,
                    rank=item.get("rank", 0),
                    title=clean_text(item.get("title", "")),
                    price=parse_price(item.get("price", "")),
                    snapshot_date=now_str(),
                ))
                if len(rankings) >= top_n:
                    break

        except Exception as e:
            logger.error(f"[AliExpress] 排行抓取失败: {e}")

        return rankings

    # ── 辅助方法 ──────────────────────────────────────

    def _dismiss_popups(self, page) -> None:
        """关闭 AliExpress 的各种弹窗（地区选择、优惠券、newsletter）"""
        close_selectors = [
            "img[src*='close']",
            ".close-layer",
            "[class*='close']",
            "[class*='popup'] [class*='close']",
            ".btn-close",
            ".next-dialog-close",
            "[data-role='close']",
        ]
        for sel in close_selectors:
            try:
                el = page.ele(sel, timeout=0.5)
                if el:
                    el.click()
                    time.sleep(0.3)
            except Exception:
                continue

        # ESC 键关闭
        try:
            page.run_js("document.body.click()")
        except Exception:
            pass

    def _ensure_us_settings(self, page) -> None:
        """确保区域/货币设置为美国/美元"""
        try:
            # 检查当前货币设置
            current = page.run_js("""
                var el = document.querySelector('[class*="currency"], [class*="ship-to"]');
                return el ? el.textContent.trim() : '';
            """)
            logger.debug(f"[AliExpress] 当前设置: {current}")
        except Exception:
            pass

    def _deep_scroll(self, page, times: int = 5) -> None:
        """深度滚动触发 AliExpress 懒加载"""
        for i in range(times):
            try:
                scroll_by = random.randint(300, 700)
                page.run_js(f"window.scrollBy(0, {scroll_by})")
                time.sleep(random.uniform(0.5, 1.2))
            except Exception:
                break
        # 慢慢滚回去
        try:
            page.scroll.to_top()
            time.sleep(0.5)
        except Exception:
            pass

    def _go_next_page(self, page) -> bool:
        """AliExpress 翻页"""
        try:
            next_btn = page.ele("[class*='pagination'] [class*='next'], .next-pagination-item", timeout=2)
            if next_btn:
                next_btn.click()
                time.sleep(4)
                return True
        except Exception:
            pass

        try:
            current_url = page.url
            m = re.search(r'[&?]page=(\d+)', current_url)
            if m:
                current_page = int(m.group(1))
                new_url = re.sub(r'([&?])page=\d+', f'\\1page={current_page + 1}', current_url)
            else:
                sep = "&" if "?" in current_url else "?"
                new_url = current_url + f"{sep}page=2"
            page.get(new_url)
            time.sleep(4)
            return True
        except Exception:
            pass

        return False
