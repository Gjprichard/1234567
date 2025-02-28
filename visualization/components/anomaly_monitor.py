import streamlit as st
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import pandas as pd
import numpy as np

def show_anomaly_monitor(data: pd.DataFrame):
    """显示异常监控面板"""
    if data.empty:
        st.warning("没有监控数据")
        return
        
    # 1. 成交量异常监控
    st.subheader("成交量异常监控")
    
    # 计算成交量统计
    volume_stats = calculate_volume_stats(data)
    
    # 显示成交量统计指标
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric(
            "异常成交量合约数",
            f"{volume_stats['anomaly_count']}个",
            f"{volume_stats['anomaly_ratio']:.1f}%"
        )
    with col2:
        st.metric(
            "最大成交量",
            f"{volume_stats['max_volume']:,.0f}",
            f"{volume_stats['max_volume_change']:+.1f}%"
        )
    with col3:
        st.metric(
            "平均成交量",
            f"{volume_stats['avg_volume']:,.0f}"
        )
    with col4:
        st.metric(
            "成交量集中度",
            f"{volume_stats['concentration']:.2f}"
        )
    
    # 显示成交量分布图
    show_volume_distribution(data)
    
    # 2. 价格异常监控
    st.subheader("价格异常监控")
    
    # 计算价格统计
    price_stats = calculate_price_stats(data)
    
    # 显示价格异常
    show_price_anomalies(data, price_stats)
    
    # 3. 波动率异常监控
    st.subheader("波动率异常监控")
    show_volatility_anomalies(data)

def calculate_volume_stats(data: pd.DataFrame) -> dict:
    """计算成交量统计指标"""
    # 计算Z-score
    mean_volume = data['volume'].mean()
    std_volume = data['volume'].std()
    z_scores = (data['volume'] - mean_volume) / std_volume
    
    # 识别异常值 (Z-score > 2)
    anomalies = abs(z_scores) > 2
    
    # 计算成交量集中度 (Herfindahl指数)
    total_volume = data['volume'].sum()
    volume_shares = data['volume'] / total_volume
    concentration = (volume_shares ** 2).sum()
    
    return {
        'anomaly_count': anomalies.sum(),
        'anomaly_ratio': anomalies.sum() / len(data) * 100,
        'max_volume': data['volume'].max(),
        'max_volume_change': ((data['volume'].max() - mean_volume) / mean_volume) * 100,
        'avg_volume': mean_volume,
        'concentration': concentration
    }

def show_volume_distribution(data: pd.DataFrame):
    """显示成交量分布"""
    fig = make_subplots(rows=1, cols=2)
    
    # 成交量分布直方图
    fig.add_trace(
        go.Histogram(
            x=data['volume'],
            name='成交量分布',
            nbinsx=30
        ),
        row=1, col=1
    )
    
    # 成交量箱线图（按到期日分组）
    fig.add_trace(
        go.Box(
            x=data['days_to_expiry'],
            y=data['volume'],
            name='成交量分布'
        ),
        row=1, col=2
    )
    
    fig.update_layout(
        height=400,
        title_text="成交量分布分析"
    )
    
    st.plotly_chart(fig, use_container_width=True)
    
    # 显示异常成交量合约
    show_volume_anomalies(data)

def show_volume_anomalies(data: pd.DataFrame):
    """显示异常成交量合约"""
    # 计算成交量Z-score
    mean_volume = data['volume'].mean()
    std_volume = data['volume'].std()
    data['volume_zscore'] = (data['volume'] - mean_volume) / std_volume
    
    # 筛选异常值
    anomalies = data[abs(data['volume_zscore']) > 2].copy()
    anomalies['volume_change'] = (anomalies['volume'] - mean_volume) / mean_volume * 100
    
    if not anomalies.empty:
        st.write("异常成交量合约:")
        for _, row in anomalies.iterrows():
            severity = 'high' if abs(row['volume_zscore']) > 3 else 'medium'
            color = 'red' if severity == 'high' else 'orange'
            
            st.markdown(
                f"<div style='color: {color}'>"
                f"合约 {row['symbol']}: 成交量 {row['volume']:,.0f} "
                f"(较均值变化 {row['volume_change']:+.1f}%)"
                f"</div>",
                unsafe_allow_html=True
            )
    else:
        st.success("没有检测到异常成交量")

def calculate_price_stats(data: pd.DataFrame) -> dict:
    """计算价格统计指标"""
    # 计算价格偏离度
    data['price_deviation'] = abs(data['price'] - data['price'].mean()) / data['price'].mean() * 100
    
    return {
        'avg_price': data['price'].mean(),
        'price_std': data['price'].std(),
        'max_deviation': data['price_deviation'].max(),
        'anomaly_threshold': data['price'].mean() + 2 * data['price'].std()
    }

def show_price_anomalies(data: pd.DataFrame, stats: dict):
    """显示价格异常"""
    # 计算价格Z-score
    data['price_zscore'] = (data['price'] - stats['avg_price']) / stats['price_std']
    
    # 筛选异常值
    anomalies = data[abs(data['price_zscore']) > 2].copy()
    
    if not anomalies.empty:
        st.write("价格异常合约:")
        for _, row in anomalies.iterrows():
            severity = 'high' if abs(row['price_zscore']) > 3 else 'medium'
            color = 'red' if severity == 'high' else 'orange'
            
            st.markdown(
                f"<div style='color: {color}'>"
                f"合约 {row['symbol']}: 价格 {row['price']:.2f} "
                f"(Z-score: {row['price_zscore']:.2f})"
                f"</div>",
                unsafe_allow_html=True
            )
    else:
        st.success("没有检测到价格异常")

def show_volatility_anomalies(data: pd.DataFrame):
    """显示波动率异常"""
    # 计算IV Z-score
    mean_iv = data['iv'].mean()
    std_iv = data['iv'].std()
    data['iv_zscore'] = (data['iv'] - mean_iv) / std_iv
    
    # 筛选异常值
    anomalies = data[abs(data['iv_zscore']) > 2].copy()
    
    if not anomalies.empty:
        st.write("波动率异常合约:")
        for _, row in anomalies.iterrows():
            severity = 'high' if abs(row['iv_zscore']) > 3 else 'medium'
            color = 'red' if severity == 'high' else 'orange'
            
            st.markdown(
                f"<div style='color: {color}'>"
                f"合约 {row['symbol']}: IV {row['iv']:.1f}% "
                f"(Z-score: {row['iv_zscore']:.2f})"
                f"</div>",
                unsafe_allow_html=True
            )
    else:
        st.success("没有检测到波动率异常") 