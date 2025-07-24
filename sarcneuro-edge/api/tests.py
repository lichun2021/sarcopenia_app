"""
SarcNeuro Edge 测试管理API
"""
from typing import List, Optional, Dict, Any
from datetime import datetime
import logging

from fastapi import APIRouter, HTTPException, Depends, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.database import db_manager
from models.database_models import Test, Patient, AnalysisResult, PressureData
from api import success_response, error_response, paginated_response

logger = logging.getLogger(__name__)

router = APIRouter()

# Pydantic模型
class TestResponse(BaseModel):
    id: int
    patient_id: int
    patient_name: str
    test_type: str
    test_mode: str
    status: str
    duration: Optional[float]
    start_time: Optional[str]
    end_time: Optional[str]
    parameters: Optional[Dict[str, Any]]
    environment: Optional[Dict[str, Any]]
    notes: Optional[str]
    created_at: str
    updated_at: str
    has_analysis: bool
    has_pressure_data: bool
    data_points_count: int

# 依赖注入
def get_db():
    """获取数据库会话"""
    return db_manager.get_session()

# API端点
@router.get("/", response_model=Dict[str, Any])
async def get_tests(
    page: int = Query(1, ge=1, description="页码"),
    size: int = Query(20, ge=1, le=100, description="每页数量"),
    patient_id: Optional[int] = Query(None, description="患者ID筛选"),
    test_type: Optional[str] = Query(None, description="测试类型筛选"),
    status: Optional[str] = Query(None, description="状态筛选"),
    date_from: Optional[str] = Query(None, description="开始日期 (YYYY-MM-DD)"),
    date_to: Optional[str] = Query(None, description="结束日期 (YYYY-MM-DD)"),
    db: Session = Depends(get_db)
):
    """获取测试列表"""
    try:
        with next(db) as session:
            # 构建查询
            query = session.query(Test).join(Patient)
            
            # 筛选条件
            if patient_id:
                query = query.filter(Test.patient_id == patient_id)
            
            if test_type:
                query = query.filter(Test.test_type == test_type)
            
            if status:
                query = query.filter(Test.status == status)
            
            if date_from:
                date_from_obj = datetime.fromisoformat(date_from)
                query = query.filter(Test.created_at >= date_from_obj)
            
            if date_to:
                date_to_obj = datetime.fromisoformat(date_to)
                query = query.filter(Test.created_at <= date_to_obj)
            
            # 获取总数
            total = query.count()
            
            # 分页
            offset = (page - 1) * size
            tests = query.order_by(Test.created_at.desc()).offset(offset).limit(size).all()
            
            # 构造响应数据
            test_list = []
            for test in tests:
                # 统计相关数据
                has_analysis = test.analysis_result is not None
                pressure_data_count = len(test.pressure_data)
                has_pressure_data = pressure_data_count > 0
                
                test_data = {
                    "id": test.id,
                    "patient_id": test.patient.id,
                    "patient_name": test.patient.name,
                    "test_type": test.test_type,
                    "test_mode": test.test_mode,
                    "status": test.status,
                    "duration": test.duration,
                    "start_time": test.start_time.isoformat() if test.start_time else None,
                    "end_time": test.end_time.isoformat() if test.end_time else None,
                    "parameters": test.parameters,
                    "environment": test.environment,
                    "notes": test.notes,
                    "created_at": test.created_at.isoformat(),
                    "updated_at": test.updated_at.isoformat(),
                    "sync_status": test.sync_status,
                    "has_analysis": has_analysis,
                    "has_pressure_data": has_pressure_data,
                    "data_points_count": pressure_data_count,
                    "overall_score": test.analysis_result.overall_score if has_analysis else None,
                    "risk_level": test.analysis_result.risk_level if has_analysis else None
                }
                
                test_list.append(test_data)
            
            return paginated_response(test_list, total, page, size)
            
    except Exception as e:
        logger.error(f"获取测试列表失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取测试列表失败: {str(e)}")

