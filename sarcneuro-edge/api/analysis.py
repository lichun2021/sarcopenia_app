"""
SarcNeuro Edge 数据分析API
"""
import json
import uuid
from typing import List, Optional, Dict, Any
from datetime import datetime
import logging

from fastapi import APIRouter, HTTPException, Depends, UploadFile, File, Form
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.database import db_manager
from models.database_models import Patient, Test, PressureData, AnalysisResult, GaitMetrics, BalanceMetrics
from core.analyzer import SarcNeuroAnalyzer, PatientInfo, PressurePoint
from api import success_response, error_response

logger = logging.getLogger(__name__)

router = APIRouter()

# Pydantic模型
class PatientCreateRequest(BaseModel):
    name: str = Field(..., min_length=2, max_length=50, description="患者姓名")
    age: int = Field(..., ge=0, le=120, description="患者年龄")
    gender: str = Field(..., pattern="^(MALE|FEMALE)$", description="患者性别")
    height: Optional[float] = Field(None, ge=50, le=250, description="身高(cm)")
    weight: Optional[float] = Field(None, ge=10, le=200, description="体重(kg)")
    phone: Optional[str] = Field(None, max_length=20, description="联系电话")
    email: Optional[str] = Field(None, max_length=100, description="邮箱地址")

class AnalysisRequest(BaseModel):
    patient_id: Optional[int] = Field(None, description="患者ID，不提供则自动创建")
    patient_info: Optional[PatientCreateRequest] = Field(None, description="患者信息，用于创建新患者")
    test_type: str = Field("COMPREHENSIVE", pattern="^(STATIC|DYNAMIC|BALANCE|COMPREHENSIVE)$", description="测试类型")
    test_mode: str = Field("UPLOAD", pattern="^(REAL_TIME|UPLOAD)$", description="测试模式")
    csv_data: str = Field(..., description="CSV格式的压力数据")
    parameters: Optional[Dict[str, Any]] = Field(None, description="测试参数")

class AnalysisResponse(BaseModel):
    analysis_id: int
    patient_name: str
    test_type: str
    overall_score: float
    risk_level: str
    confidence: float
    interpretation: str
    abnormalities: List[str]
    recommendations: List[str]
    processing_time: float

# 依赖注入
def get_db():
    """获取数据库会话"""
    return db_manager.get_session()

def get_analyzer():
    """获取分析器实例"""
    return SarcNeuroAnalyzer()

