# 必须是第一个 Streamlit 命令
import streamlit as st
st.set_page_config(
    page_title="市场监控系统",
    layout="wide",
    initial_sidebar_state="expanded"
)

# 检查jinja2版本
import jinja2
print(f"Jinja2版本: {jinja2.__version__}")

# 尝试修复jinja2版本问题
import subprocess
import sys
try:
    print("尝试重新安装jinja2...")
    subprocess.check_call([sys.executable, "-m", "pip", "install", "--force-reinstall", "jinja2>=3.0.0"])
    print("jinja2重新安装完成")
    
    # 重新导入jinja2
    import importlib
    importlib.reload(jinja2)
    print(f"重新加载后的Jinja2版本: {jinja2.__version__}")
except Exception as e:
    print(f"重新安装jinja2失败: {str(e)}")

import pandas as pd
import plotly.graph_objects as go
from datetime import datetime, timedelta
import time
from market_monitor import MarketMonitor
from option_monitor import OptionMonitor
import logging
import numpy as np
from plotly.subplots import make_subplots
from okx_monitor import OKXOptionMonitor
import requests
from typing import Dict, List
from database import Database
import functools
import random
# 导入API工具模块
from api_utils import APIClient
import os
from dotenv import load_dotenv
import ccxt

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# 初始化数据库和市场监控器
db = Database()
monitor = MarketMonitor()

# 加载环境变量
load_dotenv()

# 设置OKX API凭据（如果环境变量中没有，则使用默认测试值）
os.environ.setdefault('REST_API_URL', 'https://www.okx.com')
os.environ.setdefault('API_KEY', 'your-api-key')  # 使用默认测试值
os.environ.setdefault('API_SECRET', 'your-api-secret')  # 使用默认测试值
os.environ.setdefault('API_PASSPHRASE', 'your-passphrase')  # 使用默认测试值

# 初始化期权监控器
option_monitor = OKXOptionMonitor()

# API配置
API_BASE_URL = "http://localhost:5002/api"

# 初始化API客户端
api_client = APIClient(
    base_url=API_BASE_URL,
    cache_ttl=60,  # 默认缓存有效期（秒）
    min_request_interval=5.0,  # 默认最小请求间隔（秒）
    timeout=10,
    max_retries=3
)

def fetch_data(endpoint: str) -> dict:
    """从API获取数据，使用APIClient处理缓存和限速"""
    return api_client.fetch(endpoint)

def format_number(value, prefix='$'):
    """格式化数字显示"""
    if value >= 1_000_000_000:
        return f"{prefix}{value/1_000_000_000:.2f}B"
    elif value >= 1_000_000:
        return f"{prefix}{value/1_000_000:.2f}M"
    else:
        return f"{prefix}{value:,.2f}"

def format_price(price):
    return f"${price:,.2f}"

def format_change(change):
    return f"{change:+.2f}%" if change else "0.00%"

def format_volume(volume):
    if volume >= 1_000_000_000:
        return f"${volume/1_000_000_000:.2f}B"
    elif volume >= 1_000_000:
        return f"${volume/1_000_000:.2f}M"
    else:
        return f"${volume:,.0f}"

