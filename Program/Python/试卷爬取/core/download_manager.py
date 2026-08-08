"""
下载管理器 — 去重、断点续传、文件组织、验证。
"""

import os
import hashlib
import logging
from pathlib import Path
from typing import Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from core.base_scraper import BaseScraper, PaperLink
    from storage.database import DownloadDatabase

logger = logging.getLogger(__name__)


class DownloadManager:
    """管理下载生命周期：去重、命名、续传、验证、记录。"""

    def __init__(self, config=None, db: "DownloadDatabase" = None):
        self.config = config
        self.db = db

        # 下载目录
        self.download_dir = Path(
            config.get("general", {}).get("download_dir", "./downloads")
            if hasattr(config, "get") else "./downloads"
        )

        # 下载配置
        dl_config = config.get("download", {}) if hasattr(config, "get") else {}
        self.overwrite = dl_config.get("overwrite_existing", False)
        self.resume = dl_config.get("resume_incomplete", True)
        self.allowed_extensions = dl_config.get("allowed_extensions", ["pdf", "doc", "docx"])
        self.min_file_size = dl_config.get("min_file_size_kb", 10) * 1024
        self.max_file_size = dl_config.get("max_file_size_mb", 50) * 1024 * 1024
        self.dedup_enabled = dl_config.get("dedup", {}).get("enabled", True)

    def download(self, link: "PaperLink",
                 scraper: "BaseScraper") -> Optional[str]:
        """
        下载一个试卷文件。

        Args:
            link: 试卷链接信息
            scraper: 所属爬虫实例

        Returns:
            本地文件路径，失败返回 None
        """
        # 1. 去重检查
        if self.dedup_enabled and self.db:
            if self.db.is_duplicate(link.url):
                logger.info(f"跳过重复: {link.title}")
                return None

        # 2. 生成目标路径
        dest_path = self._generate_path(link, scraper.site_name)

        # 3. 检查已存在
        if dest_path.exists():
            if not self.overwrite:
                logger.info(f"文件已存在，跳过: {dest_path}")
                if self.db:
                    self.db.record_download(
                        link.url, link.title, scraper.site_name,
                        grade=link.grade, paper_type=link.paper_type,
                        file_path=str(dest_path),
                        file_size=dest_path.stat().st_size,
                        file_format=link.format_hint,
                        status="completed"
                    )
                return str(dest_path)
            else:
                dest_path.unlink()

        # 4. 断点续传
        temp_path = dest_path.with_suffix(dest_path.suffix + ".part")
        resume_pos = 0
        if self.resume and temp_path.exists():
            resume_pos = temp_path.stat().st_size
            logger.info(f"续传下载: {link.title}, 从 {resume_pos} 字节开始")

        # 5. 委托给爬虫的实际下载逻辑
        # 先获取直接下载 URL（爬虫的 download_paper 可能已经处理过）
        try:
            result_path = scraper.download_paper(link)
            if result_path:
                # 爬虫自己处理了下载
                if self.db:
                    self.db.record_download(
                        link.url, link.title, scraper.site_name,
                        grade=link.grade, paper_type=link.paper_type,
                        file_path=result_path,
                        file_format=link.format_hint,
                        status="completed"
                    )
                return result_path
        except Exception as e:
            logger.error(f"爬虫下载失败: {e}")

        # 6. 使用默认方式下载
        result = self._stream_download(link, scraper, dest_path,
                                       temp_path, resume_pos)
        return result

    def _stream_download(self, link, scraper, dest_path, temp_path,
                         resume_pos) -> Optional[str]:
        """流式下载文件（支持断点续传）。"""
        try:
            session = scraper.session_manager.get_session(scraper.site_name) \
                if scraper.session_manager else None

            headers = {}
            mode = "wb"
            if resume_pos > 0:
                headers["Range"] = f"bytes={resume_pos}-"
                mode = "ab"

            # 限速等待
            if scraper.rate_limiter:
                domain = scraper._extract_domain(link.url)
                scraper.rate_limiter.wait(domain)

            if session:
                resp = session.get(link.url, headers=headers,
                                   stream=True, timeout=60)
            else:
                import requests
                resp = requests.get(link.url, headers=headers,
                                   stream=True, timeout=60)

            if resp.status_code not in (200, 206):
                logger.error(f"下载失败 HTTP {resp.status_code}: {link.url}")
                self._record_error(link, scraper, f"HTTP {resp.status_code}")
                return None

            # 确定写入模式
            dest_path.parent.mkdir(parents=True, exist_ok=True)

            with open(temp_path, mode) as f:
                for chunk in resp.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)

            # 验证文件
            file_size = temp_path.stat().st_size
            if file_size < self.min_file_size:
                logger.warning(f"文件过小 ({file_size} bytes)，丢弃: {link.title}")
                temp_path.unlink()
                self._record_error(link, scraper, "文件过小")
                return None

            if file_size > self.max_file_size:
                logger.warning(f"文件过大 ({file_size} bytes)，丢弃: {link.title}")
                temp_path.unlink()
                self._record_error(link, scraper, "文件过大")
                return None

            # 验证扩展名
            if link.format_hint and link.format_hint not in self.allowed_extensions:
                logger.warning(f"不允许的格式: {link.format_hint}")
                # 不丢弃，只是警告，因为格式检测可能不准确

            # 原子重命名
            temp_path.rename(dest_path)
            logger.info(f"下载完成: {dest_path} ({file_size} bytes)")

            if self.db:
                self.db.record_download(
                    link.url, link.title, scraper.site_name,
                    grade=link.grade, paper_type=link.paper_type,
                    file_path=str(dest_path),
                    file_size=file_size,
                    file_format=link.format_hint,
                    status="completed"
                )

            return str(dest_path)

        except Exception as e:
            logger.error(f"下载异常: {link.title} - {e}")
            self._record_error(link, scraper, str(e))
            return None

    def _generate_path(self, link: "PaperLink", site_name: str) -> Path:
        """生成按站点/年级组织的下载路径。"""
        safe_site = self._sanitize(site_name)
        safe_grade = self._sanitize(link.grade) if link.grade else "未知年级"
        safe_type = self._sanitize(link.paper_type) if link.paper_type else "其他"
        safe_title = self._sanitize(link.title, max_len=60)
        ext = link.format_hint.lstrip(".") if link.format_hint else "pdf"

        filename = f"{safe_type}_{safe_title}.{ext}"
        return self.download_dir / safe_site / safe_grade / filename

    def _record_error(self, link, scraper, error: str):
        """记录下载错误。"""
        if self.db:
            try:
                self.db.record_download(
                    link.url, link.title, scraper.site_name,
                    grade=link.grade, paper_type=link.paper_type,
                    status="failed", error=error
                )
            except Exception:
                pass

    @staticmethod
    def _sanitize(text: str, max_len: int = 50) -> str:
        """清理路径中的非法字符。"""
        import re
        cleaned = re.sub(r'[<>:"/\\|?*\n\r\t]', '_', text)
        cleaned = cleaned.strip().strip('.')
        if len(cleaned) > max_len:
            cleaned = cleaned[:max_len]
        return cleaned if cleaned else "unknown"
