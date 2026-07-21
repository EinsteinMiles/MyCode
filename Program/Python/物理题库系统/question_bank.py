"""高中物理题库系统 - 题库管理"""

from database import Database, DB_PATH
from models import Question, Topic
from typing import Optional
import os


class QuestionBank:
    """题库管理类 - 提供浏览、搜索、增删改等功能"""

    def __init__(self, db: Database = None):
        self.db = db or Database()
        # 如果数据库是新建的，自动初始化种子数据
        if self.db.count_questions() == 0:
            self._auto_seed()

    def _auto_seed(self):
        """首次运行时自动导入预置题库"""
        from seed_data import seed_all
        seed_all(self.db)

    # ========== 浏览功能 ==========

    def browse_by_grade(self, grade_level: str) -> list[Question]:
        """按年级浏览题目"""
        return self.db.get_questions(grade_level=grade_level)

    def browse_by_topic(self, topic_id: int) -> list[Question]:
        """按知识点浏览题目"""
        return self.db.get_questions(topic_id=topic_id)

    def get_topic_tree(self, grade_level: Optional[str] = None) -> list[dict]:
        """获取知识点树结构"""
        parents = self.db.get_topics(grade_level=grade_level)
        tree = []
        for p in parents:
            node = {"topic": p, "children": self.db.get_subtopics(p.id)}
            tree.append(node)
        return tree

    def display_topic_tree(self, grade_level: Optional[str] = None):
        """显示知识点目录树"""
        tree = self.get_topic_tree(grade_level)
        for node in tree:
            p = node["topic"]
            count = self.db.count_questions(topic_id=p.id)
            # 同时统计子知识点下的题目
            for child in node["children"]:
                count += self.db.count_questions(topic_id=child.id)
            print(f"  📘 {p.name} ({count}题)")
            for child in node["children"]:
                child_count = self.db.count_questions(topic_id=child.id)
                print(f"      📄 {child.name} ({child_count}题)")

    # ========== 搜索功能 ==========

    def search(self, keyword: str = None, grade_level: str = None,
               qtype: str = None, difficulty: str = None,
               topic_id: int = None, topic_ids: list = None,
               limit: int = 50) -> list[Question]:
        """综合搜索"""
        return self.db.get_questions(
            grade_level=grade_level,
            topic_id=topic_id,
            topic_ids=topic_ids,
            qtype=qtype,
            difficulty=difficulty,
            keyword=keyword,
            limit=limit
        )

    # ========== 增删改 ==========

    def add_question_interactive(self):
        """交互式添加题目"""
        print("\n" + "=" * 60)
        print("  ✏️  添加新题目")
        print("=" * 60)

        # 选择年级
        print("\n选择年级：")
        print("  1. 高一高二")
        print("  2. 高三")
        grade_choice = input("请选择 (1/2): ").strip()
        grade_level = "高一高二" if grade_choice == "1" else "高三"

        # 显示知识点
        print(f"\n{grade_level} 知识点列表：")
        tree = self.get_topic_tree(grade_level)
        topic_map = {}
        idx = 1
        for node in tree:
            p = node["topic"]
            print(f"  {idx}. {p.name}")
            topic_map[str(idx)] = p.id
            idx += 1
            for child in node["children"]:
                print(f"     {idx}. {child.name}")
                topic_map[str(idx)] = child.id
                idx += 1

        topic_choice = input("\n请选择知识点编号: ").strip()
        topic_id = topic_map.get(topic_choice)
        if not topic_id:
            print("❌ 无效选择")
            return

        # 选择题型
        print("\n题型：1.单选题  2.多选题  3.实验题  4.计算题")
        qtype_map = {"1": "单选题", "2": "多选题", "3": "实验题", "4": "计算题"}
        qtype = qtype_map.get(input("请选择 (1/2/3/4): ").strip(), "单选题")

        # 选择难度
        print("\n难度：1.易  2.中  3.难")
        diff_map = {"1": "易", "2": "中", "3": "难"}
        difficulty = diff_map.get(input("请选择 (1/2/3): ").strip(), "中")

        # 输入题目内容
        print("\n请输入题目内容（输入完成后按回车，支持多行，输入 END 结束）：")
        lines = []
        while True:
            line = input()
            if line.strip() == "END":
                break
            lines.append(line)
        content = "\n".join(lines).strip()
        if not content:
            print("❌ 题目内容不能为空")
            return

        # 选择题需要输入选项
        options = []
        if qtype in ("单选题", "多选题"):
            print("\n请输入选项（每行一个，输入 END 结束）：")
            print("（格式示例：A. 5m/s  或直接输入选项文字）")
            while True:
                line = input()
                if line.strip() == "END":
                    break
                if line.strip():
                    # 去掉可能的前缀字母
                    opt = line.strip()
                    if len(opt) > 2 and opt[1] in ['.', '、', ' ']:
                        opt = opt[2:].strip()
                    options.append(opt)

        # 输入答案
        answer = input("\n请输入正确答案: ").strip()
        if not answer:
            print("❌ 答案不能为空")
            return

        # 输入解析
        explanation = input("请输入解析（可选，直接回车跳过）: ").strip()

        # 输入图片路径
        image_path = input("请输入配图文件名（可选，将图片放入 images/ 目录后输入文件名）: ").strip()

        # 保存
        q = Question(
            topic_id=topic_id,
            qtype=qtype,
            difficulty=difficulty,
            content=content,
            options=options,
            answer=answer,
            explanation=explanation,
            image_path=image_path,
        )
        qid = self.db.add_question(q)
        print(f"\n✅ 题目添加成功！ID: {qid}")

    def edit_question(self, question_id: int):
        """编辑题目"""
        q = self.db.get_question(question_id)
        if not q:
            print(f"❌ 未找到ID为 {question_id} 的题目")
            return

        print("\n当前题目：")
        print(q.full_display())

        print("\n修改题目（直接回车保留原值）：")
        new_content = input(f"题目内容 [{q.content[:30]}...]: ").strip()
        new_answer = input(f"答案 [{q.answer}]: ").strip()
        new_explanation = input(f"解析 [{q.explanation[:20] if q.explanation else '无'}...]: ").strip()
        new_diff = input(f"难度 [{q.difficulty}] (易/中/难): ").strip()

        if new_content:
            q.content = new_content
        if new_answer:
            q.answer = new_answer
        if new_explanation:
            q.explanation = new_explanation
        if new_diff and new_diff in ["易", "中", "难"]:
            q.difficulty = new_diff

        self.db.update_question(q)
        print(f"✅ 题目 {question_id} 已更新")

    def delete_question(self, question_id: int):
        """删除题目"""
        q = self.db.get_question(question_id)
        if not q:
            print(f"❌ 未找到ID为 {question_id} 的题目")
            return

        print("\n将要删除的题目：")
        print(f"  {q.content[:60]}...")
        confirm = input(f"\n确认删除题目 {question_id}？(y/n): ").strip().lower()
        if confirm == 'y':
            self.db.delete_question(question_id)
            print(f"✅ 题目 {question_id} 已删除")

    def view_question(self, question_id: int):
        """查看题目详情"""
        q = self.db.get_question(question_id)
        if not q:
            print(f"❌ 未找到ID为 {question_id} 的题目")
            return
        print("\n" + "=" * 60)
        print(q.full_display())
        print("=" * 60)

    # ========== 统计 ==========

    def stats(self) -> dict:
        """获取题库统计信息"""
        return {
            "total": self.db.count_questions(),
            "grade_10_11": self.db.count_questions(grade_level="高一高二"),
            "grade_12": self.db.count_questions(grade_level="高三"),
            "single": self.db.count_questions(qtype="单选题"),
            "multi": self.db.count_questions(qtype="多选题"),
            "choice": self.db.count_questions(qtype="单选题") + self.db.count_questions(qtype="多选题"),
            "experiment": self.db.count_questions(qtype="实验题"),
            "calc": self.db.count_questions(qtype="计算题"),
            "easy": self.db.count_questions(difficulty="易"),
            "mid": self.db.count_questions(difficulty="中"),
            "hard": self.db.count_questions(difficulty="难"),
        }

    def print_stats(self):
        """打印统计信息"""
        s = self.stats()
        print("\n" + "=" * 40)
        print("  📊 题库统计")
        print("=" * 40)
        print(f"  总题数：{s['total']}")
        print(f"  高一高二：{s['grade_10_11']}题  |  高三：{s['grade_12']}题")
        print(f"  单选题：{s['single']}  |  多选题：{s['multi']}  |  实验题：{s['experiment']}  |  计算题：{s['calc']}")
        print(f"  难度：易={s['easy']}  中={s['mid']}  难={s['hard']}")
        print("=" * 40)

    def close(self):
        self.db.close()
