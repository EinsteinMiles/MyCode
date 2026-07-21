#!/usr/bin/env python3
"""
财报分析 - Web 应用
启动 Web 服务器，在浏览器中交互式查询和分析上市公司财报

用法:
    python web_app.py                 # 默认 http://localhost:5000
    python web_app.py --port 8080     # 指定端口
"""

import sys
import os
import re
import shutil
import subprocess
import argparse
import logging
import threading
import webbrowser

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from flask import Flask, request, render_template_string, send_from_directory, jsonify

from scraper.fetcher import FinancialStatementFetcher
from cleaner.parser import DataCleaner, DataMerger
from cleaner.indicators import IndicatorCalculator
from cleaner.analyzer import ReportAnalyzer
from display.charts import ChartGenerator
from display.report import ReportBuilder
from config import DEFAULT_YEARS, CHART_DIR, REPORT_DIR

# --- 日志 ---
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("财报分析Web")

# --- Flask App ---
app = Flask(__name__)

# --- 工具函数 ---

def format_large_number(val, unit="亿"):
    """将数值格式化为带单位的字符串"""
    if val is None or (isinstance(val, float) and (val != val)):
        return "N/A"
    if abs(val) >= 1e8:
        return f"{val / 1e8:.2f} 亿"
    elif abs(val) >= 1e4:
        return f"{val / 1e4:.2f} 万"
    else:
        return f"{val:.2f}"


