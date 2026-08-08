#!/usr/bin/env python3
"""
数据处理工具 - 主入口
========================
支持 Excel/CSV/JSON/TXT/DOCX 等多种格式的：
  读取、合并、拆分、数据透视、筛选、排序、聚合、匹配、
  数据清洗、预处理、数据可视化、数据分析报告

适用场景：大批量文件处理 | 大型文件处理 | 数据清洗 | 数据可视化 | 数据分析
"""
import os
import sys
import traceback
try:
    import readline  # 启用终端行编辑：退格删除、方向键、Ctrl+A/E/K/U/W
except ImportError:
    try:
        import pyreadline3 as readline  # Windows 备选
    except ImportError:
        pass  # 无 readline 也能运行，但编辑体验较差
import pandas as pd
import numpy as np

# 添加当前目录到路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config import OUTPUT_DIR, CHART_DIR, REPORT_DIR, SUPPORTED_WRITE_FORMATS
from utils.helpers import find_files, get_file_info, parse_column_list, safe_parse_value
from core.reader import read_file, read_multiple, read_chunked
from core.writer import write_file
from core.batch import batch_process
from operations.transform import (
    rename_columns, select_columns, drop_columns,
    add_calculated_column, change_type, reorder_columns
)
from operations.filter_sort import (
    filter_by_value, filter_by_list,
    filter_top_n, sort_data, drop_duplicates_custom
)
from operations.merge_split import (
    merge_rows, merge_on_key, merge_on_different_keys,
    split_by_column, split_by_rows, split_by_value
)
from operations.pivot_agg import (
    pivot_table, group_aggregate, crosstab
)
from operations.lookup import vlookup, fuzzy_match, range_lookup
from cleaning.cleaner import (
    handle_missing, fill_missing, remove_outliers,
    strip_whitespace, clean_column_names
)
from cleaning.normalize import (
    min_max_scale, z_score_standardize, log_transform
)
from visualization.charts import (
    bar_chart, line_chart, pie_chart, scatter_plot,
    histogram, box_plot, heatmap, correlation_heatmap,
    time_series, multi_line_chart
)
from visualization.dashboard import dashboard_layout
from visualization.interactive import (
    ibar_chart, iline_chart, ipie_chart, iscatter_plot,
    ihistogram, ibox_plot, iheatmap, icorrelation_heatmap,
    itime_series, iarea_chart, isunburst, itreemap, idashboard
)
from analysis.stats import (
    describe_data, all_columns_summary,
    frequency_table, missing_report, outlier_report
)
from analysis.correlation import (
    correlation_matrix, top_correlations, find_related_pairs
)
from analysis.report import generate_report, generate_html_report
from export.pdf_exporter import export_to_pdf, export_report_to_pdf


