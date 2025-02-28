"""
API工具模块 - 提供API请求限速、缓存和错误处理功能

该模块实现了API请求的缓存机制和限速控制，以避免频繁请求同一资源导致的API限流问题。
同时提供了统一的错误处理和日志记录功能。
"""

import time
import random
import logging
import requests
from datetime import datetime
from typing import Dict, Any, Optional, Tuple, Callable

# 配置日志
logger = logging.getLogger(__name__)

class APIRateLimiter:
    """
    API请求限速器
    
    控制API请求频率，避免触发API提供方的限流措施。
    支持随机延迟和自定义请求间隔。
    """
    
    def __init__(self, min_interval: float = 5.0, jitter: float = 2.0):
        """
        初始化限速器
        
        Args:
            min_interval: 最小请求间隔（秒）
            jitter: 随机抖动范围（秒），用于避免固定间隔请求
        """
        self.min_interval = min_interval
        self.jitter = jitter
        self.last_request_time: Dict[str, float] = {}
    
    def wait_if_needed(self, endpoint: str) -> None:
        """
        根据需要等待一段时间，确保请求间隔不小于最小间隔
        
        Args:
            endpoint: API端点标识
        """
        current_time = time.time()
        
        if endpoint in self.last_request_time:
            elapsed = current_time - self.last_request_time[endpoint]
            if elapsed < self.min_interval:
                # 添加随机延迟，避免固定间隔请求
                sleep_time = self.min_interval - elapsed + random.uniform(0, self.jitter)
                logger.info(f"API请求过于频繁，延迟 {sleep_time:.2f} 秒后再请求: {endpoint}")
                time.sleep(sleep_time)
        
        # 更新最后请求时间
        self.last_request_time[endpoint] = time.time()
    
    def clear_history(self) -> None:
        """清除请求历史记录"""
        self.last_request_time.clear()
        logger.info("已清除API请求历史记录")


class APICache:
    """
    API响应缓存
    
    缓存API响应数据，减少重复请求，提高应用性能。
    支持TTL（生存时间）和缓存清理。
    """
    
    def __init__(self, default_ttl: int = 60):
        """
        初始化缓存
        
        Args:
            default_ttl: 默认缓存有效期（秒）
        """
        self.default_ttl = default_ttl
        self.cache: Dict[str, Tuple[float, Any]] = {}
    
    def get(self, key: str) -> Optional[Any]:
        """
        获取缓存数据
        
        Args:
            key: 缓存键名
            
        Returns:
            缓存的数据，如果不存在或已过期则返回None
        """
        if key not in self.cache:
            return None
        
        timestamp, data = self.cache[key]
        if time.time() - timestamp > self.default_ttl:
            # 缓存已过期
            return None
            
        logger.info(f"使用缓存数据: {key}, 缓存时间: {datetime.fromtimestamp(timestamp).strftime('%H:%M:%S')}")
        return data
    
    def set(self, key: str, data: Any, ttl: Optional[int] = None) -> None:
        """
        设置缓存数据
        
        Args:
            key: 缓存键名
            data: 要缓存的数据
            ttl: 缓存有效期（秒），如果为None则使用默认值
        """
        self.cache[key] = (time.time(), data)
    
    def get_expired(self, key: str) -> Optional[Any]:
        """
        获取已过期的缓存数据
        
        即使缓存已过期，也返回数据，用于API请求失败时的回退策略
        
        Args:
            key: 缓存键名
            
        Returns:
            缓存的数据，如果不存在则返回None
        """
        if key not in self.cache:
            return None
            
        _, data = self.cache[key]
        logger.warning(f"返回过期的缓存数据: {key}")
        return data
    
    def clear(self) -> None:
        """清除所有缓存"""
        self.cache.clear()
        logger.info("已清除所有API缓存")
    
    def get_cache_info(self) -> Dict[str, Dict[str, Any]]:
        """
        获取缓存状态信息
        
        Returns:
            包含缓存键和对应状态信息的字典
        """
        result = {}
        current_time = time.time()
        
        for key, (timestamp, _) in self.cache.items():
            age = current_time - timestamp
            is_expired = age > self.default_ttl
            result[key] = {
                "age": int(age),
                "expired": is_expired,
                "timestamp": datetime.fromtimestamp(timestamp).strftime('%Y-%m-%d %H:%M:%S')
            }
            
        return result


