from laboratory.utils import *
from datetime import datetime
from utils.util import timestamp_to_date_number_plus_n_days

# 获取股票池中，近5天有过涨停的股票，但最新一天未涨停，且涨停日至今的最低价不能低于涨停日的开盘价
def get_stock_pool_in_xuliban(stock_list, nearly_days=5, limitup_days=2):
    """
    蓄力板图形，图形特征：
    1.近n天涨停次数大于0但小于等于limitup_days
    2.最近一次涨停的K线，开盘价不等于收盘价
    3.最新一天未涨停
    4.涨停日至今的最低价要高于涨停日的开盘价
    
    输入：股票池列表
    返回:
        list: 符合条件的股票代码列表
    """
    result = []
    logger.info(f"{GREEN}【筛选K线图形】{RESET}正在筛选蓄力板图形...")
    for stock in tqdm(stock_list, desc="筛选K线图形", ncols=100):
        # 判断近nearly_days天涨停次数
        limitup_days_count = get_neary_limit_up_days(stock, nearly_days)
        if limitup_days_count > 0 and limitup_days_count <= limitup_days:
            # 判断最近一次涨停的K线，开盘价不等于收盘价
            kline = get_last_limit_up_kline(stock, nearly_days)
            if kline['open'] != kline['close']:
                # 判断最新一天未涨停
                if not is_last_day_limit_up(stock):
                    # 判断涨停日（不含涨停日）至今的最低价要高于涨停日的开盘价
                    start_time = timestamp_to_date_number_plus_n_days(kline['time'], 1)
                    end_time = datetime.now().strftime('%Y%m%d')
                    low_price = get_klines_low_price(stock, start_time, end_time)
                    if low_price > kline['open']:
                        result.append(stock)
    logger.info(f"{GREEN}【筛选K线图形】{RESET}成功获取{len(result)}只股票")
    return result
    


