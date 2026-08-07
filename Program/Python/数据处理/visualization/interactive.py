"""
交互式图表：使用 Plotly 生成可在浏览器中查看的交互式图表
支持缩放、悬停提示、平移、下载等交互功能
"""
import os
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots

from config import CHART_DIR, logger


def _save_html(fig, filename: str, output_dir: str = None) -> str:
    """保存为独立 HTML 文件，可在浏览器打开"""
    if output_dir is None:
        output_dir = CHART_DIR
    os.makedirs(output_dir, exist_ok=True)
    path = os.path.join(output_dir, filename)
    fig.write_html(path, config={'displayModeBar': True, 'responsive': True})
    logger.info(f"交互式图表已保存: {path}")
    return path


def _save_image(fig, filename: str, output_dir: str = None) -> str:
    """保存为静态图片"""
    if output_dir is None:
        output_dir = CHART_DIR
    os.makedirs(output_dir, exist_ok=True)
    path = os.path.join(output_dir, filename)
    fig.write_image(path, scale=2)
    logger.info(f"图表图片已保存: {path}")
    return path


def ibar_chart(df: pd.DataFrame, x: str, y: str, title: str = None,
               color: str = None, horizontal: bool = False,
               filename: str = 'interactive_bar.html') -> str:
    """交互式柱状图"""
    if horizontal:
        fig = px.bar(df, y=x, x=y, title=title or f'{y} by {x}',
                     color=color, orientation='h')
    else:
        fig = px.bar(df, x=x, y=y, title=title or f'{y} by {x}', color=color)

    fig.update_layout(
        template='plotly_white',
        hovermode='x unified',
        title={'x': 0.5, 'xanchor': 'center'},
    )
    fig.update_traces(textposition='outside', texttemplate='%{y:,.1f}')
    return _save_html(fig, filename)


def iline_chart(df: pd.DataFrame, x: str, y: str | list[str],
                title: str = None,
                filename: str = 'interactive_line.html') -> str:
    """交互式折线图"""
    if isinstance(y, list):
        fig = px.line(df, x=x, y=y, title=title or '趋势图',
                      markers=True)
    else:
        fig = px.line(df, x=x, y=y, title=title or f'{y} over {x}',
                      markers=True)

    fig.update_layout(
        template='plotly_white',
        hovermode='x unified',
        title={'x': 0.5, 'xanchor': 'center'},
    )
    return _save_html(fig, filename)


def ipie_chart(df: pd.DataFrame, labels_col: str, values_col: str,
               title: str = None, donut: bool = False,
               filename: str = 'interactive_pie.html') -> str:
    """交互式饼图/环形图"""
    fig = px.pie(df, names=labels_col, values=values_col,
                 title=title or f'{values_col} 分布',
                 hole=0.45 if donut else 0)

    fig.update_layout(
        template='plotly_white',
        title={'x': 0.5, 'xanchor': 'center'},
    )
    fig.update_traces(textposition='inside', textinfo='percent+label')
    return _save_html(fig, filename)


def iscatter_plot(df: pd.DataFrame, x: str, y: str, title: str = None,
                  color: str = None, size: str = None,
                  trendline: bool = False,
                  filename: str = 'interactive_scatter.html') -> str:
    """交互式散点图"""
    fig = px.scatter(df, x=x, y=y, title=title or f'{y} vs {x}',
                     color=color, size=size,
                     trendline='ols' if trendline else None,
                     hover_data=df.columns.tolist())

    fig.update_layout(
        template='plotly_white',
        title={'x': 0.5, 'xanchor': 'center'},
    )
    return _save_html(fig, filename)


def ihistogram(df: pd.DataFrame, column: str, bins: int = 20,
               title: str = None,
               filename: str = 'interactive_hist.html') -> str:
    """交互式直方图"""
    fig = px.histogram(df, x=column, nbins=bins,
                       title=title or f'{column} 分布',
                       marginal='box',  # 顶部添加箱线图
                       opacity=0.7)

    fig.update_layout(
        template='plotly_white',
        title={'x': 0.5, 'xanchor': 'center'},
    )
    return _save_html(fig, filename)


def ibox_plot(df: pd.DataFrame, x: str = None, y: str = None,
              title: str = None,
              filename: str = 'interactive_box.html') -> str:
    """交互式箱线图"""
    fig = px.box(df, x=x, y=y, title=title or '箱线图',
                 points='outliers')  # 显示离群点

    fig.update_layout(
        template='plotly_white',
        title={'x': 0.5, 'xanchor': 'center'},
    )
    return _save_html(fig, filename)


def iheatmap(df: pd.DataFrame, title: str = None,
             filename: str = 'interactive_heatmap.html') -> str:
    """交互式热力图"""
    fig = px.imshow(df, text_auto='.2f', aspect='auto',
                    title=title or '热力图',
                    color_continuous_scale='RdBu_r')

    fig.update_layout(
        template='plotly_white',
        title={'x': 0.5, 'xanchor': 'center'},
    )
    return _save_html(fig, filename)


def icorrelation_heatmap(df: pd.DataFrame, columns: list[str] = None,
                         method: str = 'pearson',
                         filename: str = 'interactive_corr.html') -> str:
    """交互式相关系数热力图"""
    if columns:
        corr_df = df[columns].corr(method=method)
    else:
        corr_df = df.select_dtypes(include=[np.number]).corr(method=method)

    return iheatmap(corr_df, title=f'相关系数矩阵 ({method})', filename=filename)


