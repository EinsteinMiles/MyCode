"""
交互式图表：使用 Plotly 生成可在浏览器中查看的交互式图表
支持缩放、悬停提示、平移、下载等交互功能
自动处理大数据量：智能采样、限制显示数量
"""
import os
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots

from config import CHART_DIR, logger

# ---- 大数据量阈值 ----
MAX_BAR_ITEMS = 30       # 柱状图超过此数自动限制
MAX_PIE_ITEMS = 10       # 饼图超过此数归为"其他"
MAX_SCATTER_POINTS = 3000 # 散点图超过此数自动采样
MAX_BOX_CATEGORIES = 30  # 箱线图超过此数自动限制
MAX_LINES = 10           # 多线图超过此数限制
LABEL_MAX_LEN = 10       # 交互式图表标签截断长度（比静态稍长，因为有悬停提示）


# ================================================================
#  内部工具
# ================================================================

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

def _save_html(fig, filename: str, output_dir: str = None) -> str:
    """保存为独立 HTML 文件"""
    if output_dir is None:
        output_dir = CHART_DIR
    os.makedirs(output_dir, exist_ok=True)
    path = os.path.join(output_dir, filename)
    fig.write_html(path, config={'displayModeBar': True, 'responsive': True})
    logger.info(f"交互式图表已保存: {path}")
    return path


def _check_columns(df: pd.DataFrame, required: list[str], label: str = "图表") -> None:
    """校验列是否存在，不存在则抛出清晰的错误"""
    missing = [c for c in required if c not in df.columns]
    if missing:
        raise ValueError(
            f"❌ {label}: 列 {missing} 不存在于数据中。\n"
            f"   可用列: {', '.join(df.columns.tolist())}"
        )


def _check_numeric(df: pd.DataFrame, columns: list[str], label: str = "图表") -> None:
    """校验列是否为数值类型"""
    for col in columns:
        if col not in df.columns:
            continue
        if not pd.api.types.is_numeric_dtype(df[col]):
            try:
                # 尝试转换
                df[col] = pd.to_numeric(df[col], errors='coerce')
                logger.info(f"  列 '{col}' 已自动转换为数值类型")
            except Exception:
                raise ValueError(
                    f"❌ {label}: 列 '{col}' 不是数值类型 ({df[col].dtype})，"
                    f"无法用于图表。\n   请先用菜单 2-6-5 转换类型。"
                )


def _safe_df(df: pd.DataFrame) -> pd.DataFrame:
    """创建安全的副本，处理极端值"""
    return df.copy()


# ================================================================
#  交互式图表
# ================================================================

def ibar_chart(df: pd.DataFrame, x: str, y: str, title: str = None,
               color: str = None, horizontal: bool = False,
               filename: str = 'interactive_bar.html') -> str:
    """交互式柱状图 - 数据过多时自动限制"""
    data = _safe_df(df)
    _check_columns(data, [x, y], '柱状图')
    _check_numeric(data, [y], '柱状图')

    n = len(data)

    # 自动限制
    if n > MAX_BAR_ITEMS:
        data = data.nlargest(MAX_BAR_ITEMS, y)
        logger.warning(f"  柱状图: {n} 项过多，仅显示前 {MAX_BAR_ITEMS} 项")

    # 截断长标签
    raw_labels = data[x].astype(str).tolist()
    if _avg_label_len(raw_labels) > LABEL_MAX_LEN:
        data[x] = _truncate_labels(raw_labels)
        logger.info(f"  柱状图: 标签过长(平均{_avg_label_len(raw_labels):.0f}字)，已自动截断")

    if horizontal:
        fig = px.bar(data, y=x, x=y, title=title or f'{y} by {x} (Top {min(n, MAX_BAR_ITEMS)})',
                     color=color, orientation='h')
    else:
        fig = px.bar(data, x=x, y=y, title=title or f'{y} by {x}', color=color)

    fig.update_layout(
        template='plotly_white',
        hovermode='x unified',
        title={'x': 0.5, 'xanchor': 'center'},
        height=max(400, 250 + n * 15),  # 自适应高度
    )
    fig.update_traces(textposition='outside', texttemplate='%{y:,.1f}')
    return _save_html(fig, filename)


