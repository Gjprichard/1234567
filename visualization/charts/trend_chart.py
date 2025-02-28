import plotly.graph_objects as go
from plotly.subplots import make_subplots
import pandas as pd
import logging
from ..utils.formatters import format_price, format_volume

logger = logging.getLogger(__name__)

def create_trend_chart(df: pd.DataFrame, symbol: str) -> go.Figure:
    """创建价格和成交量趋势图"""
    try:
        # 获取指定交易对的数据
        symbol_data = df[df['symbol'] == symbol].copy()
        if symbol_data.empty:
            return None
            
        # 创建子图
        fig = make_subplots(
            rows=2, cols=1,
            shared_xaxes=True,
            vertical_spacing=0.05,
            subplot_titles=('价格趋势', '成交量趋势'),
            row_heights=[0.7, 0.3]
        )
        
        # 添加价格趋势
        fig.add_trace(
            go.Scatter(
                x=symbol_data['timestamp'],
                y=symbol_data['price'],
                name='价格',
                line=dict(color='#26A69A')
            ),
            row=1, col=1
        )
        
        # 添加成交量趋势
        fig.add_trace(
            go.Bar(
                x=symbol_data['timestamp'],
                y=symbol_data['volume'],
                name='成交量',
                marker_color='rgba(38,166,154,0.3)'
            ),
            row=2, col=1
        )
        
        # 更新布局
        fig.update_layout(
            template='plotly_dark',
            plot_bgcolor='#1E1E1E',
            paper_bgcolor='#1E1E1E',
            height=600,
            showlegend=True,
            legend=dict(
                orientation="h",
                yanchor="bottom",
                y=1.02,
                xanchor="right",
                x=1
            )
        )
        
        # 更新Y轴格式
        fig.update_yaxes(title_text="价格 (USDT)", row=1, col=1)
        fig.update_yaxes(title_text="成交量", row=2, col=1)
        
        return fig
        
    except Exception as e:
        logger.error(f"创建趋势图表失败: {str(e)}")
        return None 