SEARCH_PAGE = """<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>财报分析工具</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: "PingFang SC", "Heiti SC", "Microsoft YaHei", sans-serif;
            background: linear-gradient(135deg, #0d1b2a 0%, #1b2838 30%, #1a237e 70%, #283593 100%);
            min-height: 100vh;
            display: flex;
            align-items: center;
            justify-content: center;
            color: #333;
        }
        .page-container {
            width: 100%;
            max-width: 900px;
            padding: 20px;
        }

        /* 头部 */
        .hero {
            text-align: center;
            margin-bottom: 40px;
        }
        .hero h1 {
            font-size: 42px;
            color: #ffffff;
            font-weight: 800;
            letter-spacing: 2px;
            margin-bottom: 8px;
        }
        .hero .subtitle {
            font-size: 16px;
            color: rgba(255,255,255,0.7);
            font-weight: 300;
        }

        /* 搜索卡片 */
        .search-card {
            background: #ffffff;
            border-radius: 20px;
            padding: 40px;
            box-shadow: 0 20px 60px rgba(0,0,0,0.3);
        }
        .search-card h3 {
            font-size: 20px;
            color: #1a237e;
            margin-bottom: 24px;
            text-align: center;
        }

        /* 输入组 */
        .input-group {
            display: flex;
            gap: 12px;
            margin-bottom: 16px;
            flex-wrap: wrap;
        }
        .input-group input {
            flex: 1;
            min-width: 200px;
            padding: 14px 20px;
            font-size: 16px;
            border: 2px solid #e0e0e0;
            border-radius: 12px;
            outline: none;
            transition: border-color 0.3s, box-shadow 0.3s;
        }
        .input-group input:focus {
            border-color: #1a237e;
            box-shadow: 0 0 0 3px rgba(26,35,126,0.1);
        }
        .input-group select {
            padding: 14px 16px;
            font-size: 16px;
            border: 2px solid #e0e0e0;
            border-radius: 12px;
            outline: none;
            background: white;
            cursor: pointer;
            min-width: 100px;
        }
        .input-group select:focus {
            border-color: #1a237e;
        }

        /* 按钮 */
        .btn-row {
            display: flex;
            gap: 12px;
            flex-wrap: wrap;
        }
        .btn {
            flex: 1;
            min-width: 120px;
            padding: 14px 28px;
            font-size: 16px;
            font-weight: 600;
            border: none;
            border-radius: 12px;
            cursor: pointer;
            transition: all 0.3s;
            letter-spacing: 1px;
        }
        .btn-primary {
            background: linear-gradient(135deg, #1a237e, #283593);
            color: white;
            flex: 2;
        }
        .btn-primary:hover {
            transform: translateY(-2px);
            box-shadow: 0 8px 25px rgba(26,35,126,0.4);
        }
        .btn-outline {
            background: white;
            color: #1a237e;
            border: 2px solid #1a237e;
        }
        .btn-outline:hover {
            background: #f5f5ff;
        }

        /* 示例标签 */
        .examples {
            margin-top: 20px;
            display: flex;
            gap: 8px;
            flex-wrap: wrap;
            justify-content: center;
        }
        .example-tag {
            padding: 6px 14px;
            background: #f0f2ff;
            color: #1a237e;
            border-radius: 20px;
            font-size: 13px;
            cursor: pointer;
            border: none;
            transition: all 0.2s;
        }
        .example-tag:hover {
            background: #1a237e;
            color: white;
        }

        /* Loading */
        .loading-overlay {
            display: none;
            position: fixed;
            top: 0; left: 0;
            width: 100%; height: 100%;
            background: rgba(0,0,0,0.6);
            z-index: 999;
            align-items: center;
            justify-content: center;
        }
        .loading-overlay.active {
            display: flex;
        }
        .loading-box {
            background: white;
            border-radius: 16px;
            padding: 40px;
            text-align: center;
            box-shadow: 0 20px 60px rgba(0,0,0,0.3);
        }
        .spinner {
            width: 48px; height: 48px;
            border: 4px solid #e0e0e0;
            border-top: 4px solid #1a237e;
            border-radius: 50%;
            animation: spin 1s linear infinite;
            margin: 0 auto 16px;
        }
        @keyframes spin {
            to { transform: rotate(360deg); }
        }
        .loading-text {
            font-size: 16px;
            color: #333;
        }
        .loading-detail {
            font-size: 13px;
            color: #999;
            margin-top: 6px;
        }
    </style>
</head>
<body>

    <!-- Loading overlay -->
    <div class="loading-overlay" id="loadingOverlay">
        <div class="loading-box">
            <div class="spinner"></div>
            <div class="loading-text">正在分析财报数据...</div>
            <div class="loading-detail" id="loadingDetail">正在获取数据...</div>
        </div>
    </div>

    <div class="page-container">
        <!-- Hero -->
        <div class="hero">
            <h1>📊 财报分析</h1>
            <div class="subtitle">A股上市公司财务数据分析 · 一键生成可视化报告</div>
        </div>

        <!-- Search Card -->
        <div class="search-card">
            <h3>输入股票代码或公司名称</h3>

            <form id="searchForm" action="/analyze" method="POST" target="_blank">
                <div class="input-group">
                    <input type="text" name="query" id="queryInput"
                           placeholder="例如: 300750 或 宁德时代"
                           autocomplete="off" required autofocus>
                    <select name="years" id="yearsSelect">
                        <option value="3">3年</option>
                        <option value="5" selected>5年</option>
                        <option value="10">10年</option>
                        <option value="0">全部</option>
                    </select>
                </div>
                <div class="btn-row">
                    <button type="submit" class="btn btn-primary">🔍 开始分析</button>
                    <button type="button" class="btn btn-outline" id="luckyBtn">🎲 随机看一个</button>
                </div>
            </form>

            <div class="examples">
                <span style="color:#999;font-size:13px;line-height:30px;">热门:</span>
                <button class="example-tag" onclick="fillQuery('300750')">宁德时代</button>
                <button class="example-tag" onclick="fillQuery('600519')">贵州茅台</button>
                <button class="example-tag" onclick="fillQuery('000858')">五粮液</button>
                <button class="example-tag" onclick="fillQuery('002594')">比亚迪</button>
                <button class="example-tag" onclick="fillQuery('601899')">紫金矿业</button>
                <button class="example-tag" onclick="fillQuery('300059')">东方财富</button>
                <button class="example-tag" onclick="fillQuery('688981')">中芯国际</button>
            </div>
        </div>
    </div>

    <script>
        function fillQuery(value) {
            document.getElementById('queryInput').value = value;
            document.getElementById('queryInput').focus();
        }

        // 表单提交时显示 loading
        document.getElementById('searchForm').addEventListener('submit', function(e) {
            document.getElementById('loadingOverlay').classList.add('active');
            document.getElementById('loadingDetail').textContent = '正在获取财务数据...';

            // 模拟进度更新
            setTimeout(() => { document.getElementById('loadingDetail').textContent = '正在计算财务指标...'; }, 2000);
            setTimeout(() => { document.getElementById('loadingDetail').textContent = '正在生成图表...'; }, 4000);
            setTimeout(() => { document.getElementById('loadingDetail').textContent = '正在生成报告...'; }, 6000);

            // 30 秒后自动隐藏（超时保护）
            setTimeout(() => {
                document.getElementById('loadingOverlay').classList.remove('active');
            }, 30000);
        });

        // 随机按钮
        document.getElementById('luckyBtn').addEventListener('click', function() {
            var stocks = ['300750','600519','000858','002594','601899','300059','000333',
                          '002415','600036','601318','000001','002230','600276','300124'];
            var pick = stocks[Math.floor(Math.random() * stocks.length)];
            document.getElementById('queryInput').value = pick;
            document.getElementById('searchForm').submit();
        });

        // 回车提交
        document.getElementById('queryInput').addEventListener('keydown', function(e) {
            if (e.key === 'Enter') {
                e.preventDefault();
                document.getElementById('searchForm').submit();
            }
        });
    </script>
</body>
</html>"""


