"""
数据解析器 - 将 akshare 的 stock_financial_abstract 数据清洗为标准化格式
包含列名映射、单位转换、缺失值处理
"""

import pandas as pd
import numpy as np
import logging
from typing import Dict, List

from config import (
    DEFAULT_UNIT,
)

logger = logging.getLogger(__name__)


# ---- 中文指标名 → 英文标准名映射 ----
INDICATOR_NAME_MAP = {
    # 常用指标
    "营业总收入": "total_revenue",
    "营业成本": "operating_cost",
    "净利润": "net_profit",
    "归母净利润": "net_profit_attributable",
    "扣非净利润": "net_profit_deducted",
    "股东权益合计(净资产)": "total_equity",
    "商誉": "goodwill",
    "经营现金流量净额": "operating_cash_flow",
    "基本每股收益": "eps",
    "每股净资产": "bvps",
    "每股现金流": "cfps",
    "净资产收益率(ROE)": "roe",
    "总资产报酬率(ROA)": "roa",
    "毛利率": "gross_margin",
    "销售净利率": "net_margin",
    "期间费用率": "expense_ratio",
    "资产负债率": "debt_ratio",

    # 盈利能力
    "摊薄净资产收益率": "roe_diluted",
    "净资产收益率_平均": "roe_avg",
    "总资产报酬率": "roa_total",
    "总资本回报率": "roic",
    "投入资本回报率": "roic_invested",
    "息税前利润率": "ebit_margin",
    "成本费用利润率": "cost_profit_ratio",
    "营业利润率": "operating_margin",
    "总资产净利率_平均": "net_profit_to_assets",

    # 成长能力
    "营业总收入增长率": "revenue_growth",
    "归属母公司净利润增长率": "net_profit_growth",

    # 收益质量
    "经营活动净现金/销售收入": "ocf_to_revenue",
    "经营性现金净流量/营业总收入": "ocf_to_operating_revenue",
    "经营活动净现金/归属母公司的净利润": "ocf_to_net_profit",

    # 财务风险
    "流动比率": "current_ratio",
    "速动比率": "quick_ratio",
    "保守速动比率": "conservative_quick_ratio",
    "权益乘数": "equity_multiplier",
    "产权比率": "debt_to_equity",
    "现金比率": "cash_ratio",

    # 营运能力
    "应收账款周转率": "receivables_turnover",
    "应收账款周转天数": "receivables_days",
    "存货周转率": "inventory_turnover",
    "存货周转天数": "inventory_days",
    "总资产周转率": "asset_turnover",
    "总资产周转天数": "asset_turnover_days",
    "流动资产周转率": "current_asset_turnover",
    "流动资产周转天数": "current_asset_days",
    "应付账款周转率": "payables_turnover",

    # 每股指标
    "稀释每股收益": "diluted_eps",
    "每股经营现金流": "eps_cash_flow",
    "每股未分配利润": "eps_undistributed_profit",
    "每股资本公积金": "eps_capital_reserve",
    "每股营业收入": "eps_revenue",

    # 同花顺补充指标
    "净利润同比增长率": "net_profit_growth",
    "扣非净利润同比增长率": "deducted_profit_growth",
    "营业总收入同比增长率": "revenue_growth",
    "销售毛利率": "gross_margin",
    "净资产收益率": "roe",
    "净资产收益率-摊薄": "roe_diluted",
    "营业周期": "operating_cycle",
}