# API端点
@router.post("/analyze", response_model=Dict[str, Any])
async def analyze_pressure_data(
    request: AnalysisRequest,
    db: Session = Depends(get_db),
    analyzer: SarcNeuroAnalyzer = Depends(get_analyzer)
):
    """分析压力数据"""
    try:
        logger.info(f"开始分析请求 - 测试类型: {request.test_type}")
        
        with next(db) as session:
            # 获取或创建患者
            patient = None
            if request.patient_id:
                patient = session.query(Patient).filter(Patient.id == request.patient_id).first()
                if not patient:
                    raise HTTPException(status_code=404, detail="患者不存在")
            elif request.patient_info:
                # 创建新患者
                patient = Patient(
                    name=request.patient_info.name,
                    age=request.patient_info.age,
                    gender=request.patient_info.gender,
                    height=request.patient_info.height,
                    weight=request.patient_info.weight,
                    phone=request.patient_info.phone,
                    email=request.patient_info.email,
                    sync_status="pending"
                )
                session.add(patient)
                session.flush()  # 获取patient.id
            else:
                raise HTTPException(status_code=400, detail="必须提供患者ID或患者信息")
            
            # 创建测试记录
            test = Test(
                patient_id=patient.id,
                test_type=request.test_type,
                test_mode=request.test_mode,
                parameters=request.parameters,
                status="PROCESSING",
                start_time=datetime.now(),
                sync_status="pending"
            )
            session.add(test)
            session.flush()
            
            # 解析CSV数据
            try:
                pressure_points = analyzer.parse_csv_data(request.csv_data)
                logger.info(f"解析到 {len(pressure_points)} 个压力数据点")
            except Exception as e:
                test.status = "FAILED"
                session.commit()
                raise HTTPException(status_code=400, detail=f"CSV数据解析失败: {str(e)}")
            
            # 保存压力数据到数据库
            for i, point in enumerate(pressure_points):
                pressure_data = PressureData(
                    test_id=test.id,
                    timestamp=datetime.fromisoformat(point.timestamp.replace('Z', '+00:00')) if 'T' in point.timestamp else datetime.now(),
                    frame_number=i,
                    left_foot_data=point.data[:512] if len(point.data) >= 512 else point.data,  # 前512个数据点作为左脚
                    right_foot_data=point.data[512:] if len(point.data) >= 1024 else point.data,  # 后512个数据点作为右脚
                    max_pressure=float(point.max_pressure),
                    total_area=float(point.contact_area),
                    center_of_pressure_x=16.0,  # 默认值，实际应该计算
                    center_of_pressure_y=16.0,
                    sync_status="pending"
                )
                session.add(pressure_data)
            
            # 创建患者信息对象进行分析
            patient_info = PatientInfo(
                name=patient.name,
                age=patient.age,
                gender=patient.gender,
                height=patient.height,
                weight=patient.weight
            )
            
            # 执行分析
            try:
                analysis_result = analyzer.comprehensive_analysis(
                    pressure_points, 
                    patient_info, 
                    request.test_type
                )
                logger.info(f"分析完成 - 评分: {analysis_result.overall_score}, 风险: {analysis_result.risk_level}")
            except Exception as e:
                test.status = "FAILED"
                session.commit()
                raise HTTPException(status_code=500, detail=f"数据分析失败: {str(e)}")
            
            # 保存分析结果
            db_analysis_result = AnalysisResult(
                test_id=test.id,
                overall_score=analysis_result.overall_score,
                risk_level=analysis_result.risk_level,
                confidence=analysis_result.confidence,
                interpretation=analysis_result.interpretation,
                abnormalities=analysis_result.abnormalities,
                recommendations=analysis_result.recommendations,
                detailed_analysis=analysis_result.detailed_analysis,
                processing_time=analysis_result.detailed_analysis.get("analysis_time", 0) * 1000,  # 转换为毫秒
                model_version="SarcNeuro-1.0.0",
                sync_status="pending"
            )
            session.add(db_analysis_result)
            session.flush()
            
            # 保存步态指标
            gait_metrics = GaitMetrics(
                analysis_result_id=db_analysis_result.id,
                walking_speed=analysis_result.gait_analysis.walking_speed,
                step_length=analysis_result.gait_analysis.step_length,
                step_width=analysis_result.gait_analysis.step_width,
                cadence=analysis_result.gait_analysis.cadence,
                stride_time=analysis_result.gait_analysis.stride_time,
                left_step_length=analysis_result.gait_analysis.left_step_length,
                right_step_length=analysis_result.gait_analysis.right_step_length,
                left_cadence=analysis_result.gait_analysis.left_cadence,
                right_cadence=analysis_result.gait_analysis.right_cadence,
                left_stride_speed=analysis_result.gait_analysis.left_stride_speed,
                right_stride_speed=analysis_result.gait_analysis.right_stride_speed,
                left_swing_speed=analysis_result.gait_analysis.left_swing_speed,
                right_swing_speed=analysis_result.gait_analysis.right_swing_speed,
                stance_phase=analysis_result.gait_analysis.stance_phase,
                swing_phase=analysis_result.gait_analysis.swing_phase,
                left_stance_phase=analysis_result.gait_analysis.left_stance_phase,
                right_stance_phase=analysis_result.gait_analysis.right_stance_phase,
                left_swing_phase=analysis_result.gait_analysis.left_swing_phase,
                right_swing_phase=analysis_result.gait_analysis.right_swing_phase,
                double_support_time=analysis_result.gait_analysis.double_support_time,
                left_double_support_time=analysis_result.gait_analysis.left_double_support_time,
                right_double_support_time=analysis_result.gait_analysis.right_double_support_time,
                left_step_height=analysis_result.gait_analysis.left_step_height,
                right_step_height=analysis_result.gait_analysis.right_step_height,
                turn_time=analysis_result.gait_analysis.turn_time,
                asymmetry_index=analysis_result.gait_analysis.asymmetry_index,
                stability_score=analysis_result.gait_analysis.stability_score,
                rhythm_regularity=analysis_result.gait_analysis.rhythm_regularity,
                speed_abnormal=analysis_result.gait_analysis.speed_abnormal,
                cadence_abnormal=analysis_result.gait_analysis.cadence_abnormal,
                stance_abnormal=analysis_result.gait_analysis.stance_abnormal,
                stride_abnormal=analysis_result.gait_analysis.stride_abnormal,
                swing_abnormal=analysis_result.gait_analysis.swing_abnormal
            )
            session.add(gait_metrics)
            
            # 保存平衡指标
            balance_metrics = BalanceMetrics(
                analysis_result_id=db_analysis_result.id,
                cop_displacement=analysis_result.balance_analysis.cop_displacement,
                sway_area=analysis_result.balance_analysis.sway_area,
                sway_velocity=analysis_result.balance_analysis.sway_velocity,
                stability_index=analysis_result.balance_analysis.stability_index,
                fall_risk_score=analysis_result.balance_analysis.fall_risk_score,
                anterior_stability=analysis_result.balance_analysis.anterior_stability,
                posterior_stability=analysis_result.balance_analysis.posterior_stability,
                medial_stability=analysis_result.balance_analysis.medial_stability,
                lateral_stability=analysis_result.balance_analysis.lateral_stability
            )
            session.add(balance_metrics)
            
            # 更新测试状态
            test.status = "COMPLETED"
            test.end_time = datetime.now()
            test.duration = (test.end_time - test.start_time).total_seconds()
            
            # 提交所有更改
            session.commit()
            session.refresh(db_analysis_result)
            
            # 构造响应
            response_data = {
                "analysis_id": db_analysis_result.id,
                "test_id": test.id,
                "patient_id": patient.id,
                "patient_name": patient.name,
                "test_type": test.test_type,
                "overall_score": analysis_result.overall_score,
                "risk_level": analysis_result.risk_level,
                "confidence": analysis_result.confidence,
                "interpretation": analysis_result.interpretation,
                "abnormalities": analysis_result.abnormalities,
                "recommendations": analysis_result.recommendations,
                "processing_time": db_analysis_result.processing_time,
                "detailed_analysis": {
                    "gait_analysis": {
                        "walking_speed": analysis_result.gait_analysis.walking_speed,
                        "step_length": analysis_result.gait_analysis.step_length,
                        "cadence": analysis_result.gait_analysis.cadence,
                        "asymmetry_index": analysis_result.gait_analysis.asymmetry_index,
                        "stability_score": analysis_result.gait_analysis.stability_score
                    },
                    "balance_analysis": {
                        "cop_displacement": analysis_result.balance_analysis.cop_displacement,
                        "sway_area": analysis_result.balance_analysis.sway_area,
                        "sway_velocity": analysis_result.balance_analysis.sway_velocity,
                        "stability_index": analysis_result.balance_analysis.stability_index,
                        "fall_risk_score": analysis_result.balance_analysis.fall_risk_score
                    }
                },
                "created_at": test.created_at.isoformat(),
                "completed_at": test.end_time.isoformat()
            }
            
            logger.info(f"分析完成并保存 - 分析ID: {db_analysis_result.id}")
            return success_response(response_data, "数据分析完成")
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"分析处理失败: {e}")
        raise HTTPException(status_code=500, detail=f"分析处理失败: {str(e)}")

