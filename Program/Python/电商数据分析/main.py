#!/usr/bin/env python3
"""
电商数据分析系统 — CLI 入口
参考 物理题库系统/main.py 的数字菜单 TUI 模式
"""

import sys
import os
from datetime import datetime

# 确保项目根目录在 sys.path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config import logger
from core import Database, get_browser_manager
from core.models import PriceRecord
from core.browser import BrowserManager

from scrapers import Alibaba1688Scraper, TaobaoScraper, PinduoduoScraper
from monitors import PriceMonitor, HotTracker
from analyzers import ReviewAnalyzer, ProductSelector
from exporters import CsvExporter, ChartGenerator, HtmlExporter, PdfExporter


class EcommerceApp:
    """电商数据分析系统主应用"""

    def __init__(self):
        self.db = Database()
        self.browser_mgr = BrowserManager()
        self.scraper_1688 = Alibaba1688Scraper(self.browser_mgr)
        self.scraper_taobao = TaobaoScraper(self.browser_mgr)
        self.scraper_pdd = PinduoduoScraper(self.browser_mgr)
        self.price_monitor = PriceMonitor(self.db)
        self.hot_tracker = HotTracker(self.db)
        self.review_analyzer = ReviewAnalyzer(self.db)
        self.product_selector = ProductSelector(self.db)
        self.csv_exporter = CsvExporter()
        self.chart_gen = ChartGenerator()
        self.html_exporter = HtmlExporter()
        self.pdf_exporter = PdfExporter()

    # ── 主菜单 ────────────────────────────────────────

    def run(self):
        """主循环"""
        self._print_banner()
        while True:
            try:
                self._show_menu()
                choice = input("\n请选择 [0-8]: ").strip()

                if choice == "1":
                    self._menu_scrape_products()
                elif choice == "2":
                    self._menu_price_monitor()
                elif choice == "3":
                    self._menu_hot_tracker()
                elif choice == "4":
                    self._menu_review_analysis()
                elif choice == "5":
                    self._menu_product_selection()
                elif choice == "6":
                    self._menu_export_report()
                elif choice == "7":
                    self._menu_export_data()
                elif choice == "8":
                    self._menu_login()
                elif choice == "0":
                    self._exit()
                    break
                else:
                    print("无效选择，请重试")
            except KeyboardInterrupt:
                print("\n")
                self._exit()
                break
            except Exception as e:
                logger.error(f"操作异常: {e}")
                print(f"❌ 操作失败: {e}")

    @staticmethod
    def _print_banner():
        print("\n" + "=" * 50)
        print("    📊 电商数据分析系统 v1.0")
        print("    支持: 1688 | 淘宝 | 拼多多")
        print("=" * 50)

    @staticmethod
    def _show_menu():
        print("""
┌─────────────────────────────────────────┐
│  [1] 🔍 批量抓取商品                      │
│  [2] 💰 竞品价格监控                      │
│  [3] 🔥 热销品追踪                        │
│  [4] 💬 评论分析与痛点提取                  │
│  [5] 🎯 选品分析                          │
│  [6] 📄 生成可视化报告 (HTML + PDF)         │
│  [7] 📊 导出数据表格 (CSV / Excel)          │
│  [8] 🔑 平台登录管理                       │
│  [0] 退出                                 │
└─────────────────────────────────────────┘""")

    # ── 菜单 1：批量抓取 ──────────────────────────────

    def _menu_scrape_products(self):
        print("\n── 🔍 批量抓取商品 ──")
        print("平台: [1] 1688  [2] 淘宝  [3] 拼多多")
        pf = input("选择平台 (1-3): ").strip()

        platform_map = {"1": ("1688", self.scraper_1688), "2": ("淘宝", self.scraper_taobao), "3": ("拼多多", self.scraper_pdd)}
        if pf not in platform_map:
            print("无效选择")
            return

        platform, scraper = platform_map[pf]

        # ── 1688/淘宝 登录检查 ──
        if platform in ("1688", "taobao"):
            cookie_file = os.path.join(
                os.path.dirname(os.path.abspath(__file__)),
                "cookies", f"{platform}.json"
            )
            if not os.path.exists(cookie_file):
                print(f"\n⚠️  {platform} 需要登录后才能搜索！")
                print(f"   当前没有 {platform} 的登录 Cookie。")
                choice = input(f"   是否现在登录？(Y/n): ").strip().lower()
                if choice != "n":
                    from login_helper import login_platform
                    login_platform(platform)
                    if not os.path.exists(cookie_file):
                        print(f"   登录未完成，无法继续抓取。")
                        return
                else:
                    print(f"   跳过登录，尝试抓取（很可能返回空结果）...")

        keyword = input("搜索关键词: ").strip()
        if not keyword:
            print("关键词不能为空")
            return

        try:
            pages = int(input("翻页数量 (默认3): ").strip() or "3")
        except ValueError:
            pages = 3

        category = input("品类标签 (可选): ").strip()

        print(f"\n开始抓取 {platform}「{keyword}」，最多 {pages} 页...")
        products = scraper.search_products(keyword, max_pages=pages, category=category)

        if not products:
            print(f"\n⚠️  未抓取到商品。可能原因：")
            if platform == "1688":
                print(f"   1. 未登录 — 运行 python3 login_helper.py 1688 先登录")
                print(f"   2. Cookie 过期 — 重新登录即可")
            print(f"   3. 反爬限制 — 稍后重试")
            print(f"   4. 页面结构变化 — 检查 output/ 目录截图")
            return

        # 存入数据库
        count = self.db.upsert_products_batch(products)
        print(f"\n✅ 抓取完成: {len(products)} 个商品，存入数据库 {count} 个")

        # 预览
        print("\n── 预览（前5条）──")
        for p in products[:5]:
            print(f"  {p.title[:40]:40s} | {p.display_price():>10s} | {p.display_sales():>8s} | {p.shop_name[:15]}")

    # ── 菜单 2：价格监控 ──────────────────────────────

    def _menu_price_monitor(self):
        print("\n── 💰 竞品价格监控 ──")
        print("[1] 添加监控商品")
        print("[2] 查看监控列表")
        print("[3] 手动检查价格")
        print("[4] 查看价格历史")
        choice = input("选择: ").strip()

        if choice == "1":
            url = input("商品链接: ").strip()
            platform = input("平台 (taobao/pinduoduo/1688): ").strip()
            task_id = self.price_monitor.add_product_by_url(url, platform)
            if task_id > 0:
                print(f"✅ 已添加监控任务 #{task_id}")

        elif choice == "2":
            tasks = self.db.get_active_monitor_tasks(task_type="price")
            if not tasks:
                print("暂无监控任务")
                return
            print(f"\n共 {len(tasks)} 个监控任务:")
            for t in tasks:
                print(f"  #{t.id} | {t.platform} | {t.product_url[:50]}... | 上次检查: {t.last_checked or '未检查'}")

        elif choice == "3":
            alerts = self.price_monitor.check_all_monitored()
            if alerts:
                print(f"\n⚠️ 发现 {len(alerts)} 个价格异动:")
                for a in alerts:
                    print(f"  {a['direction']} {abs(a['change_pct']):.1f}%: {a['title'][:30]}... (¥{a['old_price']:.2f} → ¥{a['new_price']:.2f})")
            else:
                print("✅ 所有监控商品价格稳定")

        elif choice == "4":
            products = self.price_monitor.get_monitored_products()
            if not products:
                print("暂无监控商品")
                return
            for i, p in enumerate(products):
                print(f"  [{i}] {p.title[:40]} - {p.display_price()}")
            try:
                idx = int(input("选择商品序号: ").strip())
                if 0 <= idx < len(products):
                    p = products[idx]
                    dates, prices = self.price_monitor.get_price_history_for_chart(p.id)
                    if dates:
                        print(f"\n价格历史 ({len(dates)} 条):")
                        for d, pr in zip(dates[-10:], prices[-10:]):
                            print(f"  {d}  ¥{pr:.2f}")
                        # 生成图表
                        self.chart_gen.plot_price_trend(dates, prices, p.title)
                        print(f"📈 趋势图已保存到 output/charts/")
                    else:
                        print("暂无价格记录")
            except (ValueError, IndexError):
                print("无效选择")

    # ── 菜单 3：热销追踪 ──────────────────────────────

    def _menu_hot_tracker(self):
        print("\n── 🔥 热销品追踪 ──")
        print("[1] 添加品类追踪")
        print("[2] 查看活跃追踪")
        print("[3] 手动抓取排行快照")
        print("[4] 查看排名变化")
        choice = input("选择: ").strip()

        if choice == "1":
            platform = input("平台 (taobao/pinduoduo/1688): ").strip()
            category = input("品类关键词: ").strip()
            task_id = self.hot_tracker.add_category_tracking(platform, category)
            if task_id > 0:
                print(f"✅ 已添加热销追踪 #{task_id}")

        elif choice == "2":
            tasks = self.hot_tracker.get_active_tracking_tasks()
            if not tasks:
                print("暂无追踪任务")
                return
            for t in tasks:
                print(f"  #{t.id} | {t.platform} | {t.category} | {t.keywords}")

        elif choice == "3":
            platform = input("平台 (taobao/pinduoduo/1688): ").strip()
            category = input("品类关键词: ").strip()

            pf_map = {"taobao": self.scraper_taobao, "pinduoduo": self.scraper_pdd, "1688": self.scraper_1688}
            scraper = pf_map.get(platform)
            if not scraper:
                print("无效平台")
                return

            print(f"抓取 {platform}/{category} 热销排行...")
            rankings = scraper.get_hot_ranking(category)
            count = self.hot_tracker.take_snapshot(platform, category, rankings)
            print(f"✅ 快照保存: {count} 个商品")

            # 显示 Top 10
            for r in rankings[:10]:
                print(f"  #{r.rank} {r.title[:35]:35s} ¥{r.price:.2f}")

        elif choice == "4":
            platform = input("平台: ").strip()
            category = input("品类: ").strip()
            changes = self.hot_tracker.get_ranking_changes(platform, category)
            if changes:
                print(f"\n排名变化 ({len(changes)} 项):")
                for c in changes:
                    if c["type"] == "排名变化":
                        print(f"  {c['direction']}{abs(c['change'])}位: {c['title'][:30]} (#{c['old_rank']}→#{c['new_rank']})")
                    elif c["type"] == "新品上榜":
                        print(f"  🆕 新品上榜 #{c['new_rank']}: {c['title'][:30]}")
                    elif c["type"] == "下榜":
                        print(f"  📉 下榜 (曾 #{c['old_rank']}): {c['title'][:30]}")
            else:
                print("暂无足够数据进行对比（至少需要两次快照）")

    # ── 菜单 4：评论分析 ──────────────────────────────

    def _menu_review_analysis(self):
        print("\n── 💬 评论分析与痛点提取 ──")
        products = self.db.get_products(limit=50)

        if not products:
            print("数据库中暂无商品，请先抓取商品")
            return

        for i, p in enumerate(products):
            print(f"  [{i}] [{p.platform}] {p.title[:50]} - {p.display_price()}")

        try:
            idx = int(input("\n选择商品序号: ").strip())
            if idx < 0 or idx >= len(products):
                print("无效选择")
                return
        except ValueError:
            print("无效输入")
            return

        product = products[idx]
        print(f"\n分析商品: {product.title}")

        # 抓取评论（如果有链接）
        if product.url:
            print("正在抓取评论（这可能需要几分钟）...")
            platform_map = {"1688": self.scraper_1688, "taobao": self.scraper_taobao, "pinduoduo": self.scraper_pdd}
            scraper = platform_map.get(product.platform)
            if scraper:
                reviews = scraper.get_reviews(product.url, max_pages=3)
                for r in reviews:
                    r.product_db_id = product.id
                self.db.insert_reviews_batch(reviews)
                print(f"  抓取到 {len(reviews)} 条评论")

        # NLP 分析
        print("正在进行 NLP 分析...")
        result = self.review_analyzer.full_analysis(product.id)

        sentiment = result["sentiment"]
        print(f"\n── 情感分析 ──")
        print(f"  评论总数: {sentiment['total']}")
        print(f"  好评: {sentiment['positive']} | 中评: {sentiment['neutral']} | 差评: {sentiment['negative']}")
        if sentiment.get("positive_rate"):
            print(f"  好评率: {sentiment['positive_rate']}%")
        print(f"  平均情感分: {sentiment.get('avg_sentiment', 'N/A')}")

        pain_points = result["pain_points"]
        if pain_points:
            print(f"\n── 痛点关键词 Top 10 ──")
            for kw, freq, sent in pain_points[:10]:
                print(f"  {kw:15s} 频次:{freq:3d}  情感:{sent:.2f}")

        word_freq = result["word_frequency"]
        if word_freq:
            print(f"\n── 高频词 Top 10 ──")
            for w, f in word_freq[:10]:
                print(f"  {w:15s} {f}次")

        # 生成图表
        print("\n生成可视化图表...")
        chart_files = []
        chart_files.append(self.chart_gen.plot_sentiment_pie(
            positive=sentiment.get("positive", 0),
            neutral=sentiment.get("neutral", 0),
            negative=sentiment.get("negative", 0),
            product_name=product.title[:30],
        ))
        if pain_points:
            kws = [p[0] for p in pain_points[:15]]
            freqs = [p[1] for p in pain_points[:15]]
            chart_files.append(self.chart_gen.plot_pain_points(kws, freqs, product_name=product.title[:30]))

        # 生成 HTML 报告
        html_path = self.html_exporter.build_review_analysis_report(
            product_name=product.title,
            stats=sentiment,
            pain_points=pain_points,
            chart_files=chart_files,
        )
        print(f"✅ HTML 报告: {html_path}")

        # 尝试生成 PDF
        pdf_path = self.pdf_exporter.html_to_pdf(html_path, browser_manager=self.browser_mgr)
        if pdf_path:
            print(f"✅ PDF 报告: {pdf_path}")

    # ── 菜单 5：选品分析 ──────────────────────────────

    def _menu_product_selection(self):
        print("\n── 🎯 选品分析 ──")
        print("[1] 分析数据库中的商品")
        print("[2] 先抓取1688品类再分析")
        choice = input("选择: ").strip()

        if choice == "2":
            keyword = input("1688 搜索关键词: ").strip()
            try:
                pages = int(input("翻页数量 (默认5): ").strip() or "5")
            except ValueError:
                pages = 5
            print(f"正在抓取 1688「{keyword}」...")
            products = self.scraper_1688.search_products(keyword, max_pages=pages, category=keyword)
            self.db.upsert_products_batch(products)
            print(f"抓取 {len(products)} 个商品")

        # 从数据库获取
        platform = input("筛选平台 (1688/taobao/pinduoduo/留空=全部): ").strip()
        category = input("筛选品类 (留空=全部): ").strip()

        products = self.db.get_products(platform=platform, category=category, limit=200)
        if not products:
            print("没有符合条件的商品")
            return

        print(f"\n正在分析 {len(products)} 个商品...")
        ranked = self.product_selector.rank_products(products, category=category)

        # 推荐分组
        recs = self.product_selector.get_recommendations(ranked)

        print(f"\n── 选品推荐 ──")
        print(f"  ⭐ 推荐: {len(recs['recommended'])} 个")
        print(f"  △ 可考虑: {len(recs['worth_considering'])} 个")
        print(f"  × 不推荐: {len(recs['skip'])} 个")

        # 推荐列表 Top 10
        if recs["recommended"]:
            print(f"\n── ⭐ 推荐商品 Top 10 ──")
            for p, score, rank in recs["recommended"][:10]:
                print(f"  #{rank} [{score:.1f}] {p.title[:40]:40s} {p.display_price():>10s} | {p.display_sales()}")

        # 导出选品表格
        export_choice = input("\n导出选品表格? [1] Excel [2] CSV [0] 跳过: ").strip()
        if export_choice == "1":
            products_list, scores_list, ranks_list = zip(*[(p, s, r) for p, s, r in ranked])
            path = self.csv_exporter.export_selection_report_to_excel(
                list(products_list), list(scores_list), list(ranks_list)
            )
            print(f"✅ Excel: {path}")
        elif export_choice == "2":
            path = self.csv_exporter.export_products_to_csv(
                [p for p, _, _ in ranked]
            )
            print(f"✅ CSV: {path}")

    # ── 菜单 6：生成报告 ──────────────────────────────

    def _menu_export_report(self):
        print("\n── 📄 生成可视化报告 ──")
        print("[1] 价格监控报告")
        print("[2] 选品分析报告")
        print("[3] 评论分析报告")
        choice = input("选择: ").strip()

        if choice == "1":
            monitored = self.price_monitor.get_monitored_products()
            if not monitored:
                print("暂无监控商品，请先添加价格监控")
                return

            alerts = self.price_monitor.check_all_monitored()
            chart_files = []

            for p in monitored[:5]:
                dates, prices = self.price_monitor.get_price_history_for_chart(p.id)
                if dates and len(dates) >= 2:
                    f = self.chart_gen.plot_price_trend(dates, prices, p.title[:20])
                    chart_files.append(f)

            html_path = self.html_exporter.build_price_monitor_report(
                monitored, {}, alerts or [], chart_files
            )
            print(f"✅ HTML 报告: {html_path}")
            pdf_path = self.pdf_exporter.html_to_pdf(html_path, browser_manager=self.browser_mgr)
            if pdf_path:
                print(f"✅ PDF 报告: {pdf_path}")

        elif choice == "2":
            products = self.db.get_products(limit=50)
            if not products:
                print("数据库中没有商品")
                return
            ranked = self.product_selector.rank_products(products)
            ps, ss, rs = zip(*[(p, s, r) for p, s, r in ranked])
            html_path = self.html_exporter.build_product_selection_report(
                list(ps), list(ss), list(rs)
            )
            print(f"✅ HTML 报告: {html_path}")
            pdf_path = self.pdf_exporter.html_to_pdf(html_path, browser_manager=self.browser_mgr)
            if pdf_path:
                print(f"✅ PDF 报告: {pdf_path}")

        elif choice == "3":
            products = self.db.get_products(limit=20)
            if not products:
                print("数据库中没有商品")
                return
            for i, p in enumerate(products):
                print(f"  [{i}] {p.title[:40]}")
            try:
                idx = int(input("选择商品: ").strip())
                product = products[idx]
            except (ValueError, IndexError):
                print("无效选择")
                return

            result = self.review_analyzer.full_analysis(product.id)
            chart_files = []
            s = result["sentiment"]
            chart_files.append(self.chart_gen.plot_sentiment_pie(
                positive=s.get("positive", 0), neutral=s.get("neutral", 0),
                negative=s.get("negative", 0), product_name=product.title[:30],
            ))
            pp = result["pain_points"]
            if pp:
                chart_files.append(self.chart_gen.plot_pain_points(
                    [p[0] for p in pp[:15]], [p[1] for p in pp[:15]],
                    product_name=product.title[:30],
                ))

            html_path = self.html_exporter.build_review_analysis_report(
                product.title, s, pp, chart_files
            )
            print(f"✅ HTML 报告: {html_path}")
            pdf_path = self.pdf_exporter.html_to_pdf(html_path, browser_manager=self.browser_mgr)
            if pdf_path:
                print(f"✅ PDF 报告: {pdf_path}")

    # ── 菜单 7：导出数据 ──────────────────────────────

    def _menu_export_data(self):
        print("\n── 📊 导出数据表格 ──")
        print("[1] 导出全部商品")
        print("[2] 导出指定平台商品")
        print("[3] 导出监控商品价格历史")
        choice = input("选择: ").strip()

        if choice == "1":
            products = self.db.get_products(limit=500)
            if not products:
                print("数据库中没有商品")
                return
            fmt = input("格式 [1] Excel [2] CSV: ").strip()
            if fmt == "1":
                path = self.csv_exporter.export_products_to_excel(products)
            else:
                path = self.csv_exporter.export_products_to_csv(products)
            print(f"✅ 已导出: {path}")

        elif choice == "2":
            platform = input("平台 (taobao/pinduoduo/1688): ").strip()
            products = self.db.get_products(platform=platform, limit=500)
            if not products:
                print(f"{platform} 没有商品")
                return
            path = self.csv_exporter.export_products_to_excel(
                products, filename=f"{platform}_products_{datetime.now().strftime('%Y%m%d')}.xlsx"
            )
            print(f"✅ 已导出: {path}")

        elif choice == "3":
            monitored = self.price_monitor.get_monitored_products()
            if not monitored:
                print("暂无监控商品")
                return
            for p in monitored:
                dates, prices = self.price_monitor.get_price_history_for_chart(p.id)
                if dates:
                    records = [PriceRecord(product_db_id=p.id, price=pr, recorded_at=d)
                               for d, pr in zip(dates, prices)]
                    path = self.csv_exporter.export_price_history_to_csv(p.title, records)
                    print(f"✅ {path}")

    # ── 菜单 8：平台登录 ──────────────────────────────

    def _menu_login(self):
        print("\n── 🔑 平台登录管理 ──")
        print("[1] 登录 1688")
        print("[2] 登录 淘宝")
        print("[3] 登录 拼多多")
        print("[4] 检查所有平台 Cookie 状态")
        choice = input("选择: ").strip()

        from login_helper import login_platform, check_all_platforms

        if choice == "1":
            login_platform("1688")
        elif choice == "2":
            login_platform("taobao")
        elif choice == "3":
            login_platform("pinduoduo")
        elif choice == "4":
            check_all_platforms()
        else:
            print("无效选择")

        input("\n按回车返回主菜单...")

    # ── 退出 ──────────────────────────────────────────

    def _exit(self):
        print("\n正在关闭...")
        try:
            BrowserManager.close()
        except Exception:
            pass
        self.db.close()
        print("👋 再见！")


def main():
    """入口函数"""
    app = EcommerceApp()
    app.run()


if __name__ == "__main__":
    main()