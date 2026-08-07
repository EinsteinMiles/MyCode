"""
评论分析器 — 跨境电商版
English NLP pipeline: NLTK tokenization → VADER sentiment → TF-IDF pain points + word cloud
"""

import os
import re
from typing import List, Dict, Tuple, Any
from collections import Counter

from config import (
    SENTIMENT_POSITIVE, SENTIMENT_NEGATIVE,
    MAX_REVIEW_PAGES, CHART_DIR, logger,
)
from core.models import Review
from core.storage import Database
from core.utils import clean_text


# ── English e-commerce stop words ────────────────────
ECOMMERCE_STOP_WORDS = set([
    "the", "a", "an", "is", "are", "was", "were", "be", "been", "being",
    "have", "has", "had", "do", "does", "did", "will", "would", "could",
    "should", "may", "might", "can", "shall", "must", "i", "me", "my",
    "we", "our", "you", "your", "he", "she", "it", "they", "them",
    "this", "that", "these", "those", "am", "at", "by", "for", "with",
    "about", "between", "through", "during", "before", "after", "above",
    "below", "to", "from", "in", "out", "on", "off", "over", "under",
    "again", "further", "then", "once", "here", "there", "all", "both",
    "each", "few", "more", "most", "other", "some", "such", "no", "nor",
    "not", "only", "own", "same", "so", "than", "too", "very", "just",
    "because", "but", "and", "or", "if", "while", "also", "up", "down",
    "product", "item", "buy", "bought", "purchased", "order", "ordered",
    "received", "seller", "shipping", "delivery", "arrived", "package",
    "good", "great", "nice", "ok", "okay", "well", "really", "pretty",
    "quite", "much", "lot", "bit", "little", "one", "two", "get", "got",
    "even", "still", "though", "although", "however", "yet", "ever",
    "never", "always", "sometimes", "usually", "around", "every",
    "say", "said", "think", "thought", "know", "thing", "things",
    "dont", "didnt", "wasnt", "werent", "isnt", "arent", "couldnt",
    "wouldnt", "shouldnt", "cant", "wont", "im", "ive", "youre",
    "theyre", "its", "thats",
])

# ── Pain point dimension keywords ────────────────────
PAIN_POINT_DIMENSIONS = {
    "Quality & Build": [
        "quality", "cheap", "broke", "broken", "defective", "damaged",
        "flimsy", "poor quality", "falls apart", "stopped working",
        "malfunction", "defect", "cracked", "scratch", "scratched",
        "faulty", "doesn't work", "didn't work", "not working",
    ],
    "Shipping & Delivery": [
        "shipping", "delivery", "late", "delay", "delayed", "never arrived",
        "lost", "tracking", "slow shipping", "took forever", "weeks",
        "month", "waiting", "still waiting", "arrived late", "long shipping",
    ],
    "Customer Service": [
        "customer service", "support", "rude", "unhelpful", "no response",
        "no reply", "ignored", "refund", "return", "won't respond",
        "terrible service", "communication", "never responded",
    ],
    "Price & Value": [
        "expensive", "overpriced", "not worth", "waste of money",
        "cheaper elsewhere", "price", "rip off", "ripoff", "over charge",
        "too much", "paid", "cost",
    ],
    "Description Accuracy": [
        "not as described", "different", "misleading", "picture",
        "photo", "smaller", "bigger", "color", "size", "wrong",
        "fake", "counterfeit", "not genuine", "not authentic",
        "looks different", "not what", "expected",
    ],
    "Return & Refund": [
        "return", "refund", "money back", "return policy",
        "won't refund", "no refund", "return shipping",
        "restocking fee", "hassle", "difficult",
    ],
}