@router.post("/upload-file", response_model=Dict[str, Any])
async def upload_csv_file(
    file: UploadFile = File(...),
    patient_id: Optional[int] = Form(None),
    patient_name: Optional[str] = Form(None),
    patient_age: Optional[int] = Form(None),
    patient_gender: Optional[str] = Form(None),
    patient_height: Optional[float] = Form(None),
    patient_weight: Optional[float] = Form(None),
    test_type: str = Form("COMPREHENSIVE"),
    db: Session = Depends(get_db)
):
    """上传CSV文件进行分析"""
    try:
        # 检查文件类型
        if not file.filename.endswith('.csv'):
            raise HTTPException(status_code=400, detail="只支持CSV文件")
        
        # 读取文件内容
        content = await file.read()
        csv_data = content.decode('utf-8')
        
        # 构造分析请求
        request_data = {
            "test_type": test_type,
            "test_mode": "UPLOAD",
            "csv_data": csv_data
        }
        
        # 处理患者信息
        if patient_id:
            request_data["patient_id"] = patient_id
        elif patient_name and patient_age and patient_gender:
            request_data["patient_info"] = {
                "name": patient_name,
                "age": patient_age,
                "gender": patient_gender.upper(),
                "height": patient_height,
                "weight": patient_weight
            }
        else:
            raise HTTPException(status_code=400, detail="必须提供患者ID或完整的患者信息")
        
        # 调用分析函数
        analysis_request = AnalysisRequest(**request_data)
        return await analyze_pressure_data(analysis_request, db, get_analyzer())
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"文件上传分析失败: {e}")
        raise HTTPException(status_code=500, detail=f"文件处理失败: {str(e)}")

