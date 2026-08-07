"""
热销品追踪
品类排名快照 + 变化检测 + 趋势报告
"""

from typing import List, Dict, Any, Optional
from datetime import datetime

from config import logger
from core.models import Product, HotRanking, MonitorTask
from core.storage import Database
from core.utils import now_str


class HotTracker:
    """热销品追踪器"""

    def __init__(self, db: Database):
        self.db = db

    def add_category_tracking(
        self, platform: str, category: str, keywords: str = ""
    ) -> int:
        """添加品类热销追踪"""
        task = MonitorTask(
            task_type="hot_ranking",
            platform=platform,
            category=category,
            keywords=keywords or category,
            is_active=True,
            created_at=now_str(),
        )
        task_id = self.db.add_monitor_task(task)
        logger.info(f"已添加热销追踪: {platform}/{category}")
        return task_id

    def take_snapshot(
        self, platform: str, category: str, rankings: List[HotRanking]
    ) -> int:
        """
        保存排行快照
        返回保存的条数
        """
        for r in rankings:
            r.platform = platform
            r.category = category
            r.snapshot_date = now_str()
        return self.db.insert_rankings_batch(rankings)

    def get_ranking_changes(
        self, platform: str, category: str
    ) -> List[Dict[str, Any]]:
        """
        分析排名变化（最近两次快照对比）
        """
        history = self.db.get_ranking_history(platform, category, days=7)

        if len(history) < 2:
            return []

        # 取最新两次快照
        latest_date = history[0]["snapshot_date"]
        prev_date = None
        for h in history[1:]:
            if h["snapshot_date"] != latest_date:
                prev_date = h["snapshot_date"]
                break

        if not prev_date:
            return []

        latest = {h["title"]: h for h in history if h["snapshot_date"] == latest_date}
        prev = {h["title"]: h for h in history if h["snapshot_date"] == prev_date}

        changes = []

        # 排名变化
        for title, item in latest.items():
            prev_item = prev.get(title)
            if prev_item:
                rank_change = prev_item["rank"] - item["rank"]
                if abs(rank_change) >= 3:  # 变化超过3位
                    changes.append({
                        "title": title,
                        "type": "排名变化",
                        "old_rank": prev_item["rank"],
                        "new_rank": item["rank"],
                        "change": rank_change,
                        "direction": "上升" if rank_change > 0 else "下降",
                    })

        # 新品上榜
        prev_titles = set(prev.keys())
        for title in latest:
            if title not in prev_titles:
                changes.append({
                    "title": title,
                    "type": "新品上榜",
                    "new_rank": latest[title]["rank"],
                })

        # 下榜
        latest_titles = set(latest.keys())
        for title in prev:
            if title not in latest_titles:
                changes.append({
                    "title": title,
                    "type": "下榜",
                    "old_rank": prev[title]["rank"],
                })

        return sorted(changes, key=lambda x: abs(x.get("change", x.get("new_rank", 0))))

    def detect_hot_newcomers(
        self, platform: str, category: str
    ) -> List[Dict[str, Any]]:
        """检测新品上榜（最近才出现的商品）"""
        changes = self.get_ranking_changes(platform, category)
        return [c for c in changes if c["type"] == "新品上榜"]

    def get_trending_products(
        self, platform: str, category: str, top_n: int = 10
    ) -> List[Dict[str, Any]]:
        """
        获取趋势商品（排名持续上升的）
        """
        history = self.db.get_ranking_history(platform, category, days=7)
        if not history:
            return []

        # 按标题分组，计算排名趋势
        by_title: Dict[str, List] = {}
        for h in history:
            title = h["title"]
            if title not in by_title:
                by_title[title] = []
            by_title[title].append(h)

        trends = []
        for title, entries in by_title.items():
            if len(entries) < 2:
                continue
            first_rank = entries[-1]["rank"]  # 最早
            last_rank = entries[0]["rank"]  # 最新
            if first_rank > last_rank:  # 排名数字越小越好
                trends.append({
                    "title": title,
                    "first_rank": first_rank,
                    "last_rank": last_rank,
                    "improvement": first_rank - last_rank,
                    "price": entries[0].get("price", 0),
                    "sales": entries[0].get("sales_text", ""),
                })

        return sorted(trends, key=lambda x: x["improvement"], reverse=True)[:top_n]

    def get_active_tracking_tasks(self) -> List[MonitorTask]:
        """获取活跃追踪任务"""
        return self.db.get_active_monitor_tasks(task_type="hot_ranking")

    def update_tracking_time(self, task_id: int) -> None:
        self.db.update_monitor_last_checked(task_id, now_str())
