"""高中物理题库系统 - 数据模型"""

from dataclasses import dataclass, field
from typing import Optional
import json


@dataclass
class Topic:
    """知识点"""
    id: Optional[int] = None
    name: str = ""
    grade_level: str = ""          # "高一高二" 或 "高三"
    parent_id: Optional[int] = None  # 父知识点ID，支持二级分类

    def __str__(self):
        return self.name


@dataclass
class Question:
    """题目"""
    id: Optional[int] = None
    topic_id: int = 0
    topic_name: str = ""           # 关联查询时填充
    grade_level: str = ""          # 关联查询时填充（高一高二/高三）
    qtype: str = "单选题"           # 单选题 / 多选题 / 实验题 / 计算题
    difficulty: str = "中"          # 易 / 中 / 难
    content: str = ""              # 题目内容
    options: list = field(default_factory=list)  # 选择题选项
    answer: str = ""               # 正确答案
    explanation: str = ""          # 解析
    image_path: str = ""           # 配图路径（相对于 images/ 目录）
    created_at: str = ""

    def options_text(self) -> str:
        """格式化显示选项"""
        if not self.options:
            return ""
        labels = ["A", "B", "C", "D", "E", "F"]
        lines = []
        for i, opt in enumerate(self.options):
            lines.append(f"  {labels[i]}. {opt}")
        return "\n".join(lines)

    def full_display(self) -> str:
        """完整显示题目（含答案和解析）"""
        parts = [f"【{self.qtype}】【难度：{self.difficulty}】"]
        if self.topic_name:
            parts[0] += f" 【{self.topic_name}】"
        parts.append(self.content)
        if self.image_path:
            parts.append(f"🖼️  配图：{self.image_path}")
        if self.options:
            parts.append(self.options_text())
        parts.append(f"\n✅ 答案：{self.answer}")
        if self.explanation:
            parts.append(f"📖 解析：{self.explanation}")
        return "\n".join(parts)

    def is_choice(self) -> bool:
        """是否选择题类型（单选或多选）"""
        return self.qtype in ("单选题", "多选题", "选择题")

    def is_multi(self) -> bool:
        """是否为多选题"""
        return self.qtype == "多选题"

    def brief_display(self, index: int = 0) -> str:
        """简要显示题目（不含答案）"""
        prefix = f"[{index}] " if index > 0 else ""
        lines = [f"{prefix}【{self.qtype}】【{self.difficulty}】{self.content}"]
        if self.image_path:
            lines.append(f"  🖼️  配图：{self.image_path}")
        if self.options:
            lines.append(self.options_text())
        return "\n".join(lines)


@dataclass
class TestRecord:
    """答题记录"""
    id: Optional[int] = None
    test_name: str = ""
    questions_json: str = "[]"
    answers_json: str = "{}"
    score: float = 0.0
    total: float = 0.0
    created_at: str = ""

    def get_questions(self) -> list:
        return json.loads(self.questions_json) if self.questions_json else []

    def get_answers(self) -> dict:
        return json.loads(self.answers_json) if self.answers_json else {}
