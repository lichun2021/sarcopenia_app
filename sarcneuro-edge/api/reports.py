"""
SarcNeuro Edge 报告管理API
"""
from typing import List, Optional, Dict, Any
from datetime import datetime
import logging
import os

from fastapi import APIRouter, HTTPException, Depends, Query, BackgroundTasks
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.database import db_manager
from models.database_models import Report, Test, Patient, AnalysisResult
from core.report_generator import report_generator
from api import success_response, error_response, paginated_response

logger = logging.getLogger(__name__)

router = APIRouter()

# Pydantic模型
class ReportGenerateRequest(BaseModel):
    test_id: int = Field(..., description="测试ID")
    report_type: str = Field("comprehensive", pattern="^(comprehensive|summary|detailed)$", description="报告类型")
    format: str = Field("html", pattern="^(html|pdf)$", description="报告格式")
    title: Optional[str] = Field(None, description="自定义标题")
    template: Optional[str] = Field(None, description="报告模板")

class ReportResponse(BaseModel):
    id: int
    title: str
    report_number: str
    status: str
    patient_name: str
    test_type: str
    format: str
    file_size: Optional[int]
    created_at: str
    updated_at: str
    is_published: bool
    published_at: Optional[str]

# 依赖注入
def get_db():
    """获取数据库会话"""
    return db_manager.get_session()

# API端点
@router.post("/generate", response_model=Dict[str, Any])
async def generate_report(
    request: ReportGenerateRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """生成分析报告"""
    try:
        with next(db) as session:
            # 验证测试记录存在
            test = session.query(Test).filter(Test.id == request.test_id).first()
            if not test:
                raise HTTPException(status_code=404, detail="测试记录不存在")
            
            # 验证是否有分析结果
            analysis_result = test.analysis_result
            if not analysis_result:
                raise HTTPException(status_code=400, detail="该测试尚未完成分析，无法生成报告")
            
            # 检查是否已有报告
            existing_report = session.query(Report).filter(
                Report.test_id == request.test_id
            ).first()
            
            if existing_report and existing_report.is_published:
                # 如果已有发布的报告，返回现有报告
                logger.info(f"返回现有报告: {existing_report.report_number}")
                return success_response({
                    "report_id": existing_report.id,
                    "report_number": existing_report.report_number,
                    "status": "existing",
                    "message": "报告已存在",
                    "file_path": existing_report.content.get("file_path") if existing_report.content else None
                })
            
            # 生成报告
            try:
                result = await report_generator.generate_report(
                    test_id=request.test_id,
                    report_type=request.report_type,
                    format=request.format
                )
                
                if result["status"] == "success":
                    logger.info(f"报告生成成功: {result['report_number']}")
                    return success_response({
                        "report_id": result["report_id"],
                        "report_number": result["report_number"],
                        "file_path": result["report_path"],
                        "format": result["format"],
                        "generation_time": result["generation_time"]
                    }, "报告生成成功")
                else:
                    raise HTTPException(status_code=500, detail=result["message"])
                    
            except Exception as e:
                logger.error(f"报告生成失败: {e}")
                raise HTTPException(status_code=500, detail=f"报告生成失败: {str(e)}")
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"报告生成处理失败: {e}")
        raise HTTPException(status_code=500, detail=f"报告生成处理失败: {str(e)}")

@router.get("/", response_model=Dict[str, Any])
async def get_reports(
    page: int = Query(1, ge=1, description="页码"),
    size: int = Query(20, ge=1, le=100, description="每页数量"),
    patient_id: Optional[int] = Query(None, description="患者ID筛选"),
    status: Optional[str] = Query(None, description="状态筛选"),
    date_from: Optional[str] = Query(None, description="开始日期"),
    date_to: Optional[str] = Query(None, description="结束日期"),
    db: Session = Depends(get_db)
):
    """获取报告列表"""
    try:
        with next(db) as session:
            # 构建查询
            query = session.query(Report).join(Patient)
            
            # 筛选条件
            if patient_id:
                query = query.filter(Report.patient_id == patient_id)
            
            if status:
                query = query.filter(Report.status == status)
            
            if date_from:
                date_from_obj = datetime.fromisoformat(date_from)
                query = query.filter(Report.created_at >= date_from_obj)
            
            if date_to:
                date_to_obj = datetime.fromisoformat(date_to)
                query = query.filter(Report.created_at <= date_to_obj)
            
            # 获取总数
            total = query.count()
            
            # 分页
            offset = (page - 1) * size
            reports = query.order_by(Report.created_at.desc()).offset(offset).limit(size).all()
            
            # 构造响应数据
            report_list = []
            for report in reports:
                # 获取文件信息
                file_path = report.content.get("file_path") if report.content else None
                file_size = None
                if file_path and os.path.exists(file_path):
                    file_size = os.path.getsize(file_path)
                
                # 确定格式
                format_type = "html" if file_path and file_path.endswith('.html') else "pdf"
                
                report_data = {
                    "id": report.id,
                    "title": report.title,
                    "report_number": report.report_number,
                    "status": report.status,
                    "patient_id": report.patient.id,
                    "patient_name": report.patient.name,
                    "test_id": report.test.id if report.test else None,
                    "test_type": report.test.test_type if report.test else None,
                    "format": format_type,
                    "file_size": file_size,
                    "is_published": report.is_published,
                    "version": report.version,
                    "template": report.template,
                    "created_at": report.created_at.isoformat(),
                    "updated_at": report.updated_at.isoformat(),
                    "published_at": report.published_at.isoformat() if report.published_at else None,
                    "sync_status": report.sync_status
                }
                
                report_list.append(report_data)
            
            return paginated_response(report_list, total, page, size)
            
    except Exception as e:
        logger.error(f"获取报告列表失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取报告列表失败: {str(e)}")

