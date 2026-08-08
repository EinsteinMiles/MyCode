#!/usr/bin/env python3
"""
平台登录助手 — 跨境电商版
打开可见浏览器，引导手动登录，保存 Cookie 供后续使用

用法: python3 login_helper.py [platform]
支持: ebay, amazon, aliexpress, shopee
"""

import sys
import os
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config import logger
from core.browser import BrowserManager

PLATFORM_CONFIG = {
    "ebay": {
        "test_url": "https://www.ebay.com/sch/i.html?_nkw=test",
        "login_indicators": ["signin.ebay.com", "login"],
        "name": "eBay",
    },
    "amazon": {
        "test_url": "https://www.amazon.com/s?k=test",
        "login_indicators": ["ap/signin", "ap-signin"],
        "name": "Amazon",
    },
    "aliexpress": {
        "test_url": "https://www.aliexpress.com/w/wholesale-test.html",
        "login_indicators": ["login.aliexpress.com", "passport.aliexpress.com"],
        "name": "AliExpress",
    },
    "shopee": {
        "test_url": "https://shopee.sg/search?keyword=test",
        "login_indicators": ["shopee.sg/buyer/login", "shopee.sg/account/login"],
        "name": "Shopee",
    },
}


def detect_login_wall(page, config: dict) -> bool:
    """检测是否遇到登录墙"""
    try:
        import json
        result = page.run_js("""
            return JSON.stringify({
                url: location.href,
                title: document.title
            });
        """)
        data = json.loads(result)
        url = data.get("url", "")

        for indicator in config["login_indicators"]:
            if indicator in url.lower():
                return True

        if "robot check" in page.html[:5000].lower():
            return True

        return False
    except Exception:
        return True


def login_platform(platform: str) -> bool:
    """为指定平台打开可见浏览器进行手动登录"""
    config = PLATFORM_CONFIG.get(platform)
    if not config:
        print(f"不支持的平台: {platform}")
        print(f"可选: {', '.join(PLATFORM_CONFIG.keys())}")
        return False

    print(f"\n{'='*60}")
    print(f"  {config['name']} 登录助手")
    print(f"{'='*60}")
    print(f"\n即将打开浏览器窗口...")
    print(f"1. 在浏览器中完成登录（邮箱/密码 或 扫码）")
    print(f"2. 登录后确认能看到搜索结果")
    print(f"3. 回到此处按回车保存 Cookie")
    print(f"\n按回车开始...")
    input()

    browser = BrowserManager()

    try:
        # 先尝试已有 Cookie
        if browser.load_cookies(platform):
            print("已加载保存的 Cookie，测试中...")
            page = browser.get_page(headless=True)
            page.get(config["test_url"])
            time.sleep(4)

            if not detect_login_wall(page, config):
                print("✅ 已保存的 Cookie 仍然有效！无需重新登录。")
                BrowserManager.close()
                return True
            else:
                print("Cookie 已过期，需要重新登录。")
                BrowserManager.close()

        # 打开可见浏览器
        page = browser.get_page(headless=False)
        page.get(config["test_url"])
        time.sleep(3)

        print(f"\n{'='*60}")
        print(f"  请在浏览器中登录 {config['name']}")
        print(f"{'='*60}")
        print(f"提示: 登录后请确认能看到搜索结果")
        print(f"      然后回到此处按回车保存 Cookie")
        input()

        # 验证登录
        if detect_login_wall(page, config):
            print("\n⚠️  仍然看到登录页面，Cookie 可能未保存。")
            retry = input("重试？(y/N): ").strip().lower()
            if retry == "y":
                BrowserManager.close()
                return login_platform(platform)
            return False

        # 保存 Cookie
        browser.save_cookies(platform)
        print(f"\n✅ Cookie 已保存至 cookies/{platform}.json")
        print(f"   后续 {platform} 采集将自动加载这些 Cookie。")
        BrowserManager.close()
        return True

    except KeyboardInterrupt:
        print("\n\n已取消。")
        return False
    except Exception as e:
        print(f"\n❌ 登录错误: {e}")
        return False


def check_all_platforms():
    """检查所有平台的 Cookie 状态"""
    print(f"\n{'='*60}")
    print(f"  平台 Cookie 状态")
    print(f"{'='*60}")

    browser = BrowserManager()
    for platform, config in PLATFORM_CONFIG.items():
        cookie_file = os.path.join(
            os.path.dirname(os.path.abspath(__file__)),
            "cookies", f"{platform}.json"
        )
        has_file = os.path.exists(cookie_file)
        status = ""

        if has_file:
            try:
                page = browser.get_page(headless=True)
                browser.load_cookies(platform)
                page.get(config["test_url"])
                time.sleep(4)
                if not detect_login_wall(page, config):
                    status = "✅ 有效"
                else:
                    status = "⚠️  已过期"
                BrowserManager.close()
            except Exception:
                status = "❓ 未知"
        else:
            status = "❌ 未登录"

        print(f"  {config['name']:12s}  {status}")

    return True


def main():
    if len(sys.argv) > 1:
        platform = sys.argv[1].lower()
        if platform == "check":
            check_all_platforms()
            return
        login_platform(platform)
        return

    # 交互式菜单
    print(f"\n{'='*60}")
    print(f"  跨境电商登录助手")
    print(f"{'='*60}")
    print(f"\n选择要登录的平台:")
    for i, (key, config) in enumerate(PLATFORM_CONFIG.items(), 1):
        cookie_file = os.path.join(
            os.path.dirname(os.path.abspath(__file__)),
            "cookies", f"{key}.json"
        )
        has_cookie = "📁" if os.path.exists(cookie_file) else "  "
        print(f"  {i}. {has_cookie} {config['name']}")
    print(f"  5. 📋 检查所有平台")
    print(f"  0. 退出")

    try:
        choice = input("\n选择: ").strip()
    except (EOFError, KeyboardInterrupt):
        return

    if choice == "0":
        return
    elif choice == "1":
        login_platform("ebay")
    elif choice == "2":
        login_platform("amazon")
    elif choice == "3":
        login_platform("aliexpress")
    elif choice == "4":
        login_platform("shopee")
    elif choice == "5":
        check_all_platforms()
    else:
        print("无效选择")


if __name__ == "__main__":
    main()
