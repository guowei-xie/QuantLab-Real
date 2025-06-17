"""
QuantLab-Real 主程序
"""
import configparser
import time
from core.data import MyXtData
from core.trader import XtTrader
from strategy.pool import get_stock_pool_in_main_board
from utils.logger import logger
from utils.anis import GREEN, YELLOW, RESET

def main():
    """主函数"""
    # 加载配置
    config = configparser.ConfigParser()
    config.read('config.ini', encoding='utf-8')
    account_id = config['ACCOUNT']['ACCOUNT_ID']    
    mini_qmt_path = config['ACCOUNT']['MINI_QMT_PATH']
    
    # 初始化数据对象
    data_api = MyXtData()
    # 创建交易账号连接
    trader = XtTrader(account_id, mini_qmt_path)
    trader.connect()


    if not trader:
        logger.error(f"{YELLOW}【程序退出】{RESET}交易连接失败")
        return
    
    # 查询账户资金信息
    trader.get_asset(display=True)
    
    # 查询持仓信息
    trader.get_positions(display=True)

    # 获取主板股票池
    stock_pool = get_stock_pool_in_main_board()
        
    
    # 保持程序运行
    logger.info(f"{GREEN}【程序运行】{RESET}初始化完成，按Ctrl+C退出...")
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        pass
    finally:
        if trader:
            trader.disconnect()

if __name__ == '__main__':
    main()






