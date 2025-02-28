import streamlit as st
import plotly.graph_objects as go
import pandas as pd
import numpy as np

def show_volatility_surface(option_chain):
    """显示波动率曲面"""
    if not option_chain or not (option_chain.calls or option_chain.puts):
        st.info("无波动率数据")
        return
    
    # 提取数据
    strikes = []
    expiries = []
    ivs = []
    
    for option in option_chain.calls + option_chain.puts:
        if 'iv' in option and option['iv']:
            strikes.append(option['strike_price'])
            expiries.append(option['expiry_date'])
            ivs.append(option['iv'])
    
    if not strikes:
        st.info("无有效波动率数据")
        return
    
    # 创建波动率曲面图
    fig = go.Figure(data=[go.Surface(
        x=strikes,
        y=expiries,
        z=ivs,
        colorscale='Viridis'
    )])
    
    fig.update_layout(
        title='波动率曲面',
        scene = dict(
            xaxis_title='行权价',
            yaxis_title='到期日',
            zaxis_title='隐含波动率'
        ),
        width=600,
        height=400
    )
    
    st.plotly_chart(fig)
    
    # 显示波动率偏斜
    show_volatility_skew(pd.DataFrame(option_chain.calls + option_chain.puts))

def show_volatility_skew(data: pd.DataFrame):
    """显示波动率偏斜"""
    # 按到期日分组
    expiries = data['days_to_expiry'].unique()
    
    fig = go.Figure()
    
    for expiry in expiries:
        expiry_data = data[data['days_to_expiry'] == expiry]
        fig.add_trace(
            go.Scatter(
                x=expiry_data['strike_price'],
                y=expiry_data['iv'],
                name=f'{expiry}天',
                mode='lines+markers'
            )
        )
    
    fig.update_layout(
        title='波动率偏斜',
        xaxis_title='行权价',
        yaxis_title='隐含波动率(%)',
        showlegend=True
    )
    
    st.plotly_chart(fig, use_container_width=True) 