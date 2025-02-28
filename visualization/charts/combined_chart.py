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
            'ma5': '#FF9900',
            'ma10': '#00FFFF',
            'ma20': '#FF00FF',
            'depth_buy': 'rgba(0,200,83,0.2)',
            'depth_sell': 'rgba(255,61,113,0.2)',
            'annotation': '#8F92A1',
            'highlight': '#3366FF'
        }

        # 计算关键指标
        current_price = kline_df['close'].iloc[-1]
        price_change = ((current_price - kline_df['open'].iloc[-1]) / kline_df['open'].iloc[-1]) * 100
        high_24h = kline_df['high'].max()
        low_24h = kline_df['low'].min()
        volume_24h = kline_df['volume'].sum()

        # 创建子图布局
        fig = make_subplots(
            rows=3, cols=1,  # 改为3行
            shared_xaxes=True,
            vertical_spacing=0.01,
            row_heights=[0.6, 0.2, 0.2],  # 调整比例
            subplot_titles=('', '', '')
        )

        # 1. 添加K线图
        fig.add_trace(
            go.Candlestick(
                x=kline_df['timestamp'],
                open=kline_df['open'],
                high=kline_df['high'],
                low=kline_df['low'],
                close=kline_df['close'],
                increasing_line_color=colors['up'],
                decreasing_line_color=colors['down'],
                name='OHLC',
                increasing_fillcolor=colors['up'],
                decreasing_fillcolor=colors['down']
            ),
            row=1, col=1
        )

        # 2. 添加移动平均线
        for ma, color in [('MA5', 'ma5'), ('MA10', 'ma10'), ('MA20', 'ma20')]:
            kline_df[ma] = kline_df['close'].rolling(window=int(ma[2:])).mean()
            fig.add_trace(
                go.Scatter(
                    x=kline_df['timestamp'],
                    y=kline_df[ma],
                    line=dict(color=colors[color], width=1),
                    name=ma
                ),
                row=1, col=1
            )

        # 3. 添加成交量柱状图
        colors_volume = [
            colors['volume_up'] if row['close'] >= row['open']
            else colors['volume_down']
            for _, row in kline_df.iterrows()
        ]
        
        fig.add_trace(
            go.Bar(
                x=kline_df['timestamp'],
                y=kline_df['volume'],
                marker_color=colors_volume,
                name='Volume',
                showlegend=False
            ),
            row=2, col=1
        )

        # 4. 添加深度图
        if orderbook and orderbook['bids'] and orderbook['asks']:
            bids_df = pd.DataFrame(orderbook['bids'], columns=['price', 'amount'])
            asks_df = pd.DataFrame(orderbook['asks'], columns=['price', 'amount'])
            
            bids_df['cumulative'] = bids_df['amount'].cumsum()
            asks_df['cumulative'] = asks_df['amount'].cumsum()

            fig.add_trace(
                go.Scatter(
                    x=bids_df['price'],
                    y=bids_df['cumulative'],
                    fill='tozeroy',
                    name='Bids',
                    line=dict(color=colors['up']),
                    fillcolor=colors['depth_buy'],
                    hovertemplate='Price: %{x}<br>Cumulative: %{y:.2f}<extra></extra>'
                ),
                row=3, col=1  # 移到第三行
            )

            fig.add_trace(
                go.Scatter(
                    x=asks_df['price'],
                    y=asks_df['cumulative'],
                    fill='tozeroy',
                    name='Asks',
                    line=dict(color=colors['down']),
                    fillcolor=colors['depth_sell'],
                    hovertemplate='Price: %{x}<br>Cumulative: %{y:.2f}<extra></extra>'
                ),
                row=3, col=1  # 移到第三行
            )

        # 5. 添加市场信息标注
        fig.add_annotation(
            text=f"{symbol}",
            xref="paper",
            yref="paper",
            x=0.01,
            y=0.99,
            showarrow=False,
            font=dict(size=20, color=colors['text']),
            bgcolor='rgba(28,28,40,0.8)',
            bordercolor=colors['grid'],
            borderwidth=1,
            borderpad=4
        )

        # 添加价格信息
        fig.add_annotation(
            text=f"Price: {current_price:.2f} ({price_change:+.2f}%)",
            xref="paper",
            yref="paper",
            x=0.01,
            y=0.95,
            showarrow=False,
            font=dict(
                size=14,
                color=colors['up'] if price_change >= 0 else colors['down']
            ),
            bgcolor='rgba(28,28,40,0.8)',
            bordercolor=colors['grid'],
            borderwidth=1,
            borderpad=4
        )

        # 添加24h统计
        stats_text = (
            f"24h High: {high_24h:.2f}<br>"
            f"24h Low: {low_24h:.2f}<br>"
            f"24h Volume: {volume_24h:.2f}"
        )
        fig.add_annotation(
            text=stats_text,
            xref="paper",
            yref="paper",
            x=0.99,
            y=0.99,
            showarrow=False,
            font=dict(size=12, color=colors['text']),
            bgcolor='rgba(28,28,40,0.8)',
            bordercolor=colors['grid'],
            borderwidth=1,
            borderpad=4,
            align='left'
        )

        # 更新布局
        fig.update_layout(
            height=800,  # 增加高度
            template='plotly_dark',
            paper_bgcolor=colors['paper'],
            plot_bgcolor=colors['background'],
            margin=dict(t=20, l=50, r=5, b=20),
            showlegend=True,
            legend=dict(
                orientation="h",
                yanchor="bottom",
                y=1,
                xanchor="left",
                x=0.3,
                bgcolor='rgba(28,28,40,0.8)',
                bordercolor=colors['grid'],
                borderwidth=1,
                font=dict(color=colors['text'])
            ),
            xaxis_rangeslider_visible=False,
            hoverlabel=dict(
                bgcolor=colors['background'],
                font_size=12,
                font_family="IBM Plex Mono"
            )
        )

        # 更新坐标轴样式
        fig.update_xaxes(
            showgrid=True,
            gridwidth=1,
            gridcolor=colors['grid'],
            tickfont=dict(color=colors['text']),
            tickformat='%H:%M',
            showspikes=True,
            spikethickness=1,
            spikecolor=colors['grid'],
            spikemode='across'
        )

        # 为不同区域设置不同的Y轴格式
        # K线图区域
        fig.update_yaxes(
            row=1,
            showgrid=True,
            gridwidth=1,
            gridcolor=colors['grid'],
            tickfont=dict(color=colors['text']),
            tickformat='.2f',
            showspikes=True,
            spikethickness=1,
            spikecolor=colors['grid'],
            spikemode='across',
            title="Price"
        )

        # 成交量区域
        fig.update_yaxes(
            row=2,
            showgrid=True,
            gridwidth=1,
            gridcolor=colors['grid'],
            tickfont=dict(color=colors['text']),
            tickformat='.2f',
            title="Volume"
        )

        # 深度图区域
        fig.update_yaxes(
            row=3,
            showgrid=True,
            gridwidth=1,
            gridcolor=colors['grid'],
            tickfont=dict(color=colors['text']),
            tickformat='.2f',
            title="Depth"
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