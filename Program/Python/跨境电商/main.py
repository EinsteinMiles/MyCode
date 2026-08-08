#!/usr/bin/env python3
"""
跨境电商数据分析系统 — CLI 入口
支持: eBay | Amazon | AliExpress | Shopee

对标 电商数据分析/main.py TUI 模式
"""

import sys
import os
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config import logger
from core import Database
from core.models import PriceRecord
from core.browser import BrowserManager

from scrapers import EbayScraper, AmazonScraper, AliExpressScraper, ShopeeScraper
from monitors import PriceMonitor, HotTracker
from analyzers import ReviewAnalyzer, ProductSelector
from exporters import CsvExporter, ChartGenerator, HtmlExporter, PdfExporter


class CrossBorderApp:
    """跨境电商数据分析系统"""

    def __init__(self):
        self.db = Database()
        self.browser_mgr = BrowserManager()
        self.scraper_ebay = EbayScraper(self.browser_mgr)
        self.scraper_amazon = AmazonScraper(self.browser_mgr)
        self.scraper_aliexpress = AliExpressScraper(self.browser_mgr)
        self.scraper_shopee = ShopeeScraper(self.browser_mgr)
        self.price_monitor = PriceMonitor(self.db)
        self.hot_tracker = HotTracker(self.db)
        self.review_analyzer = ReviewAnalyzer(self.db)
        self.product_selector = ProductSelector(self.db)
        self.csv_exporter = CsvExporter()
        self.chart_gen = ChartGenerator()
        self.html_exporter = HtmlExporter()
        self.pdf_exporter = PdfExporter()

    # ── 主菜单 ──────────────────────────────────────

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
                logger.error(f"错误: {e}")
                print(f"❌ 操作失败: {e}")

    @staticmethod
    def _print_banner():
        print("\n" + "=" * 50)
        print("    📊 跨境电商数据分析系统 v1.0")
        print("    支持平台: eBay | Amazon | AliExpress | Shopee")
        print("=" * 50)

    @staticmethod
    def _show_menu():
        print("""
┌─────────────────────────────────────────┐
│  [1] 🔍 批量采集商品                      │
│  [2] 💰 价格监控                          │
│  [3] 🔥 热销商品追踪                      │
│  [4] 💬 评论分析与情感判断                 │
│  [5] 🎯 选品分析                          │
│  [6] 📄 生成报表 (HTML + PDF)             │
│  [7] 📊 导出数据 (CSV / Excel)            │
│  [8] 🔑 平台登录管理                      │
│  [0] 退出                                │
└─────────────────────────────────────────┘""")

    # ── 菜单 1: 批量采集 ────────────────────────────

    def _menu_scrape_products(self):
        print("\n── 🔍 批量采集商品 ──")
        print("平台: [1] eBay  [2] Amazon  [3] AliExpress  [4] Shopee")
        pf = input("选择平台 (1-4): ").strip()

        platform_map = {
            "1": ("eBay", self.scraper_ebay),
            "2": ("Amazon", self.scraper_amazon),
            "3": ("AliExpress", self.scraper_aliexpress),
            "4": ("Shopee", self.scraper_shopee),
        }
        if pf not in platform_map:
            print("无效选择")
            return

        platform, scraper = platform_map[pf]

        keyword = input("搜索关键词: ").strip()
        if not keyword:
            print("关键词不能为空")
            return

        try:
            pages = int(input("采集页数 (默认 3): ").strip() or "3")
        except ValueError:
            pages = 3

        category = input("分类标签 (可选): ").strip()

        print(f"\n正在采集 {platform} '{keyword}'，最多 {pages} 页...")
        print(f"⚠️  Amazon 反爬严格，建议使用较少页数 (1-2)")
        print(f"⚠️  Shopee 有 Cloudflare 防护，建议使用较少页数 (1-3)")

        if platform == "Amazon":
            print("   建议先在菜单 [8] 中登录，降低验证码风险")
        if platform == "Shopee":
            print("   建议先在菜单 [8] 中登录，降低 Cloudflare 验证风险")

        products = scraper.search_products(keyword, max_pages=pages, category=category)

        if not products:
            print(f"\n⚠️  未从 {platform} 采集到商品。")
            print(f"   诊断截图和 HTML 已保存至 output/ 目录")
            print(f"   可能原因:")
            if platform == "eBay":
                print(f"   1. eBay 跳转到了本地化域名 — 查看 output/ 截图")
                print(f"   2. 需要登录 — 先使用菜单 [8] 登录")
                print(f"   3. 页面未渲染 — 在 config.py 中设置 HEADLESS=False")
            elif platform == "Amazon":
                print(f"   1. Amazon 验证码非常严格 — 先通过菜单 [8] 登录")
                print(f"   2. 尝试设置 headless=False 并手动完成验证")
            elif platform == "AliExpress":
                print(f"   1. AliExpress 需要更长加载时间 — 尝试减少页数")
                print(f"   2. 可能根据地区跳转")
            elif platform == "Shopee":
                print(f"   1. Shopee 有 Cloudflare 验证 — 先通过菜单 [8] 登录")
                print(f"   2. 尝试设置 headless=False 并手动完成验证")
                print(f"   3. shopee.sg 可能根据 IP 地区跳转")
            print(f"   4. 网络/代理问题 — 平台可能屏蔽了你的 IP")
            return

        count = self.db.upsert_products_batch(products)
        print(f"\n✅ 采集了 {len(products)} 个商品，保存 {count} 条至数据库")

        print("\n── 预览 (前 5 条) ──")
        for p in products[:5]:
            print(f"  {p.title[:40]:40s} | {p.display_price():>12s} | {p.display_sales():>12s} | ⭐{p.rating:.1f}" if p.rating else f"  {p.title[:40]:40s} | {p.display_price():>12s} | {p.display_sales():>12s}")

    # ── 菜单 2: 价格监控 ────────────────────────────

    def _menu_price_monitor(self):
        print("\n── 💰 价格监控 ──")
        print("[1] 添加监控商品")
        print("[2] 查看监控列表")
        print("[3] 立即检查价格")
        print("[4] 查看价格历史")
        choice = input("请选择: ").strip()

        if choice == "1":
            url = input("商品链接: ").strip()
            platform = input("平台 (ebay/amazon/aliexpress/shopee): ").strip()
            task_id = self.price_monitor.add_product_by_url(url, platform)
            if task_id > 0:
                print(f"✅ 已添加监控任务 #{task_id}")

        elif choice == "2":
            tasks = self.db.get_active_monitor_tasks(task_type="price")
            if not tasks:
                print("暂无活跃的监控任务")
                return
            print(f"\n{tasks.__len__()} 个活跃监控任务:")
            for t in tasks:
                print(f"  #{t.id} | {t.platform} | {t.product_url[:50]}... | 上次检查: {t.last_checked or '从未'}")

        elif choice == "3":
            alerts = self.price_monitor.check_all_monitored()
            if alerts:
                print(f"\n⚠️  发现 {len(alerts)} 个价格变动:")
                for a in alerts:
                    print(f"  {a['direction']} {abs(a['change_pct']):.1f}%: {a['title'][:30]}... (${a['old_price']:.2f} → ${a['new_price']:.2f})")
            else:
                print("✅ 所有监控价格稳定")

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
                        print(f"\n价格历史 ({len(dates)} 条记录):")
                        for d, pr in zip(dates[-10:], prices[-10:]):
                            print(f"  {d}  ${pr:.2f}")
                        self.chart_gen.plot_price_trend(dates, prices, p.title, p.currency)
                        print(f"📈 图表已保存至 output/charts/")
                    else:
                        print("暂无价格记录")
            except (ValueError, IndexError):
                print("无效选择")

    # ── 菜单 3: 热销追踪 ────────────────────────────

    def _menu_hot_tracker(self):
        print("\n── 🔥 热销商品追踪 ──")
        print("[1] 添加分类追踪")
        print("[2] 查看活跃追踪")
        print("[3] 采集排行快照")
        print("[4] 查看排行变化")
        choice = input("请选择: ").strip()

        if choice == "1":
            platform = input("平台 (ebay/amazon/aliexpress/shopee): ").strip()
            category = input("分类关键词: ").strip()
            task_id = self.hot_tracker.add_category_tracking(platform, category)
            if task_id > 0:
                print(f"✅ 已添加追踪任务 #{task_id}")

        elif choice == "2":
            tasks = self.hot_tracker.get_active_tracking_tasks()
            if not tasks:
                print("暂无活跃的追踪任务")
                return
            for t in tasks:
                print(f"  #{t.id} | {t.platform} | {t.category} | {t.keywords}")

        elif choice == "3":
            platform = input("平台 (ebay/amazon/aliexpress/shopee): ").strip()
            category = input("分类关键词: ").strip()
            pf_map = {"ebay": self.scraper_ebay, "amazon": self.scraper_amazon, "aliexpress": self.scraper_aliexpress, "shopee": self.scraper_shopee}
            scraper = pf_map.get(platform)
            if not scraper:
                print("无效平台")
                return

            print(f"正在采集 {platform}/{category} 热销排行...")
            rankings = scraper.get_hot_ranking(category)
            count = self.hot_tracker.take_snapshot(platform, category, rankings)
            print(f"✅ 快照已保存: {count} 个商品")

            for r in rankings[:10]:
                print(f"  #{r.rank} {r.title[:35]:35s} ${r.price:.2f}")

        elif choice == "4":
            platform = input("平台: ").strip()
            category = input("分类: ").strip()
            changes = self.hot_tracker.get_ranking_changes(platform, category)
            if changes:
                print(f"\n排行变化 ({len(changes)} 条):")
                for c in changes:
                    if c["type"] == "排名变化":
                        print(f"  {c['direction']}{abs(c['change'])} 位: {c['title'][:30]} (#{c['old_rank']}→#{c['new_rank']})")
                    elif c["type"] == "新上榜":
                        print(f"  🆕 新上榜 #{c['new_rank']}: {c['title'][:30]}")
                    elif c["type"] == "已下榜":
                        print(f"  📉 已下榜 (曾是 #{c['old_rank']}): {c['title'][:30]}")
            else:
                print("数据不足，无法比较（需要至少 2 个快照）")

    # ── 菜单 4: 评论分析 ────────────────────────────

    def _menu_review_analysis(self):
        print("\n── 💬 评论分析与情感判断 ──")
        products = self.db.get_products(limit=50)

        if not products:
            print("数据库中没有商品，请先采集！")
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
        print(f"\n正在分析: {product.title}")

        if product.url:
            print("正在抓取评论 (可能需要几分钟)...")
            platform_map = {"ebay": self.scraper_ebay, "amazon": self.scraper_amazon, "aliexpress": self.scraper_aliexpress, "shopee": self.scraper_shopee}
            scraper = platform_map.get(product.platform)
            if scraper:
                reviews = scraper.get_reviews(product.url, max_pages=3)
                for r in reviews:
                    r.product_db_id = product.id
                self.db.insert_reviews_batch(reviews)
                print(f"  抓取了 {len(reviews)} 条评论")

        print("正在运行 NLP 分析...")
        result = self.review_analyzer.full_analysis(product.id)

        sentiment = result["sentiment"]
        print(f"\n── 情感分析 ──")
        print(f"  评论数: {sentiment['total']}")
        print(f"  正面: {sentiment['positive']} | 中性: {sentiment['neutral']} | 负面: {sentiment['negative']}")
        if sentiment.get("positive_rate"):
            print(f"  好评率: {sentiment['positive_rate']}%")
        print(f"  平均情感 (VADER): {sentiment.get('avg_sentiment', 'N/A')}")

        pain_points = result["pain_points"]
        if pain_points:
            print(f"\n── 痛点 Top 10 ──")
            for kw, freq, sent in pain_points[:10]:
                print(f"  {kw:20s} 频次:{freq:3d}  情感:{sent:.2f}")

        word_freq = result["word_frequency"]
        if word_freq:
            print(f"\n── 关键词 ──")
            for w, f in word_freq[:10]:
                print(f"  {w:20s} {f}次")

        print("\n正在生成图表...")
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
            chart_files.append(self.chart_gen.plot_pain_points(
                kws, freqs, product_name=product.title[:30],
            ))

        html_path = self.html_exporter.build_review_analysis_report(
            product_name=product.title,
            stats=sentiment,
            pain_points=pain_points,
            chart_files=chart_files,
        )
        print(f"✅ HTML 报告: {html_path}")

        pdf_path = self.pdf_exporter.html_to_pdf(html_path, browser_manager=self.browser_mgr)
        if pdf_path:
            print(f"✅ PDF 报告: {pdf_path}")

    # ── 菜单 5: 选品分析 ────────────────────────────

    def _menu_product_selection(self):
        print("\n── 🎯 选品分析 ──")
        print("[1] 分析数据库已有商品")
        print("[2] 先采集再分析")
        choice = input("请选择: ").strip()

        if choice == "2":
            print("平台: [1] eBay  [2] Amazon  [3] AliExpress  [4] Shopee")
            pf = input("选择平台 (1-4): ").strip()
            pf_map = {"1": ("ebay", self.scraper_ebay), "2": ("amazon", self.scraper_amazon), "3": ("aliexpress", self.scraper_aliexpress), "4": ("shopee", self.scraper_shopee)}
            if pf not in pf_map:
                print("无效选择")
                return
            platform, scraper = pf_map[pf]

            keyword = input("搜索关键词: ").strip()
            try:
                pages = int(input("采集页数 (默认 5): ").strip() or "5")
            except ValueError:
                pages = 5

            print(f"正在采集 {platform} '{keyword}'...")
            products = scraper.search_products(keyword, max_pages=pages, category=keyword)
            self.db.upsert_products_batch(products)
            print(f"采集了 {len(products)} 个商品")

        platform = input("按平台筛选 (ebay/amazon/aliexpress/shopee/留空=全部): ").strip()
        category = input("按分类筛选 (留空=全部): ").strip()

        products = self.db.get_products(platform=platform, category=category, limit=200)
        if not products:
            print("没有符合条件的商品")
            return

        print(f"\n正在分析 {len(products)} 个商品...")
        ranked = self.product_selector.rank_products(products, category=category)
        recs = self.product_selector.get_recommendations(ranked)

        print(f"\n── 选品结果 ──")
        print(f"  ★ 推荐: {len(recs['recommended'])}")
        print(f"  △ 可考虑: {len(recs['worth_considering'])}")
        print(f"  × 不建议: {len(recs['skip'])}")

        if recs["recommended"]:
            print(f"\n── ★ 推荐榜单 ──")
            for p, score, rank in recs["recommended"][:10]:
                print(f"  #{rank} [{score:.1f}] {p.title[:40]:40s} {p.display_price():>12s} | {p.display_sales()}")

        export_choice = input("\n导出结果? [1] Excel [2] CSV [0] 跳过: ").strip()
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

    # ── 菜单 6: 生成报表 ────────────────────────────

    def _menu_export_report(self):
        print("\n── 📄 生成报表 ──")
        print("[1] 价格监控报表")
        print("[2] 选品分析报表")
        print("[3] 评论分析报表")
        choice = input("请选择: ").strip()

        if choice == "1":
            monitored = self.price_monitor.get_monitored_products()
            if not monitored:
                print("暂无监控商品，请先在菜单 [2] 中添加。")
                return

            alerts = self.price_monitor.check_all_monitored()
            chart_files = []
            for p in monitored[:5]:
                dates, prices = self.price_monitor.get_price_history_for_chart(p.id)
                if dates and len(dates) >= 2:
                    f = self.chart_gen.plot_price_trend(dates, prices, p.title[:20], p.currency)
                    chart_files.append(f)

            html_path = self.html_exporter.build_price_monitor_report(monitored, {}, alerts or [], chart_files)
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
            html_path = self.html_exporter.build_product_selection_report(list(ps), list(ss), list(rs))
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

            html_path = self.html_exporter.build_review_analysis_report(product.title, s, pp, chart_files)
            print(f"✅ HTML 报告: {html_path}")
            pdf_path = self.pdf_exporter.html_to_pdf(html_path, browser_manager=self.browser_mgr)
            if pdf_path:
                print(f"✅ PDF 报告: {pdf_path}")

    # ── 菜单 7: 导出数据 ────────────────────────────

    def _menu_export_data(self):
        print("\n── 📊 导出数据 ──")
        print("[1] 导出全部商品")
        print("[2] 按平台导出")
        print("[3] 导出价格历史")
        choice = input("请选择: ").strip()

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
            platform = input("平台 (ebay/amazon/aliexpress/shopee): ").strip()
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

    # ── 菜单 8: 登录管理 ────────────────────────────

    def _menu_login(self):
        print("\n── 🔑 平台登录管理 ──")
        print("[1] 登录 eBay")
        print("[2] 登录 Amazon")
        print("[3] 登录 AliExpress")
        print("[4] 登录 Shopee")
        print("[5] 检查所有平台登录状态")
        choice = input("请选择: ").strip()

        from login_helper import login_platform, check_all_platforms

        if choice == "1":
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

        input("\n按回车返回主菜单...")

    # ── 退出 ──────────────────────────────────────

    def _exit(self):
        print("\n正在关闭...")
        try:
            BrowserManager.close()
        except Exception:
            pass
        self.db.close()
        print("👋 再见！")


def main():
    """入口"""
    app = CrossBorderApp()
    app.run()


if __name__ == "__main__":
    main()
