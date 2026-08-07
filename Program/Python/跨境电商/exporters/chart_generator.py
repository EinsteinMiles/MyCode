"""
图表生成器 — 跨境电商版
中文标签，多币种支持
"""

import os
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.ticker as ticker
import numpy as np

from config import CHART_DIR, logger

# ── 中文字体配置 ──────────────────────────────────────
plt.rcParams["axes.unicode_minus"] = False
# macOS 优先使用 PingFang / Heiti，Windows 使用 Microsoft YaHei
for _font in ["PingFang SC", "Heiti SC", "Microsoft YaHei", "SimHei", "Arial Unicode MS"]:
    try:
        plt.rcParams["font.sans-serif"] = [_font]
        break
    except Exception:
        continue

# ── 配色方案 ──────────────────────────────────────────
COLORS = {
    "primary": "#4A90D9",
    "secondary": "#6C757D",
    "success": "#28A745",
    "danger": "#DC3545",
    "warning": "#FFC107",
    "info": "#17A2B8",
    "purple": "#6F42C1",
    "teal": "#20C997",
    "orange": "#FD7E14",
    "pink": "#E83E8C",
}
CHART_COLORS = list(COLORS.values())


class ChartGenerator:
    """图表生成器"""

    def __init__(self, output_dir: str = CHART_DIR):
        self.output_dir = output_dir
        os.makedirs(output_dir, exist_ok=True)

    @staticmethod
    def _save_chart(fig, filename: str, dpi: int = 150) -> str:
        filepath = os.path.join(CHART_DIR, filename)
        fig.savefig(filepath, dpi=dpi, bbox_inches="tight", facecolor="white")
        plt.close(fig)
        logger.info(f"图表已保存: {filepath}")
        return filepath

    # ── 价格趋势折线图 ────────────────────────────────

    def plot_price_trend(
        self, dates: list, prices: list,
        product_name: str = "", currency: str = "USD",
        filename: str = "price_trend.png",
    ) -> str:
        sym = "$" if currency == "USD" else ("€" if currency == "EUR" else "£")
        fig, ax = plt.subplots(figsize=(10, 5))

        ax.plot(dates, prices, color=COLORS["primary"], linewidth=2,
                marker="o", markersize=4, label="价格")

        if len(prices) > 1:
            min_idx = np.argmin(prices)
            max_idx = np.argmax(prices)
            ax.annotate(f"{sym}{prices[min_idx]:.2f}",
                        (dates[min_idx], prices[min_idx]),
                        textcoords="offset points", xytext=(0, -15), ha="center",
                        fontsize=9, color=COLORS["success"])
            ax.annotate(f"{sym}{prices[max_idx]:.2f}",
                        (dates[max_idx], prices[max_idx]),
                        textcoords="offset points", xytext=(0, 10), ha="center",
                        fontsize=9, color=COLORS["danger"])

        title = f"价格趋势 - {product_name}" if product_name else "价格趋势"
        ax.set_title(title, fontsize=14, fontweight="bold")
        ax.set_xlabel("日期")
        ax.set_ylabel(f"价格 ({currency})")
        ax.yaxis.set_major_formatter(ticker.FormatStrFormatter(f"{sym}%.2f"))
        ax.legend()
        ax.grid(True, alpha=0.3)
        fig.autofmt_xdate()

        return self._save_chart(fig, filename)

    # ── 销量排行横向柱状图 ────────────────────────────

    def plot_sales_ranking(
        self, titles: list, sales: list,
        title: str = "销量排行",
        filename: str = "sales_ranking.png", top_n: int = 15,
    ) -> str:
        titles = titles[:top_n][::-1]
        sales = sales[:top_n][::-1]

        fig, ax = plt.subplots(figsize=(10, max(6, top_n * 0.4)))
        colors = [COLORS["primary"]] * len(sales)
        if sales:
            colors[-1] = COLORS["success"]

        bars = ax.barh(range(len(titles)), sales, color=colors)
        for bar, val in zip(bars, sales):
            if val >= 1000:
                label = f"{val/1000:.1f}K"
            else:
                label = str(val)
            ax.text(bar.get_width() + max(sales) * 0.01,
                    bar.get_y() + bar.get_height()/2,
                    label, va="center", fontsize=9)

        ax.set_yticks(range(len(titles)))
        ax.set_yticklabels([t[:25] for t in titles], fontsize=9)
        ax.set_title(title, fontsize=14, fontweight="bold")
        ax.set_xlabel("销量")
        ax.grid(True, alpha=0.3, axis="x")

        return self._save_chart(fig, filename)

    # ── 情感饼图 ──────────────────────────────────────

    def plot_sentiment_pie(
        self, positive: int = 0, neutral: int = 0, negative: int = 0,
        product_name: str = "", filename: str = "sentiment_pie.png",
    ) -> str:
        fig, ax = plt.subplots(figsize=(7, 7))

        labels = ["正面", "中性", "负面"]
        sizes = [positive, neutral, negative]
        sentiment_colors = [COLORS["success"], COLORS["warning"], COLORS["danger"]]

        filtered = [(l, s, c) for l, s, c in zip(labels, sizes, sentiment_colors) if s > 0]
        if not filtered:
            ax.text(0.5, 0.5, "暂无评论数据", ha="center", va="center", fontsize=14)
            ax.set_title("评论情感分布")
            return self._save_chart(fig, filename)

        labels, sizes, sentiment_colors = zip(*filtered)
        wedges, texts, autotexts = ax.pie(
            sizes, labels=None, autopct="%1.1f%%",
            colors=sentiment_colors, startangle=90,
            wedgeprops={"width": 0.4, "edgecolor": "white"},
            textprops={"fontsize": 11},
        )
        ax.legend(wedges, [f"{l} ({s})" for l, s in zip(labels, sizes)],
                  loc="center left", bbox_to_anchor=(1, 0, 0.5, 1))

        title = f"评论情感 - {product_name}" if product_name else "评论情感"
        ax.set_title(title, fontsize=14, fontweight="bold")

        return self._save_chart(fig, filename)

    # ── 痛点柱状图 ────────────────────────────────────

    def plot_pain_points(
        self, keywords: list, frequencies: list,
        product_name: str = "", title: str = "用户痛点",
        filename: str = "pain_points.png", top_n: int = 15,
    ) -> str:
        keywords = keywords[:top_n][::-1]
        frequencies = frequencies[:top_n][::-1]

        fig, ax = plt.subplots(figsize=(10, max(6, top_n * 0.4)))

        norm = plt.Normalize(min(frequencies), max(frequencies)) if frequencies else plt.Normalize(0, 1)
        bar_colors = [plt.cm.Reds(norm(f)) for f in frequencies]

        ax.barh(range(len(keywords)), frequencies, color=bar_colors)
        for i, (kw, freq) in enumerate(zip(keywords, frequencies)):
            ax.text(freq + max(frequencies) * 0.01, i, f"{kw} ({freq})",
                    va="center", fontsize=9)

        ax.set_yticks(range(len(keywords)))
        ax.set_yticklabels(keywords, fontsize=9)

        chart_title = f"{title} - {product_name}" if product_name else title
        ax.set_title(chart_title, fontsize=14, fontweight="bold")
        ax.set_xlabel("出现频次")
        ax.grid(True, alpha=0.3, axis="x")

        return self._save_chart(fig, filename)

    # ── 选品雷达图 ────────────────────────────────────

    def plot_selection_radar(
        self, categories: list, scores: list,
        product_name: str = "", filename: str = "selection_radar.png",
    ) -> str:
        N = len(categories)
        angles = [n / float(N) * 2 * np.pi for n in range(N)]
        angles += angles[:1]

        scores_closed = list(scores) + [scores[0]]

        fig, ax = plt.subplots(figsize=(7, 7), subplot_kw={"projection": "polar"})

        ax.fill(angles, scores_closed, COLORS["primary"], alpha=0.25)
        ax.plot(angles, scores_closed, COLORS["primary"], linewidth=2)

        for level in [20, 40, 60, 80]:
            ax.plot(angles, [level] * len(angles), color="gray", alpha=0.2, linewidth=0.5)

        ax.set_xticks(angles[:-1])
        ax.set_xticklabels([c[:20] for c in categories], fontsize=10)
        ax.set_ylim(0, 100)
        ax.set_yticks([20, 40, 60, 80, 100])
        ax.set_yticklabels(["20", "40", "60", "80", "100"], fontsize=7, color="gray")

        title = f"选品评分 - {product_name}" if product_name else "选品评分"
        ax.set_title(title, fontsize=14, fontweight="bold", pad=20)

        return self._save_chart(fig, filename)

    # ── 价格对比柱状图 ────────────────────────────────

    def plot_price_comparison(
        self, products: list, prices: list,
        title: str = "价格对比", currency: str = "USD",
        filename: str = "price_comparison.png",
    ) -> str:
        sym = "$" if currency == "USD" else ("€" if currency == "EUR" else "£")
        products = products[:12][::-1]
        prices = prices[:12][::-1]

        fig, ax = plt.subplots(figsize=(10, max(5, len(products) * 0.4)))
        avg_price = np.mean(prices) if prices else 0

        bar_colors = [
            COLORS["danger"] if p > avg_price * 1.2 else
            COLORS["success"] if p < avg_price * 0.8 else
            COLORS["primary"]
            for p in prices
        ]

        ax.barh(range(len(products)), prices, color=bar_colors)
        ax.axvline(avg_price, color=COLORS["secondary"], linestyle="--",
                   linewidth=1, label=f"均价 {sym}{avg_price:.2f}")

        for i, p in enumerate(prices):
            ax.text(p + max(prices) * 0.01, i, f"{sym}{p:.2f}", va="center", fontsize=9)

        ax.set_yticks(range(len(products)))
        ax.set_yticklabels([p[:30] for p in products], fontsize=9)
        ax.set_title(title, fontsize=14, fontweight="bold")
        ax.set_xlabel(f"价格 ({currency})")
        ax.legend()

        return self._save_chart(fig, filename)
