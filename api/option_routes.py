from fastapi import APIRouter, Query
from typing import Dict, List, Optional
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

def create_option_router(option_monitor) -> APIRouter:
    """创建期权相关路由"""
    router = APIRouter(prefix="/api/v1/option", tags=["option"])

    @router.get("/statistics")
    async def get_market_statistics(
        contract_id: Optional[str] = None,
        time_range: int = Query(default=3600, description="统计时间范围(秒)")
    ) -> Dict:
        """获取期权市场统计数据"""
        try:
            stats = option_monitor.db.get_market_statistics(contract_id)
            return {
                "status": "success",
                "data": stats,
                "timestamp": datetime.now().isoformat()
            }
        except Exception as e:
            logger.error(f"获取市场统计失败: {str(e)}")
            return {
                "status": "error",
                "message": str(e),
                "timestamp": datetime.now().isoformat()
            }

    @router.get("/market-data")  # 保持与现有API风格一致
    async def get_option_market_data():
        """获取期权市场数据"""
        try:
            data = option_monitor.get_option_data()
            return {
                'success': True,
                'data': data,
                'timestamp': datetime.now().isoformat()
            }
        except Exception as e:
            logger.error(f"获取期权数据失败: {str(e)}")
            return {
                "status": "error",
                "message": str(e),
                "timestamp": datetime.now().isoformat()
            }

    @router.get("/anomalies")
    async def get_anomaly_contracts(
        threshold: float = Query(default=2.0, description="异常阈值"),
        limit: int = Query(default=10, description="返回记录数")
    ) -> Dict:
        """获取异常合约"""
        try:
            anomalies = option_monitor.db.get_anomaly_contracts(threshold)
            return {
                "status": "success",
                "data": anomalies[:limit],
                "timestamp": datetime.now().isoformat()
            }
        except Exception as e:
            logger.error(f"获取异常合约失败: {str(e)}")
            return {
                "status": "error",
                "message": str(e),
                "timestamp": datetime.now().isoformat()
            }

    @router.get("/market-summary")  # 保持命名一致性
    async def get_market_summary() -> Dict:
        """获取市场概览"""
        try:
            stats = option_monitor.db.get_market_statistics()
            anomalies = option_monitor.db.get_anomaly_contracts(threshold=2.0)
            health_score = calculate_market_health(stats, anomalies)
            
            return {
                "status": "success",
                "data": {
                    "statistics": stats,
                    "anomalies_count": len(anomalies),
                    "health_score": health_score,
                    "last_update": datetime.now().isoformat()
                },
                "timestamp": datetime.now().isoformat()
            }
        except Exception as e:
            logger.error(f"获取市场概览失败: {str(e)}")
            return {
                "status": "error",
                "message": str(e),
                "timestamp": datetime.now().isoformat()
            }

    return router

def calculate_market_health(stats: Dict, anomalies: List[Dict]) -> float:
    """计算市场健康度分数"""
    try:
        score = 100.0
        
        # 异常合约扣分
        anomaly_penalty = len(anomalies) * 5
        score -= min(anomaly_penalty, 30)
        
        # 价格变化扣分
        if 'premium_change_range' in stats:
            price_change = max(
                abs(stats['premium_change_range']['max']),
                abs(stats['premium_change_range']['min'])
            )
            score -= min(price_change * 0.5, 30)
        
        # 成交量变化扣分
        if 'volume_change_range' in stats:
            volume_change = max(
                abs(stats['volume_change_range']['max']),
                abs(stats['volume_change_range']['min'])
            )
            score -= min(volume_change * 0.3, 20)
        
        return max(min(score, 100), 0)
        
    except Exception:
        return 50.0 