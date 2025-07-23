"""
SarcNeuro Edge 数据库模型
"""
from datetime import datetime
from sqlalchemy import Column, Integer, String, Float, Text, DateTime, Boolean, JSON, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

Base = declarative_base()

class Patient(Base):
    """患者信息表"""
    __tablename__ = "patients"
    
    id = Column(Integer, primary_key=True, index=True)
    cloud_id = Column(String(50), unique=True, index=True)  # 云端同步ID
    
    # 基本信息
    name = Column(String(100), nullable=False, index=True)
    gender = Column(String(10), nullable=False)  # MALE/FEMALE
    age = Column(Integer, nullable=False)
    height = Column(Float, nullable=True)  # 身高(cm)
    weight = Column(Float, nullable=True)  # 体重(kg)
    phone = Column(String(20), nullable=True)
    email = Column(String(100), nullable=True)
    id_number = Column(String(50), nullable=True)
    medical_record_number = Column(String(50), nullable=True, index=True)
    
    # 医疗信息
    medical_history = Column(JSON, nullable=True)  # 病史
    medications = Column(JSON, nullable=True)      # 用药
    allergies = Column(JSON, nullable=True)        # 过敏
    
    # 系统信息
    is_active = Column(Boolean, default=True)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
    synced_at = Column(DateTime, nullable=True)  # 最后同步时间
    sync_status = Column(String(20), default="pending")  # pending/synced/conflict
    
    # 关系
    tests = relationship("Test", back_populates="patient", cascade="all, delete-orphan")
    reports = relationship("Report", back_populates="patient", cascade="all, delete-orphan")

class Test(Base):
    """测试记录表"""
    __tablename__ = "tests"
    
    id = Column(Integer, primary_key=True, index=True)
    cloud_id = Column(String(50), unique=True, index=True)
    
    # 关联信息
    patient_id = Column(Integer, ForeignKey("patients.id"), nullable=False, index=True)
    
    # 测试信息
    test_type = Column(String(50), nullable=False)  # STATIC/DYNAMIC/BALANCE/COMPREHENSIVE
    test_mode = Column(String(50), nullable=False)  # REAL_TIME/UPLOAD
    duration = Column(Float, nullable=True)  # 测试时长(秒)
    
    # 测试参数
    parameters = Column(JSON, nullable=True)
    environment = Column(JSON, nullable=True)
    
    # 状态
    status = Column(String(20), default="PENDING")  # PENDING/PROCESSING/COMPLETED/FAILED
    start_time = Column(DateTime, nullable=True)
    end_time = Column(DateTime, nullable=True)
    
    # 系统信息
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
    synced_at = Column(DateTime, nullable=True)
    sync_status = Column(String(20), default="pending")
    
    # 关系
    patient = relationship("Patient", back_populates="tests")
    pressure_data = relationship("PressureData", back_populates="test", cascade="all, delete-orphan")
    analysis_result = relationship("AnalysisResult", back_populates="test", uselist=False, cascade="all, delete-orphan")
    reports = relationship("Report", back_populates="test", cascade="all, delete-orphan")

class PressureData(Base):
    """压力数据表"""
    __tablename__ = "pressure_data"
    
    id = Column(Integer, primary_key=True, index=True)
    cloud_id = Column(String(50), unique=True, index=True)
    
    # 关联信息
    test_id = Column(Integer, ForeignKey("tests.id"), nullable=False, index=True)
    
    # 压力数据
    timestamp = Column(DateTime, nullable=False)
    frame_number = Column(Integer, nullable=False)
    left_foot_data = Column(JSON, nullable=True)   # 左脚压力数据 32x32
    right_foot_data = Column(JSON, nullable=True)  # 右脚压力数据 32x32
    
    # 计算数据
    max_pressure = Column(Float, nullable=True)
    total_area = Column(Float, nullable=True)
    center_of_pressure_x = Column(Float, nullable=True)
    center_of_pressure_y = Column(Float, nullable=True)
    left_foot_cop = Column(JSON, nullable=True)
    right_foot_cop = Column(JSON, nullable=True)
    
    # 系统信息
    created_at = Column(DateTime, server_default=func.now())
    synced_at = Column(DateTime, nullable=True)
    sync_status = Column(String(20), default="pending")
    
    # 关系
    test = relationship("Test", back_populates="pressure_data")

