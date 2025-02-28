import ccxt
import pandas as pd
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from base_monitor import BaseMonitor
from database import Database
import time

logger = logging.getLogger(__name__)

class OptionMonitor(BaseMonitor):
    def __init__(self):
        super().__init__()
        self.logger = logger
        self.db = Database()
        self.running = False
        
        # 初始化 exchange
        try:
            self.exchange = ccxt.okx({
                'enableRateLimit': True,
                'rateLimit': 2000,  # 增加到2秒
                'options': {
                    'defaultType': 'option',
                    'adjustForTimeDifference': True,
                    'recvWindow': 5000
                }
            })
        except Exception as e:
            logger.error(f"初始化交易所失败: {str(e)}")
            self.exchange = None
        
        self.last_update = None
        self.market_data = []
        
        # 设置请求间隔
        self.request_interval = 2  # 每个请求之间至少间隔2秒
        self.last_request_time = {}  # 记录每个接口的最后请求时间
        
        try:
            # 监控的币种
            self.symbols = ['BTC', 'ETH']
            # 异常成交量阈值(标准差倍数)
            self.volume_threshold = 2.0
            # 存储历史成交量数据
            self.volume_history = {}
            
        except Exception as e:
            logger.error(f"初始化期权监控失败: {str(e)}")
            self.exchange = None

    def _check_rate_limit(self, endpoint: str) -> bool:
        """检查是否可以发送请求"""
        current_time = time.time()
        if endpoint in self.last_request_time:
            time_passed = current_time - self.last_request_time[endpoint]
            if time_passed < self.request_interval:
                time.sleep(self.request_interval - time_passed)
        
        self.last_request_time[endpoint] = current_time
        return True

    def get_option_data(self) -> List[Dict]:
        """获取期权市场数据"""
        try:
            # 获取BTC期权合约列表
            contracts = self.exchange.fetch_option_markets('BTC/USDT')
            if not contracts:
                return []
            
            data = []
            # 将合约分组处理，每组10个
            contract_groups = [contracts[i:i+10] for i in range(0, len(contracts), 10)]
            
            for group in contract_groups:
                try:
                    for contract in group:
                        # 获取合约详情
                        ticker = self.exchange.fetch_ticker(contract['id'])
                        
                        option_data = {
                            'symbol': contract['symbol'],
                            'strike': float(contract['strike']),
                            'expiry': datetime.fromisoformat(contract['expiry']),
                            'option_type': contract['type'].upper(),
                            'price': float(ticker['last'] or 0),
                            'volume': float(ticker['baseVolume'] or 0),
                            'open_interest': float(contract.get('openInterest', 0)),
                            'timestamp': datetime.now()
                        }
                        
                        data.append(option_data)
                        self.db.save_option_data(option_data)
                    
                    # 每组处理完后等待2秒
                    time.sleep(2)
                    
                except Exception as e:
                    logger.error(f"处理合约数据失败: {str(e)}")
                    time.sleep(2)  # 出错后等待2秒
                    continue
            
            self.last_update = datetime.now()
            return data
            
        except Exception as e:
            logger.error(f"获取期权数据失败: {str(e)}")
            return []

    def detect_abnormal_volume(self, df: pd.DataFrame) -> List[Dict]:
        """检测异常成交量"""
        alerts = []
        
        for symbol in self.symbols:
            symbol_data = df[df['symbol'] == symbol]
            if symbol_data.empty:
                continue
                
            # 计算成交量统计
            mean_volume = symbol_data['volume'].mean()
            std_volume = symbol_data['volume'].std()
            
            # 检测异常值
            abnormal = symbol_data[
                symbol_data['volume'] > (mean_volume + self.volume_threshold * std_volume)
            ]
            
            for _, row in abnormal.iterrows():
                alerts.append({
                    'symbol': symbol,
                    'contract': row['contract'],
                    'type': row['type'],
                    'strike': row['strike'],
                    'expiry': row['expiry'],
                    'volume': row['volume'],
                    'volume_change': row['volume_change'],
                    'severity': self._get_severity(row['volume'], mean_volume, std_volume),
                    'time': datetime.fromtimestamp(row['timestamp']/1000).strftime('%Y-%m-%d %H:%M:%S')
                })
        
        return alerts

    def _get_severity(self, volume: float, mean: float, std: float) -> str:
        """计算警报严重程度"""
        deviation = (volume - mean) / std
        if deviation > 3:
            return 'critical'
        elif deviation > 2:
            return 'warning'
        return 'normal'

    def get_historical_data(self, contract: str) -> Tuple[pd.DataFrame, Dict]:
        """获取历史数据"""
        try:
            # 获取K线数据
            ohlcv = self.exchange.fetch_ohlcv(
                contract,
                timeframe='5m',
                limit=100
            )
            
            df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
            
            # 计算指标
            metrics = {
                'high': float(df['high'].max()),
                'low': float(df['low'].min()),
                'volume': float(df['volume'].sum()),
                'volume_change': float(df['volume'].pct_change().mean() * 100)
            }
            
            return df, metrics
            
        except Exception as e:
            logger.error(f"获取期权历史数据失败 ({contract}): {str(e)}")
            return pd.DataFrame(), {}

    def update_market_data(self) -> bool:
        """更新市场数据"""
        try:
            logger.info("更新期权市场数据")
            
            # 获取最新数据
            df = self.get_option_data()
            if not df:
                logger.error("获取期权数据失败")
                return False
            
            # 更新内部数据存储
            self.market_data = df
            self.last_update = datetime.now()
            
            # 检查异常成交量
            alerts = self.detect_abnormal_volume(pd.DataFrame(df))
            if alerts:
                logger.info(f"检测到 {len(alerts)} 个异常成交量预警")
            
            return True
            
        except Exception as e:
            logger.error(f"更新期权市场数据失败: {str(e)}")
            return False

    def get_contracts(self) -> List[Dict]:
        """获取期权合约列表"""
        try:
            self._check_rate_limit('contracts')  # 添加频率限制
            
            # 获取BTC期权合约
            response = self.exchange.fetch_option_contracts('BTC/USDT')
            if not response:
                return []
            
            contracts = []
            for contract in response:
                try:
                    contracts.append({
                        'symbol': contract['symbol'],
                        'strike': float(contract['strike']),
                        'expiry': contract['expiry'],
                        'type': contract['type'],
                        'last': float(contract['last'] or 0),
                        'volume': float(contract['volume'] or 0),
                        'openInterest': float(contract.get('openInterest', 0))
                    })
                except Exception as e:
                    logger.error(f"处理合约数据失败: {str(e)}")
                    continue
            
            return contracts
            
        except Exception as e:
            logger.error(f"获取期权合约列表失败: {str(e)}")
            return []

    def sync_data(self):
        """同步数据"""
        try:
            logger.info("开始同步数据...")
            
            # 清理过期数据
            self.cleanup_expired_data()
            
            # 获取合约列表
            contracts = self.get_contracts()
            if not contracts:
                return
            
            logger.info(f"获取到 {len(contracts)} 个期权合约")
            
            # 获取并保存数据
            for contract in contracts:
                try:
                    self._check_rate_limit('market_data')  # 添加频率限制
                    
                    data = {
                        'symbol': contract['symbol'],
                        'strike': float(contract['strike']),
                        'expiry': datetime.fromisoformat(contract['expiry']),
                        'option_type': contract['type'].upper(),
                        'price': float(contract['last']),
                        'volume': float(contract['volume']),
                        'open_interest': float(contract.get('openInterest', 0)),
                        'timestamp': datetime.now()
                    }
                    
                    self.db.save_option_data(data)
                    
                except Exception as e:
                    logger.error(f"处理合约数据失败: {str(e)}")
                    continue
            
            logger.info("数据同步完成")
            
        except Exception as e:
            logger.error(f"同步数据失败: {str(e)}")

    def start(self):
        """启动监控"""
        self.running = True
        logger.info("期权监控器已启动")
    
    def stop(self):
        """停止监控"""
        self.running = False
        logger.info("期权监控器已停止")
    
    def get_market_overview(self) -> Dict:
        """获取市场概览"""
        try:
            # 从数据库获取期权市场概览
            data = self.db.get_option_data(limit=50)
            return {
                'data': data,
                'timestamp': datetime.now()
            }
        except Exception as e:
            logger.error(f"获取期权市场概览失败: {str(e)}")
            return {}
    
    def get_price_analysis(self) -> Dict:
        """获取价格分析"""
        try:
            # 从数据库获取期权价格分析
            data = self.db.get_option_data(limit=50)
            return {
                'data': data,
                'timestamp': datetime.now()
            }
        except Exception as e:
            logger.error(f"获取期权价格分析失败: {str(e)}")
            return {}
    
    def get_alerts(self) -> List[Dict]:
        """获取预警信息"""
        try:
            # 从数据库获取期权预警
            alerts = self.db.get_alerts(limit=50)
            return alerts
        except Exception as e:
            logger.error(f"获取期权预警失败: {str(e)}")
            return []

    def get_historical_data(self, symbol: str) -> tuple:
        """获取历史数据"""
        try:
            # 从数据库获取期权历史数据
            data = self.db.get_option_data(symbol=symbol, limit=100)
            return data, {}
        except Exception as e:
            logger.error(f"获取期权历史数据失败: {str(e)}")
            return [], {}