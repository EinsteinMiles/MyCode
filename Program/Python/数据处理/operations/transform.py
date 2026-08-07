"""
数据变换：列操作、类型转换、重命名、计算列等
"""
import pandas as pd
import numpy as np

from config import logger


def rename_columns(df: pd.DataFrame, mapping: dict) -> pd.DataFrame:
    """重命名列

    Args:
        df: DataFrame
        mapping: {旧名: 新名} 映射字典
    """
    result = df.rename(columns=mapping)
    logger.info(f"已重命名 {len(mapping)} 列: {list(mapping.keys())}")
    return result


def select_columns(df: pd.DataFrame, columns: list[str]) -> pd.DataFrame:
    """选择指定列"""
    missing = [c for c in columns if c not in df.columns]
    if missing:
        logger.warning(f"列不存在: {missing}")
    valid = [c for c in columns if c in df.columns]
    return df[valid]


def drop_columns(df: pd.DataFrame, columns: list[str]) -> pd.DataFrame:
    """删除指定列"""
    existing = [c for c in columns if c in df.columns]
    result = df.drop(columns=existing, errors='ignore')
    logger.info(f"已删除 {len(existing)} 列: {existing}")
    return result


def add_column(df: pd.DataFrame, name: str, value=None) -> pd.DataFrame:
    """添加新列"""
    result = df.copy()
    result[name] = value
    logger.info(f"已添加列: {name}")
    return result


def add_calculated_column(df: pd.DataFrame, name: str,
                          expression: str) -> pd.DataFrame:
    """添加计算列（使用 eval 表达式）

    Example:
        add_calculated_column(df, '利润率', "df['利润'] / df['收入'] * 100")
    """
    result = df.copy()
    # 安全 eval: 只允许 df 变量
    result[name] = eval(expression, {'df': result, 'np': np, 'pd': pd}, {})
    logger.info(f"已添加计算列: {name}")
    return result


def change_type(df: pd.DataFrame, column: str,
                new_type: str) -> pd.DataFrame:
    """转换列类型

    Args:
        new_type: 'int', 'float', 'str', 'datetime', 'category'
    """
    result = df.copy()
    type_map = {
        'int': 'int64',
        'float': 'float64',
        'str': 'string',
        'datetime': 'datetime64[ns]',
        'category': 'category',
        'bool': 'bool',
    }
    target = type_map.get(new_type, new_type)

    if new_type == 'datetime':
        result[column] = pd.to_datetime(result[column], errors='coerce')
    elif new_type == 'int':
        result[column] = pd.to_numeric(result[column], errors='coerce').astype('Int64')
    elif new_type == 'float':
        result[column] = pd.to_numeric(result[column], errors='coerce')
    else:
        result[column] = result[column].astype(target)

    logger.info(f"列 {column} 类型已转换为 {new_type}")
    return result


def reorder_columns(df: pd.DataFrame, order: list[str]) -> pd.DataFrame:
    """重新排序列"""
    remaining = [c for c in df.columns if c not in order]
    new_order = [c for c in order if c in df.columns] + remaining
    return df[new_order]


def fill_sequence(df: pd.DataFrame, column: str, start: int = 1,
                  step: int = 1) -> pd.DataFrame:
    """为列填充序列号"""
    result = df.copy()
    result[column] = range(start, start + len(result) * step, step)
    return result
