import os
import shutil
from datetime import datetime
import logging
import glob
from tqdm import tqdm
import json
import hashlib

logger = logging.getLogger(__name__)

def setup_logging():
    """配置日志"""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler('backup.log')
        ]
    )

def get_total_files(items):
    """计算需要备份的文件总数"""
    total = 0
    for item in items:
        if os.path.isfile(item):
            total += 1
        elif os.path.isdir(item):
            for root, _, files in os.walk(item):
                total += len(files)
    return total

def calculate_file_hash(file_path):
    """计算文件的MD5哈希值"""
    hash_md5 = hashlib.md5()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            hash_md5.update(chunk)
    return hash_md5.hexdigest()

def create_project_backup():
    """创建项目备份"""
    try:
        # 创建备份目录
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        backup_dir = f'backup_{timestamp}'
        os.makedirs(backup_dir, exist_ok=True)
        
        # 需要备份的项目文件和目录
        items_to_backup = [
            'option_monitor/',
            'visualization/',
            'api/',
            'frontend/',
            'tests/',
            '*.py',
            '*.json',
            '*.txt',
            'requirements.txt',
            '.env',
            '.streamlit/',
            'README.md'
        ]
        
        # 获取所有匹配的文件
        files_to_backup = []
        for item in items_to_backup:
            if '*' in item:
                files_to_backup.extend(glob.glob(item))
            else:
                if os.path.exists(item):
                    files_to_backup.append(item)
        
        # 计算总文件数
        total_files = get_total_files(files_to_backup)
        logger.info(f"开始备份 {total_files} 个文件...")
        
        # 创建备份清单
        manifest = {
            'timestamp': timestamp,
            'files': [],
            'total_files': total_files
        }
        
        # 使用进度条显示备份进度
        with tqdm(total=total_files, desc="备份进度") as pbar:
            for item in files_to_backup:
                if os.path.isfile(item):
                    # 备份单个文件
                    dest = os.path.join(backup_dir, item)
                    os.makedirs(os.path.dirname(dest), exist_ok=True)
                    shutil.copy2(item, dest)
                    
                    # 记录文件信息
                    manifest['files'].append({
                        'path': item,
                        'size': os.path.getsize(item),
                        'hash': calculate_file_hash(item)
                    })
                    pbar.update(1)
                    
                elif os.path.isdir(item):
                    # 备份目录
                    for root, _, files in os.walk(item):
                        for file in files:
                            src = os.path.join(root, file)
                            rel_path = os.path.relpath(src)
                            dest = os.path.join(backup_dir, rel_path)
                            os.makedirs(os.path.dirname(dest), exist_ok=True)
                            shutil.copy2(src, dest)
                            
                            # 记录文件信息
                            manifest['files'].append({
                                'path': rel_path,
                                'size': os.path.getsize(src),
                                'hash': calculate_file_hash(src)
                            })
                            pbar.update(1)
        
        # 保存备份清单
        manifest_path = os.path.join(backup_dir, 'manifest.json')
        with open(manifest_path, 'w', encoding='utf-8') as f:
            json.dump(manifest, f, indent=2, ensure_ascii=False)
        
        # 创建压缩文件
        shutil.make_archive(backup_dir, 'zip', backup_dir)
        
        # 清理临时目录
        shutil.rmtree(backup_dir)
        
        logger.info(f"备份完成: {backup_dir}.zip")
        return f"{backup_dir}.zip"
        
    except Exception as e:
        logger.error(f"备份失败: {str(e)}")
        if os.path.exists(backup_dir):
            shutil.rmtree(backup_dir)
        return None

def verify_backup(backup_file):
    """验证备份文件的完整性"""
    try:
        # 解压备份文件到临时目录
        temp_dir = 'temp_verify'
        shutil.unpack_archive(backup_file, temp_dir, 'zip')
        
        # 读取清单文件
        manifest_path = os.path.join(temp_dir, 'manifest.json')
        with open(manifest_path, 'r', encoding='utf-8') as f:
            manifest = json.load(f)
        
        # 验证每个文件
        success = True
        for file_info in manifest['files']:
            file_path = os.path.join(temp_dir, file_info['path'])
            if not os.path.exists(file_path):
                logger.error(f"文件丢失: {file_info['path']}")
                success = False
                continue
                
            current_hash = calculate_file_hash(file_path)
            if current_hash != file_info['hash']:
                logger.error(f"文件校验失败: {file_info['path']}")
                success = False
        
        return success
        
    finally:
        # 清理临时目录
        if os.path.exists(temp_dir):
            shutil.rmtree(temp_dir)

if __name__ == "__main__":
    setup_logging()
    logger.info("开始创建项目备份...")
    
    try:
        backup_file = create_project_backup()
        if backup_file:
            logger.info("开始验证备份...")
            if verify_backup(backup_file):
                logger.info(f"备份验证成功: {backup_file}")
            else:
                logger.error("备份验证失败！")
        else:
            logger.error("备份创建失败！")
            
    except KeyboardInterrupt:
        logger.warning("备份被用户中断！")
    except Exception as e:
        logger.error(f"备份过程出错: {str(e)}") 