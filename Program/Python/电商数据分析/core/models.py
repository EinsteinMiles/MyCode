"""
数据模型
参考 物理题库系统/models.py 的 dataclass + Optional ID 模式
"""

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class Product:
    """商品信息（多平台统一模型）"""
    id: Optional[int] = None
    platform: str = ""           # 'taobao' | 'pinduoduo' | '1688'
    product_id: str = ""          # 平台原生 ID
    title: str = ""
    price: float = 0.0            # 当前价格（取最低 SKU 或区间下限）
    price_range: str = ""         # 原始价格区间文本 "¥5.00-¥15.00"
    original_price: float = 0.0   # 划线价
    sales_count: int = 0
    sales_text: str = ""          # 原始销量文本 "1.2万+"
    shop_name: str = ""
    location: str = ""            # 发货地
    category: str = ""
    image_url: str = ""
    url: str = ""
    moq: int = 0                  # 起批量 (1688)
    is_monitor: bool = False      # 是否加入价格监控
    first_seen: str = ""
    last_updated: str = ""
    extra_json: str = "{}"        # 平台特有字段 JSON

    def display_price(self) -> str:
        if self.price_range:
            return self.price_range
        return f"¥{self.price:.2f}"

    # 合理的单商品销量上限（超过此值视为脏数据）
    MAX_REASONABLE_SALES = 50_000_000

    def display_sales(self) -> str:
        # 如果 sales_text 是有效的销量文本就使用它
        if self.sales_text and self._is_valid_sales_text(self.sales_text):
            return self.sales_text
        if 0 < self.sales_count <= self.MAX_REASONABLE_SALES:
            if self.sales_count >= 10000:
                return f"{self.sales_count/10000:.1f}万+"
            return str(self.sales_count)
        return "-"

    @staticmethod
    def _is_valid_sales_text(text: str) -> bool:
        """检查 sales_text 是否真的像销量数据（而非服务评分等垃圾文本）"""
        import re
        if len(text) > 25:
            return False
        for garbage in ["采购咨询", "退换体验", "品质体验", "纠纷解决", "综合服务", "验厂报告", "找相似"]:
            if garbage in text:
                return False
        return bool(re.search(r"成交|已售|销量|月销|笔|件|单|\+|万|\d", text))


@dataclass
class PriceRecord:
    """价格历史快照"""
    id: Optional[int] = None
    product_db_id: int = 0
    price: float = 0.0
    original_price: float = 0.0
    recorded_at: str = ""


@dataclass
class Review:
    """商品评论"""
    id: Optional[int] = None
    product_db_id: int = 0
    reviewer_name: str = ""
    rating: int = 0              # 1-5 星
    content: str = ""
    sentiment_score: float = 0.0  # 0-1, SnowNLP 输出
    sentiment_label: str = ""     # positive / neutral / negative
    review_date: str = ""
    scraped_at: str = ""


@dataclass
class HotRanking:
    """热销排行快照"""
    id: Optional[int] = None
    platform: str = ""
    category: str = ""           # 品类关键词
    product_db_id: Optional[int] = None
    rank: int = 0
    title: str = ""
    price: float = 0.0
    sales_text: str = ""
    snapshot_date: str = ""


@dataclass
class MonitorTask:
    """监控任务配置"""
    id: Optional[int] = None
    task_type: str = ""          # 'price' | 'hot_ranking'
    platform: str = ""
    product_url: str = ""
    product_db_id: Optional[int] = None
    category: str = ""           # 热销追踪的品类关键词
    keywords: str = ""           # 逗号分隔搜索词
    is_active: bool = True
    created_at: str = ""
    last_checked: str = ""


@dataclass
class ExportRecord:
    """导出历史"""
    id: Optional[int] = None
    export_type: str = ""        # 'csv' | 'excel' | 'html' | 'pdf'
    file_path: str = ""
    created_at: str = ""
