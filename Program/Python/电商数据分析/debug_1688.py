#!/usr/bin/env python3
"""
1688 抓取诊断脚本（更新版）
- 先检查登录状态
- 如果未登录，引导使用 login_helper
- 如果已登录，测试搜索和提取

用法: python3 debug_1688.py
"""

import sys
import os
import time
import json

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config import logger, COOKIE_DIR
from core.browser import BrowserManager
from scrapers.alibaba1688 import Alibaba1688Scraper


def main():
    keyword = input("搜索关键词 (回车=蓝牙耳机): ").strip() or "蓝牙耳机"

    # 检查 Cookie 状态
    cookie_file = os.path.join(COOKIE_DIR, "1688.json")
    has_cookies = os.path.exists(cookie_file)

    print(f"\n{'='*60}")
    print(f"  1688 爬虫诊断 — 搜索「{keyword}」")
    print(f"{'='*60}")
    print(f"\n  Cookie 状态: {'✅ 已有' if has_cookies else '❌ 未登录'}")

    if not has_cookies:
        print(f"\n  ⚠️  1688 搜索需要登录！")
        print(f"  请先运行: python3 login_helper.py 1688")
        retry = input(f"\n  是否现在启动登录助手? (Y/n): ").strip().lower()
        if retry != "n":
            from login_helper import login_platform
            login_platform("1688")
            # 检查是否登录成功
            if not os.path.exists(cookie_file):
                print("登录未完成，退出。")
                return
        else:
            print("跳过登录，尝试未登录状态抓取...")

    browser = None
    try:
        # 创建爬虫
        browser = BrowserManager()
        scraper = Alibaba1688Scraper(browser)

        print(f"\n[1] 开始搜索...")
        products = scraper.search_products(keyword, max_pages=2)

        if not products:
            print(f"\n  ❌ 未提取到商品。可能原因：")
            print(f"     1. Cookie 已过期 — 重新运行 login_helper.py 1688")
            print(f"     2. 页面结构变化 — 检查截图 output/debug_1688_pg1.png")
            print(f"     3. 被反爬限制 — 等待后重试")
            return

        print(f"\n[2] 提取到 {len(products)} 个商品:")
        for i, p in enumerate(products[:15]):
            print(f"  {i+1:2d}. {p.title[:55]:55s} {p.display_price():>10s} | {p.display_sales():>8s} | {p.shop_name[:15]}")

        if len(products) > 15:
            print(f"  ... 共 {len(products)} 个")

        # 检查数据质量
        good_titles = sum(1 for p in products if len(p.title) > 8 and "找相似" not in p.title)
        good_prices = sum(1 for p in products if p.price > 0.5 and p.price < 99999)
        good_shops = sum(1 for p in products if p.shop_name and len(p.shop_name) > 2)

        print(f"\n[3] 数据质量:")
        print(f"  标题正常: {good_titles}/{len(products)} ({good_titles*100//len(products)}%)")
        print(f"  价格正常: {good_prices}/{len(products)} ({good_prices*100//len(products)}%)")
        print(f"  店铺正常: {good_shops}/{len(products)} ({good_shops*100//len(products)}%)")

        if good_titles == 0 or good_prices == 0:
            print(f"\n  ⚠️  数据质量差，需要调整提取逻辑")
            print(f"  检查截图: output/debug_1688_pg1.png")

        print(f"\n诊断完成。")
    finally:
        if browser:
            browser.close()


if __name__ == "__main__":
    main()
