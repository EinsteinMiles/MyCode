"""
工具函数：文件查找、类型推断、进度显示、内存监控等
"""
import os
import glob
import sys
import time
from pathlib import Path
from typing import Callable, Optional
import pandas as pd

from config import SUPPORTED_READ_FORMATS, MAX_MEMORY_MB, logger


def find_files(directory: str = '.', patterns: list = None,
               recursive: bool = True) -> list[str]:
    """查找匹配的文件

    Args:
        directory: 搜索目录
        patterns: 文件扩展名列表，如 ['.xlsx', '.csv']，默认全部支持格式
        recursive: 是否递归搜索子目录

    Returns:
        匹配的文件路径列表
    """
    if patterns is None:
        patterns = list(SUPPORTED_READ_FORMATS.keys())

    files = []
    for pattern in patterns:
        search_pattern = f"*{pattern}"
        if recursive:
            search_pattern = f"**/{search_pattern}"

        full_pattern = os.path.join(directory, search_pattern)
        matched = glob.glob(full_pattern, recursive=recursive)
        # 过滤隐藏文件
        matched = [f for f in matched if not os.path.basename(f).startswith('.')]
        files.extend(matched)

    return sorted(files)


def get_file_info(path: str) -> dict:
    """获取文件信息"""
    stat = os.stat(path)
    ext = os.path.splitext(path)[1].lower()
    return {
        'path': path,
        'name': os.path.basename(path),
        'ext': ext,
        'format': SUPPORTED_READ_FORMATS.get(ext, '未知'),
        'size_mb': round(stat.st_size / (1024 * 1024), 2),
        'mtime': time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(stat.st_mtime)),
    }


def infer_type(series: pd.Series) -> str:
    """推断列的数据类型（比 pandas 更细粒度）

    Returns: 'int' | 'float' | 'datetime' | 'bool' | 'category' | 'string'
    """
    s = series.dropna()
    if len(s) == 0:
        return 'string'

    # 尝试转为数值
    if pd.api.types.is_integer_dtype(s):
        return 'int'
    if pd.api.types.is_float_dtype(s):
        return 'float'
    if pd.api.types.is_bool_dtype(s):
        return 'bool'
    if pd.api.types.is_datetime64_any_dtype(s):
        return 'datetime'

    # 尝试推断
    try:
        pd.to_numeric(s)
        return 'float'
    except (ValueError, TypeError):
        pass

    try:
        pd.to_datetime(s)
        return 'datetime'
    except (ValueError, TypeError):
        pass

    unique_ratio = s.nunique() / len(s)
    if unique_ratio < 0.1 and len(s) > 50:
        return 'category'

    return 'string'


def memory_usage(df: pd.DataFrame) -> float:
    """估算 DataFrame 内存占用 (MB)"""
    return df.memory_usage(deep=True).sum() / (1024 * 1024)


def check_memory(df: pd.DataFrame, warn: bool = True) -> bool:
    """检查内存是否超阈值，返回是否安全"""
    usage = memory_usage(df)
    if warn and usage > MAX_MEMORY_MB:
        logger.warning(f"内存占用 {usage:.1f}MB 超过阈值 {MAX_MEMORY_MB}MB")
        return False
    return True


def estimate_chunksize(path: str, ext: str) -> int:
    """根据文件大小估算合适的分块行数"""
    from config import CSV_CHUNKSIZE, EXCEL_CHUNKSIZE
    size_mb = os.path.getsize(path) / (1024 * 1024)

    if ext in ('.csv', '.tsv', '.txt'):
        return CSV_CHUNKSIZE
    elif ext in ('.xlsx', '.xls'):
        return EXCEL_CHUNKSIZE
    return CSV_CHUNKSIZE


def print_progress(current: int, total: int, label: str = "处理中"):
    """打印进度条"""
    pct = current / total * 100 if total > 0 else 100
    bar_len = 30
    filled = int(bar_len * current / total) if total > 0 else bar_len
    bar = '█' * filled + '░' * (bar_len - filled)
    sys.stdout.write(f"\r{label} [{bar}] {pct:.1f}% ({current}/{total})")
    sys.stdout.flush()
    if current >= total:
        print()


def parse_column_list(raw: str) -> list[str]:
    """解析用户输入的列名列表

    >>> parse_column_list("col1, col2 , col3")
    ['col1', 'col2', 'col3']
    """
    return [c.strip() for c in raw.split(',') if c.strip()]


def parse_filter_expr(raw: str) -> tuple[str, str, str]:
    """解析筛选表达式

    支持格式:
      "列名 > 100"
      "列名 == '文本'"
      "列名 contains '关键字'"

    Returns: (column, operator, value)
    """
    operators = ['>=', '<=', '!=', '==', '>', '<', 'contains', 'not contains',
                 'startswith', 'endswith']
    for op in sorted(operators, key=len, reverse=True):
        if f' {op} ' in raw:
            col, val = raw.split(f' {op} ', 1)
            return col.strip(), op, val.strip().strip("'\"")
    raise ValueError(f"无法解析筛选表达式: {raw}")


def safe_parse_value(val: str) -> any:
    """安全解析值，尝试转为数字"""
    val = val.strip()
    # 尝试整数
    try:
        return int(val)
    except ValueError:
        pass
    # 尝试浮点数
    try:
        return float(val)
    except ValueError:
        pass
    # 返回字符串
    return val


def timing(func: Callable) -> Callable:
    """装饰器：打印函数执行时间"""
    def wrapper(*args, **kwargs):
        start = time.time()
        result = func(*args, **kwargs)
        elapsed = time.time() - start
        logger.info(f"{func.__name__} 完成，耗时 {elapsed:.2f}s")
        return result
    return wrapper
