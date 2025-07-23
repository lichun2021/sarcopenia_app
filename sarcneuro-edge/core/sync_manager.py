"""
SarcNeuro Edge 数据同步管理器
"""
import asyncio
import json
import uuid
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any
from sqlalchemy.orm import Session
import httpx
import logging

from app.database import db_manager
from app.config import config
from models.database_models import (
    Patient, Test, PressureData, AnalysisResult, Report, 
    SyncLog, ModelInfo, SystemStatus
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class SyncManager:
    """数据同步管理器"""
    
    def __init__(self):
        self.api_base_url = config.sync.cloud_url
        self.api_key = config.sync.api_key
        self.timeout = config.sync.timeout
        self.batch_size = config.sync.batch_size
        self.retry_count = config.sync.retry_count
        
        self.is_syncing = False
        self.last_sync_time = None
        
    async def check_cloud_connection(self) -> bool:
        """检查云端连接状态"""
        if not self.api_key:
            return False
            
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                response = await client.get(
                    f"{self.api_base_url}/api/health",
                    headers={"Authorization": f"Bearer {self.api_key}"}
                )
                return response.status_code == 200
        except Exception as e:
            logger.warning(f"云端连接检查失败: {e}")
            return False
    
    async def sync_all_data(self) -> Dict[str, Any]:
        """同步所有数据"""
        if self.is_syncing:
            return {"status": "already_syncing", "message": "同步正在进行中"}
            
        self.is_syncing = True
        sync_start_time = datetime.now()
        
        try:
            # 检查云端连接
            if not await self.check_cloud_connection():
                return {"status": "no_connection", "message": "无法连接到云端服务器"}
            
            sync_results = {
                "status": "success",
                "start_time": sync_start_time,
                "operations": []
            }
            
            # 1. 下载最新模型
            model_result = await self.sync_models()
            sync_results["operations"].append({"type": "models", "result": model_result})
            
            # 2. 上传患者数据
            patient_result = await self.upload_patients()
            sync_results["operations"].append({"type": "patients", "result": patient_result})
            
            # 3. 上传测试数据
            test_result = await self.upload_tests()
            sync_results["operations"].append({"type": "tests", "result": test_result})
            
            # 4. 上传报告
            report_result = await self.upload_reports()
            sync_results["operations"].append({"type": "reports", "result": report_result})
            
            # 5. 下载云端患者更新
            patient_download_result = await self.download_patient_updates()
            sync_results["operations"].append({"type": "patient_updates", "result": patient_download_result})
            
            # 更新系统状态
            self._update_system_sync_status()
            
            sync_results["end_time"] = datetime.now()
            sync_results["duration"] = (sync_results["end_time"] - sync_start_time).total_seconds()
            
            self.last_sync_time = sync_results["end_time"]
            
            # 记录同步日志
            self._log_sync_operation("full_sync", sync_results)
            
            logger.info(f"数据同步完成，耗时: {sync_results['duration']:.2f}秒")
            return sync_results
            
        except Exception as e:
            error_result = {
                "status": "error",
                "message": f"同步失败: {str(e)}",
                "start_time": sync_start_time,
                "end_time": datetime.now()
            }
            
            # 记录错误日志
            self._log_sync_operation("full_sync", error_result)
            logger.error(f"数据同步失败: {e}")
            
            return error_result
            
        finally:
            self.is_syncing = False
    
    async def sync_models(self) -> Dict[str, Any]:
        """同步AI模型"""
        try:
            # 获取云端模型列表
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(
                    f"{self.api_base_url}/api/models/list",
                    headers={"Authorization": f"Bearer {self.api_key}"}
                )
                
                if response.status_code != 200:
                    return {"status": "failed", "message": "获取模型列表失败"}
                
                cloud_models = response.json()
                
            # 检查本地模型版本
            with db_manager.get_session() as session:
                local_models = session.query(ModelInfo).all()
                local_model_dict = {model.name: model for model in local_models}
                
                updated_models = []
                new_models = []
                
                for cloud_model in cloud_models:
                    model_name = cloud_model["name"]
                    cloud_version = cloud_model["version"]
                    
                    local_model = local_model_dict.get(model_name)
                    
                    # 检查是否需要更新
                    if not local_model or local_model.version != cloud_version:
                        download_result = await self._download_model(cloud_model)
                        
                        if download_result["status"] == "success":
                            if local_model:
                                updated_models.append(model_name)
                            else:
                                new_models.append(model_name)
                
                return {
                    "status": "success",
                    "updated_models": updated_models,
                    "new_models": new_models,
                    "total_models": len(cloud_models)
                }
                
        except Exception as e:
            logger.error(f"模型同步失败: {e}")
            return {"status": "failed", "message": str(e)}
    
    async def _download_model(self, model_info: Dict[str, Any]) -> Dict[str, Any]:
        """下载单个模型"""
        try:
            model_name = model_info["name"]
            download_url = model_info["download_url"]
            
            # 下载模型文件
            async with httpx.AsyncClient(timeout=600) as client:  # 10分钟超时
                response = await client.get(
                    download_url,
                    headers={"Authorization": f"Bearer {self.api_key}"}
                )
                
                if response.status_code != 200:
                    return {"status": "failed", "message": "模型下载失败"}
                
                # 保存模型文件
                model_path = config.get_model_path(f"{model_name}.pkl")
                with open(model_path, "wb") as f:
                    f.write(response.content)
                
                # 更新数据库记录
                with db_manager.get_session() as session:
                    existing_model = session.query(ModelInfo).filter(
                        ModelInfo.name == model_name
                    ).first()
                    
                    if existing_model:
                        # 更新现有模型
                        existing_model.version = model_info["version"]
                        existing_model.file_path = model_path
                        existing_model.file_size = len(response.content)
                        existing_model.downloaded_at = datetime.now()
                        existing_model.is_downloaded = True
                        existing_model.description = model_info.get("description")
                        existing_model.performance_metrics = model_info.get("performance_metrics")
                    else:
                        # 创建新模型记录
                        new_model = ModelInfo(
                            name=model_name,
                            version=model_info["version"],
                            file_path=model_path,
                            file_size=len(response.content),
                            description=model_info.get("description"),
                            model_type=model_info.get("model_type"),
                            performance_metrics=model_info.get("performance_metrics"),
                            is_downloaded=True,
                            downloaded_at=datetime.now()
                        )
                        session.add(new_model)
                    
                    session.commit()
                
                logger.info(f"模型下载成功: {model_name}")
                return {"status": "success", "model": model_name}
                
        except Exception as e:
            logger.error(f"模型下载失败 {model_info.get('name')}: {e}")
            return {"status": "failed", "message": str(e)}
    
    async def upload_patients(self) -> Dict[str, Any]:
        """上传患者数据"""
        try:
            with db_manager.get_session() as session:
                # 获取需要同步的患者
                pending_patients = session.query(Patient).filter(
                    Patient.sync_status.in_(["pending", "conflict"])
                ).limit(self.batch_size).all()
                
                if not pending_patients:
                    return {"status": "success", "uploaded": 0, "message": "无需同步的患者数据"}
                
                uploaded_count = 0
                failed_count = 0
                
                for patient in pending_patients:
                    upload_result = await self._upload_single_patient(patient)
                    
                    if upload_result["status"] == "success":
                        # 更新同步状态
                        patient.cloud_id = upload_result.get("cloud_id")
                        patient.sync_status = "synced"
                        patient.synced_at = datetime.now()
                        uploaded_count += 1
                    else:
                        failed_count += 1
                        logger.error(f"患者上传失败 {patient.name}: {upload_result.get('message')}")
                
                session.commit()
                
                return {
                    "status": "success",
                    "uploaded": uploaded_count,
                    "failed": failed_count,
                    "total": len(pending_patients)
                }
                
        except Exception as e:
            logger.error(f"患者数据上传失败: {e}")
            return {"status": "failed", "message": str(e)}
    
    async def _upload_single_patient(self, patient: Patient) -> Dict[str, Any]:
        """上传单个患者数据"""
        try:
            patient_data = {
                "local_id": patient.id,
                "name": patient.name,
                "gender": patient.gender,
                "age": patient.age,
                "height": patient.height,
                "weight": patient.weight,
                "phone": patient.phone,
                "email": patient.email,
                "id_number": patient.id_number,
                "medical_record_number": patient.medical_record_number,
                "medical_history": patient.medical_history,
                "medications": patient.medications,
                "allergies": patient.allergies,
                "notes": patient.notes,
                "created_at": patient.created_at.isoformat()
            }
            
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                if patient.cloud_id:
                    # 更新现有患者
                    response = await client.put(
                        f"{self.api_base_url}/api/patients/{patient.cloud_id}",
                        json=patient_data,
                        headers={"Authorization": f"Bearer {self.api_key}"}
                    )
                else:
                    # 创建新患者
                    response = await client.post(
                        f"{self.api_base_url}/api/patients",
                        json=patient_data,
                        headers={"Authorization": f"Bearer {self.api_key}"}
                    )
                
                if response.status_code in [200, 201]:
                    result = response.json()
                    return {
                        "status": "success",
                        "cloud_id": result.get("id")
                    }
                else:
                    return {
                        "status": "failed",
                        "message": f"HTTP {response.status_code}: {response.text}"
                    }
                    
        except Exception as e:
            return {"status": "failed", "message": str(e)}
    
    async def upload_tests(self) -> Dict[str, Any]:
        """上传测试数据"""
        try:
            with db_manager.get_session() as session:
                # 获取需要同步的测试
                pending_tests = session.query(Test).filter(
                    Test.sync_status.in_(["pending", "conflict"])
                ).limit(self.batch_size).all()
                
                if not pending_tests:
                    return {"status": "success", "uploaded": 0, "message": "无需同步的测试数据"}
                
                uploaded_count = 0
                failed_count = 0
                
                for test in pending_tests:
                    upload_result = await self._upload_single_test(test)
                    
                    if upload_result["status"] == "success":
                        test.cloud_id = upload_result.get("cloud_id")
                        test.sync_status = "synced"
                        test.synced_at = datetime.now()
                        uploaded_count += 1
                    else:
                        failed_count += 1
                
                session.commit()
                
                return {
                    "status": "success",
                    "uploaded": uploaded_count,
                    "failed": failed_count,
                    "total": len(pending_tests)
                }
                
        except Exception as e:
            logger.error(f"测试数据上传失败: {e}")
            return {"status": "failed", "message": str(e)}
    
    async def _upload_single_test(self, test: Test) -> Dict[str, Any]:
        """上传单个测试数据"""
        try:
            # 获取关联的压力数据和分析结果
            with db_manager.get_session() as session:
                pressure_data_list = session.query(PressureData).filter(
                    PressureData.test_id == test.id
                ).all()
                
                analysis_result = session.query(AnalysisResult).filter(
                    AnalysisResult.test_id == test.id
                ).first()
                
                test_data = {
                    "local_id": test.id,
                    "patient_cloud_id": test.patient.cloud_id,
                    "test_type": test.test_type,
                    "test_mode": test.test_mode,
                    "duration": test.duration,
                    "parameters": test.parameters,
                    "environment": test.environment,
                    "status": test.status,
                    "start_time": test.start_time.isoformat() if test.start_time else None,
                    "end_time": test.end_time.isoformat() if test.end_time else None,
                    "notes": test.notes,
                    "created_at": test.created_at.isoformat(),
                    "pressure_data": [
                        {
                            "timestamp": pd.timestamp.isoformat(),
                            "frame_number": pd.frame_number,
                            "left_foot_data": pd.left_foot_data,
                            "right_foot_data": pd.right_foot_data,
                            "max_pressure": pd.max_pressure,
                            "total_area": pd.total_area,
                            "center_of_pressure_x": pd.center_of_pressure_x,
                            "center_of_pressure_y": pd.center_of_pressure_y
                        }
                        for pd in pressure_data_list
                    ],
                    "analysis_result": {
                        "overall_score": analysis_result.overall_score,
                        "risk_level": analysis_result.risk_level,
                        "confidence": analysis_result.confidence,
                        "interpretation": analysis_result.interpretation,
                        "abnormalities": analysis_result.abnormalities,
                        "recommendations": analysis_result.recommendations,
                        "detailed_analysis": analysis_result.detailed_analysis,
                        "processing_time": analysis_result.processing_time,
                        "model_version": analysis_result.model_version
                    } if analysis_result else None
                }
                
                async with httpx.AsyncClient(timeout=self.timeout * 3) as client:  # 测试数据较大，延长超时时间
                    if test.cloud_id:
                        # 更新现有测试
                        response = await client.put(
                            f"{self.api_base_url}/api/tests/{test.cloud_id}",
                            json=test_data,
                            headers={"Authorization": f"Bearer {self.api_key}"}
                        )
                    else:
                        # 创建新测试
                        response = await client.post(
                            f"{self.api_base_url}/api/tests",
                            json=test_data,
                            headers={"Authorization": f"Bearer {self.api_key}"}
                        )
                    
                    if response.status_code in [200, 201]:
                        result = response.json()
                        return {
                            "status": "success",
                            "cloud_id": result.get("id")
                        }
                    else:
                        return {
                            "status": "failed",
                            "message": f"HTTP {response.status_code}: {response.text}"
                        }
                        
        except Exception as e:
            logger.error(f"测试上传失败: {e}")
            return {"status": "failed", "message": str(e)}
    
    async def upload_reports(self) -> Dict[str, Any]:
        """上传报告数据"""
        try:
            with db_manager.get_session() as session:
                pending_reports = session.query(Report).filter(
                    Report.sync_status.in_(["pending", "conflict"])
                ).limit(self.batch_size).all()
                
                if not pending_reports:
                    return {"status": "success", "uploaded": 0, "message": "无需同步的报告数据"}
                
                uploaded_count = 0
                failed_count = 0
                
                for report in pending_reports:
                    upload_result = await self._upload_single_report(report)
                    
                    if upload_result["status"] == "success":
                        report.cloud_id = upload_result.get("cloud_id")
                        report.sync_status = "synced"
                        report.synced_at = datetime.now()
                        uploaded_count += 1
                    else:
                        failed_count += 1
                
                session.commit()
                
                return {
                    "status": "success",
                    "uploaded": uploaded_count,
                    "failed": failed_count,
                    "total": len(pending_reports)
                }
                
        except Exception as e:
            logger.error(f"报告数据上传失败: {e}")
            return {"status": "failed", "message": str(e)}
    
    async def _upload_single_report(self, report: Report) -> Dict[str, Any]:
        """上传单个报告"""
        try:
            report_data = {
                "local_id": report.id,
                "patient_cloud_id": report.patient.cloud_id,
                "test_cloud_id": report.test.cloud_id,
                "title": report.title,
                "report_number": report.report_number,
                "status": report.status,
                "summary": report.summary,
                "content": report.content,
                "recommendations": report.recommendations,
                "template": report.template,
                "version": report.version,
                "is_published": report.is_published,
                "published_at": report.published_at.isoformat() if report.published_at else None,
                "created_at": report.created_at.isoformat()
            }
            
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                if report.cloud_id:
                    response = await client.put(
                        f"{self.api_base_url}/api/reports/{report.cloud_id}",
                        json=report_data,
                        headers={"Authorization": f"Bearer {self.api_key}"}
                    )
                else:
                    response = await client.post(
                        f"{self.api_base_url}/api/reports",
                        json=report_data,
                        headers={"Authorization": f"Bearer {self.api_key}"}
                    )
                
                if response.status_code in [200, 201]:
                    result = response.json()
                    return {
                        "status": "success",
                        "cloud_id": result.get("id")
                    }
                else:
                    return {
                        "status": "failed",
                        "message": f"HTTP {response.status_code}: {response.text}"
                    }
                    
        except Exception as e:
            return {"status": "failed", "message": str(e)}
    
    async def download_patient_updates(self) -> Dict[str, Any]:
        """下载患者数据更新"""
        try:
            # 获取最后同步时间
            last_sync = self.last_sync_time or (datetime.now() - timedelta(days=1))
            
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(
                    f"{self.api_base_url}/api/patients/updates",
                    params={"since": last_sync.isoformat()},
                    headers={"Authorization": f"Bearer {self.api_key}"}
                )
                
                if response.status_code != 200:
                    return {"status": "failed", "message": "获取患者更新失败"}
                
                updates = response.json()
                
                updated_count = 0
                for patient_data in updates:
                    update_result = await self._process_patient_update(patient_data)
                    if update_result["status"] == "success":
                        updated_count += 1
                
                return {
                    "status": "success",
                    "updated": updated_count,
                    "total": len(updates)
                }
                
        except Exception as e:
            logger.error(f"下载患者更新失败: {e}")
            return {"status": "failed", "message": str(e)}
    
    async def _process_patient_update(self, patient_data: Dict[str, Any]) -> Dict[str, Any]:
        """处理患者数据更新"""
        try:
            cloud_id = patient_data["id"]
            
            with db_manager.get_session() as session:
                # 查找本地患者记录
                local_patient = session.query(Patient).filter(
                    Patient.cloud_id == cloud_id
                ).first()
                
                if local_patient:
                    # 更新现有患者
                    local_patient.name = patient_data.get("name", local_patient.name)
                    local_patient.gender = patient_data.get("gender", local_patient.gender)
                    local_patient.age = patient_data.get("age", local_patient.age)
                    local_patient.height = patient_data.get("height", local_patient.height)
                    local_patient.weight = patient_data.get("weight", local_patient.weight)
                    local_patient.phone = patient_data.get("phone", local_patient.phone)
                    local_patient.email = patient_data.get("email", local_patient.email)
                    local_patient.sync_status = "synced"
                    local_patient.synced_at = datetime.now()
                else:
                    # 创建新的本地患者记录
                    new_patient = Patient(
                        cloud_id=cloud_id,
                        name=patient_data["name"],
                        gender=patient_data["gender"],
                        age=patient_data["age"],
                        height=patient_data.get("height"),
                        weight=patient_data.get("weight"),
                        phone=patient_data.get("phone"),
                        email=patient_data.get("email"),
                        sync_status="synced",
                        synced_at=datetime.now()
                    )
                    session.add(new_patient)
                
                session.commit()
                return {"status": "success"}
                
        except Exception as e:
            logger.error(f"处理患者更新失败: {e}")
            return {"status": "failed", "message": str(e)}
    
    def _update_system_sync_status(self):
        """更新系统同步状态"""
        try:
            with db_manager.get_session() as session:
                system_status = session.query(SystemStatus).first()
                
                if system_status:
                    system_status.last_sync_time = datetime.now()
                    system_status.cloud_connected = True
                    
                    # 更新统计数据
                    system_status.total_patients = session.query(Patient).count()
                    system_status.total_tests = session.query(Test).count()
                    system_status.total_reports = session.query(Report).count()
                    
                    # 计算待同步数量
                    pending_count = 0
                    for model_class in [Patient, Test, Report]:
                        pending_count += session.query(model_class).filter(
                            model_class.sync_status == "pending"
                        ).count()
                    
                    system_status.pending_sync_count = pending_count
                    session.commit()
                    
        except Exception as e:
            logger.error(f"更新系统同步状态失败: {e}")
    
    def _log_sync_operation(self, operation_type: str, result: Dict[str, Any]):
        """记录同步操作日志"""
        try:
            with db_manager.get_session() as session:
                sync_log = SyncLog(
                    sync_type=operation_type,
                    operation="sync",
                    status=result.get("status", "unknown"),
                    details=result,
                    start_time=result.get("start_time", datetime.now()),
                    end_time=result.get("end_time", datetime.now()),
                    duration=result.get("duration", 0)
                )
                session.add(sync_log)
                session.commit()
                
        except Exception as e:
            logger.error(f"记录同步日志失败: {e}")
    
    async def get_sync_status(self) -> Dict[str, Any]:
        """获取同步状态"""
        try:
            is_connected = await self.check_cloud_connection()
            
            with db_manager.get_session() as session:
                # 获取待同步数据统计
                pending_patients = session.query(Patient).filter(
                    Patient.sync_status == "pending"
                ).count()
                
                pending_tests = session.query(Test).filter(
                    Test.sync_status == "pending"
                ).count()
                
                pending_reports = session.query(Report).filter(
                    Report.sync_status == "pending"
                ).count()
                
                # 获取最近同步日志
                recent_logs = session.query(SyncLog).order_by(
                    SyncLog.created_at.desc()
                ).limit(5).all()
                
                return {
                    "is_connected": is_connected,
                    "is_syncing": self.is_syncing,
                    "last_sync_time": self.last_sync_time.isoformat() if self.last_sync_time else None,
                    "pending_sync": {
                        "patients": pending_patients,
                        "tests": pending_tests,
                        "reports": pending_reports,
                        "total": pending_patients + pending_tests + pending_reports
                    },
                    "sync_config": {
                        "enabled": config.sync.enabled,
                        "cloud_url": config.sync.cloud_url,
                        "has_api_key": bool(config.sync.api_key),
                        "interval": config.sync.interval
                    },
                    "recent_logs": [
                        {
                            "type": log.sync_type,
                            "status": log.status,
                            "duration": log.duration,
                            "created_at": log.created_at.isoformat()
                        }
                        for log in recent_logs
                    ]
                }
                
        except Exception as e:
            logger.error(f"获取同步状态失败: {e}")
            return {
                "is_connected": False,
                "is_syncing": False,
                "error": str(e)
            }

# 全局同步管理器实例
sync_manager = SyncManager()

# 自动同步调度器
class SyncScheduler:
    """自动同步调度器"""
    
    def __init__(self, sync_manager: SyncManager):
        self.sync_manager = sync_manager
        self.is_running = False
        
    async def start_auto_sync(self):
        """启动自动同步"""
        if not config.sync.enabled:
            logger.info("自动同步已禁用")
            return
            
        self.is_running = True
        logger.info(f"启动自动同步，间隔: {config.sync.interval}秒")
        
        while self.is_running:
            try:
                # 检查网络连接
                if await self.sync_manager.check_cloud_connection():
                    logger.info("开始自动同步...")
                    result = await self.sync_manager.sync_all_data()
                    logger.info(f"自动同步完成: {result.get('status')}")
                else:
                    logger.warning("无网络连接，跳过自动同步")
                
                # 等待下次同步
                await asyncio.sleep(config.sync.interval)
                
            except Exception as e:
                logger.error(f"自动同步失败: {e}")
                await asyncio.sleep(60)  # 出错时等待1分钟后重试
    
    def stop_auto_sync(self):
        """停止自动同步"""
        self.is_running = False
        logger.info("自动同步已停止")

# 全局调度器实例
sync_scheduler = SyncScheduler(sync_manager)

# 导出
__all__ = [
    "SyncManager",
    "sync_manager", 
    "SyncScheduler",
    "sync_scheduler"
]