@router.get("/results/{analysis_id}", response_model=Dict[str, Any])
async def get_analysis_result(
    analysis_id: int,
    db: Session = Depends(get_db)
):
    """获取分析结果详情"""
    try:
        with next(db) as session:
            # 获取分析结果
            analysis_result = session.query(AnalysisResult).filter(
                AnalysisResult.id == analysis_id
            ).first()
            
            if not analysis_result:
                raise HTTPException(status_code=404, detail="分析结果不存在")
            
            # 获取关联的测试和患者信息
            test = analysis_result.test
            patient = test.patient
            gait_metrics = analysis_result.gait_metrics
            balance_metrics = analysis_result.balance_metrics
            
            # 构造详细响应
            response_data = {
                "analysis_id": analysis_result.id,
                "test_id": test.id,
                "patient": {
                    "id": patient.id,
                    "name": patient.name,
                    "age": patient.age,
                    "gender": patient.gender,
                    "height": patient.height,
                    "weight": patient.weight
                },
                "test_info": {
                    "test_type": test.test_type,
                    "test_mode": test.test_mode,
                    "duration": test.duration,
                    "status": test.status,
                    "start_time": test.start_time.isoformat() if test.start_time else None,
                    "end_time": test.end_time.isoformat() if test.end_time else None
                },
                "analysis_results": {
                    "overall_score": analysis_result.overall_score,
                    "risk_level": analysis_result.risk_level,
                    "confidence": analysis_result.confidence,
                    "interpretation": analysis_result.interpretation,
                    "abnormalities": analysis_result.abnormalities,
                    "recommendations": analysis_result.recommendations,
                    "processing_time": analysis_result.processing_time,
                    "model_version": analysis_result.model_version
                },
                "gait_metrics": {
                    "walking_speed": gait_metrics.walking_speed if gait_metrics else None,
                    "step_length": gait_metrics.step_length if gait_metrics else None,
                    "cadence": gait_metrics.cadence if gait_metrics else None,
                    "stance_phase": gait_metrics.stance_phase if gait_metrics else None,
                    "swing_phase": gait_metrics.swing_phase if gait_metrics else None,
                    "asymmetry_index": gait_metrics.asymmetry_index if gait_metrics else None,
                    "stability_score": gait_metrics.stability_score if gait_metrics else None,
                    "rhythm_regularity": gait_metrics.rhythm_regularity if gait_metrics else None
                } if gait_metrics else None,
                "balance_metrics": {
                    "cop_displacement": balance_metrics.cop_displacement if balance_metrics else None,
                    "sway_area": balance_metrics.sway_area if balance_metrics else None,
                    "sway_velocity": balance_metrics.sway_velocity if balance_metrics else None,
                    "stability_index": balance_metrics.stability_index if balance_metrics else None,
                    "fall_risk_score": balance_metrics.fall_risk_score if balance_metrics else None
                } if balance_metrics else None,
                "created_at": analysis_result.created_at.isoformat(),
                "updated_at": analysis_result.updated_at.isoformat()
            }
            
            return success_response(response_data)
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取分析结果失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取分析结果失败: {str(e)}")

