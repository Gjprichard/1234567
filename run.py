"""启动脚本"""
import os
import logging
from multiprocessing import Process
import streamlit.web.bootstrap as bootstrap
import signal
import sys
import subprocess

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def run_api():
    """运行API服务器"""
    try:
        port = int(os.getenv('API_PORT', 5000))
        app.run(host='0.0.0.0', port=port, debug=False)
        logger.info(f"API服务器已启动在端口 {port}")
    except Exception as e:
        logger.error(f"API服务器启动失败: {str(e)}")

def run_streamlit():
    """运行Streamlit应用"""
    try:
        bootstrap.run("app.py", "", [], [])
        logger.info("Streamlit应用已启动")
    except Exception as e:
        logger.error(f"Streamlit应用启动失败: {str(e)}")

def signal_handler(sig, frame):
    print("正在关闭应用...")
    sys.exit(0)

if __name__ == "__main__":
    # 注册信号处理器
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    try:
        # 启动 Streamlit 应用
        subprocess.run(["streamlit", "run", "app.py"])
    except KeyboardInterrupt:
        print("应用已关闭") 