class DataCleaner:
    """清洗原始财务数据：标准化列名、转换单位、处理缺失值"""

    def __init__(self, unit: str = DEFAULT_UNIT):
        self.unit = unit
        # 单位转换因子：原始数据中 "万" → "亿"
        self._unit_divisor = {"yi": 1e8, "wan": 1e4, "yuan": 1.0}[unit]

    # ------------------------------------------------------------------
    # 列名标准化
    # ------------------------------------------------------------------

    @staticmethod
    def standardize_columns(df: pd.DataFrame) -> pd.DataFrame:
        """将中文列名映射为英文标准名"""
        rename_dict = {}
        for cn, en in INDICATOR_NAME_MAP.items():
            if cn in df.columns:
                rename_dict[cn] = en

        df = df.rename(columns=rename_dict)

        # 去重列（保留第一个）
        df = df.loc[:, ~df.columns.duplicated()]
        return df

    # ------------------------------------------------------------------
    # 数值处理
    # ------------------------------------------------------------------

    def to_numeric_all(self, df: pd.DataFrame) -> pd.DataFrame:
        """将所有非日期列转为数值"""
        for col in df.columns:
            if col == "report_date":
                continue
            try:
                df[col] = pd.to_numeric(df[col], errors="coerce")
            except Exception:
                pass
        return df

    def convert_units(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        将绝对金额从原始单位（元）转换为目标单位（亿）
        比率类指标（%结尾、比率、周转率等）不转换

        哪些列是金额（需要转换单位）：
          total_revenue, net_profit, operating_cost, total_equity,
          goodwill, operating_cash_flow, net_profit_attributable,
          net_profit_deducted
        哪些列是比率或每股指标（不需要转换）：
          roe, roa, gross_margin, net_margin, eps, bvps,
          current_ratio, quick_ratio, asset_turnover, debt_ratio 等
        """
        # 金额类列（以元为单位，需要转换为亿）
        amount_cols = {
            "total_revenue", "net_profit", "operating_cost",
            "total_equity", "goodwill", "operating_cash_flow",
            "net_profit_attributable", "net_profit_deducted",
            "cfps",
        }

        for col in df.columns:
            if col == "report_date":
                continue

            if col in amount_cols and df[col].dtype in (np.float64, np.int64, float, int):
                # 检查数量级：如果值在百万以下，说明原始单位可能已经是万或亿
                max_val = df[col].abs().max()
                if max_val > 1e10:   # > 100亿（元），说明是元
                    df[col] = df[col] / 1e8   # 元 → 亿
                elif max_val > 1e7:  # > 1亿（元）但 < 100亿（元），说明是元
                    df[col] = df[col] / 1e8   # 元 → 亿
                elif max_val > 1e5:  # > 10万，可能是万元
                    df[col] = df[col] / 1e4 * 1e-4  # 万 → 亿 (即除以 1e4 再转亿...)
                    # 简化：如果是万，实际上值已经比较小了
                    pass
                # 如果值本身就很小（< 1000），已经是亿了，不转换

        return df

    def handle_missing(self, df: pd.DataFrame, strategy: str = "zero") -> pd.DataFrame:
        """处理缺失值"""
        df = df.dropna(axis=1, how="all")
        df = df.dropna(axis=0, how="all")

        if strategy == "zero":
            df = df.fillna(0)
        elif strategy == "ffill":
            df = df.fillna(method="ffill").fillna(method="bfill")
        elif strategy == "drop":
            df = df.dropna()

        return df

    def set_report_date_index(self, df: pd.DataFrame) -> pd.DataFrame:
        """确保日期格式正确并按升序排列"""
        if "report_date" not in df.columns:
            return df

        df["report_date"] = pd.to_datetime(df["report_date"], errors="coerce")
        df = df.dropna(subset=["report_date"])
        df = df.sort_values("report_date").reset_index(drop=True)
        return df

    def clean_indicators(self, df: pd.DataFrame, strategy: str = "zero") -> pd.DataFrame:
        """
        完整的清洗流程（针对 indicators DataFrame）
        """
        if df is None or df.empty:
            return pd.DataFrame()

        df = self.standardize_columns(df)
        df = self.to_numeric_all(df)
        df = self.set_report_date_index(df)
        df = self.convert_units(df)
        df = self.handle_missing(df, strategy=strategy)

        # 添加年份列
        if "report_date" in df.columns:
            df["year"] = pd.to_datetime(df["report_date"]).dt.year

        return df

    # ------------------------------------------------------------------
    # 批量清洗
    # ------------------------------------------------------------------

    def clean_all(
        self,
        statements: Dict[str, pd.DataFrame],
        strategy: str = "zero",
    ) -> Dict[str, pd.DataFrame]:
        """
        清洗全部数据
        现在主要处理 indicators DataFrame，三大报表可能为空
        """
        cleaned = {}

        # 主数据源：indicators
        if "indicators" in statements and not statements["indicators"].empty:
            df = self.clean_indicators(statements["indicators"], strategy)
            cleaned["indicators"] = df
            logger.info(f"指标数据清洗完成: {len(df)} 行 x {len(df.columns)} 列")

        # 三大报表（可能为空）
        for key in ["income", "balance", "cash_flow"]:
            if key in statements and not statements[key].empty:
                cleaned[key] = statements[key]  # 暂不做深度清洗
                logger.info(f"{key} 报表保留: {len(statements[key])} 行")

        return cleaned


class DataMerger:
    """合并数据源，构建统一分析 DataFrame"""

    def __init__(self, cleaner: DataCleaner = None):
        self.cleaner = cleaner or DataCleaner()

    def prepare_analysis_data(self, cleaned: Dict[str, pd.DataFrame]) -> pd.DataFrame:
        """
        从清洗后的数据中提取分析用主 DataFrame
        """
        if "indicators" in cleaned and not cleaned["indicators"].empty:
            df = cleaned["indicators"].copy()
        else:
            logger.warning("无 indicators 数据")
            return pd.DataFrame()

        # 添加年份列
        if "report_date" in df.columns:
            df["year"] = pd.to_datetime(df["report_date"]).dt.year

        # 确保关键列存在
        essential_cols = ["total_revenue", "net_profit", "roe", "gross_margin",
                          "net_margin", "debt_ratio", "current_ratio", "asset_turnover"]
        for col in essential_cols:
            if col not in df.columns:
                df[col] = np.nan

        return df

    def filter_years(self, df: pd.DataFrame, years: int = None) -> pd.DataFrame:
        """按最近 N 年筛选"""
        if years is None or "year" not in df.columns:
            return df

        available_years = sorted(df["year"].dropna().unique())
        if len(available_years) > years:
            cutoff = available_years[-years]
            df = df[df["year"] >= cutoff]

        return df
