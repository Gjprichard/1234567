import os
from pycoingecko import CoinGeckoAPI
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import streamlit as st

class CryptoMonitor:
    def __init__(self):
        self.cg = CoinGeckoAPI()
        self.cg.request_timeout = 20  # Reduced timeout for better response time

    @st.cache_data(ttl=60)  # 1 minute cache
    def get_top_50_coins(_self):  # Added underscore to fix caching
        """Get market data for top 50 cryptocurrencies"""
        try:
            coins = _self.cg.get_coins_markets(
                vs_currency='usd',
                order='market_cap_desc',
                per_page=50,
                sparkline=False
            )

            df = pd.DataFrame(coins)
            if df.empty:
                return pd.DataFrame()

            return df[['id', 'symbol', 'name', 'current_price']]
        except Exception as e:
            st.error(f"Error fetching data: {str(e)}")
            return pd.DataFrame()

    @st.cache_data(ttl=60)  # 1 minute cache
    def get_historical_data(_self, coin_id):  # Added underscore to fix caching
        """Get recent price and volume data"""
        try:
            data = _self.cg.get_coin_market_chart_by_id(
                id=coin_id,
                vs_currency='usd',
                days='0.042'  # Approximately 1 hour
            )

            if not data or 'prices' not in data or 'total_volumes' not in data:
                return [], None, None, None

            # Convert to DataFrame for time series processing
            price_df = pd.DataFrame(data['prices'], columns=['timestamp', 'price'])
            volume_df = pd.DataFrame(data['total_volumes'], columns=['timestamp', 'volume'])

            # Convert timestamps
            price_df['timestamp'] = pd.to_datetime(price_df['timestamp'], unit='ms')
            volume_df['timestamp'] = pd.to_datetime(volume_df['timestamp'], unit='ms')

            # Get latest and 15 minutes ago data
            fifteen_min_ago = datetime.now() - timedelta(minutes=15)

            latest_price = price_df.iloc[-1]['price']
            latest_volume = volume_df.iloc[-1]['volume']

            # Find closest data point to 15 minutes ago
            fifteen_min_price = price_df[price_df['timestamp'] <= fifteen_min_ago].iloc[-1]['price']
            fifteen_min_volume = volume_df[volume_df['timestamp'] <= fifteen_min_ago].iloc[-1]['volume']

            return price_df['price'].tolist(), latest_volume, fifteen_min_volume, fifteen_min_price

        except Exception as e:
            st.error(f"Error fetching historical data: {str(e)}")
            return [], None, None, None

    def calculate_change_percentage(self, current_value, previous_value):
        """Calculate percentage change"""
        if not previous_value or previous_value == 0:
            return 0
        return ((current_value - previous_value) / previous_value) * 100

    def generate_alerts(self, coin_data, price_threshold=0.1, volume_threshold=0.5):
        """Generate price and volume alerts"""
        alerts = []
        for _, coin in coin_data.iterrows():
            try:
                prices, latest_volume, fifteen_min_volume, fifteen_min_price = self.get_historical_data(coin['id'])
                if not prices:
                    continue

                current_price = prices[-1]
                price_change = self.calculate_change_percentage(current_price, fifteen_min_price)
                volume_change = self.calculate_change_percentage(latest_volume, fifteen_min_volume)

                # Generate alert if price or volume change exceeds threshold
                if abs(price_change) > price_threshold or abs(volume_change) > volume_threshold:
                    alerts.append({
                        'coin': coin['name'],
                        'symbol': coin['symbol'].upper(),
                        'current_price': current_price,
                        'previous_price': fifteen_min_price,
                        'price_change': price_change,
                        'current_volume': latest_volume,
                        'previous_volume': fifteen_min_volume,
                        'volume_change': volume_change
                    })
            except Exception:
                continue

        # Sort by absolute price change
        return sorted(alerts, key=lambda x: abs(x['price_change']), reverse=True)