@router.get("/{report_id}", response_model=Dict[str, Any])
async def get_report(
    report_id: int,
    db: Session = Depends(get_db)
):
    """获取报告详细信息"""
    try:
        with next(db) as session:
            report = session.query(Report).filter(Report.id == report_id).first()
            
            if not report:
                raise HTTPException(status_code=404, detail="报告不存在")
            
            # 获取文件信息
            file_path = report.content.get("file_path") if report.content else None
            file_size = None
            file_exists = False
            
            if file_path:
                file_exists = os.path.exists(file_path)
                if file_exists:
                    file_size = os.path.getsize(file_path)
            
            # 确定格式
            format_type = "html" if file_path and file_path.endswith('.html') else "pdf"
            
            # 构造响应数据
            response_data = {
                "id": report.id,
                "title": report.title,
                "report_number": report.report_number,
                "status": report.status,
                "patient": {
                    "id": report.patient.id,
                    "name": report.patient.name,
                    "age": report.patient.age,
                    "gender": report.patient.gender
                },
                "test": {
                    "id": report.test.id,
                    "test_type": report.test.test_type,
                    "created_at": report.test.created_at.isoformat()
                } if report.test else None,
                "report_info": {
                    "format": format_type,
                    "template": report.template,
                    "version": report.version,
                    "is_published": report.is_published,
                    "published_at": report.published_at.isoformat() if report.published_at else None
                },
                "file_info": {
                    "file_path": file_path,
                    "file_size": file_size,
                    "file_exists": file_exists
                },
                "content": {
                    "summary": report.summary,
                    "recommendations": report.recommendations,
                    "generation_info": report.content
                },
                "metadata": {
                    "created_at": report.created_at.isoformat(),
                    "updated_at": report.updated_at.isoformat(),
                    "sync_status": report.sync_status,
                    "synced_at": report.synced_at.isoformat() if report.synced_at else None
                }
            }
            
            return success_response(response_data)
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取报告详情失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取报告详情失败: {str(e)}")

@router.get("/{report_id}/download")
async def download_report(
    report_id: int,
    db: Session = Depends(get_db)
):
    """下载报告文件"""
    try:
        with next(db) as session:
            report = session.query(Report).filter(Report.id == report_id).first()
            
            if not report:
                raise HTTPException(status_code=404, detail="报告不存在")
            
            # 获取文件路径
            file_path = report.content.get("file_path") if report.content else None
            
            if not file_path or not os.path.exists(file_path):
                raise HTTPException(status_code=404, detail="报告文件不存在")
            
            # 确定文件类型和下载名称
            if file_path.endswith('.html'):
                media_type = "text/html"
                filename = f"{report.report_number}.html"
            elif file_path.endswith('.pdf'):
                media_type = "application/pdf"
                filename = f"{report.report_number}.pdf"
            else:
                media_type = "application/octet-stream"
                filename = f"{report.report_number}.file"
            
            logger.info(f"下载报告: {report.report_number} -> {filename}")
            
            return FileResponse(
                path=file_path,
                media_type=media_type,
                filename=filename,
                headers={"Content-Disposition": f"attachment; filename={filename}"}
            )
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"下载报告失败: {e}")
        raise HTTPException(status_code=500, detail=f"下载报告失败: {str(e)}")

@router.delete("/{report_id}", response_model=Dict[str, Any])
async def delete_report(
    report_id: int,
    delete_file: bool = Query(False, description="是否删除文件"),
    db: Session = Depends(get_db)
):
    """删除报告"""
    try:
        with next(db) as session:
            report = session.query(Report).filter(Report.id == report_id).first()
            
            if not report:
                raise HTTPException(status_code=404, detail="报告不存在")
            
            # 获取文件路径
            file_path = report.content.get("file_path") if report.content else None
            
            # 删除数据库记录
            session.delete(report)
            session.commit()
            
            # 删除文件（如果请求）
            if delete_file and file_path and os.path.exists(file_path):
                try:
                    os.remove(file_path)
                    logger.info(f"报告文件已删除: {file_path}")
                except Exception as e:
                    logger.warning(f"删除报告文件失败: {e}")
            
            logger.info(f"报告删除成功: {report.report_number}")
            return success_response({
                "report_id": report_id,
                "report_number": report.report_number,
                "file_deleted": delete_file and file_path and os.path.exists(file_path)
            }, "报告删除成功")
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"报告删除失败: {e}")
        raise HTTPException(status_code=500, detail=f"报告删除失败: {str(e)}")

