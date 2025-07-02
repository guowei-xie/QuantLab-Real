"""
交易信号生成模块

本模块包含各种交易信号生成函数，用于根据市场数据和技术指标生成买入或卖出信号。
每个信号函数接收股票代码、行情数据和开盘数据等参数，返回标准格式的交易信号字典。

信号类型包括:
- BUY_VALUE: 按金额买入
- SELL_ALL: 清仓卖出
- SELL_PERCENT: 按比例卖出
"""

from broker.data import get_stock_info, get_latest_price, get_daily_data
from datetime import datetime, time
from laboratory.utils import caculate_macd, is_macd_top
from utils.logger import logger
from utils.anis import GREEN, RESET, YELLOW

def signal_by_board_hitting(stock_code, gmd_data, open_data, fixed_value=10000):
    """
    涨停打板信号（排除一字板和T字板）
    
    参数:
        stock_code (str): 股票代码
        gmd_data (DataFrame): 包含最新1m行情数据的DataFrame，需要包含'open'和'close'列
        open_data (dict): 开盘数据字典，包含'limit_up_price'和'open_price'键
        fixed_value (int, optional): 买入金额，默认10000元
        
    返回:
        dict: 如果触发信号返回包含交易指令的字典，否则返回空字典
             信号格式: {"stock_code": 股票代码, "signal_type": "BUY_VALUE", "value": 买入金额, "price": 买入价格}
    """
    limit_up_price = open_data['limit_up_price']
    latest_open_price = gmd_data['open'].iloc[-1] # 1m开盘价
    latest_close_price = gmd_data['close'].iloc[-1] # 1m收盘价
    open_price = open_data['open_price'].iloc[-1] # 1d开盘价

    # 涨停，并且不是一字板（开盘价等于涨停价）
    if latest_open_price < limit_up_price and latest_close_price >= limit_up_price * 0.998:
        if open_price >= limit_up_price :
            return {} # 一字板或T字板
        log_info = f"{GREEN}【信号生成】{RESET} 股票{stock_code}触发涨停打板信号"
        return {
            "stock_code": stock_code,
            "signal_type": "BUY_VALUE",
            "value": fixed_value,
            "price": limit_up_price,
            "signal_name": "涨停打板买入",
            "log_info": log_info
        }
    
    return {}

def signal_by_open_down(stock_code, gmd_data, open_data, delay_seconds = 30, down_percent = 0.01, is_down_preclose = True):
    """
    开盘后指定时间段内，股价相对开盘价下跌指定百分比（down_percent）时生成清仓信号
    如果设置is_down_preclose为True，则首先判断当前价格是否低于上一日收盘价，如果不低于，则返回空信号
    
    参数:
        stock_code (str): 股票代码
        gmd_data (DataFrame): 包含最新1m行情数据的DataFrame，需要包含'time'和'close'列
        open_data (dict): 开盘数据字典，包含'open_price'键
        delay_seconds (int, optional): 开盘后开始监控的秒数，默认60秒
        down_percent (float, optional): 股价相对开盘价下跌的百分比，默认1%
        is_down_preclose (bool, optional): 是否判断当前股价是否低于上一日收盘价，默认True
    返回:
        dict: 如果触发信号返回包含清仓指令的字典，否则返回空字典
             信号格式: {"stock_code": 股票代码, "signal_type": "SELL_ALL"}
    """
    # 使用系统当前时间
    current_time = datetime.now()
    
    # 获取当天的开盘时间（9:30）
    current_date = current_time.date()
    market_open_time = datetime.combine(current_date, time(9, 30))
    
    # 计算时间差（秒）
    time_diff_seconds = (current_time - market_open_time).total_seconds()

    latest_close_price = gmd_data['close'].iloc[-1]  # 最新分钟K线收盘价
    open_price = open_data['open_price'].iloc[-1]  # 开盘价
    down_price = open_price * (1 - down_percent)

    # 如果开盘后指定秒数内、开盘后指定秒数+60秒外，或股价下跌不到指定百分比时，返回空信号
    if not (delay_seconds <= time_diff_seconds <= delay_seconds + 30): 
        return {}
    
    # 如果is_down_preclose为True，则首先判断当前价格是否低于上一日收盘价，如果不低于，则返回空信号
    if is_down_preclose:
        latest_preclose_price = open_data['preclose_price']  # 上一根日K线收盘价
        if latest_close_price >= latest_preclose_price:
            return {}
    
    # 如果股价下跌不到指定百分比，返回空信号
    if latest_close_price >= down_price:
        return {}

    log_info = f"{GREEN}【信号生成】{RESET} 股票{stock_code}开盘{delay_seconds}秒内趋势向下，触发清仓条件"
    return {
            "stock_code": stock_code,
            "price": latest_close_price * 0.98,
            "signal_type": "SELL_ALL",
            "signal_name": "开盘清仓",
            "log_info": log_info
        }

