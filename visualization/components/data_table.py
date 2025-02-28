import streamlit as st
import pandas as pd
from ..utils.formatters import format_price, format_volume, format_change, format_timestamp

def show_market_table(df: pd.DataFrame):
    """显示市场数据表格"""
    try:
        st.subheader("市场数据")
        
        # 过滤和排序选项
        col1, col2 = st.columns(2)
        
        with col1:
            sort_by = st.selectbox(
                "排序依据",
                options=['成交量', '价格变化', '价格'],
                index=0
            )
        
        with col2:
            order = st.selectbox(
                "排序方式",
                options=['降序', '升序'],
                index=0
            )
        
        # 应用排序
        sort_map = {
            '成交量': 'volume',
            '价格变化': 'price_change_15m',
            '价格': 'price'
        }
        
        df_sorted = df.sort_values(
            sort_map[sort_by],
            ascending=(order == '升序')
        )
        
        # 显示数据表格
        st.dataframe(
            df_sorted[[
                'symbol', 'price', 'volume', 
                'price_change_15m', 'volume_change_15m',
                'timestamp'
            ]].style.format({
                'price': format_price,
                'volume': format_volume,
                'price_change_15m': format_change,
                'volume_change_15m': format_change,
                'timestamp': format_timestamp
            }),
            use_container_width=True
        )
        
    except Exception as e:
        st.error(f"显示数据表格失败: {str(e)}") 