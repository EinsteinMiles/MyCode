"""
组合图表布局（多子图 Dashboard）
"""
import matplotlib.pyplot as plt
import seaborn as sns
import pandas as pd
import numpy as np
import os

from config import CHART_DIR, CHART_DPI, FONT_FAMILY

plt.rcParams['font.family'] = 'sans-serif'
plt.rcParams['font.sans-serif'] = FONT_FAMILY
plt.rcParams['axes.unicode_minus'] = False


def dashboard_layout(plots: list[dict], rows: int = None, cols: int = None,
                     title: str = None, figsize: tuple = (16, 12),
                     filename: str = 'dashboard.png',
                     output_dir: str = None) -> str:
    """多图组合 Dashboard

    Args:
        plots: 图表配置列表，每个元素为 dict:
            {
                'type': 'bar' | 'line' | 'pie' | 'hist' | 'box' | 'scatter',
                'title': '子图标题',
                'data': pd.DataFrame,
                'params': {对应绘图函数的参数...}
            }
        rows, cols: 行列数 (自动计算)
        title: 总标题

    Example:
        dashboard_layout([
            {'type': 'bar', 'title': '销售额', 'data': df1, 'params': {'x': '月', 'y': '销售额'}},
            {'type': 'line', 'title': '趋势', 'data': df2, 'params': {'x': '日期', 'y': '收入'}},
            {'type': 'pie', 'title': '分布', 'data': df3, 'params': {'labels_col': '类别', 'values_col': '数量'}},
            {'type': 'hist', 'title': '直方图', 'data': df4, 'params': {'column': '年龄'}},
        ])
    """
    n = len(plots)
    if rows is None and cols is None:
        cols = min(3, n)
        rows = (n + cols - 1) // cols
    elif rows is None:
        rows = (n + cols - 1) // cols
    elif cols is None:
        cols = (n + rows - 1) // rows

    fig, axes = plt.subplots(rows, cols, figsize=figsize)
    if title:
        fig.suptitle(title, fontsize=18, fontweight='bold', y=0.98)

    # 展平 axes 数组
    if rows * cols == 1:
        axes = [axes]
    else:
        axes = axes.flatten()

    for i, plot_config in enumerate(plots):
        if i >= len(axes):
            break
        ax = axes[i]
        _draw_plot(ax, plot_config)

    # 隐藏多余的子图
    for j in range(len(plots), len(axes)):
        axes[j].set_visible(False)

    plt.tight_layout()

    if output_dir is None:
        output_dir = CHART_DIR
    os.makedirs(output_dir, exist_ok=True)
    path = os.path.join(output_dir, filename)
    fig.savefig(path, dpi=CHART_DPI, bbox_inches='tight', facecolor='white')
    plt.close(fig)
    return path


def _draw_plot(ax, config: dict):
    """在指定 ax 上绘制单个图表"""
    plot_type = config.get('type', 'bar')
    data = config.get('data')
    params = config.get('params', {})
    title = config.get('title', '')

    if data is None and 'data' not in params:
        ax.set_title(title)
        ax.text(0.5, 0.5, 'No Data', ha='center', va='center',
                transform=ax.transAxes)
        return

    if 'data' in params:
        data = params.pop('data')

    try:
        if plot_type == 'bar':
            x = params.get('x', data.columns[0])
            y = params.get('y', data.columns[1])
            ax.bar(data[x].astype(str), data[y], color='#4A90D9', edgecolor='white')
            ax.set_xlabel(x)
            ax.set_ylabel(y)
            ax.tick_params(axis='x', rotation=45)

        elif plot_type == 'line':
            x = params.get('x', data.columns[0])
            y = params.get('y', data.columns[1])
            ax.plot(data[x].astype(str), data[y], color='#E74C3C',
                    marker='o', linewidth=2, markersize=4)
            ax.set_xlabel(x)
            ax.set_ylabel(y)
            ax.tick_params(axis='x', rotation=45)

        elif plot_type == 'pie':
            labels_col = params.get('labels_col', data.columns[0])
            values_col = params.get('values_col', data.columns[1])
            colors = sns.color_palette('Set3', len(data))
            ax.pie(data[values_col], labels=data[labels_col].astype(str),
                   autopct='%1.1f%%', colors=colors, startangle=90)

        elif plot_type == 'hist':
            column = params.get('column', data.columns[0])
            bins = params.get('bins', 20)
            ax.hist(data[column].dropna(), bins=bins, density=True,
                    alpha=0.7, color='#4A90D9', edgecolor='white')
            ax.set_xlabel(column)

        elif plot_type == 'box':
            column = params.get('column')
            x = params.get('x')
            y = params.get('y')
            if x and y:
                sns.boxplot(data=data, x=x, y=y, ax=ax, palette='Set2')
            elif column:
                sns.boxplot(data=data, y=column, ax=ax, color='#4A90D9')
            ax.tick_params(axis='x', rotation=45)

        elif plot_type == 'scatter':
            x = params.get('x', data.columns[0])
            y = params.get('y', data.columns[1])
            ax.scatter(data[x], data[y], alpha=0.6, c='#4A90D9')
            ax.set_xlabel(x)
            ax.set_ylabel(y)

        ax.set_title(title, fontsize=12, fontweight='bold')

    except Exception as e:
        ax.set_title(f'{title}\n[Error: {e}]')