class DataProcessor:
    """数据处理主控制器"""

    def __init__(self):
        self.df: pd.DataFrame = None  # 当前工作数据
        self.file_path: str = None     # 当前文件路径
        self.history: list = []        # 操作历史（用于撤回）

    # ============================================================
    #  主菜单
    # ============================================================

    def run(self):
        """启动主循环"""
        self._clear_screen()
        print("""
╔══════════════════════════════════════════════════════╗
║           🛠  数据处理工具  v1.0                      ║
║           Excel · CSV · JSON · TXT · DOCX            ║
╚══════════════════════════════════════════════════════╝
        """)
        while True:
            self._show_main_menu()
            choice = input("\n👉 请选择操作 (0-6): ").strip()

            if choice == '0':
                print("\n👋 再见！")
                break
            elif choice == '1':
                self._menu_read()
            elif choice == '2':
                self._menu_operations()
            elif choice == '3':
                self._menu_cleaning()
            elif choice == '4':
                self._menu_visualization()
            elif choice == '5':
                self._menu_analysis()
            elif choice == '6':
                self._menu_batch()
            elif choice == '7':
                self._menu_pdf_export()
            else:
                print("❌ 无效选择，请重新输入")

    def _show_main_menu(self):
        print(f"""
┌──────────────────────────────────────────────────────┐
│  当前数据: {self._data_status()} │
├──────────────────────────────────────────────────────┤
│  1. 📂 文件读取  (Excel/CSV/JSON/TXT/DOCX)           │
│  2. 🔧 数据操作  (筛选/排序/合并/拆分/透视/匹配)      │
│  3. 🧹 数据清洗  (缺失值/异常值/去重/标准化)         │
│  4. 📊 数据可视化 (静态图/交互式图表/仪表板)          │
│  5. 📋 数据分析  (描述统计/相关性/HTML报告)          │
│  6. ⚡ 批量处理  (多文件批处理)                       │
│  7. 📄 PDF导出   (数据表/分析报告导出PDF)            │
│  0. 🚪 退出                                          │
└──────────────────────────────────────────────────────┘
        """)

    def _data_status(self) -> str:
        if self.df is None:
            return "未加载"
        return f"{len(self.df)}行×{len(self.df.columns)}列"

    def _check_data(self) -> bool:
        if self.df is None:
            print("❌ 请先读取数据文件 (菜单 1)")
            return False
        return True

    # ============================================================
    #  1. 文件读取菜单
    # ============================================================

    def _menu_read(self):
        while True:
            print(f"""
┌─── 文件读取 ─────────────────────────────────────────┐
│  当前数据: {self._data_status():<44} │
├──────────────────────────────────────────────────────┤
│  1. 📖 读取单个文件                                   │
│  2. 📚 批量读取+合并 (同目录多文件)                   │
│  3. 📋 分块读取大文件                                 │
│  4. 🔍 扫描目录找文件                                 │
│  5. 💾 导出当前数据                                   │
│  6. 📝 预览当前数据 (前20行)                          │
│  7. ℹ️  查看列信息和类型                              │
│  0. ↩️  返回主菜单                                    │
└──────────────────────────────────────────────────────┘
            """)
            choice = input("👉 请选择: ").strip()

            try:
                if choice == '0':
                    break
                elif choice == '1':
                    self._read_single()
                elif choice == '2':
                    self._read_batch()
                elif choice == '3':
                    self._read_chunked()
                elif choice == '4':
                    self._scan_files()
                elif choice == '5':
                    self._export_data()
                elif choice == '6':
                    self._preview_data()
                elif choice == '7':
                    self._show_info()
                else:
                    print("❌ 无效选择")
            except Exception as e:
                print(f"❌ 错误: {e}")

    def _read_single(self):
        path = input("📂 文件路径: ").strip()
        if not os.path.exists(path):
            print(f"❌ 文件不存在: {path}")
            return

        # 表头配置
        header = self._ask_header()

        # Excel 文件询问工作表名
        kwargs = {'header': header}
        ext = os.path.splitext(path)[1].lower()
        if ext in ('.xlsx', '.xls'):
            sheet = input("工作表名 (直接回车默认第一个): ").strip() or 0
            kwargs['sheet_name'] = sheet

        self.df = read_file(path, **kwargs)
        self.file_path = path
        self._show_data_summary()

    def _ask_header(self) -> int | None:
        """询问用户表头配置

        Returns:
            None = 无表头（自动生成 列1, 列2...）
            0 = 第1行是表头（默认）
            1 = 第2行是表头
            2 = 第3行是表头
            ...
        """
        print("""
表头设置:
  回车跳过 = 第1行是表头 (默认)
  0 = 无表头，数据从第1行开始 (自动生成 列1, 列2, ...)
  1 = 第2行是表头 (跳过第1行)
  2 = 第3行是表头 (跳过第1-2行)
  ...以此类推
        """)
        choice = input("👉 表头在哪一行? (回车=第1行, 0=无表头, 1=第2行...): ").strip()

        if choice == '':
            return 0  # 默认：第1行是表头
        elif choice == '0':
            return None  # 无表头
        else:
            try:
                return int(choice)  # 第 N+1 行是表头
            except ValueError:
                print("⚠ 输入无效，使用默认(第1行是表头)")
                return 0

    def _read_batch(self):
        directory = input("📁 目录路径 (直接回车=当前目录): ").strip() or '.'
        ext = input("扩展名 (如 .xlsx, .csv, 直接回车=全部格式): ").strip()

        patterns = [ext] if ext else None
        files = find_files(directory, patterns=patterns)
        if not files:
            print("❌ 未找到匹配文件")
            return

        print(f"\n找到 {len(files)} 个文件:")
        for f in files[:20]:
            info = get_file_info(f)
            print(f"  {info['name']} ({info['size_mb']}MB)")
        if len(files) > 20:
            print(f"  ... 还有 {len(files) - 20} 个文件")

        confirm = input(f"\n合并读取全部 {len(files)} 个文件? (y/n): ").strip().lower()
        if confirm == 'y':
            header = self._ask_header()
            self.df = read_multiple(files, concat=True, header=header)
            self.file_path = directory
            self._show_data_summary()

    def _read_chunked(self):
        path = input("📂 文件路径: ").strip()
        chunksize = input("每块行数 (直接回车=自动): ").strip()
        chunksize = int(chunksize) if chunksize else None
        header = self._ask_header()
        self.df = read_chunked(path, chunksize=chunksize, header=header)
        self.file_path = path
        self._show_data_summary()

    def _scan_files(self):
        directory = input("📁 目录路径: ").strip() or '.'
        ext = input("扩展名过滤 (如 .xlsx, 直接回车=全部): ").strip()
        patterns = [ext] if ext else None
        files = find_files(directory, patterns=patterns)
        print(f"\n找到 {len(files)} 个文件:")
        for f in files:
            info = get_file_info(f)
            print(f"  {info['path']} | {info['size_mb']}MB | {info['mtime']}")

    def _export_data(self):
        if not self._check_data():
            return
        filename = input("输出文件名 (如 output.xlsx): ").strip()
        ext = os.path.splitext(filename)[1].lower()
        if ext not in SUPPORTED_WRITE_FORMATS:
            print(f"❌ 不支持的格式: {ext}, 支持: {SUPPORTED_WRITE_FORMATS}")
            return
        path = os.path.join(OUTPUT_DIR, filename)
        write_file(self.df, path)
        print(f"✅ 已保存: {path}")

    def _preview_data(self):
        if not self._check_data():
            return
        n = input("显示行数 (直接回车=20): ").strip()
        n = int(n) if n else 20
        pd.set_option('display.max_columns', 20)
        pd.set_option('display.width', 200)
        pd.set_option('display.max_colwidth', 30)
        print(f"\n--- 预览 (前 {min(n, len(self.df))} 行) ---")
        print(self.df.head(n).to_string())

    def _show_info(self):
        if not self._check_data():
            return
        print(f"\n--- 数据信息 ---")
        print(f"行数: {len(self.df)}")
        print(f"列数: {len(self.df.columns)}")
        print(f"内存: {self.df.memory_usage(deep=True).sum() / 1024 / 1024:.2f} MB")
        print(f"\n列详情:")
        for col in self.df.columns:
            dtype = str(self.df[col].dtype)
            missing = self.df[col].isna().sum()
            unique = self.df[col].nunique()
            print(f"  {col:<20} {dtype:<12} 缺失:{missing:<6} 唯一值:{unique}")

    def _show_data_summary(self):
        print(f"\n✅ 读取成功: {len(self.df)} 行 × {len(self.df.columns)} 列")
        print(f"   列名: {', '.join(self.df.columns[:15].tolist())}"
              + ('...' if len(self.df.columns) > 15 else ''))

    # ============================================================
    #  2. 数据操作菜单
    # ============================================================

    def _menu_operations(self):
        while True:
            print(f"""
┌─── 数据操作 ─────────────────────────────────────────┐
│  当前数据: {self._data_status():<44} │
├──────────────────────────────────────────────────────┤
│  --- 筛选与排序 ---                                  │
│  1. 🔍 条件筛选    (>, <, ==, contains...)           │
│  2. 📋 列表筛选    (in / not in)                     │
│  3. 🔝 取Top N     (最大/最小N条)                    │
│  4. 📊 多列排序                                      │
│  5. 🔄 去重                                         │
│  --- 变换与合并 ---                                  │
│  6. ✏️  列操作     (选择/删除/重命名/新增计算列)     │
│  7. 🔗 键合并     (类似 SQL JOIN / VLOOKUP)          │
│  8. 📎 行合并     (纵向追加)                         │
│  9. ✂️  拆分数据   (按列值/行数/区间)               │
│  --- 透视与聚合 ---                                  │
│  10. 📐 数据透视表                                   │
│  11. 📊 分组聚合  (sum/mean/count/...)               │
│  12. 🔀 交叉表    (频数统计)                         │
│  --- 查找与匹配 ---                                  │
│  13. 🔎 VLOOKUP   (值匹配)                           │
│  14. 🔍 模糊匹配  (关键词搜索)                       │
│  15. 🎯 范围查找  (区间分类)                         │
│  0. ↩️  返回主菜单                                    │
└──────────────────────────────────────────────────────┘
            """)
            choice = input("👉 请选择: ").strip()

            if choice == '0':
                break
            elif not self._check_data():
                continue

            try:
                if choice == '1':
                    self._op_filter_condition()
                elif choice == '2':
                    self._op_filter_list()
                elif choice == '3':
                    self._op_top_n()
                elif choice == '4':
                    self._op_sort()
                elif choice == '5':
                    self._op_dedup()
                elif choice == '6':
                    self._op_columns()
                elif choice == '7':
                    self._op_merge_key()
                elif choice == '8':
                    self._op_merge_rows()
                elif choice == '9':
                    self._op_split()
                elif choice == '10':
                    self._op_pivot()
                elif choice == '11':
                    self._op_group_agg()
                elif choice == '12':
                    self._op_crosstab()
                elif choice == '13':
                    self._op_vlookup()
                elif choice == '14':
                    self._op_fuzzy()
                elif choice == '15':
                    self._op_range_lookup()
                else:
                    print("❌ 无效选择")
            except Exception as e:
                print(f"❌ 错误: {e}")

    def _op_filter_condition(self):
        print("\n列名: " + ", ".join(self.df.columns.tolist()))
        col = input("筛选列: ").strip()
        print("运算符: ==  !=  >  >=  <  <=  contains  startswith  endswith  between  isnull  notnull")
        op = input("运算符: ").strip()
        if op in ('isnull', 'notnull'):
            self.df = filter_by_value(self.df, col, op, None)
        elif op == 'between':
            lo = safe_parse_value(input("下限: ").strip())
            hi = safe_parse_value(input("上限: ").strip())
            self.df = filter_by_value(self.df, col, op, (lo, hi))
        else:
            val = input("值: ").strip()
            val = safe_parse_value(val)
            self.df = filter_by_value(self.df, col, op, val)
        self._show_data_summary()

    def _op_filter_list(self):
        col = input("筛选列: ").strip()
        vals = input("值列表 (逗号分隔): ").strip()
        values = [safe_parse_value(v.strip()) for v in vals.split(',')]
        inclusive = input("包含(1) 还是 排除(0)? (直接回车=包含): ").strip() != '0'
        self.df = filter_by_list(self.df, col, values, inclusive)
        self._show_data_summary()

    def _op_top_n(self):
        col = input("排序列: ").strip()
        n = int(input("取几条: ").strip() or '10')
        asc = input("升序(1) 降序(0)? (直接回车=降序): ").strip() == '1'
        self.df = filter_top_n(self.df, col, n, ascending=asc)
        self._show_data_summary()

    def _op_sort(self):
        cols = parse_column_list(input("排序列 (逗号分隔): ").strip())
        asc_input = input("升序(1) 降序(0)? 多列用逗号 (直接回车=升序): ").strip()
        if ',' in asc_input:
            ascending = [v.strip() == '1' for v in asc_input.split(',')]
        else:
            ascending = asc_input != '0'
        self.df = sort_data(self.df, cols, ascending)
        print("✅ 排序完成")
        print(self.df.head(10).to_string())

    def _op_dedup(self):
        cols = input("去重列 (逗号分隔, 直接回车=所有列): ").strip()
        subset = parse_column_list(cols) if cols else None
        self.df = drop_duplicates_custom(self.df, subset)
        self._show_data_summary()

    def _op_columns(self):
        while True:
            print(f"\n--- 列操作 ---")
            print(f"  列: {', '.join(self.df.columns.tolist())}")
            print("  1. 选择列  2. 删除列  3. 重命名  4. 添加计算列  5. 改类型  6. 重排序  0. 返回")
            sub = input("👉 ").strip()
            if sub == '0':
                break
            elif sub == '1':
                cols = parse_column_list(input("保留的列 (逗号分隔): ").strip())
                self.df = select_columns(self.df, cols)
            elif sub == '2':
                cols = parse_column_list(input("删除的列 (逗号分隔): ").strip())
                self.df = drop_columns(self.df, cols)
            elif sub == '3':
                print("格式: 旧名1->新名1, 旧名2->新名2")
                raw = input("重命名映射: ").strip()
                mapping = {}
                for pair in raw.split(','):
                    old, new = pair.strip().split('->')
                    mapping[old.strip()] = new.strip()
                self.df = rename_columns(self.df, mapping)
            elif sub == '4':
                name = input("新列名: ").strip()
                expr = input("表达式 (如 df['收入'] - df['成本']): ").strip()
                self.df = add_calculated_column(self.df, name, expr)
            elif sub == '5':
                col = input("列名: ").strip()
                t = input("目标类型 (int/float/str/datetime/category): ").strip()
                self.df = change_type(self.df, col, t)
            elif sub == '6':
                cols = parse_column_list(input("新顺序 (逗号分隔): ").strip())
                self.df = reorder_columns(self.df, cols)
            self._show_data_summary()

    def _op_merge_key(self):
        path = input("📂 要合并的文件路径: ").strip()
        header = self._ask_header()
        right_df = read_file(path, header=header)
        print(f"左表列: {', '.join(self.df.columns.tolist())}")
        print(f"右表列: {', '.join(right_df.columns.tolist())}")

        same_key = input("左右关联键相同? (y/n): ").strip().lower()
        if same_key == 'y':
            on = parse_column_list(input("关联键 (逗号分隔): ").strip())
            how = input("合并方式 (left/right/inner/outer, 默认left): ").strip() or 'left'
            self.df = merge_on_key(self.df, right_df, on=on, how=how)
        else:
            left_on = parse_column_list(input("左表键: ").strip())
            right_on = parse_column_list(input("右表键: ").strip())
            how = input("合并方式: ").strip() or 'left'
            self.df = merge_on_different_keys(self.df, right_df, left_on, right_on, how)
        self._show_data_summary()

    def _op_merge_rows(self):
        path = input("📂 要追加的文件路径: ").strip()
        header = self._ask_header()
        right_df = read_file(path, header=header)
        self.df = merge_rows(self.df, right_df)
        self._show_data_summary()

    def _op_split(self):
        print("拆分方式: 1.按列值  2.按行数  3.按数值区间")
        method = input("👉 ").strip()
        if method == '1':
            col = input("拆分列: ").strip()
            groups = split_by_column(self.df, col)
            self._save_split_groups(groups, col)
        elif method == '2':
            n = int(input("拆分为几份: ").strip())
            parts = split_by_rows(self.df, n)
            for i, part in enumerate(parts):
                path = os.path.join(OUTPUT_DIR, f"split_part_{i+1}.csv")
                write_file(part, path)
            print(f"✅ 已拆分为 {n} 份，保存在 {OUTPUT_DIR}")
        elif method == '3':
            col = input("数值列: ").strip()
            thresholds = [safe_parse_value(v) for v in
                          input("分割点 (逗号分隔, 如 0,100,500,1000): ").strip().split(',')]
            groups = split_by_value(self.df, col, thresholds)
            self._save_split_groups(groups, col)

    def _save_split_groups(self, groups: dict, col_name: str):
        fmt = input("输出格式 (csv/xlsx, 默认csv): ").strip() or 'csv'
        for key, group_df in groups.items():
            safe_key = str(key).replace('/', '_').replace('\\', '_')
            path = os.path.join(OUTPUT_DIR, f"split_{col_name}_{safe_key}.{fmt}")
            write_file(group_df, path)
            print(f"  ✅ {key}: {len(group_df)} 行 → {path}")

    def _op_pivot(self):
        print(f"可用列: {', '.join(self.df.columns.tolist())}")
        index = parse_column_list(input("行标签 (逗号分隔): ").strip())
        columns = input("列标签 (直接回车=None): ").strip() or None
        values = input("值列 (直接回车=全部数值列): ").strip() or None
        if values:
            values = parse_column_list(values)
        aggfunc = input("聚合函数 (sum/mean/count/min/max/median/std, 默认sum): ").strip() or 'sum'
        result = pivot_table(self.df, index=index, columns=columns, values=values, aggfunc=aggfunc)
        print("\n--- 透视表结果 ---")
        pd.set_option('display.max_columns', 30)
        pd.set_option('display.width', 300)
        print(result.to_string())
        self._ask_save_result(result)

    def _op_group_agg(self):
        print(f"可用列: {', '.join(self.df.columns.tolist())}")
        by = parse_column_list(input("分组列 (逗号分隔): ").strip())
        print("聚合格式: 列名=函数, 如 '销售额=sum, 数量=mean'")
        raw = input("聚合配置: ").strip()
        agg_dict = {}
        for pair in raw.split(','):
            col, func = pair.strip().split('=')
            agg_dict[col.strip()] = func.strip()
        result = group_aggregate(self.df, by, agg_dict)
        print(f"\n--- 分组聚合 ({len(result)} 组) ---")
        print(result.to_string())
        self._ask_save_result(result)

    def _op_crosstab(self):
        print(f"可用列: {', '.join(self.df.columns.tolist())}")
        index = input("行标签列: ").strip()
        columns = input("列标签列: ").strip()
        normalize = input("显示比例? (y/n): ").strip().lower() == 'y'
        result = crosstab(self.df, index, columns, normalize=normalize)
        print("\n--- 交叉表 ---")
        print(result.to_string())
        self._ask_save_result(result)

    def _op_vlookup(self):
        path = input("📂 查找表文件路径: ").strip()
        header = self._ask_header()
        lookup_df = read_file(path, header=header)
        print(f"主表列: {', '.join(self.df.columns.tolist())}")
        print(f"查找表列: {', '.join(lookup_df.columns.tolist())}")
        key = input("主表关联列: ").strip()
        lookup_key = input("查找表关联列 (相同则回车): ").strip() or None
        cols = input("要取回的列 (逗号分隔, 直接回车=全部): ").strip()
        columns = parse_column_list(cols) if cols else None
        how = input("匹配方式 (left=保留所有/ inner=仅匹配, 默认left): ").strip() or 'left'
        self.df = vlookup(self.df, lookup_df, key, lookup_key, columns, how)
        self._show_data_summary()

    def _op_fuzzy(self):
        col = input("搜索列: ").strip()
        pattern = input("关键词: ").strip()
        result = fuzzy_match(self.df, col, pattern)
        print(f"\n找到 {len(result)} 条匹配记录:")
        print(result.head(20).to_string())
        self._ask_save_result(result, "是否保存匹配结果? (y/n): ")

    def _op_range_lookup(self):
        col = input("数值列: ").strip()
        print("区间格式: 0,60,80,100 (表示 0-60, 60-80, 80-100)")
        raw = input("分割点: ").strip()
        thresholds = [float(v.strip()) for v in raw.split(',')]
        labels = input("区间标签 (逗号分隔, 直接回车=自动): ").strip()
        labels = [l.strip() for l in labels.split(',')] if labels else None
        ranges = [(thresholds[i], thresholds[i+1]) for i in range(len(thresholds) - 1)]
        result = range_lookup(self.df, col, ranges, labels)
        self.df = result
        print(f"✅ 已添加分类列: {col}_bin")
        print(self.df[[col, f'{col}_bin']].head(10).to_string())

    # ============================================================
    #  3. 数据清洗菜单
    # ============================================================

    def _menu_cleaning(self):
        while True:
            print(f"""
┌─── 数据清洗 ─────────────────────────────────────────┐
│  当前数据: {self._data_status():<44} │
├──────────────────────────────────────────────────────┤
│  1. 🔍 查看缺失值报告                                 │
│  2. 🩹 处理缺失值  (删除/填充/自动)                  │
│  3. 🩹 填充缺失值  (前向/后向/均值/中位数/众数)     │
│  4. 🔍 异常值检测报告                                 │
│  5. ✂️  移除异常值行                                  │
│  6. 🔄 删除重复行                                    │
│  7. 🧽 清理列名和空白                                 │
│  8. 📐 Min-Max 归一化                                │
│  9. 📐 Z-Score 标准化                                │
│  10. 📐 对数变换 (偏态处理)                          │
│  0. ↩️  返回主菜单                                    │
└──────────────────────────────────────────────────────┘
            """)
            choice = input("👉 请选择: ").strip()

            if choice == '0':
                break
            elif not self._check_data():
                continue

            try:
                if choice == '1':
                    print("\n--- 缺失值报告 ---")
                    print(missing_report(self.df).to_string())
                elif choice == '2':
                    strategy = input("策略 (drop=删除行 / fill=填值 / auto=自动): ").strip()
                    if strategy == 'fill':
                        val = input("填充值 (直接回车=0): ").strip() or 0
                        self.df = handle_missing(self.df, strategy='fill', fill_value=safe_parse_value(val))
                    else:
                        self.df = handle_missing(self.df, strategy=strategy)
                    self._show_data_summary()
                elif choice == '3':
                    method = input("填充方法 (ffill/bfill/mean/median/mode/zero/interpolate): ").strip()
                    self.df = fill_missing(self.df, method=method)
                    self._show_data_summary()
                elif choice == '4':
                    print("\n--- 异常值报告 ---")
                    method = input("检测方法 (iqr/zscore/percentile, 默认iqr): ").strip() or 'iqr'
                    print(outlier_report(self.df, method=method).to_string())
                elif choice == '5':
                    cols = parse_column_list(input("检查的列 (逗号分隔): ").strip())
                    method = input("方法 (iqr/zscore/percentile, 默认iqr): ").strip() or 'iqr'
                    self.df = remove_outliers(self.df, cols, method=method)
                    self._show_data_summary()
                elif choice == '6':
                    cols = input("去重列 (逗号分隔, 回车=全部列): ").strip()
                    subset = parse_column_list(cols) if cols else None
                    self.df = drop_duplicates_custom(self.df, subset)
                    self._show_data_summary()
                elif choice == '7':
                    self.df = clean_column_names(self.df)
                    self.df = strip_whitespace(self.df)
                    self._show_data_summary()
                elif choice == '8':
                    cols = input("归一化列 (逗号分隔, 回车=全部数值列): ").strip()
                    cols = parse_column_list(cols) if cols else None
                    self.df = min_max_scale(self.df, cols)
                    print("✅ Min-Max 归一化完成 (范围 0-1)")
                elif choice == '9':
                    cols = input("标准化列 (逗号分隔, 回车=全部数值列): ").strip()
                    cols = parse_column_list(cols) if cols else None
                    self.df = z_score_standardize(self.df, cols)
                    print("✅ Z-Score 标准化完成 (均值=0, 标准差=1)")
                elif choice == '10':
                    cols = input("变换列 (逗号分隔, 回车=全部数值列): ").strip()
                    cols = parse_column_list(cols) if cols else None
                    self.df = log_transform(self.df, cols)
                    print("✅ 对数变换完成")
                else:
                    print("❌ 无效选择")
            except Exception as e:
                print(f"❌ 错误: {e}")

    # ============================================================
    #  4. 数据可视化菜单
    # ============================================================

    def _menu_visualization(self):
        while True:
            print(f"""
┌─── 数据可视化 ───────────────────────────────────────┐
│  当前数据: {self._data_status():<44} │
│  输出目录: {CHART_DIR:<43} │
├─────────────────────── 静态图表 ──────────────────────┤
│  1. 📊 柱状图      6. 📦 箱线图                      │
│  2. 📈 折线图      7. 🔥 热力图                      │
│  3. 🥧 饼图        8. 🔗 相关系数热力图              │
│  4. 🎯 散点图      9. ⏰ 时间序列图                  │
│  5. 📊 直方图      10. 🗂️  组合仪表板               │
├──────────────────── 交互式图表 (浏览器) ──────────────┤
│  11. 📊 柱状图     16. 🔗 相关系数热力图             │
│  12. 📈 折线图     17. ⏰ 时间序列图                 │
│  13. 🥧 饼图       18. 🎯 散点图 (缩放/悬停)        │
│  14. 📦 箱线图     19. 🌞 旭日图/矩形树图           │
│  15. 🔥 热力图     20. 🗂️  交互仪表板               │
│  0. ↩️  返回主菜单                                    │
└──────────────────────────────────────────────────────┘
            """)
            choice = input("👉 请选择: ").strip()

            if choice == '0':
                break
            elif not self._check_data():
                continue

            try:
                if choice == '1':
                    self._chart_bar()
                elif choice == '2':
                    self._chart_line()
                elif choice == '3':
                    self._chart_pie()
                elif choice == '4':
                    self._chart_scatter()
                elif choice == '5':
                    self._chart_hist()
                elif choice == '6':
                    self._chart_box()
                elif choice == '7':
                    self._chart_heatmap()
                elif choice == '8':
                    self._chart_corr_heatmap()
                elif choice == '9':
                    self._chart_timeseries()
                elif choice == '10':
                    self._chart_dashboard()
                elif choice == '11':
                    self._ichart_bar()
                elif choice == '12':
                    self._ichart_line()
                elif choice == '13':
                    self._ichart_pie()
                elif choice == '14':
                    self._ichart_box()
                elif choice == '15':
                    self._ichart_heatmap()
                elif choice == '16':
                    self._ichart_corr()
                elif choice == '17':
                    self._ichart_timeseries()
                elif choice == '18':
                    self._ichart_scatter()
                elif choice == '19':
                    self._ichart_hierarchy()
                elif choice == '20':
                    self._ichart_dashboard()
                else:
                    print("❌ 无效选择")
            except Exception as e:
                print(f"❌ 错误: {e}")

    def _chart_bar(self):
        print(f"列: {', '.join(self.df.columns.tolist())}")
        x = input("X轴列 (类别): ").strip()
        y = input("Y轴列 (数值): ").strip()
        if not x or not y:
            print("❌ 请填写X轴和Y轴列名")
            return
        filename = input("文件名 (如 bar.png): ").strip() or 'bar_chart.png'
        path = bar_chart(self.df, x=x, y=y, filename=filename)
        print(f"✅ 柱状图已保存: {path}")

    def _chart_line(self):
        x = input("X轴列: ").strip()
        y_cols = input("Y轴列 (多列用逗号, 如 收入,成本): ").strip()
        y_list = parse_column_list(y_cols)
        if not y_list:
            print("❌ 请至少输入一个Y轴列")
            return
        filename = input("文件名: ").strip() or 'line_chart.png'
        if len(y_list) > 1:
            path = multi_line_chart(self.df, x=x, y_columns=y_list, filename=filename)
        else:
            path = line_chart(self.df, x=x, y=y_list[0], filename=filename)
        print(f"✅ 折线图已保存: {path}")

    def _chart_pie(self):
        labels = input("标签列: ").strip()
        values = input("数值列: ").strip()
        if not labels or not values:
            print("❌ 请填写标签列和数值列")
            return
        donut = input("环形图? (y/n): ").strip().lower() == 'y'
        filename = input("文件名: ").strip() or 'pie_chart.png'
        path = pie_chart(self.df, labels_col=labels, values_col=values, donut=donut, filename=filename)
        print(f"✅ 饼图已保存: {path}")

    def _chart_scatter(self):
        x = input("X轴列: ").strip()
        y = input("Y轴列: ").strip()
        if not x or not y:
            print("❌ 请填写X轴和Y轴列名")
            return
        color = input("颜色映射列 (直接回车=无): ").strip() or None
        filename = input("文件名: ").strip() or 'scatter.png'
        path = scatter_plot(self.df, x=x, y=y, color=color, filename=filename)
        print(f"✅ 散点图已保存: {path}")

    def _chart_hist(self):
        col = input("列名: ").strip()
        if not col:
            print("❌ 请输入列名")
            return
        bins = input("柱数 (默认20): ").strip()
        try:
            bins = int(bins) if bins else 20
        except ValueError:
            print("❌ 柱数请输入数字")
            return
        filename = input("文件名: ").strip() or 'histogram.png'
        path = histogram(self.df, column=col, bins=bins, filename=filename)
        print(f"✅ 直方图已保存: {path}")

    def _chart_box(self):
        mode = input("模式: 1=单列分布, 2=分组对比 (1/2): ").strip()
        filename = input("文件名: ").strip() or 'boxplot.png'
        if mode == '1':
            col = input("列名: ").strip()
            if not col:
                print("❌ 请输入列名")
                return
            path = box_plot(self.df, column=col, filename=filename)
        else:
            x = input("分组列 (X): ").strip()
            y = input("数值列 (Y): ").strip()
            if not x or not y:
                print("❌ 请填写X分组列和Y数值列")
                return
            path = box_plot(self.df, x=x, y=y, filename=filename)
        print(f"✅ 箱线图已保存: {path}")

    def _chart_heatmap(self):
        print("使用当前数据的前30列数值数据生成热力图...")
        numeric = self.df.select_dtypes(include=[np.number])
        if numeric.shape[1] > 30:
            numeric = numeric.iloc[:, :30]
        filename = input("文件名: ").strip() or 'heatmap.png'
        path = heatmap(numeric, filename=filename)
        print(f"✅ 热力图已保存: {path}")

    def _chart_corr_heatmap(self):
        filename = input("文件名: ").strip() or 'correlation.png'
        method = input("方法 (pearson/spearman/kendall, 默认pearson): ").strip() or 'pearson'
        path = correlation_heatmap(self.df, method=method, filename=filename)
        print(f"✅ 相关性热力图已保存: {path}")

    def _chart_timeseries(self):
        print(f"列: {', '.join(self.df.columns.tolist())}")
        date_col = input("日期列: ").strip()
        val_cols = parse_column_list(input("数值列 (逗号分隔): ").strip())
        if not val_cols:
            print("❌ 请至少输入一个数值列")
            return
        resample = input("重采样 (M=月, W=周, Q=季度, 回车=不重采样): ").strip() or None
        filename = input("文件名: ").strip() or 'timeseries.png'
        path = time_series(self.df, date_col=date_col, value_cols=val_cols,
                    resample=resample, filename=filename)
        print(f"✅ 时间序列图已保存: {path}")

    def _chart_dashboard(self):
        print("组合仪表板 - 选择几个图表组合在一起")
        n = int(input("子图数量 (1-6): ").strip() or '2')
        plots = []
        for i in range(n):
            print(f"\n--- 子图 {i+1} ---")
            plot_type = input("类型 (bar/line/pie/hist/box/scatter): ").strip()
            title = input("标题: ").strip() or f"Chart {i+1}"
            plots.append({
                'type': plot_type,
                'title': title,
                'data': self.df,
                'params': self._get_plot_params(plot_type),
            })
        filename = input("文件名: ").strip() or 'dashboard.png'
        path = dashboard_layout(plots, filename=filename)
        print(f"✅ 仪表板已保存: {path}")

    def _get_plot_params(self, plot_type: str) -> dict:
        """根据图表类型获取参数"""
        if plot_type == 'bar':
            x = input("  X轴: ").strip()
            y = input("  Y轴: ").strip()
            return {'x': x, 'y': y}
        elif plot_type == 'line':
            x = input("  X轴: ").strip()
            y = input("  Y轴: ").strip()
            return {'x': x, 'y': y}
        elif plot_type == 'pie':
            labels = input("  标签列: ").strip()
            values = input("  数值列: ").strip()
            return {'labels_col': labels, 'values_col': values}
        elif plot_type == 'hist':
            col = input("  列: ").strip()
            return {'column': col}
        elif plot_type == 'box':
            col = input("  列: ").strip()
            return {'column': col}
        elif plot_type == 'scatter':
            x = input("  X轴: ").strip()
            y = input("  Y轴: ").strip()
            return {'x': x, 'y': y}
        return {}

    # ============================================================
    #  交互式图表 (Plotly)
    # ============================================================

    def _ichart_bar(self):
        x = input("X轴列: ").strip()
        y = input("Y轴列: ").strip()
        if not x or not y:
            print("❌ 请填写X轴和Y轴列名")
            return
        filename = input("文件名 (如 ibar.html): ").strip() or 'interactive_bar.html'
        path = ibar_chart(self.df, x=x, y=y, filename=filename)
        print(f"✅ 交互式柱状图: {path}")

    def _ichart_line(self):
        x = input("X轴列: ").strip()
        y_cols = input("Y轴列 (多列逗号分隔): ").strip()
        y = parse_column_list(y_cols)
        if not y:
            print("❌ 请至少输入一个Y轴列")
            return
        filename = input("文件名: ").strip() or 'interactive_line.html'
        path = iline_chart(self.df, x=x, y=y[0] if len(y) == 1 else y, filename=filename)
        print(f"✅ 交互式折线图: {path}")

    def _ichart_pie(self):
        labels = input("标签列: ").strip()
        values = input("数值列: ").strip()
        if not labels or not values:
            print("❌ 请填写标签列和数值列")
            return
        donut = input("环形图? (y/n): ").strip().lower() == 'y'
        filename = input("文件名: ").strip() or 'interactive_pie.html'
        path = ipie_chart(self.df, labels_col=labels, values_col=values, donut=donut, filename=filename)
        print(f"✅ 交互式饼图: {path}")

    def _ichart_box(self):
        x = input("分组列 (直接回车=单列): ").strip() or None
        y = input("数值列: ").strip()
        if not y:
            print("❌ 请输入数值列")
            return
        filename = input("文件名: ").strip() or 'interactive_box.html'
        path = ibox_plot(self.df, x=x, y=y, filename=filename)
        print(f"✅ 交互式箱线图: {path}")

    def _ichart_heatmap(self):
        numeric = self.df.select_dtypes(include=[np.number])
        if numeric.shape[1] > 30:
            numeric = numeric.iloc[:, :30]
        filename = input("文件名: ").strip() or 'interactive_heatmap.html'
        path = iheatmap(numeric, filename=filename)
        print(f"✅ 交互式热力图: {path}")

    def _ichart_corr(self):
        method = input("方法 (pearson/spearman/kendall): ").strip() or 'pearson'
        filename = input("文件名: ").strip() or 'interactive_corr.html'
        path = icorrelation_heatmap(self.df, method=method, filename=filename)
        print(f"✅ 交互式相关性图: {path}")

    def _ichart_timeseries(self):
        date_col = input("日期列: ").strip()
        val_cols = parse_column_list(input("数值列 (逗号分隔): ").strip())
        if not val_cols:
            print("❌ 请至少输入一个数值列")
            return
        resample = input("重采样 (M/W/Q, 回车跳过): ").strip() or None
        filename = input("文件名: ").strip() or 'interactive_timeseries.html'
        path = itime_series(self.df, date_col=date_col, value_cols=val_cols, resample=resample, filename=filename)
        print(f"✅ 交互式时间序列: {path}")

    def _ichart_scatter(self):
        x = input("X轴列: ").strip()
        y = input("Y轴列: ").strip()
        if not x or not y:
            print("❌ 请填写X轴和Y轴列名")
            return
        color = input("颜色映射列 (回车=无): ").strip() or None
        filename = input("文件名: ").strip() or 'interactive_scatter.html'
        path = iscatter_plot(self.df, x=x, y=y, color=color, filename=filename)
        print(f"✅ 交互式散点图: {path}")

    def _ichart_hierarchy(self):
        print("层级图类型: 1.旭日图  2.矩形树图")
        t = input("👉 ").strip()
        path_cols = parse_column_list(input("层级列 (逗号分隔, 如 部门,职位): ").strip())
        if not path_cols:
            print("❌ 请至少输入一个层级列")
            return
        values = input("数值列 (回车=计数): ").strip() or None
        filename = input("文件名: ").strip() or 'interactive_hierarchy.html'
        if t == '2':
            path = itreemap(self.df, path=path_cols, values=values, filename=filename)
        else:
            path = isunburst(self.df, path=path_cols, values=values, filename=filename)
        print(f"✅ 交互式层级图: {path}")

    def _ichart_dashboard(self):
        n = int(input("子图数量 (1-4): ").strip() or '2')
        charts = []
        for i in range(n):
            print(f"\n子图 {i+1}:")
            chart_type = input("  类型 (bar/line/pie): ").strip()
            title = input("  标题: ").strip()
            config = {'type': chart_type, 'title': title}
            if chart_type == 'bar':
                config['x'] = input("  X轴: ").strip()
                config['y'] = input("  Y轴: ").strip()
            elif chart_type == 'line':
                config['x'] = input("  X轴: ").strip()
                config['y'] = input("  Y轴: ").strip()
            elif chart_type == 'pie':
                config['labels_col'] = input("  标签列: ").strip()
                config['values_col'] = input("  数值列: ").strip()
            charts.append(config)
        filename = input("文件名: ").strip() or 'interactive_dashboard.html'
        path = idashboard(self.df, charts=charts, filename=filename)
        print(f"✅ 交互式仪表板: {path}")

    # ============================================================
    #  5. 数据分析菜单
    # ============================================================

    def _menu_analysis(self):
        while True:
            print(f"""
┌─── 数据分析 ─────────────────────────────────────────┐
│  当前数据: {self._data_status():<44} │
├──────────────────────────────────────────────────────┤
│  1. 📊 描述统计      (count/mean/std/min/max...)     │
│  2. 📋 频数统计      (某列的取值分布)                │
│  3. 📝 列摘要        (所有列的详细摘要)              │
│  4. 🔗 相关系数矩阵  (数值列相关度)                  │
│  5. 🔍 最强相关对    (TOP关联变量)                   │
│  6. 🎯 目标变量关联  (找与某变量相关的所有列)        │
│  7. 📄 生成文本报告  (控制台输出)                    │
│  8. 🌐 生成HTML报告  (网页格式,含图表)               │
│  0. ↩️  返回主菜单                                    │
└──────────────────────────────────────────────────────┘
            """)
            choice = input("👉 请选择: ").strip()

            if choice == '0':
                break
            elif not self._check_data():
                continue

            try:
                if choice == '1':
                    print("\n--- 描述统计 ---")
                    print(describe_data(self.df).to_string())
                elif choice == '2':
                    col = input("列名: ").strip()
                    n = input("显示前N条 (默认20): ").strip()
                    n = int(n) if n else 20
                    print(f"\n--- {col} 频数统计 ---")
                    print(frequency_table(self.df, col, top_n=n).to_string())
                elif choice == '3':
                    print("\n--- 列摘要 ---")
                    for s in all_columns_summary(self.df):
                        print(f"\n{s['column']} ({s['dtype']}):")
                        print(f"  非空: {s['count']}, 缺失: {s['missing']} ({s['missing_pct']}%), "
                              f"唯一值: {s['unique']} ({s['unique_pct']}%)")
                        if 'mean' in s:
                            print(f"  均值={s['mean']}, 中位数={s['median']}, "
                                  f"标准差={s['std']}, 范围=[{s['min']}, {s['max']}]")
                elif choice == '4':
                    method = input("方法 (pearson/spearman/kendall, 默认pearson): ").strip() or 'pearson'
                    corr = correlation_matrix(self.df, method=method)
                    print("\n--- 相关系数矩阵 ---")
                    pd.set_option('display.max_columns', 20)
                    print(corr.round(2).to_string())
                elif choice == '5':
                    method = input("方法 (pearson/spearman/kendall, 默认pearson): ").strip() or 'pearson'
                    corr = correlation_matrix(self.df, method=method)
                    print("\n--- 最强相关对 ---")
                    print(top_correlations(corr, top_n=10).to_string())
                elif choice == '6':
                    target = input("目标列: ").strip()
                    threshold = float(input("相关系数阈值 (默认0.3): ").strip() or '0.3')
                    print(f"\n--- 与 {target} 相关的变量 ---")
                    print(find_related_pairs(self.df, target, threshold).to_string())
                elif choice == '7':
                    title = input("报告标题 (回车=默认): ").strip() or "数据分析报告"
                    report_text = generate_report(self.df, title=title)
                    print("\n" + report_text)
                    save = input("保存到文件? (y/n): ").strip().lower()
                    if save == 'y':
                        path = os.path.join(REPORT_DIR, 'report.txt')
                        with open(path, 'w', encoding='utf-8') as f:
                            f.write(report_text)
                        print(f"✅ 已保存: {path}")
                elif choice == '8':
                    title = input("报告标题 (回车=默认): ").strip() or "数据分析报告"
                    path = generate_html_report(self.df, title=title)
                    print(f"✅ HTML 报告已生成: {path}")
                else:
                    print("❌ 无效选择")
            except Exception as e:
                print(f"❌ 错误: {e}")

    # ============================================================
    #  6. 批量处理菜单
    # ============================================================

    def _menu_batch(self):
        print("""
┌─── 批量处理 ─────────────────────────────────────────┐
│  对多个文件执行相同操作，自动读取→处理→输出          │
└──────────────────────────────────────────────────────┘
        """)
        pattern = input("文件匹配 (如 data/*.csv 或 .xlsx): ").strip()

        files = find_files(patterns=[pattern] if pattern.startswith('.') else None)
        if pattern and not pattern.startswith('.'):
            import glob
            files = glob.glob(pattern, recursive=True)

        if not files:
            print("❌ 未找到匹配文件")
            return

        print(f"\n找到 {len(files)} 个文件:")
        for f in files[:10]:
            print(f"  {f}")
        if len(files) > 10:
            print(f"  ... 还有 {len(files)-10} 个")

        print("""
批量操作类型:
  1. 合并所有文件
  2. 逐文件处理并分别输出
  3. 合并后筛选/排序
  4. 合并后去重
  5. 合并后分组聚合
        """)
        choice = input("👉 请选择: ").strip()

        try:
            if choice == '1':
                # 合并读取
                self.df = read_multiple(files, concat=True)
                self._show_data_summary()
                save = input("保存合并结果? (y/n): ").strip().lower()
                if save == 'y':
                    fmt = input("格式 (csv/xlsx): ").strip() or 'csv'
                    path = os.path.join(OUTPUT_DIR, f"merged.{fmt}")
                    write_file(self.df, path)

            elif choice == '2':
                operation_desc = input("操作描述 (如 '删除空行'): ").strip()
                output_fmt = input("输出格式 (csv/xlsx, 默认csv): ").strip() or 'csv'

                def simple_op(df):
                    return df.dropna()

                batch_process(pattern, simple_op, output_fmt=output_fmt)
                print("✅ 批量处理完成")

            elif choice == '3':
                # 合并后筛选排序
                self.df = read_multiple(files, concat=True)
                self._show_data_summary()
                col = input("筛选列: ").strip()
                op = input("运算符 (>, <, ==, contains...): ").strip()
                val = safe_parse_value(input("值: ").strip())
                self.df = filter_by_value(self.df, col, op, val)
                sort_cols = parse_column_list(input("排序列 (逗号分隔, 回车跳过): ").strip())
                if sort_cols:
                    self.df = sort_data(self.df, sort_cols)
                self._ask_save_result(self.df)

            elif choice == '4':
                self.df = read_multiple(files, concat=True)
                cols = input("去重列 (逗号分隔, 回车=所有列): ").strip()
                subset = parse_column_list(cols) if cols else None
                self.df = drop_duplicates_custom(self.df, subset)
                self._show_data_summary()
                self._ask_save_result(self.df)

            elif choice == '5':
                self.df = read_multiple(files, concat=True)
                by = parse_column_list(input("分组列 (逗号分隔): ").strip())
                raw = input("聚合配置 (如 金额=sum, 数量=count): ").strip()
                agg_dict = {}
                for pair in raw.split(','):
                    c, f = pair.strip().split('=')
                    agg_dict[c.strip()] = f.strip()
                result = group_aggregate(self.df, by, agg_dict)
                print(f"\n--- 聚合结果 ({len(result)} 组) ---")
                print(result.to_string())
                self._ask_save_result(result)

        except Exception as e:
            print(f"❌ 错误: {e}")
            traceback.print_exc()

    # ============================================================
    #  7. PDF 导出菜单
    # ============================================================

    def _menu_pdf_export(self):
        if not self._check_data():
            return
        while True:
            print(f"""
┌─── PDF 导出 ─────────────────────────────────────────┐
│  当前数据: {self._data_status():<44} │
├──────────────────────────────────────────────────────┤
│  1. 📄 导出数据表为 PDF  (表格格式)                  │
│  2. 📊 导出分析报告为 PDF (含统计+图表)              │
│  0. ↩️  返回主菜单                                    │
└──────────────────────────────────────────────────────┘
            """)
            choice = input("👉 请选择: ").strip()

            try:
                if choice == '0':
                    break
                elif choice == '1':
                    title = input("标题 (回车=默认): ").strip() or "数据表"
                    orient = input("方向 (L=横向/P=纵向, 默认L): ").strip() or 'L'
                    path = export_to_pdf(self.df, title=title, orientation=orient)
                    print(f"✅ PDF 已导出: {path}")
                elif choice == '2':
                    title = input("报告标题 (回车=默认): ").strip() or "数据分析报告"
                    print("正在生成 PDF 报告（含统计+图表）...")
                    path = export_report_to_pdf(self.df, title=title)
                    print(f"✅ PDF 报告已导出: {path}")
                else:
                    print("❌ 无效选择")
            except Exception as e:
                print(f"❌ 错误: {e}")

    # ============================================================
    #  辅助方法
    # ============================================================

    def _ask_save_result(self, df, prompt: str = "是否保存结果? (y/n): "):
        """询问是否保存结果"""
        save = input(prompt).strip().lower()
        if save == 'y':
            fmt = input("格式 (csv/xlsx/json, 默认csv): ").strip() or 'csv'
            name = input("文件名 (如 result.csv): ").strip() or f"result.{fmt}"
            path = os.path.join(OUTPUT_DIR, name)
            write_file(df, path)
            print(f"✅ 已保存: {path}")

    @staticmethod
    def _clear_screen():
        os.system('clear' if os.name == 'posix' else 'cls')


def main():
    """程序入口"""
    try:
        app = DataProcessor()
        app.run()
    except KeyboardInterrupt:
        print("\n\n👋 已退出")
    except Exception as e:
        print(f"\n❌ 程序异常: {e}")
        traceback.print_exc()


if __name__ == '__main__':
    main()
