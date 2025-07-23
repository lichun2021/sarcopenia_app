"""
SarcNeuro Edge 数据同步API
"""
from typing import Optional, Dict, Any
from datetime import datetime
import logging

from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel

from core.sync_manager import sync_manager
from app.config import config
from api import success_response, error_response

logger = logging.getLogger(__name__)

router = APIRouter()

# Pydantic模型
class SyncConfigUpdate(BaseModel):
    enabled: Optional[bool] = None
    api_key: Optional[str] = None
    cloud_url: Optional[str] = None
    interval: Optional[int] = None

# API端点
@router.get("/status", response_model=Dict[str, Any])
async def get_sync_status():
    """获取同步状态"""
    try:
        status = await sync_manager.get_sync_status()
        return success_response(status, "同步状态获取成功")
    except Exception as e:
        logger.error(f"获取同步状态失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取同步状态失败: {str(e)}")

@router.post("/trigger", response_model=Dict[str, Any])
async def trigger_manual_sync(background_tasks: BackgroundTasks):
    """手动触发数据同步"""
    try:
        if not config.sync.enabled:
            return error_response("同步功能未启用")
        
        if not config.sync.api_key:
            return error_response("未配置API密钥")
        
        # 检查是否正在同步
        if sync_manager.is_syncing:
            return error_response("同步正在进行中，请稍后再试")
        
        # 启动后台同步任务
        async def background_sync():
            try:
                result = await sync_manager.sync_all_data()
                logger.info(f"手动同步完成: {result.get('status')}")
            except Exception as e:
                logger.error(f"手动同步失败: {e}")
        
        background_tasks.add_task(background_sync)
        
        return success_response({
            "sync_triggered": True,
            "message": "同步任务已启动，请稍后查看状态"
        }, "同步任务已触发")
        
    except Exception as e:
        logger.error(f"触发同步失败: {e}")
        raise HTTPException(status_code=500, detail=f"触发同步失败: {str(e)}")

@router.post("/models/update", response_model=Dict[str, Any])
async def update_models(background_tasks: BackgroundTasks):
    """更新AI模型"""
    try:
        if not config.sync.enabled:
            return error_response("同步功能未启用")
        
        if not config.sync.api_key:
            return error_response("未配置API密钥")
        
        # 启动后台模型更新任务
        async def background_model_update():
            try:
                result = await sync_manager.sync_models()
                logger.info(f"模型更新完成: {result}")
            except Exception as e:
                logger.error(f"模型更新失败: {e}")
        
        background_tasks.add_task(background_model_update)
        
        return success_response({
            "update_triggered": True,
            "message": "模型更新任务已启动"
        }, "模型更新任务已触发")
        
    except Exception as e:
        logger.error(f"触发模型更新失败: {e}")
        raise HTTPException(status_code=500, detail=f"触发模型更新失败: {str(e)}")

@router.get("/connection/test")
async def test_cloud_connection():
    """测试云端连接"""
    try:
        is_connected = await sync_manager.check_cloud_connection()
        
        if is_connected:
            return success_response({
                "connected": True,
                "cloud_url": config.sync.cloud_url,
                "test_time": datetime.now().isoformat()
            }, "云端连接正常")
        else:
            return error_response("无法连接到云端服务器")
            
    except Exception as e:
        logger.error(f"测试云端连接失败: {e}")
        return error_response(f"连接测试失败: {str(e)}")

@router.get("/config", response_model=Dict[str, Any])
async def get_sync_config():
    """获取同步配置"""
    try:
        sync_config = {
            "enabled": config.sync.enabled,
            "cloud_url": config.sync.cloud_url,
            "has_api_key": bool(config.sync.api_key),
            "interval": config.sync.interval,
            "timeout": config.sync.timeout,
            "batch_size": config.sync.batch_size,
            "retry_count": config.sync.retry_count,
            "is_standalone_mode": config.is_standalone_mode
        }
        
        return success_response(sync_config, "同步配置获取成功")
        
    except Exception as e:
        logger.error(f"获取同步配置失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取同步配置失败: {str(e)}")

@router.put("/config", response_model=Dict[str, Any])
async def update_sync_config(config_update: SyncConfigUpdate):
    """更新同步配置"""
    try:
        # 更新配置（这里应该实现配置更新逻辑）
        # 注意：在生产环境中，这需要更安全的权限验证
        
        updated_fields = []
        
        if config_update.enabled is not None:
            config.sync.enabled = config_update.enabled
            updated_fields.append("enabled")
        
        if config_update.api_key is not None:
            config.sync.api_key = config_update.api_key
            updated_fields.append("api_key")
        
        if config_update.cloud_url is not None:
            config.sync.cloud_url = config_update.cloud_url
            updated_fields.append("cloud_url")
        
        if config_update.interval is not None:
            config.sync.interval = config_update.interval
            updated_fields.append("interval")
        
        # 保存配置到文件（如果需要持久化）
        try:
            config.save_config_file()
        except Exception as e:
            logger.warning(f"保存配置文件失败: {e}")
        
        return success_response({
            "updated_fields": updated_fields,
            "current_config": {
                "enabled": config.sync.enabled,
                "cloud_url": config.sync.cloud_url,
                "has_api_key": bool(config.sync.api_key),
                "interval": config.sync.interval
            }
        }, "同步配置更新成功")
        
    except Exception as e:
        logger.error(f"更新同步配置失败: {e}")
        raise HTTPException(status_code=500, detail=f"更新同步配置失败: {str(e)}")

