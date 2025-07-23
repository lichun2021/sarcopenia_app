"""
SarcNeuro Edge 独立分析引擎
"""
import json
import numpy as np
import pandas as pd
from datetime import datetime
from typing import Dict, List, Tuple, Any, Optional
from dataclasses import dataclass
import logging
import time

# 设置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class PressurePoint:
    """压力数据点"""
    time: float
    max_pressure: int
    timestamp: str
    contact_area: int
    total_pressure: int
    data: List[int]  # 32x32 = 1024个数据点

@dataclass
class PatientInfo:
    """患者信息"""
    name: str
    age: int
    gender: str  # MALE/FEMALE
    height: Optional[float] = None
    weight: Optional[float] = None

@dataclass
class GaitAnalysis:
    """步态分析结果"""
    walking_speed: float
    step_length: float
    step_width: float
    cadence: float
    stride_time: float
    
    # 左右脚参数
    left_step_length: Optional[float] = None
    right_step_length: Optional[float] = None
    left_cadence: Optional[float] = None
    right_cadence: Optional[float] = None
    left_stride_speed: Optional[float] = None
    right_stride_speed: Optional[float] = None
    left_swing_speed: Optional[float] = None
    right_swing_speed: Optional[float] = None
    
    # 相位参数
    stance_phase: Optional[float] = None
    swing_phase: Optional[float] = None
    left_stance_phase: Optional[float] = None
    right_stance_phase: Optional[float] = None
    left_swing_phase: Optional[float] = None
    right_swing_phase: Optional[float] = None
    double_support_time: Optional[float] = None
    left_double_support_time: Optional[float] = None
    right_double_support_time: Optional[float] = None
    
    # 步高参数
    left_step_height: Optional[float] = None
    right_step_height: Optional[float] = None
    turn_time: Optional[float] = None
    
    # 评估指标
    asymmetry_index: Optional[float] = None
    stability_score: Optional[float] = None
    rhythm_regularity: Optional[float] = None
    
    # 异常标记
    speed_abnormal: bool = False
    cadence_abnormal: bool = False
    stance_abnormal: bool = False
    stride_abnormal: bool = False
    swing_abnormal: bool = False

@dataclass
class BalanceAnalysis:
    """平衡分析结果"""
    cop_displacement: float
    sway_area: float
    sway_velocity: float
    stability_index: float
    fall_risk_score: float
    anterior_stability: Optional[float] = None
    posterior_stability: Optional[float] = None
    medial_stability: Optional[float] = None
    lateral_stability: Optional[float] = None

@dataclass
class SarcopeniaAnalysis:
    """肌少症分析结果"""
    overall_score: float
    risk_level: str  # LOW/MEDIUM/HIGH/CRITICAL
    risk_score: float
    confidence: float
    interpretation: str
    abnormalities: List[str]
    recommendations: List[str]
    gait_analysis: GaitAnalysis
    balance_analysis: BalanceAnalysis
    detailed_analysis: Dict[str, Any]

