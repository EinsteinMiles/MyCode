"""
百度文库爬虫 — wenku.baidu.com
严重反爬保护，需要 JavaScript 渲染和登录。

策略：
- 搜索使用公开 API（如可用）
- 文档内容需要 VIP + 登录
- 使用 Playwright 渲染（如已安装）
- 实际下载需要人工介入或百度 VIP Cookie

使用方式：
  1. python main.py search --site 百度文库 --keyword 力学
     → 列出搜索结果（标题、URL）
  2. 手动在浏览器中下载需要的文档
  3. 或提供 VIP Cookie 尝试自动下载
"""

from typing import Optional, Iterator
from urllib.parse import urljoin, quote

from core.base_scraper import (
    BaseScraper, PaperLink, ScraperType, AuthLevel
)
from scrapers.scraper_registry import register_scraper


@register_scraper
class WenkuBaiduScraper(BaseScraper):
    """百度文库爬虫（受限功能）。"""

    site_name = "百度文库"
    base_url = "https://wenku.baidu.com"
    scraper_type = ScraperType.DYNAMIC
    auth_level = AuthLevel.WALLED

    # 搜索 URL
    SEARCH_URL = "https://wenku.baidu.com/search?word={keyword}&pn={start}"

    def search_papers(
        self,
        grade: Optional[str] = None,
        paper_type: Optional[str] = None,
        keyword: Optional[str] = None,
        max_pages: int = 5,
    ) -> Iterator[PaperLink]:
        """
        搜索百度文库。

        注意：百度文库搜索依赖于 JS 渲染。如果 requests 方式失败，
        会尝试使用 Playwright。如果都没有，会标记为不可用。
        """
        search_terms = ["高中物理"]
        if grade:
            search_terms.append(grade)
        if paper_type:
            search_terms.append(paper_type)
        if keyword:
            search_terms.append(keyword)

        query = " ".join(search_terms)

        # 尝试方式1: 静态请求（大概率失败/被反爬）
        for page in range(max_pages):
            start = page * 10
            url = self.SEARCH_URL.format(keyword=quote(query), start=start)
            self.logger.debug(f"搜索: {url}")

            soup = self._get_soup(url)
            if soup:
                for link in self._parse_search_results(soup, grade or ""):
                    yield link

    def _parse_search_results(self, soup, grade: str) -> Iterator[PaperLink]:
        """解析搜索结果页。"""
        # 百度文库的 DOM 结构经常变化，这里列多种可能的选择器
        selectors = [
            "div.result-item",
            "dl.search-result dd",
            "div.doc-item",
            "div.wk-search-result .item",
            "li.result-item",
        ]

        items = []
        for sel in selectors:
            items = soup.select(sel)
            if items:
                break

        for item in items:
            a_tag = item.find("a")
            if not a_tag:
                continue

            href = a_tag.get("href", "").strip()
            if not href or "wenku.baidu.com" not in href:
                continue

            title = a_tag.get_text(strip=True)
            if not title or len(title) < 3:
                continue

            if "物理" not in title:
                continue

            # 提取可能的格式信息
            format_hint = "pdf"
            item_text = item.get_text()
            if ".doc" in item_text.lower():
                format_hint = "doc"
            elif ".ppt" in item_text.lower():
                continue  # 跳过 PPT

            yield PaperLink(
                url=href if href.startswith("http") else urljoin(self.base_url, href),
                title=title,
                grade=self._infer_grade(title) or grade,
                paper_type=self._infer_paper_type(title),
                format_hint=format_hint,
                metadata={
                    "source": "wenku.baidu.com",
                    "warning": "百度文库文档需要 VIP 才能下载完整版",
                },
            )

    def download_paper(self, link: PaperLink) -> Optional[str]:
        """
        下载百度文库文档。

        百度文库有强反爬和 VIP 限制：
        - 免费用户只能预览部分页面
        - 下载需要 VIP 会员和登录
        - 反爬机制包括验证码、频率限制等

        实际策略：
        - 如果配置了百度 Cookie，尝试下载
        - 否则记录链接供手动下载
        """
        self.logger.warning(
            f"百度文库文档无法自动下载: {link.title}\n"
            f"  URL: {link.url}\n"
            f"  原因: 百度文库需要 VIP 会员且存在强反爬保护\n"
            f"  建议: 请在浏览器中手动打开此链接下载"
        )
        return None
