"""
SarcNeuro Edge FastAPI应用主入口
"""
import asyncio
import uvicorn
from contextlib import asynccontextmanager
from typing import Dict, Any
from datetime import datetime
import logging
import os
from pathlib import Path

from fastapi import FastAPI, HTTPException, Depends, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, FileResponse, JSONResponse
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import psutil

# 项目内部导入
from app.config import config
from app.database import init_database, db_manager
from core.sync_manager import sync_manager, sync_scheduler
from core.report_generator import report_generator
from core.analyzer import SarcNeuroAnalyzer

# API路由
from api.patients import router as patients_router
from api.tests import router as tests_router
from api.reports import router as reports_router
from api.sync import router as sync_router
from api.analysis import router as analysis_router

# 配置日志
logging.basicConfig(
    level=getattr(logging, config.logging.level),
    format=config.logging.format,
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(
            f"{config.logging.file_path}/sarcneuro_edge.log",
            encoding='utf-8'
        )
    ]
)
logger = logging.getLogger(__name__)

# JWT安全
security = HTTPBearer()

@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    logger.info("SarcNeuro Edge 服务启动中...")
    
    try:
        # 初始化数据库
        init_database()
        logger.info("数据库初始化完成")
        
        # 启动自动同步（如果启用）
        if config.sync.enabled:
            asyncio.create_task(sync_scheduler.start_auto_sync())
            logger.info("自动同步服务已启动")
        
        # 初始化分析器
        global analyzer
        analyzer = SarcNeuroAnalyzer()
        logger.info("分析引擎初始化完成")
        
        yield
        
    except Exception as e:
        logger.error(f"服务启动失败: {e}")
        raise
    
    finally:
        # 关闭服务
        logger.info("SarcNeuro Edge 服务关闭中...")
        sync_scheduler.stop_auto_sync()
        logger.info("服务已关闭")

# 创建FastAPI应用
app = FastAPI(
    title="SarcNeuro Edge",
    description="SarcNeuro 边缘计算分析服务 - 本地部署版本",
    version=config.app.version,
    lifespan=lifespan,
    docs_url="/docs" if config.app.debug else None,
    redoc_url="/redoc" if config.app.debug else None
)

# 添加CORS中间件
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 静态文件服务 - 确保目录存在
static_dirs = ["./static", "./reports"]
for dir_path in static_dirs:
    Path(dir_path).mkdir(parents=True, exist_ok=True)

app.mount("/static", StaticFiles(directory="./static"), name="static")
app.mount("/reports", StaticFiles(directory="./reports"), name="reports")

# 全局分析器实例
analyzer = None

# 依赖注入
def get_analyzer():
    """获取分析器实例"""
    if analyzer is None:
        raise HTTPException(status_code=500, detail="分析器未初始化")
    return analyzer

