
import time
from utils.logger import logger
from utils.anis import GREEN, RESET, YELLOW
from utils.util import timestamp_to_date_number
from broker.broker import Broker
from broker.data import do_subscribe_quote, prepare_open_data, get_daily_data
from laboratory.pool import get_stock_pool_in_main_board
from laboratory.graph import filter_stock_pool_in_xuliban
from laboratory.signal import signal_by_board_hitting, signal_by_open_down, signal_by_board_explosion, signal_by_macd_sell


class BoardHitting:
    """
    板块打板策略类
    
    实现自动选股、订阅行情、信号生成和交易执行的完整交易策略
    """
    def __init__(self, account_id, mini_qmt_path, config):
        """
        初始化板块打板策略
        
        Args:
            account_id: 交易账户ID
            mini_qmt_path: QMT路径
        """
        self.strategy_name = 'BoardHitting'
        self.trade_date = timestamp_to_date_number(time.time())
        self.is_prepared = False
        self.fixed_value = 10000  # 固定单次买入市值
        self.macd_sell_times = 0  # macd柱见顶卖出次数
        self.buy_stock_pool = []  # 买入股票池
        self.sell_stock_pool = [] # 卖出股票池(持仓)
        self.open_data = {}       # 开盘数据缓存
        self.broker = Broker(account_id, mini_qmt_path, config)
        self.broker.connect()
        self.broker.get_asset(display=True)

    def set_buy_stock_pool(self):
        """
        创建买入股票池
        
        从主板获取股票列表并筛选符合条件的股票
        """
        logger.info(f"{GREEN}【自选股票池】{RESET}开始创建...")
        stock_list = get_stock_pool_in_main_board()
        self.buy_stock_pool = filter_stock_pool_in_xuliban(stock_list, nearly_days=5, limitup_days=2)
        logger.info(f"{GREEN}【自选股票池】{RESET}创建成功!")

    def set_sell_stock_pool(self):
        """
        获取卖出股票池
        
        从当前持仓中获取需要监控的卖出股票列表
        """
        logger.info(f"{GREEN}【持仓股票池】{RESET}开始获取...")
        pos = self.broker.get_positions(display=False)
        if pos.empty:
            return
        self.sell_stock_pool = pos['股票代码'].tolist()
        logger.info(f"{GREEN}【持仓股票池】{RESET}获取成功!")

    def set_prepare_open_data(self):
        """
        准备开盘数据
        
        在9:25竞价结束后获取所有监控股票的开盘数据
        """
        current_time = time.strftime('%H:%M:%S', time.localtime(time.time()))
        if current_time < '09:30:05':
            return

        logger.info(f"{GREEN}【已开盘】{RESET}正在准备开盘数据...")
        for stock in self.buy_stock_pool + self.sell_stock_pool:
            self.open_data[stock] = prepare_open_data(stock, self.trade_date)

        # 检查是否所有股票的开盘数据都准备好了
        for stock in self.buy_stock_pool + self.sell_stock_pool:
            if self.open_data[stock] is None:
                return
        logger.info(f"{GREEN}【已开盘】{RESET}开盘数据准备完成，正在等待交易信号...")
        self.is_prepared = True

    def run(self):
        """
        运行策略主函数
        
        初始化股票池、订阅行情并执行交易循环
        """
        self.set_buy_stock_pool()
        self.set_sell_stock_pool()
        self.subscribe(period='1d')
        self.subscribe(period='1m')
        time.sleep(1)

        while True:
            if not self.is_prepared:
                self.set_prepare_open_data()
            else:
                self.trading()
            time.sleep(1)

            # 15:00:00 收盘后，退出
            current_time = time.strftime('%H:%M:%S', time.localtime(time.time()))
            if current_time >= '15:00:00':
                logger.info(f"{GREEN}【退出】{RESET} 当前已收盘，退出策略")
                break


    def trading(self):
        """
        交易执行函数
        
        在9:30开盘后，根据信号执行买卖操作
        """
        current_time = time.strftime('%H:%M:%S', time.localtime(time.time()))
        # 9:30 ~ 11:30  13:00 ~ 15:00 交易时间
        if current_time < '09:30:05' or current_time > '14:55:00' or (current_time > '11:30:00' and current_time < '13:00:05'):
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
                if signal['signal_type'] == 'SELL_PERCENT':
                    # 第1次macd信号卖出50%，第二次卖出剩余所有
                    signal['percent'] = 0.5 if self.macd_sell_times == 0 else 1.0
                order_id = self.broker.order_by_signal(signal, strategy_name=self.strategy_name)
                if order_id != -1:
                    self.macd_sell_times += 1
        

    def subscribe(self, period='1m'):
        """
        订阅股票行情
        
        订阅买入池和卖出池中股票的分钟级行情数据
        
        Returns:
            bool: 是否成功订阅行情
        """
        logger.info(f"{GREEN}【订阅行情】{RESET}开始订阅【自选股票池】{period}行情数据...")
        print("-"*100)
        if len(self.buy_stock_pool) > 0:    
            do_subscribe_quote(self.buy_stock_pool, period)
        else:
            logger.info(f"{YELLOW}【订阅行情】{RESET}【自选股票池】为空")
        print("-"*100)
        logger.info(f"{GREEN}【订阅行情】{RESET}开始订阅【持仓股票池】{period}行情数据...")
        if len(self.sell_stock_pool) > 0:
            do_subscribe_quote(self.sell_stock_pool, period)
        else:
            logger.info(f"{YELLOW}【订阅行情】{RESET}【持仓股票池】为空")
        print("-"*100)
        
        # 如果均为空，则退出
        if len(self.buy_stock_pool) == 0 and len(self.sell_stock_pool) == 0:
            logger.info(f"{YELLOW}【订阅行情】{RESET}【自选股票池】和【持仓股票池】均为空，策略退出")
            return False
        return True
    
       
    def buy_signal(self, stock_code, gmd_data, open_data):
        """
        生成买入信号
        
        Args:
            stock_code (str): 股票代码
            gmd_data (DataFrame): 行情数据
            open_data (dict): 开盘数据
            
        Returns:
            dict: 买入信号，无信号时返回空字典
        """
        signal = signal_by_board_hitting(stock_code, gmd_data, open_data, self.fixed_value)
        if signal:
            # 检查是否存在相同策略的买入订单，如果存在，则不再进行买入
            for record in self.broker.order_records:
                record_strategy_name = record.get('strategy_name', '')
                record_stock_code = record.get('stock_code', '')
                record_signal_type = record.get('signal_type')
                if record_stock_code == stock_code and record_strategy_name == signal['strategy_name'] and record_signal_type == 'BUY_VALUE':
                    return {}
            return signal
        return {}
    
    def sell_signal(self, stock_code, gmd_data, open_data):
        """
        生成卖出信号，按优先级依次检查各种卖出条件
        
        Args:
            stock_code (str): 股票代码
            gmd_data (DataFrame): 行情数据
            open_data (dict): 开盘数据
            
        Returns:
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


 
