import pandas as pd
from utils.anis import RED, GREEN, YELLOW, RESET
from utils.logger import logger
from broker.trader import XtTrader
from utils.util import *
from broker import data

class Broker(XtTrader):
    """
    券商接口类，继承XtTrader类，提供交易接口和账户操作功能
    主要功能包括：账户资金查询、持仓查询、委托交易、撤单等操作
    """
    def __init__(self, account_id, mini_qmt_path):
        """
        初始化券商接口类
        
        参数:
            account_id (str): 账户ID
            mini_qmt_path (str): miniQMT路径
        """
        super().__init__(account_id, mini_qmt_path)
        self.order_records = []
        
    def get_asset(self, display=False):
        """
        获取账户资金信息
        
        参数:
            display (bool): 是否显示资金信息
            
        返回:
            dict: 账户资金信息，包含总资产、可用资金、持仓市值、冻结资金等
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
        
        返回:
            float: 账户总资产，查询失败则返回None
        """
        asset = self.get_asset()
        if asset:
            return asset['总资产']
        return None
    
    def get_cash(self):
        """
        获取可用资金
        
        返回:
            float: 账户可用资金，查询失败则返回None
        """
        asset = self.get_asset()
        if asset:
            return asset['可用资金']
        return None
    
    def get_market_value(self):
        """
        获取持仓市值
        
        返回:
            float: 账户持仓市值，查询失败则返回None
        """
        asset = self.get_asset()
        if asset:
            return asset['持仓市值']
        return None
    
    def get_market_percent(self):
        """
        获取持仓市值占总资产的百分比
        
        返回:
            float: 持仓市值占总资产的比例，查询失败则返回None
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
            pandas.DataFrame: 持仓信息，包含股票代码、名称、持仓数量、可用数量、成本价、当前价、市值、盈亏等
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
                    logger.info(f"{GREEN}【持仓明细】{RESET} 共{len(positions)}只股票")
                    # 设置pandas显示选项
                    pd.set_option('display.max_rows', None)
                    pd.set_option('display.max_columns', None)
                    pd.set_option('display.width', 1000)
                    print(df)               
                return df
            else:
                if display:
                    logger.warning(f"{YELLOW}【持仓明细】{RESET} 暂无持仓")
                return pd.DataFrame()
        except Exception as e:
            logger.error(f"{RED}【查询失败】{RESET} 错误:{str(e)}")
            return pd.DataFrame()
        
    def get_stock_position(self, stock_code):
        """
        获取指定股票的持仓信息
        
        参数:
            stock_code (str): 股票代码
            
        返回:
            dict: 股票持仓信息，无持仓则返回None
        """
        positions = self.get_positions()
        if positions.empty:
            return None
        position = positions[positions['股票代码'] == add_stock_suffix(stock_code)]
        return position.to_dict(orient='records')[0] if not position.empty else None
    
    def get_stock_position_percent(self, stock_code):
        """
        获取指定股票的持仓市值占总资产的百分比
        
        参数:
            stock_code (str): 股票代码
            
        返回:
            float: 股票市值占总资产的比例，无持仓则返回None
        """
        position = self.get_stock_position(stock_code)
        if position:
            return position['市值'] / self.get_total_asset()
        return None
    
    def get_stock_value(self, stock_code):
        """
        获取指定股票的市值
        
        参数:
            stock_code (str): 股票代码
            
        返回:
            float: 股票市值，无持仓则返回None
        """
        position = self.get_stock_position(stock_code)
        if position:
            return position['市值']
        return None

    def get_stock_available_volume(self, stock_code):
        """
        获取指定股票的可用数量
        
        参数:
            stock_code (str): 股票代码
            
        返回:
            int: 股票可用数量，无持仓则返回None
        """
        position = self.get_stock_position(stock_code)
        if position:
            return position['可用数量']
        return None
    
    def get_orders(self, cancelable_only=False, display=False):
        """
        获取委托信息
        
        参数:
            cancelable_only (bool): 是否只查询可撤单委托
            display (bool): 是否显示委托信息
            
        返回:
            pandas.DataFrame: 委托信息，包含订单编号、股票代码、名称、委托类型、价格、数量、状态等
        """
        if not self.is_connected:
            logger.error(f"{RED}【查询失败】{RESET} 交易未连接")
            return pd.DataFrame()
            
        try:
            orders = self.trader.query_stock_orders(self.account, cancelable_only)
            if orders:
                data = []
                for order in orders:
                    data.append({
                        '订单编号': order.order_id,
                        '股票代码': order.stock_code,
                        '股票名称': order.order_remark,
                        '委托类型': parse_order_type(order.order_type),
                        '委托价格': order.price,
                        '委托数量': order.order_volume,
                        '成交数量': order.traded_volume,
                        '成交均价': order.traded_price,
                        '委托状态': order.order_status,
                        '状态描述': order.status_msg,
                        '委托时间': timestamp_to_datetime_string(convert_to_current_date(order.order_time))
                    })
                df = pd.DataFrame(data)
                if display:
                    logger.info(f"{GREEN}【委托列表】{RESET} 共{len(orders)}笔委托")
                    pd.set_option('display.max_rows', None)
                    pd.set_option('display.max_columns', None)
                    pd.set_option('display.width', 1000)
                    print(df)
                return df
            else:
                if display:
                    logger.warning(f"{YELLOW}【委托列表】{RESET} 无委托记录")
                return pd.DataFrame()
        except Exception as e:
            logger.error(f"{RED}【查询失败】{RESET} 错误:{str(e)}")
            return pd.DataFrame()
    
    def check_order_before_trade(self, stock_code, side, volume=100, price=0):
        """
        委托前校验，若买则校验可用余额，若卖则校验可用数量
        
        参数:
            stock_code (str): 股票代码
            side (str): 交易方向，'BUY'或'SELL'
            volume (int): 交易数量
            price (float): 交易价格，为0时自动获取最新价格
            
        返回:
            bool: 是否通过校验
        """
        if price == 0:
            price = data.get_latest_price(stock_code)
            if price is None or volume == 0 or volume is None:
                logger.warning(f"{YELLOW}【委托失败】{RESET} 无法获取股票{stock_code}最新价格或交易数量为0")
                return False
                
        if side == 'BUY':
            if self.get_cash() < round(volume * price, 2):
                logger.warning(f"{YELLOW}【委托失败】{RESET} 可用余额不足")
                return False
        else:
            available_volume = self.get_stock_available_volume(stock_code)
            if available_volume is None or available_volume < volume:
                logger.warning(f"{YELLOW}【委托失败】{RESET} 可用数量不足")
                return False
        return True
    
    def send_order(self, stock_code, side_type, volume, price, stategy_name, remark):
        """
        发送委托
        
        参数:
            stock_code (str): 股票代码
            side (str): 交易方向，'BUY'或'SELL'
            volume (int): 交易数量
            price (float): 交易价格，为0时使用市价委托
            stategy_name (str): 策略名称
            remark (str): 备注信息
            
        返回:
            str: 订单编号，委托失败则返回None
        """
        if not self.check_order_before_trade(stock_code, side_type, volume, price):
            return
        
        side = xtconstant.STOCK_BUY if side_type == 'BUY' else xtconstant.STOCK_SELL
        price_type = xtconstant.FIX_PRICE if price > 0 else xtconstant.LATEST_PRICE
        order_id = self.trader.order_stock(self.account, add_stock_suffix(stock_code), side, volume, price_type, price, stategy_name, remark)
        if order_id == -1:
            logger.warning(f"{YELLOW}【委托失败】{RESET} 委托失败")
            return
        logger.info(f"{GREEN}【委托成功】{RESET} 委托{order_id} 股票{stock_code} 方向-{side_type} 数量{volume} 价格{price} 策略-{stategy_name} 备注-{remark}")
        return order_id

        
    def order_value(self, stock_code, side, value=None, price=0, stategy_name='', remark=''):
        """
        买入或卖出指定市值的股票
        
        参数:
            stock_code (str): 股票代码
            side (str): 交易方向，'BUY'或'SELL'
            value (float): 交易市值
            price (float): 交易价格，为0时自动获取最新价格
            stategy_name (str): 策略名称
            remark (str): 备注信息
            
        返回:
            str: 订单编号，委托失败则返回None
        """
        if value is None or value == 0:
            return
        
        if price == 0:
            price = data.get_latest_price(stock_code)
            if price is None:
                logger.warning(f"{YELLOW}【委托失败】{RESET} 无法获取股票{stock_code}最新价格")
                return
        
        volume = calculate_volume(value, price)
        if volume == 0:
            logger.warning(f"{YELLOW}【委托失败】{RESET} 交易股数为0")
            return
        
        order_id = self.send_order(stock_code, side, volume, price, stategy_name, remark)
        return order_id
       
    def sell_all(self, stock_code, price=0, stategy_name='', remark=''):
        """
        清仓指定股票
        
        参数:
            stock_code (str): 股票代码
            price (float): 交易价格，为0时自动获取最新价格
            stategy_name (str): 策略名称
            remark (str): 备注信息
            
        返回:
            str: 订单编号，委托失败则返回None
        """
        if price == 0:
            price = data.get_latest_price(stock_code)
            if price is None:
                logger.warning(f"{YELLOW}【委托失败】{RESET} 无法获取股票{stock_code}最新价格")
                return
        
        volume = self.get_stock_available_volume(stock_code)
        if volume is None or volume == 0:
            logger.warning(f"{YELLOW}【委托失败】{RESET} 可用数量为0")
            return
        
        order_id = self.send_order(stock_code, 'SELL', volume, price, stategy_name, remark)
        return order_id

    def sell_available_percent(self, stock_code, percent=1.0, price=0, stategy_name='', remark=''):
        """
        按百分比卖出指定股票的可用持仓，如果计算出的交易数量不足100股则全部卖出
        
        参数:
            stock_code (str): 股票代码
            percent (float): 卖出比例，默认为1.0（全部卖出）
            price (float): 交易价格，为0时自动获取最新价格
            stategy_name (str): 策略名称
            remark (str): 备注信息
            
        返回:
            str: 订单编号，委托失败则返回None
        """
        if percent is None or percent == 0:
            return
       
        volume = self.get_stock_available_volume(stock_code)
        if volume is None or volume == 0:
            return
        
        volume = calculate_volume(volume * percent, price)
        
        if volume == 0:
            self.sell_all(stock_code, price, stategy_name, remark)
            return
        
        return self.send_order(stock_code, 'SELL', volume, price, stategy_name, remark)
        
        
    def cancel_order(self, order_id=None):
        """
        撤销指定订单
        
        参数:
            order_id (str): 订单编号
            
        返回:
            int: 撤单结果，0表示成功
        """
        if order_id is None:
            return
        
        result = self.trader.cancel_order_stock(self.account, order_id)
        if result == 0:
            logger.info(f"{GREEN}【撤单成功】{RESET} 撤单{order_id}")
        else:
            logger.warning(f"{YELLOW}【撤单失败】{RESET} 撤单{order_id}失败")
        
        return result
        

    def cancel_all_orders(self):
        """
        撤销所有未成交订单
        
        返回:
            list: 所有撤单结果的列表
        """
        cancel_result = []
        orders = self.get_orders(cancelable_only=True)
        for idx, row in orders.iterrows():
            order_id = row['订单编号']
            if order_id is not None:
                result = self.cancel_order(order_id)
                cancel_result.append(result)
        return cancel_result
    
    def cancel_stock_orders(self, stock_code):
        """
        撤销指定股票的未成交订单
        
        参数:
            stock_code (str): 股票代码
            
        返回:
            list: 该股票所有撤单结果的列表
        """
        cancel_result = []
        orders = self.get_orders(cancelable_only=True)
        for idx, row in orders.iterrows():
            if row['股票代码'] == add_stock_suffix(stock_code):
                result = self.cancel_order(row['订单编号'])
                cancel_result.append(result)
        return cancel_result
    
    def order_by_signal(self, signal, strategy_name='', remark=''):
        """
        根据信号进行交易
        
        参数:
            signal (dict): 信号字典，包含股票代码、交易方向、交易数量、交易价格、策略名称、备注
        """
        if signal['signal_type'] == 'BUY_VALUE':
            order_id = self.order_value(signal['stock_code'], 'BUY', signal['value'], signal['price'], strategy_name, remark)
        elif signal['signal_type'] == 'SELL_ALL':
            order_id = self.sell_all(signal['stock_code'], signal['price'], strategy_name, remark)

        # 添加订单记录
        if order_id != -1:
            self.order_records.append({
                'order_id': order_id,
                'stock_code': signal['stock_code'],
                'signal_type': signal['signal_type'],
                'value': signal['value'],
                'price': signal['price'],
                'stategy_name': strategy_name,
                'remark': remark if remark != '' else  signal['signal_name'],
                'create_time': timestamp_to_datetime_string(time.time())
            })
        