"""
数据透视表与分组聚合
"""
import pandas as pd
import numpy as np

from config import logger


def pivot_table(df: pd.DataFrame, index: str | list[str],
                columns: str = None, values: str | list[str] = None,
                aggfunc: str = 'sum', fill_value=0) -> pd.DataFrame:
    """数据透视表

    Args:
        index: 行索引列
        columns: 列索引列 (可选)
        values: 值列
        aggfunc: 聚合函数 ('sum','mean','count','min','max','median','std')
        fill_value: 空值填充
    """
    result = pd.pivot_table(
        df, index=index, columns=columns, values=values,
        aggfunc=aggfunc, fill_value=fill_value
    )
    logger.info(f"透视表: index={index}, columns={columns}, values={values}, agg={aggfunc}")
    return result


def group_aggregate(df: pd.DataFrame, by: str | list[str],
                    agg_dict: dict) -> pd.DataFrame:
    """分组聚合

    Args:
        by: 分组列
        agg_dict: {列名: '聚合函数'} 如 {'销售额': 'sum', '数量': 'mean'}

    支持聚合函数: sum, mean, count, min, max, median, std, var,
                  first, last, nunique (去重计数)
    """
    result = df.groupby(by, as_index=False).agg(agg_dict)
    logger.info(f"分组聚合 [{by}]: {result.shape[0]} 组")
    return result


def group_multi_agg(df: pd.DataFrame, by: str | list[str],
                    column: str, aggs: list[str]) -> pd.DataFrame:
    """单列多聚合

    Example:
        group_multi_agg(df, '部门', '工资', ['sum', 'mean', 'max', 'min'])
    """
    result = df.groupby(by, as_index=False)[column].agg(aggs)
    # 扁平化列名
    if isinstance(result.columns, pd.MultiIndex):
        result.columns = ['_'.join(col).strip('_') for col in result.columns.values]
    logger.info(f"多聚合 [{column}]: {aggs}")
    return result


def crosstab(df: pd.DataFrame, index: str, columns: str,
             values: str = None, aggfunc: str = 'count',
             normalize: bool = False) -> pd.DataFrame:
    """交叉表（频数/比例）

    Args:
        normalize: True=显示比例而非计数
    """
    result = pd.crosstab(
        df[index], df[columns], values=values,
        aggfunc=aggfunc, normalize=normalize
    )
    logger.info(f"交叉表: {index} × {columns}")
    return result


def rolling_aggregate(df: pd.DataFrame, column: str,
                      window: int, aggfunc: str = 'mean') -> pd.Series:
    """滚动窗口聚合（用于时间序列）

    Args:
        window: 窗口大小
        aggfunc: 'mean' | 'sum' | 'std' | 'min' | 'max'
    """
    roller = df[column].rolling(window=window)
    result = getattr(roller, aggfunc)()
    return result


def cumulative_sum(df: pd.DataFrame, column: str,
                   group_by: str = None) -> pd.Series:
    """累计求和（支持分组累计）"""
    if group_by:
        result = df.groupby(group_by)[column].cumsum()
    else:
        result = df[column].cumsum()
    return result


def describe_groups(df: pd.DataFrame, group_by: str | list[str],
                    columns: list[str] = None) -> pd.DataFrame:
    """分组描述统计（count/mean/std/min/25%/50%/75%/max）"""
    if columns:
        result = df.groupby(group_by)[columns].describe()
    else:
        result = df.groupby(group_by).describe()
    logger.info(f"分组描述: {group_by}")
    return result
