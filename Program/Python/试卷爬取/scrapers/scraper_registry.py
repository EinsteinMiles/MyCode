"""
爬虫注册中心 — 自动发现和管理所有站点爬虫。
"""

import logging
from typing import Optional, Iterator

from core.base_scraper import BaseScraper, PaperLink

logger = logging.getLogger(__name__)

# 所有已注册的爬虫类
_registry: list[type] = []


def register_scraper(cls):
    """装饰器：将爬虫类注册到全局注册表。"""
    _registry.append(cls)
    return cls


def get_all_scrapers(config=None, session_manager=None,
                     rate_limiter=None, download_manager=None) -> list[BaseScraper]:
    """实例化所有已注册的爬虫。"""
    scrapers = []
    for cls in _registry:
        try:
            instance = cls(
                config=config,
                session_manager=session_manager,
                rate_limiter=rate_limiter,
                download_manager=download_manager,
            )
            scrapers.append(instance)
        except Exception as e:
            logger.error(f"初始化 {cls.__name__} 失败: {e}")
    return scrapers


def get_scraper(site_name: str, **kwargs) -> Optional[BaseScraper]:
    """根据站点名获取爬虫实例。"""
    for cls in _registry:
        if cls.site_name == site_name:
            return cls(**kwargs)
    return None


def get_scraper_by_url(url: str, **kwargs) -> Optional[BaseScraper]:
    """根据 URL 匹配爬虫。"""
    for cls in _registry:
        if cls.base_url and cls.base_url in url:
            return cls(**kwargs)
    return None


def list_sites() -> list[dict]:
    """列出所有已注册的站点信息。"""
    result = []
    for cls in _registry:
        result.append({
            "site_name": cls.site_name,
            "base_url": cls.base_url,
            "scraper_type": cls.scraper_type.value,
            "auth_level": cls.auth_level.value,
        })
    return result


def search_all(
    grade: str = None,
    paper_type: str = None,
    keyword: str = None,
    site: str = None,
    max_pages: int = 5,
    scrapers: list = None,
) -> Iterator[PaperLink]:
    """
    在所有（或指定）站点搜索试卷。

    Args:
        grade: 年级筛选
        paper_type: 试卷类型筛选
        keyword: 关键词
        site: 限定站点名
        max_pages: 每个站点最多页数
        scrapers: 预初始化的爬虫列表

    Yields:
        PaperLink 对象
    """
    for scraper in scrapers:
        if site and scraper.site_name != site:
            continue

        logger.info(f"搜索 {scraper.site_name} (auth={scraper.auth_level.value})...")
        try:
            count = 0
            for link in scraper.search_papers(
                grade=grade,
                paper_type=paper_type,
                keyword=keyword,
                max_pages=max_pages,
            ):
                yield link
                count += 1
            logger.info(f"  {scraper.site_name}: 找到 {count} 条结果")
        except NotImplementedError:
            logger.warning(f"  {scraper.site_name}: 尚未实现")
        except Exception as e:
            logger.error(f"  {scraper.site_name}: 搜索出错 - {e}")


# ---- 导入所有爬虫模块，触发注册 ----
# 在文件末尾导入，避免循环依赖
def _import_scrapers():
    """延迟导入所有爬虫模块。"""
    import scrapers.shijuan1      # noqa
    import scrapers.shijuan2      # noqa
    import scrapers._7cxk         # noqa
    import scrapers._51jiaoxi     # noqa
    import scrapers.zxxk          # noqa
    import scrapers._21cnjy       # noqa
    import scrapers.wenku_baidu   # noqa
    import scrapers.jyeoo         # noqa
    import scrapers.zujuan        # noqa