def create_candlestick_chart(df, symbol):
    """创建专业的K线图"""
    # 创建主图（K线）
    fig = make_subplots(
        rows=2, 
        cols=1,
        row_heights=[0.7, 0.3],
        vertical_spacing=0.05,
        shared_xaxes=True
    )
    
    # 添加K线
    fig.add_trace(
        go.Candlestick(
            x=pd.to_datetime(df['timestamp'], unit='s'),
            open=df['open'],
            high=df['high'],
            low=df['low'],
            close=df['close'],
            name='K线',
            increasing_line_color='#26A69A',
            decreasing_line_color='#EF5350',
            showlegend=False
        ),
        row=1, col=1
    )
    
    # 添加均线
    ma5 = df['close'].rolling(window=5).mean()
    ma10 = df['close'].rolling(window=10).mean()
    ma20 = df['close'].rolling(window=20).mean()
    
    fig.add_trace(
        go.Scatter(x=pd.to_datetime(df['timestamp'], unit='s'), y=ma5, 
                  name='MA5', line=dict(color='#2962FF', width=1)),
        row=1, col=1
    )
    fig.add_trace(
        go.Scatter(x=pd.to_datetime(df['timestamp'], unit='s'), y=ma10, 
                  name='MA10', line=dict(color='#FF6D00', width=1)),
        row=1, col=1
    )
    fig.add_trace(
        go.Scatter(x=pd.to_datetime(df['timestamp'], unit='s'), y=ma20, 
                  name='MA20', line=dict(color='#E040FB', width=1)),
        row=1, col=1
    )
    
    # 添加成交量
    colors = ['#26A69A' if close >= open_ else '#EF5350' 
              for close, open_ in zip(df['close'], df['open'])]
    
    fig.add_trace(
        go.Bar(
            x=pd.to_datetime(df['timestamp'], unit='s'),
            y=df['volume'],
            name='成交量',
            marker_color=colors,
            showlegend=False
        ),
        row=2, col=1
    )
    
    # 更新布局
    fig.update_layout(
        title=dict(
            text=f'{symbol}/USDT',
            font=dict(size=20, color='#E0E0E0'),
            x=0.5,
            y=0.97
        ),
        template='plotly_dark',
        plot_bgcolor='#1E1E1E',
        paper_bgcolor='#1E1E1E',
        height=700,
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1,
            xanchor="center",
            x=0.5,
            bgcolor='rgba(30,30,30,0.8)'
        ),
        margin=dict(l=5, r=5, t=50, b=5)
    )
    
    # 更新坐标轴样式
    fig.update_xaxes(
        gridcolor='#2B2B2B',
        showgrid=True,
        tickformat='%H:%M',
        tickfont=dict(size=10),
        row=2, col=1
    )
    
    fig.update_yaxes(
        gridcolor='#2B2B2B',
        showgrid=True,
        tickformat=',.2f',
        tickprefix='$',
        side='right',
        row=1, col=1
    )
    
    fig.update_yaxes(
        gridcolor='#2B2B2B',
        showgrid=True,
        tickformat=',.0f',
        title='成交量',
        row=2, col=1
    )
    
    # 添加交互功能
    fig.update_layout(
        hovermode='x unified',
        hoverdistance=100,
        spikedistance=1000,
        xaxis=dict(
            showspikes=True,
            spikethickness=1,
            spikecolor='#999999',
            spikemode='across'
        ),
        xaxis2=dict(
            showspikes=True,
            spikethickness=1,
            spikecolor='#999999',
            spikemode='across'
        ),
        yaxis=dict(
            showspikes=True,
            spikethickness=1,
            spikecolor='#999999',
            spikemode='across'
        )
    )
    
    return fig

def create_market_metrics(kline_data, metrics):
    """创建市场指标展示"""
    cols = st.columns(4)
    
    # 最新价格
    with cols[0]:
        price_change = ((kline_data['close'].iloc[-1] - kline_data['close'].iloc[0]) / kline_data['close'].iloc[0]) * 100
        st.metric(
            "最新价格",
            format_price(kline_data['close'].iloc[-1]),
            format_change(price_change),
            delta_color="normal" if price_change >= 0 else "inverse"
        )
    
    # 24h最高价
    with cols[1]:
        high_change = ((metrics['high'] - kline_data['close'].iloc[-1]) / kline_data['close'].iloc[-1]) * 100
        st.metric(
            "24h最高",
            format_price(metrics['high']),
            format_change(high_change),
            delta_color="normal" if high_change >= 0 else "inverse"
        )
    
    # 24h最低价
    with cols[2]:
        low_change = ((metrics['low'] - kline_data['close'].iloc[-1]) / kline_data['close'].iloc[-1]) * 100
        st.metric(
            "24h最低",
            format_price(metrics['low']),
            format_change(low_change),
            delta_color="normal" if low_change >= 0 else "inverse"
        )
    
    # 24h成交量
    with cols[3]:
        volume_change = metrics.get('volume_change', 0)
        st.metric(
            "24h成交量",
            format_volume(metrics['volume']),
            format_change(volume_change),
            delta_color="normal" if volume_change >= 0 else "inverse"
        )

