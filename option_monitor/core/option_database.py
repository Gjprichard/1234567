import sqlite3
import pandas as pd
from datetime import datetime
import logging
from typing import Dict, List, Optional, Tuple
from threading import Lock
import os
import shutil
import threading
import time

logger = logging.getLogger(__name__)

class OptionDatabase:
    def __init__(self, db_path: str = 'option_data.db'):
        """初始化数据库"""
        # 处理空路径情况
        if not db_path or db_path.strip() == '':
            db_path = 'option_data.db'
            logger.warning(f"数据库路径为空，使用默认路径: {db_path}")
            
        self.db_path = db_path
        self.lock = threading.Lock()
        
        # 确保数据目录存在
        db_dir = os.path.dirname(db_path)
        if db_dir and not os.path.exists(db_dir):
            try:
                os.makedirs(db_dir)
                logger.info(f"创建数据目录: {db_dir}")
            except Exception as e:
                logger.error(f"创建数据目录失败: {str(e)}")
                # 如果创建目录失败，使用当前目录
                self.db_path = os.path.basename(db_path)
                logger.warning(f"使用当前目录作为数据库路径: {self.db_path}")
        
        # 创建表（不删除现有数据库）
        self.create_tables()
        logger.info(f"期权数据表创建成功，使用数据库: {self.db_path}")
    
    def create_tables(self):
        """创建数据表，确保字段定义一致"""
        try:
            with self.lock, sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # 期权合约表
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS option_contracts (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        symbol TEXT NOT NULL,
                        underlying TEXT NOT NULL,
                        contract_type TEXT NOT NULL,
                        strike_price REAL NOT NULL,
                        expiry_date TEXT NOT NULL,
                        settlement TEXT NOT NULL,
                        multiplier INTEGER NOT NULL,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        UNIQUE(symbol)
                    )
                """)
                
                # 期权市场数据表
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS option_market_data (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        contract_id INTEGER NOT NULL,
                        timestamp INTEGER NOT NULL,
                        last_price REAL NOT NULL,
                        mark_price REAL NOT NULL,
                        volume REAL NOT NULL,
                        open_interest INTEGER NOT NULL,
                        bid REAL,
                        ask REAL,
                        iv REAL,
                        delta REAL,
                        gamma REAL,
                        theta REAL,
                        vega REAL,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY(contract_id) REFERENCES option_contracts(id),
                        UNIQUE(contract_id, timestamp)
                    )
                """)
                
                # 创建索引
                cursor.execute("""
                    CREATE INDEX IF NOT EXISTS idx_market_data_timestamp 
                    ON option_market_data(timestamp)
                """)
                
                conn.commit()
                
        except Exception as e:
            logger.error(f"创建数据表失败: {str(e)}")
            raise
    
    def save_contracts(self, contracts: List[Dict]) -> bool:
        """批量保存期权合约"""
        try:
            with self.lock, sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # 批量插入或更新合约
                cursor.executemany("""
                    INSERT OR REPLACE INTO option_contracts (
                        symbol, underlying, contract_type, strike_price,
                        expiry_date, settlement, multiplier
                    ) VALUES (?, ?, ?, ?, ?, ?, ?)
                """, [(
                    c['symbol'],
                    c['underlying'],
                    c.get('contract_type', c.get('type', '')),  # 兼容两种字段名
                    c.get('strike_price', c.get('strike', 0.0)),
                    c.get('expiry_date', c.get('expiry', '')),
                    c.get('settlement', 'USDT'),
                    c.get('multiplier', 1.0)
                ) for c in contracts])
                
                conn.commit()
                logger.info(f"批量保存了{len(contracts)}个合约")
                return True
                
        except Exception as e:
            logger.error(f"保存期权合约失败: {str(e)}")
            if conn:
                conn.rollback()
            return False
    
    def validate_market_data(self, market_data: Dict) -> bool:
        """验证市场数据的有效性"""
        try:
            # 检查必要字段是否存在
            required_fields = ['price', 'underlying_price', 'volume', 'iv']
            if not all(field in market_data for field in required_fields):
                logger.warning(f"数据缺少必要字段: {required_fields}")
                return False
            
            # 检查数据范围的合理性
            if market_data['price'] <= 0 or market_data['underlying_price'] <= 0:
                logger.warning("价格数据异常")
                return False
            
            if market_data['volume'] < 0:
                logger.warning("成交量数据异常")
                return False
            
            if not 0 < market_data['iv'] < 500:  # IV通常不会超过500%
                logger.warning(f"隐含波动率数据异常: {market_data['iv']}%")
                return False
            
            # 检查数据时效性
            if 'timestamp' in market_data:
                data_time = datetime.fromtimestamp(market_data['timestamp'])
                time_diff = datetime.now() - data_time
                if time_diff.total_seconds() > 300:  # 数据不应该超过5分钟
                    logger.warning(f"数据可能过期: {time_diff.total_seconds()}秒")
                    return False
            
            return True
        except Exception as e:
            logger.error(f"数据验证失败: {str(e)}")
            return False

    def calculate_market_indicators(self, contract_id: str) -> Dict[str, float]:
        """计算市场指标"""
        try:
            with self.lock, sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                query = """
                    WITH time_windows AS (
                        SELECT 
                            price,
                            volume,
                            timestamp,
                            AVG(price) OVER w15 as avg_price_15m,
                            AVG(volume) OVER w15 as avg_volume_15m,
                            AVG(price) OVER w30 as avg_price_30m,
                            AVG(volume) OVER w30 as avg_volume_30m,
                            LAG(price, 1) OVER w15 as prev_price,
                            LAG(volume, 1) OVER w15 as prev_volume
                        FROM option_market_data
                        WHERE contract_id = ?
                        AND timestamp >= ?
                        WINDOW 
                            w15 AS (ORDER BY timestamp DESC RANGE 900 PRECEDING),
                            w30 AS (ORDER BY timestamp DESC RANGE 1800 PRECEDING)
                    )
                    SELECT 
                        price,
                        volume,
                        avg_price_15m,
                        avg_volume_15m,
                        avg_price_30m,
                        avg_volume_30m,
                        prev_price,
                        prev_volume
                    FROM time_windows
                    WHERE timestamp = (SELECT MAX(timestamp) FROM time_windows)
                """
                
                current_ts = int(time.time())
                thirty_mins_ago = current_ts - 1800
                
                cursor.execute(query, (contract_id, thirty_mins_ago))
                row = cursor.fetchone()
                
                if not row:
                    return self._get_default_indicators()
                    
                # 解包数据
                (price, volume, avg_price_15m, avg_volume_15m,
                 avg_price_30m, avg_volume_30m, prev_price, prev_volume) = row
                
                # 计算指标
                indicators = {
                    # 价格变化率
                    'premium_change_15m': self._calculate_change_rate(
                        price, prev_price, avg_price_15m
                    ),
                    
                    # 成交量变化率
                    'volume_change_15m': self._calculate_change_rate(
                        volume, prev_volume, avg_volume_15m
                    ),
                    
                    # 动量指标
                    'momentum_indicator': self._calculate_momentum(
                        price, avg_price_15m, avg_price_30m
                    ),
                    
                    # 波动率比率
                    'volatility_ratio': self._calculate_volatility_ratio(
                        price, avg_price_15m, avg_price_30m
                    )
                }
                
                return indicators
                
        except Exception as e:
            logger.error(f"计算市场指标失败: {str(e)}")
            return self._get_default_indicators()

    def _calculate_change_rate(self, current: float, previous: float, average: float) -> float:
        """计算变化率"""
        try:
            if not previous or previous == 0:
                return 0.0
            
            # 使用平均值来平滑异常值
            base = (previous + average) / 2
            change_rate = ((current - base) / base) * 100
            
            # 限制变化率范围
            return max(min(change_rate, 1000), -1000)
            
        except Exception:
            return 0.0

    def _calculate_momentum(self, current: float, avg_15m: float, avg_30m: float) -> float:
        """计算动量指标"""
        try:
            if not avg_15m or not avg_30m:
                return 0.0
            
            short_term = (current - avg_15m) / avg_15m
            long_term = (avg_15m - avg_30m) / avg_30m
            
            return (short_term - long_term) * 100
            
        except Exception:
            return 0.0

    def _calculate_volatility_ratio(self, current: float, avg_15m: float, avg_30m: float) -> float:
        """计算波动率比率"""
        try:
            if not avg_15m or not avg_30m:
                return 1.0
            
            short_vol = abs(current - avg_15m) / avg_15m
            long_vol = abs(avg_15m - avg_30m) / avg_30m
            
            if long_vol == 0:
                return 1.0
            
            return short_vol / long_vol
            
        except Exception:
            return 1.0

    def save_market_data(self, market_data_list: List[Dict]) -> bool:
        """批量保存市场数据"""
        try:
            with self.lock, sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # 批量计算指标
                for market_data in market_data_list:
                    if not self.validate_market_data(market_data):
                        continue
                    
                    # 计算市场指标
                    indicators = self.calculate_market_indicators(
                        market_data['contract_id']
                    )
                    market_data.update(indicators)
                    
                # 批量插入数据
                cursor.executemany("""
                    INSERT INTO option_market_data (
                        contract_id, price, underlying_price, bid, ask,
                        volume, open_interest, iv, volume_change_15m,
                        premium_change_15m, momentum_indicator,
                        volatility_ratio, timestamp
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, [(
                    data['contract_id'],
                    data['price'],
                    data['underlying_price'],
                    data.get('bid', 0),
                    data.get('ask', 0),
                    data['volume'],
                    data.get('open_interest', 0),
                    data['iv'],
                    data['volume_change_15m'],
                    data['premium_change_15m'],
                    data['momentum_indicator'],
                    data['volatility_ratio'],
                    data.get('timestamp', int(time.time()))
                ) for data in market_data_list])
                
                conn.commit()
                return True
                
        except Exception as e:
            logger.error(f"保存市场数据失败: {str(e)}")
            return False
    
    def get_active_contracts(self, underlying: str) -> List[Dict]:
        """获取活跃期权合约"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                # 获取未过期、3天内到期且持仓量前50的合约
                cursor.execute('''
                    SELECT c.id, c.symbol, c.underlying, c.contract_type, 
                           c.strike_price, c.expiry_date, c.settlement, c.multiplier,
                           COALESCE(m.open_interest, 0) as open_interest
                    FROM option_contracts c
                    LEFT JOIN (
                        SELECT contract_id, open_interest
                        FROM option_market_data
                        WHERE timestamp >= datetime('now', '-1 hour')
                        GROUP BY contract_id
                    ) m ON c.id = m.contract_id
                    WHERE c.underlying = ?
                    AND c.expiry_date >= date('now')
                    AND c.expiry_date <= date('now', '+3 day')
                    ORDER BY m.open_interest DESC NULLS LAST
                    LIMIT 50
                ''', (underlying,))
                
                contracts = []
                for row in cursor.fetchall():
                    contracts.append({
                        'id': row['id'],
                        'symbol': row['symbol'],
                        'underlying': row['underlying'],
                        'contract_type': row['contract_type'],
                        'strike_price': row['strike_price'],
                        'expiry_date': row['expiry_date'],
                        'settlement': row['settlement'],
                        'multiplier': row['multiplier'],
                        'open_interest': row['open_interest']
                    })
                
                if contracts:
                    logger.info(f"获取到{len(contracts)}个{underlying}活跃合约")
                else:
                    logger.warning(f"没有找到{underlying}的活跃合约")
                
                return contracts
                
        except Exception as e:
            logger.error(f"获取活跃合约失败: {str(e)}")
            return []
    
    def get_market_depth(self, contract_id: int) -> Dict:
        """获取期权合约的市场深度数据"""
        try:
            with self.lock, sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT 
                        price,
                        bid,
                        ask,
                        volume,
                        open_interest,
                        iv
                    FROM option_market_data
                    WHERE contract_id = ?
                    ORDER BY timestamp DESC
                    LIMIT 1
                ''', (contract_id,))
                
                row = cursor.fetchone()
                if row:
                    return {
                        'price': row[0],
                        'bid': row[1],
                        'ask': row[2],
                        'volume': row[3],
                        'open_interest': row[4],
                        'iv': row[5]
                    }
                return None
                
        except Exception as e:
            logger.error(f"获取期权市场深度数据失败: {str(e)}")
            return None
    
    def get_historical_data(self, contract_id: int, days: int = 7) -> pd.DataFrame:
        """获取期权合约的历史数据"""
        try:
            with self.lock, sqlite3.connect(self.db_path) as conn:
                query = '''
                    SELECT 
                        price,
                        underlying_price,
                        volume,
                        open_interest,
                        iv,
                        delta,
                        gamma,
                        theta,
                        vega,
                        timestamp
                    FROM option_market_data
                    WHERE 
                        contract_id = ?
                        AND timestamp >= datetime('now', ?)
                    ORDER BY timestamp ASC
                '''
                
                df = pd.read_sql_query(
                    query,
                    conn,
                    params=(contract_id, f'-{days} days')
                )
                
                df['timestamp'] = pd.to_datetime(df['timestamp'])
                return df
                
        except Exception as e:
            logger.error(f"获取期权历史数据失败: {str(e)}")
            return pd.DataFrame()
    
    def get_contract_data(self, contract_id: int) -> Optional[Dict]:
        """获取单个合约数据"""
        try:
            with self.lock, sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT 
                        id,
                        symbol,
                        underlying,
                        contract_type,
                        strike_price,
                        expiry_date,
                        settlement,
                        multiplier
                    FROM option_contracts
                    WHERE id = ?
                ''', (contract_id,))
                
                row = cursor.fetchone()
                if row:
                    return {
                        'id': row[0],
                        'symbol': row[1],
                        'underlying': row[2],
                        'contract_type': row[3],
                        'strike_price': row[4],
                        'expiry_date': row[5],
                        'settlement': row[6],
                        'multiplier': row[7]
                    }
                return None
                
        except Exception as e:
            logger.error(f"获取合约数据失败: {str(e)}")
            return None
    
    def cleanup_old_data(self, days: int = 7) -> bool:
        """清理旧数据"""
        try:
            with self.lock, sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # 计算截止时间戳
                cutoff_ts = int(time.time()) - (days * 24 * 60 * 60)
                
                # 删除旧数据
                cursor.execute("""
                    DELETE FROM option_market_data 
                    WHERE timestamp < ?
                """, (cutoff_ts,))
                
                # 优化数据库
                cursor.execute("VACUUM")
                
                deleted_count = cursor.rowcount
                conn.commit()
                
                logger.info(f"已清理 {deleted_count} 条{days}天前的数据")
                return True
                
        except Exception as e:
            logger.error(f"清理旧数据失败: {str(e)}")
            return False
    
    def backup_database(self):
        """备份数据库"""
        try:
            backup_path = f'backup/option_data_{datetime.now().strftime("%Y%m%d_%H%M%S")}.db'
            os.makedirs(os.path.dirname(backup_path), exist_ok=True)
            
            with self.lock:
                shutil.copy2(self.db_path, backup_path)
            
            logger.info(f"数据库已备份到: {backup_path}")
            return True
            
        except Exception as e:
            logger.error(f"备份数据库失败: {str(e)}")
            return False 

    def check_contracts(self):
        """检查合约数据"""
        try:
            with self.lock, sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT 
                        symbol, 
                        underlying, 
                        contract_type, 
                        strike_price, 
                        expiry_date,
                        date(expiry_date) > date('now') as is_active
                    FROM option_contracts 
                    LIMIT 5
                ''')
                rows = cursor.fetchall()
                for row in rows:
                    logger.info(f"合约示例: {row}")
                
                # 检查日期格式
                cursor.execute('''
                    SELECT COUNT(*) 
                    FROM option_contracts 
                    WHERE date(expiry_date) > date('now')
                ''')
                active_count = cursor.fetchone()[0]
                logger.info(f"未过期合约数量: {active_count}")
                
        except Exception as e:
            logger.error(f"检查合约数据失败: {str(e)}") 

    def get_recent_market_data(self, contract_id: int, minutes: int = 15) -> Optional[Dict]:
        """获取最近的市场数据"""
        try:
            with self.lock, sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT 
                        price,
                        underlying_price,
                        volume,
                        open_interest,
                        iv,
                        timestamp
                    FROM option_market_data
                    WHERE 
                        contract_id = ? 
                        AND timestamp >= datetime('now', ?)
                    ORDER BY timestamp DESC
                    LIMIT 1
                ''', (contract_id, f'-{minutes} minutes'))
                
                row = cursor.fetchone()
                if row:
                    return {
                        'price': row[0],
                        'underlying_price': row[1],
                        'volume': row[2],
                        'open_interest': row[3],
                        'iv': row[4],
                        'timestamp': row[5]
                    }
                return None
                
        except Exception as e:
            logger.error(f"获取最近市场数据失败: {str(e)}")
            return None 

    def get_connection(self):
        """获取数据库连接"""
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row  # 启用行工厂，使结果可以通过列名访问
            return conn
        except Exception as e:
            logger.error(f"获取数据库连接失败: {str(e)}")
            raise 

    def save_option_data(self, data: pd.DataFrame):
        """保存期权市场数据"""
        try:
            if data.empty:
                logger.warning("没有数据需要保存")
                return
            
            conn = self.get_connection()
            cursor = conn.cursor()
            
            # 创建临时表
            cursor.execute("""
                CREATE TEMPORARY TABLE IF NOT EXISTS temp_option_data (
                    symbol TEXT,
                    strike REAL,
                    expiry TEXT,
                    type TEXT,
                    last REAL,
                    bid REAL,
                    ask REAL,
                    volume REAL,
                    open_interest REAL,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # 插入数据到临时表
            data_to_insert = data.to_dict('records')
            cursor.executemany(
                """
                INSERT INTO temp_option_data (
                    symbol, strike, expiry, type, last, bid, ask, 
                    volume, open_interest
                ) VALUES (
                    :symbol, :strike, :expiry, :type, :last, :bid, :ask,
                    :volume, :openInterest
                )
                """,
                data_to_insert
            )
            
            # 更新或插入主表
            cursor.execute("""
                INSERT OR REPLACE INTO option_market_data (
                    symbol, strike, expiry, type, last, bid, ask,
                    volume, open_interest, timestamp
                )
                SELECT 
                    symbol, strike, expiry, type, last, bid, ask,
                    volume, open_interest, timestamp
                FROM temp_option_data
            """)
            
            # 删除临时表
            cursor.execute("DROP TABLE temp_option_data")
            
            conn.commit()
            logger.info(f"成功保存 {len(data)} 条期权市场数据")
            
        except Exception as e:
            logger.error(f"保存期权市场数据失败: {str(e)}")
            if conn:
                conn.rollback()
        finally:
            if cursor:
                cursor.close()
            if conn:
                conn.close() 

    def get_latest_market_data(self) -> List[Dict]:
        """获取最新的期权市场数据"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            # 获取最新数据
            cursor.execute("""
                SELECT 
                    symbol,
                    strike,
                    expiry,
                    type,
                    last,
                    bid,
                    ask,
                    volume,
                    open_interest,
                    timestamp
                FROM option_market_data
                WHERE timestamp >= datetime('now', '-5 minutes')
                ORDER BY timestamp DESC
            """)
            
            # 转换为字典列表
            columns = [col[0] for col in cursor.description]
            results = [dict(zip(columns, row)) for row in cursor.fetchall()]
            
            if not results:
                logger.warning("未找到最近5分钟内的期权市场数据")
            else:
                logger.info(f"获取到 {len(results)} 条期权市场数据")
                
            return results
            
        except Exception as e:
            logger.error(f"获取最新市场数据失败: {str(e)}")
            return []
            
        finally:
            if cursor:
                cursor.close()
            if conn:
                conn.close() 

    def _get_default_indicators(self) -> Dict[str, float]:
        """获取默认指标值"""
        return {
            'volume_change_15m': 0.0,
            'premium_change_15m': 0.0,
            'momentum_indicator': 0.0,
            'volatility_ratio': 1.0
        } 

    def get_market_statistics(self, contract_id: str = None) -> Dict:
        """获取市场统计数据"""
        try:
            with self.lock, sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # 基础查询
                query = """
                    WITH recent_data AS (
                        SELECT 
                            m.*,
                            c.contract_type,
                            c.strike_price
                        FROM option_market_data m
                        JOIN option_contracts c ON m.contract_id = c.id
                        WHERE m.timestamp >= ?
                        {}  -- 合约ID条件占位符
                    )
                    SELECT
                        COUNT(*) as total_records,
                        AVG(price) as avg_price,
                        AVG(volume) as avg_volume,
                        AVG(iv) as avg_iv,
                        MAX(volume_change_15m) as max_volume_change,
                        MIN(volume_change_15m) as min_volume_change,
                        MAX(premium_change_15m) as max_premium_change,
                        MIN(premium_change_15m) as min_premium_change,
                        AVG(momentum_indicator) as avg_momentum,
                        AVG(volatility_ratio) as avg_volatility_ratio,
                        SUM(CASE WHEN contract_type = 'call' THEN volume ELSE 0 END) as call_volume,
                        SUM(CASE WHEN contract_type = 'put' THEN volume ELSE 0 END) as put_volume
                    FROM recent_data
                """
                
                # 添加合约ID条件
                if contract_id:
                    query = query.format("AND m.contract_id = ?")
                    params = (int(time.time()) - 3600, contract_id)  # 1小时内的数据
                else:
                    query = query.format("")
                    params = (int(time.time()) - 3600,)
                
                cursor.execute(query, params)
                row = cursor.fetchone()
                
                if not row:
                    return {}
                    
                # 构建统计结果
                stats = {
                    'total_records': row[0],
                    'avg_price': round(row[1], 2) if row[1] else 0,
                    'avg_volume': round(row[2], 2) if row[2] else 0,
                    'avg_iv': round(row[3], 2) if row[3] else 0,
                    'volume_change_range': {
                        'max': round(row[4], 2) if row[4] else 0,
                        'min': round(row[5], 2) if row[5] else 0
                    },
                    'premium_change_range': {
                        'max': round(row[6], 2) if row[6] else 0,
                        'min': round(row[7], 2) if row[7] else 0
                    },
                    'avg_momentum': round(row[8], 2) if row[8] else 0,
                    'avg_volatility_ratio': round(row[9], 2) if row[9] else 1,
                    'put_call_volume_ratio': (
                        round(row[11] / row[10], 2) if row[10] and row[10] > 0 else 0
                    )
                }
                
                return stats
                
        except Exception as e:
            logger.error(f"获取市场统计失败: {str(e)}")
            return {}

    def get_anomaly_contracts(self, threshold: float = 2.0) -> List[Dict]:
        """获取异常合约"""
        try:
            with self.lock, sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                query = """
                    WITH recent_data AS (
                        SELECT 
                            m.*,
                            c.symbol,
                            c.contract_type,
                            c.strike_price,
                            c.expiry_date
                        FROM option_market_data m
                        JOIN option_contracts c ON m.contract_id = c.id
                        WHERE m.timestamp >= ?
                    )
                    SELECT 
                        symbol,
                        contract_type,
                        strike_price,
                        expiry_date,
                        price,
                        volume,
                        iv,
                        volume_change_15m,
                        premium_change_15m,
                        momentum_indicator,
                        volatility_ratio
                    FROM recent_data
                    WHERE 
                        ABS(volume_change_15m) > ? OR
                        ABS(premium_change_15m) > ? OR
                        ABS(momentum_indicator) > ? OR
                        volatility_ratio > ?
                    ORDER BY 
                        ABS(volume_change_15m) + 
                        ABS(premium_change_15m) + 
                        ABS(momentum_indicator) +
                        volatility_ratio DESC
                    LIMIT 10
                """
                
                cursor.execute(query, (
                    int(time.time()) - 900,  # 15分钟内的数据
                    threshold * 100,  # 变化率阈值
                    threshold * 100,  # 价格变化阈值
                    threshold * 10,   # 动量阈值
                    threshold * 2     # 波动率比率阈值
                ))
                
                columns = [desc[0] for desc in cursor.description]
                anomalies = [dict(zip(columns, row)) for row in cursor.fetchall()]
                
                return anomalies
                
        except Exception as e:
            logger.error(f"获取异常合约失败: {str(e)}")
            return [] 

    def optimize_database(self) -> bool:
        """优化数据库"""
        try:
            with self.lock, sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # 重建索引
                cursor.execute("REINDEX")
                
                # 整理数据库
                cursor.execute("VACUUM")
                
                # 分析表
                cursor.execute("ANALYZE")
                
                conn.commit()
                logger.info("数据库优化完成")
                return True
                
        except Exception as e:
            logger.error(f"数据库优化失败: {str(e)}")
            return False 