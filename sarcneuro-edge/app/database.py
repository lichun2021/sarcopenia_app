"""
SarcNeuro Edge 数据库连接管理
"""
import os
import sys
from pathlib import Path
from typing import Generator
from sqlalchemy import create_engine, event
from sqlalchemy.engine import Engine
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import StaticPool
import sqlite3

# 添加父目录到路径，以便导入模型
sys.path.append(str(Path(__file__).parent.parent))

from app.config import config
from models.database_models import Base

class DatabaseManager:
    """数据库管理器"""
    
    def __init__(self):
        self.engine = None
        self.SessionLocal = None
        self._initialize_engine()
    
    def _initialize_engine(self):
        """初始化数据库引擎"""
        try:
            # SQLite特殊配置
            if config.database.url.startswith("sqlite"):
                # 确保数据库目录存在
                db_path = Path(config.database_path)
                db_path.parent.mkdir(parents=True, exist_ok=True)
                
                # SQLite引擎配置
                self.engine = create_engine(
                    config.database.url,
                    echo=config.database.echo,
                    poolclass=StaticPool,
                    connect_args={
                        "check_same_thread": False,
                        "timeout": 30
                    }
                )
                
                # 启用SQLite外键约束和优化
                @event.listens_for(Engine, "connect")
                def set_sqlite_pragma(dbapi_connection, connection_record):
                    if isinstance(dbapi_connection, sqlite3.Connection):
                        cursor = dbapi_connection.cursor()
                        # 启用外键约束
                        cursor.execute("PRAGMA foreign_keys=ON")
                        # 设置日志模式为WAL以提高并发性能
                        cursor.execute("PRAGMA journal_mode=WAL")
                        # 设置同步模式
                        cursor.execute("PRAGMA synchronous=NORMAL")
                        # 设置缓存大小 (10MB)
                        cursor.execute("PRAGMA cache_size=-10000")
                        # 设置临时存储在内存中
                        cursor.execute("PRAGMA temp_store=MEMORY")
                        cursor.close()
            
            else:
                # 其他数据库配置
                self.engine = create_engine(
                    config.database.url,
                    echo=config.database.echo,
                    pool_size=config.database.pool_size,
                    max_overflow=config.database.max_overflow
                )
            
            # 创建会话工厂
            self.SessionLocal = sessionmaker(
                autocommit=False,
                autoflush=False,
                bind=self.engine
            )
            
            print(f"数据库引擎初始化成功: {config.database.url}")
            
        except Exception as e:
            print(f"数据库引擎初始化失败: {e}")
            raise
    
    def create_tables(self):
        """创建所有数据表"""
        try:
            Base.metadata.create_all(bind=self.engine)
            print("数据表创建成功")
        except Exception as e:
            print(f"数据表创建失败: {e}")
            raise
    
    def drop_tables(self):
        """删除所有数据表"""
        try:
            Base.metadata.drop_all(bind=self.engine)
            print("数据表删除成功")
        except Exception as e:
            print(f"数据表删除失败: {e}")
            raise
    
    def get_session(self) -> Generator[Session, None, None]:
        """获取数据库会话"""
        session = self.SessionLocal()
        try:
            yield session
        except Exception as e:
            session.rollback()
            raise e
        finally:
            session.close()
    
    def check_connection(self) -> bool:
        """检查数据库连接"""
        try:
            with self.engine.connect() as connection:
                connection.execute("SELECT 1")
            return True
        except Exception as e:
            print(f"数据库连接检查失败: {e}")
            return False
    
    def get_database_info(self) -> dict:
        """获取数据库信息"""
        try:
            with self.engine.connect() as connection:
                if config.database.url.startswith("sqlite"):
                    # SQLite信息
                    result = connection.execute("PRAGMA database_list")
                    db_info = result.fetchall()
                    
                    # 获取数据库大小
                    db_size = 0
                    if os.path.exists(config.database_path):
                        db_size = os.path.getsize(config.database_path)
                    
                    return {
                        "type": "sqlite",
                        "path": config.database_path,
                        "size": db_size,
                        "info": db_info,
                        "connection": "OK"
                    }
                else:
                    # 其他数据库信息
                    return {
                        "type": "other",
                        "url": config.database.url,
                        "connection": "OK"
                    }
                    
        except Exception as e:
            return {
                "type": "unknown",
                "connection": "FAILED",
                "error": str(e)
            }
    
    def vacuum_database(self):
        """优化数据库（SQLite VACUUM）"""
        if not config.database.url.startswith("sqlite"):
            print("VACUUM操作仅支持SQLite数据库")
            return
        
        try:
            with self.engine.connect() as connection:
                connection.execute("VACUUM")
            print("数据库优化完成")
        except Exception as e:
            print(f"数据库优化失败: {e}")
            raise
    
    def backup_database(self, backup_path: str):
        """备份数据库"""
        if not config.database.url.startswith("sqlite"):
            print("备份功能目前仅支持SQLite数据库")
            return False
        
        try:
            import shutil
            source_path = config.database_path
            
            if os.path.exists(source_path):
                # 确保备份目录存在
                Path(backup_path).parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(source_path, backup_path)
                print(f"数据库备份成功: {backup_path}")
                return True
            else:
                print(f"源数据库文件不存在: {source_path}")
                return False
                
        except Exception as e:
            print(f"数据库备份失败: {e}")
            return False
    
    def restore_database(self, backup_path: str):
        """恢复数据库"""
        if not config.database.url.startswith("sqlite"):
            print("恢复功能目前仅支持SQLite数据库")
            return False
        
        try:
            import shutil
            target_path = config.database_path
            
            if os.path.exists(backup_path):
                # 关闭所有连接
                self.engine.dispose()
                
                # 恢复数据库文件
                shutil.copy2(backup_path, target_path)
                
                # 重新初始化引擎
                self._initialize_engine()
                
                print(f"数据库恢复成功: {backup_path}")
                return True
            else:
                print(f"备份文件不存在: {backup_path}")
                return False
                
        except Exception as e:
            print(f"数据库恢复失败: {e}")
            return False

