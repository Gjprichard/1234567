from typing import Dict, List, Optional
from datetime import datetime
import pandas as pd
from .option_database import OptionDatabase
from .option_analyzer import OptionAnalyzer
from ..models.option_chain import OptionChain
from ..models.greeks import GreeksCalculator
import logging
import time
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from ..config import Config
from ..exchanges.okx_option import OptionAPI
from ..utils.performance import measure_time
import sqlite3
import schedule

logger = logging.getLogger(__name__)

class OptionMonitor:
    def __init__(self):
        """初始化期权监控器"""
        try:
            self.config = Config()
            self.db = OptionDatabase(self.config.db_path)
            self.analyzer = OptionAnalyzer()
            
            # 统一数据结构定义
            self.market_data_columns = [
                'contract_id', 'timestamp', 'last_price', 'mark_price',
                'volume', 'open_interest', 'bid', 'ask', 'iv',
                'delta', 'gamma', 'theta', 'vega'
            ]
            
            # 初始化API客户端
            exchange_config = self.config.exchange_config.get('okx', {})
            self.api = OptionAPI(
                exchange_id='okx',
                config=exchange_config
            )
            
            # 初始化调度器
            self.scheduler = BackgroundScheduler()
            self.setup_jobs()
            
            logger.info("期权监控器初始化完成")
            
        except Exception as e:
            logger.error(f"期权监控器初始化失败: {str(e)}")
            raise

    def start(self):
        """启动期权监控"""
        try:
            logger.info("期权监控器启动")
            
            # 设置定时任务
            self.scheduler.add_job(
                self.update_market_data,
                CronTrigger(minute='*'),  # 改为每分钟更新一次
                id='update_market_data'
            )
            self.scheduler.add_job(
                self.update_contracts,
                CronTrigger(minute='*/5'),   # 每5分钟更新一次合约列表
                id='update_contracts'
            )
            
            # 立即执行一次更新
            self.update_contracts()
            self.update_market_data()
            
            # 启动调度器
            if not self.scheduler.running:
                self.scheduler.start()
            
        except Exception as e:
            logger.error(f"启动期权监控失败: {str(e)}")
            raise

    def stop(self):
        """停止期权监控"""
        try:
            self.scheduler.shutdown()
            logger.info("期权监控器已停止")
        except Exception as e:
            logger.error(f"停止期权监控失败: {str(e)}")

    @measure_time
    def update_contracts(self):
        """更新合约列表"""
        try:
            all_contracts = []
            
            # 获取 BTC 和 ETH 的合约
            for underlying in ['BTC', 'ETH']:
                contracts = self.api.get_option_contracts(underlying)
                if contracts:
                    all_contracts.extend(contracts)
                else:
                    logger.warning(f"未获取到{underlying}的合约")
            
            if not all_contracts:
                logger.warning("未获取到任何合约")
                return
                
            # 保存所有合约
            if self.db.save_contracts(all_contracts):
                logger.info(f"成功更新了{len(all_contracts)}个合约")
            else:
                logger.error("保存合约失败")
                
        except Exception as e:
            logger.error(f"更新合约列表失败: {str(e)}")

    @measure_time
    def update_market_data(self):
        """更新期权市场数据"""
        try:
            logger.info("开始更新期权市场数据")
            
            # 获取活跃合约列表
            contracts = self.db.get_active_contracts()
            if not contracts:
                logger.warning("没有找到活跃合约")
                return
            
            # 批量获取市场数据
            market_data = []
            for contract in contracts:
                try:
                    data = self.api.get_market_data(contract['symbol'])
                    if data:
                        # 确保数据结构一致性
                        market_data.append({
                            'contract_id': contract['id'],
                            'timestamp': int(time.time()),
                            'last_price': data.get('last_price', 0.0),
                            'mark_price': data.get('mark_price', 0.0),
                            'volume': data.get('volume', 0.0),
                            'open_interest': data.get('open_interest', 0),
                            'bid': data.get('bid'),
                            'ask': data.get('ask'),
                            'iv': data.get('iv'),
                            'delta': data.get('delta'),
                            'gamma': data.get('gamma'),
                            'theta': data.get('theta'),
                            'vega': data.get('vega')
                        })
                except Exception as e:
                    logger.error(f"获取{contract['symbol']}市场数据失败: {str(e)}")
                    continue
                
            if market_data:
                # 批量保存市场数据
                success = self.db.save_market_data(market_data)
                if success:
                    logger.info(f"成功更新{len(market_data)}条市场数据")
                else:
                    logger.error("保存市场数据失败")
                
        except Exception as e:
            logger.error(f"更新市场数据失败: {str(e)}")

    def get_active_contracts(self, underlying: str) -> pd.DataFrame:
        """获取活跃期权合约"""
        return self.db.get_active_contracts(underlying)
        
    def analyze_market_data(self, data: pd.DataFrame) -> Dict:
        """分析期权市场数据"""
        return self.analyzer.analyze_market_data(data)
        
    def detect_anomalies(self, data: pd.DataFrame, thresholds: Dict) -> List[Dict]:
        """检测期权市场异常"""
        return self.analyzer.detect_anomalies(data, thresholds)
        
    def get_option_chain(self, underlying: str) -> OptionChain:
        """获取期权链数据"""
        try:
            # 获取活跃合约数据
            contracts = self.db.get_active_contracts(underlying)
            if not contracts:
                return None
            
            # 分离看涨和看跌期权
            calls = [c for c in contracts if c['contract_type'] == 'CALL']
            puts = [c for c in contracts if c['contract_type'] == 'PUT']
            
            # 获取最近到期日
            expiry_dates = sorted(set(c['expiry_date'] for c in contracts))
            nearest_expiry = expiry_dates[0] if expiry_dates else None
            
            return OptionChain(
                underlying=underlying,
                expiry_date=nearest_expiry,
                calls=calls,
                puts=puts
            )
        
        except Exception as e:
            logger.error(f"获取期权链数据失败: {str(e)}")
            return None
        
    def calculate_greeks(self, contract_id: int) -> Dict:
        """计算期权希腊字母"""
        try:
            # 获取合约数据
            contract_data = self.db.get_contract_data(contract_id)
            if not contract_data:
                return {}
            
            # 获取市场数据
            market_data = self.db.get_market_depth(contract_id)
            if not market_data:
                return {}
            
            # 计算到期时间（年）
            expiry_date = pd.to_datetime(contract_data['expiry_date'])
            days_to_expiry = (expiry_date - pd.Timestamp.now()).days
            T = days_to_expiry / 365.0
            
            # 调用希腊字母计算器
            greeks = self.greeks_calc.calculate_greeks(
                S=market_data['underlying_price'],
                K=contract_data['strike_price'],
                T=T,
                r=self.greeks_calc.risk_free_rate,
                sigma=market_data['iv'] / 100,  # 转换为小数
                option_type=contract_data['contract_type']
            )
            
            return greeks
        
        except Exception as e:
            logger.error(f"计算合约{contract_id}希腊字母失败: {str(e)}")
            return {}
        
    def get_volatility_surface(self, underlying: str) -> pd.DataFrame:
        """获取波动率曲面数据"""
        try:
            # 获取活跃合约数据
            data = self.get_active_contracts(underlying)
            if data.empty:
                return pd.DataFrame()
            
            # 创建波动率曲面数据
            surface_data = pd.pivot_table(
                data,
                values='iv',
                index='strike_price',
                columns='days_to_expiry',
                aggfunc='mean'
            ).reset_index()
            
            return surface_data
        
        except Exception as e:
            logger.error(f"计算波动率曲面失败: {str(e)}")
            return pd.DataFrame()

    def get_option_data(self, symbol: str = None) -> Dict:
        """获取期权数据和分析结果"""
        try:
            # 获取市场数据
            df = self.get_market_data(symbol)
            if df.empty:
                logger.warning("没有找到市场数据")
                return {}
            
            # 计算市场指标
            metrics = {
                'total_volume': df['volume'].sum(),
                'avg_iv': df['iv'].mean() if 'iv' in df else None,
                'timestamp': datetime.now().isoformat()
            }
            
            # 转换为期权链结构
            chains = OptionChain.from_dataframe(df)
            if chains:
                data = [{
                    'expiry': chain.expiry_date,
                    'underlying': chain.underlying,
                    'calls': chain.calls.to_dict('records'),
                    'puts': chain.puts.to_dict('records')
                } for chain in chains]
            else:
                data = []
            
            # 检测异常
            anomalies = self.analyzer.detect_anomalies(df)
            
            return {
                'data': data,
                'metrics': metrics,
                'anomalies': anomalies,
                'timestamp': datetime.now().isoformat()
            }
        
        except Exception as e:
            logger.error(f"获取期权数据失败: {str(e)}")
            return {}

    def get_market_data(self, symbol: str = None) -> pd.DataFrame:
        """获取市场数据，确保数据结构一致"""
        try:
            query = """
                SELECT m.*, c.symbol, c.strike_price, c.expiry_date, c.contract_type
                FROM option_market_data m
                JOIN option_contracts c ON m.contract_id = c.id
                WHERE m.timestamp >= ?
            """
            if symbol:
                query += " AND c.underlying = ?"
                params = (self.get_timestamp_threshold(), symbol)
            else:
                params = (self.get_timestamp_threshold(),)
                
            df = pd.read_sql_query(query, self.db.get_connection(), params=params)
            return df
            
        except Exception as e:
            logger.error(f"获取市场数据失败: {str(e)}")
            return pd.DataFrame()

    def _retry_operation(self, operation, max_retries: int = 3, delay: float = 1.0):
        """重试操作"""
        for attempt in range(max_retries):
            try:
                return operation()
            except Exception as e:
                if attempt == max_retries - 1:
                    raise
                logger.warning(f"操作失败，{delay}秒后重试: {str(e)}")
                time.sleep(delay) 

    def setup_jobs(self):
        # This method is mentioned in the __init__ method but not implemented in the provided code block
        # It's assumed to exist as it's called in the start method
        pass 

    def get_timestamp_threshold(self) -> int:
        """获取数据时间阈值"""
        # 默认获取最近5分钟的数据
        return int(time.time()) - 300 