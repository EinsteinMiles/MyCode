"""
数据处理工具 - 全局配置
"""
import os
import logging

# --- 路径常量 ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
OUTPUT_DIR = os.path.join(BASE_DIR, 'output')
CHART_DIR = os.path.join(OUTPUT_DIR, 'charts')
REPORT_DIR = os.path.join(OUTPUT_DIR, 'reports')
CLEAN_DIR = os.path.join(OUTPUT_DIR, 'cleaned')

# 自动创建输出目录
for _dir in (OUTPUT_DIR, CHART_DIR, REPORT_DIR, CLEAN_DIR):
    os.makedirs(_dir, exist_ok=True)

# --- 文件处理配置 ---
DEFAULT_ENCODING = 'utf-8'
FALLBACK_ENCODINGS = ['utf-8', 'gbk', 'gb2312', 'gb18030', 'latin-1']
CSV_CHUNKSIZE = 100_000       # CSV 分块读取行数
EXCEL_CHUNKSIZE = 50_000      # Excel 分块读取行数
MAX_MEMORY_MB = 500           # 内存预警阈值

# --- 可视化配置 ---
CHART_DPI = 150
CHART_FIGSIZE = (12, 6)
CHART_STYLE = 'seaborn-v0_8-darkgrid'
FONT_FAMILY = ['Arial Unicode MS', 'SimHei', 'WenQuanYi Micro Hei', 'sans-serif']

# --- 日志配置 ---
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger('DataProcessor')

# --- 支持的文件格式 ---
SUPPORTED_READ_FORMATS = {
    '.xlsx': 'Excel (OpenXML)',
    '.xls': 'Excel (97-2003)',
    '.csv': 'CSV (逗号分隔)',
    '.tsv': 'TSV (制表符分隔)',
    '.txt': '文本文件',
    '.json': 'JSON',
    '.docx': 'Word 文档',
}

SUPPORTED_WRITE_FORMATS = ['.xlsx', '.csv', '.json', '.txt']
