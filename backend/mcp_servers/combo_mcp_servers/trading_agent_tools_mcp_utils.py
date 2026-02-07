from datetime import datetime
from typing import Annotated, Dict
import pandas as pd

from data_processing.data_provider.tushare import Tushare


def get_china_stock_data_tushare(
    ticker: Annotated[str, "中国股票代码，如：000001、600036等"],
    start_date: Annotated[str, "开始日期，格式：YYYY-MM-DD"],
    end_date: Annotated[str, "结束日期，格式：YYYY-MM-DD"],
) -> str:
    try:
        print(f"📊 [Tushare] 获取{ticker}股票数据...")
        tushare_processor = Tushare()
        data = tushare_processor.get_stock_daily(ticker, start_date, end_date)
        if data is not None and not data.empty:
            data = validate_and_standardize_data(data)
        else:
            import pandas as pd
            data = pd.DataFrame()

        if data is not None and not data.empty:
            # 获取股票基本信息
            stock_info = tushare_processor.get_stock_info(ticker)
            stock_name = stock_info.get('name', f'股票{ticker}') if stock_info else f'股票{ticker}'

            # 计算最新价格和涨跌幅
            latest_data = data.iloc[-1]
            current_price = f"¥{latest_data['close']:.2f}"

            if len(data) > 1:
                prev_close = data.iloc[-2]['close']
                change = latest_data['close'] - prev_close
                change_pct = (change / prev_close) * 100
                change_pct_str = f"{change_pct:+.2f}%"
            else:
                change_pct_str = "N/A"

            # 格式化成交量 - 修复成交量显示问题
            volume = 0
            if 'vol' in latest_data.index:
                volume = latest_data['vol']
            elif 'volume' in latest_data.index:
                volume = latest_data['volume']

            # 处理NaN值
            import pandas as pd
            if pd.isna(volume):
                volume = 0

            if volume > 10000:
                volume_str = f"{volume/10000:.1f}万手"
            elif volume > 0:
                volume_str = f"{volume:.0f}手"
            else:
                volume_str = "暂无数据"

            # 转换为与TDX兼容的字符串格式
            result = f"# {ticker} 股票数据分析\n\n"
            result += f"## 📊 实时行情\n"
            result += f"- 股票名称: {stock_name}\n"
            result += f"- 股票代码: {ticker}\n"
            result += f"- 当前价格: {current_price}\n"
            result += f"- 涨跌幅: {change_pct_str}\n"
            result += f"- 成交量: {volume_str}\n"
            result += f"- 数据来源: Tushare\n\n"
            result += f"## 📈 历史数据概览\n"
            result += f"- 数据期间: {start_date} 至 {end_date}\n"
            result += f"- 数据条数: {len(data)}条\n"

            if len(data) > 0:
                period_high = data['high'].max()
                period_low = data['low'].min()
                result += f"- 期间最高: ¥{period_high:.2f}\n"
                result += f"- 期间最低: ¥{period_low:.2f}\n\n"

            result += "## 📋 最新交易数据\n"
            result += data.tail(5).to_string(index=False)

            return result
        else:
            return f"❌ 未能获取{ticker}的股票数据"

    except Exception as e:
        print(e)
        return



# def _get_realtime_data(symbol: str) -> pd.DataFrame:
#     """获取实时数据（使用最新日线数据）"""
#     # Tushare免费版不支持实时数据，使用最新日线数据
#     end_date = datetime.now().strftime('%Y-%m-%d')
#     start_date = (datetime.now() - timedelta(days=5)).strftime('%Y-%m-%d')
#
#     data = self.provider.get_stock_daily(symbol, start_date, end_date)
#
#     if data is not None and not data.empty:
#         # 返回最新一条数据
#         latest_data = data.tail(1)
#         return validate_and_standardize_data(latest_data)
#     else:
#         return pd.DataFrame()

