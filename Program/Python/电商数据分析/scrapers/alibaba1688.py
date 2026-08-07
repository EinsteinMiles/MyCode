"""
1688 爬虫 — 实际验证版本
已验证：1688 搜索页可用，offer 链接可达 46 个/页
核心策略：querySelectorAll('[href*="offer"]') → 容器文本 → 正则提取
"""

from __future__ import annotations

import time
import re
import json
import os
import random
import urllib.parse
from typing import TYPE_CHECKING, List, Optional

if TYPE_CHECKING:
    from DrissionPage import ChromiumPage

from config import OUTPUT_DIR, logger
from scrapers.base import BaseScraper
from core.models import Product, Review, HotRanking
from core.utils import parse_price, parse_sales, clean_text, now_str


class Alibaba1688Scraper(BaseScraper):
    """1688 平台爬虫（实测版）"""

    platform = "1688"

    # ── 搜索商品 ──────────────────────────────────────

    def search_products(
        self, keyword: str, max_pages: int = 5, category: str = ""
    ) -> List[Product]:
        max_pages = min(max_pages, 20)
        all_products: List[Product] = []
        page = self._get_page()

        # 加载 Cookie（如果有的话）
        self.browser_mgr.load_cookies("1688")

        # 1688 服务器需 GBK 编码 URL 参数才能正确显示中文
        kw_encoded = urllib.parse.quote(keyword.encode("gbk"))
        url = f"https://s.1688.com/selloffer/offer_search.htm?keywords={kw_encoded}"
        logger.info(f"[1688] {keyword} (最多{max_pages}页)")

        try:
            page.get(url, timeout=30)
            time.sleep(5)

            # ── 登录墙检测 ──
            if self._is_login_wall(page):
                logger.warning("[1688] ⚠️  需要登录！请先运行 login_helper.py 登录")
                logger.warning("[1688] 运行: python3 login_helper.py 1688")
                return all_products

            # ── 如果搜索框仍然乱码，重新导航 ──
            self._fix_search_keyword(page, keyword)

            for pg in range(1, max_pages + 1):
                logger.info(f"[1688] 第 {pg}/{max_pages} 页")
                self._rate_limit()
                # 滚动触发懒加载（1688 商品列表是异步加载的）
                self._scroll_to_load(page, times=6)

                products = self._extract_products(page, keyword, category)
                if not products:
                    # 保底：检查是否又被踢到登录页
                    if self._is_login_wall(page):
                        logger.warning(f"[1688] 第{pg}页被踢回登录页")
                        break
                    self._debug_screenshot(page, f"1688_pg{pg}")
                    logger.warning(f"[1688] 第{pg}页无数据")
                    break

                all_products.extend(products)
                logger.info(f"[1688] → {len(products)} 个商品 (累计 {len(all_products)})")

                if pg < max_pages:
                    if not self._try_next_page(page):
                        break
                    time.sleep(random.uniform(3, 6))

        except Exception as e:
            logger.error(f"[1688] 异常: {e}")

        logger.info(f"[1688] 完成: {len(all_products)} 个商品")
        return all_products

    # ── 搜索框关键词修正 ──────────────────────────────

    def _fix_search_keyword(self, page, keyword: str) -> None:
        """
        检测搜索框内容是否与输入一致，不一致（乱码）则导航到正确 GBK 编码 URL。
        """
        try:
            result = page.run_js("""
                var inputs = document.querySelectorAll('input[type="text"], input:not([type])');
                for (var i = 0; i < inputs.length; i++) {
                    var v = inputs[i].value || '';
                    if (v.length > 0) {
                        return JSON.stringify({value: v, index: i});
                    }
                }
                return JSON.stringify({value: '', index: -1});
            """)
            data = json.loads(result)
            current_val = data.get("value", "")

            if not current_val or keyword not in current_val:
                if current_val:
                    logger.info(f"[1688] 搜索框乱码: '{current_val[:20]}' → 修正")
                # 直接导航到正确编码的 URL（不走表单提交避免二次编码）
                kw_encoded = urllib.parse.quote(keyword.encode("gbk"))
                correct_url = f"https://s.1688.com/selloffer/offer_search.htm?keywords={kw_encoded}"
                logger.info(f"[1688] 重新导航到正确 URL")
                page.get(correct_url)
                time.sleep(3)
        except Exception as e:
            logger.debug(f"[1688] 搜索框修正跳过: {e}")

    # ── 登录墙检测 ──────────────────────────────────────

    def _is_login_wall(self, page) -> bool:
        """检测当前页面是否是登录墙"""
        try:
            current_url = page.run_js("return location.href") or ""
            if any(kw in current_url for kw in ["login.taobao.com", "login.1688.com"]):
                return True
            # 也检查页面内容
            if "请登录" in (page.run_js("return document.title") or ""):
                return True
        except Exception:
            pass
        return False

    # ── 核心提取（经过实际验证的 JS）──────────────────

    def _extract_products(self, page, keyword: str, category: str) -> List[Product]:
        """
        1688 搜索页商品提取。

        策略：
        1. JS 层：通过 detail.m.1688.com 链接定位，向上找单品卡片容器
        2. Python 层：正则提取价格/销量/店铺/所在地

        注意：1688 必须登录后才能访问搜索页
        """
        raw = page.run_js("""
var links = document.querySelectorAll('a[href*="detail.m.1688.com"]');
var seen = {};
var items = [];

for (var i = 0; i < links.length; i++) {
    var a = links[i];
    var href = a.getAttribute('href') || '';
    var m = href.match(/offerId=(\\d+)/);
    if (!m) continue;
    var oid = m[1];
    if (seen[oid]) continue;
    seen[oid] = true;

	    // 向上找单品卡片容器
	    var card = a.closest('[class*="offer-card"], [class*="OfferCard"], [class*="offer-item"], [class*="card"], li, .item');
	    if (!card) {
	        card = a;
	        for (var j = 0; j < 8; j++) {
	            card = card.parentElement;
	            if (!card) break;
	            var w = card.getBoundingClientRect().width;
	            if (w >= 200 && w <= 650) break;
	        }
	    }

	    // 提取卡片内文本
    var text = (card.textContent || '').replace(/\\s+/g, ' ').trim().substring(0, 800);

	    // ── 标题提取 ──
	    // 优先从产品 offer 链接自身的 title 属性获取
	    var title = (a.getAttribute('title') || '').trim();
	    // 过滤无效标题：聊天提示、找相似
	    if (title.indexOf('点此可以直接和卖家交流') === 0 || title.indexOf('找相似') === 0 || title.length < 5) {
	        title = '';
	    }
	    // 策略2：从卡内其他 a[title] 提取（排除聊天提示等）
	    if (!title) {
	        var allAs = card.querySelectorAll('a[title]');
	        for (var k = 0; k < allAs.length; k++) {
	            var t = (allAs[k].getAttribute('title') || '').trim();
	            if (t.length > 8 && t.indexOf('点此可以直接和卖家交流') !== 0 && t.indexOf('找相似') !== 0) {
	                title = t;
	                break;
	            }
	        }
	    }
	    // 策略3：class 含 title/name/subject 的元素
	    if (!title) {
	        var titleEl = card.querySelector('[class*="title"], [class*="name"], [class*="subject"]');
	        if (titleEl) {
	            var te = (titleEl.textContent || '').trim();
	            if (te.length > 5) title = te;
	        }
	    }
	    // 策略4：纯文本兜底
	    if (!title || title.length < 3) {
	        title = (a.textContent || '').trim().substring(0, 200);
	    }

    // 图片
    var img = card.querySelector('img');
    var imgSrc = img ? (img.getAttribute('src') || img.getAttribute('data-src') || '') : '';

    // 价格（尝试从卡片内价格元素提取）
    var priceText = '';
    var priceEl = card.querySelector('[class*="price"]');
    if (priceEl) {
        priceText = (priceEl.textContent || '').trim().substring(0, 50);
    }

    // 销量/成交
    var salesText = '';
    var salesEl = card.querySelector('[class*="sale"], [class*="trade"], [class*="offer"]');
    if (salesEl) {
        salesText = (salesEl.textContent || '').trim().substring(0, 50);
    }

    // 店铺名
    var shopText = '';
    var shopEl = card.querySelector('[class*="shop"], [class*="company"], [class*="supplier"]');
    if (shopEl) {
        shopText = (shopEl.textContent || '').trim().substring(0, 50);
    }

    items.push({
        oid: oid, href: href, title: title, text: text, img: imgSrc,
        priceText: priceText, salesText: salesText, shopText: shopText
    });

    if (items.length >= 40) break;
}

return JSON.stringify(items);
""")

        if not raw:
            return []

        try:
            items = json.loads(raw)
        except json.JSONDecodeError:
            return []

        products = []
        for item in items:
            oid = item.get("oid", "")
            href = item.get("href", "")
            img = item.get("img", "")
            text = item.get("text", "")

            # 标题清理
            title = self._clean_title(item.get("title", ""))

            if not title or len(title) < 3:
                continue

            # 构建 URL
            url = href
            if url.startswith("//"):
                url = "https:" + url
            elif url and not url.startswith("http"):
                url = "https:" + url

            # ── 价格提取 ──
            price = 0.0
            price_range = ""
            # 优先使用卡片内 price 元素文本
            price_text = item.get("priceText", "")
            search_text = price_text if price_text else text
            # 1688: ¥5.00-15.00 或 ¥19.90
            price_match = re.search(
                r'[¥￥]\s*(\d+(?:\.\d{1,2})?)\s*(?:[-~]\s*[¥￥]?\s*(\d+(?:\.\d{1,2})?))?',
                search_text
            )
            if price_match:
                low = price_match.group(1)
                high = price_match.group(2)
                try:
                    price = float(low)
                except ValueError:
                    price = 0.0
                price_range = price_match.group(0)
            else:
                # 纯数字价格（避免匹配评分等数字）
                num_match = re.search(r'(?<!\d)(\d{1,5}\.\d{2})(?!\d)', text)
                if num_match:
                    try:
                        price = float(num_match.group(1))
                        price_range = f"¥{price:.2f}"
                    except ValueError:
                        pass

            # ── 销量提取 ──
            sales_text = ""
            sales_count = 0
            # 优先使用卡片内 sales 元素
            sales_raw = item.get("salesText", "")
            if sales_raw:
                sales_text = sales_raw
                sales_count = parse_sales(sales_raw)
            if not sales_text:
                trade_match = re.search(
                    r'(?:成交|已售|销量)\s*([\d.]+[万万千]?\+?\s*(?:笔|件|单)?)',
                    text
                )
                if trade_match:
                    sales_text = trade_match.group(0)
                    sales_count = parse_sales(sales_text)

            # ── 公司名 ──
            shop_name = ""
            shop_raw = item.get("shopText", "")
            if shop_raw:
                shop_name = shop_raw[:50]
            if not shop_name:
                company_match = re.search(
                    r'([一-鿿]{2,20}(?:有限公司|有限责任公司|厂|经营部|商行|商贸|实业))',
                    text
                )
                if company_match:
                    shop_name = company_match.group(1)

            # ── 所在地 ──
            location = ""
            loc_match = re.search(r'(?:所在地|发货|产地)[：:]\s*([一-鿿]{2,8})', text)
            if loc_match:
                location = loc_match.group(1)

            # ── 起批量 ──
            moq = 0
            moq_match = re.search(r'[≥>=]\s*(\d+)\s*(?:件|个|套|双)', text)
            if not moq_match:
                moq_match = re.search(r'(\d+)\s*(?:件|个|套|双)起批', text)
            if moq_match:
                try:
                    moq = int(moq_match.group(1))
                except ValueError:
                    pass

            products.append(Product(
                platform=self.platform,
                product_id=oid,
                title=title,
                price=price,
                price_range=price_range,
                sales_count=sales_count,
                sales_text=sales_text,
                shop_name=shop_name,
                location=location,
                category=category or keyword,
                image_url=img,
                url=url,
                moq=moq,
                first_seen=now_str(),
                last_updated=now_str(),
            ))

            if len(products) >= 40:
                break

        return products

    @staticmethod
    def _clean_title(title: str) -> str:
        """清理 1688 商品标题"""
        if not title:
            return ""
        # 移除"找相似"前缀
        title = re.sub(r'^找相似\s*', '', title)
        # 移除多余的空白
        title = re.sub(r'\s+', ' ', title).strip()
        return title

    # ── 商品详情 ──────────────────────────────────────

    def get_product_detail(self, url: str) -> Optional[Product]:
        page = self._get_page()
        self._rate_limit()
        try:
            page.get(url)
            time.sleep(3)
            self._scroll_to_load(page, times=3)

            data = page.run_js("""
                var h1 = document.querySelector('h1');
                var title = (h1 && h1.textContent || document.title || '').trim();
                var body = (document.body && document.body.textContent || '');
                var p = body.match(/[¥￥]\\s*(\\d+(\\.\\d{1,2})?)/);
                var price = p ? p[1] : '';
                return JSON.stringify({title: title, price: price});
            """)
            if data:
                d = json.loads(data)
                return Product(
                    platform=self.platform,
                    title=clean_text(d.get("title", "")),
                    price=parse_price(d.get("price", "0")),
                    url=url,
                    first_seen=now_str(),
                    last_updated=now_str(),
                )
        except Exception as e:
            logger.error(f"[1688] 详情失败: {e}")
        return None

    # ── 评论 ──────────────────────────────────────────

    def get_reviews(self, product_url: str, max_pages: int = 5) -> List[Review]:
        page = self._get_page()
        reviews: List[Review] = []
        try:
            page.get(product_url)
            time.sleep(3)
            # 尝试点击评价 tab
            for sel in ["a:contains('评价')", "[class*='review']", "span:contains('评价')"]:
                try:
                    tab = page.ele(sel, timeout=2)
                    if tab:
                        tab.click()
                        time.sleep(2)
                        break
                except Exception:
                    continue

            for pg in range(max_pages):
                items = page.run_js("""
                    var els = document.querySelectorAll('[class*="comment"], [class*="review"], [class*="evaluate"]');
                    var r = [];
                    els.forEach(function(el) {
                        var t = (el.textContent || '').trim();
                        if (t.length > 10 && t.length < 2000) r.push(t);
                    });
                    return r;
                """)
                if items:
                    for t in items:
                        reviews.append(Review(
                            product_db_id=0, content=clean_text(t),
                            rating=5, review_date=now_str(), scraped_at=now_str(),
                        ))
                # 翻页
                next_btn = page.ele("a:contains('下一页')", timeout=2)
                if next_btn:
                    next_btn.click()
                    time.sleep(2)
                else:
                    break
        except Exception as e:
            logger.error(f"[1688] 评论失败: {e}")
        return reviews

    # ── 热销排行 ──────────────────────────────────────

    def get_hot_ranking(self, category: str, top_n: int = 50) -> List[HotRanking]:
        return []  # 1688 排行页变化频繁，暂不实现

    # ── 翻页 ──────────────────────────────────────────

    def _try_next_page(self, page) -> bool:
        for sel in ["a.next", "a:contains('下一页')", "[class*='next']"]:
            try:
                btn = page.ele(sel, timeout=2)
                if btn:
                    btn.click()
                    time.sleep(3)
                    return True
            except Exception:
                continue

        # URL 翻页
        try:
            current = page.url
            m = re.search(r'[&?]begin=(\d+)', current)
            new_begin = (int(m.group(1)) + 40) if m else 40
            sep = "&" if "?" in current else "?"
            new_url = re.sub(r'[&?]begin=\d+', '', current) + f"{sep}begin={new_begin}"
            page.get(new_url)
            time.sleep(3)
            return True
        except Exception:
            pass
        return False

    # ── 调试 ──────────────────────────────────────────

    def _debug_screenshot(self, page, name: str):
        try:
            path = os.path.join(OUTPUT_DIR, f"{name}.png")
            page.screenshot(path)
            logger.info(f"截图: {path}")
        except Exception:
            pass
