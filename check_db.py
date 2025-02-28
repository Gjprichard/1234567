import sqlite3
import os

def check_database(db_path):
    print(f"检查数据库: {db_path}")
    print(f"数据库文件大小: {os.path.getsize(db_path)} 字节")
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # 获取所有表
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = cursor.fetchall()
        print(f"数据库中的表: {[table[0] for table in tables]}")
        
        # 检查每个表中的数据
        for table in tables:
            table_name = table[0]
            
            # 获取表结构
            cursor.execute(f"PRAGMA table_info({table_name})")
            columns_info = cursor.fetchall()
            if columns_info:
                print(f"\n表 {table_name} 的结构:")
                for col in columns_info:
                    print(f"  {col[1]} ({col[2]}){' PRIMARY KEY' if col[5] else ''}")
            
            cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
            count = cursor.fetchone()[0]
            print(f"表 {table_name} 中有 {count} 条记录")
            
            if count > 0:
                cursor.execute(f"SELECT * FROM {table_name} LIMIT 1")
                row = cursor.fetchone()
                print(f"示例数据: {row}")
        
        conn.close()
        print("\n数据库检查完成")
    except Exception as e:
        print(f"检查数据库时出错: {str(e)}")

if __name__ == "__main__":
    check_database("option_data.db")
    print("\n" + "="*50 + "\n")
    try:
        check_database("market_data.db")
    except FileNotFoundError:
        print("market_data.db 文件不存在") 