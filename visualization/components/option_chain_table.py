import streamlit as st
import pandas as pd
from ..utils.formatters import format_price, format_percentage

def show_option_chain_table(data: pd.DataFrame):
    """显示期权链表格"""
    if data.empty:
        st.warning("无期权数据")
        return
    
    # 调试信息
    st.write("数据列：", data.columns.tolist())
    st.write("数据示例：")
    st.write(data[['symbol', 'volume_change_15m', 'premium_change_15m']].head())
        
    # 按看涨看跌分组
    calls = data[data['type'].str.lower() == 'call'].copy()
    puts = data[data['type'].str.lower() == 'put'].copy()
    
    # 设置显示列
    display_columns = [
        'symbol',
        'strike',
        'price',
        'volume',
        'iv',
        'volume_change_15m',
        'premium_change_15m'
    ]
    
    # 格式化函数
    formatters = {
        'strike': lambda x: f"${x:,.2f}",
        'price': lambda x: f"${x:,.2f}",
        'volume': lambda x: f"{x:,.0f}",
        'iv': lambda x: f"{x:.1f}%" if x else "-",
        'volume_change_15m': lambda x: f"{x:+.2f}%" if pd.notnull(x) else "-",
        'premium_change_15m': lambda x: f"{x:+.2f}%" if pd.notnull(x) else "-"
    }
    
    # 设置样式
    def style_negative_positive(val):
        try:
            val = float(str(val).strip('%'))
            if abs(val) > 10:
                color = 'red' if val > 0 else 'blue'
            elif abs(val) > 5:
                color = 'darkred' if val > 0 else 'darkblue'
            else:
                color = 'black'
            return f'color: {color}'
        except:
            return ''
    
    # 创建两列布局
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("看涨期权")
        if not calls.empty:
            st.dataframe(
                calls[display_columns].style
                .format(formatters)
                .applymap(style_negative_positive, subset=['volume_change_15m', 'premium_change_15m'])
                .set_properties(**{'text-align': 'right'})
                .hide_index(),
                use_container_width=True
            )
    
    with col2:
        st.subheader("看跌期权")
        if not puts.empty:
            st.dataframe(
                puts[display_columns].style
                .format(formatters)
                .applymap(style_negative_positive, subset=['volume_change_15m', 'premium_change_15m'])
                .set_properties(**{'text-align': 'right'})
                .hide_index(),
                use_container_width=True
            )

def highlight_moneyness(row):
    """根据价内价外程度设置样式"""
    moneyness = abs(row['moneyness'])
    if moneyness <= 2:
        return ['background-color: #90EE90'] * len(row)  # 平值
    elif moneyness <= 5:
        return ['background-color: #E8E8E8'] * len(row)  # 轻度价内/价外
    else:
        return [''] * len(row)  # 深度价内/价外 