# 炸板清仓
def signal_by_board_explosion(stock_code, gmd_data, open_data):
    """
    炸板清仓信号
    
    当股票从涨停状态回落时触发清仓信号，即股价从涨停板回落（炸板）时卖出。
    
    参数:
        stock_code (str): 股票代码
        gmd_data (DataFrame): 包含最新1m行情数据的DataFrame，需要包含'open'、'close'和'preClose'列
        open_data (dict): 开盘数据字典，包含'limit_up_price'键
        
    返回:
        dict: 如果触发信号返回包含清仓指令的字典，否则返回空字典
             信号格式: {"stock_code": 股票代码, "signal_type": "SELL_ALL", "price": 卖出价格}
    """
    latest_open_price = gmd_data['open'].iloc[-1] # 最新开盘价
    latest_close_price = gmd_data['close'].iloc[-1] # 最新收盘价
    latest_preclose_price = gmd_data['preClose'].iloc[-1] # 上一根K线收盘价
    limit_up_price = open_data['limit_up_price'] * 0.98

    # 当前分钟K线收盘价低于涨停价，当前K线开盘价或上一根K线收盘价大于涨停价，则生成清仓信号
    if latest_close_price < limit_up_price and (latest_open_price >= limit_up_price or latest_preclose_price >= limit_up_price):
        log_info = f"{GREEN}【信号生成】{RESET} 股票{stock_code}炸板，触发清仓条件"
        return {
            "stock_code": stock_code,
            "signal_type": "SELL_ALL",
            "price": latest_close_price * 0.98,
            "signal_name": "炸板清仓",
            "log_info": log_info
        }
    return {}

# 根据macd信号分批卖出信号
def signal_by_macd_sell(stock_code, gmd_data, open_data, is_down_preclose = True):
    """
    MACD柱见顶卖出信号
    
    检测MACD柱见顶信号，如果MACD柱形成顶部拐点，则生成卖出信号。
    MACD柱见顶定义：上一分钟MACD柱小于上上一根MACD柱，且上上一根MACD柱大于再上一根MACD柱。
    注意：若当前股价处于涨停状态，或(is_down_preclose为True时)当前股价高于上一日收盘价，则不生成卖出信号。
    
    参数:
        stock_code (str): 股票代码
        gmd_data (DataFrame): 包含最新行情数据的DataFrame，用于计算MACD指标
        open_data (dict): 开盘数据字典，包含'limit_up_price'键
        is_down_preclose (bool, optional): 是否判断当前股价是否低于上一日收盘价，默认True
    返回:
        dict: 如果触发信号返回包含按比例卖出指令的字典，否则返回空字典
             信号格式: {"stock_code": 股票代码, "signal_type": "SELL_PERCENT", "percent": 卖出比例, "signal_name": "macd柱见顶卖出"}
    """
    latest_price = gmd_data['close'].iloc[-1]
    limit_up_price = open_data['limit_up_price']
    latest_preclose_price = open_data['preclose_price']

    if is_down_preclose:
        if latest_price >= latest_preclose_price:
            return {}

    if latest_price >= limit_up_price:
        return {}

    macd_data = caculate_macd(gmd_data)
    if is_macd_top(macd_data):
        log_info = f"{GREEN}【信号生成】{RESET} 股票{stock_code}MACD柱见顶，触发分批卖出条件"
        return {
            "stock_code": stock_code,
            "signal_type": "SELL_PERCENT",
            "price": latest_price * 0.99,
            "percent": 1.0,
            "signal_name": "MACD分批卖出",
            "log_info": log_info
        }
    return {}