@router.get("/{test_id}", response_model=Dict[str, Any])
async def get_test(
    test_id: int,
    include_pressure_data: bool = Query(False, description="是否包含压力数据"),
    db: Session = Depends(get_db)
):
    """获取测试详细信息"""
    try:
        with next(db) as session:
            test = session.query(Test).filter(Test.id == test_id).first()
            
            if not test:
                raise HTTPException(status_code=404, detail="测试记录不存在")
            
            # 获取分析结果
            analysis_result = test.analysis_result
            
            # 构造基础响应数据
            response_data = {
                "id": test.id,
                "patient": {
                    "id": test.patient.id,
                    "name": test.patient.name,
                    "age": test.patient.age,
                    "gender": test.patient.gender,
                    "height": test.patient.height,
                    "weight": test.patient.weight
                },
                "test_info": {
                    "test_type": test.test_type,
                    "test_mode": test.test_mode,
                    "status": test.status,
                    "duration": test.duration,
                    "start_time": test.start_time.isoformat() if test.start_time else None,
                    "end_time": test.end_time.isoformat() if test.end_time else None,
                    "parameters": test.parameters,
                    "environment": test.environment,
                    "notes": test.notes
                },
                "metadata": {
                    "created_at": test.created_at.isoformat(),
                    "updated_at": test.updated_at.isoformat(),
                    "sync_status": test.sync_status,
                    "synced_at": test.synced_at.isoformat() if test.synced_at else None
                },
                "statistics": {
                    "pressure_data_count": len(test.pressure_data),
                    "has_analysis": analysis_result is not None
                }
            }
            
            # 添加分析结果
            if analysis_result:
                response_data["analysis_result"] = {
                    "id": analysis_result.id,
                    "overall_score": analysis_result.overall_score,
                    "risk_level": analysis_result.risk_level,
                    "confidence": analysis_result.confidence,
                    "interpretation": analysis_result.interpretation,
                    "abnormalities": analysis_result.abnormalities,
                    "recommendations": analysis_result.recommendations,
                    "processing_time": analysis_result.processing_time,
                    "model_version": analysis_result.model_version,
                    "quality_score": analysis_result.quality_score,
                    "created_at": analysis_result.created_at.isoformat()
                }
                
                # 添加步态和平衡指标
                if analysis_result.gait_metrics:
                    gait = analysis_result.gait_metrics
                    response_data["gait_metrics"] = {
                        "walking_speed": gait.walking_speed,
                        "step_length": gait.step_length,
                        "cadence": gait.cadence,
                        "stance_phase": gait.stance_phase,
                        "swing_phase": gait.swing_phase,
                        "asymmetry_index": gait.asymmetry_index,
                        "stability_score": gait.stability_score
                    }
                
                if analysis_result.balance_metrics:
                    balance = analysis_result.balance_metrics
                    response_data["balance_metrics"] = {
                        "cop_displacement": balance.cop_displacement,
                        "sway_area": balance.sway_area,
                        "sway_velocity": balance.sway_velocity,
                        "stability_index": balance.stability_index,
                        "fall_risk_score": balance.fall_risk_score
                    }
            
            # 添加压力数据（如果请求）
            if include_pressure_data and test.pressure_data:
                pressure_data_list = []
                for pd in test.pressure_data[:100]:  # 限制返回数量
                    pressure_data_list.append({
                        "id": pd.id,
                        "timestamp": pd.timestamp.isoformat(),
                        "frame_number": pd.frame_number,
                        "max_pressure": pd.max_pressure,
                        "total_area": pd.total_area,
                        "center_of_pressure_x": pd.center_of_pressure_x,
                        "center_of_pressure_y": pd.center_of_pressure_y,
                        "left_foot_data_preview": pd.left_foot_data[:10] if pd.left_foot_data else None,
                        "right_foot_data_preview": pd.right_foot_data[:10] if pd.right_foot_data else None
                    })
                
                response_data["pressure_data"] = {
                    "total_count": len(test.pressure_data),
                    "returned_count": len(pressure_data_list),
                    "data": pressure_data_list
                }
            
            return success_response(response_data)
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取测试详情失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取测试详情失败: {str(e)}")

@router.delete("/{test_id}", response_model=Dict[str, Any])
async def delete_test(
    test_id: int,
    hard_delete: bool = Query(False, description="是否物理删除"),
    db: Session = Depends(get_db)
):
    """删除测试记录"""
    try:
        with next(db) as session:
            test = session.query(Test).filter(Test.id == test_id).first()
            
            if not test:
                raise HTTPException(status_code=404, detail="测试记录不存在")
            
            if hard_delete:
                # 物理删除（级联删除相关数据）
                session.delete(test)
                message = "测试记录已彻底删除"
            else:
                # 逻辑删除（更新状态）
                test.status = "DELETED"
                test.sync_status = "pending"
                message = "测试记录已标记为删除"
            
            session.commit()
            
            logger.info(f"测试删除成功: ID {test_id} (硬删除: {hard_delete})")
            return success_response({"test_id": test_id, "hard_delete": hard_delete}, message)
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"测试删除失败: {e}")
        raise HTTPException(status_code=500, detail=f"测试删除失败: {str(e)}")

