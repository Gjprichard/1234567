from typing import Dict, List, Optional
import pandas as pd
import numpy as np
from datetime import datetime
import logging
from scipy.stats import norm

logger = logging.getLogger(__name__)

class OptionAnalyzer:
    def __init__(self):
        self.risk_free_rate = 0.02  # 无风险利率
        
    def analyze_market_data(self, data: pd.DataFrame) -> Dict:
        """分析期权市场数据"""
        try:
            if data.empty:
                return {}
                
            # 获取当前价格
            current_price = data['underlying_price'].iloc[0]
                
            metrics = {
                # 交易活跃度指标
                'total_volume': data['volume'].sum(),
                'total_open_interest': data['open_interest'].sum(),
                'volume_concentration': self._calculate_volume_concentration(data),
                
                # 波动率指标
                'avg_iv': data['iv'].mean(),
                'iv_skew': self._calculate_iv_skew(data),
                'iv_term_structure': self._calculate_iv_term_structure(data),
                
                # 期权比率指标
                'put_call_ratio': self._calculate_put_call_ratio(data),
                'put_call_open_interest_ratio': self._calculate_pc_oi_ratio(data),
                
                # 价格指标
                'current_price': current_price,
                'avg_premium': data['price'].mean(),
                'max_premium': data['price'].max(),
                'min_premium': data['price'].min(),
                
                # 风险指标
                'net_delta': self._calculate_net_delta(data),
                'net_gamma': self._calculate_net_gamma(data),
                'net_theta': self._calculate_net_theta(data),
                'net_vega': self._calculate_net_vega(data)
            }
            
            return metrics
            
        except Exception as e:
            logger.error(f"分析市场数据失败: {str(e)}")
            return {}
    
    def detect_anomalies(self, data: pd.DataFrame, config: Dict) -> List[Dict]:
        """检测市场异常"""
        try:
            anomalies = []
            
            # 成交量异常检测
            volume_anomalies = self._detect_volume_anomalies(
                data, 
                config.get('volume_threshold', 2.0)
            )
            anomalies.extend(volume_anomalies)
            
            # 价格异常检测
            if 'premium_change_15m' in data.columns:
                price_anomalies = self.detect_price_anomalies(data)
                anomalies.extend(price_anomalies)
            
            # IV异常检测
            if 'iv' in data.columns:
                iv_anomalies = self.detect_iv_anomalies(data)
                anomalies.extend(iv_anomalies)
            
            return anomalies
            
        except Exception as e:
            logger.error(f"检测市场异常失败: {str(e)}")
            return []
    
    def _calculate_volume_concentration(self, data: pd.DataFrame) -> float:
        """计算成交量集中度"""
        total_volume = data['volume'].sum()
        if total_volume == 0:
            return 0
        volume_shares = data['volume'] / total_volume
        return float((volume_shares ** 2).sum())
    
    def _calculate_iv_skew(self, data: pd.DataFrame) -> float:
        """计算隐含波动率偏斜"""
        calls = data[data['contract_type'] == 'CALL']
        puts = data[data['contract_type'] == 'PUT']
        
        if calls.empty or puts.empty:
            return 0
            
        return float(puts['iv'].mean() - calls['iv'].mean())
    
    def _calculate_iv_term_structure(self, data: pd.DataFrame) -> Dict:
        """计算隐含波动率期限结构"""
        return data.groupby('days_to_expiry')['iv'].mean().to_dict()
    
    def _calculate_put_call_ratio(self, data: pd.DataFrame) -> float:
        """计算看跌看涨比率"""
        calls_volume = data[data['contract_type'] == 'CALL']['volume'].sum()
        puts_volume = data[data['contract_type'] == 'PUT']['volume'].sum()
        
        return float(puts_volume / calls_volume) if calls_volume > 0 else 0
    
    def _calculate_pc_oi_ratio(self, data: pd.DataFrame) -> float:
        """计算看跌看涨持仓比率"""
        calls_oi = data[data['contract_type'] == 'CALL']['open_interest'].sum()
        puts_oi = data[data['contract_type'] == 'PUT']['open_interest'].sum()
        
        return float(puts_oi / calls_oi) if calls_oi > 0 else 0
    
    def _calculate_net_delta(self, data: pd.DataFrame) -> float:
        """计算净Delta"""
        return float(data['delta'].sum())
    
    def _calculate_net_gamma(self, data: pd.DataFrame) -> float:
        """计算净Gamma"""
        return float(data['gamma'].sum())
    
    def _calculate_net_theta(self, data: pd.DataFrame) -> float:
        """计算净Theta"""
        return float(data['theta'].sum())
    
    def _calculate_net_vega(self, data: pd.DataFrame) -> float:
        """计算净Vega"""
        return float(data['vega'].sum())
    
    def _detect_iv_anomalies(self, data: pd.DataFrame, threshold: float) -> List[Dict]:
        """检测隐含波动率异常"""
        try:
            iv_mean = data['iv'].mean()
            iv_std = data['iv'].std()
            
            anomalies = []
            for _, row in data.iterrows():
                z_score = (row['iv'] - iv_mean) / iv_std if iv_std > 0 else 0
                if abs(z_score) > threshold:
                    anomalies.append({
                        'contract_id': row['id'],
                        'symbol': row['symbol'],
                        'type': 'IV_ANOMALY',
                        'severity': 'HIGH' if abs(z_score) > threshold * 1.5 else 'MEDIUM',
                        'value': row['iv'],
                        'z_score': z_score,
                        'message': f"异常隐含波动率: {row['iv']:.2f}% (Z-score: {z_score:.2f})"
                    })
            
            return anomalies
            
        except Exception as e:
            logger.error(f"检测IV异常失败: {str(e)}")
            return []
    
    def _detect_volume_anomalies(self, data: pd.DataFrame, threshold: float) -> List[Dict]:
        """检测成交量异常"""
        try:
            volume_mean = data['volume'].mean()
            volume_std = data['volume'].std()
            
            anomalies = []
            for _, row in data.iterrows():
                z_score = (row['volume'] - volume_mean) / volume_std if volume_std > 0 else 0
                if abs(z_score) > threshold:
                    anomalies.append({
                        'contract_id': row['id'],
                        'symbol': row['symbol'],
                        'type': 'VOLUME_ANOMALY',
                        'severity': 'HIGH' if abs(z_score) > threshold * 1.5 else 'MEDIUM',
                        'value': row['volume'],
                        'z_score': z_score,
                        'message': f"异常成交量: {row['volume']:.0f} (Z-score: {z_score:.2f})"
                    })
            
            return anomalies
            
        except Exception as e:
            logger.error(f"检测成交量异常失败: {str(e)}")
            return []

    def detect_iv_anomalies(self, data: pd.DataFrame) -> List[Dict]:
        """检测隐含波动率异常"""
        try:
            if 'iv' not in data.columns:
                return []
            
            # 计算IV的Z-score
            mean_iv = data['iv'].mean()
            std_iv = data['iv'].std()
            if std_iv == 0:
                return []
            
            data['iv_zscore'] = (data['iv'] - mean_iv) / std_iv
            
            # 找出异常值
            anomalies = data[abs(data['iv_zscore']) > self.threshold].copy()
            
            return anomalies.to_dict('records')
            
        except Exception as e:
            logger.error(f"检测IV异常失败: {str(e)}")
            return []

    def detect_price_anomalies(self, data: pd.DataFrame) -> List[Dict]:
        """检测价格异常"""
        try:
            if 'premium_change_15m' not in data.columns:
                return []
            
            # 计算价格变化的Z-score
            mean_change = data['premium_change_15m'].mean()
            std_change = data['premium_change_15m'].std()
            if std_change == 0:
                return []
            
            data['price_zscore'] = (data['premium_change_15m'] - mean_change) / std_change
            
            # 找出异常值
            anomalies = data[abs(data['price_zscore']) > self.threshold].copy()
            
            return anomalies.to_dict('records')
            
        except Exception as e:
            logger.error(f"检测价格异常失败: {str(e)}")
            return [] 