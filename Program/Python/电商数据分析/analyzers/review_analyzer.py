"""
评论分析器
三阶段 NLP 管线：jieba 分词 → SnowNLP 情感 → TF-IDF 痛点提取 + 词云
"""

import os
import re
from typing import List, Dict, Tuple, Any
from collections import Counter

from config import (
    SENTIMENT_POSITIVE, SENTIMENT_NEGATIVE,
    MAX_REVIEW_PAGES, logger,
)
from core.models import Review
from core.storage import Database
from core.utils import clean_text


# ── 电商停用词 ────────────────────────────────────────
ECOMMERCE_STOP_WORDS = set([
    "的", "了", "在", "是", "我", "有", "和", "就", "不", "人", "都", "一",
    "一个", "上", "也", "很", "到", "说", "要", "去", "你", "会", "着",
    "没有", "看", "好", "自己", "这", "他", "她", "它", "们", "那", "些",
    "这个", "那个", "哪个", "什么", "怎么", "怎样", "因为", "所以", "但是",
    "然后", "可以", "还是", "比较", "非常", "真的", "特别", "不错", "还行",
    "感觉", "觉得", "应该", "可能", "已经", "一直", "以后", "东西", "买",
    "质量", "收到", "快递", "客服", "包装", "物流", "颜色", "尺码", "效果",
    "使用", "宝贝", "店家", "卖家", "好评", "差评", "大家", "这次", "下次",
])

# ── 痛点维度关键词映射 ────────────────────────────────
PAIN_POINT_DIMENSIONS = {
    "质量做工": ["质量差", "做工", "粗糙", "坏了", "破损", "掉色", "开线", "裂缝", "瑕疵", "次品", "变形"],
    "物流配送": ["快递慢", "不发货", "物流慢", "少发", "漏发", "发错", "破损", "暴力", "迟迟", "没收到"],
    "客服服务": ["态度差", "不理人", "忽悠", "敷衍", "不回复", "推诿", "踢皮球", "态度", "客服"],
    "价格问题": ["贵了", "不值", "坑", "降价", "买贵", "差价", "套路", "虚假", "标价"],
    "描述不符": ["不一样", "不符", "差距", "差异", "盗版", "山寨", "不是正品", "假货", "冒充"],
    "售后体验": ["退货", "不处理", "推脱", "维权", "退款", "无门", "不认账", "过期"],
}


