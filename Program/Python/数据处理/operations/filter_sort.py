"""
数据筛选与排序
"""
import pandas as pd
import numpy as np

from config import logger


def filter_by_value(df: pd.DataFrame, column: str, operator: str,
                    value) -> pd.DataFrame:
    """按值筛选

    Args:
        column: 列名
        operator: '==' | '!=' | '>' | '>=' | '<' | '<=' | 'between' | 'isnull' | 'notnull'
        value: 比较值 (between 时传 (min, max) 元组)
    """
    ops = {
        '==': lambda s, v: s == v,
        '!=': lambda s, v: s != v,
        '>': lambda s, v: s > v,
        '>=': lambda s, v: s >= v,
        '<': lambda s, v: s < v,
        '<=': lambda s, v: s <= v,
        'between': lambda s, v: s.between(v[0], v[1]),
        'isnull': lambda s, v: s.isnull(),
        'notnull': lambda s, v: s.notnull(),
    }
    if operator not in ops:
        raise ValueError(f"不支持的运算符: {operator}")

    mask = ops[operator](df[column], value)
    result = df[mask].copy()
    logger.info(f"筛选 [{column} {operator} {value}]: {len(df)} → {len(result)} 行")
    return result


def filter_by_condition(df: pd.DataFrame, condition: str) -> pd.DataFrame:
    """使用 query 风格条件筛选

    Example:
        filter_by_condition(df, "年龄 > 30 and 城市 == '北京'")
    """
    result = df.query(condition)
    logger.info(f"条件筛选 [{condition}]: {len(df)} → {len(result)} 行")
    return result


def filter_by_list(df: pd.DataFrame, column: str,
                   values: list, inclusive: bool = True) -> pd.DataFrame:
    """按列表值筛选

    Args:
        inclusive: True=包含在列表中, False=排除列表中的值
    """
    if inclusive:
        result = df[df[column].isin(values)]
    else:
        result = df[~df[column].isin(values)]
    logger.info(f"列表筛选 [{column}]: {len(df)} → {len(result)} 行")
    return result


def filter_top_n(df: pd.DataFrame, column: str, n: int = 10,
                 ascending: bool = False) -> pd.DataFrame:
    """取前N条（按某列排序）"""
    result = df.nlargest(n, column) if not ascending else df.nsmallest(n, column)
    logger.info(f"取 [{column}] {'最小' if ascending else '最大'} {n} 条")
    return result


def sort_data(df: pd.DataFrame, by: list[str],
              ascending: bool | list = True) -> pd.DataFrame:
    """多列排序

    Args:
        by: 排序列名列表
        ascending: True/False 或每列的排序方向列表
    """
    result = df.sort_values(by=by, ascending=ascending)
    logger.info(f"排序完成: {by}")
    return result


def drop_duplicates_custom(df: pd.DataFrame,
                           subset: list[str] = None,
                           keep: str = 'first') -> pd.DataFrame:
    """删除重复行

    Args:
        subset: 判断重复的列，None=全部列
        keep: 'first' | 'last' | False(全部删除)
    """
    before = len(df)
    result = df.drop_duplicates(subset=subset, keep=keep)
    removed = before - len(result)
    logger.info(f"去重: 删除 {removed} 条重复行")
    return result
