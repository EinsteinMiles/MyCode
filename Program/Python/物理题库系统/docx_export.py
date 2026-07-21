"""高中物理题库系统 - Word 文档导出器（全国卷物理试卷模板）

纯 Python 标准库实现，数值和单位自动使用 Word 公式（OMML）排版。
"""

import zipfile
import re
import io
from xml.sax.saxutils import escape as xml_escape
from datetime import datetime

# ========== 上标/下标映射 ==========
SUPER_MAP = str.maketrans(
    "⁰¹²³⁴⁵⁶⁷⁸⁹⁺⁻⁼⁽⁾ⁿ",
    "0123456789+-=()n"
)
SUB_MAP = str.maketrans(
    "₀₁₂₃₄₅₆₇₈₉₊₋₌₍₎",
    "0123456789+-=()"
)
SUPER_CHARS = set("⁰¹²³⁴⁵⁶⁷⁸⁹⁺⁻⁼⁽⁾ⁿ")
SUB_CHARS = set("₀₁₂₃₄₅₆₇₈₉₊₋₌₍₎")

OMML_NS = "http://schemas.openxmlformats.org/officeDocument/2006/math"

_CONTENT_TYPES = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
  <Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
  <Default Extension="xml" ContentType="application/xml"/>
  <Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>
</Types>"""

_RELS = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/>
</Relationships>"""

