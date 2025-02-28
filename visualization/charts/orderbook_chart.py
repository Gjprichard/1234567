import plotly.graph_objects as go
import pandas as pd
import logging
from ..utils.formatters import format_price, format_volume

logger = logging.getLogger(__name__)

def create_orderbook_chart(bids: list, asks: list) -> go.Figure:
    """创建深度图"""
    try:
        if not bids or not asks:
            logger.warning("订单簿数据为空")
            return None
            
        # 设置专业的配色方案
        colors = {
            'background': '#1C1C28',
            'paper': '#1C1C28',
            'grid': '#2B2B3E',
            'text': '#E1E1E6',
            'bids': '#00C853',
            'asks': '#FF3D71'
        }

        # 计算累计数量
        bids_df = pd.DataFrame(bids, columns=['price', 'amount'])
        asks_df = pd.DataFrame(asks, columns=['price', 'amount'])
        
        bids_df['cumulative'] = bids_df['amount'].cumsum()
        asks_df['cumulative'] = asks_df['amount'].cumsum()

        # 创建图表
        fig = go.Figure()

        # 添加买单深度
        fig.add_trace(
            go.Scatter(
                x=bids_df['price'],
                y=bids_df['cumulative'],
                fill='tozeroy',
                name='Bids',
                line=dict(color=colors['bids']),
                fillcolor=f'rgba(0,200,83,0.2)'
            )
        )

        # 添加卖单深度
        fig.add_trace(
            go.Scatter(
                x=asks_df['price'],
                y=asks_df['cumulative'],
                fill='tozeroy',
                name='Asks',
                line=dict(color=colors['asks']),
                fillcolor=f'rgba(255,61,113,0.2)'
            )
        )

        # 更新布局
        fig.update_layout(
            height=300,
            template='plotly_dark',
            paper_bgcolor=colors['paper'],
            plot_bgcolor=colors['background'],
            margin=dict(t=20, l=50, r=50, b=20),
            showlegend=True,
            legend=dict(
                orientation="h",
                yanchor="bottom",
                y=1,
                xanchor="left",
                x=0,
                bgcolor='rgba(0,0,0,0)',
                font=dict(color=colors['text'])
            ),
            hovermode='x unified'
        )

        # 更新坐标轴
        fig.update_xaxes(
            title="Price",
            showgrid=True,
            gridwidth=1,
            gridcolor=colors['grid'],
            tickfont=dict(color=colors['text']),
            title_font=dict(color=colors['text'], size=12)
        )

        fig.update_yaxes(
            title="Cumulative Size",
            showgrid=True,
            gridwidth=1,
            gridcolor=colors['grid'],
            tickfont=dict(color=colors['text']),
            title_font=dict(color=colors['text'], size=12)
        )

        return fig

    except Exception as e:
        logger.error(f"创建深度图失败: {str(e)}")
        logger.exception("详细错误信息:")
        return None 