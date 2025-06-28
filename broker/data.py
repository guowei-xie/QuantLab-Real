from xtquant import xtdata
from utils.logger import logger
from tqdm import tqdm
from utils.anis import GREEN, RESET, YELLOW, RED
from utils.util import add_stock_suffix, add_stock_suffix_list, timestamp_to_date_number
import pandas as pd
import time


"""
行情数据处理模块，封装xtquant的数据接口
"""

def download_history_data(stock_list=None, start_time='20250101', period='1d', progress_bar=True):
    """
    补全历史数据
    
    参数:
        stock_list (list): 股票代码列表
        start_time (str): 开始时间，格式为'YYYYMMDD'
        period (str): 周期，如'1d'表示日线
        progress_bar (bool): 是否显示进度条
    """
    if not stock_list:
        logger.warning(f"{YELLOW}【下载历史数据】{RESET} 股票列表为空")
        return
        
    iterator = tqdm(stock_list, desc=f"{GREEN}下载历史数据{RESET}", ncols=100, colour="green") if progress_bar else stock_list
    for code in iterator:
        xtdata.download_history_data(code, period=period, start_time=start_time, incrementally=True)

def get_daily_data(stock_list=['000001.SZ'], period='1d', start_time='', end_time='', count=100):
    """
    获取行情数据
    
    参数:
        stock_list (list): 股票代码列表
        period (str): 周期，如'1d'表示日线
        start_time (str): 开始时间
        end_time (str): 结束时间
        count (int): 获取的数据条数
        
    返回:
        pandas.DataFrame: 行情数据
    """

    try:
        dict_data = xtdata.get_market_data_ex(
            field_list=[],
            stock_list=add_stock_suffix_list(stock_list),
            period=period,
            start_time=start_time,
            end_time=end_time,
            count=count,
            dividend_type='none',
            fill_data=True
        )
        return dict_data
    except Exception as e:
        logger.error(f"{RED}【行情数据获取失败】{RESET} {e}")
        return {}

def get_stock_list_in_sector(sector_name):
    """
    获取板块股票列表
    
    参数:
        sector_name (str): 板块名称
        
    返回:
        list: 板块内的股票代码列表
    """
    try:
        stock_list = xtdata.get_stock_list_in_sector(sector_name)
        logger.info(f"{GREEN}【获取板块成份股】{RESET} {sector_name}: 共{len(stock_list)}只股票")
        return stock_list
    except Exception as e:
        logger.error(f"{RED}【获取板块成份股失败】{RESET} {sector_name}: {e}")
        return []

def get_stock_info(stock_code):
    """
    获取股票基本信息
    
    参数:
        stock_code (str): 股票代码
        
    返回:
        dict: 股票信息字典，包含股票名称、停牌状态、市值等信息
    """
    try:
        stock_code_with_suffix = add_stock_suffix(stock_code)
        detail = xtdata.get_instrument_detail(stock_code_with_suffix)
 
        if detail is None:
            return None
        
        # 获取停牌状态 (InstrumentStatus<=0:正常交易（-1:复牌）;>=1停牌天数)
        instrument_status = detail.get('InstrumentStatus', 0)
        is_suspended = 1 if instrument_status >= 1 else 0  # 1表示停牌，0表示正常交易
            
        result = {
            '股票名称': detail.get('InstrumentName', ''),
            '停牌状态': is_suspended,
            '总市值': detail.get('TotalVolume', 0) * detail.get('PreClose', 0),
            '流通市值': detail.get('FloatVolume', 0) * detail.get('PreClose', 0),
            '当日涨停价': detail.get('UpStopPrice', 0),
            '当日跌停价': detail.get('DownStopPrice', 0),
            '前收盘价': detail.get('PreClose', 0),
            '流通股本': detail.get('FloatVolume', 0),
            '是否可交易': detail.get('IsTrading', True)
        }
        
        return result
    except Exception as e:
        logger.error(f"{RED}【获取股票信息失败】{RESET} {stock_code}: {e}")
        return None

def get_latest_price(stock_code):
    """
    获取最新价格
    
    参数:
        stock_code (str): 股票代码
        
    返回:
        float: 最新价格，失败返回None
    """
    stock_code_with_suffix = add_stock_suffix(stock_code)
    try:
        tick_data = xtdata.get_full_tick([stock_code_with_suffix])
        if stock_code_with_suffix in tick_data and 'lastPrice' in tick_data[stock_code_with_suffix]:
            return tick_data[stock_code_with_suffix]['lastPrice']
        else:
            logger.warning(f"{YELLOW}【获取最新价格失败】{RESET} {stock_code}: 无数据")
        return None
    except Exception as e:
        logger.error(f"{RED}【获取最新价格失败】{RESET} {stock_code}: {e}")
        return None
    
def get_stock_name(stock_code):
    """
    获取股票名称
    """
    stock_code_with_suffix = add_stock_suffix(stock_code)
    return xtdata.get_instrument_detail(stock_code_with_suffix)['InstrumentName']
    
def subscribe_quote(stock_code, period, log_info=True, callback=None):
    """
    订阅股票行情数据
    
    参数:
        stock_code (str): 股票代码，如 '000001.SZ'
        period (str): 行情周期，支持 '1m'、'5m'、'15m'、'1d'、'tick' 等
        callback (callable): 行情数据回调函数
        
    返回:
        bool: 订阅是否成功
    """
    try:
        xtdata.subscribe_quote(stock_code, period=period, callback=callback)
        if log_info:
            logger.info(f"{GREEN}【订阅成功】{RESET} 股票:{stock_code} {get_stock_name(stock_code)} 周期:{period}")
        return True
    except Exception as e:
        if log_info:
            logger.error(f"{RED}【订阅失败】{RESET} 股票:{stock_code} {get_stock_name(stock_code)} 周期:{period} 错误:{e}")
        return False

def unsubscribe_quote(stock_code):
    """
    取消订阅股票行情数据
    
    参数:
        stock_code (str): 股票代码，如 '000001.SZ'
        
    返回:
        bool: 取消订阅是否成功
    """
    try:
        xtdata.unsubscribe_quote(stock_code)
        logger.info(f"{GREEN}【取消订阅成功】{RESET} 股票:{stock_code}")
        return True
    except Exception as e:
        logger.error(f"{RED}【取消订阅失败】{RESET} 股票:{stock_code} 错误:{e}")
        return False

def do_subscribe_quote(stock_list, period, callback=None):
    """
    订阅股票行情数据
    """
    for stock in stock_list:
        subscribe_quote(stock, period, callback=callback)
    time.sleep(1)

def prepare_open_data(stock_code, trade_date):
    """
    准备trade_date日的开盘数据
    """
    daily_data = get_daily_data([stock_code], '1d', start_time=trade_date, count=1)
    info_data = get_stock_info(stock_code)
    if daily_data[stock_code]['open'].empty or info_data is None:
        logger.warning(f"{YELLOW}【准备开盘数据】{RESET} 股票:{stock_code} 交易日期:{trade_date} 无数据")
        return None
    return {
        'stock_name': info_data['股票名称'],
        'limit_up_price': info_data['当日涨停价'],
        'limit_down_price': info_data['当日跌停价'],
        'open_price': daily_data[stock_code]['open'],
        'preclose_price': info_data['前收盘价'],
    }