def iline_chart(df: pd.DataFrame, x: str, y, title: str = None,
                filename: str = 'interactive_line.html') -> str:
    """交互式折线图 - 数据点多时自动隐藏标记"""
    data = _safe_df(df)
    y_cols = y if isinstance(y, list) else [y]
    _check_columns(data, [x] + y_cols, '折线图')

    # 线条过多时限制
    if isinstance(y, list) and len(y) > MAX_LINES:
        logger.warning(f"  折线图: {len(y)} 条线过多，仅显示前 {MAX_LINES} 条")
        y = y[:MAX_LINES]
        y_cols = y

    # 截断长标签
    raw_labels = data[x].astype(str).tolist()
    if _avg_label_len(raw_labels) > LABEL_MAX_LEN:
        data[x] = _truncate_labels(raw_labels)
    else:
        data[x] = raw_labels

    n = len(data)

    # 数据点多时不显示标记
    use_markers = n <= 50

    if isinstance(y, list):
        fig = px.line(data, x=x, y=y, title=title or '趋势图',
                      markers=use_markers)
    else:
        fig = px.line(data, x=x, y=y, title=title or f'{y} over {x}',
                      markers=use_markers)

    fig.update_layout(
        template='plotly_white',
        hovermode='x unified',
        title={'x': 0.5, 'xanchor': 'center'},
    )
    return _save_html(fig, filename)


def ipie_chart(df: pd.DataFrame, labels_col: str, values_col: str,
               title: str = None, donut: bool = False,
               filename: str = 'interactive_pie.html') -> str:
    """交互式饼图/环形图 - 项目过多时归为"其他" """
    data = _safe_df(df)
    _check_columns(data, [labels_col, values_col], '饼图')
    _check_numeric(data, [values_col], '饼图')

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

    # 截断长标签
    raw_labels = data[labels_col].astype(str).tolist()
    if _avg_label_len(raw_labels) > LABEL_MAX_LEN:
        data[labels_col] = _truncate_labels(raw_labels, max_len=12)

    fig = px.pie(data, names=labels_col, values=values_col,
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
                  filename: str = 'interactive_scatter.html') -> str:
    """交互式散点图 - 数据点过多时自动采样"""
    data = _safe_df(df)
    _check_columns(data, [x, y], '散点图')
    _check_numeric(data, [x, y], '散点图')

    # 过滤掉 NaN
    cols = [x, y] + ([color] if color and color in data.columns else [])
    data = data[cols].dropna()
    if len(data) == 0:
        raise ValueError("❌ 散点图: 去除空值后无有效数据")

    # 自动采样
    n_total = len(data)
    if n_total > MAX_SCATTER_POINTS:
        data = data.sample(n=MAX_SCATTER_POINTS, random_state=42)
        logger.warning(f"  散点图: {n_total} 个点过多，随机采样 {MAX_SCATTER_POINTS} 个")

    fig = px.scatter(data, x=x, y=y, title=title or f'{y} vs {x}',
                     color=color, size=size,
                     hover_data=data.columns.tolist())

    fig.update_layout(
        template='plotly_white',
        title={'x': 0.5, 'xanchor': 'center'},
    )
    return _save_html(fig, filename)


def ihistogram(df: pd.DataFrame, column: str, bins: int = 20,
               title: str = None,
               filename: str = 'interactive_hist.html') -> str:
    """交互式直方图"""
    data = _safe_df(df)
    _check_columns(data, [column], '直方图')
    _check_numeric(data, [column], '直方图')

    valid = data[column].dropna()
    if len(valid) == 0:
        raise ValueError(f"❌ 直方图: 列 '{column}' 去除空值后无有效数据")

    fig = px.histogram(data, x=column, nbins=bins,
                       title=title or f'{column} 分布',
                       marginal='box', opacity=0.7)

    fig.update_layout(
        template='plotly_white',
        title={'x': 0.5, 'xanchor': 'center'},
    )
    return _save_html(fig, filename)


