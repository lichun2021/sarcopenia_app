"""
SarcNeuro Edge 配置管理
"""
import os
import json
from pathlib import Path
from typing import Optional, Dict, Any
from pydantic import Field
from pydantic_settings import BaseSettings
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

class AppConfig(BaseSettings):
    """应用配置"""
    name: str = "SarcNeuro Edge"
    version: str = "1.0.0"
    debug: bool = Field(default=False, env="DEBUG")
    host: str = Field(default="0.0.0.0", env="HOST")
    port: int = Field(default=8000, env="PORT")
    
    class Config:
        env_prefix = "APP_"

class DatabaseConfig(BaseSettings):
    """数据库配置"""
    url: str = Field(default="sqlite:///./data/sarcneuro.db", env="DATABASE_URL")
    pool_size: int = Field(default=10, env="DB_POOL_SIZE")
    max_overflow: int = Field(default=20, env="DB_MAX_OVERFLOW")
    echo: bool = Field(default=False, env="DB_ECHO")
    
    class Config:
        env_prefix = "DB_"

class SyncConfig(BaseSettings):
    """同步配置"""
    enabled: bool = Field(default=True, env="SYNC_ENABLED")
    cloud_url: str = Field(default="https://api.sarcneuro.com", env="CLOUD_API_URL")
    api_key: str = Field(default="", env="CLOUD_API_KEY")
    interval: int = Field(default=300, env="SYNC_INTERVAL")  # 5分钟
    retry_count: int = Field(default=3, env="SYNC_RETRY_COUNT")
    timeout: int = Field(default=30, env="SYNC_TIMEOUT")
    batch_size: int = Field(default=100, env="SYNC_BATCH_SIZE")
    
    class Config:
        env_prefix = "SYNC_"

class ModelConfig(BaseSettings):
    """AI模型配置"""
    cache_path: str = Field(default="./ml/models", env="MODEL_CACHE_PATH")
    update_interval: int = Field(default=3600, env="MODEL_UPDATE_INTERVAL")  # 1小时
    model_version: str = Field(default="latest", env="MODEL_VERSION")
    download_timeout: int = Field(default=600, env="MODEL_DOWNLOAD_TIMEOUT")  # 10分钟
    
    class Config:
        env_prefix = "MODEL_"

class SecurityConfig(BaseSettings):
    """安全配置"""
    secret_key: str = Field(default="your-secret-key-here", env="SECRET_KEY")
    access_token_expire_minutes: int = Field(default=1440, env="ACCESS_TOKEN_EXPIRE_MINUTES")  # 24小时
    algorithm: str = Field(default="HS256", env="JWT_ALGORITHM")
    
    class Config:
        env_prefix = "SECURITY_"

class LoggingConfig(BaseSettings):
    """日志配置"""
    level: str = Field(default="INFO", env="LOG_LEVEL")
    file_path: str = Field(default="./logs", env="LOG_FILE_PATH")
    max_file_size: int = Field(default=10 * 1024 * 1024, env="LOG_MAX_FILE_SIZE")  # 10MB
    backup_count: int = Field(default=5, env="LOG_BACKUP_COUNT")
    format: str = Field(
        default="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        env="LOG_FORMAT"
    )
    
    class Config:
        env_prefix = "LOG_"

class EdgeConfig:
    """Edge设备总配置"""
    
    def __init__(self, config_file: Optional[str] = None):
        self.config_file = config_file or "./config.json"
        self.app = AppConfig()
        self.database = DatabaseConfig()
        self.sync = SyncConfig()
        self.model = ModelConfig()
        self.security = SecurityConfig()
        self.logging = LoggingConfig()
        
        # 从配置文件加载配置
        self.load_config_file()
        
        # 确保必要的目录存在
        self._ensure_directories()
    
    def load_config_file(self):
        """从JSON配置文件加载配置"""
        if os.path.exists(self.config_file):
            try:
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    config_data = json.load(f)
                
                # 更新配置对象
                if 'app' in config_data:
                    self._update_config(self.app, config_data['app'])
                if 'database' in config_data:
                    self._update_config(self.database, config_data['database'])
                if 'sync' in config_data:
                    self._update_config(self.sync, config_data['sync'])
                if 'model' in config_data:
                    self._update_config(self.model, config_data['model'])
                if 'security' in config_data:
                    self._update_config(self.security, config_data['security'])
                if 'logging' in config_data:
                    self._update_config(self.logging, config_data['logging'])
                    
            except Exception as e:
                print(f"警告: 加载配置文件失败 {e}")
    
    def _update_config(self, config_obj, config_dict: Dict[str, Any]):
        """更新配置对象"""
        for key, value in config_dict.items():
            if hasattr(config_obj, key):
                setattr(config_obj, key, value)
    
    def _ensure_directories(self):
        """确保必要的目录存在"""
        directories = [
            "./data",
            "./logs", 
            "./ml/models",
            "./templates",
            Path(self.database.url.replace("sqlite:///", "")).parent
        ]
        
        for directory in directories:
            Path(directory).mkdir(parents=True, exist_ok=True)
    
    def save_config_file(self):
        """保存配置到文件"""
        config_data = {
            "app": self.app.dict(),
            "database": self.database.dict(),
            "sync": self.sync.dict(),
            "model": self.model.dict(),
            "security": {k: v for k, v in self.security.dict().items() if k != "secret_key"},
            "logging": self.logging.dict()
        }
        
        with open(self.config_file, 'w', encoding='utf-8') as f:
            json.dump(config_data, f, indent=2, ensure_ascii=False)
    
    @property
    def is_standalone_mode(self) -> bool:
        """是否为独立模式"""
        return not self.sync.enabled or not self.sync.api_key
    
    @property
    def database_path(self) -> str:
        """获取数据库文件路径"""
        if self.database.url.startswith("sqlite:///"):
            return self.database.url.replace("sqlite:///", "")
        return "./data/sarcneuro.db"
    
    def get_model_path(self, model_name: str) -> str:
        """获取模型文件路径"""
        return os.path.join(self.model.cache_path, model_name)
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "app": self.app.dict(),
            "database": self.database.dict(),
            "sync": self.sync.dict(),
            "model": self.model.dict(),
            "security": self.security.dict(),
            "logging": self.logging.dict()
        }

# 全局配置实例
config = EdgeConfig()

# 导出配置对象
__all__ = [
    "config",
    "EdgeConfig", 
    "AppConfig",
    "DatabaseConfig",
    "SyncConfig", 
    "ModelConfig",
    "SecurityConfig",
    "LoggingConfig"
]