@router.get("/demo")
async def demo_analysis():
    """演示分析功能"""
    # 模拟CSV数据
    demo_csv_data = """time,max_pressure,timestamp,contact_area,total_pressure,data
0.1,150,2024-07-22T10:00:00Z,45,1200,"[10,15,20,25,30,35,40,45,50,55,60,65,70,75,80,85,90,95,100,105,110,115,120,125,130,135,140,145,150,155,160,165,170,175,180,185,190,195,200,205,210,215,220,225,230,235,240,245,250,255,260,265,270,275,280,285,290,295,300,305,310,315,320,325,330,335,340,345,350,355,360,365,370,375,380,385,390,395,400,405,410,415,420,425,430,435,440,445,450,455,460,465,470,475,480,485,490,495,500,505,510,515,520,525,530,535,540,545,550,555,560,565,570,575,580,585,590,595,600,605,610,615,620,625,630,635,640,645,650,655,660,665,670,675,680,685,690,695,700,705,710,715,720,725,730,735,740,745,750,755,760,765,770,775,780,785,790,795,800,805,810,815,820,825,830,835,840,845,850,855,860,865,870,875,880,885,890,895,900,905,910,915,920,925,930,935,940,945,950,955,960,965,970,975,980,985,990,995,1000,1005,1010,1015,1020,1025,1030,1035,1040,1045,1050,1055,1060,1065,1070,1075,1080,1085,1090,1095,1100,1105,1110,1115,1120,1125,1130,1135,1140,1145,1150,1155,1160,1165,1170,1175,1180,1185,1190,1195,1200,1205,1210,1215,1220,1225,1230,1235,1240,1245,1250,1255,1260,1265,1270,1275,1280,1285,1290,1295,1300,1305,1310,1315,1320,1325,1330,1335,1340,1345,1350,1355,1360,1365,1370,1375,1380,1385,1390,1395,1400,1405,1410,1415,1420,1425,1430,1435,1440,1445,1450,1455,1460,1465,1470,1475,1480,1485,1490,1495,1500,1505,1510,1515,1520,1525,1530,1535,1540,1545,1550,1555,1560,1565,1570,1575,1580,1585,1590,1595,1600,1605,1610,1615,1620,1625,1630,1635,1640,1645,1650,1655,1660,1665,1670,1675,1680,1685,1690,1695,1700,1705,1710,1715,1720,1725,1730,1735,1740,1745,1750,1755,1760,1765,1770,1775,1780,1785,1790,1795,1800,1805,1810,1815,1820,1825,1830,1835,1840,1845,1850,1855,1860,1865,1870,1875,1880,1885,1890,1895,1900,1905,1910,1915,1920,1925,1930,1935,1940,1945,1950,1955,1960,1965,1970,1975,1980,1985,1990,1995,2000,2005,2010,2015,2020,2025,2030,2035,2040,2045,2050,2055,2060,2065,2070,2075,2080,2085,2090,2095,2100,2105,2110,2115,2120,2125,2130,2135,2140,2145,2150,2155,2160,2165,2170,2175,2180,2185,2190,2195,2200,2205,2210,2215,2220,2225,2230,2235,2240,2245,2250,2255,2260,2265,2270,2275,2280,2285,2290,2295,2300,2305,2310,2315,2320,2325,2330,2335,2340,2345,2350,2355,2360,2365,2370,2375,2380,2385,2390,2395,2400,2405,2410,2415,2420,2425,2430,2435,2440,2445,2450,2455,2460,2465,2470,2475,2480,2485,2490,2495,2500,2505,2510,2515,2520,2525,2530,2535,2540,2545,2550,2555,2560,2565,2570,2575,2580,2585,2590,2595,2600,2605,2610,2615,2620,2625,2630,2635,2640,2645,2650,2655,2660,2665,2670,2675,2680,2685,2690,2695,2700,2705,2710,2715,2720,2725,2730,2735,2740,2745,2750,2755,2760,2765,2770,2775,2780,2785,2790,2795,2800,2805,2810,2815,2820,2825,2830,2835,2840,2845,2850,2855,2860,2865,2870,2875,2880,2885,2890,2895,2900,2905,2910,2915,2920,2925,2930,2935,2940,2945,2950,2955,2960,2965,2970,2975,2980,2985,2990,2995,3000,3005,3010,3015,3020,3025,3030,3035,3040,3045,3050,3055,3060,3065,3070,3075,3080,3085,3090,3095,3100,3105,3110,3115,3120,3125,3130,3135,3140,3145,3150,3155,3160,3165,3170,3175,3180,3185,3190,3195,3200,3205,3210,3215,3220,3225,3230,3235,3240,3245,3250,3255,3260,3265,3270,3275,3280,3285,3290,3295,3300,3305,3310,3315,3320,3325,3330,3335,3340,3345,3350,3355,3360,3365,3370,3375,3380,3385,3390,3395,3400,3405,3410,3415,3420,3425,3430,3435,3440,3445,3450,3455,3460,3465,3470,3475,3480,3485,3490,3495,3500,3505,3510,3515,3520,3525,3530,3535,3540,3545,3550,3555,3560,3565,3570,3575,3580,3585,3590,3595,3600,3605,3610,3615,3620,3625,3630,3635,3640,3645,3650,3655,3660,3665,3670,3675,3680,3685,3690,3695,3700,3705,3710,3715,3720,3725,3730,3735,3740,3745,3750,3755,3760,3765,3770,3775,3780,3785,3790,3795,3800,3805,3810,3815,3820,3825,3830,3835,3840,3845,3850,3855,3860,3865,3870,3875,3880,3885,3890,3895,3900,3905,3910,3915,3920,3925,3930,3935,3940,3945,3950,3955,3960,3965,3970,3975,3980,3985,3990,3995,4000,4005,4010,4015,4020,4025,4030,4035,4040,4045,4050,4055,4060,4065,4070,4075,4080,4085,4090,4095]"
0.2,155,2024-07-22T10:00:00Z,48,1250,"[15,20,25,30,35,40,45,50,55,60,65,70,75,80,85,90,95,100,105,110,115,120,125,130,135,140,145,150,155,160,165,170,175,180,185,190,195,200,205,210,215,220,225,230,235,240,245,250,255,260,265,270,275,280,285,290,295,300,305,310,315,320,325,330,335,340,345,350,355,360,365,370,375,380,385,390,395,400,405,410,415,420,425,430,435,440,445,450,455,460,465,470,475,480,485,490,495,500,505,510,515,520,525,530,535,540,545,550,555,560,565,570,575,580,585,590,595,600,605,610,615,620,625,630,635,640,645,650,655,660,665,670,675,680,685,690,695,700,705,710,715,720,725,730,735,740,745,750,755,760,765,770,775,780,785,790,795,800,805,810,815,820,825,830,835,840,845,850,855,860,865,870,875,880,885,890,895,900,905,910,915,920,925,930,935,940,945,950,955,960,965,970,975,980,985,990,995,1000,1005,1010,1015,1020,1025,1030,1035,1040,1045,1050,1055,1060,1065,1070,1075,1080,1085,1090,1095,1100,1105,1110,1115,1120,1125,1130,1135,1140,1145,1150,1155,1160,1165,1170,1175,1180,1185,1190,1195,1200,1205,1210,1215,1220,1225,1230,1235,1240,1245,1250,1255,1260,1265,1270,1275,1280,1285,1290,1295,1300,1305,1310,1315,1320,1325,1330,1335,1340,1345,1350,1355,1360,1365,1370,1375,1380,1385,1390,1395,1400,1405,1410,1415,1420,1425,1430,1435,1440,1445,1450,1455,1460,1465,1470,1475,1480,1485,1490,1495,1500,1505,1510,1515,1520,1525,1530,1535,1540,1545,1550,1555,1560,1565,1570,1575,1580,1585,1590,1595,1600,1605,1610,1615,1620,1625,1630,1635,1640,1645,1650,1655,1660,1665,1670,1675,1680,1685,1690,1695,1700,1705,1710,1715,1720,1725,1730,1735,1740,1745,1750,1755,1760,1765,1770,1775,1780,1785,1790,1795,1800,1805,1810,1815,1820,1825,1830,1835,1840,1845,1850,1855,1860,1865,1870,1875,1880,1885,1890,1895,1900,1905,1910,1915,1920,1925,1930,1935,1940,1945,1950,1955,1960,1965,1970,1975,1980,1985,1990,1995,2000,2005,2010,2015,2020,2025,2030,2035,2040,2045,2050,2055,2060,2065,2070,2075,2080,2085,2090,2095,2100,2105,2110,2115,2120,2125,2130,2135,2140,2145,2150,2155,2160,2165,2170,2175,2180,2185,2190,2195,2200,2205,2210,2215,2220,2225,2230,2235,2240,2245,2250,2255,2260,2265,2270,2275,2280,2285,2290,2295,2300,2305,2310,2315,2320,2325,2330,2335,2340,2345,2350,2355,2360,2365,2370,2375,2380,2385,2390,2395,2400,2405,2410,2415,2420,2425,2430,2435,2440,2445,2450,2455,2460,2465,2470,2475,2480,2485,2490,2495,2500,2505,2510,2515,2520,2525,2530,2535,2540,2545,2550,2555,2560,2565,2570,2575,2580,2585,2590,2595,2600,2605,2610,2615,2620,2625,2630,2635,2640,2645,2650,2655,2660,2665,2670,2675,2680,2685,2690,2695,2700,2705,2710,2715,2720,2725,2730,2735,2740,2745,2750,2755,2760,2765,2770,2775,2780,2785,2790,2795,2800,2805,2810,2815,2820,2825,2830,2835,2840,2845,2850,2855,2860,2865,2870,2875,2880,2885,2890,2895,2900,2905,2910,2915,2920,2925,2930,2935,2940,2945,2950,2955,2960,2965,2970,2975,2980,2985,2990,2995,3000,3005,3010,3015,3020,3025,3030,3035,3040,3045,3050,3055,3060,3065,3070,3075,3080,3085,3090,3095,3100,3105,3110,3115,3120,3125,3130,3135,3140,3145,3150,3155,3160,3165,3170,3175,3180,3185,3190,3195,3200,3205,3210,3215,3220,3225,3230,3235,3240,3245,3250,3255,3260,3265,3270,3275,3280,3285,3290,3295,3300,3305,3310,3315,3320,3325,3330,3335,3340,3345,3350,3355,3360,3365,3370,3375,3380,3385,3390,3395,3400,3405,3410,3415,3420,3425,3430,3435,3440,3445,3450,3455,3460,3465,3470,3475,3480,3485,3490,3495,3500,3505,3510,3515,3520,3525,3530,3535,3540,3545,3550,3555,3560,3565,3570,3575,3580,3585,3590,3595,3600,3605,3610,3615,3620,3625,3630,3635,3640,3645,3650,3655,3660,3665,3670,3675,3680,3685,3690,3695,3700,3705,3710,3715,3720,3725,3730,3735,3740,3745,3750,3755,3760,3765,3770,3775,3780,3785,3790,3795,3800,3805,3810,3815,3820,3825,3830,3835,3840,3845,3850,3855,3860,3865,3870,3875,3880,3885,3890,3895,3900,3905,3910,3915,3920,3925,3930,3935,3940,3945,3950,3955,3960,3965,3970,3975,3980,3985,3990,3995,4000,4005,4010,4015,4020,4025,4030,4035,4040,4045,4050,4055,4060,4065,4070,4075,4080,4085,4090,4095,4100]"
"""
    
    # 构造演示请求
    demo_request = AnalysisRequest(
        patient_info=PatientCreateRequest(
            name="演示患者",
            age=65,
            gender="MALE",
            height=170.0,
            weight=70.0
        ),
        test_type="COMPREHENSIVE",
        test_mode="UPLOAD",
        csv_data=demo_csv_data
    )
    
    try:
        # 执行演示分析
        result = await analyze_pressure_data(
            demo_request,
            get_db(),
            get_analyzer()
        )
        
        return {
            "message": "演示分析执行成功",
            "demo": True,
            "result": result
        }
        
    except Exception as e:
        return error_response(f"演示分析失败: {str(e)}")