async def verify_token(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """验证JWT Token（简化版本，生产环境需要完整实现）"""
    # 这里应该实现完整的JWT验证逻辑
    # 当前为演示版本，接受任何token
    if not credentials.credentials:
        raise HTTPException(status_code=401, detail="未提供认证token")
    return credentials.credentials

# 注册API路由
app.include_router(patients_router, prefix="/api/patients", tags=["患者管理"])
app.include_router(tests_router, prefix="/api/tests", tags=["测试管理"])  
app.include_router(reports_router, prefix="/api/reports", tags=["报告管理"])
app.include_router(sync_router, prefix="/api/sync", tags=["数据同步"])
app.include_router(analysis_router, prefix="/api/analysis", tags=["数据分析"])

# 基础API端点
@app.get("/", response_class=HTMLResponse)
async def root():
    """首页"""
    return """
    <!DOCTYPE html>
    <html>
    <head>
        <title>SarcNeuro Edge</title>
        <meta charset="utf-8">
        <style>
            body { font-family: Arial, sans-serif; margin: 40px; background: #f5f5f5; }
            .container { max-width: 800px; margin: 0 auto; background: white; padding: 40px; border-radius: 8px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }
            h1 { color: #007bff; text-align: center; }
            .info { background: #e3f2fd; padding: 20px; border-radius: 4px; margin: 20px 0; }
            .status { display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 20px; margin: 20px 0; }
            .status-card { background: #f8f9fa; padding: 15px; border-radius: 4px; text-align: center; border-left: 4px solid #007bff; }
            .links { text-align: center; margin: 30px 0; }
            .links a { display: inline-block; margin: 10px; padding: 10px 20px; background: #007bff; color: white; text-decoration: none; border-radius: 4px; }
            .links a:hover { background: #0056b3; }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>🧠 SarcNeuro Edge</h1>
            <div class="info">
                <h3>肌少症智能监测与健康步态分析系统 - 边缘版本</h3>
                <p><strong>版本:</strong> """ + config.app.version + """</p>
                <p><strong>模式:</strong> """ + ("离线模式" if config.is_standalone_mode else "联网模式") + """</p>
                <p><strong>服务时间:</strong> <span id="time"></span></p>
            </div>
            
            <div class="status">
                <div class="status-card">
                    <h4>数据库</h4>
                    <p>✅ SQLite 已连接</p>
                </div>
                <div class="status-card">
                    <h4>分析引擎</h4>
                    <p>✅ AI 模型就绪</p>
                </div>
                <div class="status-card">
                    <h4>同步状态</h4>
                    <p>""" + ("🔄 自动同步" if config.sync.enabled else "📱 离线模式") + """</p>
                </div>
            </div>
            
            <div class="links">
                <a href="/api/docs">📖 API 文档</a>
                <a href="/system/status">📊 系统状态</a>
                <a href="/dashboard">📈 控制面板</a>
            </div>
        </div>
        
        <script>
            function updateTime() {
                document.getElementById('time').textContent = new Date().toLocaleString('zh-CN');
            }
            updateTime();
            setInterval(updateTime, 1000);
        </script>
    </body>
    </html>
    """

@app.get("/health")
async def health_check():
    """健康检查"""
    return {
        "status": "healthy",
        "version": config.app.version,
        "timestamp": datetime.now().isoformat(),
        "database": "connected" if db_manager.check_connection() else "disconnected",
        "sync_enabled": config.sync.enabled,
        "is_standalone": config.is_standalone_mode
    }

@app.get("/system/status")
async def system_status():
    """系统状态信息"""
    try:
        # 获取系统资源使用情况
        cpu_usage = psutil.cpu_percent(interval=1)
        memory = psutil.virtual_memory()
        disk = psutil.disk_usage('/')
        
        # 获取数据库信息
        db_info = db_manager.get_database_info()
        
        # 获取同步状态
        sync_status = await sync_manager.get_sync_status()
        
        # 统计数据
        with db_manager.get_session() as session:
            from models.database_models import Patient, Test, Report
            
            patient_count = session.query(Patient).count()
            test_count = session.query(Test).count()
            report_count = session.query(Report).count()
        
        return {
            "system": {
                "cpu_usage": cpu_usage,
                "memory_usage": memory.percent,
                "memory_total": memory.total,
                "memory_available": memory.available,
                "disk_usage": (disk.used / disk.total) * 100,
                "disk_total": disk.total,
                "disk_free": disk.free
            },
            "database": db_info,
            "sync": sync_status,
            "statistics": {
                "patients": patient_count,
                "tests": test_count,
                "reports": report_count
            },
            "config": {
                "app_version": config.app.version,
                "debug_mode": config.app.debug,
                "sync_enabled": config.sync.enabled,
                "is_standalone": config.is_standalone_mode
            },
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"获取系统状态失败: {e}")
        raise HTTPException(status_code=500, detail=f"系统状态获取失败: {str(e)}")

@app.get("/dashboard", response_class=HTMLResponse)
async def dashboard():
    """简单的控制面板"""
    return """
    <!DOCTYPE html>
    <html>
    <head>
        <title>SarcNeuro Edge 控制面板</title>
        <meta charset="utf-8">
        <style>
            body { font-family: Arial, sans-serif; margin: 0; background: #1a1a1a; color: white; }
            .header { background: linear-gradient(135deg, #007bff, #0056b3); padding: 20px; text-align: center; }
            .container { padding: 20px; max-width: 1200px; margin: 0 auto; }
            .grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); gap: 20px; margin: 20px 0; }
            .card { background: #2d2d2d; border-radius: 8px; padding: 20px; border: 1px solid #444; }
            .card h3 { color: #007bff; margin-top: 0; }
            .metrics { display: grid; grid-template-columns: repeat(auto-fit, minmax(100px, 1fr)); gap: 10px; }
            .metric { text-align: center; padding: 10px; background: #3d3d3d; border-radius: 4px; }
            .metric-value { font-size: 24px; font-weight: bold; color: #28a745; }
            .metric-label { font-size: 12px; color: #aaa; }
            .btn { display: inline-block; padding: 10px 20px; background: #007bff; color: white; text-decoration: none; border-radius: 4px; margin: 5px; }
            .btn:hover { background: #0056b3; }
            .status { display: inline-block; padding: 4px 8px; border-radius: 12px; font-size: 12px; font-weight: bold; }
            .status-online { background: #28a745; color: white; }
            .status-offline { background: #dc3545; color: white; }
        </style>
    </head>
    <body>
        <div class="header">
            <h1>🧠 SarcNeuro Edge 控制面板</h1>
            <p>肌少症智能监测系统 - 边缘计算版本</p>
        </div>
        
        <div class="container">
            <div class="grid">
                <div class="card">
                    <h3>系统概览</h3>
                    <div id="system-info">正在加载...</div>
                    <div style="margin-top: 15px;">
                        <a href="/api/docs" class="btn">API 文档</a>
                        <a href="/system/status" class="btn">详细状态</a>
                    </div>
                </div>
                
                <div class="card">
                    <h3>数据统计</h3>
                    <div id="statistics" class="metrics">正在加载...</div>
                </div>
                
                <div class="card">
                    <h3>同步状态</h3>
                    <div id="sync-status">正在加载...</div>
                    <div style="margin-top: 15px;">
                        <a href="#" onclick="triggerSync()" class="btn">手动同步</a>
                    </div>
                </div>
                
                <div class="card">
                    <h3>快速操作</h3>
                    <a href="/api/patients" class="btn">患者管理</a>
                    <a href="/api/tests" class="btn">测试管理</a>
                    <a href="/api/reports" class="btn">报告管理</a>
                    <a href="/api/analysis/demo" class="btn">演示分析</a>
                </div>
            </div>
        </div>
        
        <script>
            async function loadSystemStatus() {
                try {
                    const response = await fetch('/system/status');
                    const data = await response.json();
                    
                    // 更新系统信息
                    document.getElementById('system-info').innerHTML = `
                        <p>CPU 使用率: ${data.system.cpu_usage.toFixed(1)}%</p>
                        <p>内存使用率: ${data.system.memory_usage.toFixed(1)}%</p>
                        <p>磁盘使用率: ${data.system.disk_usage.toFixed(1)}%</p>
                        <p>数据库: <span class="status ${data.database.connection === 'OK' ? 'status-online' : 'status-offline'}">${data.database.connection}</span></p>
                    `;
                    
                    // 更新统计信息
                    document.getElementById('statistics').innerHTML = `
                        <div class="metric">
                            <div class="metric-value">${data.statistics.patients}</div>
                            <div class="metric-label">患者</div>
                        </div>
                        <div class="metric">
                            <div class="metric-value">${data.statistics.tests}</div>
                            <div class="metric-label">测试</div>
                        </div>
                        <div class="metric">
                            <div class="metric-value">${data.statistics.reports}</div>
                            <div class="metric-label">报告</div>
                        </div>
                    `;
                    
                    // 更新同步状态
                    const syncConnected = data.sync.is_connected;
                    document.getElementById('sync-status').innerHTML = `
                        <p>云端连接: <span class="status ${syncConnected ? 'status-online' : 'status-offline'}">${syncConnected ? '已连接' : '未连接'}</span></p>
                        <p>待同步: ${data.sync.pending_sync?.total || 0} 条记录</p>
                        <p>最后同步: ${data.sync.last_sync_time ? new Date(data.sync.last_sync_time).toLocaleString() : '从未'}</p>
                    `;
                    
                } catch (error) {
                    console.error('加载系统状态失败:', error);
                }
            }
            
            async function triggerSync() {
                try {
                    const response = await fetch('/api/sync/trigger', { method: 'POST' });
                    const result = await response.json();
                    alert(result.message || '同步已触发');
                    setTimeout(loadSystemStatus, 2000);  // 2秒后刷新状态
                } catch (error) {
                    alert('同步触发失败: ' + error.message);
                }
            }
            
            // 初始加载和定时刷新
            loadSystemStatus();
            setInterval(loadSystemStatus, 10000);  // 每10秒刷新一次
        </script>
    </body>
    </html>
    """

@app.post("/system/shutdown")
async def shutdown(background_tasks: BackgroundTasks):
    """安全关闭系统"""
    def shutdown_server():
        import os
        import signal
        os.kill(os.getpid(), signal.SIGTERM)
    
    background_tasks.add_task(shutdown_server)
    return {"message": "系统正在安全关闭..."}

if __name__ == "__main__":
    # 直接运行时的启动配置
    uvicorn.run(
        "app.main:app",
        host=config.app.host,
        port=config.app.port,
        reload=config.app.debug,
        access_log=True,
        log_level="info"
    )