"""
CSV/Excel 导出器 — 跨境电商版
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
            "平台", "标题", "价格", "原价", "币种",
            "运费", "成色", "销量", "评分", "评论数",
            "卖家", "卖家评分", "发货地", "分类", "链接", "更新时间",
        ]

        with open(filepath, "w", newline="", encoding="utf-8-sig") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()

            for p in products:
                writer.writerow({
                    "平台": p.platform,
                    "标题": p.title,
                    "价格": f"${p.price:.2f}" if p.price else p.price_range,
                    "原价": f"${p.original_price:.2f}" if p.original_price else "",
                    "币种": p.currency,
                    "运费": f"${p.shipping_cost:.2f}" if p.shipping_cost else "包邮",
                    "成色": p.condition,
                    "销量": p.display_sales(),
                    "评分": f"{p.rating:.1f}" if p.rating else "",
                    "评论数": p.review_count,
                    "卖家": p.shop_name,
                    "卖家评分": f"{p.seller_rating:.1f}%" if p.seller_rating else "",
                    "发货地": p.location,
                    "分类": p.category,
                    "链接": p.url,
                    "更新时间": p.last_updated,
                })

        logger.info(f"CSV exported: {filepath} ({len(products)} rows)")
        return filepath

    def export_products_to_excel(
        self, products: List[Product], filename: str = "", sheet_name: str = "Products",
    ) -> str:
        """导出商品列表为 Excel"""
        if not filename:
            filename = f"products_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
        filepath = os.path.join(self.output_dir, filename)

        data = []
        for p in products:
            data.append({
                "平台": p.platform,
                "标题": p.title,
                "价格": p.price if p.price else "",
                "价格区间": p.price_range,
                "原价": p.original_price if p.original_price else "",
                "币种": p.currency,
                "运费": p.shipping_cost,
                "成色": p.condition,
                "销量": p.sales_count,
                "销量文本": p.sales_text,
                "评分": p.rating,
                "评论数": p.review_count,
                "卖家": p.shop_name,
                "卖家评分": p.seller_rating,
                "发货地": p.location,
                "分类": p.category,
                "链接": p.url,
                "更新时间": p.last_updated,
            })

        df = pd.DataFrame(data)

        with pd.ExcelWriter(filepath, engine="openpyxl") as writer:
            df.to_excel(writer, sheet_name=sheet_name or "商品列表", index=False)
            ws = writer.sheets[sheet_name]
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
                ws.column_dimensions[col_letter].width = min(max_len + 4, 60)

        logger.info(f"Excel exported: {filepath} ({len(products)} rows)")
        return filepath

    def export_price_history_to_csv(
        self, product_name: str, records: List[PriceRecord], filename: str = "",
    ) -> str:
        """导出价格历史为 CSV"""
        if not filename:
            safe_name = product_name[:20].replace(" ", "_")
            filename = f"price_history_{safe_name}_{datetime.now().strftime('%Y%m%d')}.csv"
        filepath = os.path.join(self.output_dir, filename)

        with open(filepath, "w", newline="", encoding="utf-8-sig") as f:
            writer = csv.writer(f)
            writer.writerow(["日期", "价格", "原价", "币种"])
            for r in records:
                writer.writerow([r.recorded_at, r.price, r.original_price, r.currency])

        logger.info(f"Price history CSV exported: {filepath}")
        return filepath

    def export_reviews_to_csv(
        self, reviews: List[Review], filename: str = "",
    ) -> str:
        """导出评论为 CSV"""
        if not filename:
            filename = f"reviews_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        filepath = os.path.join(self.output_dir, filename)

        with open(filepath, "w", newline="", encoding="utf-8-sig") as f:
            writer = csv.writer(f)
            writer.writerow([
                "评论者", "评分", "标题", "内容",
                "已验证购买", "有用数", "情感分", "情感标签", "日期",
            ])
            for r in reviews:
                # Translate sentiment labels
                label_map = {"positive": "正面", "neutral": "中性", "negative": "负面"}
                sentiment_label = label_map.get(r.sentiment_label, r.sentiment_label)
                writer.writerow([
                    r.reviewer_name, r.rating, r.title, r.content,
                    "是" if r.verified_purchase else "否",
                    r.helpful_count, f"{r.sentiment_score:.3f}",
                    sentiment_label, r.review_date,
                ])

        logger.info(f"Reviews CSV exported: {filepath}")
        return filepath

    def export_selection_report_to_excel(
        self, products: List[Product], scores: List[float], ranks: List[int],
        filename: str = "",
    ) -> str:
        """导出选品分析报告为 Excel"""
        if not filename:
            filename = f"selection_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
        filepath = os.path.join(self.output_dir, filename)

        data = []
        for p, score, rank in sorted(zip(products, scores, ranks), key=lambda x: x[2]):
            level = "★ 推荐" if score >= 80 else ("△ 可考虑" if score >= 60 else "× 不建议")
            data.append({
                "排名": rank,
                "等级": level,
                "评分": f"{score:.1f}",
                "标题": p.title,
                "价格": f"${p.price:.2f}" if p.price else p.price_range,
                "销量": p.display_sales(),
                "评价": p.display_rating(),
                "卖家": p.shop_name,
                "发货地": p.location,
                "分类": p.category,
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

        logger.info(f"Selection report exported: {filepath}")
        return filepath
