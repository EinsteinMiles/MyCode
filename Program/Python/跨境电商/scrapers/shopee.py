"""
Shopee 爬虫
AJAX 重度网站 — 需要等待 JS 渲染 + 滚动触发懒加载 + 多策略提取
类名是哈希化的，主要靠通用选择器和 JS 枚举元素
Cloudflare 防护 — 需要持久化浏览器配置文件 + 预热 + 保守延迟
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

from config import SHOPEE_SEARCH_URL, SHOPEE_ITEM_URL, MAX_REVIEW_PAGES, OUTPUT_DIR, logger
from scrapers.base import BaseScraper
from core.models import Product, Review, HotRanking
from core.utils import (
    random_delay, page_delay, parse_price, parse_currency,
    parse_sales, parse_rating, clean_text, now_str,
)


class ShopeeScraper(BaseScraper):
    """Shopee 平台爬虫 — 多策略版"""

    platform = "shopee"

    # ── Session Warm-Up ───────────────────────────────

    _warmed_up = False

    @classmethod
    def _warm_up(cls, page) -> None:
        """Visit Shopee homepage first to establish cookies before searching."""
        if cls._warmed_up:
            return

        logger.info("[Shopee] 预热中 — 先访问首页...")
        try:
            page.get("https://shopee.sg/")
            time.sleep(5)
            # Dismiss any popups
            cls._dismiss_shopee_popups(page)
            cls._warmed_up = True
            logger.info("[Shopee] 预热完成")
        except Exception as e:
            logger.warning(f"[Shopee] 预热失败: {e}")

    # ── 搜索商品 ──────────────────────────────────────

    def search_products(
        self, keyword: str, max_pages: int = 5, category: str = ""
    ) -> List[Product]:
        max_pages = min(max_pages, 5)  # Shopee 翻页保守一些
        all_products: List[Product] = []
        page = self._get_page()

        search_url = SHOPEE_SEARCH_URL.format(keyword=quote(keyword))
        logger.info(f"[Shopee] 搜索: {keyword} (最多 {max_pages} 页)")
        logger.info(f"[Shopee] URL: {search_url}")

        try:
            # Warm up: visit homepage first
            ShopeeScraper._warm_up(page)

            page.get(search_url)
            time.sleep(6)  # Shopee 有 Cloudflare，需要更长等待

            # 处理可能的弹窗
            ShopeeScraper._dismiss_shopee_popups(page)

            # 诊断页面
            diagnosis = self._diagnose(page)
            logger.info(f"[Shopee] 诊断: {json.dumps(diagnosis, indent=2)}")

            # 检查 CAPTCHA
            if self._check_captcha(page):
                logger.error("[Shopee] ⚠️ 触发验证码或 Cloudflare 拦截！")
                self._save_debug(page, "captcha")
                return all_products

            # 检查是否有搜索结果
            if diagnosis.get("card_count", 0) == 0:
                logger.error(
                    "[Shopee] 未找到商品卡片。\n"
                    "  可能原因:\n"
                    "  1. Shopee 要求登录 — 先使用菜单 [8] 登录\n"
                    "  2. Cloudflare 拦截 — 尝试 headless=False 并手动验证\n"
                    "  3. 搜索关键词无结果\n"
                )
                self._save_debug(page, "no_results")
                return all_products

            for pg in range(1, max_pages + 1):
                logger.info(f"[Shopee] 解析第 {pg}/{max_pages} 页...")
                self._rate_limit()

                # Shopee 商品是懒加载的，深度滚动触发渲染
                self._shopee_scroll(page, times=4)

                # JS 提取（Shopee 类名全部哈希化，JS 为唯一可靠方式）
                products = self._extract_by_js(page, keyword, category)
                all_products.extend(products)
                logger.info(f"[Shopee] 第 {pg} 页提取 {len(products)} 个商品")

                if pg < max_pages:
                    time.sleep(random.uniform(4, 8))
                    if not self._load_more_products(page):
                        logger.info("[Shopee] 无法加载更多商品")
                        break
                    ShopeeScraper._dismiss_shopee_popups(page)

        except Exception as e:
            logger.error(f"[Shopee] 搜索异常: {e}")
            import traceback
            traceback.print_exc()

        logger.info(f"[Shopee] 搜索完成: 共 {len(all_products)} 个商品")
        return all_products

    def _extract_by_js(self, page, keyword: str, category: str) -> List[Product]:
        """通过 JS 提取 Shopee 商品数据（主策略）"""
        products: List[Product] = []
        seen_ids: Set[str] = set()

        try:
            items = page.run_js("""
                var results = [];
                var seen = new Set();

                // Shopee 卡片选择器 — 尝试多种可能的容器
                var cards = document.querySelectorAll(
                    '[class*="shopee-search-item-result__item"], ' +
                    '[class*="col-xs-2-4"], ' +
                    'a[data-sqe="item"], ' +
                    '[class*="search-result-item"]'
                );

                // 如果没找到，尝试从链接反推
                if (cards.length === 0) {
                    var links = document.querySelectorAll('a[href*="/product/"]');
                    links.forEach(function(link) {
                        var card = link.closest('div[class]');
                        if (card && card.textContent.trim().length > 40) {
                            cards = document.querySelectorAll(card.tagName + '.' + card.className.split(' ').join('.'));
                        }
                    });
                }

                cards.forEach(function(card) {
                    try {
                        // 获取商品链接
                        var linkEl = card.querySelector('a[href*="/product/"], a[data-sqe="item"]');
                        if (!linkEl) {
                            // 卡片自己可能就是链接
                            if (card.tagName === 'A' && card.href && card.href.includes('/product/')) {
                                linkEl = card;
                            }
                        }
                        if (!linkEl) return;

                        var href = linkEl.href || '';
                        // Shopee URL: /product/{shop_id}/{item_id} 或 /{name}-i.{shop_id}.{item_id}
                        var idMatch = href.match(/i\\.(\\d+)\\.(\\d+)/) || href.match(/\\/product\\/(\\d+)\\/(\\d+)/);
                        var itemId = idMatch ? (idMatch[2] || idMatch[1]) : href.replace(/[^0-9]/g, '').slice(-10);
                        if (!itemId || seen.has(itemId)) return;

                        // 标题 — 查找可辨认的文本块
                        var title = '';
                        var titleEl = card.querySelector(
                            '[class*="name"], [class*="title"], [class*="yQ"], ' +
                            '[class*="O6"], [class*="description"], [class*="text"]'
                        );
                        if (titleEl) {
                            title = (titleEl.textContent || '').trim();
                        }
                        if (title.length < 10) {
                            // 从卡片文本中提取最长的文本行
                            var divs = card.querySelectorAll('div, span');
                            var longest = '';
                            divs.forEach(function(el) {
                                var t = (el.textContent || '').trim();
                                if (t.length > longest.length && t.length < 200 && !t.startsWith('$') && !t.startsWith('₱') && !t.startsWith('Rp')) {
                                    longest = t;
                                }
                            });
                            title = longest;
                        }
                        if (title.length < 10) return;

                        // 获取卡片所有文本用于解析
                        var cardText = (card.textContent || '').trim();

                        // 价格 — Shopee 价格通常有关键类名或货币符号
                        var price = '';
                        var priceEls = card.querySelectorAll(
                            '[class*="price"], [class*="Oo"], [class*="currency"], ' +
                            'span:not([class*="sold"]):not([class*="location"])'
                        );
                        for (var i = 0; i < priceEls.length; i++) {
                            var txt = (priceEls[i].textContent || '').trim();
                            // 多种货币符号
                            if (txt.match(/[\\$₱Rp¥฿₫]\\s*[\\d,.]+/) || txt.match(/[\\d,.]+\\s*(₫|₱|Rp)/)) {
                                price = txt;
                                break;
                            }
                        }
                        if (!price) {
                            // 备用: 从卡片文本中提取
                            var pm = cardText.match(/(?:\\$|₱|Rp|RM|S\\$|฿|₫)\\s*[\\d,.]+(?:\\s*-\\s*[\\d,.]+)?/);
                            if (pm) price = pm[0];
                        }

                        // 原始价格 (划线价)
                        var origPrice = '';
                        var origEls = card.querySelectorAll('[class*="orig"], [class*="discount"], [class*="strikethrough"], del, s');
                        for (var i = 0; i < origEls.length; i++) {
                            var txt = (origEls[i].textContent || '').trim();
                            if (txt.match(/[\\$₱Rp¥฿₫]\\s*[\\d,.]+/)) {
                                origPrice = txt;
                                break;
                            }
                        }

                        // 销量
                        var sold = '';
                        var soldEl = card.querySelector('[class*="sold"], [class*="item-sold"]');
                        if (soldEl) sold = (soldEl.textContent || '').trim();
                        if (!sold) {
                            var sm = cardText.match(/(\\d+(?:\\.\\d+)?[Kk万万]?\\s*\\+?\\s*(?:sold|sold|已售|售出|卖出|件|个))|((?:sold|已售|售出)\\s*\\d+(?:\\.\\d+)?[Kk万万]?\\s*\\+?\\s*[件个]?)/);
                            if (sm) sold = sm[0];
                        }

                        // 评分 — Shopee 评分通常显示为星星或数字
                        var rating = '';
                        var ratingEl = card.querySelector('[class*="rating"], [class*="star"], [class*="score"]');
                        if (ratingEl) rating = (ratingEl.textContent || '').trim();
                        if (!rating) {
                            var rm = cardText.match(/(\\d+(?:\\.\\d+)?)\\s*\\/\\s*5/);
                            if (rm) rating = rm[1];
                        }

                        // 店铺名 — 通常在卡片底部
                        var store = '';
                        var storeEl = card.querySelector('[class*="shop"], [class*="seller"], [class*="store"], [class*="brand"], [class*="merchant"]');
                        if (storeEl) store = (storeEl.textContent || '').trim();

                        // 发货地
                        var location = '';
                        var locEl = card.querySelector('[class*="location"]');
                        if (locEl) location = (locEl.textContent || '').trim();

                        // 图片
                        var imgEl = card.querySelector('img');
                        var image = imgEl ? (imgEl.src || imgEl.dataset.src || imgEl.getAttribute('data-src') || '') : '';

                        seen.add(itemId);
                        results.push({
                            itemId: itemId,
                            title: title,
                            url: href,
                            price: price,
                            origPrice: origPrice,
                            sold: sold,
                            rating: rating,
                            store: store,
                            location: location,
                            image: image
                        });
                    } catch(e) {}
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
                sold_text = item.get("sold", "")

                rating = parse_rating(item.get("rating", ""))
                sales_count = parse_sales(sold_text)
                # 如果 parse_sales 返回 0，尝试直接从文本提取数字
                if sales_count == 0 and sold_text:
                    try:
                        sales_count = int(re.sub(r'[^\d]', '', sold_text.replace(',', '')) or 0)
                    except ValueError:
                        pass

                products.append(self._new_product(
                    product_id=item_id,
                    title=clean_text(item.get("title", "")),
                    price=parse_price(price_text),
                    price_range=price_text,
                    original_price=parse_price(item.get("origPrice", "")),
                    currency=parse_currency(price_text) if price_text else "SGD",
                    rating=rating,
                    review_count=sales_count,  # Shopee 用销量近似
                    sales_count=sales_count,
                    sales_text=sold_text,
                    shop_name=clean_text(item.get("store", "")),
                    condition="New",
                    location=clean_text(item.get("location", "")),
                    category=category or keyword,
                    image_url=item.get("image", ""),
                    url=item.get("url", ""),
                ))

                if len(products) >= 60:
                    break

        except Exception as e:
            logger.error(f"[Shopee] JS 提取失败: {e}")
            import traceback
            traceback.print_exc()

        return products

    # ── 商品详情 ──────────────────────────────────────

    def get_product_detail(self, url: str) -> Optional[Product]:
        page = self._get_page()
        self._rate_limit()

        try:
            page.get(url)
            time.sleep(5)
            ShopeeScraper._dismiss_shopee_popups(page)
            self._shopee_scroll(page, times=2)

            data = page.run_js("""
                var result = {};

                // 标题
                var titleEl = document.querySelector(
                    '[class*="product-title"], [class*="name"], ' +
                    '[class*="attM"], h1, [class*="section-title"]'
                );
                result.title = titleEl ? titleEl.textContent.trim() : document.title;

                // 价格
                var priceEl = document.querySelector(
                    '[class*="price"], [class*="product-price"], ' +
                    '[class*="igwY"]'
                );
                if (priceEl) result.price = priceEl.textContent.trim();

                // 原始价格 (划线价)
                var origEl = document.querySelector(
                    '[class*="original"], [class*="discount"], del, s, ' +
                    '[class*="strikethrough"]'
                );
                if (origEl) result.origPrice = origEl.textContent.trim();

                // 销量
                var soldEl = document.querySelector(
                    '[class*="sold"], [class*="sales"], [class*="item-sold"]'
                );
                if (soldEl) result.sold = soldEl.textContent.trim();

                // 评分
                var ratingEl = document.querySelector(
                    '[class*="rating"], [class*="star"], [class*="score"]'
                );
                if (ratingEl) result.rating = ratingEl.textContent.trim();

                // 店铺
                var storeEl = document.querySelector(
                    '[class*="shop-name"], [class*="seller-name"], ' +
                    '[class*="store-name"], [class*="merchant"]'
                );
                if (storeEl) result.store = storeEl.textContent.trim();

                // 描述
                var descEl = document.querySelector(
                    '[class*="product-detail"], [class*="description"], ' +
                    '[class*="content"]'
                );
                if (descEl) result.description = descEl.textContent.trim().slice(0, 2000);

                return result;
            """)

            if data and data.get("title"):
                item_id = ""
                shop_id = ""
                # Shopee URL: /product/{shop_id}/{item_id} or /{name}-i.{shop_id}.{item_id}
                m = re.search(r'/product/(\d+)/(\d+)', url)
                if m:
                    shop_id = m.group(1)
                    item_id = m.group(2)
                else:
                    m = re.search(r'i\.(\d+)\.(\d+)', url)
                    if m:
                        shop_id = m.group(1)
                        item_id = m.group(2)

                price_text = data.get("price", "")
                return self._new_product(
                    product_id=item_id,
                    title=clean_text(data.get("title", "")),
                    price=parse_price(price_text),
                    price_range=price_text,
                    original_price=parse_price(data.get("origPrice", "")),
                    currency=parse_currency(price_text) if price_text else "SGD",
                    rating=parse_rating(data.get("rating", "")),
                    sales_text=data.get("sold", ""),
                    sales_count=parse_sales(data.get("sold", "")),
                    shop_name=clean_text(data.get("store", "")),
                    url=url,
                )

        except Exception as e:
            logger.error(f"[Shopee] 详情获取失败: {e}")

        return None

    # ── 评论抓取 ──────────────────────────────────────

    def get_reviews(
        self, product_url: str, max_pages: int = MAX_REVIEW_PAGES
    ) -> List[Review]:
        """抓取 Shopee 评论"""
        reviews: List[Review] = []

        page = self._get_page()
        try:
            page.get(product_url)
            time.sleep(5)
            ShopeeScraper._dismiss_shopee_popups(page)

            # 尝试点击评论 tab
            try:
                review_tab = page.ele(
                    '[class*="tab"][class*="review"], [class*="rating"], '
                    '[class*="comment"], [class*="feedback"]',
                    timeout=3
                )
                if review_tab:
                    review_tab.click()
                    time.sleep(3)
            except Exception:
                pass

            for pg in range(1, min(max_pages, 5) + 1):
                self._shopee_scroll(page, times=3)

                items = page.run_js("""
                    var reviews = document.querySelectorAll(
                        '[class*="review-item"], [class*="comment-item"], ' +
                        '[class*="rating-item"], [class*="feedback"]'
                    );
                    var result = [];
                    reviews.forEach(function(r) {
                        var text = (r.textContent || '').trim();
                        if (text.length < 15 || text.length > 3000) return;

                        // 尝试提取评分
                        var rating = 5;
                        var ratingEl = r.querySelector(
                            '[class*="star"], [class*="rating"], ' +
                            'svg, [class*="score"]'
                        );
                        if (ratingEl) {
                            var rt = (ratingEl.textContent || ratingEl.getAttribute('aria-label') || '').trim();
                            var rm = rt.match(/(\\d+)/);
                            if (rm) rating = parseInt(rm[1]) || 5;
                        }

                        // 提取用户名
                        var name = '';
                        var nameEl = r.querySelector('[class*="name"], [class*="user"], [class*="author"]');
                        if (nameEl) name = nameEl.textContent.trim();

                        // 提取日期
                        var date = '';
                        var dateEl = r.querySelector('[class*="date"], [class*="time"]');
                        if (dateEl) date = dateEl.textContent.trim();

                        result.push({
                            content: text,
                            rating: rating,
                            reviewer_name: name,
                            date: date
                        });
                    });
                    return result;
                """)

                for item in (items or []):
                    reviews.append(Review(
                        product_db_id=0,
                        reviewer_name=clean_text(item.get("reviewer_name", "")),
                        content=clean_text(item.get("content", "")),
                        rating=item.get("rating", 5),
                        review_date=item.get("date", "") or now_str(),
                        scraped_at=now_str(),
                    ))

                if len(reviews) >= 50:
                    break
                page_delay()

        except Exception as e:
            logger.error(f"[Shopee] 评论抓取失败: {e}")

        return reviews

    # ── 热销排行 ──────────────────────────────────────

    def get_hot_ranking(self, category: str, top_n: int = 50) -> List[HotRanking]:
        """Shopee 热销排行 — 使用按销量排序的搜索结果"""
        rankings: List[HotRanking] = []
        page = self._get_page()

        # Shopee 排序: 按销量排序
        url = SHOPEE_SEARCH_URL.format(keyword=quote(category)) + "&sortBy=sales"
        try:
            page.get(url)
            time.sleep(6)
            ShopeeScraper._dismiss_shopee_popups(page)
            self._shopee_scroll(page, times=4)

            items = page.run_js("""
                var cards = document.querySelectorAll(
                    '[class*="shopee-search-item-result__item"], ' +
                    '[class*="col-xs-2-4"], ' +
                    'a[data-sqe="item"]'
                );
                var result = [];
                var seen = new Set();
                var rank = 1;

                cards.forEach(function(card) {
                    var linkEl = card.querySelector('a[href*="/product/"]');
                    if (!linkEl && card.tagName === 'A') linkEl = card;
                    if (!linkEl) return;

                    var href = linkEl.href || '';
                    var idMatch = href.match(/i\\.(\\d+)\\.(\\d+)/) || href.match(/\\/product\\/(\\d+)\\/(\\d+)/);
                    var itemId = idMatch ? (idMatch[2] || idMatch[1]) : '';
                    if (!itemId || seen.has(itemId)) return;
                    seen.add(itemId);

                    var title = (linkEl.textContent || '').trim();
                    if (title.length < 10) {
                        var titleEl = card.querySelector('[class*="name"], [class*="title"]');
                        if (titleEl) title = titleEl.textContent.trim();
                    }
                    if (title.length < 10) return;

                    var cardText = (card.textContent || '').trim();
                    var price = '';
                    var pm = cardText.match(/(?:\\$|₱|Rp|RM|S\\$|฿|₫)\\s*[\\d,.]+/);
                    if (pm) price = pm[0];

                    result.push({title: title, price: price, rank: rank++});
                    if (rank > 50) return;
                });

                // 备用: 从链接枚举
                if (result.length === 0) {
                    var links = document.querySelectorAll('a[href*="/product/"]');
                    links.forEach(function(link) {
                        var href = link.href || '';
                        var idMatch = href.match(/i\\.(\\d+)\\.(\\d+)/);
                        var itemId = idMatch ? idMatch[1] + idMatch[2] : href;
                        if (seen.has(itemId)) return;
                        seen.add(itemId);

                        var title = (link.textContent || '').trim();
                        if (title.length < 10) return;
                        if (title.length > 200) title = title.slice(0, 120);

                        result.push({title: title, price: '', rank: rank++});
                        if (rank > 50) return;
                    });
                }

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
            logger.error(f"[Shopee] 排行抓取失败: {e}")

        return rankings

    # ── 辅助方法 ──────────────────────────────────────

    @staticmethod
    def _dismiss_shopee_popups(page) -> None:
        """关闭 Shopee 的各种弹窗（语言选择、优惠券、newsletter）"""
        close_selectors = [
            "svg[class*='close']",
            "[class*='shopee-popup__close']",
            "[class*='modal__close']",
            ".shopee-popup__close-btn",
            "[class*='close-btn']",
            "[class*='popup'] button",
            "button[aria-label*='Close']",
            "button[aria-label*='close']",
        ]
        for sel in close_selectors:
            try:
                el = page.ele(sel, timeout=0.5)
                if el:
                    el.click()
                    time.sleep(0.3)
            except Exception:
                continue

        # 尝试关闭通过文本找到的按钮
        try:
            page.run_js("""
                var buttons = document.querySelectorAll('button');
                buttons.forEach(function(btn) {
                    var text = (btn.textContent || '').trim().toLowerCase();
                    if (text === '×' || text === '✕' || text === 'close' || text === 'skip' || text === 'later') {
                        btn.click();
                    }
                });
            """)
        except Exception:
            pass

        try:
            page.run_js("document.body.click()")
        except Exception:
            pass

    def _shopee_scroll(self, page, times: int = 4) -> None:
        """深度滚动触发 Shopee 懒加载"""
        for i in range(times):
            try:
                scroll_by = random.randint(400, 800)
                page.run_js(f"window.scrollBy(0, {scroll_by})")
                time.sleep(random.uniform(0.8, 1.5))
            except Exception:
                break
        # 慢慢滚回去
        try:
            page.scroll.to_top()
            time.sleep(0.5)
        except Exception:
            pass

    def _load_more_products(self, page) -> bool:
        """Shopee 加载更多商品（滚动到底部触发无限滚动）"""
        try:
            # 方法 1: 点击 "查看更多" 按钮
            more_btn = page.ele(
                '[class*="load-more"], [class*="more"], '
                '[class*="show-more"], button:contains("更多")',
                timeout=2
            )
            if more_btn:
                more_btn.click()
                time.sleep(4)
                return True
        except Exception:
            pass

        # 方法 2: 滚动到底部触发懒加载
        try:
            page.scroll.to_bottom()
            time.sleep(3)
            new_page = page.run_js("return document.querySelectorAll('[class*=\"shopee-search-item\"]').length")
            return True  # 即使没数到也继续
        except Exception:
            pass

        # 方法 3: URL 翻页（部分 Shopee 站点支持）
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
            time.sleep(5)
            return True
        except Exception:
            pass

        return False

    def _diagnose(self, page) -> dict:
        """诊断 Shopee 搜索结果页"""
        result = {}
        try:
            diag = page.run_js("""
                var cards = document.querySelectorAll(
                    '[class*="shopee-search-item-result__item"], ' +
                    '[class*="col-xs-2-4"], ' +
                    'a[data-sqe="item"]'
                );
                var productLinks = document.querySelectorAll('a[href*="/product/"]');
                return JSON.stringify({
                    url: location.href,
                    title: document.title,
                    card_count: cards.length,
                    product_links: productLinks.length,
                    has_captcha: document.body.textContent.includes('captcha') ||
                                 document.body.textContent.includes('verify'),
                    has_cloudflare: document.title.includes('Just a moment') ||
                                    document.title.includes('Checking')
                });
            """)
            result = json.loads(diag)
        except Exception as e:
            logger.warning(f"[Shopee] 诊断失败: {e}")
            result = {"error": str(e)}
        return result

    def _save_debug(self, page, tag: str) -> str:
        """保存调试截图和 HTML"""
        import os
        debug_dir = os.path.join(OUTPUT_DIR, "debug")
        os.makedirs(debug_dir, exist_ok=True)

        ts = time.strftime("%Y%m%d_%H%M%S")
        try:
            html_path = os.path.join(debug_dir, f"shopee_{tag}_{ts}.html")
            with open(html_path, "w", encoding="utf-8") as f:
                f.write(page.html)
            logger.info(f"[Shopee] 调试 HTML 已保存: {html_path}")
        except Exception as e:
            logger.warning(f"[Shopee] HTML 保存失败: {e}")

        try:
            ss_path = os.path.join(debug_dir, f"shopee_{tag}_{ts}.png")
            page.screenshot(path=ss_path, full_page=False)
            logger.info(f"[Shopee] 调试截图已保存: {ss_path}")
        except Exception as e:
            logger.warning(f"[Shopee] 截图保存失败: {e}")

        return debug_dir
