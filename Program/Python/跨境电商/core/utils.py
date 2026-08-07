"""
工具函数 — 跨境电商版
Multi-currency price parsing, English sales parsing, UA pool
"""

import re
import time
import random
import functools
from typing import Any, Callable, Optional

from config import (
    RETRY_TIMES, RETRY_DELAY,
    MIN_DELAY, MAX_DELAY,
    PAGE_DELAY_MIN, PAGE_DELAY_MAX,
    logger,
)


def random_delay(min_s: float = MIN_DELAY, max_s: float = MAX_DELAY) -> None:
    """随机延迟（均匀分布），模拟人类浏览行为"""
    delay = random.uniform(min_s, max_s)
    time.sleep(delay)


def gaussian_delay(mean: float = 2.0, std: float = 0.5) -> None:
    """高斯分布随机延迟"""
    delay = max(0.3, random.gauss(mean, std))
    time.sleep(delay)


def page_delay() -> None:
    """翻页间隔"""
    random_delay(PAGE_DELAY_MIN, PAGE_DELAY_MAX)


def parse_price(text: str) -> float:
    """
    解析多币种价格文本 → float
    支持: "$19.90", "US $29.99", "EUR 29,99", "£15.00",
          "$19.99 to $39.99" → 19.99, "1,299.00"
    """
    if not text or not isinstance(text, str):
        return 0.0

    text = text.strip()

    # 区间价格取低值
    if " to " in text.lower():
        text = text.split(" to ")[0].strip()

    # 去掉币种前缀/后缀
    text = re.sub(
        r'(?:US\s*\$|USD\s*|EUR\s*|GBP\s*|£|€|AU\s*\$|CA\s*\$|CDN\s*\$|A\s*\$|JPY\s*|¥|￥|R\$\s*)',
        '', text, flags=re.IGNORECASE
    )

    # 德语/法语数字格式: 29,99 → 29.99（但 1,299.00 保持不变）
    if re.match(r'^\d{1,2},\d{2}$', text):
        text = text.replace(',', '.')
    else:
        text = text.replace(',', '')

    text = text.strip()

    num = re.sub(r'[^\d.]', '', text)
    try:
        return float(num) if num else 0.0
    except ValueError:
        return 0.0


def parse_currency(text: str) -> str:
    """从价格文本中提取币种"""
    if not text:
        return "USD"
    text_upper = text.upper()
    if "EUR" in text_upper or "€" in text:
        return "EUR"
    if "GBP" in text_upper or "£" in text:
        return "GBP"
    if "CNY" in text_upper or "RMB" in text_upper or "元" in text:
        return "CNY"
    if "JPY" in text_upper or "¥" in text:
        return "JPY"
    if "CAD" in text_upper or "CDN" in text_upper or "CA$" in text:
        return "CAD"
    if "AUD" in text_upper or "AU$" in text or "A$" in text:
        return "AUD"
    if "$" in text or "USD" in text_upper:
        return "USD"
    return "USD"


