from utils.logger import logger
from utils.anis import GREEN, RESET, YELLOW
from laboratory.pool import get_stock_pool_in_main_board
from laboratory.graph import filter_stock_pool_in_xuliban
from utils.util import timestamp_to_date_number
from broker.broker import Broker
from broker.data import do_subscribe_quote, prepare_open_data, get_daily_data
import time
from laboratory.signal import signal_by_board_hitting, signal_by_open_down, signal_by_board_explosion, signal_by_macd_sell

class BoardHitting:
    def __init__(self, account_id, mini_qmt_path):
        self.strategy_name = 'BoardHitting'
        self.trade_date = timestamp_to_date_number(time.time())
        self.is_prepared = False
        self.fixed_value = 10000 # 固定单次买入市值
        self.buy_stock_pool = []
        self.sell_stock_pool = []
        self.open_data = {}
        self.broker = Broker(account_id, mini_qmt_path)
        self.broker.connect()
        self.broker.get_asset(display=True)
        self.set_buy_stock_pool()
        self.set_sell_stock_pool()

    def set_buy_stock_pool(self):
        logger.info(f"{GREEN}【自选股票池】{RESET}开始创建...")
        stock_list = get_stock_pool_in_main_board()
        self.buy_stock_pool = filter_stock_pool_in_xuliban(stock_list, nearly_days=5, limitup_days=2)
        logger.info(f"{GREEN}【自选股票池】{RESET}创建成功!")

    def set_sell_stock_pool(self):
        logger.info(f"{GREEN}【持仓股票池】{RESET}开始获取...")
        pos = self.broker.get_positions(display=True)
        if pos.empty:
            return
        self.sell_stock_pool = pos['股票代码'].tolist()
        logger.info(f"{GREEN}【持仓股票池】{RESET}获取成功!")

    def set_prepare_open_data(self):
        # 当前时间处于9点25分之后，则可以准备开盘数据，否则跳出函数
        current_time = time.strftime('%H:%M:%S', time.localtime(time.time()))
        if current_time < '09:25:00':
            return

        logger.info(f"{GREEN}【盘前准备】{RESET}竞价结束，开始准备开盘数据...")
        for stock in self.buy_stock_pool + self.sell_stock_pool:
            self.open_data[stock] = prepare_open_data(stock, self.trade_date)

        # 检查是否所有股票的开盘数据都准备好了
        for stock in self.buy_stock_pool + self.sell_stock_pool:
            if self.open_data[stock] is None:
                return
        logger.info(f"{GREEN}【盘前准备】{RESET}开盘数据准备成功!")
        self.is_prepared = True

    def run(self):
        if self.subscribe():
            while True:
                if not self.is_prepared:
                    self.set_prepare_open_data()
                else:
                    self.trading()

                time.sleep(1)


    def trading(self):
        # 当前时间处于9点30分之后，开始实盘交易，否则跳出函数
        current_time = time.strftime('%H:%M:%S', time.localtime(time.time()))
        if current_time < '09:30:00':
            return
        
        pool_data = get_daily_data(self.buy_stock_pool, start_time=self.trade_date, period='1m', count=-1)

        # 交易信号与执行（先卖后买）
        for stock in self.sell_stock_pool:
            signal = self.sell_signal(stock, pool_data[stock], self.open_data[stock])
            if signal:
                self.broker.order_by_signal(signal, strategy_name=self.strategy_name)

        for stock in self.buy_stock_pool:
            signal = self.buy_signal(stock, pool_data[stock], self.open_data[stock])
            if signal:
                self.broker.order_by_signal(signal, strategy_name=self.strategy_name)





    def subscribe(self):
        logger.info(f"{GREEN}【订阅行情】{RESET}开始订阅【自选股票池】行情数据...")
        print("-"*100)
        if len(self.buy_stock_pool) > 0:    
            do_subscribe_quote(self.buy_stock_pool, '1m', callback=self.print_data)
        else:
            logger.info(f"{YELLOW}【订阅行情】{RESET}【自选股票池】为空")
        print("-"*100)
        logger.info(f"{GREEN}【订阅行情】{RESET}开始订阅【持仓股票池】行情数据...")
        if len(self.sell_stock_pool) > 0:
            do_subscribe_quote(self.sell_stock_pool, '1m', callback=self.print_data)
        else:
            logger.info(f"{YELLOW}【订阅行情】{RESET}【持仓股票池】为空")
        print("-"*100)
        # 如果均为空，则退出
        if len(self.buy_stock_pool) == 0 and len(self.sell_stock_pool) == 0:
            logger.info(f"{YELLOW}【订阅行情】{RESET}【自选股票池】和【持仓股票池】均为空，策略退出")
            return False
        return True
       
        
    def buy_signal(self, stock_code, gmd_data, open_data):
        signal = signal_by_board_hitting(stock_code, gmd_data, open_data, self.fixed_value)
        if signal:
            # 检查是否存在相同策略的买入订单，如果存在，则不再进行买入
            for record in self.broker.order_records:
                if record['stock_code'] == stock_code and record['stategy_name'] == signal['stategy_name'] and record['signal_type'] == 'BUY_VALUE':
                    return {}
            return signal
        return {}
    
    def sell_signal(self, stock_code, gmd_data, open_data):
        """
        生成卖出信号，按优先级依次检查各种卖出条件
        
        参数:
            stock_code (str): 股票代码
            gmd_data (DataFrame): 行情数据
            open_data (dict): 开盘数据
            
        返回:
            dict: 卖出信号，无信号时返回空字典
        """
        # 按优先级检查各种卖出信号
        for signal_func in [
            lambda: signal_by_board_explosion(stock_code, gmd_data, open_data),
            lambda: signal_by_open_down(stock_code, gmd_data, open_data, start_minutes=1, end_minutes=2),
            lambda: signal_by_macd_sell(stock_code, gmd_data, open_data)
        ]:
            signal = signal_func()
            if signal and self.broker.get_stock_position(stock_code) is not None:
                return signal
                
        return {}


    def print_data(self, data):
        print(data)
