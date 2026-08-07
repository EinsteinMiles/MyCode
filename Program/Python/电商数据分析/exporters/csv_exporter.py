"""
CSV/Excel 导出器
支持 CSV 和 Excel (openpyxl) 格式，多 sheet，格式化
"""

import csv
import os
from typing import List, Dict, Any, Optional
from datetime import datetime

import pandas as pd

from config import CSV_DIR, logger
from core.models import Product, PriceRecord, Review


class CsvExporter:
    """CSV/Excel 导出"""

    def __init__(self, output_dir: str = CSV_DIR):
        self.output_dir = output_dir
        os.makedirs(output_dir, exist_ok=True)

    def export_products_to_csv(
        self, products: List[Product], filename: str = ""
    ) -> str:
        """导出商品列表为 CSV"""
        if not filename:
            filename = f"products_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        filepath = os.path.join(self.output_dir, filename)

        fieldnames = [
            "平台", "商品标题", "价格", "原价", "销量", "店铺",
            "所在地", "品类", "起批量", "商品链接", "更新时间",
        ]

        with open(filepath, "w", newline="", encoding="utf-8-sig") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()

            for p in products:
                writer.writerow({
                    "平台": p.platform,
                    "商品标题": p.title,
                    "价格": f"¥{p.price:.2f}" if p.price else p.price_range,
                    "原价": f"¥{p.original_price:.2f}" if p.original_price else "",
                    "销量": p.display_sales(),
                    "店铺": p.shop_name,
                    "所在地": p.location,
                    "品类": p.category,
                    "起批量": p.moq if p.moq else "",
                    "商品链接": p.url,
                    "更新时间": p.last_updated,
                })

        logger.info(f"CSV 已导出: {filepath} ({len(products)} 条)")
        return filepath

    def export_products_to_excel(
        self,
        products: List[Product],
        filename: str = "",
        sheet_name: str = "商品列表",
    ) -> str:
        """导出商品列表为 Excel（带格式化）"""
        if not filename:
            filename = f"products_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
        filepath = os.path.join(self.output_dir, filename)

        data = []
        for p in products:
            data.append({
                "平台": p.platform,
                "商品标题": p.title,
                "价格": p.price if p.price else "",
                "价格区间": p.price_range,
                "原价": p.original_price if p.original_price else "",
                "销量": p.sales_count if p.sales_count else p.sales_text,
                "店铺": p.shop_name,
                "所在地": p.location,
                "品类": p.category,
                "起批量": p.moq if p.moq else "",
                "商品链接": p.url,
                "更新时间": p.last_updated,
            })

        df = pd.DataFrame(data)

        with pd.ExcelWriter(filepath, engine="openpyxl") as writer:
            df.to_excel(writer, sheet_name=sheet_name, index=False)

            # 格式化
            ws = writer.sheets[sheet_name]
            ws.freeze_panes = "A2"  # 冻结首行
            ws.auto_filter.ref = ws.dimensions  # 自动筛选

            # 自适应列宽
            for col in ws.columns:
                max_len = 0
                col_letter = col[0].column_letter
                for cell in col:
                    try:
                        max_len = max(max_len, len(str(cell.value or "")))
                    except Exception:
                        pass
                ws.column_dimensions[col_letter].width = min(max_len + 4, 60)

        logger.info(f"Excel 已导出: {filepath} ({len(products)} 条)")
        return filepath

    def export_price_history_to_csv(
        self,
        product_name: str,
        records: List[PriceRecord],
        filename: str = "",
    ) -> str:
        """导出价格历史为 CSV"""
        if not filename:
            safe_name = product_name[:20].replace(" ", "_")
            filename = f"price_history_{safe_name}_{datetime.now().strftime('%Y%m%d')}.csv"
        filepath = os.path.join(self.output_dir, filename)

        with open(filepath, "w", newline="", encoding="utf-8-sig") as f:
            writer = csv.writer(f)
            writer.writerow(["记录时间", "价格(¥)", "原价(¥)"])
            for r in records:
                writer.writerow([r.recorded_at, r.price, r.original_price])

        logger.info(f"价格历史 CSV 已导出: {filepath}")
        return filepath

    def export_reviews_to_csv(
        self,
        reviews: List[Review],
        filename: str = "",
    ) -> str:
        """导出评论为 CSV"""
        if not filename:
            filename = f"reviews_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        filepath = os.path.join(self.output_dir, filename)

        with open(filepath, "w", newline="", encoding="utf-8-sig") as f:
            writer = csv.writer(f)
            writer.writerow(["评论内容", "评分", "情感评分", "情感标签", "评论日期"])
            for r in reviews:
                writer.writerow([
                    r.content, r.rating, f"{r.sentiment_score:.3f}",
                    r.sentiment_label, r.review_date,
                ])

        logger.info(f"评论 CSV 已导出: {filepath}")
        return filepath

    def export_selection_report_to_excel(
        self,
        products: List[Product],
        scores: List[float],
        ranks: List[int],
        filename: str = "",
    ) -> str:
        """导出选品分析报告为 Excel（多 sheet）"""
        if not filename:
            filename = f"选品分析_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
        filepath = os.path.join(self.output_dir, filename)

        data = []
        for p, score, rank in sorted(
            zip(products, scores, ranks), key=lambda x: x[2]
        ):
            level = "⭐ 推荐" if score >= 80 else ("△ 可考虑" if score >= 60 else "× 不推荐")
            data.append({
                "排名": rank,
                "推荐等级": level,
                "综合评分": f"{score:.1f}",
                "商品标题": p.title,
                "价格": f"¥{p.price:.2f}" if p.price else p.price_range,
                "销量": p.display_sales(),
                "店铺": p.shop_name,
                "所在地": p.location,
                "品类": p.category,
                "链接": p.url,
            })

        df = pd.DataFrame(data)

        with pd.ExcelWriter(filepath, engine="openpyxl") as writer:
            df.to_excel(writer, sheet_name="选品分析", index=False)
            ws = writer.sheets["选品分析"]
            ws.freeze_panes = "A2"
            ws.auto_filter.ref = ws.dimensions

            for col in ws.columns:
                max_len = 0
                col_letter = col[0].column_letter
                for cell in col:
                    try:
                        max_len = max(max_len, len(str(cell.value or "")))
                    except Exception:
                        pass
                ws.column_dimensions[col_letter].width = min(max_len + 4, 80)

        logger.info(f"选品分析报告已导出: {filepath}")
        return filepath
