import logging
from option_monitor.core.option_monitor import OptionMonitor

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

def test_monitor():
    """测试期权监控系统"""
    try:
        # 初始化监控器
        monitor = OptionMonitor()
        
        # 更新合约列表
        monitor.update_contracts()
        
        # 更新市场数据
        monitor.update_market_data()
        
        # 获取活跃合约
        contracts = monitor.get_active_contracts('BTC')
        print(f"获取到{len(contracts)}个活跃合约")
        
    except Exception as e:
        logging.error(f"测试失败: {str(e)}")
        raise
    finally:
        logging.info("测试完成")

if __name__ == '__main__':
    test_monitor() 