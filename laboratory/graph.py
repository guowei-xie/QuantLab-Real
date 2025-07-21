from laboratory.utils import *
from datetime import datetime
from utils.util import timestamp_to_date_number_plus_n_days

"""
股票K线图形模式识别模块
该模块提供了各种K线图形模式的识别功能，用于选股和交易信号生成
"""

def filter_stock_pool_in_xuliban(stock_list, nearly_days=5, limitup_days=2):
    """
    识别并筛选出符合"蓄力板"形态的股票
    
    蓄力板图形特征：
    1. 近n天内有过涨停，但涨停次数不超过limitup_days次
    2. 最近一次涨停的K线，开盘价不等于收盘价（非一字板）
    3. 最新一个交易日未涨停
    4. 涨停日至今的最低价要高于涨停日的开盘价（回调不破开盘价）
    
    参数:
        stock_list (list): 待筛选的股票代码列表
        nearly_days (int): 向前查找的交易日天数，默认为5天
        limitup_days (int): 允许的最大涨停次数，默认为2次
    
    返回:
        list: 符合蓄力涨停板条件的股票代码列表
    """
    result = []
    logger.info(f"{GREEN}【模式识别-蓄力涨停板】{RESET}正在匹配识别...")
    for stock in tqdm(stock_list, desc="匹配识别中...", ncols=100):
        # 判断近nearly_days天涨停次数，必须大于0且不超过limitup_days
        limitup_days_count = get_neary_limit_up_days(stock, nearly_days)
        if limitup_days_count > 0 and limitup_days_count <= limitup_days:
            # 判断最近一次涨停的K线，开盘价不等于收盘价（排除一字板）
            kline = get_last_limit_up_kline(stock, nearly_days)
            if kline['open'] != kline['close']:
                # 判断最新一天未涨停
                if not is_last_day_limit_up(stock):
                    # 判断涨停日（不含涨停日）至今的最低价要高于涨停日的开盘价（回调不破开盘价）
                    start_time = timestamp_to_date_number_plus_n_days(kline['time'], 1)
                    end_time = datetime.now().strftime('%Y%m%d')
                    low_price = get_klines_low_price(stock, start_time, end_time)
                    if low_price > kline['open']:
                        result.append(stock)
    logger.info(f"{GREEN}【模式识别-蓄力涨停板】{RESET}成功匹配识别{len(result)}只股票")
    return result
    
def filter_stock_pool_buy_on_dips(stock_list, n_days=5, m_days=10, limitup_days=2):
    """
    识别并筛选出符合"低吸"形态的股票
    
    低吸图形特征：
    1. 近n天内有过涨停，但涨停次数不超过limitup_days次（最近一次涨停的交易日为T日）
    2. 近m天无一字板涨停
    3. T日后至少有两个交易日
    4. T+1日放量（不低于T日即涨停日的80%成交量），且收盘价不高于5%涨幅
    5. T+2日至今连续缩量（即低于前一天的成交量）
    6. 回调期间最低价不破T日开盘价
    7. 回调期间无跌停、炸板
    """

    result = []
    logger.info(f"{GREEN}【模式识别-低吸图形】{RESET}正在匹配识别...")
    for stock in tqdm(stock_list, desc="匹配识别中...", ncols=100):
        # 1. 获取近n_days天涨停次数，需要涨停次数不超过limitup_days次，否则跳过该股票
        limitup_days_count = get_neary_limit_up_days(stock, n_days)
        if limitup_days_count == 0 or limitup_days_count > limitup_days:
            continue
        
        # 2. 获取近m_days天一字板涨停次数，需要无一字板涨停，否则跳过该股票
        word_one_limit_up_days_count = get_neary_limit_up_days(stock, m_days, is_word_one=1)
        if word_one_limit_up_days_count > 0:
            continue

        # 3. 获取涨停后的行情数据，至少有3天，否则跳过该股票
        start_date = get_last_limit_up_kline(stock, n_days)['time']
        start_date = timestamp_to_date_number(start_date)
        end_date = nearest_close_date_number()
        klines = get_daily_data(stock_list=[stock], period='1d', start_time=start_date, end_time=end_date, count=-1).get(stock)
        if len(klines) < 3:
            continue

        # 4. 判断T+1日放量，且收盘价不高于5%涨幅，否则跳过
        t0_k = klines.iloc[0]
        t1_k = klines.iloc[1]
        if t1_k['volume'] < t0_k['volume'] * 0.8 or t1_k['close'] > t0_k['close'] * 1.05:
            continue

        # 5. 判断回调期间连续缩量(排除T0、T1日)，否则跳过
        if not is_continuous_volume_reduction(klines.iloc[1:]):
            continue

        # 6. 判断回调期间最低价不破T日开盘价，否则跳过
        low_price = klines.iloc[1:]['low'].min()
        if low_price <= t0_k['open']:
            continue
        
        # 7. 判断回调期间无炸板、无跌停，否则跳过
        is_limit_down_or_flipping = False
        for i in range(1, len(klines)):
            if is_flipping_after_hitting_the_limit(stock, klines.iloc[i]):
                is_limit_down_or_flipping = True
                break
            if is_limit_down(stock, klines.iloc[i]['close'], klines.iloc[i]['preClose']):
                is_limit_down_or_flipping = True
                break
        if is_limit_down_or_flipping:
            continue
        
        result.append(stock)
    logger.info(f"{GREEN}【模式识别-低吸图形】{RESET}成功匹配识别{len(result)}只股票")
    return result






                        
                

      
        





