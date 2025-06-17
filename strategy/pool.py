"""
股池策略模块
"""
from core.data import MyXtData
from utils.logger import logger
from utils.anis import GREEN, RESET

def is_main_board(stock_code):
    """
    判断股票是否在主板
    
    参数:
        stock_code (str): 股票代码
    
    返回:
        bool: 是否为主板股票
    """
    if '.' in stock_code:
        stock_code = stock_code.split('.')[0]
    return stock_code.startswith('60') or stock_code.startswith('00')

def is_st(stock_name):
    """
    判断股票是否是ST股票
    
    参数:
        stock_name (str): 股票名称
    
    返回:
        bool: 是否为ST股票
    """
    return 'ST' in stock_name or '*ST' in stock_name

def get_stock_pool_in_main_board():
    """
    获取主板股票池（非ST股票）
    
    返回:
        list: 符合条件的股票代码列表
    """
    logger.info(f"{GREEN}【获取股票池】{RESET}正在获取主板股票池...")
    data_api = MyXtData()
    stock_list = data_api.get_stock_list_in_sector('沪深A股')
    result = [stock for stock in stock_list if is_main_board(stock) and not is_st(stock)]
    logger.info(f"{GREEN}【获取股票池】{RESET}成功获取{len(result)}只股票")
    return result

