"""
报告生成器 - 生成 HTML 财报分析报告，支持导出 PDF
"""

import os
import logging
import pandas as pd
import numpy as np
from typing import List, Dict, Optional
from datetime import datetime
import webbrowser

from config import REPORT_DIR, CHART_DIR, THRESHOLDS

logger = logging.getLogger(__name__)


class ReportBuilder:
    """HTML 财报分析报告构建器"""

    def __init__(self, output_dir: str = None):
        self.output_dir = output_dir or REPORT_DIR
        os.makedirs(self.output_dir, exist_ok=True)

    # ------------------------------------------------------------------
    # 辅助方法
    # ------------------------------------------------------------------

    @staticmethod
    def _color_for_value(name: str, value: float) -> str:
        """根据指标名称和值返回颜色"""
        if pd.isna(value):
            return "#999"
        threshold = THRESHOLDS.get(name, {})
        if not threshold:
            return "#333"
        if value >= threshold.get("excellent", float("inf")):
            return "#2E7D32"
        if value >= threshold.get("healthy", 0):
            return "#4CAF50"
        if value >= threshold.get("warning", float("-inf")):
            return "#FF9800"
        return "#F44336"

    @staticmethod
    def _format_value(value, fmt: str = ".2f") -> str:
        """安全格式化数值"""
        if pd.isna(value) or np.isinf(value):
            return "N/A"
        return f"{value:{fmt}}"

    @staticmethod
    def _indicator_tag(name: str, value: float, unit: str = "%") -> str:
        """生成一个指标 KPI 卡片 HTML"""
        color = ReportBuilder._color_for_value(name, value)
        display_val = f"{value:.2f}{unit}" if not pd.isna(value) else "N/A"
        cn_names = {
            "roe": "ROE", "roa": "ROA",
            "gross_margin": "毛利率", "net_margin": "净利率",
            "debt_ratio": "资产负债率", "current_ratio": "流动比率",
            "quick_ratio": "速动比率",
            "revenue_growth": "营收增长率", "net_profit_growth": "净利润增长率",
            "asset_turnover": "总资产周转率",
        }
        label = cn_names.get(name, name)
        return f"""
        <div class="indicator-card">
            <div class="indicator-label">{label}</div>
            <div class="indicator-value" style="color:{color}">{display_val}</div>
        </div>
        """

    # ------------------------------------------------------------------
    # HTML 报告生成
    # ------------------------------------------------------------------

    def build_html_report(
        self,
        company_name: str,
        stock_code: str,
        indicators: pd.DataFrame,
        chart_files: List[str],
        conclusion: str = "",
    ) -> str:
        """
        生成完整的 HTML 财报分析报告

        参数:
            company_name: 公司名称
            stock_code: 股票代码
            indicators: 指标 DataFrame（多行=多年）
            chart_files: 图表文件路径列表
            conclusion: 分析结论（Markdown 格式文本）
        返回: HTML 文件路径
        """
        if indicators.empty:
            raise ValueError("指标数据为空，无法生成报告")

        latest = indicators.iloc[-1]
        report_year = latest.get("year", datetime.now().year)

        # 提取图表文件名
        chart_names = {os.path.basename(f).replace(".png", ""): os.path.basename(f) for f in chart_files}

        # 构建 KPI 卡片
        kpi_cards = ""
        key_metrics = [
            ("roe", latest.get("roe"), "%"),
            ("roa", latest.get("roa"), "%"),
            ("gross_margin", latest.get("gross_margin"), "%"),
            ("net_margin", latest.get("net_margin"), "%"),
            ("revenue_growth", latest.get("revenue_growth"), "%"),
            ("net_profit_growth", latest.get("net_profit_growth"), "%"),
            ("debt_ratio", latest.get("debt_ratio"), "%"),
            ("current_ratio", latest.get("current_ratio"), ""),
        ]
        for name, val, unit in key_metrics:
            kpi_cards += self._indicator_tag(name, val, unit)

        # 构建历史数据表格
        table_rows = ""
        display_cols = ["year", "total_revenue", "net_profit", "roe", "roa",
                        "gross_margin", "net_margin", "revenue_growth",
                        "net_profit_growth", "debt_ratio", "current_ratio",
                        "asset_turnover"]
        col_labels = ["年份", "营收(亿)", "净利润(亿)", "ROE(%)", "ROA(%)",
                      "毛利率(%)", "净利率(%)", "营收增长(%)",
                      "净利增长(%)", "负债率(%)", "流动比率", "资产周转率"]

        for _, row in indicators.iterrows():
            cells = ""
            for col, fmt in zip(display_cols, ["d", ".2f", ".2f", ".2f", ".2f",
                                                ".2f", ".2f", ".2f", ".2f",
                                                ".2f", ".2f", ".2f"]):
                if col == "year":
                    cells += f"<td>{int(row.get(col, 0))}</td>"
                elif col in row:
                    val = row[col]
                    if pd.isna(val):
                        cells += "<td>N/A</td>"
                    else:
                        color = self._color_for_value(col, val) if col in THRESHOLDS else "#333"
                        cells += f'<td style="color:{color};font-weight:bold">{val:{fmt}}</td>'
                else:
                    cells += "<td>-</td>"
            table_rows += f"<tr>{cells}</tr>"

        # 图表 HTML（使用相对路径，嵌入时转为 data URI 或直接用文件路径）
        chart_sections = ""
        chart_section_map = {
            "revenue_profit_trend": "营收与利润趋势",
            "profitability": "盈利能力指标",
            "growth": "成长能力指标",
            "health_radar": "财务健康度雷达",
            "dupont": "杜邦分析",
            "balance_structure": "资产负债结构",
        }

        for key, title in chart_section_map.items():
            if key in chart_names:
                chart_sections += f"""
                <div class="chart-section">
                    <h2>{title}</h2>
                    <img src="{chart_names[key]}" alt="{title}" class="chart-img">
                </div>
                """

        # 结论 HTML（将 Markdown 格式简单转换）
        conclusion_html = conclusion.replace("\n", "<br>").replace("### ", "<h3>").replace("## ", "<h2>")

        # 完整 HTML
        html = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{company_name}({stock_code}) 财报分析报告</title>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{
            font-family: "PingFang SC", "Heiti SC", "Microsoft YaHei", sans-serif;
            background: #f5f7fa;
            color: #333;
            line-height: 1.6;
        }}
        .container {{ max-width: 1100px; margin: 0 auto; padding: 20px; }}
        .header {{
            background: linear-gradient(135deg, #1a237e, #283593);
            color: white;
            padding: 40px 30px;
            border-radius: 12px;
            margin-bottom: 25px;
            text-align: center;
        }}
        .header h1 {{ font-size: 28px; margin-bottom: 8px; }}
        .header .subtitle {{ font-size: 14px; opacity: 0.85; }}
        .kpi-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(130px, 1fr));
            gap: 12px;
            margin-bottom: 25px;
        }}
        .indicator-card {{
            background: white;
            border-radius: 10px;
            padding: 16px 12px;
            text-align: center;
            box-shadow: 0 2px 8px rgba(0,0,0,0.08);
        }}
        .indicator-label {{ font-size: 12px; color: #666; margin-bottom: 6px; }}
        .indicator-value {{ font-size: 22px; font-weight: 700; }}
        .chart-section {{
            background: white;
            border-radius: 12px;
            padding: 25px;
            margin-bottom: 20px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.08);
        }}
        .chart-section h2 {{
            font-size: 18px;
            margin-bottom: 15px;
            color: #1a237e;
            border-left: 4px solid #1a237e;
            padding-left: 12px;
        }}
        .chart-img {{ width: 100%; height: auto; border-radius: 6px; }}
        table {{
            width: 100%;
            border-collapse: collapse;
            margin: 20px 0;
            font-size: 13px;
        }}
        th, td {{
            padding: 10px 8px;
            text-align: center;
            border-bottom: 1px solid #e0e0e0;
        }}
        th {{
            background: #1a237e;
            color: white;
            font-weight: 600;
            position: sticky;
            top: 0;
        }}
        tr:hover {{ background: #f5f5f5; }}
        .conclusion {{
            background: white;
            border-radius: 12px;
            padding: 25px;
            margin-bottom: 20px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.08);
        }}
        .conclusion h2 {{
            font-size: 20px;
            color: #1a237e;
            margin-bottom: 15px;
        }}
        .conclusion h3 {{
            font-size: 16px;
            color: #283593;
            margin: 15px 0 8px;
        }}
        .footer {{
            text-align: center;
            padding: 20px;
            color: #999;
            font-size: 12px;
        }}
        /* PDF 导出工具栏 - 页面底部 */
        .toolbar {{
            text-align: center;
            padding: 30px 0;
            margin: 20px 0;
            display: flex; gap: 16px;
            justify-content: center;
            flex-wrap: wrap;
        }}
        .toolbar button {{
            padding: 12px 32px; border: none; border-radius: 10px;
            font-size: 15px; font-weight: 600; cursor: pointer;
            transition: all 0.2s; box-shadow: 0 2px 8px rgba(0,0,0,0.12);
        }}
        .btn-pdf {{
            background: #1a237e; color: white;
        }}
        .btn-pdf:hover {{ transform: translateY(-2px); box-shadow: 0 4px 16px rgba(26,35,126,0.4); }}
        .btn-back {{
            background: white; color: #1a237e; border: 1px solid #ccc !important;
        }}
        @media print {{
            body {{ background: white; }}
            .toolbar {{ display: none !important; }}
            .chart-section, .indicator-card, .conclusion {{ box-shadow: none; break-inside: avoid; }}
            .chart-section {{ page-break-inside: avoid; }}
            .header {{ background: #1a237e !important; -webkit-print-color-adjust: exact; print-color-adjust: exact; }}
            th {{ background: #1a237e !important; -webkit-print-color-adjust: exact; print-color-adjust: exact; }}
        }}
    </style>
</head>
<body>
    <div class="container">
        <!-- 头部 -->
        <div class="header">
            <h1>{company_name} ({stock_code})</h1>
            <div class="subtitle">
                财报分析报告 | 数据年份: {int(report_year)} | 生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M')}
            </div>
        </div>

        <!-- 关键指标卡片 -->
        <h2 style="margin-bottom:12px;color:#1a237e;">📊 关键财务指标</h2>
        <div class="kpi-grid">
            {kpi_cards}
        </div>

        <!-- 历史数据表 -->
        <div class="chart-section">
            <h2>📋 历年财务数据一览</h2>
            <div style="overflow-x:auto;">
                <table>
                    <thead>
                        <tr>{''.join(f'<th>{l}</th>' for l in col_labels)}</tr>
                    </thead>
                    <tbody>
                        {table_rows}
                    </tbody>
                </table>
            </div>
        </div>

        <!-- 图表 -->
        {chart_sections}

        <!-- 分析结论 -->
        <div class="conclusion">
            {conclusion_html}
        </div>

        <!-- PDF 导出工具栏 -->
        <div class="toolbar">
            <button class="btn-pdf" onclick="printPDF()">🖨️ 打印 PDF</button>
            <button class="btn-pdf" onclick="downloadPDF()" id="btnDownload">📥 下载 PDF</button>
            <button class="btn-back" onclick="history.back()">← 返回查询</button>
        </div>

        <!-- 页脚 -->
        <div class="footer">
            本报告由财报分析工具自动生成 | 数据来源: 东方财富 / akshare | 仅供参考，不构成投资建议
        </div>
    </div>

    <script>
    function printPDF() {{
        // 浏览器打印 → macOS 可选"另存为 PDF"
        window.print();
    }}

    function downloadPDF() {{
        var btn = document.getElementById('btnDownload');
        btn.textContent = '⏳ 生成中...';
        btn.disabled = true;

        // 尝试服务端生成
        var formData = new FormData();
        formData.append('filename', '{stock_code}_{company_name}_财报分析报告.html');

        fetch('/download-pdf', {{
            method: 'POST',
            body: formData
        }})
        .then(function(resp) {{
            if (!resp.ok) {{
                // 服务端失败 → 降级为浏览器打印
                btn.textContent = '📥 下载 PDF';
                btn.disabled = false;
                alert('服务端 PDF 生成失败，请使用"打印 PDF"按钮，在打印对话框中选择"另存为 PDF"');
                return;
            }}
            return resp.blob();
        }})
        .then(function(blob) {{
            if (!blob) return;
            var url = window.URL.createObjectURL(blob);
            var a = document.createElement('a');
            a.href = url;
            a.download = '{stock_code}_{company_name}_财报分析报告.pdf';
            document.body.appendChild(a);
            a.click();
            a.remove();
            window.URL.revokeObjectURL(url);
            btn.textContent = '✅ 下载完成';
            btn.disabled = false;
        }})
        .catch(function() {{
            btn.textContent = '📥 下载 PDF';
            btn.disabled = false;
            alert('下载失败，请使用"打印 PDF"按钮');
        }});
    }}
    </script>
</body>
</html>"""

        # 保存 HTML
        filename = f"{stock_code}_{company_name}_财报分析报告.html"
        filepath = os.path.join(self.output_dir, filename)
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(html)

        logger.info(f"HTML 报告已生成: {filepath}")
        return filepath

    # ------------------------------------------------------------------
    # PDF 导出
    # ------------------------------------------------------------------

    def export_pdf(self, html_path: str) -> Optional[str]:
        """
        将 HTML 报告导出为 PDF
        需要安装 weasyprint: pip install weasyprint
        或者 wkhtmltopdf 作为后备
        """
        pdf_path = html_path.rsplit(".", 1)[0] + ".pdf"

        # 方法 1: weasyprint
        try:
            from weasyprint import HTML
            HTML(filename=html_path).write_pdf(pdf_path)
            logger.info(f"PDF 报告已生成 (weasyprint): {pdf_path}")
            return pdf_path
        except ImportError:
            logger.warning("weasyprint 未安装，尝试 wkhtmltopdf...")
        except Exception as e:
            logger.warning(f"weasyprint 生成 PDF 失败: {e}")

        # 方法 2: wkhtmltopdf
        try:
            import subprocess
            result = subprocess.run(
                ["wkhtmltopdf", "--enable-local-file-access", html_path, pdf_path],
                capture_output=True, timeout=60,
            )
            if result.returncode == 0:
                logger.info(f"PDF 报告已生成 (wkhtmltopdf): {pdf_path}")
                return pdf_path
            else:
                logger.error(f"wkhtmltopdf 失败: {result.stderr.decode()}")
        except FileNotFoundError:
            logger.warning("wkhtmltopdf 未安装")
        except Exception as e:
            logger.error(f"PDF 导出失败: {e}")

        return None

    # ------------------------------------------------------------------
    # 快捷方法：一键生成报告
    # ------------------------------------------------------------------

    def generate_full_report(
        self,
        company_name: str,
        stock_code: str,
        indicators: pd.DataFrame,
        chart_files: List[str],
        conclusion: str = "",
        export_pdf: bool = False,
        open_browser: bool = True,
    ) -> str:
        """
        一键生成完整报告（HTML + 可选 PDF）
        返回 HTML 文件路径
        """
        # 复制图表文件到报告目录
        import shutil
        for chart_path in chart_files:
            if os.path.exists(chart_path):
                shutil.copy2(chart_path, os.path.join(self.output_dir, os.path.basename(chart_path)))

        html_path = self.build_html_report(
            company_name=company_name,
            stock_code=stock_code,
            indicators=indicators,
            chart_files=chart_files,
            conclusion=conclusion,
        )

        if export_pdf:
            self.export_pdf(html_path)

        if open_browser:
            webbrowser.open("file://" + os.path.abspath(html_path))

        return html_path
