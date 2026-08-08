"""
七彩学科网爬虫 — www.7cxk.com
部分免费，下载需要积分。站点有反爬 JS 检测。

策略:
- 使用分类浏览 + 搜索
- 需要绕过 JS 反爬（Cookie 注入）
- 下载需要积分

已验证 URL 结构 (2026-08):
- 分类: /c-00011-{page}-2244780-0-32950-0-0-9-0-0.html (高中物理)
- 搜索: /search?keyword={}
- 详情: /{id}.html
"""

import re
from typing import Optional, Iterator
from urllib.parse import urljoin, quote

from core.base_scraper import (
    BaseScraper, PaperLink, ScraperType, AuthLevel
)
from scrapers.scraper_registry import register_scraper


@register_scraper
class QcxkScraper(BaseScraper):
    """七彩学科网爬虫。"""

    site_name = "七彩学科网"
    base_url = "https://www.7cxk.com"
    scraper_type = ScraperType.STATIC
    auth_level = AuthLevel.LOGIN

    # 高中物理分类页（参数说明：c-00011 = 高中物理）
    CATEGORY_URL = "/c-00011-{page}-2244780-0-32950-0-0-9-0-0.html"
    SEARCH_URL = "/search?keyword={keyword}&page={page}"

    def search_papers(
        self,
        grade: Optional[str] = None,
        paper_type: Optional[str] = None,
        keyword: Optional[str] = None,
        max_pages: int = 10,
    ) -> Iterator[PaperLink]:
        """搜索试卷。"""
        # 构建搜索关键词
        search_terms = ["高中物理"]
        if grade:
            search_terms.append(grade)
        if paper_type:
            type_kw = self.TYPE_KEYWORDS.get(paper_type, [paper_type])
            search_terms.append(type_kw[0])
        if keyword:
            search_terms.append(keyword)

        query = " ".join(search_terms)

        for page in range(1, max_pages + 1):
            url = urljoin(
                self.base_url,
                self.SEARCH_URL.format(keyword=quote(query), page=page)
            )
            self.logger.debug(f"搜索: {url}")

            soup = self._get_soup(url)
            if not soup:
                self.logger.debug("搜索无响应")
                break

            # 检查是否被反爬拦截
            if self._is_antibot(soup):
                self.logger.warning(
                    "被反爬机制拦截！请使用 --cookie 参数提供浏览器 Cookie\n"
                    "  获取方法: 浏览器登录 7cxk.com 后，在 DevTools → "
                    "Application → Cookies 中复制"
                )
                break

            items = self._extract_items(soup)
            if not items:
                break

            for item in items:
                link = self._parse_item(item, grade or "")
                if link and self._matches_filter(link, paper_type, keyword):
                    yield link

    def _extract_items(self, soup):
        """提取搜索结果条目。"""
        # 多种可能的选择器
        selectors = [
            "div.resource-item",
            "div.doc-item",
            "li.resource-list-item",
            "div.search-result .item",
            "ul.list li",
            "div.list-item",
        ]
        for sel in selectors:
            items = soup.select(sel)
            if items:
                return items
        # 兜底：找所有包含链接的块级元素
        return soup.select("a[href$='.html']")

    def _parse_item(self, item, grade: str) -> Optional[PaperLink]:
        """解析单个条目。"""
        # 如果 item 本身就是 a 标签
        if item.name == "a":
            a_tag = item
        else:
            a_tag = item.find("a")

        if not a_tag:
            return None

        href = a_tag.get("href", "").strip()
        if not href or any(s in href.lower() for s in ["javascript:", "mailto:", "#"]):
            return None

        title = a_tag.get_text(strip=True) or a_tag.get("title", "")
        if not title or len(title) < 3:
            return None

        # 确保物理相关
        if "物理" not in title:
            exclude = ["化学", "生物", "数学", "英语", "语文", "历史", "地理", "政治"]
            if any(kw in title for kw in exclude):
                return None

        detail_url = urljoin(self.base_url, href)
        format_hint = self._infer_format(href)

        # 尝试提取文件大小和格式
        item_text = item.get_text() if item.name != "a" else ""
        if not format_hint:
            for ext in ["doc", "docx", "pdf", "rar", "zip"]:
                if f".{ext}" in item_text.lower():
                    format_hint = ext
                    break

        return PaperLink(
            url=detail_url,
            title=title,
            grade=self._infer_grade(title) or grade,
            paper_type=self._infer_paper_type(title),
            format_hint=format_hint or "doc",
            metadata={"source": "7cxk.com"},
        )

    def download_paper(self, link: PaperLink) -> Optional[str]:
        """下载试卷。七彩学科网需要积分。"""
        self.logger.info(f"尝试下载: {link.title}")

        soup = self._get_soup(link.url)
        if not soup:
            return None

        if self._is_antibot(soup):
            self.logger.warning("被反爬拦截，请提供浏览器 Cookie")
            return None

        # 检查是否需要积分
        if self._needs_points(soup):
            self.logger.warning(
                f"需要积分下载: {link.title}\n"
                f"  URL: {link.url}\n"
                f"  建议: 注册并上传资源赚取积分，或提供登录 Cookie"
            )
            return None

        # 查找下载链接
        for a in soup.find_all("a"):
            text = a.get_text().strip()
            href = a.get("href", "")
            if any(kw in text for kw in ["下载", "download"]) and href.startswith("/"):
                download_url = urljoin(self.base_url, href)
                original_url = link.url
                link.url = download_url
                link.format_hint = link.format_hint or self._infer_format(href)
                try:
                    return self._simple_download(link)
                finally:
                    link.url = original_url

        self.logger.warning(f"未找到下载链接: {link.url}")
        return None

    @staticmethod
    def _is_antibot(soup) -> bool:
        """检查是否被反爬拦截。"""
        html = str(soup)
        # 7cxk 的反爬 JS 特征
        if "anticc_js_concat" in html:
            return True
        if "window.location" in html and "search?keyword" in html:
            return True
        return False

    @staticmethod
    def _needs_points(soup) -> bool:
        """检查是否需要积分/登录。"""
        text = soup.get_text()
        indicators = ["积分", "点数", "充值", "VIP", "登录后下载", "立即登录"]
        return any(ind in text for ind in indicators)
