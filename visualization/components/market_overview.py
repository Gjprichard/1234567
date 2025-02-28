import streamlit as st
import pandas as pd
import logging
from ..utils.formatters import format_price, format_volume, format_change, format_timestamp
from market_monitor import MarketMonitor
import plotly.graph_objects as go

logger = logging.getLogger(__name__)

def show_market_overview(df: pd.DataFrame):
    """显示市场概览"""
    try:
        st.subheader("市场概览")
        
        # 检查必要的列是否存在
        required_columns = {'symbol', 'price', 'volume', 'price_change_15m', 'volume_change_15m'}
        if not all(col in df.columns for col in required_columns):
            st.warning(f"数据缺少必要的列: {required_columns - set(df.columns)}")
            return
            
        # 计算市场指标
        metrics = {
            'total_volume': df['volume'].sum(),
            'avg_price_change': df['price_change_15m'].mean() if 'price_change_15m' in df else 0,
            'up_tokens': len(df[df['price_change_15m'] > 0]) if 'price_change_15m' in df else 0,
            'down_tokens': len(df[df['price_change_15m'] < 0]) if 'price_change_15m' in df else 0
        }
        
        # 显示指标
        cols = st.columns(4)
        cols[0].metric("总成交量(USDT)", format_volume(metrics['total_volume']))
        cols[1].metric("平均价格变化", f"{metrics['avg_price_change']:.2f}%")
        cols[2].metric("上涨代币数", metrics['up_tokens'])
        cols[3].metric("下跌代币数", metrics['down_tokens'])

        # 添加价格变化趋势图
        fig_price = go.Figure()
        df_sorted = df.sort_values('price_change_15m', ascending=False)
        
        fig_price.add_trace(
            go.Bar(
                x=df_sorted['symbol'],
                y=df_sorted['price_change_15m'],
                name='Price Change',
                marker_color=['green' if x >= 0 else 'red' for x in df_sorted['price_change_15m']]
            )
        )
        
        fig_price.update_layout(
            title='15分钟价格变化 (%)',
            xaxis_title='交易对',
            yaxis_title='变化率 (%)',
            template='plotly_dark',
            height=300
        )
        
        st.plotly_chart(fig_price, use_container_width=True)

        # 添加成交量变化趋势图
        fig_volume = go.Figure()
        df_sorted = df.sort_values('volume', ascending=False)
        
        fig_volume.add_trace(
            go.Bar(
                x=df_sorted['symbol'],
                y=df_sorted['volume'],
                name='Volume',
                marker_color='rgb(55,83,109)'
            )
        )
        
        fig_volume.update_layout(
            title='成交量分布 (USDT)',
            xaxis_title='交易对',
            yaxis_title='成交量',
            template='plotly_dark',
            height=300
        )
        
        st.plotly_chart(fig_volume, use_container_width=True)
        
        # 显示市场数据表格
        st.subheader("市场数据明细")
        st.dataframe(
            df[['symbol', 'price', 'volume', 'price_change_15m', 'volume_change_15m']].style.format({
                'price': format_price,
                'volume': format_volume,
                'price_change_15m': lambda x: f"{x:.2f}%",
                'volume_change_15m': lambda x: f"{x:.2f}%"
            }),
            use_container_width=True
        )
            
    except Exception as e:
        logger.error(f"显示市场概览失败: {str(e)}")
        st.error("显示市场概览失败") 