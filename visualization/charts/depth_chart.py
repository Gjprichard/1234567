import plotly.graph_objects as go
import pandas as pd
import logging

logger = logging.getLogger(__name__)

def create_depth_chart(bids: pd.DataFrame, asks: pd.DataFrame) -> go.Figure:
    """创建市场深度图"""
    try:
        if bids.empty or asks.empty:
            return None
            
        fig = go.Figure()
        
        # 添加买单深度
        fig.add_trace(go.Scatter(
            x=bids['price'],
            y=bids['cumulative'],
            name='买单',
            fill='tonexty',
            fillcolor='rgba(38,166,154,0.3)',
            line=dict(color='#26A69A')
        ))
        
        # 添加卖单深度
        fig.add_trace(go.Scatter(
            x=asks['price'],
            y=asks['cumulative'],
            name='卖单',
            fill='tonexty',
            fillcolor='rgba(239,83,80,0.3)',
            line=dict(color='#EF5350')
        ))
        
        # 更新布局
        fig.update_layout(
            title=dict(
                text='市场深度',
                font=dict(size=20, color='#E0E0E0')
            ),
            height=300,
            template='plotly_dark',
            plot_bgcolor='#1E1E1E',
            paper_bgcolor='#1E1E1E',
            showlegend=True,
            legend=dict(
                orientation="h",
                yanchor="bottom",
                y=1.02,
                xanchor="right",
                x=1
            ),
            xaxis_title='价格',
            yaxis_title='累计数量'
        )
        
        return fig
        
    except Exception as e:
        logger.error(f"创建深度图表失败: {str(e)}")
        return None