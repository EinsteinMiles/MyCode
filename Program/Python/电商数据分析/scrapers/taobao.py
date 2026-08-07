"""
淘宝爬虫（重写版）
反爬极强（7层检测），采用多重策略：
1. 先检测页面状态（登录墙/验证码/正常搜索结果）
2. 使用 XPath + 文本内容匹配（淘宝类名随机化，CSS 选择器无效）
3. 通过 <a href="item.taobao.com"> 定位商品卡片，反向提取价格/销量/店铺
4. 可选 API 拦截方式（监听 XHR 响应获取结构化数据）
"""

from __future__ import annotations

import time
import re
import json
import os
import random
from typing import TYPE_CHECKING, List, Optional, Dict, Any
from urllib.parse import quote, urljoin

if TYPE_CHECKING:
    from DrissionPage import ChromiumPage

from config import (
    TAOBAO_SEARCH_URL, TAOBAO_ITEM_URL, MAX_REVIEW_PAGES,
    OUTPUT_DIR, logger,
)
from scrapers.base import BaseScraper
from core.models import Product, Review, HotRanking
from core.utils import (
    random_delay, page_delay, parse_price, parse_sales,
    clean_text, now_str,
)


class TaobaoScraper(BaseScraper):
    """淘宝平台爬虫（重写版）"""

    platform = "taobao"

    # 淘宝搜索页的各种可能 URL
    SEARCH_URLS = [
        "https://s.taobao.com/search?q={keyword}",
        "https://www.taobao.com/markets/search?q={keyword}",
        "https://s.taobao.com/search?q={keyword}&s=0",  # s=0 表示第一页
    ]

    # ── 搜索商品 ──────────────────────────────────────

    def search_products(
        self, keyword: str, max_pages: int = 2, category: str = ""
    ) -> List[Product]:
        """
        搜索淘宝商品 — 多策略尝试

        策略优先级:
          1. 浏览器访问搜索页 → XPath+文本解析
          2. 如果触发验证/登录 → 给出明确提示
        """
        max_pages = min(max_pages, 3)
        all_products: List[Product] = []
        page = self._get_page()

        search_url = f"https://s.taobao.com/search?q={quote(keyword)}"
        logger.info(f"[淘宝] 搜索: {keyword} (最多{max_pages}页)")
        logger.info("[淘宝] 策略: 浏览器+XPath文本匹配")

        # 加载 Cookie
        self.browser_mgr.load_cookies("taobao")

        try:
            # ── 访问搜索页 ──
            page.get(search_url)
            time.sleep(5)  # 淘宝 JS 渲染非常慢

            # ── 诊断页面状态 ──
            page_state = self._diagnose_page(page)
            logger.info(f"[淘宝] 页面诊断: {page_state}")

            if page_state == "login_wall":
                logger.error(
                    "[淘宝] ⚠️ 遇到登录墙！淘宝搜索页现在需要登录才能访问。\n"
                    "   建议方案:\n"
                    "   1. 在浏览器中手动登录淘宝后导出 Cookie 放到 cookies/taobao.json\n"
                    "   2. 改用 1688 平台抓取（无需登录，在菜单[1]选 1688）\n"
                    "   3. 使用淘宝移动端 API（见下方说明）"
                )
                # 尝试保存截图帮助诊断
                self._save_debug_screenshot(page, "taobao_login_wall")
                return all_products

            elif page_state == "captcha":
                logger.error(
                    "[淘宝] ⚠️ 触发滑块验证！请在浏览器窗口中手动完成验证，"
                    "然后按回车继续..."
                )
                input("按回车继续...")
                # 验证后重试当前页
                products = self._parse_page_by_links(page, keyword, category)
                all_products.extend(products)

            elif page_state == "search_results":
                # 正常搜索，开始解析
                for pg in range(1, max_pages + 1):
                    logger.info(f"[淘宝] 解析第 {pg}/{max_pages} 页...")
                    self._rate_limit()

                    # 慢速滚动触发懒加载
                    self._human_like_scroll(page, times=3)

                    # 核心：通过商品链接反向定位
                    products = self._parse_page_by_links(page, keyword, category)
                    all_products.extend(products)
                    logger.info(f"[淘宝] 第 {pg} 页提取 {len(products)} 个商品")

                    if pg < max_pages:
                        if not self._go_next_page(page):
                            logger.info("[淘宝] 无下一页")
                            break
                        time.sleep(random.uniform(4, 8))
            else:
                # unknown 状态 — 还是尝试解析
                logger.warning(f"[淘宝] 未知页面状态: {page_state}，尝试解析...")
                products = self._parse_page_by_links(page, keyword, category)
                all_products.extend(products)

        except Exception as e:
            logger.error(f"[淘宝] 搜索异常: {e}")
            import traceback
            traceback.print_exc()

        logger.info(f"[淘宝] 搜索完成: 共 {len(all_products)} 个商品")
        return all_products

    # ── 页面诊断 ──────────────────────────────────────

    def _diagnose_page(self, page) -> str:
        """
        诊断淘宝页面当前状态
        返回: 'login_wall' | 'captcha' | 'search_results' | 'empty' | 'unknown'
        """
        try:
            html = page.html[:10000]  # 前 10KB
            current_url = page.url

            # 1. 检查是否跳转到登录页
            if any(kw in current_url for kw in ["login.taobao.com", "login.tmall.com"]):
                return "login_wall"

            # 登录相关的文本提示
            login_indicators = [
                "请登录", "登录淘宝", "扫码登录", "密码登录",
                "login", "淘宝登录", "taobao login",
            ]
            for indicator in login_indicators:
                if indicator in html:
                    return "login_wall"

            # 2. 检查验证码
            captcha_indicators = [
                "滑块验证", "请按住滑块", "拖动滑块", "验证码",
                "安全验证", "请完成安全验证", "_nc", "_tb_token",
            ]
            captcha_count = sum(1 for c in captcha_indicators if c in html)
            if captcha_count >= 2:
                return "captcha"

            # 3. 检查是否有搜索结果（商品链接）
            item_links = re.findall(r'href="[^"]*item\.(?:taobao|tmall)\.com[^"]*"', html)
            if item_links:
                return "search_results"

            # 4. 检查是否是空结果
            if "没有找到" in html or "抱歉" in html:
                return "empty"

            # 5. 检查页面标题
            title = page.title.lower() if hasattr(page, 'title') else ""
            if "login" in title:
                return "login_wall"
            if "搜索" in html or "search" in current_url.lower():
                return "search_results"  # 在搜索页但可能 JS 未渲染

            return "unknown"

        except Exception as e:
            logger.warning(f"页面诊断失败: {e}")
            return "unknown"

    # ── 通过商品链接反向解析（核心方法）──────────────────

    def _parse_page_by_links(
        self, page, keyword: str, category: str
    ) -> List[Product]:
        """
        通过提取页面中所有 item.taobao.com 链接来定位商品

        淘宝的类名是随机生成的，但商品链接格式不变：
          //item.taobao.com/item.htm?id=xxxxxxxx
          //detail.tmall.com/item.htm?id=xxxxxxxx

        策略：找到这些 <a> 标签 → 向上找容器 → 提取价格/销量
        """
        products: List[Product] = []
        seen_ids: set = set()

        try:
            # 提取所有淘宝/TMALL 商品链接
            item_links_js = page.run_js("""
                var links = document.querySelectorAll('a[href*="item.taobao.com"], a[href*="detail.tmall.com"]');
                var result = [];
                links.forEach(function(a) {
                    var href = a.getAttribute('href') || '';
                    var text = (a.textContent || '').trim();
                    var rect = a.getBoundingClientRect();
                    // 获取父元素及其兄弟节点的文本
                    var parent = a.closest('div,li') || a.parentElement;
                    var parentText = parent ? (parent.textContent || '').trim() : '';
                    if (href && text && text.length > 5) {
                        result.push({
                            href: href,
                            text: text.substring(0, 200),
                            parentText: parentText.substring(0, 600),
                            y: rect.y
                        });
                    }
                });
                return result;
            """)

            if not item_links_js:
                logger.warning("[淘宝] 未找到商品链接，页面可能未加载完成或被拦截")
                # 保底：尝试从 HTML 中直接匹配
                html = page.html
                raw_links = re.findall(
                    r'(//item\.(?:taobao|tmall)\.com/item\.htm\?[^"\'\s]+)',
                    html
                )
                if raw_links:
                    logger.info(f"[淘宝] HTML 直接匹配到 {len(raw_links)} 个链接（可能未渲染）")
                return products

            logger.debug(f"[淘宝] JS 提取到 {len(item_links_js)} 个商品链接")

            for item_data in item_links_js:
                href = item_data.get("href", "")
                text = item_data.get("text", "")
                parent_text = item_data.get("parentText", "")

                # 提取商品 ID
                item_id = ""
                m = re.search(r'[?&]id=(\d+)', href)
                if m:
                    item_id = m.group(1)

                if item_id in seen_ids:
                    continue
                seen_ids.add(item_id)

                # 构建完整 URL
                url = href
                if url.startswith("//"):
                    url = "https:" + url
                elif not url.startswith("http"):
                    url = "https:" + url

                # 从父元素文本中提取价格（¥符号 + 数字）
                price = 0.0
                price_text = ""
                combined_text = parent_text + " " + text

                # 价格模式：¥19.90 或 ¥ 19.90 或 19.90
                price_matches = re.findall(
                    r'(?:¥|￥|RMB\s*)\s*(\d+(?:,\d{3})*(?:\.\d{1,2})?)'
                    r'|(\d+(?:\.\d{1,2})?)\s*(?:元|¥)',
                    combined_text
                )
                if price_matches:
                    for pm in price_matches:
                        val = pm[0] or pm[1]
                        if val:
                            try:
                                price = float(val.replace(",", ""))
                                break
                            except ValueError:
                                continue
                    # 找原始价格文本
                    price_text_match = re.search(
                        r'(?:¥|￥)\s*\d+(?:\.\d{1,2})?', combined_text
                    )
                    if price_text_match:
                        price_text = price_text_match.group(0)

                # 从父元素文本中提取销量
                sales_text = ""
                sales_count = 0
                sales_patterns = [
                    r'(\d+[+＋])人付款', r'(\d+[+＋])人收货',
                    r'已售(\d+[+＋]?)', r'月销(?:量)?\s*(\d+[+＋万]?)',
                    r'(\d+(?:\.\d+)?万?[+＋]?)人付款',
                    r'(\d+)笔',
                ]
                for sp in sales_patterns:
                    sm = re.search(sp, combined_text)
                    if sm:
                        sales_text = sm.group(0)
                        sales_count = parse_sales(sales_text)
                        break

                # 从父元素文本中提取店铺名
                shop_name = ""
                shop_patterns = [
                    r'([一-鿿]{2,20}(?:旗舰店|专卖店|专营店|店铺))',
                ]
                for sp in shop_patterns:
                    sm = re.search(sp, combined_text)
                    if sm:
                        shop_name = sm.group(1)
                        break

                # 从父元素文本中提取所在地
                location = ""
                loc_match = re.search(
                    r'(?:发货地|产地|所在地)[：:]\s*([一-鿿]{2,6})',
                    combined_text
                )
                if loc_match:
                    location = loc_match.group(1)

                # 标题用链接文本
                title = clean_text(text)

                if not title or len(title) < 3:
                    continue

                products.append(self._new_product(
                    product_id=item_id,
                    title=title,
                    price=price,
                    price_range=price_text,
                    sales_count=sales_count,
                    sales_text=sales_text,
                    shop_name=shop_name,
                    location=location,
                    category=category or keyword,
                    url=url,
                ))

                if len(products) >= 50:  # 每页最多 50 个
                    break

        except Exception as e:
            logger.error(f"[淘宝] 链接解析失败: {e}")

        return products

    # ── 商品详情（通过移动端 API 尝试）─────────────────

    def get_product_detail(self, url: str) -> Optional[Product]:
        """
        获取淘宝商品详情
        优先尝试移动端 API，不行再用浏览器
        """
        page = self._get_page()
        self._rate_limit()

        # 提取商品 ID
        item_id = ""
        m = re.search(r'[?&]id=(\d+)', url)
        if m:
            item_id = m.group(1)

        # 方案 A：移动端 H5 页面（相对好抓）
        if item_id:
            h5_url = f"https://h5.m.taobao.com/awp/core/detail.htm?id={item_id}"
            try:
                page.get(h5_url)
                time.sleep(3)

                # 用 JS 从页面提取数据
                data = page.run_js("""
                    try {
                        var title = (document.querySelector('h1') || document.querySelector('[class*="title"]') || {}).textContent || '';
                        var priceEl = document.querySelector('[class*="price"]') || document.querySelector('.price');
                        var price = priceEl ? priceEl.textContent.replace(/[^0-9.]/g, '') : '';
                        var salesEl = document.querySelector('[class*="sale"]') || document.querySelector('[class*="sell"]');
                        var sales = salesEl ? salesEl.textContent : '';
                        return {title: title.trim(), price: price, sales: sales};
                    } catch(e) { return {}; }
                """)

                if data and data.get("title"):
                    return self._new_product(
                        product_id=item_id,
                        title=clean_text(data.get("title", "")),
                        price=parse_price(data.get("price", "0")),
                        price_range=data.get("price", ""),
                        sales_text=data.get("sales", ""),
                        sales_count=parse_sales(data.get("sales", "")),
                        url=url,
                    )
            except Exception as e:
                logger.debug(f"H5 详情获取失败: {e}")

        # 方案 B：PC 页面
        try:
            page.get(url)
            time.sleep(4)
            self._human_like_scroll(page)

            data = page.run_js("""
                try {
                    var title = document.title || (document.querySelector('h1') || {}).textContent || '';
                    var priceEl = document.querySelector('#J_StrPrice') || document.querySelector('.tb-rmb-num') || document.querySelector('[class*="price"]');
                    var price = priceEl ? priceEl.textContent : '';
                    var salesEl = document.querySelector('.tb-sell-counter') || document.querySelector('[class*="sell"]');
                    var sales = salesEl ? salesEl.textContent : '';
                    return {title: title.trim(), price: price, sales: sales};
                } catch(e) { return {}; }
            """)

            if data and data.get("title"):
                return self._new_product(
                    product_id=item_id,
                    title=clean_text(data.get("title", "")),
                    price=parse_price(data.get("price", "0")),
                    price_range=data.get("price", ""),
                    sales_text=data.get("sales", ""),
                    sales_count=parse_sales(data.get("sales", "")),
                    url=url,
                )
        except Exception as e:
            logger.error(f"[淘宝] PC 详情获取失败: {e}")

        return None

    # ── 评论抓取（尝试移动端评价 API）───────────────────

    def get_reviews(
        self, product_url: str, max_pages: int = MAX_REVIEW_PAGES
    ) -> List[Review]:
        """
        淘宝评价抓取
        尝试淘宝官方评价 API（比页面解析可靠）
        """
        reviews: List[Review] = []

        # 提取商品 ID
        item_id = ""
        m = re.search(r'[?&]id=(\d+)', url=product_url)
        if m:
            item_id = m.group(1)

        if not item_id:
            logger.warning("[淘宝] 无法提取商品 ID")
            return reviews

        page = self._get_page()

        # 尝试通过移动端评价页面
        review_url = (
            f"https://h5.m.taobao.com/awp/core/detail.htm?id={item_id}"
            "#!fulldesc=true"
        )
        try:
            page.get(review_url)
            time.sleep(3)

            for pg in range(1, min(max_pages, 5) + 1):
                # 用 JS 提取当前可见的评论
                items = page.run_js("""
                    var items = document.querySelectorAll('[class*="comment"], [class*="review"], [class*="rate"]');
                    var result = [];
                    items.forEach(function(el) {
                        var text = (el.textContent || '').trim();
                        if (text.length > 20 && text.length < 2000) {
                            result.push(text);
                        }
                    });
                    return result;
                """)

                if items:
                    for text in items:
                        reviews.append(Review(
                            product_db_id=0,
                            content=clean_text(text),
                            rating=5,
                            review_date=now_str(),
                            scraped_at=now_str(),
                        ))
                    logger.info(f"[淘宝] 第{pg}页评论: {len(items)} 条")

                if len(reviews) >= 50:
                    break
                page_delay()

        except Exception as e:
            logger.error(f"[淘宝] 评论抓取失败: {e}")

        return reviews

    # ── 热销排行 ──────────────────────────────────────

    def get_hot_ranking(self, category: str, top_n: int = 50) -> List[HotRanking]:
        """淘宝热销排行需要登录"""
        logger.warning("[淘宝] 热销排行需要登录淘宝账号，当前不支持")
        return []

    # ── 淘宝专用：行为模拟 ─────────────────────────────

    def _human_like_scroll(self, page, times: int = 4) -> None:
        """模拟人类浏览：慢速、不均匀滚动 + 随机停顿"""
        for i in range(times):
            try:
                # 随机滚动距离
                scroll_by = random.randint(150, 500)
                page.run_js(f"window.scrollBy(0, {scroll_by})")
                # 随机停顿
                time.sleep(random.uniform(0.6, 1.8))

                # 偶尔在"有趣"的位置停一下
                if random.random() < 0.3:
                    time.sleep(random.uniform(0.5, 1.2))
            except Exception:
                break
        try:
            page.scroll.to_top()
            time.sleep(0.3)
        except Exception:
            pass

    def _go_next_page(self, page) -> bool:
        """淘宝翻页 — 多种方式尝试"""
        # 方式1：点击"下一页"
        next_selectors = [
            "a:contains('下一页')",
            "a.next",
            ".pagination-next",
            "[class*='next']",
            "a[rel='next']",
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

        # 方式2：URL 翻页（淘宝用 s=44, s=88 翻页）
        try:
            current_url = page.url
            # 匹配 &s=数字 或 &b=数字
            s_match = re.search(r'[&?]s=(\d+)', current_url)
            if s_match:
                current_s = int(s_match.group(1))
                new_url = re.sub(r'([&?])s=\d+', f'\\1s={current_s + 44}', current_url)
            else:
                # 首次翻页
                sep = "&" if "?" in current_url else "?"
                new_url = current_url + f"{sep}s=44"

            page.get(new_url)
            time.sleep(3)
            return True
        except Exception:
            pass

        return False

    # ── 调试辅助 ──────────────────────────────────────

    def _save_debug_screenshot(self, page, name: str) -> str:
        """保存调试截图到 output/ 目录"""
        try:
            filepath = os.path.join(OUTPUT_DIR, f"{name}_{now_str().replace(' ', '_').replace(':', '-')}.png")
            page.screenshot(filepath)
            logger.info(f"调试截图已保存: {filepath}")
            return filepath
        except Exception as e:
            logger.warning(f"截图失败: {e}")
            return ""
