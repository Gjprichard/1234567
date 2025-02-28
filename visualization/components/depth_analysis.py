import streamlit as st
import pandas as pd
from market_monitor import MarketMonitor
from ..utils.formatters import format_volume, format_price
from ..charts.depth_chart import create_depth_chart

def show_depth_analysis(symbol: str, market_monitor: MarketMonitor):
    """显示深度分析"""
    try:
        st.subheader("市场深度分析")
        
        # 获取深度数据和指标
        depth_data = market_monitor.db.get_market_depth_with_metrics(symbol)
        
        if depth_data:
            metrics = depth_data['metrics']
            
            # 显示深度指标
            cols = st.columns(4)
            with cols[0]:
                st.metric(
                    "买单总量", 
                    format_volume(metrics['bid_volume']),
                    format_volume(metrics['bid_value'], prefix="≈$")
                )
            with cols[1]:
                st.metric(
                    "卖单总量", 
                    format_volume(metrics['ask_volume']),
                    format_volume(metrics['ask_value'], prefix="≈$")
                )
            with cols[2]:
                st.metric(
                    "价差", 
                    format_price(metrics['spread']),
                    f"{metrics['spread_percentage']:.2f}%"
                )
            with cols[3]:
                imbalance = metrics['depth_imbalance'] * 100
                st.metric(
                    "深度不平衡", 
                    f"{abs(imbalance):.2f}%",
                    "买方主导" if imbalance > 0 else "卖方主导"
                )
            
            # 显示深度图表
            depth_chart = create_depth_chart(
                pd.DataFrame(depth_data['bids']), 
                pd.DataFrame(depth_data['asks'])
            )
            if depth_chart:
                st.plotly_chart(depth_chart, use_container_width=True)
                
            # 显示详细数据
            col1, col2 = st.columns(2)
            with col1:
                st.markdown("##### 买单明细")
                st.dataframe(
                    pd.DataFrame(depth_data['bids']).style.format({
                        'price': format_price,
                        'amount': format_volume,
                        'cumulative': format_volume
                    }),
                    use_container_width=True
                )
            
            with col2:
                st.markdown("##### 卖单明细")
                st.dataframe(
                    pd.DataFrame(depth_data['asks']).style.format({
                        'price': format_price,
                        'amount': format_volume,
                        'cumulative': format_volume
                    }),
                    use_container_width=True
                )
                
    except Exception as e:
        st.error(f"显示深度分析失败: {str(e)}") 