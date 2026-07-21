"""高中物理题库系统 - 组卷与答题评分"""

import json
import random
from datetime import datetime
from typing import Optional
from database import Database
from models import Question, TestRecord


class TestGenerator:
    """组卷与答题管理"""

    def __init__(self, db: Database):
        self.db = db

    def generate_by_criteria(self, grade_level: str = None,
                             topic_id: int = None,
                             qtype: str = None,
                             difficulty: str = None,
                             count: int = 10,
                             name: str = "自定义试卷") -> list[Question]:
        """根据条件生成试卷"""
        ids = self.db.get_question_ids(
            grade_level=grade_level,
            topic_id=topic_id,
            qtype=qtype,
            difficulty=difficulty
        )
        if len(ids) < count:
            print(f"⚠️  符合条件的题目只有 {len(ids)} 道，已全部选取")
            count = len(ids)

        if count == 0:
            print("❌ 没有符合条件的题目")
            return []

        selected = random.sample(ids, min(count, len(ids)))
        questions = [self.db.get_question(qid) for qid in selected]
        return [q for q in questions if q is not None]

    def generate_mixed(self, grade_level: str, total: int = 20,
                       easy_ratio: float = 0.3,
                       mid_ratio: float = 0.5,
                       hard_ratio: float = 0.2,
                       name: str = "综合试卷") -> list[Question]:
        """生成混合难度试卷"""
        easy_count = max(1, int(total * easy_ratio))
        mid_count = max(1, int(total * mid_ratio))
        hard_count = max(1, total - easy_count - mid_count)

        questions = []

        easy_qs = self.generate_by_criteria(
            grade_level=grade_level, difficulty="易", count=easy_count
        )
        mid_qs = self.generate_by_criteria(
            grade_level=grade_level, difficulty="中", count=mid_count
        )
        hard_qs = self.generate_by_criteria(
            grade_level=grade_level, difficulty="难", count=hard_count
        )

        all_qs = easy_qs + mid_qs + hard_qs
        random.shuffle(all_qs)
        return all_qs

    def generate_for_gaokao(self, count: int = 15, name: str = "高三模拟卷") -> list[Question]:
        """生成高三高考模拟卷（高三知识点为主，中等偏难）"""
        total = count
        # 高三内容占70%，高一高二占30%
        senior_count = int(total * 0.7)
        junior_count = total - senior_count

        senior_qs = self.generate_by_criteria(
            grade_level="高三", count=senior_count
        )
        junior_qs = self.generate_by_criteria(
            grade_level="高一高二", count=junior_count
        )

        # 获取不到足够高三题目时用高一高二补充
        if len(senior_qs) < senior_count:
            extra = self.generate_by_criteria(
                grade_level="高一高二", count=senior_count - len(senior_qs)
            )
            junior_qs.extend(extra)

        all_qs = senior_qs + junior_qs
        random.shuffle(all_qs)
        return all_qs

    def take_test(self, questions: list[Question], test_name: str = "测试"):
        """进行答题，返回答题记录"""
        if not questions:
            print("❌ 试卷为空")
            return None

        print(f"\n{'=' * 60}")
        print(f"  📝 {test_name} - 共 {len(questions)} 题")
        print(f"{'=' * 60}")

        answers = {}
        score = 0.0
        total = float(len(questions))

        for i, q in enumerate(questions, 1):
            print(f"\n{'─' * 60}")
            print(f"第 {i}/{len(questions)} 题 {q.brief_display()}")

            if q.is_choice():
                answer = self._answer_choice(q)
            else:
                answer = input("  请输入你的答案: ").strip()

            answers[str(q.id)] = answer

            # 选择题自动判分
            if q.is_choice():
                pts, full = self.check_choice_answer(answer, q.answer, q.is_multi())
                score += pts
                if full:
                    print("  ✅ 正确！")
                elif pts > 0:
                    print(f"  ⚠️  部分正确（+{pts}分）！正确答案是 {q.answer}")
                else:
                    print(f"  ❌ 错误！正确答案是 {q.answer}")
                    if q.explanation:
                        print(f"  💡 {q.explanation}")

        # 显示结果
        final_score = (score / total) * 100 if total > 0 else 0
        print(f"\n{'=' * 60}")
        print(f"  📊 答题完成！")
        print(f"  得分：{score:.0f}/{total:.0f} ({final_score:.1f}分)")
        print(f"{'=' * 60}")

        # 非选择题手动核对
        has_non_choice = any(q.qtype != "选择题" for q in questions)
        if has_non_choice:
            print("\n📝 以下为非选择题，请手动核对：")
            for i, q in enumerate(questions, 1):
                if q.qtype != "选择题":
                    user_ans = answers.get(str(q.id), "")
                    print(f"\n第{i}题: {q.content[:50]}...")
                    print(f"  你的答案: {user_ans}")
                    print(f"  参考答案: {q.answer}")
                    correct = input("  是否正确？(y/n/直接回车跳过): ").strip().lower()
                    if correct == 'y':
                        score += 1.0
                        answers[str(q.id)] = user_ans + " ✓"

            final_score = (score / total) * 100 if total > 0 else 0
            print(f"\n  修正后得分：{score:.0f}/{total:.0f} ({final_score:.1f}分)")

        # 保存记录
        questions_data = [
            {
                "id": q.id, "qtype": q.qtype, "difficulty": q.difficulty,
                "content": q.content[:100], "answer": q.answer,
                "topic_name": q.topic_name
            }
            for q in questions
        ]

        record = TestRecord(
            test_name=test_name,
            questions_json=json.dumps(questions_data, ensure_ascii=False),
            answers_json=json.dumps(answers, ensure_ascii=False),
            score=score,
            total=total,
            created_at=datetime.now().strftime("%Y-%m-%d %H:%M")
        )
        self.db.add_test_record(record)

        return record

    def _answer_choice(self, q: Question) -> str:
        """选择题作答（单选题或多选题）"""
        labels = ["A", "B", "C", "D", "E", "F"]
        valid = [l.lower() for l in labels[:len(q.options)]]
        if q.is_multi():
            hint = f"  请输入选项组合（如 AC）: "
            while True:
                ans = input(hint).strip().upper()
                if all(c.lower() in valid for c in ans) and len(ans) > 0:
                    return ans
                print(f"  请输入有效选项组合 ({'/'.join(labels[:len(q.options)])})")
        else:
            while True:
                ans = input("  请选择你的答案: ").strip().lower()
                if ans in valid:
                    return ans.upper()
                print(f"  请输入有效选项 ({'/'.join(l.upper() for l in valid)})")

    @staticmethod
    def check_choice_answer(user_answer: str, correct_answer: str,
                            is_multi: bool = False) -> tuple[float, bool]:
        """检查选择题答案，返回 (得分, 是否完全正确)"""
        user_set = set(user_answer.upper().strip())
        correct_set = set(correct_answer.upper().strip())
        if not is_multi:
            # 单选题：完全匹配
            return (1.0, True) if user_set == correct_set else (0.0, False)
        # 多选题
        if user_set == correct_set:
            return (1.0, True)   # 完全正确
        if user_set and user_set.issubset(correct_set):
            return (0.5, False)  # 选对但不全，得一半分
        return (0.0, False)      # 有选错

    def export_test(self, questions: list[Question], filepath: str,
                    include_answer: bool = False):
        """导出试卷到文本文件"""
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write("=" * 60 + "\n")
            f.write("  高中物理试卷\n")
            f.write("=" * 60 + "\n\n")

            for i, q in enumerate(questions, 1):
                f.write(f"第{i}题 【{q.qtype}】【{q.difficulty}】\n")
                f.write(f"{q.content}\n")
                if q.options:
                    labels = ["A", "B", "C", "D", "E", "F"]
                    for j, opt in enumerate(q.options):
                        f.write(f"  {labels[j]}. {opt}\n")
                f.write("\n")

            if include_answer:
                f.write("\n" + "=" * 60 + "\n")
                f.write("  参考答案\n")
                f.write("=" * 60 + "\n\n")
                for i, q in enumerate(questions, 1):
                    f.write(f"{i}. {q.answer}")
                    if q.explanation:
                        f.write(f"  ({q.explanation})")
                    f.write("\n")

        print(f"✅ 试卷已导出到: {filepath}")

    def export_to_docx(self, questions: list[Question], filepath: str,
                       test_name: str = "物理试卷",
                       include_answer: bool = False,
                       grade_level: str = "") -> str:
        """导出试卷为 Word 文档 (.docx)"""
        from docx_export import export_test_to_docx
        result = export_test_to_docx(
            questions=questions,
            filepath=filepath,
            test_name=test_name,
            include_answer=include_answer,
            grade_level=grade_level,
        )
        print(f"✅ Word 试卷已导出到: {filepath}")
        return result

    def export_to_docx_bytes(self, questions: list[Question],
                             test_name: str = "物理试卷",
                             include_answer: bool = False,
                             grade_level: str = "") -> bytes:
        """导出试卷为 Word 文档的字节数据"""
        from docx_export import export_test_to_docx_bytes
        return export_test_to_docx_bytes(
            questions=questions,
            test_name=test_name,
            include_answer=include_answer,
            grade_level=grade_level,
        )

    def print_test(self, questions: list[Question], include_answer: bool = False):
        """打印试卷到终端"""
        print("\n" + "=" * 60)
        print("  📄 试卷预览")
        print("=" * 60)

        for i, q in enumerate(questions, 1):
            print(f"\n第{i}题 {q.brief_display()}")

        if include_answer:
            print("\n" + "-" * 40)
            print("参考答案：")
            for i, q in enumerate(questions, 1):
                print(f"  {i}. {q.answer}  ", end="")
                if q.explanation:
                    print(f"({q.explanation})", end="")
                print()

    def view_history(self, limit: int = 10):
        """查看答题历史"""
        records = self.db.get_test_records(limit)
        if not records:
            print("\n暂无答题记录")
            return

        print("\n" + "=" * 60)
        print("  📋 答题记录")
        print("=" * 60)
        for r in records:
            pct = (r.score / r.total * 100) if r.total > 0 else 0
            print(f"  [{r.created_at}] {r.test_name}")
            print(f"    得分: {r.score:.0f}/{r.total:.0f} ({pct:.1f}分)")
            print()
