"""
教习网爬虫 — www.51jiaoxi.com
使用内部 JSON API 搜索，无需登录即可搜索和浏览。

API 端点（已验证 2026-08）:
- 搜索: GET /api/search?keyword={}&page={}
- 详情: /doc-{id}.html
- 下载: 需要积分（point），但可提取完整元数据和预览图

特性:
- 搜索返回 JSON，含标题/格式/年级/知识点/预览图/积分等
- 11万+高中物理试卷
- 下载需要积分（通常10-50点）
"""

import json
from typing import Optional, Iterator
from urllib.parse import urljoin, quote

from core.base_scraper import (
    BaseScraper, PaperLink, ScraperType, AuthLevel
)
from scrapers.scraper_registry import register_scraper


@register_scraper
class JiaoxiScraper(BaseScraper):
    """教习网爬虫（API 驱动）。"""

    site_name = "教习网"
    base_url = "https://www.51jiaoxi.com"
    scraper_type = ScraperType.API
    auth_level = AuthLevel.LOGIN

    # API 端点
    SEARCH_API = "/api/search"

    def search_papers(
        self,
        grade: Optional[str] = None,
        paper_type: Optional[str] = None,
        keyword: Optional[str] = None,
        max_pages: int = 10,
    ) -> Iterator[PaperLink]:
        """通过 API 搜索试卷。"""
        search_terms = ["高中物理"]
        if grade:
            search_terms.append(grade)
        if paper_type:
            # 使用配置中的类型关键词
            type_kw = self.TYPE_KEYWORDS.get(paper_type, [paper_type])
            search_terms.append(type_kw[0])
        if keyword:
            search_terms.append(keyword)

        query = " ".join(search_terms)

        for page in range(1, max_pages + 1):
            url = f"{self.base_url}{self.SEARCH_API}?keyword={quote(query)}&page={page}"
            self.logger.debug(f"API 搜索: {url}")

            resp = self._get(url)
            if not resp:
                break

            try:
                data = resp.json()
            except json.JSONDecodeError:
                self.logger.warning(f"API 返回非 JSON，可能需要登录")
                break

            api_data = data.get("data", {})
            items = api_data.get("pager", {}).get("data", [])
            total = api_data.get("total", 0)

            if not items:
                break

            self.logger.info(
                f"  第{page}页: {len(items)}条 (共{total}条)"
            )

            for item in items:
                link = self._parse_api_item(item, grade or "")
                if link and self._matches_filter(link, paper_type, keyword):
                    yield link

            # 检查是否有下一页
            current = int(api_data.get("pager", {}).get("current_page", page))
            if current < page:
                break

    def _parse_api_item(self, item: dict, default_grade: str) -> Optional[PaperLink]:
        """解析 API 返回的单条数据。"""
        doc_id = item.get("id")
        title = item.get("title", "")
        if not title or not doc_id:
            return None

        # 过滤非物理
        subject = item.get("subject_name", "")
        if subject and subject != "物理":
            return None

        # 排除其他科目试卷（标题中含有其他科目）
        exclude_subjects = ["化学", "生物", "数学", "英语", "语文", "历史", "地理", "政治"]
        for s in exclude_subjects:
            if s in title and "物理" not in title:
                return None

        file_type = item.get("file_type", "doc")
        points = item.get("point", 0)
        web_url = item.get("web_url", f"/doc-{doc_id}.html")
        book_name = item.get("book_name", "")
        stage_name = item.get("stage_name", "")

        # 构建元数据
        metadata = {
            "doc_id": doc_id,
            "points": points,
            "downloads": item.get("download_num", 0),
            "updated_at": item.get("updated_at", ""),
            "book_name": book_name,
            "stage_name": stage_name,
            "previews": item.get("previews", []),
            "nickname": item.get("nickname", ""),
        }

        if points > 0:
            metadata["warning"] = f"需要{points}积分下载（可注册后上传资源赚取积分）"

        # 推断年级
        grade = self._infer_grade(title)
        if not grade and book_name:
            grade = self._infer_grade(book_name)
        if not grade:
            grade = default_grade

        # 推断试卷类型
        paper_type = self._infer_paper_type(title)
        if not paper_type and book_name:
            paper_type = self._infer_paper_type(book_name)

        return PaperLink(
            url=urljoin(self.base_url, web_url),
            title=title,
            grade=grade,
            paper_type=paper_type or "其他",
            format_hint=file_type,
            metadata=metadata,
        )

    def download_paper(self, link: PaperLink) -> Optional[str]:
        """尝试下载试卷。教习网需要积分，通常需要登录。"""
        points = link.metadata.get("points", 0)
        if points > 0:
            self.logger.warning(
                f"教习网下载需要{points}积分: {link.title}\n"
                f"  URL: {link.url}\n"
                f"  建议: 注册教习网账号，上传资源赚取积分后下载\n"
                f"  或通过 --cookie 参数提供已登录账号的 Cookie"
            )
            return None

        # 如果没有积分要求，尝试直接下载
        self.logger.info(f"尝试下载: {link.title}")
        soup = self._get_soup(link.url)
        if soup:
            # 查找下载按钮
            for a in soup.find_all("a"):
                href = a.get("href", "")
                text = a.get_text()
                if ("下载" in text and "/org/attachments/" in href):
                    download_url = urljoin(self.base_url, href)
                    original_url = link.url
                    link.url = download_url
                    try:
                        return self._simple_download(link)
                    finally:
                        link.url = original_url

        return None
