import sys
import os
from fastapi import FastAPI, HTTPException, APIRouter, Query
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
import logging
from market_monitor import MarketMonitor
from option_monitor import OptionMonitor
from api.option_routes import create_option_router
from database import Database
from datetime import datetime
import pandas as pd
from typing import List, Dict, Optional

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# 创建FastAPI应用
app = FastAPI(
    title="Market Monitor API",
    description="加密货币市场监控API",
    version="1.0.0"
)

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

# 创建路由
router = APIRouter(prefix="/api/v1")

@router.get("/market/data")
async def get_market_data():
    """获取市场数据"""
    try:
        data = market_monitor.get_market_data()
        return {"status": "success", "data": data}
    except Exception as e:
        logger.error(f"获取市场数据失败: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/market/analysis")
async def get_market_analysis():
    """获取市场分析"""
    try:
        analysis = market_monitor.get_market_analysis()
        return analysis
    except Exception as e:
        logger.error(f"获取市场分析失败: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/market/alerts")
async def get_market_alerts():
    """获取市场预警"""
    try:
        alerts = market_monitor.get_alerts()
        return {"status": "success", "alerts": alerts}
    except Exception as e:
        logger.error(f"获取市场预警失败: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

# 添加路由到应用
app.include_router(router)

# 注册期权路由
option_router = create_option_router(option_monitor)
app.include_router(option_router)

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=5002)