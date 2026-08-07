"""
统一配置模块
参考 财报分析/config.py 的配置即模块常量模式
"""

import os
import logging

# ── 路径常量 ──────────────────────────────────────────
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")
OUTPUT_DIR = os.path.join(BASE_DIR, "output")
CHART_DIR = os.path.join(OUTPUT_DIR, "charts")
HTML_DIR = os.path.join(OUTPUT_DIR, "html")
PDF_DIR = os.path.join(OUTPUT_DIR, "pdf")
CSV_DIR = os.path.join(OUTPUT_DIR, "csv")
COOKIE_DIR = os.path.join(BASE_DIR, "cookies")
TEMPLATE_DIR = os.path.join(BASE_DIR, "templates")

for _d in [DATA_DIR, OUTPUT_DIR, CHART_DIR, HTML_DIR, PDF_DIR, CSV_DIR, COOKIE_DIR]:
    os.makedirs(_d, exist_ok=True)

# ── 数据库 ────────────────────────────────────────────
DB_PATH = os.path.join(DATA_DIR, "ecommerce.db")

# ── 爬取参数 ──────────────────────────────────────────
RETRY_TIMES = 3
RETRY_DELAY = 2.0          # 基础重试间隔(秒)
REQUEST_TIMEOUT = 30       # 页面加载超时(秒)
PAGE_LOAD_TIMEOUT = 15     # 元素等待超时(秒)

# 随机延迟范围 (高斯分布, 避免规律性)
MIN_DELAY = 1.0
MAX_DELAY = 3.0
# 翻页间隔更长
PAGE_DELAY_MIN = 3.0
PAGE_DELAY_MAX = 8.0
# 长休息: 每 N 次请求后休息
REST_EVERY_N = 20
REST_MIN = 30.0
REST_MAX = 120.0

# ── 浏览器参数 ────────────────────────────────────────
HEADLESS = False           # 开发阶段有头模式，方便调试
WINDOW_WIDTH = 1366
WINDOW_HEIGHT = 768
BROWSER_IDLE_TIMEOUT = 300  # 5分钟空闲自动关闭

# ── 监控参数 ──────────────────────────────────────────
PRICE_CHECK_INTERVAL_HOURS = 6
PRICE_ALERT_THRESHOLD_PCT = 5.0   # 价格变动 >5% 告警

# ── 评论分析参数 ──────────────────────────────────────
REVIEW_BATCH_SIZE = 50
MAX_REVIEW_PAGES = 10
# 情感分类阈值
SENTIMENT_POSITIVE = 0.6
SENTIMENT_NEGATIVE = 0.4

# ── 平台 URL ──────────────────────────────────────────
TAOBAO_SEARCH_URL = "https://s.taobao.com/search?q={keyword}"
TAOBAO_ITEM_URL = "https://item.taobao.com/item.htm?id={item_id}"

PINDUODUO_SEARCH_URL = "https://mobile.yangkeduo.com/search_result.html?search_key={keyword}"

ALIBABA_SEARCH_URL = "https://s.1688.com/selloffer/offer_search.htm?keywords={keyword}"
ALIBABA_ITEM_URL = "https://detail.1688.com/offer/{offer_id}.html"

# ── 平台选择器（按需维护，应对页面结构变化）────────────
TAOBAO_SELECTORS = {
    "search_item": "[class*='item']",
    "title": "[class*='title']",
    "price": "[class*='price']",
    "sales": "[class*='deal-cnt']",
    "shop": "[class*='shop']",
}

ALIBABA_SELECTORS = {
    "search_item": ".offer-list-item",
    "title": ".offer-title",
    "price": ".offer-price",
    "trade_count": ".offer-trade",
    "shop_name": ".offer-company",
    "location": ".offer-address",
}

PINDUODUO_SELECTORS = {
    "search_item": ".goods-item",
    "title": ".goods-title",
    "price": ".goods-price",
    "sales": ".goods-sales",
}

# ── 日志 ──────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("ecommerce")
