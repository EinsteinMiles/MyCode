"""
选品分析器 — 跨境电商版
加权综合评分模型（5 维度）
"""

from typing import List, Tuple, Dict, Any, Optional
import math

from config import logger
from core.models import Product
from core.storage import Database


class ProductSelector:
    """
    选品综合评分模型

    评分维度：
    - Price Competitiveness (30%)
    - Sales Performance (25%)
    - Review Quality (20%)
    - Competition Level (15%)
    - Profit Potential (10%)
    """

    DEFAULT_WEIGHTS = {
        "price_competitiveness": 0.30,
        "sales_performance": 0.25,
        "review_quality": 0.20,
        "competition_level": 0.15,
        "profit_potential": 0.10,
    }

    def __init__(self, db: Database, weights: Dict[str, float] = None):
        self.db = db
        self.weights = weights or self.DEFAULT_WEIGHTS

    def score_price_competitiveness(self, product: Product, avg_price: float) -> float:
        """价格竞争力评分 (0-100)"""
        if product.price <= 0 or avg_price <= 0:
            return 50.0

        ratio = product.price / avg_price
        if ratio <= 0.5:
            return 90.0
        elif ratio <= 0.7:
            return 80.0
        elif ratio <= 0.9:
            return 70.0
        elif ratio <= 1.1:
            return 60.0
        elif ratio <= 1.5:
            return 40.0
        else:
            return 20.0

    def score_sales_performance(
        self, product: Product, max_sales: int, median_sales: float
    ) -> float:
        """销量表现评分 (0-100)"""
        if product.sales_count <= 0:
            return 30.0 if not product.sales_text else 40.0
        if max_sales <= 0:
            return 50.0

        log_sales = math.log(product.sales_count + 1)
        log_max = math.log(max_sales + 1)
        log_median = math.log(median_sales + 1) if median_sales > 0 else log_max / 2
        ratio = (log_sales - log_median) / (log_max - log_median) if log_max > log_median else 0.5
        return min(100, max(0, 50 + ratio * 50))

    def score_review_quality(self, product_db_id: int) -> float:
        """评价质量评分 (0-100)"""
        stats = self.db.get_review_sentiment_stats(product_db_id)
        total = sum(stats.values())
        if total == 0:
            return 50.0

        positive = stats.get("positive", 0)
        positive_rate = positive / total
        volume_bonus = min(20, math.log(total + 1) * 4)
        return min(100, positive_rate * 80 + volume_bonus)

    def score_competition(self, product: Product, total_in_category: int) -> float:
        """竞争度评分 (0-100)"""
        if total_in_category <= 0:
            return 50.0

        if 20 <= total_in_category <= 100:
            return 80.0
        elif total_in_category < 20:
            return 50.0 + total_in_category * 1.5
        elif total_in_category <= 300:
            return 80.0 - (total_in_category - 100) * 0.15
        else:
            return max(20.0, 50.0 - (total_in_category - 300) * 0.05)

    def score_profit_potential(self, product: Product, avg_price: float) -> float:
        """利润空间评分 (0-100)"""
        if product.price <= 0:
            return 40.0

        # 低单价 + 高评分 = 转售利润空间
        review_bonus = min(15, product.rating * 3) if product.rating > 0 else 0

        if avg_price > 0 and product.price < avg_price:
            margin = (avg_price - product.price) / avg_price * 100
            return min(100, 50 + margin * 0.5 + review_bonus)

        return 30.0 + review_bonus

    # ── 综合排名 ──────────────────────────────────────

    def rank_products(
        self, products: List[Product], category: str = ""
    ) -> List[Tuple[Product, float, int]]:
        """综合评分并排名"""
        if not products:
            return []

        prices = [p.price for p in products if p.price > 0]
        avg_price = sum(prices) / len(prices) if prices else 0
        sales = [p.sales_count for p in products if p.sales_count > 0]
        max_sales = max(sales) if sales else 0
        median_sales = sorted(sales)[len(sales) // 2] if sales else 0
        total_in_category = len(products)

        results = []
        for product in products:
            try:
                score_parts = {
                    "price_competitiveness": self.score_price_competitiveness(product, avg_price),
                    "sales_performance": self.score_sales_performance(product, max_sales, median_sales),
                    "review_quality": self.score_review_quality(product.id) if product.id else 50.0,
                    "competition_level": self.score_competition(product, total_in_category),
                    "profit_potential": self.score_profit_potential(product, avg_price),
                }

                total_score = sum(
                    score_parts[k] * self.weights[k]
                    for k in self.weights
                )

                results.append((product, round(total_score, 1), score_parts))

            except Exception as e:
                logger.warning(f"评分失败: {product.title[:30]}... - {e}")
                results.append((product, 30.0, {}))

        results.sort(key=lambda x: x[1], reverse=True)
        ranked = [(p, s, i + 1) for i, (p, s, _) in enumerate(results)]
        return ranked

    def get_recommendations(
        self, ranked: List[Tuple[Product, float, int]]
    ) -> Dict[str, List]:
        """将排名结果分组为推荐等级"""
        recommended = []
        worth_considering = []
        skip = []

        for product, score, rank in ranked:
            if score >= 80:
                recommended.append((product, score, rank))
            elif score >= 60:
                worth_considering.append((product, score, rank))
            else:
                skip.append((product, score, rank))

        return {
            "recommended": recommended,
            "worth_considering": worth_considering,
            "skip": skip,
        }
