"""开发环境配置"""
import os
from dataclasses import dataclass
from typing import Dict, Any

# 开发环境配置
DEBUG = True

# 服务器配置
HOST = '0.0.0.0'
PORT = 8501

# WebSocket配置
WS_HEARTBEAT_INTERVAL = 30  # 心跳间隔(秒)
WS_RECONNECT_INTERVAL = 3   # 重连间隔(秒)

# 数据更新配置
UPDATE_INTERVAL = 1  # 数据更新间隔(秒)
HISTORY_LENGTH = 100  # 历史数据长度

# 日志配置
LOG_LEVEL = 'INFO'
LOG_FORMAT = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'

# 跨域配置
CORS_ORIGINS = ["*"]
CORS_METHODS = ["*"]
CORS_HEADERS = ["*"]

class DevConfig:
    DEBUG = True
    
class DevEnvironment:
    def __init__(self):
        self.config = DevConfig()

dev_env = DevEnvironment() 