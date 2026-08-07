"""
数据可视化：柱状图、折线图、饼图、散点图、直方图、箱线图、热力图等
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


def _setup_figure(figsize: tuple = None, title: str = None):
    """创建并配置图表"""
    fig, ax = plt.subplots(figsize=figsize or CHART_FIGSIZE)
    if title:
        ax.set_title(title, fontsize=14, fontweight='bold', pad=15)
    return fig, ax


def bar_chart(df: pd.DataFrame, x: str, y: str, title: str = None,
              color: str = '#4A90D9', horizontal: bool = False,
              sort: bool = True, top_n: int = None,
              filename: str = 'bar_chart.png',
              output_dir: str = None) -> str:
    """柱状图

    Args:
        df: 数据
        x: X轴列（类别）
        y: Y轴列（数值）
        horizontal: True=水平柱状图
        sort: 是否按值排序
        top_n: 只显示前N条
    """
    data = df.copy()
    if sort:
        data = data.sort_values(y, ascending=horizontal)
    if top_n:
        data = data.head(top_n) if not horizontal else data.tail(top_n)

    fig, ax = _setup_figure(title=title or f'{y} by {x}')

    if horizontal:
        ax.barh(data[x].astype(str), data[y], color=color, edgecolor='white')
        ax.set_xlabel(y)
    else:
        ax.bar(data[x].astype(str), data[y], color=color, edgecolor='white')
        ax.set_ylabel(y)
        plt.xticks(rotation=45, ha='right')

    ax.set_title(title or f'{y} by {x}', fontsize=14, fontweight='bold')
    _add_value_labels(ax, horizontal=horizontal)

    return _save_and_close(fig, filename, output_dir)


def line_chart(df: pd.DataFrame, x: str, y: str, title: str = None,
               color: str = '#E74C3C', marker: str = 'o',
               filename: str = 'line_chart.png',
               output_dir: str = None) -> str:
    """折线图"""
    fig, ax = _setup_figure(title=title or f'{y} over {x}')
    ax.plot(df[x].astype(str), df[y], color=color, marker=marker,
            linewidth=2, markersize=6)
    ax.set_xlabel(x)
    ax.set_ylabel(y)
    plt.xticks(rotation=45, ha='right')
    ax.grid(True, alpha=0.3)

    return _save_and_close(fig, filename, output_dir)


def multi_line_chart(df: pd.DataFrame, x: str, y_columns: list[str],
                     title: str = None, filename: str = 'multi_line.png',
                     output_dir: str = None) -> str:
    """多线折线图（多条Y线）"""
    fig, ax = _setup_figure(title=title or f'趋势对比')
    colors = sns.color_palette('husl', len(y_columns))

    for i, col in enumerate(y_columns):
        ax.plot(df[x].astype(str), df[col], color=colors[i], marker='o',
                linewidth=2, markersize=4, label=col)

    ax.set_xlabel(x)
    ax.legend(loc='best', frameon=True)
    plt.xticks(rotation=45, ha='right')
    ax.grid(True, alpha=0.3)

    return _save_and_close(fig, filename, output_dir)


def pie_chart(df: pd.DataFrame, labels_col: str, values_col: str,
              title: str = None, donut: bool = False,
              filename: str = 'pie_chart.png',
              output_dir: str = None) -> str:
    """饼图 / 环形图

    Args:
        donut: True=环形图 (中间有洞)
    """
    data = df.nlargest(10, values_col) if len(df) > 10 else df
    fig, ax = _setup_figure(title=title or f'{values_col} 分布')

    colors = sns.color_palette('Set3', len(data))
    wedges, texts, autotexts = ax.pie(
        data[values_col],
        labels=data[labels_col].astype(str),
        autopct='%1.1f%%',
        colors=colors,
        pctdistance=0.75 if donut else 0.6,
        startangle=90
    )

    if donut:
        centre_circle = plt.Circle((0, 0), 0.55, fc='white', linewidth=0)
        ax.add_artist(centre_circle)

    # 提升文字可读性
    for t in autotexts:
        t.set_fontsize(8)
    for t in texts:
        t.set_fontsize(9)

    return _save_and_close(fig, filename, output_dir)


def scatter_plot(df: pd.DataFrame, x: str, y: str,
                 color: str = None, size: str = None,
                 title: str = None, trendline: bool = True,
                 filename: str = 'scatter.png',
                 output_dir: str = None) -> str:
    """散点图（可选颜色和大小维度、趋势线）"""
    fig, ax = _setup_figure(title=title or f'{y} vs {x}')

    if color and color in df.columns:
        scatter = ax.scatter(df[x], df[y], c=df[color], cmap='viridis',
                             alpha=0.6, edgecolors='white', linewidth=0.5)
        plt.colorbar(scatter, ax=ax, label=color)
    elif size and size in df.columns:
        scatter = ax.scatter(df[x], df[y], s=df[size] * 20, alpha=0.6,
                             edgecolors='white', linewidth=0.5)
    else:
        ax.scatter(df[x], df[y], alpha=0.6, c='#4A90D9',
                   edgecolors='white', linewidth=0.5)

    if trendline and len(df) > 2:
        z = np.polyfit(df[x], df[y], 1)
        p = np.poly1d(z)
        x_range = np.linspace(df[x].min(), df[x].max(), 100)
        ax.plot(x_range, p(x_range), '--', color='red', linewidth=1.5,
                label=f'y={z[0]:.2f}x+{z[1]:.2f}')
        ax.legend()

    ax.set_xlabel(x)
    ax.set_ylabel(y)

    return _save_and_close(fig, filename, output_dir)


def histogram(df: pd.DataFrame, column: str, bins: int = 20,
              kde: bool = True, title: str = None,
              filename: str = 'histogram.png',
              output_dir: str = None) -> str:
    """直方图（含KDE密度曲线）"""
    fig, ax = _setup_figure(title=title or f'{column} 分布')
    ax.hist(df[column].dropna(), bins=bins, density=True, alpha=0.7,
            color='#4A90D9', edgecolor='white')
    if kde:
        sns.kdeplot(data=df[column].dropna(), ax=ax, color='red',
                    linewidth=2, label='KDE')
        ax.legend()
    ax.set_xlabel(column)
    ax.set_ylabel('频率')

    return _save_and_close(fig, filename, output_dir)


def box_plot(df: pd.DataFrame, column: str = None,
             x: str = None, y: str = None,
             title: str = None, filename: str = 'boxplot.png',
             output_dir: str = None) -> str:
    """箱线图

    两种模式:
      单列分布: column='销售额'
      分组对比: x='月份', y='销售额'
    """
    fig, ax = _setup_figure(title=title or '箱线图')

    if x and y:
        sns.boxplot(data=df, x=x, y=y, ax=ax, palette='Set2')
    elif column:
        sns.boxplot(data=df, y=column, ax=ax, color='#4A90D9')
    plt.xticks(rotation=45, ha='right')

    return _save_and_close(fig, filename, output_dir)


def heatmap(df: pd.DataFrame, annot: bool = True,
            cmap: str = 'YlOrRd', title: str = None,
            figsize: tuple = (14, 10),
            filename: str = 'heatmap.png',
            output_dir: str = None) -> str:
    """热力图（适用于透视表/交叉表）"""
    fig, ax = plt.subplots(figsize=figsize)
    sns.heatmap(df, annot=annot, fmt='.1f' if annot else '',
                cmap=cmap, ax=ax, linewidths=0.5,
                cbar_kws={'shrink': 0.8})
    if title:
        ax.set_title(title, fontsize=14, fontweight='bold', pad=15)
    plt.xticks(rotation=45, ha='right')

    return _save_and_close(fig, filename, output_dir)


def correlation_heatmap(df: pd.DataFrame, columns: list[str] = None,
                        method: str = 'pearson',
                        filename: str = 'correlation.png',
                        output_dir: str = None) -> str:
    """相关系数热力图

    Args:
        method: 'pearson' | 'spearman' | 'kendall'
    """
    if columns:
        corr_df = df[columns].corr(method=method)
    else:
        corr_df = df.select_dtypes(include=[np.number]).corr(method=method)

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
    data = df.copy()
    data[date_col] = pd.to_datetime(data[date_col])
    data = data.sort_values(date_col)

    if resample:
        data = data.set_index(date_col)
        data = data[value_cols].resample(resample).mean().reset_index()

    fig, ax = _setup_figure(title=title or '时间序列')
    colors = sns.color_palette('husl', len(value_cols))
    for i, col in enumerate(value_cols):
        ax.plot(data[date_col], data[col], color=colors[i],
                linewidth=2, marker='', label=col)

    ax.set_xlabel('日期')
    ax.legend(loc='best')
    ax.grid(True, alpha=0.3)
    fig.autofmt_xdate()

    return _save_and_close(fig, filename, output_dir)


def stacked_bar(df: pd.DataFrame, x: str, y_columns: list[str],
                title: str = None, normalize: bool = False,
                filename: str = 'stacked_bar.png',
                output_dir: str = None) -> str:
    """堆叠柱状图

    Args:
        normalize: True=百分比堆叠
    """
    data = df.copy()
    if normalize:
        data[y_columns] = data[y_columns].div(data[y_columns].sum(axis=1), axis=0) * 100

    fig, ax = _setup_figure(title=title or '堆叠柱状图')
    colors = sns.color_palette('Set2', len(y_columns))

    bottom = np.zeros(len(data))
    for i, col in enumerate(y_columns):
        ax.bar(data[x].astype(str), data[col], bottom=bottom,
               color=colors[i], label=col, edgecolor='white')
        bottom += data[col].values

    ax.set_ylabel('百分比' if normalize else '值')
    ax.legend(loc='best', frameon=True)
    plt.xticks(rotation=45, ha='right')

    return _save_and_close(fig, filename, output_dir)


def _add_value_labels(ax, spacing: int = 5, horizontal: bool = False):
    """在柱状图上添加数值标签"""
    for rect in ax.patches:
        value = rect.get_width() if horizontal else rect.get_height()
        if value == 0:
            continue
        if horizontal:
            x = value + spacing
            y = rect.get_y() + rect.get_height() / 2
            ax.annotate(f'{value:,.1f}' if value != int(value) else f'{int(value):,}',
                        (x, y), va='center', fontsize=8)
        else:
            x = rect.get_x() + rect.get_width() / 2
            y = value + spacing
            ax.annotate(f'{value:,.1f}' if value != int(value) else f'{int(value):,}',
                        (x, y), ha='center', fontsize=8)
