import sqlite3
import os
import logging

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def fix_database():
    """修复数据库表结构问题"""
    db_path = 'option_data.db'
    
    # 检查数据库是否存在
    if not os.path.exists(db_path):
        logger.error(f"数据库文件 {db_path} 不存在")
        return False
    
    # 备份数据库
    backup_path = f"{db_path}.bak"
    try:
        with open(db_path, 'rb') as src, open(backup_path, 'wb') as dst:
            dst.write(src.read())
        logger.info(f"已备份数据库到 {backup_path}")
    except Exception as e:
        logger.error(f"备份数据库失败: {str(e)}")
        return False
    
    # 连接数据库
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # 开始事务
        cursor.execute('BEGIN TRANSACTION')
        
        # 删除现有表
        logger.info("删除现有表...")
        cursor.execute('DROP TABLE IF EXISTS option_market_data')
        cursor.execute('DROP TABLE IF EXISTS option_tickers')
        cursor.execute('DROP TABLE IF EXISTS option_contracts')
        
        # 创建期权合约表
        logger.info("创建期权合约表...")
        cursor.execute('''
            CREATE TABLE option_contracts (
                instId TEXT PRIMARY KEY,
                symbol TEXT NOT NULL,
                strike REAL NOT NULL,
                expTime INTEGER NOT NULL,  -- 使用毫秒时间戳
                optType TEXT NOT NULL,
                state TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # 创建期权行情表
        logger.info("创建期权行情表...")
        cursor.execute('''
            CREATE TABLE option_tickers (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                instId TEXT NOT NULL,
                last REAL NOT NULL,
                vol24h REAL NOT NULL,
                volume_15m REAL NOT NULL,
                ts INTEGER NOT NULL,  -- 使用毫秒时间戳
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (instId) REFERENCES option_contracts(instId)
            )
        ''')
        
        # 提交事务
        conn.commit()
        logger.info("数据库表结构修复完成")
        
        # 初始化测试数据
        logger.info("初始化测试数据...")
        from option_database import OptionDatabase
        db = OptionDatabase()
        if db.initialize_test_data():
            logger.info("测试数据初始化成功")
        else:
            logger.warning("测试数据初始化失败")
        
        return True
        
    except Exception as e:
        logger.error(f"修复数据库失败: {str(e)}")
        if conn:
            conn.rollback()
        return False
    finally:
        if conn:
            conn.close()

if __name__ == "__main__":
    if fix_database():
        logger.info("数据库修复成功")
    else:
        logger.error("数据库修复失败") 