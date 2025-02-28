from typing import Any, Optional
import time

class Cache:
    def __init__(self, ttl: int = 60):
        self.cache = {}
        self.ttl = ttl
    
    def get(self, key: str) -> Optional[Any]:
        """获取缓存数据"""
        if key in self.cache:
            data, timestamp = self.cache[key]
            if time.time() - timestamp <= self.ttl:
                return data
            del self.cache[key]
        return None
    
    def set(self, key: str, value: Any):
        """设置缓存数据"""
        self.cache[key] = (value, time.time())
    
    def clear(self):
        """清除过期缓存"""
        current_time = time.time()
        expired_keys = [
            key for key, (_, timestamp) in self.cache.items()
            if current_time - timestamp > self.ttl
        ]
        for key in expired_keys:
            del self.cache[key] 