@router.get("/logs", response_model=Dict[str, Any])
async def get_sync_logs(
    limit: int = 50,
    offset: int = 0
):
    """获取同步日志"""
    try:
        from app.database import db_manager
        from models.database_models import SyncLog
        
        for session in db_manager.get_session():
            # 获取同步日志
            query = session.query(SyncLog).order_by(SyncLog.created_at.desc())
            
            total = query.count()
            logs = query.offset(offset).limit(limit).all()
            
            # 构造响应数据
            log_list = []
            for log in logs:
                log_data = {
                    "id": log.id,
                    "sync_type": log.sync_type,
                    "operation": log.operation,
                    "status": log.status,
                    "total_records": log.total_records,
                    "synced_records": log.synced_records,
                    "failed_records": log.failed_records,
                    "duration": log.duration,
                    "start_time": log.start_time.isoformat(),
                    "end_time": log.end_time.isoformat() if log.end_time else None,
                    "error_message": log.error_message,
                    "created_at": log.created_at.isoformat()
                }
                log_list.append(log_data)
            
            return success_response({
                "logs": log_list,
                "pagination": {
                    "total": total,
                    "limit": limit,
                    "offset": offset,
                    "has_more": offset + limit < total
                }
            }, "同步日志获取成功")
            
    except Exception as e:
        logger.error(f"获取同步日志失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取同步日志失败: {str(e)}")

@router.delete("/logs", response_model=Dict[str, Any])
async def clear_sync_logs(
    days_to_keep: int = 30
):
    """清理同步日志"""
    try:
        from app.database import db_manager
        from models.database_models import SyncLog
        from datetime import timedelta
        
        cutoff_date = datetime.now() - timedelta(days=days_to_keep)
        
        for session in db_manager.get_session():
            # 删除旧日志
            deleted_count = session.query(SyncLog).filter(
                SyncLog.created_at < cutoff_date
            ).delete()
            
            session.commit()
            
            return success_response({
                "deleted_count": deleted_count,
                "days_kept": days_to_keep,
                "cutoff_date": cutoff_date.isoformat()
            }, f"已清理{deleted_count}条旧日志记录")
            
    except Exception as e:
        logger.error(f"清理同步日志失败: {e}")
        raise HTTPException(status_code=500, detail=f"清理同步日志失败: {str(e)}")

@router.get("/pending", response_model=Dict[str, Any])
async def get_pending_sync_data():
    """获取待同步数据统计"""
    try:
        from app.database import db_manager
        from models.database_models import Patient, Test, Report
        
        for session in db_manager.get_session():
            # 统计待同步数据
            pending_patients = session.query(Patient).filter(
                Patient.sync_status == "pending"
            ).count()
            
            pending_tests = session.query(Test).filter(
                Test.sync_status == "pending"
            ).count()
            
            pending_reports = session.query(Report).filter(
                Report.sync_status == "pending"
            ).count()
            
            # 获取一些详细信息
            recent_pending_patients = session.query(Patient).filter(
                Patient.sync_status == "pending"
            ).order_by(Patient.updated_at.desc()).limit(5).all()
            
            recent_pending_tests = session.query(Test).filter(
                Test.sync_status == "pending"
            ).order_by(Test.updated_at.desc()).limit(5).all()
            
            pending_data = {
                "summary": {
                    "total_pending": pending_patients + pending_tests + pending_reports,
                    "patients": pending_patients,
                    "tests": pending_tests,
                    "reports": pending_reports
                },
                "recent_pending": {
                    "patients": [
                        {
                            "id": p.id,
                            "name": p.name,
                            "updated_at": p.updated_at.isoformat()
                        }
                        for p in recent_pending_patients
                    ],
                    "tests": [
                        {
                            "id": t.id,
                            "patient_name": t.patient.name,
                            "test_type": t.test_type,
                            "updated_at": t.updated_at.isoformat()
                        }
                        for t in recent_pending_tests
                    ]
                }
            }
            
            return success_response(pending_data, "待同步数据统计获取成功")
            
    except Exception as e:
        logger.error(f"获取待同步数据失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取待同步数据失败: {str(e)}")

# 导出路由
__all__ = ["router"]