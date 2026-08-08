"""
爬虫抽象基类 — 所有站点爬虫的基础。
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional, Iterator
from urllib.parse import urljoin
import logging

import requests
from bs4 import BeautifulSoup


class ScraperType(Enum):
    """爬虫策略类型。"""
    STATIC = "static"      # requests + BeautifulSoup
    DYNAMIC = "dynamic"    # selenium/playwright 渲染
    API = "api"            # 内部 JSON API 逆向


class AuthLevel(Enum):
    """站点认证要求。"""
    NONE = "none"          # 完全开放，无需登录
    LOGIN = "login"        # 需登录才能看到下载链接
    VIP = "vip"            # 需付费 VIP
    WALLED = "walled"      # 强反爬（验证码等）


@dataclass
class PaperLink:
    """发现的试卷链接（下载前）。"""
    url: str
    title: str
    grade: str = ""                      # "高一", "高二", "高三"
    paper_type: str = ""                 # "期中", "期末", "月考", "模拟", "真题", "专项"
    format_hint: str = ""                # "pdf", "doc", "docx"
    size_hint: str = ""                  # e.g., "1.2MB"
    metadata: dict = field(default_factory=dict)

    def __str__(self):
        parts = []
        if self.grade:
            parts.append(self.grade)
        if self.paper_type:
            parts.append(self.paper_type)
        parts.append(self.title)
        if self.format_hint:
            parts.append(f"[{self.format_hint}]")
        return " ".join(parts)


class BaseScraper(ABC):
    """所有站点爬虫的抽象基类。"""

    # ---- 子类必须设置 ----
    site_name: str = ""       # e.g., "第一试卷网"
    base_url: str = ""        # e.g., "https://www.shijuan1.com"
    scraper_type: ScraperType = ScraperType.STATIC
    auth_level: AuthLevel = AuthLevel.NONE

    # 试卷类型关键词映射
    TYPE_KEYWORDS = {
        "期中考试": ["期中", "期中考试", "期中测试", "期中试卷"],
        "期末考试": ["期末", "期末考试", "期末测试", "期末试卷"],
        "月考试卷": ["月考", "月考试卷", "月考卷"],
        "高考模拟": ["模拟", "一模", "二模", "三模", "模拟考试", "仿真"],
        "高考真题": ["高考真题", "高考", "高考试题", "全国卷", "真题"],
        "专项练习": ["专项", "专题", "练习", "强化", "训练"],
        "同步练习": ["同步", "课时", "随堂", "章节"],
    }

    def __init__(self, config=None, session_manager=None,
                 rate_limiter=None, download_manager=None,
                 logger: logging.Logger = None):
        self.config = config
        self.session_manager = session_manager
        self.rate_limiter = rate_limiter
        self.download_manager = download_manager
        self.logger = logger or logging.getLogger(self.site_name or __name__)

    # ---- 抽象方法 ----

    @abstractmethod
    def search_papers(
        self,
        grade: Optional[str] = None,
        paper_type: Optional[str] = None,
        keyword: Optional[str] = None,
        max_pages: int = 10,
    ) -> Iterator[PaperLink]:
        """
        搜索试卷。必须实现为生成器，逐个 yield PaperLink。

        Args:
            grade: 年级筛选 ("高一"/"高二"/"高三")，None 表示全部
            paper_type: 试卷类型筛选，None 表示全部
            keyword: 额外搜索关键词
            max_pages: 最多搜索页数

        Yields:
            PaperLink 对象
        """
        ...

    # ---- 可选重写 ----

    def download_paper(self, link: PaperLink) -> Optional[str]:
        """
        下载单个试卷。返回本地文件路径或 None。
        默认实现：GET 下载 → 委托给 DownloadManager。
        子类可重写以处理特定站点的下载逻辑。
        """
        if self.download_manager:
            return self.download_manager.download(link, self)
        return self._simple_download(link)

    def can_handle(self, url: str) -> bool:
        """检查此爬虫能否处理该 URL。"""
        return self.base_url in url if self.base_url else False

    # ---- 供子类使用的辅助方法 ----

    def _get(self, url: str, **kwargs) -> Optional[requests.Response]:
        """带限速的 GET 请求。"""
        if self.rate_limiter:
            domain = self._extract_domain(url)
            self.rate_limiter.wait(domain)

        session = self.session_manager.get_session(self.site_name) \
            if self.session_manager else requests

        try:
            kwargs.setdefault("timeout", 30)
            response = session.get(url, **kwargs)
            response.raise_for_status()
            return response
        except Exception as e:
            self.logger.error(f"GET {url} 失败: {e}")
            return None

    def _post(self, url: str, **kwargs) -> Optional[requests.Response]:
        """带限速的 POST 请求。"""
        if self.rate_limiter:
            domain = self._extract_domain(url)
            self.rate_limiter.wait(domain)

        session = self.session_manager.get_session(self.site_name) \
            if self.session_manager else requests

        try:
            kwargs.setdefault("timeout", 30)
            response = session.post(url, **kwargs)
            response.raise_for_status()
            return response
        except Exception as e:
            self.logger.error(f"POST {url} 失败: {e}")
            return None

    def _get_soup(self, url: str, encoding: str = None) -> Optional[BeautifulSoup]:
        """获取页面并解析为 BeautifulSoup。"""
        resp = self._get(url)
        if not resp:
            return None

        # 自动检测编码
        if encoding is None:
            # 尝试从 Content-Type 获取
            ct = resp.headers.get("Content-Type", "")
            if "charset=" in ct:
                encoding = ct.split("charset=")[-1].strip()
            else:
                # 尝试从 meta 标签获取
                resp.encoding = resp.apparent_encoding

        if encoding:
            resp.encoding = encoding

        return BeautifulSoup(resp.text, "lxml")

    # 文件魔术字节 → 扩展名映射
    FILE_MAGIC = {
        b"Rar!\x1a\x07\x00": "rar",
        b"Rar!\x1a\x07\x01": "rar",
        b"PK\x03\x04": "zip",        # ZIP 和 DOCX 都是 ZIP 格式
        b"%PDF": "pdf",
        b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1": "doc",  # OLE2 (旧 .doc)
    }

    @classmethod
    def _detect_format_by_magic(cls, filepath: Path) -> Optional[str]:
        """通过文件魔术字节检测真实文件类型。"""
        try:
            with open(filepath, "rb") as f:
                header = f.read(8)
            for magic, ext in cls.FILE_MAGIC.items():
                if header.startswith(magic):
                    # DOCX 是 ZIP 格式，需要额外判断
                    if ext == "zip" and filepath.suffix.lower() in (".docx",):
                        return "docx"
                    return ext
        except Exception:
            pass
        return None

    def _simple_download(self, link: PaperLink) -> Optional[str]:
        """最简单的下载：直接 GET 写入文件，自动修正扩展名。"""
        resp = self._get(link.url, stream=True)
        if not resp:
            return None

        ext = link.format_hint.lstrip(".") or "pdf"
        safe_title = self._sanitize_filename(link.title, max_len=60)
        filename = f"{link.paper_type}_{safe_title}.{ext}" if link.paper_type else f"{safe_title}.{ext}"

        grade_dir = link.grade or "未知年级"
        site_dir = self._sanitize_filename(self.site_name)
        download_dir = (self.config.get("general", {}).get("download_dir", "./downloads")
                        if hasattr(self.config, "get") else "./downloads")
        dest_dir = Path(download_dir) / site_dir / grade_dir
        dest_dir.mkdir(parents=True, exist_ok=True)
        dest_path = dest_dir / filename

        with open(dest_path, "wb") as f:
            for chunk in resp.iter_content(chunk_size=8192):
                f.write(chunk)

        # 用文件头魔术字节修正扩展名（防止 HTML 错误页 / 格式标注错误）
        real_ext = self._detect_format_by_magic(dest_path)
        if real_ext and real_ext != ext:
            # .docx 是 ZIP 格式的特殊情况
            if ext == "docx" and real_ext == "zip":
                pass  # DOCX 本身就是 ZIP，不需要改
            else:
                new_path = dest_path.with_suffix(f".{real_ext}")
                dest_path.rename(new_path)
                dest_path = new_path
                self.logger.info(f"扩展名已修正: .{ext} → .{real_ext}")

        self.logger.info(f"下载完成: {dest_path}")
        return str(dest_path)

    def _paginate(self, url_template: str, max_pages: int,
                  start: int = 1) -> Iterator[str]:
        """生成分页 URL。"""
        for page in range(start, max_pages + 1):
            yield url_template.format(page=page)

    def _infer_paper_type(self, title: str) -> str:
        """从标题推断试卷类型。"""
        for paper_type, keywords in self.TYPE_KEYWORDS.items():
            for kw in keywords:
                if kw in title:
                    return paper_type
        return "其他"

    def _infer_grade(self, title: str) -> str:
        """从标题推断年级。"""
        if "高三" in title or "高考" in title:
            return "高三"
        if "高二" in title:
            return "高二"
        if "高一" in title:
            return "高一"
        return ""

    def _infer_format(self, url: str) -> str:
        """从 URL 推断文件格式。"""
        url_lower = url.lower()
        if ".pdf" in url_lower:
            return "pdf"
        if ".docx" in url_lower:
            return "docx"
        if ".doc" in url_lower:
            return "doc"
        if ".rar" in url_lower:
            return "rar"
        if ".zip" in url_lower:
            return "zip"
        return ""

    def _matches_filter(self, link: PaperLink, paper_type: str = None,
                        keyword: str = None) -> bool:
        """检查 PaperLink 是否匹配筛选条件。"""
        if paper_type and link.paper_type and link.paper_type != paper_type:
            # 宽松匹配
            keywords = self.TYPE_KEYWORDS.get(paper_type, [])
            if not any(kw in link.title for kw in keywords):
                return False
        if keyword and keyword not in link.title:
            return False
        return True

    @staticmethod
    def _extract_domain(url: str) -> str:
        """从 URL 提取域名。"""
        from urllib.parse import urlparse
        return urlparse(url).netloc or urlparse("//" + url).netloc

    @staticmethod
    def _sanitize_filename(filename: str, max_len: int = 80) -> str:
        """清理文件名中的非法字符。"""
        import re
        # 替换非法字符
        cleaned = re.sub(r'[<>:"/\\|?*]', '_', filename)
        # 截断
        if len(cleaned) > max_len:
            cleaned = cleaned[:max_len]
        return cleaned.strip()

    def __repr__(self):
        return (f"{self.__class__.__name__}("
                f"site='{self.site_name}', "
                f"type={self.scraper_type.value}, "
                f"auth={self.auth_level.value})")


import os
from pathlib import Path