_DOC_RELS = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
</Relationships>"""


def _to_omml(text: str) -> str:
    """将含上标/下标/单位的文本转换为 OMML 公式 XML"""
    # 先处理 superscript runs
    result = []
    i = 0
    while i < len(text):
        ch = text[i]
        if ch in SUPER_CHARS:
            base = ""
            sup = ""
            # 收集连续的上标字符
            while i < len(text) and text[i] in SUPER_CHARS:
                sup += text[i].translate(SUPER_MAP)
                i += 1
            result.append(f'<m:sup><m:e><m:r><m:t>{xml_escape(base or " ")}</m:t></m:r></m:e>'
                          f'<m:sup><m:r><m:t>{xml_escape(sup)}</m:t></m:r></m:sup></m:sup>')
        elif ch in SUB_CHARS:
            sub = ""
            while i < len(text) and text[i] in SUB_CHARS:
                sub += text[i].translate(SUB_MAP)
                i += 1
            result.append(f'<m:sub><m:e><m:r><m:t> </m:t></m:r></m:e>'
                          f'<m:sub><m:r><m:t>{xml_escape(sub)}</m:t></m:r></m:sub></m:sub>')
        else:
            result.append(xml_escape(ch))
            i += 1
    return "".join(result)


def _is_formula_text(text: str) -> bool:
    """判断文本片段是否应渲染为公式"""
    if SUPER_CHARS & set(text) or SUB_CHARS & set(text):
        return True
    # 数字+物理单位模式
    return bool(re.search(r'\d+\s*[A-Za-z/²³¹⁰⁴⁵⁶⁷⁸⁹⁺⁻·]+', text))


def _split_formula_spans(text: str) -> list[tuple[str, bool]]:
    """将文本拆分为 [ (文本, 是否公式), ... ]"""
    pattern = re.compile(
        r'('
        r'\d+\.?\d*\s*×\s*10\s*[⁰¹²³⁴⁵⁶⁷⁸⁹⁺⁻]+\s*[A-Za-z/²³·]+'  # 2×10⁻⁵ C
        r'|'
        r'\d+\.?\d*\s*[A-Za-z/²³⁰¹⁴⁵⁶⁷⁸⁹⁺⁻·]+\s*(?:[A-Za-z/²³]+)?'  # 10 m/s², 5 kg
        r'|'
        r'[A-Za-z]\s*=\s*\d+\.?\d*\s*[A-Za-z/²³]*'  # g=10 m/s²
        r'|'
        r'[\d.]+[⁰¹²³⁴⁵⁶⁷⁸⁹⁺⁻]+'  # 纯上标
        r')'
    )
    spans = []
    last_end = 0
    for m in pattern.finditer(text):
        start, end = m.start(), m.end()
        if start > last_end:
            spans.append((text[last_end:start], False))
        spans.append((text[start:end], True))
        last_end = end
    if last_end < len(text):
        spans.append((text[last_end:], False))
    # 合并相邻同类
    merged = []
    for txt, is_f in spans:
        if merged and merged[-1][1] == is_f:
            merged[-1] = (merged[-1][0] + txt, is_f)
        else:
            merged.append((txt, is_f))
    return merged if merged else [(text, False)]


class DocxBuilder:
    """构建 .docx 文档，支持 OMML 公式"""

    def __init__(self):
        self._body_parts = []
        self._page_break = '  <w:p><w:r><w:br w:type="page"/></w:r></w:p>'

    def _r(self, text: str, bold: bool = False, font_size: int = 22,
           font_name: str = "宋体"):
        """普通文字 run"""
        return (
            f'<w:r><w:rPr>'
            f'<w:rFonts w:eastAsia="{font_name}" w:ascii="{font_name}" w:hAnsi="{font_name}"/>'
            f'<w:sz w:val="{font_size}"/>'
            f'{"<w:b/>" if bold else ""}'
            f'</w:rPr><w:t xml:space="preserve">{xml_escape(text)}</w:t></w:r>'
        )

    def _omml_r(self, text: str):
        """公式内文字 run"""
        return f'<m:r><m:t>{xml_escape(text)}</m:t></m:r>'

    def _omml_fragment(self, text: str) -> str:
        """将含上标下标的文本转为 OMML 片段，普通文字用 <m:r> 包裹"""
        parts = []
        buf = ""
        i = 0
        while i < len(text):
            ch = text[i]
            if ch in SUPER_CHARS:
                if buf:
                    parts.append(f'<m:r><m:t>{xml_escape(buf)}</m:t></m:r>')
                    buf = ""
                sup_chars = ""
                while i < len(text) and text[i] in SUPER_CHARS:
                    sup_chars += text[i].translate(SUPER_MAP)
                    i += 1
                parts.append(
                    f'<m:sup><m:e><m:r><m:t> </m:t></m:r></m:e>'
                    f'<m:sup><m:r><m:t>{xml_escape(sup_chars)}</m:t></m:r></m:sup>'
                    f'</m:sup>'
                )
            elif ch in SUB_CHARS:
                if buf:
                    parts.append(f'<m:r><m:t>{xml_escape(buf)}</m:t></m:r>')
                    buf = ""
                sub_chars = ""
                while i < len(text) and text[i] in SUB_CHARS:
                    sub_chars += text[i].translate(SUB_MAP)
                    i += 1
                parts.append(
                    f'<m:sub><m:e><m:r><m:t> </m:t></m:r></m:e>'
                    f'<m:sub><m:r><m:t>{xml_escape(sub_chars)}</m:t></m:r></m:sub>'
                    f'</m:sub>'
                )
            else:
                buf += ch
                i += 1
        if buf:
            parts.append(f'<m:r><m:t>{xml_escape(buf)}</m:t></m:r>')
        return "".join(parts)

    def _p_mixed(self, segments: list[tuple[str, bool]], bold: bool = False,
                 font_size: int = 22, font_name: str = "宋体",
                 alignment: str = "left", spacing_after: int = 60,
                 spacing_before: int = 0, indent_left: int = 0):
        """混合文本+公式的段落"""
        align_val = {"left": "left", "center": "center", "right": "right"}.get(alignment, "left")
        indent = ""
        if indent_left:
            indent = f'<w:ind w:left="{indent_left}"/>'

        runs = []
        for text, is_formula in segments:
            if not text:
                continue
            if is_formula:
                omml = self._omml_fragment(text)
                if omml:
                    runs.append(
                        f'<m:oMath>{omml}</m:oMath>'
                    )
            else:
                runs.append(self._r(text, bold=bold, font_size=font_size,
                                    font_name=font_name))

        p = f"""  <w:p>
    <w:pPr>
      <w:jc w:val="{align_val}"/>
      <w:spacing w:before="{spacing_before}" w:after="{spacing_after}" w:line="360" w:lineRule="auto"/>
      {indent}
    </w:pPr>
    {"".join(runs)}
  </w:p>"""
        self._body_parts.append(p)

    def p_text(self, text: str, bold: bool = False, font_size: int = 22,
               font_name: str = "宋体", alignment: str = "left",
               spacing_after: int = 60, spacing_before: int = 0,
               indent_left: int = 0):
        """添加段落，自动处理公式"""
        if _is_formula_text(text):
            segs = _split_formula_spans(text)
            self._p_mixed(segs, bold=bold, font_size=font_size, font_name=font_name,
                          alignment=alignment, spacing_after=spacing_after,
                          spacing_before=spacing_before, indent_left=indent_left)
        else:
            # 纯文本，简单段落
            self._p_mixed([(text, False)], bold=bold, font_size=font_size,
                          font_name=font_name, alignment=alignment,
                          spacing_after=spacing_after, spacing_before=spacing_before,
                          indent_left=indent_left)

    def p_empty(self, spacing_after: int = 40):
        """空行（留答题空间）"""
        self._body_parts.append(
            f'  <w:p><w:pPr><w:spacing w:after="{spacing_after}"/>'
            f'</w:pPr></w:p>'
        )

    def add_page_break(self):
        self._body_parts.append(self._page_break)

    def add_table(self, rows: list[list[str]], col_widths: list[int] = None):
        if not rows:
            return
        ncols = len(rows[0])
        widths = col_widths or [2250] * ncols
        table = ['  <w:tbl>']
        table.append('    <w:tblPr><w:tblW w:w="9000" w:type="dxa"/>'
                     '<w:tblBorders><w:top w:val="single" w:sz="4"/>'
                     '<w:left w:val="single" w:sz="4"/>'
                     '<w:bottom w:val="single" w:sz="4"/>'
                     '<w:right w:val="single" w:sz="4"/>'
                     '</w:tblBorders></w:tblPr>')
        table.append('    <w:tblGrid>')
        for w in widths:
            table.append(f'      <w:gridCol w:w="{w}"/>')
        table.append('    </w:tblGrid>')
        for row in rows:
            table.append('    <w:tr>')
            for j, cell in enumerate(row):
                w = widths[j] if j < len(widths) else 2250
                table.append(f'      <w:tc><w:tcPr><w:tcW w:w="{w}" w:type="dxa"/>'
                             f'</w:tcPr><w:p><w:r><w:rPr>'
                             f'<w:rFonts w:eastAsia="宋体" w:ascii="宋体"/>'
                             f'<w:sz w:val="20"/></w:rPr>'
                             f'<w:t xml:space="preserve">{xml_escape(str(cell))}</w:t>'
                             f'</w:r></w:p></w:tc>')
            table.append('    </w:tr>')
        table.append('  </w:tbl>')
        self._body_parts.append("\n".join(table))

    def build(self, filepath: str):
        document_xml = self._build_document_xml()
        with zipfile.ZipFile(filepath, "w", zipfile.ZIP_DEFLATED) as zf:
            zf.writestr("[Content_Types].xml", _CONTENT_TYPES.encode())
            zf.writestr("_rels/.rels", _RELS.encode())
            zf.writestr("word/_rels/document.xml.rels", _DOC_RELS.encode())
            zf.writestr("word/document.xml", document_xml.encode("utf-8"))

    def build_bytes(self) -> bytes:
        document_xml = self._build_document_xml()
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
            zf.writestr("[Content_Types].xml", _CONTENT_TYPES.encode())
            zf.writestr("_rels/.rels", _RELS.encode())
            zf.writestr("word/_rels/document.xml.rels", _DOC_RELS.encode())
            zf.writestr("word/document.xml", document_xml.encode("utf-8"))
        return buf.getvalue()

    def _build_document_xml(self) -> str:
        body = "\n".join(self._body_parts)
        return f"""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"
            xmlns:m="{OMML_NS}"
            xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">
  <w:body>
{body}
  </w:body>
