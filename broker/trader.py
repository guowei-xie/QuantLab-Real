from xtquant.xttrader import XtQuantTrader, XtQuantTraderCallback
from xtquant.xttype import StockAccount
import random
import pandas as pd
from utils.util import timestamp_to_datetime_string, parse_order_type, convert_to_current_date
from utils.anis import RED, GREEN, YELLOW, BLUE, RESET
from utils.logger import logger

class MyXtTraderCallback(XtQuantTraderCallback):
    """
    交易回调类，处理交易事件
    """
    def __init__(self):
        """
        初始化交易回调类
        """
        super().__init__()
        self.error_orders = set()  # 使用集合存储错误订单ID，避免重复

    def on_disconnected(self):
        """
        连接断开回调
        """
        logger.warning(f"{YELLOW}【连接断开】{RESET} 交易连接已断开")
        
    def on_stock_order(self, order):
        """
        委托信息推送回调
        
        参数:
            order: XtOrder对象
        """
        # 委托状态码：50-已委托，53/54-已撤单
        if order.order_status == 50:
            logger.info(f"{BLUE}【已委托】{RESET} {parse_order_type(order.order_type)} 代码:{order.stock_code} 名称:{order.order_remark} 委托价格:{order.price:.2f} 委托数量:{order.order_volume} 订单编号:{order.order_id} 委托时间:{timestamp_to_datetime_string(convert_to_current_date(order.order_time))}")
        elif order.order_status in (53, 54):
            logger.warning(f"{YELLOW}【已撤单】{RESET} {parse_order_type(order.order_type)} 代码:{order.stock_code} 名称:{order.order_remark} 委托价格:{order.price:.2f} 委托数量:{order.order_volume} 订单编号:{order.order_id} 委托时间:{timestamp_to_datetime_string(convert_to_current_date(order.order_time))}")

    def on_stock_trade(self, trade):
        """
        成交信息推送回调
        
        参数:
            trade: XtTrade对象
        """
        logger.info(f"{GREEN}【已成交】{RESET} {parse_order_type(trade.order_type)} 代码:{trade.stock_code} 名称:{trade.order_remark} 成交价格:{trade.traded_price:.2f} 成交数量:{trade.traded_volume} 成交编号:{trade.order_id} 成交时间:{timestamp_to_datetime_string(convert_to_current_date(trade.traded_time))}")

    def on_order_error(self, data):
        """
        委托错误回调
        
        参数:
            data: 错误数据对象
        """
        if data.order_id in self.error_orders:
            return
        self.error_orders.add(data.order_id)
        logger.error(f"{RED}【委托失败】{RESET}错误信息:{data.error_msg.strip()}")

    def on_cancel_error(self, data):
        """
        撤单错误回调
        
        参数:
            data: 错误数据对象
        """
        if data.order_id in self.error_orders:
            return
        self.error_orders.add(data.order_id)
        logger.error(f"{RED}【撤单失败】{RESET}错误信息:{data.error_msg.strip()}")


class XtTrader:
    """
    交易类，封装XtQuantTrader的功能
    """
    def __init__(self, account_id, mini_qmt_path):
        """
        初始化交易类
        
        参数:
            account_id (str): 账户ID
            mini_qmt_path (str): miniQMT路径
        """
        self.account_id = account_id
        self.mini_qmt_path = mini_qmt_path
        self.trader = None
        self.account = None
        self.callback = None
        self.is_connected = False
        
    def connect(self):
        """
        连接交易账户
        
        返回:
            bool: 是否连接成功
        """
        # 创建session_id
        session_id = random.randint(100000, 999999)
        
        # 创建交易对象
        self.trader = XtQuantTrader(self.mini_qmt_path, session_id)
        
        # 启动交易对象
        self.trader.start()
        
        # 连接客户端
        connect_result = self.trader.connect()

        if connect_result == 0:
            logger.info(f"{GREEN}【miniQMT连接成功】{RESET} 路径:{self.mini_qmt_path}")
        else:
            logger.error(f"{RED}【miniQMT连接失败】{RESET} 路径:{self.mini_qmt_path}, 错误码:{connect_result}")
            return False

        # 创建账号对象
        self.account = StockAccount(self.account_id)
        
        # 订阅账号
        subscribe_result = self.trader.subscribe(self.account)
        if subscribe_result == 0:
            logger.info(f"{GREEN}【账号订阅成功】{RESET} 账号ID:{self.account_id}")
        else:
            logger.error(f"{RED}【账号订阅失败】{RESET} 账号ID:{self.account_id}, 错误码:{subscribe_result}")
            return False
        
        # 注册回调类
        self.callback = MyXtTraderCallback()
        self.trader.register_callback(self.callback)
        
        self.is_connected = True
        return True
    
    def disconnect(self):
        """
        断开连接
        """
        if self.trader:
            self.trader.stop()
            logger.info(f"{GREEN}【交易连接已关闭】{RESET}")
            self.is_connected = False
    
    

