"""
21世纪教育网爬虫 — www.21cnjy.com
教育资源平台，需点数/VIP下载。

搜索/浏览公开，下载受限。
"""

from typing import Optional, Iterator
from urllib.parse import urljoin, quote

from core.base_scraper import (
    BaseScraper, PaperLink, ScraperType, AuthLevel
)
from scrapers.scraper_registry import register_scraper


@register_scraper
class C21cnjyScraper(BaseScraper):
    """21世纪教育网爬虫。"""

    site_name = "21世纪教育网"
    base_url = "https://www.21cnjy.com"
    scraper_type = ScraperType.STATIC
    auth_level = AuthLevel.VIP

    SEARCH_URL = "/search?keyword={keyword}&page={page}"
    PHYSICS_URL = "/gaozhong/wuli/"

    def search_papers(
        self,
        grade: Optional[str] = None,
        paper_type: Optional[str] = None,
        keyword: Optional[str] = None,
        max_pages: int = 5,
    ) -> Iterator[PaperLink]:
        """搜索试卷。"""
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
            soup = self._get_soup(url)
            if not soup:
                break

            items = self._extract_items(soup)
            if not items:
                break

            for item in items:
                link = self._parse_item(item, grade or "")
                if link and self._matches_filter(link, paper_type, keyword):
                    yield link

    def _extract_items(self, soup):
        selectors = [
            "div.search-result .item",
            "ul.resource-list li",
            "div.resource-item",
            "li.resource-item",
            "div.doc-item",
        ]
        for sel in selectors:
            items = soup.select(sel)
            if items:
                return items
        return soup.find_all(["li", "div"], recursive=True)

    def _parse_item(self, item, grade: str) -> Optional[PaperLink]:
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

        if "物理" not in title:
            return None

        detail_url = urljoin(self.base_url, href)

        return PaperLink(
            url=detail_url,
            title=title,
            grade=self._infer_grade(title) or grade,
            paper_type=self._infer_paper_type(title),
            format_hint="doc",
            metadata={
                "source": "21cnjy.com",
                "warning": "需要点数/VIP下载",
            },
        )

    def download_paper(self, link: PaperLink) -> Optional[str]:
        self.logger.warning(
            f"21世纪教育网需要点数: {link.title}\n"
            f"  URL: {link.url}\n"
            f"  建议: 使用点数下载或通过 --cookie 提供已登录账号"
        )
        return None
