import plotly.graph_objects as go
import pandas as pd
import logging
from ..utils.formatters import format_volume

logger = logging.getLogger(__name__)

def create_volume_chart(df: pd.DataFrame) -> go.Figure:
    """创建成交量图表"""
    try:
        if df.empty or 'volume' not in df.columns:
            logger.warning("没有可用的成交量数据")
            return None
            
        # 按成交量排序并获取前10个交易对
        top_volumes = df.groupby('symbol')['volume'].sum().sort_values(ascending=False).head(10)
        
        # 创建图表
        fig = go.Figure(data=[
            go.Bar(
                x=top_volumes.index,
                y=top_volumes.values,
                text=[format_volume(v) for v in top_volumes.values],
                textposition='auto',
            )
        ])
        
        # 更新布局
        fig.update_layout(
            title="交易对成交量排名 (Top 10)",
            xaxis_title="交易对",
            yaxis_title="成交量 (USDT)",
            showlegend=False,
            height=400,
            template='plotly_dark'
        )
        
        # 格式化Y轴数值
        fig.update_yaxes(
            tickformat=".2s",
            title_standoff=25
        )
        
        return fig
        
    except Exception as e:
        logger.error(f"创建成交量图表失败: {str(e)}")
        return None 