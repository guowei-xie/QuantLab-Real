import logging
import requests
import os
import re
from datetime import date

# 定义日志格式
DEFAULT_LOG_FORMAT = '[%(levelname)s][%(asctime)s]%(message)s'
DEFAULT_DATE_FORMAT = '%Y-%m-%d %H:%M:%S'

class RemoveAnsiEscapeCodes(logging.Filter):
    """
    日志过滤器，用于移除日志消息中的ANSI转义码
    """
    def filter(self, record):
        """
        过滤日志记录，移除ANSI转义码
        
        参数:
            record (LogRecord): 日志记录对象
            
        返回:
            bool: 始终返回True，表示保留该日志记录
        """
        if isinstance(record.msg, str):
            record.msg = re.sub(r'\033\[[0-9;]*m', '', record.msg)
        return True

class WeChatHandler(logging.Handler):
    """
    自定义日志处理器，用于将日志发送到企业微信
    """
    def __init__(self, webhook_url):
        """
        初始化企业微信日志处理器
        
        参数:
            webhook_url (str): 企业微信机器人的webhook URL
        """
        super().__init__()
        self.webhook_url = webhook_url

    def emit(self, record):
        """
        发送日志记录到企业微信
        
        参数:
            record (LogRecord): 日志记录对象
        """
        log_entry = self.format(record)
        payload = {
            "msgtype": "text",
            "text": {
                "content": log_entry
            }
        }
        try:
            response = requests.post(self.webhook_url, json=payload)
            response.raise_for_status()
        except requests.exceptions.RequestException as e:
            print(f"Failed to send log to WeChat: {e}")

def create_logger(name='log', log_dir='logs', log_level=logging.DEBUG, 
                  log_format=None, date_format=None, wechat_webhook_url=None, 
                  wechat_level=logging.INFO):
    """
    创建并配置日志记录器
    
    参数:
        name (str): 日志记录器名称
        log_dir (str): 日志文件目录
        log_level (int): 日志级别
        log_format (str): 日志格式
        date_format (str): 日期格式
        wechat_webhook_url (str): 企业微信webhook URL
        wechat_level (int): 企业微信推送的日志级别
        
    返回:
        logging.Logger: 配置好的日志记录器实例
    """
    # 使用默认格式或自定义格式
    formatter = logging.Formatter(
        log_format or DEFAULT_LOG_FORMAT, 
        datefmt=date_format or DEFAULT_DATE_FORMAT
    )
    
    # 创建日志记录器
    logger = logging.getLogger(name)
    logger.setLevel(log_level)
    
    # 清除现有处理器，避免重复添加
    if logger.handlers:
        logger.handlers.clear()

    # 添加控制台输出处理器
    stream_handler = logging.StreamHandler()
    stream_handler.setFormatter(formatter)
    logger.addHandler(stream_handler)

    # 创建日志文件夹（如果不存在）
    if not os.path.exists(log_dir):
        os.makedirs(log_dir)

    # 创建文件处理器，并将日志写入文件
    log_file = os.path.join(log_dir, f"{date.today().strftime('%Y-%m-%d')}.log")
    file_handler = logging.FileHandler(log_file, encoding='utf-8')
    file_handler.setLevel(log_level)
    file_handler.setFormatter(formatter)
    file_handler.addFilter(RemoveAnsiEscapeCodes())
    logger.addHandler(file_handler)

    # 如果提供了企业微信webhook，添加企业微信处理器
    if wechat_webhook_url:
        wechat_handler = WeChatHandler(wechat_webhook_url)
        wechat_handler.setLevel(wechat_level)
        wechat_handler.setFormatter(formatter)
        wechat_handler.addFilter(RemoveAnsiEscapeCodes())
        logger.addHandler(wechat_handler)

    return logger

# 创建默认日志记录器实例
logger = create_logger()