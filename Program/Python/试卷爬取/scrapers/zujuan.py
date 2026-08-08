"""
组卷网爬虫 — zujuan.xkw.com
在线组卷平台，需要登录和 VIP 才能使用。

策略：
- 完全需要登录认证
- 提供搜索接口（需 Cookie）
- 实际组卷/下载需要 VIP
"""

from typing import Optional, Iterator
from urllib.parse import urljoin, quote

from core.base_scraper import (
    BaseScraper, PaperLink, ScraperType, AuthLevel
)
from scrapers.scraper_registry import register_scraper


@register_scraper
class ZujuanScraper(BaseScraper):
    """组卷网爬虫（受限功能）。"""

    site_name = "组卷网"
    base_url = "https://zujuan.xkw.com"
    scraper_type = ScraperType.DYNAMIC
    auth_level = AuthLevel.VIP

    # 搜索入口
    SEARCH_URL = "/search?q={keyword}&page={page}"
    PHYSICS_URL = "/physics/"

    def search_papers(
        self,
        grade: Optional[str] = None,
        paper_type: Optional[str] = None,
        keyword: Optional[str] = None,
        max_pages: int = 5,
    ) -> Iterator[PaperLink]:
        """
        搜索组卷网。

        组卷网的全部功能都需要登录。公开可访问的内容非常有限。
        """
        self.logger.warning(
            "组卷网需要登录和 VIP。"
            "请通过 --cookie 参数提供登录后的 Cookie。"
        )

        search_terms = ["高中物理"]
        if grade:
            search_terms.append(grade)
        if paper_type:
            search_terms.append(paper_type)
        if keyword:
            search_terms.append(keyword)

        query = quote(" ".join(search_terms))

        for page in range(1, max_pages + 1):
            url = urljoin(
                self.base_url,
                self.SEARCH_URL.format(keyword=query, page=page)
            )
            soup = self._get_soup(url)
            if soup:
                for link in self._parse_results(soup, grade or ""):
                    yield link

    def _parse_results(self, soup, grade: str) -> Iterator[PaperLink]:
        """解析搜索结果。"""
        selectors = [
            "div.search-list .item",
            "div.paper-list li",
            "div.question-item",
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
                    "source": "zujuan.xkw.com",
                    "warning": "组卷网需要 VIP 才能组卷和下载",
                },
            )

    def download_paper(self, link: PaperLink) -> Optional[str]:
        """组卷网全部需要 VIP。"""
        self.logger.warning(
            f"组卷网下载需要 VIP: {link.title}\n"
            f"  URL: {link.url}\n"
            f"  建议: 请在浏览器中登录组卷网后手动组卷下载"
        )
        return None
