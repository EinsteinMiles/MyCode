"""爬虫模块：淘宝、拼多多、1688 平台爬虫"""

from .base import BaseScraper
from .alibaba1688 import Alibaba1688Scraper
from .taobao import TaobaoScraper
from .pinduoduo import PinduoduoScraper

__all__ = [
    "BaseScraper",
    "Alibaba1688Scraper",
    "TaobaoScraper",
    "PinduoduoScraper",
]
