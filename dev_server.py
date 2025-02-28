"""开发服务器"""
import multiprocessing
import streamlit.web.bootstrap as bootstrap
from dev_config import dev_env
from api import app
import logging

logger = logging.getLogger(__name__)

def run_api():
    """运行API服务器"""
    try:
        app.run(
            host=dev_env.config.API_HOST,
            port=dev_env.config.API_PORT,
            debug=dev_env.config.DEBUG
        )
    except Exception as e:
        logger.error(f"API服务器启动失败: {str(e)}")

def run_streamlit():
    """运行Streamlit应用"""
    try:
        bootstrap.run(
            "app.py",
            "",
            [],
            flag_options={
                "server.port": dev_env.config.STREAMLIT_PORT,
                "server.address": "localhost",
                "browser.serverAddress": "localhost",
                "server.runOnSave": dev_env.config.HOT_RELOAD,
                "theme.base": "light"
            }
        )
    except Exception as e:
        logger.error(f"Streamlit应用启动失败: {str(e)}")

def main():
    """主函数"""
    try:
        # 启动开发环境
        dev_env.start()
        
        # 启动API服务器
        api_process = multiprocessing.Process(target=run_api)
        api_process.start()
        
        # 启动Streamlit应用
        streamlit_process = multiprocessing.Process(target=run_streamlit)
        streamlit_process.start()
        
        # 等待进程结束
        api_process.join()
        streamlit_process.join()
        
    except KeyboardInterrupt:
        logger.info("正在关闭服务...")
    except Exception as e:
        logger.error(f"开发服务器启动失败: {str(e)}")

if __name__ == "__main__":
    main() 