#!/usr/bin/env python3
"""高中物理题库系统 - 主程序入口

一个面向高中生物理学习的题库管理软件，
分为高一高二（基础学习）和高三（高考复习）两个阶段。

功能：
  1. 题库浏览 - 按年级和知识点分类浏览
  2. 题目搜索 - 多条件筛选搜索
  3. 题目管理 - 添加、编辑、删除题目
  4. 组卷测试 - 自动生成试卷并在线答题
  5. 答题记录 - 查看历史成绩
  6. 题库统计 - 题库概况

纯Python标准库实现,无需额外安装依赖。
"""

import sys
import os
from question_bank import QuestionBank
from test_generator import TestGenerator
from database import Database


# ========== ANSI 颜色代码 ==========
class Color:
    """终端颜色"""
    RESET = "\033[0m"
    BOLD = "\033[1m"
    RED = "\033[91m"
    GREEN = "\033[92m"
    YELLOW = "\033[93m"
    BLUE = "\033[94m"
    MAGENTA = "\033[95m"
    CYAN = "\033[96m"
    WHITE = "\033[97m"

    @staticmethod
    def supports_color():
        """检查终端是否支持颜色"""
        if os.environ.get("NO_COLOR"):
            return False
        return hasattr(sys.stdout, "isatty") and sys.stdout.isatty()


# 如果不支持颜色，用空字符串替代
if not Color.supports_color():
    Color.RESET = Color.BOLD = Color.RED = Color.GREEN = Color.YELLOW = ""
    Color.BLUE = Color.MAGENTA = Color.CYAN = Color.WHITE = ""


def print_header():
    """打印程序标题"""
    print(f"""
{Color.CYAN}{Color.BOLD}
╔══════════════════════════════════════════════════╗
║           🎓 高中物理题库系统 v1.0              ║
║       高一高二 · 基础夯实  |  高三 · 冲刺高考     ║
╚══════════════════════════════════════════════════╝
{Color.RESET}""")


def print_menu():
    """打印主菜单"""
    print(f"""
{Color.YELLOW}{Color.BOLD}  📋 主菜单{Color.RESET}
{Color.CYAN}  ────────────────────────────────────{Color.RESET}
  {Color.GREEN}1.{Color.RESET} 📖 题库浏览  - 按年级/知识点浏览题目
  {Color.GREEN}2.{Color.RESET} 🔍 题目搜索  - 多条件筛选搜索
  {Color.GREEN}3.{Color.RESET} ✏️  题目管理  - 添加/编辑/删除题目
  {Color.GREEN}4.{Color.RESET} 📝 组卷测试  - 生成试卷并答题
  {Color.GREEN}5.{Color.RESET} 📋 答题记录  - 查看历史成绩
  {Color.GREEN}6.{Color.RESET} 📊 题库统计  - 题库概况
  {Color.GREEN}7.{Color.RESET} 📄 导出试卷  - 生成可打印试卷文件
{Color.CYAN}  ────────────────────────────────────{Color.RESET}
  {Color.RED}0.{Color.RESET} 🚪 退出程序
""")


def browse_questions(bank: QuestionBank):
    """题库浏览子菜单"""
    while True:
        print(f"\n{Color.YELLOW}{Color.BOLD}  📖 题库浏览{Color.RESET}")
        print(f"  {Color.GREEN}1.{Color.RESET} 高一高二（知识点目录）")
        print(f"  {Color.GREEN}2.{Color.RESET} 高三（知识点目录）")
        print(f"  {Color.GREEN}3.{Color.RESET} 全部知识点")
        print(f"  {Color.RED}0.{Color.RESET} 返回主菜单")

        choice = input(f"\n  请选择: ").strip()

        if choice == "1":
            _browse_grade(bank, "高一高二")
        elif choice == "2":
            _browse_grade(bank, "高三")
        elif choice == "3":
            print(f"\n{Color.BOLD}  📘 高一高二：{Color.RESET}")
            bank.display_topic_tree("高一高二")
            print(f"\n{Color.BOLD}  📘 高三：{Color.RESET}")
            bank.display_topic_tree("高三")
            input(f"\n  按回车继续...")
        elif choice == "0":
            break