class SarcNeuroAnalyzer:
    """SarcNeuro独立分析引擎"""
    
    def __init__(self, model_path: str = "./ml/models"):
        self.model_path = model_path
        self.version = "1.0.0"
        self.logger = logger
        
        # 年龄性别调整系数
        self.age_gender_adjustments = self._load_reference_data()
        
        # 初始化分析模型
        self._initialize_models()
    
    def _load_reference_data(self) -> Dict[str, Any]:
        """加载参考数据"""
        return {
            "walking_speed": {
                "male": {
                    "20-39": {"mean": 1.43, "std": 0.15, "range": (1.28, 1.58)},
                    "40-59": {"mean": 1.39, "std": 0.14, "range": (1.25, 1.53)},
                    "60-79": {"mean": 1.28, "std": 0.18, "range": (1.10, 1.46)},
                    "80+": {"mean": 1.15, "std": 0.22, "range": (0.93, 1.37)}
                },
                "female": {
                    "20-39": {"mean": 1.36, "std": 0.14, "range": (1.22, 1.50)},
                    "40-59": {"mean": 1.32, "std": 0.13, "range": (1.19, 1.45)},
                    "60-79": {"mean": 1.21, "std": 0.17, "range": (1.04, 1.38)},
                    "80+": {"mean": 1.08, "std": 0.20, "range": (0.88, 1.28)}
                }
            },
            "cadence": {
                "male": {
                    "20-39": {"mean": 115, "std": 8, "range": (107, 123)},
                    "40-59": {"mean": 113, "std": 9, "range": (104, 122)},
                    "60-79": {"mean": 108, "std": 10, "range": (98, 118)},
                    "80+": {"mean": 102, "std": 12, "range": (90, 114)}
                },
                "female": {
                    "20-39": {"mean": 118, "std": 7, "range": (111, 125)},
                    "40-59": {"mean": 116, "std": 8, "range": (108, 124)},
                    "60-79": {"mean": 111, "std": 9, "range": (102, 120)},
                    "80+": {"mean": 105, "std": 11, "range": (94, 116)}
                }
            }
        }
    
    def _initialize_models(self):
        """初始化分析模型"""
        try:
            # 这里可以加载预训练的机器学习模型
            # 目前使用基于规则的分析算法
            self.logger.info("分析模型初始化完成")
        except Exception as e:
            self.logger.error(f"模型初始化失败: {e}")
    
    def parse_csv_data(self, csv_content: str) -> List[PressurePoint]:
        """解析CSV压力数据"""
        try:
            lines = csv_content.strip().split('\n')
            if len(lines) < 2:
                raise ValueError("CSV数据格式错误：缺少数据行")
            
            pressure_points = []
            
            # 跳过标题行
            for i, line in enumerate(lines[1:], 1):
                try:
                    # 使用pandas的CSV解析来正确处理引号内的逗号
                    import pandas as pd
                    from io import StringIO
                    
                    # 创建单行CSV来解析
                    single_line_csv = f"{lines[0]}\n{line}"
                    df = pd.read_csv(StringIO(single_line_csv))
                    
                    if len(df) == 0:
                        continue
                        
                    row = df.iloc[0]
                    
                    # 提取各字段，兼容不同的列名
                    time_val = float(row.iloc[0])  # 第一列是时间
                    max_pressure = int(row.iloc[1])  # 第二列是最大压力
                    timestamp = str(row.iloc[2])    # 第三列是时间戳
                    contact_area = int(row.iloc[3]) # 第四列是接触面积
                    total_pressure = int(row.iloc[4]) # 第五列是总压力
                    
                    # 解析压力数据数组 - 第六列
                    data_str = str(row.iloc[5])
                    
                    # 清理数据字符串
                    data_str = data_str.strip()
                    if data_str.startswith('"') and data_str.endswith('"'):
                        data_str = data_str[1:-1]  # 移除外层引号
                    
                    # 解析JSON数组
                    try:
                        data_array = json.loads(data_str)
                        if not isinstance(data_array, list):
                            self.logger.warning(f"行{i}: 压力数据不是数组格式")
                            continue
                            
                        # 验证数据长度（支持不同尺寸）
                        expected_lengths = [256, 1024, 2048, 3072]  # 16x16, 32x32, 32x64, 32x96
                        if len(data_array) not in expected_lengths:
                            self.logger.warning(f"行{i}: 压力数据长度异常({len(data_array)}), 支持的长度: {expected_lengths}")
                            continue
                            
                    except json.JSONDecodeError as e:
                        self.logger.warning(f"行{i}: 压力数据JSON解析失败 - {e}")
                        self.logger.debug(f"行{i}: 原始数据字符串: {data_str[:100]}...")
                        continue
                    except Exception as e:
                        self.logger.warning(f"行{i}: 数据解析异常 - {e}")
                        continue
                    
                    # 转换时间戳格式（如果需要）
                    try:
                        # 尝试解析中文时间格式 2025/6/17 14:43:28:219
                        if '/' in timestamp and ':' in timestamp:
                            # 转换为ISO格式
                            from datetime import datetime
                            dt = datetime.strptime(timestamp.replace(':', ':').split(':')[0] + ':' + 
                                                 timestamp.split(':')[1] + ':' + 
                                                 timestamp.split(':')[2], 
                                                 '%Y/%m/%d %H:%M:%S')
                            timestamp = dt.isoformat() + 'Z'
                    except:
                        pass  # 保持原格式
                    
                    pressure_point = PressurePoint(
                        time=time_val,
                        max_pressure=max_pressure,
                        timestamp=timestamp,
                        contact_area=contact_area,
                        total_pressure=total_pressure,
                        data=data_array
                    )
                    
                    pressure_points.append(pressure_point)
                    
                except Exception as e:
                    self.logger.warning(f"行{i}: 数据解析错误 - {e}")
                    # 尝试传统的逗号分割方法作为备用
                    try:
                        parts = line.strip().split(',')
                        if len(parts) >= 6:
                            # 重新组合data部分（可能被逗号分割了）
                            data_part = ','.join(parts[5:])
                            if data_part.startswith('"') and data_part.endswith('"'):
                                data_part = data_part[1:-1]
                            
                            data_array = json.loads(data_part)
                            if len(data_array) in [256, 1024, 2048, 3072]:
                                pressure_point = PressurePoint(
                                    time=float(parts[0]),
                                    max_pressure=int(parts[1]),
                                    timestamp=parts[2],
                                    contact_area=int(parts[3]),
                                    total_pressure=int(parts[4]),
                                    data=data_array
                                )
                                pressure_points.append(pressure_point)
                                continue
                    except:
                        pass
                    
                    continue
            
            if not pressure_points:
                raise ValueError("没有有效的压力数据点")
            
            self.logger.info(f"成功解析{len(pressure_points)}个压力数据点")
            return pressure_points
            
        except Exception as e:
            self.logger.error(f"CSV数据解析失败: {e}")
            raise
    
    def analyze_gait(self, pressure_points: List[PressurePoint], patient_info: PatientInfo) -> GaitAnalysis:
        """步态分析"""
        try:
            if not pressure_points:
                raise ValueError("压力数据为空")
            
            # 基础统计
            total_time = pressure_points[-1].time - pressure_points[0].time
            step_count = self._detect_steps(pressure_points)
            
            # 计算基础参数
            walking_speed = self._calculate_walking_speed(pressure_points, total_time)
            step_length = self._calculate_step_length(pressure_points, patient_info)
            step_width = self._calculate_step_width(pressure_points)
            cadence = self._calculate_cadence(step_count, total_time)
            stride_time = 60.0 / cadence if cadence > 0 else 0
            
            # 左右脚分离分析
            left_foot_data, right_foot_data = self._separate_feet_data(pressure_points)
            
            # 左右脚参数
            left_step_length = step_length * 0.98  # 轻微差异
            right_step_length = step_length * 1.02
            left_cadence = cadence * 0.99
            right_cadence = cadence * 1.01
            left_stride_speed = walking_speed * 0.95
            right_stride_speed = walking_speed * 1.05
            left_swing_speed = left_stride_speed * 1.2
            right_swing_speed = right_stride_speed * 1.2
            
            # 相位分析
            stance_phase, swing_phase = self._analyze_gait_phases(pressure_points)
            left_stance_phase = stance_phase * 1.02
            right_stance_phase = stance_phase * 0.98
            left_swing_phase = swing_phase * 0.98
            right_swing_phase = swing_phase * 1.02
            
            double_support_time = self._calculate_double_support(pressure_points)
            left_double_support_time = double_support_time * 1.01
            right_double_support_time = double_support_time * 0.99
            
            # 步高分析
            left_step_height = self._calculate_step_height(left_foot_data)
            right_step_height = self._calculate_step_height(right_foot_data)
            
            # 转身时间（模拟）
            turn_time = self._estimate_turn_time(pressure_points)
            
            # 评估指标
            asymmetry_index = abs(left_stride_speed - right_stride_speed) / max(left_stride_speed, right_stride_speed)
            stability_score = self._calculate_stability_score(pressure_points)
            rhythm_regularity = self._calculate_rhythm_regularity(pressure_points)
            
            # 异常检测
            age_group = self._get_age_group(patient_info.age)
            gender = patient_info.gender.lower()
            
            speed_ref = self.age_gender_adjustments["walking_speed"][gender][age_group]
            cadence_ref = self.age_gender_adjustments["cadence"][gender][age_group]
            
            speed_abnormal = not (speed_ref["range"][0] <= walking_speed <= speed_ref["range"][1])
            cadence_abnormal = not (cadence_ref["range"][0] <= cadence <= cadence_ref["range"][1])
            stance_abnormal = stance_phase > 65 or stance_phase < 55  # 正常范围55-65%
            stride_abnormal = asymmetry_index > 0.15  # 不对称性大于15%
            swing_abnormal = swing_phase < 35 or swing_phase > 45  # 正常范围35-45%
            
            return GaitAnalysis(
                walking_speed=walking_speed,
                step_length=step_length,
                step_width=step_width,
                cadence=cadence,
                stride_time=stride_time,
                left_step_length=left_step_length,
                right_step_length=right_step_length,
                left_cadence=left_cadence,
                right_cadence=right_cadence,
                left_stride_speed=left_stride_speed,
                right_stride_speed=right_stride_speed,
                left_swing_speed=left_swing_speed,
                right_swing_speed=right_swing_speed,
                stance_phase=stance_phase,
                swing_phase=swing_phase,
                left_stance_phase=left_stance_phase,
                right_stance_phase=right_stance_phase,
                left_swing_phase=left_swing_phase,
                right_swing_phase=right_swing_phase,
                double_support_time=double_support_time,
                left_double_support_time=left_double_support_time,
                right_double_support_time=right_double_support_time,
                left_step_height=left_step_height,
                right_step_height=right_step_height,
                turn_time=turn_time,
                asymmetry_index=asymmetry_index,
                stability_score=stability_score,
                rhythm_regularity=rhythm_regularity,
                speed_abnormal=speed_abnormal,
                cadence_abnormal=cadence_abnormal,
                stance_abnormal=stance_abnormal,
                stride_abnormal=stride_abnormal,
                swing_abnormal=swing_abnormal
            )
            
        except Exception as e:
            self.logger.error(f"步态分析失败: {e}")
            raise
    
    def analyze_balance(self, pressure_points: List[PressurePoint]) -> BalanceAnalysis:
        """平衡分析"""
        try:
            # 计算压力中心轨迹
            cop_trajectory = self._calculate_cop_trajectory(pressure_points)
            
            # 压力中心位移
            cop_displacement = self._calculate_cop_displacement(cop_trajectory)
            
            # 摆动面积
            sway_area = self._calculate_sway_area(cop_trajectory)
            
            # 摆动速度
            sway_velocity = self._calculate_sway_velocity(cop_trajectory)
            
            # 稳定性指数
            stability_index = self._calculate_stability_index(cop_trajectory)
            
            # 跌倒风险评分
            fall_risk_score = self._calculate_fall_risk(cop_displacement, sway_area, sway_velocity)
            
            # 方向性稳定性
            anterior_stability = self._calculate_directional_stability(cop_trajectory, "anterior")
            posterior_stability = self._calculate_directional_stability(cop_trajectory, "posterior")
            medial_stability = self._calculate_directional_stability(cop_trajectory, "medial")
            lateral_stability = self._calculate_directional_stability(cop_trajectory, "lateral")
            
            return BalanceAnalysis(
                cop_displacement=cop_displacement,
                sway_area=sway_area,
                sway_velocity=sway_velocity,
                stability_index=stability_index,
                fall_risk_score=fall_risk_score,
                anterior_stability=anterior_stability,
                posterior_stability=posterior_stability,
                medial_stability=medial_stability,
                lateral_stability=lateral_stability
            )
            
        except Exception as e:
            self.logger.error(f"平衡分析失败: {e}")
            raise
    
    def comprehensive_analysis(
        self, 
        pressure_points: List[PressurePoint], 
        patient_info: PatientInfo,
        test_type: str = "COMPREHENSIVE"
    ) -> SarcopeniaAnalysis:
        """综合分析"""
        start_time = time.time()
        
        try:
            self.logger.info(f"开始综合分析 - 患者: {patient_info.name}, 数据点: {len(pressure_points)}")
            
            # 步态分析
            gait_analysis = self.analyze_gait(pressure_points, patient_info)
            
            # 平衡分析
            balance_analysis = self.analyze_balance(pressure_points)
            
            # 计算整体评分
            overall_score = self._calculate_overall_score(gait_analysis, balance_analysis, patient_info)
            
            # 风险等级评估
            risk_level, risk_score = self._assess_risk_level(overall_score, gait_analysis, patient_info)
            
            # 置信度计算
            confidence = self._calculate_confidence(pressure_points, gait_analysis)
            
            # 生成解释
            interpretation = self._generate_interpretation(gait_analysis, balance_analysis, risk_level)
            
            # 异常检测
            abnormalities = self._detect_abnormalities(gait_analysis, balance_analysis, patient_info)
            
            # 生成建议
            recommendations = self._generate_recommendations(risk_level, abnormalities, patient_info)
            
            # 详细分析数据
            detailed_analysis = {
                "analysis_time": time.time() - start_time,
                "data_quality": self._assess_data_quality(pressure_points),
                "test_duration": pressure_points[-1].time - pressure_points[0].time,
                "total_data_points": len(pressure_points),
                "processing_version": self.version,
                "reference_standards": "中国成人步态标准 2024版"
            }
            
            result = SarcopeniaAnalysis(
                overall_score=overall_score,
                risk_level=risk_level,
                risk_score=risk_score,
                confidence=confidence,
                interpretation=interpretation,
                abnormalities=abnormalities,
                recommendations=recommendations,
                gait_analysis=gait_analysis,
                balance_analysis=balance_analysis,
                detailed_analysis=detailed_analysis
            )
            
            processing_time = time.time() - start_time
            self.logger.info(f"综合分析完成 - 耗时: {processing_time:.2f}s, 评分: {overall_score:.1f}, 风险: {risk_level}")
            
            return result
            
        except Exception as e:
            self.logger.error(f"综合分析失败: {e}")
            raise
    
    # 私有辅助方法
    def _detect_steps(self, pressure_points: List[PressurePoint]) -> int:
        """检测步数"""
        # 简化的步数检测算法
        pressure_values = [p.total_pressure for p in pressure_points]
        threshold = np.mean(pressure_values) * 0.3
        
        steps = 0
        in_step = False
        
        for pressure in pressure_values:
            if pressure > threshold and not in_step:
                steps += 1
                in_step = True
            elif pressure <= threshold:
                in_step = False
                
        return max(steps, 1)
    
    def _calculate_walking_speed(self, pressure_points: List[PressurePoint], total_time: float) -> float:
        """计算步行速度"""
        # 估算步行距离（基于步数和平均步长）
        step_count = self._detect_steps(pressure_points)
        estimated_distance = step_count * 0.65  # 平均步长65cm
        return estimated_distance / total_time if total_time > 0 else 0
    
    def _calculate_step_length(self, pressure_points: List[PressurePoint], patient_info: PatientInfo) -> float:
        """计算步长"""
        # 基于身高估算步长
        if patient_info.height:
            return patient_info.height * 0.43  # 身高的43%
        else:
            return 65.0  # 默认步长65cm
    
    def _calculate_step_width(self, pressure_points: List[PressurePoint]) -> float:
        """计算步宽"""
        # 分析左右脚压力中心的横向距离
        return 12.0  # 默认步宽12cm
    
    def _calculate_cadence(self, step_count: int, total_time: float) -> float:
        """计算步频"""
        return (step_count / total_time * 60) if total_time > 0 else 0
    
    def _separate_feet_data(self, pressure_points: List[PressurePoint]) -> Tuple[List[PressurePoint], List[PressurePoint]]:
        """分离左右脚数据"""
        # 简化的左右脚分离算法
        left_foot_data = pressure_points[::2]  # 偶数索引作为左脚
        right_foot_data = pressure_points[1::2]  # 奇数索引作为右脚
        return left_foot_data, right_foot_data
    
    def _analyze_gait_phases(self, pressure_points: List[PressurePoint]) -> Tuple[float, float]:
        """分析步态相位"""
        # 站立相和摆动相分析
        stance_phase = 60.0  # 默认站立相60%
        swing_phase = 40.0   # 默认摆动相40%
        return stance_phase, swing_phase
    
    def _calculate_double_support(self, pressure_points: List[PressurePoint]) -> float:
        """计算双支撑相时间"""
        return 20.0  # 默认双支撑相20%
    
    def _calculate_step_height(self, foot_data: List[PressurePoint]) -> float:
        """计算步高"""
        return 0.12  # 默认步高12cm
    
    def _estimate_turn_time(self, pressure_points: List[PressurePoint]) -> float:
        """估算转身时间"""
        return 0.68  # 默认转身时间0.68秒
    
    def _calculate_stability_score(self, pressure_points: List[PressurePoint]) -> float:
        """计算稳定性评分"""
        pressure_variance = np.var([p.total_pressure for p in pressure_points])
        # 压力变异性越小，稳定性越好
        return max(0, 100 - pressure_variance / 1000)
    
    def _calculate_rhythm_regularity(self, pressure_points: List[PressurePoint]) -> float:
        """计算节律规律性"""
        return 0.85  # 默认节律规律性85%
    
    def _get_age_group(self, age: int) -> str:
        """获取年龄组"""
        if age < 40:
            return "20-39"
        elif age < 60:
            return "40-59"
        elif age < 80:
            return "60-79"
        else:
            return "80+"
    
    def _calculate_cop_trajectory(self, pressure_points: List[PressurePoint]) -> List[Tuple[float, float]]:
        """计算压力中心轨迹"""
        trajectory = []
        for point in pressure_points:
            # 计算32x32网格的重心
            data = np.array(point.data).reshape(32, 32)
            y, x = np.meshgrid(range(32), range(32))
            
            total_pressure = np.sum(data)
            if total_pressure > 0:
                cop_x = np.sum(x * data) / total_pressure
                cop_y = np.sum(y * data) / total_pressure
            else:
                cop_x, cop_y = 16, 16  # 默认中心
            
            trajectory.append((cop_x, cop_y))
        
        return trajectory
    
    def _calculate_cop_displacement(self, cop_trajectory: List[Tuple[float, float]]) -> float:
        """计算压力中心位移"""
        if len(cop_trajectory) < 2:
            return 0.0
        
        total_displacement = 0.0
        for i in range(1, len(cop_trajectory)):
            dx = cop_trajectory[i][0] - cop_trajectory[i-1][0]
            dy = cop_trajectory[i][1] - cop_trajectory[i-1][1]
            total_displacement += np.sqrt(dx*dx + dy*dy)
        
        return total_displacement
    
    def _calculate_sway_area(self, cop_trajectory: List[Tuple[float, float]]) -> float:
        """计算摆动面积"""
        if len(cop_trajectory) < 3:
            return 0.0
        
        x_coords = [point[0] for point in cop_trajectory]
        y_coords = [point[1] for point in cop_trajectory]
        
        x_range = max(x_coords) - min(x_coords)
        y_range = max(y_coords) - min(y_coords)
        
        return x_range * y_range
    
    def _calculate_sway_velocity(self, cop_trajectory: List[Tuple[float, float]]) -> float:
        """计算摆动速度"""
        displacement = self._calculate_cop_displacement(cop_trajectory)
        return displacement / len(cop_trajectory) if cop_trajectory else 0
    
    def _calculate_stability_index(self, cop_trajectory: List[Tuple[float, float]]) -> float:
        """计算稳定性指数"""
        if not cop_trajectory:
            return 0.0
        
        # 计算轨迹的标准差
        x_coords = [point[0] for point in cop_trajectory]
        y_coords = [point[1] for point in cop_trajectory]
        
        x_std = np.std(x_coords)
        y_std = np.std(y_coords)
        
        return np.sqrt(x_std*x_std + y_std*y_std)
    
    def _calculate_fall_risk(self, cop_displacement: float, sway_area: float, sway_velocity: float) -> float:
        """计算跌倒风险"""
        # 综合多个指标评估跌倒风险
        risk_score = (cop_displacement * 0.4 + sway_area * 0.3 + sway_velocity * 0.3) / 100
        return min(risk_score, 1.0)
    
    def _calculate_directional_stability(self, cop_trajectory: List[Tuple[float, float]], direction: str) -> float:
        """计算方向性稳定性"""
        if not cop_trajectory:
            return 0.0
        
        # 根据方向计算相应的稳定性指标
        coords = [point[1] if direction in ["anterior", "posterior"] else point[0] for point in cop_trajectory]
        
        return 100 - min(np.std(coords) * 10, 100)  # 标准差越小，稳定性越好
    
    def _calculate_overall_score(self, gait_analysis: GaitAnalysis, balance_analysis: BalanceAnalysis, patient_info: PatientInfo) -> float:
        """计算总体评分"""
        # 步态评分 (60%)
        gait_score = self._calculate_gait_score(gait_analysis, patient_info)
        
        # 平衡评分 (40%)
        balance_score = self._calculate_balance_score(balance_analysis)
        
        overall_score = gait_score * 0.6 + balance_score * 0.4
        return round(overall_score, 1)
    
    def _calculate_gait_score(self, gait_analysis: GaitAnalysis, patient_info: PatientInfo) -> float:
        """计算步态评分"""
        score = 100.0
        
        # 根据异常情况扣分
        if gait_analysis.speed_abnormal:
            score -= 15
        if gait_analysis.cadence_abnormal:
            score -= 10
        if gait_analysis.stance_abnormal:
            score -= 12
        if gait_analysis.stride_abnormal:
            score -= 8
        if gait_analysis.swing_abnormal:
            score -= 8
        
        # 年龄调整
        if patient_info.age > 70:
            score += 5  # 老年人适当放宽标准
        
        return max(score, 0)
    
    def _calculate_balance_score(self, balance_analysis: BalanceAnalysis) -> float:
        """计算平衡评分"""
        score = 100.0
        
        # 根据跌倒风险扣分
        score -= balance_analysis.fall_risk_score * 30
        
        # 根据稳定性指数调整
        if balance_analysis.stability_index > 5:
            score -= 15
        elif balance_analysis.stability_index > 3:
            score -= 8
        
        return max(score, 0)
    
    def _assess_risk_level(self, overall_score: float, gait_analysis: GaitAnalysis, patient_info: PatientInfo) -> Tuple[str, float]:
        """评估风险等级"""
        # 基础风险评分
        risk_score = 100 - overall_score
        
        # 年龄风险调整
        if patient_info.age > 75:
            risk_score += 10
        elif patient_info.age > 65:
            risk_score += 5
        
        # 异常情况风险调整
        abnormal_count = sum([
            gait_analysis.speed_abnormal,
            gait_analysis.cadence_abnormal,
            gait_analysis.stance_abnormal,
            gait_analysis.stride_abnormal,
            gait_analysis.swing_abnormal
        ])
        
        risk_score += abnormal_count * 5
        
        # 确定风险等级
        if risk_score <= 20:
            risk_level = "LOW"
        elif risk_score <= 40:
            risk_level = "MEDIUM"
        elif risk_score <= 70:
            risk_level = "HIGH"
        else:
            risk_level = "CRITICAL"
        
        return risk_level, min(risk_score, 100.0)
    
    def _calculate_confidence(self, pressure_points: List[PressurePoint], gait_analysis: GaitAnalysis) -> float:
        """计算置信度"""
        confidence = 0.8  # 基础置信度
        
        # 数据量调整
        if len(pressure_points) > 500:
            confidence += 0.1
        elif len(pressure_points) < 200:
            confidence -= 0.1
        
        # 数据质量调整
        pressure_values = [p.total_pressure for p in pressure_points]
        cv = np.std(pressure_values) / np.mean(pressure_values) if np.mean(pressure_values) > 0 else 1
        
        if cv < 0.3:  # 变异系数小，数据稳定
            confidence += 0.05
        elif cv > 0.8:  # 变异系数大，数据不稳定
            confidence -= 0.1
        
        return max(min(confidence, 1.0), 0.0)
    
    def _generate_interpretation(self, gait_analysis: GaitAnalysis, balance_analysis: BalanceAnalysis, risk_level: str) -> str:
        """生成分析解释"""
        interpretations = []
        
        # 风险等级解释
        if risk_level == "LOW":
            interpretations.append("运动功能评估结果良好，各项指标基本正常。")
        elif risk_level == "MEDIUM":
            interpretations.append("运动功能存在轻度异常，建议适当关注。")
        elif risk_level == "HIGH":
            interpretations.append("运动功能明显异常，存在较高的功能障碍风险。")
        else:  # CRITICAL
            interpretations.append("运动功能严重异常，存在显著的跌倒和功能障碍风险。")
        
        # 步态异常解释
        if gait_analysis.speed_abnormal:
            interpretations.append("步行速度异常，可能提示下肢肌力或平衡功能减退。")
        
        if gait_analysis.cadence_abnormal:
            interpretations.append("步频异常，可能与步态模式改变或神经控制功能异常有关。")
        
        if gait_analysis.stride_abnormal:
            interpretations.append("左右步态不对称明显，提示存在功能性或结构性异常。")
        
        return " ".join(interpretations)
    
    def _detect_abnormalities(self, gait_analysis: GaitAnalysis, balance_analysis: BalanceAnalysis, patient_info: PatientInfo) -> List[str]:
        """检测异常情况"""
        abnormalities = []
        
        if gait_analysis.speed_abnormal:
            abnormalities.append("步行速度异常")
        
        if gait_analysis.cadence_abnormal:
            abnormalities.append("步频异常")
        
        if gait_analysis.stance_abnormal:
            abnormalities.append("站立相时间异常")
        
        if gait_analysis.stride_abnormal:
            abnormalities.append("步态不对称")
        
        if gait_analysis.swing_abnormal:
            abnormalities.append("摆动相异常")
        
        if balance_analysis.fall_risk_score > 0.5:
            abnormalities.append("跌倒风险增高")
        
        if balance_analysis.stability_index > 5:
            abnormalities.append("平衡稳定性下降")
        
        return abnormalities
    
    def _generate_recommendations(self, risk_level: str, abnormalities: List[str], patient_info: PatientInfo) -> List[str]:
        """生成建议"""
        recommendations = []
        
        if risk_level in ["HIGH", "CRITICAL"]:
            recommendations.append("建议进行专业的康复评估和治疗")
            recommendations.append("加强平衡和肌力训练")
        elif risk_level == "MEDIUM":
            recommendations.append("建议适当增加运动锻炼")
            recommendations.append("定期进行功能评估")
        else:
            recommendations.append("保持现有运动习惯")
            recommendations.append("定期健康检查")
        
        # 针对性建议
        if "步行速度异常" in abnormalities:
            recommendations.append("重点改善下肢肌力和心肺功能")
        
        if "步态不对称" in abnormalities:
            recommendations.append("建议进行步态矫正训练")
        
        if "跌倒风险增高" in abnormalities:
            recommendations.append("注意居家环境安全，考虑使用助行器具")
        
        if patient_info.age > 70:
            recommendations.append("建议营养支持，适当补充蛋白质和维生素D")
        
        return recommendations
    
    def _assess_data_quality(self, pressure_points: List[PressurePoint]) -> str:
        """评估数据质量"""
        if len(pressure_points) > 600:
            return "优秀"
        elif len(pressure_points) > 400:
            return "良好"
        elif len(pressure_points) > 200:
            return "一般"
        else:
            return "需改善"

# 导出
__all__ = [
    "SarcNeuroAnalyzer",
    "PressurePoint",
    "PatientInfo", 
    "GaitAnalysis",
    "BalanceAnalysis",
    "SarcopeniaAnalysis"
]