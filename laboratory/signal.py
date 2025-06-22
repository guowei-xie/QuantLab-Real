from broker.data import get_stock_info, get_latest_price, get_daily_data
from datetime import datetime, time
from laboratory.utils import caculate_macd, is_macd_top

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
    
    参数:
        stock_code (str): 股票代码
        gmd_data (DataFrame): 包含最新1m行情数据的DataFrame，需要包含'open'和'close'列
        open_data (dict): 开盘数据字典，包含'limit_up_price'和'open_price'键
        
    返回:
        dict: 如果触发信号返回包含清仓指令的字典，否则返回空字典
             信号格式: {"stock_code": 股票代码, "signal_type": "SELL_ALL"}
    """
    latest_open_price = gmd_data['open'].iloc[-1] # 最新开盘价
    latest_close_price = gmd_data['close'].iloc[-1] # 最新收盘价
    latest_preclose_price = gmd_data['preClose'].iloc[-1] # 上一根K线收盘价
    limit_up_price = open_data['limit_up_price'] * 0.98

    # 当前分钟K线收盘价低于涨停价，当前K线开盘价或上一根K线收盘价大于涨停价，则生成清仓信号
    if latest_close_price < limit_up_price and (latest_open_price >= limit_up_price or latest_preclose_price >= limit_up_price):
        return {
            "stock_code": stock_code,
            "signal_type": "SELL_ALL",
            "price": latest_close_price * 0.98,
            "signal_name": "炸板清仓"
        }
    return {}

# 根据macd信号分批卖出信号
def signal_by_macd_sell(stock_code, gmd_data, open_data):
    # 检测macd柱见顶信号，如果macd柱见顶，则生成卖出信号
    # macd柱见顶：即上一分钟macd柱小于上上一根macd柱，并且上上一根macd柱大于再上一根macd柱，则生成卖出信号
    macd_data = caculate_macd(gmd_data)
    if is_macd_top(macd_data):
        return {
            "stock_code": stock_code,
            "signal_type": "SELL_PERCENT",
            "percent": 0.5,
            "signal_name": "macd柱见顶卖出"
        }
    return {}