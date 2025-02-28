import plotly.graph_objects as go
import pandas as pd
import logging
from ..utils.formatters import format_price, format_change

logger = logging.getLogger(__name__)

def create_price_chart(df: pd.DataFrame) -> go.Figure:
    """创建价格变化图表"""
    try:
        # 获取价格变化最大的10个交易对
        price_df = pd.concat([
            df.nlargest(5, 'price_change_15m'),
            df.nsmallest(5, 'price_change_15m')
        ]).sort_values('price_change_15m', ascending=True)
        
        # 创建图表
        fig = go.Figure()
        
        fig.add_trace(go.Bar(
            x=price_df['symbol'],
            y=price_df['price_change_15m'],
            marker_color=price_df['price_change_15m'].apply(
                lambda x: 'rgba(38,166,154,0.6)' if x >= 0 else 'rgba(239,83,80,0.6)'
            ),
            text=price_df['price_change_15m'].apply(format_change),
            textposition='auto',
        ))
        
        # 更新布局
        fig.update_layout(
            title="价格变化Top10",
            template='plotly_dark',
            plot_bgcolor='#1E1E1E',
            paper_bgcolor='#1E1E1E',
            height=300,
            showlegend=False,
            xaxis_title="交易对",
            yaxis_title="价格变化 (%)"
        )
        
        return fig
        
    except Exception as e:
        logger.error(f"创建价格图表失败: {str(e)}")
        return None 