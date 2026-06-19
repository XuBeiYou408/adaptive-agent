import os
from dotenv import load_dotenv

# ==================== 本地数据的读取 ====================
load_dotenv()
folder_path = os.getenv('YUAN_SUCAI_PATH')

# 定义一个本地文件夹路径，数据库文件会自动创建并保存在这里
LOCAL_DB_PATH = os.getenv('LOCAL_DB_PATH')
