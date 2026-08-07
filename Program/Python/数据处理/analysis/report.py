"""
文字分析报告生成
使用 Jinja2 模板生成 HTML 和文本格式的分析报告
"""
import os
import time
import pandas as pd
import numpy as np
from datetime import datetime

from jinja2 import Template, Environment, BaseLoader

from config import REPORT_DIR, logger
from analysis.stats import describe_data, all_columns_summary, missing_report, outlier_report
from analysis.correlation import correlation_matrix, top_correlations

# --- HTML 模板 ---
HTML_TEMPLATE = r"""
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>数据分析报告 - {{ title }}</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'PingFang SC', 'Microsoft YaHei', sans-serif; background: #f5f7fa; color: #333; line-height: 1.6; }
        .container { max-width: 1100px; margin: 0 auto; padding: 20px; }
        .header { background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 40px; border-radius: 12px; margin-bottom: 24px; }
        .header h1 { font-size: 28px; margin-bottom: 8px; }
        .header p { opacity: 0.9; font-size: 14px; }
        .section { background: white; border-radius: 12px; padding: 28px; margin-bottom: 20px; box-shadow: 0 2px 12px rgba(0,0,0,0.06); }
        .section h2 { font-size: 20px; color: #333; margin-bottom: 16px; padding-bottom: 10px; border-bottom: 2px solid #667eea; }
        .stat-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 16px; margin-bottom: 20px; }
        .stat-card { background: #f8f9fc; border-radius: 8px; padding: 16px; text-align: center; border: 1px solid #e8ecf1; }
        .stat-card .label { font-size: 13px; color: #888; margin-bottom: 4px; }
        .stat-card .value { font-size: 24px; font-weight: 700; color: #333; }
        table { width: 100%; border-collapse: collapse; margin: 12px 0; font-size: 14px; }
        th { background: #f0f2f5; padding: 10px 12px; text-align: left; font-weight: 600; border-bottom: 2px solid #ddd; }
        td { padding: 8px 12px; border-bottom: 1px solid #eee; }
        tr:hover { background: #fafbfc; }
        .badge { display: inline-block; padding: 2px 8px; border-radius: 4px; font-size: 12px; font-weight: 500; }
        .badge-strong { background: #e74c3c22; color: #e74c3c; }
        .badge-moderate { background: #f39c1222; color: #f39c12; }
        .badge-weak { background: #27ae6022; color: #27ae60; }
        .warning { background: #fff3cd; border-left: 4px solid #ffc107; padding: 12px 16px; margin: 12px 0; border-radius: 4px; font-size: 14px; }
        .insight { background: #d4edda; border-left: 4px solid #28a745; padding: 12px 16px; margin: 12px 0; border-radius: 4px; font-size: 14px; }
        .footer { text-align: center; padding: 20px; color: #999; font-size: 13px; }
    </style>
</head>
<body>
    <div class="container">
        <!-- Header -->
        <div class="header">
            <h1>📊 {{ title }}</h1>
            <p>生成时间: {{ generated_at }} | 数据行数: {{ row_count }} | 列数: {{ col_count }}</p>
        </div>

        <!-- 数据概览 -->
        <div class="section">
            <h2>📋 数据概览</h2>
            <div class="stat-grid">
                <div class="stat-card">
                    <div class="label">总行数</div>
                    <div class="value">{{ overview.row_count }}</div>
                </div>
                <div class="stat-card">
                    <div class="label">总列数</div>
                    <div class="value">{{ overview.col_count }}</div>
                </div>
                <div class="stat-card">
                    <div class="label">数值列</div>
                    <div class="value">{{ overview.numeric_cols }}</div>
                </div>
                <div class="stat-card">
                    <div class="label">缺失率</div>
                    <div class="value">{{ overview.missing_pct }}%</div>
                </div>
            </div>
            <p><strong>列名:</strong> {{ overview.columns | join(', ') }}</p>
        </div>

        <!-- 描述统计 -->
        <div class="section">
            <h2>📈 描述统计</h2>
            {{ describe_table | safe }}
        </div>

        <!-- 缺失值 -->
        {% if missing_table %}
        <div class="section">
            <h2>⚠️ 缺失值检测</h2>
            {{ missing_table | safe }}
            {% if missing_insights %}
            {% for insight in missing_insights %}
            <div class="warning">⚠ {{ insight }}</div>
            {% endfor %}
            {% endif %}
        </div>
        {% endif %}

        <!-- 异常值 -->
        {% if outlier_table %}
        <div class="section">
            <h2>🔍 异常值检测</h2>
            {{ outlier_table | safe }}
        </div>
        {% endif %}

        <!-- 相关性分析 -->
        {% if correlation_table %}
        <div class="section">
            <h2>🔗 相关性分析</h2>
            {{ correlation_table | safe }}
            {% if correlation_insights %}
            {% for insight in correlation_insights %}
            <div class="insight">💡 {{ insight }}</div>
            {% endfor %}
            {% endif %}
        </div>
        {% endif %}

        <!-- 列摘要 -->
        <div class="section">
            <h2>📝 各列摘要</h2>
            {% for col_info in column_summaries %}
            <div style="margin-bottom: 16px; padding: 12px; background: #fafbfc; border-radius: 6px;">
                <strong>{{ col_info.column }}</strong>
                <span style="color: #888; margin-left: 8px; font-size: 13px;">{{ col_info.dtype }}</span>
                {% if col_info.missing_pct > 0 %}
                <span class="badge badge-moderate" style="margin-left: 8px;">缺失 {{ col_info.missing_pct }}%</span>
                {% endif %}
                <div style="margin-top: 6px; font-size: 13px; color: #666;">
                    唯一值: {{ col_info.unique }} ({{ col_info.unique_pct }}%)
                    {% if col_info.mean is not none %}
                    | 均值: {{ col_info.mean }} | 中位数: {{ col_info.median }}
                    | 标准差: {{ col_info.std }} | 范围: [{{ col_info.min }}, {{ col_info.max }}]
                    {% endif %}
                </div>
            </div>
            {% endfor %}
        </div>

        <div class="footer">
            由 数据处理工具 自动生成 | {{ generated_at }}
        </div>
    </div>
</body>
</html>
"""