def validate_and_standardize_data(data: pd.DataFrame) -> pd.DataFrame:
    """验证并标准化数据格式，增强版本（修复KeyError: 'volume'问题）"""
    if data.empty:
        print("🔍 [数据标准化] 输入数据为空，直接返回")
        return data

    try:
        # 复制数据避免修改原始数据
        standardized = data.copy()

        # 列名映射
        column_mapping = {
            'trade_date': 'date',
            'ts_code': 'code',
            'open': 'open',
            'high': 'high',
            'low': 'low',
            'close': 'close',
            'vol': 'volume',  # 关键映射：vol -> volume
            'amount': 'amount',
            'pct_chg': 'pct_change',
            'change': 'change'
        }

        # 记录映射过程
        mapped_columns = []

        # 重命名列
        for old_col, new_col in column_mapping.items():
            if old_col in standardized.columns:
                standardized = standardized.rename(columns={old_col: new_col})
                mapped_columns.append(f"{old_col}->{new_col}")

        # 验证关键列是否存在，添加备用处理
        required_columns = ['volume', 'close', 'high', 'low']
        missing_columns = [col for col in required_columns if col not in standardized.columns]
        if missing_columns:
            add_fallback_columns(standardized, missing_columns, data)

        # 确保日期列存在且格式正确
        if 'date' in standardized.columns:
            standardized['date'] = pd.to_datetime(standardized['date'])
            standardized = standardized.sort_values('date')

        # 添加股票代码列（如果不存在）
        if 'code' in standardized.columns and '股票代码' not in standardized.columns:
            standardized['股票代码'] = standardized['code'].str.replace('.SH', '').str.replace('.SZ', '').str.replace('.BJ', '')

        # 添加涨跌幅列（如果不存在）
        if 'pct_change' in standardized.columns and '涨跌幅' not in standardized.columns:
            standardized['涨跌幅'] = standardized['pct_change']
        return standardized

    except Exception as e:
        print(f"❌ [数据标准化] 数据标准化失败: {e}", exc_info=True)
        return data


def get_china_stock_cash_flow_tushare(
    ticker: Annotated[str, "中国股票代码，如：000001、600036等"],
    start_date: Annotated[str, "开始日期，格式：YYYY-MM-DD"],
    end_date: Annotated[str, "结束日期，格式：YYYY-MM-DD"]
) -> str:
    try:
        print(f"📊 [Tushare] 获取{ticker}现金流...")
        tushare_processor = Tushare()
        stock_cash_flow = tushare_processor.get_stock_cash_flow(ticker, start_date, end_date)

        result = f"\n#{ticker}现金流数据：\n"
        result += f"- 股票代码: {stock_cash_flow.get('ts_code')}\n"
        result += f"- 交易日期: {stock_cash_flow.get('trade_date')}\n"
        result += f"- 小单买入金额: {stock_cash_flow.get('buy_sm_amount')}万元\n"
        result += f"- 小单卖出金额: {stock_cash_flow.get('sell_sm_amount')}万元\n"
        result += f"- 中单买入金额: {stock_cash_flow.get('buy_md_amount')}万元\n"
        result += f"- 中单卖出金额: {stock_cash_flow.get('sell_md_amount')}万元\n"
        result += f"- 大单买入金额: {stock_cash_flow.get('buy_lg_amount')}万元\n"
        result += f"- 大单卖出金额: {stock_cash_flow.get('sell_lg_amount')}万元\n"
        result += f"- 特大单买入金额: {stock_cash_flow.get('buy_elg_amount')}万元\n"
        result += f"- 特大单卖出金额: {stock_cash_flow.get('sell_elg_amount')}万元\n"
        result += f"- 净流入额: {stock_cash_flow.get('net_mf_amount')}\n"
        return result
    except Exception as e:
        print(e)
        return

