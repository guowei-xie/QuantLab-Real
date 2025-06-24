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
    


