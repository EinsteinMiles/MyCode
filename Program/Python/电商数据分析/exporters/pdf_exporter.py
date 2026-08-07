"""
PDF 报告导出器
三引擎降级链：DrissionPage CDP → WeasyPrint → wkhtmltopdf
参考 财报分析/web_app.py::download_pdf() 模式
"""

import os
import shutil
import subprocess
from typing import Optional

from config import PDF_DIR, logger


class PdfExporter:
    """PDF 报告导出"""

    def __init__(self, output_dir: str = PDF_DIR):
        self.output_dir = output_dir
        os.makedirs(output_dir, exist_ok=True)

    def html_to_pdf(
        self,
        html_path: str,
        pdf_filename: str = "",
        browser_manager=None,
    ) -> Optional[str]:
        """
        HTML → PDF 转换（三引擎降级）
        参考 财报分析/web_app.py::download_pdf() 多引擎降级模式
        """
        if not os.path.exists(html_path):
            logger.error(f"HTML 文件不存在: {html_path}")
            return None

        if not pdf_filename:
            base = os.path.splitext(os.path.basename(html_path))[0]
            pdf_filename = f"{base}.pdf"

        pdf_path = os.path.join(self.output_dir, pdf_filename)
        abs_html = os.path.abspath(html_path)
        html_uri = f"file://{abs_html}"

        # ── 引擎 1：DrissionPage CDP (Chrome headless) ──
        if browser_manager:
            try:
                logger.info(f"PDF 引擎 1 (Chrome CDP): {html_path}")
                page = browser_manager.new_tab()
                page.get(html_uri)
                page.save(pdf_path)
                page.close_tabs()
                logger.info(f"PDF 已生成 (Chrome CDP): {pdf_path}")
                return pdf_path
            except Exception as e:
                logger.warning(f"PDF 引擎 1 失败: {e}")

        # ── 引擎 2：WeasyPrint ──
        try:
            from weasyprint import HTML
            logger.info(f"PDF 引擎 2 (WeasyPrint): {html_path}")
            HTML(filename=abs_html).write_pdf(pdf_path)
            logger.info(f"PDF 已生成 (WeasyPrint): {pdf_path}")
            return pdf_path
        except ImportError:
            logger.warning("WeasyPrint 未安装，跳过引擎 2")
        except Exception as e:
            logger.warning(f"PDF 引擎 2 失败: {e}")

        # ── 引擎 3：Chrome 命令行 ──
        chrome_paths = [
            "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
            "/Applications/Chromium.app/Contents/MacOS/Chromium",
            "/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge",
            shutil.which("google-chrome"),
            shutil.which("chromium"),
            shutil.which("chrome"),
        ]

        for chrome in chrome_paths:
            if chrome and os.path.exists(chrome):
                try:
                    logger.info(f"PDF 引擎 3 (Chrome headless): {chrome}")
                    subprocess.run(
                        [
                            chrome, "--headless", "--disable-gpu",
                            "--no-pdf-header-footer",
                            f"--print-to-pdf={pdf_path}",
                            html_uri,
                        ],
                        check=True, timeout=30, capture_output=True,
                    )
                    logger.info(f"PDF 已生成 (Chrome headless): {pdf_path}")
                    return pdf_path
                except Exception as e:
                    logger.warning(f"PDF 引擎 3 ({chrome}) 失败: {e}")

        # ── 引擎 4：wkhtmltopdf ──
        if shutil.which("wkhtmltopdf"):
            try:
                logger.info(f"PDF 引擎 4 (wkhtmltopdf): {html_path}")
                subprocess.run(
                    ["wkhtmltopdf", "--enable-local-file-access", html_path, pdf_path],
                    check=True, timeout=30, capture_output=True,
                )
                logger.info(f"PDF 已生成 (wkhtmltopdf): {pdf_path}")
                return pdf_path
            except Exception as e:
                logger.warning(f"PDF 引擎 4 失败: {e}")

        logger.error("所有 PDF 引擎均失败！请安装 WeasyPrint: pip install weasyprint")
        logger.info(f"提示：可以直接用浏览器打开 HTML 并打印为 PDF: {abs_html}")
        return None
