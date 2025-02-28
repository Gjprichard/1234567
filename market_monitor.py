import ccxt
import requests
import pandas as pd
from datetime import datetime, timedelta
import time
import hmac
import base64
from config import API_KEY, API_SECRET, API_PASSPHRASE, REST_API_URL
from database import Database
from logger_config import setup_logger
from typing import Tuple, Dict, List, Any, Optional
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from base_monitor import BaseMonitor
import threading
import numpy as np
import logging

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class MarketMonitor(BaseMonitor):
    class ApiUtils:
        """API工具类"""
        def __init__(self, api_secret: str):
            self.api_secret = api_secret
        
        def get_timestamp(self) -> str:
            """获取时间戳"""
            return datetime.utcnow().isoformat()[:-3] + 'Z'
        
        def sign(self, timestamp: str, method: str, request_path: str, body: str = '') -> str:
            """生成签名"""
            message = timestamp + method + request_path + (body or '')
            mac = hmac.new(
                bytes(self.api_secret, encoding='utf8'),
                bytes(message, encoding='utf-8'),
                digestmod='sha256'
            )
            return base64.b64encode(mac.digest()).decode()
    
    def __init__(self):
        """初始化市场监控器"""
        try:
            super().__init__()
            
            # 基础配置
            self.logger = logger
            self.base_url = "https://www.okx.com/api/v5"
            self.api_key = API_KEY
            self.api_secret = API_SECRET
            self.passphrase = API_PASSPHRASE
            
            # 设置预警阈值
            self.alert_thresholds = {
                'price_change': 3.0,
                'volume_change': 50.0
            }
            
            # 监控指定的10个币种
            self.symbols = [
                'BTC/USDT',  # 比特币
                'ETH/USDT',  # 以太坊
                'SOL/USDT',  # 索拉纳
                'XRP/USDT',  # 瑞波币
                'DOGE/USDT', # 狗狗币
                'ADA/USDT',  # 卡尔达诺
                'LINK/USDT', # 链接
                'OP/USDT',   # Optimism
                'LTC/USDT',  # 莱特币
                'TON/USDT'   # Telegram Open Network
            ]
            
            # 初始化数据库
            self.db = Database()
            
            # 初始化交易所API
            self.exchange = ccxt.okx({
                'enableRateLimit': True,
                'options': {
                    'defaultType': 'spot'
                }
            })
            
            # 清理任务配置
            self.cleanup_interval = 3600  # 每小时清理一次
            self.cleanup_retention = 24   # 保留24小时的数据
            
            # 初始化API工具
            self.api_utils = self.ApiUtils(API_SECRET)
            
            # 设置运行状态
            self.running = False
            self.last_update = None
            self.update_thread = None
            self._stop_event = threading.Event()
            
            # 启动监控和清理任务
            self.start()
            self.start_cleanup_task()
            
            logger.info("市场监控器初始化完成")
            
        except Exception as e:
            logger.error(f"初始化市场监控器失败: {str(e)}")
            raise
        
    def __del__(self):
        """确保清理资源"""
        try:
            if hasattr(self, 'running'):
                self.running = False
        except Exception as e:
            logger.error(f"清理资源失败: {str(e)}")
    
    def start(self):
        """启动监控"""
        if not self.running:
            self.running = True
            self._stop_event.clear()
            self.update_thread = threading.Thread(target=self._update_loop)
            self.update_thread.daemon = True
            self.update_thread.start()
            logger.info("市场监控已启动")
    
    def stop(self):
        """停止监控"""
        try:
            if self.running:
                logger.info("正在停止市场监控...")
                # 先设置停止标志
                self.running = False
                self._stop_event.set()
                
                # 等待更新线程结束
                if self.update_thread and self.update_thread.is_alive():
                    try:
                        for _ in range(5):  # 分段等待，最多5秒
                            self.update_thread.join(timeout=1)
                            if not self.update_thread.is_alive():
                                break
                    except Exception:
                        logger.warning("等待更新线程超时")
                    
                    if self.update_thread.is_alive():
                        logger.warning("更新线程未能在5秒内停止")
                
                # 关闭数据库连接
                try:
                    if hasattr(self, 'db'):
                        self.db.close()
                except Exception as e:
                    logger.error(f"关闭数据库连接失败: {str(e)}")
                
                logger.info("市场监控已停止")
        except Exception as e:
            logger.error(f"停止市场监控失败: {str(e)}")
    
    def _update_loop(self):
        """更新循环"""
        while not self._stop_event.is_set():
            try:
                if not self.running:
                    break
                
                self.update_market_data()
                
                # 分段等待，便于及时响应停止信号
                for _ in range(60):  # 60秒更新间隔
                    if self._stop_event.is_set() or not self.running:
                        break
                    time.sleep(1)
                
            except Exception as e:
                logger.error(f"更新循环异常: {str(e)}")
                if not self._stop_event.is_set() and self.running:
                    time.sleep(5)  # 发生错误时等待5秒
    
    def _get_timestamp(self):
        return datetime.utcnow().isoformat()[:-3] + 'Z'

    def _sign(self, timestamp, method, request_path, body=''):
        message = timestamp + method + request_path + (body or '')
        mac = hmac.new(
            bytes(self.api_secret, encoding='utf8'),
            bytes(message, encoding='utf-8'),
            digestmod='sha256'
        )
        d = mac.digest()
        return base64.b64encode(d).decode()

    def _request(self, method: str, endpoint: str, params: dict = None) -> Optional[dict]:
        """发送API请求"""
        try:
            # 构建完整URL
            url = f"{self.base_url}{endpoint}"
            
            # 添加时间戳和签名
            timestamp = self._get_timestamp()
            sign = self._sign(timestamp, method, endpoint)
            
            # 设置请求头
            headers = {
                'OK-ACCESS-KEY': self.api_key,
                'OK-ACCESS-SIGN': sign,
                'OK-ACCESS-TIMESTAMP': timestamp,
                'OK-ACCESS-PASSPHRASE': self.passphrase,
                'Content-Type': 'application/json'
            }
            
            # 设置重试策略
            retry_strategy = Retry(
                total=3,
                backoff_factor=0.5,
                status_forcelist=[500, 502, 503, 504]
            )
            adapter = HTTPAdapter(max_retries=retry_strategy)
            self.session.mount("https://", adapter)
            
            # 发送请求
            logger.debug(f"发送请求: {method} {url}")
            logger.debug(f"请求参数: {params}")
            
            response = self.session.request(
                method=method,
                url=url,
                params=params,
                headers=headers,
                timeout=10
            )
            
            # 检查响应状态
            response.raise_for_status()
            
            # 解析响应
            data = response.json()
            
            if data.get('code') == '0':
                return data
            else:
                logger.error(f"API请求失败: {data.get('msg', 'Unknown error')}")
                logger.debug(f"完整响应: {data}")
                return None
            
        except requests.exceptions.RequestException as e:
            logger.error(f"请求失败 ({method} {endpoint}): {str(e)}")
            return None
        except Exception as e:
            logger.error(f"请求处理失败: {str(e)}")
            return None

    def get_historical_data(self, symbol: str) -> Tuple[pd.DataFrame, Dict[str, float]]:
        """获取历史数据"""
        try:
            logger.info(f"获取 {symbol} 的历史数据")
            
            # 从数据库获取数据
            data = self.db.get_spot_data(
                symbol=symbol,
                limit=100,
                time_offset=timedelta(hours=1)  # 获取1小时的数据
            )
            
            if not data:
                logger.error(f"获取历史数据失败: {symbol}")
                return pd.DataFrame(), {}
            
            # 转换为DataFrame
            df = pd.DataFrame(data)
            
            # 计算指标
            metrics = {
                'avg_price': df['price'].mean(),
                'avg_volume': df['volume'].mean(),
                'price_change': self._calculate_price_change(df),
                'volume_change': self._calculate_volume_change(df)
            }
            
            return df, metrics
            
        except Exception as e:
            logger.error(f"获取历史数据失败: {str(e)}")
            return pd.DataFrame(), {}

    def _calculate_price_change(self, df: pd.DataFrame) -> float:
        """计算价格变化率"""
        if len(df) < 2:
            return 0.0
        first_price = df.iloc[0]['price']
        last_price = df.iloc[-1]['price']
        return ((last_price - first_price) / first_price) * 100

    def _calculate_volume_change(self, df: pd.DataFrame) -> float:
        """计算成交量变化率"""
        if len(df) < 2:
            return 0.0
        first_volume = df.iloc[0]['volume']
        last_volume = df.iloc[-1]['volume']
        return ((last_volume - first_volume) / first_volume) * 100

    def get_alerts(self) -> List[Dict]:
        """获取预警信息"""
        try:
            logger.info("开始获取预警信息")
            # 获取原始数据并计算指标
            data = self.db.get_spot_data(limit=50)
            alerts = []
            
            if not data:
                return []
            
            df = pd.DataFrame(data)
            
            # 计算15分钟变化率和波动率
            for symbol in df['symbol'].unique():
                try:
                    symbol_data = df[df['symbol'] == symbol].copy()
                    if len(symbol_data) < 2:
                        continue
                        
                    # 计算价格变化
                    price_change = self._calculate_price_change(symbol_data)
                    
                    # 计算成交量变化
                    volume_change = self._calculate_volume_change(symbol_data)
                    
                    # 计算波动率
                    volatility = symbol_data['price'].pct_change().std() * 100
                    
                    latest = symbol_data.iloc[-1]
                    
                    # 检查价格变化
                    if abs(price_change) > self.alert_thresholds['price_change']:
                        alerts.append({
                            'symbol': symbol,
                            'type': 'PRICE_ALERT',
                            'severity': 'warning' if abs(price_change) > 5 else 'info',
                            'message': f"价格15分钟变化: {price_change:.2f}%",
                            'price': latest['price'],
                            'change': price_change,
                            'timestamp': latest['timestamp']
                        })
                    
                    # 检查成交量变化
                    if abs(volume_change) > self.alert_thresholds['volume_change']:
                        alerts.append({
                            'symbol': symbol,
                            'type': 'VOLUME_ALERT',
                            'severity': 'warning' if abs(volume_change) > 100 else 'info',
                            'message': f"成交量15分钟变化: {volume_change:.2f}%",
                            'volume': latest['volume'],
                            'change': volume_change,
                            'timestamp': latest['timestamp']
                        })
                    
                    # 检查波动率
                    if volatility > 2.0:  # 2%的波动率阈值
                        alerts.append({
                            'symbol': symbol,
                            'type': 'VOLATILITY_ALERT',
                            'severity': 'warning' if volatility > 5.0 else 'info',
                            'message': f"15分钟波动率: {volatility:.2f}%",
                            'price': latest['price'],
                            'change': volatility,
                            'timestamp': latest['timestamp']
                        })
                except Exception as e:
                    logger.error(f"处理{symbol}预警失败: {str(e)}")
                    continue
            
            # 保存预警到数据库
            for alert in alerts:
                self.db.save_alert(alert)
            
            logger.info(f"生成 {len(alerts)} 个预警")
            return alerts
            
        except Exception as e:
            logger.error(f"获取预警信息失败: {str(e)}")
            return []

    def get_market_depth(self, symbol: str) -> Tuple[pd.DataFrame, pd.DataFrame]:
        """获取市场深度数据"""
        try:
            # 先尝试从数据库获取最新数据
            depth_data = self.db.get_market_depth_with_metrics(symbol)
            
            if depth_data and depth_data.get('bids') and depth_data.get('asks'):
                bids_df = pd.DataFrame(depth_data['bids'])
                asks_df = pd.DataFrame(depth_data['asks'])
                return bids_df, asks_df
            
            # 如果数据库没有数据，则从交易所获取
            orderbook = self.exchange.fetch_order_book(f"{symbol}/USDT")
            
            # 创建买单和卖单的DataFrame
            bids_df = pd.DataFrame(orderbook['bids'], columns=['price', 'amount'])
            asks_df = pd.DataFrame(orderbook['asks'], columns=['price', 'amount'])
            
            # 计算累计数量
            bids_df['cumulative'] = bids_df['amount'].cumsum()
            asks_df['cumulative'] = asks_df['amount'].cumsum()
            
            # 转换数据类型
            for df in [bids_df, asks_df]:
                df['price'] = pd.to_numeric(df['price'])
                df['amount'] = pd.to_numeric(df['amount'])
                df['cumulative'] = pd.to_numeric(df['cumulative'])
                
                # 按价格排序
                if df is bids_df:
                    df.sort_values('price', ascending=False, inplace=True)
                else:
                    df.sort_values('price', ascending=True, inplace=True)
                
                # 重置索引
                df.reset_index(drop=True, inplace=True)
            
            # 保存到数据库
            self.db.save_market_depth(symbol, bids_df, asks_df)
            
            return bids_df, asks_df
            
        except Exception as e:
            logger.error(f"获取市场深度数据失败: {str(e)}")
            return pd.DataFrame(), pd.DataFrame()

    def start_cleanup_task(self):
        """启动数据清理任务"""
        def cleanup_task():
            while self.running:
                try:
                    # 1. 检查数据完整性
                    self.check_data_integrity()
                    
                    # 2. 清理旧数据
                    self.db.cleanup_old_data()
                    
                    # 3. 优化数据库
                    self.db.optimize_db()
                    
                    # 4. 等待下次清理
                    time.sleep(self.cleanup_interval)
                except Exception as e:
                    logger.error(f"清理任务异常: {str(e)}")
                    time.sleep(60)  # 出错后等待1分钟再试
        
        cleanup_thread = threading.Thread(target=cleanup_task)
        cleanup_thread.daemon = True
        cleanup_thread.start()
        logger.info("启动数据清理任务")

    def check_data_integrity(self) -> bool:
        """检查数据完整性"""
        try:
            # 获取最新数据
            latest_data = self.db.get_latest_market_data()
            if not latest_data:
                logger.warning("未找到市场数据")
                return False
            
            # 检查数据完整性
            for symbol in self.symbols:
                symbol_data = [d for d in latest_data if d['symbol'] == symbol]
                if not symbol_data:
                    logger.warning(f"缺少 {symbol} 的数据")
                    return False
            
            # 检查数据时效性
            current_time = int(time.time())
            latest_timestamp = max(d['timestamp'] for d in latest_data)
            if current_time - latest_timestamp > 300:  # 5分钟
                logger.warning("数据已过期")
                return False
            
            return True
            
        except Exception as e:
            logger.error(f"数据完整性检查失败: {str(e)}")
            return False

    def check_status(self) -> Dict:
        """检查监控器状态"""
        try:
            # 获取最新的数据统计
            metrics = self.db.get_market_metrics()
            alerts = self.db.get_alerts(limit=1)
            
            return {
                'status': 'running' if self.running else 'stopped',
                'last_update': self.last_update.isoformat() if self.last_update else None,
                'symbols': self.symbols,
                'metrics': {
                    'total_volume': metrics.get('total_volume', 0),
                    'up_count': metrics.get('up_count', 0),
                    'down_count': metrics.get('down_count', 0),
                    'avg_volatility': metrics.get('avg_volatility', 0)
                },
                'alerts_count': len(alerts),
                'timestamp': datetime.now()
            }
        except Exception as e:
            logger.error(f"获取状态失败: {str(e)}")
            return {
                'status': 'error',
                'timestamp': datetime.now()
            }

    def get_market_data(self) -> List[Dict]:
        """获取市场数据"""
        try:
            # 获取最新数据
            data = self._fetch_market_data()
            if not data:
                # 如果获取失败，尝试从数据库获取最新数据
                data = self.db.get_latest_market_data()
            
            # 确保数据格式正确
            if data:
                # 转换为DataFrame进行处理
                df = pd.DataFrame(data)
                
                # 确保必要的列存在
                required_columns = {
                    'symbol', 'price', 'volume', 
                    'price_change_15m', 'volume_change_15m'
                }
                
                if not all(col in df.columns for col in required_columns):
                    logger.error(f"数据缺少必要的列: {required_columns - set(df.columns)}")
                    return []
                
                # 确保数值类型正确
                try:
                    df['price'] = pd.to_numeric(df['price'])
                    df['volume'] = pd.to_numeric(df['volume'])
                    df['price_change_15m'] = pd.to_numeric(df['price_change_15m'])
                    df['volume_change_15m'] = pd.to_numeric(df['volume_change_15m'])
                except Exception as e:
                    logger.error(f"数据类型转换失败: {str(e)}")
                    return []
                
                # 返回处理后的数据
                return df.to_dict('records')
            
            return []
            
        except Exception as e:
            logger.error(f"获取市场数据失败: {str(e)}")
            logger.exception("详细错误信息:")
            return []

    def process_market_data(self) -> bool:
        """处理和保存市场数据"""
        try:
            # 直接更新市场数据
            return self.update_market_data()
        except Exception as e:
            logger.error(f"处理市场数据失败: {str(e)}")
            return False

    def get_market_overview(self):
        """获取市场概览数据"""
        try:
            # 获取最新市场数据
            market_data = self.db.get_latest_market_data()
            if not market_data:
                logger.warning("未获取到市场数据")
                return {
                    'total_volume': 0,
                    'avg_price_change': 0,
                    'avg_volume_change': 0,
                    'up_tokens': 0,
                    'down_tokens': 0,
                    'timestamp': int(time.time()),
                    'latest_data': []
                }
            
            # 转换为DataFrame进行处理
            df = pd.DataFrame(market_data)
            
            # 确保必要的列存在
            if 'price_change_15m' not in df.columns:
                df['price_change_15m'] = 0.0
            if 'volume_change_15m' not in df.columns:
                df['volume_change_15m'] = 0.0
            
            # 计算市场概览数据
            overview = {
                'total_volume': float(df['volume'].sum()),
                'avg_price_change': float(df['price_change_15m'].mean()),
                'avg_volume_change': float(df['volume_change_15m'].mean()),
                'up_tokens': int(len(df[df['price_change_15m'] > 0])),
                'down_tokens': int(len(df[df['price_change_15m'] < 0])),
                'timestamp': int(df['timestamp'].max()),
                'latest_data': df.to_dict('records')
            }
            
            logger.info(f"获取市场概览成功: {len(df)} 个交易对")
            return overview
            
        except Exception as e:
            logger.error(f"获取市场概览失败: {str(e)}")
            return None

    def get_price_analysis(self) -> Dict:
        """获取价格分析数据"""
        try:
            # 获取最新数据
            latest_data = self.db.get_latest_market_data()
            if not latest_data:
                return {}
            
            df = pd.DataFrame(latest_data)
            
            # 确保必要的列存在
            if 'price_change_15m' not in df.columns:
                df['price_change_15m'] = 0.0
            
            # 计算价格变化
            df['abs_price_change'] = df['price_change_15m'].abs()  # 计算绝对值
            price_changes = df.nlargest(10, 'abs_price_change')[['symbol', 'price', 'price_change_15m', 'timestamp']]
            
            return {
                'price_changes': price_changes.to_dict('records'),
                'timestamp': int(time.time())
            }
            
        except Exception as e:
            logger.error(f"获取价格分析数据失败: {str(e)}")
            return {}

    def get_volume_analysis(self) -> Dict:
        """获取成交量分析数据"""
        try:
            # 获取最新数据
            latest_data = self.db.get_latest_market_data()
            if not latest_data:
                return {}
            
            df = pd.DataFrame(latest_data)
            
            # 确保必要的列存在
            if 'volume_change_15m' not in df.columns:
                df['volume_change_15m'] = 0.0
            
            # 计算成交量变化
            df['abs_volume_change'] = df['volume_change_15m'].abs()  # 计算绝对值
            volume_changes = df.nlargest(10, 'abs_volume_change')[['symbol', 'volume', 'volume_change_15m', 'timestamp']]
            
            return {
                'volume_changes': volume_changes.to_dict('records'),
                'timestamp': int(time.time())
            }
            
        except Exception as e:
            logger.error(f"获取成交量分析数据失败: {str(e)}")
            return {}

    def get_market_status(self) -> Dict:
        """获取市场状态"""
        try:
            # 获取最新的市场指标
            metrics = self.db.get_market_metrics()
            
            # 计算市场状态
            status = {
                'market_trend': 'bullish' if metrics['up_count'] > metrics['down_count'] else 'bearish',
                'volatility_level': 'high' if metrics['avg_volatility'] > 5.0 else 'normal',
                'volume_trend': 'up' if metrics['avg_volume_change'] > 0 else 'down',
                'timestamp': datetime.now()
            }
            
            return status
        except Exception as e:
            logger.error(f"获取市场状态失败: {str(e)}")
            return {}

    def _validate_market_data(self, data: Dict) -> bool:
        """验证市场数据"""
        try:
            required_fields = {
                'symbol', 'price', 'volume', 'timestamp',
                'price_change_15m', 'volume_change_15m'
            }
            
            # 检查必要字段是否存在
            if not all(field in data for field in required_fields):
                logger.warning(f"数据缺少必要字段: {required_fields - set(data.keys())}")
                return False
            
            # 检查数值是否有效
            if not isinstance(data['price'], (int, float)) or data['price'] <= 0:
                logger.warning(f"无效的价格: {data['price']}")
                return False
            
            if not isinstance(data['volume'], (int, float)) or data['volume'] < 0:
                logger.warning(f"无效的成交量: {data['volume']}")
                return False
            
            return True
            
        except Exception as e:
            logger.error(f"验证数据失败: {str(e)}")
            return False

    def update_market_data(self) -> bool:
        """更新市场数据"""
        try:
            # 获取市场数据
            data = self._fetch_market_data()
            if not data:
                return False
            
            current_time = int(time.time())
            
            # 计算价格和成交量变化
            for item in data:
                try:
                    # 添加时间戳
                    item['timestamp'] = current_time
                    
                    # 获取15分钟和30分钟前的数据
                    historical_15m = self.db.get_historical_data(
                        item['symbol'],
                        timestamp=current_time - 900  # 15分钟 = 900秒
                    )
                    
                    historical_30m = self.db.get_historical_data(
                        item['symbol'],
                        timestamp=current_time - 1800  # 30分钟 = 1800秒
                    )
                    
                    # 计算价格和成交量变化率
                    if historical_15m and historical_30m:
                        # 计算当前到15分钟前的价格变化率
                        current_15m_price_change = (
                            (item['price'] - historical_15m['price']) / 
                            historical_15m['price'] * 100
                        )
                        
                        # 计算15分钟前到30分钟前的价格变化率
                        prev_15m_price_change = (
                            (historical_15m['price'] - historical_30m['price']) / 
                            historical_30m['price'] * 100
                        )
                        
                        # 价格变化率的梯度（差值）
                        item['price_change_15m'] = current_15m_price_change - prev_15m_price_change
                        
                        # 计算当前到15分钟前的成交量变化率
                        current_15m_volume_change = (
                            (item['volume'] - historical_15m['volume']) / 
                            historical_15m['volume'] * 100
                        )
                        
                        # 计算15分钟前到30分钟前的成交量变化率
                        prev_15m_volume_change = (
                            (historical_15m['volume'] - historical_30m['volume']) / 
                            historical_30m['volume'] * 100
                        )
                        
                        # 成交量变化率的梯度（差值）
                        item['volume_change_15m'] = current_15m_volume_change - prev_15m_volume_change
                        
                        logger.debug(
                            f"{item['symbol']} 价格变化: {item['price_change_15m']:.2f}%, "
                            f"成交量变化: {item['volume_change_15m']:.2f}%"
                        )
                    else:
                        item['price_change_15m'] = 0.0
                        item['volume_change_15m'] = 0.0
                        logger.debug(f"{item['symbol']} 缺少历史数据，使用默认值")
                    
                    # 保存到数据库
                    self.db.save_market_data(item)
                    
                except Exception as e:
                    logger.error(f"处理{item['symbol']}数据失败: {str(e)}")
                    continue
            
            return True
            
        except Exception as e:
            logger.error(f"更新市场数据失败: {str(e)}")
            return False

    def get_processed_data(self) -> Dict:
        """获取处理后的市场数据"""
        try:
            # 获取最新数据
            latest_data = self.db.get_latest_market_data()
            if not latest_data:
                return {
                    'data': [],
                    'timestamp': int(time.time())
                }
            
            # 转换为DataFrame进行处理
            df = pd.DataFrame(latest_data)
            
            # 确保必要的列存在
            if 'price_change_15m' not in df.columns:
                df['price_change_15m'] = 0.0
            if 'volume_change_15m' not in df.columns:
                df['volume_change_15m'] = 0.0
            
            # 处理数据
            processed_data = []
            for _, row in df.iterrows():
                processed_data.append({
                    'symbol': row['symbol'],
                    'price': float(row['price']),
                    'volume': float(row['volume']),
                    'price_change_15m': float(row['price_change_15m']),
                    'volume_change_15m': float(row['volume_change_15m']),
                    'timestamp': int(row['timestamp'])
                })
            
            return {
                'data': processed_data,
                'timestamp': int(time.time())
            }
            
        except Exception as e:
            logger.error(f"处理市场数据失败: {str(e)}")
            return {
                'data': [],
                'timestamp': int(time.time())
            }

    def cleanup_old_data(self):
        """优化的数据清理策略"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            try:
                # 只保留最近2小时的数据
                cutoff_time = int(time.time() - 7200)  # 2小时 = 7200秒
                
                # 批量删除旧数据
                cursor.execute('''
                    DELETE FROM spot_market_data
                    WHERE timestamp < ?
                ''', (cutoff_time,))
                
                deleted_count = cursor.rowcount
                
                # 定期清理预警数据
                cursor.execute('''
                    DELETE FROM market_alerts
                    WHERE created_at < datetime(?, 'unixepoch')
                ''', (cutoff_time,))
                
                conn.commit()
                logger.info(f"已清理 {deleted_count} 条旧数据")
                
            finally:
                conn.close()
                
        except Exception as e:
            logger.error(f"清理旧数据失败: {str(e)}")

    def _fetch_market_data(self) -> List[Dict]:
        """从交易所获取市场数据"""
        try:
            market_data = []
            current_time = int(time.time())
            
            # 获取所有交易对的ticker数据
            tickers = self.exchange.fetch_tickers(self.symbols)
            
            for symbol in self.symbols:
                try:
                    if symbol not in tickers:
                        continue
                        
                    ticker = tickers[symbol]
                    
                    # 获取历史数据计算变化率
                    historical_15m = self.db.get_historical_data(
                        symbol,
                        timestamp=current_time - 900  # 15分钟前
                    )
                    
                    # 计算变化率
                    price_change = 0.0
                    volume_change = 0.0
                    
                    if historical_15m:
                        try:
                            current_price = float(ticker['last'])
                            current_volume = float(ticker['quoteVolume'])
                            old_price = float(historical_15m['price'])
                            old_volume = float(historical_15m['volume'])
                            
                            if old_price > 0:
                                price_change = ((current_price - old_price) / old_price) * 100
                            if old_volume > 0:
                                volume_change = ((current_volume - old_volume) / old_volume) * 100
                        except Exception as e:
                            logger.error(f"计算{symbol}变化率失败: {str(e)}")
                    
                    # 构建数据
                    data = {
                        'symbol': symbol,
                        'price': float(ticker['last']),
                        'volume': float(ticker['quoteVolume']),
                        'high': float(ticker['high']),
                        'low': float(ticker['low']),
                        'price_change_15m': price_change,
                        'volume_change_15m': volume_change,
                        'timestamp': current_time
                    }
                    
                    # 验证并保存数据
                    if self._validate_market_data(data):
                        market_data.append(data)
                        self.db.save_market_data(data)
                        logger.debug(f"添加{symbol}数据: {data}")
                
                except Exception as e:
                    logger.error(f"获取{symbol}数据失败: {str(e)}")
                    continue
            
            if not market_data:
                logger.warning("未获取到有效的市场数据")
                return []
            
            logger.info(f"成功获取 {len(market_data)} 个交易对的数据")
            return market_data
            
        except Exception as e:
            logger.error(f"获取市场数据失败: {str(e)}")
            logger.exception("详细错误信息:")
            return []

    def get_option_data(self) -> List[Dict]:
        """获取期权市场数据"""
        try:
            # 从数据库获取最新期权数据
            option_data = self.db.get_option_data()
            
            if not option_data:
                return []
            
            # 计算期权指标
            for item in option_data:
                # 添加开仓量
                if 'open_interest' not in item:
                    item['open_interest'] = 0.0
                    
                # 添加隐含波动率
                if 'iv' not in item:
                    item['iv'] = self._calculate_iv(item)
                    
                # 添加希腊字母
                greeks = self._calculate_greeks(item)
                item.update(greeks)
                
            return option_data
            
        except Exception as e:
            logger.error(f"获取期权数据失败: {str(e)}")
            return []
        
    def _calculate_iv(self, option: Dict) -> float:
        """计算隐含波动率"""
        try:
            # 这里添加实际的IV计算逻辑
            return 0.0
        except Exception:
            return 0.0
        
    def _calculate_greeks(self, option: Dict) -> Dict:
        """计算期权希腊字母"""
        try:
            return {
                'delta': 0.0,
                'gamma': 0.0,
                'theta': 0.0,
                'vega': 0.0
            }
        except Exception:
            return {
                'delta': 0.0,
                'gamma': 0.0,
                'theta': 0.0,
                'vega': 0.0
            }

    def get_kline_data(self, symbol: str, timeframe: str = '1m', limit: int = 100) -> List[Dict]:
        """获取K线数据"""
        try:
            # 获取K线数据
            klines = self.exchange.fetch_ohlcv(symbol, timeframe, limit=limit)
            
            # 转换数据格式
            kline_data = []
            for k in klines:
                try:
                    data = {
                        'timestamp': pd.Timestamp(k[0]),  # 确保时间戳格式正确
                        'open': float(k[1]),
                        'high': float(k[2]),
                        'low': float(k[3]),
                        'close': float(k[4]),
                        'volume': float(k[5])
                    }
                    kline_data.append(data)
                except Exception as e:
                    logger.error(f"处理K线数据失败: {str(e)}")
                    continue
            
            # 转换为DataFrame并排序
            if kline_data:
                df = pd.DataFrame(kline_data)
                df = df.sort_values('timestamp')
                logger.debug(f"K线数据形状: {df.shape}")
                logger.debug(f"K线数据列: {df.columns.tolist()}")
                return df.to_dict('records')
            return []
            
        except Exception as e:
            logger.error(f"获取K线数据失败: {str(e)}")
            logger.exception("详细错误信息:")
            return []

    def get_orderbook(self, symbol: str, limit: int = 20) -> Dict:
        """获取订单簿数据"""
        try:
            orderbook = self.exchange.fetch_order_book(symbol, limit)
            logger.debug(f"原始订单簿数据: {orderbook}")
            
            # 确保数据格式正确
            bids = [[float(bid[0]), float(bid[1])] for bid in orderbook['bids']]
            asks = [[float(ask[0]), float(ask[1])] for ask in orderbook['asks']]
            
            return {
                'bids': bids,
                'asks': asks
            }
        except Exception as e:
            logger.error(f"获取订单簿数据失败: {str(e)}")
            return {'bids': [], 'asks': []}

# 测试代码
if __name__ == "__main__":
    monitor = MarketMonitor()
    
    print("获取市场数据...")
    market_data = monitor.get_market_data()
    print(f"\n获取到 {len(market_data)} 个交易对的数据")
    
    print("\n示例数据:")
    if market_data:
        print(market_data[0])
    
    print("\n获取预警信息...")
    alerts = monitor.get_alerts()
    print(f"发现 {len(alerts)} 个预警")
    for alert in alerts:
        print(f"{alert['symbol']}: {alert['message']}") 