"""
SarcNeuro Edge 患者管理API
"""
from typing import List, Optional, Dict, Any
from datetime import datetime
import logging

from fastapi import APIRouter, HTTPException, Depends, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.database import db_manager
from models.database_models import Patient
from api import success_response, error_response, paginated_response

logger = logging.getLogger(__name__)

router = APIRouter()

# Pydantic模型
class PatientCreate(BaseModel):
    name: str = Field(..., min_length=2, max_length=50, description="患者姓名")
    age: int = Field(..., ge=0, le=120, description="患者年龄")
    gender: str = Field(..., regex="^(MALE|FEMALE)$", description="患者性别")
    height: Optional[float] = Field(None, ge=50, le=250, description="身高(cm)")
    weight: Optional[float] = Field(None, ge=10, le=200, description="体重(kg)")
    phone: Optional[str] = Field(None, max_length=20, description="联系电话")
    email: Optional[str] = Field(None, max_length=100, description="邮箱地址")
    id_number: Optional[str] = Field(None, max_length=50, description="身份证号")
    medical_record_number: Optional[str] = Field(None, max_length=50, description="病历号")
    medical_history: Optional[List[str]] = Field(None, description="既往病史")
    medications: Optional[List[str]] = Field(None, description="当前用药")
    allergies: Optional[List[str]] = Field(None, description="过敏史")
    notes: Optional[str] = Field(None, max_length=1000, description="备注")

class PatientUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=2, max_length=50, description="患者姓名")
    age: Optional[int] = Field(None, ge=0, le=120, description="患者年龄")
    gender: Optional[str] = Field(None, regex="^(MALE|FEMALE)$", description="患者性别")
    height: Optional[float] = Field(None, ge=50, le=250, description="身高(cm)")
    weight: Optional[float] = Field(None, ge=10, le=200, description="体重(kg)")
    phone: Optional[str] = Field(None, max_length=20, description="联系电话")
    email: Optional[str] = Field(None, max_length=100, description="邮箱地址")
    id_number: Optional[str] = Field(None, max_length=50, description="身份证号")
    medical_record_number: Optional[str] = Field(None, max_length=50, description="病历号")
    medical_history: Optional[List[str]] = Field(None, description="既往病史")
    medications: Optional[List[str]] = Field(None, description="当前用药")
    allergies: Optional[List[str]] = Field(None, description="过敏史")
    notes: Optional[str] = Field(None, max_length=1000, description="备注")
    is_active: Optional[bool] = Field(None, description="是否激活")

class PatientResponse(BaseModel):
    id: int
    name: str
    age: int
    gender: str
    height: Optional[float]
    weight: Optional[float]
    phone: Optional[str]
    email: Optional[str]
    id_number: Optional[str]
    medical_record_number: Optional[str]
    medical_history: Optional[List[str]]
    medications: Optional[List[str]]
    allergies: Optional[List[str]]
    notes: Optional[str]
    is_active: bool
    created_at: str
    updated_at: str
    test_count: int = 0
    report_count: int = 0
    last_test_date: Optional[str] = None

# 依赖注入
def get_db():
    """获取数据库会话"""
    return db_manager.get_session()

# API端点
@router.post("/", response_model=Dict[str, Any])
async def create_patient(
    patient_data: PatientCreate,
    db: Session = Depends(get_db)
):
    """创建新患者"""
    try:
        with next(db) as session:
            # 检查是否存在同名患者
            existing_patient = session.query(Patient).filter(
                Patient.name == patient_data.name,
                Patient.is_active == True
            ).first()
            
            if existing_patient:
                raise HTTPException(status_code=400, detail="同名患者已存在")
            
            # 创建患者记录
            patient = Patient(
                name=patient_data.name,
                age=patient_data.age,
                gender=patient_data.gender,
                height=patient_data.height,
                weight=patient_data.weight,
                phone=patient_data.phone,
                email=patient_data.email,
                id_number=patient_data.id_number,
                medical_record_number=patient_data.medical_record_number,
                medical_history=patient_data.medical_history,
                medications=patient_data.medications,
                allergies=patient_data.allergies,
                notes=patient_data.notes,
                sync_status="pending"
            )
            
            session.add(patient)
            session.commit()
            session.refresh(patient)
            
            # 构造响应数据
            response_data = {
                "id": patient.id,
                "name": patient.name,
                "age": patient.age,
                "gender": patient.gender,
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
                "is_active": patient.is_active,
                "created_at": patient.created_at.isoformat(),
                "updated_at": patient.updated_at.isoformat()
            }
            
            logger.info(f"患者创建成功: {patient.name} (ID: {patient.id})")
            return success_response(response_data, "患者创建成功")
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"患者创建失败: {e}")
        raise HTTPException(status_code=500, detail=f"患者创建失败: {str(e)}")

