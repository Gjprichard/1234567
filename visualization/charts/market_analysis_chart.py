import plotly.graph_objects as go
from plotly.subplots import make_subplots
import pandas as pd
import logging
from ..utils.formatters import format_price, format_volume, format_change

logger = logging.getLogger(__name__)

def create_market_analysis_chart(df: pd.DataFrame) -> go.Figure:
    """创建市场分析图表"""
    try:
        # 打印输入数据信息
        logger.debug(f"输入数据形状: {df.shape}")
        logger.debug(f"输入数据列: {df.columns.tolist()}")
        
        # 确保数据包含必要的列
        required_columns = {'symbol', 'price_change_15m', 'volume_change_15m'}
        missing_columns = required_columns - set(df.columns)
        if missing_columns:
            logger.error(f"数据缺少必要的列: {missing_columns}")
            return None

        # 确保数据不为空
        if df.empty:
            logger.warning("数据为空")
            return None
            
        # 检查数据类型
        logger.debug(f"数据类型:\n{df.dtypes}")
        
        # 尝试转换数据类型
        try:
            df['price_change_15m'] = pd.to_numeric(df['price_change_15m'])
            df['volume_change_15m'] = pd.to_numeric(df['volume_change_15m'])
        except Exception as e:
            logger.error(f"数据类型转换失败: {str(e)}")
            return None

        # 设置专业的配色方案
        colors = {
            'background': '#1C1C28',
            'paper': '#1C1C28',
            'grid': '#2B2B3E',
            'text': '#E1E1E6',
            'positive': '#00C853',
            'negative': '#FF3D71',
            'neutral': '#8F92A1',
            'accent': '#3366FF'
        }

        # 创建子图布局
        fig = make_subplots(
            rows=2, cols=2,
            subplot_titles=(
                '价格变化分布',
                '成交量分布',
                '市场趋势',
                '交易对分析'
            ),
            specs=[
                [{"type": "bar"}, {"type": "pie"}],
                [{"type": "scatter"}, {"type": "table"}]
            ],
            vertical_spacing=0.12,
            horizontal_spacing=0.08
        )

        # 1. 价格变化柱状图
        df_sorted = df.sort_values('price_change_15m', ascending=True)
        colors_price = [
            colors['positive'] if x >= 0 else colors['negative']
            for x in df_sorted['price_change_15m']
        ]
        
        fig.add_trace(
            go.Bar(
                x=df_sorted['symbol'],
                y=df_sorted['price_change_15m'],
                marker_color=colors_price,
                text=df_sorted['price_change_15m'].apply(lambda x: f'{x:.2f}%'),
                textposition='auto',
                name='价格变化'
            ),
            row=1, col=1
        )

        # 2. 成交量分布饼图
        volume_data = df.nlargest(5, 'volume')
        fig.add_trace(
            go.Pie(
                labels=volume_data['symbol'],
                values=volume_data['volume'],
                hole=0.5,
                marker_colors=[colors['accent'], colors['positive'], colors['neutral']],
                textinfo='label+percent',
                name='成交量分布'
            ),
            row=1, col=2
        )

        # 3. 市场趋势散点图
        fig.add_trace(
            go.Scatter(
                x=df['price_change_15m'],
                y=df['volume_change_15m'],
                mode='markers+text',
                marker=dict(
                    size=12,
                    color=df['volume'],
                    colorscale='Viridis',
                    showscale=True,
                    colorbar=dict(title='成交量')
                ),
                text=df['symbol'],
                textposition='top center',
                name='市场趋势'
            ),
            row=2, col=1
        )

        # 4. 交易对分析表格
        df_analysis = df.nlargest(5, 'volume')[['symbol', 'price', 'volume', 'price_change_15m']]
        fig.add_trace(
            go.Table(
                header=dict(
                    values=['交易对', '价格', '成交量', '涨跌幅'],
                    fill_color=colors['grid'],
                    align='left',
                    font=dict(color=colors['text'], size=12)
                ),
                cells=dict(
                    values=[
                        df_analysis['symbol'],
                        df_analysis['price'].apply(lambda x: f'{x:.2f}'),
                        df_analysis['volume'].apply(lambda x: f'{x:,.0f}'),
                        df_analysis['price_change_15m'].apply(lambda x: f'{x:+.2f}%')
                    ],
                    fill_color=colors['paper'],
                    align='left',
                    font=dict(color=colors['text'], size=11)
                )
            ),
            row=2, col=2
        )

        # 更新布局
        fig.update_layout(
            height=800,
            showlegend=True,
            template='plotly_dark',
            paper_bgcolor=colors['paper'],
            plot_bgcolor=colors['background'],
            title={
                'text': '市场分析概览',
                'y': 0.98,
                'x': 0.5,
                'xanchor': 'center',
                'yanchor': 'top',
                'font': {'size': 24, 'color': colors['text']}
            },
            margin=dict(t=100, l=50, r=50, b=50),
            legend=dict(
                orientation="h",
                yanchor="bottom",
                y=1.02,
                xanchor="right",
                x=1,
                bgcolor='rgba(0,0,0,0)',
                font=dict(color=colors['text'])
            )
        )

        # 更新坐标轴样式
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

        # 添加水印（移除了 layer 属性）
        fig.add_annotation(
            text="Market Monitor",
            xref="paper",
            yref="paper",
            x=0.5,
            y=0.5,
            showarrow=False,
            font=dict(size=50, color="rgba(255,255,255,0.05)"),
            textangle=-30
        )

        return fig

    except Exception as e:
        logger.error(f"创建市场分析图表失败: {str(e)}")
        logger.exception("详细错误信息:")
        return None 