"""
相关性分析
"""
import pandas as pd
import numpy as np

from config import logger


def correlation_matrix(df: pd.DataFrame, columns: list[str] = None,
                       method: str = 'pearson') -> pd.DataFrame:
    """计算相关系数矩阵

    Args:
        method: 'pearson' | 'spearman' | 'kendall'
    """
    if columns:
        numeric_df = df[columns].select_dtypes(include=[np.number])
    else:
        numeric_df = df.select_dtypes(include=[np.number])

    corr = numeric_df.corr(method=method)
    logger.info(f"相关系数矩阵: {corr.shape[0]}×{corr.shape[1]} ({method})")
    return corr


def top_correlations(corr_matrix: pd.DataFrame, top_n: int = 10,
                     exclude_diagonal: bool = True) -> pd.DataFrame:
    """从相关系数矩阵中提取最强相关对

    Args:
        corr_matrix: 相关系数矩阵
        top_n: 返回前N对
        exclude_diagonal: 排除自相关

    Returns:
        DataFrame with columns: 变量1, 变量2, 相关系数, 强度
    """
    corr = corr_matrix.copy()
    if exclude_diagonal:
        np.fill_diagonal(corr.values, np.nan)

    # 取上三角去重
    mask = np.triu(np.ones_like(corr, dtype=bool), k=1)
    corr_triu = corr.where(mask)

    pairs = []
    for i in range(len(corr.columns)):
        for j in range(i + 1, len(corr.columns)):
            if not mask[i, j]:
                continue
            val = corr.iloc[i, j]
            if pd.notna(val):
                pairs.append({
                    '变量1': corr.columns[i],
                    '变量2': corr.columns[j],
                    '相关系数': round(val, 4),
                    '强度': _correlation_strength(val),
                })

    result = pd.DataFrame(pairs).sort_values(
        '相关系数', key=abs, ascending=False).head(top_n)
    logger.info(f"最强相关对: {len(result)} 对")
    return result.reset_index(drop=True)


def find_related_pairs(df: pd.DataFrame, target: str,
                       threshold: float = 0.3,
                       method: str = 'pearson') -> pd.DataFrame:
    """找出与目标变量相关的所有列

    Args:
        target: 目标列名
        threshold: 相关系数阈值（绝对值）
        method: 相关系数类型
    """
    numeric_df = df.select_dtypes(include=[np.number])
    if target not in numeric_df.columns:
        raise ValueError(f"目标列 '{target}' 不是数值列")

    corr = numeric_df.corr(method=method)[target].drop(target)
    related = corr[corr.abs() >= threshold].sort_values(ascending=False)

    result = pd.DataFrame({
        '变量': related.index,
        '相关系数': related.values.round(4),
        '强度': related.values.apply(_correlation_strength),
    }).sort_values('相关系数', key=abs, ascending=False)

    logger.info(f"与 {target} 相关的变量: {len(result)} 个 (|r|≥{threshold})")
    return result.reset_index(drop=True)


def _correlation_strength(r: float) -> str:
    """判断相关强度"""
    r_abs = abs(r)
    if r_abs >= 0.8:
        return '极强' + ('正相关' if r > 0 else '负相关')
    elif r_abs >= 0.6:
        return '强' + ('正相关' if r > 0 else '负相关')
    elif r_abs >= 0.4:
        return '中等' + ('正相关' if r > 0 else '负相关')
    elif r_abs >= 0.2:
        return '弱' + ('正相关' if r > 0 else '负相关')
    else:
        return '极弱或无关'
