"""
HTML 报告导出器
Jinja2 模板 + base64 图片嵌入，独立可移植的 HTML 报告
"""

import os
import base64
from typing import List, Dict, Any, Optional
from datetime import datetime

from config import HTML_DIR, logger
from core.models import Product, PriceRecord, Review


def _img_to_b64(filepath: str) -> str:
    """将图片转为 base64 data URI"""
    if not filepath or not os.path.exists(filepath):
        return ""
    with open(filepath, "rb") as f:
        data = base64.b64encode(f.read()).decode("utf-8")
    ext = os.path.splitext(filepath)[1].lower().replace(".", "")
    return f"data:image/{ext};base64,{data}"


class HtmlExporter:
    """HTML 报告导出"""

    def __init__(self, output_dir: str = HTML_DIR):
        self.output_dir = output_dir
        os.makedirs(output_dir, exist_ok=True)

    @staticmethod
    def _base_template(title: str, body: str, style: str = "") -> str:
        """基础 HTML 骨架"""
        return f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{title}</title>
<style>
    * {{ margin: 0; padding: 0; box-sizing: border-box; }}
    body {{
        font-family: "PingFang SC", "Heiti SC", "Microsoft YaHei", sans-serif;
        color: #333; background: #f5f7fa;
        line-height: 1.6; padding: 20px;
    }}
    .container {{ max-width: 1100px; margin: 0 auto; }}
    .header {{
        background: linear-gradient(135deg, #4A90D9, #357ABD);
        color: white; padding: 30px 40px; border-radius: 12px 12px 0 0;
    }}
    .header h1 {{ font-size: 24px; margin-bottom: 8px; }}
    .header .meta {{ font-size: 14px; opacity: 0.85; }}
    .card {{
        background: white; border-radius: 0 0 12px 12px;
        padding: 30px; margin-bottom: 20px; box-shadow: 0 2px 8px rgba(0,0,0,0.08);
    }}
    .card-title {{
        font-size: 18px; font-weight: bold; margin-bottom: 20px;
        padding-bottom: 10px; border-bottom: 2px solid #4A90D9;
    }}
    table {{
        width: 100%; border-collapse: collapse; margin: 15px 0;
        font-size: 13px;
    }}
    th {{
        background: #4A90D9; color: white; padding: 12px 10px;
        text-align: left; font-weight: 500;
    }}
    td {{ padding: 10px; border-bottom: 1px solid #eee; }}
    tr:hover {{ background: #f8f9fa; }}
    .chart-img {{
        max-width: 100%; height: auto; margin: 15px 0;
        border-radius: 8px; box-shadow: 0 1px 4px rgba(0,0,0,0.1);
    }}
    .alert {{ padding: 12px 16px; border-radius: 6px; margin: 10px 0; font-size: 14px; }}
    .alert-danger {{ background: #FFF5F5; border-left: 4px solid #DC3545; color: #C53030; }}
    .alert-success {{ background: #F0FFF4; border-left: 4px solid #28A745; color: #276749; }}
    .alert-warning {{ background: #FFFFF0; border-left: 4px solid #FFC107; color: #975A16; }}
    .badge {{
        display: inline-block; padding: 3px 10px; border-radius: 12px;
        font-size: 12px; font-weight: 500;
    }}
    .badge-success {{ background: #C6F6D5; color: #276749; }}
    .badge-danger {{ background: #FED7D7; color: #C53030; }}
    .badge-warning {{ background: #FEFCBF; color: #975A16; }}
    .kpi-row {{ display: flex; gap: 20px; margin: 20px 0; flex-wrap: wrap; }}
    .kpi-card {{
        flex: 1; min-width: 150px; background: #f8f9fa;
        padding: 20px; border-radius: 8px; text-align: center;
    }}
    .kpi-value {{ font-size: 28px; font-weight: bold; color: #4A90D9; }}
    .kpi-label {{ font-size: 13px; color: #666; margin-top: 4px; }}
    .footer {{
        text-align: center; padding: 20px; color: #999; font-size: 12px;
    }}
    @media print {{
        body {{ background: white; padding: 0; }}
        .card {{ box-shadow: none; break-inside: avoid; }}
    }}
    {style}
</style>
</head>
<body>
<div class="container">
{body}
<div class="footer">电商数据分析系统 · 生成于 {datetime.now().strftime('%Y-%m-%d %H:%M')}</div>
</div>
</body>
</html>"""

    def build_price_monitor_report(
        self,
        products: List[Product],
        price_histories: Dict[int, List[PriceRecord]],
        alerts: List[Dict[str, Any]],
        chart_files: List[str] = None,
        filename: str = "",
    ) -> str:
        """构建价格监控报告"""
        if not filename:
            filename = f"price_monitor_{datetime.now().strftime('%Y%m%d_%H%M%S')}.html"
        filepath = os.path.join(self.output_dir, filename)

        # 构建 KPI
        total = len(products)
        alerted = len(alerts) if alerts else 0

        body_parts = [
            '<div class="header">',
            '<h1>📊 竞品价格监控报告</h1>',
            f'<div class="meta">监控商品数: {total} · 价格异动: {alerted} · {datetime.now().strftime("%Y-%m-%d %H:%M")}</div>',
            '</div>',
            '<div class="card">',
            '<div class="kpi-row">',
            f'<div class="kpi-card"><div class="kpi-value">{total}</div><div class="kpi-label">监控商品</div></div>',
            f'<div class="kpi-card"><div class="kpi-value">{alerted}</div><div class="kpi-label">价格异动</div></div>',
            '</div>',
        ]

        # 告警列表
        if alerts:
            body_parts.append('<div class="card-title">⚠️ 价格异动告警</div>')
            for alert in alerts:
                css_class = "danger" if alert.get("change_pct", 0) > 0 else "success"
                arrow = "↑" if alert.get("change_pct", 0) > 0 else "↓"
                body_parts.append(
                    f'<div class="alert alert-{css_class}">'
                    f'<strong>{alert.get("title", "")}</strong>: '
                    f'¥{alert.get("old_price", 0):.2f} → ¥{alert.get("new_price", 0):.2f} '
                    f'({arrow}{abs(alert.get("change_pct", 0)):.1f}%)'
                    f'</div>'
                )

        # 商品表格
        body_parts.append('<div class="card-title">📋 监控商品列表</div>')
        body_parts.append('<table><tr><th>商品</th><th>平台</th><th>当前价格</th><th>销量</th><th>店铺</th></tr>')
        for p in products:
            body_parts.append(
                f'<tr><td><a href="{p.url}" target="_blank">{p.title[:40]}</a></td>'
                f'<td>{p.platform}</td><td>{p.display_price()}</td>'
                f'<td>{p.display_sales()}</td><td>{p.shop_name}</td></tr>'
            )
        body_parts.append('</table>')

        # 图表嵌入
        if chart_files:
            body_parts.append('<div class="card-title">📈 价格趋势图</div>')
            for f in chart_files:
                b64 = _img_to_b64(f)
                if b64:
                    body_parts.append(f'<img class="chart-img" src="{b64}" alt="价格趋势">')

        body_parts.append('</div>')
        html = self._base_template("竞品价格监控报告", "\n".join(body_parts))

        with open(filepath, "w", encoding="utf-8") as f:
            f.write(html)

        logger.info(f"HTML 报告已导出: {filepath}")
        return filepath

    def build_review_analysis_report(
        self,
        product_name: str,
        stats: Dict[str, Any],
        pain_points: List[tuple],
        chart_files: List[str] = None,
        filename: str = "",
    ) -> str:
        """构建评论分析报告"""
        if not filename:
            safe_name = product_name[:20].replace(" ", "_")
            filename = f"review_analysis_{safe_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.html"
        filepath = os.path.join(self.output_dir, filename)

        body_parts = [
            '<div class="header">',
            '<h1>💬 评论分析报告</h1>',
            f'<div class="meta">{product_name} · {datetime.now().strftime("%Y-%m-%d %H:%M")}</div>',
            '</div>',
            '<div class="card">',
            '<div class="kpi-row">',
            f'<div class="kpi-card"><div class="kpi-value">{stats.get("total", 0)}</div><div class="kpi-label">评论总数</div></div>',
            f'<div class="kpi-card"><div class="kpi-value">{stats.get("positive", 0)}</div><div class="kpi-label">好评</div></div>',
            f'<div class="kpi-card"><div class="kpi-value">{stats.get("neutral", 0)}</div><div class="kpi-label">中评</div></div>',
            f'<div class="kpi-card"><div class="kpi-value">{stats.get("negative", 0)}</div><div class="kpi-label">差评</div></div>',
            '</div>',
        ]

        # 好评率
        total = stats.get("total", 0)
        if total > 0:
            praise_rate = stats.get("positive", 0) / total * 100
            body_parts.append(
                f'<div class="kpi-card" style="background:#E8F5E9">'
                f'<div class="kpi-value" style="color:#28A745">{praise_rate:.1f}%</div>'
                f'<div class="kpi-label">好评率</div></div>'
            )

        # 痛点
        if pain_points:
            body_parts.append('<div class="card-title">🔍 用户痛点关键词</div>')
            body_parts.append('<table><tr><th>关键词</th><th>频次</th><th>关联情感</th></tr>')
            for kw, freq, sent in pain_points[:20]:
                badge = "badge-danger" if sent < 0.4 else ("badge-warning" if sent < 0.6 else "badge-success")
                body_parts.append(
                    f'<tr><td>{kw}</td><td>{freq}</td>'
                    f'<td><span class="badge {badge}">{sent:.2f}</span></td></tr>'
                )
            body_parts.append('</table>')

        # 图表
        if chart_files:
            for f in chart_files:
                b64 = _img_to_b64(f)
                if b64:
                    body_parts.append(f'<img class="chart-img" src="{b64}" alt="分析图表">')

        body_parts.append('</div>')
        html = self._base_template("评论分析报告", "\n".join(body_parts))

        with open(filepath, "w", encoding="utf-8") as f:
            f.write(html)

        logger.info(f"HTML 报告已导出: {filepath}")
        return filepath

    def build_product_selection_report(
        self,
        products: List[Product],
        scores: List[float],
        ranks: List[int],
        chart_files: List[str] = None,
        filename: str = "",
    ) -> str:
        """构建选品分析报告"""
        if not filename:
            filename = f"selection_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.html"
        filepath = os.path.join(self.output_dir, filename)

        body_parts = [
            '<div class="header">',
            '<h1>🎯 选品分析报告</h1>',
            f'<div class="meta">共 {len(products)} 个商品 · {datetime.now().strftime("%Y-%m-%d %H:%M")}</div>',
            '</div>',
            '<div class="card">',
            '<div class="card-title">📋 选品推荐排名</div>',
            '<table><tr><th>排名</th><th>推荐</th><th>评分</th><th>商品</th><th>价格</th><th>销量</th><th>店铺</th></tr>',
        ]

        for p, score, rank in sorted(zip(products, scores, ranks), key=lambda x: x[2]):
            level = "⭐ 推荐" if score >= 80 else ("△ 可考虑" if score >= 60 else "× 不推荐")
            badge = "badge-success" if score >= 80 else ("badge-warning" if score >= 60 else "badge-danger")
            body_parts.append(
                f'<tr><td>#{rank}</td>'
                f'<td><span class="badge {badge}">{level}</span></td>'
                f'<td><strong>{score:.1f}</strong></td>'
                f'<td><a href="{p.url}" target="_blank">{p.title[:30]}</a></td>'
                f'<td>{p.display_price()}</td>'
                f'<td>{p.display_sales()}</td>'
                f'<td>{p.shop_name}</td></tr>'
            )
        body_parts.append('</table>')

        if chart_files:
            for f in chart_files:
                b64 = _img_to_b64(f)
                if b64:
                    body_parts.append(f'<img class="chart-img" src="{b64}" alt="分析图表">')

        body_parts.append('</div>')
        html = self._base_template("选品分析报告", "\n".join(body_parts))

        with open(filepath, "w", encoding="utf-8") as f:
            f.write(html)

        logger.info(f"HTML 报告已导出: {filepath}")
        return filepath
