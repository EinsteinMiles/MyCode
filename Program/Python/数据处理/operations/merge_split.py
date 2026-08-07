"""
数据合并与拆分
"""
import os
import pandas as pd

from config import logger


def merge_rows(*dfs: pd.DataFrame, ignore_index: bool = True) -> pd.DataFrame:
    """纵向合并（追加行）- 类似 SQL UNION ALL

    Args:
        *dfs: 多个 DataFrame
        ignore_index: 是否重建索引
    """
    result = pd.concat(dfs, axis=0, ignore_index=ignore_index)
    logger.info(f"纵向合并: {len(dfs)} 个表 → {result.shape[0]} 行 × {result.shape[1]} 列")
    return result


def merge_columns(*dfs: pd.DataFrame, axis: int = 1) -> pd.DataFrame:
    """横向合并（追加列）- 按索引对齐"""
    result = pd.concat(dfs, axis=axis)
    logger.info(f"横向合并: {len(dfs)} 个表 → {result.shape[0]} 行 × {result.shape[1]} 列")
    return result


def merge_on_key(left: pd.DataFrame, right: pd.DataFrame,
                 on: str | list[str], how: str = 'left',
                 suffixes: tuple = ('_x', '_y')) -> pd.DataFrame:
    """按键合并 - 类似 SQL JOIN

    Args:
        left: 左表
        right: 右表
        on: 关联键（列名或列表）
        how: 'left' | 'right' | 'inner' | 'outer'
        suffixes: 重名列后缀
    """
    result = pd.merge(left, right, on=on, how=how, suffixes=suffixes)
    logger.info(f"键合并 [{how} join on {on}]: {result.shape[0]} 行 × {result.shape[1]} 列")
    return result


def merge_on_different_keys(left: pd.DataFrame, right: pd.DataFrame,
                            left_on: str | list[str], right_on: str | list[str],
                            how: str = 'left') -> pd.DataFrame:
    """不同列名关联 - 类似 VLOOKUP 跨列匹配"""
    result = pd.merge(left, right, left_on=left_on, right_on=right_on, how=how)
    logger.info(f"跨列合并 [{how}]: {result.shape[0]} 行")
    return result


def split_by_column(df: pd.DataFrame, column: str) -> dict:
    """按列值拆分为多个 DataFrame

    Returns:
        {值: DataFrame} 字典
    """
    groups = {}
    for value, group_df in df.groupby(column):
        key = str(value)
        groups[key] = group_df.reset_index(drop=True)
    logger.info(f"按 [{column}] 拆分为 {len(groups)} 组")
    return groups


def split_by_rows(df: pd.DataFrame, n_parts: int) -> list[pd.DataFrame]:
    """等行数拆分为 N 份"""
    chunk_size = len(df) // n_parts
    parts = []
    for i in range(n_parts):
        start = i * chunk_size
        if i == n_parts - 1:
            end = len(df)
        else:
            end = (i + 1) * chunk_size
        parts.append(df.iloc[start:end].reset_index(drop=True))
    logger.info(f"拆分为 {n_parts} 份, 每份约 {chunk_size} 行")
    return parts


def split_by_value(df: pd.DataFrame, column: str,
                   thresholds: list) -> dict:
    """按数值区间拆分

    Args:
        thresholds: 分割点列表，如 [0, 100, 500, 1000]
    """
    labels = [f"{thresholds[i]}-{thresholds[i+1]}"
              for i in range(len(thresholds) - 1)]
    df = df.copy()
    df['_group'] = pd.cut(df[column], bins=thresholds, labels=labels,
                          include_lowest=True)
    groups = {}
    for label, group_df in df.groupby('_group', observed=False):
        group_df = group_df.drop(columns=['_group']).reset_index(drop=True)
        groups[str(label)] = group_df
    logger.info(f"按 [{column}] 区间拆分为 {len(groups)} 组")
    return groups


def cross_join(left: pd.DataFrame, right: pd.DataFrame) -> pd.DataFrame:
    """笛卡尔积（交叉连接）"""
    left['_key'] = 1
    right['_key'] = 1
    result = pd.merge(left, right, on='_key').drop('_key', axis=1)
    result = result.drop(columns=['_key'])
    logger.info(f"交叉连接: {len(left)} × {len(right)} = {len(result)} 行")
    return result