def generate_report(df: pd.DataFrame, title: str = "数据分析报告") -> str:
    """生成文本格式分析报告

    Returns:
        报告文本
    """
    lines = []
    lines.append("=" * 60)
    lines.append(f"  {title}")
    lines.append("=" * 60)
    lines.append(f"生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    lines.append(f"数据规模: {df.shape[0]} 行 × {df.shape[1]} 列")
    lines.append("")

    # 概览
    lines.append("【数据概览】")
    lines.append(f"  数值列: {df.select_dtypes(include=[np.number]).shape[1]}")
    lines.append(f"  文本列: {df.select_dtypes(include=['object', 'string']).shape[1]}")
    lines.append(f"  缺失率: {df.isna().mean().mean() * 100:.2f}%")
    lines.append("")

    # 描述统计
    lines.append("【描述统计】")
    desc = describe_data(df)
    lines.append(desc.to_string())
    lines.append("")

    # 缺失值
    missing = missing_report(df)
    if not missing.empty:
        lines.append("【缺失值检测】")
        lines.append(missing.to_string())
        lines.append("")
    else:
        lines.append("【缺失值检测】✅ 无缺失值")
        lines.append("")

    # 异常值
    try:
        outliers = outlier_report(df)
        if not outliers.empty:
            lines.append("【异常值检测】")
            lines.append(outliers.to_string())
            lines.append("")
    except Exception:
        pass

    # 相关性
    numeric_cols = df.select_dtypes(include=[np.number]).columns
    if len(numeric_cols) >= 2:
        lines.append("【相关性分析】")
        corr = correlation_matrix(df)
        top_pairs = top_correlations(corr, top_n=5)
        for _, row in top_pairs.iterrows():
            lines.append(f"  {row['变量1']} ↔ {row['变量2']}: r={row['相关系数']} ({row['强度']})")
        lines.append("")

    lines.append("=" * 60)
    lines.append("  报告结束")
    lines.append("=" * 60)

    report_text = "\n".join(lines)
    logger.info(f"文本报告生成完成")
    return report_text


def generate_html_report(df: pd.DataFrame, title: str = "数据分析报告",
                         output_path: str = None) -> str:
    """生成 HTML 格式分析报告

    Args:
        df: 数据
        title: 报告标题
        output_path: 输出路径 (默认 REPORT_DIR/report_时间戳.html)

    Returns:
        报告文件路径
    """
    # 概览
    numeric_cols = df.select_dtypes(include=[np.number]).columns
    overview = {
        'row_count': len(df),
        'col_count': len(df.columns),
        'numeric_cols': len(numeric_cols),
        'missing_pct': round(df.isna().mean().mean() * 100, 2),
        'columns': df.columns.tolist(),
    }

    # 描述统计表
    desc_df = describe_data(df)
    describe_table = desc_df.to_html(classes='', border=0, float_format='%.2f')

    # 缺失值
    missing_df = missing_report(df)
    missing_table = missing_df.to_html(index=False) if not missing_df.empty else ''
    missing_insights = []
    for _, row in missing_df.iterrows():
        if row['缺失率(%)'] > 30:
            missing_insights.append(
                f"列 '{row['列名']}' 缺失率高达 {row['缺失率(%)']}%，建议检查数据源或考虑删除该列。")
        elif row['缺失率(%)'] > 10:
            missing_insights.append(
                f"列 '{row['列名']}' 缺失率 {row['缺失率(%)']}%，建议进行填充处理。")

    # 异常值
    try:
        outlier_df = outlier_report(df)
        outlier_table = outlier_df.to_html(index=False) if not outlier_df.empty else ''
    except Exception:
        outlier_df = pd.DataFrame()
        outlier_table = ''

    # 相关性
    corr_table = ''
    correlation_insights = []
    if len(numeric_cols) >= 2:
        corr = correlation_matrix(df)
        top_pairs = top_correlations(corr, top_n=10)
        corr_table = top_pairs.to_html(index=False) if not top_pairs.empty else ''
        for _, row in top_pairs.iterrows():
            if abs(row['相关系数']) >= 0.7:
                correlation_insights.append(
                    f"{row['变量1']} 与 {row['变量2']} 呈{row['强度']} (r={row['相关系数']})，"
                    f"存在显著的线性关系。")

    # 列摘要
    column_summaries = all_columns_summary(df)

    # 渲染模板
    template = Template(HTML_TEMPLATE)
    html = template.render(
        title=title,
        generated_at=datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        row_count=len(df),
        col_count=len(df.columns),
        overview=overview,
        describe_table=describe_table,
        missing_table=missing_table,
        missing_insights=missing_insights,
        outlier_table=outlier_table,
        correlation_table=corr_table,
        correlation_insights=correlation_insights,
        column_summaries=column_summaries,
    )

    if output_path is None:
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"report_{timestamp}.html"
        output_path = os.path.join(REPORT_DIR, filename)

    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(html)

    logger.info(f"HTML 报告已保存: {output_path}")
    return output_path
