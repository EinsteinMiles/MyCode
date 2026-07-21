"""高中物理题库系统 - 数据库层"""

import sqlite3
import os
import json
from datetime import datetime
from typing import Optional
from models import Question, Topic, TestRecord

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "physics_bank.db")


class Database:
    """数据库管理类"""

    def __init__(self, db_path: str = DB_PATH):
        self.db_path = db_path
        self.conn = sqlite3.connect(db_path)
        self.conn.row_factory = sqlite3.Row
        self._init_tables()

    def _init_tables(self):
        """建表"""
        self.conn.executescript("""
            CREATE TABLE IF NOT EXISTS topics (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                grade_level TEXT NOT NULL,
                parent_id INTEGER,
                FOREIGN KEY (parent_id) REFERENCES topics(id)
            );

            CREATE TABLE IF NOT EXISTS questions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                topic_id INTEGER NOT NULL,
                qtype TEXT NOT NULL DEFAULT '选择题',
                difficulty TEXT NOT NULL DEFAULT '中',
                content TEXT NOT NULL,
                options TEXT DEFAULT '[]',
                answer TEXT NOT NULL DEFAULT '',
                explanation TEXT DEFAULT '',
                image_path TEXT DEFAULT '',
                created_at TEXT NOT NULL,
                FOREIGN KEY (topic_id) REFERENCES topics(id)
            );

            CREATE TABLE IF NOT EXISTS test_records (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                test_name TEXT NOT NULL,
                questions_json TEXT DEFAULT '[]',
                answers_json TEXT DEFAULT '{}',
                score REAL DEFAULT 0.0,
                total REAL DEFAULT 0.0,
                created_at TEXT NOT NULL
            );
        """)
        # 兼容旧数据库：如果缺少 image_path 列则自动添加
        try:
            self.conn.execute("SELECT image_path FROM questions LIMIT 0")
        except sqlite3.OperationalError:
            self.conn.execute("ALTER TABLE questions ADD COLUMN image_path TEXT DEFAULT ''")
        # 迁移：将旧的"选择题"→"单选题"，"填空题"→"实验题"
        self.conn.execute(
            "UPDATE questions SET qtype = '单选题' WHERE qtype = '选择题'"
        )
        self.conn.execute(
            "UPDATE questions SET qtype = '实验题' WHERE qtype = '填空题'"
        )
        self.conn.commit()

    # ========== 知识点操作 ==========

    def add_topic(self, name: str, grade_level: str, parent_id: Optional[int] = None) -> int:
        """添加知识点，返回ID"""
        cur = self.conn.execute(
            "INSERT INTO topics (name, grade_level, parent_id) VALUES (?, ?, ?)",
            (name, grade_level, parent_id)
        )
        self.conn.commit()
        return cur.lastrowid

    def get_topics(self, grade_level: Optional[str] = None, parent_id: Optional[int] = None) -> list[Topic]:
        """获取知识点列表"""
        sql = "SELECT * FROM topics WHERE 1=1"
        params = []
        if grade_level:
            sql += " AND grade_level = ?"
            params.append(grade_level)
        if parent_id is not None:
            sql += " AND parent_id = ?"
            params.append(parent_id)
        else:
            sql += " AND parent_id IS NULL"
        sql += " ORDER BY id"
        rows = self.conn.execute(sql, params).fetchall()
        return [Topic(**dict(r)) for r in rows]

    def get_subtopics(self, parent_id: int) -> list[Topic]:
        """获取子知识点"""
        return self.get_topics(parent_id=parent_id)

    def get_topic_by_id(self, topic_id: int) -> Optional[Topic]:
        row = self.conn.execute("SELECT * FROM topics WHERE id = ?", (topic_id,)).fetchone()
        return Topic(**dict(row)) if row else None

    def get_all_topics(self) -> list[Topic]:
        """获取所有知识点"""
        rows = self.conn.execute("SELECT * FROM topics ORDER BY id").fetchall()
        return [Topic(**dict(r)) for r in rows]

    # ========== 题目操作 ==========

    def add_question(self, q: Question) -> int:
        """添加题目，返回ID"""
        cur = self.conn.execute(
            """INSERT INTO questions (topic_id, qtype, difficulty, content, options, answer, explanation, image_path, created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (q.topic_id, q.qtype, q.difficulty, q.content,
             json.dumps(q.options, ensure_ascii=False),
             q.answer, q.explanation, q.image_path,
             q.created_at or datetime.now().strftime("%Y-%m-%d %H:%M"))
        )
        self.conn.commit()
        return cur.lastrowid

    def update_question(self, q: Question):
        """更新题目"""
        self.conn.execute(
            """UPDATE questions SET topic_id=?, qtype=?, difficulty=?, content=?,
               options=?, answer=?, explanation=?, image_path=? WHERE id=?""",
            (q.topic_id, q.qtype, q.difficulty, q.content,
             json.dumps(q.options, ensure_ascii=False),
             q.answer, q.explanation, q.image_path, q.id)
        )
        self.conn.commit()

    def delete_question(self, question_id: int):
        self.conn.execute("DELETE FROM questions WHERE id = ?", (question_id,))
        self.conn.commit()

    def get_question(self, question_id: int) -> Optional[Question]:
        row = self.conn.execute(
            """SELECT q.*, t.name as topic_name, t.grade_level
               FROM questions q LEFT JOIN topics t ON q.topic_id = t.id
               WHERE q.id = ?""", (question_id,)
        ).fetchone()
        if not row:
            return None
        d = dict(row)
        d['options'] = json.loads(d.get('options', '[]'))
        return Question(**d)

    def get_questions(self, grade_level: Optional[str] = None,
                      topic_id: Optional[int] = None,
                      topic_ids: Optional[list[int]] = None,
                      qtype: Optional[str] = None,
                      difficulty: Optional[str] = None,
                      keyword: Optional[str] = None,
                      limit: int = 100,
                      offset: int = 0) -> list[Question]:
        """多条件查询题目"""
        sql = """SELECT q.*, t.name as topic_name, t.grade_level
                 FROM questions q LEFT JOIN topics t ON q.topic_id = t.id
                 WHERE 1=1"""
        params = []

        if grade_level:
            sql += " AND t.grade_level = ?"
            params.append(grade_level)
        if topic_ids:
            placeholders = ",".join("?" * len(topic_ids))
            sql += f" AND q.topic_id IN ({placeholders})"
            params.extend(topic_ids)
        elif topic_id:
            sql += " AND q.topic_id = ?"
            params.append(topic_id)
        if qtype:
            sql += " AND q.qtype = ?"
            params.append(qtype)
        if difficulty:
            sql += " AND q.difficulty = ?"
            params.append(difficulty)
        if keyword:
            sql += " AND q.content LIKE ?"
            params.append(f"%{keyword}%")

        sql += " ORDER BY q.id DESC LIMIT ? OFFSET ?"
        params.extend([limit, offset])

        rows = self.conn.execute(sql, params).fetchall()
        result = []
        for r in rows:
            d = dict(r)
            d['options'] = json.loads(d.get('options', '[]'))
            result.append(Question(**d))
        return result

    def count_questions(self, grade_level: Optional[str] = None,
                        topic_id: Optional[int] = None,
                        topic_ids: Optional[list[int]] = None,
                        qtype: Optional[str] = None,
                        difficulty: Optional[str] = None,
                        keyword: Optional[str] = None) -> int:
        """统计题目数量"""
        sql = """SELECT COUNT(*) FROM questions q
                 LEFT JOIN topics t ON q.topic_id = t.id WHERE 1=1"""
        params = []
        if grade_level:
            sql += " AND t.grade_level = ?"
            params.append(grade_level)
        if topic_ids:
            placeholders = ",".join("?" * len(topic_ids))
            sql += f" AND q.topic_id IN ({placeholders})"
            params.extend(topic_ids)
        elif topic_id:
            sql += " AND q.topic_id = ?"
            params.append(topic_id)
        if qtype:
            sql += " AND q.qtype = ?"
            params.append(qtype)
        if difficulty:
            sql += " AND q.difficulty = ?"
            params.append(difficulty)
        if keyword:
            sql += " AND q.content LIKE ?"
            params.append(f"%{keyword}%")
        return self.conn.execute(sql, params).fetchone()[0]

    def get_question_ids(self, grade_level: Optional[str] = None,
                         topic_id: Optional[int] = None,
                         topic_ids: Optional[list[int]] = None,
                         qtype: Optional[str] = None,
                         difficulty: Optional[str] = None) -> list[int]:
        """获取符合条件的题目ID列表（用于随机组卷）"""
        sql = """SELECT q.id FROM questions q
                 LEFT JOIN topics t ON q.topic_id = t.id WHERE 1=1"""
        params = []
        if grade_level:
            sql += " AND t.grade_level = ?"
            params.append(grade_level)
        if topic_ids:
            placeholders = ",".join("?" * len(topic_ids))
            sql += f" AND q.topic_id IN ({placeholders})"
            params.extend(topic_ids)
        elif topic_id:
            sql += " AND q.topic_id = ?"
            params.append(topic_id)
        if qtype:
            sql += " AND q.qtype = ?"
            params.append(qtype)
        if difficulty:
            sql += " AND q.difficulty = ?"
            params.append(difficulty)
        rows = self.conn.execute(sql, params).fetchall()
        return [r[0] for r in rows]

    # ========== 答题记录操作 ==========

    def add_test_record(self, record: TestRecord) -> int:
        cur = self.conn.execute(
            """INSERT INTO test_records (test_name, questions_json, answers_json, score, total, created_at)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (record.test_name, record.questions_json, record.answers_json,
             record.score, record.total,
             record.created_at or datetime.now().strftime("%Y-%m-%d %H:%M"))
        )
        self.conn.commit()
        return cur.lastrowid

    def get_test_records(self, limit: int = 20) -> list[TestRecord]:
        rows = self.conn.execute(
            "SELECT * FROM test_records ORDER BY id DESC LIMIT ?", (limit,)
        ).fetchall()
        return [TestRecord(**dict(r)) for r in rows]

    def close(self):
        self.conn.close()
