"""
图表生成器
参考 财报分析/display/charts.py 的 ChartGenerator 模式
包含中文字体自动检测、多种图表类型
"""

import os
import matplotlib
matplotlib.use("Agg")  # 非交互后端，参考财报分析
import matplotlib.pyplot as plt
import matplotlib.ticker as ticker
import numpy as np

from config import CHART_DIR, logger

# ── 中文字体配置（参考 财报分析/display/charts.py 行18-22）──
_CHINESE_FONTS = [
    "PingFang SC", "Heiti SC", "STHeiti", "Songti SC",
    "SimHei", "Microsoft YaHei", "WenQuanYi Micro Hei",
    "Arial Unicode MS", "Noto Sans CJK SC", "sans-serif",
]

for _font in _CHINESE_FONTS:
    try:
        matplotlib.font_manager.findfont(_font, fallback_to_default=False)
        plt.rcParams["font.sans-serif"] = [_font] + plt.rcParams["font.sans-serif"]
        logger.debug(f"使用中文字体: {_font}")
        break
    except Exception:
        continue

plt.rcParams["axes.unicode_minus"] = False

# ── 色板（参考 财报分析 语义色板）─────────────────────
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
    """图表生成器（参考 财报分析/display/charts.py::ChartGenerator）"""

    def __init__(self, output_dir: str = CHART_DIR):
        self.output_dir = output_dir
        os.makedirs(output_dir, exist_ok=True)

    @staticmethod
    def _save_chart(fig, filename: str, dpi: int = 150) -> str:
        """标准化保存（参考 财报分析 _save_chart）"""
        filepath = os.path.join(CHART_DIR, filename)
        fig.savefig(filepath, dpi=dpi, bbox_inches="tight", facecolor="white")
        plt.close(fig)
        logger.info(f"图表已保存: {filepath}")
        return filepath

    # ── 价格趋势折线图 ────────────────────────────────

    def plot_price_trend(
        self,
        dates: list,
        prices: list,
        product_name: str = "",
        filename: str = "price_trend.png",
    ) -> str:
        """价格历史趋势折线图"""
        fig, ax = plt.subplots(figsize=(10, 5))

        ax.plot(dates, prices, color=COLORS["primary"], linewidth=2,
                marker="o", markersize=4, label="价格")

        # 标注最低价和最高价
        if len(prices) > 1:
            min_idx = np.argmin(prices)
            max_idx = np.argmax(prices)
            ax.annotate(f"¥{prices[min_idx]:.2f}", (dates[min_idx], prices[min_idx]),
                        textcoords="offset points", xytext=(0, -15), ha="center",
                        fontsize=9, color=COLORS["success"])
            ax.annotate(f"¥{prices[max_idx]:.2f}", (dates[max_idx], prices[max_idx]),
                        textcoords="offset points", xytext=(0, 10), ha="center",
                        fontsize=9, color=COLORS["danger"])

        title = f"价格趋势 - {product_name}" if product_name else "价格趋势"
        ax.set_title(title, fontsize=14, fontweight="bold")
        ax.set_xlabel("日期")
        ax.set_ylabel("价格 (¥)")
        ax.yaxis.set_major_formatter(ticker.FormatStrFormatter("¥%.2f"))
        ax.legend()
        ax.grid(True, alpha=0.3)
        fig.autofmt_xdate()

        return self._save_chart(fig, filename)

    # ── 销量排行柱状图 ────────────────────────────────

    def plot_sales_ranking(
        self,
        titles: list,
        sales: list,
        title: str = "销量排行",
        filename: str = "sales_ranking.png",
        top_n: int = 15,
    ) -> str:
        """销量排行水平柱状图"""
        # 取 Top N
        titles = titles[:top_n][::-1]
        sales = sales[:top_n][::-1]

        fig, ax = plt.subplots(figsize=(10, max(6, top_n * 0.4)))

        colors = [COLORS["primary"]] * len(sales)
        # 最高销量高亮
        if sales:
            colors[-1] = COLORS["success"]

        bars = ax.barh(range(len(titles)), sales, color=colors)

        for i, (bar, val) in enumerate(zip(bars, sales)):
            if val >= 10000:
                label = f"{val/10000:.1f}万"
            else:
                label = str(val)
            ax.text(bar.get_width() + max(sales) * 0.01, bar.get_y() + bar.get_height()/2,
                    label, va="center", fontsize=9)

        ax.set_yticks(range(len(titles)))
        ax.set_yticklabels([t[:25] for t in titles], fontsize=9)
        ax.set_title(title, fontsize=14, fontweight="bold")
        ax.set_xlabel("销量")
        ax.grid(True, alpha=0.3, axis="x")

        return self._save_chart(fig, filename)

    # ── 品类分布饼图 ──────────────────────────────────

    def plot_category_pie(
        self,
        labels: list,
        values: list,
        title: str = "品类分布",
        filename: str = "category_pie.png",
    ) -> str:
        """品类占比饼图"""
        fig, ax = plt.subplots(figsize=(8, 8))

        colors = CHART_COLORS[:len(labels)]
        wedges, texts, autotexts = ax.pie(
            values, labels=None, autopct="%1.1f%%",
            colors=colors, startangle=90,
            textprops={"fontsize": 10},
        )

        ax.legend(wedges, [f"{l} ({v})" for l, v in zip(labels, values)],
                  title="品类", loc="center left", bbox_to_anchor=(1, 0, 0.5, 1))

        ax.set_title(title, fontsize=14, fontweight="bold")

        return self._save_chart(fig, filename)

    # ── 情感分析饼图 ──────────────────────────────────

    def plot_sentiment_pie(
        self,
        positive: int = 0,
        neutral: int = 0,
        negative: int = 0,
        product_name: str = "",
        filename: str = "sentiment_pie.png",
    ) -> str:
        """评论情感分布环形图"""
        fig, ax = plt.subplots(figsize=(7, 7))

        labels = ["好评", "中评", "差评"]
        sizes = [positive, neutral, negative]
        sentiment_colors = [COLORS["success"], COLORS["warning"], COLORS["danger"]]

        # 过滤掉零值
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

        ax.legend(wedges, [f"{l} ({s}条)" for l, s in zip(labels, sizes)],
                  loc="center left", bbox_to_anchor=(1, 0, 0.5, 1))

        title = f"评论情感分布 - {product_name}" if product_name else "评论情感分布"
        ax.set_title(title, fontsize=14, fontweight="bold")

        return self._save_chart(fig, filename)

    # ── 痛点柱状图 ─────────────────────────────────────

    def plot_pain_points(
        self,
        keywords: list,
        frequencies: list,
        title: str = "用户痛点分析",
        filename: str = "pain_points.png",
        top_n: int = 15,
    ) -> str:
        """痛点关键词柱状图"""
        keywords = keywords[:top_n][::-1]
        frequencies = frequencies[:top_n][::-1]

        fig, ax = plt.subplots(figsize=(10, max(6, top_n * 0.4)))

        # 渐变色（频率越高颜色越深）
        norm = plt.Normalize(min(frequencies), max(frequencies)) if frequencies else plt.Normalize(0, 1)
        bar_colors = [plt.cm.Reds(norm(f)) for f in frequencies]

        ax.barh(range(len(keywords)), frequencies, color=bar_colors)

        for i, (kw, freq) in enumerate(zip(keywords, frequencies)):
            ax.text(freq + max(frequencies) * 0.01, i, f"{kw} ({freq})",
                    va="center", fontsize=9)

        ax.set_yticks(range(len(keywords)))
        ax.set_yticklabels(keywords, fontsize=9)
        ax.set_title(title, fontsize=14, fontweight="bold")
        ax.set_xlabel("出现频次")
        ax.grid(True, alpha=0.3, axis="x")

        return self._save_chart(fig, filename)

    # ── 选品评分雷达图 ────────────────────────────────

    def plot_selection_radar(
        self,
        categories: list,
        scores: list,
        product_name: str = "",
        filename: str = "selection_radar.png",
    ) -> str:
        """选品综合评分雷达图（参考 财报分析 plot_financial_health_radar）"""
        N = len(categories)
        angles = [n / float(N) * 2 * np.pi for n in range(N)]
        angles += angles[:1]  # 闭合

        scores_closed = list(scores) + [scores[0]]
        categories_closed = list(categories) + [categories[0]]

        fig, ax = plt.subplots(figsize=(7, 7), subplot_kw={"projection": "polar"})

        ax.fill(angles, scores_closed, COLORS["primary"], alpha=0.25)
        ax.plot(angles, scores_closed, COLORS["primary"], linewidth=2)

        # 添加参考线
        for level in [20, 40, 60, 80]:
            ax.plot(angles, [level] * len(angles), color="gray", alpha=0.2, linewidth=0.5)

        ax.set_xticks(angles[:-1])
        ax.set_xticklabels(categories, fontsize=10)
        ax.set_ylim(0, 100)
        ax.set_yticks([20, 40, 60, 80, 100])
        ax.set_yticklabels(["20", "40", "60", "80", "100"], fontsize=7, color="gray")

        title = f"选品评分 - {product_name}" if product_name else "选品综合评分"
        ax.set_title(title, fontsize=14, fontweight="bold", pad=20)

        return self._save_chart(fig, filename)

    # ── 价格对比柱状图 ────────────────────────────────

    def plot_price_comparison(
        self,
        products: list,
        prices: list,
        title: str = "价格对比",
        filename: str = "price_comparison.png",
    ) -> str:
        """多商品价格横向对比"""
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
                   linewidth=1, label=f"均价 ¥{avg_price:.2f}")

        for i, p in enumerate(prices):
            ax.text(p + max(prices) * 0.01, i, f"¥{p:.2f}", va="center", fontsize=9)

        ax.set_yticks(range(len(products)))
        ax.set_yticklabels([p[:30] for p in products], fontsize=9)
        ax.set_title(title, fontsize=14, fontweight="bold")
        ax.set_xlabel("价格 (¥)")
        ax.legend()

        return self._save_chart(fig, filename)

    # ── 批量生成 ──────────────────────────────────────

    def generate_all_for_product(self, product_name: str, data: dict) -> list:
        """
        为一个商品生成所有相关图表
        每个图表独立 try/except（参考 财报分析 generate_all）
        """
        files = []
        chart_methods = [
            ("plot_price_trend", data.get("dates", []), data.get("prices", [])),
            ("plot_sentiment_pie", data.get("positive", 0), data.get("neutral", 0), data.get("negative", 0)),
            ("plot_pain_points", data.get("keywords", []), data.get("frequencies", [])),
            ("plot_selection_radar", data.get("dimensions", []), data.get("dim_scores", [])),
        ]

        for method_name, *args in chart_methods:
            try:
                method = getattr(self, method_name)
                kwargs = {"product_name": product_name} if "product_name" in method.__code__.co_varnames else {}
                result = method(*args, **kwargs)
                files.append(result)
            except Exception as e:
                logger.warning(f"图表 {method_name} 生成失败: {e}")

        return files
