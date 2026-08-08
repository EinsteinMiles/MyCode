"""
SQLite 数据库 — 下载记录、去重、统计。
"""

import sqlite3
import hashlib
import threading
from pathlib import Path
from datetime import datetime
from typing import Optional


class DownloadDatabase:
    """管理下载记录的 SQLite 数据库。"""

    def __init__(self, db_path: str = None):
        if db_path is None:
            db_path = Path(__file__).parent / "downloads.db"
        self.db_path = str(db_path)
        self._local = threading.local()
        self._init_db()

    @property
    def conn(self) -> sqlite3.Connection:
        """线程安全的数据库连接。"""
        if not hasattr(self._local, "conn") or self._local.conn is None:
            self._local.conn = sqlite3.connect(self.db_path)
            self._local.conn.row_factory = sqlite3.Row
            self._local.conn.execute("PRAGMA journal_mode=WAL")
        return self._local.conn

    def _init_db(self):
        """初始化数据库表。"""
        conn = sqlite3.connect(self.db_path)
        conn.execute("PRAGMA journal_mode=WAL")
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS download_records (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                url_hash TEXT UNIQUE NOT NULL,
                original_url TEXT NOT NULL,
                final_url TEXT,
                title TEXT,
                site_name TEXT NOT NULL,
                grade TEXT,
                paper_type TEXT,
                file_path TEXT,
                file_size_bytes INTEGER,
                file_format TEXT,
                status TEXT DEFAULT 'pending',
                error_message TEXT,
                retry_count INTEGER DEFAULT 0,
                created_at TEXT DEFAULT (datetime('now','localtime')),
                updated_at TEXT DEFAULT (datetime('now','localtime'))
            );

            CREATE INDEX IF NOT EXISTS idx_url_hash ON download_records(url_hash);
            CREATE INDEX IF NOT EXISTS idx_site ON download_records(site_name);
            CREATE INDEX IF NOT EXISTS idx_status ON download_records(status);

            CREATE TABLE IF NOT EXISTS scrape_sessions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                site_name TEXT NOT NULL,
                pages_scraped INTEGER DEFAULT 0,
                links_found INTEGER DEFAULT 0,
                downloads_attempted INTEGER DEFAULT 0,
                downloads_completed INTEGER DEFAULT 0,
                started_at TEXT DEFAULT (datetime('now','localtime')),
                finished_at TEXT
            );
        """)
        conn.commit()
        conn.close()

    @staticmethod
    def hash_url(url: str) -> str:
        """计算 URL 的 SHA256 哈希。"""
        return hashlib.sha256(url.encode("utf-8")).hexdigest()

    def is_duplicate(self, url: str) -> bool:
        """检查 URL 是否已经下载过（仅检查成功完成的）。"""
        url_hash = self.hash_url(url)
        row = self.conn.execute(
            "SELECT id FROM download_records WHERE url_hash = ? AND status = 'completed'",
            (url_hash,)
        ).fetchone()
        return row is not None

    def record_download(self, url: str, title: str, site_name: str,
                        grade: str = "", paper_type: str = "",
                        file_path: str = "", file_size: int = 0,
                        file_format: str = "", status: str = "pending",
                        error: str = "") -> int:
        """记录下载（存在则更新）。"""
        url_hash = self.hash_url(url)
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        existing = self.conn.execute(
            "SELECT id, retry_count FROM download_records WHERE url_hash = ?",
            (url_hash,)
        ).fetchone()

        if existing:
            retry_count = existing["retry_count"] + 1
            self.conn.execute("""
                UPDATE download_records
                SET final_url = ?, file_path = ?, file_size_bytes = ?,
                    file_format = ?, status = ?, error_message = ?,
                    retry_count = ?, updated_at = ?
                WHERE url_hash = ?
            """, (url, file_path, file_size, file_format, status, error,
                  retry_count, now, url_hash))
            self.conn.commit()
            return existing["id"]
        else:
            cur = self.conn.execute("""
                INSERT INTO download_records
                (url_hash, original_url, final_url, title, site_name, grade,
                 paper_type, file_path, file_size_bytes, file_format, status,
                 error_message, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (url_hash, url, url, title, site_name, grade, paper_type,
                  file_path, file_size, file_format, status, error, now, now))
            self.conn.commit()
            return cur.lastrowid

    def start_scrape_session(self, site_name: str) -> int:
        """开始一次爬取会话，返回 session ID。"""
        cur = self.conn.execute(
            "INSERT INTO scrape_sessions (site_name) VALUES (?)",
            (site_name,)
        )
        self.conn.commit()
        return cur.lastrowid

    def update_scrape_session(self, session_id: int, **kwargs):
        """更新爬取会话统计。"""
        if not kwargs:
            return
        sets = ", ".join(f"{k} = ?" for k in kwargs)
        values = list(kwargs.values()) + [session_id]
        self.conn.execute(
            f"UPDATE scrape_sessions SET {sets} WHERE id = ?", values
        )
        self.conn.commit()

    def finish_scrape_session(self, session_id: int, links: int = 0,
                               downloads: int = 0, completed: int = 0):
        """结束爬取会话。"""
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.conn.execute("""
            UPDATE scrape_sessions
            SET finished_at = ?, links_found = ?,
                downloads_attempted = ?, downloads_completed = ?
            WHERE id = ?
        """, (now, links, downloads, completed, session_id))
        self.conn.commit()

    def get_stats(self) -> dict:
        """获取下载统计。"""
        total = self.conn.execute(
            "SELECT COUNT(*) FROM download_records"
        ).fetchone()[0]
        completed = self.conn.execute(
            "SELECT COUNT(*) FROM download_records WHERE status = 'completed'"
        ).fetchone()[0]
        failed = self.conn.execute(
            "SELECT COUNT(*) FROM download_records WHERE status = 'failed'"
        ).fetchone()[0]

        # 按站点统计
        by_site = {}
        rows = self.conn.execute("""
            SELECT site_name, COUNT(*) as cnt
            FROM download_records WHERE status = 'completed'
            GROUP BY site_name
        """).fetchall()
        for r in rows:
            by_site[r["site_name"]] = r["cnt"]

        # 按年级统计
        by_grade = {}
        rows = self.conn.execute("""
            SELECT grade, COUNT(*) as cnt
            FROM download_records WHERE status = 'completed'
            GROUP BY grade
        """).fetchall()
        for r in rows:
            by_grade[r["grade"]] = r["cnt"]

        return {
            "total": total,
            "completed": completed,
            "failed": failed,
            "by_site": by_site,
            "by_grade": by_grade,
        }

    def close(self):
        """关闭数据库连接。"""
        if hasattr(self._local, "conn") and self._local.conn:
            self._local.conn.close()
            self._local.conn = None
