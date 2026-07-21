#!/usr/bin/env python3
"""
================================================================================
 财报分析工具 - 主入口
 一站式 A 股上市公司财报数据获取、清洗、分析、可视化

 用法:
   python test.py                          # 交互式菜单
   python test.py --symbol 300750          # 分析单只股票
   python test.py -s 600519,000858         # 批量分析
   python test.py -s 300750 --years 3      # 指定年份
   python test.py -s 300750 --pdf          # 同时导出 PDF
================================================================================
"""

import sys
import os
import argparse
import logging
# 确保项目根目录在 path 中
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config import DEFAULT_YEARS
from scraper.fetcher import FinancialStatementFetcher
from scraper.pdf_downloader import PDFDownloader
from cleaner.parser import DataCleaner, DataMerger
from cleaner.indicators import IndicatorCalculator
from cleaner.analyzer import ReportAnalyzer
from display.charts import ChartGenerator
from display.report import ReportBuilder

# 日志配置
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("财报分析")


class FinancialAnalysisPipeline:
    """
    财报分析流水线
    整合 爬取 → 清洗 → 计算 → 图表 → 报告 全流程
    """

    def __init__(self, years: int = DEFAULT_YEARS, export_pdf: bool = False):
        self.years = years
        self.export_pdf = export_pdf

        # 初始化各模块
        self.fetcher = FinancialStatementFetcher()
        self.pdf_downloader = PDFDownloader()
        self.cleaner = DataCleaner(unit="yi")
        self.merger = DataMerger(self.cleaner)
        self.calculator = IndicatorCalculator()
        self.analyzer = ReportAnalyzer()
        self.charts = ChartGenerator()
        self.reporter = ReportBuilder()

    def run(self, symbol: str, company_name: str = "") -> str:
        """
        执行单个公司的完整分析流程

        参数:
            symbol: 股票代码 (如 "300750")
            company_name: 公司名称 (可选，不提供则自动获取)

        返回: HTML 报告文件路径
        """
        symbol = str(symbol).strip().zfill(6)

        if not FinancialStatementFetcher.validate_stock_code(symbol):
            raise ValueError(f"无效的股票代码: {symbol}")

        logger.info("=" * 60)
        logger.info(f"开始分析: {company_name or symbol} ({symbol})")
        logger.info("=" * 60)

        # ---- 阶段 1: 数据爬取 ----
        logger.info("\n📥 阶段 1/4: 数据获取...")
        try:
            statements = self.fetcher.fetch_all_statements(symbol)
        except Exception as e:
            logger.error(f"数据获取失败: {e}")
            raise

        if all(df.empty for df in statements.values()):
            raise RuntimeError(f"未能获取到 {symbol} 的任何财务数据，请检查股票代码")

        # 尝试获取公司信息
        if not company_name:
            try:
                info = self.fetcher.fetch_company_info(symbol)
                company_name = info.get("股票简称", symbol)
            except Exception:
                company_name = symbol

        # ---- 阶段 2: 数据清洗 ----
        logger.info("\n🧹 阶段 2/4: 数据清洗与指标计算...")
        cleaned = self.cleaner.clean_all(statements)

        # 计算财务指标
        indicators = self.calculator.calculate_all(cleaned)

        if indicators.empty:
            raise RuntimeError("指标计算后数据为空")

        # 按年份筛选
        if "year" in indicators.columns:
            available_years = sorted(indicators["year"].dropna().unique())
            if len(available_years) > self.years:
                cutoff = available_years[-self.years]
                indicators = indicators[indicators["year"] >= cutoff]
            logger.info(f"分析年份: {available_years[-self.years:]}")

        # ---- 阶段 3: 生成图表 & 分析 ----
        logger.info("\n📊 阶段 3/4: 生成图表与分析结论...")
        chart_files = self.charts.generate_all(indicators)

        conclusion = self.analyzer.generate_conclusion(indicators, company_name)
        health = self.analyzer.calculate_health_score(indicators)
        trends = self.analyzer.analyze_trends(indicators)

        # 打印分析摘要到控制台
        self._print_summary(company_name, symbol, indicators, health, trends)

        # ---- 阶段 4: 生成报告 ----
        logger.info("\n📄 阶段 4/4: 生成分析报告...")
        html_path = self.reporter.generate_full_report(
            company_name=company_name,
            stock_code=symbol,
            indicators=indicators,
            chart_files=chart_files,
            conclusion=conclusion,
            export_pdf=self.export_pdf,
            open_browser=True,
        )

        logger.info(f"\n✅ 分析完成! 报告: {html_path}")
        return html_path

    def run_batch(self, symbols: list) -> list:
        """批量分析多个公司"""
        results = []
        for i, symbol in enumerate(symbols, 1):
            logger.info(f"\n{'='*40}\n  [{i}/{len(symbols)}] 分析 {symbol}\n{'='*40}")
            try:
                path = self.run(symbol)
                results.append({"symbol": symbol, "status": "success", "path": path})
            except Exception as e:
                logger.error(f"分析 {symbol} 失败: {e}")
                results.append({"symbol": symbol, "status": "failed", "error": str(e)})

        # 汇总
        success = sum(1 for r in results if r["status"] == "success")
        logger.info(f"\n批量分析完成: {success}/{len(symbols)} 成功")
        return results

    def _print_summary(self, name: str, code: str, indicators, health: dict, trends: dict):
        """打印控制台摘要"""
        latest = indicators.iloc[-1]
        year = int(latest.get("year", 0))

        print(f"\n{'='*50}")
        print(f"  {name} ({code}) - {year}年 财务分析摘要")
        print(f"{'='*50}")
        print(f"  综合评分: {health['score']}/100 ({health['level']})")
        print(f"{'-'*30}")

        key_items = [
            ("ROE", latest.get("roe"), "%", "roe"),
            ("毛利率", latest.get("gross_margin"), "%", "gross_margin"),
            ("净利率", latest.get("net_margin"), "%", "net_margin"),
            ("营收增长率", latest.get("revenue_growth"), "%", "revenue_growth"),
            ("净利增长率", latest.get("net_profit_growth"), "%", "net_profit_growth"),
            ("资产负债率", latest.get("debt_ratio"), "%", "debt_ratio"),
            ("流动比率", latest.get("current_ratio"), "", "current_ratio"),
            ("总资产周转率", latest.get("asset_turnover"), "", "asset_turnover"),
        ]

        for label, val, unit, key in key_items:
            trend_info = trends.get(key, {})
            direction = trend_info.get("direction", "")
            val_str = f"{val:.2f}{unit}" if val is not None and not (isinstance(val, float) and (val != val)) else "N/A"
            print(f"  {label:　<8s}: {val_str:　>12s}  {direction}")

        print(f"{'='*50}\n")


