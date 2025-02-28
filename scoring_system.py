"""评分系统模块"""
import numpy as np
from typing import Dict, List, Optional
import logging
from datetime import datetime
from textblob import TextBlob
import pandas as pd

logger = logging.getLogger(__name__)

class ScoringSystem:
    """评分系统"""
    def __init__(self):
        self.sentiment_analyzer = TextBlob
        
    def calculate_sentiment_score(self, text: str) -> float:
        """计算情感得分"""
        try:
            analysis = self.sentiment_analyzer(text)
            # 将得分归一化到 [-1, 1] 范围
            return float(analysis.sentiment.polarity)
            
        except Exception as e:
            logger.error(f"计算情感得分失败: {str(e)}")
            return 0.0
    
    def calculate_policy_impact(self, policy_data: Dict) -> float:
        """计算政策影响得分"""
        try:
            # 基于政策类型、范围和严重程度计算得分
            impact_score = 0.0
            
            # 政策类型权重
            type_weights = {
                'regulation': 1.0,
                'monetary': 0.8,
                'fiscal': 0.6
            }
            
            # 计算得分
            if 'type' in policy_data:
                impact_score += type_weights.get(policy_data['type'], 0.5)
            
            if 'severity' in policy_data:
                impact_score *= policy_data['severity']
            
            # 归一化到 [-1, 1]
            return max(min(impact_score, 1.0), -1.0)
            
        except Exception as e:
            logger.error(f"计算政策影响得分失败: {str(e)}")
            return 0.0 