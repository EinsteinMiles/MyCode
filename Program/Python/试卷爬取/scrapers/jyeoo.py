"""
菁优网爬虫 — www.jyeoo.com
大型题库网站，所有下载需要 VIP，搜索也需要登录。

策略：
- 如果提供登录 Cookie，尝试搜索 API
- 否则只能标记为不可用
- 搜索 API 通常是 JSON 格式内部接口
"""

from typing import Optional, Iterator
from urllib.parse import urljoin, quote

from core.base_scraper import (
    BaseScraper, PaperLink, ScraperType, AuthLevel
)
from scrapers.scraper_registry import register_scraper


@register_scraper
class JyeooScraper(BaseScraper):
    """菁优网爬虫（受限功能）。"""

    site_name = "菁优网"
    base_url = "https://www.jyeoo.com"
    scraper_type = ScraperType.API
    auth_level = AuthLevel.VIP

    # 物理频道
    PHYSICS_URL = "/physics/"
    # 高中物理
    HIGH_SCHOOL_URL = "/physics/high/"

    # 可能的搜索 API 端点
    SEARCH_API = "/api/search"

    def search_papers(
        self,
        grade: Optional[str] = None,
        paper_type: Optional[str] = None,
        keyword: Optional[str] = None,
        max_pages: int = 5,
    ) -> Iterator[PaperLink]:
        """
        搜索菁优网。

        菁优网的搜索功能需要登录认证。
        如果提供了有效的 Cookie，可以尝试 API 调用。
        否则返回空结果。
        """
        self.logger.warning(
            "菁优网需要登录和 VIP 才能搜索和下载。"
            "请通过 --cookie 参数提供登录后的 Cookie 字符串。"
        )

        # 尝试公开页面（如果存在）
        search_terms = ["高中物理"]
        if grade:
            search_terms.append(grade)
        if paper_type:
            search_terms.append(paper_type)
        if keyword:
            search_terms.append(keyword)

        query = quote(" ".join(search_terms))

        # 尝试搜索页面
        for page in range(1, max_pages + 1):
            # 多种可能的 URL 模式
            urls_to_try = [
                f"{self.base_url}/search?q={query}&page={page}",
                f"{self.base_url}/physics/search/?q={query}&p={page}",
            ]
            for url in urls_to_try:
                soup = self._get_soup(url)
                if soup:
                    for link in self._parse_search_results(soup, grade or ""):
                        yield link
                    break

    def _parse_search_results(self, soup, grade: str) -> Iterator[PaperLink]:
        """解析搜索结果。"""
        # 菁优网搜索结果的 DOM 结构
        selectors = [
            "div.search-result .item",
            "li.question-item",
            "div.ques-item",
            "div.paper-item",
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
            if not href or any(s in href.lower() for s in ["javascript:", "#"]):
                continue

            title = a_tag.get_text(strip=True)
            if not title or len(title) < 3:
                continue

            if "物理" not in title:
                continue

            yield PaperLink(
                url=urljoin(self.base_url, href),
                title=title,
                grade=self._infer_grade(title) or grade,
                paper_type=self._infer_paper_type(title),
                format_hint="pdf",
                metadata={
                    "source": "jyeoo.com",
                    "warning": "菁优网需要 VIP 才能下载完整试卷",
                },
            )

    def download_paper(self, link: PaperLink) -> Optional[str]:
        """菁优网下载全部需要 VIP。"""
        self.logger.warning(
            f"菁优网下载需要 VIP: {link.title}\n"
            f"  URL: {link.url}\n"
            f"  建议: 请在浏览器中登录菁优网 VIP 账号后手动下载"
        )
        return None