def create_volume_analysis(df):
    """创建交易量分析图表"""
    fig = go.Figure()
    
    # 计算成交量移动平均
    vma5 = df['volume'].rolling(window=5).mean()
    vma10 = df['volume'].rolling(window=10).mean()
    
    # 添加成交量柱状图
    fig.add_trace(go.Bar(
        x=pd.to_datetime(df['timestamp'], unit='s'),
        y=df['volume'],
        name='成交量',
        marker_color=np.where(df['close'] >= df['open'], '#26A69A', '#EF5350'),
        opacity=0.8
    ))
    
    # 添加成交量均线
    fig.add_trace(go.Scatter(
        x=pd.to_datetime(df['timestamp'], unit='s'),
        y=vma5,
        name='VMA5',
        line=dict(color='#2962FF', width=1)
    ))
    
    fig.add_trace(go.Scatter(
        x=pd.to_datetime(df['timestamp'], unit='s'),
        y=vma10,
        name='VMA10',
        line=dict(color='#FF6D00', width=1)
    ))
    
    # 更新布局
    fig.update_layout(
        title=dict(
            text='成交量分析',
            font=dict(size=20, color='#E0E0E0')
        ),
        height=300,
        template='plotly_dark',
        plot_bgcolor='#1E1E1E',
        paper_bgcolor='#1E1E1E',
        showlegend=True,
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1
        ),
        margin=dict(l=10, r=10, t=50, b=10)
    )
    
    return fig

def create_technical_indicators(df):
    """创建技术指标图表"""
    # 计算RSI
    delta = df['close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
    rs = gain / loss
    rsi = 100 - (100 / (1 + rs))
    
    # 计算MACD
    exp1 = df['close'].ewm(span=12, adjust=False).mean()
    exp2 = df['close'].ewm(span=26, adjust=False).mean()
    macd = exp1 - exp2
    signal = macd.ewm(span=9, adjust=False).mean()
    hist = macd - signal
    
    # 创建图表
    fig = make_subplots(rows=2, cols=1, 
                        row_heights=[0.5, 0.5],
                        subplot_titles=('RSI (14)', 'MACD'))
    
    # 添加RSI
    fig.add_trace(
        go.Scatter(
            x=pd.to_datetime(df['timestamp'], unit='s'),
            y=rsi,
            name='RSI',
            line=dict(color='#B2DFDB')
        ),
        row=1, col=1
    )
    
    # 添加RSI参考线
    fig.add_hline(y=70, line_dash="dash", line_color="#EF5350", row=1, col=1)
    fig.add_hline(y=30, line_dash="dash", line_color="#26A69A", row=1, col=1)
    
    # 添加MACD
    fig.add_trace(
        go.Scatter(
            x=pd.to_datetime(df['timestamp'], unit='s'),
            y=macd,
            name='MACD',
            line=dict(color='#2962FF')
        ),
        row=2, col=1
    )
    
    fig.add_trace(
        go.Scatter(
            x=pd.to_datetime(df['timestamp'], unit='s'),
            y=signal,
            name='Signal',
            line=dict(color='#FF6D00')
        ),
        row=2, col=1
    )
    
    fig.add_trace(
        go.Bar(
            x=pd.to_datetime(df['timestamp'], unit='s'),
            y=hist,
            name='Histogram',
            marker_color=np.where(hist >= 0, '#26A69A', '#EF5350')
        ),
        row=2, col=1
    )
    
    # 更新布局
    fig.update_layout(
        height=400,
        template='plotly_dark',
        plot_bgcolor='#1E1E1E',
        paper_bgcolor='#1E1E1E',
        showlegend=True,
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1
        )
    )
    
    return fig

def create_market_depth(symbol):
    """创建市场深度图"""
    try:
        # 获取订单簿数据
        orderbook = monitor.exchange.fetch_order_book(f"{symbol}/USDT")
        
        bids = pd.DataFrame(orderbook['bids'], columns=['price', 'amount'])
        asks = pd.DataFrame(orderbook['asks'], columns=['price', 'amount'])
        
        # 计算累计数量
        bids['cumulative'] = bids['amount'].cumsum()
        asks['cumulative'] = asks['amount'].cumsum()
        
        # 创建图表
        fig = go.Figure()
        
        # 添加买单深度
        fig.add_trace(go.Scatter(
            x=bids['price'],
            y=bids['cumulative'],
            name='买单',
            fill='tonexty',
            fillcolor='rgba(38,166,154,0.3)',
            line=dict(color='#26A69A')
        ))
        
        # 添加卖单深度
        fig.add_trace(go.Scatter(
            x=asks['price'],
            y=asks['cumulative'],
            name='卖单',
            fill='tonexty',
            fillcolor='rgba(239,83,80,0.3)',
            line=dict(color='#EF5350')
        ))
        
        # 更新布局
        fig.update_layout(
            title=dict(
                text='市场深度',
                font=dict(size=20, color='#E0E0E0')
            ),
            height=300,
            template='plotly_dark',
            plot_bgcolor='#1E1E1E',
            paper_bgcolor='#1E1E1E',
            showlegend=True,
            legend=dict(
                orientation="h",
                yanchor="bottom",
                y=1.02,
                xanchor="right",
                x=1
            ),
            xaxis_title='价格',
            yaxis_title='累计数量'
        )
        
        return fig
    except Exception as e:
        logger.error(f"获取市场深度数据失败: {str(e)}")
        return None

