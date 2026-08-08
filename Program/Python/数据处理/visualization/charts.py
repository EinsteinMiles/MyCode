"""
数据可视化：柱状图、折线图、饼图、散点图、直方图、箱线图、热力图等
自动处理大数据量：智能限制显示数量、自适应尺寸、标签优化
"""
import os
import matplotlib
matplotlib.use('Agg')  # 非交互式后端
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import seaborn as sns
import pandas as pd
import numpy as np

from config import CHART_DIR, CHART_DPI, CHART_FIGSIZE, CHART_STYLE, FONT_FAMILY, logger

# 设置中文字体
plt.rcParams['font.family'] = 'sans-serif'
plt.rcParams['font.sans-serif'] = FONT_FAMILY
plt.rcParams['axes.unicode_minus'] = False
plt.style.use(CHART_STYLE)

# ---- 大数据量阈值 ----
MAX_BAR_ITEMS = 20       # 柱状图超过此数自动切换水平 + top-N
MAX_PIE_ITEMS = 8        # 饼图超过此数归为"其他"
MAX_SCATTER_POINTS = 2000 # 散点图超过此数自动采样
MAX_BOX_CATEGORIES = 25  # 箱线图超过此数自动限制
TICK_STEP_THRESHOLD = 12 # x轴标签超过此数开始间隔显示
MAX_LINES = 8            # 多线图超过此数限制
MAX_STACK_COLS = 8       # 堆叠柱状图超过此数列数限制
LABEL_MAX_LEN = 8        # 标签超过此长度自动截断
FORCE_HORIZONTAL_LEN = 6 # 平均标签长度超过此值强制水平柱状图


# ================================================================
#  内部工具函数
# ================================================================

def _save_and_close(fig, filename: str, output_dir: str = None) -> str:
    """保存图表并关闭"""
    if output_dir is None:
        output_dir = CHART_DIR
    os.makedirs(output_dir, exist_ok=True)
    path = os.path.join(output_dir, filename)
    fig.savefig(path, dpi=CHART_DPI, bbox_inches='tight', facecolor='white')
    plt.close(fig)
    logger.info(f"图表已保存: {path}")
    return path


def _check_col(df: pd.DataFrame, col: str, label: str = "图表"):
    """校验单列是否存在"""
    if col and col not in df.columns:
        raise ValueError(
            f"❌ {label}: 列 '{col}' 不存在。\n"
            f"   可用列: {', '.join(df.columns.tolist())}"
        )


def _check_cols(df: pd.DataFrame, cols: list, label: str = "图表"):
    """校验多列是否存在"""
    for c in cols:
        _check_col(df, c, label)


def _setup_figure(figsize: tuple = None, title: str = None):
    """创建并配置图表"""
    fig, ax = plt.subplots(figsize=figsize or CHART_FIGSIZE)
    if title:
        ax.set_title(title, fontsize=14, fontweight='bold', pad=15)
    return fig, ax


def _auto_figsize(n_items: int, base: tuple = None) -> tuple:
    """根据数据量自动计算合适的图表尺寸"""
    base_w, base_h = base or CHART_FIGSIZE
    if n_items <= 10:
        return base
    # 每增加 10 项，宽度增加 1.5 英寸
    extra = (n_items - 10) / 10 * 1.5
    return (base_w + extra, base_h)


def _truncate_labels(labels: list, max_len: int = None) -> list:
    """截断过长的标签，添加省略号"""
    if max_len is None:
        max_len = LABEL_MAX_LEN
    result = []
    for s in labels:
        s = str(s)
        if len(s) > max_len:
            result.append(s[:max_len - 1] + '…')
        else:
            result.append(s)
    return result


def _avg_label_len(labels) -> float:
    """计算标签平均长度"""
    if not labels:
        return 0
    return sum(len(str(s)) for s in labels) / len(labels)


