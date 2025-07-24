from broker.broker import Broker
import time
from utils.util import is_trading_time, timestamp_to_date_number, current_date_number
from utils.logger import logger
from utils.anis import GREEN, RESET, RED
from laboratory.pool import get_stock_pool_in_main_board
from laboratory.graph import filter_stock_pool_buy_on_dips
from laboratory.graph import get_last_limit_up_kline
from laboratory.utils import *
from broker.data import get_daily_data, nearest_close_date_number
from utils.database import Database


class BuyOnDips:
    """
    低吸策略类
    
    实现自动选股、订阅行情、信号生成和交易执行的完整交易策略
    """

    def __init__(self, account_id, mini_qmt_path, config, n_days=5, m_days=10, limitup_days=2, fixed_value=5000):
        self.strategy_name = 'BuyOnDips'
        self.broker = Broker(account_id, mini_qmt_path, config)
        self.broker.connect()
        self.broker.get_asset(display=True)
        self.db = Database()
        self.n_days = n_days # 近n天内有涨停
        self.m_days = m_days # 近m天内无一字板涨停
        self.limitup_days = limitup_days # 涨停次数上限
        self.fixed_value = fixed_value # 固定单次买入市值
        self.sell_stock_pool = [] # 预卖出股票池
        self.buy_stock_pool = [] # 预买入股票池
        self.cache_data = {} # 缓存数据
        

    # 策略运行函数
    def run(self):
        self.prepare()
        self.trading()
        self.post_processing()
        
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
        while True:
            if not is_trading_time():
                time.sleep(1)
                continue

            # 获取分时行情数据
            daily_data = get_daily_data(self.buy_stock_pool + self.sell_stock_pool, start_time=current_date_number(), period='1m', count=-1)

            # 卖出信号生成与执行
            for stock in self.sell_stock_pool:
                signal = self.sell_signal(stock, daily_data[stock])
                if signal:
                    logger.info(signal['log_info'])
                    self.broker.order_by_signal(signal, strategy_name=self.strategy_name, remark=signal['signal_desc'])

            # 买入信号生成与执行
            for stock in self.buy_stock_pool:
                signal = self.buy_signal(stock, daily_data[stock])
                if signal:
                    logger.info(signal['log_info'])
                    self.broker.order_by_signal(signal, strategy_name=self.strategy_name, remark=signal['signal_desc'])
            
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
            # 缓存今日涨停价(有误差，允许误差为0.002)
            self.cache_data[stock]['limit_up_price'] = caculate_kline_limit_up_price(stock, yesterday_kline)
            # 缓存建仓日期
            self.cache_data[stock]['build_date'] = self.db.get_last_buy_record(stock).get('traded_date', '')
            # 缓存建仓日成交量（即klines中time等于建仓日的那根K线）
            if self.cache_data[stock]['build_date']:
                build_date_kline = klines[klines['time'] == self.cache_data[stock]['build_date']]
                self.cache_data[stock]['build_date_volume'] = build_date_kline['volume']
            else:
                # 从sell_stock_pool中去掉该股票
                self.sell_stock_pool.remove(stock)
                logger.warning(f"{RED}【建仓日期获取失败】{RESET}股票{stock}建仓日期获取失败，从预卖出股票池中移除")

    # 订阅行情
    def subscribe(self):
        stock_list = self.buy_stock_pool + self.sell_stock_pool
        do_subscribe_quote(stock_list, '1m')

    # 买入信号生成
    def buy_signal(self, stock, daily_data):
        """
        建仓条件：
        1.已突破过昨日实体最高价
        2.当日没有涨停或炸板
        3.当前MACD拐点
        4.当前价格高于分时均价
        5.当前价格高于上一日收盘价
        
        """
        # 1.判断今日分时(从开盘至当下)最高价是否已突破过昨日实体最高价
        if daily_data['high'].max() <= self.cache_data[stock]['yesterday_entity_max']:
            return {}
        
        # 2.判断今日分时（从开盘至当下）是否有过涨停或炸板
        if daily_data['high'].max() >= self.cache_data[stock]['limit_up_price']:
            return {}
        
        # 3.判断当前MACD是否拐点
        if not is_macd_bottom(daily_data):
            return {}
        
        # 4.判断当前价格是否高于分时均价
        if daily_data['close'].iloc[-1] < caculate_minute_average_price(daily_data):
            return {}
        
        # 5.判断当前价格是否高于上一日收盘价
        if daily_data['close'].iloc[-1] < self.cache_data[stock]['yesterday_close']:
            return {}
        
        # 6.判断当日是否在持仓中
        if self.db.is_in_position(stock):
            return {}
        
        # 7.判断今日是否有清仓记录
        last_sell_date = self.db.get_last_sell_record(stock).get('traded_date', '')
        if last_sell_date == current_date_number():
            return {}
        
        # 生成建仓信号
        log_info = f"{GREEN}【建仓-信号生成】{RESET} 股票{stock} {get_stock_name(stock)} 触发建仓条件"
        return {
            "stock_code": stock,
            "signal_type": "BUY_VALUE",
            "value": self.fixed_value,
            "price": daily_data['close'].iloc[-1],
            "signal_desc": self.strategy_name + "-建仓",
            "log_info": log_info
        }

    # 卖出信号生成
    def sell_signal(self, stock, daily_data):
        pass
