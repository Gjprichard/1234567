import pandas as pd
import numpy as np
from typing import Dict, List, Tuple

def calculate_market_metrics(df: pd.DataFrame) -> Dict:
    """计算市场指标"""
    try:
        metrics = {
            'total_volume': df['volume'].sum(),
            'avg_price_change': df['price_change_15m'].mean(),
            'avg_volume_change': df['volume_change_15m'].mean(),
            'up_tokens': len(df[df['price_change_15m'] > 0]),
            'down_tokens': len(df[df['price_change_15m'] < 0]),
            'volatility': df['price_change_15m'].std(),
            'timestamp': df['timestamp'].max()
        }
        return metrics
    except Exception as e:
        return {}

def calculate_option_metrics(df: pd.DataFrame) -> Dict:
    """计算期权市场指标"""
    try:
        call_volume = df[df['option_type'] == 'CALL']['volume'].sum()
        put_volume = df[df['option_type'] == 'PUT']['volume'].sum()
        
        metrics = {
            'total_volume': df['volume'].sum(),
            'call_volume': call_volume,
            'put_volume': put_volume,
            'pc_ratio': call_volume / put_volume if put_volume > 0 else float('inf'),
            'avg_strike': df['strike'].mean(),
            'total_open_interest': df['open_interest'].sum(),
            'timestamp': df['timestamp'].max()
        }
        return metrics
    except Exception as e:
        return {}

def detect_anomalies(df: pd.DataFrame, threshold: float = 2.0) -> List[Dict]:
    """检测异常数据"""
    try:
        # 计算z-score
        df['volume_zscore'] = (df['volume'] - df['volume'].mean()) / df['volume'].std()
        df['price_zscore'] = (df['price_change_15m'] - df['price_change_15m'].mean()) / df['price_change_15m'].std()
        
        # 检测异常
        anomalies = df[
            (df['volume_zscore'].abs() > threshold) | 
            (df['price_zscore'].abs() > threshold)
        ]
        
        return anomalies.to_dict('records')
    except Exception as e:
        return [] 