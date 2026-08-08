"""爬虫模块：eBay、Amazon、AliExpress、Shopee 平台爬虫"""

from .base import BaseScraper
from .ebay import EbayScraper
from .amazon import AmazonScraper
from .aliexpress import AliExpressScraper
from .shopee import ShopeeScraper

__all__ = [
    "BaseScraper",
    "EbayScraper",
    "AmazonScraper",
    "AliExpressScraper",
    "ShopeeScraper",
]