@router.post("/{report_id}/publish", response_model=Dict[str, Any])
async def publish_report(
    report_id: int,
    db: Session = Depends(get_db)
):
    """发布报告"""
    try:
        with next(db) as session:
            report = session.query(Report).filter(Report.id == report_id).first()
            
            if not report:
                raise HTTPException(status_code=404, detail="报告不存在")
            
            if report.is_published:
                return success_response({"report_id": report_id}, "报告已经是发布状态")
            
            # 更新发布状态
            report.is_published = True
            report.published_at = datetime.now()
            report.status = "PUBLISHED"
            report.sync_status = "pending"
            
            session.commit()
            
            logger.info(f"报告发布成功: {report.report_number}")
            return success_response({
                "report_id": report_id,
                "report_number": report.report_number,
                "published_at": report.published_at.isoformat()
            }, "报告发布成功")
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"报告发布失败: {e}")
        raise HTTPException(status_code=500, detail=f"报告发布失败: {str(e)}")

@router.get("/list/by-patient/{patient_id}")
async def get_reports_by_patient(
    patient_id: int,
    published_only: bool = Query(True, description="仅显示已发布报告"),
    db: Session = Depends(get_db)
):
    """获取指定患者的报告列表"""
    try:
        with next(db) as session:
            # 验证患者存在
            patient = session.query(Patient).filter(Patient.id == patient_id).first()
            if not patient:
                raise HTTPException(status_code=404, detail="患者不存在")
            
            # 构建查询
            query = session.query(Report).filter(Report.patient_id == patient_id)
            
            if published_only:
                query = query.filter(Report.is_published == True)
            
            reports = query.order_by(Report.created_at.desc()).all()
            
            # 构造响应数据
            report_list = []
            for report in reports:
                report_data = {
                    "id": report.id,
                    "title": report.title,
                    "report_number": report.report_number,
                    "status": report.status,
                    "test_type": report.test.test_type if report.test else None,
                    "is_published": report.is_published,
                    "created_at": report.created_at.isoformat(),
                    "published_at": report.published_at.isoformat() if report.published_at else None
                }
                report_list.append(report_data)
            
            return success_response({
                "patient": {
                    "id": patient.id,
                    "name": patient.name
                },
                "reports": report_list,
                "total_count": len(report_list)
            })
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取患者报告列表失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取患者报告列表失败: {str(e)}")

@router.get("/statistics/summary")
async def get_reports_statistics(
    date_from: Optional[str] = Query(None, description="开始日期"),
    date_to: Optional[str] = Query(None, description="结束日期"),
    db: Session = Depends(get_db)
):
    """获取报告统计信息"""
    try:
        with next(db) as session:
            # 构建基础查询
            query = session.query(Report)
            
            # 筛选条件
            if date_from:
                date_from_obj = datetime.fromisoformat(date_from)
                query = query.filter(Report.created_at >= date_from_obj)
            
            if date_to:
                date_to_obj = datetime.fromisoformat(date_to)
                query = query.filter(Report.created_at <= date_to_obj)
            
            # 基础统计
            total_reports = query.count()
            published_reports = query.filter(Report.is_published == True).count()
            draft_reports = query.filter(Report.status == "DRAFT").count()
            
            # 按状态统计
            status_stats = {}
            for status in ["DRAFT", "PENDING", "PUBLISHED"]:
                count = query.filter(Report.status == status).count()
                status_stats[status] = count
            
            # 按模板统计
            template_stats = {}
            templates = session.query(Report.template).filter(Report.template.isnot(None)).distinct().all()
            for template in templates:
                template_name = template[0]
                count = query.filter(Report.template == template_name).count()
                template_stats[template_name] = count
            
            statistics = {
                "overview": {
                    "total_reports": total_reports,
                    "published_reports": published_reports,
                    "draft_reports": draft_reports,
                    "publish_rate": (published_reports / total_reports * 100) if total_reports > 0 else 0
                },
                "status_distribution": status_stats,
                "template_distribution": template_stats,
                "date_range": {
                    "from": date_from,
                    "to": date_to
                }
            }
            
            return success_response(statistics)
            
    except Exception as e:
        logger.error(f"获取报告统计失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取报告统计失败: {str(e)}")

# 导出路由
__all__ = ["router"]