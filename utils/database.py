import sqlite3

def init_order_record_table(database_name='database/strategy.db'):
    """
    初始化交易记录表
    
    表结构：
    
    参数:
        database_name：数据库名称(默认路径：database/strategy.db)
    
    返回:
        None
    """
    conn = sqlite3.connect(database_name)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS order_record (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            stock_code TEXT NOT NULL,
            order_type TEXT NOT NULL,
            order_price REAL NOT NULL,
            order_volume INTEGER NOT NULL,
            order_time TEXT NOT NULL,
            order_date TEXT NOT NULL,
            order_status TEXT NOT NULL,
            order_result TEXT NOT NULL,
            order_message TEXT NOT NULL,
            order_error TEXT NOT NULL,
            order_error_message TEXT NOT NULL)
    ''')
    conn.commit()
    conn.close()


