"""日志配置模块"""
import logging
import os
from datetime import datetime
from logging.handlers import TimedRotatingFileHandler

def setup_logger(name: str, log_dir: str = 'logs') -> logging.Logger:
    """设置日志记录器"""
    # 创建日志目录
    os.makedirs(log_dir, exist_ok=True)
    
    logger = logging.getLogger(name)
    
    # 避免重复添加处理器
    if logger.handlers:
        return logger
    
    # 设置基本日志级别
    logger.setLevel(logging.INFO)
    
    # 创建文件处理器（按时间轮转）
    log_file = os.path.join(log_dir, f'{name}.log')
    file_handler = TimedRotatingFileHandler(
        log_file,
        when='midnight',     # 每天午夜轮转
        interval=1,          # 间隔为1天
        backupCount=7,       # 保留7天的日志
        encoding='utf-8'
    )
    file_handler.setLevel(logging.INFO)
    
    # 创建控制台处理器
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.WARNING)  # 控制台只显示警告及以上级别
    
    # 创建格式化器
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # 设置格式化器
    file_handler.setFormatter(formatter)
    console_handler.setFormatter(formatter)
    
    # 添加处理器
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)
    
    return logger 