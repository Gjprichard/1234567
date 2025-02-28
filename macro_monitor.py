"""宏观市场监控系统"""
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import logging
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from enum import Enum
import os
from database import MacroDatabase
from data_collector import DataCollector
import time
from functools import wraps
from logger_config import setup_logger
import threading
import random

# 创建宏观监控日志记录器
logger = setup_logger('macro_monitor')

class FactorType(Enum):
    """因子类型"""
    POLICY = "policy"           # 政策
    PEOPLE = "people"          # 重要人物
    MARKET = "market"          # 市场
    ECONOMY = "economy"        # 经济
    TECH = "tech"             # 技术
    SOCIAL = "social"          # 社交媒体
    EVENT = "event"           # 重大事件

@dataclass
class Factor:
    """监控因子"""
    id: str
    name: str
    type: FactorType
    weight: float
    description: str
    
class MacroMonitor:
    """宏观市场监控器"""
    def __init__(self, db_path: str = 'macro_data.db'):
        self.logger = logger
        # 初始化因子列表
        self.factors = self._init_factors()
        # 初始化数据库
        self.db = MacroDatabase(db_path)
        # 初始化数据收集器
        self.collector = DataCollector(self._get_collector_config())
        self.last_update_time = None
        self.update_interval = timedelta(hours=2.4)  # 24小时10次
        self.data_cache = {}
        self.last_update = datetime.now()
        
    def _get_collector_config(self) -> Dict:
        """获取数据收集器配置"""
        return {
            'twitter': {
                'consumer_key': os.getenv('TWITTER_CONSUMER_KEY', ''),
                'consumer_secret': os.getenv('TWITTER_CONSUMER_SECRET', ''),
                'access_token': os.getenv('TWITTER_ACCESS_TOKEN', ''),
                'access_token_secret': os.getenv('TWITTER_ACCESS_TOKEN_SECRET', '')
            },
            'alpha_vantage': {
                'api_key': os.getenv('ALPHA_VANTAGE_API_KEY', '')
            }
        }
    
    def _init_factors(self) -> Dict[str, Factor]:
        """初始化监控因子"""
        return {
            # 政策类因子
            'fed_policy': Factor(
                id='fed_policy',
                name='美联储政策',
                type=FactorType.POLICY,
                weight=0.25,
                description='美联储货币政策变化'
            ),
            'crypto_regulation': Factor(
                id='crypto_regulation',
                name='加密监管',
                type=FactorType.POLICY,
                weight=0.20,
                description='加密货币监管政策'
            ),
            
            # 市场类因子
            'market_sentiment': Factor(
                id='market_sentiment',
                name='市场情绪',
                type=FactorType.MARKET,
                weight=0.15,
                description='市场整体情绪指标'
            ),
            'institutional_flow': Factor(
                id='institutional_flow',
                name='机构资金流',
                type=FactorType.MARKET,
                weight=0.15,
                description='机构资金流向'
            ),
            
            # 经济类因子
            'inflation': Factor(
                id='inflation',
                name='通货膨胀',
                type=FactorType.ECONOMY,
                weight=0.10,
                description='通货膨胀数据'
            ),
            'employment': Factor(
                id='employment',
                name='就业数据',
                type=FactorType.ECONOMY,
                weight=0.05,
                description='就业市场数据'
            ),
            
            # 社交媒体因子
            'social_sentiment': Factor(
                id='social_sentiment',
                name='社交情绪',
                type=FactorType.SOCIAL,
                weight=0.05,
                description='社交媒体情绪分析'
            ),
            
            # 技术类因子
            'network_metrics': Factor(
                id='network_metrics',
                name='网络指标',
                type=FactorType.TECH,
                weight=0.05,
                description='区块链网络指标'
            )
        }
    
    def _rate_limit(func):
        """访问频率限制装饰器"""
        @wraps(func)
        def wrapper(self, *args, **kwargs):
            current_time = datetime.now()
            
            # 检查是否需要更新
            if (self.last_update_time is None or 
                current_time - self.last_update_time >= self.update_interval):
                # 更新数据
                result = func(self, *args, **kwargs)
                self.last_update_time = current_time
                self.data_cache[func.__name__] = result
                return result
            else:
                # 返回缓存数据
                logger.info(f"使用缓存数据 ({func.__name__})")
                return self.data_cache.get(func.__name__, {})
                
        return wrapper
    
    @_rate_limit
    def update_all_factors(self) -> bool:
        """更新所有因子数据"""
        try:
            success = True
            
            # 1. 更新政策因子
            fed_data = self.collector.collect_news_data()
            if fed_data:
                self.update_factor_data('fed_policy', {
                    'policy_type': 'monetary',
                    'impact_level': self._analyze_policy_impact(fed_data),
                    'sentiment': self._calculate_news_sentiment(fed_data)
                })
            
            # 2. 更新市场因子
            market_data = self._collect_market_data()
            if market_data:
                self.update_factor_data('market_sentiment', market_data)
            
            # 3. 更新经济因子
            economic_data = self.collector.collect_economic_data()
            if economic_data:
                self.update_factor_data('inflation', {
                    'cpi_change': economic_data.get('cpi', {}).get('change', 0),
                    'gdp_growth': economic_data.get('gdp', {}).get('growth', 0)
                })
            
            # 4. 更新社交媒体因子
            social_data = self.collector.collect_twitter_data([
                'elonmusk', 'cz_binance', 'saylor'
            ])
            if social_data:
                self.update_factor_data('social_sentiment', {
                    'sentiment_scores': self._analyze_social_sentiment(social_data),
                    'engagement_rates': self._calculate_engagement_rates(social_data),
                    'influence_scores': self._calculate_influence_scores(social_data)
                })
            
            # 5. 更新技术因子
            network_data = self.collector.collect_network_metrics()
            if network_data:
                self.update_factor_data('network_metrics', {
                    'hashrate_change': self._calculate_metric_change(
                        network_data.get('hashrate', {}).get('values', [])
                    ),
                    'difficulty_change': self._calculate_metric_change(
                        network_data.get('difficulty', {}).get('values', [])
                    ),
                    'transaction_growth': self._calculate_metric_change(
                        network_data.get('transaction_count', {}).get('values', [])
                    )
                })
            
            # 计算并保存总体评分
            total_score = self.calculate_total_score()
            factor_scores = {
                factor_id: self.data[factor_id]['score']
                for factor_id in self.factors
                if factor_id in self.data
            }
            self.db.save_score_history(total_score, factor_scores)
            
            return success
            
        except Exception as e:
            logger.error(f"更新因子数据失败: {str(e)}")
            return False
    
    def update_factor_data(self, factor_id: str, data: Dict) -> bool:
        """更新因子数据"""
        try:
            if factor_id not in self.factors:
                logger.error(f"因子 {factor_id} 不存在")
                return False
            
            # 计算得分
            score = self._calculate_factor_score(factor_id, data)
            
            # 保存到数据库
            self.db.save_factor_data(factor_id, data, score)
            
            # 更新内存中的数据
            self.data[factor_id] = {
                'timestamp': datetime.now(),
                'data': data,
                'score': score
            }
            
            return True
            
        except Exception as e:
            logger.error(f"更新因子数据失败: {str(e)}")
            return False
    
    def _calculate_factor_score(self, factor_id: str, data: Dict) -> float:
        """计算单个因子的得分"""
        try:
            factor = self.factors[factor_id]
            
            # 根据因子类型计算得分
            if factor.type == FactorType.POLICY:
                return self._calculate_policy_score(data)
            elif factor.type == FactorType.MARKET:
                return self._calculate_market_score(data)
            elif factor.type == FactorType.ECONOMY:
                return self._calculate_economy_score(data)
            elif factor.type == FactorType.SOCIAL:
                return self._calculate_social_score(data)
            elif factor.type == FactorType.TECH:
                return self._calculate_tech_score(data)
            
            return 0.0
            
        except Exception as e:
            logger.error(f"计算因子得分失败: {str(e)}")
            return 0.0
    
    def _calculate_policy_score(self, data: Dict) -> float:
        """计算政策类因子得分"""
        try:
            # 政策类型权重
            policy_weights = {
                'monetary': 1.0,  # 货币政策
                'regulatory': 0.8,  # 监管政策
                'fiscal': 0.6     # 财政政策
            }
            
            # 影响程度权重
            impact_weights = {
                'high': 1.0,
                'medium': 0.6,
                'low': 0.3
            }
            
            policy_type = data.get('policy_type', 'regulatory')
            impact_level = data.get('impact_level', 'medium')
            sentiment = data.get('sentiment', 0)  # -1 到 1 的情感得分
            
            # 计算基础得分
            base_score = policy_weights.get(policy_type, 0.5) * impact_weights.get(impact_level, 0.6)
            
            # 结合情感得分
            final_score = base_score * (1 + sentiment)
            
            # 归一化到 [-1, 1]
            return max(min(final_score, 1.0), -1.0)
            
        except Exception as e:
            logger.error(f"计算政策得分失败: {str(e)}")
            return 0.0
    
    def _calculate_market_score(self, data: Dict) -> float:
        """计算市场类因子得分"""
        try:
            # 获取市场指标
            volume_change = data.get('volume_change', 0)  # 成交量变化
            price_change = data.get('price_change', 0)    # 价格变化
            volatility = data.get('volatility', 0)        # 波动率
            
            # 计算综合得分
            score = (
                0.4 * np.tanh(volume_change / 100) +  # 成交量变化的影响
                0.4 * np.tanh(price_change / 10) +    # 价格变化的影响
                0.2 * (-np.tanh(volatility / 50))     # 波动率的影响（负面）
            )
            
            return max(min(score, 1.0), -1.0)
            
        except Exception as e:
            logger.error(f"计算市场得分失败: {str(e)}")
            return 0.0
    
    def _calculate_economy_score(self, data: Dict) -> float:
        """计算经济类因子得分"""
        try:
            # 获取经济指标
            cpi_change = data.get('cpi_change', 0)  # CPI同比变化
            gdp_growth = data.get('gdp_growth', 0)  # GDP增长率
            employment_change = data.get('employment_change', 0)  # 就业变化
            
            # 设置指标阈值
            CPI_THRESHOLD = 2.0  # 理想通胀率
            GDP_THRESHOLD = 2.5  # 理想GDP增长率
            
            # 计算CPI得分（偏离目标值越远越差）
            cpi_score = -abs(cpi_change - CPI_THRESHOLD) / 5  # 归一化到 [-1, 1]
            
            # 计算GDP得分
            gdp_score = np.tanh(gdp_growth / GDP_THRESHOLD)
            
            # 计算就业得分
            employment_score = np.tanh(employment_change / 2)
            
            # 加权平均
            score = (
                0.4 * cpi_score +      # CPI权重
                0.4 * gdp_score +      # GDP权重
                0.2 * employment_score # 就业权重
            )
            
            return max(min(score, 1.0), -1.0)
            
        except Exception as e:
            logger.error(f"计算经济得分失败: {str(e)}")
            return 0.0
    
    def _calculate_social_score(self, data: Dict) -> float:
        """计算社交媒体情绪得分"""
        try:
            # 获取社交媒体指标
            sentiment_scores = data.get('sentiment_scores', [])  # 情感分析得分列表
            engagement_rates = data.get('engagement_rates', [])  # 参与度列表
            influence_scores = data.get('influence_scores', [])  # 影响力得分列表
            
            if not sentiment_scores:
                return 0.0
            
            # 计算加权情感得分
            weighted_scores = []
            for sentiment, engagement, influence in zip(
                sentiment_scores, 
                engagement_rates, 
                influence_scores
            ):
                # 结合参与度和影响力的权重
                weight = engagement * influence
                weighted_scores.append(sentiment * weight)
            
            # 计算最终得分
            if weighted_scores:
                final_score = sum(weighted_scores) / sum(
                    engagement * influence 
                    for engagement, influence in zip(engagement_rates, influence_scores)
                )
                return max(min(final_score, 1.0), -1.0)
            
            return 0.0
            
        except Exception as e:
            logger.error(f"计算社交媒体得分失败: {str(e)}")
            return 0.0
    
    def _calculate_tech_score(self, data: Dict) -> float:
        """计算技术指标得分"""
        try:
            # 获取网络指标
            hashrate_change = data.get('hashrate_change', 0)  # 算力变化
            difficulty_change = data.get('difficulty_change', 0)  # 难度变化
            transaction_growth = data.get('transaction_growth', 0)  # 交易量增长
            
            # 计算各指标得分
            hashrate_score = np.tanh(hashrate_change / 20)  # 算力变化得分
            difficulty_score = np.tanh(difficulty_change / 15)  # 难度变化得分
            transaction_score = np.tanh(transaction_growth / 10)  # 交易量得分
            
            # 加权平均
            score = (
                0.3 * hashrate_score +     # 算力权重
                0.3 * difficulty_score +   # 难度权重
                0.4 * transaction_score    # 交易量权重
            )
            
            return max(min(score, 1.0), -1.0)
            
        except Exception as e:
            logger.error(f"计算技术指标得分失败: {str(e)}")
            return 0.0
    
    def calculate_total_score(self) -> float:
        """计算总体评分"""
        try:
            total_score = 0.0
            total_weight = 0.0
            
            for factor_id, factor in self.factors.items():
                if factor_id in self.data:
                    score = self.data[factor_id]['score']
                    total_score += score * factor.weight
                    total_weight += factor.weight
            
            if total_weight > 0:
                final_score = total_score / total_weight
                return final_score
            
            return 0.0
            
        except Exception as e:
            logger.error(f"计算总体评分失败: {str(e)}")
            return 0.0
    
    @_rate_limit
    def get_factor_analysis(self) -> Dict:
        """获取因子分析"""
        try:
            analysis = {}
            for factor_id, factor in self.factors.items():
                # 从数据库获取最新数据
                factor_data = self.db.get_latest_factor_data(factor_id)
                if factor_data:
                    analysis[factor_id] = {
                        'name': factor.name,
                        'type': factor.type.value,
                        'weight': factor.weight,
                        'score': factor_data['score'],
                        'last_update': factor_data['timestamp']
                    }
            return analysis
            
        except Exception as e:
            logger.error(f"获取因子分析失败: {str(e)}")
            return {}
    
    @_rate_limit
    def get_score_summary(self) -> Dict:
        """获取评分汇总"""
        try:
            # 获取最近7天的评分历史
            score_history = self.db.get_score_history(days=7)
            
            if not score_history:
                return {
                    'current_score': 0.0,
                    'score_change_24h': 0.0,
                    'top_factors': [],
                    'update_time': datetime.now().isoformat()
                }
            
            current_score = score_history[-1]['total_score']
            
            # 计算24小时变化
            day_ago_score = next(
                (s['total_score'] for s in score_history 
                 if (datetime.now() - datetime.fromisoformat(s['timestamp'])).days == 1),
                current_score
            )
            score_change = current_score - day_ago_score
            
            # 获取最新的因子得分
            latest_factor_scores = score_history[-1]['factor_scores']
            
            # 获取影响最大的因子
            factor_impacts = [
                (factor_id, abs(score * self.factors[factor_id].weight))
                for factor_id, score in latest_factor_scores.items()
            ]
            
            top_factors = sorted(factor_impacts, key=lambda x: x[1], reverse=True)[:3]
            
            return {
                'current_score': current_score,
                'score_change_24h': score_change,
                'top_factors': [
                    {
                        'id': f_id,
                        'name': self.factors[f_id].name,
                        'impact': impact
                    }
                    for f_id, impact in top_factors
                ],
                'update_time': score_history[-1]['timestamp']
            }
            
        except Exception as e:
            logger.error(f"获取评分汇总失败: {str(e)}")
            return {
                'current_score': 0.0,
                'score_change_24h': 0.0,
                'top_factors': [],
                'update_time': datetime.now().isoformat()
            }

    def start_update_task(self):
        """启动定时更新任务"""
        def update_task():
            while True:
                try:
                    self.update_macro_data()
                    time.sleep(7200)  # 每2小时更新一次 (2 * 60 * 60 = 7200秒)
                except Exception as e:
                    self.logger.error(f"更新任务异常: {str(e)}")
                    time.sleep(5)
        
        update_thread = threading.Thread(target=update_task)
        update_thread.daemon = True
        update_thread.start()
        self.logger.info("启动宏观数据更新任务")

    def clean_expired_data(self):
        """清理过期数据"""
        try:
            with self.db.get_connection() as conn:
                cursor = conn.cursor()
                
                # 删除1天前的数据
                cursor.execute('''
                    DELETE FROM macro_data 
                    WHERE timestamp < datetime('now', '-1 day')
                ''')
                
                conn.commit()
                
        except Exception as e:
            self.logger.error(f"清理过期数据失败: {str(e)}")

    def get_score_summary(self):
        """获取评分概览"""
        return {
            'overall_score': round(random.uniform(0, 100), 2),
            'market_sentiment': round(random.uniform(-1, 1), 2),
            'risk_level': random.choice(['low', 'medium', 'high']),
            'update_time': datetime.now().isoformat()
        }
        
    def check_status(self):
        """检查监控器状态"""
        return {
            'status': 'running',
            'last_update': self.last_update.isoformat()
        } 