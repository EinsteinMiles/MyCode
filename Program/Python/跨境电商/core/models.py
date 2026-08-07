"""
数据模型 — 跨境电商版
多平台统一数据模型：eBay / Amazon / AliExpress
"""

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class Product:
    """商品信息（多平台统一模型）"""
    id: Optional[int] = None
    platform: str = ""              # 'ebay' | 'amazon' | 'aliexpress'
    product_id: str = ""            # 平台原生 ID / ASIN / Item ID
    title: str = ""
    price: float = 0.0              # 当前价格
    price_range: str = ""           # 原始价格文本 "$5.00 - $15.00"
    original_price: float = 0.0     # 划线价 / MSRP
    currency: str = "USD"           # USD | EUR | GBP | JPY | ...
    shipping_cost: float = 0.0
    condition: str = ""             # New | Used | Refurbished | Open Box
    sales_count: int = 0
    sales_text: str = ""            # 原始销量文本 "1.2K sold"
    rating: float = 0.0             # 1-5 星评分
    review_count: int = 0
    shop_name: str = ""             # 店铺名 / 卖家名
    seller_rating: float = 0.0      # 卖家反馈评分
    seller_feedback_count: int = 0
    location: str = ""              # 发货地
    category: str = ""
    image_url: str = ""
    url: str = ""
    is_monitor: bool = False
    first_seen: str = ""
    last_updated: str = ""
    extra_json: str = "{}"

    def display_price(self) -> str:
        if self.price_range:
            return self.price_range
        sym = self._currency_symbol()
        return f"{sym}{self.price:.2f}"

    def display_sales(self) -> str:
        if self.sales_text:
            return self.sales_text
        if self.sales_count > 0:
            if self.sales_count >= 10000:
                return f"{self.sales_count/10000:.1f}万"
            elif self.sales_count >= 1000:
                return f"{self.sales_count/1000:.1f}K"
            return f"{self.sales_count}"
        return "-"

    def display_rating(self) -> str:
        if self.rating > 0:
            return f"{self.rating:.1f}★ ({self.review_count})"
        return "-"

    def _currency_symbol(self) -> str:
        symbols = {"USD": "$", "EUR": "€", "GBP": "£", "JPY": "¥", "CAD": "C$", "AUD": "A$"}
        return symbols.get(self.currency, f"{self.currency} ")


@dataclass
class PriceRecord:
    """价格历史快照"""
    id: Optional[int] = None
    product_db_id: int = 0
    price: float = 0.0
    original_price: float = 0.0
    currency: str = "USD"
    recorded_at: str = ""


@dataclass
class Review:
    """商品评论"""
    id: Optional[int] = None
    product_db_id: int = 0
    reviewer_name: str = ""
    rating: int = 0                 # 1-5 星
    title: str = ""                 # 评论标题
    content: str = ""
    verified_purchase: bool = False
    helpful_count: int = 0
    sentiment_score: float = 0.0    # VADER compound (-1 ~ +1)
    sentiment_label: str = ""       # positive / neutral / negative
    review_date: str = ""
    scraped_at: str = ""


@dataclass
class HotRanking:
    """热销排行快照"""
    id: Optional[int] = None
    platform: str = ""
    category: str = ""
    product_db_id: Optional[int] = None
    rank: int = 0
    title: str = ""
    price: float = 0.0
    sales_text: str = ""
    rating: float = 0.0
    snapshot_date: str = ""


@dataclass
class MonitorTask:
    """监控任务配置"""
    id: Optional[int] = None
    task_type: str = ""             # 'price' | 'hot_ranking'
    platform: str = ""
    product_url: str = ""
    product_db_id: Optional[int] = None
    category: str = ""
    keywords: str = ""
    is_active: bool = True
    created_at: str = ""
    last_checked: str = ""


@dataclass
class ExportRecord:
    """导出历史"""
    id: Optional[int] = None
    export_type: str = ""
    file_path: str = ""
    created_at: str = ""
