import os
from dotenv import load_dotenv
import logging

logger = logging.getLogger(__name__)

class Config:
    def __init__(self):
        load_dotenv()
        
        # 确保data目录存在
        self.data_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data')
        if not os.path.exists(self.data_dir):
            os.makedirs(self.data_dir)
            
        # 数据库路径配置
        self.db_path = os.getenv('OPTION_DB_PATH', os.path.join(self.data_dir, 'option_data.db'))
        self.db_backup_path = os.getenv('OPTION_DB_BACKUP_PATH', os.path.join(self.data_dir, 'backup', 'option_data.db'))
        
        # 交易所配置
        self.exchange_config = {
            'okx': {
                'api_key': os.getenv('OKX_API_KEY', ''),
                'api_secret': os.getenv('OKX_SECRET', ''),
                'password': os.getenv('OKX_PASSWORD', '')
            }
        }
        
        # 监控配置
        self.monitor_config = {
            'update_interval': int(os.getenv('OPTION_UPDATE_INTERVAL', '60')),
            'cleanup_days': int(os.getenv('OPTION_CLEANUP_DAYS', '30')),
            'volume_threshold': int(os.getenv('OPTION_VOLUME_THRESHOLD', '10')),
            'price_deviation': float(os.getenv('OPTION_PRICE_DEVIATION', '0.1'))
        }
        
        # 确保备份目录存在
        backup_dir = os.path.dirname(self.db_backup_path)
        if not os.path.exists(backup_dir):
            os.makedirs(backup_dir)
            
        # 添加API配置
        self.api_config = {
            'timeout': 30000,
            'max_retries': 3,
            'retry_delay': 2.0,
            'rate_limit': 1000  # 毫秒
        }
        
        logger.info(f"配置初始化完成，数据库路径: {self.db_path}") 