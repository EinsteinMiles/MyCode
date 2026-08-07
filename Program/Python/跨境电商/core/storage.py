"""
SQLite 数据库层 — 跨境电商版
自动建表 + 动态查询 + JSON 序列化
"""

import sqlite3
import json
import os
from typing import List, Optional, Dict, Any, Tuple

from config import DB_PATH, logger
from core.models import Product, PriceRecord, Review, HotRanking, MonitorTask, ExportRecord


class Database:
    """电商数据 SQLite 数据库"""

    def __init__(self, db_path: str = DB_PATH):
        self.db_path = db_path
        self.conn = sqlite3.connect(db_path)
        self.conn.row_factory = sqlite3.Row
        self.conn.execute("PRAGMA journal_mode=WAL")
        self.conn.execute("PRAGMA foreign_keys=ON")
        self._init_tables()
        logger.info(f"数据库已连接: {db_path}")

    def _init_tables(self) -> None:
        self.conn.executescript("""
            CREATE TABLE IF NOT EXISTS products (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                platform TEXT NOT NULL DEFAULT '',
                product_id TEXT NOT NULL DEFAULT '',
                title TEXT DEFAULT '',
                price REAL DEFAULT 0.0,
                price_range TEXT DEFAULT '',
                original_price REAL DEFAULT 0.0,
                currency TEXT DEFAULT 'USD',
                shipping_cost REAL DEFAULT 0.0,
                condition TEXT DEFAULT '',
                sales_count INTEGER DEFAULT 0,
                sales_text TEXT DEFAULT '',
                rating REAL DEFAULT 0.0,
                review_count INTEGER DEFAULT 0,
                shop_name TEXT DEFAULT '',
                seller_rating REAL DEFAULT 0.0,
                seller_feedback_count INTEGER DEFAULT 0,
                location TEXT DEFAULT '',
                category TEXT DEFAULT '',
                image_url TEXT DEFAULT '',
                url TEXT DEFAULT '',
                is_monitor INTEGER DEFAULT 0,
                first_seen TEXT DEFAULT '',
                last_updated TEXT DEFAULT '',
                extra_json TEXT DEFAULT '{}',
                UNIQUE(platform, product_id)
            );

            CREATE TABLE IF NOT EXISTS price_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                product_db_id INTEGER NOT NULL,
                price REAL NOT NULL DEFAULT 0.0,
                original_price REAL DEFAULT 0.0,
                currency TEXT DEFAULT 'USD',
                recorded_at TEXT NOT NULL DEFAULT '',
                FOREIGN KEY (product_db_id) REFERENCES products(id)
            );

            CREATE TABLE IF NOT EXISTS hot_rankings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                platform TEXT NOT NULL DEFAULT '',
                category TEXT NOT NULL DEFAULT '',
                product_db_id INTEGER,
                rank INTEGER NOT NULL DEFAULT 0,
                title TEXT DEFAULT '',
                price REAL DEFAULT 0.0,
                sales_text TEXT DEFAULT '',
                rating REAL DEFAULT 0.0,
                snapshot_date TEXT NOT NULL DEFAULT '',
                FOREIGN KEY (product_db_id) REFERENCES products(id)
            );

            CREATE TABLE IF NOT EXISTS reviews (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                product_db_id INTEGER NOT NULL,
                reviewer_name TEXT DEFAULT '',
                rating INTEGER DEFAULT 0,
                title TEXT DEFAULT '',
                content TEXT DEFAULT '',
                verified_purchase INTEGER DEFAULT 0,
                helpful_count INTEGER DEFAULT 0,
                sentiment_score REAL DEFAULT 0.0,
                sentiment_label TEXT DEFAULT '',
                review_date TEXT DEFAULT '',
                scraped_at TEXT NOT NULL DEFAULT '',
                FOREIGN KEY (product_db_id) REFERENCES products(id)
            );

            CREATE TABLE IF NOT EXISTS monitor_tasks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                task_type TEXT NOT NULL DEFAULT '',
                platform TEXT NOT NULL DEFAULT '',
                product_url TEXT DEFAULT '',
                product_db_id INTEGER,
                category TEXT DEFAULT '',
                keywords TEXT DEFAULT '',
                is_active INTEGER DEFAULT 1,
                created_at TEXT NOT NULL DEFAULT '',
                last_checked TEXT DEFAULT '',
                FOREIGN KEY (product_db_id) REFERENCES products(id)
            );

            CREATE TABLE IF NOT EXISTS export_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                export_type TEXT NOT NULL DEFAULT '',
                file_path TEXT NOT NULL DEFAULT '',
                created_at TEXT NOT NULL DEFAULT ''
            );

            CREATE INDEX IF NOT EXISTS idx_products_platform ON products(platform);
            CREATE INDEX IF NOT EXISTS idx_products_category ON products(category);
            CREATE INDEX IF NOT EXISTS idx_price_history_product ON price_history(product_db_id);
            CREATE INDEX IF NOT EXISTS idx_reviews_product ON reviews(product_db_id);
            CREATE INDEX IF NOT EXISTS idx_hot_rankings_category ON hot_rankings(category, snapshot_date);
            CREATE INDEX IF NOT EXISTS idx_monitor_active ON monitor_tasks(is_active);
        """)
        self.conn.commit()

    # ── 产品操作 ──────────────────────────────────────

    def upsert_product(self, product: Product) -> int:
        existing = self.conn.execute(
            "SELECT id FROM products WHERE platform = ? AND product_id = ?",
            (product.platform, product.product_id),
        ).fetchone()

        if existing:
            product_id = existing["id"]
            self.conn.execute(
                """UPDATE products SET
                    title=?, price=?, price_range=?, original_price=?, currency=?,
                    shipping_cost=?, condition=?, sales_count=?, sales_text=?,
                    rating=?, review_count=?, shop_name=?, seller_rating=?,
                    seller_feedback_count=?, location=?, category=?, image_url=?,
                    url=?, is_monitor=?, last_updated=?, extra_json=?
                WHERE id=?""",
                (
                    product.title, product.price, product.price_range, product.original_price,
                    product.currency, product.shipping_cost, product.condition,
                    product.sales_count, product.sales_text, product.rating,
                    product.review_count, product.shop_name, product.seller_rating,
                    product.seller_feedback_count, product.location, product.category,
                    product.image_url, product.url, 1 if product.is_monitor else 0,
                    product.last_updated, product.extra_json, product_id,
                ),
            )
        else:
            cursor = self.conn.execute(
                """INSERT INTO products
                    (platform, product_id, title, price, price_range, original_price,
                     currency, shipping_cost, condition, sales_count, sales_text,
                     rating, review_count, shop_name, seller_rating, seller_feedback_count,
                     location, category, image_url, url, is_monitor, first_seen, last_updated, extra_json)
                VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                (
                    product.platform, product.product_id, product.title,
                    product.price, product.price_range, product.original_price,
                    product.currency, product.shipping_cost, product.condition,
                    product.sales_count, product.sales_text, product.rating,
                    product.review_count, product.shop_name, product.seller_rating,
                    product.seller_feedback_count, product.location, product.category,
                    product.image_url, product.url, 1 if product.is_monitor else 0,
                    product.first_seen, product.last_updated, product.extra_json,
                ),
            )
            product_id = cursor.lastrowid

        self.conn.commit()
        return product_id

    def upsert_products_batch(self, products: List[Product]) -> int:
        count = 0
        for p in products:
            try:
                self.upsert_product(p)
                count += 1
            except Exception as e:
                logger.warning(f"upsert 失败: {p.title[:30]}... {e}")
        return count

    def get_product_by_id(self, db_id: int) -> Optional[Product]:
        row = self.conn.execute("SELECT * FROM products WHERE id = ?", (db_id,)).fetchone()
        return self._row_to_product(row) if row else None

    def get_products(
        self, platform: str = "", category: str = "",
        is_monitor: Optional[bool] = None,
        limit: int = 100, offset: int = 0,
    ) -> List[Product]:
        sql = "SELECT * FROM products WHERE 1=1"
        params: List[Any] = []

        if platform:
            sql += " AND platform = ?"
            params.append(platform)
        if category:
            sql += " AND category LIKE ?"
            params.append(f"%{category}%")
        if is_monitor is not None:
            sql += " AND is_monitor = ?"
            params.append(1 if is_monitor else 0)

        sql += " ORDER BY last_updated DESC LIMIT ? OFFSET ?"
        params.extend([limit, offset])

        rows = self.conn.execute(sql, params).fetchall()
        return [self._row_to_product(r) for r in rows]

    def search_products(self, keyword: str, limit: int = 50) -> List[Product]:
        rows = self.conn.execute(
            "SELECT * FROM products WHERE title LIKE ? ORDER BY last_updated DESC LIMIT ?",
            (f"%{keyword}%", limit),
        ).fetchall()
        return [self._row_to_product(r) for r in rows]

    def get_product_count(self, platform: str = "") -> int:
        if platform:
            row = self.conn.execute(
                "SELECT COUNT(*) as c FROM products WHERE platform = ?", (platform,)
            ).fetchone()
        else:
            row = self.conn.execute("SELECT COUNT(*) as c FROM products").fetchone()
        return row["c"] if row else 0

    def set_monitor_status(self, db_id: int, active: bool) -> None:
        self.conn.execute(
            "UPDATE products SET is_monitor = ? WHERE id = ?",
            (1 if active else 0, db_id)
        )
        self.conn.commit()

    # ── 价格历史 ──────────────────────────────────────

    def insert_price(self, record: PriceRecord) -> int:
        cursor = self.conn.execute(
            "INSERT INTO price_history (product_db_id, price, original_price, currency, recorded_at) VALUES (?,?,?,?,?)",
            (record.product_db_id, record.price, record.original_price, record.currency, record.recorded_at),
        )
        self.conn.commit()
        return cursor.lastrowid

    def get_price_history(self, product_db_id: int, days: int = 30) -> List[PriceRecord]:
        rows = self.conn.execute(
            """SELECT * FROM price_history
               WHERE product_db_id = ?
               AND recorded_at >= datetime('now', ? || ' days')
               ORDER BY recorded_at ASC""",
            (product_db_id, f"-{days}"),
        ).fetchall()
        return [self._row_to_price_record(r) for r in rows]

    def get_latest_price(self, product_db_id: int) -> Optional[PriceRecord]:
        row = self.conn.execute(
            "SELECT * FROM price_history WHERE product_db_id = ? ORDER BY recorded_at DESC LIMIT 1",
            (product_db_id,),
        ).fetchone()
        return self._row_to_price_record(row) if row else None

    # ── 评论操作 ──────────────────────────────────────

    def insert_review(self, review: Review) -> int:
        cursor = self.conn.execute(
            """INSERT INTO reviews
               (product_db_id, reviewer_name, rating, title, content, verified_purchase,
                helpful_count, sentiment_score, sentiment_label, review_date, scraped_at)
               VALUES (?,?,?,?,?,?,?,?,?,?,?)""",
            (
                review.product_db_id, review.reviewer_name, review.rating,
                review.title, review.content, 1 if review.verified_purchase else 0,
                review.helpful_count, review.sentiment_score, review.sentiment_label,
                review.review_date, review.scraped_at,
            ),
        )
        self.conn.commit()
        return cursor.lastrowid

    def insert_reviews_batch(self, reviews: List[Review]) -> int:
        count = 0
        for r in reviews:
            try:
                self.insert_review(r)
                count += 1
            except Exception as e:
                logger.warning(f"插入评论失败: {e}")
        return count

    def get_reviews(
        self, product_db_id: int, sentiment_label: str = "", limit: int = 100,
    ) -> List[Review]:
        sql = "SELECT * FROM reviews WHERE product_db_id = ?"
        params: List[Any] = [product_db_id]
        if sentiment_label:
            sql += " AND sentiment_label = ?"
            params.append(sentiment_label)
        sql += " ORDER BY review_date DESC LIMIT ?"
        params.append(limit)
        rows = self.conn.execute(sql, params).fetchall()
        return [self._row_to_review(r) for r in rows]

    def get_review_sentiment_stats(self, product_db_id: int) -> Dict[str, int]:
        rows = self.conn.execute(
            """SELECT sentiment_label, COUNT(*) as cnt
               FROM reviews WHERE product_db_id = ?
               GROUP BY sentiment_label""",
            (product_db_id,),
        ).fetchall()
        return {r["sentiment_label"]: r["cnt"] for r in rows}

    # ── 热销排行 ──────────────────────────────────────

    def insert_ranking(self, ranking: HotRanking) -> int:
        cursor = self.conn.execute(
            """INSERT INTO hot_rankings
               (platform, category, product_db_id, rank, title, price, sales_text, rating, snapshot_date)
               VALUES (?,?,?,?,?,?,?,?,?)""",
            (ranking.platform, ranking.category, ranking.product_db_id,
             ranking.rank, ranking.title, ranking.price, ranking.sales_text,
             ranking.rating, ranking.snapshot_date),
        )
        self.conn.commit()
        return cursor.lastrowid

    def insert_rankings_batch(self, rankings: List[HotRanking]) -> int:
        count = 0
        for r in rankings:
            try:
                self.insert_ranking(r)
                count += 1
            except Exception as e:
                logger.warning(f"插入排行失败: {e}")
        return count

    def get_ranking_history(
        self, platform: str, category: str, days: int = 7
    ) -> List[Dict[str, Any]]:
        rows = self.conn.execute(
            """SELECT * FROM hot_rankings
               WHERE platform = ? AND category = ?
               AND snapshot_date >= datetime('now', ? || ' days')
               ORDER BY snapshot_date DESC, rank ASC""",
            (platform, category, f"-{days}"),
        ).fetchall()
        return [dict(r) for r in rows]

    # ── 监控任务 ──────────────────────────────────────

    def add_monitor_task(self, task: MonitorTask) -> int:
        cursor = self.conn.execute(
            """INSERT INTO monitor_tasks
               (task_type, platform, product_url, product_db_id, category, keywords,
                is_active, created_at, last_checked)
               VALUES (?,?,?,?,?,?,?,?,?)""",
            (task.task_type, task.platform, task.product_url, task.product_db_id,
             task.category, task.keywords, 1 if task.is_active else 0,
             task.created_at, task.last_checked),
        )
        self.conn.commit()
        return cursor.lastrowid

    def get_active_monitor_tasks(self, task_type: str = "") -> List[MonitorTask]:
        sql = "SELECT * FROM monitor_tasks WHERE is_active = 1"
        params: List[Any] = []
        if task_type:
            sql += " AND task_type = ?"
            params.append(task_type)
        rows = self.conn.execute(sql, params).fetchall()
        return [self._row_to_monitor_task(r) for r in rows]

    def update_monitor_last_checked(self, task_id: int, checked_at: str) -> None:
        self.conn.execute(
            "UPDATE monitor_tasks SET last_checked = ? WHERE id = ?",
            (checked_at, task_id),
        )
        self.conn.commit()

    def delete_monitor_task(self, task_id: int) -> None:
        self.conn.execute("DELETE FROM monitor_tasks WHERE id = ?", (task_id,))
        self.conn.commit()

    # ── 导出记录 ──────────────────────────────────────

    def record_export(self, export_type: str, file_path: str, created_at: str) -> int:
        cursor = self.conn.execute(
            "INSERT INTO export_history (export_type, file_path, created_at) VALUES (?,?,?)",
            (export_type, file_path, created_at),
        )
        self.conn.commit()
        return cursor.lastrowid

    # ── 行转模型 ──────────────────────────────────────

    def _row_to_product(self, row: sqlite3.Row) -> Product:
        return Product(
            id=row["id"], platform=row["platform"], product_id=row["product_id"],
            title=row["title"], price=row["price"], price_range=row["price_range"],
            original_price=row["original_price"], currency=row["currency"],
            shipping_cost=row["shipping_cost"], condition=row["condition"],
            sales_count=row["sales_count"], sales_text=row["sales_text"],
            rating=row["rating"], review_count=row["review_count"],
            shop_name=row["shop_name"], seller_rating=row["seller_rating"],
            seller_feedback_count=row["seller_feedback_count"],
            location=row["location"], category=row["category"],
            image_url=row["image_url"], url=row["url"],
            is_monitor=bool(row["is_monitor"]),
            first_seen=row["first_seen"], last_updated=row["last_updated"],
            extra_json=row["extra_json"],
        )

    def _row_to_price_record(self, row: sqlite3.Row) -> PriceRecord:
        return PriceRecord(
            id=row["id"], product_db_id=row["product_db_id"],
            price=row["price"], original_price=row["original_price"],
            currency=row.get("currency", "USD"), recorded_at=row["recorded_at"],
        )

    def _row_to_review(self, row: sqlite3.Row) -> Review:
        return Review(
            id=row["id"], product_db_id=row["product_db_id"],
            reviewer_name=row["reviewer_name"], rating=row["rating"],
            title=row.get("title", ""), content=row["content"],
            verified_purchase=bool(row.get("verified_purchase", 0)),
            helpful_count=row.get("helpful_count", 0),
            sentiment_score=row["sentiment_score"],
            sentiment_label=row["sentiment_label"],
            review_date=row["review_date"], scraped_at=row["scraped_at"],
        )

    def _row_to_monitor_task(self, row: sqlite3.Row) -> MonitorTask:
        return MonitorTask(
            id=row["id"], task_type=row["task_type"], platform=row["platform"],
            product_url=row["product_url"], product_db_id=row["product_db_id"],
            category=row["category"], keywords=row["keywords"],
            is_active=bool(row["is_active"]),
            created_at=row["created_at"], last_checked=row["last_checked"],
        )

    # ── 生命周期 ──────────────────────────────────────

    def close(self) -> None:
        self.conn.close()
        logger.info("数据库已关闭")

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()
