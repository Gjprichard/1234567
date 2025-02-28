import sqlite3
from datetime import datetime, timedelta
import pandas as pd
import logging
from threading import Lock
from typing import Dict, List, Optional, Tuple
import json
import os
import queue
import threading
import numpy as np

logger = logging.getLogger(__name__)

class ConnectionPool:
    """数据库连接池"""
    def __init__(self, db_path: str, max_connections: int = 5):
        self.db_path = db_path
        self.max_connections = max_connections
        self.connections = queue.Queue(maxsize=max_connections)
        self.lock = threading.Lock()
        
        # 初始化连接池
        for _ in range(max_connections):
            conn = sqlite3.connect(db_path, check_same_thread=False)
            conn.row_factory = sqlite3.Row
            self.connections.put(conn)
    
    def get_connection(self):
        """获取连接"""
        return self.connections.get()
    
    def return_connection(self, conn):
        """归还连接"""
        self.connections.put(conn)
    
    def close_all(self):
        """关闭所有连接"""
        while not self.connections.empty():
            conn = self.connections.get()
            conn.close()

class Database:
    def __init__(self, db_path: str = 'market_data.db', max_connections: int = 5):
        self.db_path = db_path
        self._connection = None
        self._lock = threading.Lock()
        self.pool = ConnectionPool(db_path, max_connections)
        self.create_tables()
    
    def __del__(self):
        """析构函数，确保关闭所有连接"""
        try:
            self.pool.close_all()
        except Exception as e:
            logger.error(f"关闭数据库连接失败: {str(e)}")
    
    def execute_with_connection(self, func):
        """使用连接池执行操作的装饰器"""
        conn = self.pool.get_connection()
        try:
            result = func(conn)
            return result
        finally:
            self.pool.return_connection(conn)
    
    def create_tables(self):
        """创建数据库表"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                # 创建市场数据表
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS market_data (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        symbol TEXT NOT NULL,
                        price REAL NOT NULL,
                        volume REAL NOT NULL,
                        price_change_15m REAL DEFAULT 0.0,
                        volume_change_15m REAL DEFAULT 0.0,
                        timestamp INTEGER NOT NULL,
                        created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                    )
                ''')
                
                # 创建市场预警表
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS market_alerts (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        symbol TEXT NOT NULL,
                        type TEXT NOT NULL,
                        message TEXT NOT NULL,
                        severity TEXT NOT NULL,
                        created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                    )
                ''')
                
                # 创建必要的索引
                cursor.execute('''
                    CREATE INDEX IF NOT EXISTS idx_market_data_symbol_time 
                    ON market_data(symbol, timestamp)
                ''')
                
                cursor.execute('''
                    CREATE INDEX IF NOT EXISTS idx_market_data_timestamp 
                    ON market_data(timestamp)
                ''')
                
                conn.commit()
                logger.info("数据库表创建完成")
                
        except Exception as e:
            logger.error(f"创建数据库表失败: {str(e)}")
            raise
    
    def save_market_data(self, data: Dict):
        """保存市场数据"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT INTO market_data (
                        symbol, price, volume, 
                        price_change_15m, volume_change_15m,
                        timestamp
                    ) VALUES (?, ?, ?, ?, ?, ?)
                ''', (
                    data['symbol'],
                    data['price'],
                    data['volume'],
                    data.get('price_change_15m', 0.0),
                    data.get('volume_change_15m', 0.0),
                    data['timestamp']
                ))
                conn.commit()
                return True
                
        except Exception as e:
            logger.error(f"保存市场数据失败: {str(e)}")
            return False
    
    def get_market_data(self, symbol: Optional[str] = None, limit: int = 100) -> List[Dict]:
        """获取市场数据"""
        def _get_market_data(conn):
            try:
                cursor = conn.cursor()
                
                if symbol:
                    cursor.execute('''
                        SELECT * FROM market_data
                        WHERE symbol = ?
                        ORDER BY timestamp DESC
                        LIMIT ?
                    ''', (symbol, limit))
                else:
                    cursor.execute('''
                        SELECT * FROM market_data
                        ORDER BY timestamp DESC
                        LIMIT ?
                    ''', (limit,))
                
                # 获取列名
                columns = [description[0] for description in cursor.description]
                
                # 转换结果
                results = []
                for row in cursor.fetchall():
                    result = dict(zip(columns, row))
                    # 转换时间戳
                    if 'timestamp' in result:
                        result['timestamp'] = datetime.fromisoformat(result['timestamp'])
                    results.append(result)
                
                return results
                
            except Exception as e:
                logger.error(f"获取市场数据失败: {str(e)}")
                return []
        
        return self.execute_with_connection(_get_market_data)
    
    def save_alert(self, alert: Dict):
        """保存预警信息"""
        def _save_alert(conn):
            try:
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT INTO alerts (
                        symbol, type, severity, message,
                        price, volume, change, timestamp
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    alert['symbol'],
                    alert['type'],
                    alert['severity'],
                    alert['message'],
                    alert.get('price'),
                    alert.get('volume'),
                    alert.get('change'),
                    datetime.now()
                ))
                conn.commit()
                logger.info(f"保存预警信息成功: {alert['message']}")
                return True
            except Exception as e:
                logger.error(f"保存预警信息失败: {str(e)}")
                return False
        
        return self.execute_with_connection(_save_alert)
    
    def get_alerts(self, limit: int = 50) -> List[Dict]:
        """获取预警信息"""
        def _get_alerts(conn):
            try:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT * FROM alerts
                    ORDER BY timestamp DESC
                    LIMIT ?
                ''', (limit,))
                
                columns = [description[0] for description in cursor.description]
                results = []
                
                for row in cursor.fetchall():
                    result = dict(zip(columns, row))
                    if 'timestamp' in result:
                        result['timestamp'] = datetime.fromisoformat(result['timestamp'])
                    results.append(result)
                
                return results
                
            except Exception as e:
                logger.error(f"获取预警信息失败: {str(e)}")
                return []
        
        return self.execute_with_connection(_get_alerts)
    
    def cleanup_old_data(self):
        """清理旧数据并验证"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            try:
                # 获取当前记录数
                cursor.execute("SELECT COUNT(*) FROM spot_market_data")
                initial_count = cursor.fetchone()[0]
                
                # 删除旧数据
                cutoff_time = datetime.now() - timedelta(hours=4)
                cursor.execute('''
                    DELETE FROM spot_market_data
                    WHERE timestamp < ?
                ''', (int(cutoff_time.timestamp() * 1000),))
                
                deleted_count = cursor.rowcount
                
                # 删除旧预警
                cursor.execute('''
                    DELETE FROM market_alerts
                    WHERE created_at < datetime(?, 'unixepoch')
                ''', (cutoff_time.timestamp(),))
                
                # 验证删除后的数据一致性
                cursor.execute("SELECT COUNT(*) FROM spot_market_data")
                final_count = cursor.fetchone()[0]
                
                if initial_count - deleted_count != final_count:
                    logger.warning("数据清理后的记录数不一致")
                
                conn.commit()
                logger.info(f"已清理 {deleted_count} 条旧数据")
                
            finally:
                conn.close()
                
        except Exception as e:
            logger.error(f"清理旧数据失败: {str(e)}")

    def save_spot_data(self, data: Dict) -> bool:
        """保存现货市场数据"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            try:
                # 插入数据
                cursor.execute('''
                    INSERT INTO spot_market_data (
                        symbol, price, volume, timestamp,
                        price_change_15m, volume_change_15m
                    )
                    VALUES (?, ?, ?, ?, ?, ?)
                ''', (
                    data['symbol'],
                    data['price'],
                    data['volume'],
                    data['timestamp'],
                    data.get('price_change_15m', 0.0),  # 使用 get 方法提供默认值
                    data.get('volume_change_15m', 0.0)
                ))
                
                conn.commit()
                return True
                
            finally:
                conn.close()
                
        except Exception as e:
            logger.error(f"保存现货数据失败 {data.get('symbol')}: {str(e)}")
            return False

    def save_option_data(self, data: Dict):
        """保存期权市场数据"""
        def _save_option_data(conn):
            try:
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT INTO option_market_data (
                        symbol, strike, expiry, option_type,
                        price, volume, open_interest, timestamp
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    data['symbol'],
                    data['strike'],
                    data['expiry'],
                    data['option_type'],
                    data['price'],
                    data['volume'],
                    data.get('open_interest', 0),
                    data['timestamp']
                ))
                conn.commit()
                return True
            except Exception as e:
                logger.error(f"保存期权数据失败: {str(e)}")
                return False
        return self.execute_with_connection(_save_option_data)

    def get_spot_data(self, limit: int = 100, time_offset: timedelta = None) -> List[Dict]:
        """获取现货市场数据"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                if time_offset:
                    cutoff_time = datetime.now() - time_offset
                    cursor.execute('''
                        SELECT * FROM spot_market_data 
                        WHERE timestamp > ?
                        ORDER BY timestamp DESC
                        LIMIT ?
                    ''', (int(cutoff_time.timestamp() * 1000), limit))
                else:
                    cursor.execute('''
                        SELECT * FROM spot_market_data 
                        ORDER BY timestamp DESC
                        LIMIT ?
                    ''', (limit,))
                
                columns = [col[0] for col in cursor.description]
                return [dict(zip(columns, row)) for row in cursor.fetchall()]
                
        except Exception as e:
            logger.error(f"获取现货数据失败: {str(e)}")
            return []

    def get_option_data(self, symbol: Optional[str] = None, limit: int = 100) -> List[Dict]:
        """获取期权市场数据"""
        def _get_option_data(conn):
            try:
                cursor = conn.cursor()
                if symbol:
                    cursor.execute('''
                        SELECT * FROM option_market_data
                        WHERE symbol = ?
                        ORDER BY timestamp DESC
                        LIMIT ?
                    ''', (symbol, limit))
                else:
                    cursor.execute('''
                        SELECT * FROM option_market_data
                        ORDER BY timestamp DESC
                        LIMIT ?
                    ''', (limit,))
                
                columns = [description[0] for description in cursor.description]
                return [dict(zip(columns, row)) for row in cursor.fetchall()]
            except Exception as e:
                logger.error(f"获取期权数据失败: {str(e)}")
                return []
        return self.execute_with_connection(_get_option_data)

    def save_market_depth(self, symbol: str, bids: pd.DataFrame, asks: pd.DataFrame):
        """保存市场深度数据"""
        def _save_market_depth(conn):
            try:
                cursor = conn.cursor()
                timestamp = datetime.now()
                
                # 保存买单深度
                for _, row in bids.iterrows():
                    cursor.execute('''
                        INSERT OR REPLACE INTO market_depth (
                            symbol, side, price, amount, cumulative, value, timestamp
                        ) VALUES (?, ?, ?, ?, ?, ?, ?)
                    ''', (
                        symbol,
                        'bid',
                        float(row['price']),
                        float(row['amount']),
                        float(row['cumulative']),
                        float(row['price'] * row['amount']),
                        timestamp
                    ))
                
                # 保存卖单深度
                for _, row in asks.iterrows():
                    cursor.execute('''
                        INSERT OR REPLACE INTO market_depth (
                            symbol, side, price, amount, cumulative, value, timestamp
                        ) VALUES (?, ?, ?, ?, ?, ?, ?)
                    ''', (
                        symbol,
                        'ask',
                        float(row['price']),
                        float(row['amount']),
                        float(row['cumulative']),
                        float(row['price'] * row['amount']),
                        timestamp
                    ))
                
                # 计算并保存指标
                metrics = {
                    'bid_volume': float(bids['amount'].sum()),
                    'ask_volume': float(asks['amount'].sum()),
                    'bid_value': float((bids['price'] * bids['amount']).sum()),
                    'ask_value': float((asks['price'] * asks['amount']).sum()),
                    'spread': float(asks['price'].min() - bids['price'].max()),
                    'spread_percentage': float((asks['price'].min() - bids['price'].max()) / asks['price'].min() * 100),
                    'depth_imbalance': float((bids['amount'].sum() - asks['amount'].sum()) / (bids['amount'].sum() + asks['amount'].sum()))
                }
                
                cursor.execute('''
                    INSERT OR REPLACE INTO depth_metrics (
                        symbol, bid_volume, ask_volume, bid_value, ask_value,
                        spread, spread_percentage, depth_imbalance, timestamp
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    symbol,
                    metrics['bid_volume'],
                    metrics['ask_volume'],
                    metrics['bid_value'],
                    metrics['ask_value'],
                    metrics['spread'],
                    metrics['spread_percentage'],
                    metrics['depth_imbalance'],
                    timestamp
                ))
                
                conn.commit()
                return True
            except Exception as e:
                logger.error(f"保存深度数据失败: {str(e)}")
                return False
        return self.execute_with_connection(_save_market_depth)

    def get_market_depth(self, symbol: str) -> Tuple[pd.DataFrame, pd.DataFrame]:
        """获取市场深度数据"""
        def _get_market_depth(conn):
            try:
                cursor = conn.cursor()
                
                # 获取最新的买单深度
                cursor.execute('''
                    SELECT price, amount, cumulative
                    FROM market_depth
                    WHERE symbol = ? AND side = 'bid'
                    ORDER BY timestamp DESC
                    LIMIT 20
                ''', (symbol,))
                bids = pd.DataFrame(cursor.fetchall(), columns=['price', 'amount', 'cumulative'])
                
                # 获取最新的卖单深度
                cursor.execute('''
                    SELECT price, amount, cumulative
                    FROM market_depth
                    WHERE symbol = ? AND side = 'ask'
                    ORDER BY timestamp DESC
                    LIMIT 20
                ''', (symbol,))
                asks = pd.DataFrame(cursor.fetchall(), columns=['price', 'amount', 'cumulative'])
                
                return bids, asks
                
            except Exception as e:
                logger.error(f"获取深度数据失败: {str(e)}")
                return pd.DataFrame(), pd.DataFrame()
        return self.execute_with_connection(_get_market_depth)

    def get_spot_data_with_metrics(self, limit: int = 100) -> List[Dict]:
        """获取带有计算指标的现货数据"""
        def _get_data(conn):
            try:
                cursor = conn.cursor()
                
                # 使用窗口函数计算指标
                cursor.execute('''
                    WITH metrics AS (
                        SELECT 
                            symbol,
                            price,
                            volume,
                            timestamp,
                            -- 计算价格变化
                            100.0 * (price - LAG(price, 1) OVER (
                                PARTITION BY symbol 
                                ORDER BY timestamp
                            )) / LAG(price, 1) OVER (
                                PARTITION BY symbol 
                                ORDER BY timestamp
                            ) as price_change_15m,
                            -- 计算成交量变化
                            100.0 * (volume - LAG(volume, 1) OVER (
                                PARTITION BY symbol 
                                ORDER BY timestamp
                            )) / LAG(volume, 1) OVER (
                                PARTITION BY symbol 
                                ORDER BY timestamp
                            ) as volume_change_15m,
                            -- 计算波动率
                            100.0 * STDEV(price) OVER (
                                PARTITION BY symbol 
                                ORDER BY timestamp
                                ROWS BETWEEN 14 PRECEDING AND CURRENT ROW
                            ) / AVG(price) OVER (
                                PARTITION BY symbol 
                                ORDER BY timestamp
                                ROWS BETWEEN 14 PRECEDING AND CURRENT ROW
                            ) as volatility
                        FROM spot_market_data
                        WHERE timestamp >= datetime('now', '-15 minutes')
                    )
                    SELECT * FROM metrics
                    ORDER BY timestamp DESC
                    LIMIT ?
                ''', (limit,))
                
                columns = [description[0] for description in cursor.description]
                results = []
                for row in cursor.fetchall():
                    result = dict(zip(columns, row))
                    # 数据类型转换
                    for key in ['price', 'volume', 'price_change_15m', 'volume_change_15m', 'volatility']:
                        if key in result:
                            result[key] = float(result.get(key, 0))
                    if 'timestamp' in result:
                        result['timestamp'] = datetime.fromisoformat(result['timestamp'])
                    results.append(result)
                
                return results
                
            except Exception as e:
                logger.error(f"获取计算指标数据失败: {str(e)}")
                return []
            
        return self.execute_with_connection(_get_data)

    def get_market_depth_with_metrics(self, symbol: str) -> Dict:
        """获取带有计算指标的市场深度数据"""
        def _get_data(conn):
            try:
                cursor = conn.cursor()
                
                # 获取最新的深度数据
                bids, asks = self.get_market_depth(symbol)
                
                # 获取最新的指标数据
                cursor.execute('''
                    SELECT 
                        bid_volume, ask_volume, bid_value, ask_value,
                        spread, spread_percentage, depth_imbalance, timestamp
                    FROM depth_metrics
                    WHERE symbol = ?
                    ORDER BY timestamp DESC
                    LIMIT 1
                ''', (symbol,))
                
                metrics_row = cursor.fetchone()
                if metrics_row:
                    metrics = {
                        'bid_volume': float(metrics_row[0]),
                        'ask_volume': float(metrics_row[1]),
                        'bid_value': float(metrics_row[2]),
                        'ask_value': float(metrics_row[3]),
                        'spread': float(metrics_row[4]),
                        'spread_percentage': float(metrics_row[5]),
                        'depth_imbalance': float(metrics_row[6]),
                        'timestamp': datetime.fromisoformat(metrics_row[7])
                    }
                else:
                    metrics = {}
                
                return {
                    'bids': bids.to_dict('records'),
                    'asks': asks.to_dict('records'),
                    'metrics': metrics
                }
                
            except Exception as e:
                logger.error(f"获取深度指标数据失败: {str(e)}")
                return {}
            
        return self.execute_with_connection(_get_data)

    def get_market_metrics(self) -> Dict:
        """获取市场整体指标"""
        def _get_metrics(conn):
            try:
                cursor = conn.cursor()
                
                # 计算市场整体指标
                cursor.execute('''
                    WITH latest_data AS (
                        SELECT 
                            symbol,
                            price,
                            volume,
                            price_change_15m,
                            volume_change_15m,
                            volatility,
                            timestamp,
                            ROW_NUMBER() OVER (PARTITION BY symbol ORDER BY timestamp DESC) as rn
                        FROM spot_market_data
                        WHERE timestamp >= datetime('now', '-24 hours')
                    )
                    SELECT 
                        COUNT(CASE WHEN price_change_15m > 0 THEN 1 END) as up_count,
                        COUNT(CASE WHEN price_change_15m < 0 THEN 1 END) as down_count,
                        SUM(volume) as total_volume,
                        AVG(volume_change_15m) as avg_volume_change,
                        AVG(volatility) as avg_volatility,
                        MAX(CASE WHEN rn = 1 THEN volume END) as max_volume,
                        MAX(CASE WHEN rn = 1 AND volume = (
                            SELECT MAX(volume) FROM latest_data WHERE rn = 1
                        ) THEN symbol END) as most_active_symbol
                    FROM latest_data
                ''')
                
                row = cursor.fetchone()
                if row:
                    return {
                        'up_count': row[0],
                        'down_count': row[1],
                        'total_volume': float(row[2]),
                        'avg_volume_change': float(row[3]),
                        'avg_volatility': float(row[4]),
                        'max_volume': float(row[5]),
                        'most_active_symbol': row[6]
                    }
                return {}
                
            except Exception as e:
                logger.error(f"获取市场指标失败: {str(e)}")
                return {}
                
        return self.execute_with_connection(_get_metrics)

    def optimize_db(self) -> bool:
        """优化数据库"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            try:
                # 执行 VACUUM 来整理数据库文件
                cursor.execute("VACUUM")
                
                # 更新统计信息
                cursor.execute("ANALYZE")
                
                # 重建索引
                cursor.execute("""
                    CREATE INDEX IF NOT EXISTS idx_spot_symbol_time 
                    ON spot_market_data(symbol, timestamp)
                """)
                
                # 重建预警表索引
                cursor.execute("""
                    CREATE INDEX IF NOT EXISTS idx_alerts_created_at
                    ON market_alerts(created_at)
                """)
                
                conn.commit()
                logger.info("数据库优化完成")
                return True
                
            finally:
                conn.close()
                
        except Exception as e:
            logger.error(f"数据库优化失败: {str(e)}")
            return False

    def get_connection(self):
        """获取数据库连接"""
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            return conn
        except Exception as e:
            logger.error(f"获取数据库连接失败: {str(e)}")
            raise

    def close(self):
        """关闭数据库连接"""
        try:
            with self._lock:
                if self._connection:
                    self._connection.close()
                    self._connection = None
                # 关闭连接池中的所有连接
                if hasattr(self, 'pool'):
                    self.pool.close_all()
            logger.info("数据库连接已关闭")
        except Exception as e:
            logger.error(f"关闭数据库连接失败: {str(e)}")

    def get_latest_market_data(self):
        """获取最新市场数据"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT * FROM market_data 
                    WHERE timestamp = (
                        SELECT MAX(timestamp) FROM market_data
                    )
                ''')
                
                columns = [description[0] for description in cursor.description]
                rows = cursor.fetchall()
                
                return [dict(zip(columns, row)) for row in rows]
                
        except Exception as e:
            logger.error(f"获取最新市场数据失败: {str(e)}")
            return []

    def get_historical_data(self, symbol: str, timestamp: int) -> Optional[Dict]:
        """获取指定时间点的历史数据"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                # 获取最接近指定时间点的数据
                cursor.execute('''
                    SELECT * FROM market_data 
                    WHERE symbol = ? 
                    AND timestamp <= ?
                    ORDER BY ABS(timestamp - ?) ASC
                    LIMIT 1
                ''', (symbol, timestamp, timestamp))
                
                row = cursor.fetchone()
                if row:
                    columns = [description[0] for description in cursor.description]
                    return dict(zip(columns, row))
                return None
                
        except Exception as e:
            logger.error(f"获取历史数据失败: {str(e)}")
            return None

    def get_historical_ticker(self, symbol: str, timestamp: int) -> Optional[Dict]:
        """获取指定时间的ticker数据"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT * FROM market_data
                    WHERE symbol = ? AND timestamp <= ?
                    ORDER BY timestamp DESC
                    LIMIT 1
                ''', (symbol, timestamp))
                
                row = cursor.fetchone()
                if row:
                    return {
                        'symbol': row[1],
                        'price': row[2],
                        'volume': row[3],
                        'timestamp': row[4]
                    }
                return None
                
        except Exception as e:
            logger.error(f"获取历史ticker数据失败: {str(e)}")
            return None