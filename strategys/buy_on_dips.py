from broker.broker import Broker
import time
from utils.util import is_trading_time, timestamp_to_date_number, current_date_number, yesterday_date_number, nearest_close_date_number, is_market_closed
from utils.logger import logger
from utils.anis import GREEN, RESET, RED
from laboratory.pool import get_stock_pool_in_main_board
from laboratory.graph import filter_stock_pool_buy_on_dips
from laboratory.graph import get_last_limit_up_kline
from laboratory.utils import *
from broker.data import get_daily_data
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
        self.buy_signal_allowed = config.get('SIGNAL', 'BUY_SIGNAL')
        self.sell_signal_allowed = config.get('SIGNAL', 'SELL_SIGNAL')
        

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
        logger.info(f"{GREEN}【交易】{RESET}开始执行交易，等待信号生成...")
        while True:
            if is_market_closed():
                logger.info(f"{GREEN}【收盘】{RESET}当前已收盘，策略结束")
                break

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
        if not self.sell_signal_allowed:
            logger.info(f"{GREEN}【持仓股票池】{RESET}卖出信号已关闭，跳过获取持仓股票池")
            return
        pos = self.broker.get_available_positions()
        if pos.empty:
            return

        self.sell_stock_pool = pos['股票代码'].tolist()
        logger.info(f"{GREEN}【持仓股票池】{RESET}获取成功!")
        
    # 初始化：买入股票池（预买入股票池）
    def set_buy_stock_pool(self):
        logger.info(f"{GREEN}【自选股票池】{RESET}开始创建...")
        if not self.buy_signal_allowed:
            logger.info(f"{GREEN}【自选股票池】{RESET}买入信号已关闭，跳过获取自选股票池")
            return
        stock_list = get_stock_pool_in_main_board()
        self.buy_stock_pool = filter_stock_pool_buy_on_dips(stock_list, n_days=self.n_days, m_days=self.m_days, limitup_days=self.limitup_days)
        self.buy_stock_pool = [stock for stock in self.buy_stock_pool if stock not in self.sell_stock_pool]
        logger.info(f"{GREEN}【自选股票池】{RESET}创建成功!")

    # 初始化：缓存数据
    def set_cache_data(self):
        logger.info(f"{GREEN}【缓存数据】{RESET}开始缓存股池静态数据...")
        # 缓存买入股票池所需的判断条件
        for stock in self.buy_stock_pool:
            self.cache_data[stock] = {}
            # 缓存昨日K线实体最高价
            kline = get_daily_data(stock_list=[stock], period='1d', end_time=nearest_close_date_number(), count=1).get(stock)
            self.cache_data[stock]['yesterday_entity_max'] = get_kline_entity(kline)
            # 缓存今日涨停价
            self.cache_data[stock]['limit_up_price'] = caculate_kline_limit_up_price(stock, kline.iloc[0])
            # 缓存昨日收盘价
            self.cache_data[stock]['yesterday_close'] = kline.iloc[0]['close']

        # 缓存卖出股票池所需的判断条件
        sell_stock_pool = self.sell_stock_pool.copy()
        for stock in sell_stock_pool:
            self.cache_data[stock] = {}
            # 初始化macd_top_price
            self.cache_data[stock]['macd_top_price'] = 0
            # 初始化macd_signal_updated
            self.cache_data[stock]['macd_signal_updated'] = 0
            # 初始化sell_percent_record
            self.cache_data[stock]['sell_percent_record'] = 0
            # 获取最近涨停日
            limit_up_date = get_last_limit_up_kline(stock, nearly_days=30)['time']
            limit_up_date = timestamp_to_date_number(limit_up_date)
            klines = get_daily_data(stock_list=[stock], period='1d', start_time=limit_up_date, end_time=nearest_close_date_number(), count=-1).get(stock)
            yesterday_kline = klines.iloc[-1]
            # 缓存昨日是否炸板
            self.cache_data[stock]['yesterday_flipping'] = is_flipping_after_hitting_the_limit(stock, yesterday_kline)
            # 缓存昨日是否跌停
            self.cache_data[stock]['yesterday_limit_down'] = is_limit_down_kline(stock, yesterday_kline)
            # 缓存昨日是否涨停
            self.cache_data[stock]['yesterday_limit_up'] = is_limit_up_kline(stock, yesterday_kline)
            # 缓存昨日成交量
            self.cache_data[stock]['yesterday_volume'] = yesterday_kline['volume']
            # 缓存昨日是否缩量（允许10%误差）
            self.cache_data[stock]['yesterday_volume_reduction'] = is_continuous_volume_reduction(klines.tail(2), tolerance=0.1) 
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
            
        logger.info(f"{GREEN}【缓存数据】{RESET}缓存股池静态数据成功!")

    # 订阅行情
    def subscribe(self):
        # 订阅自选股票池
        logger.info(f"{GREEN}【订阅行情】{RESET}开始订阅自选股票池...")
        do_subscribe_quote(self.buy_stock_pool, '1m')
        # 订阅持仓股票池
        logger.info(f"{GREEN}【订阅行情】{RESET}开始订阅持仓股票池...")
        do_subscribe_quote(self.sell_stock_pool, '1m')

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
        # 0.判断是否已生成过建仓信号
        if self.cache_data[stock].get('buy_signal_generated', False):
            return {}
        
        # 1.判断今日分时(从开盘至当下)最高价是否已突破过昨日实体最高价
        if daily_data['high'].max() <= self.cache_data[stock]['yesterday_entity_max']:
            return {}
        
        # 2.判断今日分时（从开盘至当下）是否有过涨停或炸板
        if daily_data['high'].max() >= self.cache_data[stock]['limit_up_price']:
            return {}
        
        # 3.判断当前MACD是否拐点
        if not is_macd_bottom(caculate_macd(daily_data)):
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

        # 记录建仓信号到缓存数据
        self.cache_data[stock]['buy_signal_generated'] = True

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
        """
        卖出条件
        情况1：分时监听到炸板，全仓卖出
        情况2：尾盘14:50时，如果今日放量（允许10%误差）且收阴线，则全仓卖出
        情况3：当前价格低于T日开盘价，MACD顶分批卖出
        情况4：昨日（不含建仓日）放量，MACD顶分批卖出
        情况5：昨日放量超过T+1日成交量，MACD顶分批卖出
        情况6：昨日涨停、炸板，MACD顶分批卖出
        若当前涨停，则不卖出
        """        
        result = {}

        if daily_data.empty:
            logger.warning(f"{RED}【卖出信号生成】{RESET} 股票{stock} {get_stock_name(stock)} 行情数据获取失败，跳过卖出信号生成")
            return {}
        
        for signal_func in [
            lambda: self.sub_sell_signal_explode(stock, daily_data),
            lambda: self.sub_sell_signal_final_time(stock, daily_data),
            lambda: self.sub_sell_signal_stop_loss(stock, daily_data),
            lambda: self.sub_sell_signal_volume_surge(stock, daily_data),
            lambda: self.sub_sell_signal_volume_surge_T(stock, daily_data),
            lambda: self.sub_sell_signal_limit_up_and_explode(stock, daily_data)
        ]:
            signal = signal_func()
            if signal:
                result = signal
                break

        self.update_macd_top_price(stock, daily_data)

        # 当产生了有效信号时，继续判断是否有可用持仓，如果无持仓则屏蔽该信号
        if result:
            available_volume = self.broker.get_stock_available_volume(stock)
            if available_volume == 0:
                return {}
            logger.info(result.get('log_info', ''))

        return result

    def sub_sell_signal_explode(self, stock, daily_data):
        """
        分时监听到炸板，全仓卖出信号
        """
        # 最高价突破过涨停价，且当前价格低于涨停价
        if daily_data['high'].max() < self.cache_data[stock]['limit_up_price']:
            return {}
        
        # 当前价格低于涨停价
        if daily_data['close'].iloc[-1] >= self.cache_data[stock]['limit_up_price']:
            return {}
        
        return {
            "stock_code": stock,
            "signal_type": "SELL_ALL",
            "price": daily_data['close'].iloc[-1] * 0.98,
            "signal_desc": self.strategy_name + "-炸板清仓",
            "log_info": f"{GREEN}【全部清仓-信号生成】{RESET} 股票{stock} {get_stock_name(stock)} 触发炸板清仓条件"
        }

    def sub_sell_signal_final_time(self, stock, daily_data):
        """
        尾盘14:50时，如果今日成交量超过昨日成交量的1.1倍且收阴线，则全仓卖出信号
        """
        # 当前时间在14:50时
        if time.localtime().tm_hour != 14 or time.localtime().tm_min != 50:
            return {}
        
        # 今日当前累计成交量超过昨日成交量的1.1倍
        if daily_data['volume'].sum() < self.cache_data[stock]['yesterday_volume'] * 1.1:
            return {}
        
        # 今日收阴线（即当前分时价格低于第一个分时K线开盘价）
        if daily_data['close'].iloc[-1] >= daily_data['open'].iloc[0]:
            return {}
        
        return {
            "stock_code": stock,
            "signal_type": "SELL_ALL",
            "price": daily_data['close'].iloc[-1],
            "signal_desc": self.strategy_name + "-尾盘清仓",
            "log_info": f"{GREEN}【全部清仓-信号生成】{RESET} 股票{stock} {get_stock_name(stock)} 触发尾盘清仓条件"
        }

    def sub_sell_signal_stop_loss(self, stock, daily_data):
        """
        当前价格低于T日开盘价，MACD顶分批卖出信号
        运行频率：每分钟运行一次（通过缓存记录该分钟是否已运行过该函数）
        """
        # 每分钟只需要运行一次，通过缓存记录该分钟是否已运行过该函数
        update_minute = time.localtime().tm_min
        if self.cache_data[stock].get('macd_signal_updated', 0) == update_minute:
            return {}

        # 当前价格低于T日开盘价
        if daily_data['close'].iloc[-1] >= self.cache_data[stock]['limit_up_open']:
            return {}
        
        # 当前MACD柱见顶
        if not is_macd_top(caculate_macd(daily_data)):
            return {}
        
        # 当前价格低于MACD上一次顶价格
        if daily_data['close'].iloc[-1] >= self.cache_data[stock]['macd_top_price']:
            return {}
        
        # 当前价格非涨停
        if daily_data['close'].iloc[-1] >= self.cache_data[stock]['limit_up_price']:
            return {}
        
        # 首次分批卖出50%，之后全仓卖出
        if self.cache_data[stock].get('sell_percent_record', 0) == 0:
            sell_percent = 0.5
            self.cache_data[stock]['sell_percent_record'] = 1
        else:
            sell_percent = 1.0
        
        self.cache_data[stock]['macd_signal_updated'] = update_minute

        return {
            "stock_code": stock,
            "signal_type": "SELL_PERCENT",
            "percent": sell_percent,
            "price": daily_data['close'].iloc[-1],
            "signal_desc": self.strategy_name + "-MACD顶分批止损",
            "log_info": f"{GREEN}【分批清仓-信号生成】{RESET} 股票{stock} {get_stock_name(stock)} 触发MACD顶分批止损条件"
        }

    def sub_sell_signal_volume_surge(self, stock, daily_data):
        """
        昨日放量，则今日MACD顶分批卖出信号
        但昨日是建仓日时，则信号无效
        """
        # 每分钟只需要运行一次，通过缓存记录该分钟是否已运行过该函数，且距离上次运行间隔至少5分钟
        update_minute = time.localtime().tm_min
        last_updated = self.cache_data[stock].get('macd_signal_updated', 0)

        # 检查当前分钟是否已运行过，或者距离上次运行不足5分钟
        if update_minute == last_updated or (update_minute - last_updated) % 60 < 5:
            return {}

        # 昨日缩量，则信号无效
        if self.cache_data[stock]['yesterday_volume_reduction']:
            return {}

        # 昨日是建仓日时，则信号无效
        if self.cache_data[stock]['build_date'] == yesterday_date_number():
            return {}
        
        # 当前价格涨停，则信号无效
        if daily_data['close'].iloc[-1] >= self.cache_data[stock]['limit_up_price']:
            return {}
        
        # 当前非MACD柱见顶，则信号无效
        if not is_macd_top(caculate_macd(daily_data)):
            return {}
        
        # 当前价格高于MACD上一次顶价格，则信号无效
        if daily_data['close'].iloc[-1] >= self.cache_data[stock]['macd_top_price']:
            return {}
        
        # 首次分批卖出50%，之后全仓卖出
        if self.cache_data[stock].get('sell_percent_record', 0) == 0:
            sell_percent = 0.5
            self.cache_data[stock]['sell_percent_record'] = 1
        else:
            sell_percent = 1.0
        
        self.cache_data[stock]['macd_signal_updated'] = update_minute

        return {
            "stock_code": stock,
            "signal_type": "SELL_PERCENT",
            "percent": sell_percent,
            "price": daily_data['close'].iloc[-1],
            "signal_desc": self.strategy_name + "-昨日放量分批卖出",
            "log_info": f"{GREEN}【分批清仓-信号生成】{RESET} 股票{stock} {get_stock_name(stock)} 触发昨日放量分批卖出条件"
        }        

    def sub_sell_signal_volume_surge_T(self, stock, daily_data):
        """
        昨日成交量>=T+1日成交量的0.95倍，MACD顶分批卖出信号
        """
        # 每分钟只需要运行一次，通过缓存记录该分钟是否已运行过该函数，且距离上次运行间隔至少5分钟
        update_minute = time.localtime().tm_min
        last_updated = self.cache_data[stock].get('macd_signal_updated', 0)

        # 检查当前分钟是否已运行过，或者距离上次运行不足5分钟
        if update_minute == last_updated or (update_minute - last_updated) % 60 < 5:
            return {}
        
        # 昨日成交量<T+1日成交量的0.95倍，则信号无效
        if self.cache_data[stock]['yesterday_volume'] < self.cache_data[stock]['limit_up_next_day_volume'] * 0.95:
            return {}
        
        # 当前非MACD柱见顶，则信号无效
        if not is_macd_top(caculate_macd(daily_data)):
            return {}
        
        # 当前价格高于MACD上一次顶价格，则信号无效
        if daily_data['close'].iloc[-1] >= self.cache_data[stock]['macd_top_price']:
            return {}
        
        # 当前价格涨停，则信号无效
        if daily_data['close'].iloc[-1] >= self.cache_data[stock]['limit_up_price']:
            return {}
        
        # 首次分批卖出50%，之后全仓卖出
        if self.cache_data[stock].get('sell_percent_record', 0) == 0:
            sell_percent = 0.5
            self.cache_data[stock]['sell_percent_record'] = 1
        else:
            sell_percent = 1.0
        
        self.cache_data[stock]['macd_signal_updated'] = update_minute
        
        return {
            "stock_code": stock,
            "signal_type": "SELL_PERCENT",
            "percent": sell_percent,
            "price": daily_data['close'].iloc[-1],
            "signal_desc": self.strategy_name + "-昨日放量超过涨停次日成交量分批卖出",
            "log_info": f"{GREEN}【分批清仓-信号生成】{RESET} 股票{stock} {get_stock_name(stock)} 触发昨日放量超过涨停次日成交量分批卖出条件"
        }

    def sub_sell_signal_limit_up_and_explode(self, stock, daily_data):
        """
        昨日涨停、炸板、跌停，MACD顶分批卖出信号
        """
        # 每分钟只需要运行一次，通过缓存记录该分钟是否已运行过该函数，且距离上次运行间隔至少5分钟
        update_minute = time.localtime().tm_min
        last_updated = self.cache_data[stock].get('macd_signal_updated', 0)

        # 检查当前分钟是否已运行过，或者距离上次运行不足5分钟
        if update_minute == last_updated or (update_minute - last_updated) % 60 < 5:
            return {}
        
        # 昨日没有涨停、炸板、跌停中的任一情况时，信号无效
        if not (self.cache_data[stock]['yesterday_limit_up'] or 
                self.cache_data[stock]['yesterday_flipping'] or 
                self.cache_data[stock]['yesterday_limit_down']):
            return {}
        
        # 当前非MACD柱见顶，则信号无效
        if not is_macd_top(caculate_macd(daily_data)):
            return {}
        
        # 当前价格高于MACD上一次顶价格，则信号无效
        if daily_data['close'].iloc[-1] >= self.cache_data[stock]['macd_top_price']:
            return {}
        
        # 当前价格涨停，则信号无效
        if daily_data['close'].iloc[-1] >= self.cache_data[stock]['limit_up_price']:
            return {}
        
        # 首次分批卖出50%，之后全仓卖出
        if self.cache_data[stock].get('sell_percent_record', 0) == 0:
            sell_percent = 0.5
            self.cache_data[stock]['sell_percent_record'] = 1
        else:
            sell_percent = 1.0
        
        self.cache_data[stock]['macd_signal_updated'] = update_minute

        return {
            "stock_code": stock,
            "signal_type": "SELL_PERCENT",
            "percent": sell_percent,
            "price": daily_data['close'].iloc[-1],
            "signal_desc": self.strategy_name + "-昨日涨停、炸板、跌停分批卖出",
            "log_info": f"{GREEN}【分批清仓-信号生成】{RESET} 股票{stock} {get_stock_name(stock)} 触发昨日涨停、炸板、跌停分批卖出条件"
        }

    def update_macd_top_price(self, stock, daily_data):
        """
        缓存当前最高的MACD顶价格
        """
        # 每分钟只需要更新一次，通过缓存记录该分钟是否已更新过
        update_minute = time.localtime().tm_min
        if self.cache_data[stock].get('macd_top_price_updated', 0) == update_minute:
            return

        macd_data = caculate_macd(daily_data)
        if is_macd_top(macd_data):
            if self.cache_data[stock].get('macd_top_price', 0) == 0:
                self.cache_data[stock]['macd_top_price'] = daily_data['close'].iloc[-1]
            elif self.cache_data[stock]['macd_top_price'] < daily_data['close'].iloc[-1]:
                self.cache_data[stock]['macd_top_price'] = daily_data['close'].iloc[-1]

        self.cache_data[stock]['macd_top_price_updated'] = update_minute
   
    
