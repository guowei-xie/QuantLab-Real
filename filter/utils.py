from utils.util import add_stock_suffix
from broker.data import *  
import pandas as pd

def get_stock_market_type(stock_code):
    """
    根据股票代码判断股票所属市场类型
    
    参数:
        stock_code (str): 股票代码，可以带后缀如.SH/.SZ，也可以不带
    
    返回:
        tuple: (市场类型, 涨跌幅限制比例)
    """
    stock_code_with_suffix = add_stock_suffix(stock_code)
    if '.' in stock_code_with_suffix:
        stock_code_with_suffix = stock_code_with_suffix.split('.')[0]
    if stock_code_with_suffix.startswith('688') or stock_code_with_suffix.startswith('689'):
        return 'STAR'
    elif stock_code_with_suffix.startswith('30'):
        return 'GEM'
    elif stock_code_with_suffix.startswith('83'):
        return 'BSE'
    else:
        return 'MAIN'
    
def is_main_board(stock_code):
    """
    判断股票是否在主板
    
    参数:
        stock_code (str): 股票代码
    
    返回:
        bool: 是否为主板股票
    """
    return get_stock_market_type(stock_code) == 'MAIN'

def is_st(stock_code):
    """
    判断股票是否是ST股票
    
    参数:
        stock_name (str): 股票名称
    
    返回:
        bool: 是否为ST股票
    """
    stock_name = get_stock_name(stock_code)
    return 'ST' in stock_name or '*ST' in stock_name

def is_suspended(stock_code):
    """
    判断股票是否停牌
    
    参数:
        stock_code (str): 股票代码
    
    返回:
        bool: 是否停牌
    """
    return get_stock_info(stock_code)['停牌状态'] == 1
    
def get_stock_limit_rate(stock_code):
    """
    根据股票代码获取股票涨跌幅限制比例
    
    参数:
        stock_code (str): 股票代码
    
    返回:
        float: 涨跌幅限制比例
    """
    market_type = get_stock_market_type(stock_code)
    if is_st(stock_code):
        return 0.05
    if market_type == 'STAR':
        return 0.20
    elif market_type == 'GEM':
        return 0.20
    elif market_type == 'BSE':
        return 0.30
    else:
        return 0.10

def is_limit_up(stock_code, price, pre_close, tolerance=0.002):
    """
    判断股票是否涨停(允许误差tolerance)
    
    参数:
        stock_code (str): 股票代码
        price (float): 当前价格
        pre_close (float): 前收盘价
    
    返回:
        bool: 是否涨停
    """
    return price / pre_close - 1 >= get_stock_limit_rate(stock_code) - tolerance
    
def is_limit_down(stock_code, price, pre_close, tolerance=0.002):
    """
    判断股票是否跌停(允许误差tolerance)
    
    参数:
        stock_code (str): 股票代码
        price (float): 当前价格
        pre_close (float): 前收盘价
        tolerance (float): 允许误差
    
    返回:
        bool: 是否跌停
    """
    return price / pre_close - 1 <= -get_stock_limit_rate(stock_code) + tolerance

def is_nearly_limit_up(stock_code, nearly_days=5, tolerance=0.002):
    """
    判断股票是否近nearly_days天有过涨停
    
    参数:
        stock_code (str): 股票代码
        nearly_days (int): 近多少天
        tolerance (float): 允许误差
    """
    dict_data = get_daily_data(stock_list=[stock_code], period='1d', start_time='', end_time='', count=nearly_days)
    df = dict_data.get(stock_code)
    if df is None:
        return False
    for index, row in df.iterrows():   
        if is_limit_up(stock_code, row['close'], row['preClose'], tolerance):
            return True 
    return False
    