def get_china_stock_tech_tushare(
    ticker: Annotated[str, "中国股票代码，如：000001、600036等"],
    start_date: Annotated[str, "开始日期，格式：YYYY-MM-DD"],
    end_date: Annotated[str, "结束日期，格式：YYYY-MM-DD"]
) -> str:
    try:
        print(f"📊 [Tushare] 获取{ticker}现金流...")
        tushare_processor = Tushare()
        stock_tech = tushare_processor.get_stock_tech(ticker, start_date, end_date)
        result = f"\n#{ticker}技术面数据：\n"
        result += f"- 股票代码: {stock_tech.get('ts_code')}\n"
        result += f"- 交易日期: {stock_tech.get('trade_date')}\n"
        result += f"- 收盘价: {stock_tech.get('close')}\n"
        result += f"- 开盘价: {stock_tech.get('open')}\n"
        result += f"- 最高价: {stock_tech.get('high')}\n"
        result += f"- 最低价: {stock_tech.get('low')}\n"
        result += f"- 昨收价: {stock_tech.get('pre_close')}\n"
        result += f"- 涨跌额: {stock_tech.get('change')}\n"
        result += f"- 涨跌幅%: {stock_tech.get('pct_change')}\n"
        result += f"- 成交量: {stock_tech.get('vol')}手\n"
        result += f"- 成交额: {stock_tech.get('amount')}千元\n"
        result += f"- MACD: {stock_tech.get('macd')}\n"
        result += f"- MACD_DIF: {stock_tech.get('macd_dif')}\n"
        result += f"- MACD_DEA: {stock_tech.get('macd_dea')}\n"
        result += f"- KDJ_K: {stock_tech.get('kdj_k')}\n"
        result += f"- KDJ_D: {stock_tech.get('kdj_d')}\n"
        result += f"- KDJ_J: {stock_tech.get('kdj_j')}\n"
        result += f"- RSI_6: {stock_tech.get('rsi_6')}\n"
        result += f"- RSI_12: {stock_tech.get('rsi_12')}\n"
        result += f"- RSI_24: {stock_tech.get('rsi_24')}\n"
        result += f"- BOLL_UPPER: {stock_tech.get('boll_upper')}\n"
        result += f"- BOLL_MIDDLE: {stock_tech.get('boll_mid')}\n"
        result += f"- BOLL_LOW: {stock_tech.get('boll_lower')}\n"
        result += f"- CCI: {stock_tech.get('cci')}\n"
        return result
    except Exception as e:
        print(e)
        return

def get_fundamentals(symbol: str) -> str:
    try:
        tushare_processor = Tushare()

        # 获取股票基本信息
        stock_info = tushare_processor.get_stock_info(symbol)

        # 获取财务数据
        financial_data = tushare_processor.get_financial_data(symbol)

        # 生成基本面分析报告
        report = generate_fundamentals_report(symbol, stock_info, financial_data)

        return report

    except Exception as e:
        print(e)
        return

