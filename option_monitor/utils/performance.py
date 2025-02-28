import time
from functools import wraps
import logging

logger = logging.getLogger(__name__)

def measure_time(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        start = time.time()
        result = func(*args, **kwargs)
        end = time.time()
        
        logger.info(f"{func.__name__} 执行时间: {end - start:.3f}秒")
        return result
    return wrapper 