def parse_sales(text: str) -> int:
    """
    解析销量文本 → int (supports English + Chinese)
    支持: "1.2K sold", "10K+ sold", "1,234 sold", "Over 500 sold",
          "12 sold", "500+", "已售出 32 件", "已售 1.2万+"
    """
    if not text or not isinstance(text, str):
        return 0

    text = text.strip()

    # 中文模式 (before stripping non-ASCII)
    cn_patterns = [
        r'已售(?:出)?\s*(\d+(?:,\d{3})*(?:\.\d+)?)\s*[万Ww]?\s*\+?\s*[件个]?',  # 已售出 32 件, 已售 1.2万+
        r'已售(?:出)?\s*(\d+(?:,\d{3})*(?:\.\d+)?)\s*[Kk]\s*\+?\s*[件个]?',   # 已售出 1.2K 件
        r'(\d+(?:,\d{3})*(?:\.\d+)?)\s*[万Ww]\s*\+?\s*[件个]?\s*(?:已售)?',   # 1.2万 件已售
        r'(\d+(?:,\d{3})*(?:\.\d+)?)\s*\+?\s*[件个]\s*(?:已售)?',            # 32 件已售
    ]
    for pat in cn_patterns:
        m = re.search(pat, text)
        if m:
            num_str = m.group(1).replace(',', '')
            try:
                val = float(num_str)
            except ValueError:
                continue
            if re.search(r'[万Ww]', text):
                val *= 10000
            if re.search(r'[Kk]', text):
                val *= 1000
            return int(val)

    # English patterns
    patterns = [
        r'(\d+(?:,\d{3})*(?:\.\d+)?)\s*[Kk]\s*\+?\s*sold',   # 1.2K sold
        r'(\d+(?:,\d{3})*(?:\.\d+)?)\s*[Kk]\s*\+?',           # 10K+
        r'([\d,]+)\s*\+?\s*sold',                               # 1,234 sold
        r'Over\s+([\d,]+)',                                     # Over 500
        r'([\d,]+)\s*\+',                                       # 500+
        r'Sold\s+([\d,]+)',                                     # Sold 123
        r'(\d+(?:,\d{3})*(?:\.\d+)?)\s*orders',                # 1.5K orders (AliExpress)
    ]

    for pat in patterns:
        m = re.search(pat, text, re.IGNORECASE)
        if m:
            num_str = m.group(1).replace(',', '')
            try:
                val = float(num_str)
            except ValueError:
                continue

            # K 后缀检测
            if re.search(r'[Kk]', text):
                val *= 1000
            # M 后缀
            if re.search(r'[Mm]', text):
                val *= 1_000_000

            return int(val)

    return 0


def parse_rating(text: str) -> float:
    """解析评分文本 → float，如 "4.5 out of 5 stars" → 4.5"""
    if not text:
        return 0.0
    m = re.search(r'(\d+(?:\.\d+)?)', text)
    if m:
        val = float(m.group(1))
        return val if val <= 5 else val / 20  # 100分制转5分制
    return 0.0


def retry_call(
    func: Callable, *args: Any,
    max_retries: int = RETRY_TIMES,
    delay: float = RETRY_DELAY,
    **kwargs: Any,
) -> Optional[Any]:
    """带指数退避的重试调用"""
    for attempt in range(max_retries + 1):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            if attempt < max_retries:
                wait = delay * (attempt + 1)
                logger.warning(
                    f"Retry {attempt + 1}/{max_retries}: {func.__name__} failed ({e}), "
                    f"waiting {wait:.1f}s"
                )
                time.sleep(wait)
            else:
                logger.error(f"Retries exhausted: {func.__name__} failed: {e}")
                return None


def retry(max_retries: int = RETRY_TIMES, delay: float = RETRY_DELAY):
    """retry_call 的装饰器版本"""
    def decorator(func: Callable):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            return retry_call(func, *args, max_retries=max_retries, delay=delay, **kwargs)
        return wrapper
    return decorator


def clean_text(text: str) -> str:
    """清洗文本：去除 HTML 标签、多余空白、控制字符"""
    if not text:
        return ""
    text = re.sub(r'<[^>]+>', '', text)
    text = re.sub(r'\s+', ' ', text)
    text = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]', '', text)
    return text.strip()


def sanitize_filename(name: str) -> str:
    """生成安全的文件名"""
    name = re.sub(r'[\\/:*?"<>|]', '_', name)
    return name[:100]


def now_str() -> str:
    """当前时间字符串"""
    return time.strftime("%Y-%m-%d %H:%M:%S")


# ── UA 池 (English / International) ────────────────────
_USER_AGENTS = [
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/129.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:133.0) Gecko/20100101 Firefox/133.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:132.0) Gecko/20100101 Firefox/132.0",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:133.0) Gecko/20100101 Firefox/133.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.1 Safari/605.1.15",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36 Edg/131.0.0.0",
]


def random_ua() -> str:
    """随机返回一个 User-Agent"""
    return random.choice(_USER_AGENTS)
