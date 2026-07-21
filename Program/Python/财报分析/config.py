"""
财报分析 - 配置文件
包含数据目录、默认参数、列名映射、财务指标阈值等
"""

import os

# --- 路径配置 ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")
OUTPUT_DIR = os.path.join(BASE_DIR, "output")
CHART_DIR = os.path.join(OUTPUT_DIR, "charts")
REPORT_DIR = os.path.join(OUTPUT_DIR, "reports")
TEMPLATE_DIR = os.path.join(BASE_DIR, "display", "templates")

# 自动创建输出目录
for d in [DATA_DIR, OUTPUT_DIR, CHART_DIR, REPORT_DIR]:
    os.makedirs(d, exist_ok=True)

# --- 默认参数 ---
DEFAULT_YEARS = 5          # 默认获取近 N 年数据
DEFAULT_UNIT = "yi"        # 默认单位：亿 (yi=亿, wan=万, yuan=元)
RETRY_TIMES = 3            # API 请求重试次数
RETRY_DELAY = 1.0          # 重试间隔(秒)
REQUEST_TIMEOUT = 30       # 请求超时(秒)

# --- 股票代码前缀映射 ---
# 上交所: 60xxxx, 688xxx
# 深交所: 00xxxx, 30xxxx, 002xxx, 003xxx
SHANGHAI_PREFIXES = ("60", "68")
SHENZHEN_PREFIXES = ("00", "30", "002", "003")

# --- 列名映射：中文 -> 英文 ---
# 利润表
INCOME_STATEMENT_MAP = {
    "报告期": "report_date",
    "营业总收入": "total_revenue",
    "营业收入": "total_revenue",
    "营业总成本": "total_cost",
    "营业成本": "operating_cost",
    "销售费用": "selling_expense",
    "管理费用": "admin_expense",
    "财务费用": "finance_expense",
    "研发费用": "rd_expense",
    "营业利润": "operating_profit",
    "利润总额": "total_profit",
    "所得税费用": "income_tax",
    "净利润": "net_profit",
    "归属于母公司股东的净利润": "net_profit_attributable",
    "扣非净利润": "net_profit_deducted",
    "基本每股收益": "eps",
    "稀释每股收益": "diluted_eps",
    "利息收入": "interest_income",
    "利息支出": "interest_expense",
    "投资收益": "investment_income",
    "营业外收入": "non_operating_income",
    "营业外支出": "non_operating_expense",
    "其他收益": "other_income",
    "信用减值损失": "credit_impairment_loss",
    "资产减值损失": "asset_impairment_loss",
    "公允价值变动收益": "fair_value_change",
    "资产处置收益": "asset_disposal_income",
    "综合收益总额": "total_comprehensive_income",
    "营业总收入(万元)": "total_revenue",
    "营业总收入(元)": "total_revenue",
}

# 资产负债表
BALANCE_SHEET_MAP = {
    "报告期": "report_date",
    "资产总计": "total_assets",
    "流动资产合计": "current_assets",
    "货币资金": "cash_and_equivalents",
    "交易性金融资产": "trading_financial_assets",
    "应收账款": "accounts_receivable",
    "存货": "inventory",
    "非流动资产合计": "non_current_assets",
    "固定资产": "fixed_assets",
    "在建工程": "construction_in_progress",
    "无形资产": "intangible_assets",
    "商誉": "goodwill",
    "长期股权投资": "long_term_equity_investment",
    "负债合计": "total_liabilities",
    "流动负债合计": "current_liabilities",
    "短期借款": "short_term_borrowing",
    "应付账款": "accounts_payable",
    "非流动负债合计": "non_current_liabilities",
    "长期借款": "long_term_borrowing",
    "所有者权益合计": "total_equity",
    "归属于母公司股东权益合计": "equity_attributable",
    "实收资本（或股本）": "paid_in_capital",
    "资本公积": "capital_reserve",
    "盈余公积": "surplus_reserve",
    "未分配利润": "undistributed_profit",
    "少数股东权益": "minority_interest",
    "资产总计(万元)": "total_assets",
    "负债和所有者权益(或股东权益)总计": "total_liabilities_and_equity",
}

# 现金流量表
CASH_FLOW_MAP = {
    "报告期": "report_date",
    "经营活动产生的现金流量净额": "operating_cash_flow",
    "投资活动产生的现金流量净额": "investing_cash_flow",
    "筹资活动产生的现金流量净额": "financing_cash_flow",
    "经营活动现金流入小计": "operating_cash_inflow",
    "经营活动现金流出小计": "operating_cash_outflow",
    "销售商品、提供劳务收到的现金": "cash_from_sales",
    "投资活动现金流入小计": "investing_cash_inflow",
    "投资活动现金流出小计": "investing_cash_outflow",
    "筹资活动现金流入小计": "financing_cash_inflow",
    "筹资活动现金流出小计": "financing_cash_outflow",
    "期末现金及现金等价物余额": "cash_balance_end",
    "期初现金及现金等价物余额": "cash_balance_begin",
    "现金及现金等价物净增加额": "net_cash_increase",
    "汇率变动对现金的影响": "fx_effect",
    "净利润": "net_profit",  # 现金流量表附表也有净利润
    "购建固定资产、无形资产和其他长期资产支付的现金": "capex",
}

# --- 财务指标阈值（用于报告中的颜色标注）---
# 格式: (优秀上界, 健康下界, 健康上界, 危险下界)
# 优秀 绿色 | 健康 正常 | 警告 黄色 | 危险 红色
THRESHOLDS = {
    # 盈利能力
    "roe": {"excellent": 20, "healthy": 10, "warning": 5},       # >=20%优秀, >=10%健康, >=5%警告, <5%危险
    "roa": {"excellent": 10, "healthy": 5, "warning": 2},
    "gross_margin": {"excellent": 50, "healthy": 30, "warning": 15},
    "net_margin": {"excellent": 20, "healthy": 10, "warning": 5},

    # 偿债能力
    "debt_to_equity": {"excellent": 50, "healthy": 100, "warning": 200},  # 资产负债率(%)
    "current_ratio": {"excellent": 2.0, "healthy": 1.5, "warning": 1.0},    # 流动比率
    "quick_ratio": {"excellent": 1.5, "healthy": 1.0, "warning": 0.5},      # 速动比率

    # 成长能力
    "revenue_growth": {"excellent": 30, "healthy": 15, "warning": 5},       # 营收增长率(%)
    "net_profit_growth": {"excellent": 30, "healthy": 15, "warning": 5},    # 净利润增长率(%)

    # 营运能力
    "asset_turnover": {"excellent": 1.0, "healthy": 0.5, "warning": 0.3},   # 总资产周转率
    "inventory_turnover": {"excellent": 8, "healthy": 4, "warning": 2},     # 存货周转率
}

# --- 估值阈值 ---
# PE较高可能高估，较低可能低估
# PB较高可能高估
PE_WARNING = 50      # PE > 50 标记警告
PB_WARNING = 10      # PB > 10 标记警告
