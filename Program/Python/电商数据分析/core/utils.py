"""
工具函数
参考 财报分析/scraper/fetcher.py 的 _retry_call 和 _parse_value
"""

import re
import time
import random
import functools
from typing import Any, Callable, Optional

from config import (
    RETRY_TIMES,
    RETRY_DELAY,
    MIN_DELAY,
    MAX_DELAY,
    PAGE_DELAY_MIN,
    PAGE_DELAY_MAX,
    logger,
)


def random_delay(min_s: float = MIN_DELAY, max_s: float = MAX_DELAY) -> None:
    """随机延迟（均匀分布），模拟人类浏览行为"""
    delay = random.uniform(min_s, max_s)
    time.sleep(delay)


def gaussian_delay(mean: float = 2.0, std: float = 0.5) -> None:
    """高斯分布随机延迟，比均匀分布更自然"""
    delay = max(0.3, random.gauss(mean, std))
    time.sleep(delay)


def page_delay() -> None:
    """翻页间隔（比普通延迟更长）"""
    random_delay(PAGE_DELAY_MIN, PAGE_DELAY_MAX)


def parse_price(text: str) -> float:
    """
    解析价格文本 → float
    支持: "¥ 19.90", "19.9-39.9" → 19.9, "￥299.00", "1.9万" → 19000.0
    参考 财报分析/scraper/fetcher.py::_parse_value
    """
    if not text or not isinstance(text, str):
        return 0.0

    text = text.strip().replace("¥", "").replace("￥", "").replace(",", "").replace(" ", "")

    # 区间价格取低值
    if "-" in text:
        text = text.split("-")[0]

    # 中文单位
    if "万" in text:
        num = re.sub(r"[^\d.]", "", text.replace("万", ""))
        try:
            return float(num) * 10000
        except ValueError:
            return 0.0

    # 纯数字
    num = re.sub(r"[^\d.]", "", text)
    try:
        return float(num) if num else 0.0
    except ValueError:
        return 0.0


def parse_sales(text: str) -> int:
    """
    解析销量文本 → int
    支持: "1.2万+", "已售10万+", "1000+", "5000笔", "成交 2.3万笔"

    返回 0 如果：
    - 文本不包含销量特征关键字
    - 解析结果超过合理上限（单商品 5000 万已是极端情况）
    """
    if not text or not isinstance(text, str):
        return 0

    # 前置校验：必须包含销量特征（纯数字文本 + 关键字）
    has_keyword = bool(re.search(r"成交|已售|销量|月销|笔|件|单|\+|万", text))
    is_plain_number = bool(re.fullmatch(r"\d+", text.strip()))
    if not has_keyword and not is_plain_number:
        return 0

    # 长度限制：正常销量文本很短
    if len(text) > 25 and not is_plain_number:
        return 0

    # 排除服务评分等垃圾文本
    for garbage in ["采购咨询", "退换体验", "品质体验", "纠纷解决", "综合服务", "验厂报告", "找相似"]:
        if garbage in text:
            return 0

    text = (
        text.strip()
        .replace(",", "")
        .replace(" ", "")
        .replace("已售", "")
        .replace("成交", "")
        .replace("笔", "")
        .replace("件", "")
        .rstrip("+")
    )

    if "万" in text:
        num = re.sub(r"[^\d.]", "", text.replace("万", ""))
        try:
            result = int(float(num) * 10000)
        except ValueError:
            return 0
    else:
        num = re.sub(r"[^\d]", "", text)
        try:
            result = int(num) if num else 0
        except ValueError:
            return 0

    # 合理性检验：单商品销量超过 5000 万视为异常
    MAX_REASONABLE_SALES = 50_000_000
    if result > MAX_REASONABLE_SALES:
        return 0

    return result


def retry_call(
    func: Callable,
    *args: Any,
    max_retries: int = RETRY_TIMES,
    delay: float = RETRY_DELAY,
    **kwargs: Any,
) -> Optional[Any]:
    """
    带指数退避的重试调用
    参考 财报分析/scraper/fetcher.py::_retry_call
    """
    for attempt in range(max_retries + 1):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            if attempt < max_retries:
                wait = delay * (attempt + 1)
                logger.warning(
                    f"重试 {attempt + 1}/{max_retries}: {func.__name__} 失败 ({e}), "
                    f"等待 {wait:.1f}s"
                )
                time.sleep(wait)
            else:
                logger.error(f"重试耗尽: {func.__name__} 最终失败: {e}")
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
    """清洗文本：去除多余空白、换行、控制字符"""
    if not text:
        return ""
    # 去 HTML 标签
    text = re.sub(r"<[^>]+>", "", text)
    # 合并空白
    text = re.sub(r"\s+", " ", text)
    # 去控制字符(保留换行为空格)
    text = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]", "", text)
    return text.strip()


def sanitize_filename(name: str) -> str:
    """生成安全的文件名"""
    name = re.sub(r'[\\/:*?"<>|]', "_", name)
    return name[:100]  # 限制长度


def now_str() -> str:
    """当前时间字符串"""
    return time.strftime("%Y-%m-%d %H:%M:%S")


# ── UA 池 ─────────────────────────────────────────────
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
]


def random_ua() -> str:
    """随机返回一个 User-Agent"""
    return random.choice(_USER_AGENTS)
