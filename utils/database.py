import sqlite3
from configparser import ConfigParser
from utils.logger import logger
import os

class Database:
    def __init__(self):
        """
        数据库类，用于操作数据库
        
        参数:
            database_name: 数据库名称(默认路径：database/strategy.db)
        
        返回:
            None
        """
        self.database_name = self.get_database_config()
        self.init_order_record_table()

    def get_database_config(self):
        """
        获取数据库配置
        """
        config = ConfigParser()
        config.read('config.ini', encoding='utf-8')
        return config.get('DATABASE', 'DATABASE_NAME', fallback='database/strategy.db')

    def connect(self):
        """
        连接数据库
        """
        if not os.path.exists(os.path.dirname(self.database_name)):
            os.makedirs(os.path.dirname(self.database_name))
        self.conn = sqlite3.connect(self.database_name)
        self.cursor = self.conn.cursor()

    def close(self):
        """
        关闭数据库连接
        """
        self.conn.close()
        
    def init_order_record_table(self):
        """
        初始化交易记录表
        """
        self.connect()
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS order_record (
                order_id INTEGER PRIMARY KEY AUTOINCREMENT,
                stock_code TEXT NOT NULL,
                stock_name TEXT NOT NULL,
                order_type TEXT NOT NULL,
                traded_price REAL NOT NULL,
                traded_volume INTEGER NOT NULL,
                traded_time TEXT NOT NULL,
                traded_date TEXT NOT NULL,
                order_remark TEXT NOT NULL)
        ''')
        try:
            self.conn.commit()
        except Exception as e:
            logger.error(f"初始化交易记录表失败: {e}")
        finally:
            self.close()

    def insert_trade_record(self, order_id, stock_code, stock_name, order_type, traded_price, traded_volume, traded_time, traded_date, order_remark):
        """
        插入交易记录
        参数:
            order_id: 订单ID
            stock_code: 股票代码
            stock_name: 股票名称
            order_type: 订单类型
            traded_price: 成交价格
            traded_volume: 成交数量
            traded_time: 成交时间
            traded_date: 成交日期
            order_remark: 订单备注
        
        返回:
            None
        """
        self.connect()
        self.cursor.execute('''
            INSERT INTO order_record (order_id, stock_code, stock_name, order_type, traded_price, traded_volume, traded_time, traded_date, order_remark)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (order_id, stock_code, stock_name, order_type, traded_price, traded_volume, traded_time, traded_date, order_remark))
        try:
            self.conn.commit()
        except Exception as e:
            logger.error(f"插入交易记录失败: {e}")
        finally:
            self.close()
    
    def get_trade_record(self, stock_code):
        """
        获取交易记录
        参数:
            stock_code: 股票代码
        
        返回:
            dict: 交易记录,字典类型，无结果则返回{}
        """
        self.connect()
        self.cursor.execute('''
            SELECT * FROM order_record WHERE stock_code = ?
        ''', (stock_code,))
        result = self.cursor.fetchall()
        self.close()
        if result:
            return {
                'order_id': result[0][0],
                'stock_code': result[0][1],
                'stock_name': result[0][2],
                'order_type': result[0][3],
                'traded_price': result[0][4],
                'traded_volume': result[0][5],
                'traded_time': result[0][6],
                'traded_date': result[0][7],
                'order_remark': result[0][8]
            }
        else:
            return {}
    
    def get_last_buy_record(self, stock_code):
        """
        获取最近一次买入记录
        参数:
            stock_code: 股票代码
        
        返回:
            dict: 最近一次买入记录,字典类型，无结果则返回{}
        """
        self.connect()
        self.cursor.execute('''
            SELECT * FROM order_record WHERE stock_code = ? AND order_type = '买入' ORDER BY traded_time DESC LIMIT 1
        ''', (stock_code,))
        result = self.cursor.fetchone()
        self.close()
        if result:
            return {
                'order_id': result[0],
                'stock_code': result[1],
                'stock_name': result[2],
                'order_type': result[3],
                'traded_price': result[4],
                'traded_volume': result[5],
                'traded_time': result[6],
                'traded_date': result[7],
                'order_remark': result[8]
            }
        else:
            logger.warning(f"获取最近一次买入记录失败: {stock_code}")
            return {}
    
    def get_last_sell_record(self, stock_code):
        """
        获取最近一次卖出记录
        参数:
            stock_code: 股票代码
        
        返回:
            dict: 最近一次卖出记录,字典类型，无结果则返回{}
        """
        self.connect()
        self.cursor.execute('''
            SELECT * FROM order_record WHERE stock_code = ? AND order_type = '卖出' ORDER BY traded_time DESC LIMIT 1
        ''', (stock_code,))
        result = self.cursor.fetchone()
        self.close()
        if result:
            return {
                'order_id': result[0],
                'stock_code': result[1],
                'stock_name': result[2],
                'order_type': result[3],
                'traded_price': result[4],
                'traded_volume': result[5],
                'traded_time': result[6],
                'traded_date': result[7],
                'order_remark': result[8]
            }
        else:
            return {}   

    def is_in_position(self, stock_code):
        """
        基于数据库记录判断股票是否在持仓中
        
        参数:
            stock_code (str): 股票代码
        """
        last_buy_date = self.get_last_buy_record(stock_code).get('traded_date', '')
        last_sell_date = self.get_last_sell_record(stock_code).get('traded_date', '')
        if last_buy_date == '' and last_sell_date == '': # 历史无持仓记录
            return False
        else:
            diff_days = int(last_sell_date) - int(last_buy_date)
            if diff_days <= 0:
                return True
            else:
                return False