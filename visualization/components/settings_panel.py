import streamlit as st
from typing import Dict

def show_settings_panel() -> Dict:
    """显示设置面板"""
    try:
        st.sidebar.header("配置")
        
        # 自动刷新设置
        auto_refresh = st.sidebar.checkbox("自动刷新", value=True)
        
        # 刷新间隔
        refresh_interval = st.sidebar.slider(
            "刷新间隔(秒)",
            min_value=5,
            max_value=60,
            value=15
        )
        
        # 预警设置
        st.sidebar.subheader("预警设置")
        
        price_threshold = st.sidebar.slider(
            "价格变化阈值(%)",
            min_value=1.0,
            max_value=10.0,
            value=3.0
        )
        
        volume_threshold = st.sidebar.slider(
            "成交量变化阈值(%)",
            min_value=10.0,
            max_value=100.0,
            value=50.0
        )
        
        # 显示设置
        st.sidebar.subheader("显示设置")
        
        show_alerts = st.sidebar.checkbox("显示预警", value=True)
        show_trends = st.sidebar.checkbox("显示趋势", value=True)
        show_depth = st.sidebar.checkbox("显示深度", value=True)
        
        return {
            'auto_refresh': auto_refresh,
            'refresh_interval': refresh_interval,
            'price_threshold': price_threshold,
            'volume_threshold': volume_threshold,
            'show_alerts': show_alerts,
            'show_trends': show_trends,
            'show_depth': show_depth
        }
        
    except Exception as e:
        st.error(f"加载设置面板失败: {str(e)}")
        return {} 