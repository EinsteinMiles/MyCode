"""
财务指标计算器
基于 akshare 已提供的指标，补充计算衍生指标

由于 stock_financial_abstract 已经返回了大量预计算指标，
此模块主要处理：
  1. 补充计算缺失的同比/环比增长率
  2. 计算复合增长率 (CAGR)
  3. 计算估值相关指标
  4. 数据四舍五入和格式标准化
"""

import pandas as pd
import numpy as np
import logging
from typing import Dict

logger = logging.getLogger(__name__)


class IndicatorCalculator:
    """补充指标计算器"""

    def __init__(self):
        pass

    # ==================================================================
    # 同比增长率
    # ==================================================================

    @staticmethod
    def calc_yoy_growth(series: pd.Series) -> pd.Series:
        """同比增长率 = (本期 - 上期) / |上期| * 100%"""
        if series is None or len(series) < 2:
            return pd.Series([np.nan] * len(series)) if series is not None else pd.Series()

        result = series.pct_change() * 100
        result = result.replace([np.inf, -np.inf], np.nan)
        return result

    # ==================================================================
    # 复合增长率
    # ==================================================================

    @staticmethod
    def calc_cagr(series: pd.Series) -> float:
        """
        计算复合年增长率 CAGR
        CAGR = (期末值 / 期初值)^(1/n) - 1
        """
        clean = series.dropna()
        if len(clean) < 2:
            return np.nan

        begin = clean.iloc[0]
        end = clean.iloc[-1]
        periods = len(clean) - 1

        if begin <= 0 or periods <= 0:
            return np.nan

        try:
            return ((end / begin) ** (1.0 / periods) - 1) * 100
        except Exception:
            return np.nan

    # ==================================================================
    # 补充计算
    # ==================================================================

    def calculate_all(
        self,
        cleaned_statements: Dict[str, pd.DataFrame],
    ) -> pd.DataFrame:
        """
        基于清洗后的数据，补充计算衍生指标

        参数:
            cleaned_statements: 清洗后的数据字典，
                               主数据在 cleaned_statements["indicators"] 中

        返回:
            补充了衍生指标的 DataFrame
        """
        # 优先使用 indicators
        df = cleaned_statements.get("indicators", pd.DataFrame())

        if df.empty:
            logger.warning("indicators 为空，无法计算")
            return pd.DataFrame()

        df = df.copy()

        # ---- 补充营收增长率（如果缺失） ----
        if "revenue_growth" not in df.columns or df["revenue_growth"].isna().all():
            if "total_revenue" in df.columns:
                df["revenue_growth"] = self.calc_yoy_growth(df["total_revenue"])
                logger.info("补充计算: 营收增长率")

        # ---- 补充净利润增长率（如果缺失） ----
        if "net_profit_growth" not in df.columns or df["net_profit_growth"].isna().all():
            if "net_profit" in df.columns:
                df["net_profit_growth"] = self.calc_yoy_growth(df["net_profit"])
                logger.info("补充计算: 净利润增长率")

        # ---- 补充总资产增长率 ----
        if "total_assets" in df.columns:
            df["asset_growth"] = self.calc_yoy_growth(df["total_assets"])

        # ---- 补充净资产增长率 ----
        if "total_equity" in df.columns:
            df["equity_growth"] = self.calc_yoy_growth(df["total_equity"])

        # ---- 确保关键列是百分比格式（0-100 范围） ----
        pct_cols = ["roe", "roa", "gross_margin", "net_margin",
                     "operating_margin", "debt_ratio", "revenue_growth",
                     "net_profit_growth", "asset_growth", "equity_growth",
                     "ebit_margin", "expense_ratio"]

        for col in pct_cols:
            if col in df.columns:
                # 检查：如果所有值都 <= 1（小数格式），转为百分比
                max_val = df[col].abs().max()
                if 0 < max_val <= 1:
                    logger.info(f"列 {col} 从小数转为百分比 (max={max_val})")
                    df[col] = df[col] * 100

        # ---- 四舍五入 ----
        numeric_cols = df.select_dtypes(include=[np.number]).columns
        for col in numeric_cols:
            if col == "year" or col == "report_date":
                continue
            df[col] = df[col].apply(lambda x: round(x, 2) if pd.notna(x) and not np.isinf(x) else x)

        logger.info(f"指标计算完成: {len(df)} 年, {len(df.columns)} 项指标")
        return df