</w:document>"""


# ========== 全国卷构建器 ==========

class GaoKaoPaperBuilder:

    def __init__(self):
        self.doc = DocxBuilder()

    def build_paper(self, questions: list, test_name: str = "物理模拟试卷",
                    include_answer: bool = False, grade_level: str = ""):
        self._build_header(test_name, grade_level)
        self._build_score_table()

        single_qs = [q for q in questions if _get(q, "qtype") == "单选题"]
        multi_qs = [q for q in questions if _get(q, "qtype") == "多选题"]
        calc_qs = [q for q in questions if _get(q, "qtype") not in ("单选题", "多选题")]

        self._build_choice_section(single_qs, multi_qs, include_answer)
        self.doc.add_page_break()
        self._build_calc_section(calc_qs, include_answer)

        if include_answer:
            self.doc.add_page_break()
            self._build_answer_section(questions)

        return self.doc

    def _build_header(self, test_name, grade_level):
        self.doc.p_text("姓名：__________  班级：__________  得分：__________",
                         font_size=18, alignment="center", spacing_after=60)
        self.doc.p_text("（密封线内不要答题）", font_size=16, alignment="center",
                         spacing_after=120)
        self.doc.p_text(test_name, bold=True, font_size=32, alignment="center",
                         spacing_after=60, font_name="黑体")
        subtitle = f"物理（{grade_level}）" if grade_level else "物理"
        self.doc.p_text(subtitle, bold=True, font_size=28, alignment="center",
                         spacing_after=120, font_name="黑体")
        now = datetime.now().strftime("%Y-%m-%d")
        self.doc.p_text(
            f"考试时间：{now}    满分：100分    考试时长：60分钟",
            font_size=20, alignment="center", spacing_after=160
        )

    def _build_score_table(self):
        self.doc.p_text("得分表", bold=True, font_size=22, alignment="center",
                         spacing_after=60)
        self.doc.add_table([
            ["题型", "选择题", "非选择题", "总分"],
            ["分值", "", "", ""],
            ["得分", "", "", ""],
        ])
        self.doc.p_empty(spacing_after=60)

    def _build_choice_section(self, single_qs, multi_qs, include_answer):
        total = len(single_qs) + len(multi_qs)
        choice_total = total * 6

        inst = (f"一、选择题：本题共{total}小题，每小题6分，共{choice_total}分。")
        if single_qs and multi_qs:
            inst += (f"第1—{len(single_qs)}题只有一项符合题目要求；"
                     f"第{len(single_qs)+1}—{total}题有多项符合题目要求。"
                     f"全部选对的得6分，选对但不全的得3分，有选错的得0分。")
        elif single_qs:
            inst += "每小题只有一个选项符合题目要求。"

        self.doc.p_text(inst, font_size=21, spacing_after=80)

        idx = 0
        for q in single_qs:
            idx += 1
            self._write_choice_q(idx, q, False, include_answer)
        for q in multi_qs:
            idx += 1
            self._write_choice_q(idx, q, True, include_answer)

    def _write_choice_q(self, idx, q, is_multi, include_answer):
        content = _get(q, "content")
        options = _get(q, "options", [])
        answer = _get(q, "answer")
        explanation = _get(q, "explanation")
        tag = "（多选）" if is_multi else ""

        self.doc.p_text(f"{idx}.{tag} {content}", font_size=22, spacing_after=30)

        if options:
            labels = "ABCDEF"
            for j, opt in enumerate(options):
                if j < len(labels):
                    self.doc.p_text(f"    {labels[j]}. {opt}", font_size=22,
                                    spacing_after=15)

        if include_answer:
            self.doc.p_text(f"    【答案】{answer}", bold=True, font_size=21,
                            spacing_after=30)
            if explanation:
                self.doc.p_text(f"    【解析】{explanation}", font_size=20,
                                spacing_after=40)

    def _build_calc_section(self, calc_qs, include_answer):
        if not calc_qs:
            return

        total_score = sum(
            {"易": 8, "中": 12, "难": 16}.get(_get(q, "difficulty", "中"), 12)
            for q in calc_qs
        )
        self.doc.p_text(
            f"二、非选择题：本题共{len(calc_qs)}小题，共{total_score}分。"
            f"解答应写出必要的文字说明、方程式和重要演算步骤。",
            font_size=21, spacing_after=120
        )

        for i, q in enumerate(calc_qs, 1):
            content = _get(q, "content")
            answer = _get(q, "answer")
            explanation = _get(q, "explanation")
            difficulty = _get(q, "difficulty", "中")
            score = {"易": 8, "中": 12, "难": 16}.get(difficulty, 12)

            # 小问拆行
            sub_items = _split_calc_items(content)
            first = sub_items[0] if sub_items else content
            self.doc.p_text(f"{i}.（{score}分）{first}", bold=True, font_size=22,
                            spacing_after=30)
            for sub in sub_items[1:]:
                self.doc.p_text(sub, font_size=22, spacing_after=30)

            if not include_answer:
                for _ in range(4):
                    self.doc.p_empty(spacing_after=30)
            else:
                self.doc.p_text(f"    【答案】{answer}", bold=True, font_size=21,
                                spacing_after=30)
                if explanation:
                    self.doc.p_text(f"    【解析】{explanation}", font_size=20,
                                    spacing_after=50)

    def _build_answer_section(self, questions):
        self.doc.p_text("参考答案", bold=True, font_size=32, alignment="center",
                         spacing_after=160, font_name="黑体")

        choice_qs = [q for q in questions if _get(q, "qtype") in ("单选题", "多选题")]
        calc_qs = [q for q in questions if _get(q, "qtype") not in ("单选题", "多选题")]

        if choice_qs:
            self.doc.p_text("一、选择题", bold=True, font_size=24, spacing_after=80,
                            font_name="黑体")
            for i, q in enumerate(choice_qs, 1):
                answer = _get(q, "answer")
                explanation = _get(q, "explanation")
                tag = "（多选）" if _get(q, "qtype") == "多选题" else ""
                line = f"{i}.{tag} {answer}"
                if explanation:
                    line += f"    {explanation}"
                self.doc.p_text(line, font_size=21, spacing_after=40)

        if calc_qs:
            self.doc.p_text("二、非选择题", bold=True, font_size=24, spacing_after=80,
                            font_name="黑体")
            for i, q in enumerate(calc_qs, 1):
                answer = _get(q, "answer")
                explanation = _get(q, "explanation")
                self.doc.p_text(f"{i}. {answer}", font_size=21, spacing_after=30)
                if explanation:
                    self.doc.p_text(f"    {explanation}", font_size=20,
                                    spacing_after=50)


# ========== 工具函数 ==========

def _split_calc_items(text: str) -> list[str]:
    """将计算题小问拆行"""
    parts = re.split(r'(?=（\d+）)|(?=\(\d+\))|(?=[①②③④⑤⑥])', text)
    return [p.strip() for p in parts if p.strip()]


def _get(q, key, default=""):
    if isinstance(q, dict):
        val = q.get(key, default)
        return val if val is not None else default
    val = getattr(q, key, None)
    return val if val is not None else default


# ========== 公开导出函数 ==========

def export_test_to_docx(questions: list, filepath: str,
                        test_name: str = "物理模拟试卷",
                        include_answer: bool = False,
                        grade_level: str = "") -> str:
    builder = GaoKaoPaperBuilder()
    doc = builder.build_paper(questions=questions, test_name=test_name,
                              include_answer=include_answer,
                              grade_level=grade_level)
    doc.build(filepath)
    return filepath


def export_test_to_docx_bytes(questions: list, test_name: str = "物理模拟试卷",
                              include_answer: bool = False,
                              grade_level: str = "") -> bytes:
    builder = GaoKaoPaperBuilder()
    doc = builder.build_paper(questions=questions, test_name=test_name,
                              include_answer=include_answer,
                              grade_level=grade_level)
    return doc.build_bytes()
