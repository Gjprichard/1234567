import os
from dotenv import load_dotenv

load_dotenv()

# OKX API配置
API_KEY = os.getenv('API_KEY', '')
API_SECRET = os.getenv('API_SECRET', '')
API_PASSPHRASE = os.getenv('API_PASSPHRASE', '')

# API URL
REST_API_URL = os.getenv('REST_API_URL', 'https://www.okx.com')
# REST_API_URL = "https://www.okx.com/api/v5/market"  # 模拟盘 

# 应用配置
class Config:
    def __init__(self):
        self.config = {
            'update_interval': 60,  # 数据更新间隔（秒）
            'min_volume': 1000000,  # 最小24h成交额
            'alert_price_threshold': 3.0,  # 价格变化警报阈值
            'alert_volume_threshold': 50.0  # 成交量变化警报阈值
        }

# 应用配置
DEFAULT_UPDATE_INTERVAL = 60  # 默认更新间隔（秒）
DEFAULT_PRICE_THRESHOLD = 1.0  # 默认价格变化阈值（%）
DEFAULT_VOLUME_THRESHOLD = 2.0  # 默认成交量变化阈值（%）

# 服务器配置
SERVER_CONFIG = {
    'host': 'localhost',
    'port': 5002,
    'debug': True
}

class Config:
    DEBUG = True
    SECRET_KEY = os.getenv('SECRET_KEY', 'your-secret-key')
    DATABASE_URL = os.getenv('DATABASE_URL', 'sqlite:///market_data.db') 

# API配置
EXCHANGE_CONFIG = {
    'binance': {
        'api_key': 'YOUR_BINANCE_API_KEY',
        'api_secret': 'YOUR_BINANCE_SECRET'
    },
    'okx': {
        'api_key': 'YOUR_OKX_API_KEY',
        'api_secret': 'YOUR_OKX_SECRET',
        'passphrase': 'YOUR_OKX_PASSPHRASE'
    }
}

# 数据配置
DATA_CONFIG = {
    'symbols': ['BTC', 'ETH'],
    'timeframes': ['1m', '5m', '15m', '1h', '4h', '1d'],
    'cache_expire': {
        'ticker': 0.5,    # 0.5秒
        'kline': 60,      # 1分钟
        'options': 60     # 1分钟
    }
} 