def itime_series(df: pd.DataFrame, date_col: str, value_cols: list[str],
                 title: str = None, resample: str = None,
                 filename: str = 'interactive_timeseries.html') -> str:
    """交互式时间序列图"""
    data = df.copy()
    data[date_col] = pd.to_datetime(data[date_col])
    data = data.sort_values(date_col)

    if resample:
        data = data.set_index(date_col)
        data = data[value_cols].resample(resample).mean().reset_index()

    fig = px.line(data, x=date_col, y=value_cols,
                  title=title or '时间序列',
                  markers=False)

    fig.update_layout(
        template='plotly_white',
        hovermode='x unified',
        title={'x': 0.5, 'xanchor': 'center'},
        xaxis_title='日期',
    )
    return _save_html(fig, filename)


def iarea_chart(df: pd.DataFrame, x: str, y: str | list[str],
                title: str = None, stacked: bool = True,
                filename: str = 'interactive_area.html') -> str:
    """交互式面积图（堆叠面积图）"""
    if isinstance(y, list):
        fig = px.area(df, x=x, y=y, title=title or '面积图',
                      groupnorm='stack' if stacked else None)
    else:
        fig = px.area(df, x=x, y=y, title=title or f'{y} over {x}')

    fig.update_layout(
        template='plotly_white',
        hovermode='x unified',
        title={'x': 0.5, 'xanchor': 'center'},
    )
    return _save_html(fig, filename)


def isunburst(df: pd.DataFrame, path: list[str], values: str = None,
              title: str = None,
              filename: str = 'interactive_sunburst.html') -> str:
    """交互式旭日图（层级数据展示）

    Example:
        isunburst(df, path=['部门', '职位'], values='工资')
    """
    fig = px.sunburst(df, path=path, values=values,
                      title=title or '层级分布图')

    fig.update_layout(
        template='plotly_white',
        title={'x': 0.5, 'xanchor': 'center'},
    )
    return _save_html(fig, filename)


def itreemap(df: pd.DataFrame, path: list[str], values: str = None,
             title: str = None,
             filename: str = 'interactive_treemap.html') -> str:
    """交互式矩形树图（层级数据 + 大小对比）"""
    fig = px.treemap(df, path=path, values=values,
                     title=title or '矩形树图')

    fig.update_layout(
        template='plotly_white',
        title={'x': 0.5, 'xanchor': 'center'},
    )
    return _save_html(fig, filename)


def ibubble_chart(df: pd.DataFrame, x: str, y: str,
                  size: str, color: str = None,
                  title: str = None,
                  filename: str = 'interactive_bubble.html') -> str:
    """交互式气泡图"""
    fig = px.scatter(df, x=x, y=y, size=size, color=color,
                     title=title or '气泡图',
                     hover_data=df.columns.tolist())

    fig.update_layout(
        template='plotly_white',
        title={'x': 0.5, 'xanchor': 'center'},
    )
    return _save_html(fig, filename)


def idashboard(df: pd.DataFrame, charts: list[dict],
               title: str = None, rows: int = None, cols: int = None,
               filename: str = 'interactive_dashboard.html') -> str:
    """交互式仪表板 - 多个图表组合

    Args:
        charts: [{'type': 'bar', 'x': '...', 'y': '...', 'title': '...'}, ...]
        支持 type: 'bar', 'line', 'pie', 'area', 'scatter'
    """
    n = len(charts)
    if rows is None and cols is None:
        cols = min(2, n)
        rows = (n + cols - 1) // cols

    # 构建 specs: pie 需要 'domain' 类型
    specs = []
    for i in range(n):
        chart_type = charts[i].get('type', 'bar')
        if chart_type == 'pie':
            specs.append({'type': 'domain'})
        else:
            specs.append({'type': 'xy'})

    # 填充到完整矩阵
    spec_matrix = []
    for r in range(rows):
        row_specs = []
        for c in range(cols):
            idx = r * cols + c
            if idx < n:
                row_specs.append(specs[idx])
            else:
                row_specs.append(None)
        spec_matrix.append(row_specs)

    subplot_titles = [c.get('title', '') for c in charts]
    # 填充空的子图标题
    while len(subplot_titles) < rows * cols:
        subplot_titles.append('')

    fig = make_subplots(rows=rows, cols=cols,
                        specs=spec_matrix,
                        subplot_titles=subplot_titles)

    for i, config in enumerate(charts):
        chart_type = config.get('type', 'bar')
        row = (i // cols) + 1
        col = (i % cols) + 1

        if chart_type == 'bar':
            trace = go.Bar(
                x=df[config['x']].astype(str),
                y=df[config['y']],
                name=config.get('title', ''),
                marker_color='#4A90D9'
            )
        elif chart_type == 'line':
            trace = go.Scatter(
                x=df[config['x']].astype(str),
                y=df[config['y']],
                mode='lines+markers',
                name=config.get('title', ''),
                line=dict(color='#E74C3C')
            )
        elif chart_type == 'area':
            trace = go.Scatter(
                x=df[config['x']].astype(str),
                y=df[config['y']],
                mode='lines',
                fill='tozeroy',
                name=config.get('title', ''),
                line=dict(color='#4A90D9')
            )
        elif chart_type == 'scatter':
            trace = go.Scatter(
                x=df[config['x']].astype(str),
                y=df[config['y']],
                mode='markers',
                name=config.get('title', ''),
                marker=dict(color='#4A90D9', size=10)
            )
        elif chart_type == 'pie':
            trace = go.Pie(
                labels=df[config['labels_col']].astype(str),
                values=df[config['values_col']],
                name=config.get('title', ''),
            )
        else:
            continue

        fig.add_trace(trace, row=row, col=col)

    fig.update_layout(
        title_text=title or '数据分析仪表板',
        title_x=0.5,
        template='plotly_white',
        height=350 * rows,
    )

    return _save_html(fig, filename)
