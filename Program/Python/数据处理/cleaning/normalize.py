"""
数据标准化与归一化
"""
import pandas as pd
import numpy as np

from config import logger


def min_max_scale(df: pd.DataFrame, columns: list[str] = None,
                  feature_range: tuple = (0, 1)) -> pd.DataFrame:
    """Min-Max 归一化

    将数据缩放到 [0, 1] 或指定范围

    Formula: X_scaled = (X - X_min) / (X_max - X_min) * (max - min) + min
    """
    from sklearn.preprocessing import MinMaxScaler
    result = _apply_scaler(df, columns, MinMaxScaler(feature_range=feature_range))
    logger.info(f"Min-Max 归一化完成: 范围 {feature_range}")
    return result


def z_score_standardize(df: pd.DataFrame, columns: list[str] = None) -> pd.DataFrame:
    """Z-Score 标准化

    转换为均值为0、标准差为1的分布

    Formula: X_scaled = (X - mean) / std
    """
    from sklearn.preprocessing import StandardScaler
    result = _apply_scaler(df, columns, StandardScaler())
    logger.info("Z-Score 标准化完成 (mean=0, std=1)")
    return result


def robust_scale(df: pd.DataFrame, columns: list[str] = None) -> pd.DataFrame:
    """Robust 缩放（对异常值鲁棒）

    Formula: X_scaled = (X - median) / IQR
    """
    from sklearn.preprocessing import RobustScaler
    result = _apply_scaler(df, columns, RobustScaler())
    logger.info("Robust 缩放完成 (基于中位数和IQR)")
    return result


def log_transform(df: pd.DataFrame, columns: list[str] = None,
                  base: str = 'e') -> pd.DataFrame:
    """对数变换（处理偏态分布）

    Args:
        base: 'e' (自然对数) | '10' | '2'
    """
    result = df.copy()
    if columns is None:
        columns = result.select_dtypes(include=[np.number]).columns.tolist()

    for col in columns:
        # 处理非正值
        min_val = result[col].min()
        shift = 0
        if min_val <= 0:
            shift = abs(min_val) + 1
            result[col] = result[col] + shift

        if base == 'e':
            result[col] = np.log(result[col])
        elif base == '10':
            result[col] = np.log10(result[col])
        elif base == '2':
            result[col] = np.log2(result[col])

        if shift:
            logger.info(f"  {col}: 平移 {shift} 后取对数")

    logger.info(f"对数变换完成 ({len(columns)} 列, base={base})")
    return result


def winsorize(df: pd.DataFrame, columns: list[str] = None,
              limits: tuple = (0.05, 0.05)) -> pd.DataFrame:
    """Winsorize 缩尾处理（限制极端值）

    Args:
        limits: (下界分位数, 上界分位数) 如 (0.05, 0.05) 表示5%缩尾
    """
    from scipy.stats.mstats import winsorize as wz
    result = df.copy()
    if columns is None:
        columns = result.select_dtypes(include=[np.number]).columns.tolist()

    for col in columns:
        result[col] = wz(result[col].dropna().values, limits=limits)
        logger.info(f"  {col}: {limits[0]*100}%-{limits[1]*100}% 缩尾")

    logger.info(f"Winsorize 完成 ({len(columns)} 列)")
    return result


def bin_discretize(df: pd.DataFrame, column: str, bins: int = 5,
                   labels: list[str] = None,
                   strategy: str = 'uniform') -> pd.DataFrame:
    """连续值离散化（分箱）

    Args:
        bins: 分箱数
        labels: 箱标签
        strategy: 'uniform'(等宽) | 'quantile'(等频) | 'kmeans'(K-Means聚类)
    """
    result = df.copy()

    if strategy == 'uniform':
        result[f'{column}_bin'], bin_edges = pd.cut(
            result[column], bins=bins, labels=labels, retbins=True)
    elif strategy == 'quantile':
        result[f'{column}_bin'], bin_edges = pd.qcut(
            result[column], q=bins, labels=labels, retbins=True, duplicates='drop')
    elif strategy == 'kmeans':
        from sklearn.preprocessing import KBinsDiscretizer
        kbd = KBinsDiscretizer(n_bins=bins, encode='ordinal', strategy='kmeans')
        result[f'{column}_bin'] = kbd.fit_transform(
            result[[column]]).astype(int).flatten()
        bin_edges = None

    if bin_edges is not None:
        logger.info(f"分箱完成 [{column}]: {bins} 箱, 边界={bin_edges.tolist()}")
    else:
        logger.info(f"分箱完成 [{column}]: {bins} 箱 (K-Means)")
    return result


def _apply_scaler(df: pd.DataFrame, columns: list[str], scaler) -> pd.DataFrame:
    """内部：应用 sklearn scaler"""
    result = df.copy()
    if columns is None:
        columns = result.select_dtypes(include=[np.number]).columns.tolist()

    numeric_cols = [c for c in columns if pd.api.types.is_numeric_dtype(result[c])]
    if numeric_cols:
        result[numeric_cols] = scaler.fit_transform(result[numeric_cols])

    return result
