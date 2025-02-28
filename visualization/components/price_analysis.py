import streamlit as st
import pandas as pd
import logging
from ..utils.formatters import format_price, format_volume, format_change, format_timestamp
from ..charts.price_chart import create_price_chart
from market_monitor import MarketMonitor

logger = logging.getLogger(__name__)

def show_price_analysis(market_monitor: MarketMonitor):
    """显示价格分析"""
    try:
        st.subheader("价格分析")
        
        # 获取价格分析数据
        analysis = market_monitor.get_price_analysis()
        if not analysis:
            st.info("暂无价格分析数据")
            return
            
        # 显示价格变化排名
        st.write("价格变化排名")
        if price_changes := analysis.get('price_changes'):
            df = pd.DataFrame(price_changes)
            if not df.empty:
                st.dataframe(
                    df.style.format({
                        'price': format_price,
                        'price_change_15m': format_change,
                        'timestamp': format_timestamp
                    }),
                    use_container_width=True
                )
            
    except Exception as e:
        logger.error(f"显示价格分析失败: {str(e)}")
        st.error("显示价格分析失败，请稍后重试") 