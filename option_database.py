import sqlite3
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)

class OptionDatabase:
    def __init__(self, db_path: str = 'option_data.db'):
        self.db_path = db_path
        self.create_tables()
    
    def get_connection(self):
        """获取数据库连接"""
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            # 启用外键约束
            conn.execute('PRAGMA foreign_keys = ON')
            return conn
        except Exception as e:
            logger.error(f"期权数据库连接失败: {str(e)}")
            raise
    
    def create_tables(self):
        """创建期权数据表"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                # 创建期权合约表
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS option_contracts (
                        instId TEXT PRIMARY KEY,
                        symbol TEXT NOT NULL,
                        strike REAL NOT NULL,
                        expTime INTEGER NOT NULL,  -- 使用毫秒时间戳
                        optType TEXT NOT NULL,
                        state TEXT NOT NULL,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                ''')
                
                # 创建期权行情表
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS option_tickers (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        instId TEXT NOT NULL,
                        last REAL NOT NULL,
                        vol24h REAL NOT NULL,
                        volume_15m REAL NOT NULL,
                        ts INTEGER NOT NULL,  -- 使用毫秒时间戳
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY (instId) REFERENCES option_contracts(instId)
                    )
                ''')
                
                conn.commit()
                logger.info("期权数据表创建成功")
                
        except Exception as e:
            logger.error(f"创建期权数据表失败: {str(e)}")
            raise 

    def clean_old_data(self):
        """清理过期数据（保留4小时）"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                # 计算4小时前的时间戳
                cutoff_time = datetime.now() - timedelta(hours=4)
                cutoff_ts = int(cutoff_time.timestamp() * 1000)
                
                # 删除过期的行情数据
                cursor.execute('''
                    DELETE FROM option_tickers
                    WHERE created_at < datetime(?, 'unixepoch')
                ''', (cutoff_time.timestamp(),))
                
                # 删除过期的合约数据
                cursor.execute('''
                    DELETE FROM option_contracts
                    WHERE expTime < ?
                    OR created_at < datetime(?, 'unixepoch')
                ''', (cutoff_ts, cutoff_time.timestamp()))
                
                conn.commit()
                logger.info(f"已清理 {cursor.rowcount} 条过期数据")
                
        except Exception as e:
            logger.error(f"清理过期数据失败: {str(e)}") 