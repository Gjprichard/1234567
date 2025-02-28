import numpy as np
from scipy.stats import norm
from typing import Dict

class GreeksCalculator:
    """期权希腊字母计算器"""
    def __init__(self, risk_free_rate: float = 0.02):
        self.risk_free_rate = risk_free_rate
        
    def calculate_greeks(self, S: float, K: float, T: float, r: float, sigma: float, option_type: str) -> Dict:
        """计算期权希腊字母
        
        参数:
        S: 标的价格
        K: 行权价
        T: 到期时间（年）
        r: 无风险利率
        sigma: 波动率
        option_type: 期权类型 ('CALL' 或 'PUT')
        """
        try:
            # 计算d1和d2
            d1 = (np.log(S/K) + (r + sigma**2/2)*T) / (sigma*np.sqrt(T))
            d2 = d1 - sigma*np.sqrt(T)
            
            # 计算N(d1)和N(d2)
            Nd1 = norm.cdf(d1)
            Nd2 = norm.cdf(d2)
            
            if option_type == 'CALL':
                # 看涨期权希腊字母
                delta = Nd1
                theta = (-S*sigma*np.exp(-d1**2/2)/(2*np.sqrt(2*np.pi*T)) - 
                        r*K*np.exp(-r*T)*Nd2)
                gamma = np.exp(-d1**2/2)/(S*sigma*np.sqrt(2*np.pi*T))
                vega = S*np.sqrt(T)*np.exp(-d1**2/2)/np.sqrt(2*np.pi)
                
            else:  # PUT
                # 看跌期权希腊字母
                delta = Nd1 - 1
                theta = (-S*sigma*np.exp(-d1**2/2)/(2*np.sqrt(2*np.pi*T)) + 
                        r*K*np.exp(-r*T)*(1-Nd2))
                gamma = np.exp(-d1**2/2)/(S*sigma*np.sqrt(2*np.pi*T))
                vega = S*np.sqrt(T)*np.exp(-d1**2/2)/np.sqrt(2*np.pi)
            
            return {
                'delta': delta,
                'gamma': gamma,
                'theta': theta,
                'vega': vega
            }
            
        except Exception as e:
            logger.error(f"计算希腊字母失败: {str(e)}")
            return {} 