class APIClient:
    """
    API客户端
    
    集成了限速、缓存和错误处理的API客户端。
    提供统一的接口进行API请求。
    """
    
    def __init__(
        self, 
        base_url: str, 
        cache_ttl: int = 60, 
        min_request_interval: float = 5.0,
        timeout: int = 10,
        max_retries: int = 3
    ):
        """
        初始化API客户端
        
        Args:
            base_url: API基础URL
            cache_ttl: 缓存有效期（秒）
            min_request_interval: 最小请求间隔（秒）
            timeout: 请求超时时间（秒）
            max_retries: 最大重试次数
        """
        self.base_url = base_url
        self.timeout = timeout
        self.max_retries = max_retries
        
        # 初始化缓存和限速器
        self.cache = APICache(default_ttl=cache_ttl)
        self.rate_limiter = APIRateLimiter(min_interval=min_request_interval)
        
        # 创建会话对象，用于保持连接
        self.session = requests.Session()
        
        # 设置默认请求头
        self.session.headers.update({
            'User-Agent': 'Market-Monitor/1.0',
        })
    
    def fetch(self, endpoint: str, use_cache: bool = True, force_refresh: bool = False) -> Dict[str, Any]:
        """
        获取API数据
        
        Args:
            endpoint: API端点路径
            use_cache: 是否使用缓存
            force_refresh: 是否强制刷新缓存
            
        Returns:
            API响应数据
        """
        # 检查缓存
        if use_cache and not force_refresh:
            cached_data = self.cache.get(endpoint)
            if cached_data is not None:
                return cached_data
        
        try:
            # 应用限速
            self.rate_limiter.wait_if_needed(endpoint)
            
            # 构建完整URL
            url = f"{self.base_url}/{endpoint}"
            
            # 添加请求ID
            headers = {
                'X-Request-ID': f"{random.randint(1000000, 9999999)}"
            }
            
            # 发送请求
            logger.info(f"正在请求API: {url}")
            response = self.session.get(
                url, 
                headers=headers,
                timeout=self.timeout
            )
            
            # 处理响应
            if response.status_code == 200:
                logger.info(f"API请求成功: {endpoint}")
                data = response.json()
                
                # 更新缓存
                if use_cache:
                    self.cache.set(endpoint, data)
                    
                return data
            else:
                logger.error(f"API请求失败: 状态码 {response.status_code}, 响应: {response.text}")
                
                # 如果缓存存在但已过期，仍然返回过期的缓存数据而不是错误
                if use_cache:
                    expired_data = self.cache.get_expired(endpoint)
                    if expired_data is not None:
                        return expired_data
                        
                return {"status": "error", "message": f"API请求失败: {response.status_code}"}
                
        except requests.exceptions.ConnectionError as e:
            logger.error(f"API连接错误: {str(e)}")
            # 尝试使用缓存数据
            if use_cache:
                expired_data = self.cache.get_expired(endpoint)
                if expired_data is not None:
                    return expired_data
            return {"status": "error", "message": f"无法连接到API服务器: {str(e)}"}
            
        except requests.exceptions.Timeout as e:
            logger.error(f"API请求超时: {str(e)}")
            # 尝试使用缓存数据
            if use_cache:
                expired_data = self.cache.get_expired(endpoint)
                if expired_data is not None:
                    return expired_data
            return {"status": "error", "message": f"API请求超时: {str(e)}"}
            
        except requests.exceptions.RequestException as e:
            logger.error(f"API请求异常: {str(e)}")
            # 尝试使用缓存数据
            if use_cache:
                expired_data = self.cache.get_expired(endpoint)
                if expired_data is not None:
                    return expired_data
            return {"status": "error", "message": f"API请求异常: {str(e)}"}
            
        except Exception as e:
            logger.error(f"请求API失败: {str(e)}")
            # 尝试使用缓存数据
            if use_cache:
                expired_data = self.cache.get_expired(endpoint)
                if expired_data is not None:
                    return expired_data
            return {"status": "error", "message": f"请求API失败: {str(e)}"}
    
    def update_settings(self, cache_ttl: Optional[int] = None, min_request_interval: Optional[float] = None) -> None:
        """
        更新客户端设置
        
        Args:
            cache_ttl: 新的缓存有效期（秒）
            min_request_interval: 新的最小请求间隔（秒）
        """
        if cache_ttl is not None:
            self.cache.default_ttl = cache_ttl
            logger.info(f"已更新缓存有效期为 {cache_ttl} 秒")
            
        if min_request_interval is not None:
            self.rate_limiter.min_interval = min_request_interval
            logger.info(f"已更新最小请求间隔为 {min_request_interval} 秒")
    
    def clear_cache(self) -> None:
        """清除所有缓存和请求历史"""
        self.cache.clear()
        self.rate_limiter.clear_history()
        logger.info("已清除所有缓存和请求历史")
    
    def get_cache_info(self) -> Dict[str, Dict[str, Any]]:
        """获取缓存状态信息"""
        return self.cache.get_cache_info() 