def _browse_grade(bank: QuestionBank, grade_level: str):
    """浏览某个年级的题目"""
    print(f"\n{Color.BOLD}  📘 {grade_level} 知识点目录：{Color.RESET}")
    bank.display_topic_tree(grade_level)

    # 收集所有 topic id
    tree = bank.get_topic_tree(grade_level)
    topic_map = {}
    idx = 1
    for node in tree:
        p = node["topic"]
        topic_map[str(idx)] = p.id
        idx += 1
        for child in node["children"]:
            topic_map[str(idx)] = child.id
            idx += 1

    choice = input(f"\n  选择知识点编号查看题目 (0=返回): ").strip()
    if choice == "0" or choice not in topic_map:
        return

    # 题型筛选
    print(f"\n  筛选题型（直接回车显示全部）：")
    print(f"  {Color.GREEN}1.{Color.RESET} 选择题  {Color.GREEN}2.{Color.RESET} 实验题  {Color.GREEN}3.{Color.RESET} 计算题  {Color.GREEN}4.{Color.RESET} 全部")
    type_choice = input("  请选择: ").strip()
    type_map = {"1": "选择题", "2": "实验题", "3": "计算题"}
    qtype = type_map.get(type_choice)

    questions = bank.search(topic_id=topic_map[choice], qtype=qtype)
    _display_question_list(bank, questions)


def _display_question_list(bank: QuestionBank, questions: list):
    """显示题目列表，支持查看详情"""
    if not questions:
        print(f"\n  {Color.YELLOW}暂无题目{Color.RESET}")
        input(f"\n  按回车返回...")
        return

    page_size = 10
    page = 0
    total_pages = (len(questions) - 1) // page_size + 1

    while True:
        start = page * page_size
        end = min(start + page_size, len(questions))
        page_questions = questions[start:end]

        print(f"\n{Color.BOLD}  共 {len(questions)} 道题目 (第{page+1}/{total_pages}页){Color.RESET}")
        print(f"  {Color.CYAN}{'─'*50}{Color.RESET}")

        for i, q in enumerate(page_questions, 1):
            global_idx = start + i
            print(f"{Color.GREEN}  [{global_idx}]{Color.RESET} {Color.BOLD}【{q.qtype}】【{q.difficulty}】{Color.RESET}")
            print(f"      {q.content[:60]}{'...' if len(q.content) > 60 else ''}")
            if q.topic_name:
                print(f"      {Color.BLUE}▸ {q.topic_name}{Color.RESET}")

        print(f"\n  {Color.GREEN}n{Color.RESET}=下一页  {Color.GREEN}p{Color.RESET}=上一页  {Color.GREEN}[编号]{Color.RESET}=查看详情  {Color.RED}0{Color.RESET}=返回")
        choice = input("  > ").strip().lower()

        if choice == "0":
            break
        elif choice == "n" and page < total_pages - 1:
            page += 1
        elif choice == "p" and page > 0:
            page -= 1
        elif choice.isdigit():
            idx = int(choice)
            if 1 <= idx <= len(questions):
                bank.view_question(questions[idx - 1].id)
                input(f"\n  按回车继续...")
            else:
                print(f"  {Color.RED}无效编号{Color.RESET}")


def search_questions(bank: QuestionBank):
    """题目搜索子菜单"""
    print(f"\n{Color.YELLOW}{Color.BOLD}  🔍 题目搜索{Color.RESET}")
    print(f"  （直接回车表示不限条件）")

    # 年级
    print(f"\n  年级：1=高一高二  2=高三  回车=不限")
    grade_choice = input("  > ").strip()
    grade_map = {"1": "高一高二", "2": "高三"}
    grade_level = grade_map.get(grade_choice)

    # 题型
    print(f"  题型：1=选择题  2=实验题  3=计算题  回车=不限")
    type_choice = input("  > ").strip()
    type_map = {"1": "选择题", "2": "实验题", "3": "计算题"}
    qtype = type_map.get(type_choice)

    # 难度
    print(f"  难度：1=易  2=中  3=难  回车=不限")
    diff_choice = input("  > ").strip()
    diff_map = {"1": "易", "2": "中", "3": "难"}
    difficulty = diff_map.get(diff_choice)

    # 关键词
    keyword = input(f"  关键词搜索: ").strip() or None

    questions = bank.search(
        grade_level=grade_level,
        qtype=qtype,
        difficulty=difficulty,
        keyword=keyword
    )
    _display_question_list(bank, questions)


