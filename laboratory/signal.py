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
    limit_up_price = open_data['limit_up_price'] * 0.98
    latest_open_price = gmd_data['open'].iloc[-1] # 最新开盘价
    latest_close_price = gmd_data['close'].iloc[-1] # 最新收盘价
    open_price = open_data['open_price'] # 开盘价

    # 涨停，并且不是一字板（开盘价等于涨停价）
    if latest_open_price < limit_up_price and latest_close_price >= limit_up_price:
        if open_price >= limit_up_price:
            return False # 一字板或T字板
        logger.info(f"{GREEN}【信号生成】{RESET} 股票{stock_code}触发涨停打板信号")
        return {
            "stock_code": stock_code,
            "signal_type": "BUY_VALUE",
            "value": fixed_value,
            "price": limit_up_price,
            "signal_name": "涨停打板买入"
        }
    
    return {}

def signal_by_open_down(stock_code, gmd_data, open_data, start_minutes=1, end_minutes=2):
    """
    开盘后指定时间段内，股价低于开盘价时生成清仓信号
    
    参数:
        stock_code (str): 股票代码
        gmd_data (DataFrame): 包含最新1m行情数据的DataFrame，需要包含'time'和'close'列
        open_data (dict): 开盘数据字典，包含'open_price'键
        start_minutes (int, optional): 开盘后开始监控的分钟数，默认1分钟
        end_minutes (int, optional): 开盘后结束监控的分钟数，默认2分钟
        
    返回:
        dict: 如果触发信号返回包含清仓指令的字典，否则返回空字典
             信号格式: {"stock_code": 股票代码, "signal_type": "SELL_ALL"}
    """
    latest_timestamp = gmd_data['time'].iloc[-1]
    dt = datetime.fromtimestamp(latest_timestamp / 1000)  # 毫秒转秒
    
    # 获取当天的开盘时间（9:30）
    market_open_time = datetime.combine(dt.date(), time(9, 30))
    market_open_timestamp = int(market_open_time.timestamp() * 1000)  # 转为毫秒
    
    # 计算时间差（毫秒）并转换为分钟
    time_diff_minutes = (latest_timestamp - market_open_timestamp) / (60 * 1000)
    
    # 如果不在开盘后指定分钟内，返回空信号
    if not (start_minutes <= time_diff_minutes <= end_minutes): 
        return {}

    latest_close_price = gmd_data['close'] # 最新分钟K线收盘价
    open_price = open_data['open_price'] # 开盘价
    
    # 开盘趋势向下
    if latest_close_price < open_price:
        logger.info(f"{GREEN}【信号生成】{RESET} 股票{stock_code}触发开盘趋势向下清仓信号")
        return {
            "stock_code": stock_code,
            "price": latest_close_price * 0.98,
            "signal_type": "SELL_ALL",
            "signal_name": "开盘趋势向下清仓"
        }
    return {}

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
        logger.info(f"{GREEN}【信号生成】{RESET} 股票{stock_code}触发炸板清仓信号")
        return {
            "stock_code": stock_code,
            "signal_type": "SELL_ALL",
            "price": latest_close_price * 0.98,
            "signal_name": "炸板清仓"
        }
    return {}

# 根据macd信号分批卖出信号
def signal_by_macd_sell(stock_code, gmd_data, open_data):
    """
    MACD柱见顶卖出信号
    
    检测MACD柱见顶信号，如果MACD柱形成顶部拐点，则生成卖出信号。
    MACD柱见顶定义：上一分钟MACD柱小于上上一根MACD柱，且上上一根MACD柱大于再上一根MACD柱。
    注意：若当前股价处于涨停状态，则不生成卖出信号。
    
    参数:
        stock_code (str): 股票代码
        gmd_data (DataFrame): 包含最新行情数据的DataFrame，用于计算MACD指标
        open_data (dict): 开盘数据字典，包含'limit_up_price'键
        
    返回:
        dict: 如果触发信号返回包含按比例卖出指令的字典，否则返回空字典
             信号格式: {"stock_code": 股票代码, "signal_type": "SELL_PERCENT", "signal_name": "macd柱见顶卖出"}
    """
    latest_price = gmd_data['close'].iloc[-1]
    limit_up_price = open_data['limit_up_price'] * 0.98
    if latest_price >= limit_up_price:
        return {}

    macd_data = caculate_macd(gmd_data)
    if is_macd_top(macd_data):
        logger.info(f"{GREEN}【信号生成】{RESET} 股票{stock_code}触发分时见顶卖出信号")
        return {
            "stock_code": stock_code,
            "signal_type": "SELL_PERCENT",
            "signal_name": "macd柱见顶卖出"
        }
    return {}