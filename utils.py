from datetime import datetime, timedelta
import pandas as pd
from typing import Union, Any
import time
from flask import Flask, jsonify, request
from flask_cors import CORS
import streamlit as st

def calculate_streak(habit_logs):
    if not habit_logs:
        return 0
        
    dates = [datetime.strptime(log[2], '%Y-%m-%d').date() 
             for log in habit_logs]
    dates.sort(reverse=True)
    
    current_streak = 1
    current_date = dates[0]
    
    for date in dates[1:]:
        if (current_date - date).days == 1:
            current_streak += 1
            current_date = date
        else:
            break
            
    return current_streak

def calculate_completion_rate(habit_logs):
    if not habit_logs:
        return 0.0
        
    dates = [datetime.strptime(log[2], '%Y-%m-%d').date() 
             for log in habit_logs]
    
    # Calculate date range
    start_date = min(dates)
    end_date = max(dates)
    total_days = (end_date - start_date).days + 1
    
    # Calculate completion rate
    completion_rate = (len(dates) / total_days) * 100
    return round(completion_rate, 1)

class Utils:
    @staticmethod
    def format_price(price: float) -> str:
        """格式化价格显示"""
        return f"${price:,.4f}"
    
    @staticmethod
    def format_change(change: float) -> str:
        """格式化变化率显示"""
        return f"{change:+.2f}%"
    
    @staticmethod
    def format_volume(volume: float) -> str:
        """格式化成交量显示"""
        return f"${volume:,.0f}"
    
    @staticmethod
    def format_time(seconds: float) -> str:
        """格式化时间显示"""
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        return f"{hours}小时{minutes}分钟"

app = Flask(__name__)
CORS(app, resources={r"/api/*": {"origins": "*"}})

@app.route('/api/test', methods=['GET'])
def test():
    return jsonify({'message': 'API is working'})

@app.route('/api/market-data', methods=['GET'])
def get_market_data():
    try:
        if 'market_monitor' not in st.session_state:
            return jsonify({'error': 'Market monitor not initialized'}), 500
        market_monitor = st.session_state.market_monitor
        data = market_monitor.get_top_50_coins()
        if isinstance(data, pd.DataFrame):
            return jsonify(data.to_dict('records'))
        return jsonify([])
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/chart-data/<symbol>', methods=['GET'])
def get_chart_data(symbol):
    try:
        if 'market_monitor' not in st.session_state:
            return jsonify({'error': 'Market monitor not initialized'}), 500
        market_monitor = st.session_state.market_monitor
        df, metrics = market_monitor.get_historical_data(symbol)
        if isinstance(df, pd.DataFrame):
            return jsonify({
                'data': df.to_dict('records'),
                'metrics': metrics
            })
        return jsonify({'data': [], 'metrics': {}})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(host='localhost', port=5002, debug=True)
