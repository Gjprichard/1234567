import streamlit as st
from datetime import datetime, timedelta
from visualizations import create_habit_heatmap, create_streak_chart, create_completion_rate_chart

def generate_sample_data():
    """生成示例数据用于演示"""
    today = datetime.now().date()
    sample_logs = []
    
    # 生成过去90天的随机数据
    for i in range(90):
        # 70%的概率记录一个日期
        if i % 3 != 0:  # 简单模拟70%的完成率
            date = today - timedelta(days=i)
            sample_logs.append((i, 1, date.strftime('%Y-%m-%d')))
    
    # 确保最近有一些连续的记录
    for i in range(5):
        date = today - timedelta(days=i)
        if (i, 1, date.strftime('%Y-%m-%d')) not in sample_logs:
            sample_logs.append((i+100, 1, date.strftime('%Y-%m-%d')))
    
    return sample_logs

def main():
    st.title("习惯追踪可视化演示")
    
    # 生成示例数据
    sample_logs = generate_sample_data()
    
    # 创建热力图
    st.header("1. 习惯完成热力图")
    st.plotly_chart(create_habit_heatmap(sample_logs), use_container_width=True)
    
    # 创建连续记录图表
    st.header("2. 连续记录历史")
    st.plotly_chart(create_streak_chart(sample_logs), use_container_width=True)
    
    # 创建完成率图表
    st.header("3. 每周完成率趋势")
    st.plotly_chart(create_completion_rate_chart(sample_logs), use_container_width=True)
    
    # 添加数据说明
    with st.expander("查看示例数据说明"):
        st.write("""
        - 示例数据包含过去90天的记录
        - 模拟了约70%的完成率
        - 最近5天保证有连续记录
        - 数据格式: (id, habit_id, date)
        """)
        st.write("数据示例：")
        st.write(sample_logs[:5])

if __name__ == "__main__":
    main() 