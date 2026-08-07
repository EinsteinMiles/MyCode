"""
数据清洗：缺失值处理、异常值检测、去重、格式清理
"""
import pandas as pd
import numpy as np

from config import logger


def handle_missing(df: pd.DataFrame, strategy: str = 'auto',
                   fill_value=None, columns: list[str] = None) -> pd.DataFrame:
    """统一处理缺失值

    Args:
        df: DataFrame
        strategy: 'drop' | 'fill' | 'auto'
            - auto: 缺失率>50%删除列, 否则数值列填中位数, 文本列填众数
        fill_value: strategy='fill' 时的填充值
        columns: 指定处理的列 (None=全部列)
    """
    if columns is None:
        columns = df.columns.tolist()

    result = df.copy()

    missing_report = {}
    for col in columns:
        missing_count = result[col].isna().sum()
        missing_pct = missing_count / len(result) * 100
        if missing_count > 0:
            missing_report[col] = {'count': missing_count, 'pct': round(missing_pct, 1)}

    if missing_report:
        logger.info(f"缺失值检测: {len(missing_report)} 列存在缺失")
        for col, info in missing_report.items():
            logger.info(f"  {col}: {info['count']} ({info['pct']}%)")

    if strategy == 'drop':
        result = result.dropna(subset=columns)
        logger.info(f"已删除含缺失值的行, 剩余 {len(result)} 行")

    elif strategy == 'fill':
        for col in columns:
            if result[col].isna().any():
                result[col] = result[col].fillna(fill_value)
        logger.info(f"已用 {fill_value} 填充缺失值")

    elif strategy == 'auto':
        for col in columns:
            miss_pct = result[col].isna().sum() / len(result) * 100
            if miss_pct > 50:
                result = result.drop(columns=[col])
                logger.info(f"  列 {col} 缺失率 {miss_pct:.1f}% > 50%，删除该列")
            elif miss_pct > 0:
                if pd.api.types.is_numeric_dtype(result[col]):
                    fill_val = result[col].median()
                    result[col] = result[col].fillna(fill_val)
                    logger.info(f"  列 {col}: 用中位数 {fill_val} 填充")
                else:
                    mode_vals = result[col].mode()
                    fill_val = mode_vals[0] if len(mode_vals) > 0 else '缺失'
                    result[col] = result[col].fillna(fill_val)
                    logger.info(f"  列 {col}: 用众数 '{fill_val}' 填充")

    return result


def drop_missing(df: pd.DataFrame, threshold: float = 0.5,
                 axis: str = 'row') -> pd.DataFrame:
    """按阈值删除缺失值

    Args:
        threshold: 缺失率阈值 (0-1)
        axis: 'row'=删除行, 'col'=删除列
    """
    if axis == 'col':
        cols_to_drop = df.columns[df.isna().mean() > threshold]
        result = df.drop(columns=cols_to_drop)
        logger.info(f"删除 {len(cols_to_drop)} 列 (缺失率>{threshold*100}%)")
    else:
        result = df.dropna(thresh=int(df.shape[1] * (1 - threshold)))
        logger.info(f"删除缺失率>{threshold*100}%的行, 剩余 {len(result)} 行")
    return result


def fill_missing(df: pd.DataFrame, method: str = 'ffill',
                 columns: list[str] = None) -> pd.DataFrame:
    """按方法填充缺失值

    Args:
        method: 'ffill'(前向填充) | 'bfill'(后向填充) | 'mean' | 'median' | 'mode' | 'zero'
    """
    result = df.copy()
    if columns is None:
        columns = df.columns.tolist()

    for col in columns:
        if not result[col].isna().any():
            continue
        if method in ('ffill', 'bfill'):
            result[col] = result[col].fillna(method=method)
        elif method == 'mean' and pd.api.types.is_numeric_dtype(result[col]):
            result[col] = result[col].fillna(result[col].mean())
        elif method == 'median' and pd.api.types.is_numeric_dtype(result[col]):
            result[col] = result[col].fillna(result[col].median())
        elif method == 'mode':
            m = result[col].mode()
            result[col] = result[col].fillna(m[0] if len(m) > 0 else 0)
        elif method == 'zero':
            result[col] = result[col].fillna(0)
        elif method == 'interpolate':
            result[col] = result[col].interpolate()

    logger.info(f"缺失值填充完成: method={method}")
    return result