@router.get("/", response_model=Dict[str, Any])
async def get_patients(
    page: int = Query(1, ge=1, description="页码"),
    size: int = Query(20, ge=1, le=100, description="每页数量"),
    search: Optional[str] = Query(None, description="搜索关键词"),
    gender: Optional[str] = Query(None, regex="^(MALE|FEMALE)$", description="性别筛选"),
    age_min: Optional[int] = Query(None, ge=0, description="最小年龄"),
    age_max: Optional[int] = Query(None, le=120, description="最大年龄"),
    active_only: bool = Query(True, description="仅显示活跃患者"),
    db: Session = Depends(get_db)
):
    """获取患者列表"""
    try:
        with next(db) as session:
            # 构建查询
            query = session.query(Patient)
            
            # 筛选条件
            if active_only:
                query = query.filter(Patient.is_active == True)
            
            if search:
                query = query.filter(
                    Patient.name.contains(search) |
                    Patient.phone.contains(search) |
                    Patient.email.contains(search) |
                    Patient.medical_record_number.contains(search)
                )
            
            if gender:
                query = query.filter(Patient.gender == gender)
            
            if age_min is not None:
                query = query.filter(Patient.age >= age_min)
            
            if age_max is not None:
                query = query.filter(Patient.age <= age_max)
            
            # 获取总数
            total = query.count()
            
            # 分页
            offset = (page - 1) * size
            patients = query.order_by(Patient.updated_at.desc()).offset(offset).limit(size).all()
            
            # 构造响应数据
            patient_list = []
            for patient in patients:
                # 获取测试和报告统计
                test_count = len(patient.tests)
                report_count = len(patient.reports)
                last_test_date = None
                
                if patient.tests:
                    last_test = max(patient.tests, key=lambda t: t.created_at)
                    last_test_date = last_test.created_at.isoformat()
                
                patient_data = {
                    "id": patient.id,
                    "name": patient.name,
                    "age": patient.age,
                    "gender": patient.gender,
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
                    "is_active": patient.is_active,
                    "created_at": patient.created_at.isoformat(),
                    "updated_at": patient.updated_at.isoformat(),
                    "test_count": test_count,
                    "report_count": report_count,
                    "last_test_date": last_test_date,
                    "sync_status": patient.sync_status
                }
                
                patient_list.append(patient_data)
            
            return paginated_response(patient_list, total, page, size)
            
    except Exception as e:
        logger.error(f"获取患者列表失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取患者列表失败: {str(e)}")

@router.get("/{patient_id}", response_model=Dict[str, Any])
async def get_patient(
    patient_id: int,
    db: Session = Depends(get_db)
):
    """获取患者详细信息"""
    try:
        with next(db) as session:
            patient = session.query(Patient).filter(Patient.id == patient_id).first()
            
            if not patient:
                raise HTTPException(status_code=404, detail="患者不存在")
            
            # 获取关联数据统计
            test_count = len(patient.tests)
            report_count = len(patient.reports)
            
            # 获取最近的测试和报告
            recent_tests = sorted(patient.tests, key=lambda t: t.created_at, reverse=True)[:5]
            recent_reports = sorted(patient.reports, key=lambda r: r.created_at, reverse=True)[:5]
            
            # 构造响应数据
            response_data = {
                "id": patient.id,
                "name": patient.name,
                "age": patient.age,
                "gender": patient.gender,
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
                "is_active": patient.is_active,
                "created_at": patient.created_at.isoformat(),
                "updated_at": patient.updated_at.isoformat(),
                "sync_status": patient.sync_status,
                "synced_at": patient.synced_at.isoformat() if patient.synced_at else None,
                "statistics": {
                    "test_count": test_count,
                    "report_count": report_count
                },
                "recent_tests": [
                    {
                        "id": test.id,
                        "test_type": test.test_type,
                        "status": test.status,
                        "created_at": test.created_at.isoformat()
                    } for test in recent_tests
                ],
                "recent_reports": [
                    {
                        "id": report.id,
                        "title": report.title,
                        "status": report.status,
                        "created_at": report.created_at.isoformat()
                    } for report in recent_reports
                ]
            }
            
            return success_response(response_data)
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取患者详情失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取患者详情失败: {str(e)}")

@router.put("/{patient_id}", response_model=Dict[str, Any])
async def update_patient(
    patient_id: int,
    patient_data: PatientUpdate,
    db: Session = Depends(get_db)
):
    """更新患者信息"""
    try:
        with next(db) as session:
            patient = session.query(Patient).filter(Patient.id == patient_id).first()
            
            if not patient:
                raise HTTPException(status_code=404, detail="患者不存在")
            
            # 更新字段
            update_data = patient_data.dict(exclude_unset=True)
            for field, value in update_data.items():
                setattr(patient, field, value)
            
            # 更新同步状态
            patient.sync_status = "pending"
            
            session.commit()
            session.refresh(patient)
            
            # 构造响应数据
            response_data = {
                "id": patient.id,
                "name": patient.name,
                "age": patient.age,
                "gender": patient.gender,
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
                "is_active": patient.is_active,
                "created_at": patient.created_at.isoformat(),
                "updated_at": patient.updated_at.isoformat()
            }
            
            logger.info(f"患者信息更新成功: {patient.name} (ID: {patient.id})")
            return success_response(response_data, "患者信息更新成功")
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"患者信息更新失败: {e}")
        raise HTTPException(status_code=500, detail=f"患者信息更新失败: {str(e)}")

