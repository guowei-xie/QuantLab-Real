from broker.broker import Broker
import time
from utils.util import is_trading_time, timestamp_to_date_number
from utils.logger import logger
from utils.anis import GREEN, RESET
from laboratory.pool import get_stock_pool_in_main_board
from laboratory.graph import filter_stock_pool_buy_on_dips
from laboratory.graph import get_last_limit_up_kline
from laboratory.utils import get_kline_entity, is_flipping_after_hitting_the_limit, is_limit_down_kline, is_limit_up_kline, is_continuous_volume_reduction
from broker.data import get_daily_data, nearest_close_date_number


class BuyOnDips:
    """
    低吸策略类
    
    实现自动选股、订阅行情、信号生成和交易执行的完整交易策略
    """

    def __init__(self, account_id, mini_qmt_path, config, n_days=5, m_days=10, limitup_days=2):
        self.strategy_name = 'BuyOnDips'
        self.broker = Broker(account_id, mini_qmt_path, config)
        self.broker.connect()
        self.broker.get_asset(display=True)
        self.n_days = n_days # 近n天内有涨停
        self.m_days = m_days # 近m天内无一字板涨停
        self.limitup_days = limitup_days # 涨停次数上限
        self.sell_stock_pool = [] # 预卖出股票池
        self.buy_stock_pool = [] # 预买入股票池
        self.cache_data = {} # 缓存数据

    # 策略运行函数
    def run(self):
        pass
        
    # 盘前准备
    def prepare(self):
        # 获取持仓股票池
        self.set_sell_stock_pool()
        # 获取买入股票池
        self.set_buy_stock_pool()
        # 获取缓存数据
        self.set_cache_data()
        # 订阅行情
        self.subscribe()

    # 盘中交易
    def trading(self):
        if not is_trading_time():
            return
        


    # 盘后处理
    def post_processing(self):
        pass

    # 初始化：持仓股票池(预卖出股票池)
    def set_sell_stock_pool(self):
        logger.info(f"{GREEN}【持仓股票池】{RESET}开始获取...")
        pos = self.broker.get_available_positions()
        if pos.empty:
            return

        self.sell_stock_pool = pos['股票代码'].tolist()
        logger.info(f"{GREEN}【持仓股票池】{RESET}获取成功!")
        

    # 初始化：买入股票池（预买入股票池）
    def set_buy_stock_pool(self):
        logger.info(f"{GREEN}【自选股票池】{RESET}开始创建...")
        stock_list = get_stock_pool_in_main_board()
        self.buy_stock_pool = filter_stock_pool_buy_on_dips(stock_list, n_days=self.n_days, m_days=self.m_days, limitup_days=self.limitup_days)
        self.buy_stock_pool = [stock for stock in self.buy_stock_pool if stock not in self.sell_stock_pool]
        logger.info(f"{GREEN}【自选股票池】{RESET}创建成功!")

    # 初始化：缓存数据
    def set_cache_data(self):
        # 缓存买入股票池所需的判断条件
        for stock in self.buy_stock_pool:
            # 缓存昨日K线实体最高价
            kline = get_daily_data(stock_list=[stock], period='1d', end_time=nearest_close_date_number(), count=1).get(stock)
            self.cache_data[stock]['yesterday_entity_max'] = get_kline_entity(kline)

        # 缓存卖出股票池所需的判断条件
        for stock in self.sell_stock_pool:
            # 获取最近涨停日
            limit_up_date = get_last_limit_up_kline(stock, n_days=self.n_days)['time']
            limit_up_date = timestamp_to_date_number(limit_up_date)
            klines = get_daily_data(stock_list=[stock], period='1d', start_time=limit_up_date, end_time=nearest_close_date_number(), count=-1).get(stock)
            yesterday_kline = klines.iloc[-1]
            # 缓存昨日是否炸板
            self.cache_data[stock]['yesterday_flipping'] = is_flipping_after_hitting_the_limit(stock, yesterday_kline)
            # 缓存昨日是否跌停
            self.cache_data[stock]['yesterday_limit_down'] = is_limit_down_kline(yesterday_kline)
            # 缓存昨日是否涨停
            self.cache_data[stock]['yesterday_limit_up'] = is_limit_up_kline(yesterday_kline)
            # 缓存昨日是否缩量（允许10%误差）
            self.cache_data[stock]['yesterday_volume_reduction'] = is_continuous_volume_reduction(klines.iloc[:-2], tolerance=0.1) 
            # 缓存最近涨停日的开盘价
            self.cache_data[stock]['limit_up_open'] = klines.iloc[0]['open']
            # 缓存最近涨停日的次日成交量
            self.cache_data[stock]['limit_up_next_day_volume'] = klines.iloc[1]['volume']
            # 缓存建仓日期
            self.cache_data[stock]['build_date'] = get_build_date(stock)
            # 缓存建仓日成交量（即klines中time等于建仓日的那根K线）
            build_date_kline = klines[klines['time'] == self.cache_data[stock]['build_date']]
            self.cache_data[stock]['build_date_volume'] = build_date_kline['volume']

    # 订阅行情
    def subscribe(self):
        pass


