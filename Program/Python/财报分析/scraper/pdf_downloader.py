"""
PDF 下载器 - 从巨潮资讯网下载年报 PDF
"""

import os
import re
import logging
import requests
from typing import List, Optional
from config import DATA_DIR

logger = logging.getLogger(__name__)


class PDFDownloader:
    """
    年报 PDF 下载器
    从巨潮资讯网 (cninfo.com.cn) 下载上市公司年报 PDF
    """

    BASE_URL = "http://www.cninfo.com.cn/new/hisAnnouncement/query"
    DOWNLOAD_URL = "http://static.cninfo.com.cn/"

    def __init__(self, output_dir: str = None):
        self.output_dir = output_dir or os.path.join(DATA_DIR, "pdf_reports")
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                          "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "application/json, text/plain, */*",
            "Referer": "http://www.cninfo.com.cn/",
        })
        os.makedirs(self.output_dir, exist_ok=True)

    def _search_announcements(
        self,
        stock_code: str,
        keyword: str = "年度报告",
        page_num: int = 1,
        page_size: int = 30,
    ) -> dict:
        """
        搜索巨潮资讯网公告
        stock_code: 纯数字代码如 "300750"
        keyword: 搜索关键词
        """
        # 判断市场
        if stock_code.startswith(("60", "68")):
            stock_code_full = stock_code + ",SH"
        else:
            stock_code_full = stock_code + ",SZ"
        # 去掉前导零
        short_code = stock_code.lstrip("0") or "0"

        params = {
            "pageNum": page_num,
            "pageSize": page_size,
            "column": "szse",
            "tabName": "fulltext",
            "plate": "",
            "stock": f"{short_code},{stock_code_full}",
            "searchkey": keyword,
            "secid": "",
            "category": "",
            "trade": "",
            "seDate": "",
            "sortName": "declaredate",
            "sortType": "desc",
            "isHLtitle": "true",
        }

        try:
            resp = self.session.post(self.BASE_URL, data=params, timeout=30)
            resp.raise_for_status()
            return resp.json()
        except Exception as e:
            logger.error(f"搜索公告失败: {e}")
            return {}

    def download_annual_reports(
        self,
        symbol: str,
        years: Optional[List[str]] = None,
        max_reports: int = 5,
    ) -> List[str]:
        """
        下载指定公司的年报 PDF

        参数:
            symbol: 股票代码
            years: 年份列表，如 ["2023", "2024"]；None 表示下载最近 N 年
            max_reports: 最多下载几年

        返回:
            PDF 文件路径列表
        """
        symbol = str(symbol).strip().zfill(6)
        company_dir = os.path.join(self.output_dir, symbol)
        os.makedirs(company_dir, exist_ok=True)

        downloaded = []

        logger.info(f"搜索 {symbol} 的年度报告...")
        result = self._search_announcements(symbol, keyword="年度报告", page_size=50)

        announcements = result.get("announcements") or []
        if not announcements:
            logger.warning(f"未找到 {symbol} 的年度报告")
            return downloaded

        # 筛选年报并匹配年份
        count = 0
        for ann in announcements:
            title = ann.get("announcementTitle", "")
            adjunct_url = ann.get("adjunctUrl", "")
            ann_date = ann.get("announcementDate", "")

            # 过滤：必须是年报 PDF
            if not re.search(r"年度报告", title):
                continue
            if not adjunct_url.endswith(".pdf") and not adjunct_url.endswith(".PDF"):
                continue

            # 提取年份
            year_match = re.search(r"20\d{2}", title)
            if not year_match:
                year_match = re.search(r"20\d{2}", ann_date)
            if not year_match:
                continue
            report_year = year_match.group()

            # 年份过滤
            if years and report_year not in years:
                continue

            # 构建下载链接
            pdf_url = adjunct_url
            if not pdf_url.startswith("http"):
                pdf_url = self.DOWNLOAD_URL + pdf_url.lstrip("/")

            filename = f"{report_year}年报_{title}.pdf"[:100] + ".pdf"
            # 清理文件名非法字符
            filename = re.sub(r'[\\/:*?"<>|]', '_', filename)
            filepath = os.path.join(company_dir, filename)

            if os.path.exists(filepath):
                logger.info(f"已存在，跳过: {filename}")
                downloaded.append(filepath)
                count += 1
                if count >= max_reports:
                    break
                continue

            # 下载
            try:
                logger.info(f"下载: {title}")
                pdf_resp = self.session.get(pdf_url, timeout=120)
                pdf_resp.raise_for_status()

                with open(filepath, "wb") as f:
                    f.write(pdf_resp.content)

                logger.info(f"保存至: {filepath}")
                downloaded.append(filepath)
                count += 1

                if count >= max_reports:
                    break
            except Exception as e:
                logger.error(f"下载失败: {title} - {e}")

        logger.info(f"共下载 {len(downloaded)} 份年报")
        return downloaded
