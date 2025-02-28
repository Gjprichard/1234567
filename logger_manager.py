import logging
import os
from datetime import datetime, timedelta
from logging.handlers import TimedRotatingFileHandler
import glob

class LoggerManager:
    def __init__(self):
        self.log_dir = 'logs'
        if not os.path.exists(self.log_dir):
            os.makedirs(self.log_dir)
            
    def get_logger(self, name):
        logger = logging.getLogger(name)
        if not logger.handlers:
            logger.setLevel(logging.INFO)
            
            # 创建文件处理器
            log_file = os.path.join(self.log_dir, f'{name}.log')
            file_handler = logging.FileHandler(log_file)
            file_handler.setLevel(logging.INFO)
            
            # 创建控制台处理器
            console_handler = logging.StreamHandler()
            console_handler.setLevel(logging.INFO)
            
            # 设置格式
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
            file_handler.setFormatter(formatter)
            console_handler.setFormatter(formatter)
            
            # 添加处理器
            logger.addHandler(file_handler)
            logger.addHandler(console_handler)
            
        return logger
    
    def clean_old_logs(self):
        """清理过期日志"""
        try:
            now = datetime.now()
            for name, retention_time in self.retention_times.items():
                log_pattern = os.path.join(self.log_dir, f'{name}.log.*')
                for log_file in glob.glob(log_pattern):
                    # 获取日志文件的修改时间
                    mtime = datetime.fromtimestamp(os.path.getmtime(log_file))
                    if now - mtime > retention_time:
                        os.remove(log_file)
                        print(f"已删除过期日志: {log_file}")
                        
        except Exception as e:
            print(f"清理日志失败: {str(e)}")
    
    def compress_old_logs(self):
        """压缩旧日志文件"""
        try:
            import gzip
            import shutil
            
            for name in self.retention_times.keys():
                log_pattern = os.path.join(self.log_dir, f'{name}.log.*')
                for log_file in glob.glob(log_pattern):
                    if not log_file.endswith('.gz'):
                        # 压缩日志文件
                        with open(log_file, 'rb') as f_in:
                            with gzip.open(f'{log_file}.gz', 'wb') as f_out:
                                shutil.copyfileobj(f_in, f_out)
                        # 删除原文件
                        os.remove(log_file)
                        print(f"已压缩日志文件: {log_file}")
                        
        except Exception as e:
            print(f"压缩日志失败: {str(e)}") 