class AnalysisResult(Base):
    """分析结果表"""
    __tablename__ = "analysis_results"
    
    id = Column(Integer, primary_key=True, index=True)
    cloud_id = Column(String(50), unique=True, index=True)
    
    # 关联信息
    test_id = Column(Integer, ForeignKey("tests.id"), nullable=False, index=True)
    
    # 基础评分
    overall_score = Column(Float, nullable=False, default=0.0)
    risk_level = Column(String(20), nullable=False)  # LOW/MEDIUM/HIGH/CRITICAL
    confidence = Column(Float, nullable=True, default=0.0)
    
    # 分析结果
    interpretation = Column(Text, nullable=True)
    abnormalities = Column(JSON, nullable=True)
    recommendations = Column(JSON, nullable=True)
    detailed_analysis = Column(JSON, nullable=True)
    
    # 处理信息
    processing_time = Column(Float, nullable=True)  # 处理时间(毫秒)
    model_version = Column(String(50), nullable=True)
    quality_score = Column(Float, nullable=True)
    
    # 系统信息
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
    synced_at = Column(DateTime, nullable=True)
    sync_status = Column(String(20), default="pending")
    
    # 关系
    test = relationship("Test", back_populates="analysis_result")
    gait_metrics = relationship("GaitMetrics", back_populates="analysis_result", uselist=False, cascade="all, delete-orphan")
    balance_metrics = relationship("BalanceMetrics", back_populates="analysis_result", uselist=False, cascade="all, delete-orphan")

class GaitMetrics(Base):
    """步态指标表"""
    __tablename__ = "gait_metrics"
    
    id = Column(Integer, primary_key=True, index=True)
    analysis_result_id = Column(Integer, ForeignKey("analysis_results.id"), nullable=False, index=True)
    
    # 基础步态参数
    walking_speed = Column(Float, nullable=True)      # 步速 m/s
    step_length = Column(Float, nullable=True)        # 步长 cm
    step_width = Column(Float, nullable=True)         # 步宽 cm
    cadence = Column(Float, nullable=True)            # 步频 steps/min
    stride_time = Column(Float, nullable=True)        # 步幅时间 s
    
    # 左右脚分别参数
    left_step_length = Column(Float, nullable=True)
    right_step_length = Column(Float, nullable=True)
    left_cadence = Column(Float, nullable=True)
    right_cadence = Column(Float, nullable=True)
    left_stride_speed = Column(Float, nullable=True)
    right_stride_speed = Column(Float, nullable=True)
    left_swing_speed = Column(Float, nullable=True)
    right_swing_speed = Column(Float, nullable=True)
    
    # 相位参数
    stance_phase = Column(Float, nullable=True)         # 站立相 %
    swing_phase = Column(Float, nullable=True)          # 摆动相 %
    left_stance_phase = Column(Float, nullable=True)
    right_stance_phase = Column(Float, nullable=True)
    left_swing_phase = Column(Float, nullable=True)
    right_swing_phase = Column(Float, nullable=True)
    double_support_time = Column(Float, nullable=True)  # 双支撑相 %
    left_double_support_time = Column(Float, nullable=True)
    right_double_support_time = Column(Float, nullable=True)
    
    # 步高参数
    left_step_height = Column(Float, nullable=True)
    right_step_height = Column(Float, nullable=True)
    
    # 转身时间
    turn_time = Column(Float, nullable=True)
    
    # 评估指标
    asymmetry_index = Column(Float, nullable=True)      # 不对称指数
    stability_score = Column(Float, nullable=True)      # 稳定性评分
    rhythm_regularity = Column(Float, nullable=True)    # 节律规律性
    
    # 异常标记
    speed_abnormal = Column(Boolean, default=False)
    cadence_abnormal = Column(Boolean, default=False)
    stance_abnormal = Column(Boolean, default=False)
    stride_abnormal = Column(Boolean, default=False)
    swing_abnormal = Column(Boolean, default=False)
    
    # 系统信息
    created_at = Column(DateTime, server_default=func.now())
    
    # 关系
    analysis_result = relationship("AnalysisResult", back_populates="gait_metrics")

class BalanceMetrics(Base):
    """平衡指标表"""
    __tablename__ = "balance_metrics"
    
    id = Column(Integer, primary_key=True, index=True)
    analysis_result_id = Column(Integer, ForeignKey("analysis_results.id"), nullable=False, index=True)
    
    # 压力中心指标
    cop_displacement = Column(Float, nullable=True)     # 压力中心位移 mm
    sway_area = Column(Float, nullable=True)           # 摆动面积 mm²
    sway_velocity = Column(Float, nullable=True)       # 摆动速度 mm/s
    stability_index = Column(Float, nullable=True)     # 稳定性指数
    fall_risk_score = Column(Float, nullable=True)     # 跌倒风险评分
    
    # 方向性稳定指标
    anterior_stability = Column(Float, nullable=True)   # 前向稳定性
    posterior_stability = Column(Float, nullable=True)  # 后向稳定性
    medial_stability = Column(Float, nullable=True)     # 内侧稳定性
    lateral_stability = Column(Float, nullable=True)    # 外侧稳定性
    
    # 系统信息
    created_at = Column(DateTime, server_default=func.now())
    
    # 关系
    analysis_result = relationship("AnalysisResult", back_populates="balance_metrics")

