"""
数据爬取 - 核心数据获取器
基于 akshare 的 stock_financial_abstract 获取 A 股公司完整财务数据
"""

import akshare as ak
import pandas as pd
import numpy as np
import re
import time
import logging
from typing import Dict, Optional, List

from config import (
    RETRY_TIMES, RETRY_DELAY,
    SHANGHAI_PREFIXES, SHENZHEN_PREFIXES,
)

logger = logging.getLogger(__name__)


class FinancialStatementFetcher:
    """
    财报数据获取器
    通过 akshare 的 stock_financial_abstract 获取完整的财务指标数据

    stock_financial_abstract 返回所有关键指标：
      - 常用指标：营收、净利润、ROE、ROA、毛利率、净利率、资产负债率等
      - 每股指标：EPS、每股净资产、每股经营现金流等
      - 盈利能力：ROE(多口径)、营业利润率、ROIC 等
      - 成长能力：营收增长率、净利润增长率等
      - 收益质量：经营现金流/净利润等
      - 财务风险：流动比率、速动比率、资产负债率、权益乘数等
      - 营运能力：应收账款/存货/总资产周转率及周转天数
    """

    def __init__(self, max_retries: int = RETRY_TIMES, retry_delay: float = RETRY_DELAY):
        self.max_retries = max_retries
        self.retry_delay = retry_delay

    # ------------------------------------------------------------------
    # 工具方法
    # ------------------------------------------------------------------

    @staticmethod
    def get_market(symbol: str) -> str:
        """根据股票代码判断所属交易所"""
        symbol = str(symbol).strip().zfill(6)
        if any(symbol.startswith(p) for p in SHANGHAI_PREFIXES):
            return "sh"
        elif any(symbol.startswith(p) for p in SHENZHEN_PREFIXES):
            return "sz"
        else:
            raise ValueError(f"无法识别股票代码 '{symbol}' 的交易所")

    @staticmethod
    def format_symbol(symbol: str) -> str:
        """格式化股票代码，如 'sh600519'"""
        symbol = str(symbol).strip().zfill(6)
        market = FinancialStatementFetcher.get_market(symbol)
        return f"{market}{symbol}"

    @staticmethod
    def validate_stock_code(symbol: str) -> bool:
        """验证 A 股股票代码是否合法"""
        symbol = str(symbol).strip()
        if len(symbol) != 6 or not symbol.isdigit():
            return False
        try:
            FinancialStatementFetcher.get_market(symbol)
            return True
        except ValueError:
            return False

    @staticmethod
    def search_company(keyword: str) -> Optional[pd.DataFrame]:
        """根据公司名称模糊搜索股票代码"""
        try:
            df = ak.stock_info_a_code_name()
            matched = df[df["name"].str.contains(keyword, case=False, na=False)]
            if matched.empty:
                logger.warning(f"未找到包含 '{keyword}' 的公司")
                return None
            return matched
        except Exception as e:
            logger.error(f"搜索公司失败: {e}")
            return None

    def _retry_call(self, func, *args, **kwargs):
        """带重试的 akshare API 调用"""
        last_error = None
        for attempt in range(self.max_retries):
            try:
                result = func(*args, **kwargs)
                if result is not None and not (isinstance(result, pd.DataFrame) and result.empty):
                    return result
                logger.warning(f"第 {attempt+1} 次调用 {func.__name__} 返回空数据")
            except Exception as e:
                last_error = e
                logger.warning(f"第 {attempt+1} 次调用 {func.__name__} 失败: {e}")

            if attempt < self.max_retries - 1:
                time.sleep(self.retry_delay * (attempt + 1))

        raise RuntimeError(f"调用 {func.__name__} 失败（已重试 {self.max_retries} 次）: {last_error}")

    # ------------------------------------------------------------------
    # 核心数据获取
    # ------------------------------------------------------------------

    def _parse_value(self, val) -> float:
        """
        解析 akshare 返回值，处理带单位的数值
        如 "54.42亿", "8.67亿", "1609.94%", "False" 等
        """
        if val is None or pd.isna(val):
            return np.nan

        if isinstance(val, (int, float, np.integer, np.floating)):
            return float(val)

        s = str(val).strip()

        if s == "False" or s == "" or s == "--":
            return np.nan

        # 去除百分号
        is_pct = s.endswith("%")
        if is_pct:
            s = s[:-1]

        # 处理单位
        unit_multiplier = 1.0
        if s.endswith("亿"):
            unit_multiplier = 1e8
            s = s[:-1]
        elif s.endswith("万"):
            unit_multiplier = 1e4
            s = s[:-1]

        try:
            num = float(s.replace(",", ""))
            return num * unit_multiplier
        except (ValueError, AttributeError):
            return np.nan

    def fetch_financial_abstract(self, symbol: str) -> pd.DataFrame:
        """
        获取财务摘要数据（来自东方财富）
        返回转置后的 DataFrame：每行一个报告期，每列一个指标

        原始数据格式：每行是一个指标，列是日期
        转置后格式：每行是一个日期，列是指标名称
        """
        logger.info(f"获取 {symbol} 财务摘要数据...")

        try:
            raw = ak.stock_financial_abstract(symbol=symbol)
        except Exception as e:
            logger.error(f"stock_financial_abstract 失败: {e}")
            return pd.DataFrame()

        if raw is None or raw.empty:
            logger.warning(f"{symbol} 无财务数据")
            return pd.DataFrame()

        # raw 格式:
        #   '选项' | '指标' | '20141231' | '20151231' | ...
        # 每个指标一行

        # --- 构建指标名称（去重） ---
        # 同一指标名可能出现在多个分类中，我们用"分类_指标名"来区分
        raw = raw.copy()
        raw["full_name"] = raw["指标"]  # 简化：只用指标名

        # 日期列
        date_cols = [c for c in raw.columns if c not in ("选项", "指标", "full_name")]
        if not date_cols:
            logger.warning("无日期列")
            return pd.DataFrame()

        # --- 转置：日期变成行，指标变成列 ---
        # 构建转置 DataFrame
        records = []
        for date_col in date_cols:
            row_data = {"report_date": date_col}
            for _, data_row in raw.iterrows():
                indicator_name = data_row["full_name"]
                row_data[indicator_name] = self._parse_value(data_row[date_col])
            records.append(row_data)

        df = pd.DataFrame(records)

        # 转换日期
        df["report_date"] = pd.to_datetime(df["report_date"], format="%Y%m%d", errors="coerce")
        df = df.dropna(subset=["report_date"])
        df = df.sort_values("report_date").reset_index(drop=True)

        logger.info(f"财务摘要获取成功: {len(df)} 个报告期, {len(df.columns)} 项指标")
        return df

    def fetch_financial_abstract_ths(self, symbol: str) -> pd.DataFrame:
        """
        获取财务摘要数据（同花顺来源，作为补充）
        与 stock_financial_abstract 相比，有略微不同的指标覆盖
        """
        logger.info(f"获取 {symbol} 财务摘要(同花顺)...")
        try:
            df = ak.stock_financial_abstract_ths(
                symbol=symbol, indicator="按报告期"
            )
            if df is not None and not df.empty:
                # 解析数值
                for col in df.columns:
                    if col == "报告期":
                        continue
                    df[col] = df[col].apply(self._parse_value)

                # 重命名报告期列
                if "报告期" in df.columns:
                    df = df.rename(columns={"报告期": "report_date"})
                    df["report_date"] = pd.to_datetime(df["report_date"], errors="coerce")
                    df = df.dropna(subset=["report_date"])
                    df = df.sort_values("report_date").reset_index(drop=True)

                logger.info(f"财务摘要(同花顺)获取成功: {len(df)} 行")
                return df
        except Exception as e:
            logger.warning(f"stock_financial_abstract_ths 失败: {e}")

        return pd.DataFrame()

    def fetch_all_statements(self, symbol: str) -> Dict[str, pd.DataFrame]:
        """
        获取全部财务数据
        整合多个数据源

        返回:
            {
                "income": pd.DataFrame,     # 利润表相关数据
                "balance": pd.DataFrame,    # 资产负债表相关数据
                "cash_flow": pd.DataFrame,  # 现金流量表相关数据
                "indicators": pd.DataFrame, # 主要财务指标（这是统一的主数据源）
            }
        """
        logger.info("=" * 50)
        logger.info(f"开始获取 {symbol} 的全部财务数据...")

        # 主数据源：东方财富财务摘要
        df_main = self.fetch_financial_abstract(symbol)

        # 补充数据源：同花顺财务摘要
        df_ths = self.fetch_financial_abstract_ths(symbol)

        # 合并两个数据源（按 report_date）
        if not df_main.empty and not df_ths.empty:
            # 合并时去重列名，优先保留主数据源
            ths_cols = [c for c in df_ths.columns if c not in df_main.columns or c == "report_date"]
            df_combined = pd.merge(df_main, df_ths[ths_cols], on="report_date", how="outer")
        elif not df_main.empty:
            df_combined = df_main
        elif not df_ths.empty:
            df_combined = df_ths
        else:
            logger.warning(f"{symbol} 所有数据源均无数据")
            return {"income": pd.DataFrame(), "balance": pd.DataFrame(),
                    "cash_flow": pd.DataFrame(), "indicators": pd.DataFrame()}

        # 只保留年报数据 (12月31日)
        df_annual = df_combined[
            (df_combined["report_date"].dt.month == 12) &
            (df_combined["report_date"].dt.day == 31)
        ].copy()

        if df_annual.empty:
            # 如果没有年报，使用最新的季度数据
            logger.warning("无年报数据，使用最新季度数据")
            df_annual = df_combined

        logger.info(f"全部数据获取完成: {len(df_combined)} 个报告期 (其中 {len(df_annual)} 个年报)")
        return {
            "income": pd.DataFrame(),       # 利润表数据已在 indicators 中
            "balance": pd.DataFrame(),      # 资产负债表数据已在 indicators 中
            "cash_flow": pd.DataFrame(),    # 现金流量表数据已在 indicators 中
            "indicators": df_annual,        # 统一的主数据源
        }

    # ------------------------------------------------------------------
    # 财务指标 & 估值
    # ------------------------------------------------------------------

    def fetch_financial_indicators(self, symbol: str) -> pd.DataFrame:
        """
        获取主要财务指标
        直接使用 fetch_financial_abstract 的结果
        """
        return self.fetch_financial_abstract(symbol)

    def fetch_valuation_indicators(self, symbol: str) -> pd.DataFrame:
        """获取 PE/PB 等估值指标的历史数据"""
        logger.info(f"获取 {symbol} 估值指标...")
        try:
            df = ak.stock_a_lg_indicator(symbol=symbol)
            logger.info(f"估值指标获取成功: {len(df)} 行")
            return df
        except Exception as e:
            logger.warning(f"stock_a_lg_indicator 失败: {e}")
            try:
                df = ak.stock_individual_info_em(symbol=symbol)
                logger.info("降级获取成功")
                return df
            except Exception as e2:
                logger.error(f"估值获取完全失败: {e2}")
                return pd.DataFrame()

    def fetch_company_info(self, symbol: str) -> dict:
        """获取公司基本信息"""
        logger.info(f"获取 {symbol} 公司信息...")
        try:
            df = ak.stock_individual_info_em(symbol=symbol)
            if df is not None and not df.empty:
                info = dict(zip(df["item"], df["value"]))
                return info
        except Exception as e:
            logger.warning(f"获取公司信息失败: {e}")

        # 降级：从搜索获取名称
        try:
            df = ak.stock_info_a_code_name()
            match = df[df["code"] == symbol]
            if not match.empty:
                return {"股票简称": match.iloc[0]["name"], "股票代码": symbol}
        except Exception:
            pass

        return {}
