import requests
import logging
from typing import Dict, Any, Optional, List
from abc import ABC, abstractmethod
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

logger = logging.getLogger(__name__)

class BaseMonitor(ABC):
    def __init__(self):
        self.session = self._create_session()
        self.market_data = None
        self.last_update = None

    def _create_session(self):
        """创建请求会话"""
        session = requests.Session()
        retry = Retry(total=3, backoff_factor=0.5)
        session.mount("https://", HTTPAdapter(max_retries=retry))
        return session

    @abstractmethod
    def update_market_data(self) -> bool:
        """更新市场数据"""
        pass

    @abstractmethod
    def get_historical_data(self, symbol: str) -> tuple:
        """获取历史数据"""
        pass

    @abstractmethod
    def get_market_overview(self) -> Dict:
        """获取市场概览"""
        pass

    @abstractmethod
    def get_price_analysis(self) -> Dict:
        """获取价格分析"""
        pass

    @abstractmethod
    def get_alerts(self) -> List[Dict]:
        """获取预警信息"""
        pass

    @abstractmethod
    def start(self):
        """启动监控"""
        pass

    @abstractmethod
    def stop(self):
        """停止监控"""
        pass

    def _make_request(self, method: str, url: str, **kwargs) -> Optional[Dict[str, Any]]:
        """发送HTTP请求"""
        try:
            response = self.session.request(method, url, **kwargs)
            response.raise_for_status()
            data = response.json()
            if isinstance(data, dict) and data.get('code') == '0':
                return data
            logger.error(f"API响应错误: {data}")
            return None
        except requests.exceptions.RequestException as e:
            logger.error(f"请求失败 ({method} {url}): {str(e)}")
            return None
        except Exception as e:
            logger.error(f"请求处理失败: {str(e)}")
            return None

    def should_update(self, interval: int) -> bool:
        """检查是否需要更新数据"""
        if not self.last_update:
            return True
        from datetime import datetime
        time_diff = (datetime.now() - self.last_update).total_seconds()
        return time_diff >= interval 