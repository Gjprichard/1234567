from dataclasses import dataclass
from typing import List, Dict
import pandas as pd
from datetime import datetime

@dataclass
class OptionContract:
    """期权合约数据结构"""
    symbol: str
    underlying: str
    contract_type: str
    strike_price: float
    expiry_date: str
    settlement: str
    multiplier: int
    
@dataclass
class OptionMarketData:
    """期权市场数据结构"""
    contract_id: int
    timestamp: int
    last_price: float
    mark_price: float
    volume: float
    open_interest: int
    bid: float = None
    ask: float = None
    iv: float = None
    delta: float = None
    gamma: float = None
    theta: float = None
    vega: float = None

@dataclass
class OptionChain:
    """期权链数据结构"""
    underlying: str
    expiry_date: str
    calls: pd.DataFrame
    puts: pd.DataFrame
    
    @classmethod
    def from_dataframe(cls, df: pd.DataFrame) -> 'OptionChain':
        """从DataFrame创建期权链"""
        if df.empty:
            return None
            
        # 按到期日分组
        grouped = df.groupby('expiry_date')
        chains = []
        
        for expiry, group in grouped:
            calls = group[group['contract_type'] == 'CALL']
            puts = group[group['contract_type'] == 'PUT']
            
            if not calls.empty and not puts.empty:
                chain = cls(
                    underlying=group['underlying'].iloc[0],
                    expiry_date=expiry,
                    calls=calls,
                    puts=puts
                )
                chains.append(chain)
                
        return chains 