class ReviewAnalyzer:
    """评论分析器"""

    def __init__(self, db: Database):
        self.db = db
        self._jieba_loaded = False

    def _ensure_jieba(self):
        """延迟加载 jieba"""
        if self._jieba_loaded:
            return
        try:
            import jieba
            jieba.setLogLevel(20)  # 减少 jieba 日志
            self._jieba_loaded = True
        except ImportError:
            raise ImportError("请安装 jieba: pip install jieba")

    # ── 情感分析 ──────────────────────────────────────

    def analyze_sentiment(self, product_db_id: int) -> Dict[str, Any]:
        """
        批量情感分析
        使用 SnowNLP 对产品评论进行情感打分
        """
        reviews = self.db.get_reviews(product_db_id, limit=500)
        if not reviews:
            logger.warning("没有评论数据可供分析")
            return {"total": 0, "positive": 0, "neutral": 0, "negative": 0, "avg_sentiment": 0}

        try:
            from snownlp import SnowNLP
        except ImportError:
            logger.warning("SnowNLP 未安装，使用基于评分的简单情感判断")
            return self._simple_sentiment(reviews)

        positive = neutral = negative = 0
        total_score = 0.0

        for review in reviews:
            if not review.content or len(review.content.strip()) < 2:
                continue

            try:
                s = SnowNLP(review.content)
                score = s.sentiments  # 0-1
            except Exception:
                score = review.rating / 5.0 if review.rating > 0 else 0.5

            review.sentiment_score = round(score, 3)

            if score >= SENTIMENT_POSITIVE:
                review.sentiment_label = "positive"
                positive += 1
            elif score < SENTIMENT_NEGATIVE:
                review.sentiment_label = "negative"
                negative += 1
            else:
                review.sentiment_label = "neutral"
                neutral += 1

            total_score += score

            # 更新到数据库
            try:
                self.db.conn.execute(
                    "UPDATE reviews SET sentiment_score=?, sentiment_label=? WHERE id=?",
                    (review.sentiment_score, review.sentiment_label, review.id),
                )
            except Exception:
                pass

        self.db.conn.commit()

        total = positive + neutral + negative
        return {
            "total": total,
            "positive": positive,
            "neutral": neutral,
            "negative": negative,
            "avg_sentiment": round(total_score / total, 3) if total > 0 else 0,
            "positive_rate": round(positive / total * 100, 1) if total > 0 else 0,
        }

    def _simple_sentiment(self, reviews: List[Review]) -> Dict[str, Any]:
        """基于评分的简单情感判断（无需 SnowNLP）"""
        positive = neutral = negative = 0
        for review in reviews:
            if review.rating >= 4:
                review.sentiment_label = "positive"
                review.sentiment_score = 0.8
                positive += 1
            elif review.rating <= 2:
                review.sentiment_label = "negative"
                review.sentiment_score = 0.3
                negative += 1
            else:
                review.sentiment_label = "neutral"
                review.sentiment_score = 0.5
                neutral += 1

        total = positive + neutral + negative
        return {
            "total": total,
            "positive": positive,
            "neutral": neutral,
            "negative": negative,
            "avg_sentiment": round((positive * 0.8 + neutral * 0.5 + negative * 0.3) / total, 3) if total > 0 else 0,
            "positive_rate": round(positive / total * 100, 1) if total > 0 else 0,
        }

    # ── 痛点提取 ──────────────────────────────────────

    def extract_pain_points(
        self, product_db_id: int, top_n: int = 20
    ) -> List[Tuple[str, int, float]]:
        """
        提取痛点关键词
        返回: [(关键词, 频次, 平均情感分), ...]
        """
        self._ensure_jieba()
        import jieba
        import jieba.analyse

        # 只分析差评
        negative_reviews = self.db.get_reviews(product_db_id, sentiment_label="negative", limit=200)
        if not negative_reviews:
            # 如果没有标记情感，取所有评论
            negative_reviews = self.db.get_reviews(product_db_id, limit=200)

        # 拼接文本
        all_text = " ".join(r.content for r in negative_reviews if r.content)

        if not all_text:
            return []

        # TF-IDF 关键词提取
        try:
            keywords = jieba.analyse.extract_tags(
                all_text, topK=top_n * 2, withWeight=True,
            )
        except Exception as e:
            logger.warning(f"TF-IDF 提取失败: {e}")
            return []

        # 过滤停用词和短词
        results = []
        for kw, weight in keywords:
            if kw in ECOMMERCE_STOP_WORDS or len(kw) < 2:
                continue

            # 计算该关键词的平均情感分
            related_reviews = [
                r for r in negative_reviews
                if r.content and kw in r.content
            ]
            avg_sentiment = (
                sum(r.sentiment_score for r in related_reviews) / len(related_reviews)
                if related_reviews else 0.3
            )

            freq = len(related_reviews)
            results.append((kw, freq, round(avg_sentiment, 2)))

        # 按频次排序
        results.sort(key=lambda x: x[1], reverse=True)
        return results[:top_n]

    # ── 痛点维度分类 ──────────────────────────────────

    def classify_pain_dimensions(
        self, pain_points: List[Tuple[str, int, float]]
    ) -> Dict[str, int]:
        """
        将痛点关键词映射到维度
        """
        dimensions = {dim: 0 for dim in PAIN_POINT_DIMENSIONS}

        for kw, freq, _ in pain_points:
            for dim, keywords in PAIN_POINT_DIMENSIONS.items():
                if any(k in kw for k in keywords):
                    dimensions[dim] += freq
                    break

        return dimensions

    # ── 词频统计 ──────────────────────────────────────

    def get_word_frequency(
        self, product_db_id: int, top_n: int = 50
    ) -> List[Tuple[str, int]]:
        """获取词频统计"""
        self._ensure_jieba()
        import jieba

        reviews = self.db.get_reviews(product_db_id, limit=500)
        all_words = []

        for review in reviews:
            if not review.content:
                continue
            words = jieba.cut(clean_text(review.content))
            all_words.extend(
                w for w in words
                if len(w) >= 2 and w not in ECOMMERCE_STOP_WORDS
            )

        return Counter(all_words).most_common(top_n)

    # ── 词云 ──────────────────────────────────────────

    def generate_wordcloud(
        self, product_db_id: int, output_path: str = ""
    ) -> str:
        """生成评论词云图"""
        try:
            from wordcloud import WordCloud
            import matplotlib.pyplot as plt
        except ImportError:
            logger.warning("wordcloud 未安装: pip install wordcloud")
            return ""

        reviews = self.db.get_reviews(product_db_id, limit=500)
        text = " ".join(r.content for r in reviews if r.content)

        if not text:
            return ""

        # 查找中文字体
        from config import CHART_DIR
        font_path = None
        for fp in [
            "/System/Library/Fonts/PingFang.ttc",
            "/System/Library/Fonts/STHeiti Light.ttc",
            "/System/Library/Fonts/Hiragino Sans GB.ttc",
        ]:
            if os.path.exists(fp):
                font_path = fp
                break

        wc = WordCloud(
            font_path=font_path,
            width=800, height=500,
            background_color="white",
            max_words=200,
            collocations=False,
        ).generate(text)

        if not output_path:
            output_path = os.path.join(CHART_DIR, f"wordcloud_{product_db_id}.png")

        wc.to_file(output_path)
        logger.info(f"词云已生成: {output_path}")
        return output_path

    # ── 综合分析 ──────────────────────────────────────

    def full_analysis(self, product_db_id: int) -> Dict[str, Any]:
        """对一个产品运行完整的评论分析"""
        logger.info(f"开始评论分析: product_db_id={product_db_id}")

        # 情感分析
        sentiment = self.analyze_sentiment(product_db_id)

        # 痛点提取
        pain_points = self.extract_pain_points(product_db_id)

        # 维度分类
        dimensions = self.classify_pain_dimensions(pain_points)

        # 词频
        word_freq = self.get_word_frequency(product_db_id, top_n=20)

        # 词云
        wordcloud_path = ""
        try:
            wordcloud_path = self.generate_wordcloud(product_db_id)
        except Exception as e:
            logger.warning(f"词云生成失败: {e}")

        return {
            "product_db_id": product_db_id,
            "sentiment": sentiment,
            "pain_points": pain_points,
            "dimensions": dimensions,
            "word_frequency": word_freq,
            "wordcloud_path": wordcloud_path,
        }
