"""
财报分析器 - 对比分析和结论生成
包含趋势对比、同行业对比、自动生成分析结论
"""

import pandas as pd
import numpy as np
import logging
from typing import Dict, List, Optional, Tuple

from config import THRESHOLDS, PE_WARNING, PB_WARNING

logger = logging.getLogger(__name__)


class ReportAnalyzer:
    """
    财报分析器
    对计算出的指标进行趋势分析、健康度评估、自动结论生成
    """

    def __init__(self):
        self.thresholds = THRESHOLDS

    # ------------------------------------------------------------------
    # 单指标健康度判定
    # ------------------------------------------------------------------

    # 越低越好的指标（如负债率）
    LOWER_IS_BETTER = {"debt_ratio"}

    def classify_indicator(self, name: str, value: float) -> Tuple[str, str]:
        """
        对单个指标进行分类判定
        返回: (等级, 颜色)
        等级: excellent / healthy / warning / danger / unknown
        """
        if pd.isna(value) or np.isinf(value):
            return ("unknown", "gray")

        threshold = self.thresholds.get(name)
        if threshold is None:
            return ("unknown", "gray")

        if name in self.LOWER_IS_BETTER:
            # 越低越好：value <= excellent 为优秀
            if value <= threshold.get("excellent", -float("inf")):
                return ("excellent", "#2E7D32")
            if value <= threshold.get("healthy", float("inf")):
                return ("healthy", "#4CAF50")
            if value <= threshold.get("warning", float("inf")):
                return ("warning", "#FF9800")
            return ("danger", "#F44336")
        else:
            # 越高越好
            if value >= threshold.get("excellent", float("inf")):
                return ("excellent", "#2E7D32")
            if value >= threshold.get("healthy", 0):
                return ("healthy", "#4CAF50")
            if value >= threshold.get("warning", float("-inf")):
                return ("warning", "#FF9800")
            return ("danger", "#F44336")

    @staticmethod
    def classify_pe(pe_value: float) -> Tuple[str, str]:
        """PE 分析：低 PE 可能是价值洼地，高 PE 可能是高估"""
        if pd.isna(pe_value) or pe_value <= 0:
            return ("unknown", "gray")
        if pe_value < 15:
            return ("excellent", "#2E7D32")
        elif pe_value < 25:
            return ("healthy", "#4CAF50")
        elif pe_value < 50:
            return ("warning", "#FF9800")
        else:
            return ("danger", "#F44336")

    @staticmethod
    def classify_pb(pb_value: float) -> Tuple[str, str]:
        """PB 分析"""
        if pd.isna(pb_value) or pb_value <= 0:
            return ("unknown", "gray")
        if pb_value < 2:
            return ("excellent", "#2E7D32")
        elif pb_value < 4:
            return ("healthy", "#4CAF50")
        elif pb_value < 8:
            return ("warning", "#FF9800")
        else:
            return ("danger", "#F44336")

    # ------------------------------------------------------------------
    # 趋势分析
    # ------------------------------------------------------------------

    def analyze_trends(self, indicators: pd.DataFrame) -> dict:
        """
        分析各指标多年趋势
        返回趋势方向：上升/下降/稳定
        """
        trends = {}
        key_metrics = [
            "roe", "roa", "gross_margin", "net_margin",
            "revenue_growth", "net_profit_growth",
            "debt_ratio", "current_ratio", "asset_turnover",
        ]

        for metric in key_metrics:
            if metric not in indicators.columns:
                continue

            values = indicators[metric].dropna()
            if len(values) < 2:
                trends[metric] = {"direction": "数据不足", "change_pct": None}
                continue

            # 计算从首年到末年的变化
            first, last = values.iloc[0], values.iloc[-1]
            if first == 0:
                change_pct = None
            else:
                change_pct = ((last - first) / abs(first)) * 100

            if change_pct is not None:
                if change_pct > 10:
                    direction = "显著上升 ↑"
                elif change_pct > 3:
                    direction = "小幅上升 ↗"
                elif change_pct > -3:
                    direction = "基本稳定 →"
                elif change_pct > -10:
                    direction = "小幅下降 ↘"
                else:
                    direction = "显著下降 ↓"
            else:
                direction = "无法判定"

            trends[metric] = {
                "direction": direction,
                "change_pct": round(change_pct, 1) if change_pct is not None else None,
                "first_year": round(first, 2),
                "last_year": round(last, 2),
            }

        return trends

    # ------------------------------------------------------------------
    # 综合评分
    # ------------------------------------------------------------------

    def calculate_health_score(self, indicators: pd.DataFrame) -> dict:
        """
        基于最新一年的指标计算综合健康度评分 (0-100)
        加权计算各维度的得分
        """
        if indicators.empty:
            return {"score": 0, "level": "unknown", "detail": {}}

        latest = indicators.iloc[-1]
        scores = {}
        weights = {}

        # 盈利能力 (权重 35%)
        profit_metrics = {
            "roe": 15,
            "roa": 10,
            "gross_margin": 5,
            "net_margin": 5,
        }
        for metric, weight in profit_metrics.items():
            if metric in indicators.columns and not pd.isna(latest.get(metric)):
                val = latest[metric]
                th = self.thresholds.get(metric, {})
                if th:
                    if val >= th.get("excellent", 99): s = 100
                    elif val >= th.get("healthy", 79): s = 75
                    elif val >= th.get("warning", 49): s = 50
                    else: s = 25
                    scores[metric] = s * weight / 100
                    weights[metric] = weight

        # 偿债能力 (权重 25%)
        debt_metrics = {
            "debt_ratio": 10,
            "current_ratio": 10,
            "quick_ratio": 5,
        }
        for metric, weight in debt_metrics.items():
            if metric in indicators.columns and not pd.isna(latest.get(metric)):
                val = latest[metric]
                th = self.thresholds.get(metric, {})
                if th:
                    if val <= th.get("excellent", 0) if metric == "debt_ratio" else val >= th.get("excellent", 99): s = 100
                    elif (metric == "debt_ratio" and val <= th.get("healthy", 99)) or \
                         (metric != "debt_ratio" and val >= th.get("healthy", 0)): s = 75
                    elif (metric == "debt_ratio" and val <= th.get("warning", 199)) or \
                         (metric != "debt_ratio" and val >= th.get("warning", 0)): s = 50
                    else: s = 25
                    scores[metric] = s * weight / 100
                    weights[metric] = weight

        # 成长能力 (权重 25%)
        growth_metrics = {
            "revenue_growth": 15,
            "net_profit_growth": 10,
        }
        for metric, weight in growth_metrics.items():
            if metric in indicators.columns and not pd.isna(latest.get(metric)):
                val = latest[metric]
                th = self.thresholds.get(metric, {})
                if th:
                    if val >= th.get("excellent", 99): s = 100
                    elif val >= th.get("healthy", 79): s = 75
                    elif val >= th.get("warning", 49): s = 50
                    else: s = 25
                    scores[metric] = s * weight / 100
                    weights[metric] = weight

        # 营运能力 (权重 15%)
        efficiency_metrics = {
            "asset_turnover": 15,
        }
        for metric, weight in efficiency_metrics.items():
            if metric in indicators.columns and not pd.isna(latest.get(metric)):
                val = latest[metric]
                th = self.thresholds.get(metric, {})
                if th:
                    if val >= th.get("excellent", 99): s = 100
                    elif val >= th.get("healthy", 79): s = 75
                    elif val >= th.get("warning", 49): s = 50
                    else: s = 25
                    scores[metric] = s * weight / 100
                    weights[metric] = weight

        # 计算总分
        total_weight = sum(weights.values())
        if total_weight == 0:
            return {"score": 0, "level": "unknown", "detail": {}}

        raw_score = sum(scores.values()) / total_weight * 100
        raw_score = round(raw_score, 1)

        if raw_score >= 80: level = "优秀"
        elif raw_score >= 60: level = "良好"
        elif raw_score >= 40: level = "一般"
        else: level = "较差"

        return {
            "score": raw_score,
            "level": level,
            "detail": {m: {"value": latest.get(m), "score": scores.get(m, 0)} for m in weights},
        }

    # ------------------------------------------------------------------
    # 自动生成分析结论
    # ------------------------------------------------------------------

    def generate_conclusion(self, indicators: pd.DataFrame, company_name: str = "") -> str:
        """
        基于指标自动生成文字分析结论
        """
        if indicators.empty:
            return "暂无足够数据生成分析结论。"

        latest = indicators.iloc[-1]
        trends = self.analyze_trends(indicators)
        health = self.calculate_health_score(indicators)

        lines = []
        name = company_name or "该公司"
        year = latest.get("year", "最新")

        # 总览
        lines.append(f"## {name} 财务分析结论\n")
        lines.append(f"**综合评分**: {health['score']}/100 ({health['level']})\n")

        # 盈利能力
        lines.append("### 盈利能力")
        roe = latest.get("roe")
        if not pd.isna(roe):
            lines.append(f"- **ROE**: {roe:.1f}%（{self.classify_indicator('roe', roe)[0]}）")
        roa = latest.get("roa")
        if not pd.isna(roa):
            lines.append(f"- **ROA**: {roa:.1f}%")
        gm = latest.get("gross_margin")
        if not pd.isna(gm):
            lines.append(f"- **毛利率**: {gm:.1f}%")
        nm = latest.get("net_margin")
        if not pd.isna(nm):
            lines.append(f"- **净利率**: {nm:.1f}%")
        lines.append("")

        # 成长能力
        lines.append("### 成长能力")
        rg = latest.get("revenue_growth")
        if not pd.isna(rg):
            trend = trends.get("revenue_growth", {})
            lines.append(f"- **营收增长率**: {rg:.1f}%（趋势: {trend.get('direction', 'N/A')}）")
        npr = latest.get("net_profit_growth")
        if not pd.isna(npr):
            trend = trends.get("net_profit_growth", {})
            lines.append(f"- **净利润增长率**: {npr:.1f}%（趋势: {trend.get('direction', 'N/A')}）")
        lines.append("")

        # 偿债能力
        lines.append("### 偿债能力")
        dr = latest.get("debt_ratio")
        if not pd.isna(dr):
            lines.append(f"- **资产负债率**: {dr:.1f}%（{self.classify_indicator('debt_ratio', dr)[0]}）")
        cr = latest.get("current_ratio")
        if not pd.isna(cr):
            lines.append(f"- **流动比率**: {cr:.2f}")
        qr = latest.get("quick_ratio")
        if not pd.isna(qr):
            lines.append(f"- **速动比率**: {qr:.2f}")
        lines.append("")

        # 营运能力
        lines.append("### 营运能力")
        at = latest.get("asset_turnover")
        if not pd.isna(at):
            lines.append(f"- **总资产周转率**: {at:.2f}")
        it_ = latest.get("inventory_turnover")
        if not pd.isna(it_):
            lines.append(f"- **存货周转率**: {it_:.2f}")
        lines.append("")

        # 核心数据
        lines.append("### 核心数据")
        rev = latest.get("total_revenue")
        if not pd.isna(rev):
            lines.append(f"- **营业收入**: {rev:.2f} 亿")
        np_ = latest.get("net_profit")
        if not pd.isna(np_):
            lines.append(f"- **净利润**: {np_:.2f} 亿")
        ta = latest.get("total_assets")
        if not pd.isna(ta):
            lines.append(f"- **总资产**: {ta:.2f} 亿")
        te = latest.get("total_equity")
        if not pd.isna(te):
            lines.append(f"- **净资产**: {te:.2f} 亿")

        return "\n".join(lines)

    # ------------------------------------------------------------------
    # 同行业对比（预留接口）
    # ------------------------------------------------------------------

    def compare_peers(
        self,
        indicators_list: List[Dict],
    ) -> pd.DataFrame:
        """
        对比多家公司的指标
        indicators_list: [{"name": "公司A", "indicators": DataFrame}, ...]
        """
        comparison = []
        for item in indicators_list:
            name = item["name"]
            ind = item["indicators"]
            if ind.empty:
                continue
            latest = ind.iloc[-1]
            row = {"公司": name}
            for col in ["roe", "roa", "gross_margin", "net_margin",
                         "revenue_growth", "net_profit_growth",
                         "debt_ratio", "current_ratio", "asset_turnover"]:
                row[col] = latest.get(col, np.nan)
            comparison.append(row)

        return pd.DataFrame(comparison)
