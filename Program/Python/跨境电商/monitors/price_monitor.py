"""
竞品价格监控 — 跨境电商版
定时抓取价格 + 变动检测 + 告警
"""

from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta

from config import PRICE_ALERT_THRESHOLD_PCT, logger
from core.models import Product, PriceRecord, MonitorTask
from core.storage import Database
from core.utils import now_str


class PriceMonitor:
    """价格监控器"""

    def __init__(self, db: Database):
        self.db = db

    def add_product_to_monitor(self, product_db_id: int, platform: str = "") -> int:
        """将商品加入价格监控"""
        product = self.db.get_product_by_id(product_db_id)
        if not product:
            logger.error(f"商品不存在: id={product_db_id}")
            return -1

        self.db.set_monitor_status(product_db_id, True)

        task = MonitorTask(
            task_type="price",
            platform=product.platform,
            product_url=product.url,
            product_db_id=product_db_id,
            is_active=True,
            created_at=now_str(),
        )
        task_id = self.db.add_monitor_task(task)
        logger.info(f"已添加价格监控: {product.title[:30]}... (task_id={task_id})")
        return task_id

    def add_product_by_url(
        self, url: str, platform: str, product_db_id: int = 0
    ) -> int:
        """通过 URL 添加监控"""
        task = MonitorTask(
            task_type="price",
            platform=platform,
            product_url=url,
            product_db_id=product_db_id,
            is_active=True,
            created_at=now_str(),
        )
        task_id = self.db.add_monitor_task(task)
        logger.info(f"已添加价格监控: {url[:60]}...")
        return task_id

    def check_price(
        self, product_db_id: int, current_price: float, currency: str = "USD"
    ) -> Optional[Dict[str, Any]]:
        """检查价格变动，返回告警信息 dict"""
        latest = self.db.get_latest_price(product_db_id)
        if not latest:
            self.db.insert_price(PriceRecord(
                product_db_id=product_db_id,
                price=current_price,
                currency=currency,
                recorded_at=now_str(),
            ))
            return None

        old_price = latest.price
        if old_price <= 0:
            return None

        change_pct = ((current_price - old_price) / old_price) * 100

        self.db.insert_price(PriceRecord(
            product_db_id=product_db_id,
            price=current_price,
            currency=currency,
            recorded_at=now_str(),
        ))

        if abs(change_pct) >= PRICE_ALERT_THRESHOLD_PCT:
            product = self.db.get_product_by_id(product_db_id)
            alert = {
                "product_id": product_db_id,
                "title": product.title if product else "Unknown",
                "old_price": old_price,
                "new_price": current_price,
                "change_pct": round(change_pct, 1),
                "direction": "价格上涨" if change_pct > 0 else "价格下跌",
                "time": now_str(),
            }
            logger.warning(
                f"价格异动: {alert['title'][:30]}... "
                f"{alert['direction']} {abs(change_pct):.1f}% "
                f"(${old_price:.2f} → ${current_price:.2f})"
            )
            return alert

        return None

    def check_all_monitored(self, scraper_get_price=None) -> List[Dict[str, Any]]:
        """检查所有活跃的价格监控任务"""
        tasks = self.db.get_active_monitor_tasks(task_type="price")
        alerts = []

        if not tasks:
            logger.info("没有活跃的价格监控任务")
            return alerts

        logger.info(f"开始检查 {len(tasks)} 个价格监控任务...")

        for task in tasks:
            if not task.product_db_id:
                continue

            try:
                if scraper_get_price and task.product_url:
                    current_price = scraper_get_price(task.product_url)
                else:
                    product = self.db.get_product_by_id(task.product_db_id)
                    current_price = product.price if product else 0.0

                if current_price > 0:
                    alert = self.check_price(task.product_db_id, current_price)
                    if alert:
                        alerts.append(alert)
            except Exception as e:
                logger.error(f"检查价格失败 task={task.id}: {e}")

            self.db.update_monitor_last_checked(task.id, now_str())

        logger.info(f"价格检查完成: {len(alerts)} 个异动")
        return alerts

    def get_monitored_products(self) -> List[Product]:
        """获取所有监控中的商品"""
        return self.db.get_products(is_monitor=True)

    def get_price_history_for_chart(self, product_db_id: int, days: int = 30):
        """获取可用于图表的价格历史"""
        records = self.db.get_price_history(product_db_id, days)
        dates = [r.recorded_at[:10] for r in records]
        prices = [r.price for r in records]
        return dates, prices

    def remove_monitor(self, task_id: int) -> None:
        """移除监控任务"""
        task = self.db.get_active_monitor_tasks()
        for t in task:
            if t.id == task_id:
                if t.product_db_id:
                    self.db.set_monitor_status(t.product_db_id, False)
                break
        self.db.delete_monitor_task(task_id)
        logger.info(f"已移除监控任务: {task_id}")