def ibox_plot(df: pd.DataFrame, x: str = None, y: str = None,
              title: str = None,
              filename: str = 'interactive_box.html') -> str:
    """交互式箱线图 - 分组过多时自动限制"""
    data = _safe_df(df)
    cols = [c for c in [x, y] if c is not None]
    if cols:
        _check_columns(data, cols, '箱线图')

    # 分组过多时限制
    if x and y and data[x].nunique() > MAX_BOX_CATEGORIES:
        top_cats = data[x].value_counts().nlargest(MAX_BOX_CATEGORIES).index
        data = data[data[x].isin(top_cats)]
        logger.warning(f"  箱线图: 分组过多，仅显示前 {MAX_BOX_CATEGORIES} 组")

    fig = px.box(data, x=x, y=y, title=title or '箱线图',
                 points='outliers')

    fig.update_layout(
        template='plotly_white',
        title={'x': 0.5, 'xanchor': 'center'},
    )
    return _save_html(fig, filename)


def iheatmap(df: pd.DataFrame, title: str = None,
             filename: str = 'interactive_heatmap.html') -> str:
    """交互式热力图"""
    data = _safe_df(df)
    # 只取数值列
    numeric = data.select_dtypes(include=[np.number])
    if numeric.shape[1] < 2:
        raise ValueError(
            f"❌ 热力图需要至少 2 列数值数据，当前只有 {numeric.shape[1]} 列。\n"
            f"   请先做分组聚合或透视表再生成热力图。"
        )

    fig = px.imshow(numeric, text_auto='.2f', aspect='auto',
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
    data = _safe_df(df)

    if columns:
        _check_columns(data, columns, '相关性热力图')
        numeric_cols = [c for c in columns if pd.api.types.is_numeric_dtype(data[c])]
    else:
        numeric_cols = data.select_dtypes(include=[np.number]).columns.tolist()

    if len(numeric_cols) < 2:
        raise ValueError(
            f"❌ 相关性分析需要至少 2 个数值列，当前只有 {len(numeric_cols)} 个。\n"
            f"   可用数值列: {numeric_cols}"
        )

    try:
        corr_df = data[numeric_cols].corr(method=method)
    except Exception as e:
        raise ValueError(f"❌ 无法计算相关系数矩阵: {e}")

    if corr_df.isna().all().all():
        raise ValueError("❌ 相关系数全部为空，请检查数据中是否有常数列或全空列。")

    return iheatmap(corr_df, title=f'相关系数矩阵 ({method})', filename=filename)


def itime_series(df: pd.DataFrame, date_col: str, value_cols: list[str],
                 title: str = None, resample: str = None,
                 filename: str = 'interactive_timeseries.html') -> str:
    """交互式时间序列图"""
    data = _safe_df(df)
    _check_columns(data, [date_col] + value_cols, '时间序列')

    # 日期列转换，容错处理
    try:
        data[date_col] = pd.to_datetime(data[date_col], errors='coerce')
    except Exception as e:
        raise ValueError(
            f"❌ 列 '{date_col}' 不是日期格式，无法生成时间序列图。\n"
            f"   错误: {e}\n   请先用菜单 2-6-5 将列转换为 datetime 类型。"
        )

    # 删除日期无效的行
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
            if len(data) == 0:
                raise ValueError(f"重采样 '{resample}' 后无数据")
        except Exception as e:
            raise ValueError(f"❌ 重采样失败: {e}")

    fig = px.line(data, x=date_col, y=value_cols,
                  title=title or '时间序列', markers=False)

    fig.update_layout(
        template='plotly_white',
        hovermode='x unified',
        title={'x': 0.5, 'xanchor': 'center'},
        xaxis_title='日期',
    )
    return _save_html(fig, filename)


def iarea_chart(df: pd.DataFrame, x: str, y, title: str = None,
                stacked: bool = True,
                filename: str = 'interactive_area.html') -> str:
    """交互式面积图"""
    data = _safe_df(df)
    y_cols = y if isinstance(y, list) else [y]
    _check_columns(data, [x] + y_cols, '面积图')

    data[x] = data[x].astype(str)

    if isinstance(y, list):
        fig = px.area(data, x=x, y=y, title=title or '面积图')
    else:
        fig = px.area(data, x=x, y=y, title=title or f'{y} over {x}')

    fig.update_layout(
        template='plotly_white',
        hovermode='x unified',
        title={'x': 0.5, 'xanchor': 'center'},
    )
    return _save_html(fig, filename)


def isunburst(df: pd.DataFrame, path: list[str], values: str = None,
              title: str = None,
              filename: str = 'interactive_sunburst.html') -> str:
    """交互式旭日图（层级数据展示）"""
    data = _safe_df(df)
    _check_columns(data, path, '旭日图')
    if values:
        _check_columns(data, [values], '旭日图')

    # 层级路径中去除空值行
    for p in path:
        data = data[data[p].notna()]

    if len(data) == 0:
        raise ValueError("❌ 旭日图: 层级路径中存在过多空值，无有效数据。")

    fig = px.sunburst(data, path=path, values=values,
                      title=title or '层级分布图')

    fig.update_layout(
        template='plotly_white',
        title={'x': 0.5, 'xanchor': 'center'},
    )
    return _save_html(fig, filename)


def itreemap(df: pd.DataFrame, path: list[str], values: str = None,
             title: str = None,
             filename: str = 'interactive_treemap.html') -> str:
    """交互式矩形树图"""
    data = _safe_df(df)
    _check_columns(data, path, '矩形树图')
    if values:
        _check_columns(data, [values], '矩形树图')

    for p in path:
        data = data[data[p].notna()]

    if len(data) == 0:
        raise ValueError("❌ 矩形树图: 层级路径中存在过多空值，无有效数据。")

    fig = px.treemap(data, path=path, values=values,
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
    data = _safe_df(df)
    _check_columns(data, [x, y, size], '气泡图')
    _check_numeric(data, [x, y, size], '气泡图')

    fig = px.scatter(data, x=x, y=y, size=size, color=color,
                     title=title or '气泡图',
                     hover_data=data.columns.tolist())

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
    """
    if not charts:
        raise ValueError("❌ 仪表板: 至少需要 1 个子图配置。")

    n = len(charts)
    if rows is None and cols is None:
        cols = min(2, n)
        rows = (n + cols - 1) // cols

    # 构建 specs
    specs = []
    for c in charts:
        if c.get('type') == 'pie':
            specs.append({'type': 'domain'})
        else:
            specs.append({'type': 'xy'})

    spec_matrix = []
    for r in range(rows):
        row_specs = []
        for c in range(cols):
            idx = r * cols + c
            row_specs.append(specs[idx] if idx < n else None)
        spec_matrix.append(row_specs)

    subplot_titles = [c.get('title', '') for c in charts]
    while len(subplot_titles) < rows * cols:
        subplot_titles.append('')

    fig = make_subplots(rows=rows, cols=cols,
                        specs=spec_matrix,
                        subplot_titles=subplot_titles)

    for i, config in enumerate(charts):
        chart_type = config.get('type', 'bar')
        row = (i // cols) + 1
        col = (i % cols) + 1

        try:
            if chart_type == 'bar':
                if 'x' not in config or 'y' not in config:
                    raise ValueError("缺少 x 或 y 参数")
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
                    mode='lines', fill='tozeroy',
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
                logger.warning(f"  仪表板: 跳过未知图表类型 '{chart_type}'")
                continue

            fig.add_trace(trace, row=row, col=col)

        except KeyError as e:
            logger.error(f"  仪表板子图 {i+1}: 列不存在 - {e}")
            raise ValueError(f"仪表板子图 {i+1} ('{config.get('title', '')}'): 列 {e} 不存在")

    fig.update_layout(
        title_text=title or '数据分析仪表板',
        title_x=0.5,
        template='plotly_white',
        height=350 * rows,
    )

    return _save_html(fig, filename)
