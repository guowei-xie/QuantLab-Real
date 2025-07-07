"""
QuantLab-Real 主程序
"""
from broker.data import download_history_data
from laboratory.pool import get_stock_pool_in_main_board
from strategys.board_hitting import BoardHitting
from configparser import ConfigParser

if __name__ == '__main__':
    # 读取全局配置
    config = ConfigParser()
    config.read('config.ini', encoding='utf-8')
    account_id = config.get('ACCOUNT', 'ACCOUNT_ID')
    mini_qmt_path = config.get('ACCOUNT', 'MINI_QMT_PATH')
    
    # 补全下载大盘股票历史数据(主板)
    stock_list = get_stock_pool_in_main_board()
    download_history_data(stock_list=stock_list, start_time='20250101', period='1d', progress_bar=True)

    # 创建/执行策略
    strategy = BoardHitting(account_id, mini_qmt_path, config)
    strategy.run()
