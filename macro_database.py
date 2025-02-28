import sqlite3
import logging
from datetime import datetime, timedelta
import json
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)

class MacroDatabase:
    def __init__(self, db_path: str = 'macro_data.db'):
        self.db_path = db_path
        self.create_tables()
    
    def get_connection(self):
        """获取数据库连接"""
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            return conn
        except Exception as e:
            logger.error(f"宏观数据库连接失败: {str(e)}")
            raise
    
    def create_tables(self):
        """创建数据表"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                # 创建因子数据表
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS factor_data (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        name TEXT NOT NULL,
                        type TEXT NOT NULL,
                        value REAL NOT NULL,
                        weight REAL NOT NULL,
                        impact REAL,
                        timestamp INTEGER NOT NULL,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                ''')
                
                # 创建新闻数据表
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS news_data (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        title TEXT NOT NULL,
                        content TEXT,
                        source TEXT NOT NULL,
                        sentiment REAL,
                        published_at INTEGER NOT NULL,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                ''')
                
                # 创建社交媒体数据表
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS social_data (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        platform TEXT NOT NULL,
                        user TEXT NOT NULL,
                        content TEXT NOT NULL,
                        sentiment REAL,
                        engagement INTEGER,
                        posted_at INTEGER NOT NULL,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                ''')
                
                conn.commit()
                logger.info("宏观数据表创建成功")
                
        except Exception as e:
            logger.error(f"创建宏观数据表失败: {str(e)}")
            raise
    
    def clean_old_data(self):
        """清理过期数据（保留1天）"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                # 删除1天前的数据
                cutoff_time = datetime.now() - timedelta(days=1)
                cutoff_ts = int(cutoff_time.timestamp() * 1000)
                
                # 清理各种数据表
                tables = [
                    'factor_data',
                    'news_data',
                    'social_data'
                ]
                
                for table in tables:
                    cursor.execute(f'''
                        DELETE FROM {table}
                        WHERE created_at < datetime(?, 'unixepoch')
                    ''', (cutoff_time.timestamp(),))
                    
                    logger.info(f"已从 {table} 清理 {cursor.rowcount} 条过期数据")
                
                conn.commit()
                
        except Exception as e:
            logger.error(f"清理宏观数据失败: {str(e)}") 