def detect_outliers(df: pd.DataFrame, column: str,
                    method: str = 'iqr') -> pd.Series:
    """检测异常值

    Args:
        method: 'iqr' (IQR方法) | 'zscore' (Z分数) | 'percentile' (百分位)
        column: 检测列

    Returns:
        bool Series (True=异常值)
    """
    if method == 'iqr':
        Q1 = df[column].quantile(0.25)
        Q3 = df[column].quantile(0.75)
        IQR = Q3 - Q1
        lower = Q1 - 1.5 * IQR
        upper = Q3 + 1.5 * IQR
        outliers = (df[column] < lower) | (df[column] > upper)
        logger.info(f"IQR异常值 [{column}]: {outliers.sum()} 个 "
                    f"(范围 [{lower:.2f}, {upper:.2f}])")

    elif method == 'zscore':
        z = (df[column] - df[column].mean()) / df[column].std()
        outliers = z.abs() > 3
        logger.info(f"Z-score异常值 [{column}]: {outliers.sum()} 个 (|z|>3)")

    elif method == 'percentile':
        lower = df[column].quantile(0.01)
        upper = df[column].quantile(0.99)
        outliers = (df[column] < lower) | (df[column] > upper)
        logger.info(f"百分位异常值 [{column}]: {outliers.sum()} 个 (1%-99%)")

    return outliers


def remove_outliers(df: pd.DataFrame, columns: list[str],
                    method: str = 'iqr') -> pd.DataFrame:
    """移除异常值行"""
    mask = pd.Series(False, index=df.index)
    for col in columns:
        if pd.api.types.is_numeric_dtype(df[col]):
            mask = mask | detect_outliers(df, col, method)
    result = df[~mask].copy()
    logger.info(f"移除异常值: {len(df)} → {len(result)} 行")
    return result


def drop_duplicates_custom(df: pd.DataFrame, subset: list[str] = None,
                           keep: str = 'first') -> pd.DataFrame:
    """删除重复行"""
    before = len(df)
    result = df.drop_duplicates(subset=subset, keep=keep)
    logger.info(f"去重: 删除 {before - len(result)} 行")
    return result


def strip_whitespace(df: pd.DataFrame, columns: list[str] = None) -> pd.DataFrame:
    """去除字符串列前后空白"""
    result = df.copy()
    if columns is None:
        columns = df.select_dtypes(include=['object', 'string']).columns

    for col in columns:
        if pd.api.types.is_string_dtype(result[col]) or result[col].dtype == object:
            result[col] = result[col].str.strip()
    logger.info(f"已清理 {len(columns)} 列的空白字符")
    return result


def clean_column_names(df: pd.DataFrame) -> pd.DataFrame:
    """清理列名：去除空白、特殊字符、统一命名"""
    result = df.copy()
    new_names = {}
    for col in result.columns:
        new = str(col).strip()
        new = new.replace('\n', '').replace('\r', '')
        new = new.replace('（', '(').replace('）', ')')
        new = new.replace('　', ' ')  # 全角空格
        new = ' '.join(new.split())  # 合并连续空格
        if new != col:
            new_names[col] = new
    if new_names:
        result = result.rename(columns=new_names)
        logger.info(f"已清理 {len(new_names)} 个列名")
    return result


def standardize_values(df: pd.DataFrame, column: str,
                       mapping: dict) -> pd.DataFrame:
    """标准化枚举值（统一不同写法）

    Example:
        standardize_values(df, '性别', {'男': '男性', 'M': '男性', '女': '女性', 'F': '女性'})
    """
    result = df.copy()
    result[column] = result[column].map(mapping).fillna(result[column])
    logger.info(f"已标准化 [{column}] 列值: {len(mapping)} 个映射")
    return result