@router.delete("/{patient_id}", response_model=Dict[str, Any])
async def delete_patient(
    patient_id: int,
    hard_delete: bool = Query(False, description="是否物理删除"),
    db: Session = Depends(get_db)
):
    """删除患者"""
    try:
        with next(db) as session:
            patient = session.query(Patient).filter(Patient.id == patient_id).first()
            
            if not patient:
                raise HTTPException(status_code=404, detail="患者不存在")
            
            if hard_delete:
                # 物理删除（级联删除相关数据）
                session.delete(patient)
                message = "患者记录已彻底删除"
            else:
                # 逻辑删除
                patient.is_active = False
                patient.sync_status = "pending"
                message = "患者记录已标记为删除"
            
            session.commit()
            
            logger.info(f"患者删除成功: {patient.name} (ID: {patient.id}, 硬删除: {hard_delete})")
            return success_response({"patient_id": patient_id, "hard_delete": hard_delete}, message)
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"患者删除失败: {e}")
        raise HTTPException(status_code=500, detail=f"患者删除失败: {str(e)}")

@router.get("/{patient_id}/tests", response_model=Dict[str, Any])
async def get_patient_tests(
    patient_id: int,
    page: int = Query(1, ge=1),
    size: int = Query(10, ge=1, le=50),
    db: Session = Depends(get_db)
):
    """获取患者的测试记录"""
    try:
        with next(db) as session:
            patient = session.query(Patient).filter(Patient.id == patient_id).first()
            
            if not patient:
                raise HTTPException(status_code=404, detail="患者不存在")
            
            # 获取测试记录
            tests = patient.tests
            total = len(tests)
            
            # 分页
            offset = (page - 1) * size
            tests_page = sorted(tests, key=lambda t: t.created_at, reverse=True)[offset:offset + size]
            
            # 构造响应数据
            test_list = []
            for test in tests_page:
                test_data = {
                    "id": test.id,
                    "test_type": test.test_type,
                    "test_mode": test.test_mode,
                    "status": test.status,
                    "duration": test.duration,
                    "start_time": test.start_time.isoformat() if test.start_time else None,
                    "end_time": test.end_time.isoformat() if test.end_time else None,
                    "created_at": test.created_at.isoformat(),
                    "has_analysis": test.analysis_result is not None,
                    "overall_score": test.analysis_result.overall_score if test.analysis_result else None,
                    "risk_level": test.analysis_result.risk_level if test.analysis_result else None
                }
                test_list.append(test_data)
            
            return paginated_response(test_list, total, page, size)
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取患者测试记录失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取患者测试记录失败: {str(e)}")

@router.get("/{patient_id}/reports", response_model=Dict[str, Any])
async def get_patient_reports(
    patient_id: int,
    page: int = Query(1, ge=1),
    size: int = Query(10, ge=1, le=50),
    db: Session = Depends(get_db)
):
    """获取患者的报告记录"""
    try:
        with next(db) as session:
            patient = session.query(Patient).filter(Patient.id == patient_id).first()
            
            if not patient:
                raise HTTPException(status_code=404, detail="患者不存在")
            
            # 获取报告记录
            reports = patient.reports
            total = len(reports)
            
            # 分页
            offset = (page - 1) * size
            reports_page = sorted(reports, key=lambda r: r.created_at, reverse=True)[offset:offset + size]
            
            # 构造响应数据
            report_list = []
            for report in reports_page:
                report_data = {
                    "id": report.id,
                    "title": report.title,
                    "report_number": report.report_number,
                    "status": report.status,
                    "is_published": report.is_published,
                    "created_at": report.created_at.isoformat(),
                    "published_at": report.published_at.isoformat() if report.published_at else None,
                    "test_type": report.test.test_type if report.test else None
                }
                report_list.append(report_data)
            
            return paginated_response(report_list, total, page, size)
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取患者报告记录失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取患者报告记录失败: {str(e)}")

@router.get("/search/by-name")
async def search_patients_by_name(
    name: str = Query(..., min_length=1, description="患者姓名"),
    limit: int = Query(10, ge=1, le=50, description="返回结果数量"),
    db: Session = Depends(get_db)
):
    """根据姓名搜索患者"""
    try:
        with next(db) as session:
            patients = session.query(Patient).filter(
                Patient.name.contains(name),
                Patient.is_active == True
            ).limit(limit).all()
            
            # 构造响应数据
            patient_list = []
            for patient in patients:
                patient_data = {
                    "id": patient.id,
                    "name": patient.name,
                    "age": patient.age,
                    "gender": patient.gender,
                    "phone": patient.phone,
                    "medical_record_number": patient.medical_record_number
                }
                patient_list.append(patient_data)
            
            return success_response(patient_list)
            
    except Exception as e:
        logger.error(f"患者姓名搜索失败: {e}")
        raise HTTPException(status_code=500, detail=f"搜索失败: {str(e)}")

# 导出路由
__all__ = ["router"]