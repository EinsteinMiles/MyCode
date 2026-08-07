"""
Amazon 爬虫
Amazon 反爬极强，使用多重策略：
1. JS 提取（避免 CSS 选择器被类名随机化影响）
2. 长延迟、模拟人类行为
3. 搜索结果通过 XHR 拦截获取结构化数据
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

from config import AMAZON_SEARCH_URL, AMAZON_ITEM_URL, MAX_REVIEW_PAGES, OUTPUT_DIR, logger
from scrapers.base import BaseScraper
from core.models import Product, Review, HotRanking
from core.utils import (
    random_delay, page_delay, parse_price, parse_currency,
    parse_sales, parse_rating, clean_text, now_str,
)


class AmazonScraper(BaseScraper):
    """Amazon 平台爬虫"""

    platform = "amazon"

    # 不同国家的 Amazon
    DOMAINS = {
        "com": "https://www.amazon.com",
        "co.uk": "https://www.amazon.co.uk",
        "de": "https://www.amazon.de",
        "co.jp": "https://www.amazon.co.jp",
        "ca": "https://www.amazon.ca",
    }

    # ── Session Warm-Up ───────────────────────────────

    _warmed_up = False

    def _warm_up(self, page) -> None:
        """Visit Amazon homepage first to establish cookies before searching."""
        if AmazonScraper._warmed_up:
            return

        logger.info("[Amazon] Warming up — visiting homepage first...")
        try:
            page.get("https://www.amazon.com/")
            time.sleep(4)
            try:
                page.scroll.down(300)
                time.sleep(0.5)
            except Exception:
                pass
            AmazonScraper._warmed_up = True
            logger.info("[Amazon] Warm-up complete")
        except Exception as e:
            logger.warning(f"[Amazon] Warm-up failed: {e}")

    # ── 搜索商品 ──────────────────────────────────────

    def search_products(
        self, keyword: str, max_pages: int = 3, category: str = ""
    ) -> List[Product]:
        """
        搜索 Amazon 商品
        Amazon 极其敏感 — 每次请求之间使用长延迟
        """
        max_pages = min(max_pages, 5)
        all_products: List[Product] = []
        page = self._get_page()

        search_url = AMAZON_SEARCH_URL.format(keyword=quote(keyword))
        logger.info(f"[Amazon] 搜索: {keyword} (最多 {max_pages} 页)")

        try:
            # Warm up: visit homepage first
            self._warm_up(page)

            page.get(search_url)
            time.sleep(5)  # Amazon JS 渲染慢，给足时间

            # 检查 CAPTCHA
            if self._check_captcha(page):
                logger.error(
                    "[Amazon] ⚠️ 触发验证码！\n"
                    "   Amazon 反爬非常严格，请：\n"
                    "   1. 在浏览器中手动完成验证\n"
                    "   2. 稍后重试\n"
                    "   3. 降低翻页数量"
                )
                return all_products

            for pg in range(1, max_pages + 1):
                logger.info(f"[Amazon] 解析第 {pg}/{max_pages} 页...")
                self._rate_limit()

                # 人类般滚动
                self._human_like_scroll(page, times=3)

                # 使用 JS 提取（Amazon 类名随机化）
                products = self._extract_by_js(page, keyword, category)
                all_products.extend(products)
                logger.info(f"[Amazon] 第 {pg} 页提取 {len(products)} 个商品")

                if pg < max_pages:
                    if not self._go_next_page(page):
                        logger.info("[Amazon] 无下一页")
                        break
                    # Amazon 特别敏感 — 翻页间长延迟
                    time.sleep(random.uniform(8, 15))

        except Exception as e:
            logger.error(f"[Amazon] 搜索异常: {e}")
            import traceback
            traceback.print_exc()

        logger.info(f"[Amazon] 搜索完成: 共 {len(all_products)} 个商品")
        return all_products

    def _extract_by_js(self, page, keyword: str, category: str) -> List[Product]:
        """通过 JS 提取 Amazon 搜索结果"""
        products: List[Product] = []
        seen_asins: Set[str] = set()

        try:
            items = page.run_js("""
                var items = document.querySelectorAll('[data-component-type="s-search-result"]');
                var result = [];
                items.forEach(function(card) {
                    // 标题
                    var titleEl = card.querySelector('h2 .a-text-normal, h2 a');
                    var title = titleEl ? titleEl.textContent.trim() : '';
                    if (!title || title.length < 5) return;

                    // ASIN (Amazon Standard Identification Number)
                    var asin = card.getAttribute('data-asin') || '';

                    // URL
                    var linkEl = card.querySelector('h2 a');
                    var url = linkEl ? linkEl.href : '';
                    if (!asin && url) {
                        var m = url.match(/\\/dp\\/([A-Z0-9]+)/);
                        if (m) asin = m[1];
                    }

                    // 价格
                    var priceEl = card.querySelector('.a-price .a-offscreen');
                    var price = priceEl ? priceEl.textContent.trim() : '';
                    if (!price) {
                        var wholeEl = card.querySelector('.a-price-whole');
                        var fractionEl = card.querySelector('.a-price-fraction');
                        if (wholeEl) {
                            price = wholeEl.textContent.trim();
                            if (fractionEl) price += fractionEl.textContent.trim();
                        }
                    }

                    // 原始价格 (划线价)
                    var origPriceEl = card.querySelector('.a-text-price .a-offscreen');
                    var origPrice = origPriceEl ? origPriceEl.textContent.trim() : '';

                    // 评分
                    var ratingEl = card.querySelector('.a-icon-star-small .a-icon-alt, .a-icon-alt');
                    var rating = ratingEl ? ratingEl.textContent.trim() : '';

                    // 评论数
                    var reviewEl = card.querySelector('.a-size-base.s-underline-text, .a-size-small .s-link-style');
                    var reviewCount = reviewEl ? reviewEl.textContent.trim() : '';

                    // 徽章 (Best Seller, Amazon's Choice)
                    var badgeEl = card.querySelector('.a-badge-text, .a-badge-label-inner');
                    var badge = badgeEl ? badgeEl.textContent.trim() : '';

                    // Prime 标记
                    var primeEl = card.querySelector('.a-icon-prime');
                    var isPrime = primeEl ? true : false;

                    // 图片
                    var imgEl = card.querySelector('.s-image');
                    var image = imgEl ? (imgEl.src || '') : '';

                    result.push({
                        asin: asin,
                        title: title,
                        url: url,
                        price: price,
                        origPrice: origPrice,
                        rating: rating,
                        reviewCount: reviewCount,
                        badge: badge,
                        isPrime: isPrime,
                        image: image
                    });
                });
                return result;
            """)

            if not items:
                return products

            for item in items:
                asin = item.get("asin", "")
                if asin in seen_asins:
                    continue
                seen_asins.add(asin)

                price_text = item.get("price", "")
                orig_price_text = item.get("origPrice", "")
                rating_text = item.get("rating", "")
                review_text = item.get("reviewCount", "")

                rating = parse_rating(rating_text)
                review_count = 0
                if review_text:
                    try:
                        review_count = int(re.sub(r'[^\d]', '', review_text.replace(',', '')) or 0)
                    except ValueError:
                        review_count = 0

                badge = item.get("badge", "")
                sales_text = badge if "seller" in badge.lower() or "best" in badge.lower() else ""

                products.append(self._new_product(
                    product_id=asin,
                    title=clean_text(item.get("title", "")),
                    price=parse_price(price_text),
                    price_range=price_text,
                    original_price=parse_price(orig_price_text),
                    currency=parse_currency(price_text) if price_text else "USD",
                    rating=rating,
                    review_count=review_count,
                    sales_text=sales_text,
                    sales_count=review_count,  # Amazon 不直接显示销量
                    condition="New",
                    category=category or keyword,
                    image_url=item.get("image", ""),
                    url=item.get("url", ""),
                    extra_json=json.dumps({"badge": badge, "isPrime": item.get("isPrime", False)}),
                ))

                if len(products) >= 50:
                    break

        except Exception as e:
            logger.error(f"[Amazon] JS 提取失败: {e}")

        return products

    # ── 商品详情 ──────────────────────────────────────

    def get_product_detail(self, url: str) -> Optional[Product]:
        page = self._get_page()
        self._rate_limit()

        try:
            page.get(url)
            time.sleep(4)

            data = page.run_js("""
                var result = {};

                var titleEl = document.querySelector('#productTitle');
                result.title = titleEl ? titleEl.textContent.trim() : '';

                var priceEl = document.querySelector('.a-price .a-offscreen, #priceblock_ourprice, #priceblock_dealprice, .a-price-whole');
                result.price = priceEl ? priceEl.textContent.trim() : '';

                var origPriceEl = document.querySelector('.a-text-price .a-offscreen, .basisPrice .a-offscreen');
                result.origPrice = origPriceEl ? origPriceEl.textContent.trim() : '';

                var ratingEl = document.querySelector('#acrPopover .a-icon-alt, .a-icon-star .a-icon-alt');
                result.rating = ratingEl ? ratingEl.textContent.trim() : '';

                var reviewCountEl = document.querySelector('#acrCustomerReviewText');
                result.reviewCount = reviewCountEl ? reviewCountEl.textContent.trim() : '';

                var bsrEl = document.querySelector('#productDetails_detailBullets_sections1 tr, #detailBullets_feature_div tr');
                result.bsr = '';
                if (bsrEl) result.bsr = bsrEl.textContent.trim();

                var brandEl = document.querySelector('#bylineInfo');
                result.brand = brandEl ? brandEl.textContent.trim() : '';

                return result;
            """)

            if data and data.get("title"):
                asin = ""
                m = re.search(r'/dp/([A-Z0-9]+)', url)
                if m:
                    asin = m.group(1)

                price_text = data.get("price", "")
                review_text = data.get("reviewCount", "")
                review_count = 0
                try:
                    review_count = int(re.sub(r'[^\d]', '', review_text.replace(',', '')) or 0)
                except ValueError:
                    pass

                return self._new_product(
                    product_id=asin,
                    title=clean_text(data.get("title", "")),
                    price=parse_price(price_text),
                    price_range=price_text,
                    original_price=parse_price(data.get("origPrice", "")),
                    currency=parse_currency(price_text) if price_text else "USD",
                    rating=parse_rating(data.get("rating", "")),
                    review_count=review_count,
                    shop_name=clean_text(data.get("brand", "")),
                    url=url,
                )

        except Exception as e:
            logger.error(f"[Amazon] 详情获取失败: {e}")

        return None

    # ── 评论抓取 ──────────────────────────────────────

    def get_reviews(
        self, product_url: str, max_pages: int = MAX_REVIEW_PAGES
    ) -> List[Review]:
        """抓取 Amazon 评论"""
        reviews: List[Review] = []

        asin = ""
        m = re.search(r'/dp/([A-Z0-9]+)', product_url)
        if m:
            asin = m.group(1)

        if not asin:
            logger.warning("[Amazon] 无法提取 ASIN")
            return reviews

        page = self._get_page()

        # Amazon 评论页
        review_url = f"https://www.amazon.com/product-reviews/{asin}"
        try:
            page.get(review_url)
            time.sleep(4)

            for pg in range(1, min(max_pages, 5) + 1):
                items = page.run_js("""
                    var reviews = document.querySelectorAll('[data-hook="review"]');
                    var result = [];
                    reviews.forEach(function(r) {
                        var titleEl = r.querySelector('[data-hook="review-title"]');
                        var title = titleEl ? titleEl.textContent.trim() : '';

                        var bodyEl = r.querySelector('[data-hook="review-body"]');
                        var body = bodyEl ? bodyEl.textContent.trim() : '';

                        var ratingEl = r.querySelector('.a-icon-star .a-icon-alt, [data-hook="review-star-rating"] .a-icon-alt');
                        var rating = ratingEl ? ratingEl.textContent.trim() : '';

                        var authorEl = r.querySelector('.a-profile-name');
                        var author = authorEl ? authorEl.textContent.trim() : '';

                        var dateEl = r.querySelector('[data-hook="review-date"]');
                        var date = dateEl ? dateEl.textContent.trim() : '';

                        var verifiedEl = r.querySelector('[data-hook="avp-badge"]');
                        var verified = !!verifiedEl;

                        var helpfulEl = r.querySelector('[data-hook="helpful-vote-statement"]');
                        var helpful = helpfulEl ? helpfulEl.textContent.trim() : '';

                        result.push({
                            title: title, body: body, rating: rating,
                            author: author, date: date,
                            verified: verified, helpful: helpful
                        });
                    });
                    return result;
                """)

                for item in (items or []):
                    rating_text = item.get("rating", "")
                    rating = 5
                    m = re.search(r'(\d+(?:\.\d+)?)', rating_text)
                    if m:
                        rating = min(5, max(1, int(float(m.group(1)))))

                    helpful_count = 0
                    helpful_text = item.get("helpful", "")
                    hm = re.search(r'(\d+)', helpful_text)
                    if hm:
                        helpful_count = int(hm.group(1))

                    reviews.append(Review(
                        product_db_id=0,
                        reviewer_name=clean_text(item.get("author", "")),
                        rating=rating,
                        title=clean_text(item.get("title", "")),
                        content=clean_text(item.get("body", "")),
                        verified_purchase=item.get("verified", False),
                        helpful_count=helpful_count,
                        review_date=clean_text(item.get("date", "")),
                        scraped_at=now_str(),
                    ))

                if len(reviews) >= 50:
                    break
                page_delay()
                self._go_review_next_page(page)

        except Exception as e:
            logger.error(f"[Amazon] 评论抓取失败: {e}")

        return reviews

    # ── 热销排行 ──────────────────────────────────────

    def get_hot_ranking(self, category: str, top_n: int = 50) -> List[HotRanking]:
        """Amazon Best Sellers 排行"""
        rankings: List[HotRanking] = []
        page = self._get_page()

        bsr_url = "https://www.amazon.com/Best-Sellers/zgbs"
        try:
            page.get(bsr_url)
            time.sleep(4)

            items = page.run_js("""
                var items = document.querySelectorAll('.zg-item-immersion, .zg-grid-general-item, #gridItemRoot');
                var result = [];
                var rank = 1;
                items.forEach(function(item) {
                    var titleEl = item.querySelector('.p13n-sc-truncate, [class*="title"]');
                    var title = titleEl ? titleEl.textContent.trim() : '';
                    if (!title) return;

                    var priceEl = item.querySelector('.a-price .a-offscreen');
                    var price = priceEl ? priceEl.textContent.trim() : '';

                    var ratingEl = item.querySelector('.a-icon-alt');
                    var rating = ratingEl ? ratingEl.textContent.trim() : '';

                    result.push({
                        title: title,
                        price: price,
                        rating: rating,
                        rank: rank++
                    });
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
                    rating=parse_rating(item.get("rating", "")),
                    snapshot_date=now_str(),
                ))
                if len(rankings) >= top_n:
                    break

        except Exception as e:
            logger.error(f"[Amazon] 排行抓取失败: {e}")

        return rankings

    # ── 辅助方法 ──────────────────────────────────────

    def _human_like_scroll(self, page, times: int = 4) -> None:
        """模拟人类浏览行为"""
        for i in range(times):
            try:
                scroll_by = random.randint(100, 400)
                page.run_js(f"window.scrollBy(0, {scroll_by})")
                time.sleep(random.uniform(0.8, 2.0))
                if random.random() < 0.25:
                    time.sleep(random.uniform(0.5, 1.5))
            except Exception:
                break
        try:
            page.scroll.to_top()
            time.sleep(0.3)
        except Exception:
            pass

    def _go_next_page(self, page) -> bool:
        """Amazon 翻页"""
        try:
            next_btn = page.ele("a.s-pagination-next, .s-pagination-next", timeout=3)
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

    def _go_review_next_page(self, page) -> bool:
        """评论页翻页"""
        try:
            next_btn = page.ele("a[data-hook='see-all-reviews-link-foot'], li.a-last a", timeout=2)
            if next_btn:
                next_btn.click()
                time.sleep(3)
                return True
        except Exception:
            pass
        return False
