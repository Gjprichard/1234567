import sqlite3
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import os
from dotenv import load_dotenv
import time
import random

# 加载环境变量
load_dotenv()

logger = logging.getLogger(__name__)

class OptionDatabase:
    def __init__(self, db_path: str = None):
        # 优先使用传入的db_path，其次使用环境变量，最后使用默认值
        self.db_path = db_path or os.getenv('OPTION_DB_PATH', 'option_data.db')
        logger.info(f"使用期权数据库: {self.db_path}")
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

    def initialize_test_data(self):
        """初始化测试数据"""
        try:
            logger.info("开始初始化测试数据...")
            
            # 检查是否已有数据
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT COUNT(*) FROM option_contracts")
                contract_count = cursor.fetchone()[0]
                
                if contract_count > 0:
                    logger.info(f"数据库中已有 {contract_count} 个合约，跳过初始化")
                    return True
            
            # 生成测试数据
            symbols = ['BTC', 'ETH']
            current_time = int(time.time() * 1000)  # 当前时间戳（毫秒）
            
            # 生成未来1-7天的到期日
            expiry_days = [1, 3, 7]
            expiry_times = []
            for days in expiry_days:
                expiry_time = current_time + (days * 24 * 60 * 60 * 1000)
                expiry_times.append(expiry_time)
            
            # 生成合约数据
            contracts = []
            tickers = []
            
            for symbol in symbols:
                # 获取模拟的现货价格
                spot_price = 30000 if symbol == 'BTC' else 2000
                
                # 生成不同执行价的期权
                for expiry_time in expiry_times:
                    # 生成执行价（现货价格的80%-120%范围内）
                    strikes = [
                        round(spot_price * 0.8, 2),
                        round(spot_price * 0.9, 2),
                        round(spot_price, 2),
                        round(spot_price * 1.1, 2),
                        round(spot_price * 1.2, 2)
                    ]
                    
                    for strike in strikes:
                        # 生成看涨期权
                        call_id = f"{symbol}-{strike}-C-{expiry_time}"
                        contracts.append({
                            'instId': call_id,
                            'symbol': symbol,
                            'strike': strike,
                            'expTime': expiry_time,
                            'optType': 'C',
                            'state': 'live'
                        })
                        
                        # 生成看跌期权
                        put_id = f"{symbol}-{strike}-P-{expiry_time}"
                        contracts.append({
                            'instId': put_id,
                            'symbol': symbol,
                            'strike': strike,
                            'expTime': expiry_time,
                            'optType': 'P',
                            'state': 'live'
                        })
                        
                        # 生成行情数据
                        for contract_id in [call_id, put_id]:
                            # 随机生成价格和成交量
                            last_price = round(random.uniform(10, 1000), 2)
                            vol24h = round(random.uniform(1000, 10000), 2)
                            volume_15m = round(random.uniform(100, 1000), 2)
                            
                            tickers.append({
                                'instId': contract_id,
                                'last': last_price,
                                'vol24h': vol24h,
                                'volume_15m': volume_15m,
                                'ts': current_time
                            })
            
            # 保存数据到数据库
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                # 保存合约数据
                for contract in contracts:
                    cursor.execute('''
                        INSERT INTO option_contracts 
                        (instId, symbol, strike, expTime, optType, state)
                        VALUES (?, ?, ?, ?, ?, ?)
                    ''', (
                        contract['instId'],
                        contract['symbol'],
                        contract['strike'],
                        contract['expTime'],
                        contract['optType'],
                        contract['state']
                    ))
                
                # 保存行情数据
                for ticker in tickers:
                    cursor.execute('''
                        INSERT INTO option_tickers
                        (instId, last, vol24h, volume_15m, ts)
                        VALUES (?, ?, ?, ?, ?)
                    ''', (
                        ticker['instId'],
                        ticker['last'],
                        ticker['vol24h'],
                        ticker['volume_15m'],
                        ticker['ts']
                    ))
                
                conn.commit()
                logger.info(f"成功初始化 {len(contracts)} 个合约和 {len(tickers)} 条行情数据")
                return True
                
        except Exception as e:
            logger.error(f"初始化测试数据失败: {str(e)}")
            return False

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