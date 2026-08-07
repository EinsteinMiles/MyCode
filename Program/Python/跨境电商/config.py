"""
统一配置模块 — 跨境电商版
支持: eBay | Amazon | AliExpress
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
DB_PATH = os.path.join(DATA_DIR, "cross_border.db")

# ── 爬取参数 ──────────────────────────────────────────
RETRY_TIMES = 3
RETRY_DELAY = 2.0
REQUEST_TIMEOUT = 30
PAGE_LOAD_TIMEOUT = 15

MIN_DELAY = 1.0
MAX_DELAY = 3.0
PAGE_DELAY_MIN = 3.0
PAGE_DELAY_MAX = 8.0
REST_EVERY_N = 20
REST_MIN = 30.0
REST_MAX = 120.0

# ── 浏览器参数 ────────────────────────────────────────
HEADLESS = False
WINDOW_WIDTH = 1366
WINDOW_HEIGHT = 768
BROWSER_IDLE_TIMEOUT = 300

# ── 监控参数 ──────────────────────────────────────────
PRICE_CHECK_INTERVAL_HOURS = 6
PRICE_ALERT_THRESHOLD_PCT = 5.0

# ── 评论分析参数 ──────────────────────────────────────
REVIEW_BATCH_SIZE = 50
MAX_REVIEW_PAGES = 10
SENTIMENT_POSITIVE = 0.05    # VADER compound ≥ 0.05 → positive
SENTIMENT_NEGATIVE = -0.05   # VADER compound ≤ -0.05 → negative

# ── 平台 URL ──────────────────────────────────────────
EBAY_SEARCH_URL = "https://www.ebay.com/sch/i.html?_nkw={keyword}"
EBAY_ITEM_URL = "https://www.ebay.com/itm/{item_id}"

AMAZON_SEARCH_URL = "https://www.amazon.com/s?k={keyword}"
AMAZON_ITEM_URL = "https://www.amazon.com/dp/{asin}"

ALIEXPRESS_SEARCH_URL = "https://www.aliexpress.com/w/wholesale-{keyword}.html"
ALIEXPRESS_ITEM_URL = "https://www.aliexpress.com/item/{item_id}.html"

# ── 平台选择器 ─────────────────────────────────────────
EBAY_SELECTORS = {
    "search_item": ".s-item",
    "title": ".s-item__title",
    "price": ".s-item__price",
    "shipping": ".s-item__shipping",
    "condition": ".s-item__subtitle .SECONDARY_INFO",
    "seller": ".s-item__seller-info-text",
    "sold": ".s-item__quantitySold",
    "location": ".s-item__itemLocation",
}

AMAZON_SELECTORS = {
    "search_item": "[data-component-type='s-search-result']",
    "title": "h2 .a-text-normal",
    "price": ".a-price .a-offscreen",
    "rating": ".a-icon-star-small .a-icon-alt",
    "review_count": ".a-size-base.s-underline-text",
    "badge": ".a-badge-text",
}

ALIEXPRESS_SELECTORS = {
    "search_item": ".list--gallery--C2f2tvm [class*='search-item-card']",
    "title": ".multi--titleText--",
    "price": ".multi--price-sale--",
    "original_price": ".multi--price-original--",
    "orders": ".multi--trade--",
    "rating": ".multi--rating--",
    "store": ".multi--storeName--",
}

# ── 日志 ──────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("crossborder")
