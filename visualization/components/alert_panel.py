import streamlit as st
import pandas as pd
import logging
from ..utils.formatters import format_price, format_volume, format_change

logger = logging.getLogger(__name__)

def show_alert_panel(df: pd.DataFrame):
    """显示预警面板"""
    try:
        st.subheader("市场预警")
        
        # 检查必要的列是否存在
        required_columns = {'symbol', 'price_change_15m', 'volume_change_15m'}
        if not all(col in df.columns for col in required_columns):
            st.warning("数据缺少必要的列")
            return
        
        # 设置预警阈值
        price_threshold = 3.0  # 价格变化阈值
        volume_threshold = 50.0  # 成交量变化阈值
        
        # 检测价格异常
        price_alerts = df[abs(df['price_change_15m']) > price_threshold]
        if not price_alerts.empty:
            st.warning("价格异常")
            for _, alert in price_alerts.iterrows():
                st.write(f"{alert['symbol']}: {format_change(alert['price_change_15m'])}%")
                
        # 检测成交量异常
        volume_alerts = df[abs(df['volume_change_15m']) > volume_threshold]
        if not volume_alerts.empty:
            st.warning("成交量异常")
            for _, alert in volume_alerts.iterrows():
                st.write(f"{alert['symbol']}: {format_change(alert['volume_change_15m'])}%")
                
        if price_alerts.empty and volume_alerts.empty:
            st.success("市场运行正常")
            
    except Exception as e:
        logger.error(f"显示预警面板失败: {str(e)}")
        st.error("显示预警面板失败") 