import streamlit as st
from option_monitor.core.option_monitor import OptionMonitor
from .option_chain_table import show_option_chain_table
from .volatility_surface import show_volatility_surface
from .greeks_monitor import show_greeks_monitor
from .anomaly_monitor import show_anomaly_monitor

def show_option_dashboard():
    """显示期权市场监控面板"""
    try:
        st.title("期权市场监控")
        
        # 初始化期权监控器
        if 'option_monitor' not in st.session_state:
            st.session_state.option_monitor = OptionMonitor()
            st.session_state.option_monitor.start()
        
        # 选择标的资产
        col1, col2 = st.columns([2, 1])
        with col1:
            underlying = st.selectbox("选择标的资产", ["BTC", "ETH"])
        with col2:
            expiry_filter = st.selectbox("到期日筛选", ["全部", "7天内", "30天内", "90天内"])
        
        # 获取期权数据
        option_data = st.session_state.option_monitor.get_market_data()
        if option_data.empty:
            st.warning("暂无期权市场数据")
            return
            
        # 确保变化率列存在
        if 'volume_change_15m' not in option_data.columns:
            option_data['volume_change_15m'] = 0.0
        if 'premium_change_15m' not in option_data.columns:
            option_data['premium_change_15m'] = 0.0
        
        # 显示市场概览
        st.subheader("市场概览")
        col1, col2, col3, col4 = st.columns(4)

        # 按合约类型分类
        calls = option_data[option_data['type'] == 'call']
        puts = option_data[option_data['type'] == 'put']
        expiry_dates = sorted(option_data['expiry'].unique())
        nearest_expiry = expiry_dates[0] if expiry_dates else '-'

        with col1:
            st.metric("活跃合约数", len(option_data))
        with col2:
            st.metric("看涨合约数", len(calls))
        with col3:
            st.metric("看跌合约数", len(puts))
        with col4:
            st.metric("最近到期日", nearest_expiry)
        
        # 创建主要内容布局
        col1, col2 = st.columns([3, 2])
        
        with col1:
            # 期权链表格
            st.subheader("期权链")
            show_option_chain_table(option_data)
            
            # Greeks监控
            st.subheader("Greeks监控")
            show_greeks_monitor(option_data)
        
        with col2:
            # 波动率曲面
            st.subheader("波动率曲面")
            show_volatility_surface(option_data)
            
            # 异常监控
            st.subheader("异常监控")
            show_anomaly_monitor(option_data)
        
        # 自动刷新
        if st.sidebar.checkbox("自动刷新", value=True):
            refresh_interval = st.sidebar.slider("刷新间隔(秒)", 5, 60, 30)
            st.empty()
            import time
            time.sleep(refresh_interval)
            st.experimental_rerun()

    except Exception as e:
        st.error(f"显示期权面板失败: {str(e)}")

def cleanup_option_monitor():
    """清理期权监控器资源"""
    if 'option_monitor' in st.session_state:
        st.session_state.option_monitor.stop()
        del st.session_state.option_monitor 