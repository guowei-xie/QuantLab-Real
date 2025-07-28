from utils.util import add_stock_suffix
from broker.data import *  
import pandas as pd
from utils.util import nearest_close_date_number

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

def is_delisting(stock_code):
    """
    判断股票是否退市
    
    参数:
        stock_code (str): 股票代码
    """
    stock_name = get_stock_name(stock_code)
    return '退市' in stock_name

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
        tolerance (float): 允许误差
    
    返回:
        bool: 是否涨停
    """
    return price / pre_close - 1 >= get_stock_limit_rate(stock_code) - tolerance

def is_limit_up_kline(stock_code, kline, tolerance=0.002):
    """
    判断股票是否涨停(允许误差tolerance)
    
    参数:
        kline (DataFrame): 股票日K线数据
        tolerance (float): 允许误差
    
    返回:
        bool: 是否涨停
    """
    return is_limit_up(stock_code, kline['close'], kline['preClose'], tolerance)

def is_word_one_limit_up(stock_code, price, pre_close, open, tolerance=0.002):
    """
    判断股票是否为一字板涨停(允许误差tolerance)
    
    参数:
        stock_code (str): 股票代码
        price (float): 今收盘价
        pre_close (float): 昨收盘价
        open (float): 今开盘价
        tolerance (float): 允许误差
    
    返回:
        bool: 是否为一字板涨停
    """    
    limit_up = is_limit_up(stock_code, price, pre_close, tolerance)
    if limit_up:
        if price == open:
            return True
        else:
            return False
    else:
        return False
    
# 计算单日K线的涨停股价
def caculate_kline_limit_up_price(stock_code, kline, tolerance=0.002):
    """
    计算次日K线的涨停股价
    
    参数:
        stock_code (str): 股票代码
        kline (series): 股票日K线数据
        tolerance (float): 允许误差
    返回:
        float: 涨停股价 
    """
    close_price = kline['close']
    return close_price * (1 + get_stock_limit_rate(stock_code) - tolerance)
    

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

def is_limit_down_kline(stock_code, kline, tolerance=0.002):
    """
    判断股票是否跌停(允许误差tolerance)
    
    参数:
        kline (DataFrame): 股票日K线数据
        tolerance (float): 允许误差
    """
    return is_limit_down(stock_code, kline['close'], kline['preClose'], tolerance)

def is_nearly_limit_up(stock_code, nearly_days=5, tolerance=0.002):
    """
    判断股票是否近nearly_days天有过涨停
    
    参数:
        stock_code (str): 股票代码
        nearly_days (int): 近多少天
        tolerance (float): 允许误差
    """
    end_date = nearest_close_date_number()
    dict_data = get_daily_data(stock_list=[stock_code], period='1d', end_time=end_date, count=nearly_days)
    df = dict_data.get(stock_code)
    if df is None:
        return False
    for index, row in df.iterrows():   
        if is_limit_up(stock_code, row['close'], row['preClose'], tolerance):
            return True 
    return False
    
def get_neary_limit_up_days(stock_code, nearly_days=5, tolerance=0.002, is_word_one=-1):
    """
    获取股票近nearly_days天有过涨停的天数，返回天数
    
    参数:
        stock_code (str): 股票代码
        nearly_days (int): 近多少天
        tolerance (float): 允许误差
        is_word_one (int): 是否为一字板涨停，0为否，1为是,-1为不限
    """
    end_date = nearest_close_date_number()
    dict_data = get_daily_data(stock_list=[stock_code], period='1d', end_time=end_date, count=nearly_days)
    df = dict_data.get(stock_code)
    if df is None:
        return 0
    
    limit_up_days = 0
    
    # 不限涨停类型
    if is_word_one == -1:
        for index, row in df.iterrows():
            if is_limit_up(stock_code, row['close'], row['preClose'], tolerance):
                limit_up_days += 1
    
    # 只统计一字板涨停
    if is_word_one == 1:
        for index, row in df.iterrows():
            if is_word_one_limit_up(stock_code, row['close'], row['preClose'], row['open'], tolerance):
                limit_up_days += 1
    
    # 只统计非一字板涨停
    if is_word_one == 0:
        for index, row in df.iterrows():
            if is_limit_up(stock_code, row['close'], row['preClose'], tolerance) and not is_word_one_limit_up(stock_code, row['close'], row['preClose'], row['open'], tolerance):
                limit_up_days += 1

    return limit_up_days

def get_last_limit_up_kline(stock_code, nearly_days=5, tolerance=0.002):
    """
    获取股票近nearly_days天中，最后一次涨停的K线
    无涨停返回空
    有涨停返回当天该股票的日k线信息
    
    参数:
        stock_code (str): 股票代码
        nearly_days (int): 近多少天
        tolerance (float): 允许误差
    """
    end_date = nearest_close_date_number()
    dict_data = get_daily_data(stock_list=[stock_code], period='1d', end_time=end_date, count=nearly_days)
    df = dict_data.get(stock_code)
    df = df.sort_values(by='time', ascending=False)
    if df is None:
        return None
    for index, row in df.iterrows():
        if is_limit_up(stock_code, row['close'], row['preClose'], tolerance):
            return row
    return None

def get_klines_low_price(stock_code, start_time, end_time):
    """
    获取指定日期区间K线的最低价
    
    参数:
        stock_code (str): 股票代码
        start_time (str): 开始时间
        end_time (str): 结束时间
    """
    dict_data = get_daily_data(stock_list=[stock_code], period='1d', start_time=start_time, end_time=end_time)
    df = dict_data.get(stock_code)
    if df is None:
        return 0
    return df['low'].min()

def is_last_day_limit_up(stock_code, tolerance=0.002):
    """
    判断股票昨天的收盘价是否涨停
    
    参数:
        stock_code (str): 股票代码
        tolerance (float): 允许误差
    """
    end_date = nearest_close_date_number()
    dict_data = get_daily_data(stock_list=[stock_code], period='1d', end_time=end_date, count=1)
    df = dict_data.get(stock_code)
    if df is None:
        return False
    if is_limit_up(stock_code, df.iloc[0]['close'], df.iloc[0]['preClose'], tolerance):
        return True
    return False

def is_flipping_after_hitting_the_limit(stock_code, kline, tolerance=0.002):
    """
    判断股票是否在涨停后炸板（即最高价为涨停价，但收盘价低于最高价）
    
    参数:
        stock_code (str): 股票代码
        kline (DataFrame): 股票日K线数据
        tolerance (float): 允许误差
    """
    limit_rate = get_stock_limit_rate(stock_code)
    limit_price = kline['preClose'] * (1 + limit_rate - tolerance)
    if kline['high'] >= limit_price and kline['close'] < kline['high']:
        return True
    return False

def is_continuous_volume_reduction(klines, tolerance=0):
    """
    判断股票是否连续缩量，缩量定义为成交量小于前一天的成交量
    注意：klines中日期是升序，不限制天数，但至少需要2天
    参数:
        klines (DataFrame): 股票日K线数据
        tolerance (float): 允许误差
    """
    if len(klines) < 2:
        return False

    for i in range(1, len(klines)):
        if klines.iloc[i]['volume'] > klines.iloc[i - 1]['volume'] * (1 + tolerance):
            return False
    return True

def caculate_macd(gmd_data):
    """
    计算macd指标
    
    参数:
        gmd_data (DataFrame): 行情数据，需要包含close列
        
    返回:
        DataFrame: 包含原始数据和MACD指标(DIF、DEA和MACD)的DataFrame
    """
    # 复制原始数据，避免修改原始数据
    df = gmd_data.copy()
    
    # 计算EMA(12)和EMA(26)
    df['EMA12'] = df['close'].ewm(span=12, adjust=False).mean()
    df['EMA26'] = df['close'].ewm(span=26, adjust=False).mean()
    
    # 计算DIF: DIF = EMA(12) - EMA(26)
    df['DIF'] = df['EMA12'] - df['EMA26']
    
    # 计算DEA: DEA = EMA(DIF, 9)
    df['DEA'] = df['DIF'].ewm(span=9, adjust=False).mean()
    
    # 计算MACD柱: MACD = 2 * (DIF - DEA)
    df['MACD'] = 2 * (df['DIF'] - df['DEA'])
    
    # 删除中间计算列
    df.drop(['EMA12', 'EMA26'], axis=1, inplace=True)
    
    return df

def is_macd_top(macd_data):
    """
    判断MACD柱是否见顶
    
    参数:
        macd_data (DataFrame): 包含MACD列的行情数据
        
    返回:
        bool: MACD柱见顶返回True，否则返回False
    """
    # 检查数据量是否足够
    if len(macd_data) < 4:
        return False
    
    # 获取最近四根MACD柱值
    m1, m2, m3, m4 = macd_data['MACD'].iloc[-1:-5:-1]
    
    # 判断是否满足见顶条件：m1 < m2 < m3 > m4
    return m1 < m2 < m3 > m4 and m1 > 0 and m2 > 0 and m3 > 0 and m4 > 0

def is_macd_bottom(macd_data):
    """
    判断MACD柱是否见底
    MACD柱见底定义：T0为当前分钟，T-1分钟MACD绿柱短于T-2分钟MACD绿柱，且T-2分钟MACD绿柱短于T-3分钟MACD绿柱，但T-3分钟MACD绿柱长于T-4分钟MACD绿柱。
    
    参数:
        macd_data (DataFrame): 包含MACD列的行情数据
    """
    if len(macd_data) < 5:
        return False
    
    # 获取最近五根MACD柱值  
    m1, m2, m3, m4, m5 = macd_data['MACD'].iloc[-1:-6:-1]
    
    # 判断是否满足见底条件：m1 < m2 < m3 < m4 < m5
    return m1 > m2 > m3 > m4 < m5 and m1 < 0 and m2 < 0 and m3 < 0 and m4 < 0 and m5 < 0

def get_kline_entity(kline, is_max=True)    :
    """
    获取单根K线实体价格
    
    参数:
        kline (DataFrame): 股票日K线数据
        is_max (bool): 是否获取实体最高价，True为最高价，False为最低价
    
    返回:
        float: 实体价格
    """
    if is_max:
        if kline.iloc[-1]['close'] > kline.iloc[-1]['open']:
            return kline.iloc[-1]['close']
        else:
            return kline.iloc[-1]['open']
    else:
        if kline.iloc[-1]['close'] > kline.iloc[-1]['open']:
            return kline.iloc[-1]['open']
        else:
            return kline.iloc[-1]['close']
        
def caculate_minute_average_price(gmd_data):
    """
    计算分时均价(从开盘至当下)
    分时均价定义：从开盘至当下，所有成交额除以所有成交量
    
    参数:
        gmd_data (DataFrame): 包含最新分时行情数据的DataFrame
    """
    return gmd_data['amount'].sum() / gmd_data['volume'].sum() / 100

def is_board_explosion(stock_code, gmd_data):
    """
    判断股票是否炸板
    
    参数:
        stock_code (str): 股票代码
        gmd_data (DataFrame): 包含最新分时行情数据的DataFrame
    """
    
    
