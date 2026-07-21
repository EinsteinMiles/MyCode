"""
图表生成器 - 基于 matplotlib 生成财报分析图表
所有图表输出为 PNG，可直接嵌入 HTML 报告
"""

import os
import logging
import numpy as np
import pandas as pd
from typing import List, Optional, Dict

import matplotlib
matplotlib.use("Agg")  # 非交互后端，适合服务器环境
import matplotlib.pyplot as plt
import matplotlib.ticker as ticker

# 中文字体设置
plt.rcParams["font.sans-serif"] = [
    "PingFang SC", "Heiti SC", "STHeiti", "SimHei",
    "Microsoft YaHei", "WenQuanYi Micro Hei", "Arial Unicode MS",
]
plt.rcParams["axes.unicode_minus"] = False  # 解决负号显示问题

from config import CHART_DIR

logger = logging.getLogger(__name__)

# 配色方案
COLORS = {
    "primary": "#2196F3",
    "secondary": "#FF9800",
    "success": "#4CAF50",
    "danger": "#F44336",
    "warning": "#FFC107",
    "purple": "#9C27B0",
    "teal": "#009688",
    "dark": "#37474F",
    "gray": "#9E9E9E",
    "light_blue": "#BBDEFB",
}


class ChartGenerator:
    """财报数据图表生成器"""

    def __init__(self, output_dir: str = None):
        self.output_dir = output_dir or CHART_DIR
        os.makedirs(self.output_dir, exist_ok=True)

    def _save_chart(self, fig, filename: str) -> str:
        """保存图表并关闭 figure"""
        filepath = os.path.join(self.output_dir, filename)
        fig.savefig(filepath, dpi=150, bbox_inches="tight", facecolor="white")
        plt.close(fig)
        logger.info(f"图表已保存: {filepath}")
        return filepath

    # ------------------------------------------------------------------
    # 1. 营收与利润趋势
    # ------------------------------------------------------------------

    def plot_revenue_profit_trend(self, indicators: pd.DataFrame) -> str:
        """
        营收（柱状图）+ 净利润（折线图）双轴趋势
        """
        fig, ax1 = plt.subplots(figsize=(10, 5))

        years = indicators["year"].astype(int).tolist()
        revenue = indicators["total_revenue"].tolist()
        net_profit = indicators["net_profit"].tolist()

        x = range(len(years))

        # 营收柱状图
        bars = ax1.bar(x, revenue, width=0.5, color=COLORS["light_blue"], edgecolor=COLORS["primary"], label="营业收入(亿)")
        ax1.set_xlabel("年份")
        ax1.set_ylabel("营业收入（亿元）", color=COLORS["primary"])
        ax1.tick_params(axis="y", labelcolor=COLORS["primary"])

        # 净利润折线图
        ax2 = ax1.twinx()
        ax2.plot(x, net_profit, "o-", color=COLORS["danger"], linewidth=2.5, markersize=8, label="净利润(亿)")
        ax2.set_ylabel("净利润（亿元）", color=COLORS["danger"])
        ax2.tick_params(axis="y", labelcolor=COLORS["danger"])

        # 数值标签
        for i, (r, n) in enumerate(zip(revenue, net_profit)):
            ax1.text(i, r + max(revenue) * 0.02, f"{r:.1f}", ha="center", va="bottom", fontsize=8, color=COLORS["primary"])
            ax2.text(i, n + max(net_profit) * 0.02, f"{n:.1f}", ha="center", va="bottom", fontsize=8, color=COLORS["danger"])

        ax1.set_xticks(x)
        ax1.set_xticklabels(years)
        ax1.set_title("营业收入与净利润趋势", fontsize=16, fontweight="bold")

        # 图例
        lines1, labels1 = ax1.get_legend_handles_labels()
        lines2, labels2 = ax2.get_legend_handles_labels()
        ax1.legend(lines1 + lines2, labels1 + labels2, loc="upper left")

        ax1.grid(axis="y", alpha=0.3)

        return self._save_chart(fig, "revenue_profit_trend.png")

    # ------------------------------------------------------------------
    # 2. 盈利能力面板
    # ------------------------------------------------------------------

    def plot_profitability(self, indicators: pd.DataFrame) -> str:
        """ROE, ROA, 毛利率, 净利率 组合折线图"""
        fig, axes = plt.subplots(2, 2, figsize=(12, 8))

        years = indicators["year"].astype(int).tolist()
        x = range(len(years))

        metrics = [
            ("roe", "ROE (%)", COLORS["primary"], (0, 0)),
            ("roa", "ROA (%)", COLORS["teal"], (0, 1)),
            ("gross_margin", "毛利率 (%)", COLORS["success"], (1, 0)),
            ("net_margin", "净利率 (%)", COLORS["danger"], (1, 1)),
        ]

        for col, title, color, pos in metrics:
            ax = axes[pos]
            if col in indicators.columns:
                values = indicators[col].tolist()
                ax.plot(x, values, "o-", color=color, linewidth=2, markersize=7)
                # 标注数值
                for i, v in enumerate(values):
                    ax.text(i, v + max(values) * 0.03, f"{v:.1f}", ha="center", fontsize=8, color=color)
                # 添加参考线
                ax.axhline(y=sum(values)/len(values), color="gray", linestyle="--", alpha=0.5, linewidth=1, label="均值")
            ax.set_xticks(x)
            ax.set_xticklabels(years)
            ax.set_title(title, fontsize=13, fontweight="bold")
            ax.grid(axis="y", alpha=0.3)

        fig.suptitle("盈利能力指标", fontsize=16, fontweight="bold", y=1.01)
        fig.tight_layout()

        return self._save_chart(fig, "profitability.png")

    # ------------------------------------------------------------------
    # 3. 成长能力
    # ------------------------------------------------------------------

    def plot_growth(self, indicators: pd.DataFrame) -> str:
        """营收增长率 + 净利润增长率 对比柱状图"""
        fig, ax = plt.subplots(figsize=(10, 5))

        years = indicators["year"].astype(int).tolist()
        x = range(len(years))

        rev_growth = indicators.get("revenue_growth", pd.Series([0]*len(years))).tolist()
        profit_growth = indicators.get("net_profit_growth", pd.Series([0]*len(years))).tolist()

        width = 0.35
        bars1 = ax.bar([i - width/2 for i in x], rev_growth, width, color=COLORS["primary"], label="营收增长率(%)")
        bars2 = ax.bar([i + width/2 for i in x], profit_growth, width, color=COLORS["danger"], label="净利润增长率(%)")

        # 标注
        for bar in bars1:
            h = bar.get_height()
            va = "bottom" if h >= 0 else "top"
            ax.text(bar.get_x() + bar.get_width()/2, h, f"{h:.1f}", ha="center", va=va, fontsize=8)
        for bar in bars2:
            h = bar.get_height()
            va = "bottom" if h >= 0 else "top"
            ax.text(bar.get_x() + bar.get_width()/2, h, f"{h:.1f}", ha="center", va=va, fontsize=8)

        # 零线
        ax.axhline(y=0, color="black", linewidth=0.8)
        ax.set_xticks(x)
        ax.set_xticklabels(years)
        ax.set_title("成长能力指标", fontsize=16, fontweight="bold")
        ax.legend(loc="upper left")
        ax.grid(axis="y", alpha=0.3)

        return self._save_chart(fig, "growth.png")

    # ------------------------------------------------------------------
    # 4. 偿债能力雷达图
    # ------------------------------------------------------------------

    def plot_financial_health_radar(self, indicators: pd.DataFrame) -> str:
        """偿债能力 + 流动性雷达图"""
        if len(indicators) < 2:
            return ""

        fig, ax = plt.subplots(figsize=(8, 8), subplot_kw=dict(polar=True))

        # 选取最新两年对比
        latest = indicators.iloc[-1]
        previous = indicators.iloc[-2]

        categories = ["资产负债率\n(越低越好)", "流动比率", "速动比率", "股东权益比率", "ROE"]
        # 注意：资产负债率取倒数来比较（越低越好）
        latest_vals = [
            max(0, 100 - latest.get("debt_ratio", 50)),
            min(latest.get("current_ratio", 0), 5),
            min(latest.get("quick_ratio", 0), 5),
            latest.get("equity_ratio", 30),
            max(latest.get("roe", 0), 0),
        ]
        prev_vals = [
            max(0, 100 - previous.get("debt_ratio", 50)),
            min(previous.get("current_ratio", 0), 5),
            min(previous.get("quick_ratio", 0), 5),
            previous.get("equity_ratio", 30),
            max(previous.get("roe", 0), 0),
        ]

        N = len(categories)
        angles = np.linspace(0, 2 * np.pi, N, endpoint=False).tolist()
        latest_vals += latest_vals[:1]
        prev_vals += prev_vals[:1]
        angles += angles[:1]

        ax.plot(angles, latest_vals, "o-", linewidth=2, color=COLORS["primary"], label=f"{indicators['year'].iloc[-1]:.0f}年")
        ax.fill(angles, latest_vals, alpha=0.15, color=COLORS["primary"])
        ax.plot(angles, prev_vals, "o-", linewidth=2, color=COLORS["gray"], label=f"{indicators['year'].iloc[-2]:.0f}年")
        ax.fill(angles, prev_vals, alpha=0.10, color=COLORS["gray"])

        ax.set_xticks(angles[:-1])
        ax.set_xticklabels(categories, fontsize=10)
        ax.set_title("财务健康度雷达图", fontsize=14, fontweight="bold", pad=30)
        ax.legend(loc="upper right", bbox_to_anchor=(1.35, 1.1))

        return self._save_chart(fig, "health_radar.png")

    # ------------------------------------------------------------------
    # 5. 杜邦分析
    # ------------------------------------------------------------------

    def _derive_assets(self, indicators: pd.DataFrame) -> pd.Series:
        """从净资产和资产负债率推导总资产"""
        te = indicators.get("total_equity", pd.Series(dtype=float))
        dr = indicators.get("debt_ratio", pd.Series(dtype=float))

        if te.empty or dr.empty:
            return pd.Series(dtype=float)

        # total_assets = total_equity / (1 - debt_ratio/100)
        with np.errstate(divide="ignore", invalid="ignore"):
            ta = te / (1 - dr / 100)
        return ta.replace([np.inf, -np.inf], np.nan)

    def _derive_liabilities(self, indicators: pd.DataFrame) -> pd.Series:
        """从总资产和资产负债率推导总负债"""
        ta = self._derive_assets(indicators)
        dr = indicators.get("debt_ratio", pd.Series(dtype=float))
        if ta.empty or dr.empty:
            return pd.Series(dtype=float)
        return ta * dr / 100

    def plot_dupont(self, indicators: pd.DataFrame) -> str:
        """
        杜邦分析: ROE = 净利率 × 总资产周转率 × 权益乘数
        """
        fig, axes = plt.subplots(1, 3, figsize=(14, 4))

        years = indicators["year"].astype(int).tolist()
        x = range(len(years))

        # 净利率
        ax = axes[0]
        nm = indicators.get("net_margin", pd.Series([np.nan]*len(years))).tolist()
        ax.bar(x, nm, color=COLORS["success"])
        for i, v in enumerate(nm):
            if not np.isnan(v):
                ax.text(i, v + 0.1, f"{v:.1f}%", ha="center", fontsize=9)
        ax.set_xticks(x); ax.set_xticklabels(years)
        ax.set_title("净利率", fontsize=13)
        ax.grid(axis="y", alpha=0.3)

        # 总资产周转率
        ax = axes[1]
        at = indicators.get("asset_turnover", pd.Series([np.nan]*len(years))).tolist()
        ax.bar(x, at, color=COLORS["primary"])
        for i, v in enumerate(at):
            if not np.isnan(v):
                ax.text(i, v + 0.01, f"{v:.2f}", ha="center", fontsize=9)
        ax.set_xticks(x); ax.set_xticklabels(years)
        ax.set_title("总资产周转率", fontsize=13)
        ax.grid(axis="y", alpha=0.3)

        # 权益乘数 = 总资产 / 净资产
        ax = axes[2]
        ta = self._derive_assets(indicators)
        te = indicators.get("total_equity", pd.Series(dtype=float))
        em = []
        for i in range(len(years)):
            a = ta.iloc[i] if i < len(ta) else np.nan
            e = te.iloc[i] if i < len(te) else np.nan
            if pd.notna(a) and pd.notna(e) and e != 0:
                em.append(a / e)
            else:
                em.append(np.nan)
        ax.bar(x, em, color=COLORS["danger"])
        for i, v in enumerate(em):
            if not np.isnan(v):
                ax.text(i, v + 0.05, f"{v:.2f}", ha="center", fontsize=9)
        ax.set_xticks(x); ax.set_xticklabels(years)
        ax.set_title("权益乘数", fontsize=13)
        ax.grid(axis="y", alpha=0.3)

        fig.suptitle("杜邦分析: ROE分解", fontsize=16, fontweight="bold")

        return self._save_chart(fig, "dupont.png")

    # ------------------------------------------------------------------
    # 6. 资产负债结构
    # ------------------------------------------------------------------

    def plot_balance_structure(self, indicators: pd.DataFrame) -> str:
        """资产负债结构堆积图"""
        fig, ax = plt.subplots(figsize=(10, 5))

        years = indicators["year"].astype(int).tolist()
        x = range(len(years))

        # 尝试直接获取，如果不存在则推导
        equity = indicators.get("total_equity", pd.Series(dtype=float))
        liabilities = self._derive_liabilities(indicators)

        if equity.empty:
            logger.warning("无净资产数据，跳过资产负债结构图")
            plt.close(fig)
            return ""

        eq_list = equity.tolist()
        liab_list = liabilities.tolist() if not liabilities.empty else [np.nan] * len(eq_list)

        # 堆积柱状图
        ax.bar(x, eq_list, color=COLORS["success"], label="净资产(亿)")
        ax.bar(x, liab_list, bottom=eq_list, color=COLORS["danger"], label="总负债(亿)")

        # 资产负债率标注
        for i in range(len(years)):
            e = eq_list[i] if i < len(eq_list) and pd.notna(eq_list[i]) else 0
            l = liab_list[i] if i < len(liab_list) and pd.notna(liab_list[i]) else 0
            total = e + l
            if total > 0:
                ratio = l / total * 100
                ax.text(i, total + max(eq_list) * 0.02,
                        f"负债率\n{ratio:.1f}%", ha="center", fontsize=8, color=COLORS["danger"])

        ax.set_xticks(x)
        ax.set_xticklabels(years)
        ax.set_title("资产负债结构", fontsize=16, fontweight="bold")
        ax.legend(loc="upper right")
        ax.grid(axis="y", alpha=0.3)

        return self._save_chart(fig, "balance_structure.png")

    # ------------------------------------------------------------------
    # 批量生成
    # ------------------------------------------------------------------

    def generate_all(self, indicators: pd.DataFrame) -> List[str]:
        """生成全部图表，返回文件路径列表"""
        if indicators.empty:
            logger.warning("无数据，无法生成图表")
            return []

        chart_files = []

        try:
            chart_files.append(self.plot_revenue_profit_trend(indicators))
        except Exception as e:
            logger.error(f"营收利润趋势图失败: {e}")

        try:
            chart_files.append(self.plot_profitability(indicators))
        except Exception as e:
            logger.error(f"盈利能力图失败: {e}")

        try:
            chart_files.append(self.plot_growth(indicators))
        except Exception as e:
            logger.error(f"成长能力图失败: {e}")

        try:
            radar = self.plot_financial_health_radar(indicators)
            if radar:
                chart_files.append(radar)
        except Exception as e:
            logger.error(f"雷达图失败: {e}")

        try:
            chart_files.append(self.plot_dupont(indicators))
        except Exception as e:
            logger.error(f"杜邦分析图失败: {e}")

        try:
            chart_files.append(self.plot_balance_structure(indicators))
        except Exception as e:
            logger.error(f"资产负债结构图失败: {e}")

        logger.info(f"图表生成完成: {len(chart_files)} 张")
        return chart_files