# ======================================================================
# Flask 路由
# ======================================================================

@app.route("/")
def index():
    """搜索首页"""
    return render_template_string(SEARCH_PAGE)


@app.route("/analyze", methods=["POST"])
def analyze():
    """
    接收查询请求，运行完整分析流程，返回 HTML 报告
    """
    query = request.form.get("query", "").strip()
    years_str = request.form.get("years", "5")
    years = int(years_str) if years_str.isdigit() else DEFAULT_YEARS

    if not query:
        return "<h2>请输入股票代码或公司名称</h2>", 400

    logger.info(f"查询请求: {query}, 年份: {years}")

    fetcher = FinancialStatementFetcher()

    # ---- 解析输入：代码 or 名称 ----
    symbol = None
    company_name = ""

    if query.isdigit() and len(query) == 6:
        symbol = query.zfill(6)
        if not FinancialStatementFetcher.validate_stock_code(symbol):
            return f"<h2>无效的股票代码: {symbol}</h2>", 400
    else:
        # 模糊搜索
        result = fetcher.search_company(query)
        if result is None or result.empty:
            return f"<h2>未找到与 '{query}' 相关的公司</h2><p>请尝试输入完整的股票代码（如 300750）</p>", 404

        if len(result) > 30:
            return f"<h2>'{query}' 匹配结果太多（{len(result)} 个）</h2><p>请输入更精确的名称或使用股票代码</p>", 400

        # 如果只有 1 个结果，直接使用
        if len(result) == 1:
            row = result.iloc[0]
            symbol = str(row["code"]).zfill(6)
            company_name = row["name"]
        else:
            # 多个结果：显示选择列表
            options_html = ""
            for _, row in result.iterrows():
                code = str(row["code"]).zfill(6)
                name = row["name"]
                options_html += f"""
                <div style="padding:12px;margin:6px 0;background:#f5f7fa;border-radius:8px;
                            cursor:pointer;transition:0.2s;"
                     onmouseover="this.style.background='#e8eaf6'"
                     onmouseout="this.style.background='#f5f7fa'"
                     onclick="window.open('/analyze', '_blank')">
                    <form action="/analyze" method="POST" target="_blank" style="margin:0;">
                        <input type="hidden" name="query" value="{code}">
                        <input type="hidden" name="years" value="{years}">
                        <button type="submit" style="background:none;border:none;cursor:pointer;
                                font-size:15px;width:100%;text-align:left;padding:0;color:#333;">
                            <strong>{code}</strong> — {name}
                        </button>
                    </form>
                </div>"""
            return f"""
            <html lang="zh-CN">
            <head><meta charset="UTF-8"><title>选择公司</title></head>
            <body style="font-family:'PingFang SC','Microsoft YaHei',sans-serif;
                         max-width:600px;margin:60px auto;padding:20px;">
                <h2 style="color:#1a237e;">搜索结果: "{query}"</h2>
                <p style="color:#666;">找到 {len(result)} 家公司，请点击选择:</p>
                {options_html}
            </body></html>"""

    if not symbol:
        return "<h2>无法定位公司，请检查输入</h2>", 400

    # ---- 运行分析流水线 ----
    try:
        from config import CHART_DIR, REPORT_DIR
        import os
        os.makedirs(CHART_DIR, exist_ok=True)
        os.makedirs(REPORT_DIR, exist_ok=True)

        # 1. 数据获取
        logger.info(f"开始分析: {symbol}")
        statements = fetcher.fetch_all_statements(symbol)

        if all(df.empty for df in statements.values()):
            return f"<h2>未能获取到 {symbol} 的财务数据</h2><p>请检查股票代码是否正确</p>", 500

        # 获取公司名称
        if not company_name:
            try:
                info = fetcher.fetch_company_info(symbol)
                company_name = info.get("股票简称", symbol)
            except Exception:
                company_name = symbol

        # 2. 数据清洗
        cleaner = DataCleaner(unit="yi")
        cleaned = cleaner.clean_all(statements)

        # 3. 指标计算
        calculator = IndicatorCalculator()
        indicators = calculator.calculate_all(cleaned)

        if indicators.empty:
            return f"<h2>数据清洗后无有效数据</h2>", 500

        # 按年份筛选
        if years > 0 and "year" in indicators.columns:
            available_years = sorted(indicators["year"].dropna().unique())
            if len(available_years) > years:
                cutoff = available_years[-years]
                indicators = indicators[indicators["year"] >= cutoff]

        # 4. 图表 + 分析
        chart_gen = ChartGenerator()
        chart_files = chart_gen.generate_all(indicators)

        analyzer = ReportAnalyzer()
        conclusion = analyzer.generate_conclusion(indicators, company_name)

        # 5. 生成报告
        reporter = ReportBuilder()
        for chart_path in chart_files:
            if os.path.exists(chart_path):
                shutil.copy2(chart_path, os.path.join(REPORT_DIR, os.path.basename(chart_path)))

        html_path = reporter.build_html_report(
            company_name=company_name,
            stock_code=symbol,
            indicators=indicators,
            chart_files=chart_files,
            conclusion=conclusion,
        )

        logger.info(f"分析完成: {html_path}")

        # 重定向到报告页面
        filename = os.path.basename(html_path)
        return f"""<!DOCTYPE html>
<html lang="zh-CN">
<head><meta charset="UTF-8">
<meta http-equiv="refresh" content="0;url=/reports/{filename}">
</head>
<body><p>报告已生成，正在跳转... <a href="/reports/{filename}">点击这里</a></p></body>
</html>"""

    except Exception as e:
        logger.error(f"分析失败: {e}", exc_info=True)
        return f"<h2>分析失败</h2><p>{e}</p><p>请稍后重试或联系管理员</p>", 500


