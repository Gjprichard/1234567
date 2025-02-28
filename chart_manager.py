import plotly.graph_objects as go
import pandas as pd
import numpy as np
from typing import List, Optional
import streamlit as st
from plotly.subplots import make_subplots

class ChartManager:
    def __init__(self):
        self.chart_height = 600
        self.chart_width = None  # 自适应宽度
        
    def create_price_chart(self, 
                          prices: List[float], 
                          volumes: List[float], 
                          symbol: str) -> Optional[go.Figure]:
        """创建价格和成交量组合图表"""
        try:
            # 创建子图
            fig = go.Figure()
            
            # 添加价格线图
            fig.add_trace(
                go.Scatter(
                    y=prices,
                    name='价格',
                    line=dict(color='#2196F3', width=2),
                    hovertemplate='价格: $%{y:.4f}<extra></extra>'
                )
            )
            
            # 更新布局
            fig.update_layout(
                title=f'{symbol} 价格走势',
                height=self.chart_height,
                width=self.chart_width,
                showlegend=True,
                plot_bgcolor='rgba(0,0,0,0)',
                paper_bgcolor='rgba(0,0,0,0)',
                xaxis=dict(
                    showgrid=True,
                    gridcolor='rgba(128,128,128,0.2)',
                    title='时间'
                ),
                yaxis=dict(
                    showgrid=True,
                    gridcolor='rgba(128,128,128,0.2)',
                    title='价格 ($)',
                    tickformat='.4f'
                ),
                margin=dict(l=10, r=10, t=40, b=10)
            )
            
            return fig
            
        except Exception as e:
            st.error(f"创建价格图表失败: {str(e)}")
            return None
            
    def create_market_overview(self, df: pd.DataFrame) -> Optional[go.Figure]:
        """创建市场概览图表"""
        try:
            # 计算涨跌分布
            changes = pd.to_numeric(df['24h涨跌'].str.rstrip('%'), errors='coerce')
            bins = [-np.inf, -10, -5, -2, 0, 2, 5, 10, np.inf]
            labels = ['<-10%', '-10%~-5%', '-5%~-2%', '-2%~0%', '0%~2%', '2%~5%', '5%~10%', '>10%']
            distribution = pd.cut(changes, bins=bins, labels=labels).value_counts()
            
            # 创建图表
            fig = go.Figure()
            
            # 添加柱状图
            colors = ['#FF1744', '#FF5252', '#FF867F', '#FFCDD2', 
                     '#C8E6C9', '#81C784', '#4CAF50', '#2E7D32']
            
            fig.add_trace(go.Bar(
                x=distribution.index,
                y=distribution.values,
                marker_color=colors,
                name='涨跌分布'
            ))
            
            # 更新布局
            fig.update_layout(
                title='24小时涨跌分布',
                xaxis_title='涨跌幅区间',
                yaxis_title='交易对数量',
                showlegend=False,
                height=300,
                plot_bgcolor='rgba(0,0,0,0)',
                paper_bgcolor='rgba(0,0,0,0)',
                margin=dict(l=10, r=10, t=40, b=10)
            )
            
            return fig
            
        except Exception as e:
            st.error(f"创建市场概览图表失败: {str(e)}")
            return None

    def create_volume_distribution(self, df: pd.DataFrame) -> Optional[go.Figure]:
        """创建成交量分布图表"""
        try:
            # 提取成交量数据
            volumes = pd.to_numeric(df['24h成交额'].str.replace('$', '').str.replace(',', ''), errors='coerce')
            
            # 创建图表
            fig = go.Figure()
            
            # 添加直方图
            fig.add_trace(go.Histogram(
                x=volumes,
                nbinsx=30,
                name='成交量分布',
                marker_color='rgba(33, 150, 243, 0.6)',
                hovertemplate='成交量: $%{x:,.0f}<br>数量: %{y}<extra></extra>'
            ))
            
            # 更新布局
            fig.update_layout(
                title='24小时成交量分布',
                xaxis_title='成交量 (USDT)',
                yaxis_title='交易对数量',
                showlegend=False,
                height=300,
                plot_bgcolor='rgba(0,0,0,0)',
                paper_bgcolor='rgba(0,0,0,0)',
                margin=dict(l=10, r=10, t=40, b=10)
            )
            
            # 使用对数刻度
            fig.update_xaxes(type='log')
            
            return fig
            
        except Exception as e:
            st.error(f"创建成交量分布图表失败: {str(e)}")
            return None

    def create_price_trend_chart(self, df: pd.DataFrame) -> Optional[go.Figure]:
        """创建价格趋势图表"""
        try:
            # 创建子图
            fig = make_subplots(
                rows=2, cols=1,
                shared_xaxis=True,
                vertical_spacing=0.05,
                subplot_titles=('价格趋势', '成交量趋势')
            )
            
            # 添加价格线和15分钟变化
            fig.add_trace(
                go.Scatter(
                    x=df.index,
                    y=df['price'],
                    name='价格',
                    line=dict(color='#2196F3', width=2)
                ),
                row=1, col=1
            )
            
            # 添加15分钟价格变化百分比
            fig.add_trace(
                go.Scatter(
                    x=df.index,
                    y=df['price_change_15m'],
                    name='15分钟涨跌',
                    line=dict(color='#FF4081', width=1, dash='dot'),
                    yaxis='y2'
                ),
                row=1, col=1
            )
            
            # 添加成交量柱状图
            fig.add_trace(
                go.Bar(
                    x=df.index,
                    y=df['volume'],
                    name='成交量',
                    marker_color='rgba(33, 150, 243, 0.3)'
                ),
                row=2, col=1
            )
            
            # 添加15分钟成交量变化百分比
            fig.add_trace(
                go.Scatter(
                    x=df.index,
                    y=df['volume_change_15m'],
                    name='成交量变化',
                    line=dict(color='#FF9800', width=1, dash='dot'),
                    yaxis='y4'
                ),
                row=2, col=1
            )
            
            # 更新布局
            fig.update_layout(
                height=500,
                showlegend=True,
                plot_bgcolor='rgba(0,0,0,0)',
                paper_bgcolor='rgba(0,0,0,0)',
                margin=dict(l=10, r=10, t=40, b=10),
                legend=dict(
                    orientation="h",
                    yanchor="bottom",
                    y=1.02,
                    xanchor="right",
                    x=1
                )
            )
            
            # 更新Y轴
            fig.update_yaxes(
                title_text="价格 (USDT)",
                tickformat='.4f',
                gridcolor='rgba(128,128,128,0.2)',
                row=1, col=1
            )
            fig.update_yaxes(
                title_text="成交量",
                gridcolor='rgba(128,128,128,0.2)',
                row=2, col=1
            )
            
            # 添加第二个Y轴用于显示变化百分比
            fig.update_layout(
                yaxis2=dict(
                    title="15分钟涨跌 (%)",
                    overlaying="y",
                    side="right",
                    tickformat='.2f'
                ),
                yaxis4=dict(
                    title="成交量变化 (%)",
                    overlaying="y3",
                    side="right",
                    tickformat='.2f'
                )
            )
            
            return fig
            
        except Exception as e:
            st.error(f"创建价格趋势图表失败: {str(e)}")
            return None

    def create_market_metrics(self, df: pd.DataFrame) -> None:
        """创建市场指标展示"""
        try:
            # 创建三列布局
            col1, col2, col3 = st.columns(3)
            
            with col1:
                st.metric(
                    "24小时涨跌",
                    f"{df['24h涨跌'].iloc[0]}",
                    delta=None,
                    delta_color="normal"
                )
                
            with col2:
                st.metric(
                    "15分钟涨跌",
                    f"{df['15m涨跌'].iloc[0]}",
                    delta=None,
                    delta_color="normal"
                )
                
            with col3:
                st.metric(
                    "成交量变化",
                    f"{df['volume_change_15m'].iloc[0]:.2f}%",
                    delta=None,
                    delta_color="normal"
                )
                
        except Exception as e:
            st.error(f"创建市场指标失败: {str(e)}")

    def create_candlestick_chart(self, price_df: pd.DataFrame, metric_df: pd.DataFrame) -> go.Figure:
        """创建K线图"""
        fig = make_subplots(
            rows=2, cols=1,
            shared_xaxis=True,
            vertical_spacing=0.05,
            subplot_titles=('价格', '成交量')
        )

        # 添加K线图
        fig.add_trace(
            go.Candlestick(
                x=price_df['timestamp'],
                open=price_df['open'],
                high=price_df['high'],
                low=price_df['low'],
                close=price_df['close'],
                name='K线'
            ),
            row=1, col=1
        )

        # 添加成交量图
        fig.add_trace(
            go.Bar(
                x=price_df['timestamp'],
                y=price_df['quote_volume'],
                name='成交量'
            ),
            row=2, col=1
        )

        # 添加趋势指标
        if not metric_df.empty:
            fig.add_trace(
                go.Scatter(
                    x=metric_df['timestamp'],
                    y=metric_df['price_trend'],
                    name='价格趋势',
                    line=dict(color='orange')
                ),
                row=1, col=1
            )
            
            fig.add_trace(
                go.Scatter(
                    x=metric_df['timestamp'],
                    y=metric_df['volume_trend'],
                    name='成交量趋势',
                    line=dict(color='purple')
                ),
                row=2, col=1
            )

        # 更新布局
        fig.update_layout(
            height=800,
            xaxis_rangeslider_visible=False
        )

        return fig

    def create_trend_chart(self, df: pd.DataFrame) -> go.Figure:
        """创建K线和成交量组合图表"""
        try:
            # 创建子图，设置共享x轴
            fig = make_subplots(
                rows=2, cols=1,
                row_heights=[0.7, 0.3],
                vertical_spacing=0.05,
                specs=[[{"secondary_y": False}],
                      [{"secondary_y": False}]],
                shared_xaxes=True  # 使用 shared_xaxes 替代 shared_xaxis
            )
            
            # 添加K线图
            fig.add_trace(
                go.Candlestick(
                    x=df.index,
                    open=df['open'],
                    high=df['high'],
                    low=df['low'],
                    close=df['close'],
                    name='价格'
                ),
                row=1, col=1
            )
            
            # 添加成交量柱状图
            colors = ['red' if row['close'] < row['open'] else 'green' 
                     for _, row in df.iterrows()]
            
            fig.add_trace(
                go.Bar(
                    x=df.index,
                    y=df['volume'],
                    name='成交量',
                    marker_color=colors
                ),
                row=2, col=1
            )
            
            # 更新布局
            fig.update_layout(
                title='价格和成交量走势',
                height=self.chart_height,
                width=self.chart_width,
                showlegend=True,
                xaxis_rangeslider_visible=False,
                margin=dict(l=10, r=10, t=30, b=10),
                template='plotly_dark',
                paper_bgcolor='rgba(0,0,0,0)',
                plot_bgcolor='rgba(0,0,0,0)',
                font=dict(size=12)
            )
            
            # 更新X轴
            fig.update_xaxes(
                gridcolor='rgba(128,128,128,0.1)',
                zeroline=False,
                showgrid=True
            )
            
            # 更新Y轴
            fig.update_yaxes(
                title_text="价格 (USDT)",
                tickformat='.4f',
                gridcolor='rgba(128,128,128,0.1)',
                zeroline=False,
                row=1, col=1
            )
            fig.update_yaxes(
                title_text="成交量",
                gridcolor='rgba(128,128,128,0.1)',
                zeroline=False,
                row=2, col=1
            )
            
            return fig
            
        except Exception as e:
            st.error(f"创建图表失败: {str(e)}")
            return None 