def _smart_ticks(ax, labels: list, axis: str = 'x', threshold: int = None):
    """智能刻度间隔：基于标签数量和长度计算最优步长"""
    n = len(labels)
    if threshold is None:
        avg_len = _avg_label_len(labels)
        # 长标签需要更大步长（显示更少标签）
        if avg_len > 10:
            threshold = 5
        elif avg_len > 6:
            threshold = 8
        else:
            threshold = TICK_STEP_THRESHOLD

    if n <= threshold:
        return

    step = max(1, n // threshold)
    if axis == 'x':
        for i, label in enumerate(ax.get_xticklabels()):
            if i % step != 0:
                label.set_visible(False)
    else:
        for i, label in enumerate(ax.get_yticklabels()):
            if i % step != 0:
                label.set_visible(False)


def _smart_rotation(labels) -> int:
    """根据标签数量和平均长度自动选择旋转角度"""
    n = len(labels) if isinstance(labels, (list, pd.Index)) else labels
    avg_len = _avg_label_len(labels) if isinstance(labels, (list, pd.Index)) else 4

    if n <= 6 and avg_len <= 6:
        return 0
    elif n <= 12 and avg_len <= 8:
        return 45
    else:
        return 90


def _label_fontsize(n_items: int, avg_len: float = 5) -> int:
    """根据数据量和标签长度计算最佳字体大小"""
    base = 10
    # 项目多 → 缩小
    base -= max(0, (n_items - 10) // 5)
    # 标签长 → 缩小
    base -= max(0, (avg_len - 6) // 2)
    return max(5, base)


def _auto_sample(df: pd.DataFrame, max_points: int = None) -> pd.DataFrame:
    """数据点过多时随机采样"""
    if max_points is None:
        max_points = MAX_SCATTER_POINTS
    if len(df) <= max_points:
        return df
    logger.warning(f"  数据点过多 ({len(df)}), 随机采样 {max_points} 个点用于绘图")
    return df.sample(n=max_points, random_state=42)


def _limit_data(data: pd.DataFrame, n: int, y_col: str = None,
                label: str = "图表") -> pd.DataFrame:
    """限制数据行数，超出时发出警告"""
    if len(data) <= n:
        return data
    logger.warning(f"  {label}: 数据过多 ({len(data)} 项)，仅显示前 {n} 项")
    return data.head(n)


# ================================================================
#  图表函数
# ================================================================

def bar_chart(df: pd.DataFrame, x: str, y: str, title: str = None,
              color: str = '#4A90D9', horizontal: bool = False,
              sort: bool = True, top_n: int = None,
              filename: str = 'bar_chart.png',
              output_dir: str = None) -> str:
    """柱状图 - 数据过多/标签过长自动优化

    Args:
        df: 数据
        x: X轴列（类别）
        y: Y轴列（数值）
        horizontal: True=水平柱状图
        sort: 是否按值排序
        top_n: 只显示前N条
    """
    _check_col(df, x, '柱状图')
    _check_col(df, y, '柱状图')

    data = df.copy()
    # Flatten MultiIndex columns
    if isinstance(data.columns, pd.MultiIndex):
        data.columns = ['_'.join(str(c) for c in col).strip('_') for col in data.columns.values]
        if isinstance(y, tuple):
            y = '_'.join(str(c) for c in y).strip('_')

    n = len(data)

    # 排序
    if sort:
        data = data.sort_values(y, ascending=horizontal)

    # 自动限制数量
    auto_limit = top_n or (MAX_BAR_ITEMS if n > MAX_BAR_ITEMS else None)
    if auto_limit:
        data = data.head(auto_limit)
        n = len(data)

    # 标签处理：截断长标签
    raw_labels = data[x].astype(str).tolist()
    avg_len = _avg_label_len(raw_labels)
    truncated = _truncate_labels(raw_labels)

    # 自动水平：标签太多 或 标签太长 → 水平柱状图更清晰
    auto_horizontal = False
    if not horizontal and (n > MAX_BAR_ITEMS or avg_len > FORCE_HORIZONTAL_LEN):
        horizontal = True
        auto_horizontal = True
        logger.info(f"  柱状图: 标签名较长(平均{avg_len:.0f}字)，自动切换为水平柱状图")
        logger.info(f"    → 横轴={y}(数值), 纵轴={x}(类别)")

    # 自适应尺寸
    figsize = _auto_figsize(n)
    fig, ax = _setup_figure(figsize=figsize,
                            title=title or f'{y} by {x} (共{n}项)')

    # 颜色
    if n > 5:
        colors = sns.color_palette('viridis', n)
    else:
        colors = color

    if horizontal:
        # 水平柱状图：类别在纵轴(y)，数值在横轴(x)
        bar_width = min(0.8, max(0.3, 1.0 - n * 0.02))
        ax.barh(truncated, data[y], color=colors, edgecolor='white',
                height=bar_width)
        ax.set_xlabel(y)      # 横轴 = 数值
        ax.set_ylabel(x)      # 纵轴 = 类别
        # 水平图 y 轴反转（顶部最大）
        ax.invert_yaxis()
    else:
        # 垂直柱状图：类别在横轴(x)，数值在纵轴(y)
        bar_width = min(0.8, max(0.3, 1.0 - n * 0.03))
        ax.bar(truncated, data[y], color=colors, edgecolor='white',
               width=bar_width)
        ax.set_xlabel(x)      # 横轴 = 类别
        ax.set_ylabel(y)      # 纵轴 = 数值
        rotation = _smart_rotation(raw_labels)
        plt.xticks(rotation=rotation, ha='right' if rotation else 'center')

    # 数值标签：柱数 ≤ 12 时才显示
    _add_value_labels(ax, horizontal=horizontal, max_items=12)

    # 动态字体
    fontsize = _label_fontsize(n, avg_len)
    ax.tick_params(axis='y' if horizontal else 'x', labelsize=fontsize)

    _smart_ticks(ax, raw_labels, axis='y' if horizontal else 'x')

    return _save_and_close(fig, filename, output_dir)


def line_chart(df: pd.DataFrame, x: str, y: str, title: str = None,
               color: str = '#E74C3C', marker: str = 'o',
               filename: str = 'line_chart.png',
               output_dir: str = None) -> str:
    """折线图 - 标签过多时自动间隔 + 截断"""
    _check_col(df, x, '折线图')
    _check_col(df, y, '折线图')

    n = len(df)
    raw_labels = df[x].astype(str).tolist()
    avg_len = _avg_label_len(raw_labels)
    truncated = _truncate_labels(raw_labels)

    figsize = _auto_figsize(n, base=(10, 5))
    fig, ax = _setup_figure(figsize=figsize, title=title or f'{y} over {x}')

    # 数据点多时不显示 marker
    use_marker = marker if n <= 30 else ''
    marker_size = max(2, 6 - n // 50) if n <= 30 else 0

    ax.plot(truncated, df[y], color=color,
            marker=use_marker, linewidth=2, markersize=marker_size)
    ax.set_xlabel(x)
    ax.set_ylabel(y)

    rotation = _smart_rotation(raw_labels)
    plt.xticks(rotation=rotation, ha='right' if rotation else 'center')
    ax.grid(True, alpha=0.3)
    _smart_ticks(ax, raw_labels)

    # 标签多时减小字体
    fontsize = _label_fontsize(n, avg_len)
    ax.tick_params(axis='x', labelsize=fontsize)

    return _save_and_close(fig, filename, output_dir)


def multi_line_chart(df: pd.DataFrame, x: str, y_columns: list[str],
                     title: str = None, filename: str = 'multi_line.png',
                     output_dir: str = None) -> str:
    """多线折线图（多条Y线）- 线条过多时自动限制"""
    _check_col(df, x, '多线折线图')
    _check_cols(df, y_columns, '多线折线图')

    # 线条过多时限制并警告
    if len(y_columns) > MAX_LINES:
        logger.warning(f"  多线折线图: {len(y_columns)} 条线过多，仅显示前 {MAX_LINES} 条")
        y_columns = y_columns[:MAX_LINES]

    n = len(df)
    raw_labels = df[x].astype(str).tolist()
    avg_len = _avg_label_len(raw_labels)
    truncated = _truncate_labels(raw_labels)

    figsize = _auto_figsize(n, base=(12, 6))
    fig, ax = _setup_figure(figsize=figsize, title=title or '趋势对比')

    colors = sns.color_palette('husl', len(y_columns))
    line_styles = ['-', '--', '-.', ':'] * (len(y_columns) // 4 + 1)
    use_marker = n <= 30

    for i, col in enumerate(y_columns):
        ax.plot(truncated, df[col],
                color=colors[i], linestyle=line_styles[i],
                linewidth=2,
                marker='o' if use_marker else '',
                markersize=4 if use_marker else 0,
                label=col)

    ax.set_xlabel(x)
    ax.set_ylabel('值')
    ncol = 2 if len(y_columns) > 4 else 1
    ax.legend(loc='upper left', frameon=True, ncol=ncol,
              fontsize=max(7, 9 - len(y_columns) // 5))

    rotation = _smart_rotation(raw_labels)
    plt.xticks(rotation=rotation, ha='right' if rotation else 'center')
    ax.grid(True, alpha=0.3)
    ax.tick_params(axis='x', labelsize=_label_fontsize(n, avg_len))
    _smart_ticks(ax, raw_labels)

    return _save_and_close(fig, filename, output_dir)


def pie_chart(df: pd.DataFrame, labels_col: str, values_col: str,
              title: str = None, donut: bool = False,
              filename: str = 'pie_chart.png',
              output_dir: str = None) -> str:
    """饼图 / 环形图 - 项目过多时自动归为"其他"

    Args:
        donut: True=环形图 (中间有洞)
    """
    _check_col(df, labels_col, '饼图')
    _check_col(df, values_col, '饼图')

    data = df.copy()
    n_orig = len(data)

    # 超过阈值：保留 top N，其余归为"其他"
    if n_orig > MAX_PIE_ITEMS:
        data = data.nlargest(MAX_PIE_ITEMS, values_col)
        other_value = df[values_col].sum() - data[values_col].sum()
        if other_value > 0:
            other_row = pd.DataFrame({
                labels_col: [f'其他({n_orig - MAX_PIE_ITEMS}项)'],
                values_col: [other_value]
            })
            data = pd.concat([data, other_row], ignore_index=True)
        logger.warning(f"  饼图: {n_orig} 项过多，保留前 {MAX_PIE_ITEMS} 项，其余归为'其他'")

    n = len(data)

    # 标签处理：截断长标签（饼图保留稍长）
    raw_labels = data[labels_col].astype(str).tolist()
    pie_label_limit = 10  # 饼图标签允许稍长
    display_labels = _truncate_labels(raw_labels, max_len=pie_label_limit)
    avg_len = _avg_label_len(raw_labels)

    # 饼图尺寸随项目数自适应
    pie_size = (10, 8) if n <= 6 else (12, 9) if n <= 10 else (14, 10)
    fig, ax = _setup_figure(figsize=pie_size,
                            title=title or f'{values_col} 分布 (共{n_orig}项)')

    colors = sns.color_palette('Set3', n)
    # "其他"用灰色
    if n_orig > MAX_PIE_ITEMS:
        colors = [c for c in colors]
        colors[-1] = (0.85, 0.85, 0.85)  # 灰色

    # 计算哪些扇区太小（< 5%），跳过百分比标注避免重叠
    values = data[values_col].values
    total = values.sum()
    small_threshold = total * 0.05

    # 构建 autopct 函数：小扇区不显示百分比
    def _safe_autopct(pct):
        return f'{pct:.1f}%' if (pct / 100 * total) >= small_threshold else ''

    # 标签距离：扇区多时推远一点
    label_dist = 1.15 if n <= 6 else 1.2
    pct_dist = 0.75 if donut else (0.6 if n <= 8 else 0.55)

    wedges, texts, autotexts = ax.pie(
        values,
        labels=display_labels,
        autopct=_safe_autopct if n <= 10 else '%1.0f%%',
        colors=colors,
        pctdistance=pct_dist,
        labeldistance=label_dist,
        startangle=90
    )

    if donut:
        centre_circle = plt.Circle((0, 0), 0.55, fc='white', linewidth=0)
        ax.add_artist(centre_circle)

    # 防重叠：项目多/标签长时大幅缩小字体，小扇区更小
    fontsize_text = max(5, 10 - n // 3 - max(0, (avg_len - 6) // 2))
    fontsize_pct = max(5, 9 - n // 3)

    # 逐标签调整：小扇区进一步缩小
    for i, (t, autot) in enumerate(zip(texts, autotexts)):
        slice_val = values[i]
        pct = slice_val / total * 100 if total > 0 else 0
        if pct < 3:  # < 3% 的扇区用更小字体
            t.set_fontsize(max(4, fontsize_text - 2))
            autot.set_fontsize(max(4, fontsize_pct - 2))
        elif pct < 8:
            t.set_fontsize(max(5, fontsize_text - 1))
            autot.set_fontsize(max(5, fontsize_pct - 1))
        else:
            t.set_fontsize(fontsize_text)
            autot.set_fontsize(fontsize_pct)

    return _save_and_close(fig, filename, output_dir)


def scatter_plot(df: pd.DataFrame, x: str, y: str,
                 color: str = None, size: str = None,
                 title: str = None, trendline: bool = True,
                 filename: str = 'scatter.png',
                 output_dir: str = None) -> str:
    """散点图（可选颜色和大小维度、趋势线）
    大数据量时自动采样 + 调整透明度
    """
    _check_col(df, x, '散点图')
    _check_col(df, y, '散点图')

    data = _auto_sample(df.copy(), MAX_SCATTER_POINTS)
    n = len(data)

    # 透明度自适应：点越多越透明
    alpha = min(0.8, max(0.15, 1.0 - n / 5000))
    point_size = max(5, 30 - n / 200)

    fig, ax = _setup_figure(title=title or f'{y} vs {x} ({n:,}点)')

    if color and color in data.columns:
        scatter = ax.scatter(data[x], data[y], c=data[color], cmap='viridis',
                             alpha=alpha, edgecolors='none', s=point_size)
        plt.colorbar(scatter, ax=ax, label=color)
    elif size and size in data.columns:
        scatter = ax.scatter(data[x], data[y], s=data[size] * 20, alpha=alpha,
                             edgecolors='none')
    else:
        ax.scatter(data[x], data[y], alpha=alpha, c='#4A90D9',
                   edgecolors='none', s=point_size)

    if trendline and len(data) > 2:
        # 采样后做趋势线减少计算
        trend_data = _auto_sample(data, 500)
        try:
            z = np.polyfit(trend_data[x].dropna(), trend_data[y].dropna(), 1)
            p = np.poly1d(z)
            x_range = np.linspace(data[x].min(), data[x].max(), 100)
            ax.plot(x_range, p(x_range), '--', color='red', linewidth=1.5,
                    label=f'y={z[0]:.2f}x+{z[1]:.2f}')
            ax.legend()
        except Exception:
            pass  # 趋势线失败不阻塞图表生成

    ax.set_xlabel(x)
    ax.set_ylabel(y)

    return _save_and_close(fig, filename, output_dir)


def histogram(df: pd.DataFrame, column: str, bins: int = 20,
              kde: bool = True, title: str = None,
              filename: str = 'histogram.png',
              output_dir: str = None) -> str:
    """直方图（含KDE密度曲线）"""
    _check_col(df, column, '直方图')

    data = df[column].dropna()
    n = len(data)

    # 大数据量时自动调整 bins
    if n > 1000 and bins == 20:
        bins = min(100, int(np.sqrt(n)))
        logger.info(f"  直方图: {n} 个数据点, bins 自动调整为 {bins}")

    fig, ax = _setup_figure(title=title or f'{column} 分布 (n={n:,})')
    ax.hist(data, bins=bins, density=True, alpha=0.7,
            color='#4A90D9', edgecolor='white')
    if kde:
        try:
            sns.kdeplot(data=data, ax=ax, color='red',
                        linewidth=2, label='KDE')
            ax.legend()
        except Exception:
            pass  # KDE 失败不阻塞
    ax.set_xlabel(column)
    ax.set_ylabel('频率')

    return _save_and_close(fig, filename, output_dir)


def box_plot(df: pd.DataFrame, column: str = None,
             x: str = None, y: str = None,
             title: str = None, filename: str = 'boxplot.png',
             output_dir: str = None) -> str:
    """箱线图 - 分组过多时自动限制

    两种模式:
      单列分布: column='销售额'
      分组对比: x='月份', y='销售额'
    """
    if x and y:
        _check_col(df, x, '箱线图')
        _check_col(df, y, '箱线图')
        # 分组过多时限制
        categories = df[x].nunique()
        if categories > MAX_BOX_CATEGORIES:
            top_cats = df[x].value_counts().nlargest(MAX_BOX_CATEGORIES).index
            df = df[df[x].isin(top_cats)]
            logger.warning(f"  箱线图: 分组过多 ({categories}), 仅显示前 {MAX_BOX_CATEGORIES} 组")
    elif column:
        _check_col(df, column, '箱线图')

    n_cats = df[x].nunique() if x else 1
    figsize = _auto_figsize(n_cats, base=(10, 6))

    # 分组标签处理：截断长标签
    if x:
        raw_labels = df[x].astype(str).unique().tolist()
        avg_len = _avg_label_len(raw_labels)
        label_map = {lbl: _truncate_labels([lbl])[0] for lbl in raw_labels}
        df = df.copy()
        df[x] = df[x].astype(str).map(label_map)
    else:
        raw_labels = []
        avg_len = 5

    fig, ax = _setup_figure(figsize=figsize, title=title or '箱线图')

    if x and y:
        sns.boxplot(data=df, x=x, y=y, ax=ax, palette='Set2',
                    hue=x, legend=False)
    elif column:
        sns.boxplot(data=df, y=column, ax=ax, color='#4A90D9')

    if raw_labels:
        rotation = _smart_rotation(raw_labels)
        plt.xticks(rotation=rotation, ha='right' if rotation else 'center')
        ax.tick_params(axis='x', labelsize=_label_fontsize(n_cats, avg_len))
        _smart_ticks(ax, raw_labels)

    return _save_and_close(fig, filename, output_dir)


def heatmap(df: pd.DataFrame, annot: bool = True,
            cmap: str = 'YlOrRd', title: str = None,
            figsize: tuple = None,
            filename: str = 'heatmap.png',
            output_dir: str = None) -> str:
    """热力图（适用于透视表/交叉表）- 自适应尺寸和标注"""
    numeric_cols = df.select_dtypes(include=[np.number]).columns
    if len(numeric_cols) < 1:
        raise ValueError(
            f"❌ 热力图: 数据中没有数值列，无法生成热力图。\n"
            f"   请先做分组聚合或透视表再生成热力图。"
        )

    n_rows, n_cols = df.shape

    # 自适应尺寸：每行/列至少 0.4 英寸
    if figsize is None:
        w = max(8, min(20, n_cols * 0.5))
        h = max(6, min(16, n_rows * 0.45))
        figsize = (w, h)

    # 数据量大时关闭标注避免卡死
    total_cells = n_rows * n_cols
    if total_cells > 400 and annot:
        annot = False
        logger.info(f"  热力图: {total_cells} 个单元格，自动关闭数值标注")

    fmt = '.1f' if annot else ''

    # 截断长标签：修改 DataFrame 副本的 index/columns 用于显示
    display_df = df.copy()
    # 截断列名
    col_labels = [str(c) for c in df.columns]
    if _avg_label_len(col_labels) > LABEL_MAX_LEN:
        display_df.columns = _truncate_labels(col_labels)
    # 截断行索引名
    row_labels = [str(i) for i in df.index]
    if _avg_label_len(row_labels) > LABEL_MAX_LEN:
        display_df.index = _truncate_labels(row_labels)

    fig, ax = plt.subplots(figsize=figsize)
    sns.heatmap(display_df, annot=annot, fmt=fmt,
                cmap=cmap, ax=ax, linewidths=0.5 if total_cells <= 200 else 0,
                cbar_kws={'shrink': 0.8},
                annot_kws={'fontsize': max(5, 10 - total_cells // 100)})

    if title:
        ax.set_title(title, fontsize=14, fontweight='bold', pad=15)

    # 标签多时旋转 + 缩小字体（基于原始标签计算）
    label_fontsize = max(5, 10 - n_cols // 20 - max(0, (_avg_label_len(col_labels) - 6) // 3))
    ax.tick_params(axis='both', labelsize=label_fontsize)
    rotation = _smart_rotation(col_labels)
    plt.xticks(rotation=rotation, ha='right' if rotation else 'center')

    return _save_and_close(fig, filename, output_dir)


def correlation_heatmap(df: pd.DataFrame, columns: list[str] = None,
                        method: str = 'pearson',
                        filename: str = 'correlation.png',
                        output_dir: str = None) -> str:
    """相关系数热力图

    Args:
        method: 'pearson' | 'spearman' | 'kendall'
    """
    if method not in ('pearson', 'spearman', 'kendall'):
        raise ValueError(
            f"❌ 相关性热力图: 不支持的方法 '{method}'。\n"
            f"   可用方法: pearson, spearman, kendall"
        )

    if columns:
        _check_cols(df, columns, '相关性热力图')
        numeric_cols = [c for c in columns if pd.api.types.is_numeric_dtype(df[c])]
    else:
        numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()

    if len(numeric_cols) < 2:
        raise ValueError(
            f"❌ 相关性分析需要至少 2 个数值列，当前只有 {len(numeric_cols)} 个。\n"
            f"   可用数值列: {numeric_cols}"
        )

    # 限制相关矩阵大小（超过 30 列难以阅读）
    if len(numeric_cols) > 30:
        logger.warning(f"  相关性: {len(numeric_cols)} 列过多，仅取前 30 个数值列")
        numeric_cols = numeric_cols[:30]

    corr_df = df[numeric_cols].corr(method=method)

    title = f'相关系数矩阵 ({method})'
    return heatmap(corr_df, annot=True, cmap='RdBu_r', title=title,
                   filename=filename, output_dir=output_dir)


def time_series(df: pd.DataFrame, date_col: str, value_cols: list[str],
                title: str = None, resample: str = None,
                filename: str = 'timeseries.png',
                output_dir: str = None) -> str:
    """时间序列图

    Args:
        resample: 重采样频率，如 'M'(月), 'W'(周), 'Q'(季度)
    """
    _check_col(df, date_col, '时间序列')
    _check_cols(df, value_cols, '时间序列')

    data = df.copy()
    try:
        data[date_col] = pd.to_datetime(data[date_col], errors='coerce')
    except Exception as e:
        raise ValueError(
            f"❌ 列 '{date_col}' 不是日期格式，无法生成时间序列图。\n"
            f"   错误: {e}\n   请先转换列类型为 datetime。"
        )

    before = len(data)
    data = data.dropna(subset=[date_col])
    if len(data) == 0:
        raise ValueError(f"❌ 列 '{date_col}' 中没有有效的日期值。")
    if len(data) < before:
        logger.info(f"  时间序列: 跳过 {before - len(data)} 行无效日期")

    data = data.sort_values(date_col)

    if resample:
        try:
            data = data.set_index(date_col)
            data = data[value_cols].resample(resample).mean().reset_index()
        except Exception as e:
            raise ValueError(f"❌ 重采样失败: {e}")

    # 值列过多时限制
    if len(value_cols) > MAX_LINES:
        logger.warning(f"  时间序列: {len(value_cols)} 条线过多，仅显示前 {MAX_LINES} 条")
        value_cols = value_cols[:MAX_LINES]

    n = len(data)
    figsize = _auto_figsize(n, base=(14, 6))
    fig, ax = _setup_figure(figsize=figsize, title=title or '时间序列')

    colors = sns.color_palette('husl', len(value_cols))
    for i, col in enumerate(value_cols):
        ax.plot(data[date_col], data[col], color=colors[i],
                linewidth=2, marker='', label=col)

    ax.set_xlabel('日期')
    ax.set_ylabel('值')
    ncol = 2 if len(value_cols) > 5 else 1
    ax.legend(loc='best', ncol=ncol, fontsize=max(7, 9 - len(value_cols) // 5))
    ax.grid(True, alpha=0.3)
    fig.autofmt_xdate()

    return _save_and_close(fig, filename, output_dir)


def stacked_bar(df: pd.DataFrame, x: str, y_columns: list[str],
                title: str = None, normalize: bool = False,
                filename: str = 'stacked_bar.png',
                output_dir: str = None) -> str:
    """堆叠柱状图 - 数据量大时自动限制

    Args:
        normalize: True=百分比堆叠
    """
    _check_col(df, x, '堆叠柱状图')
    _check_cols(df, y_columns, '堆叠柱状图')

    data = df.copy()
    n = len(data)

    # 列数过多时限制
    if len(y_columns) > MAX_STACK_COLS:
        logger.warning(f"  堆叠柱状图: 列过多 ({len(y_columns)}), 仅显示前 {MAX_STACK_COLS} 列")
        y_columns = y_columns[:MAX_STACK_COLS]

    # 行数过多时限制
    if n > MAX_BAR_ITEMS:
        data = data.head(MAX_BAR_ITEMS)
        logger.warning(f"  堆叠柱状图: 行数过多 ({n}), 仅显示前 {MAX_BAR_ITEMS} 行")
        n = len(data)

    raw_labels = data[x].astype(str).tolist()
    avg_len = _avg_label_len(raw_labels)
    truncated = _truncate_labels(raw_labels)

    if normalize:
        data[y_columns] = data[y_columns].div(data[y_columns].sum(axis=1), axis=0) * 100

    figsize = _auto_figsize(n, base=(12, 7))
    fig, ax = _setup_figure(figsize=figsize, title=title or '堆叠柱状图')

    colors = sns.color_palette('Set2', len(y_columns))

    bottom = np.zeros(len(data))
    for i, col in enumerate(y_columns):
        ax.bar(truncated, data[col], bottom=bottom,
               color=colors[i], label=col, edgecolor='white')
        bottom += data[col].values

    ax.set_xlabel(x)       # 横轴 = 类别
    ax.set_ylabel('百分比' if normalize else '值')
    ncol = 2 if len(y_columns) > 4 else 1
    ax.legend(loc='best', frameon=True, ncol=ncol,
              fontsize=max(7, 9 - len(y_columns) // 5))

    rotation = _smart_rotation(raw_labels)
    plt.xticks(rotation=rotation, ha='right' if rotation else 'center')
    ax.tick_params(axis='x', labelsize=_label_fontsize(n, avg_len))
    _smart_ticks(ax, raw_labels)

    return _save_and_close(fig, filename, output_dir)


def _add_value_labels(ax, spacing: int = 5, horizontal: bool = False,
                      max_items: int = 12):
    """在柱状图上添加数值标签 - 自动防重叠

    - 柱数 > max_items 时跳过
    - 字体大小随柱数动态缩小
    - 跳过极小值
    """
    patches = [p for p in ax.patches if p.get_width() > 0 or p.get_height() > 0]
    n_patches = len(patches)

    if n_patches == 0 or n_patches > max_items:
        return  # 太多柱子，标签必然重叠

    # 动态字体：柱多 → 字小
    if n_patches <= 5:
        fontsize = 9
    elif n_patches <= 8:
        fontsize = 8
    elif n_patches <= 12:
        fontsize = 7
    else:
        fontsize = 6

    # 计算值的范围，用于判断"极小值"
    all_values = []
    for rect in patches:
        v = rect.get_width() if horizontal else rect.get_height()
        if v > 0:
            all_values.append(v)
    if not all_values:
        return
    max_val = max(all_values)
    threshold = max_val * 0.03  # 小于最大值 3% 的值不标注

    for rect in patches:
        value = rect.get_width() if horizontal else rect.get_height()
        if value <= 0:
            continue
        # 跳过极小值（标签会挤在一起）
        if value < threshold:
            continue

        if horizontal:
            x = value + spacing
            y = rect.get_y() + rect.get_height() / 2
            ax.annotate(f'{value:,.1f}' if value != int(value) else f'{int(value):,}',
                        (x, y), va='center', fontsize=fontsize, fontweight='bold')
        else:
            x = rect.get_x() + rect.get_width() / 2
            y = value + spacing
            ax.annotate(f'{value:,.1f}' if value != int(value) else f'{int(value):,}',
                        (x, y), ha='center', fontsize=fontsize, fontweight='bold')
