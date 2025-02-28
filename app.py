import streamlit as st
import pandas as pd
from visualization.components.main_page import show_monitoring_page
from visualization.components.settings_panel import show_settings_panel
from visualization.components.option_dashboard import show_option_dashboard
import requests
import logging
from market_monitor import MarketMonitor
import atexit
import threading
import time
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
from option_monitor.core.option_monitor import OptionMonitor

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# API配置
API_BASE_URL = "http://localhost:5000/api"

app = FastAPI()

# 配置CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 初始化监控器
market_monitor = MarketMonitor()
option_monitor = OptionMonitor()

@app.on_event("startup")
async def startup_event():
    """启动时初始化"""
    try:
        market_monitor.start()
        option_monitor.start()
        logger.info("监控器初始化成功")
    except Exception as e:
        logger.error(f"监控器初始化失败: {str(e)}")
        raise

@app.on_event("shutdown")
async def shutdown_event():
    """关闭时清理资源"""
    try:
        market_monitor.stop()
        option_monitor.stop()
        logger.info("监控器已停止")
    except Exception as e:
        logger.error(f"停止监控器失败: {str(e)}")

# 现货市场API
@app.get("/api/market/data")
async def get_market_data():
    """获取市场数据"""
    try:
        data = market_monitor.get_market_data()
        return {"data": data}
    except Exception as e:
        logger.error(f"获取市场数据失败: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

# 期权市场API
@app.get("/api/option/contracts/{underlying}")
async def get_option_contracts(underlying: str):
    """获取期权合约列表"""
    try:
        contracts = option_monitor.get_active_contracts(underlying)
        return {"data": contracts}
    except Exception as e:
        logger.error(f"获取期权合约失败: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/option/chain/{underlying}")
async def get_option_chain(underlying: str):
    """获取期权链数据"""
    try:
        chain = option_monitor.get_option_chain(underlying)
        if chain:
            return {
                "data": {
                    "underlying": chain.underlying,
                    "expiry_date": chain.expiry_date,
                    "calls": chain.calls,
                    "puts": chain.puts
                }
            }
        else:
            return {"data": None}
    except Exception as e:
        logger.error(f"获取期权链数据失败: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/option/market/{symbol}")
async def get_option_market_data(symbol: str):
    """获取期权市场数据"""
    try:
        data = option_monitor.api.get_market_data(symbol)
        return {"data": data}
    except Exception as e:
        logger.error(f"获取期权市场数据失败: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

def cleanup():
    """清理资源"""
    logger.info("正在停止市场监控...")
    if 'market_monitor' in st.session_state:
        st.session_state.market_monitor.stop()

def fetch_data(endpoint: str) -> dict:
    """从API获取数据"""
    try:
        response = requests.get(f"{API_BASE_URL}/{endpoint}")
        response.raise_for_status()
        return response.json()
    except Exception as e:
        logger.error(f"获取数据失败: {str(e)}")
        return {}

def main():
    """主函数"""
    try:
        # 设置页面配置
        st.set_page_config(
            page_title="市场监控系统",
            page_icon="📊",
            layout="wide"
        )

        # 初始化监控器（如果还没有初始化）
        if 'market_monitor' not in st.session_state:
            st.session_state.market_monitor = MarketMonitor()
            st.session_state.market_monitor.start()
            
        if 'option_monitor' not in st.session_state:
            st.session_state.option_monitor = OptionMonitor()
            st.session_state.option_monitor.start()

        # 侧边栏
        with st.sidebar:
            st.title("市场监控系统")
            page = st.radio(
                "选择页面",
                ["市场监控", "期权监控", "设置"]
            )

        # 根据选择显示不同页面
        if page == "市场监控":
            show_monitoring_page(st.session_state.market_monitor)
        elif page == "期权监控":
            show_option_monitoring_page(st.session_state.option_monitor)
        else:
            show_settings_panel()

    except Exception as e:
        logger.error(f"应用运行错误: {str(e)}")
        st.error(f"应用发生错误: {str(e)}")

def show_option_monitoring_page(monitor):
    """显示期权监控页面"""
    st.title("期权市场监控")
    
    # 获取最新数据
    data = monitor.get_option_data()
    
    if not data:
        st.warning("暂无期权数据")
        return
        
    # 显示期权数据
    st.subheader("期权市场概览")
    df = pd.DataFrame(data['contracts'])
    st.dataframe(df)
    
    # 显示市场指标
    st.subheader("市场指标")
    metrics = data['metrics']
    cols = st.columns(4)
    with cols[0]:
        st.metric("平均隐含波动率", f"{metrics.get('avg_iv', 0):.2f}%")
    with cols[1]:
        st.metric("成交量", f"{metrics.get('total_volume', 0):,.0f}")
    with cols[2]:
        st.metric("持仓量", f"{metrics.get('total_oi', 0):,.0f}")
    with cols[3]:
        st.metric("看跌/看涨比率", f"{metrics.get('put_call_ratio', 0):.2f}")
    
    # 显示异常提醒
    if data['anomalies']:
        st.subheader("异常提醒")
        for anomaly in data['anomalies']:
            st.warning(anomaly['message'])

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        logger.error(f"应用运行错误: {str(e)}")
        st.error(f"应用发生错误: {str(e)}")