@router.get("/{test_id}/pressure-data", response_model=Dict[str, Any])
async def get_test_pressure_data(
    test_id: int,
    page: int = Query(1, ge=1),
    size: int = Query(50, ge=1, le=1000),
    format: str = Query("summary", regex="^(summary|full)$", description="数据格式"),
    db: Session = Depends(get_db)
):
    """获取测试的压力数据"""
    try:
        with next(db) as session:
            test = session.query(Test).filter(Test.id == test_id).first()
            
            if not test:
                raise HTTPException(status_code=404, detail="测试记录不存在")
            
            # 获取压力数据
            pressure_data_query = session.query(PressureData).filter(
                PressureData.test_id == test_id
            ).order_by(PressureData.frame_number)
            
            total = pressure_data_query.count()
            offset = (page - 1) * size
            pressure_data_list = pressure_data_query.offset(offset).limit(size).all()
            
            # 构造响应数据
            data_list = []
            for pd in pressure_data_list:
                if format == "summary":
                    # 摘要格式：只返回统计数据
                    data_item = {
                        "id": pd.id,
                        "timestamp": pd.timestamp.isoformat(),
                        "frame_number": pd.frame_number,
                        "max_pressure": pd.max_pressure,
                        "total_area": pd.total_area,
                        "center_of_pressure_x": pd.center_of_pressure_x,
                        "center_of_pressure_y": pd.center_of_pressure_y
                    }
                else:
                    # 完整格式：包含原始数据
                    data_item = {
                        "id": pd.id,
                        "timestamp": pd.timestamp.isoformat(),
                        "frame_number": pd.frame_number,
                        "max_pressure": pd.max_pressure,
                        "total_area": pd.total_area,
                        "center_of_pressure_x": pd.center_of_pressure_x,
                        "center_of_pressure_y": pd.center_of_pressure_y,
                        "left_foot_data": pd.left_foot_data,
                        "right_foot_data": pd.right_foot_data,
                        "left_foot_cop": pd.left_foot_cop,
                        "right_foot_cop": pd.right_foot_cop
                    }
                
                data_list.append(data_item)
            
            response_data = {
                "test_id": test_id,
                "patient_name": test.patient.name,
                "test_type": test.test_type,
                "data_format": format,
                "pressure_data": data_list,
                "pagination": {
                    "total": total,
                    "page": page,
                    "size": size,
                    "pages": (total + size - 1) // size
                }
            }
            
            return success_response(response_data)
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取压力数据失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取压力数据失败: {str(e)}")

@router.get("/statistics/summary")
async def get_tests_statistics(
    date_from: Optional[str] = Query(None, description="开始日期"),
    date_to: Optional[str] = Query(None, description="结束日期"),
    patient_id: Optional[int] = Query(None, description="患者ID"),
    db: Session = Depends(get_db)
):
    """获取测试统计信息"""
    try:
        with next(db) as session:
            # 构建基础查询
            query = session.query(Test)
            
            # 筛选条件
            if patient_id:
                query = query.filter(Test.patient_id == patient_id)
            
            if date_from:
                date_from_obj = datetime.fromisoformat(date_from)
                query = query.filter(Test.created_at >= date_from_obj)
            
            if date_to:
                date_to_obj = datetime.fromisoformat(date_to)
                query = query.filter(Test.created_at <= date_to_obj)
            
            # 基础统计
            total_tests = query.count()
            completed_tests = query.filter(Test.status == "COMPLETED").count()
            failed_tests = query.filter(Test.status == "FAILED").count()
            processing_tests = query.filter(Test.status == "PROCESSING").count()
            
            # 按测试类型统计
            type_stats = {}
            for test_type in ["STATIC", "DYNAMIC", "BALANCE", "COMPREHENSIVE"]:
                count = query.filter(Test.test_type == test_type).count()
                type_stats[test_type] = count
            
            # 平均测试时长
            avg_duration = session.query(Test.duration).filter(
                Test.duration.isnot(None),
                Test.status == "COMPLETED"
            )
            if date_from:
                avg_duration = avg_duration.filter(Test.created_at >= date_from_obj)
            if date_to:
                avg_duration = avg_duration.filter(Test.created_at <= date_to_obj)
            if patient_id:
                avg_duration = avg_duration.filter(Test.patient_id == patient_id)
            
            durations = [d[0] for d in avg_duration.all()]
            avg_test_duration = sum(durations) / len(durations) if durations else 0
            
            # 风险等级分布（已分析的测试）
            risk_stats = {}
            analysis_query = session.query(AnalysisResult).join(Test)
            if patient_id:
                analysis_query = analysis_query.filter(Test.patient_id == patient_id)
            if date_from:
                analysis_query = analysis_query.filter(Test.created_at >= date_from_obj)
            if date_to:
                analysis_query = analysis_query.filter(Test.created_at <= date_to_obj)
            
            for risk_level in ["LOW", "MEDIUM", "HIGH", "CRITICAL"]:
                count = analysis_query.filter(AnalysisResult.risk_level == risk_level).count()
                risk_stats[risk_level] = count
            
            # 构造响应数据
            statistics = {
                "overview": {
                    "total_tests": total_tests,
                    "completed_tests": completed_tests,
                    "failed_tests": failed_tests,
                    "processing_tests": processing_tests,
                    "success_rate": (completed_tests / total_tests * 100) if total_tests > 0 else 0
                },
                "test_types": type_stats,
                "risk_distribution": risk_stats,
                "performance": {
                    "average_duration": round(avg_test_duration, 2),
                    "total_analysis_time": round(sum(durations), 2) if durations else 0
                },
                "date_range": {
                    "from": date_from,
                    "to": date_to
                },
                "filters": {
                    "patient_id": patient_id
                }
            }
            
            return success_response(statistics)
            
    except Exception as e:
        logger.error(f"获取测试统计失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取测试统计失败: {str(e)}")

# 导出路由
__all__ = ["router"]