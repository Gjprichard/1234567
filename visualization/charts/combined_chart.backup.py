import plotly.graph_objects as go
from plotly.subplots import make_subplots
import pandas as pd
import logging

logger = logging.getLogger(__name__)

def create_combined_chart(kline_df: pd.DataFrame, orderbook: dict, symbol: str) -> go.Figure:
    """创建专业的组合图表"""
    try:
        # 扩展配色方案
        colors = {
            'background': '#1C1C28',
            'paper': '#1C1C28',
            'grid': '#2B2B3E',
            'text': '#E1E1E6',
            'up': '#00C853',
            'down': '#FF3D71',
            'volume_up': 'rgba(0,200,83,0.3)',
            'volume_down': 'rgba(255,61,113,0.3)',
            'bid': 'rgba(0,200,83,0.5)',
            'ask': 'rgba(255,61,113,0.5)'
        }

        # 创建子图布局
        fig = make_subplots(
            rows=3, 
            cols=1,
            shared_xaxes=True,
            vertical_spacing=0.05,
            row_heights=[0.6, 0.2, 0.2],
            subplot_titles=(
                f"{symbol} Price & Volume",
                "Market Depth",
                "Volume Profile"
            )
        )

        # 添加K线图
        fig.add_trace(
            go.Candlestick(
                x=kline_df['timestamp'],
                open=kline_df['open'],
                high=kline_df['high'],
                low=kline_df['low'],
                close=kline_df['close'],
                name='OHLC',
                increasing_line_color=colors['up'],
                decreasing_line_color=colors['down']
            ),
            row=1, col=1
        )

        # 添加成交量柱状图
        colors_volume = [
            colors['volume_up'] if row['close'] >= row['open'] else colors['volume_down']
            for _, row in kline_df.iterrows()
        ]
        
        fig.add_trace(
            go.Bar(
                x=kline_df['timestamp'],
                y=kline_df['volume'],
                name='Volume',
                marker_color=colors_volume
            ),
            row=2, col=1
        )

        # 添加深度图
        if orderbook and 'bids' in orderbook and 'asks' in orderbook:
            # 处理买单深度
            bids_df = pd.DataFrame(orderbook['bids'], columns=['price', 'amount'])
            bids_df['cumulative'] = bids_df['amount'].cumsum()
            
            # 处理卖单深度
            asks_df = pd.DataFrame(orderbook['asks'], columns=['price', 'amount'])
            asks_df['cumulative'] = asks_df['amount'].cumsum()
            
            # 添加买单深度
            fig.add_trace(
                go.Scatter(
                    x=bids_df['price'],
                    y=bids_df['cumulative'],
                    name='Bids',
                    fill='tozeroy',
                    fillcolor=colors['bid'],
                    line=dict(color=colors['up'])
                ),
                row=3, col=1
            )
            
            # 添加卖单深度
            fig.add_trace(
                go.Scatter(
                    x=asks_df['price'],
                    y=asks_df['cumulative'],
                    name='Asks',
                    fill='tozeroy',
                    fillcolor=colors['ask'],
                    line=dict(color=colors['down'])
                ),
                row=3, col=1
            )

        # 更新布局
        fig.update_layout(
            title=f"{symbol} Market Analysis",
            template='plotly_dark',
            plot_bgcolor=colors['background'],
            paper_bgcolor=colors['paper'],
            font=dict(color=colors['text']),
            showlegend=True,
            legend=dict(
                orientation="h",
                yanchor="bottom",
                y=1.02,
                xanchor="right",
                x=1
            ),
            xaxis_rangeslider_visible=False,
            height=800,
            margin=dict(l=50, r=50, t=85, b=50)
        )

        # 更新X轴
        fig.update_xaxes(
            showgrid=True,
            gridwidth=1,
            gridcolor=colors['grid'],
            tickfont=dict(color=colors['text']),
            title_font=dict(color=colors['text'], size=12)
        )

        # 更新Y轴
        fig.update_yaxes(
            showgrid=True,
            gridwidth=1,
            gridcolor=colors['grid'],
            tickfont=dict(color=colors['text']),
            title_font=dict(color=colors['text'], size=12),
            zeroline=True,
            zerolinewidth=2,
            zerolinecolor=colors['grid']
        )

        # 添加水印
        fig.add_annotation(
            text="Market Monitor Pro",
            xref="paper",
            yref="paper",
            x=0.5,
            y=0.5,
            showarrow=False,
            font=dict(size=50, color="rgba(255,255,255,0.02)"),
            textangle=-30
        )

        return fig

    except Exception as e:
        logger.error(f"创建组合图表失败: {str(e)}")
        logger.exception("详细错误信息:")
        return None 