class ReviewAnalyzer:
    """English NLP评论分析器"""

    def __init__(self, db: Database):
        self.db = db
        self._nltk_ready = False

    def _ensure_nltk(self):
        """延迟加载 NLTK + VADER"""
        if self._nltk_ready:
            return
        try:
            import nltk
            from nltk.sentiment import SentimentIntensityAnalyzer
            nltk.download('vader_lexicon', quiet=True)
            nltk.download('punkt', quiet=True)
            nltk.download('stopwords', quiet=True)
            self._nltk_ready = True
        except ImportError:
            raise ImportError("请安装 nltk: pip install nltk")

    # ── 情感分析 ──────────────────────────────────────

    def analyze_sentiment(self, product_db_id: int) -> Dict[str, Any]:
        """使用 VADER 进行批量情感分析"""
        reviews = self.db.get_reviews(product_db_id, limit=500)
        if not reviews:
            logger.warning("没有评论数据可供分析")
            return {"total": 0, "positive": 0, "neutral": 0, "negative": 0, "avg_sentiment": 0}

        self._ensure_nltk()
        from nltk.sentiment import SentimentIntensityAnalyzer
        sia = SentimentIntensityAnalyzer()

        positive = neutral = negative = 0
        total_score = 0.0

        for review in reviews:
            if not review.content or len(review.content.strip()) < 3:
                continue

            try:
                scores = sia.polarity_scores(review.content)
                compound = scores["compound"]  # -1 ~ +1
            except Exception:
                # Fallback to rating-based
                compound = (review.rating / 5.0) * 2 - 1 if review.rating > 0 else 0

            review.sentiment_score = round(compound, 3)

            if compound >= SENTIMENT_POSITIVE:
                review.sentiment_label = "positive"
                positive += 1
            elif compound <= SENTIMENT_NEGATIVE:
                review.sentiment_label = "negative"
                negative += 1
            else:
                review.sentiment_label = "neutral"
                neutral += 1

            total_score += compound

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

    # ── 痛点提取 ──────────────────────────────────────

    def extract_pain_points(
        self, product_db_id: int, top_n: int = 20
    ) -> List[Tuple[str, int, float]]:
        """提取痛点关键词（使用 TF-IDF 或词频加权）"""
        negative_reviews = self.db.get_reviews(
            product_db_id, sentiment_label="negative", limit=200
        )
        if not negative_reviews:
            negative_reviews = self.db.get_reviews(product_db_id, limit=200)

        all_text = " ".join(r.content for r in negative_reviews if r.content)
        if not all_text:
            return []

        # Tokenize and filter
        try:
            self._ensure_nltk()
            import nltk
            from nltk.corpus import stopwords
            nltk_stop = set(stopwords.words('english'))
        except Exception:
            nltk_stop = set()

        stop_words = ECOMMERCE_STOP_WORDS | nltk_stop

        # Simple tokenization (case-insensitive)
        words = re.findall(r'[a-zA-Z]+', all_text.lower())
        filtered = [w for w in words if len(w) >= 3 and w not in stop_words]

        word_counts = Counter(filtered)

        # 计算每个词在差评中的平均 VADER 情感分
        results = []
        for word, freq in word_counts.most_common(top_n * 3):
            related = [
                r for r in negative_reviews
                if r.content and word in r.content.lower()
            ]
            avg_sent = (
                sum(r.sentiment_score for r in related) / len(related)
                if related else -0.3
            )
            results.append((word, freq, round(avg_sent, 2)))

        results.sort(key=lambda x: x[1], reverse=True)
        return results[:top_n]

    # ── 痛点维度分类 ──────────────────────────────────

    def classify_pain_dimensions(
        self, pain_points: List[Tuple[str, int, float]]
    ) -> Dict[str, int]:
        """将痛点关键词映射到维度"""
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
        reviews = self.db.get_reviews(product_db_id, limit=500)
        all_words = []

        for review in reviews:
            if not review.content:
                continue
            words = re.findall(r'[a-zA-Z]+', review.content.lower())
            all_words.extend(
                w for w in words
                if len(w) >= 3 and w not in ECOMMERCE_STOP_WORDS
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
            logger.warning("wordcloud not installed: pip install wordcloud")
            return ""

        reviews = self.db.get_reviews(product_db_id, limit=500)
        text = " ".join(r.content for r in reviews if r.content)
        if not text:
            return ""

        wc = WordCloud(
            width=800, height=500,
            background_color="white",
            max_words=200,
            collocations=False,
            stopwords=ECOMMERCE_STOP_WORDS,
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

        sentiment = self.analyze_sentiment(product_db_id)
        pain_points = self.extract_pain_points(product_db_id)
        dimensions = self.classify_pain_dimensions(pain_points)
        word_freq = self.get_word_frequency(product_db_id, top_n=20)

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
