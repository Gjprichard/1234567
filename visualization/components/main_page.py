import streamlit as st
import pandas as pd
import logging
from .market_overview import show_market_overview
from .price_analysis import show_price_analysis
from .volume_analysis import show_volume_analysis
from .option_analysis import (
    show_option_overview,
    show_strike_distribution,
    show_option_details,
    show_option_page
)
from .alert_panel import show_alert_panel
from ..charts.depth_chart import create_depth_chart
from ..charts.volume_chart import create_volume_chart
from market_monitor import MarketMonitor
from .depth_analysis import show_depth_analysis
from ..charts.kline_chart import create_kline_chart
from ..charts.orderbook_chart import create_orderbook_chart
from ..charts.market_analysis_chart import create_market_analysis_chart
from ..charts.combined_chart import create_combined_chart

logger = logging.getLogger(__name__)

def show_spot_page(df: pd.DataFrame, market_monitor: MarketMonitor):
    """显示现货市场页面"""
    try:
        # 1. 市场概览
        show_market_overview(market_monitor)
        
        # 2. 价格分析
        show_price_analysis(market_monitor)
        
        # 3. 成交量分析
        show_volume_analysis(market_monitor)
        
        # 4. 成交量图表
        volume_chart = create_volume_chart(df)
        if volume_chart:
            st.plotly_chart(volume_chart, use_container_width=True)
        
        # 5. 市场深度分析
        st.subheader("市场深度")
        depth_symbol = st.selectbox(
            "选择交易对",
            options=df['symbol'].unique(),
            index=0
        )
        show_depth_analysis(depth_symbol, market_monitor)
            
    except Exception as e:
        logger.error(f"显示现货市场页面失败: {str(e)}")
        st.error("显示页面失败，请检查数据")

def show_monitoring_page(market_monitor: MarketMonitor):
    """显示监控页面"""
    try:
        st.title("市场监控")
        
        # 选择交易对
        symbol = st.selectbox(
            "选择交易对",
            options=market_monitor.symbols,
            index=0
        )

        # 显示市场图表
        show_market_charts(market_monitor, symbol)

        # 获取并显示市场数据
        market_data = market_monitor.get_market_data()
        if market_data:
            df = pd.DataFrame(market_data)
            
            # 打印数据信息用于调试
            logger.debug(f"DataFrame 信息:\n{df.info()}")
            logger.debug(f"DataFrame 前几行:\n{df.head()}")
            logger.debug(f"DataFrame 列名: {df.columns.tolist()}")
            
            # 显示市场分析
            if 'price_change_15m' in df.columns and 'volume_change_15m' in df.columns:
                show_market_analysis(df)
            else:
                st.warning("缺少价格或成交量变化数据")
            
            # 显示市场概览
            show_market_overview(df)
            
            # 显示预警信息
            show_alert_panel(df)
        else:
            st.warning("暂无市场数据")
            
    except Exception as e:
        logger.error(f"显示监控页面失败: {str(e)}")
        st.error("显示页面失败，请检查数据")

def show_market_charts(market_monitor: MarketMonitor, symbol: str):
    """显示市场图表"""
    try:
        # 创建两列布局
        col1, col2 = st.columns([0.8, 0.2])  # 调整比例，让右侧更窄
        
        with col1:
            # 获取K线数据和订单簿数据
            kline_data = market_monitor.get_kline_data(symbol)
            orderbook = market_monitor.get_orderbook(symbol)
            
            if kline_data and orderbook:
                kline_df = pd.DataFrame(kline_data)
                fig = create_combined_chart(
                    kline_df=kline_df,
                    orderbook=orderbook,
                    symbol=symbol
                )
                if fig:
                    st.plotly_chart(fig, use_container_width=True)
                else:
                    st.warning("创建图表失败")
            else:
                st.warning("暂无市场数据")

        with col2:
            if orderbook and orderbook['bids'] and orderbook['asks']:
                # 使用自定义CSS美化表格
                st.markdown("""
                <style>
                    .orderbook-container {
                        background: #1C1C28;
                        border-radius: 8px;
                        padding: 8px;
                        margin-bottom: 4px;
                        font-family: 'IBM Plex Mono', monospace;
                        font-size: 12px;
                    }
                    .orderbook-header {
                        color: #8F92A1;
                        font-size: 14px;
                        margin-bottom: 8px;
                        padding: 4px;
                        border-bottom: 1px solid #2B2B3E;
                    }
                    .orderbook-row {
                        display: flex;
                        justify-content: space-between;
                        padding: 2px 4px;
                    }
                    .bid-price { color: #00C853; }
                    .ask-price { color: #FF3D71; }
                    .volume { color: #8F92A1; }
                </style>
                """, unsafe_allow_html=True)
                
                # 显示卖单（倒序）
                st.markdown("<div class='orderbook-container'>", unsafe_allow_html=True)
                st.markdown("<div class='orderbook-header'>Asks</div>", unsafe_allow_html=True)
                asks_df = pd.DataFrame(orderbook['asks'], columns=['Price', 'Size'])
                for _, row in asks_df[:10].iloc[::-1].iterrows():
                    st.markdown(
                        f"<div class='orderbook-row'>"
                        f"<span class='ask-price'>{row['Price']:.2f}</span>"
                        f"<span class='volume'>{row['Size']:.4f}</span>"
                        f"</div>",
                        unsafe_allow_html=True
                    )
                st.markdown("</div>", unsafe_allow_html=True)
                
                # 显示买单
                st.markdown("<div class='orderbook-container'>", unsafe_allow_html=True)
                st.markdown("<div class='orderbook-header'>Bids</div>", unsafe_allow_html=True)
                bids_df = pd.DataFrame(orderbook['bids'], columns=['Price', 'Size'])
                for _, row in bids_df[:10].iterrows():
                    st.markdown(
                        f"<div class='orderbook-row'>"
                        f"<span class='bid-price'>{row['Price']:.2f}</span>"
                        f"<span class='volume'>{row['Size']:.4f}</span>"
                        f"</div>",
                        unsafe_allow_html=True
                    )
                st.markdown("</div>", unsafe_allow_html=True)
            else:
                st.warning("暂无订单簿数据")
                
    except Exception as e:
        logger.error(f"显示市场图表失败: {str(e)}")
        logger.exception("详细错误信息:")
        st.error("显示市场图表失败")

def show_market_analysis(df: pd.DataFrame):
    """显示市场分析"""
    try:
        if not df.empty:
            st.plotly_chart(
                create_market_analysis_chart(df),
                use_container_width=True
            )
    except Exception as e:
        logger.error(f"显示市场分析失败: {str(e)}")
        st.error("显示市场分析失败") 