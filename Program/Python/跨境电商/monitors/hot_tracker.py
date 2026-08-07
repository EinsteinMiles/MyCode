"""
热销品追踪
排名快照 + 趋势检测 + 新品发现
"""

from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta

from config import logger
from core.models import Product, HotRanking, MonitorTask
from core.storage import Database
from core.utils import now_str


class HotTracker:
    """热销追踪器"""

    def __init__(self, db: Database):
        self.db = db

    def add_category_tracking(self, platform: str, category: str, keywords: str = "") -> int:
        """添加品类追踪"""
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

    def get_active_tracking_tasks(self) -> List[MonitorTask]:
        """获取所有活跃的热销追踪"""
        return self.db.get_active_monitor_tasks(task_type="hot_ranking")

    def take_snapshot(
        self, platform: str, category: str, rankings: List[HotRanking]
    ) -> int:
        """保存排名快照"""
        for r in rankings:
            r.platform = platform
            r.category = category
            r.snapshot_date = now_str()
        return self.db.insert_rankings_batch(rankings)

    def get_ranking_changes(
        self, platform: str, category: str, days: int = 7
    ) -> List[Dict[str, Any]]:
        """分析排名变化"""
        history = self.db.get_ranking_history(platform, category, days=days)
        if len(history) < 2:
            return []

        # 按 snapshot_date 分组
        snapshots: Dict[str, Dict[int, Dict]] = {}
        for row in history:
            date = row["snapshot_date"][:10]  # YYYY-MM-DD
            if date not in snapshots:
                snapshots[date] = {}
            snapshots[date][row["rank"]] = row

        dates = sorted(snapshots.keys())
        if len(dates) < 2:
            return []

        latest = snapshots[dates[-1]]
        previous = snapshots[dates[-2]]

        changes = []

        # 排名变化
        for rank, item in latest.items():
            title = item.get("title", "")
            prev_rank = None
            for pr, prev_item in previous.items():
                if prev_item.get("title") == title:
                    prev_rank = pr
                    break

            if prev_rank and prev_rank != rank:
                change = prev_rank - rank  # 正值=上升
                changes.append({
                    "type": "排名变化",
                    "title": title,
                    "old_rank": prev_rank,
                    "new_rank": rank,
                    "change": change,
                    "direction": "↑" if change > 0 else "↓",
                })

        # 新品上榜
        for rank, item in latest.items():
            title = item.get("title", "")
            found = any(
                prev_item.get("title") == title
                for prev_item in previous.values()
            )
            if not found:
                changes.append({
                    "type": "新上榜",
                    "title": title,
                    "new_rank": rank,
                })

        # 下榜
        for rank, item in previous.items():
            title = item.get("title", "")
            found = any(
                latest_item.get("title") == title
                for latest_item in latest.values()
            )
            if not found:
                changes.append({
                    "type": "已下榜",
                    "title": title,
                    "old_rank": rank,
                })

        return changes