def create_market_overview(df):
    """创建市场概览"""
    st.subheader("市场概览")
    
    # 计算市场统计
    total_volume = df['quote_volume'].sum()
    gainers = len(df[df['price_change_15m'] > 0])
    losers = len(df[df['price_change_15m'] < 0])
    unchanged = len(df[df['price_change_15m'] == 0])
    total_active = gainers + losers + unchanged
    
    # 显示统计数据
    cols = st.columns(4)
    with cols[0]:
        st.metric(
            "总交易量",
            format_volume(total_volume)
        )
    with cols[1]:
        st.metric(
            "上涨数量",
            f"{gainers}",
            f"{(gainers/total_active*100) if total_active > 0 else 0:.1f}%"
        )
    with cols[2]:
        st.metric(
            "下跌数量",
            f"{losers}",
            f"{(losers/total_active*100) if total_active > 0 else 0:.1f}%"
        )
    with cols[3]:
        st.metric(
            "交易对数量",
            f"{len(df)}",
            f"持平: {unchanged}"
        )

def create_market_tables(df):
    """创建市场数据表格"""
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("涨幅榜")
        gainers_df = df.nlargest(5, 'price_change_15m')[
            ['symbol', 'last', 'price_change_15m', 'volume_change_15m']
        ]
        # 手动格式化
        formatted_gainers = gainers_df.copy()
        formatted_gainers['last'] = formatted_gainers['last'].apply(lambda x: format_price(x))
        formatted_gainers['price_change_15m'] = formatted_gainers['price_change_15m'].apply(lambda x: format_change(x))
        formatted_gainers['volume_change_15m'] = formatted_gainers['volume_change_15m'].apply(lambda x: format_change(x))
        st.dataframe(formatted_gainers, use_container_width=True)
    
    with col2:
        st.subheader("跌幅榜")
        losers_df = df.nsmallest(5, 'price_change_15m')[
            ['symbol', 'last', 'price_change_15m', 'volume_change_15m']
        ]
        # 手动格式化
        formatted_losers = losers_df.copy()
        formatted_losers['last'] = formatted_losers['last'].apply(lambda x: format_price(x))
        formatted_losers['price_change_15m'] = formatted_losers['price_change_15m'].apply(lambda x: format_change(x))
        formatted_losers['volume_change_15m'] = formatted_losers['volume_change_15m'].apply(lambda x: format_change(x))
        st.dataframe(formatted_losers, use_container_width=True)

def create_volume_leaders(df):
    """创建成交量排行"""
    st.subheader("成交量排行")
    volume_df = df.nlargest(10, 'quote_volume')[
        ['symbol', 'quote_volume', 'price_change_15m', 'volume_change_15m']
    ]
    
    # 创建条形图
    fig = go.Figure()
    
    fig.add_trace(go.Bar(
        x=volume_df['symbol'],
        y=volume_df['quote_volume'],
        marker_color=np.where(volume_df['price_change_15m'] >= 0, '#26A69A', '#EF5350'),
        text=volume_df['quote_volume'].apply(format_volume),
        textposition='auto',
    ))
    
    fig.update_layout(
        title="Top 10 成交量",
        template='plotly_dark',
        plot_bgcolor='#1E1E1E',
        paper_bgcolor='#1E1E1E',
        height=300,
        showlegend=False,
        xaxis_title="交易对",
        yaxis_title="成交量 (USDT)"
    )
    
    st.plotly_chart(fig, use_container_width=True)

