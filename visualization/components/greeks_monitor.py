import streamlit as st
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import pandas as pd

def show_greeks_monitor(data: pd.DataFrame):
    """显示希腊字母监控面板"""
    if data.empty:
        st.warning("没有希腊字母数据")
        return
        
    # 创建四个子图
    fig = make_subplots(
        rows=2, cols=2,
        subplot_titles=('Delta分布', 'Gamma分布', 'Theta分布', 'Vega分布')
    )
    
    # Delta分布
    fig.add_trace(
        go.Histogram(x=data['delta'], name='Delta'),
        row=1, col=1
    )
    
    # Gamma分布
    fig.add_trace(
        go.Histogram(x=data['gamma'], name='Gamma'),
        row=1, col=2
    )
    
    # Theta分布
    fig.add_trace(
        go.Histogram(x=data['theta'], name='Theta'),
        row=2, col=1
    )
    
    # Vega分布
    fig.add_trace(
        go.Histogram(x=data['vega'], name='Vega'),
        row=2, col=2
    )
    
    fig.update_layout(
        height=800,
        showlegend=False,
        title_text="期权希腊字母分布"
    )
    
    st.plotly_chart(fig, use_container_width=True)
    
    # 显示汇总指标
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("净Delta", f"{data['delta'].sum():.2f}")
    with col2:
        st.metric("净Gamma", f"{data['gamma'].sum():.2f}")
    with col3:
        st.metric("净Theta", f"{data['theta'].sum():.2f}")
    with col4:
        st.metric("净Vega", f"{data['vega'].sum():.2f}") 