def manage_questions(bank: QuestionBank):
    """题目管理子菜单"""
    while True:
        print(f"\n{Color.YELLOW}{Color.BOLD}  ✏️  题目管理{Color.RESET}")
        print(f"  {Color.GREEN}1.{Color.RESET} 添加新题目")
        print(f"  {Color.GREEN}2.{Color.RESET} 编辑题目")
        print(f"  {Color.GREEN}3.{Color.RESET} 删除题目")
        print(f"  {Color.GREEN}4.{Color.RESET} 查看题目详情")
        print(f"  {Color.RED}0.{Color.RESET} 返回主菜单")

        choice = input(f"\n  请选择: ").strip()

        if choice == "1":
            bank.add_question_interactive()
            input(f"\n  按回车继续...")
        elif choice == "2":
            qid = input("  请输入要编辑的题目ID: ").strip()
            if qid.isdigit():
                bank.edit_question(int(qid))
            input(f"\n  按回车继续...")
        elif choice == "3":
            qid = input("  请输入要删除的题目ID: ").strip()
            if qid.isdigit():
                bank.delete_question(int(qid))
            input(f"\n  按回车继续...")
        elif choice == "4":
            qid = input("  请输入题目ID: ").strip()
            if qid.isdigit():
                bank.view_question(int(qid))
            input(f"\n  按回车继续...")
        elif choice == "0":
            break


def test_mode(bank: QuestionBank, db: Database):
    """组卷与测试子菜单"""
    gen = TestGenerator(db)

    while True:
        print(f"\n{Color.YELLOW}{Color.BOLD}  📝 组卷测试{Color.RESET}")
        print(f"  {Color.GREEN}1.{Color.RESET} 自定义组卷（按条件筛选）")
        print(f"  {Color.GREEN}2.{Color.RESET} 高一高二综合卷")
        print(f"  {Color.GREEN}3.{Color.RESET} 高三高考模拟卷")
        print(f"  {Color.GREEN}4.{Color.RESET} 开始答题...")
        print(f"  {Color.RED}0.{Color.RESET} 返回主菜单")

        choice = input(f"\n  请选择: ").strip()
        current_test = None

        if choice == "1":
            current_test = _custom_generate(bank, gen)
        elif choice == "2":
            count = input("  题目数量 (默认15): ").strip()
            count = int(count) if count.isdigit() else 15
            current_test = gen.generate_mixed(
                grade_level="高一高二", total=count, name="高一高二综合卷"
            )
            if current_test:
                gen.print_test(current_test)
        elif choice == "3":
            count = input("  题目数量 (默认15): ").strip()
            count = int(count) if count.isdigit() else 15
            current_test = gen.generate_for_gaokao(count=count, name="高三模拟卷")
            if current_test:
                gen.print_test(current_test)
        elif choice == "4":
            # 先组卷
            print(f"\n  先来组一份试卷吧！")
            current_test = _custom_generate(bank, gen)
            if current_test:
                gen.take_test(current_test, test_name="答题测试")
            input(f"\n  按回车继续...")
        elif choice == "0":
            break

        if current_test and choice != "4":
            action = input(f"\n  {Color.GREEN}a{Color.RESET}=开始答题  {Color.GREEN}e{Color.RESET}=导出试卷  {Color.RED}回车{Color.RESET}=返回: ").strip().lower()
            if action == "a":
                gen.take_test(current_test, test_name="答题测试")
                input(f"\n  按回车继续...")
            elif action == "e":
                filepath = input("  导出路径 (如 test.txt): ").strip()
                if filepath:
                    include_ans = input("  是否包含答案？(y/n): ").strip().lower() == "y"
                    gen.export_test(current_test, filepath, include_answer=include_ans)
                input(f"\n  按回车继续...")


