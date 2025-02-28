import plotly.graph_objects as go
from plotly.subplots import make_subplots
import pandas as pd
import logging
from ..utils.formatters import format_price, format_volume

logger = logging.getLogger(__name__)

def create_kline_chart(df: pd.DataFrame, symbol: str) -> go.Figure:
    """创建K线图表"""
    try:
        # 检查必要的列
        required_columns = {'timestamp', 'open', 'high', 'low', 'close', 'volume'}
        if not all(col in df.columns for col in required_columns):
            logger.error(f"K线数据缺少必要的列: {required_columns - set(df.columns)}")
            return None
            
        # 确保时间戳格式正确
        if not isinstance(df['timestamp'].iloc[0], (int, float)):
            df['timestamp'] = pd.to_datetime(df['timestamp'])
        else:
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')

        # 设置专业的配色方案
        colors = {
            'background': '#1C1C28',
            'paper': '#1C1C28',
            'grid': '#2B2B3E',
            'text': '#E1E1E6',
            'up': '#00C853',
            'down': '#FF3D71',
            'volume_up': 'rgba(0,200,83,0.3)',
            'volume_down': 'rgba(255,61,113,0.3)',
            'ma5': '#FF9900',
            'ma10': '#00FFFF',
            'ma20': '#FF00FF'
        }

        # 创建子图
        fig = make_subplots(
            rows=2, cols=1,
            shared_xaxes=True,
            vertical_spacing=0.03,
            row_heights=[0.7, 0.3]
        )

        # 添加K线图
        fig.add_trace(
            go.Candlestick(
                x=df['timestamp'],
                open=df['open'],
                high=df['high'],
                low=df['low'],
                close=df['close'],
                increasing_line_color=colors['up'],
                decreasing_line_color=colors['down'],
                name='OHLC'
            ),
            row=1, col=1
        )

        # 计算并添加移动平均线
        df['MA5'] = df['close'].rolling(window=5).mean()
        df['MA10'] = df['close'].rolling(window=10).mean()
        df['MA20'] = df['close'].rolling(window=20).mean()

        fig.add_trace(
            go.Scatter(
                x=df['timestamp'],
                y=df['MA5'],
                line=dict(color=colors['ma5'], width=1),
                name='MA5'
            ),
            row=1, col=1
        )

        fig.add_trace(
            go.Scatter(
                x=df['timestamp'],
                y=df['MA10'],
                line=dict(color=colors['ma10'], width=1),
                name='MA10'
            ),
            row=1, col=1
        )

        fig.add_trace(
            go.Scatter(
                x=df['timestamp'],
                y=df['MA20'],
                line=dict(color=colors['ma20'], width=1),
                name='MA20'
            ),
            row=1, col=1
        )

        # 添加成交量图
        colors_volume = [
            colors['volume_up'] if row['close'] >= row['open']
            else colors['volume_down']
            for _, row in df.iterrows()
        ]

        fig.add_trace(
            go.Bar(
                x=df['timestamp'],
                y=df['volume'],
                marker_color=colors_volume,
                name='Volume'
            ),
            row=2, col=1
        )

        # 更新布局
        fig.update_layout(
            height=600,
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
            xaxis_rangeslider_visible=False
        )

        # 更新X轴和Y轴样式
        fig.update_xaxes(
            showgrid=True,
            gridwidth=1,
            gridcolor=colors['grid'],
            tickfont=dict(color=colors['text']),
            title_font=dict(color=colors['text'], size=12)
        )

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

        return fig

    except Exception as e:
        logger.error(f"创建K线图失败: {str(e)}")
        logger.exception("详细错误信息:")
        return None 