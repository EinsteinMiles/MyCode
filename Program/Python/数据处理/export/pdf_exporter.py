"""
PDF 导出模块：将数据表和分析报告导出为 PDF
使用 fpdf2（纯 Python，无系统依赖）和 matplotlib 图表嵌入
"""
import os
import tempfile
from datetime import datetime
import pandas as pd
import numpy as np

from fpdf import FPDF
from config import OUTPUT_DIR, REPORT_DIR, CHART_DPI, logger


class PDFExporter:
    """PDF 导出器 - 支持中文、表格、图表嵌入"""

    def __init__(self, orientation: str = 'L', font_size: int = 9):
        """
        Args:
            orientation: 'P'(纵向) | 'L'(横向)
            font_size: 正文字号
        """
        self.pdf = FPDF(orientation=orientation, unit='mm')
        self.font_size = font_size
        self._setup_fonts()
        self._setup_page()

    def _setup_fonts(self):
        """注册中文字体"""
        # 尝试多个常见的中文字体路径
        font_paths = [
            # macOS
            '/System/Library/Fonts/PingFang.ttc',
            '/System/Library/Fonts/STHeiti Light.ttc',
            '/System/Library/Fonts/STHeiti Medium.ttc',
            '/Library/Fonts/Arial Unicode.ttf',
            # Linux
            '/usr/share/fonts/truetype/wqy/wqy-microhei.ttc',
            '/usr/share/fonts/truetype/droid/DroidSansFallbackFull.ttf',
            '/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc',
            # Windows
            'C:\\Windows\\Fonts\\msyh.ttc',
            'C:\\Windows\\Fonts\\simsun.ttc',
        ]

        font_added = False
        for font_path in font_paths:
            if os.path.exists(font_path):
                try:
                    self.pdf.add_font('CN', '', font_path, uni=True)
                    self.pdf.add_font('CN', 'B', font_path, uni=True)
                    self.font_name = 'CN'
                    font_added = True
                    logger.info(f"中文字体已加载: {font_path}")
                    break
                except Exception:
                    continue

        if not font_added:
            logger.warning("未找到中文字体，将使用内置字体(中文可能显示为方框)")
            self.font_name = 'Helvetica'

    def _setup_page(self):
        self.pdf.set_auto_page_break(auto=True, margin=15)

    # ================================================================
    #  表格导出
    # ================================================================

    def export_dataframe(self, df: pd.DataFrame, output_path: str = None,
                         title: str = None, max_cols: int = 10) -> str:
        """将 DataFrame 导出为 PDF 表格

        自动处理大表格：分页、列过多时分多张表

        Args:
            df: 数据
            output_path: 输出文件路径
            title: 标题
            max_cols: 每张表最多列数（超过则分多张表）
        """
        if output_path is None:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            output_path = os.path.join(OUTPUT_DIR, f'data_export_{timestamp}.pdf')

        # 分列处理：列太多时分多页
        if len(df.columns) > max_cols:
            return self._export_wide_dataframe(df, output_path, title, max_cols)

        self._add_dataframe_pages(df, title)
        self.pdf.output(output_path)
        logger.info(f"PDF 表格已导出: {output_path} ({os.path.getsize(output_path)/1024:.1f} KB)")
        return output_path

    def _export_wide_dataframe(self, df: pd.DataFrame, output_path: str,
                               title: str, max_cols: int) -> str:
        """宽表格分多张子表导出"""
        cols = df.columns.tolist()
        # 第一组包含索引列概念上的前几列，保留完整行标签
        n_groups = (len(cols) + max_cols - 1) // max_cols

        for g in range(n_groups):
            start = g * max_cols
            end = min(start + max_cols, len(cols))
            subset = df.iloc[:, start:end]
            sub_title = f"{title} ({g+1}/{n_groups})" if title else f"数据表 ({g+1}/{n_groups})"
            self._add_dataframe_pages(subset, sub_title, add_page=(g > 0))

        self.pdf.output(output_path)
        logger.info(f"宽表格 PDF 已导出 ({n_groups} 组列): {output_path}")
        return output_path

    def _add_dataframe_pages(self, df: pd.DataFrame, title: str = None,
                             add_page: bool = False):
        """添加 DataFrame 页面"""
        if add_page:
            self.pdf.add_page()
        else:
            self.pdf.add_page()

        # 标题
        if title:
            self.pdf.set_font(self.font_name, 'B', 14)
            self.pdf.cell(0, 10, title, ln=True, align='C')
            self.pdf.ln(4)

        # 元信息
        self.pdf.set_font(self.font_name, '', 8)
        self.pdf.set_text_color(128, 128, 128)
        self.pdf.cell(0, 6,
                      f"行数: {len(df)} | 列数: {len(df.columns)} | "
                      f"生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
                      ln=True, align='C')
        self.pdf.ln(4)
        self.pdf.set_text_color(0, 0, 0)

        # 计算列宽
        page_w = self.pdf.w - 20  # 可用宽度 (减去边距)
        col_widths = self._calc_col_widths(df, page_w)

        # 表头
        self.pdf.set_font(self.font_name, 'B', self.font_size)
        self.pdf.set_fill_color(52, 73, 94)
        self.pdf.set_text_color(255, 255, 255)
        header_height = 8

        for i, col in enumerate(df.columns):
            self.pdf.cell(col_widths[i], header_height,
                          str(col)[:30], border=1, fill=True, align='C')
        self.pdf.ln()

        # 数据行
        self.pdf.set_font(self.font_name, '', self.font_size)
        self.pdf.set_text_color(0, 0, 0)
        row_height = 7

        for _, row in df.iterrows():
            # 检查是否跨页
            if self.pdf.get_y() > self.pdf.h - 25:
                self.pdf.add_page()
                # 重新打印表头
                self.pdf.set_font(self.font_name, 'B', self.font_size)
                self.pdf.set_fill_color(52, 73, 94)
                self.pdf.set_text_color(255, 255, 255)
                for i, col in enumerate(df.columns):
                    self.pdf.cell(col_widths[i], header_height,
                                  str(col)[:30], border=1, fill=True, align='C')
                self.pdf.ln()
                self.pdf.set_font(self.font_name, '', self.font_size)
                self.pdf.set_text_color(0, 0, 0)

            # 交替行背景
            fill = (self.pdf.page_no() % 2 == 0)
            if fill:
                self.pdf.set_fill_color(245, 247, 250)

            for i, col in enumerate(df.columns):
                val = row[col]
                if pd.isna(val):
                    text = '-'
                elif isinstance(val, float):
                    text = f'{val:.2f}'
                else:
                    text = str(val)[:50]
                self.pdf.cell(col_widths[i], row_height, text,
                              border=1, fill=fill, align='C' if i > 0 else 'L')
            self.pdf.ln()

    def _calc_col_widths(self, df: pd.DataFrame, page_w: float) -> list:
        """根据内容计算最佳列宽"""
        widths = []
        total = page_w

        for col in df.columns:
            # 取表头和前50行最长的内容
            header_len = len(str(col))
            sample = df[col].head(50).astype(str).str.len().max() if len(df) > 0 else 0
            content_len = max(header_len, sample if not pd.isna(sample) else 0)
            # 每个字符约 2.5mm (对于中文字体)
            width = min(max(content_len * 2.5, 20), 60)
            widths.append(width)

        # 等比例缩放
        total_w = sum(widths)
        if total_w > page_w:
            scale = page_w / total_w
            widths = [w * scale for w in widths]

        return widths

    # ================================================================
    #  报告导出
    # ================================================================

    def export_report(self, df: pd.DataFrame, output_path: str = None,
                      title: str = "数据分析报告") -> str:
        """生成完整的 PDF 分析报告（含统计、图表）"""
        if output_path is None:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            output_path = os.path.join(REPORT_DIR, f'report_{timestamp}.pdf')

        self.pdf.set_auto_page_break(auto=True, margin=15)

        # --- 封面 ---
        self._add_cover(title, df)

        # --- 数据概览 ---
        self._add_overview_section(df)

        # --- 描述统计 ---
        self._add_stats_section(df)

        # --- 缺失值 ---
        self._add_missing_section(df)

        # --- 相关性 ---
        self._add_correlation_section(df)

        # --- 图表 ---
        self._add_charts_section(df)

        # 保存
        self.pdf.output(output_path)
        file_size = os.path.getsize(output_path) / 1024
        logger.info(f"PDF 报告已生成: {output_path} ({file_size:.1f} KB)")
        return output_path

    def _add_cover(self, title: str, df: pd.DataFrame):
        """添加封面页"""
        self.pdf.add_page()
        self.pdf.ln(50)

        # 标题
        self.pdf.set_font(self.font_name, 'B', 28)
        self.pdf.set_text_color(44, 62, 80)
        self.pdf.cell(0, 15, title, ln=True, align='C')

        self.pdf.ln(10)
        self.pdf.set_draw_color(52, 152, 219)
        self.pdf.set_line_width(0.5)
        self.pdf.line(60, self.pdf.get_y(), self.pdf.w - 60, self.pdf.get_y())
        self.pdf.ln(15)

        # 元数据
        self.pdf.set_font(self.font_name, '', 14)
        self.pdf.set_text_color(127, 140, 141)
        metadata = [
            f"生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            f"数据行数: {len(df):,}",
            f"数据列数: {len(df.columns)}",
            f"数值列数: {len(df.select_dtypes(include=[np.number]).columns)}",
            "",
            "由 数据处理工具 自动生成",
        ]
        for line in metadata:
            self.pdf.cell(0, 10, line, ln=True, align='C')

    def _add_overview_section(self, df: pd.DataFrame):
        """数据概览"""
        self.pdf.add_page()
        self._section_header('数据概览')

        # 基本信息
        self.pdf.set_font(self.font_name, '', 11)
        items = [
            ('总行数', f'{len(df):,}'),
            ('总列数', str(len(df.columns))),
            ('数值列数', str(len(df.select_dtypes(include=[np.number]).columns))),
            ('文本列数', str(len(df.select_dtypes(include=['object', 'string']).columns))),
            ('缺失率', f'{df.isna().mean().mean() * 100:.2f}%'),
            ('内存占用', f'{df.memory_usage(deep=True).sum() / 1024 / 1024:.2f} MB'),
        ]

        for i, (label, value) in enumerate(items):
            self.pdf.set_font(self.font_name, 'B', 11)
            self.pdf.cell(40, 8, label + ':', align='R')
            self.pdf.set_font(self.font_name, '', 11)
            self.pdf.cell(60, 8, value, align='L')

        self.pdf.ln(12)

        # 列清单
        self.pdf.set_font(self.font_name, 'B', 11)
        self.pdf.cell(0, 8, '列清单:', ln=True)
        self.pdf.set_font(self.font_name, '', 9)

        for i, col in enumerate(df.columns):
            dtype = str(df[col].dtype)
            missing = df[col].isna().sum()
            self.pdf.cell(0, 6, f"  {i+1}. {col}  [{dtype}]  缺失: {missing}", ln=True)

    def _add_stats_section(self, df: pd.DataFrame):
        """描述统计"""
        self.pdf.add_page()
        self._section_header('描述统计')

        numeric_df = df.describe(percentiles=[.25, .5, .75]).round(2)
        self._small_table_from_df(numeric_df)

    def _add_missing_section(self, df: pd.DataFrame):
        """缺失值检测"""
        missing = df.isna().sum()
        missing = missing[missing > 0]

        if len(missing) == 0:
            self.pdf.set_font(self.font_name, '', 11)
            self.pdf.cell(0, 10, '✓ 未检测到缺失值', ln=True)
            return

        self.pdf.add_page()
        self._section_header('缺失值检测')

        missing_df = pd.DataFrame({
            '列名': missing.index,
            '缺失数': missing.values,
            '缺失率(%)': (missing.values / len(df) * 100).round(2),
        }).sort_values('缺失率(%)', ascending=False)

        self._small_table_from_df(missing_df)

    def _add_correlation_section(self, df: pd.DataFrame):
        """相关性分析"""
        numeric_cols = df.select_dtypes(include=[np.number]).columns
        if len(numeric_cols) < 2:
            return

        self.pdf.add_page()
        self._section_header('相关性分析')

        corr = df[numeric_cols].corr()

        # 只显示前 8 列（避免表格太宽）
        if len(corr.columns) > 8:
            corr = corr.iloc[:8, :8]

        self._small_table_from_df(corr.round(3))

        # 最强相关对
        self.pdf.ln(8)
        self.pdf.set_font(self.font_name, 'B', 11)
        self.pdf.cell(0, 8, '最强相关对:', ln=True)
        self.pdf.set_font(self.font_name, '', 10)

        # 提取上三角
        pairs = []
        for i in range(len(corr.columns)):
            for j in range(i + 1, len(corr.columns)):
                val = corr.iloc[i, j]
                if abs(val) >= 0.3:
                    pairs.append((corr.columns[i], corr.columns[j], val))

        pairs.sort(key=lambda x: abs(x[2]), reverse=True)
        for a, b, v in pairs[:10]:
            strength = '强' if abs(v) >= 0.6 else '中等' if abs(v) >= 0.4 else '弱'
            direction = '正相关' if v > 0 else '负相关'
            self.pdf.cell(0, 7, f"  {a} ↔ {b}: r={v:.3f} ({strength}{direction})", ln=True)

    def _add_charts_section(self, df: pd.DataFrame):
        """在报告中嵌入关键图表"""
        numeric_cols = df.select_dtypes(include=[np.number]).columns
        if len(numeric_cols) == 0:
            return

        self.pdf.add_page()
        self._section_header('数据可视化')

        # 使用 matplotlib 生成图表然后嵌入
        import matplotlib
        matplotlib.use('Agg')
        import matplotlib.pyplot as plt
        import seaborn as sns

        with tempfile.TemporaryDirectory() as tmpdir:
            # 直方图
            chart_path = os.path.join(tmpdir, 'hist.png')
            fig, ax = plt.subplots(figsize=(8, 4))
            col = numeric_cols[0]
            ax.hist(df[col].dropna(), bins=20, color='#4A90D9', alpha=0.7,
                    edgecolor='white')
            ax.set_title(f'{col} 分布', fontsize=12, fontweight='bold')
            ax.set_xlabel(col)
            fig.savefig(chart_path, dpi=100, bbox_inches='tight',
                        facecolor='white')
            plt.close(fig)

            self._add_image_with_caption(chart_path, f'图1: {col} 分布直方图')

            if len(numeric_cols) >= 2:
                # 相关性热力图
                self.pdf.add_page()
                chart_path2 = os.path.join(tmpdir, 'corr.png')
                fig, ax = plt.subplots(figsize=(8, 6))
                display_cols = numeric_cols[:8] if len(numeric_cols) > 8 else numeric_cols
                corr = df[display_cols].corr()
                sns.heatmap(corr, annot=True, fmt='.2f', cmap='RdBu_r',
                            ax=ax, linewidths=0.5)
                ax.set_title('相关系数热力图', fontsize=12, fontweight='bold')
                fig.savefig(chart_path2, dpi=100, bbox_inches='tight',
                            facecolor='white')
                plt.close(fig)
                self._add_image_with_caption(chart_path2, '图2: 相关系数热力图')

    def _add_image_with_caption(self, image_path: str, caption: str):
        """添加图片和标题"""
        if os.path.exists(image_path):
            # 图片居中
            img_w = self.pdf.w - 30  # 左右边距
            self.pdf.image(image_path, x=15, w=img_w)

            self.pdf.ln(3)
            self.pdf.set_font(self.font_name, '', 9)
            self.pdf.set_text_color(128, 128, 128)
            self.pdf.cell(0, 6, caption, ln=True, align='C')
            self.pdf.set_text_color(0, 0, 0)
            self.pdf.ln(5)

    def _section_header(self, title: str):
        """章节标题"""
        self.pdf.set_font(self.font_name, 'B', 16)
        self.pdf.set_text_color(44, 62, 80)
        self.pdf.cell(0, 10, title, ln=True)

        # 下划线
        self.pdf.set_draw_color(52, 152, 219)
        self.pdf.set_line_width(0.8)
        self.pdf.line(10, self.pdf.get_y(), self.pdf.w - 10, self.pdf.get_y())
        self.pdf.ln(8)
        self.pdf.set_text_color(0, 0, 0)

    def _small_table_from_df(self, df: pd.DataFrame):
        """紧凑格式的表格"""
        if df.empty:
            self.pdf.set_font(self.font_name, '', 10)
            self.pdf.cell(0, 8, '(无数据)', ln=True)
            return

        page_w = self.pdf.w - 20
        col_widths = self._calc_col_widths(df, page_w)

        # 表头
        self.pdf.set_font(self.font_name, 'B', 8)
        self.pdf.set_fill_color(52, 73, 94)
        self.pdf.set_text_color(255, 255, 255)
        for i, col in enumerate(df.columns):
            text = str(col)[:20]
            self.pdf.cell(col_widths[i], 7, text, border=1, fill=True, align='C')
            # 处理行首列（索引名）
            if i == 0 and df.index.name:
                self.pdf.cell(col_widths[i], 7, str(df.index.name)[:20],
                              border=1, fill=True, align='C')

        self.pdf.ln()

        # 数据
        self.pdf.set_font(self.font_name, '', 7.5)
        self.pdf.set_text_color(0, 0, 0)
        for idx, row in df.iterrows():
            if self.pdf.get_y() > self.pdf.h - 20:
                self.pdf.add_page()
                # 重新表头
                self.pdf.set_font(self.font_name, 'B', 8)
                self.pdf.set_fill_color(52, 73, 94)
                self.pdf.set_text_color(255, 255, 255)
                for i, col in enumerate(df.columns):
                    self.pdf.cell(col_widths[i], 7, str(col)[:20],
                                  border=1, fill=True, align='C')
                self.pdf.ln()
                self.pdf.set_font(self.font_name, '', 7.5)
                self.pdf.set_text_color(0, 0, 0)

            fill = (int(idx) % 2 == 0) if isinstance(idx, (int, float)) else False
            if fill:
                self.pdf.set_fill_color(245, 247, 250)

            for i, col in enumerate(df.columns):
                val = row[col]
                if pd.isna(val):
                    text = '-'
                elif isinstance(val, float):
                    text = f'{val:.2f}'
                else:
                    text = str(val)[:20]
                self.pdf.cell(col_widths[i], 6, text, border=1, fill=fill, align='C')
            self.pdf.ln()


# ================================================================
#  便捷函数
# ================================================================

def export_to_pdf(df: pd.DataFrame, output_path: str = None,
                  title: str = None, orientation: str = 'L') -> str:
    """快速导出 DataFrame 为 PDF 表格

    Args:
        df: 数据
        output_path: 输出路径 (默认自动生成)
        title: 表格标题
        orientation: 'L'(横向) | 'P'(纵向)
    """
    exporter = PDFExporter(orientation=orientation)
    return exporter.export_dataframe(df, output_path, title)


def export_report_to_pdf(df: pd.DataFrame, output_path: str = None,
                         title: str = "数据分析报告") -> str:
    """快速导出分析报告为 PDF

    Args:
        df: 数据
        output_path: 输出路径
        title: 报告标题
    """
    exporter = PDFExporter(orientation='L')
    return exporter.export_report(df, output_path, title)