def _custom_generate(bank: QuestionBank, gen: TestGenerator) -> list:
    """自定义组卷流程"""
    print(f"\n  {Color.BOLD}自定义组卷{Color.RESET}")

    grade_choice = input("  年级 (1=高一高二 2=高三 回车=不限): ").strip()
    grade_map = {"1": "高一高二", "2": "高三"}
    grade_level = grade_map.get(grade_choice)

    # 知识点选择
    if grade_level:
        print(f"\n  {grade_level} 知识点：")
        bank.display_topic_tree(grade_level)
    topic_choice = input("  知识点编号 (回车=不限): ").strip()
    topic_id = None
    if topic_choice.isdigit() and grade_level:
        tree = bank.get_topic_tree(grade_level)
        topic_map = {}
        idx = 1
        for node in tree:
            p = node["topic"]
            topic_map[str(idx)] = p.id
            idx += 1
            for child in node["children"]:
                topic_map[str(idx)] = child.id
                idx += 1
        topic_id = topic_map.get(topic_choice)

    qtype = input("  题型 (1=选择题 2=实验题 3=计算题 回车=不限): ").strip()
    qtype_map = {"1": "选择题", "2": "实验题", "3": "计算题"}
    qtype = qtype_map.get(qtype)

    diff = input("  难度 (1=易 2=中 3=难 回车=不限): ").strip()
    diff_map = {"1": "易", "2": "中", "3": "难"}
    difficulty = diff_map.get(diff)

    count = input("  题目数量 (默认10): ").strip()
    count = int(count) if count.isdigit() else 10

    name = input("  试卷名称 (回车使用默认): ").strip() or "自定义试卷"

    questions = gen.generate_by_criteria(
        grade_level=grade_level,
        topic_id=topic_id,
        qtype=qtype,
        difficulty=difficulty,
        count=count,
        name=name
    )

    if questions:
        gen.print_test(questions)
    return questions


def view_history(db: Database):
    """查看答题历史"""
    gen = TestGenerator(db)
    gen.view_history(limit=20)
    input(f"\n  按回车返回...")


def export_paper(bank: QuestionBank, db: Database):
    """导出试卷到文件"""
    gen = TestGenerator(db)
    print(f"\n{Color.YELLOW}{Color.BOLD}  📄 导出试卷{Color.RESET}")

    grade_choice = input("  年级 (1=高一高二 2=高三 3=不限): ").strip()
    grade_map = {"1": "高一高二", "2": "高三"}
    grade_level = grade_map.get(grade_choice)

    count = input("  题目数量 (默认20): ").strip()
    count = int(count) if count.isdigit() else 20

    name = input("  试卷名称: ").strip() or "物理试卷"

    if grade_level:
        questions = gen.generate_mixed(grade_level=grade_level, total=count, name=name)
    else:
        ids = db.get_question_ids()
        import random
        selected = random.sample(ids, min(count, len(ids)))
        questions = [db.get_question(qid) for qid in selected]
        questions = [q for q in questions if q is not None]

    if questions:
        filepath = input(f"  保存路径 (如 ./{name}.txt): ").strip()
        if not filepath:
            filepath = f"./{name}.txt"
        include_ans = input("  是否包含答案？(y/n): ").strip().lower() == "y"
        gen.export_test(questions, filepath, include_answer=include_ans)


def main():
    """主程序入口"""
    # 初始化数据库和题库
    db = Database()
    bank = QuestionBank(db)

    while True:
        print_header()
        bank.print_stats()
        print_menu()

        choice = input(f"  {Color.BOLD}请选择操作 (0-7):{Color.RESET} ").strip()

        if choice == "1":
            browse_questions(bank)
        elif choice == "2":
            search_questions(bank)
        elif choice == "3":
            manage_questions(bank)
        elif choice == "4":
            test_mode(bank, db)
        elif choice == "5":
            view_history(db)
        elif choice == "6":
            bank.print_stats()
            input(f"\n  按回车返回...")
        elif choice == "7":
            export_paper(bank, db)
            input(f"\n  按回车返回...")
        elif choice == "0":
            print(f"\n{Color.CYAN}  再见！祝你学业进步！🎓{Color.RESET}\n")
            bank.close()
            break
        else:
            print(f"  {Color.RED}无效选择，请重试{Color.RESET}")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print(f"\n\n{Color.CYAN}  已退出。再见！{Color.RESET}\n")
    except Exception as e:
        print(f"\n{Color.RED}  程序出错: {e}{Color.RESET}\n")
        raise
