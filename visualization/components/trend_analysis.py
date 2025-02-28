import streamlit as st
import pandas as pd
from ..charts.trend_chart import create_trend_chart
from ..utils.formatters import format_price, format_volume, format_change

def show_trend_analysis(df: pd.DataFrame):
    """显示趋势分析"""
    try:
        st.subheader("趋势分析")
        
        # 选择交易对
        symbol = st.selectbox(
            "选择交易对",
            options=df['symbol'].unique(),
            index=0
        )
        
        # 显示当前数据
        symbol_data = df[df['symbol'] == symbol].iloc[0]
        
        # 显示基本指标
        cols = st.columns(4)
        with cols[0]:
            st.metric(
                "当前价格",
                format_price(symbol_data['price']),
                format_change(symbol_data.get('price_change_15m', 0))
            )
        
        with cols[1]:
            st.metric(
                "成交量",
                format_volume(symbol_data['volume']),
                format_change(symbol_data.get('volume_change_15m', 0))
            )
        
        with cols[2]:
            st.metric(
                "波动率",
                f"{symbol_data.get('volatility', 0):.2f}%"
            )
        
        with cols[3]:
            st.metric(
                "趋势",
                "上涨" if symbol_data.get('price_change_15m', 0) > 0 else "下跌"
            )
        
        # 显示趋势图
        trend_chart = create_trend_chart(df, symbol)
        if trend_chart:
            st.plotly_chart(trend_chart, use_container_width=True)
        
    except Exception as e:
        st.error(f"显示趋势分析失败: {str(e)}") 