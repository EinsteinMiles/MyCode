#!/usr/bin/env python3
"""
平台登录助手
打开可见浏览器窗口，引导用户手动登录，保存 Cookie 供后续使用

用法：python3 login_helper.py [平台名]
支持: 1688, taobao, pinduoduo
"""

import sys
import os
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config import logger
from core.browser import BrowserManager

# 各平台需要登录才能访问的目标页面
PLATFORM_CONFIG = {
    "1688": {
        "test_url": "https://s.1688.com/selloffer/offer_search.htm?keywords=测试",
        "login_indicators": ["login.taobao.com", "login.1688.com"],
        "success_title": ["蓝牙耳机", "批发", "供应商"],
        "name": "1688 阿里巴巴",
    },
    "taobao": {
        "test_url": "https://s.taobao.com/search?q=测试",
        "login_indicators": ["login.taobao.com"],
        "success_title": ["淘宝网"],
        "name": "淘宝",
    },
    "pinduoduo": {
        "test_url": "https://mobile.yangkeduo.com/search_result.html?search_key=测试",
        "login_indicators": ["login"],
        "success_title": ["拼多多"],
        "name": "拼多多",
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
        title = data.get("title", "")

        # 检查 URL 是否包含登录相关域名
        for indicator in config["login_indicators"]:
            if indicator in url:
                return True

        # 检查是否在错误页面
        if "请登录" in title or "error" in url.lower():
            return True

        return False
    except Exception:
        return True  # 出错时保守地认为需要登录


def login_platform(platform: str) -> bool:
    """
    为指定平台打开可见浏览器进行手动登录
    返回 True 如果成功保存了 Cookie
    """
    config = PLATFORM_CONFIG.get(platform)
    if not config:
        print(f"不支持的平台: {platform}")
        print(f"可选: {', '.join(PLATFORM_CONFIG.keys())}")
        return False

    print(f"\n{'='*60}")
    print(f"  {config['name']} 登录助手")
    print(f"{'='*60}")
    print(f"\n即将打开浏览器窗口...")
    print(f"1. 在浏览器中完成手动登录（扫码或账号密码）")
    print(f"2. 登录成功后，确认页面显示搜索结果")
    print(f"3. 回到此窗口按回车保存 Cookie")
    print(f"\n按回车开始...")
    input()

    browser = BrowserManager()

    try:
        # 先尝试加载已有 Cookie
        if browser.load_cookies(platform):
            print("已加载历史 Cookie，尝试直接访问...")
            page = browser.get_page(headless=True)
            page.get(config["test_url"])
            time.sleep(4)

            if not detect_login_wall(page, config):
                print("✅ 已有 Cookie 仍然有效！无需重新登录。")
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
        print(f"  请在浏览器窗口中完成 {config['name']} 登录")
        print(f"{'='*60}")
        print(f"提示：登录成功后确认是否能看到搜索结果/商品列表")
        print(f"      然后回到此窗口按回车保存 Cookie")
        input()

        # 验证登录状态
        if detect_login_wall(page, config):
            print("\n⚠️  仍检测到登录页面，Cookie 可能未生效。")
            retry = input("是否重试？(y/N): ").strip().lower()
            if retry == "y":
                BrowserManager.close()
                return login_platform(platform)
            return False

        # 保存 Cookie
        browser.save_cookies(platform)
        print(f"\n✅ Cookie 已保存到 cookies/{platform}.json")
        print(f"   后续使用 {platform} 爬虫时将自动加载。")
        BrowserManager.close()
        return True

    except KeyboardInterrupt:
        print("\n\n已取消。")
        return False
    except Exception as e:
        print(f"\n❌ 登录过程出错: {e}")
        return False


def check_all_platforms():
    """检查所有平台的 Cookie 状态"""
    print(f"\n{'='*60}")
    print(f"  平台 Cookie 状态检查")
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
            # 检查是否有效
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
                status = "❓ 无法验证"
        else:
            status = "❌ 未登录"

        print(f"  {config['name']:8s}  {status}")

    return True


def main():
    if len(sys.argv) > 1:
        platform = sys.argv[1].lower()
        if platform == "check":
            check_all_platforms()
            return
        login_platform(platform)
        return

    # 交互菜单
    print(f"\n{'='*60}")
    print(f"  电商平台登录助手")
    print(f"{'='*60}")
    print(f"\n请选择要登录的平台：")
    for i, (key, config) in enumerate(PLATFORM_CONFIG.items(), 1):
        cookie_file = os.path.join(
            os.path.dirname(os.path.abspath(__file__)),
            "cookies", f"{key}.json"
        )
        has_cookie = "📁" if os.path.exists(cookie_file) else "  "
        print(f"  {i}. {has_cookie} {config['name']}")
    print(f"  4. 📋 检查所有平台状态")
    print(f"  0. 退出")

    try:
        choice = input("\n选择: ").strip()
    except (EOFError, KeyboardInterrupt):
        return

    if choice == "0":
        return
    elif choice == "1":
        login_platform("1688")
    elif choice == "2":
        login_platform("taobao")
    elif choice == "3":
        login_platform("pinduoduo")
    elif choice == "4":
        check_all_platforms()
    else:
        print("无效选择")


if __name__ == "__main__":
    main()
