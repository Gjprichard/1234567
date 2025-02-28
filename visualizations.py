import plotly.express as px
import plotly.graph_objects as go
import pandas as pd
from datetime import datetime, timedelta

def create_habit_heatmap(habit_logs):
    # Convert logs to datetime objects
    dates = [datetime.strptime(log[2], '%Y-%m-%d').date() 
             for log in habit_logs]
    
    # Create date range for the last year
    end_date = datetime.now().date()
    start_date = end_date - timedelta(days=365)
    date_range = pd.date_range(start_date, end_date, freq='D')
    
    # Create dataframe with completion status
    df = pd.DataFrame({
        'date': date_range,
        'completed': [date in dates for date in date_range]
    })
    
    # Create heatmap
    fig = px.scatter(
        df,
        x=df.date.dt.strftime('%U'),
        y=df.date.dt.strftime('%w'),
        color='completed',
        color_discrete_map={True: '#28a745', False: '#f8f9fa'},
        title="Habit Completion Heatmap (Last Year)"
    )
    
    # 添加月份标签
    month_labels = []
    month_positions = []
    current_month = None
    
    for date in date_range:
        if current_month != date.month:
            current_month = date.month
            month_labels.append(date.strftime('%b'))
            month_positions.append(date.strftime('%U'))
    
    fig.update_layout(
        xaxis_title="Week of Year",
        yaxis_title="Day of Week",
        showlegend=False,
        yaxis = dict(
            ticktext=['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat'],
            tickvals=[0, 1, 2, 3, 4, 5, 6]
        ),
        xaxis = dict(
            ticktext=month_labels,
            tickvals=month_positions
        )
    )
    
    return fig

def create_streak_chart(habit_logs):
    dates = [datetime.strptime(log[2], '%Y-%m-%d').date() 
             for log in habit_logs]
    dates.sort()
    
    if not dates:
        return go.Figure()
    
    streaks = []
    current_streak = 1
    
    for i in range(1, len(dates)):
        if (dates[i] - dates[i-1]).days == 1:
            current_streak += 1
        else:
            streaks.append(current_streak)
            current_streak = 1
    streaks.append(current_streak)
    
    # 计算最长连续次数
    max_streak = max(streaks) if streaks else 0
    
    fig = go.Figure(data=[
        go.Bar(
            x=list(range(len(streaks))),
            y=streaks,
            marker_color='#007bff'
        )
    ])
    
    fig.update_layout(
        title=f"Streak History (Longest Streak: {max_streak} days)",
        xaxis_title="Streak Number",
        yaxis_title="Streak Length (days)"
    )
    
    return fig

def create_completion_rate_chart(habit_logs):
    if not habit_logs:
        return go.Figure()
    
    dates = [datetime.strptime(log[2], '%Y-%m-%d').date() 
             for log in habit_logs]
    df = pd.DataFrame({'date': dates})
    
    # Calculate weekly completion rates
    weekly_counts = df.resample('W', on='date').size()
    completion_rates = (weekly_counts / 7) * 100
    
    # 添加7天移动平均线
    ma7 = completion_rates.rolling(window=7).mean()
    
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=completion_rates.index,
        y=completion_rates.values,
        mode='lines+markers',
        name='Weekly Rate',
        line=dict(color='#17a2b8')
    ))
    
    fig.add_trace(go.Scatter(
        x=ma7.index,
        y=ma7.values,
        mode='lines',
        name='7-week Moving Average',
        line=dict(color='#dc3545', dash='dash')
    ))
    
    fig.update_layout(
        title="Weekly Completion Rate",
        xaxis_title="Week",
        yaxis_title="Completion Rate (%)",
        yaxis_range=[0, 100],
        showlegend=True
    )
    
    return fig
