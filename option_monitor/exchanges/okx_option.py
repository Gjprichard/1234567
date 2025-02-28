import ccxt
import pandas as pd
from typing import Dict, List, Optional, Tuple
import logging
import time
import random
from datetime import datetime

logger = logging.getLogger(__name__)

class OptionAPI:
    """通用期权API接口"""
    def __init__(self, exchange_id: str = 'okx', config: Dict = None):
        """
        初始化期权API客户端
        
        Args:
            exchange_id: 交易所ID (okx, deribit等)
            config: 配置参数
        """
        logger.info(f"初始化{exchange_id} API客户端...")
        
        self.exchange_id = exchange_id
        self.config = config or {}
        
        # 初始化CCXT交易所实例
        self.exchange = getattr(ccxt, exchange_id)({
            'enableRateLimit': True,
            'timeout': 30000,
            'rateLimit': 1000,
            'options': {
                'defaultType': 'option',
                'adjustForTimeDifference': True
            },
            **self.config
        })
        
        # 批量请求的最大合约数量
        self.batch_size = 20

    def get_option_markets(self, symbol: str = 'BTC/USDT') -> List[Dict]:
        """
        获取期权市场数据
        
        Args:
            symbol: 标的资产交易对
        """
        try:
            markets = self.exchange.load_markets()
            return [
                market for market in markets.values()
                if market.get('type') == 'option' 
                and market.get('base') == symbol.split('/')[0]
            ]
        except Exception as e:
            logger.error(f"获取期权市场数据失败: {str(e)}")
            return []

    def get_option_tickers(self, symbol: Optional[str] = None) -> Dict:
        """获取期权行情数据"""
        try:
            return self.exchange.fetch_tickers(symbol)
        except Exception as e:
            logger.error(f"获取期权行情失败: {str(e)}")
            return {}

    def get_option_chain(self, underlying: str) -> pd.DataFrame:
        """
        获取期权链数据
        
        Args:
            underlying: 标的资产代码 (如 'BTC')
        """
        try:
            # 使用重试机制获取市场数据
            markets = self._retry_request(
                self.get_option_markets,
                f"{underlying}/USDT",
                max_retries=3,
                delay=2.0
            )
            if not markets:
                logger.warning(f"未获取到{underlying}期权市场数据")
                return pd.DataFrame()

            # 使用重试机制获取行情数据
            tickers = self._retry_request(
                self.get_option_tickers,
                max_retries=3,
                delay=2.0
            )
            if not tickers:
                logger.warning(f"未获取到{underlying}期权行情数据")
                return pd.DataFrame()
            
            data = []
            for market in markets:
                ticker = tickers.get(market['symbol'])
                if not ticker:
                    continue
                    
                # 安全地获取和转换数据
                def safe_float(value, default=0.0):
                    try:
                        return float(value) if value is not None else default
                    except (ValueError, TypeError):
                        return default
                
                # 检查必要字段
                strike = market.get('strike')
                if strike is None:
                    continue
                    
                try:
                    data.append({
                        'symbol': market['symbol'],
                        'strike': safe_float(strike),
                        'expiry': market['expiry'],
                        'type': 'call' if market['option'] == 'call' else 'put',
                        'last': safe_float(ticker.get('last')),
                        'bid': safe_float(ticker.get('bid')),
                        'ask': safe_float(ticker.get('ask')),
                        'volume': safe_float(ticker.get('baseVolume')),
                        'openInterest': safe_float(ticker.get('openInterest'))
                    })
                except Exception as e:
                    logger.warning(f"处理合约 {market['symbol']} 数据失败: {str(e)}")
                    continue

            df = pd.DataFrame(data)
            if df.empty:
                logger.warning(f"未获取到{underlying}的有效期权数据")
                return df
            
            # 确保数据类型
            numeric_columns = ['strike', 'last', 'bid', 'ask', 'volume', 'openInterest']
            for col in numeric_columns:
                df[col] = pd.to_numeric(df[col], errors='coerce')
            
            return df

        except Exception as e:
            logger.error(f"获取期权链数据失败: {str(e)}")
            return pd.DataFrame()

    def _retry_request(self, func, *args, max_retries: int = 3, delay: float = 1.0):
        """请求重试机制，使用指数退避算法"""
        for attempt in range(max_retries):
            try:
                return func(*args)
            except Exception as e:
                if attempt == max_retries - 1:
                    raise
                # 使用指数退避算法
                wait_time = (2 ** attempt) * delay + random.uniform(0, 1)
                logger.warning(f"请求失败，{wait_time:.2f}秒后重试 (尝试 {attempt+1}/{max_retries}): {str(e)}")
                time.sleep(wait_time)

    def get_ticker(self, symbol: str) -> Dict:
        """获取市场数据"""
        try:
            ticker = self._retry_request(self.exchange.fetch_ticker, symbol)
            if not ticker:
                return {}
            
            return {
                'last': ticker.get('last', 0),
                'bid': ticker.get('bid', 0),
                'ask': ticker.get('ask', 0),
                'volume': ticker.get('baseVolume', 0),
                'openInterest': ticker.get('openInterest', 0),
                'timestamp': ticker.get('timestamp', None)
            }
        except Exception as e:
            logger.error(f"获取{symbol}市场数据失败: {str(e)}")
            return {}

    def get_contracts(self, underlying: str = 'BTC') -> List[Dict]:
        """获取期权合约列表"""
        try:
            logger.info(f"开始获取{underlying}期权合约列表...")
            response = self.exchange.publicGetPublicInstruments(params={
                'instType': 'OPTION',
                'uly': f'{underlying}-USD'
            })
            
            if not response or 'data' not in response:
                logger.error("获取合约列表失败: 无效的响应")
                return []
            
            contracts = response['data']
            return self._format_contracts(contracts)
            
        except Exception as e:
            logger.error(f"获取合约列表失败: {str(e)}")
            return []

    def get_market_data(self, symbol: str) -> Dict:
        """获取期权市场数据"""
        try:
            # 获取行情数据
            ticker_response = self.exchange.publicGetMarketTicker({
                'instId': symbol
            })
            
            # 获取标记价格
            mark_price_response = self.exchange.publicGetPublicMarkPrice({
                'instId': symbol
            })
            
            if not ticker_response or 'data' not in ticker_response:
                return {}
                
            ticker = ticker_response['data'][0]
            
            # 安全地获取和转换数据
            def safe_float(value):
                try:
                    return float(value) if value else None
                except (ValueError, TypeError):
                    return None
            
            return {
                'price': safe_float(ticker.get('last')),
                'underlying_price': (
                    safe_float(mark_price_response['data'][0].get('idxPx'))
                    if mark_price_response.get('data')
                    else None
                ),
                'bid': safe_float(ticker.get('bidPx')),
                'ask': safe_float(ticker.get('askPx')),
                'volume': safe_float(ticker.get('vol24h', 0)),
                'open_interest': int(float(ticker.get('oi', 0)) or 0),
                'iv': safe_float(ticker.get('iv'))
            }
            
        except Exception as e:
            logger.error(f"获取{symbol}市场数据失败: {str(e)}")
            return {}

    def _format_contract(self, contract: Dict) -> Dict:
        """格式化合约数据"""
        try:
            timestamp = int(contract['expTime']) / 1000
            expiry_date = pd.Timestamp.fromtimestamp(timestamp).strftime('%Y-%m-%d')
            
            return {
                'symbol': contract['instId'],
                'underlying': contract['uly'].split('-')[0],
                'contract_type': 'CALL' if contract['optType'] == 'C' else 'PUT',
                'strike_price': float(contract['stk']),
                'expiry_date': expiry_date,
                'settlement': contract['settleCcy'],
                'multiplier': float(contract['ctVal'])
            }
        except Exception as e:
            logger.error(f"格式化合约数据失败: {str(e)}")
            return {}

    def _format_contracts(self, contracts: List[Dict]) -> List[Dict]:
        """批量格式化合约数据"""
        return [c for c in [self._format_contract(contract) for contract in contracts] if c]

    def get_option_contracts(self, underlying: str) -> List[Dict]:
        """获取期权合约列表"""
        try:
            return self._retry_request(self.get_contracts, underlying)
        except Exception as e:
            logger.error(f"获取{underlying}期权合约列表失败: {str(e)}")
            return []

    def get_batch_tickers(self, symbols: List[str]) -> Dict[str, Dict]:
        """批量获取多个合约的行情数据"""
        try:
            logger.info(f"批量获取{len(symbols)}个合约的行情数据")
            
            # 将合约列表分成多个批次，每批最多batch_size个合约
            batches = [symbols[i:i + self.batch_size] for i in range(0, len(symbols), self.batch_size)]
            
            results = {}
            for batch_idx, batch in enumerate(batches):
                logger.info(f"处理批次 {batch_idx+1}/{len(batches)}, 包含 {len(batch)} 个合约")
                
                # 对于OKX，使用多个单独请求，但在批次之间添加延迟
                batch_results = {}
                for symbol in batch:
                    try:
                        ticker = self.get_ticker(symbol)
                        if ticker:
                            batch_results[symbol] = ticker
                    except Exception as e:
                        logger.error(f"获取{symbol}行情失败: {str(e)}")
                
                # 合并结果
                results.update(batch_results)
                
                # 批次之间添加延迟，避免触发频率限制
                if batch_idx < len(batches) - 1:
                    delay = 2.0 + random.uniform(0, 1)  # 添加随机抖动
                    logger.info(f"批次处理完成，等待 {delay:.2f} 秒后处理下一批次")
                    time.sleep(delay)
            
            logger.info(f"成功获取 {len(results)}/{len(symbols)} 个合约的行情数据")
            return results
            
        except Exception as e:
            logger.error(f"批量获取行情数据失败: {str(e)}")
            return {} 