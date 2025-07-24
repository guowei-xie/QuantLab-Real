from xtquant import xtconstant
from datetime import datetime, timedelta
from utils.anis import RED, GREEN, YELLOW, BLUE, RESET
import time
from utils.logger import logger
from configparser import ConfigParser


def add_stock_suffix(stock_code):
    """
    为给定的股票代码添加相应的后缀
    
    参数:
        stock_code (str): 股票代码，6位数字
        
    返回:
        str: 添加后缀的股票代码
        
    异常:
        ValueError: 当股票代码不是6位数字时抛出
    """

    # 如果已经有后缀，直接返回
    if '.' in stock_code:
        return stock_code
        
    # 检查股票代码是否为6位数字
    if len(stock_code) != 6 or not stock_code.isdigit():
        raise ValueError("股票代码必须是6位数字")

    # 根据股票代码的前缀添加相应的后缀
    if stock_code.startswith(("00", "30", "15", "16", "18", "12")):
        return f"{stock_code}.SZ"  # 深圳证券交易所
    elif stock_code.startswith(("60", "68", "11")):
        return f"{stock_code}.SH"  # 上海证券交易所
    elif stock_code.startswith(("83", "43")):
        return f"{stock_code}.BJ"  # 北京证券交易所
    
    return f"{stock_code}.SH"  # 默认为上海证券交易所

def add_stock_suffix_list(stock_code_list):
    """
    为给定的股票代码列表添加相应的后缀
    """
    return [add_stock_suffix(stock) for stock in stock_code_list]

def timestamp_to_datetime_string(timestamp):
    """
    将时间戳转换为时间字符串
    
    参数:
        timestamp (float): 时间戳（秒级）
        
    返回:
        str: 格式化的时间字符串 'YYYY-MM-DD HH:MM:SS'
    """
    dt_object = datetime.fromtimestamp(timestamp)
    return dt_object.strftime('%Y-%m-%d %H:%M:%S')

def timestamp_to_date_number(timestamp):
    """
    将时间戳转换为日期数字格式
    
    参数:
        timestamp (float): 时间戳（可以是秒级或毫秒级）
        
    返回:
        str: 格式化的日期字符串 'YYYYMMDD'
    """
    # 判断是否为毫秒级时间戳（通常大于10^12）
    if timestamp > 10**12:
        timestamp = timestamp / 1000.0
    return datetime.fromtimestamp(timestamp).strftime('%Y%m%d')

def timestamp_to_date_number_plus_n_days(timestamp, n=1):
    """
    将时间戳转换为日期数字格式，并加n天
    """
    date_number = timestamp_to_date_number(timestamp)
    year = int(date_number[:4])
    month = int(date_number[4:6])
    day = int(date_number[6:8])
    next_day = datetime(year, month, day) + timedelta(days=n)
    return next_day.strftime('%Y%m%d')

def parse_order_type(order_type):
    """
    解析订单类型为可读文本
    
    参数:
        order_type (int): 订单类型常量
        
    返回:
        str: 带颜色格式的订单类型文本
    """
    if order_type == xtconstant.STOCK_BUY:
        return f"{RED}买入{RESET}"
    elif order_type == xtconstant.STOCK_SELL:
        return f"{GREEN}卖出{RESET}"
    else:
        return f"{YELLOW}未知类型({order_type}){RESET}"

def convert_to_current_date(timestamp):
    """
    将时间戳的日期部分转换为当前日期，保留原时间部分
    
    参数:
        timestamp (float): 原始时间戳
        
    返回:
        float: 调整后的时间戳
    """
    # 将时间戳转换为 datetime 对象
    dt = datetime.fromtimestamp(timestamp)
    
    # 获取当前日期
    current_date = datetime.now().date()
    
    # 创建一个新的 datetime 对象，使用当前日期和原始时间戳的时间部分
    new_dt = datetime.combine(current_date, dt.time())

    return new_dt.timestamp()

def calculate_volume(total_amount, price):
    """
    根据总额和价格计算交易数量，确保股数是100的整数倍
    """
    if total_amount is None or price is None:
        return 0
    if total_amount == 0 or price == 0:
        return 0
    max_shares = total_amount // price
    shares = (max_shares // 100) * 100
    return int(shares)

def nearest_close_date_number():
    """
    获取当前时间最近的收盘日期数字
    
    返回:
        str: 日期数字格式 'YYYYMMDD'
    """
    config = ConfigParser()
    config.read('config.ini', encoding='utf-8')
    if config.get('BACKTEST', 'TURN_ON') == 'True':
        custom_time = config.get('BACKTEST', 'TODAY_DATE', fallback=None)
    else:
        custom_time = None

    if custom_time is not None:
        # 适用于回测，传入自定义日期数字格式，如'20250719'
        return custom_time

    current_time = time.strftime('%H:%M:%S', time.localtime(time.time()))
    if current_time < '15:00:00':
        return timestamp_to_date_number(time.time() - 86400)
    else:
        return timestamp_to_date_number(time.time())

def is_trading_time():
    """
    判断当前是否为交易时间
    """
    current_time = time.strftime('%H:%M:%S', time.localtime(time.time()))
    # 9:30 ~ 11:30  13:00 ~ 15:00 交易时间
    if current_time < '09:30:05' or current_time > '14:55:00' or (current_time > '11:30:00' and current_time < '13:00:00'):
        return False
    else:
        return True
    
def current_date_number():
    """
    获取当前日期数字
    """
    return timestamp_to_date_number(time.time())