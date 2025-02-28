import ccxt
import pandas as pd
from datetime import datetime
import streamlit as st
import asyncio
import nest_asyncio

# 应用 nest_asyncio 来处理事件循环问题
nest_asyncio.apply()

class BinanceMonitor:
    def __init__(self):
        try:
            # 使用 ccxt 替代直接的 binance 客户端
            self.exchange = ccxt.binance({
                'enableRateLimit': True,
                'options': {
                    'defaultType': 'spot'
                }
            })
        except Exception as e:
            st.error(f"Failed to initialize exchange: {str(e)}")
            self.exchange = None

    @st.cache_data(ttl=60)
    def get_top_50_coins(_self):  # 添加下划线前缀
        """获取前50个交易对的数据"""
        try:
            if not _self.exchange:
                return pd.DataFrame()

            # 获取所有USDT交易对的24小时行情
            tickers = _self.exchange.fetch_tickers()
            usdt_pairs = {
                symbol: ticker for symbol, ticker in tickers.items() 
                if symbol.endswith('/USDT')
            }

            if not usdt_pairs:
                st.warning("No trading pairs data retrieved")
                return pd.DataFrame()

            # 转换为DataFrame
            data = []
            for symbol, ticker in usdt_pairs.items():
                data.append({
                    'symbol': symbol.replace('/USDT', ''),
                    'name': symbol.replace('/USDT', ''),
                    'current_price': ticker['last'],
                    'volume': ticker['baseVolume'],
                    'quote_volume': ticker['quoteVolume']
                })

            df = pd.DataFrame(data)
            # 按成交额排序
            df = df.sort_values('quote_volume', ascending=False).head(50)
            return df

        except Exception as e:
            st.error(f"Error fetching market data: {str(e)}")
            return pd.DataFrame()

    def get_historical_data(self, symbol):
        """获取历史数据"""
        try:
            if not self.exchange:
                return [], None, None, None, None, None

            # 获取最近的K线数据 (获取90分钟的数据来计算两个15分钟周期)
            ohlcv = self.exchange.fetch_ohlcv(
                f"{symbol}/USDT",
                timeframe='1m',
                limit=90  # 获取90分钟的数据
            )

            if not ohlcv:
                return [], None, None, None, None, None

            df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
            
            # 获取当前、15分钟前和30分钟前的数据
            latest_price = float(df['close'].iloc[-1])
            latest_volume = float(df['volume'].iloc[-1])
            
            if len(df) >= 30:  # 确保有足够的数据
                # 当前15分钟周期的起始数据
                fifteen_min_price = float(df['close'].iloc[-15])
                fifteen_min_volume = float(df['volume'].iloc[-15:].sum())
                
                # 上一个15分钟周期的数据
                previous_fifteen_min_price = float(df['close'].iloc[-30])
                previous_fifteen_min_volume = float(df['volume'].iloc[-30:-15].sum())
                
                # 计算当前15分钟的变化率
                current_price_change = ((latest_price - fifteen_min_price) / fifteen_min_price) * 100
                current_volume_change = ((latest_volume - fifteen_min_volume) / fifteen_min_volume) * 100
                
                # 计算上一个15分钟的变化率
                previous_price_change = ((fifteen_min_price - previous_fifteen_min_price) / previous_fifteen_min_price) * 100
                previous_volume_change = ((fifteen_min_volume - previous_fifteen_min_volume) / previous_fifteen_min_volume) * 100
                
                # 计算变化率的差值
                price_change_diff = current_price_change - previous_price_change
                volume_change_diff = current_volume_change - previous_volume_change
            else:
                price_change_diff = 0
                volume_change_diff = 0

            return (
                df['close'].tolist(), 
                latest_volume,
                price_change_diff,  # 返回价格变化率的差值
                volume_change_diff  # 返回成交量变化率的差值
            )

        except Exception as e:
            st.error(f"Error fetching historical data for {symbol}: {str(e)}")
            return [], None, 0, 0

    def calculate_change_percentage(self, current_value, previous_value):
        """计算变化百分比"""
        if not previous_value or previous_value == 0:
            return 0
        return ((current_value - previous_value) / previous_value) * 100

    def generate_alerts(self, coin_data, price_threshold=0.1, volume_threshold=0.5):
        """生成警报"""
        if coin_data.empty:
            return []

        alerts = []
        for _, coin in coin_data.iterrows():
            try:
                prices, latest_volume, price_change_diff, volume_change_diff = self.get_historical_data(coin['symbol'])
                if not prices:
                    continue

                current_price = prices[-1]

                if abs(price_change_diff) > price_threshold or abs(volume_change_diff) > volume_threshold:
                    alerts.append({
                        'coin': coin['name'],
                        'symbol': coin['symbol'],
                        'current_price': current_price,
                        'price_change': price_change_diff,  # 使用变化率差值
                        'current_volume': latest_volume,
                        'volume_change': volume_change_diff  # 使用变化率差值
                    })
            except Exception as e:
                st.warning(f"Error processing alert data for {coin['symbol']}: {str(e)}")
                continue

        return sorted(alerts, key=lambda x: abs(x['price_change']), reverse=True)