def show_spot_monitor():
    """显示现货市场监控"""
    try:
        spot_data = fetch_data("v1/market/data")
        if spot_data and (spot_data.get('status') == 'success' or spot_data.get('success') == True):
            data = spot_data.get('data', [])
            
            # 转换为DataFrame并处理时间戳
            if data:
                df = pd.DataFrame(data)
                if 'timestamp' in df.columns:
                    df['timestamp'] = pd.to_datetime(df['timestamp'])
                
                # 1. 市场概览
                st.subheader("市场概览")
                cols = st.columns(4)
                
                # BTC价格和变化
                with cols[0]:
                    btc_data = df[df['symbol'] == 'BTC/USDT'].iloc[0] if not df[df['symbol'] == 'BTC/USDT'].empty else (
                        df[df['symbol'] == 'BTC'].iloc[0] if not df[df['symbol'] == 'BTC'].empty else None
                    )
                    if btc_data is not None:
                        st.metric(
                            "BTC价格",
                            format_price(btc_data['price']),
                            format_change(btc_data.get('price_change_15m', 0))
                        )
                    else:
                        st.metric("BTC价格", "暂无数据")
                
                # ETH价格和变化
                with cols[1]:
                    eth_data = df[df['symbol'] == 'ETH/USDT'].iloc[0] if not df[df['symbol'] == 'ETH/USDT'].empty else (
                        df[df['symbol'] == 'ETH'].iloc[0] if not df[df['symbol'] == 'ETH'].empty else None
                    )
                    if eth_data is not None:
                        st.metric(
                            "ETH价格",
                            format_price(eth_data['price']),
                            format_change(eth_data.get('price_change_15m', 0))
                        )
                    else:
                        st.metric("ETH价格", "暂无数据")
                
                # 总成交量
                with cols[2]:
                    if 'volume' in df.columns:
                        total_volume = df['volume'].sum()
                        volume_change = df['volume_change_15m'].mean() if 'volume_change_15m' in df.columns else 0
                        st.metric(
                            "24h总成交量",
                            format_volume(total_volume),
                            format_change(volume_change)
                        )
                    else:
                        st.metric("24h总成交量", "暂无数据")
                
                # 市场趋势
                with cols[3]:
                    if 'price_change_15m' in df.columns:
                        up_tokens = len(df[df['price_change_15m'] > 0])
                        down_tokens = len(df[df['price_change_15m'] < 0])
                        st.metric(
                            "市场趋势",
                            f"上涨:{up_tokens} 下跌:{down_tokens}",
                            f"净值:{up_tokens - down_tokens}"
                        )
                    else:
                        st.metric("市场趋势", "暂无数据")
                
                # 2. 价格变化排行
                if 'price_change_15m' in df.columns:
                    st.subheader("价格变化排行")
                    price_cols = st.columns(2)
                    
                    # 涨幅榜
                    with price_cols[0]:
                        st.markdown("##### 涨幅榜")
                        gainers = df.nlargest(5, 'price_change_15m')[['symbol', 'price', 'price_change_15m']]
                        # 手动格式化
                        formatted_gainers = gainers.copy()
                        formatted_gainers['price'] = formatted_gainers['price'].apply(lambda x: f"${x:,.2f}")
                        formatted_gainers['price_change_15m'] = formatted_gainers['price_change_15m'].apply(lambda x: f"{x:+.2f}%")
                        st.dataframe(formatted_gainers, use_container_width=True)
                    
                    # 跌幅榜
                    with price_cols[1]:
                        st.markdown("##### 跌幅榜")
                        losers = df.nsmallest(5, 'price_change_15m')[['symbol', 'price', 'price_change_15m']]
                        # 手动格式化
                        formatted_losers = losers.copy()
                        formatted_losers['price'] = formatted_losers['price'].apply(lambda x: f"${x:,.2f}")
                        formatted_losers['price_change_15m'] = formatted_losers['price_change_15m'].apply(lambda x: f"{x:+.2f}%")
                        st.dataframe(formatted_losers, use_container_width=True)
                
                # 3. 成交量分析
                if 'volume' in df.columns and 'volume_change_15m' in df.columns:
                    st.subheader("成交量分析")
                    volume_cols = st.columns(2)
                    
                    # 成交量排行
                    with volume_cols[0]:
                        st.markdown("##### 成交量排行")
                        volume_leaders = df.nlargest(5, 'volume')[['symbol', 'volume', 'volume_change_15m']]
                        # 手动格式化
                        formatted_leaders = volume_leaders.copy()
                        formatted_leaders['volume'] = formatted_leaders['volume'].apply(lambda x: f"${x:,.0f}")
                        formatted_leaders['volume_change_15m'] = formatted_leaders['volume_change_15m'].apply(lambda x: f"{x:+.2f}%")
                        st.dataframe(formatted_leaders, use_container_width=True)
                    
                    # 成交量异常
                    with volume_cols[1]:
                        st.markdown("##### 成交量异常")
                        volume_anomalies = df[df['volume_change_15m'].abs() > 50][
                            ['symbol', 'volume', 'volume_change_15m']
                        ]
                        # 手动格式化
                        formatted_anomalies = volume_anomalies.copy()
                        formatted_anomalies['volume'] = formatted_anomalies['volume'].apply(lambda x: f"${x:,.0f}")
                        formatted_anomalies['volume_change_15m'] = formatted_anomalies['volume_change_15m'].apply(lambda x: f"{x:+.2f}%")
                        st.dataframe(formatted_anomalies, use_container_width=True)
                
                # 4. 市场深度图
                st.subheader("市场深度")
                depth_symbol = st.selectbox(
                    "选择交易对",
                    options=df['symbol'].tolist(),
                    index=0
                )
                depth_chart = create_market_depth(depth_symbol.replace('/USDT', '') if '/USDT' in depth_symbol else depth_symbol)
                if depth_chart:
                    st.plotly_chart(depth_chart, use_container_width=True)
                
                # 5. 完整市场数据
                st.subheader("完整市场数据")
                display_columns = [col for col in ['symbol', 'price', 'volume', 'price_change_15m', 'volume_change_15m', 'timestamp'] if col in df.columns]
                
                # 手动格式化
                formatted_df = df[display_columns].copy()
                if 'price' in formatted_df.columns:
                    formatted_df['price'] = formatted_df['price'].apply(lambda x: f"${x:,.2f}" if pd.notnull(x) else "")
                if 'volume' in formatted_df.columns:
                    formatted_df['volume'] = formatted_df['volume'].apply(lambda x: f"${x:,.0f}" if pd.notnull(x) else "")
                if 'price_change_15m' in formatted_df.columns:
                    formatted_df['price_change_15m'] = formatted_df['price_change_15m'].apply(lambda x: f"{x:+.2f}%" if pd.notnull(x) else "")
                if 'volume_change_15m' in formatted_df.columns:
                    formatted_df['volume_change_15m'] = formatted_df['volume_change_15m'].apply(lambda x: f"{x:+.2f}%" if pd.notnull(x) else "")
                if 'timestamp' in formatted_df.columns:
                    formatted_df['timestamp'] = formatted_df['timestamp'].apply(lambda x: x.strftime('%Y-%m-%d %H:%M:%S') if pd.notnull(x) else "")
                
                st.dataframe(formatted_df, use_container_width=True)
            else:
                st.warning("暂无现货市场数据")
        else:
            st.error("获取现货数据失败")
            
    except Exception as e:
        logger.error(f"显示现货监控失败: {str(e)}")
        st.error(f"获取数据失败，请检查API服务是否正常运行: {str(e)}")