# 全局数据库管理器实例
db_manager = DatabaseManager()

# 便捷函数
def get_db() -> Generator[Session, None, None]:
    """获取数据库会话（FastAPI依赖注入用）"""
    return db_manager.get_session()

def init_database():
    """初始化数据库"""
    print("正在初始化数据库...")
    
    # 检查连接
    if not db_manager.check_connection():
        raise Exception("数据库连接失败")
    
    # 创建表
    db_manager.create_tables()
    
    # 初始化系统状态
    _initialize_system_status()
    
    print("数据库初始化完成")

def _initialize_system_status():
    """初始化系统状态记录"""
    from models.database_models import SystemStatus
    import uuid
    
    try:
        with db_manager.get_session() as session:
            # 检查是否已有系统状态记录
            existing = session.query(SystemStatus).first()
            
            if not existing:
                # 创建新的系统状态记录
                system_status = SystemStatus(
                    app_version=config.app.version,
                    edge_device_id=str(uuid.uuid4()),
                    status="running"
                )
                session.add(system_status)
                session.commit()
                print(f"系统状态初始化完成，设备ID: {system_status.edge_device_id}")
            else:
                print(f"系统状态已存在，设备ID: {existing.edge_device_id}")
                
    except Exception as e:
        print(f"系统状态初始化失败: {e}")

# 命令行工具
def main():
    """命令行数据库管理工具"""
    if len(sys.argv) < 2:
        print("使用方法: python -m app.database [init|check|vacuum|info]")
        return
    
    command = sys.argv[1]
    
    try:
        if command == "init":
            init_database()
        elif command == "check":
            if db_manager.check_connection():
                print("数据库连接正常")
            else:
                print("数据库连接失败")
        elif command == "vacuum":
            db_manager.vacuum_database()
        elif command == "info":
            info = db_manager.get_database_info()
            print(f"数据库信息: {info}")
        elif command == "backup":
            if len(sys.argv) < 3:
                print("使用方法: python -m app.database backup <备份文件路径>")
                return
            backup_path = sys.argv[2]
            db_manager.backup_database(backup_path)
        elif command == "restore":
            if len(sys.argv) < 3:
                print("使用方法: python -m app.database restore <备份文件路径>")
                return
            backup_path = sys.argv[2]
            db_manager.restore_database(backup_path)
        else:
            print(f"未知命令: {command}")
            
    except Exception as e:
        print(f"执行命令失败: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()

# 导出
__all__ = [
    "db_manager",
    "get_db",
    "init_database",
    "DatabaseManager"
]