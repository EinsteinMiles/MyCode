#!/usr/bin/env python3
"""生成使用说明 PDF"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from fpdf import FPDF
from datetime import datetime


class ManualBuilder(FPDF):
    """使用说明 PDF 生成器"""

    def __init__(self):
        super().__init__('P', 'mm', 'A4')
        self._setup_fonts()
        self.set_auto_page_break(True, 20)

    def _setup_fonts(self):
        font_paths = [
            '/System/Library/Fonts/STHeiti Light.ttc',
            '/System/Library/Fonts/PingFang.ttc',
            '/Library/Fonts/Arial Unicode.ttf',
        ]
        for fp in font_paths:
            if os.path.exists(fp):
                self.add_font('CN', '', fp, uni=True)
                self.add_font('CN', 'B', fp, uni=True)
                break
        else:
            self.add_font('CN', '', '/System/Library/Fonts/STHeiti Light.ttc', uni=True)
            self.add_font('CN', 'B', '/System/Library/Fonts/STHeiti Light.ttc', uni=True)

    # === 排版辅助 ===

    def cover_page(self):
        """封面"""
        self.add_page()
        self.ln(55)
        self.set_font('CN', 'B', 36)
        self.set_text_color(44, 62, 80)
        self.cell(0, 16, '数据处理工具', align='C', ln=True)
        self.ln(4)
        self.set_font('CN', '', 22)
        self.set_text_color(52, 152, 219)
        self.cell(0, 12, '使用说明', align='C', ln=True)

        self.ln(12)
        self.set_draw_color(52, 152, 219)
        self.set_line_width(0.8)
        self.line(50, self.get_y(), self.w - 50, self.get_y())
        self.ln(16)

        self.set_font('CN', '', 13)
        self.set_text_color(127, 140, 141)
        features = [
            'Excel · CSV · JSON · TXT · DOCX 多格式支持',
            '读取 合并 拆分 透视 筛选 排序 匹配 清洗',
            '数据可视化 (静态 + 交互式)',
            '数据分析报告 (文本 / HTML / PDF)',
            '批量处理 + 大文件分块读取',
        ]
        for f in features:
            self.cell(0, 11, f, align='C', ln=True)

        self.ln(20)
        self.set_font('CN', '', 11)
        self.set_text_color(149, 165, 166)
        self.cell(0, 8, f'版本 1.0  |  {datetime.now().strftime("%Y年%m月%d日")}', align='C', ln=True)
        self.cell(0, 8, '运行: python main.py', align='C', ln=True)

    def toc_page(self):
        """目录"""
        self.add_page()
        self._section_title('目  录', level=0)
        self.ln(6)

        toc = [
            ('一、快速开始', '环境要求、启动方式'),
            ('二、文件读取', '支持格式、读取方式、预览'),
            ('三、数据操作', '筛选排序、合并拆分、透视聚合、查找匹配'),
            ('四、数据清洗', '缺失值、异常值、标准化'),
            ('五、数据可视化', '静态图表、交互式图表、仪表板'),
            ('六、数据分析', '描述统计、相关性、报告生成'),
            ('七、PDF 导出', '数据表导出、分析报告导出'),
            ('八、批量处理', '多文件批处理'),
            ('九、常用技巧', '编码处理、大文件、列操作'),
        ]
        self.set_font('CN', '', 12)
        for title, desc in toc:
            self.set_font('CN', 'B', 12)
            self.set_text_color(44, 62, 80)
            self.cell(0, 10, title, ln=True)
            self.set_font('CN', '', 11)
            self.set_text_color(127, 140, 141)
            self.cell(0, 7, f'    {desc}', ln=True)

    # === 内容方法 ===

    def _section_title(self, title, level=1):
        if level == 0:
            self.set_font('CN', 'B', 22)
            self.set_text_color(44, 62, 80)
            self.cell(0, 14, title, align='C', ln=True)
            self.set_draw_color(52, 152, 219)
            self.set_line_width(0.5)
            self.line(70, self.get_y() + 2, self.w - 70, self.get_y() + 2)
            self.ln(10)
        elif level == 1:
            self.set_font('CN', 'B', 16)
            self.set_text_color(44, 62, 80)
            self.cell(0, 10, title, ln=True)
            self.set_draw_color(52, 152, 219)
            self.line(10, self.get_y() + 1, self.w - 10, self.get_y() + 1)
            self.ln(6)
        elif level == 2:
            self.set_font('CN', 'B', 12)
            self.set_text_color(52, 73, 94)
            self.cell(0, 8, title, ln=True)
            self.ln(2)

    def _body(self, text, indent=0):
        self.set_font('CN', '', 10.5)
        self.set_text_color(51, 51, 51)
        x = 10 + indent * 8
        self.set_x(x)
        self.multi_cell(self.w - x - 10, 6.5, text, align='L')
        self.ln(1)

    def _bullet(self, text, indent=1):
        self.set_font('CN', '', 10.5)
        self.set_text_color(51, 51, 51)
        x = 10 + indent * 8
        self.set_x(x)
        self.cell(5, 6.5, '•')
        self.multi_cell(self.w - x - 15, 6.5, text)
        self.ln(0.5)

    def _code(self, text, indent=2):
        self.set_font('CN', '', 9)
        self.set_text_color(231, 76, 60)
        self.set_fill_color(250, 250, 252)
        x = 10 + indent * 8
        y = self.get_y()
        lines = text.split('\n')
        block_h = len(lines) * 5.5 + 4
        if y + block_h > self.h - 25:
            self.add_page()
            y = self.get_y()
        self.rect(x - 2, y, self.w - 2 * x + 4, block_h, 'FD')
        self.set_xy(x, y + 2)
        for line in lines:
            self.cell(0, 5.5, line, new_x="LMARGIN", new_y="NEXT")
            self.set_x(x)
        self.set_text_color(51, 51, 51)
        self.set_font('CN', '', 10.5)
        self.ln(3)

    def _tip(self, text):
        self.set_fill_color(235, 245, 251)
        self.set_text_color(41, 128, 185)
        self.set_font('CN', '', 9.5)
        x = 15
        y = self.get_y()
        # 计算高度
        self.set_x(x)
        self.multi_cell(self.w - 30, 5.5, f'💡 提示: {text}', fill=True)
        self.set_text_color(51, 51, 51)
        self.ln(2)

    def _warn(self, text):
        self.set_fill_color(254, 245, 231)
        self.set_text_color(230, 126, 34)
        self.set_font('CN', '', 9.5)
        x = 15
        self.set_x(x)
        self.multi_cell(self.w - 30, 5.5, f'⚠ 注意: {text}', fill=True)
        self.set_text_color(51, 51, 51)
        self.ln(2)

    def _table(self, headers, rows, col_widths=None):
        """简单表格"""
        n = len(headers)
        if col_widths is None:
            col_widths = [(self.w - 20) / n] * n

        # 表头
        self.set_font('CN', 'B', 9)
        self.set_fill_color(52, 73, 94)
        self.set_text_color(255, 255, 255)
        for i, h in enumerate(headers):
            self.cell(col_widths[i], 8, h, border=1, fill=True, align='C')
        self.ln()

        # 行
        self.set_font('CN', '', 9)
        self.set_text_color(51, 51, 51)
        for ri, row in enumerate(rows):
            if ri % 2 == 0:
                self.set_fill_color(245, 247, 250)
            else:
                self.set_fill_color(255, 255, 255)
            for i, cell in enumerate(row):
                self.cell(col_widths[i], 7, str(cell)[:40], border=1, fill=True, align='C')
            self.ln()
        self.ln(4)

    # ================================================================

    def ch_quickstart(self):
        self.add_page()
        self._section_title('一、快速开始')
        self.ln(2)

        self._section_title('1.1 环境要求', level=2)
        self._bullet('Python 3.10 或以上')
        self._bullet('已安装依赖：pip install -r requirements.txt')
        self._bullet('macOS / Windows / Linux 均可')
        self.ln(4)

        self._section_title('1.2 启动', level=2)
        self._body('在终端中进入项目目录，运行:')
        self._code('cd 数据处理/\npython main.py')
        self._body('启动后显示主菜单，输入数字选择功能，按 0 返回上级或退出。')
        self._body('所有操作都基于"当前数据"。首先需要用菜单 1 读取文件，然后才能进行后续的数据操作、清洗、分析和可视化。')
        self._tip('程序运行期间，当前数据保留在内存中，可以连续执行多种操作，无需重复读文件。')

    def ch_read(self):
        self.add_page()
        self._section_title('二、文件读取')

        self._section_title('2.1 支持的格式', level=2)
        self._table(
            ['格式', '扩展名', '说明'],
            [
                ['Excel (新版)', '.xlsx', 'openpyxl 引擎'],
                ['Excel (旧版)', '.xls', 'xlrd 引擎，读取'],
                ['CSV', '.csv', '逗号分隔，自动检测编码'],
                ['TSV', '.tsv', '制表符分隔'],
                ['JSON', '.json', '自动识别数组/嵌套结构'],
                ['文本', '.txt', '按行或分隔符读取'],
                ['Word', '.docx', '提取表格和段落文本'],
            ],
            [45, 30, 105]
        )

        self._section_title('2.2 读取方式', level=2)
        self._body('菜单 1-1【读取单个文件】: 输入文件路径即可。Excel 文件会提示输入工作表名。')
        self._body('菜单 1-2【批量读取+合并】: 指定目录和扩展名，自动将所有匹配文件纵向合并为一个表，并添加 _source_file 列标记来源。')
        self._body('菜单 1-3【分块读取大文件】: 将大文件分成多块逐块读取再合并，避免内存溢出。可自定义每块行数。')
        self._body('菜单 1-4【扫描目录找文件】: 查看目录下有哪些数据文件及大小、修改时间。')
        self.ln(2)

        self._section_title('2.3 数据预览与导出', level=2)
        self._body('菜单 1-6 预览前 N 行数据；菜单 1-7 查看每列的名称、类型、缺失数、唯一值数。')
        self._body('菜单 1-5 将当前数据导出为 Excel/CSV/JSON 等格式，文件保存在 output/ 目录。')
        self._tip('CSV 文件编码自动检测支持 UTF-8、GBK、GB2312 等中文编码。')

    def ch_operations(self):
        self.add_page()
        self._section_title('三、数据操作')

        self._section_title('3.1 筛选与排序', level=2)
        self._body('筛选支持 11 种运算符：==、!=、>、>=、<、<=、contains、startswith、endswith、between、isnull、notnull。')
        self._body('条件筛选示例：选择列"年龄"，运算符">"，值"25" → 筛选出年龄大于25的行。')
        self._body('列表筛选：输入逗号分隔的值列表，可选择"包含"或"排除"模式。')
        self._body('Top N：按某列数值取最大/最小的前 N 条。')
        self._body('排序：支持多列排序，可分别指定每列的升/降序方向。')
        self._body('去重：按指定列（或全部列）删除重复行。')
        self.ln(2)

        self._section_title('3.2 合并与拆分', level=2)
        self._body('行合并（菜单 2-8）: 将另一个文件的数据追加到当前数据下方，相当于 SQL UNION ALL。')
        self._body('键合并（菜单 2-7）: 类似 SQL JOIN 或 Excel VLOOKUP。支持 left/right/inner/outer 四种方式，支持单键或多键关联。左右表键名不同时也可分别指定。')
        self._body('列操作（菜单 2-6）: 选择/删除列、重命名、添加计算列（支持 df 表达式）、类型转换（int/float/str/datetime/category）、列重排序。')
        self._body('拆分（菜单 2-9）: 三种方式——按某列的不同值拆分、按行数均匀拆分、按数值区间拆分。拆分结果自动保存到 output/ 目录。')
        self.ln(2)

        self._section_title('3.3 透视与聚合', level=2)
        self._body('数据透视表（菜单 2-10）: 指定行标签、列标签（可选）、值列和聚合函数，生成透视表。')
        self._body('分组聚合（菜单 2-11）: 按列分组，对多列分别应用不同聚合函数（sum/mean/count/min/max/median/std）。')
        self._body('交叉表（菜单 2-12）: 统计两个分类变量的频数分布。')
        self.ln(2)

        self._section_title('3.4 查找与匹配', level=2)
        self._body('VLOOKUP（菜单 2-13）: 从另一文件按关联键查找并取回指定列，支持 left=保留所有 / inner=仅匹配。')
        self._body('模糊匹配（菜单 2-14）: 按关键词在指定列中搜索包含该词的记录。')
        self._body('范围查找（菜单 2-15）: 将数值列按区间分段，添加分类标签（如 0-60→不及格, 60-80→良好, 80-100→优秀）。')

    def ch_cleaning(self):
        self.add_page()
        self._section_title('四、数据清洗')

        self._section_title('4.1 缺失值处理', level=2)
        self._body('查看报告（菜单 3-1）: 显示每列的缺失数、缺失率、数据类型。')
        self._body('自动处理（菜单 3-2 auto 模式）: 缺失率>50%的列自动删除；数值列用中位数填充；文本列用众数填充。')
        self._body('手动填充（菜单 3-3）: 支持前向填充(ffill)、后向填充(bfill)、均值、中位数、众数、零值、插值7种方法。')
        self._warn('drop 模式会删除含缺失值的整行，慎用。建议先查看缺失报告再选择策略。')
        self.ln(2)

        self._section_title('4.2 异常值处理', level=2)
        self._body('检测方法（菜单 3-4）: IQR法（默认，Q1-1.5×IQR 到 Q3+1.5×IQR）、Z-Score法（|z|>3）、百分位法（排除1%-99%外）。')
        self._body('移除异常值（菜单 3-5）: 对指定数值列检测并移除异常值行。')
        self.ln(2)

        self._section_title('4.3 其他清洗', level=2)
        self._body('删除重复行（菜单 3-6）: 按指定列去重。')
        self._body('清理列名和空白（菜单 3-7）: 自动清理列名中的换行/全角空格，去除文本列前后空白。')
        self.ln(2)

        self._section_title('4.4 标准化与变换', level=2)
        self._body('Min-Max 归一化（菜单 3-8）: 将数值缩放到 [0, 1] 范围。')
        self._body('Z-Score 标准化（菜单 3-9）: 转换为均值0、标准差1的分布。')
        self._body('对数变换（菜单 3-10）: 对偏态分布数据取对数，使其更接近正态分布。')

    def ch_viz(self):
        self.add_page()
        self._section_title('五、数据可视化')

        self._section_title('5.1 静态图表 (菜单 4-1 ~ 4-10)', level=2)
        self._body('生成 PNG 格式图片，保存在 output/charts/ 目录。')
        self._table(
            ['编号', '图表类型', '说明'],
            [
                ['4-1', '柱状图', '类别对比，支持水平/垂直、排序、TopN'],
                ['4-2', '折线图', '趋势变化，支持多线对比'],
                ['4-3', '饼图/环形图', '占比分布'],
                ['4-4', '散点图', '两变量关系，可选颜色/大小维度+趋势线'],
                ['4-5', '直方图', '数值分布 + KDE密度曲线'],
                ['4-6', '箱线图', '分布特征 + 离群点，支持分组对比'],
                ['4-7', '热力图', '矩阵数值颜色映射'],
                ['4-8', '相关性热力图', 'pearson/spearman/kendall'],
                ['4-9', '时间序列图', '支持按M/W/Q重采样'],
                ['4-10', '组合仪表板', '多图组合在单张画布上'],
            ],
            [22, 48, 110]
        )

        self._section_title('5.2 交互式图表 (菜单 4-11 ~ 4-20)', level=2)
        self._body('使用 Plotly 生成，输出为独立 HTML 文件，双击在浏览器中打开。支持缩放、平移、悬停查看数值、点击图例筛选等交互操作。')
        self._table(
            ['编号', '图表类型', '额外特性'],
            [
                ['4-11', '交互式柱状图', '悬停数值、缩放、导出图片'],
                ['4-12', '交互式折线图', '多线对比、标记点切换'],
                ['4-13', '交互式饼图/环形图', '动画、点击钻取'],
                ['4-14', '交互式箱线图', '离群点悬停详情'],
                ['4-15', '交互式热力图', '值标注、颜色标尺'],
                ['4-16', '相关性热力图', '红蓝渐变色阶'],
                ['4-17', '交互式时间序列', '时间轴缩放平移'],
                ['4-18', '交互式散点图', '缩放、框选、多维度颜色'],
                ['4-19', '旭日图/矩形树图', '层级数据交互钻取'],
                ['4-20', '交互式仪表板', '多图组合+交互'],
            ],
            [22, 62, 96]
        )
        self._tip('交互式图表 HTML 文件约 4-5MB，可直接在浏览器中打开查看，也支持导出为 PNG。')

    def ch_analysis(self):
        self.add_page()
        self._section_title('六、数据分析')

        self._section_title('6.1 描述统计', level=2)
        self._body('菜单 5-1: 对全部数值列输出 count/mean/std/min/1%/5%/25%/50%/75%/95%/99%/max 等 12 个统计量。')
        self._body('菜单 5-2: 对指定列统计各取值的频数和累计占比。')
        self._body('菜单 5-3: 所有列的详细摘要——类型、缺失、唯一值、均值、中位数、范围。')
        self.ln(2)

        self._section_title('6.2 相关性分析', level=2)
        self._body('菜单 5-4: 相关系数矩阵（pearson=线性相关 / spearman=秩相关 / kendall=序相关）。')
        self._body('菜单 5-5: 自动提取最强相关对，按强度分类（极强/强/中等/弱）。')
        self._body('菜单 5-6: 找与目标变量相关的所有列，可按阈值过滤。')
        self.ln(2)

        self._section_title('6.3 报告生成', level=2)
        self._body('文本报告（菜单 5-7）: 在终端输出数据分析报告，可保存为 .txt 文件。包含数据概览、描述统计、缺失值、异常值、最强相关对。')
        self._body('HTML 报告（菜单 5-8）: 生成格式化的网页报告，含样式和洞察建议。自动识别缺失率>30%的列、强相关对（|r|≥0.7）等关键发现。文件保存在 output/reports/。')
        self._tip('HTML 报告可在任何浏览器中打开查看，排版美观，适合分享。')

    def ch_pdf(self):
        self.add_page()
        self._section_title('七、PDF 导出')

        self._section_title('7.1 数据表导出 PDF', level=2)
        self._body('菜单 7-1: 将当前数据表导出为格式化的 PDF 文档。')
        self._bullet('自动检测中文字体（macOS: 华文黑体; Windows: 微软雅黑）')
        self._bullet('自适应列宽（根据内容长度计算最佳列宽）')
        self._bullet('自动分页（每页重复表头，交替行背景色）')
        self._bullet('支持选择横向(A3宽)或纵向纸张')
        self._bullet('宽表自动拆分为多组列，分页展示')
        self.ln(2)

        self._section_title('7.2 分析报告导出 PDF', level=2)
        self._body('菜单 7-2: 生成包含完整分析内容的 PDF 报告。报告结构:')
        self._bullet('封面页: 标题、数据规模、生成时间')
        self._bullet('数据概览: 行列数、缺失率、列清单')
        self._bullet('描述统计: 所有数值列的统计量')
        self._bullet('缺失值检测: 缺失数、缺失率排名')
        self._bullet('相关性分析: 系数矩阵 + 最强相关对（含强度判断）')
        self._bullet('图表嵌入: 自动生成直方图和相关性热力图并嵌入')
        self._warn('图表嵌入部分需要 matplotlib 支持。请确保系统已安装中文字体。')

    def ch_batch(self):
        self.add_page()
        self._section_title('八、批量处理')

        self._section_title('8.1 批量处理流程', level=2)
        self._body('菜单 6 提供 5 种批量处理模式:')
        self.ln(1)
        self._bullet('合并所有文件: 将匹配的所有文件合并为一个表，可选择保存。')
        self._bullet('逐文件处理: 对每个文件执行相同操作（如删除空行），分别输出。')
        self._bullet('合并后筛选排序: 合并 → 条件筛选 → 排序 → 保存。')
        self._bullet('合并后去重: 合并多个来源文件并去除重复行。')
        self._bullet('合并后分组聚合: 适合多日数据汇总（如按月汇总销售额）。')
        self.ln(2)

        self._section_title('8.2 文件匹配', level=2)
        self._body('支持两种方式指定文件:')
        self._bullet('扩展名模式: 输入 ".xlsx" 会递归搜索当前目录下所有 .xlsx 文件。')
        self._bullet('glob 模式: 输入 "data/2024*.csv" 匹配特定目录下的文件。')
        self._tip('批量处理支持并行模式（max_workers 参数），可加速大量文件的处理速度。')

    def ch_tips(self):
        self.add_page()
        self._section_title('九、常用技巧')

        self._section_title('9.1 编码问题', level=2)
        self._body('CSV/TXT 文件读取时自动检测编码（支持 UTF-8、GBK、GB2312、GB18030、Latin-1）。如果自动检测失败，可在配置文件中修改 FALLBACK_ENCODINGS。')
        self._body('输出 CSV 默认使用 UTF-8 BOM 编码，确保在 Excel 中直接打开中文不乱码。')
        self.ln(2)

        self._section_title('9.2 大文件处理', level=2)
        self._body('对于超出内存的大文件:')
        self._bullet('使用分块读取（菜单 1-3），每块默认 10 万行（CSV）或 5 万行（Excel）。')
        self._bullet('在 config.py 中调整 CSV_CHUNKSIZE 和 EXCEL_CHUNKSIZE 参数。')
        self._bullet('MAX_MEMORY_MB 默认 500MB，超出时会警告。')
        self._bullet('优先使用 CSV 格式（比 Excel 读取快 3-5 倍）。')
        self.ln(2)

        self._section_title('9.3 列操作技巧', level=2)
        self._body('添加计算列时，表达式使用 df["列名"] 引用已有列:')
        self._code("df['销售额'] * df['利润率'] / 100")
        self._body('支持 numpy 函数: np.log(), np.sqrt() 等。')
        self._body('批量重命名时，格式为: 旧名1->新名1, 旧名2->新名2')
        self.ln(2)

        self._section_title('9.4 组合操作', level=2)
        self._body('推荐的典型工作流:')
        self._bullet('1. 读取文件 → 2. 查看列信息 → 3. 清理列名')
        self._bullet('4. 处理缺失值 → 5. 类型转换 → 6. 异常值检测')
        self._bullet('7. 筛选/排序 → 8. 分组聚合 → 9. 可视化')
        self._bullet('10. 生成 HTML/PDF 报告 → 11. 导出结果')
        self.ln(2)

        self._section_title('9.5 输出目录', level=2)
        self._table(
            ['目录', '内容'],
            [
                ['output/charts/', '静态图表(PNG) + 交互式图表(HTML)'],
                ['output/reports/', 'HTML 报告 + PDF 报告'],
                ['output/cleaned/', '清洗后的数据文件'],
                ['output/batch_result/', '批量处理结果'],
            ],
            [55, 125]
        )

        self._warn('output/ 目录下的文件不会被 git 追踪，请放心使用。')

    def ch_commands(self):
        self.add_page()
        self._section_title('附：功能快速索引')
        self._table(
            ['需求', '菜单位置', '说明'],
            [
                ['读取 Excel', '1-1', '键入路径，可选工作表'],
                ['读取 CSV', '1-1', '自动检测编码'],
                ['合并多个文件', '1-2', '指定目录+扩展名'],
                ['大文件分块读', '1-3', '防止内存溢出'],
                ['筛选数据', '2-1~2-3', '条件/列表/TopN'],
                ['排序', '2-4', '支持多列排序'],
                ['去重', '2-5', '按指定列去重'],
                ['合并两个表', '2-7~2-8', 'JOIN / UNION'],
                ['数据透视表', '2-10', '类似Excel透视表'],
                ['分组求和/平均', '2-11', 'sum/mean/count...'],
                ['VLOOKUP', '2-13', '从另一表查找值'],
                ['模糊搜索', '2-14', '关键词匹配'],
                ['缺失值处理', '3-1~3-3', '删除/填充/自动'],
                ['异常值处理', '3-4~3-5', 'IQR/Z-Score'],
                ['归一化', '3-8~3-10', 'MinMax/Z-Score/log'],
                ['生成图表', '4-1~4-20', '静态+交互式'],
                ['描述统计', '5-1', '12项统计指标'],
                ['相关性分析', '5-4~5-6', '找出相关变量'],
                ['HTML 报告', '5-8', '网页格式分析报告'],
                ['导出 PDF', '7-1~7-2', '数据表/分析报告'],
                ['批量处理', '6', '多文件一键处理'],
            ],
            [38, 28, 114]
        )

    def build(self, output_path):
        self.cover_page()
        self.toc_page()
        self.ch_quickstart()
        self.ch_read()
        self.ch_operations()
        self.ch_cleaning()
        self.ch_viz()
        self.ch_analysis()
        self.ch_pdf()
        self.ch_batch()
        self.ch_tips()
        self.ch_commands()

        self.output(output_path)
        return output_path


if __name__ == '__main__':
    builder = ManualBuilder()
    output_dir = os.path.join(os.path.dirname(__file__), 'output')
    os.makedirs(output_dir, exist_ok=True)
    path = os.path.join(output_dir, '使用说明.pdf')
    builder.build(path)
    size_kb = os.path.getsize(path) / 1024
    print(f'✅ 使用说明已生成: {path} ({size_kb:.1f} KB)')
