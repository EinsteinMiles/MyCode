"""
描述统计与数据分析
"""
import pandas as pd
import numpy as np

from config import logger
from utils.helpers import infer_type


def describe_data(df: pd.DataFrame, percentiles: list = None) -> pd.DataFrame:
    """整体描述统计（数值列）

    Returns:
        包含 count/mean/std/min/percentiles/max 的 DataFrame
    """
    if percentiles is None:
        percentiles = [.01, .05, .25, .5, .75, .95, .99]

    numeric_cols = df.select_dtypes(include=[np.number]).columns
    result = df[numeric_cols].describe(percentiles=percentiles).round(2)
    logger.info(f"描述统计: {len(numeric_cols)} 个数值列")
    return result


def column_summary(df: pd.DataFrame, column: str) -> dict:
    """单列详细摘要

    Returns:
        {
            'dtype': 数据类型,
            'count': 总数,
            'missing': 缺失数,
            'missing_pct': 缺失比例,
            'unique': 唯一值数,
            'unique_pct': 唯一值比例,
            'top_values': [(值, 频次), ...],  # 前5
            'mean': ..., 'median': ..., 'std': ...,  # 数值列
            'min': ..., 'max': ...,
        }
    """
    series = df[column]
    summary = {
        'column': column,
        'dtype': str(series.dtype),
        'inferred_type': infer_type(series),
        'count': len(series),
        'missing': int(series.isna().sum()),
        'missing_pct': round(series.isna().mean() * 100, 2),
        'unique': int(series.nunique()),
        'unique_pct': round(series.nunique() / len(series) * 100, 2),
    }

    # Top 值
    vc = series.value_counts().head(5)
    summary['top_values'] = [(str(k), int(v)) for k, v in vc.items()]

    # 数值统计
    if pd.api.types.is_numeric_dtype(series):
        summary.update({
            'mean': round(series.mean(), 2),
            'median': round(series.median(), 2),
            'std': round(series.std(), 2),
            'min': round(series.min(), 2),
            'max': round(series.max(), 2),
            'skewness': round(series.skew(), 2),
            'kurtosis': round(series.kurtosis(), 2),
        })

    return summary


def all_columns_summary(df: pd.DataFrame) -> list[dict]:
    """对所有列生成摘要"""
    summaries = []
    for col in df.columns:
        summaries.append(column_summary(df, col))
    return summaries


def frequency_table(df: pd.DataFrame, column: str, top_n: int = 20,
                    sort: bool = True) -> pd.DataFrame:
    """频数统计表"""
    freq = df[column].value_counts().head(top_n).reset_index()
    freq.columns = [column, '频数']
    freq['占比'] = (freq['频数'] / len(df) * 100).round(2)
    freq['累计占比'] = freq['占比'].cumsum().round(2)
    return freq


def value_counts_pct(df: pd.DataFrame, column: str,
                     normalize: bool = True) -> pd.Series:
    """值计数（含百分比）"""
    return df[column].value_counts(normalize=normalize)


def missing_report(df: pd.DataFrame) -> pd.DataFrame:
    """缺失值报告"""
    missing = pd.DataFrame({
        '列名': df.columns,
        '缺失数': df.isna().sum().values,
        '缺失率(%)': (df.isna().mean() * 100).round(2).values,
        '数据类型': df.dtypes.values,
    })
    missing = missing[missing['缺失数'] > 0].sort_values('缺失率(%)', ascending=False)
    missing = missing.reset_index(drop=True)
    logger.info(f"缺失值报告: {len(missing)} 列存在缺失")
    return missing


def outlier_report(df: pd.DataFrame, method: str = 'iqr') -> pd.DataFrame:
    """异常值报告（对所有数值列）"""
    from cleaning.cleaner import detect_outliers

    numeric_cols = df.select_dtypes(include=[np.number]).columns
    results = []
    for col in numeric_cols:
        outliers = detect_outliers(df, col, method=method)
        if outliers.sum() > 0:
            results.append({
                '列名': col,
                '异常值数': int(outliers.sum()),
                '异常率(%)': round(outliers.sum() / len(df) * 100, 2),
                '方法': method,
            })

    report = pd.DataFrame(results).sort_values('异常值数', ascending=False)
    logger.info(f"异常值报告: {len(report)} 列存在异常值")
    return report
