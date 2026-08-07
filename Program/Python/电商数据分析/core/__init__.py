"""核心基础设施：浏览器管理、数据库、数据模型、工具函数"""

from .storage import Database
from .models import Product, PriceRecord, Review, HotRanking, MonitorTask
from .utils import random_delay, parse_price, parse_sales, retry_call


def get_browser_manager():
    """延迟导入 BrowserManager（避免未安装 DrissionPage 时导入失败）"""
    from .browser import BrowserManager
    return BrowserManager


__all__ = [
    "Database",
    "Product",
    "PriceRecord",
    "Review",
    "HotRanking",
    "MonitorTask",
    "random_delay",
    "parse_price",
    "parse_sales",
    "retry_call",
    "get_browser_manager",
]
