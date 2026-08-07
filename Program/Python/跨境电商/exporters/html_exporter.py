"""
HTML 报告生成器 — 跨境电商版
内联 CSS + base64 嵌入图表 + KPI 卡片 + 响应式设计
"""

import os
import base64
from typing import List, Dict, Any, Optional
from datetime import datetime

from config import HTML_DIR, logger
from core.models import Product, PriceRecord, Review


class HtmlExporter:
    """HTML 报告生成"""

    def __init__(self, output_dir: str = HTML_DIR):
        self.output_dir = output_dir
        os.makedirs(output_dir, exist_ok=True)

    # ── 辅助方法 ──────────────────────────────────────

    @staticmethod
    def _img_to_base64(path: str) -> str:
        """将图片文件编码为 base64 嵌入 HTML"""
        if not path or not os.path.exists(path):
            return ""
        with open(path, "rb") as f:
            return base64.b64encode(f.read()).decode("utf-8")

    @staticmethod
    def _kpi_card(label: str, value: str, color: str = "#4A90D9") -> str:
        return f"""
        <div class="kpi-card" style="background:{color}">
            <div class="kpi-value">{value}</div>
            <div class="kpi-label">{label}</div>
        </div>"""

    def _build_base_html(self, title: str, body: str) -> str:
        return f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{title}</title>
