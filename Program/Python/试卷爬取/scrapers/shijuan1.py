"""
第一试卷网爬虫 — www.shijuan1.com
免费试卷下载，无需登录。纯静态 HTML 解析（GB2312编码）。

实际站点结构（已验证 2026-08）：
- 列表页: /a/sjwlg1/ (高一), /a/sjwlg2/ (高二), /a/sjwlgk/ (高考)
- 分页: list_701_N.html (701是列表ID, N是页码)
- 详情页: /a/sjwlg1/299220.html
- 下载: <ul class="downurllist"><li><a href="/uploads/.../xxx.rar">本地下载</a>
- 文件格式: .rar (内含 .doc/.pdf)
"""

import re
from typing import Optional, Iterator
from urllib.parse import urljoin

from bs4 import BeautifulSoup

from core.base_scraper import (
    BaseScraper, PaperLink, ScraperType, AuthLevel
)
from scrapers.scraper_registry import register_scraper


@register_scraper
class Shijuan1Scraper(BaseScraper):
    """第一试卷网爬虫。"""

    site_name = "第一试卷网"
    base_url = "https://www.shijuan1.com"
    scraper_type = ScraperType.STATIC
    auth_level = AuthLevel.NONE

    # 年级 → URL 路径映射（已验证）
    GRADE_PATH = {
        "高一": "/a/sjwlg1/",
        "高二": "/a/sjwlg2/",
        "高三": "/a/sjwlgk/",   # 高考栏目 = 高三
    }

    # 通用物理试卷入口
    ALL_PATH = "/a/sjwl/"

    # 列表页资源行选择器
    TABLE_ROW_SELECTORS = [
        "table tr",
        ".listbox table tr",
        "div.listbox table tr",
    ]

    def _get_soup(self, url: str, encoding: str = None) -> Optional[BeautifulSoup]:
        """重写：使用 GB2312 编码获取页面。"""
        import requests
        if self.rate_limiter:
            self.rate_limiter.wait(self._extract_domain(url))

        session = self.session_manager.get_session(self.site_name) \
            if self.session_manager else requests

        try:
            resp = session.get(url, timeout=30)
            resp.raise_for_status()

            # 第一试卷网使用 GB2312 编码
            if encoding is None:
                ct = resp.headers.get("Content-Type", "")
                if "charset=gb2312" in ct.lower() or "charset=gbk" in ct.lower():
                    encoding = "gb2312"
                else:
                    encoding = "gb2312"  # 默认使用 GB2312

            resp.encoding = encoding
            return BeautifulSoup(resp.text, "lxml")
        except Exception as e:
            self.logger.error(f"GET {url} 失败: {e}")
            return None

    def search_papers(
        self,
        grade: Optional[str] = None,
        paper_type: Optional[str] = None,
        keyword: Optional[str] = None,
        max_pages: int = 10,
    ) -> Iterator[PaperLink]:
        """搜索试卷。"""
        grades_to_search = [grade] if grade else list(self.GRADE_PATH.keys())

        for g in grades_to_search:
            path = self.GRADE_PATH.get(g, self.ALL_PATH)
            list_id = None  # 分页列表 ID，从第一页提取

            for page in range(1, max_pages + 1):
                # 构建列表页 URL
                if page == 1:
                    url = urljoin(self.base_url, path)
                else:
                    if list_id:
                        url = urljoin(self.base_url,
                                      f"{path}list_{list_id}_{page}.html")
                    else:
                        break  # 无法确定分页 URL

                self.logger.debug(f"抓取列表: {url}")
                soup = self._get_soup(url)

                if not soup:
                    self.logger.debug(f"列表页 {page} 无响应，停止翻页")
                    break

                # 第一页提取分页列表 ID
                if page == 1 and list_id is None:
                    list_id = self._extract_list_id(soup, url)
                    if not list_id:
                        self.logger.debug("无法提取分页列表 ID")

                rows = self._extract_table_rows(soup)
                if not rows:
                    self.logger.debug(f"列表页 {page} 无条目，停止翻页")
                    break

                found = False
                for row in rows:
                    link = self._parse_table_row(row, g)
                    if link and self._matches_filter(link, paper_type, keyword):
                        found = True
                        yield link

                if not found and page > 1:
                    break

    def _extract_list_id(self, soup, first_page_url: str) -> Optional[str]:
        """从第一页提取分页列表 ID（如 701）。"""
        # 查找 class="pagelist" 中的链接
        pagelist = soup.select_one("ul.pagelist")
        if pagelist:
            for a in pagelist.find_all("a"):
                href = a.get("href", "")
                # 匹配 list_701_2.html 模式
                match = re.search(r'list_(\d+)_(\d+)\.html', href)
                if match:
                    return match.group(1)
        return None

    def _extract_table_rows(self, soup):
        """从列表页表格中提取试卷行。"""
        # 查找包含资源列表的 table
        tables = soup.find_all("table")
        for table in tables:
            rows = table.find_all("tr")
            # 找有数据的行（第一个 td 包含 a 标签）
            data_rows = []
            for row in rows:
                tds = row.find_all("td")
                if tds and tds[0].find("a"):
                    a_tag = tds[0].find("a")
                    href = a_tag.get("href", "")
                    # 确认是试卷详情链接（不是栏目链接）
                    if href.endswith(".html") and "/a/sjwl" in href:
                        data_rows.append(row)
            if data_rows:
                return data_rows
        return []

    def _parse_table_row(self, row, grade: str) -> Optional[PaperLink]:
        """解析表格行。结构：资源名称 | 文件类型 | 所属栏目 | 版本 | 大小 | 上传日期"""
        tds = row.find_all("td")
        if len(tds) < 2:
            return None

        a_tag = tds[0].find("a")
        if not a_tag:
            return None

        href = a_tag.get("href", "").strip()
        if not href or not href.endswith(".html"):
            return None

        if any(skip in href.lower() for skip in
               ["javascript:", "mailto:", "login"]):
            return None

        title = a_tag.get_text(strip=True)
        if not title or len(title) < 3:
            return None

        # 在物理栏目中，所有试卷都是物理的
        # 但仍排除明显不是物理的
        exclude_keywords = ["化学", "生物", "数学", "英语", "语文", "历史", "地理", "政治"]
        for kw in exclude_keywords:
            if kw in title:
                return None

        detail_url = urljoin(self.base_url, href)

        # 提取文件类型（第2列）
        format_hint = ""
        file_size = ""
        if len(tds) >= 2:
            format_text = tds[1].get_text(strip=True).lower()
            format_hint = format_text.lstrip(".")
            if format_hint in ("rar", "zip"):
                format_hint = "rar"  # rar 内含 doc/pdf

        # 提取文件大小（第5列）
        if len(tds) >= 5:
            file_size = tds[4].get_text(strip=True)

        # 从标题推断类型和年级
        paper_type = self._infer_paper_type(title)
        grade_inferred = self._infer_grade(title)
        final_grade = grade_inferred or grade

        return PaperLink(
            url=detail_url,
            title=title,
            grade=final_grade,
            paper_type=paper_type,
            format_hint=format_hint or "rar",
            size_hint=file_size,
        )

    def download_paper(self, link: PaperLink) -> Optional[str]:
        """
        下载试卷。
        详情页 → <ul class="downurllist"> → <a href="...rar">本地下载</a>
        """
        self.logger.info(f"下载: {link.title}")

        # 获取详情页
        soup = self._get_soup(link.url)
        if not soup:
            self.logger.warning(f"无法获取详情页: {link.url}")
            return None

        # 查找下载列表
        down_list = soup.select_one("ul.downurllist")
        if not down_list:
            # 尝试其他选择器
            down_list = soup.find("ul", class_=re.compile("down"))
            if not down_list:
                # 尝试找包含 "下载" 的链接
                for a in soup.find_all("a"):
                    if "下载" in a.get_text() and a.get("href", "").startswith("/uploads/"):
                        download_url = urljoin(self.base_url, a["href"])
                        link.format_hint = link.format_hint or "rar"
                        original_url = link.url
                        link.url = download_url
                        try:
                            return self._simple_download(link)
                        finally:
                            link.url = original_url

        if down_list:
            a_tag = down_list.find("a")
            if a_tag and a_tag.get("href"):
                download_url = urljoin(self.base_url, a_tag["href"])

                # 下载 URL 的实际扩展名是权威的（网站列表显示 doc
                # 但实际文件是 rar 压缩包）
                real_format = self._infer_format(download_url)
                if real_format:
                    link.format_hint = real_format
                elif not link.format_hint:
                    link.format_hint = "rar"

                original_url = link.url
                link.url = download_url
                try:
                    return self._simple_download(link)
                finally:
                    link.url = original_url

        self.logger.warning(f"详情页未找到下载链接: {link.url}")
        return None
