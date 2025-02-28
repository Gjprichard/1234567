import streamlit as st
import pandas as pd
import logging
from ..utils.formatters import format_volume, format_change, format_timestamp
from market_monitor import MarketMonitor  # 直接从根目录导入

logger = logging.getLogger(__name__)

def show_volume_analysis(market_monitor: MarketMonitor):
    """显示成交量分析"""
    try:
        st.subheader("成交量分析")
        
        # 获取成交量分析数据
        analysis = market_monitor.get_volume_analysis()
        if not analysis:
            st.info("暂无成交量分析数据")
            return
            
        # 显示成交量变化排名
        st.write("成交量变化排名")
        if volume_changes := analysis.get('volume_changes'):
            df = pd.DataFrame(volume_changes)
            if not df.empty:
                st.dataframe(
                    df.style.format({
                        'volume': format_volume,
                        'volume_change_15m': format_change,
                        'timestamp': format_timestamp
                    }),
                    use_container_width=True
                )
            
    except Exception as e:
        logger.error(f"显示成交量分析失败: {str(e)}")
        st.error("显示成交量分析失败，请稍后重试") 