def generate_fundamentals_report(symbol: str, stock_info: Dict, financial_data: Dict) -> str:
    """生成基本面分析报告"""

    report = f"📊 {symbol} 基本面分析报告 (Tushare数据源)\n"
    report += "=" * 50 + "\n\n"

    # 基本信息
    report += "📋 基本信息\n"
    report += f"股票代码: {symbol}\n"
    report += f"股票名称: {stock_info.get('name', '未知')}\n"
    report += f"所属地区: {stock_info.get('area', '未知')}\n"
    report += f"所属行业: {stock_info.get('industry', '未知')}\n"
    report += f"上市市场: {stock_info.get('market', '未知')}\n"
    report += f"上市日期: {stock_info.get('list_date', '未知')}\n\n"

    # 财务数据
    if financial_data:
        report += "💰 财务数据\n"

        # 资产负债表
        balance_sheet = financial_data.get('balance_sheet', [])
        if balance_sheet:
            report += "💰 资产负债表\n"
            latest_balance = balance_sheet[0] if balance_sheet else {}
            report += f"总资产: {latest_balance.get('total_assets', 'N/A')}\n"
            report += f"总负债: {latest_balance.get('total_liab', 'N/A')}\n"
            report += f"股东权益: {latest_balance.get('total_hldr_eqy_exc_min_int', 'N/A')}\n"
            report += f"货币资金: {latest_balance.get('money_cap', 'N/A')}\n"
            report += f"交易性金融资产: {latest_balance.get('trad_asset', 'N/A')}\n"
            report += f"短期借款: {latest_balance.get('st_borr', 'N/A')}\n"
            report += f"应收帐款: {latest_balance.get('accounts_receiv', 'N/A')}\n"
            report += f"应付账款: {latest_balance.get('acct_payable', 'N/A')}\n"
            report += f"存货: {latest_balance.get('inventories', 'N/A')}\n"
            report += f"未分配利润: {latest_balance.get('undistr_porfit', 'N/A')}\n"

        # 利润表
        income_statement = financial_data.get('income_statement', [])
        if income_statement:
            report += "💰 利润表\n"
            latest_income = income_statement[0] if income_statement else {}
            report += f"营业收入: {latest_income.get('total_revenue', 'N/A')}\n"
            report += f"营业利润: {latest_income.get('operate_profit', 'N/A')}\n"
            report += f"净利润: {latest_income.get('n_income', 'N/A')}\n"
            report += f"扣非净利润: {latest_income.get('net_after_nr_lp_correct', 'N/A')}\n"
            report += f"每股收益: {latest_income.get('basic_eps', 'N/A')}\n"
            report += f"稀释每股收益: {latest_income.get('diluted_eps', 'N/A')}\n"
            report += f"利润总额: {latest_income.get('total_profit', 'N/A')}\n"
            report += f"研发费用: {latest_income.get('rd_exp', 'N/A')}\n"

        # 现金流量表
        cash_flow = financial_data.get('cash_flow', [])
        if cash_flow:
            report += "💰 现金流量表\n"
            latest_cash = cash_flow[0] if cash_flow else {}
            report += f"净利润: {latest_cash.get('net_profit', 'N/A')}\n"
            report += f"经营活动现金流: {latest_cash.get('c_fr_sale_sg', 'N/A')}\n"
            report += f"经营活动中现金流量净额: {latest_cash.get('n_cashflow_act', 'N/A')}\n"
            report += f"自由现金流: {latest_cash.get('free_cashflow', 'N/A')}\n"
            report += f"筹资活动中现金流量净额: {latest_cash.get('n_cash_flows_fnc_act', 'N/A')}\n"
            report += f"投资活动中现金流量净额: {latest_cash.get('n_cashflow_inv_act', 'N/A')}\n"
    else:
        report += "💰 财务数据: 暂无数据\n"

    report += f"\n📅 报告生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
    report += f"📊 数据来源: Tushare\n"

    return report

def add_fallback_columns(self, standardized: pd.DataFrame, missing_columns: list, original_data: pd.DataFrame):
    """为缺失的关键列添加备用值"""
    try:
        import numpy as np
        for col in missing_columns:
            if col == 'volume':
                # 尝试寻找可能的成交量列名
                volume_candidates = ['vol', 'volume', 'turnover', 'trade_volume']
                for candidate in volume_candidates:
                    if candidate in original_data.columns:
                        standardized['volume'] = original_data[candidate]
                        # logger.info(f"✅ [数据标准化] 使用备用列 {candidate} 作为 volume")
                        break
                else:
                    # 如果找不到任何成交量列，设置为0
                    standardized['volume'] = 0
                    # logger.warning(f"⚠️ [数据标准化] 未找到成交量数据，设置为0")

            elif col in ['close', 'high', 'low', 'open']:
                # 对于价格列，如果缺失则设置为NaN
                if col not in standardized.columns:
                    standardized[col] = np.nan
                    # logger.warning(f"⚠️ [数据标准化] 缺失价格列 {col}，设置为NaN")

    except Exception as e:
        print(f"❌ [数据标准化] 添加备用列失败: {e}")

