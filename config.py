import os
from pathlib import Path
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

class Config:
    """应用配置"""
    
    # 认证配置
    USERNAME: str = os.getenv("CLIP_USERNAME", "admin")
    PASSWORD: str = os.getenv("CLIP_PASSWORD", "admin")
    
    # 服务器配置
    HOST: str = os.getenv("HOST", "0.0.0.0")
    PORT: int = int(os.getenv("PORT", "8000"))
    
    # 时区配置（默认北京时间）
    TIMEZONE: str = os.getenv("TZ", "Asia/Shanghai")
    
    # 路径配置
    BASE_DIR: Path = Path(__file__).parent
    _data_dir_env: str = os.getenv("DATA_DIR", "webdav_data")
    DATA_DIR: Path = Path(_data_dir_env) if _data_dir_env.startswith("/") else BASE_DIR / _data_dir_env
    HISTORY_DIR: Path = DATA_DIR / "history"
    FILE_DIR: Path = DATA_DIR / "file"
    DB_PATH: Path = DATA_DIR / "clipboard.db"
    SYNC_JSON_PATH: Path = DATA_DIR / "SyncClipboard.json"
    
    # 静态文件目录
    STATIC_DIR: Path = BASE_DIR / "static"
    
    @classmethod
    def ensure_directories(cls):
        """确保所有必要的目录存在"""
        cls.DATA_DIR.mkdir(parents=True, exist_ok=True)
        cls.HISTORY_DIR.mkdir(parents=True, exist_ok=True)
        cls.FILE_DIR.mkdir(parents=True, exist_ok=True)
        cls.STATIC_DIR.mkdir(parents=True, exist_ok=True)

# 初始化目录
Config.ensure_directories()
