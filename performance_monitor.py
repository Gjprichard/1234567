import time
from collections import deque
from typing import Dict, Any
import statistics

class PerformanceMonitor:
    def __init__(self, max_samples: int = 100):
        self.latencies = deque(maxlen=max_samples)
        self.errors = deque(maxlen=max_samples)
        self.start_time = time.time()
    
    def record_latency(self, latency: float):
        """记录延迟"""
        self.latencies.append(latency)
    
    def record_error(self, error: bool):
        """记录错误"""
        self.errors.append(error)
    
    def get_summary(self) -> Dict[str, Any]:
        """获取性能摘要"""
        if not self.latencies:
            return {'avg_latency': 0, 'error_rate': 0}
            
        avg_latency = statistics.mean(self.latencies)
        error_rate = sum(self.errors) / len(self.errors) if self.errors else 0
        
        return {
            'avg_latency': avg_latency,
            'error_rate': error_rate
        } 