#!/usr/bin/env python3
"""高中物理题库系统 - Web 服务器

使用 Python 内置 http.server 实现的 Web 界面。
无需安装任何第三方依赖。

启动方式：
    python3 web_server.py

然后在浏览器打开 http://localhost:8090
"""

import json
import os
import sys
import socket
import base64
import uuid
import subprocess
import urllib.parse
from http.server import HTTPServer, BaseHTTPRequestHandler
from datetime import datetime

# 确保能导入同目录下的模块
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from database import Database
from question_bank import QuestionBank
from test_generator import TestGenerator
from models import Question

PORT = 8090
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "physics_bank.db")
IMAGES_DIR = os.path.join(BASE_DIR, "images")

# 确保图片目录存在
os.makedirs(IMAGES_DIR, exist_ok=True)


class APIHandler(BaseHTTPRequestHandler):
    """HTTP 请求处理器 - 同时提供页面和 API"""

    db: Database = None
    bank: QuestionBank = None
    gen: TestGenerator = None
    router: dict = None

    @classmethod
    def init_app(cls):
        """初始化数据库和路由表"""
        cls.db = Database()
        cls.bank = QuestionBank(cls.db)
        cls.gen = TestGenerator(cls.db)
        cls.router = {
            ("GET", "/"): "handle_index",
            ("GET", "/api/stats"): "api_stats",
            ("GET", "/api/topics"): "api_topics",
            ("GET", "/api/questions"): "api_questions",
            ("GET", "/api/records"): "api_records",
            ("POST", "/api/generate"): "api_generate",
            ("POST", "/api/answer"): "api_answer",
            ("POST", "/api/questions/add"): "api_add_question",
            ("POST", "/api/upload-image"): "api_upload_image",
            ("POST", "/api/export-docx"): "api_export_docx",
            ("POST", "/api/export-pdf-html"): "api_export_pdf_html",
            ("POST", "/api/questions/batch"): "api_questions_batch",
            ("PUT", "/api/questions/update"): "api_update_question",
            ("DELETE", "/api/questions/delete"): "api_delete_question",
        }

    def log_message(self, format, *args):
        """简化日志"""
        print(f"  {args[0]}")

    def do_GET(self):
        self._route("GET")

    def do_POST(self):
        self._route("POST")

    def do_PUT(self):
        self._route("PUT")

    def do_DELETE(self):
        self._route("DELETE")

    def _route(self, method):
        """路由分发"""
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path.rstrip("/") or "/"

        # 静态文件（JS/CSS 内嵌在 HTML 中，这里只处理 favicon）
        if path == "/favicon.ico":
            self.send_response(204)
            self.end_headers()
            return

        # API 路由需要完整路径匹配，部分带参数
        route_key = (method, path)
        if route_key in self.router:
            handler = getattr(self, self.router[route_key])
            handler(parsed)
            return

        # 带路径参数的 API
        if path.startswith("/api/questions/") and method == "GET":
            self.api_get_question(parsed)
            return

        # 图片静态资源
        if path.startswith("/images/") and method == "GET":
            self._serve_image(path)
            return

        # 404
        self.send_response(404)
        self.end_headers()
        self.wfile.write(b'{"error": "Not found"}')

    def _get_query(self, parsed):
        return dict(urllib.parse.parse_qsl(parsed.query))

    def _read_body(self):
        length = int(self.headers.get("Content-Length", 0))
        if length == 0:
            return {}
        body = self.rfile.read(length)
        return json.loads(body)

    def _json_response(self, data, status=200):
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(json.dumps(data, ensure_ascii=False).encode())

    def _html_response(self, html, status=200):
        self.send_response(status)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.end_headers()
        self.wfile.write(html.encode())

    def _serve_image(self, path):
        """提供图片静态资源"""
        # 安全检查：防止路径穿越
        safe_path = os.path.normpath(path.lstrip("/"))
        filepath = os.path.join(BASE_DIR, safe_path)
        if not filepath.startswith(IMAGES_DIR) or not os.path.isfile(filepath):
            self.send_response(404)
            self.end_headers()
            self.wfile.write(b'{"error": "Image not found"}')
            return
        # 根据扩展名设置 MIME
        ext = os.path.splitext(filepath)[1].lower()
        mime_map = {".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg",
                    ".gif": "image/gif", ".webp": "image/webp", ".svg": "image/svg+xml"}
        content_type = mime_map.get(ext, "application/octet-stream")
        try:
            with open(filepath, "rb") as f:
                data = f.read()
            self.send_response(200)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(data)))
            self.send_header("Cache-Control", "public, max-age=86400")
            self.end_headers()
            self.wfile.write(data)
        except Exception:
            self.send_response(500)
            self.end_headers()

    def api_upload_image(self, parsed):
        """上传图片（base64 JSON 方式）"""
        data = self._read_body()
        b64_data = data.get("data", "")
        if not b64_data:
            self._json_response({"error": "缺少图片数据"}, 400)
            return
        # 去除可能的 data:image/...;base64, 前缀
        if "," in b64_data and b64_data.startswith("data:"):
            b64_data = b64_data.split(",", 1)[1]
        try:
            raw = base64.b64decode(b64_data)
        except Exception:
            self._json_response({"error": "Base64 解码失败"}, 400)
            return
        # 生成唯一文件名
        ext = ".png"
        if len(raw) > 3:
            if raw[:3] == b'\xff\xd8\xff':
                ext = ".jpg"
            elif raw[:4] == b'\x89PNG':
                ext = ".png"
            elif raw[:3] == b'GIF':
                ext = ".gif"
        filename = f"{uuid.uuid4().hex}{ext}"
        filepath = os.path.join(IMAGES_DIR, filename)
        with open(filepath, "wb") as f:
            f.write(raw)
        self._json_response({"filename": filename, "url": f"/images/{filename}"})

    def api_questions_batch(self, parsed):
        """批量获取指定ID的题目"""
        data = self._read_body()
        ids = data.get("ids", [])
        if not ids:
            self._json_response({"questions": []})
            return
        questions = []
        for qid in ids:
            q = self.db.get_question(int(qid))
            if q:
                questions.append({
                    "id": q.id, "topic_id": q.topic_id, "topic_name": q.topic_name,
                    "grade_level": q.grade_level, "qtype": q.qtype,
                    "difficulty": q.difficulty, "content": q.content,
                    "options": q.options, "answer": q.answer,
                    "explanation": q.explanation, "image_path": q.image_path,
                })
        self._json_response({"questions": questions})

    def api_export_pdf_html(self, parsed):
        """生成打印版 HTML（浏览器打印→另存为PDF）"""
        data = self._read_body()
        questions_data = data.get("questions", [])
        test_name = data.get("test_name", "物理试卷")
        include_answer = data.get("include_answer", False)
        grade_level = data.get("grade_level", "")

        # 分类
        single_qs = [q for q in questions_data if q.get("qtype") == "单选题"]
        multi_qs = [q for q in questions_data if q.get("qtype") == "多选题"]
        calc_qs = [q for q in questions_data
                   if q.get("qtype") not in ("单选题", "多选题")]

        def esc(s):
            return (s or "").replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")

        def render_options(opts):
            if not opts:
                return ""
            labels = "ABCDEF"
            return "".join(
                f'<div class="opt">{labels[i]}. {esc(o)}</div>'
                for i, o in enumerate(opts) if i < len(labels)
            )

        html_parts = [f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<title>{esc(test_name)}</title>
<style>
  @page {{ size: A4; margin: 15mm 20mm; }}
  body {{ font-family: "SimSun","宋体",serif; font-size:14px; line-height:1.8; color:#000; }}
  h1 {{ text-align:center; font-size:22px; font-family:"SimHei","黑体",sans-serif; margin-bottom:4px; }}
  h2 {{ text-align:center; font-size:16px; font-weight:normal; margin:0 0 12px 0; }}
  .info {{ text-align:center; font-size:13px; margin-bottom:8px; }}
  .info span {{ margin:0 20px; }}
  .score-table {{ width:100%; border-collapse:collapse; margin:0 auto 16px; max-width:400px; }}
  .score-table td,.score-table th {{ border:1px solid #000; padding:4px 10px; text-align:center; font-size:13px; }}
  .section-title {{ font-size:15px; font-weight:bold; margin:14px 0 6px 0; }}
  .instruction {{ font-size:13px; margin-bottom:8px; }}
  .q {{ margin-bottom:6px; }}
  .q-content {{ font-size:14px; }}
  .opt {{ font-size:14px; padding:1px 0 1px 24px; }}
  .q-title {{ font-size:14px; }}
  .answer {{ font-size:13px; background:#f5f5f5; padding:2px 8px; margin-top:2px; }}
  .calc-q {{ margin-bottom:16px; }}
  .calc-space {{ height:120px; border-bottom:1px dashed #ccc; margin-bottom:8px; }}
  .page-break {{ page-break-before:always; }}
  @media print {{
    body {{ -webkit-print-color-adjust:exact; print-color-adjust:exact; }}
    .no-print {{ display:none; }}
  }}
</style>
</head>
<body>
<div class="no-print" style="text-align:center;padding:8px;background:#fffbeb;margin-bottom:16px;border:1px solid #ecc94b;border-radius:4px">
  ⚠️ 打印预览 — 按 <strong>Ctrl+P</strong> 或 <strong>⌘+P</strong> 选择「另存为PDF」即可导出
</div>
<h1>{esc(test_name)}</h1>
<h2>物理{('（' + esc(grade_level) + '）') if grade_level else ''}</h2>
<div class="info">
  <span>满分：100分</span><span>时间：60分钟</span>
</div>
<table class="score-table">
  <tr><th>题型</th><th>选择题</th><th>非选择题</th><th>总分</th></tr>
  <tr><td>分值</td><td>{6 * (len(single_qs) + len(multi_qs))}分</td><td></td><td>100分</td></tr>
  <tr><td>得分</td><td></td><td></td><td></td></tr>
</table>"""]

        # 选择题
        if single_qs or multi_qs:
            total_c = len(single_qs) + len(multi_qs)
            html_parts.append(
                f'<div class="section-title">一、选择题'
                f'（共{total_c}题，每题6分，共{total_c*6}分）</div>'
            )
            inst = f'第1—{len(single_qs)}题为单选题；' if single_qs else ''
            if multi_qs:
                inst += (f'第{len(single_qs)+1}—{total_c}题为多选题'
                         f'（选对但不全得3分，有选错得0分）')
            html_parts.append(f'<div class="instruction">{inst}</div>')

            idx = 0
            for q in single_qs:
                idx += 1
                html_parts.append(
                    f'<div class="q"><div class="q-title">'
                    f'{idx}. {esc(q.get("content",""))}</div>'
                    f'{render_options(q.get("options",[]))}</div>'
                )
            for q in multi_qs:
                idx += 1
                html_parts.append(
                    f'<div class="q"><div class="q-title">'
                    f'{idx}.（多选）{esc(q.get("content",""))}</div>'
                    f'{render_options(q.get("options",[]))}</div>'
                )

        # 非选择题
        if calc_qs:
            html_parts.append(
                f'<div class="section-title">二、非选择题'
                f'（共{len(calc_qs)}题）</div>'
            )
            html_parts.append(
                '<div class="instruction">解答应写出必要的文字说明和演算步骤。</div>'
            )
            for i, q in enumerate(calc_qs, 1):
                score = {"易": 8, "中": 12, "难": 16}.get(q.get("difficulty", "中"), 12)
                content = q.get("content", "")
                # 小问拆行
                import re as _re
                sub_parts = _re.split(r'(?=（\d+）)|(?=\(\d+\))|(?=[①②③④⑤⑥])', content)
                sub_parts = [s.strip() for s in sub_parts if s.strip()]
                first = sub_parts[0] if sub_parts else content
                html_parts.append(
                    f'<div class="calc-q"><div class="q-title">'
                    f'{i}.（{score}分）{esc(first)}</div>'
                )
                for sub in sub_parts[1:]:
                    html_parts.append(f'<div class="q-title">{esc(sub)}</div>')
                if not include_answer:
                    html_parts.append('<div class="calc-space"></div>')
                else:
                    html_parts.append(
                        f'<div class="answer">【答案】{esc(q.get("answer",""))}'
                        f'</div>'
                    )
                html_parts.append('</div>')

        # 答案
        if include_answer:
            html_parts.append('<div class="page-break"></div>')
            html_parts.append(
                '<h1 style="margin-top:30px">参考答案</h1>'
            )
            all_choice = single_qs + multi_qs
            if all_choice:
                html_parts.append(
                    '<div class="section-title">一、选择题</div>'
                )
                for i, q in enumerate(all_choice, 1):
                    tag = "（多选）" if q.get("qtype") == "多选题" else ""
                    html_parts.append(
                        f'<div>{i}.{tag} {esc(q.get("answer",""))}'
                        f'{" — " + esc(q.get("explanation","")) if q.get("explanation") else ""}</div>'
                    )
            if calc_qs:
                html_parts.append(
                    '<div class="section-title">二、非选择题</div>'
                )
                for i, q in enumerate(calc_qs, 1):
                    html_parts.append(
                        f'<div>{i}. {esc(q.get("answer",""))}'
                        f'{" — " + esc(q.get("explanation","")) if q.get("explanation") else ""}</div>'
                    )

        html_parts.append('</body></html>')
        self._html_response("\n".join(html_parts))

    def api_export_docx(self, parsed):
        """导出试卷为 Word 文档"""
        data = self._read_body()
        questions_data = data.get("questions", [])
        test_name = data.get("test_name", "物理试卷")
        include_answer = data.get("include_answer", False)
        grade_level = data.get("grade_level", "")

        if not questions_data:
            self._json_response({"error": "缺少题目数据"}, 400)
            return

        from docx_export import export_test_to_docx_bytes
        docx_bytes = export_test_to_docx_bytes(
            questions=questions_data,
            test_name=test_name,
            include_answer=include_answer,
            grade_level=grade_level,
        )

        # 文件名处理（中文需要 URL 编码）
        safe_name = test_name.replace("/", "_").replace("\\", "_")
        encoded_name = urllib.parse.quote(f"{safe_name}.docx")

        self.send_response(200)
        self.send_header("Content-Type",
                         "application/vnd.openxmlformats-officedocument.wordprocessingml.document")
        self.send_header("Content-Disposition",
                         f"attachment; filename*=UTF-8''{encoded_name}")
        self.send_header("Content-Length", str(len(docx_bytes)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(docx_bytes)

    # ==================== 页面处理 ====================

    def handle_index(self, parsed):
        """返回主页面"""
        self._html_response(HTML_PAGE)

    # ==================== API 处理 ====================

    def api_stats(self, parsed):
        stats = self.bank.stats()
        self._json_response(stats)

    def api_topics(self, parsed):
        grade = self._get_query(parsed).get("grade_level", "")
        tree = self.bank.get_topic_tree(grade_level=grade if grade else None)
        result = []
        for node in tree:
            p = node["topic"]
            item = {
                "id": p.id,
                "name": p.name,
                "grade_level": p.grade_level,
                "children": [
                    {"id": c.id, "name": c.name, "grade_level": c.grade_level}
                    for c in node["children"]
                ]
            }
            result.append(item)
        self._json_response(result)

    def api_questions(self, parsed):
        params = self._get_query(parsed)
        topic_id = int(params["topic_id"]) if params.get("topic_id") else None

        # 如果是父知识点，同时包含其所有子知识点
        topic_ids = None
        if topic_id:
            topic_ids = [topic_id]
            children = self.db.get_subtopics(topic_id)
            for child in children:
                topic_ids.append(child.id)

        questions = self.bank.search(
            grade_level=params.get("grade_level") or None,
            qtype=params.get("qtype") or None,
            difficulty=params.get("difficulty") or None,
            keyword=params.get("keyword") or None,
            topic_id=None,  # 使用 topic_ids 替代
            topic_ids=topic_ids,
            limit=int(params.get("limit", 50))
        )
        result = []
        for q in questions:
            result.append({
                "id": q.id,
                "topic_id": q.topic_id,
                "topic_name": q.topic_name,
                "grade_level": q.grade_level,
                "qtype": q.qtype,
                "difficulty": q.difficulty,
                "content": q.content,
                "options": q.options,
                "answer": q.answer,
                "explanation": q.explanation,
                "image_path": q.image_path,
            })
        self._json_response(result)

    def api_get_question(self, parsed):
        parts = parsed.path.strip("/").split("/")
        try:
            qid = int(parts[-1])
        except (ValueError, IndexError):
            self._json_response({"error": "Invalid ID"}, 400)
            return
        q = self.db.get_question(qid)
        if not q:
            self._json_response({"error": "Not found"}, 404)
            return
        self._json_response({
            "id": q.id, "topic_id": q.topic_id, "topic_name": q.topic_name,
            "grade_level": q.grade_level, "qtype": q.qtype,
            "difficulty": q.difficulty, "content": q.content,
            "options": q.options, "answer": q.answer, "explanation": q.explanation,
            "image_path": q.image_path,
        })

    def api_records(self, parsed):
        records = self.db.get_test_records(limit=30)
        result = []
        for r in records:
            result.append({
                "id": r.id,
                "test_name": r.test_name,
                "score": r.score,
                "total": r.total,
                "created_at": r.created_at,
            })
        self._json_response(result)

    def api_generate(self, parsed):
        data = self._read_body()
        grade_level = data.get("grade_level") or None
        topic_id = data.get("topic_id") or None
        qtype = data.get("qtype") or None
        difficulty = data.get("difficulty") or None
        count = data.get("count", 10)
        mode = data.get("mode", "custom")

        if mode == "mixed" and grade_level:
            questions = self.gen.generate_mixed(
                grade_level=grade_level, total=count, name="综合卷"
            )
        elif mode == "gaokao":
            questions = self.gen.generate_for_gaokao(count=count, name="模拟卷")
        else:
            questions = self.gen.generate_by_criteria(
                grade_level=grade_level, topic_id=topic_id,
                qtype=qtype, difficulty=difficulty, count=count
            )

        result = []
        for q in questions:
            result.append({
                "id": q.id, "qtype": q.qtype, "difficulty": q.difficulty,
                "content": q.content, "options": q.options,
                "topic_name": q.topic_name, "grade_level": q.grade_level,
                "image_path": q.image_path,
            })
        self._json_response({"questions": result, "count": len(result)})

    def api_answer(self, parsed):
        """提交答案并评分"""
        data = self._read_body()
        question_ids = data.get("question_ids", [])
        user_answers = data.get("answers", {})
        test_name = data.get("test_name", "在线测试")

        questions_data = []
        score = 0.0
        total = float(len(question_ids))

        results = []
        for qid in question_ids:
            q = self.db.get_question(int(qid))
            if not q:
                continue
            user_ans = user_answers.get(str(qid), "").strip()
            correct = False
            score_got = 0.0

            if q.is_choice():
                if q.is_multi():
                    # 多选题：完全正确得1分，部分正确得0.5分
                    user_set = set(user_ans.upper())
                    correct_set = set(q.answer.upper().strip())
                    if user_set == correct_set:
                        correct = True
                        score_got = 1.0
                    elif user_set and user_set.issubset(correct_set):
                        score_got = 0.5
                    else:
                        score_got = 0.0
                else:
                    # 单选题
                    correct = user_ans.upper() == q.answer.upper().strip()
                    score_got = 1.0 if correct else 0.0
                score += score_got

            results.append({
                "id": q.id,
                "content": q.content[:80],
                "qtype": q.qtype,
                "user_answer": user_ans,
                "correct_answer": q.answer,
                "correct": correct,
                "score": score_got,
                "explanation": q.explanation,
            })
            questions_data.append({
                "id": q.id, "qtype": q.qtype, "difficulty": q.difficulty,
                "content": q.content[:100], "answer": q.answer,
                "topic_name": q.topic_name,
            })

        final_score = (score / total * 100) if total > 0 else 0

        # 保存记录
        from models import TestRecord
        record = TestRecord(
            test_name=test_name,
            questions_json=json.dumps(questions_data, ensure_ascii=False),
            answers_json=json.dumps(user_answers, ensure_ascii=False),
            score=score, total=total,
            created_at=datetime.now().strftime("%Y-%m-%d %H:%M")
        )
        self.db.add_test_record(record)

        self._json_response({
            "score": score, "total": total, "percentage": round(final_score, 1),
            "results": results,
        })

    def api_add_question(self, parsed):
        data = self._read_body()
        q = Question(
            topic_id=data.get("topic_id", 1),
            qtype=data.get("qtype", "选择题"),
            difficulty=data.get("difficulty", "中"),
            content=data.get("content", ""),
            options=data.get("options", []),
            answer=data.get("answer", ""),
            explanation=data.get("explanation", ""),
            image_path=data.get("image_path", ""),
        )
        qid = self.db.add_question(q)
        self._json_response({"id": qid, "message": "添加成功"})

    def api_update_question(self, parsed):
        data = self._read_body()
        q = self.db.get_question(data["id"])
        if not q:
            self._json_response({"error": "Not found"}, 404)
            return
        if "content" in data:
            q.content = data["content"]
        if "answer" in data:
            q.answer = data["answer"]
        if "explanation" in data:
            q.explanation = data["explanation"]
        if "difficulty" in data:
            q.difficulty = data["difficulty"]
        if "qtype" in data:
            q.qtype = data["qtype"]
        if "options" in data:
            q.options = data["options"]
        self.db.update_question(q)
        self._json_response({"message": "更新成功"})

    def api_delete_question(self, parsed):
        data = self._read_body()
        qid = data.get("id")
        self.db.delete_question(int(qid))
        self._json_response({"message": "删除成功"})


# ================================================================
# HTML 页面（单页应用）
# ================================================================

HTML_PAGE = r"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>🎓 高中物理题库系统</title>
<style>
  :root {
    --bg: #f0f4f8;
    --card: #ffffff;
    --text: #1a202c;
    --muted: #718096;
    --border: #e2e8f0;
    --primary: #4c51bf;
    --primary-light: #ebf4ff;
    --success: #38a169;
    --danger: #e53e3e;
    --warning: #d69e2e;
    --radius: 12px;
    --shadow: 0 1px 3px rgba(0,0,0,.08), 0 1px 2px rgba(0,0,0,.06);
  }
  * { margin:0; padding:0; box-sizing:border-box; }
  body { font-family: -apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,sans-serif; background:var(--bg); color:var(--text); line-height:1.6; }

  .header { background:linear-gradient(135deg,#1a365d,#2c5282); color:#fff; padding:20px 24px; text-align:center; }
  .header h1 { font-size:1.6em; margin-bottom:4px; }
  .header p { opacity:.8; font-size:.9em; }

  .container { max-width:1000px; margin:0 auto; padding:16px; }

  .tabs { display:flex; gap:4px; background:var(--card); border-radius:var(--radius); padding:4px; margin-bottom:16px; box-shadow:var(--shadow); flex-wrap:wrap; }
  .tab { flex:1; min-width:80px; padding:10px 8px; border:none; background:transparent; cursor:pointer; border-radius:8px; font-size:.85em; transition:.2s; color:var(--muted); }
  .tab:hover { background:#edf2f7; }
  .tab.active { background:var(--primary); color:#fff; font-weight:600; }

  .card { background:var(--card); border-radius:var(--radius); box-shadow:var(--shadow); padding:20px; margin-bottom:16px; }
  .card h2 { font-size:1.2em; margin-bottom:12px; color:#2d3748; }
  .card h3 { font-size:1em; color:#4a5568; margin-bottom:8px; }

  .stats-row { display:grid; grid-template-columns:repeat(auto-fit,minmax(120px,1fr)); gap:12px; margin-bottom:16px; }
  .stat { background:var(--card); border-radius:var(--radius); padding:16px; text-align:center; box-shadow:var(--shadow); }
  .stat .num { font-size:2em; font-weight:700; color:var(--primary); }
  .stat .label { font-size:.8em; color:var(--muted); margin-top:2px; }

  .btn { display:inline-block; padding:8px 20px; border:none; border-radius:8px; cursor:pointer; font-size:.9em; font-weight:500; transition:.2s; }
  .btn-primary { background:var(--primary); color:#fff; }
  .btn-primary:hover { opacity:.9; }
  .btn-success { background:var(--success); color:#fff; }
  .btn-danger { background:var(--danger); color:#fff; }
  .btn-outline { background:transparent; border:1px solid var(--border); color:var(--text); }
  .btn-sm { padding:4px 12px; font-size:.8em; }
  .btn-group { display:flex; gap:8px; flex-wrap:wrap; margin:8px 0; }

  .select, .input { padding:8px 12px; border:1px solid var(--border); border-radius:8px; font-size:.9em; background:#fff; }
  .select:focus, .input:focus { outline:none; border-color:var(--primary); box-shadow:0 0 0 3px rgba(76,81,191,.15); }
  .input { width:100%; }

  .form-row { display:flex; gap:12px; flex-wrap:wrap; margin-bottom:12px; align-items:center; }
  .form-row label { font-size:.85em; color:var(--muted); min-width:3em; }

  .topic-list { columns:2; }
  @media(max-width:600px){ .topic-list{columns:1;} }
  .topic-item { padding:6px 10px; border-radius:6px; cursor:pointer; transition:.15s; break-inside:avoid; font-size:.9em; }
  .topic-item:hover { background:var(--primary-light); color:var(--primary); }
  .topic-item.parent { font-weight:600; margin-top:4px; }
  .topic-item.child { padding-left:24px; font-size:.85em; }
  .topic-item.selected { background:var(--primary); color:#fff; }

  .q-list-item { padding:10px 14px; border-radius:8px; cursor:pointer; transition:.15s; border:1px solid transparent; margin-bottom:6px; }
  .q-list-item:hover { border-color:var(--border); }
  .q-list-item .meta { font-size:.8em; color:var(--muted); }
  .q-list-item .content { margin-top:4px; }

  .badge { display:inline-block; padding:2px 10px; border-radius:10px; font-size:.75em; font-weight:600; }
  .badge-choice { background:#ebf8ff; color:#2b6cb0; }
  .badge-experiment { background:#faf5ff; color:#6b46c1; }
  .badge-calc { background:#fffaf0; color:#c05621; }
  .badge-experiment { background:#e6fffa; color:#234e52; }
  .badge-easy { background:#f0fff4; color:#276749; }
  .badge-mid { background:#fffff0; color:#975a16; }
  .badge-hard { background:#fff5f5; color:#c53030; }
  .badge-grade { background:#edf2f7; color:#4a5568; }

  .question-card { background:#f7fafc; border-radius:8px; padding:12px 16px; margin-bottom:6px; }
  .question-card .q-header { display:flex; gap:6px; flex-wrap:wrap; margin-bottom:8px; }
  .question-card .options { margin-top:8px; }
  .question-card .option { padding:8px 12px; margin:4px 0; border-radius:6px; border:1px solid var(--border); cursor:pointer; transition:.15s; }
  .question-card .option:hover { border-color:var(--primary); }
  .question-card .option.selected { background:var(--primary-light); border-color:var(--primary); font-weight:600; }
  .question-card .option.correct { background:#f0fff4; border-color:var(--success); }
  .question-card .option.wrong { background:#fff5f5; border-color:var(--danger); }
  .question-card .answer-input { padding:8px 12px; border:1px solid var(--border); border-radius:8px; width:100%; font-size:.9em; }

  .result-row { padding:8px 12px; border-radius:6px; margin-bottom:4px; }
  .result-row.correct { background:#f0fff4; }
  .result-row.wrong { background:#fff5f5; }

  .score-circle { width:120px; height:120px; border-radius:50%; display:flex; align-items:center; justify-content:center; flex-direction:column; margin:16px auto; border:6px solid var(--primary); }
  .score-circle .num { font-size:2.2em; font-weight:700; color:var(--primary); }

  .modal-overlay { display:none; position:fixed; inset:0; background:rgba(0,0,0,.4); z-index:100; align-items:center; justify-content:center; }
  .modal-overlay.show { display:flex; }
  .modal { background:#fff; border-radius:var(--radius); padding:24px; max-width:600px; width:90%; max-height:80vh; overflow-y:auto; box-shadow:0 20px 60px rgba(0,0,0,.2); }
  .modal h3 { margin-bottom:12px; }

  .hidden { display:none !important; }
  .text-muted { color:var(--muted); font-size:.85em; }
  .text-center { text-align:center; }
  .mt-8 { margin-top:8px; }
  .mb-8 { margin-bottom:8px; }
  .mb-16 { margin-bottom:16px; }
  .gap-8 { gap:8px; }
</style>
</head>
<body>

<div class="header">
  <h1>🎓 高中物理题库系统</h1>
  <p>高一高二 · 基础夯实 &nbsp;|&nbsp; 高三 · 冲刺高考</p>
</div>

<div class="container">
  <div id="statsRow" class="stats-row"></div>

  <div class="tabs">
    <button class="tab active" data-tab="browse">📖 题库浏览</button>
    <button class="tab" data-tab="generate">📝 组卷测试</button>
    <button class="tab" data-tab="add">✏️ 添加题目</button>
    <button class="tab" data-tab="records">📋 答题记录</button>
  </div>

  <!-- 题库浏览 -->
  <div id="tab-browse" class="tab-content">
    <div class="card">
      <div class="form-row">
        <select id="browseGrade" class="select" onchange="loadTopics()">
          <option value="">全部年级</option>
          <option value="高一高二">高一高二</option>
          <option value="高三">高三</option>
        </select>
        <select id="browseType" class="select" onchange="refreshQuestionList()">
          <option value="">全部题型</option>
          <option value="单选题">单选题</option>
          <option value="多选题">多选题</option>
          <option value="实验题">实验题</option>
          <option value="计算题">计算题</option>
        </select>
        <select id="browseDiff" class="select" onchange="refreshQuestionList()">
          <option value="">全部难度</option>
          <option value="易">易</option>
          <option value="中">中</option>
          <option value="难">难</option>
        </select>
        <input id="browseKeyword" class="input" style="max-width:200px" placeholder="搜索关键词..." oninput="refreshQuestionList()">
      </div>
      <div id="topicTree" class="topic-list mb-16"></div>
      <div id="questionList"></div>
    </div>
  </div>

  <!-- 组卷测试 -->
  <div id="tab-generate" class="tab-content hidden">
    <div class="card" id="genPanel">
      <h2>📝 组卷设置</h2>
      <div class="form-row">
        <label>模式</label>
        <select id="genMode" class="select" onchange="onGenModeChange()">
          <option value="custom">自定义筛选</option>
          <option value="mixed">综合卷（混合难度）</option>
          <option value="gaokao">高三高考模拟卷</option>
          <option value="custom_select">🖐 自定义选题（选题篮）</option>
        </select>
      </div>
      <div id="genCustomOptions">
        <div class="form-row">
          <label>年级</label>
          <select id="genGrade" class="select"><option value="">不限</option><option value="高一高二">高一高二</option><option value="高三">高三</option></select>
          <label>题型</label>
          <select id="genType" class="select"><option value="">不限</option><option value="单选题">单选题</option><option value="多选题">多选题</option><option value="实验题">实验题</option><option value="计算题">计算题</option></select>
          <label>难度</label>
          <select id="genDiff" class="select"><option value="">不限</option><option value="易">易</option><option value="中">中</option><option value="难">难</option></select>
        </div>
      </div>
      <div class="form-row">
        <label>题数</label>
        <input id="genCount" class="input" style="max-width:80px" value="10" type="number" min="1" max="50">
        <button class="btn btn-primary" onclick="generateTest()">🎲 生成试卷</button>
      </div>
    </div>
    <div id="testPaper" class="card hidden">
      <h2 id="testTitle">试卷</h2>
      <div id="testQuestions"></div>
      <div class="btn-group" id="submitArea" style="margin-top:12px">
        <button class="btn btn-success" onclick="submitAnswers()">📤 提交答案</button>
        <button class="btn btn-outline" onclick="exportDocx(false)">📄 Word（无答案）</button>
        <button class="btn btn-outline" onclick="exportDocx(true)">📄 Word（含答案）</button>
        <button class="btn btn-outline" onclick="exportPdf(false)">🖨 PDF（打印版）</button>
        <button class="btn btn-outline" onclick="exportPdf(true)">🖨 PDF（含答案）</button>
      </div>
      <div id="testResult" class="hidden"></div>
    </div>
  </div>

  <!-- 添加题目 -->
  <div id="tab-add" class="tab-content hidden">
    <div class="card">
      <h2>✏️ 添加新题目</h2>
      <div class="form-row">
        <label>年级</label>
        <select id="addGrade" class="select"><option value="高一高二">高一高二</option><option value="高三">高三</option></select>
      </div>
      <div id="addTopicTree" class="topic-list mb-16"></div>
      <div class="form-row">
        <label>题型</label>
        <select id="addType" class="select" onchange="onAddTypeChange()"><option value="单选题">单选题</option><option value="多选题">多选题</option><option value="实验题">实验题</option><option value="计算题">计算题</option></select>
        <label>难度</label>
        <select id="addDiff" class="select"><option value="易">易</option><option value="中" selected>中</option><option value="难">难</option></select>
      </div>
      <div class="mb-8"><label>题目内容</label></div>
      <textarea id="addContent" class="input" rows="4" style="resize:vertical" placeholder="在此输入题目内容..."></textarea>
      <div id="addOptionsArea" class="mb-16">
        <div class="mt-8"><label>选项（每行一个）</label></div>
        <textarea id="addOptions" class="input" rows="3" placeholder="A选项文字&#10;B选项文字&#10;C选项文字&#10;D选项文字" style="resize:vertical"></textarea>
      </div>
      <div class="form-row">
        <label>答案</label>
        <input id="addAnswer" class="input" style="max-width:300px" placeholder="正确答案">
      </div>
      <div class="mb-8">
        <label>配图（可选）</label>
        <input type="file" id="addImageFile" class="input" accept="image/*" onchange="previewAddImage()" style="max-width:300px">
        <input type="hidden" id="addImagePath" value="">
        <div id="addImagePreview" class="hidden mt-8"></div>
      </div>
      <div class="mb-8">
        <label>解析（可选）</label>
        <input id="addExplanation" class="input" placeholder="题目解析...">
      </div>
      <button class="btn btn-primary" onclick="addQuestion()">✅ 添加题目</button>
      <span id="addMsg" class="text-muted" style="margin-left:12px"></span>
    </div>
  </div>

  <!-- 答题记录 -->
  <div id="tab-records" class="tab-content hidden">
    <div class="card">
      <h2>📋 答题记录</h2>
      <div id="recordsList"></div>
    </div>
  </div>
</div>

<!-- 选题篮浮动条 -->
<div id="selectionBar" style="position:fixed;bottom:0;left:0;right:0;background:var(--primary);color:#fff;padding:10px 24px;display:none;align-items:center;justify-content:space-between;z-index:50;box-shadow:0 -2px 10px rgba(0,0,0,.2)">
  <span>📋 已选 <strong id="selectionCount">0</strong> 题</span>
  <div style="display:flex;gap:8px">
    <button class="btn btn-sm" style="background:rgba(255,255,255,.2);color:#fff" onclick="clearSelection()">🗑 清空</button>
    <button class="btn btn-sm" style="background:#fff;color:var(--primary);font-weight:600" onclick="goToTestWithSelection()">📝 用这些题组卷</button>
  </div>
</div>

<!-- 题目详情弹窗 -->
<div class="modal-overlay" id="detailModal">
  <div class="modal" id="detailContent"></div>
</div>

<script>
// ==================== 工具函数 ====================
function splitSubItems(text) {
  // 将 （1）（2）(1)(2) ①② 等拆分为行
  const parts = text.split(/(?=（\d+）)|(?=\(\d+\))|(?=[①②③④⑤⑥])/);
  return parts.filter(s => s.trim());
}

// ==================== 全局状态 ====================
let currentTopicId = null;
let currentTestQuestions = [];
let currentGradeLevel = '';
let currentTestName = '物理试卷';
let selectedQuestions = new Map();  // id -> question summary

// ==================== 标签切换 ====================
document.querySelectorAll('.tab').forEach(t => {
  t.addEventListener('click', () => {
    document.querySelectorAll('.tab').forEach(x => x.classList.remove('active'));
    t.classList.add('active');
    document.querySelectorAll('.tab-content').forEach(x => x.classList.add('hidden'));
    const target = document.getElementById('tab-' + t.dataset.tab);
    if (target) target.classList.remove('hidden');
    if (t.dataset.tab === 'records') loadRecords();
    if (t.dataset.tab === 'add') loadAddTopics();
  });
});

// ==================== 统计 ====================
async function loadStats() {
  const res = await fetch('/api/stats');
  const s = await res.json();
  document.getElementById('statsRow').innerHTML = `
    <div class="stat"><div class="num">${s.total}</div><div class="label">总题数</div></div>
    <div class="stat"><div class="num">${s.grade_10_11}</div><div class="label">高一高二</div></div>
    <div class="stat"><div class="num">${s.grade_12}</div><div class="label">高三</div></div>
    <div class="stat"><div class="num">${s.single}</div><div class="label">单选题</div></div>
    <div class="stat"><div class="num">${s.multi}</div><div class="label">多选题</div></div>
    <div class="stat"><div class="num">${s.experiment}</div><div class="label">实验题</div></div>
    <div class="stat"><div class="num">${s.calc}</div><div class="label">计算题</div></div>
  `;
}

// ==================== 知识点树 ====================
async function loadTopics() {
  // 切换年级时重置已选知识点，避免旧 topic_id 和新 grade 冲突
  currentTopicId = null;
  const grade = document.getElementById('browseGrade').value;
  const res = await fetch('/api/topics?grade_level=' + encodeURIComponent(grade));
  const tree = await res.json();
  let html = '';
  tree.forEach(parent => {
    html += `<div class="topic-item parent" data-id="${parent.id}" onclick="selectTopic(${parent.id}, this)">📘 ${parent.name}</div>`;
    parent.children.forEach(child => {
      html += `<div class="topic-item child" data-id="${child.id}" onclick="selectTopic(${child.id}, this)">📄 ${child.name}</div>`;
    });
  });
  document.getElementById('topicTree').innerHTML = html || '<p class="text-muted">暂无知识点</p>';
  refreshQuestionList();
}

function selectTopic(id, el) {
  // 切换选中状态：同一知识点再次点击则取消筛选
  if (currentTopicId === id) {
    currentTopicId = null;
  } else {
    currentTopicId = id;
  }
  // 更新 UI 高亮
  document.querySelectorAll('#topicTree .topic-item').forEach(x => x.classList.remove('selected'));
  if (currentTopicId && el) {
    el.classList.add('selected');
    // 同时高亮 data-id 匹配的元素（处理重建后的 DOM）
  } else if (currentTopicId) {
    const match = document.querySelector(`#topicTree .topic-item[data-id="${currentTopicId}"]`);
    if (match) match.classList.add('selected');
  }
  refreshQuestionList();
}

async function refreshQuestionList() {
  const grade = document.getElementById('browseGrade').value;
  const qtype = document.getElementById('browseType').value;
  const diff = document.getElementById('browseDiff').value;
  const kw = document.getElementById('browseKeyword').value;
  let url = '/api/questions?limit=200';
  if (grade) url += '&grade_level=' + encodeURIComponent(grade);
  if (qtype) url += '&qtype=' + encodeURIComponent(qtype);
  if (diff) url += '&difficulty=' + encodeURIComponent(diff);
  if (kw) url += '&keyword=' + encodeURIComponent(kw);
  if (currentTopicId) url += '&topic_id=' + currentTopicId;

  try {
    const res = await fetch(url);
    const questions = await res.json();
    renderQuestionList(questions);
  } catch(e) {
    console.error('搜索失败:', e);
  }
}

function renderQuestionList(questions) {
  let html = `<p class="text-muted">共 ${questions.length} 道题目 | 已选 <strong id="selCount">${selectedQuestions.size}</strong> 题</p>`;
  if (!questions.length) {
    html += '<p class="text-muted">没有匹配的题目，请调整筛选条件</p>';
  }
  questions.forEach(q => {
    const isSelected = selectedQuestions.has(q.id);
    let typeBadge = (q.qtype === '单选题' || q.qtype === '多选题') ? 'badge-choice' : q.qtype === '实验题' ? 'badge-experiment' : 'badge-calc';
    let diffBadge = q.difficulty === '易' ? 'badge-easy' : q.difficulty === '中' ? 'badge-mid' : 'badge-hard';
    html += `<div class="q-list-item" style="${isSelected ? 'border-color:var(--primary);background:var(--primary-light)' : ''}">
      <div style="display:flex;justify-content:space-between;align-items:flex-start">
        <div style="flex:1;cursor:pointer" onclick="showDetail(${q.id})">
          <div class="meta">
            <span class="badge ${typeBadge}">${q.qtype}</span>
            <span class="badge ${diffBadge}">${q.difficulty}</span>
            <span class="badge badge-grade">${q.topic_name||''}</span>
          </div>
          <div class="content">${q.image_path ? '🖼️ ' : ''}${escHtml(q.content.substring(0, 80))}${q.content.length>80?'...':''}</div>
        </div>
        <button class="btn btn-sm ${isSelected ? 'btn-danger' : 'btn-outline'}"
                style="flex-shrink:0;margin-left:8px;min-width:60px"
                onclick="event.stopPropagation();toggleSelection(${q.id}, ${JSON.stringify({id:q.id,content:q.content.substring(0,60),qtype:q.qtype,difficulty:q.difficulty,topic_name:q.topic_name}).replace(/"/g,'&quot;')})">
          ${isSelected ? '✖ 移除' : '＋ 选题'}
        </button>
      </div>
    </div>`;
  });
  document.getElementById('questionList').innerHTML = html;
}

// ==================== 题目详情 ====================
async function showDetail(id) {
  const res = await fetch('/api/questions/' + id);
  const q = await res.json();
  let optsHtml = '';
  if (q.options && q.options.length) {
    const labels = ['A','B','C','D','E','F'];
    optsHtml = '<div style="margin-top:8px">' + q.options.map((o,i) =>
      `<div style="padding:4px 0"><strong>${labels[i]}.</strong> ${escHtml(o)}</div>`
    ).join('') + '</div>';
  }
  document.getElementById('detailContent').innerHTML = `
    <h3>题目详情 #${q.id}</h3>
    <p><span class="badge badge-${q.qtype==='单选题'||q.qtype==='多选题'?'choice':q.qtype==='实验题'?'fill':'calc'}">${q.qtype}</span>
       <span class="badge badge-${q.difficulty==='易'?'easy':q.difficulty==='中'?'mid':'hard'}">${q.difficulty}</span>
       <span class="badge badge-grade">${q.grade_level||''} · ${q.topic_name||''}</span></p>
    <div style="margin:12px 0;font-size:1.05em">${escHtml(q.content)}</div>
    ${q.image_path ? `<div style="margin:12px 0"><img src="/images/${q.image_path}" style="max-width:100%;max-height:300px;border-radius:8px;border:1px solid var(--border)" onerror="this.style.display='none'"></div>` : ''}
    ${optsHtml}
    <div style="margin-top:16px;padding:12px;background:#f0fff4;border-radius:8px">
      <strong>✅ 答案：</strong>${escHtml(q.answer)}
    </div>
    ${q.explanation ? `<div style="margin-top:8px;padding:12px;background:#fffbeb;border-radius:8px"><strong>📖 解析：</strong>${escHtml(q.explanation)}</div>` : ''}
    <div class="btn-group mt-8">
      <button class="btn btn-danger btn-sm" onclick="deleteQuestion(${q.id})">🗑 删除</button>
    </div>
  `;
  document.getElementById('detailModal').classList.add('show');
}

async function deleteQuestion(id) {
  if (!confirm('确认删除题目 #' + id + '？')) return;
  await fetch('/api/questions/delete', {method:'DELETE',body:JSON.stringify({id})});
  document.getElementById('detailModal').classList.remove('show');
  refreshQuestionList();
  loadStats();
}

document.getElementById('detailModal').addEventListener('click', function(e) {
  if (e.target === this) this.classList.remove('show');
});

// ==================== PDF 导出 ====================
async function exportPdf(includeAnswer) {
  if (!currentTestQuestions.length) { alert('没有试卷可导出'); return; }
  const body = {
    questions: currentTestQuestions,
    test_name: currentTestName,
    include_answer: includeAnswer,
    grade_level: currentGradeLevel,
  };
  const res = await fetch('/api/export-pdf-html', {method:'POST',body:JSON.stringify(body)});
  const html = await res.text();
  const w = window.open('', '_blank', 'width=800,height=600');
  w.document.write(html);
  w.document.close();
  w.onload = function() { w.print(); };
}

// ==================== 选题篮 ====================
function toggleSelection(id, summary) {
  if (selectedQuestions.has(id)) {
    selectedQuestions.delete(id);
  } else {
    selectedQuestions.set(id, summary);
  }
  updateSelectionBar();
  refreshQuestionList();
}

function clearSelection() {
  selectedQuestions.clear();
  updateSelectionBar();
  refreshQuestionList();
}

function updateSelectionBar() {
  const bar = document.getElementById('selectionBar');
  const count = selectedQuestions.size;
  document.getElementById('selectionCount').textContent = count;
  bar.style.display = count > 0 ? 'flex' : 'none';
}

function goToTestWithSelection() {
  if (selectedQuestions.size === 0) { alert('请先选题'); return; }
  // 切换到组卷 tab
  document.querySelectorAll('.tab').forEach(x => x.classList.remove('active'));
  document.querySelector('.tab[data-tab="generate"]').classList.add('active');
  document.querySelectorAll('.tab-content').forEach(x => x.classList.add('hidden'));
  document.getElementById('tab-generate').classList.remove('hidden');
  // 切换到自定义选题模式并隐藏数量输入
  document.getElementById('genMode').value = 'custom_select';
  document.getElementById('genCustomOptions').classList.add('hidden');
  document.getElementById('genCount').parentElement.classList.add('hidden');
  // 直接生成试卷
  generateTest();
}

// ==================== 组卷 ====================
function onGenModeChange() {
  const mode = document.getElementById('genMode').value;
  document.getElementById('genCustomOptions').classList.toggle('hidden', mode !== 'custom');
  document.getElementById('genCount').parentElement.classList.toggle('hidden', mode === 'custom_select');
  if (mode === 'gaokao') {
    document.getElementById('genGrade').value = '高三';
  }
  if (mode === 'custom_select') {
    document.getElementById('genCount').value = selectedQuestions.size;
  }
}

async function generateTest() {
  const mode = document.getElementById('genMode').value;
  const count = parseInt(document.getElementById('genCount').value) || 10;
  const body = { mode, count };
  if (mode === 'custom') {
    body.grade_level = document.getElementById('genGrade').value || null;
    body.qtype = document.getElementById('genType').value || null;
    body.difficulty = document.getElementById('genDiff').value || null;
  } else if (mode === 'mixed') {
    body.grade_level = document.getElementById('genGrade').value || '高一高二';
  }

  let data;
  if (mode === 'custom_select') {
    // 使用选题篮中的题目
    if (selectedQuestions.size === 0) {
      alert('请先在题库浏览中选择题目！点击"＋ 选题"按钮将题目加入选题篮。');
      return;
    }
    const ids = Array.from(selectedQuestions.keys());
    const res = await fetch('/api/questions/batch', {method:'POST',body:JSON.stringify({ids})});
    data = await res.json();
    data.count = data.questions.length;
    currentGradeLevel = '';
    currentTestName = '自定义选题卷';
  } else {
    const res = await fetch('/api/generate', {method:'POST',body:JSON.stringify(body)});
    data = await res.json();
    currentGradeLevel = body.grade_level || '';
    currentTestName = body.mode === 'gaokao' ? '高三模拟卷' :
                      body.mode === 'mixed' ? (body.grade_level||'') + '综合卷' : '自定义试卷';
  }
  currentTestQuestions = data.questions;

  document.getElementById('testTitle').textContent = `📄 试卷 (${data.count} 题)`;
  document.getElementById('testPaper').classList.remove('hidden');
  document.getElementById('testResult').classList.add('hidden');
  document.getElementById('submitArea').classList.remove('hidden');

  // 分类：单选题、多选题、非选择题
  const singleQs = data.questions.filter(q => q.qtype === '单选题');
  const multiQs = data.questions.filter(q => q.qtype === '多选题');
  const choiceQs = [...singleQs, ...multiQs];
  const calcQs = data.questions.filter(q => q.qtype !== '单选题' && q.qtype !== '多选题');

  let html = '';

  // 试卷头
  html += `<div style="text-align:center;margin-bottom:20px">
    <h3>${currentTestName}</h3>
    <p class="text-muted">选择题 ${choiceQs.length}题 × 6分 + 非选择题 ${calcQs.length}题</p>
  </div>`;

  // 一、选择题
  if (choiceQs.length > 0) {
    const singleScore = singleQs.length * 6;
    const multiScore = multiQs.length * 6;
    const choiceTotal = singleScore + multiScore;
    html += `<div style="background:#f0f4ff;padding:10px 12px;border-radius:8px;margin-bottom:6px">
      <h3>一、选择题（共${choiceQs.length}题，每题6分，共${choiceTotal}分）</h3>
      <p class="text-muted">单选题 ${singleQs.length}题（第1-${singleQs.length}题）；多选题 ${multiQs.length}题（选对但不全得3分，有选错得0分）。</p>
    </div>`;

    let qNum = 0;
    // 单选题
    singleQs.forEach((q, i) => {
      qNum++;
      const diffBadge = q.difficulty === '易' ? 'badge-easy' : q.difficulty === '中' ? 'badge-mid' : 'badge-hard';
      html += `<div class="question-card" data-qid="${q.id}" data-multi="false">
        <div class="q-header">
          <strong>${qNum}.（单选）</strong>
          <span class="badge ${diffBadge}">${q.difficulty}</span>
          <span class="badge badge-grade">${q.topic_name||''}</span>
        </div>
        <div style="margin-bottom:8px">${escHtml(q.content)}</div>
        ${q.image_path ? `<div style="margin:8px 0"><img src="/images/${q.image_path}" style="max-width:100%;max-height:250px;border-radius:6px;border:1px solid var(--border)" onerror="this.style.display='none'"></div>` : ''}
        <div class="options">`;
      if (q.options && q.options.length) {
        const labels = ['A','B','C','D','E','F'];
        q.options.forEach((opt, j) => {
          html += `<div class="option" data-qid="${q.id}" data-ans="${labels[j]}" onclick="selectOption(this, false)"><strong>${labels[j]}.</strong> ${escHtml(opt)}</div>`;
        });
      }
      html += '</div></div>';
    });
    // 多选题
    multiQs.forEach((q, i) => {
      qNum++;
      const diffBadge = q.difficulty === '易' ? 'badge-easy' : q.difficulty === '中' ? 'badge-mid' : 'badge-hard';
      html += `<div class="question-card" data-qid="${q.id}" data-multi="true">
        <div class="q-header">
          <strong>${qNum}.（多选）</strong>
          <span class="badge badge-mid" style="background:#fefcbf;color:#975a16">多选题</span>
          <span class="badge ${diffBadge}">${q.difficulty}</span>
          <span class="badge badge-grade">${q.topic_name||''}</span>
        </div>
        <div style="margin-bottom:8px">${escHtml(q.content)}</div>
        ${q.image_path ? `<div style="margin:8px 0"><img src="/images/${q.image_path}" style="max-width:100%;max-height:250px;border-radius:6px;border:1px solid var(--border)" onerror="this.style.display='none'"></div>` : ''}
        <div class="options">`;
      if (q.options && q.options.length) {
        const labels = ['A','B','C','D','E','F'];
        q.options.forEach((opt, j) => {
          html += `<div class="option multi-option" data-qid="${q.id}" data-ans="${labels[j]}" onclick="toggleMultiOption(this)"><strong>${labels[j]}.</strong> ${escHtml(opt)}</div>`;
        });
      }
      html += '</div></div>';
    });
  }

  // 二、非选择题
  if (calcQs.length > 0) {
    html += `<div style="background:#fff8f0;padding:10px 12px;border-radius:8px;margin:8px 0 6px">
      <h3>二、非选择题（共${calcQs.length}题）</h3>
      <p class="text-muted">解答应写出必要的文字说明和演算步骤。</p>
    </div>`;

    calcQs.forEach((q, i) => {
      const scoreMap = {易: 8, 中: 12, 难: 16};
      const score = scoreMap[q.difficulty] || 12;
      const typeBadge = q.qtype === '实验题' ? 'badge-experiment' : 'badge-calc';
      const diffBadge = q.difficulty === '易' ? 'badge-easy' : q.difficulty === '中' ? 'badge-mid' : 'badge-hard';
      const subItems = splitSubItems(q.content);
      const firstLine = subItems.length > 0 ? subItems[0] : q.content;
      const restLines = subItems.slice(1).map(s => `<div style="margin-bottom:4px">${escHtml(s)}</div>`).join('');
      html += `<div class="question-card" data-qid="${q.id}">
        <div class="q-header">
          <strong>${i+1}.（${score}分）</strong>
          <span class="badge ${typeBadge}">${q.qtype}</span>
          <span class="badge ${diffBadge}">${q.difficulty}</span>
          <span class="badge badge-grade">${q.topic_name||''}</span>
        </div>
        <div style="margin-bottom:4px">${escHtml(firstLine)}</div>
        ${restLines}
        ${q.image_path ? `<div style="margin:8px 0"><img src="/images/${q.image_path}" style="max-width:100%;max-height:250px;border-radius:6px;border:1px solid var(--border)" onerror="this.style.display='none'"></div>` : ''}
        <input class="answer-input" data-qid="${q.id}" placeholder="请输入答案...">
      </div>`;
    });
  }

  document.getElementById('testQuestions').innerHTML = html;
  document.getElementById('testPaper').scrollIntoView({behavior:'smooth'});
}

function selectOption(el, isMulti) {
  const qid = el.dataset.qid;
  // 单选题：互斥选择
  el.parentElement.querySelectorAll('.option').forEach(o => o.classList.remove('selected'));
  el.classList.add('selected');
}

function toggleMultiOption(el) {
  // 多选题：toggle 选择
  el.classList.toggle('selected');
}

async function submitAnswers() {
  const answers = {};
  const questionIds = currentTestQuestions.map(q => q.id);

  currentTestQuestions.forEach(q => {
    if (q.qtype === '单选题') {
      const selected = document.querySelector(`.option.selected[data-qid="${q.id}"]`);
      answers[q.id] = selected ? selected.dataset.ans : '';
    } else if (q.qtype === '多选题') {
      const selected = document.querySelectorAll(`.option.selected[data-qid="${q.id}"]`);
      answers[q.id] = Array.from(selected).map(o => o.dataset.ans).join('');
    } else {
      const input = document.querySelector(`.answer-input[data-qid="${q.id}"]`);
      answers[q.id] = input ? input.value : '';
    }
  });

  const res = await fetch('/api/answer', {
    method: 'POST',
    body: JSON.stringify({question_ids: questionIds, answers, test_name: '在线测试'})
  });
  const data = await res.json();

  document.getElementById('submitArea').classList.add('hidden');

  let html = `<div class="score-circle"><div class="num">${data.percentage}分</div><div style="font-size:.8em;color:var(--muted)">${data.score}/${data.total}</div></div>`;
  html += '<h3>答题详情</h3>';
  data.results.forEach((r, i) => {
    const partial = r.score > 0 && !r.correct;
    const cls = r.correct ? 'correct' : partial ? 'partial' : 'wrong';
    const icon = r.correct ? '✅' : partial ? '⚠️' : '❌';
    html += `<div class="result-row ${cls}" style="${partial ? 'background:#fffff0;' : ''}">
      <strong>${i+1}.</strong> ${icon}
      ${escHtml(r.content)}
      ${!r.correct ? `<br><span class="text-muted">你的答案: ${escHtml(r.user_answer || '（未作答）')} | 正确答案: ${escHtml(r.correct_answer)}${partial ? ' （+' + r.score + '分）' : ''}</span>` : ''}
      ${r.explanation ? `<br><span class="text-muted">💡 ${escHtml(r.explanation)}</span>` : ''}
    </div>`;
  });

  // 高亮选项
  data.results.forEach(r => {
    if (r.qtype === '选择题') {
      const options = document.querySelectorAll(`.option[data-qid="${r.id}"]`);
      options.forEach(opt => {
        opt.style.pointerEvents = 'none';
        if (opt.dataset.ans === r.correct_answer) opt.classList.add('correct');
        if (opt.dataset.ans === r.user_answer && !r.correct) opt.classList.add('wrong');
      });
    }
  });

  document.getElementById('testResult').innerHTML = html;
  document.getElementById('testResult').classList.remove('hidden');
  loadStats();
}

// ==================== Word 导出 ====================
async function exportDocx(includeAnswer) {
  if (!currentTestQuestions.length) { alert('没有试卷可导出'); return; }
  const body = {
    questions: currentTestQuestions,
    test_name: currentTestName,
    include_answer: includeAnswer,
    grade_level: currentGradeLevel,
  };
  try {
    const res = await fetch('/api/export-docx', {method:'POST', body:JSON.stringify(body)});
    if (!res.ok) { alert('导出失败'); return; }
    const blob = await res.blob();
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = (includeAnswer ? '[含答案]' : '[题目]') + currentTestName + '.docx';
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  } catch(e) { alert('导出失败: ' + e); }
}

// ==================== 添加题目 ====================
let addSelectedTopicId = null;

async function loadAddTopics() {
  const grade = document.getElementById('addGrade').value;
  const res = await fetch('/api/topics?grade_level=' + encodeURIComponent(grade));
  const tree = await res.json();
  let html = '';
  tree.forEach(parent => {
    html += `<div class="topic-item parent" data-id="${parent.id}" onclick="selectAddTopic(${parent.id}, this)">📘 ${parent.name}</div>`;
    parent.children.forEach(child => {
      html += `<div class="topic-item child" data-id="${child.id}" onclick="selectAddTopic(${child.id}, this)">📄 ${child.name}</div>`;
    });
  });
  document.getElementById('addTopicTree').innerHTML = html;
}

function selectAddTopic(id, el) {
  document.querySelectorAll('#addTopicTree .topic-item').forEach(x => x.classList.remove('selected'));
  addSelectedTopicId = id;
  el.classList.add('selected');
}

function onAddTypeChange() {
  const qtype = document.getElementById('addType').value;
  const isChoice = qtype === '单选题' || qtype === '多选题';
  document.getElementById('addOptionsArea').classList.toggle('hidden', !isChoice);
}

async function addQuestion() {
  if (!addSelectedTopicId) { alert('请选择知识点'); return; }
  const content = document.getElementById('addContent').value.trim();
  if (!content) { alert('请输入题目内容'); return; }
  const answer = document.getElementById('addAnswer').value.trim();
  if (!answer) { alert('请输入答案'); return; }

  const qtype = document.getElementById('addType').value;
  let options = [];
  if (qtype === '选择题') {
    const optText = document.getElementById('addOptions').value.trim();
    options = optText.split('\n').filter(x => x.trim());
  }

  const body = {
    topic_id: addSelectedTopicId,
    qtype,
    difficulty: document.getElementById('addDiff').value,
    content,
    options,
    answer,
    explanation: document.getElementById('addExplanation').value.trim(),
    image_path: document.getElementById('addImagePath').value,
  };

  const res = await fetch('/api/questions/add', {method:'POST',body:JSON.stringify(body)});
  const data = await res.json();
  document.getElementById('addMsg').textContent = '✅ 添加成功！ID: ' + data.id;
  document.getElementById('addContent').value = '';
  document.getElementById('addOptions').value = '';
  document.getElementById('addAnswer').value = '';
  document.getElementById('addExplanation').value = '';
  document.getElementById('addImageFile').value = '';
  document.getElementById('addImagePath').value = '';
  document.getElementById('addImagePreview').classList.add('hidden');
  document.getElementById('addImagePreview').innerHTML = '';
  loadStats();
}

// ==================== 图片上传 ====================
async function previewAddImage() {
  const file = document.getElementById('addImageFile').files[0];
  if (!file) return;
  if (file.size > 5 * 1024 * 1024) { alert('图片不能超过5MB'); return; }
  // 预览
  const reader = new FileReader();
  reader.onload = function(e) {
    document.getElementById('addImagePreview').innerHTML =
      `<img src="${e.target.result}" style="max-width:200px;max-height:150px;border-radius:6px;border:1px solid var(--border)">`;
    document.getElementById('addImagePreview').classList.remove('hidden');
  };
  reader.readAsDataURL(file);
  // 上传
  const base64 = await new Promise(resolve => {
    const r = new FileReader();
    r.onload = e => resolve(e.target.result);
    r.readAsDataURL(file);
  });
  try {
    const res = await fetch('/api/upload-image', {method:'POST',body:JSON.stringify({data: base64})});
    const data = await res.json();
    if (data.filename) {
      document.getElementById('addImagePath').value = data.filename;
      document.getElementById('addMsg').textContent = '🖼️ 图片已上传';
    }
  } catch(e) {
    console.error('图片上传失败:', e);
  }
}

document.getElementById('addGrade').addEventListener('change', loadAddTopics);

// ==================== 答题记录 ====================
async function loadRecords() {
  const res = await fetch('/api/records');
  const records = await res.json();
  if (!records.length) {
    document.getElementById('recordsList').innerHTML = '<p class="text-muted">暂无答题记录</p>';
    return;
  }
  let html = '';
  records.forEach(r => {
    const pct = r.total > 0 ? (r.score / r.total * 100).toFixed(1) : '0';
    html += `<div style="padding:10px 0;border-bottom:1px solid var(--border)">
      <strong>${escHtml(r.test_name)}</strong>
      <span class="text-muted">${r.created_at}</span><br>
      得分: <strong>${r.score}/${r.total}</strong> (${pct}分)
    </div>`;
  });
  document.getElementById('recordsList').innerHTML = html;
}

// ==================== 工具函数 ====================
function escHtml(s) {
  if (!s) return '';
  return s.replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');
}

// ==================== 初始化 ====================
loadStats();
loadTopics();
loadAddTopics();
</script>
</body>
</html>"""


class ReusableHTTPServer(HTTPServer):
    """支持端口复用的 HTTP 服务器"""
    allow_reuse_address = True

    def server_bind(self):
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        super().server_bind()


def main():
    print("""
╔══════════════════════════════════════════════════╗
║     🎓 高中物理题库系统 - Web 版                ║
║     高一高二 · 基础夯实 | 高三 · 冲刺高考         ║
╚══════════════════════════════════════════════════╝
""")
    APIHandler.init_app()

    try:
        server = ReusableHTTPServer(("0.0.0.0", PORT), APIHandler)
    except OSError:
        print(f"  ❌ 端口 {PORT} 被占用，正在尝试释放...")
        subprocess.run(f"lsof -ti :{PORT} | xargs kill -9", shell=True,
                       capture_output=True)
        import time
        time.sleep(0.5)
        try:
            server = ReusableHTTPServer(("0.0.0.0", PORT), APIHandler)
        except OSError:
            print(f"  ❌ 无法启动，端口 {PORT} 仍被占用。请手动检查。")
            print(f"  运行: lsof -i :{PORT} 查看占用进程")
            APIHandler.db.close()
            sys.exit(1)

    print(f"  ✅ 服务已启动！")
    print(f"  🌐 在浏览器打开: http://localhost:{PORT}")
    print(f"  ⏹  按 Ctrl+C 停止服务\n")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n  已停止服务。再见！")
        server.server_close()
        APIHandler.db.close()


if __name__ == "__main__":
    main()