# ======================================================================
# 命令行接口
# ======================================================================

def interactive_mode():
    """交互式菜单模式"""
    print("=" * 50)
    print("    📊 财报分析工具")
    print("    支持 A 股上市公司财务数据分析")
    print("=" * 50)

    fetcher = FinancialStatementFetcher()

    # 输入股票代码或名称
    while True:
        user_input = input("\n请输入股票代码或公司名称 (输入 q 退出): ").strip()
        if user_input.lower() == "q":
            print("再见!")
            sys.exit(0)

        if not user_input:
            continue

        # 判断是代码还是名称
        if user_input.isdigit() and len(user_input) == 6:
            symbol = user_input
            company_name = ""
        else:
            # 模糊搜索
            print(f"搜索 '{user_input}' ...")
            result = fetcher.search_company(user_input)
            if result is None or result.empty:
                print(f"未找到与 '{user_input}' 相关的公司，请重试")
                continue
            print("\n搜索结果:")
            for i, (_, row) in enumerate(result.iterrows(), 1):
                print(f"  {i}. {row['code']} - {row['name']}")
            if len(result) == 1:
                symbol = result.iloc[0]["code"]
                company_name = result.iloc[0]["name"]
                print(f"自动选择: {symbol} {company_name}")
            else:
                choice = input("请选择序号 (默认 1): ").strip()
                try:
                    idx = (int(choice) - 1) if choice else 0
                    row = result.iloc[idx]
                    symbol = row["code"]
                    company_name = row["name"]
                except (ValueError, IndexError):
                    print("无效选择")
                    continue

        # 选择年份
        years_input = input(f"分析最近几年? (默认 {DEFAULT_YEARS}): ").strip()
        years = int(years_input) if years_input.isdigit() else DEFAULT_YEARS

        # 是否导出 PDF
        pdf_choice = input("是否导出 PDF? (y/n, 默认 n): ").strip().lower()
        export_pdf = pdf_choice == "y"

        # 运行分析
        print("\n开始分析，请稍候...")
        pipeline = FinancialAnalysisPipeline(years=years, export_pdf=export_pdf)
        try:
            pipeline.run(symbol, company_name)
        except Exception as e:
            logger.error(f"分析失败: {e}")
            print(f"\n❌ 分析失败: {e}")
            continue

        # 继续?
        again = input("\n是否继续分析其他公司? (y/n, 默认 n): ").strip().lower()
        if again != "y":
            print("再见!")
            break


def main():
    parser = argparse.ArgumentParser(
        description="📊 A股上市公司财报分析工具",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  python test.py                         交互式菜单
  python test.py -s 300750               分析宁德时代
  python test.py -s 600519 --years 5     分析茅台近 5 年
  python test.py -s 300750,000858        批量分析
  python test.py -s 300750 --pdf         同时导出 PDF
        """,
    )
    parser.add_argument(
        "-s", "--symbol",
        help="股票代码，多个用逗号分隔 (如 300750,600519)",
    )
    parser.add_argument(
        "--years", type=int, default=DEFAULT_YEARS,
        help=f"分析最近 N 年数据 (默认: {DEFAULT_YEARS})",
    )
    parser.add_argument(
        "--pdf", action="store_true",
        help="同时导出 PDF 报告 (需要 weasyprint 或 wkhtmltopdf)",
    )
    parser.add_argument(
        "--name",
        help="公司名称 (可选，不提供则自动获取)",
    )
    parser.add_argument(
        "--no-browser", action="store_true",
        help="不在浏览器中打开报告",
    )

    args = parser.parse_args()

    # 交互模式
    if not args.symbol:
        interactive_mode()
        return

    # 批量模式
    symbols = [s.strip().zfill(6) for s in args.symbol.split(",")]

    pipeline = FinancialAnalysisPipeline(years=args.years, export_pdf=args.pdf)

    if len(symbols) == 1:
        pipeline.run(symbols[0], args.name or "")
    else:
        pipeline.run_batch(symbols)


if __name__ == "__main__":
    main()