@router.get("/history")
async def get_analysis_history(
    limit: int = 10,
    offset: int = 0,
    patient_id: Optional[int] = None,
    db: Session = Depends(get_db)
):
    """获取分析历史记录"""
    try:
        with next(db) as session:
            # 构建查询
            query = session.query(AnalysisResult).join(Test).join(Patient)
            
            if patient_id:
                query = query.filter(Patient.id == patient_id)
            
            # 获取总数
            total = query.count()
            
            # 获取分页数据
            results = query.order_by(AnalysisResult.created_at.desc()).offset(offset).limit(limit).all()
            
            # 构造响应数据
            history_data = []
            for result in results:
                test = result.test
                patient = test.patient
                
                history_data.append({
                    "analysis_id": result.id,
                    "test_id": test.id,
                    "patient_name": patient.name,
                    "patient_age": patient.age,
                    "test_type": test.test_type,
                    "overall_score": result.overall_score,
                    "risk_level": result.risk_level,
                    "confidence": result.confidence,
                    "processing_time": result.processing_time,
                    "created_at": result.created_at.isoformat()
                })
            
            return success_response({
                "history": history_data,
                "pagination": {
                    "total": total,
                    "limit": limit,
                    "offset": offset,
                    "has_more": offset + limit < total
                }
            })
            
    except Exception as e:
        logger.error(f"获取分析历史失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取分析历史失败: {str(e)}")

# 导出路由
__all__ = ["router"]