"""
eBay 爬虫 — 重写版
Multi-strategy extraction with diagnosis, redirect handling, and robust fallbacks
"""

from __future__ import annotations

import re
import time
import json
import os
import random
from typing import TYPE_CHECKING, List, Optional, Set
from urllib.parse import quote, urljoin

if TYPE_CHECKING:
    from DrissionPage import ChromiumPage

from config import EBAY_SEARCH_URL, EBAY_ITEM_URL, MAX_REVIEW_PAGES, OUTPUT_DIR, logger
from scrapers.base import BaseScraper
from core.models import Product, Review, HotRanking
from core.utils import (
    random_delay, page_delay, parse_price, parse_currency,
    parse_sales, parse_rating, clean_text, now_str,
)


class EbayScraper(BaseScraper):
    """eBay 平台爬虫 — 多策略版"""

    platform = "ebay"

    # ── 搜索商品 ──────────────────────────────────────

    def search_products(
        self, keyword: str, max_pages: int = 5, category: str = ""
    ) -> List[Product]:
        max_pages = min(max_pages, 10)
        all_products: List[Product] = []
        page = self._get_page()

        search_url = EBAY_SEARCH_URL.format(keyword=quote(keyword))
        logger.info(f"[eBay] Searching: {keyword} (max {max_pages} pages)")
        logger.info(f"[eBay] URL: {search_url}")

        try:
            # ── Step 0: Warm up — visit homepage first to establish session ──
            self._warm_up(page)

            page.get(search_url)
            time.sleep(5)  # Give eBay time to fully render

            # ── Step 1: Diagnose the loaded page ──
            diagnosis = self._diagnose(page)
            logger.info(f"[eBay] Diagnosis: {json.dumps(diagnosis, indent=2)}")

            # Handle redirect (e.g. ebay.com → ebay.com.hk)
            if diagnosis.get("redirected"):
                logger.info(f"[eBay] Redirected to {diagnosis['current_domain']} — continuing...")

            # Dismiss cookie/GDPR banners
            self._dismiss_banners(page)

            # Check for CAPTCHA
            if self._check_captcha(page):
                logger.error("[eBay] ⚠️ CAPTCHA detected! Please complete it in the browser window.")
                self._save_debug(page, "captcha")
                return all_products

            # Check if we see products at all
            total_cards = diagnosis.get("s_card_count", 0) + diagnosis.get("legacy_s_item_count", 0)
            if total_cards == 0:
                logger.error(
                    "[eBay] No product cards found on page.\n"
                    "  s-card count: %d, legacy s-item count: %d\n"
                    "  Possible reasons:\n"
                    "  1. eBay redirected to a localized domain — check diagnosis URL\n"
                    "  2. eBay requires login — try menu [8] to login first\n"
                    "  3. Network/proxy issue — eBay may block your IP\n"
                    "  4. Page didn't render — increase sleep time\n",
                    diagnosis.get("s_card_count", 0),
                    diagnosis.get("legacy_s_item_count", 0),
                )
                self._save_debug(page, "no_items")
                return all_products

            for pg in range(1, max_pages + 1):
                logger.info(f"[eBay] Parsing page {pg}/{max_pages}...")
                self._rate_limit()

                # Scroll to trigger lazy images
                self._scroll_to_load(page, times=2)

                # ── Strategy A: JS extraction (most reliable) ──
                products = self._extract_by_js(page, keyword, category)

                # ── Strategy B: CSS-based fallback ──
                if not products:
                    logger.info("[eBay] JS extraction returned 0, trying CSS...")
                    products = self._extract_by_css(page, keyword, category)

                # ── Strategy C: HTML regex fallback (last resort) ──
                if not products:
                    logger.info("[eBay] CSS extraction returned 0, trying HTML regex...")
                    products = self._extract_by_html_regex(page, keyword, category)

                all_products.extend(products)
                logger.info(f"[eBay] Page {pg}: extracted {len(products)} products")

                if pg < max_pages:
                    if not self._go_next_page(page):
                        logger.info("[eBay] No next page")
                        break
                    time.sleep(random.uniform(3, 6))
                    self._dismiss_banners(page)

        except Exception as e:
            logger.error(f"[eBay] Search exception: {e}")
            import traceback
            traceback.print_exc()
            self._save_debug(page, "exception")

        logger.info(f"[eBay] Search complete: {len(all_products)} products total")
        return all_products

    # ── Session Warm-Up ───────────────────────────────

    _warmed_up = False  # Only warm up once per process

    def _warm_up(self, page) -> None:
        """Visit eBay homepage first to establish cookies/session before searching.
        A direct search from a cold browser looks like a bot."""
        if EbayScraper._warmed_up:
            return

        logger.info("[eBay] Warming up — visiting homepage first...")
        try:
            page.get("https://www.ebay.com/")
            time.sleep(4)

            # Accept cookies / dismiss banners
            self._dismiss_banners(page)

            # Click "Accept cookies" button if present
            try:
                page.run_js("""
                    var btns = document.querySelectorAll('button');
                    btns.forEach(function(btn) {
                        var text = (btn.textContent || '').toLowerCase().trim();
                        if (text === 'accept all' || text === 'accept cookies' ||
                            text === 'i accept' || text === 'agree' || text === 'ok') {
                            btn.click();
                        }
                    });
                """)
                time.sleep(1)
            except Exception:
                pass

            # Scroll a bit to look human
            try:
                page.scroll.down(300)
                time.sleep(0.5)
                page.scroll.up(200)
                time.sleep(0.5)
            except Exception:
                pass

            EbayScraper._warmed_up = True
            logger.info("[eBay] Warm-up complete — session established")
        except Exception as e:
            logger.warning(f"[eBay] Warm-up failed (continuing anyway): {e}")

    # ── Page Diagnosis ────────────────────────────────

    def _diagnose(self, page) -> dict:
        """Diagnose the current page state — critical for debugging"""
        try:
            info = page.run_js("""
                var result = {};
                result.url = location.href;
                result.title = document.title;
                result.domain = location.hostname;
                // eBay changed from li.s-item to li.s-card (~2025+)
                result.s_card_count = document.querySelectorAll('li.s-card').length;
                result.legacy_s_item_count = document.querySelectorAll('li.s-item').length;
                result.all_links = document.querySelectorAll('a').length;
                result.has_search_results = document.querySelector('.srp-results') ? true : false;

                result.body_text_preview = (document.body ? document.body.innerText.substring(0, 500) : '');
                return result;
            """)

            # Determine if redirected
            info["redirected"] = "ebay.com" not in info.get("domain", "")

            return info
        except Exception as e:
            return {"error": str(e)}

    def _dismiss_banners(self, page) -> None:
        """Dismiss cookie consent, GDPR, and other overlay banners"""
        dismiss_js = """
        // Try common banner close buttons
        var buttons = document.querySelectorAll(
            'button[id*="gdpr"], button[class*="gdpr"], ' +
            'button[id*="cookie"], button[class*="cookie"], ' +
            'button[aria-label*="accept"], button[aria-label*="Accept"], ' +
            'a[id*="gdpr"], a[id*="cookie"], ' +
            '.gh-banner-dismiss, #gdpr-banner-accept, ' +
            'button[data-testid*="dismiss"], button[data-testid*="close"]'
        );
        buttons.forEach(function(btn) {
            try { btn.click(); } catch(e) {}
        });

        // Try to remove overlay divs
        var overlays = document.querySelectorAll(
            '[class*="overlay"], [class*="banner"][class*="gdpr"], ' +
            '[class*="banner"][class*="cookie"], [id*="gdpr"], [id*="cookie-banner"]'
        );
        overlays.forEach(function(el) {
            try { el.style.display = 'none'; } catch(e) {}
        });
        """
        try:
            page.run_js(dismiss_js)
            time.sleep(0.5)
        except Exception:
            pass

    def _save_debug(self, page, tag: str) -> str:
        """Save debug screenshot and HTML snippet"""
        try:
            ts = time.strftime("%Y%m%d_%H%M%S")
            # Screenshot
            ss_path = os.path.join(OUTPUT_DIR, f"ebay_debug_{tag}_{ts}.png")
            page.screenshot(ss_path)
            logger.info(f"[eBay] Debug screenshot: {ss_path}")

            # HTML snippet
            html_path = os.path.join(OUTPUT_DIR, f"ebay_debug_{tag}_{ts}.html")
            html_snippet = page.html[:20000] if page.html else ""
            with open(html_path, "w", encoding="utf-8") as f:
                f.write(html_snippet)
            logger.info(f"[eBay] Debug HTML: {html_path}")
            return ss_path
        except Exception as e:
            logger.warning(f"[eBay] Debug save failed: {e}")
            return ""

    # ── Strategy A: JS Extraction ─────────────────────

    def _extract_by_js(self, page, keyword: str, category: str) -> List[Product]:
        """JS-based extraction — primary strategy (updated for new li.s-card structure)"""
        products: List[Product] = []
        seen_ids: Set[str] = set()

        try:
            items = page.run_js("""
                // Try new structure first (li.s-card), fall back to legacy (li.s-item)
                var cards = document.querySelectorAll('li.s-card');
                if (cards.length === 0) {
                    cards = document.querySelectorAll('li.s-item');
                }
                var result = [];

                cards.forEach(function(li) {
                    // Skip ad/placeholder cards (no listing ID)
                    var listingId = li.getAttribute('data-listingid') || '';
                    var itemId = li.id || '';
                    if (!listingId && !itemId) return;

                    // ── Title ──
                    var titleEl = li.querySelector('.s-card__title span')
                               || li.querySelector('.s-card__link span')
                               || li.querySelector('[class*="title"] span')
                               || li.querySelector('.s-item__title span[role="text"]')
                               || li.querySelector('.s-item__title');
                    var title = titleEl ? titleEl.textContent.trim() : '';

                    // Fallback: get first meaningful text span
                    if (!title || title.length < 3) {
                        var spans = li.querySelectorAll('.su-styled-text.primary.default');
                        if (spans.length > 0) {
                            title = spans[0].textContent.trim();
                        }
                    }

                    if (!title || title.length < 3) return;
                    // Filter ad cards and placeholder listings
                    if (title === 'Shop on eBay' || title.startsWith('New listing')
                        || title === '新物品刊登' || title.includes('新物品刊登')) return;

                    // ── URL ──
                    var linkEl = li.querySelector('a.s-card__link') || li.querySelector('a.s-item__link');
                    var url = linkEl ? linkEl.href : '';

                    // ── Item ID from URL or data attributes ──
                    if (!listingId) {
                        var idMatch = url.match(/itm[/-](\\d+)/i);
                        if (idMatch) listingId = idMatch[1];
                    }
                    if (!listingId) listingId = li.getAttribute('data-item-id') || '';

                    // ── Price ──
                    var priceEl = li.querySelector('.s-card__price')
                               || li.querySelector('[class*="price"] .su-styled-text')
                               || li.querySelector('.s-item__price');
                    var price = priceEl ? priceEl.textContent.trim() : '';

                    // ── Subtitle/Condition ──
                    var subEl = li.querySelector('.s-card__subtitle span')
                             || li.querySelector('.s-item__subtitle');
                    var conditionText = subEl ? subEl.textContent.trim() : '';

                    // ── Extract all text spans for pattern-based field detection ──
                    var allSpans = li.querySelectorAll('span');
                    var spanTexts = [];
                    allSpans.forEach(function(s) {
                        var t = s.textContent.trim();
                        if (t && t.length > 1 && t.length < 200 && t !== '在新窗口或标签中打开') {
                            spanTexts.push(t);
                        }
                    });

                    var seller = '', sold = '', shipping = '', location = '', sellerRating = '';

                    for (var k = spanTexts.length - 1; k >= 0; k--) {
                        var text = spanTexts[k];
                        // Seller rating: "98.5% 好评率 (132)" or "99.3% positive (55K)"
                        if (!sellerRating && text.match(/(\\d+(?:\\.\\d+)?)\\s*%/) && text.length < 40) {
                            sellerRating = text;
                            // Seller name is typically right before rating
                            if (k > 0 && !spanTexts[k-1].match(/\\d+%|已售|售出|运费|发货|助赞/) && spanTexts[k-1].length < 40) {
                                seller = spanTexts[k-1];
                            }
                            continue;
                        }
                        // Sold: "已售出 32 件" or "1.2K sold"
                        if (!sold && text.match(/(已售出?|sold)/i)) {
                            sold = text;
                            continue;
                        }
                        // Shipping: "+134.99元 运费" or "+$5.00 shipping"
                        if (!shipping && text.match(/(运费|shipping)/i) && text.match(/[¥$€£元]|\\d/)) {
                            shipping = text;
                            continue;
                        }
                        // Location: "发货地： 日本" or "from United States"
                        if (!location && text.match(/(发货地|from\\s)/i)) {
                            location = text;
                            continue;
                        }
                    }

                    // Also try to find seller in the forward direction (after sold count)
                    for (var m = 0; m < spanTexts.length - 1; m++) {
                        if (!seller && spanTexts[m].match(/(已售出?|sold)/i) && m + 1 < spanTexts.length) {
                            var next = spanTexts[m + 1];
                            if (next && !next.match(/\\d+%|助赞/) && next.length < 40) {
                                seller = next;
                            }
                        }
                    }

                    // ── Image ──
                    var imgEl = li.querySelector('img.s-card__image')
                             || li.querySelector('.s-item__image img')
                             || li.querySelector('img[src]');
                    var image = '';
                    if (imgEl) {
                        image = imgEl.src || imgEl.getAttribute('data-src') || '';
                    }

                    // ── Rating ──
                    var ratingEl = li.querySelector('[class*="star"] [class*="clipped"]');
                    var rating = ratingEl ? ratingEl.textContent.trim() : '';

                    result.push({
                        title: title, url: url, price: price,
                        shipping: shipping, subtitle: conditionText,
                        seller: seller, sold: sold, location: location,
                        image: image, itemId: listingId, rating: rating,
                        sellerRating: sellerRating
                    });
                });
                return result;
            """)

            if not items:
                logger.warning("[eBay] JS extraction: no cards found")
                return products

            logger.info(f"[eBay] JS found {len(items)} raw items")

            for item in items:
                item_id = item.get("itemId", "")
                if not item_id or item_id in seen_ids:
                    continue
                seen_ids.add(item_id)

                price_text = item.get("price", "")

                # ── Condition ──
                subtitle = item.get("subtitle", "")
                condition = ""
                if re.search(r'pre.owned|used|二手', subtitle, re.I):
                    condition = "Used"
                elif re.search(r'refurbished|翻新', subtitle, re.I):
                    condition = "Refurbished"
                elif re.search(r'open box', subtitle, re.I):
                    condition = "Open Box"
                elif re.search(r'brand new|new\b|全新', subtitle, re.I):
                    condition = "New"
                else:
                    condition = subtitle

                # ── Shipping cost ──
                shipping_cost = 0.0
                shipping_text = item.get("shipping", "")
                if shipping_text and "free" not in shipping_text.lower():
                    shipping_cost = parse_price(shipping_text)

                # ── Seller info ──
                seller_text = item.get("seller", "")
                seller_rating_text = item.get("sellerRating", "")
                seller_rating = 0.0
                seller_feedback = 0

                if seller_rating_text:
                    rm = re.search(r'(\d+(?:\.\d+)?)\s*%', seller_rating_text)
                    if rm:
                        seller_rating = float(rm.group(1))
                    fm = re.search(r'\((\d+(?:,\d{3})*)\)', seller_rating_text)
                    if fm:
                        seller_feedback = int(fm.group(1).replace(',', ''))

                # Also parse from seller text
                if seller_text and not seller_rating:
                    rm = re.search(r'(\d+(?:\.\d+)?)\s*%', seller_text)
                    if rm:
                        seller_rating = float(rm.group(1))
                    fm = re.search(r'\((\d+(?:,\d{3})*)\)', seller_text)
                    if fm:
                        seller_feedback = int(fm.group(1).replace(',', ''))

                products.append(self._new_product(
                    product_id=item_id,
                    title=clean_text(item.get("title", "")),
                    price=parse_price(price_text),
                    price_range=price_text,
                    currency=parse_currency(price_text) if price_text else "USD",
                    shipping_cost=shipping_cost,
                    condition=condition,
                    sales_text=item.get("sold", ""),
                    sales_count=parse_sales(item.get("sold", "")),
                    shop_name=clean_text(seller_text),
                    seller_rating=seller_rating,
                    seller_feedback_count=seller_feedback,
                    location=clean_text(item.get("location", "")),
                    rating=parse_rating(item.get("rating", "")),
                    category=category or keyword,
                    image_url=item.get("image", ""),
                    url=item.get("url", ""),
                ))

                if len(products) >= 60:
                    break

        except Exception as e:
            logger.error(f"[eBay] JS extraction error: {e}")
            import traceback
            traceback.print_exc()

        return products

    # ── Strategy B: CSS Extraction ────────────────────

    def _extract_by_css(self, page, keyword: str, category: str) -> List[Product]:
        """CSS selector extraction — fallback if JS fails"""
        products: List[Product] = []
        seen_ids: Set[str] = set()

        try:
            items = self._safe_extract_list(page, "li.s-item", timeout=5)
            logger.info(f"[eBay] CSS found {len(items)} li.s-item elements")

            for li in items:
                try:
                    cls = li.attr("class") or ""
                    if "s-item--watch" in cls:
                        continue

                    title = self._safe_extract(
                        li,
                        [".s-item__title span[role='text']", ".s-item__title", "span[role='text']"],
                        timeout=2,
                    )
                    if not title or len(title) < 3:
                        continue
                    if title.startswith(("New listing", "Shop on eBay")):
                        continue

                    link_el = li.ele("a.s-item__link", timeout=1)
                    url = link_el.attr("href") if link_el else ""
                    item_id = ""
                    m = re.search(r'itm[/-](\d+)', url, re.I)
                    if m:
                        item_id = m.group(1)
                    if not item_id or item_id in seen_ids:
                        continue
                    seen_ids.add(item_id)

                    price_text = self._safe_extract(li, [".s-item__price"], timeout=1)
                    shipping_text = self._safe_extract(li, [".s-item__shipping", ".s-item__logisticsCost"], timeout=1)
                    sales_text = self._safe_extract(li, [".s-item__quantitySold"], timeout=1)
                    seller_text = self._safe_extract(li, [".s-item__seller-info-text"], timeout=1)
                    location = self._safe_extract(li, [".s-item__itemLocation"], timeout=1)

                    shipping_cost = 0.0
                    if shipping_text and "free" not in shipping_text.lower():
                        shipping_cost = parse_price(shipping_text)

                    products.append(self._new_product(
                        product_id=item_id,
                        title=clean_text(title),
                        price=parse_price(price_text),
                        price_range=price_text,
                        currency=parse_currency(price_text) if price_text else "USD",
                        shipping_cost=shipping_cost,
                        sales_text=sales_text,
                        sales_count=parse_sales(sales_text),
                        shop_name=clean_text(seller_text),
                        location=clean_text(location),
                        category=category or keyword,
                        url=url,
                    ))

                    if len(products) >= 60:
                        break

                except Exception:
                    continue

        except Exception as e:
            logger.error(f"[eBay] CSS extraction error: {e}")

        return products

    # ── Strategy C: HTML Regex Extraction ──────────────

    def _extract_by_html_regex(self, page, keyword: str, category: str) -> List[Product]:
        """HTML regex extraction — absolute last resort when page isn't fully rendered"""
        products: List[Product] = []
        seen_ids: Set[str] = set()

        try:
            html = page.html
            if not html:
                return products

            # Find all eBay item links in the raw HTML
            # Pattern: /itm/123456789012 or itm/123456789012
            item_links = re.findall(
                r'https?://(?:www\.)?ebay\.[a-z.]+/itm/(\d+)[^"\']*',
                html, re.I
            )
            # Also match relative URLs
            item_links += re.findall(r'href="(/itm/(\d+)[^"]*)"', html, re.I)
            # Flatten
            all_ids = set()
            for match in item_links:
                if isinstance(match, tuple):
                    all_ids.add(match[0] if match[0].startswith('/itm/') else match[1])
                else:
                    all_ids.add(match)

            logger.info(f"[eBay] HTML regex found {len(all_ids)} item IDs")

            for item_id in all_ids:
                if item_id in seen_ids:
                    continue
                seen_ids.add(item_id)

                # Build URL
                url = f"https://www.ebay.com/itm/{item_id}"

                # Try to find the title near the link in HTML
                title = ""
                # Look for text near the item ID
                title_pattern = re.compile(
                    re.escape(item_id) + r'.{0,500}?"([^"]{10,200})"',
                    re.DOTALL
                )
                tm = title_pattern.search(html)
                if tm:
                    title = clean_text(tm.group(1))
                if not title:
                    title = f"eBay item {item_id}"

                products.append(self._new_product(
                    product_id=item_id,
                    title=title,
                    price=0.0,
                    currency="USD",
                    category=category or keyword,
                    url=url,
                ))

                if len(products) >= 60:
                    break

        except Exception as e:
            logger.error(f"[eBay] HTML regex extraction error: {e}")

        return products

    # ── 商品详情 ──────────────────────────────────────

    def get_product_detail(self, url: str) -> Optional[Product]:
        page = self._get_page()
        self._rate_limit()

        try:
            page.get(url)
            time.sleep(4)
            self._dismiss_banners(page)

            data = page.run_js("""
                var result = {};
                var titleEl = document.querySelector('h1.it-ttl, h1[itemprop="name"], h1.x-item-title__mainTitle span.ux-textspans');
                result.title = titleEl ? titleEl.textContent.trim() : '';

                var priceEl = document.querySelector('.x-price-primary span.ux-textspans, .vi-price, [itemprop="price"]');
                result.price = priceEl ? priceEl.textContent.trim() : '';

                var condEl = document.querySelector('.x-item-condition-text span.ux-textspans, .u-flL.condText');
                result.condition = condEl ? condEl.textContent.trim() : '';

                var sellerEl = document.querySelector('.mbg-nw, [data-testid="ux-about-this-seller"] span.ux-textspans');
                result.seller = sellerEl ? sellerEl.textContent.trim() : '';

                var soldEl = document.querySelector('.vi-qtyS .vi-qtyS-value, .d-quantity__availability .ux-textspans--BOLD');
                result.sold = soldEl ? soldEl.textContent.trim() : '';

                var shippingEl = document.querySelector('.ux-layout-section--shipping .ux-textspans');
                result.shippingCost = shippingEl ? shippingEl.textContent.trim() : '';

                var imgEl = document.querySelector('.ux-image-carousel-item img');
                result.image = imgEl ? (imgEl.src || '') : '';

                return result;
            """)

            if data and data.get("title"):
                item_id = ""
                m = re.search(r'itm[/-](\d+)', url, re.I)
                if m:
                    item_id = m.group(1)

                price_text = data.get("price", "")
                return self._new_product(
                    product_id=item_id,
                    title=clean_text(data.get("title", "")),
                    price=parse_price(price_text),
                    price_range=price_text,
                    currency=parse_currency(price_text) if price_text else "USD",
                    condition=data.get("condition", ""),
                    sales_text=data.get("sold", ""),
                    sales_count=parse_sales(data.get("sold", "")),
                    shop_name=clean_text(data.get("seller", "")),
                    image_url=data.get("image", ""),
                    url=url,
                )

        except Exception as e:
            logger.error(f"[eBay] Detail fetch failed: {e}")

        return None

    # ── 评论抓取 ──────────────────────────────────────

    def get_reviews(
        self, product_url: str, max_pages: int = MAX_REVIEW_PAGES
    ) -> List[Review]:
        reviews: List[Review] = []
        item_id = ""
        m = re.search(r'itm[/-](\d+)', product_url, re.I)
        if m:
            item_id = m.group(1)

        if not item_id:
            logger.warning("[eBay] Cannot extract item ID")
            return reviews

        page = self._get_page()
        # eBay item page itself has reviews section
        try:
            page.get(f"https://www.ebay.com/itm/{item_id}")
            time.sleep(4)
            self._dismiss_banners(page)

            # Scroll to reviews
            page.run_js("""
                var reviewSection = document.querySelector('[data-testid="reviews"], #reviews, .reviews-section');
                if (reviewSection) reviewSection.scrollIntoView();
            """)
            time.sleep(2)

            for pg in range(1, min(max_pages, 5) + 1):
                items = page.run_js("""
                    var cards = document.querySelectorAll('[class*="review"] [class*="card"], .ebay-review-card, .review-item');
                    if (cards.length === 0) {
                        // Broader search
                        cards = document.querySelectorAll('[data-testid*="review"], [class*="review"]');
                    }
                    var result = [];
                    cards.forEach(function(card) {
                        var text = (card.textContent || '').trim();
                        if (text.length > 30 && text.length < 3000) {
                            // Extract rating stars
                            var ratingEl = card.querySelector('[class*="star"], [aria-label*="star"], [class*="rating"]');
                            var rating = 5;
                            if (ratingEl) {
                                var label = ratingEl.getAttribute('aria-label') || ratingEl.textContent || '';
                                var rm = label.match(/(\\d+)/);
                                if (rm) rating = parseInt(rm[1]);
                                if (rating > 5) rating = Math.round(rating / 20);
                            }
                            result.push({content: text, rating: rating});
                        }
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
            logger.error(f"[eBay] Review fetch failed: {e}")

        return reviews

    # ── 热销排行 ──────────────────────────────────────

    def get_hot_ranking(self, category: str, top_n: int = 50) -> List[HotRanking]:
        rankings: List[HotRanking] = []
        page = self._get_page()

        url = EBAY_SEARCH_URL.format(keyword=quote(category)) + "&_sop=16"
        try:
            page.get(url)
            time.sleep(4)

            items = page.run_js("""
                var items = document.querySelectorAll('li.s-item');
                var result = [];
                var rank = 1;
                items.forEach(function(li) {
                    if (li.classList.contains('s-item--watch')) return;
                    var titleEl = li.querySelector('.s-item__title span[role="text"]') || li.querySelector('.s-item__title');
                    var title = titleEl ? titleEl.textContent.trim() : '';
                    if (!title || title.startsWith('Shop on eBay')) return;
                    var priceEl = li.querySelector('.s-item__price');
                    result.push({
                        title: title,
                        price: priceEl ? priceEl.textContent.trim() : '',
                        sales: '',
                        rank: rank++
                    });
                    if (rank > 50) return;
                });
                return result;
            """)

            for item in (items or []):
                price_text = item.get("price", "")
                rankings.append(HotRanking(
                    platform=self.platform,
                    category=category,
                    rank=item.get("rank", 0),
                    title=clean_text(item.get("title", "")),
                    price=parse_price(price_text),
                    sales_text=item.get("sales", ""),
                    snapshot_date=now_str(),
                ))
                if len(rankings) >= top_n:
                    break

        except Exception as e:
            logger.error(f"[eBay] Ranking fetch failed: {e}")

        return rankings

    # ── 翻页 ──────────────────────────────────────────

    def _go_next_page(self, page) -> bool:
        """eBay pagination"""
        # Method 1: Click "Next" button
        next_selectors = [
            "a.pagination__next",
            "a[type='next']",
            ".pagination__item:last-child a",
            "a[aria-label*='Next']",
            "a[aria-label*='next']",
            "a:contains('Next')",
        ]
        for sel in next_selectors:
            try:
                btn = page.ele(sel, timeout=2)
                if btn:
                    btn.click()
                    time.sleep(3)
                    return True
            except Exception:
                continue

        # Method 2: URL-based pagination
        try:
            current_url = page.url
            m = re.search(r'[&?]_pgn=(\d+)', current_url)
            if m:
                current_page = int(m.group(1))
                new_url = re.sub(r'([&?])_pgn=\d+', f'\\1_pgn={current_page + 1}', current_url)
            else:
                sep = "&" if "?" in current_url else "?"
                new_url = current_url + f"{sep}_pgn=2"
            page.get(new_url)
            time.sleep(3)
            return True
        except Exception:
            pass

        return False

    # ── 安全提取（带超时的 CSS 提取）─────────────────

    def _safe_extract(
        self, element, selectors: List[str],
        default: str = "", attribute: str = "text", timeout: int = 2,
    ) -> str:
        """Multi-selector extraction from a parent element"""
        for sel in selectors:
            try:
                el = element.ele(sel, timeout=timeout)
                if el:
                    if attribute == "text":
                        return clean_text(el.text) or default
                    else:
                        return el.attr(attribute) or default
            except Exception:
                continue
        return default