class Report(Base):
    """报告表"""
    __tablename__ = "reports"
    
    id = Column(Integer, primary_key=True, index=True)
    cloud_id = Column(String(50), unique=True, index=True)
    
    # 关联信息
    patient_id = Column(Integer, ForeignKey("patients.id"), nullable=False, index=True)
    test_id = Column(Integer, ForeignKey("tests.id"), nullable=False, index=True)
    
    # 报告信息
    title = Column(String(200), nullable=False)
    report_number = Column(String(50), unique=True, nullable=False, index=True)
    status = Column(String(20), default="DRAFT")  # DRAFT/PENDING/PUBLISHED
    
    # 内容
    summary = Column(Text, nullable=True)
    content = Column(JSON, nullable=True)
    recommendations = Column(JSON, nullable=True)
    template = Column(String(100), default="standard_medical_report")
    
    # 版本管理
    version = Column(Integer, default=1)
    is_published = Column(Boolean, default=False)
    published_at = Column(DateTime, nullable=True)
    
    # 系统信息
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
    synced_at = Column(DateTime, nullable=True)
    sync_status = Column(String(20), default="pending")
    
    # 关系
    patient = relationship("Patient", back_populates="reports")
    test = relationship("Test", back_populates="reports")

class SyncLog(Base):
    """同步日志表"""
    __tablename__ = "sync_logs"
    
    id = Column(Integer, primary_key=True, index=True)
    
    # 同步信息
    sync_type = Column(String(50), nullable=False)  # patients/tests/reports/models
    operation = Column(String(20), nullable=False)  # upload/download/update
    status = Column(String(20), nullable=False)     # success/failed/partial
    
    # 统计信息
    total_records = Column(Integer, default=0)
    synced_records = Column(Integer, default=0)
    failed_records = Column(Integer, default=0)
    
    # 详细信息
    details = Column(JSON, nullable=True)
    error_message = Column(Text, nullable=True)
    
    # 时间信息
    start_time = Column(DateTime, nullable=False)
    end_time = Column(DateTime, nullable=True)
    duration = Column(Float, nullable=True)  # 持续时间(秒)
    
    # 系统信息
    created_at = Column(DateTime, server_default=func.now())

class ModelInfo(Base):
    """模型信息表"""
    __tablename__ = "model_info"
    
    id = Column(Integer, primary_key=True, index=True)
    
    # 模型信息
    name = Column(String(100), nullable=False, unique=True, index=True)
    version = Column(String(50), nullable=False)
    file_path = Column(String(500), nullable=False)
    file_size = Column(Integer, nullable=True)
    
    # 模型详情
    description = Column(Text, nullable=True)
    model_type = Column(String(50), nullable=True)  # gait/balance/sarcopenia
    performance_metrics = Column(JSON, nullable=True)
    
    # 状态
    is_active = Column(Boolean, default=True)
    is_downloaded = Column(Boolean, default=False)
    
    # 时间信息
    released_at = Column(DateTime, nullable=True)
    downloaded_at = Column(DateTime, nullable=True)
    last_used_at = Column(DateTime, nullable=True)
    
    # 系统信息
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

class SystemStatus(Base):
    """系统状态表"""
    __tablename__ = "system_status"
    
    id = Column(Integer, primary_key=True, index=True)
    
    # 系统信息
    app_version = Column(String(50), nullable=False)
    edge_device_id = Column(String(100), unique=True, nullable=False)
    
    # 运行状态
    status = Column(String(20), default="running")  # running/stopped/error
    last_heartbeat = Column(DateTime, server_default=func.now())
    
    # 同步状态
    last_sync_time = Column(DateTime, nullable=True)
    sync_enabled = Column(Boolean, default=True)
    cloud_connected = Column(Boolean, default=False)
    
    # 系统统计
    total_patients = Column(Integer, default=0)
    total_tests = Column(Integer, default=0)
    total_reports = Column(Integer, default=0)
    pending_sync_count = Column(Integer, default=0)
    
    # 资源状态
    cpu_usage = Column(Float, nullable=True)
    memory_usage = Column(Float, nullable=True)
    disk_usage = Column(Float, nullable=True)
    
    # 系统信息
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

# 导出所有模型
__all__ = [
    "Base",
    "Patient",
    "Test", 
    "PressureData",
    "AnalysisResult",
    "GaitMetrics",
    "BalanceMetrics",
    "Report",
    "SyncLog",
    "ModelInfo",
    "SystemStatus"
]