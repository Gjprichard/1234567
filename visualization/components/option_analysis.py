import streamlit as st
import pandas as pd
import logging
from ..utils.formatters import format_price, format_volume, format_change, format_timestamp

logger = logging.getLogger(__name__)

def show_option_overview(df: pd.DataFrame):
    """显示期权市场概览"""
    try:
        st.subheader("期权市场概览")
        
        if df.empty:
            st.info("暂无期权市场数据")
            return
            
        # 显示基本指标
        cols = st.columns(4)
        with cols[0]:
            st.metric("期权总数", len(df))
        with cols[1]:
            st.metric("活跃期权", len(df[df['volume'] > 0]))
        with cols[2]:
            total_volume = df['volume'].sum()
            st.metric("总成交量", format_volume(total_volume))
        with cols[3]:
            avg_price = df['price'].mean()
            st.metric("平均价格", format_price(avg_price))
            
    except Exception as e:
        logger.error(f"显示期权市场概览失败: {str(e)}")
        st.error("显示期权概览失败")

def show_strike_distribution(df: pd.DataFrame):
    """显示行权价分布"""
    try:
        st.subheader("行权价分布")
        
        if df.empty:
            st.info("暂无行权价数据")
            return
            
        # 按行权价分组统计
        strike_stats = df.groupby('strike').agg({
            'volume': 'sum',
            'open_interest': 'sum'
        }).reset_index()
        
        # 显示数据表格
        st.dataframe(
            strike_stats.style.format({
                'strike': format_price,
                'volume': format_volume,
                'open_interest': format_volume
            }),
            use_container_width=True
        )
        
    except Exception as e:
        logger.error(f"显示行权价分布失败: {str(e)}")
        st.error("显示行权价分布失败")

def show_option_details(df: pd.DataFrame):
    """显示期权详细数据"""
    try:
        st.subheader("期权详细数据")
        
        if df.empty:
            st.info("暂无期权详细数据")
            return
            
        # 显示详细数据表格
        st.dataframe(
            df.style.format({
                'strike': format_price,
                'price': format_price,
                'volume': format_volume,
                'open_interest': format_volume,
                'timestamp': format_timestamp
            }),
            use_container_width=True
        )
        
    except Exception as e:
        logger.error(f"显示期权详细数据失败: {str(e)}")
        st.error("显示期权详细数据失败")

def show_option_page(df: pd.DataFrame):
    """显示期权市场页面"""
    try:
        # 1. 期权市场概览
        show_option_overview(df)
        
        # 2. 行权价分布
        show_strike_distribution(df)
        
        # 3. 期权详细数据
        show_option_details(df)
        
    except Exception as e:
        logger.error(f"显示期权市场页面失败: {str(e)}")
        st.error("显示期权页面失败，请检查数据")

def show_option_analysis(data: pd.DataFrame):
    """显示期权分析结果"""
    if data.empty:
        st.warning("无期权数据可分析")
        return
        
    # 创建多列布局
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.subheader("成交量分析")
        volume_metrics = {
            "总成交量": f"{data['volume'].sum():,.0f}",
            "平均成交量": f"{data['volume'].mean():,.0f}",
            "最大成交量": f"{data['volume'].max():,.0f}",
            "成交量变化": f"{data['volume_change_15m'].mean():+.2f}%"
        }
        for k, v in volume_metrics.items():
            st.metric(k, v)
    
    with col2:
        st.subheader("价格分析")
        price_metrics = {
            "平均权利金": f"${data['price'].mean():.2f}",
            "最高权利金": f"${data['price'].max():.2f}",
            "最低权利金": f"${data['price'].min():.2f}",
            "权利金变化": f"{data['premium_change_15m'].mean():+.2f}%"
        }
        for k, v in price_metrics.items():
            st.metric(k, v)
    
    with col3:
        st.subheader("波动率分析")
        if 'iv' in data.columns:
            iv_metrics = {
                "平均IV": f"{data['iv'].mean():.1f}%",
                "最高IV": f"{data['iv'].max():.1f}%",
                "最低IV": f"{data['iv'].min():.1f}%",
                "IV偏度": f"{data['iv'].skew():.2f}"
            }
            for k, v in iv_metrics.items():
                st.metric(k, v) 