@app.route("/reports/<path:filename>")
def serve_report(filename):
    """提供报告静态文件"""
    return send_from_directory(REPORT_DIR, filename)


@app.route("/charts/<path:filename>")
def serve_chart(filename):
    """提供图表文件"""
    return send_from_directory(CHART_DIR, filename)


@app.route("/download-pdf", methods=["POST"])
def download_pdf():
    """
    服务端 PDF 下载
    使用 Chrome 无头模式将 HTML 报告转为 PDF
    """
    filename = request.form.get("filename", "")
    if not filename:
        return "缺少文件名", 400

    html_path = os.path.join(REPORT_DIR, filename)
    if not os.path.exists(html_path):
        return "报告文件不存在", 404

    pdf_filename = filename.rsplit(".", 1)[0] + ".pdf"
    pdf_path = os.path.join(REPORT_DIR, pdf_filename)

    # 如果 PDF 已存在且比 HTML 新，直接返回
    if os.path.exists(pdf_path) and os.path.getmtime(pdf_path) >= os.path.getmtime(html_path):
        return send_from_directory(
            REPORT_DIR, pdf_filename,
            as_attachment=True, download_name=pdf_filename,
        )

    # ---- 方法1: Chrome 无头模式 ----
    chrome_paths = [
        "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
        "/Applications/Chromium.app/Contents/MacOS/Chromium",
        "google-chrome", "google-chrome-stable", "chromium", "chromium-browser",
    ]
    chrome = None
    for p in chrome_paths:
        if os.path.exists(p) or shutil.which(p):
            chrome = p
            break

    if chrome:
        try:
            file_url = "file://" + os.path.abspath(html_path)

            result = subprocess.run(
                [chrome, "--headless", "--disable-gpu", "--no-sandbox",
                 f"--print-to-pdf={os.path.abspath(pdf_path)}",
                 "--no-pdf-header-footer",
                 file_url],
                capture_output=True, timeout=30,
            )
            if result.returncode == 0 and os.path.exists(pdf_path):
                logger.info(f"Chrome PDF 生成成功: {pdf_filename}")
                return send_from_directory(
                    REPORT_DIR, pdf_filename,
                    as_attachment=True, download_name=pdf_filename,
                )
            else:
                logger.warning(f"Chrome PDF 失败: {result.stderr.decode()}")
        except Exception as e:
            logger.warning(f"Chrome 调用失败: {e}")

    # ---- 方法2: weasyprint ----
    try:
        from weasyprint import HTML

        with open(html_path, "r", encoding="utf-8") as f:
            html_content = f.read()

        html_content = re.sub(
            r'src="(?!http)([^"]+\.png)"',
            f'src="file://{REPORT_DIR}/\\1"',
            html_content,
        )

        HTML(string=html_content).write_pdf(pdf_path)
        logger.info(f"weasyprint PDF 生成成功: {pdf_filename}")
        return send_from_directory(
            REPORT_DIR, pdf_filename,
            as_attachment=True, download_name=pdf_filename,
        )
    except Exception as e:
        logger.warning(f"weasyprint 也失败: {e}")

    # 全部失败
    return "PDF 生成失败。请使用报告页面上的'打印 PDF'按钮，浏览器打印 → 另存为 PDF。", 500


# ======================================================================
# 启动
# ======================================================================

def main():
    parser = argparse.ArgumentParser(description="财报分析 Web 应用")
    parser.add_argument("--port", type=int, default=5000, help="Web 服务端口 (默认: 5000)")
    parser.add_argument("--no-browser", action="store_true", help="不自动打开浏览器")
    args = parser.parse_args()

    port = args.port
    url = f"http://localhost:{port}"

    print("=" * 55)
    print("  📊 财报分析 Web 应用")
    print(f"  地址: {url}")
    print(f"  按 Ctrl+C 停止服务")
    print("=" * 55)

    if not args.no_browser:
        # 延迟打开浏览器，等 Flask 启动完成
        def open_browser():
            import time
            time.sleep(1.0)
            webbrowser.open(url)
        threading.Thread(target=open_browser, daemon=True).start()

    app.run(host="0.0.0.0", port=port, debug=False)


if __name__ == "__main__":
    main()
