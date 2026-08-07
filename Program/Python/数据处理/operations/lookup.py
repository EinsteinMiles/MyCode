"""
值查找与匹配：VLOOKUP、模糊匹配、范围查找、INDEX-MATCH
"""
import pandas as pd
import numpy as np

from config import logger


def vlookup(df: pd.DataFrame, lookup_df: pd.DataFrame,
            key: str, lookup_key: str = None,
            columns: str | list[str] = None,
            how: str = 'left') -> pd.DataFrame:
    """类似 Excel VLOOKUP 的值匹配

    Args:
        df: 主表
        lookup_df: 查找表
        key: 主表关联列
        lookup_key: 查找表关联列 (默认同 key)
        columns: 要从查找表取回的列 (默认全部列，排除关联键)
        how: 'left'=保留主表所有行 | 'inner'=仅匹配行

    Returns:
        合并后的 DataFrame
    """
    if lookup_key is None:
        lookup_key = key

    if columns:
        cols_to_get = [lookup_key] + (columns if isinstance(columns, list) else [columns])
        cols_to_get = list(dict.fromkeys(cols_to_get))  # 去重保序
        lookup_subset = lookup_df[cols_to_get].copy()
    else:
        lookup_subset = lookup_df.copy()

    result = pd.merge(df, lookup_subset, left_on=key, right_on=lookup_key,
                      how=how, suffixes=('', '_lookup'))

    # 删除重复的关联键列
    if lookup_key != key and lookup_key in result.columns:
        result = result.drop(columns=[lookup_key])

    match_count = result[result.columns[-1]].notna().sum() if not result.empty else 0
    logger.info(f"VLOOKUP [{key}]: {match_count}/{len(df)} 行匹配成功")
    return result


def multi_key_lookup(df: pd.DataFrame, lookup_df: pd.DataFrame,
                     keys: list[str], lookup_keys: list[str] = None,
                     columns: list[str] = None,
                     how: str = 'left') -> pd.DataFrame:
    """多键查找（复合主键 VLOOKUP）"""
    if lookup_keys is None:
        lookup_keys = keys

    if columns:
        cols_to_get = lookup_keys + columns
        lookup_subset = lookup_df[cols_to_get].copy()
    else:
        lookup_subset = lookup_df.copy()

    result = pd.merge(df, lookup_subset, left_on=keys, right_on=lookup_keys,
                      how=how, suffixes=('', '_lookup'))

    for lk in lookup_keys:
        if lk not in keys and lk in result.columns:
            result = result.drop(columns=[lk])

    logger.info(f"多键查找 [{keys}]: {result.shape[0]} 行")
    return result


def fuzzy_match(df: pd.DataFrame, column: str, pattern: str,
                case: bool = False) -> pd.DataFrame:
    """模糊匹配（包含搜索）

    Args:
        column: 搜索列
        pattern: 搜索模式（关键词）
        case: 是否区分大小写
    """
    mask = df[column].str.contains(pattern, case=case, na=False)
    result = df[mask].copy()
    logger.info(f"模糊匹配 [{pattern}] in [{column}]: 找到 {len(result)} 条")
    return result


def regex_match(df: pd.DataFrame, column: str, regex: str) -> pd.DataFrame:
    """正则表达式匹配"""
    mask = df[column].str.match(regex, na=False)
    result = df[mask].copy()
    logger.info(f"正则匹配 [{regex}] in [{column}]: 找到 {len(result)} 条")
    return result


def range_lookup(df: pd.DataFrame, column: str,
                 ranges: list[tuple], labels: list[str] = None) -> pd.DataFrame:
    """范围查找（类似 VLOOKUP 的近似匹配）

    Args:
        column: 数值列
        ranges: [(min, max), ...] 区间列表
        labels: 区间标签 (默认使用区间字符串)

    Example:
        range_lookup(df, '分数', [(0,60), (60,80), (80,100)], ['不及格', '良好', '优秀'])
    """
    result = df.copy()
    if labels is None:
        labels = [f"{r[0]}-{r[1]}" for r in ranges]

    conditions = []
    for i, (lo, hi) in enumerate(ranges):
        conditions.append((result[column] >= lo) & (result[column] < hi))

    result['_range_label'] = np.select(conditions, labels, default='其他')
    logger.info(f"范围查找 [{column}]: 分为 {len(ranges)} 个区间")
    return result


def index_match(df: pd.DataFrame, lookup_df: pd.DataFrame,
                index_column: str, value_column: str,
                on_column: str) -> pd.DataFrame:
    """INDEX-MATCH 模式（按索引列匹配取值）

    类似 Excel 的 INDEX(MATCH()) 组合

    Args:
        df: 主表
        lookup_df: 查找表
        index_column: 查找表的索引列（相当于 MATCH 的查找范围）
        value_column: 要取回的值列（相当于 INDEX 的范围）
        on_column: 主表的匹配列

    Returns:
        添加了匹配结果列的 DataFrame
    """
    lookup_map = lookup_df.set_index(index_column)[value_column].to_dict()
    result = df.copy()
    result[f'{value_column}_matched'] = result[on_column].map(lookup_map)
    matched = result[f'{value_column}_matched'].notna().sum()
    logger.info(f"INDEX-MATCH: {matched}/{len(result)} 行匹配成功")
    return result


def closest_match(df: pd.DataFrame, column: str,
                  target: float) -> pd.DataFrame:
    """最接近值匹配（找最接近目标值的行）"""
    df = df.copy()
    df['_distance'] = (df[column] - target).abs()
    result = df.nsmallest(1, '_distance').drop(columns=['_distance'])
    logger.info(f"最接近 [{target}] 的值: {result[column].values[0] if not result.empty else 'N/A'}")
    return result
