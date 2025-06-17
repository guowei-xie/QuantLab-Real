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
    
    def get_asset(self, display=False):
        """
        获取账户资金信息
        
        参数:
            display (bool): 是否显示资金信息
            
        返回:
            dict: 账户资金信息
        """
        if not self.is_connected:
            logger.error(f"{RED}【查询失败】{RESET} 交易未连接")
            return None
            
        try:
            # 查询资金
            asset = self.trader.query_stock_asset(self.account)
            if asset:
                info = {
                    '总资产': asset.total_asset,
                    '可用资金': asset.cash,
                    '持仓市值': asset.market_value,
                    '冻结资金': asset.frozen_cash
                }
                if display:
                    logger.info(f"{GREEN}【账户资金】{RESET} 总资产:{info['总资产']:.2f} 可用资金:{info['可用资金']:.2f} 持仓市值:{info['持仓市值']:.2f}")
                return info
            else:
                logger.warning(f"{YELLOW}【账户资金】{RESET} 查询结果为空")
                return None
        except Exception as e:
            logger.error(f"{RED}【查询失败】{RESET} 错误:{str(e)}")
            return None
        
    def get_total_asset(self):
        """
        获取总资产
        """
        asset = self.get_asset()
        if asset:
            return asset['总资产']
        return None
    
    def get_cash(self):
        """
        获取可用资金
        """
        asset = self.get_asset()
        if asset:
            return asset['可用资金']
        return None
    
    def get_market_value(self):
        """
        获取持仓市值
        """
        asset = self.get_asset()
        if asset:
            return asset['持仓市值']
        return None
    
    def get_market_percent(self):
        """
        获取持仓市值占总资产的百分比
        """
        asset = self.get_asset()
        if asset:
            return round(asset['持仓市值'] / asset['总资产'], 2)
        return None
    

    def get_positions(self, display=False):
        """
        获取持仓信息
        
        参数:
            display (bool): 是否显示持仓信息
            
        返回:
            pandas.DataFrame: 持仓信息
        """
        if not self.is_connected:
            logger.error(f"{RED}【查询失败】{RESET} 交易未连接")
            return pd.DataFrame()
            
        try:
            # 查询持仓
            positions = self.trader.query_stock_positions(self.account)
            if positions:
                data = []
                for pos in positions:
                    data.append({
                        '股票代码': pos.stock_code,
                        '股票名称': pos.stock_name,
                        '持仓数量': pos.volume,
                        '可用数量': pos.can_use_volume,
                        '成本价': pos.open_price,
                        '当前价': pos.price,
                        '市值': pos.market_value,
                        '盈亏': pos.market_value - pos.open_price * pos.volume
                    })
                df = pd.DataFrame(data)
                if display:
                    logger.info(f"{GREEN}【持仓信息】{RESET} 共{len(positions)}只股票")
                    # 设置pandas显示选项
                    pd.set_option('display.max_rows', None)
                    pd.set_option('display.max_columns', None)
                    pd.set_option('display.width', 1000)
                    print(df)               
                return df
            else:
                if display:
                    logger.warning(f"{YELLOW}【持仓信息】{RESET} 无持仓")
                return pd.DataFrame()
        except Exception as e:
            logger.error(f"{RED}【查询失败】{RESET} 错误:{str(e)}")
            return pd.DataFrame()