<style>
    * {{ margin: 0; padding: 0; box-sizing: border-box; }}
    body {{ font-family: -apple-system, BlinkMacSystemFont, 'PingFang SC', 'Microsoft YaHei', 'Segoe UI', Roboto, sans-serif; background: #f5f7fa; color: #333; padding: 20px; }}
    .container {{ max-width: 1200px; margin: 0 auto; }}
    h1 {{ font-size: 24px; margin-bottom: 20px; color: #1a1a2e; }}
    h2 {{ font-size: 18px; margin: 24px 0 12px; color: #16213e; border-bottom: 2px solid #4A90D9; padding-bottom: 6px; }}
    .header {{ background: linear-gradient(135deg, #1a1a2e, #16213e); color: white; padding: 30px; border-radius: 12px; margin-bottom: 24px; }}
    .header h1 {{ color: white; margin-bottom: 8px; }}
    .header .subtitle {{ opacity: 0.7; font-size: 14px; }}
    .kpi-row {{ display: flex; gap: 16px; flex-wrap: wrap; margin-bottom: 24px; }}
    .kpi-card {{ flex: 1; min-width: 160px; padding: 20px; border-radius: 10px; color: white; text-align: center; }}
    .kpi-value {{ font-size: 28px; font-weight: 700; }}
    .kpi-label {{ font-size: 12px; opacity: 0.85; margin-top: 4px; letter-spacing: 0.5px; }}
    .chart-row {{ display: flex; gap: 16px; flex-wrap: wrap; margin-bottom: 20px; }}
    .chart-card {{ flex: 1; min-width: 350px; background: white; border-radius: 10px; padding: 16px; box-shadow: 0 2px 8px rgba(0,0,0,0.06); }}
    .chart-card img {{ width: 100%; height: auto; border-radius: 4px; }}
    table {{ width: 100%; border-collapse: collapse; background: white; border-radius: 10px; overflow: hidden; box-shadow: 0 2px 8px rgba(0,0,0,0.06); }}
    th {{ background: #1a1a2e; color: white; padding: 10px 12px; text-align: left; font-size: 12px; }}
    td {{ padding: 8px 12px; border-bottom: 1px solid #eee; font-size: 13px; }}
    tr:hover td {{ background: #f8f9ff; }}
    .badge {{ display: inline-block; padding: 2px 8px; border-radius: 4px; font-size: 11px; font-weight: 600; }}
    .badge-success {{ background: #d4edda; color: #155724; }}
    .badge-warning {{ background: #fff3cd; color: #856404; }}
    .badge-danger {{ background: #f8d7da; color: #721c24; }}
    .badge-info {{ background: #d1ecf1; color: #0c5460; }}
    .pain-points {{ display: flex; flex-wrap: wrap; gap: 8px; }}
    .pain-tag {{ background: #fff3cd; color: #856404; padding: 4px 10px; border-radius: 20px; font-size: 12px; }}
    .footer {{ text-align: center; margin-top: 30px; padding: 16px; color: #999; font-size: 12px; }}
</style>
</head>
<body>
<div class="container">
{body}
<div class="footer">跨境电商数据分析报告 | 生成时间 {datetime.now().strftime('%Y-%m-%d %H:%M')}</div>
</div>
</body>
</html>"""

    # ── 价格监控报告 ─────────────────────────────────

    def build_price_monitor_report(
        self, products: List[Product], stats: Dict[str, Any],
        alerts: List[Dict[str, Any]], chart_files: List[str],
    ) -> str:
        now = datetime.now().strftime('%Y-%m-%d %H:%M')
        body = f"""
<div class="header">
    <h1>📊 价格监控报告</h1>
    <div class="subtitle">生成时间: {now} | 监控商品数: {len(products)}</div>
</div>
"""

        # KPI 卡片
        up = sum(1 for a in alerts if a.get("direction") == "价格上涨")
        down = sum(1 for a in alerts if a.get("direction") == "价格下跌")
        avg_change = sum(a.get("change_pct", 0) for a in alerts) / len(alerts) if alerts else 0

        body += '<div class="kpi-row">'
        body += self._kpi_card("监控中", str(len(products)), "#4A90D9")
        body += self._kpi_card("价格下跌", str(down), "#28A745" if down > 0 else "#6C757D")
        body += self._kpi_card("价格上涨", str(up), "#DC3545" if up > 0 else "#6C757D")
        body += self._kpi_card("告警总数", str(len(alerts)), "#FD7E14" if alerts else "#6C757D")
        body += '</div>'

        # 图表
        if chart_files:
            body += '<h2>📈 价格趋势</h2><div class="chart-row">'
            for cf in chart_files:
                b64 = self._img_to_base64(cf)
                if b64:
                    body += f'<div class="chart-card"><img src="data:image/png;base64,{b64}" /></div>'
            body += '</div>'

        # 告警表格
        if alerts:
            body += f'<h2>⚠️ 价格告警 ({len(alerts)})</h2><table>'
            body += '<tr><th>商品</th><th>方向</th><th>变动</th><th>原价</th><th>现价</th><th>时间</th></tr>'
            for a in alerts:
                badge_class = "badge-danger" if a["direction"] == "价格上涨" else "badge-success"
                direction = "📈" if a["direction"] == "价格上涨" else "📉"
                body += f"""<tr>
                    <td>{a.get('title', '未知')[:60]}</td>
                    <td><span class="badge {badge_class}">{direction} {a['direction']}</span></td>
                    <td>{a['change_pct']}%</td>
                    <td>${a.get('old_price', 0):.2f}</td>
                    <td>${a.get('new_price', 0):.2f}</td>
                    <td>{a.get('time', '')}</td>
                </tr>"""
            body += '</table>'

        # 商品表格
        if products:
            body += f'<h2>📋 监控商品列表 ({len(products)})</h2><table>'
            body += '<tr><th>商品</th><th>平台</th><th>价格</th><th>销量</th><th>评分</th><th>更新时间</th></tr>'
            for p in products:
                body += f"""<tr>
                    <td>{p.title[:60]}</td>
                    <td>{p.platform.upper()}</td>
                    <td>{p.display_price()}</td>
                    <td>{p.display_sales()}</td>
                    <td>{p.display_rating()}</td>
                    <td>{p.last_updated}</td>
                </tr>"""
            body += '</table>'

        html = self._build_base_html("价格监控报告", body)
        filepath = os.path.join(self.output_dir, f"price_monitor_{datetime.now().strftime('%Y%m%d_%H%M%S')}.html")
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(html)
        logger.info(f"HTML 报告已生成: {filepath}")
        return filepath

    # ── 选品分析报告 ─────────────────────────────────

    def build_product_selection_report(
        self, products: List[Product], scores: List[float], ranks: List[int],
    ) -> str:
        now = datetime.now().strftime('%Y-%m-%d %H:%M')
        rec = sum(1 for s in scores if s >= 80)
        consider = sum(1 for s in scores if 60 <= s < 80)

        body = f"""
<div class="header">
    <h1>🎯 选品分析报告</h1>
    <div class="subtitle">生成时间: {now} | 分析商品数: {len(products)}</div>
</div>
<div class="kpi-row">
{self._kpi_card("★ 推荐", str(rec), "#28A745")}
{self._kpi_card("△ 可考虑", str(consider), "#FFC107")}
{self._kpi_card("× 不建议", str(len(products) - rec - consider), "#DC3545")}
{self._kpi_card("合计", str(len(products)), "#4A90D9")}
</div>"""

        body += f'<h2>🏆 商品排名</h2><table>'
        body += '<tr><th>排名</th><th>等级</th><th>评分</th><th>标题</th><th>价格</th><th>销量</th><th>评分</th><th>卖家</th></tr>'
        for p, s, r in sorted(zip(products, scores, ranks), key=lambda x: x[2]):
            if s >= 80:
                badge = '<span class="badge badge-success">★ 推荐</span>'
            elif s >= 60:
                badge = '<span class="badge badge-warning">△ 可考虑</span>'
            else:
                badge = '<span class="badge badge-danger">× 不建议</span>'
            body += f"""<tr>
                <td><strong>#{r}</strong></td>
                <td>{badge}</td>
                <td><strong>{s:.1f}</strong></td>
                <td>{p.title[:60]}</td>
                <td>{p.display_price()}</td>
                <td>{p.display_sales()}</td>
                <td>{p.display_rating()}</td>
                <td>{p.shop_name[:20]}</td>
            </tr>"""
        body += '</table>'

        html = self._build_base_html("选品分析报告", body)
        filepath = os.path.join(self.output_dir, f"selection_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.html")
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(html)
        logger.info(f"HTML 报告已生成: {filepath}")
        return filepath

    # ── 评论分析报告 ─────────────────────────────────

    def build_review_analysis_report(
        self, product_name: str, stats: Dict[str, Any],
        pain_points: List[tuple], chart_files: List[str],
    ) -> str:
        now = datetime.now().strftime('%Y-%m-%d %H:%M')
        positive_rate = stats.get("positive_rate", 0)

        body = f"""
<div class="header">
    <h1>💬 评论分析报告</h1>
    <div class="subtitle">商品: {product_name} | 生成时间: {now}</div>
</div>
<div class="kpi-row">
{self._kpi_card("评论总数", str(stats.get('total', 0)), "#4A90D9")}
{self._kpi_card("好评率", f"{positive_rate}%", "#28A745" if positive_rate >= 70 else "#FFC107")}
{self._kpi_card("平均情感", str(stats.get('avg_sentiment', 'N/A')), "#17A2B8")}
{self._kpi_card("痛点数量", str(len(pain_points)), "#DC3545" if pain_points else "#6C757D")}
</div>"""

        # 图表
        if chart_files:
            body += '<div class="chart-row">'
            for cf in chart_files:
                b64 = self._img_to_base64(cf)
                if b64:
                    body += f'<div class="chart-card"><img src="data:image/png;base64,{b64}" /></div>'
            body += '</div>'

        # 情感分布
        body += '<h2>📊 情感分布</h2><table>'
        body += '<tr><th>情感</th><th>数量</th><th>占比</th></tr>'
        total = stats.get("total", 1) or 1
        body += f'<tr><td><span class="badge badge-success">正面</span></td><td>{stats.get("positive", 0)}</td><td>{stats.get("positive", 0) / total * 100:.1f}%</td></tr>'
        body += f'<tr><td><span class="badge badge-warning">中性</span></td><td>{stats.get("neutral", 0)}</td><td>{stats.get("neutral", 0) / total * 100:.1f}%</td></tr>'
        body += f'<tr><td><span class="badge badge-danger">负面</span></td><td>{stats.get("negative", 0)}</td><td>{stats.get("negative", 0) / total * 100:.1f}%</td></tr>'
        body += '</table>'

        # 痛点
        if pain_points:
            body += f'<h2>🔍 用户痛点 (Top {len(pain_points)})</h2>'
            body += '<div class="pain-points">'
            for pp in pain_points[:20]:
                kw, freq, sent = pp if len(pp) == 3 else (pp[0], pp[1], 0)
                body += f'<span class="pain-tag">{kw} ({freq})</span>'
            body += '</div>'

        html = self._build_base_html("评论分析报告", body)
        filepath = os.path.join(self.output_dir, f"review_analysis_{datetime.now().strftime('%Y%m%d_%H%M%S')}.html")
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(html)
        logger.info(f"HTML 报告已生成: {filepath}")
        return filepath
