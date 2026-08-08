#!/usr/bin/env python3
"""
高中物理试卷爬取工具 — 交互式选项菜单

Usage:
    python main.py        # 交互式菜单模式
"""

import logging
import os
import subprocess
import sys
from pathlib import Path

# 确保项目根目录在 Python 路径中
sys.path.insert(0, str(Path(__file__).parent))

from core.session_manager import SessionManager
from core.rate_limiter import RateLimiter
from core.download_manager import DownloadManager
from storage.database import DownloadDatabase
from scrapers.scraper_registry import (
    _import_scrapers, get_all_scrapers, list_sites, search_all
)

logging.basicConfig(
    level=logging.WARNING,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("main")


# ──────────────────────────── 配置 ────────────────────────────

def load_config():
    config_path = Path(__file__).parent / "config.yaml"
    if config_path.exists():
        try:
            import yaml
            with open(config_path, "r", encoding="utf-8") as f:
                return yaml.safe_load(f)
        except ImportError:
            pass
        except Exception as e:
            logger.warning(f"加载 config.yaml 失败: {e}")
    return {}


class ConfigWrapper:
    def __init__(self, data: dict):
        self._data = data

    def get(self, key, default=None):
        return self._data.get(key, default)

    def __getitem__(self, key):
        return self._data[key]


# ──────────────────────────── 菜单 UI ────────────────────────────

SEP = "─" * 56
HEADER = f"""
╔══════════════════════════════════════════════════════╗
║        📝 高中物理试卷爬取工具                        ║
╚══════════════════════════════════════════════════════╝"""

GRADES = ["高一", "高二", "高三"]
PAPER_TYPES = ["期中考试", "期末考试", "月考试卷", "高考模拟", "高考真题", "专项练习", "同步练习"]


def clear_screen():
    subprocess.call("cls" if os.name == "nt" else "clear", shell=True)


def print_header():
    print(HEADER)


def press_enter():
    input("\n按 Enter 返回主菜单...")


# ──────────────────────────── 核心功能 ────────────────────────────

class AppState:
    """全局应用状态，在菜单间传递。"""

    def __init__(self):
        raw = load_config()
        self.config = ConfigWrapper(raw)
        self.session_mgr = SessionManager(self.config)
        self.rate_limiter = RateLimiter(self.config)
        self.db = DownloadDatabase()
        self.dl_mgr = DownloadManager(self.config, self.db)
        self._scrapers_loaded = False

    def load_scrapers(self):
        if not self._scrapers_loaded:
            _import_scrapers()
            self._scrapers_loaded = True

    @property
    def scrapers(self):
        self.load_scrapers()
        return get_all_scrapers(
            config=self.config,
            session_manager=self.session_mgr,
            rate_limiter=self.rate_limiter,
            download_manager=self.dl_mgr,
        )

    def close(self):
        self.db.close()
        self.session_mgr.close_all()


# ──────────────────────────── 菜单实现 ────────────────────────────

def menu_search(state: AppState):
    """搜索试卷 — 逐步选项引导。"""
    state.load_scrapers()
    print_header()
    print("\n  🔍 搜索试卷")
    print(f"  {SEP}")

    # 1. 选择年级
    print("\n  选择年级：")
    print("    [1] 高一")
    print("    [2] 高二")
    print("    [3] 高三")
    print("    [4] 全部年级")
    choice = input("\n  请输入选项 (1-4): ").strip()
    grade_map = {"1": "高一", "2": "高二", "3": "高三", "4": None}
    grade = grade_map.get(choice)
    if choice not in grade_map:
        print("  ❌ 无效选项，已取消")
        press_enter()
        return

    # 2. 选择试卷类型
    print(f"\n  {SEP}")
    print("\n  选择试卷类型：")
    for i, pt in enumerate(PAPER_TYPES, 1):
        print(f"    [{i}] {pt}")
    print(f"    [8] 全部类型")
    choice = input("\n  请输入选项 (1-8): ").strip()
    paper_type = PAPER_TYPES[int(choice) - 1] if choice.isdigit() and 1 <= int(choice) <= 7 else None
    if choice.isdigit() and int(choice) == 8:
        paper_type = None
    elif not paper_type:
        print("  ❌ 无效选项，已取消")
        press_enter()
        return

    # 3. 选择站点（多选）
    sites = list_sites()
    print(f"\n  {SEP}")
    print("\n  选择站点（可输入空格分隔的数字多选，a=全部, Enter=全部）:")
    auth_icon = {"none": "✅", "login": "⚠️", "vip": "❌", "walled": "🛡️"}
    for i, s in enumerate(sites, 1):
        icon = auth_icon.get(s["auth_level"], "  ")
        print(f"    [{i}] {icon} {s['site_name']:<12} {s['base_url']}")

    choice = input("\n  请输入: ").strip().lower()
    selected_sites = []
    if not choice or choice == "a":
        selected_sites = [s["site_name"] for s in sites]
    else:
        try:
            indices = [int(x) for x in choice.split() if x.isdigit()]
            for idx in indices:
                if 1 <= idx <= len(sites):
                    selected_sites.append(sites[idx - 1]["site_name"])
        except ValueError:
            print("  ❌ 无效选项，已取消")
            press_enter()
            return

    if not selected_sites:
        print("  ❌ 未选择任何站点")
        press_enter()
        return

    # 4. 关键词（可选）
    print(f"\n  {SEP}")
    keyword = input("\n  搜索关键词（可留空直接回车）: ").strip() or None

    # 5. 最大搜索页数
    max_pages_str = input("  每个站点搜索页数 (默认5): ").strip()
    max_pages = int(max_pages_str) if max_pages_str.isdigit() else 5

    # 6. 是否自动下载
    print(f"\n  {SEP}")
    print("\n  找到结果后是否自动下载？")
    print("    [1] 只搜索，不下载")
    print("    [2] 搜索并自动下载")
    auto_dl = input("\n  请输入 (1/2, 默认1): ").strip() == "2"

    # ──────── 执行搜索 ────────
    clear_screen()
    print_header()
    print(f"\n  🔍 搜索中...")
    print(f"  {SEP}")
    print(f"  年级: {grade or '全部'}")
    print(f"  类型: {paper_type or '全部'}")
    if keyword:
        print(f"  关键词: {keyword}")
    site_names = ", ".join(selected_sites)
    print(f"  站点: {site_names} (每站 {max_pages} 页)")
    print(f"  自动下载: {'是' if auto_dl else '否'}")
    print(f"\n  {SEP}\n")

    total = 0
    downloaded = 0
    failed = 0

    for i, site_name in enumerate(selected_sites, 1):
        print(f"\n  ── {i}/{len(selected_sites)} {site_name} ──")

        try:
            for link in search_all(
                grade=grade, paper_type=paper_type, keyword=keyword,
                site=site_name, max_pages=max_pages, scrapers=state.scrapers,
            ):
                total += 1
                fmt = f"[{link.format_hint}]" if link.format_hint else ""
                print(f"    📄 {total}. {link.grade or ''} {link.title} {fmt}")

                if auto_dl:
                    scraper = next((s for s in state.scrapers if s.can_handle(link.url)), None)
                    if scraper:
                        if scraper.auth_level.value in ("walled", "vip"):
                            print(f"       ⚠️ 需要VIP/登录，跳过下载")
                        else:
                            path = scraper.download_paper(link)
                            if path:
                                print(f"       ✅ 已下载: {path}")
                                downloaded += 1
                            else:
                                print(f"       ⚠️ 下载失败")
                                failed += 1
        except Exception as e:
            print(f"    ❌ 搜索出错: {e}")

    # 汇总
    print(f"\n  {SEP}")
    print(f"  搜索完成！共找到 {total} 条结果")
    if auto_dl:
        print(f"  下载成功: {downloaded}  失败/跳过: {failed}")
    press_enter()


def menu_download_single(state: AppState):
    """通过 URL 下载单个试卷。"""
    state.load_scrapers()
    print_header()
    print("\n  📥 下载试卷（通过URL）")
    print(f"  {SEP}")
    url = input("\n  请输入试卷详情页 URL: ").strip()

    if not url:
        print("  ❌ URL 不能为空")
        press_enter()
        return

    from scrapers.scraper_registry import get_scraper_by_url
    scraper = get_scraper_by_url(
        url, config=state.config, session_manager=state.session_mgr,
        rate_limiter=state.rate_limiter, download_manager=state.dl_mgr,
    )

    if not scraper:
        print(f"\n  ❌ 未找到能处理此 URL 的爬虫")
        press_enter()
        return

    print(f"\n  使用爬虫: {scraper.site_name}")
    from core.base_scraper import PaperLink
    link = PaperLink(url=url, title="手动下载", grade="", paper_type="")
    path = scraper.download_paper(link)
    if path:
        print(f"  ✅ 下载成功: {path}")
    else:
        print(f"  ❌ 下载失败")
    press_enter()


def menu_sites(state: AppState):
    """列出所有站点。"""
    state.load_scrapers()
    print_header()
    print("\n  📡 已注册站点")
    print(f"  {SEP}")
    print(f"  {'站点名称':<16} {'类型':<10} {'认证':<10} {'URL'}")
    print(f"  {'-'*52}")

    for s in list_sites():
        auth_icon = {"none": "✅ 免费", "login": "⚠️  需登录",
                      "vip": "❌ VIP", "walled": "🛡️  强反爬"}
        type_icon = {"static": "静态HTML", "dynamic": "JS渲染", "api": "API逆向"}
        print(f"  {s['site_name']:<16} {type_icon.get(s['scraper_type'], s['scraper_type']):<10} "
              f"{auth_icon.get(s['auth_level'], s['auth_level']):<10} {s['base_url']}")

    print(f"  {'-'*52}")
    print(f"  共 {len(list_sites())} 个站点")
    press_enter()


def menu_cookie(state: AppState):
    """Cookie 管理 — 为需登录站点注入 Cookie。"""
    state.load_scrapers()
    print_header()
    print("\n  🍪 Cookie 管理")
    print(f"  {SEP}")
    print("\n  为需要登录的站点注入浏览器 Cookie，提升爬取能力。")
    print("  获取方法: 浏览器登录网站 → F12 → Application → Cookies → 全选复制\n")

    sites = list_sites()
    login_sites = [s for s in sites if s["auth_level"] in ("login", "vip")]
    for i, s in enumerate(login_sites, 1):
        print(f"    [{i}] {s['site_name']} ({s['auth_level']})")
    print(f"    [a] 所有需要登录的站点（使用同一Cookie）")
    print(f"    [b] 返回")

    choice = input("\n  请选择: ").strip().lower()
    if choice == "b":
        return

    print(f"\n  {SEP}")
    print("\n  请粘贴 Cookie 字符串，按 Ctrl+D (Mac: Cmd+D) 结束输入:\n")

    lines = []
    try:
        while True:
            line = input()
            lines.append(line)
    except EOFError:
        pass

    cookie_str = "".join(lines).strip()
    if not cookie_str:
        print("\n  ❌ 未输入 Cookie")
        press_enter()
        return

    if choice == "a":
        for s in login_sites:
            state.session_mgr.set_cookies_from_string(s["site_name"], cookie_str)
            state.session_mgr.save_cookies(s["site_name"])
        print(f"\n  ✅ 已为 {len(login_sites)} 个站点注入 Cookie")
    elif choice.isdigit() and 1 <= int(choice) <= len(login_sites):
        s = login_sites[int(choice) - 1]
        state.session_mgr.set_cookies_from_string(s["site_name"], cookie_str)
        state.session_mgr.save_cookies(s["site_name"])
        print(f"\n  ✅ {s['site_name']} 的 Cookie 已保存")
    press_enter()


def menu_stats(_state: AppState):
    """下载统计。"""
    print_header()
    print("\n  📊 下载统计")
    print(f"  {SEP}")

    db = DownloadDatabase()
    try:
        stats = db.get_stats()
        print(f"  总计: {stats['total']} 条记录")
        print(f"  已完成: {stats['completed']}")
        print(f"  失败: {stats['failed']}")

        if stats.get("by_site"):
            print(f"\n  按站点:")
            for site, count in stats["by_site"].items():
                print(f"    {site}: {count} 个文件")

        if stats.get("by_grade"):
            print(f"\n  按年级:")
            for grade, count in stats["by_grade"].items():
                print(f"    {grade}: {count} 个文件")
    finally:
        db.close()

    # 磁盘文件统计
    downloads_dir = Path(__file__).parent / "downloads"
    if downloads_dir.exists():
        print(f"\n  磁盘文件:")
        for site_dir in sorted(downloads_dir.iterdir()):
            if site_dir.is_dir():
                files = list(site_dir.rglob("*"))
                real_files = [f for f in files if f.is_file() and not f.name.startswith(".")]
                size = sum(f.stat().st_size for f in real_files)
                size_mb = size / (1024 * 1024)
                print(f"    {site_dir.name}/: {len(real_files)} 个文件 ({size_mb:.1f} MB)")

    press_enter()


def main():
    """主菜单循环。"""
    state = AppState()

    try:
        while True:
            clear_screen()
            print_header()
            print(f"""
    [1] 🔍 搜索试卷 — 按年级/类型/站点搜索
    [2] 📥 通过URL下载 — 输入试卷链接直接下载
    [3] 📡 站点列表 — 查看已注册的爬虫站点
    [4] 🍪 Cookie管理 — 为需登录站点注入Cookie
    [5] 📊 下载统计 — 查看下载记录和磁盘文件
    [0] 🚪 退出
""")
            choice = input("  请选择操作 (0-5): ").strip()

            if choice == "0":
                print("\n  再见！\n")
                break
            elif choice == "1":
                menu_search(state)
            elif choice == "2":
                menu_download_single(state)
            elif choice == "3":
                menu_sites(state)
            elif choice == "4":
                menu_cookie(state)
            elif choice == "5":
                menu_stats(state)
            else:
                print("\n  ❌ 无效选项，请重新输入")
                input("  按 Enter 继续...")
    finally:
        state.close()


if __name__ == "__main__":
    main()
