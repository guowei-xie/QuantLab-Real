"""
股票池筛选模块
"""
from broker.data import *
from utils.logger import logger
from utils.anis import GREEN, RESET
from laboratory.utils  import *

def get_stock_pool_in_main_board():
    """
    获取主板股票池（非ST股票）,非停牌股票
    
    返回:
        list: 符合条件的股票代码列表
    """
    stock_list = get_stock_list_in_sector('沪深A股')
    result = [stock for stock in stock_list if is_main_board(stock) and not is_st(stock) and not is_suspended(stock) and not is_delisting(stock)]
    logger.info(f"{GREEN}【获取主板股票池】{RESET}筛选主板股票池，成功获取{len(result)}只股票")
    return result

