"""
PDF 报告生成器 — 跨境电商版
4-engine fallback chain: Chrome CDP → WeasyPrint → Chrome CLI → wkhtmltopdf
"""

import os
import subprocess
import shutil
from typing import Optional

from config import PDF_DIR, logger


class PdfExporter:
    """PDF 导出（多引擎降级）"""

    def __init__(self, output_dir: str = PDF_DIR):
        self.output_dir = output_dir
        os.makedirs(output_dir, exist_ok=True)

    def html_to_pdf(
        self, html_path: str, output_path: str = "", browser_manager=None,
    ) -> Optional[str]:
        """
        将 HTML 报告转换为 PDF
        尝试 4 种引擎，任意一种成功即返回
        """
        if not html_path or not os.path.exists(html_path):
            logger.warning(f"HTML 文件不存在: {html_path}")
            return None

        if not output_path:
            base = os.path.splitext(os.path.basename(html_path))[0]
            output_path = os.path.join(self.output_dir, f"{base}.pdf")

        # Strategy 1: Chrome CDP via DrissionPage (best quality)
        pdf_path = self._via_chrome_cdp(html_path, output_path, browser_manager)
        if pdf_path:
            return pdf_path

        # Strategy 2: WeasyPrint
        pdf_path = self._via_weasyprint(html_path, output_path)
        if pdf_path:
            return pdf_path

        # Strategy 3: Chrome/Chromium CLI
        pdf_path = self._via_chrome_cli(html_path, output_path)
        if pdf_path:
            return pdf_path

        # Strategy 4: wkhtmltopdf
        pdf_path = self._via_wkhtmltopdf(html_path, output_path)
        if pdf_path:
            return pdf_path

        logger.error("所有 PDF 引擎均失败")
        return None

    def _via_chrome_cdp(
        self, html_path: str, output_path: str, browser_manager=None,
    ) -> Optional[str]:
        """通过 Chrome DevTools Protocol 打印 PDF"""
        if browser_manager is None:
            return None

        try:
            from DrissionPage import ChromiumPage
            page = browser_manager.get_page()

            # 将 HTML 文件转为 file:// URL
            abs_path = os.path.abspath(html_path)
            file_url = f"file://{abs_path}"

            page.get(file_url)

            # 使用 Page.printToPDF CDP 命令
            pdf_data = page.run_cdp("Page.printToPDF", {
                "printBackground": True,
                "paperWidth": 8.27,   # A4
                "paperHeight": 11.69,
                "marginTop": 0.39,
                "marginBottom": 0.39,
                "marginLeft": 0.39,
                "marginRight": 0.39,
            })

            if pdf_data and "data" in pdf_data:
                import base64
                with open(output_path, "wb") as f:
                    f.write(base64.b64decode(pdf_data["data"]))
                logger.info(f"PDF generated (Chrome CDP): {output_path}")
                return output_path

        except Exception as e:
            logger.warning(f"Chrome CDP PDF 失败: {e}")

        return None

    def _via_weasyprint(self, html_path: str, output_path: str) -> Optional[str]:
        """通过 WeasyPrint 生成 PDF"""
        try:
            from weasyprint import HTML
            HTML(filename=html_path).write_pdf(output_path)
            logger.info(f"PDF generated (WeasyPrint): {output_path}")
            return output_path
        except ImportError:
            logger.debug("WeasyPrint 未安装")
        except Exception as e:
            logger.warning(f"WeasyPrint PDF 失败: {e}")
        return None

    def _via_chrome_cli(self, html_path: str, output_path: str) -> Optional[str]:
        """通过 Chrome/Chromium 命令行生成 PDF"""
        chrome_paths = [
            "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
            "/Applications/Chromium.app/Contents/MacOS/Chromium",
            "/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge",
            shutil.which("google-chrome"),
            shutil.which("chromium"),
            shutil.which("chromium-browser"),
        ]

        for chrome in chrome_paths:
            if not chrome or not os.path.exists(chrome):
                continue
            try:
                abs_html = os.path.abspath(html_path)
                subprocess.run(
                    [
                        chrome, "--headless", "--disable-gpu",
                        "--no-sandbox", "--print-to-pdf=" + os.path.abspath(output_path),
                        abs_html,
                    ],
                    check=True, timeout=30, capture_output=True,
                )
                if os.path.exists(output_path) and os.path.getsize(output_path) > 0:
                    logger.info(f"PDF generated (Chrome CLI): {output_path}")
                    return output_path
            except Exception:
                continue

        return None

    def _via_wkhtmltopdf(self, html_path: str, output_path: str) -> Optional[str]:
        """通过 wkhtmltopdf 生成 PDF"""
        wk = shutil.which("wkhtmltopdf")
        if not wk:
            return None
        try:
            subprocess.run(
                [wk, "--enable-local-file-access", html_path, output_path],
                check=True, timeout=30, capture_output=True,
            )
            if os.path.exists(output_path) and os.path.getsize(output_path) > 0:
                logger.info(f"PDF generated (wkhtmltopdf): {output_path}")
                return output_path
        except Exception as e:
            logger.warning(f"wkhtmltopdf PDF 失败: {e}")
        return None
