import ccxt
import pandas as pd
import streamlit as st
from datetime import datetime, timedelta
import logging
from typing import Dict, List, Optional, Tuple
from base_monitor import BaseMonitor
import os
import requests
import hmac
import base64
import time
import random
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from database import Database
import numpy as np
from dotenv import load_dotenv
from logger_config import setup_logger
from option_database import OptionDatabase
import threading
import json
import statistics

# 创建期权监控日志记录器
logger = setup_logger('option_monitor')

class MultiExchangeMonitor:
    """多交易所数据源管理器"""
    def __init__(self):
        self.logger = logger
        self.exchanges = {}
        self.exchange_weights = {}
        self.last_request_time = {}
        self.min_request_interval = float(os.getenv('MIN_REQUEST_INTERVAL', '2.0'))  # 从环境变量读取
        self.current_exchange_index = 0
        self.exchange_status = {}
        
        # 初始化交易所列表 - 至少5家主流交易所
        self.exchange_list = [
            {'id': 'binance', 'name': 'Binance', 'weight': float(os.getenv('BINANCE_WEIGHT', '1.0'))},
            {'id': 'okx', 'name': 'OKX', 'weight': float(os.getenv('OKX_WEIGHT', '1.0'))},
            {'id': 'bybit', 'name': 'Bybit', 'weight': float(os.getenv('BYBIT_WEIGHT', '1.0'))},
            {'id': 'kucoin', 'name': 'KuCoin', 'weight': float(os.getenv('KUCOIN_WEIGHT', '0.8'))},
            {'id': 'gate', 'name': 'Gate.io', 'weight': float(os.getenv('GATE_WEIGHT', '0.8'))},
            {'id': 'huobi', 'name': 'Huobi', 'weight': float(os.getenv('HUOBI_WEIGHT', '0.8'))},
            {'id': 'bitget', 'name': 'Bitget', 'weight': float(os.getenv('BITGET_WEIGHT', '0.7'))},
            {'id': 'mexc', 'name': 'MEXC', 'weight': float(os.getenv('MEXC_WEIGHT', '0.7'))}
        ]
        
        # 初始化交易所连接
        self._initialize_exchanges()
    
    def _initialize_exchanges(self):
        """初始化所有交易所连接"""
        for exchange_info in self.exchange_list:
            try:
                exchange_id = exchange_info['id']
                exchange_class = getattr(ccxt, exchange_id)
                self.exchanges[exchange_id] = exchange_class({
                    'enableRateLimit': True,
                    'timeout': int(os.getenv('REQUEST_TIMEOUT', '30000')),
                    'options': {
                        'adjustForTimeDifference': True
                    }
                })
                self.exchange_weights[exchange_id] = exchange_info['weight']
                self.exchange_status[exchange_id] = {
                    'status': 'ok',
                    'last_error': None,
                    'error_count': 0,
                    'last_success': time.time()
                }
                self.logger.info(f"已初始化交易所: {exchange_info['name']} (权重: {exchange_info['weight']})")
            except Exception as e:
                self.logger.error(f"初始化交易所 {exchange_info['name']} 失败: {str(e)}")
    
    def _check_rate_limit(self, exchange_id: str) -> bool:
        """检查是否可以发送请求"""
        current_time = time.time()
        if exchange_id in self.last_request_time:
            time_passed = current_time - self.last_request_time[exchange_id]
            if time_passed < self.min_request_interval:
                time.sleep(self.min_request_interval - time_passed)
        
        self.last_request_time[exchange_id] = time.time()
        return True
    
    def get_next_exchange(self) -> str:
        """获取下一个可用的交易所ID（轮换策略）"""
        # 过滤出状态正常的交易所
        available_exchanges = [
            exchange_id for exchange_id, status in self.exchange_status.items()
            if status['status'] == 'ok' or (
                status['status'] == 'error' and 
                time.time() - status['last_error'] > 300  # 5分钟后重试
            )
        ]
        
        if not available_exchanges:
            self.logger.warning("没有可用的交易所，重置所有交易所状态")
            for exchange_id in self.exchange_status:
                self.exchange_status[exchange_id]['status'] = 'ok'
            available_exchanges = list(self.exchanges.keys())
        
        # 轮换策略
        self.current_exchange_index = (self.current_exchange_index + 1) % len(available_exchanges)
        return available_exchanges[self.current_exchange_index]
    
    def get_spot_price(self, symbol: str) -> float:
        """从多个交易所获取现货价格，并计算加权平均值"""
        prices = []
        weights = []
        
        for exchange_id, exchange in self.exchanges.items():
            try:
                if self.exchange_status[exchange_id]['status'] == 'error' and \
                   time.time() - self.exchange_status[exchange_id]['last_error'] < 300:
                    continue
                
                self._check_rate_limit(exchange_id)
                
                # 根据交易所调整交易对格式
                if exchange_id in ['binance', 'kucoin', 'huobi', 'gate', 'mexc']:
                    market_symbol = f"{symbol}/USDT"
                else:
                    market_symbol = f"{symbol}/USDT"
                
                ticker = exchange.fetch_ticker(market_symbol)
                if ticker and 'last' in ticker and ticker['last']:
                    prices.append(ticker['last'])
                    weights.append(self.exchange_weights[exchange_id])
                    
                    # 更新交易所状态
                    self.exchange_status[exchange_id]['status'] = 'ok'
                    self.exchange_status[exchange_id]['last_success'] = time.time()
                    self.exchange_status[exchange_id]['error_count'] = 0
                    
                    self.logger.debug(f"从 {exchange_id} 获取 {symbol} 价格: {ticker['last']}")
            except Exception as e:
                # 更新交易所错误状态
                self.exchange_status[exchange_id]['status'] = 'error'
                self.exchange_status[exchange_id]['last_error'] = time.time()
                self.exchange_status[exchange_id]['error_count'] += 1
                self.logger.warning(f"从 {exchange_id} 获取 {symbol} 价格失败: {str(e)}")
        
        if not prices:
            self.logger.error(f"无法从任何交易所获取 {symbol} 价格")
            return 0.0
        
        # 计算加权平均价格
        if len(prices) == 1:
            return prices[0]
        
        # 移除异常值（可选）
        if len(prices) >= 4:
            # 计算价格的标准差
            std_dev = statistics.stdev(prices)
            mean_price = statistics.mean(prices)
            
            # 过滤掉偏离均值超过2个标准差的价格
            filtered_prices = []
            filtered_weights = []
            for i, price in enumerate(prices):
                if abs(price - mean_price) <= 2 * std_dev:
                    filtered_prices.append(price)
                    filtered_weights.append(weights[i])
            
            if filtered_prices:
                prices = filtered_prices
                weights = filtered_weights
        
        # 计算加权平均价格
        weighted_price = sum(p * w for p, w in zip(prices, weights)) / sum(weights)
        self.logger.info(f"{symbol} 加权平均价格: {weighted_price:.2f} (来自 {len(prices)} 个交易所)")
        
        return weighted_price
    
    def get_klines(self, symbol: str, timeframe: str = '5m', limit: int = 100) -> pd.DataFrame:
        """从多个交易所获取K线数据，并选择数据最完整的一个"""
        best_klines = None
        best_exchange = None
        max_length = 0
        
        for exchange_id, exchange in self.exchanges.items():
            try:
                if self.exchange_status[exchange_id]['status'] == 'error' and \
                   time.time() - self.exchange_status[exchange_id]['last_error'] < 300:
                    continue
                
                self._check_rate_limit(exchange_id)
                
                # 根据交易所调整交易对格式
                if exchange_id in ['binance', 'kucoin', 'huobi', 'gate', 'mexc']:
                    market_symbol = f"{symbol}/USDT"
                else:
                    market_symbol = f"{symbol}/USDT"
                
                # 检查交易所是否支持该交易对
                markets = exchange.load_markets()
                if market_symbol not in markets:
                    continue
                
                # 获取K线数据
                ohlcv = exchange.fetch_ohlcv(market_symbol, timeframe, limit=limit)
                
                if len(ohlcv) > max_length:
                    max_length = len(ohlcv)
                    best_klines = ohlcv
                    best_exchange = exchange_id
                
                # 更新交易所状态
                self.exchange_status[exchange_id]['status'] = 'ok'
                self.exchange_status[exchange_id]['last_success'] = time.time()
                self.exchange_status[exchange_id]['error_count'] = 0
                
            except Exception as e:
                # 更新交易所错误状态
                self.exchange_status[exchange_id]['status'] = 'error'
                self.exchange_status[exchange_id]['last_error'] = time.time()
                self.exchange_status[exchange_id]['error_count'] += 1
                self.logger.warning(f"从 {exchange_id} 获取 {symbol} K线数据失败: {str(e)}")
        
        if best_klines is None:
            self.logger.error(f"无法从任何交易所获取 {symbol} K线数据")
            return pd.DataFrame()
        
        # 转换为DataFrame
        df = pd.DataFrame(best_klines, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
        
        self.logger.info(f"成功从 {best_exchange} 获取 {symbol} K线数据 ({len(df)} 条)")
        return df
    
    def get_exchange_status(self) -> Dict:
        """获取所有交易所的状态信息"""
        status = {}
        for exchange_id, exchange_status in self.exchange_status.items():
            status[exchange_id] = {
                'name': next((e['name'] for e in self.exchange_list if e['id'] == exchange_id), exchange_id),
                'status': exchange_status['status'],
                'error_count': exchange_status['error_count'],
                'last_success': datetime.fromtimestamp(exchange_status['last_success']).strftime('%Y-%m-%d %H:%M:%S') if exchange_status['last_success'] else None,
                'last_error': datetime.fromtimestamp(exchange_status['last_error']).strftime('%Y-%m-%d %H:%M:%S') if exchange_status['last_error'] else None
            }
        return status

class OKXOptionMonitor(BaseMonitor):
    def __init__(self):
        super().__init__()
        self.logger = logger
        try:
            load_dotenv()
            # 使用 OKX API 配置
            self.base_url = os.getenv('REST_API_URL', 'https://www.okx.com')
            self.api_key = os.getenv('API_KEY', '')
            self.api_secret = os.getenv('API_SECRET', '')
            self.passphrase = os.getenv('API_PASSPHRASE', '')
            
            # 配置请求会话
            self.session = requests.Session()
            
            # 配置重试策略
            retry_strategy = Retry(
                total=5,  # 最大重试次数
                backoff_factor=0.5,  # 重试延迟因子
                status_forcelist=[429, 500, 502, 503, 504],
                method_whitelist=["GET", "POST"],
                respect_retry_after_header=True
            )
            
            # 配置连接池
            adapter = HTTPAdapter(
                max_retries=retry_strategy,
                pool_connections=100,  # 连接池大小
                pool_maxsize=100,
                pool_block=True
            )
            
            self.session.mount("http://", adapter)
            self.session.mount("https://", adapter)
            
            # 添加请求限制
            self.request_limit = 20  # 每秒最大请求数
            self.request_window = 1.0  # 时间窗口（秒）
            self.request_timestamps = []
            self.request_delay = 0.05  # 请求间隔（秒）
            
            # 添加错误处理
            self.max_retries = 3
            self.retry_delay = 1
            self.error_threshold = 10
            self.error_count = 0
            self.error_reset_time = 300  # 5分钟后重置错误计数
            self.last_error_time = time.time()
            
            # 修改为基础标的格式
            self.symbols = ['BTC', 'ETH']  # 使用基础标的
            self.volume_threshold = 2.0
            self.volume_history = {}
            
            # 添加性能监控
            self.request_times = []
            self.max_request_times = 100
            
            # 初始化期权数据库
            self.db = OptionDatabase()
            
            # 添加错误去重和日志控制
            self.error_cache = {}          # 错误缓存
            self.last_log_time = {}        # 日志时间记录
            self.log_interval = 300        # 基本日志间隔（5分钟）
            self.error_log_interval = 60   # 错误日志间隔（1分钟）
            self.max_error_cache = 1000    # 最大错误缓存数
            
            # 初始化多交易所数据源
            self.multi_exchange = MultiExchangeMonitor()
            
            # 定期清理日志缓存
            self._start_log_cleanup()
            
            # 启动数据更新任务
            self.start_update_task()
            
            # 启动数据同步任务
            self.start_sync_task()
            
        except Exception as e:
            logger.error(f"初始化期权监控失败: {str(e)}")
            self.session = None

    def _start_log_cleanup(self):
        """启动日志缓存清理任务"""
        def cleanup_task():
            while True:
                try:
                    time.sleep(3600)  # 每小时清理一次
                    current_time = time.time()
                    
                    # 清理错误缓存
                    self.error_cache = {
                        k: v for k, v in self.error_cache.items()
                        if current_time - v['time'] < 86400  # 保留24小时内的错误
                    }
                    
                    # 清理日志时间记录
                    self.last_log_time = {
                        k: v for k, v in self.last_log_time.items()
                        if current_time - v['time'] < 3600  # 保留1小时内的记录
                    }
                    
                    self.logger.info("完成日志缓存清理")
                    
                except Exception as e:
                    self.logger.error(f"日志清理任务失败: {str(e)}")
        
        cleanup_thread = threading.Thread(target=cleanup_task)
        cleanup_thread.daemon = True
        cleanup_thread.start()

    def _get_timestamp(self):
        """获取ISO格式时间戳"""
        return datetime.utcnow().isoformat()[:-3] + 'Z'

    def _sign(self, message: str) -> str:
        """生成签名"""
        mac = hmac.new(
            bytes(self.api_secret, encoding='utf8'),
            bytes(message, encoding='utf-8'),
            digestmod='sha256'
        )
        return base64.b64encode(mac.digest()).decode()

    def log_error(self, error_key: str, error_msg: str):
        """记录错误日志（带去重和限流）"""
        current_time = time.time()
        
        # 检查是否是重复错误
        if error_key in self.error_cache:
            last_error = self.error_cache[error_key]
            # 如果错误消息相同且在时间间隔内，只更新计数
            if last_error['msg'] == error_msg and \
               current_time - last_error['time'] < self.log_interval:
                last_error['count'] += 1
                return
        
        # 更新错误缓存
        self.error_cache[error_key] = {
            'msg': error_msg,
            'time': current_time,
            'count': 1
        }
        
        # 记录日志
        self.logger.error(f"{error_msg} (错误ID: {error_key})")

    def log_info(self, log_key: str, message: str):
        """记录信息日志（带频率控制和计数）"""
        current_time = time.time()
        
        # 检查是否在时间间隔内
        if log_key in self.last_log_time:
            last_time = self.last_log_time[log_key]
            if current_time - last_time['time'] < self.log_interval:
                last_time['count'] += 1
                return
            else:
                # 如果超过时间间隔，记录之前的统计
                if last_time['count'] > 1:
                    self.logger.info(
                        f"上一时段 {log_key} 共发生 {last_time['count']} 次"
                    )
        
        # 更新最后记录时间
        self.last_log_time[log_key] = {
            'time': current_time,
            'count': 1
        }
        
        # 记录日志
        self.logger.info(message)

    def log_debug(self, message: str):
        """记录调试日志（只在调试模式下记录）"""
        if self.logger.isEnabledFor(logging.DEBUG):
            self.logger.debug(message)

    def _request(self, method: str, endpoint: str, params: Dict = None) -> Optional[Dict]:
        """发送API请求"""
        try:
            url = f"{self.base_url}{endpoint}"
            
            # 使用频率控制的日志
            self.log_info('api_request', f"发送请求: {method} {url}")
            
            # 添加时间戳和签名
            timestamp = self._get_timestamp()
            if method == 'GET':
                if params:
                    param_str = '&'.join([f"{k}={v}" for k, v in sorted(params.items())])
                    path = f"{endpoint}?{param_str}"
                else:
                    path = endpoint
            else:
                path = endpoint
            
            message = timestamp + method + path
            if method != 'GET' and params:
                message += str(params)
            
            signature = self._sign(message)
            
            headers = {
                'OK-ACCESS-KEY': self.api_key,
                'OK-ACCESS-SIGN': signature,
                'OK-ACCESS-TIMESTAMP': timestamp,
                'OK-ACCESS-PASSPHRASE': self.passphrase,
                'Content-Type': 'application/json'
            }
            
            # 增强的重试逻辑，使用指数退避算法
            max_retries = int(os.getenv('MAX_RETRIES', '3'))
            base_delay = 2.0  # 基础延迟时间（秒）
            
            for attempt in range(max_retries):
                try:
                    response = self.session.request(
                        method,
                        url,
                        params=params if method == 'GET' else None,
                        json=params if method != 'GET' else None,
                        headers=headers,
                        timeout=10
                    )
                    
                    # 请求成功
                    if response.status_code == 200:
                        data = response.json()
                        if data.get('code') == '0':
                            return data
                        else:
                            self.log_error('api_error', f"API错误: {data}")
                    
                    # 请求限制 - 使用指数退避算法
                    elif response.status_code == 429:
                        # 计算指数退避时间: 2^attempt * base_delay + 随机抖动
                        wait_time = (2 ** attempt) * base_delay + random.uniform(0, 1)
                        self.log_error('rate_limit', f"请求频率超限，等待 {wait_time:.2f} 秒 (尝试 {attempt+1}/{max_retries})")
                        time.sleep(wait_time)
                        continue
                    
                    # 其他错误
                    else:
                        self.log_error('http_error', 
                                     f"HTTP错误 {response.status_code}: {response.text}")
                    
                    # 重试延迟 - 也使用指数退避
                    if attempt < max_retries - 1:
                        retry_delay = (2 ** attempt) * base_delay
                        time.sleep(retry_delay)
                    
                except Exception as e:
                    self.log_error('request_error', f"请求异常: {str(e)} (尝试 {attempt+1}/{max_retries})")
                    if attempt < max_retries - 1:
                        retry_delay = (2 ** attempt) * base_delay
                        time.sleep(retry_delay)
                    else:
                        raise
            
            return None
            
        except Exception as e:
            self.log_error('api_request', f"请求失败: {str(e)}")
            return None

    def save_option_data(self, instruments: List[Dict], tickers: List[Dict]):
        """保存期权数据到数据库"""
        try:
            self.log_info('save_data', 
                          f"开始保存期权数据: {len(instruments)} 个合约, {len(tickers)} 个行情")
            
            # 批量处理大小
            batch_size = 100
            max_retries = 3
            
            with self.db.get_connection() as conn:
                cursor = conn.cursor()
                
                try:
                    # 开始事务
                    cursor.execute('BEGIN TRANSACTION')
                    
                    # 分批处理合约数据
                    for i in range(0, len(instruments), batch_size):
                        batch = instruments[i:i + batch_size]
                        contract_data = []
                        
                        for inst in batch:
                            try:
                                contract_data.append(self._prepare_contract_data(inst))
                            except Exception as e:
                                self.log_error(f'contract_{inst.get("instId")}',
                                             f"处理合约数据失败: {str(e)}")
                                continue
                        
                        if contract_data:
                            self._execute_with_retry(
                                cursor, 
                                self._get_contract_sql(), 
                                contract_data,
                                max_retries
                            )
                    
                    # 分批处理行情数据
                    for i in range(0, len(tickers), batch_size):
                        batch = tickers[i:i + batch_size]
                        ticker_data = []
                        
                        for ticker in batch:
                            try:
                                ticker_data.append(self._prepare_ticker_data(ticker))
                            except Exception as e:
                                self.log_error(f'ticker_{ticker.get("instId")}',
                                             f"处理行情数据失败: {str(e)}")
                                continue
                        
                        if ticker_data:
                            self._execute_with_retry(
                                cursor, 
                                self._get_ticker_sql(), 
                                ticker_data,
                                max_retries
                            )
                    
                    conn.commit()
                    return True
                    
                except Exception as e:
                    conn.rollback()
                    self.log_error('save_data', f"保存数据失败: {str(e)}")
                    return False
                
        except Exception as e:
            self.log_error('save_data', f"保存期权数据失败: {str(e)}")
            return False

    def _execute_with_retry(self, cursor, sql: str, data: List[Tuple], max_retries: int):
        """执行SQL语句（带重试）"""
        for attempt in range(max_retries):
            try:
                cursor.executemany(sql, data)
                break
            except Exception as e:
                if attempt == max_retries - 1:
                    raise
                time.sleep(0.5 * (attempt + 1))

    def _get_contract_sql(self) -> str:
        """获取合约SQL语句"""
        return """
            INSERT OR REPLACE INTO option_contracts (
                instId, symbol, strike, expTime, optType, state
            ) VALUES (?, ?, ?, ?, ?, ?)
        """

    def _get_ticker_sql(self) -> str:
        """获取行情SQL语句"""
        return """
            INSERT OR REPLACE INTO option_tickers (
                instId, last, vol24h, volume_15m, ts
            ) VALUES (?, ?, ?, ?, ?)
        """

    def _prepare_contract_data(self, inst: Dict) -> Tuple:
        """准备合约数据"""
        instId = inst['instId']
        symbol = inst['uly'].split('-')[0]
        strike = float(inst.get('stk', '0')) if inst.get('stk') else 0.0
        expiry = int(inst.get('expTime', '0')) if inst.get('expTime') else 0
        
        return (
            instId,
            symbol,
            strike,
            expiry,
            inst.get('optType', ''),
            inst.get('state', '')
        )

    def _prepare_ticker_data(self, ticker: Dict) -> Tuple:
        """准备行情数据"""
        instId = ticker['instId']
        last = float(ticker.get('last', '0')) if ticker.get('last') else 0.0
        vol24h = float(ticker.get('vol24h', '0')) if ticker.get('vol24h') else 0.0
        volume_15m = float(ticker.get('volume_15m', '0')) if ticker.get('volume_15m') else 0.0
        ts = int(ticker.get('ts', '0')) if ticker.get('ts') else 0
        
        return (instId, last, vol24h, volume_15m, ts)

    def clean_expired_data(self):
        """清理过期数据"""
        try:
            self.log_info('clean_data', "开始清理过期数据...")
            
            with self.db.get_connection() as conn:
                cursor = conn.cursor()
                
                # 删除4小时前的数据
                cursor.execute('''
                    DELETE FROM option_tickers 
                    WHERE created_at < datetime('now', '-4 hours')
                ''')
                
                cursor.execute('''
                    DELETE FROM option_contracts 
                    WHERE created_at < datetime('now', '-4 hours')
                ''')
                
                conn.commit()
                self.logger.info("清理过期数据完成")
                
        except Exception as e:
            self.log_error('clean_data', f"清理过期数据失败: {str(e)}")

    def update_option_data(self):
        """更新期权数据"""
        try:
            self.log_info('update_data', "开始更新期权市场数据...")
            start_time = time.time()
            
            # 清理过期数据
            self.clean_expired_data()
            
            # 获取所有期权合约数据
            all_contracts = []
            all_tickers = []
            
            for symbol in self.symbols:
                self.logger.info(f"获取 {symbol} 期权合约列表...")
                
                # 获取期权合约列表
                contracts = self._get_option_contracts(symbol)
                self.logger.info(f"获取到 {len(contracts)} 个 {symbol} 期权合约")
                
                for contract in contracts:
                    try:
                        # 获取合约详情
                        self.logger.debug(f"获取合约 {contract['instId']} 详情...")
                        details = self._get_contract_details(contract['instId'])
                        if details:
                            all_contracts.append(contract)
                            all_tickers.append(details)
                            self.logger.debug(f"成功获取合约 {contract['instId']} 数据")
                        else:
                            self.logger.warning(f"获取合约 {contract['instId']} 详情失败")
                    except Exception as e:
                        self.logger.error(f"处理合约 {contract.get('instId', 'Unknown')} 数据失败: {str(e)}")
                        continue
            
            # 保存数据
            if all_contracts and all_tickers:
                self.save_option_data(all_contracts, all_tickers)
                self.logger.info(f"成功更新 {len(all_contracts)} 个合约数据")
            else:
                self.logger.warning("没有获取到任何期权数据")
            
            elapsed_time = time.time() - start_time
            self.logger.info(f"期权数据更新完成，耗时: {elapsed_time:.3f}秒")
            
            return True
            
        except Exception as e:
            self.log_error('update_data', f"更新期权数据失败: {str(e)}")
            return False

    def get_option_data(self, days_limit=3, price_deviation=0.15) -> pd.DataFrame:
        """
        获取期权市场数据
        
        参数:
            days_limit: 获取几天内到期的期权，默认3天
            price_deviation: 执行价偏离市场价的百分比限制，默认15%
        """
        try:
            self.logger.info(f"开始获取期权市场数据 (days_limit={days_limit}, price_deviation={price_deviation*100}%)...")
            
            # 验证数据
            if not self.verify_data():
                self.logger.warning("数据验证失败，尝试更新数据")
                if not self.update_option_data():
                    self.logger.error("无法获取期权数据，请检查API连接或网络状态")
                    return pd.DataFrame()
            
            # 获取当前市场价格
            spot_prices = {}
            for symbol in self.symbols:
                try:
                    spot_prices[symbol] = self.get_spot_price(symbol)
                    self.logger.info(f"获取到 {symbol} 现货价格: {spot_prices[symbol]}")
                except Exception as e:
                    self.logger.error(f"获取 {symbol} 现货价格失败: {str(e)}")
                    spot_prices[symbol] = 0
            
            # 获取数据
            with self.db.get_connection() as conn:
                df = pd.read_sql('''
                    SELECT 
                        c.symbol,
                        c.instId as contract,
                        c.optType as type,
                        c.strike,
                        c.expTime as expiry,
                        t.last,
                        t.volume_15m,
                        t.ts as timestamp
                    FROM option_contracts c
                    JOIN option_tickers t ON c.instId = t.instId
                    WHERE c.state = 'live'
                    AND t.created_at >= datetime('now', '-15 minutes')
                ''', conn)
            
            if df.empty:
                self.logger.warning("没有获取到任何期权数据")
                return pd.DataFrame()
            
            # 数据处理
            df['expiry_date'] = pd.to_datetime(df['expiry'], unit='ms')
            df['days_to_expiry'] = (df['expiry_date'] - pd.Timestamp.now()).dt.days
            df['type'] = df['type'].map({'C': 'CALL', 'P': 'PUT'})
            
            # 筛选近几天到期的期权
            df = df[df['days_to_expiry'] <= days_limit]
            
            # 筛选执行价偏离市场价一定范围内的期权
            filtered_df = pd.DataFrame()
            for symbol in spot_prices:
                if spot_prices[symbol] <= 0:
                    continue
                    
                symbol_df = df[df['symbol'] == symbol].copy()
                if symbol_df.empty:
                    continue
                    
                # 计算执行价与市场价的偏离度
                symbol_df['market_price'] = spot_prices[symbol]
                symbol_df['price_deviation'] = abs(symbol_df['strike'] - symbol_df['market_price']) / symbol_df['market_price']
                
                # 筛选偏离度在限制范围内的期权
                symbol_df = symbol_df[symbol_df['price_deviation'] <= price_deviation]
                filtered_df = pd.concat([filtered_df, symbol_df])
            
            if filtered_df.empty:
                self.logger.warning(f"筛选后没有符合条件的期权数据 (days_limit={days_limit}, price_deviation={price_deviation*100}%)")
                return pd.DataFrame()
            
            return filtered_df
            
        except Exception as e:
            self.logger.error(f"获取期权数据失败: {str(e)}")
            return pd.DataFrame()

    def detect_abnormal_volume(self, df: pd.DataFrame) -> List[Dict]:
        """检测异常成交量"""
        alerts = []
        
        try:
            for symbol in self.symbols:
                symbol_data = df[df['symbol'] == symbol]
                if symbol_data.empty:
                    continue
                    
                # 计算成交量统计
                mean_volume = symbol_data['volume_15m'].mean()
                std_volume = symbol_data['volume_15m'].std()
                
                # 检测异常值
                abnormal = symbol_data[
                    symbol_data['volume_15m'] > (mean_volume + self.volume_threshold * std_volume)
                ]
                
                for _, row in abnormal.iterrows():
                    alerts.append({
                        'symbol': symbol,
                        'contract': row['contract'],
                        'type': row['type'],
                        'strike': row['strike'],
                        'expiry': row['expiry'],
                        'volume': row['volume_15m'],
                        'volume_change': row['volume_15m'],
                        'severity': self._get_severity(row['volume_15m'], mean_volume, std_volume),
                        'time': datetime.fromtimestamp(row['timestamp']/1000).strftime('%Y-%m-%d %H:%M:%S')
                    })
            
            return alerts
            
        except Exception as e:
            self.logger.error(f"检测异常成交量失败: {str(e)}")
            return []

    def get_historical_data(self, contract: str) -> Tuple[pd.DataFrame, Dict]:
        """获取历史数据"""
        try:
            if not self.session:
                return [], None, 0, 0

            # 获取K线数据
            ohlcv = self.session.request(
                'GET',
                f"/api/v5/market/candles",
                params={
                    'instId': contract,
                    'bar': '1m',
                    'limit': '90'
                }
            )

            if not ohlcv or 'data' not in ohlcv:
                return [], None, 0, 0

            df = pd.DataFrame(ohlcv['data'], columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
            
            # 获取当前和历史数据
            latest_price = float(df['close'].iloc[-1])
            latest_volume = float(df['volume'].iloc[-1])
            
            if len(df) >= 30:
                # 计算15分钟周期的数据
                current_period = df.iloc[-15:]
                previous_period = df.iloc[-30:-15]
                
                # 计算当前周期的变化
                current_price_change = ((latest_price - float(current_period['close'].iloc[0])) 
                                     / float(current_period['close'].iloc[0])) * 100
                current_volume = current_period['volume'].sum()
                
                # 计算上一个周期的变化
                previous_price_change = ((float(current_period['close'].iloc[0]) - float(previous_period['close'].iloc[0]))
                                      / float(previous_period['close'].iloc[0])) * 100
                previous_volume = previous_period['volume'].sum()
                
                # 计算变化率的差值
                price_change_diff = current_price_change - previous_price_change
                volume_change_diff = ((current_volume - previous_volume) / previous_volume) * 100
            else:
                price_change_diff = 0
                volume_change_diff = 0

            return df['close'].tolist(), latest_volume, price_change_diff, volume_change_diff

        except Exception as e:
            st.error(f"Error fetching historical data for {contract}: {str(e)}")
            return [], None, 0, 0

    def generate_alerts(self, coin_data, price_threshold=0.1, volume_threshold=0.5):
        """生成警报"""
        if coin_data.empty:
            return []

        alerts = []
        for _, coin in coin_data.iterrows():
            try:
                prices, latest_volume, price_change_diff, volume_change_diff = self.get_historical_data(coin['contract'])
                if not prices:
                    continue

                if abs(price_change_diff) > price_threshold or abs(volume_change_diff) > volume_threshold:
                    alerts.append({
                        'coin': coin['contract'],
                        'symbol': coin['symbol'],
                        'current_price': prices[-1],
                        'price_change': price_change_diff,
                        'current_volume': latest_volume,
                        'volume_change': volume_change_diff
                    })
            except Exception as e:
                st.warning(f"Error processing alert data for {coin['contract']}: {str(e)}")
                continue

        return sorted(alerts, key=lambda x: abs(x['price_change']), reverse=True)

    def update_market_data(self) -> bool:
        """更新市场数据"""
        try:
            logger.info("开始更新期权市场数据...")
            success = False
            
            # 批量获取所有币种的现货价格
            spot_prices = {}
            endpoint = '/api/v5/market/tickers'
            params = {'instType': 'SPOT'}
            spot_response = self._request('GET', endpoint, params)
            
            if spot_response and 'data' in spot_response:
                for ticker in spot_response['data']:
                    if ticker['instId'].endswith('-USDT'):
                        symbol = ticker['instId'].split('-')[0]
                        if symbol in self.symbols:
                            spot_prices[symbol] = float(ticker['last'])
            
            if not spot_prices:
                logger.error("获取现货价格失败")
                return False
            
            # 批量获取所有期权合约
            all_instruments = []
            for symbol in self.symbols:
                endpoint = '/api/v5/public/instruments'
                params = {
                    'instType': 'OPTION',
                    'uly': f'{symbol}-USD',
                    'state': 'live'
                }
                
                response = self._request('GET', endpoint, params)
                if response and 'data' in response:
                    current_price = spot_prices[symbol]
                    # 筛选执行价格在当前市场价正负15%以内的合约
                    price_range = (current_price * 0.85, current_price * 1.15)
                    
                    # 筛选合约 - 只保留近三天的合约
                    now = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
                    expiry_threshold = now + timedelta(days=3)
                    
                    filtered_instruments = []
                    for inst in response['data']:
                        try:
                            expiry_ts = int(inst['expTime']) / 1000
                            expiry_date = datetime.fromtimestamp(expiry_ts)
                            strike = float(inst['stk'])
                            
                            if (now <= expiry_date < expiry_threshold and 
                                price_range[0] <= strike <= price_range[1]):
                                filtered_instruments.append(inst)
                        except Exception as e:
                            logger.error(f"处理合约数据失败: {inst.get('instId', 'Unknown')} - {str(e)}")
                            continue
                    
                    logger.info(f"筛选出 {len(filtered_instruments)}/{len(response['data'])} 个符合条件的{symbol}合约")
                    all_instruments.extend(filtered_instruments)
            
            if not all_instruments:
                logger.warning("没有找到符合条件的合约")
                return False
            
            logger.info(f"共筛选出 {len(all_instruments)} 个符合条件的合约")
            
            # 批量获取K线数据 - 使用更大的批次，减少请求次数
            inst_candles = {}
            endpoint = '/api/v5/market/history-candles-batch'
            batch_size = 20  # OKX API限制每次最多20个合约
            
            for i in range(0, len(all_instruments), batch_size):
                batch = all_instruments[i:i+batch_size]
                inst_ids = [inst['instId'] for inst in batch]
                
                params = {
                    'instIds': ','.join(inst_ids),
                    'bar': '1H',
                    'limit': '24'
                }
                
                logger.info(f"获取K线数据批次 {i//batch_size + 1}/{(len(all_instruments) + batch_size - 1)//batch_size}, 包含 {len(inst_ids)} 个合约")
                candles_response = self._request('GET', endpoint, params)
                if candles_response and 'data' in candles_response:
                    for candle_data in candles_response['data']:
                        inst_id = candle_data['instId']
                        candles = candle_data['candles']
                        if candles:
                            current_price = float(candles[0][4])
                            prev_price = float(candles[-1][4])
                            price_change = ((current_price - prev_price) / prev_price * 100 
                                          if prev_price > 0 else 0)
                            inst_candles[inst_id] = price_change
                
                # 批次之间添加延迟，避免触发频率限制
                if i + batch_size < len(all_instruments):
                    delay = 2.0 + random.uniform(0, 1)  # 添加随机抖动
                    logger.info(f"批次处理完成，等待 {delay:.2f} 秒后处理下一批次")
                    time.sleep(delay)
            
            # 更新合约数据
            for inst in all_instruments:
                inst['price_change_24h'] = inst_candles.get(inst['instId'], 0)
            
            # 批量获取行情数据 - 分批处理，避免URL过长
            all_tickers = []
            batch_size = 20  # 每批处理的合约数量
            
            for i in range(0, len(all_instruments), batch_size):
                batch = all_instruments[i:i+batch_size]
                inst_ids = [inst['instId'] for inst in batch]
                
                logger.info(f"获取行情数据批次 {i//batch_size + 1}/{(len(all_instruments) + batch_size - 1)//batch_size}, 包含 {len(inst_ids)} 个合约")
                
                endpoint = '/api/v5/market/tickers'
                params = {
                    'instType': 'OPTION',
                    'instIds': ','.join(inst_ids)
                }
                
                tickers_response = self._request('GET', endpoint, params)
                if tickers_response and 'data' in tickers_response:
                    all_tickers.extend(tickers_response['data'])
                
                # 批次之间添加延迟，避免触发频率限制
                if i + batch_size < len(all_instruments):
                    delay = 2.0 + random.uniform(0, 1)  # 添加随机抖动
                    logger.info(f"批次处理完成，等待 {delay:.2f} 秒后处理下一批次")
                    time.sleep(delay)
            
            # 筛选有成交量的合约
            valid_tickers = [t for t in all_tickers if float(t.get('vol24h', 0) or 0) > 0]
            
            if valid_tickers:
                self.save_option_data(all_instruments, valid_tickers)
                logger.info(f"保存了 {len(valid_tickers)}/{len(all_tickers)} 个有效行情数据")
                success = True
            else:
                logger.warning("没有找到有成交量的合约")
            
            return success
            
        except Exception as e:
            logger.error(f"更新期权市场数据失败: {str(e)}", exc_info=True)
            return False

    def _get_severity(self, volume: float, mean: float, std: float) -> str:
        """计算警报严重程度"""
        deviation = (volume - mean) / std
        if deviation > 3:
            return 'critical'
        elif deviation > 2:
            return 'warning'
        return 'normal'

    def get_spot_klines(self, symbol: str, interval: str = '5m', limit: int = 100) -> pd.DataFrame:
        """获取现货K线数据"""
        try:
            endpoint = '/api/v5/market/candles'
            params = {
                'instId': f'{symbol}-USDT',
                'bar': interval,
                'limit': str(limit)
            }
            
            response = self._request('GET', endpoint, params)
            if response and 'data' in response:
                # OKX API返回的数据列: [ts, open, high, low, close, vol, volCcy, volCcyQuote, confirm]
                # 转换数据
                df = pd.DataFrame(response['data'], columns=[
                    'time', 'open', 'high', 'low', 'close', 'volume', 'volCcy', 'volCcyQuote', 'confirm'
                ])
                
                # 只保留需要的列
                df = df[['time', 'open', 'high', 'low', 'close', 'volume', 'volCcy']]
                
                # 数据处理
                df['time'] = pd.to_datetime(df['time'].astype(float), unit='ms')
                for col in ['open', 'high', 'low', 'close', 'volume', 'volCcy']:
                    df[col] = pd.to_numeric(df[col], errors='coerce')
                
                return df.sort_values('time')
            
            return None
            
        except Exception as e:
            logger.error(f"获取{symbol}现货K线数据失败: {str(e)}")
            return None

    def get_spot_price(self, symbol: str) -> float:
        """获取现货价格，使用多交易所数据源"""
        try:
            # 使用多交易所数据源获取价格
            price = self.multi_exchange.get_spot_price(symbol)
            if price > 0:
                return price
                
            # 如果多交易所数据源失败，尝试使用OKX API
            self.log_info('spot_price', f"尝试从OKX获取 {symbol} 现货价格...")
            
            endpoint = "/api/v5/market/ticker"
            params = {
                'instId': f"{symbol}-USDT"
            }
            
            response = self._request('GET', endpoint, params)
            if response and 'data' in response and response['data']:
                price = float(response['data'][0]['last'])
                self.log_info('spot_price', f"从OKX获取到 {symbol} 现货价格: {price}")
                return price
            
            self.log_error('spot_price', f"无法获取 {symbol} 现货价格")
            return 0
            
        except Exception as e:
            self.log_error('spot_price', f"获取 {symbol} 现货价格失败: {str(e)}")
            return 0

    def _get_option_contracts(self, symbol: str) -> List[Dict]:
        """获取期权合约列表"""
        try:
            # 使用频率控制的日志
            self.log_info('contracts', f"请求 {symbol} 期权合约列表...")
            
            endpoint = "/api/v5/public/instruments"
            params = {
                'instType': 'OPTION',
                'uly': f'{symbol}-USD'
            }
            
            response = self._request('GET', endpoint, params)
            if response and 'data' in response:
                # 过滤出活跃的合约
                contracts = [
                    contract for contract in response['data']
                    if contract.get('state', '') == 'live'
                ]
                
                if contracts:
                    # 只记录一次日志
                    self.log_info('contracts_count', 
                                f"获取到 {len(contracts)} 个 {symbol} 期权合约")
                    
                    # 调试信息改为 debug 级别
                    if self.logger.isEnabledFor(logging.DEBUG):
                        for contract in contracts[:3]:
                            self.logger.debug(
                                f"合约示例: {contract['instId']}, "
                                f"标的: {contract.get('uly', 'Unknown')}, "
                                f"类型: {contract.get('optType', 'Unknown')}, "
                                f"执行价: {contract.get('stk', 'Unknown')}, "
                                f"到期时间: {contract.get('expTime', 'Unknown')}"
                            )
                    return contracts
                else:
                    self.log_error('contracts', f"没有找到活跃的 {symbol} 期权合约")
                    return []
            
            self.log_error('contracts', f"获取 {symbol} 期权合约列表失败: {response}")
            return []
            
        except Exception as e:
            self.log_error('contracts', f"获取期权合约列表失败 ({symbol}): {str(e)}")
            return []

    def _get_contract_details(self, contract_id: str) -> Optional[Dict]:
        """获取合约详细信息"""
        try:
            # 使用 debug 级别记录详细信息
            self.logger.debug(f"获取合约 {contract_id} 详情")
            
            endpoint = "/api/v5/market/ticker"
            params = {'instId': contract_id}
            
            response = self._request('GET', endpoint, params)
            if not response or 'data' not in response or not response['data']:
                self.log_error('contract_details', 
                              f"获取合约 {contract_id} 行情数据失败")
                return None
            
            data = response['data'][0]
            
            # 数据验证和转换
            try:
                last_price = float(data.get('last', '0')) if data.get('last') else 0.0
                vol24h = float(data.get('vol24h', '0')) if data.get('vol24h') else 0.0
                ts = int(data.get('ts', '0')) if data.get('ts') else 0
                
                # 获取15分钟成交量
                volume_15m = self._get_15min_volume(contract_id)
                
                return {
                    'instId': contract_id,
                    'last': last_price,
                    'vol24h': vol24h,
                    'volume_15m': volume_15m,
                    'ts': ts
                }
            
            except (ValueError, TypeError) as e:
                self.log_error('data_conversion', 
                              f"合约 {contract_id} 数据转换失败: {str(e)}")
                return None
            
        except Exception as e:
            self.log_error('contract_details', 
                          f"获取合约 {contract_id} 详情失败: {str(e)}")
            return None

    def _get_15min_volume(self, contract_id: str) -> float:
        """获取15分钟成交量"""
        try:
            endpoint = "/api/v5/market/history-trades"
            params = {
                'instId': contract_id,
                'limit': '100'
            }
            
            response = self._request('GET', endpoint, params)
            if not response or 'data' not in response:
                return 0.0
            
            volume_15m = 0.0
            current_time = int(time.time() * 1000)
            
            for trade in response['data']:
                try:
                    trade_time = int(trade.get('ts', '0'))
                    if current_time - trade_time <= 15 * 60 * 1000:  # 15分钟
                        volume_15m += float(trade.get('sz', '0'))
                except (ValueError, TypeError):
                    continue
                
            return volume_15m
            
        except Exception as e:
            self.log_error('volume_15m', 
                          f"获取15分钟成交量失败 ({contract_id}): {str(e)}")
            return 0.0

    def calculate_metrics(self, data: Dict) -> Dict:
        """计算期权指标"""
        try:
            metrics = {}
            for symbol, contracts in data.items():
                if not contracts:
                    continue
                    
                # 计算成交量加权平均价格
                total_volume = sum(c['volume'] for c in contracts)
                vwap = sum(c['last_price'] * c['volume'] for c in contracts) / total_volume
                
                # 计算隐含波动率
                iv = self._calculate_implied_volatility(contracts)
                
                metrics[symbol] = {
                    'vwap': vwap,
                    'total_volume': total_volume,
                    'implied_volatility': iv,
                    'update_time': datetime.now().isoformat()
                }
            
            return metrics
            
        except Exception as e:
            logger.error(f"计算期权指标失败: {str(e)}")
            return {}
    
    def _calculate_implied_volatility(self, contracts: List[Dict]) -> float:
        """计算隐含波动率（简化版）"""
        try:
            # 这里使用简化的计算方法
            # 实际应用中应该使用Black-Scholes模型
            price_changes = []
            for i in range(len(contracts)-1):
                price_change = abs(contracts[i+1]['last_price'] - contracts[i]['last_price'])
                price_changes.append(price_change)
            
            if price_changes:
                return np.std(price_changes) * np.sqrt(252)  # 年化波动率
            return 0.0
            
        except Exception as e:
            logger.error(f"计算隐含波动率失败: {str(e)}")
            return 0.0

    def verify_data(self) -> bool:
        """验证数据完整性"""
        try:
            # 使用频率控制的日志
            self.log_info('verify_data', "开始验证数据...")
            
            with self.db.get_connection() as conn:
                cursor = conn.cursor()
                
                # 检查合约数据
                cursor.execute('SELECT COUNT(*) FROM option_contracts')
                contract_count = cursor.fetchone()[0]
                
                # 检查行情数据
                cursor.execute('SELECT COUNT(*) FROM option_tickers')
                ticker_count = cursor.fetchone()[0]
                
                # 检查最新数据时间
                cursor.execute('''
                    SELECT MAX(created_at) FROM option_tickers
                ''')
                last_update = cursor.fetchone()[0]
                
                self.logger.info(f"数据验证结果:")
                self.logger.info(f"- 合约数量: {contract_count}")
                self.logger.info(f"- 行情数量: {ticker_count}")
                self.logger.info(f"- 最后更新: {last_update}")
                
                # 如果没有数据，尝试更新数据
                if contract_count == 0 or ticker_count == 0:
                    self.logger.warning("数据库中没有期权数据，尝试更新数据...")
                    if self.update_option_data():
                        self.logger.info("成功更新期权数据")
                        return True
                    else:
                        self.logger.warning("无法获取期权数据，请检查API连接或网络状态")
                        return False
                
                return contract_count > 0 and ticker_count > 0
                
        except Exception as e:
            self.log_error('verify_data', f"数据验证失败: {str(e)}")
            return False

    def start_update_task(self):
        """启动定时更新任务"""
        def update_task():
            while True:
                try:
                    self.update_option_data()
                    time.sleep(900)  # 每15分钟更新一次 (15 * 60 = 900秒)
                except Exception as e:
                    self.logger.error(f"更新任务异常: {str(e)}")
                    time.sleep(5)
        
        update_thread = threading.Thread(target=update_task)
        update_thread.daemon = True
        update_thread.start()
        self.logger.info("启动期权数据更新任务")

    def check_status(self) -> Dict:
        """检查监控器状态"""
        try:
            status = {
                'status': 'healthy',
                'last_update': None,
                'data_count': 0,
                'errors': [],
                'performance': {
                    'avg_response_time': 0,
                    'error_rate': 0
                }
            }
            
            # 检查数据库连接
            try:
                with self.db.get_connection() as conn:
                    cursor = conn.cursor()
                    
                    # 获取最新数据时间
                    cursor.execute('''
                        SELECT MAX(created_at) as last_update,
                               COUNT(*) as data_count
                        FROM option_tickers
                        WHERE created_at >= datetime('now', '-15 minutes')
                    ''')
                    result = cursor.fetchone()
                    
                    if result:
                        status['last_update'] = result[0]
                        status['data_count'] = result[1]
                        
                        # 检查数据是否过期
                        if result[1] == 0:
                            status['status'] = 'warning'
                            status['errors'].append('No recent data')
                    
            except Exception as e:
                status['status'] = 'error'
                status['errors'].append(f'Database error: {str(e)}')
            
            # 检查API连接
            try:
                response = self._request('GET', '/api/v5/public/time')
                if not response:
                    status['status'] = 'error'
                    status['errors'].append('API connection failed')
            except Exception as e:
                status['status'] = 'error'
                status['errors'].append(f'API error: {str(e)}')
            
            # 计算性能指标
            if self.request_times:
                status['performance']['avg_response_time'] = sum(self.request_times) / len(self.request_times)
                status['performance']['error_rate'] = self.error_count / len(self.request_times)
            
            return status
            
        except Exception as e:
            self.logger.error(f"检查状态失败: {str(e)}")
            return {
                'status': 'error',
                'error': str(e)
            }

    def sync_data(self):
        """同步数据"""
        try:
            self.logger.info("开始同步数据...")
            start_time = time.time()
            
            # 清理过期数据
            self.clean_expired_data()
            
            # 获取最新数据
            success = self.update_option_data()
            
            if success:
                # 验证数据完整性
                if self.verify_data():
                    self.logger.info("数据同步成功")
                    return True
                else:
                    self.logger.error("数据验证失败")
                    return False
            else:
                self.logger.error("更新数据失败")
                return False
            
        except Exception as e:
            self.logger.error(f"同步数据失败: {str(e)}")
            return False
        finally:
            elapsed_time = time.time() - start_time
            self.logger.info(f"数据同步耗时: {elapsed_time:.3f}秒")

    def start_sync_task(self):
        """启动数据同步任务"""
        def sync_task():
            while True:
                try:
                    # 检查状态
                    status = self.check_status()
                    
                    # 如果状态异常或数据过期，则同步数据
                    if status['status'] != 'healthy' or not status['data_count']:
                        self.logger.warning("检测到数据异常，开始同步...")
                        if self.sync_data():
                            # 数据同步成功后进行市场分析
                            analysis = self.analyze_market()
                            if analysis:
                                self.logger.info(f"市场分析结果: {analysis['market_sentiment']}")
                                # 保存分析结果
                                self.save_market_analysis(analysis)
                
                    # 等待下一次检查
                    time.sleep(300)  # 5分钟检查一次
                    
                except Exception as e:
                    self.logger.error(f"同步任务异常: {str(e)}")
                    time.sleep(60)  # 出错后等待1分钟
        
        sync_thread = threading.Thread(target=sync_task)
        sync_thread.daemon = True
        sync_thread.start()
        self.logger.info("启动数据同步任务")

    def get_statistics(self) -> Dict:
        """获取数据统计"""
        try:
            stats = {
                'total_contracts': 0,
                'active_contracts': 0,
                'total_volume': 0,
                'call_volume': 0,
                'put_volume': 0,
                'update_time': None
            }
            
            with self.db.get_connection() as conn:
                cursor = conn.cursor()
                
                # 获取合约统计
                cursor.execute('''
                    SELECT 
                        COUNT(*) as total,
                        SUM(CASE WHEN state = 'live' THEN 1 ELSE 0 END) as active
                    FROM option_contracts
                ''')
                result = cursor.fetchone()
                if result:
                    stats['total_contracts'] = result[0]
                    stats['active_contracts'] = result[1]
                
                # 获取成交量统计
                cursor.execute('''
                    SELECT 
                        c.optType,
                        SUM(t.volume_15m) as total_volume
                    FROM option_contracts c
                    JOIN option_tickers t ON c.instId = t.instId
                    WHERE t.created_at >= datetime('now', '-15 minutes')
                    GROUP BY c.optType
                ''')
                
                for row in cursor.fetchall():
                    if row[0] == 'C':
                        stats['call_volume'] = row[1]
                    else:
                        stats['put_volume'] = row[1]
                
                stats['total_volume'] = stats['call_volume'] + stats['put_volume']
                
                # 获取最后更新时间
                cursor.execute('SELECT MAX(created_at) FROM option_tickers')
                stats['update_time'] = cursor.fetchone()[0]
            
            return stats
            
        except Exception as e:
            self.logger.error(f"获取统计数据失败: {str(e)}")
            return {}

    def analyze_market(self) -> Dict:
        """分析期权市场状态"""
        try:
            self.logger.info("开始分析期权市场...")
            
            analysis = {
                'market_sentiment': 'neutral',  # bullish, bearish, neutral
                'volatility_level': 'medium',   # high, medium, low
                'volume_trend': 'stable',       # increasing, decreasing, stable
                'put_call_ratio': 0.0,
                'alerts': [],
                'metrics': {},
                'timestamp': datetime.now().isoformat()
            }
            
            # 获取最新数据
            df = self.get_option_data()
            if df.empty:
                self.logger.warning("无法获取期权数据进行分析")
                return analysis
            
            # 计算看跌/看涨期权比率
            call_volume = df[df['type'] == 'CALL']['volume_15m'].sum()
            put_volume = df[df['type'] == 'PUT']['volume_15m'].sum()
            
            if call_volume > 0:
                analysis['put_call_ratio'] = put_volume / call_volume
                
                # 根据PCR判断市场情绪
                if analysis['put_call_ratio'] > 1.2:
                    analysis['market_sentiment'] = 'bearish'
                elif analysis['put_call_ratio'] < 0.8:
                    analysis['market_sentiment'] = 'bullish'
            
            # 分析成交量趋势
            try:
                current_volume = df['volume_15m'].sum()
                prev_volume = self.get_historical_volume()
                
                volume_change = ((current_volume - prev_volume) / prev_volume) * 100
                if volume_change > 20:
                    analysis['volume_trend'] = 'increasing'
                elif volume_change < -20:
                    analysis['volume_trend'] = 'decreasing'
                
                analysis['metrics']['volume_change'] = volume_change
                
            except Exception as e:
                self.logger.error(f"分析成交量趋势失败: {str(e)}")
            
            # 计算隐含波动率
            try:
                iv_data = self.calculate_implied_volatility(df)
                analysis['metrics']['implied_volatility'] = iv_data
                
                # 判断波动率水平
                if iv_data['avg_iv'] > 80:
                    analysis['volatility_level'] = 'high'
                elif iv_data['avg_iv'] < 40:
                    analysis['volatility_level'] = 'low'
                
            except Exception as e:
                self.logger.error(f"计算隐含波动率失败: {str(e)}")
            
            # 生成警报
            self.generate_alerts(analysis)
            
            self.logger.info(f"市场分析完成: {analysis['market_sentiment']}, "
                            f"波动率: {analysis['volatility_level']}, "
                            f"成交量趋势: {analysis['volume_trend']}")
            
            return analysis
            
        except Exception as e:
            self.logger.error(f"市场分析失败: {str(e)}")
            return {}

    def get_historical_volume(self) -> float:
        """获取历史成交量数据"""
        try:
            with self.db.get_connection() as conn:
                cursor = conn.cursor()
                
                # 获取15-30分钟前的成交量
                cursor.execute('''
                    SELECT SUM(volume_15m) as total_volume
                    FROM option_tickers
                    WHERE created_at BETWEEN 
                        datetime('now', '-30 minutes') AND
                        datetime('now', '-15 minutes')
                ''')
                
                result = cursor.fetchone()
                return result[0] if result and result[0] else 0
                
        except Exception as e:
            self.logger.error(f"获取历史成交量失败: {str(e)}")
            return 0

    def calculate_implied_volatility(self, df: pd.DataFrame) -> Dict:
        """计算隐含波动率指标"""
        try:
            iv_data = {
                'avg_iv': 0.0,
                'call_iv': 0.0,
                'put_iv': 0.0,
                'iv_skew': 0.0,
                'term_structure': []
            }
            
            # 按到期时间分组计算
            grouped = df.groupby('days_to_expiry')
            
            for days, group in grouped:
                call_iv = self._calculate_iv(group[group['type'] == 'CALL'])
                put_iv = self._calculate_iv(group[group['type'] == 'PUT'])
                
                iv_data['term_structure'].append({
                    'days': days,
                    'call_iv': call_iv,
                    'put_iv': put_iv
                })
            
            # 计算平均IV
            if iv_data['term_structure']:
                iv_data['avg_iv'] = np.mean([x['call_iv'] + x['put_iv'] for x in iv_data['term_structure']]) / 2
                iv_data['call_iv'] = np.mean([x['call_iv'] for x in iv_data['term_structure']])
                iv_data['put_iv'] = np.mean([x['put_iv'] for x in iv_data['term_structure']])
                iv_data['iv_skew'] = iv_data['put_iv'] - iv_data['call_iv']
            
            return iv_data
            
        except Exception as e:
            self.logger.error(f"计算隐含波动率指标失败: {str(e)}")
            return {}

    def generate_alerts(self, analysis: Dict):
        """生成市场警报"""
        try:
            # 检查PCR异常
            if analysis['put_call_ratio'] > 2.0:
                analysis['alerts'].append({
                    'type': 'PCR',
                    'severity': 'high',
                    'message': f"看跌/看涨期权比率异常高: {analysis['put_call_ratio']:.2f}"
                })
            
            # 检查成交量异常
            if analysis['volume_trend'] == 'increasing':
                analysis['alerts'].append({
                    'type': 'VOLUME',
                    'severity': 'medium',
                    'message': f"成交量显著增加: {analysis['metrics']['volume_change']:.1f}%"
                })
            
            # 检查波动率异常
            if analysis['volatility_level'] == 'high':
                analysis['alerts'].append({
                    'type': 'VOLATILITY',
                    'severity': 'high',
                    'message': f"市场波动率异常高: {analysis['metrics']['implied_volatility']['avg_iv']:.1f}%"
                })
            
        except Exception as e:
            self.logger.error(f"生成市场警报失败: {str(e)}")

    def _calculate_iv(self, df: pd.DataFrame) -> float:
        """计算隐含波动率（简化版）"""
        try:
            # 这里使用简化的计算方法
            # 实际应用中应该使用Black-Scholes模型
            price_changes = []
            for i in range(len(df)-1):
                price_change = abs(df.iloc[i+1]['last_price'] - df.iloc[i]['last_price'])
                price_changes.append(price_change)
            
            if price_changes:
                return np.std(price_changes) * np.sqrt(252)  # 年化波动率
            return 0.0
            
        except Exception as e:
            self.logger.error(f"计算隐含波动率失败: {str(e)}")
            return 0.0

    def save_market_analysis(self, analysis: Dict):
        """保存市场分析结果"""
        try:
            with self.db.get_connection() as conn:
                cursor = conn.cursor()
                
                # 保存分析结果
                cursor.execute('''
                    INSERT INTO market_analysis (
                        sentiment,
                        volatility_level,
                        volume_trend,
                        put_call_ratio,
                        metrics,
                        timestamp
                    ) VALUES (?, ?, ?, ?, ?, ?)
                ''', (
                    analysis['market_sentiment'],
                    analysis['volatility_level'],
                    analysis['volume_trend'],
                    analysis['put_call_ratio'],
                    json.dumps(analysis['metrics']),
                    analysis['timestamp']
                ))
                
                # 保存警报
                for alert in analysis['alerts']:
                    cursor.execute('''
                        INSERT INTO market_alerts (
                            type,
                            severity,
                            message,
                            timestamp
                        ) VALUES (?, ?, ?, ?)
                    ''', (
                        alert['type'],
                        alert['severity'],
                        alert['message'],
                        analysis['timestamp']
                    ))
                
                conn.commit()
                self.logger.info("保存市场分析结果成功")
                
        except Exception as e:
            self.logger.error(f"保存市场分析结果失败: {str(e)}")

    def get_market_overview(self) -> Dict:
        """获取市场概览"""
        try:
            self.logger.info("获取市场概览...")
            
            # 获取期权数据
            df = self.get_option_data()
            if df.empty:
                return {'status': 'error', 'message': '没有数据'}
            
            # 计算市场指标
            call_df = df[df['type'] == 'CALL']
            put_df = df[df['type'] == 'PUT']
            
            total_volume = df['volume_15m'].sum()
            call_volume = call_df['volume_15m'].sum()
            put_volume = put_df['volume_15m'].sum()
            pc_ratio = call_volume / put_volume if put_volume > 0 else float('inf')
            
            # 获取现货价格
            spot_prices = {}
            for symbol in self.symbols:
                spot_prices[symbol] = self.get_spot_price(symbol)
            
            return {
                'status': 'success',
                'data': {
                    'total_volume': total_volume,
                    'call_volume': call_volume,
                    'put_volume': put_volume,
                    'pc_ratio': pc_ratio,
                    'spot_prices': spot_prices,
                    'timestamp': datetime.now().isoformat()
                }
            }
            
        except Exception as e:
            self.logger.error(f"获取市场概览失败: {str(e)}")
            return {'status': 'error', 'message': str(e)}

    def get_price_analysis(self) -> Dict:
        """获取价格分析"""
        try:
            self.logger.info("获取价格分析...")
            
            # 获取期权数据
            df = self.get_option_data()
            if df.empty:
                return {'status': 'error', 'message': '没有数据'}
            
            # 按币种分组
            analysis = {}
            for symbol in self.symbols:
                symbol_df = df[df['symbol'] == symbol]
                if symbol_df.empty:
                    continue
                
                # 获取现货价格
                spot_price = self.get_spot_price(symbol)
                
                # 计算价格分析指标
                analysis[symbol] = {
                    'spot_price': spot_price,
                    'avg_call_price': symbol_df[symbol_df['type'] == 'CALL']['last'].mean(),
                    'avg_put_price': symbol_df[symbol_df['type'] == 'PUT']['last'].mean(),
                    'max_volume_strike': symbol_df.loc[symbol_df['volume_15m'].idxmax()]['strike'] if not symbol_df.empty else 0,
                    'timestamp': datetime.now().isoformat()
                }
            
            return {
                'status': 'success',
                'data': analysis
            }
            
        except Exception as e:
            self.logger.error(f"获取价格分析失败: {str(e)}")
            return {'status': 'error', 'message': str(e)}

    def get_alerts(self) -> List[Dict]:
        """获取预警信息"""
        try:
            self.logger.info("获取预警信息...")
            
            # 获取期权数据
            df = self.get_option_data()
            if df.empty:
                return []
            
            alerts = []
            
            # 检查异常成交量
            volume_threshold = df['volume_15m'].mean() + 2 * df['volume_15m'].std()
            high_volume_df = df[df['volume_15m'] > volume_threshold]
            
            for _, row in high_volume_df.iterrows():
                alerts.append({
                    'type': 'volume',
                    'symbol': row['symbol'],
                    'contract': row['contract'],
                    'message': f"异常成交量: {row['contract']} 成交量为 {row['volume_15m']}",
                    'severity': 'high',
                    'timestamp': datetime.now().isoformat()
                })
            
            return alerts
            
        except Exception as e:
            self.logger.error(f"获取预警信息失败: {str(e)}")
            return []

    def start(self):
        """启动监控"""
        try:
            self.logger.info("启动期权监控...")
            
            # 初始化数据
            self.update_option_data()
            
            # 这里可以添加定时任务逻辑
            # 例如使用线程定期更新数据
            
            return True
            
        except Exception as e:
            self.logger.error(f"启动期权监控失败: {str(e)}")
            return False

    def stop(self):
        """停止监控"""
        try:
            self.logger.info("停止期权监控...")
            
            # 清理资源
            
            return True
            
        except Exception as e:
            self.logger.error(f"停止期权监控失败: {str(e)}")
            return False 