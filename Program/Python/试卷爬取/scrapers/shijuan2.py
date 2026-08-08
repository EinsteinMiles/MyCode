"""
第二试卷网爬虫 — www.shijuan2.com
免费试卷下载，无需登录。结构与第一试卷网类似。

⚠️  2026-08: 域名已失效（DNS 无法解析），网站可能已关闭。
    保留代码以便将来网站恢复时使用。

结构: 列表页 → 详情页 → 直接下载链接
"""

from typing import Optional, Iterator
from urllib.parse import urljoin

from core.base_scraper import (
    BaseScraper, PaperLink, ScraperType, AuthLevel
)


# 站点已失效，暂时取消注册以避免干扰搜索
# @register_scraper  ← 网站恢复后重新启用
class Shijuan2Scraper(BaseScraper):
    """第二试卷网爬虫（站点已失效）。"""

    site_name = "第二试卷网（已失效）"
    base_url = "https://www.shijuan2.com"
    scraper_type = ScraperType.STATIC
    auth_level = AuthLevel.NONE

    # 搜索入口
    SEARCH_PATH = "/search/"
    SUBJECT_PATH = "/gaozhong/wuli/"

    # 列表页选择器
    LIST_SELECTORS = [
        "ul.list-box li",
        "div.paper-list .item",
        "div.list ul li",
        "div.listbox ul li",
        ".article-list li",
        ".news-list li",
        "div.content ul li",
        "div.paper-item",
    ]

    # 下载链接选择器
    DOWNLOAD_SELECTORS = [
        "a[href$='.pdf']",
        "a[href$='.doc']",
        "a[href$='.docx']",
        "a.down-link",
        "a.down_url",
        "a:contains('下载')",
        "a:contains('点击下载')",
        "a:contains('本地下载')",
        "a:contains('下载地址')",
        "div.download a",
        "div.down a",
    ]

    def search_papers(
        self,
        grade: Optional[str] = None,
        paper_type: Optional[str] = None,
        keyword: Optional[str] = None,
        max_pages: int = 10,
    ) -> Iterator[PaperLink]:
        """搜索试卷。"""
        # 方案1：按年级浏览
        if grade:
            path = self.SUBJECT_PATH + self._grade_to_path(grade)
            for link in self._scrape_list_pages(path, grade, paper_type,
                                                 keyword, max_pages):
                yield link

        # 方案2：搜索关键词
        elif keyword:
            search_urls = [
                f"{self.SEARCH_PATH}?q=高中物理+{keyword}",
                f"{self.SEARCH_PATH}?keyword=高中物理+{keyword}",
            ]
            for search_url in search_urls:
                full_url = urljoin(self.base_url, search_url)
                for link in self._scrape_search_results(
                    full_url, grade, paper_type, keyword, max_pages
                ):
                    yield link

        # 方案3：全量遍历
        else:
            for g in ["高一", "高二", "高三"]:
                path = self.SUBJECT_PATH + self._grade_to_path(g)
                for link in self._scrape_list_pages(path, g, paper_type,
                                                     keyword, max_pages):
                    yield link

    def _scrape_list_pages(self, path: str, grade: str,
                           paper_type: str, keyword: str,
                           max_pages: int) -> Iterator[PaperLink]:
        """遍历年级列表页。"""
        for page in range(1, max_pages + 1):
            if page == 1:
                url = urljoin(self.base_url, path)
            else:
                url = urljoin(self.base_url, f"{path}index_{page}.html")

            self.logger.debug(f"抓取列表: {url}")
            soup = self._get_soup(url)
            if not soup:
                break

            items = self._extract_list_items(soup)
            if not items:
                break

            found = False
            for item in items:
                link = self._parse_list_item(item, grade)
                if link and self._matches_filter(link, paper_type, keyword):
                    found = True
                    yield link

            if not found and page > 1:
                break

    def _scrape_search_results(self, url: str, grade: str,
                                paper_type: str, keyword: str,
                                max_pages: int) -> Iterator[PaperLink]:
        """处理搜索结果页。"""
        soup = self._get_soup(url)
        if not soup:
            return

        items = self._extract_list_items(soup)
        for item in items:
            link = self._parse_list_item(item, grade or "")
            if link and self._matches_filter(link, paper_type, keyword):
                yield link

    def _extract_list_items(self, soup):
        """提取列表条目。"""
        for selector in self.LIST_SELECTORS:
            items = soup.select(selector)
            if items:
                return items

        all_li = soup.find_all("li")
        return [li for li in all_li if li.find("a")]

    def _parse_list_item(self, item, grade: str) -> Optional[PaperLink]:
        """解析列表条目。"""
        a_tag = item.find("a")
        if not a_tag:
            return None

        href = a_tag.get("href", "").strip()
        if not href or href == "#":
            return None

        if any(skip in href.lower() for skip in
               ["javascript:", "mailto:", "login"]):
            return None

        title = a_tag.get_text(strip=True)
        if not title or len(title) < 3:
            return None

        if not self._is_physics_related(title):
            return None

        detail_url = urljoin(self.base_url, href)
        paper_type = self._infer_paper_type(title)
        grade_inferred = self._infer_grade(title)
        final_grade = grade_inferred or grade
        format_hint = self._infer_format(href)

        return PaperLink(
            url=detail_url,
            title=title,
            grade=final_grade,
            paper_type=paper_type,
            format_hint=format_hint,
        )

    def download_paper(self, link: PaperLink) -> Optional[str]:
        """下载试卷：详情页 → 下载链接。"""
        self.logger.info(f"下载: {link.title}")

        soup = self._get_soup(link.url)
        if not soup:
            return None

        download_url = None
        for selector in self.DOWNLOAD_SELECTORS:
            elem = soup.select_one(selector)
            if elem:
                href = elem.get("href", "").strip()
                if href and href != "#":
                    download_url = urljoin(self.base_url, href)
                    break

        if not download_url:
            iframe = soup.find("iframe")
            if iframe and iframe.get("src"):
                download_url = urljoin(self.base_url, iframe["src"])

        if not download_url:
            self.logger.warning(f"未找到下载链接: {link.url}")
            return None

        link.format_hint = link.format_hint or self._infer_format(download_url)
        if not link.format_hint:
            link.format_hint = "pdf"

        original_url = link.url
        link.url = download_url
        try:
            return self._simple_download(link)
        finally:
            link.url = original_url

    @staticmethod
    def _grade_to_path(grade: str) -> str:
        """年级 → URL 路径片段。"""
        mapping = {"高一": "gaoyi/", "高二": "gaoer/", "高三": "gaosan/"}
        return mapping.get(grade, "")

    @staticmethod
    def _is_physics_related(title: str) -> bool:
        """判断标题是否物理相关。"""
        exclude = ["化学", "生物", "数学", "英语", "语文", "历史", "地理", "政治"]
        for kw in exclude:
            if kw in title:
                return False
        return "物理" in title or "wuli" in title.lower()