def show_option_monitor():
    """显示期权市场监控"""
    try:
        st.subheader("期权市场数据")
        
        # 添加筛选选项
        col1, col2 = st.columns(2)
        with col1:
            days_limit = st.slider("期权到期天数限制", min_value=1, max_value=30, value=3, 
                                  help="只显示多少天内到期的期权")
        with col2:
            price_deviation = st.slider("执行价偏离市场价百分比", min_value=5, max_value=50, value=15, 
                                       help="执行价与市场价的偏离百分比限制") / 100
        
        # 显示交易所状态信息
        st.subheader("数据源状态")
        exchange_status = option_monitor.multi_exchange.get_exchange_status()
        
        # 创建交易所状态表格
        status_data = []
        for exchange_id, status in exchange_status.items():
            status_data.append({
                "交易所": status['name'],
                "状态": "正常" if status['status'] == 'ok' else "异常",
                "错误次数": status['error_count'],
                "最后成功时间": status['last_success'] or "未知",
                "最后错误时间": status['last_error'] or "无"
            })
        
        status_df = pd.DataFrame(status_data)
        st.dataframe(status_df, use_container_width=True)
        
        # 直接从期权监控器获取数据
        with st.spinner("正在获取期权数据..."):
            df = option_monitor.get_option_data(days_limit=days_limit, price_deviation=price_deviation)
        
        if not df.empty:
            # 显示期权市场指标
            metrics = st.columns(4)
            with metrics[0]:
                total_volume = df['volume_15m'].sum() if 'volume_15m' in df.columns else 0
                st.metric(
                    "总成交量",
                    format_number(total_volume)
                )
            
            with metrics[1]:
                call_volume = df[df['type'] == 'CALL']['volume_15m'].sum() if 'type' in df.columns and 'volume_15m' in df.columns else 0
                st.metric(
                    "看涨期权成交量",
                    format_number(call_volume)
                )
            
            with metrics[2]:
                put_volume = df[df['type'] == 'PUT']['volume_15m'].sum() if 'type' in df.columns and 'volume_15m' in df.columns else 0
                st.metric(
                    "看跌期权成交量",
                    format_number(put_volume)
                )
            
            with metrics[3]:
                pc_ratio = call_volume / put_volume if put_volume > 0 else float('inf')
                st.metric(
                    "看涨/看跌比",
                    f"{pc_ratio:.2f}"
                )
            
            # 显示期权数据表格
            st.subheader("期权数据")
            
            # 准备显示列
            display_columns = ['symbol', 'contract', 'type', 'strike', 'days_to_expiry', 'last', 'volume_15m']
            display_columns = [col for col in display_columns if col in df.columns]
            
            # 重命名列以便于显示
            rename_dict = {
                'symbol': '币种',
                'contract': '合约',
                'type': '类型',
                'strike': '执行价',
                'days_to_expiry': '剩余天数',
                'last': '最新价',
                'volume_15m': '15分钟成交量',
                'market_price': '市场价',
                'price_deviation': '价格偏离度'
            }
            
            # 如果有市场价和偏离度，也显示出来
            if 'market_price' in df.columns:
                display_columns.append('market_price')
            if 'price_deviation' in df.columns:
                display_columns.append('price_deviation')
            
            # 手动格式化
            renamed_df = df[display_columns].rename(columns=rename_dict)
            if 'strike' in display_columns:
                renamed_df['执行价'] = renamed_df['执行价'].apply(lambda x: f"${x:,.2f}" if pd.notnull(x) else "")
            if 'last' in display_columns:
                renamed_df['最新价'] = renamed_df['最新价'].apply(lambda x: f"${x:,.2f}" if pd.notnull(x) else "")
            if 'volume_15m' in display_columns:
                renamed_df['15分钟成交量'] = renamed_df['15分钟成交量'].apply(lambda x: f"{x:,.0f}" if pd.notnull(x) else "")
            if 'market_price' in display_columns:
                renamed_df['市场价'] = renamed_df['市场价'].apply(lambda x: f"${x:,.2f}" if pd.notnull(x) else "")
            if 'price_deviation' in display_columns:
                renamed_df['价格偏离度'] = renamed_df['价格偏离度'].apply(lambda x: f"{x:.2%}" if pd.notnull(x) else "")
            
            st.dataframe(renamed_df, use_container_width=True)
            
            # 显示期权成交量分布
            if 'type' in df.columns and 'volume_15m' in df.columns:
                st.subheader("期权成交量分布")
                
                # 按类型和执行价分组
                volume_by_strike = df.groupby(['type', 'strike'])['volume_15m'].sum().reset_index()
                
                # 创建图表
                fig = go.Figure()
                
                # 添加看涨期权
                call_data = volume_by_strike[volume_by_strike['type'] == 'CALL']
                fig.add_trace(go.Bar(
                    x=call_data['strike'],
                    y=call_data['volume_15m'],
                    name='看涨期权',
                    marker_color='#26A69A'
                ))
                
                # 添加看跌期权
                put_data = volume_by_strike[volume_by_strike['type'] == 'PUT']
                fig.add_trace(go.Bar(
                    x=put_data['strike'],
                    y=put_data['volume_15m'],
                    name='看跌期权',
                    marker_color='#EF5350'
                ))
                
                # 如果有市场价，添加市场价线
                if 'market_price' in df.columns and not df['market_price'].empty:
                    market_price = df['market_price'].iloc[0]
                    fig.add_shape(
                        type="line",
                        x0=market_price,
                        y0=0,
                        x1=market_price,
                        y1=volume_by_strike['volume_15m'].max() * 1.1,
                        line=dict(
                            color="yellow",
                            width=2,
                            dash="dash",
                        )
                    )
                    fig.add_annotation(
                        x=market_price,
                        y=volume_by_strike['volume_15m'].max() * 1.05,
                        text=f"市场价: ${market_price:,.2f}",
                        showarrow=False,
                        font=dict(
                            color="yellow",
                            size=12
                        )
                    )
                
                # 更新布局
                fig.update_layout(
                    title="期权成交量分布",
                    xaxis_title="执行价",
                    yaxis_title="成交量",
                    template='plotly_dark',
                    plot_bgcolor='#1E1E1E',
                    paper_bgcolor='#1E1E1E',
                    barmode='group'
                )
                
                st.plotly_chart(fig, use_container_width=True)
        else:
            st.warning("暂无符合条件的期权数据，请检查API连接或网络状态")
            
            # 添加手动刷新按钮
            if st.button("手动刷新数据"):
                st.experimental_rerun()
            
    except Exception as e:
        logger.error(f"显示期权监控失败: {str(e)}")
        st.error(f"获取数据失败: {str(e)}")
        st.exception(e)

