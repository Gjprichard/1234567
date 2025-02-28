import numpy as np
import pandas as pd

class GradientAnalyzer:
    def __init__(self, window_size=24):
        # 设置分析窗口大小
        self.window_size = window_size
        
    def calculate_price_gradient(self, prices):
        """计算价格变化的梯度"""
        # 使用numpy的梯度函数计算价格变化率
        gradients = np.gradient(prices)
        return gradients
    
    def calculate_volume_gradient(self, volumes):
        """计算成交量变化的梯度"""
        # 使用numpy的梯度函数计算成交量变化率
        gradients = np.gradient(volumes)
        return gradients
    
    def detect_trend(self, gradients, threshold=0.05):
        """检测趋势方向"""
        # 计算最近的平均梯度
        recent_gradient = np.mean(gradients[-self.window_size:])
        
        if recent_gradient > threshold:
            return "强烈上涨"
        elif recent_gradient > threshold/2:
            return "温和上涨"
        elif recent_gradient < -threshold:
            return "强烈下跌"
        elif recent_gradient < -threshold/2:
            return "温和下跌"
        else:
            return "横盘整理"
    
    def calculate_momentum(self, price_gradients, volume_gradients):
        """计算动量指标"""
        # 结合价格和成交量梯度计算动量
        price_momentum = np.mean(price_gradients[-self.window_size:])
        volume_momentum = np.mean(volume_gradients[-self.window_size:])
        
        # 综合动量指标
        return price_momentum * volume_momentum
    
    def get_alert_level(self, momentum):
        """根据动量确定预警级别"""
        if abs(momentum) > 0.1:
            return "高度预警"
        elif abs(momentum) > 0.05:
            return "中度预警"
        elif abs(momentum) > 0.02:
            return "低度预警"
        else:
            return "正常波动"
