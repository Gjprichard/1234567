import sqlite3
import logging
from datetime import datetime, timedelta
import pandas as pd
from typing import Optional

logger = logging.getLogger(__name__)

class MarketDatabase:
    def __init__(self, db_path: str = 'market_data.db'):
        self.db_path = db_path
        self.create_tables()
    
    def get_connection(self):
        """获取数据库连接"""
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            return conn
        except Exception as e:
            logger.error(f"市场数据库连接失败: {str(e)}")
            raise
    
    def create_tables(self):
        """创建数据表"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                # 创建市场数据表
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS market_data (
                        symbol TEXT NOT NULL,
                        price REAL NOT NULL,
                        volume_24h REAL NOT NULL,
                        price_change_24h REAL,
                        volume_change_24h REAL,
                        timestamp INTEGER NOT NULL,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        PRIMARY KEY (symbol, timestamp)
                    )
                ''')
                
                # 创建预警数据表
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS market_alerts (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        symbol TEXT NOT NULL,
                        type TEXT NOT NULL,
                        severity TEXT NOT NULL,
                        message TEXT NOT NULL,
                        timestamp INTEGER NOT NULL,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                ''')
                
                conn.commit()
                logger.info("市场数据表创建成功")
                
        except Exception as e:
            logger.error(f"创建市场数据表失败: {str(e)}")
            raise
    
    def save_market_data(self, data: pd.DataFrame):
        """保存市场数据"""
        try:
            with self.get_connection() as conn:
                # 保存前先清理旧数据
                self.clean_old_data()
                
                # 保存新数据
                data.to_sql('market_data', conn, if_exists='append', index=False)
                logger.info(f"保存了 {len(data)} 条市场数据")
                
        except Exception as e:
            logger.error(f"保存市场数据失败: {str(e)}")
    
    def save_alert(self, alert: dict):
        """保存预警信息"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT INTO market_alerts 
                    (symbol, type, severity, message, timestamp)
                    VALUES (?, ?, ?, ?, ?)
                ''', (
                    alert['symbol'],
                    alert['type'],
                    alert['severity'],
                    alert['message'],
                    int(datetime.now().timestamp() * 1000)
                ))
                conn.commit()
                logger.info(f"保存了预警信息: {alert['message']}")
                
        except Exception as e:
            logger.error(f"保存预警信息失败: {str(e)}")
    
    def get_latest_data(self, symbol: Optional[str] = None) -> pd.DataFrame:
        """获取最新数据"""
        try:
            with self.get_connection() as conn:
                query = '''
                    SELECT * FROM market_data
                    WHERE timestamp >= ?
                '''
                params = [int((datetime.now() - timedelta(hours=4)).timestamp() * 1000)]
                
                if symbol:
                    query += ' AND symbol = ?'
                    params.append(symbol)
                
                query += ' ORDER BY timestamp DESC'
                
                df = pd.read_sql_query(query, conn, params=params)
                return df
                
        except Exception as e:
            logger.error(f"获取最新数据失败: {str(e)}")
            return pd.DataFrame()
    
    def clean_old_data(self):
        """清理过期数据（保留4小时）"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                # 删除4小时前的数据
                cutoff_time = datetime.now() - timedelta(hours=4)
                cursor.execute('''
                    DELETE FROM market_data
                    WHERE timestamp < ?
                ''', (int(cutoff_time.timestamp() * 1000),))
                
                # 删除预警数据
                cursor.execute('''
                    DELETE FROM market_alerts
                    WHERE created_at < datetime(?, 'unixepoch')
                ''', (cutoff_time.timestamp(),))
                
                conn.commit()
                logger.info(f"已清理 {cursor.rowcount} 条过期市场数据")
                
        except Exception as e:
            logger.error(f"清理市场数据失败: {str(e)}") 