def show_monitoring_page():
    """显示监控页面"""
    try:
        st.title("加密货币市场监控")
        
        # 创建标签页
        tabs = st.tabs(["现货监控", "期权监控"])  # 暂时移除宏观监控标签
        
        with tabs[0]:
            show_spot_monitor()
        with tabs[1]:
            show_option_monitor()
            
    except Exception as e:
        st.error(f"显示监控页面失败: {str(e)}")

def main():
    """主函数"""
    try:
        # 打印jinja2版本信息
        import jinja2
        import sys
        print(f"Python路径: {sys.executable}")
        print(f"Jinja2版本: {jinja2.__version__}, 路径: {jinja2.__file__}")
        
        # 侧边栏配置
        with st.sidebar:
            st.header("配置")
            auto_refresh = st.checkbox("自动刷新", value=True)
            update_interval = st.slider(
                "更新间隔(秒)",
                min_value=15,  # 增加最小更新间隔
                max_value=300,  # 增加最大更新间隔
                value=60  # 默认值改为60秒
            )
            
            # 添加API缓存配置
            st.subheader("API缓存设置")
            cache_ttl = st.slider(
                "缓存有效期(秒)",
                min_value=30,
                max_value=600,
                value=60
            )
            min_request_interval = st.slider(
                "最小请求间隔(秒)",
                min_value=3,
                max_value=30,
                value=5
            )
            
            # 更新API客户端设置
            api_client.update_settings(
                cache_ttl=cache_ttl,
                min_request_interval=min_request_interval
            )
            
            # 显示缓存状态
            cache_info = api_client.get_cache_info()
            if cache_info:
                st.subheader("缓存状态")
                for endpoint, info in cache_info.items():
                    status = "已过期" if info["expired"] else "有效"
                    st.text(f"{endpoint}: {info['age']}秒前 ({status})")
                
                if st.button("清除缓存"):
                    api_client.clear_cache()
                    st.success("缓存已清除")
            
            # 添加多交易所数据源配置
            st.subheader("多交易所数据源")
            st.text("已连接交易所:")
            try:
                if hasattr(option_monitor, 'multi_exchange'):
                    for exchange in option_monitor.multi_exchange.exchange_list:
                        st.text(f"- {exchange['name']} (权重: {exchange['weight']})")
                    
                    # 添加请求间隔设置
                    request_interval = st.slider(
                        "交易所请求间隔(秒)",
                        min_value=1.0,
                        max_value=10.0,
                        value=option_monitor.multi_exchange.min_request_interval,
                        step=0.5
                    )
                    option_monitor.multi_exchange.min_request_interval = request_interval
                else:
                    st.warning("多交易所数据源未初始化，请检查期权监控器配置")
            except Exception as e:
                st.error(f"无法加载多交易所数据: {str(e)}")
        
        # 显示监控页面
        show_monitoring_page()
        
        # 自动刷新
        if auto_refresh:
            time.sleep(update_interval)
            st.rerun()
            
    except Exception as e:
        logger.error(f"应用运行错误: {str(e)}")
        st.error(f"应用发生错误: {str(e)}")

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        logger.error(f"应用运行错误: {str(e)}")
        st.error(f"应用发生错误: {str(e)}") 