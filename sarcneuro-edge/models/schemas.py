#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SarcNeuro Edge Pydantic 数据模型
"""
from typing import List, Optional, Dict, Any, Union
from datetime import datetime
from pydantic import BaseModel, Field, validator
from enum import Enum

# 枚举类型
class GenderEnum(str, Enum):
    MALE = "MALE"
    FEMALE = "FEMALE"

class TestTypeEnum(str, Enum):
    GAIT = "GAIT"
    BALANCE = "BALANCE"
    COMPREHENSIVE = "COMPREHENSIVE"

class TestModeEnum(str, Enum):
    REALTIME = "REALTIME"
    UPLOAD = "UPLOAD"

class StatusEnum(str, Enum):
    PENDING = "PENDING"
    PROCESSING = "PROCESSING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"

class RiskLevelEnum(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"

class SyncStatusEnum(str, Enum):
    PENDING = "pending"
    SYNCED = "synced"
    FAILED = "failed"

# 基础模型
class PatientInfo(BaseModel):
    """患者信息"""
    name: str = Field(..., min_length=2, max_length=50, description="患者姓名")
    age: int = Field(..., ge=0, le=120, description="患者年龄") 
    gender: GenderEnum = Field(..., description="患者性别")
    height: Optional[float] = Field(None, ge=50, le=250, description="身高(cm)")
    weight: Optional[float] = Field(None, ge=10, le=200, description="体重(kg)")
    phone: Optional[str] = Field(None, max_length=20, description="联系电话")
    email: Optional[str] = Field(None, max_length=100, description="邮箱地址")
    medical_history: Optional[str] = Field(None, max_length=500, description="病史")
    notes: Optional[str] = Field(None, max_length=500, description="备注")

class PressurePointData(BaseModel):
    """压力数据点"""
    time: float = Field(..., description="时间戳")
    max_pressure: int = Field(..., ge=0, description="最大压力值")
    timestamp: str = Field(..., description="时间戳字符串")
    contact_area: int = Field(..., ge=0, description="接触面积")
    total_pressure: int = Field(..., ge=0, description="总压力")
    data: List[int] = Field(..., min_items=1024, max_items=1024, description="1024个压力数据点")

class AnalysisRequest(BaseModel):
    """分析请求"""
    patient_id: Optional[int] = Field(None, description="患者ID")
    patient_info: Optional[PatientInfo] = Field(None, description="患者信息")
    test_type: TestTypeEnum = Field(TestTypeEnum.COMPREHENSIVE, description="测试类型")
    test_mode: TestModeEnum = Field(TestModeEnum.UPLOAD, description="测试模式")
    csv_data: Optional[str] = Field(None, description="CSV格式的压力数据")
    pressure_data: Optional[List[PressurePointData]] = Field(None, description="压力数据点列表")
    parameters: Optional[Dict[str, Any]] = Field(default_factory=dict, description="测试参数")

class GaitAnalysisResult(BaseModel):
    """步态分析结果"""
    walking_speed: float = Field(..., description="步行速度 (m/s)")
    step_length: float = Field(..., description="步长 (cm)")
    step_width: float = Field(..., description="步宽 (cm)")
    cadence: float = Field(..., description="步频 (步/分钟)")
    stride_time: float = Field(..., description="步幅时间 (s)")
    
    # 左右脚参数
    left_step_length: Optional[float] = Field(None, description="左脚步长")
    right_step_length: Optional[float] = Field(None, description="右脚步长")
    left_cadence: Optional[float] = Field(None, description="左脚步频")
    right_cadence: Optional[float] = Field(None, description="右脚步频")
    
    # 相位参数
    stance_phase: Optional[float] = Field(None, description="支撑相")
    swing_phase: Optional[float] = Field(None, description="摆动相")
    double_support_time: Optional[float] = Field(None, description="双支撑时间")
    
    # 评估指标
    asymmetry_index: Optional[float] = Field(None, description="不对称指数")
    stability_score: Optional[float] = Field(None, description="稳定性评分")
    rhythm_regularity: Optional[float] = Field(None, description="节律规律性")
    
    # 异常标记
    speed_abnormal: bool = Field(False, description="速度异常")
    cadence_abnormal: bool = Field(False, description="步频异常")
    stance_abnormal: bool = Field(False, description="支撑相异常")
    stride_abnormal: bool = Field(False, description="步幅异常")
    swing_abnormal: bool = Field(False, description="摆动相异常")

class BalanceAnalysisResult(BaseModel):
    """平衡分析结果"""
    cop_displacement: float = Field(..., description="压力中心位移 (mm)")
    sway_area: float = Field(..., description="摆动面积 (mm²)")
    sway_velocity: float = Field(..., description="摆动速度 (mm/s)")
    stability_index: float = Field(..., description="稳定性指数")
    fall_risk_score: float = Field(..., ge=0, le=1, description="跌倒风险评分")
    
    # 方向性稳定性
    anterior_stability: Optional[float] = Field(None, description="前向稳定性")
    posterior_stability: Optional[float] = Field(None, description="后向稳定性")
    medial_stability: Optional[float] = Field(None, description="内侧稳定性")
    lateral_stability: Optional[float] = Field(None, description="外侧稳定性")

class AnalysisResult(BaseModel):
    """分析结果"""
    overall_score: float = Field(..., ge=0, le=100, description="总体评分")
    risk_level: RiskLevelEnum = Field(..., description="风险等级")
    risk_score: float = Field(..., ge=0, le=1, description="风险评分")
    confidence: float = Field(..., ge=0, le=1, description="置信度")
    interpretation: str = Field(..., description="医学解释")
    abnormalities: List[str] = Field(default_factory=list, description="异常项列表")
    recommendations: List[str] = Field(default_factory=list, description="建议列表")
    
    gait_analysis: Optional[GaitAnalysisResult] = Field(None, description="步态分析结果")
    balance_analysis: Optional[BalanceAnalysisResult] = Field(None, description="平衡分析结果")
    
    detailed_analysis: Optional[Dict[str, Any]] = Field(None, description="详细分析数据")

class AnalysisResponse(BaseModel):
    """分析响应"""
    success: bool = Field(..., description="是否成功")
    message: str = Field(..., description="响应消息")
    data: Optional[AnalysisResult] = Field(None, description="分析结果数据")
    test_id: Optional[int] = Field(None, description="测试ID")
    patient_id: Optional[int] = Field(None, description="患者ID")
    processing_time: Optional[float] = Field(None, description="处理时间(秒)")
    timestamp: datetime = Field(default_factory=datetime.now, description="响应时间戳")

class TestInfo(BaseModel):
    """测试信息"""
    id: Optional[int] = Field(None, description="测试ID") 
    patient_id: int = Field(..., description="患者ID")
    test_type: TestTypeEnum = Field(..., description="测试类型")
    test_mode: TestModeEnum = Field(..., description="测试模式")
    status: StatusEnum = Field(..., description="测试状态")
    start_time: datetime = Field(..., description="开始时间")
    end_time: Optional[datetime] = Field(None, description="结束时间")
    parameters: Optional[Dict[str, Any]] = Field(None, description="测试参数")
    notes: Optional[str] = Field(None, description="测试备注")

class PatientResponse(BaseModel):
    """患者响应"""
    id: int = Field(..., description="患者ID")
    name: str = Field(..., description="患者姓名")
    age: int = Field(..., description="患者年龄")
    gender: GenderEnum = Field(..., description="患者性别")
    height: Optional[float] = Field(None, description="身高")
    weight: Optional[float] = Field(None, description="体重")
    phone: Optional[str] = Field(None, description="联系电话")
    email: Optional[str] = Field(None, description="邮箱地址")
    created_time: datetime = Field(..., description="创建时间")
    updated_time: Optional[datetime] = Field(None, description="更新时间")
    test_count: Optional[int] = Field(None, description="测试次数")
    last_test_time: Optional[datetime] = Field(None, description="最后测试时间")

class SystemStatus(BaseModel):
    """系统状态"""
    status: str = Field(..., description="系统状态")
    version: str = Field(..., description="版本信息")
    database: str = Field(..., description="数据库状态")
    uptime: float = Field(..., description="运行时间(秒)")
    cpu_usage: Optional[float] = Field(None, description="CPU使用率")
    memory_usage: Optional[float] = Field(None, description="内存使用率")
    disk_usage: Optional[float] = Field(None, description="磁盘使用率")
    active_connections: Optional[int] = Field(None, description="活跃连接数")

class HealthResponse(BaseModel):
    """健康检查响应"""
    status: str = Field(..., description="健康状态")
    timestamp: datetime = Field(default_factory=datetime.now, description="检查时间")
    version: str = Field(..., description="服务版本")
    database: str = Field(..., description="数据库状态")
    services: Optional[Dict[str, str]] = Field(None, description="各服务状态")

# 验证器
@validator('email', pre=True, always=True)
def validate_email(cls, v):
    """验证邮箱格式"""
    if v and '@' not in v:
        raise ValueError('邮箱格式无效')
    return v

@validator('phone', pre=True, always=True) 
def validate_phone(cls, v):
    """验证电话格式"""
    if v and not v.replace('-', '').replace(' ', '').isdigit():
        raise ValueError('电话号码格式无效')
    return v

# 导出所有模型
__all__ = [
    # 枚举类型
    'GenderEnum', 'TestTypeEnum', 'TestModeEnum', 'StatusEnum', 
    'RiskLevelEnum', 'SyncStatusEnum',
    
    # 基础模型
    'PatientInfo', 'PressurePointData', 'AnalysisRequest',
    
    # 分析结果模型
    'GaitAnalysisResult', 'BalanceAnalysisResult', 'AnalysisResult', 'AnalysisResponse',
    
    # 其他响应模型
    'TestInfo', 'PatientResponse', 'SystemStatus', 'HealthResponse'
] 