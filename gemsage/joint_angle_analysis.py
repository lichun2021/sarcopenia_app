"""
关节角度分析服务 - Python版本
基于COP轨迹数据反推关节角度变化
使用生物力学模型进行角度计算

2025-08-04 - 与平台算法同步
对应文件: /server/services/jointAngleAnalysisService.ts
"""

import math
import numpy as np
from typing import List, Dict, Any, Tuple
from dataclasses import dataclass


@dataclass
class JointAngleMetrics:
    """关节角度指标数据类"""
    # 髋关节角度 (度)
    hip_flexion: List[float]
    hip_abduction: List[float] 
    hip_rotation: List[float]
    
    # 膝关节角度 (度)
    knee_flexion: List[float]
    knee_abduction: List[float]
    knee_rotation: List[float]
    
    # 踝关节角度 (度)
    ankle_flexion: List[float]
    ankle_abduction: List[float]
    ankle_rotation: List[float]
    
    # 统计指标
    average_angles: Dict[str, Dict[str, float]]
    angle_ranges: Dict[str, Dict[str, float]]
    
    # 异常检测
    abnormal_angles: List[str]
    
    # 医学评估
    medical_assessment: Dict[str, Any]


@dataclass
class COPData:
    """COP数据点"""
    x: float
    y: float
    timestamp: float
    pressure: float


class JointAngleAnalysisService:
    """关节角度分析服务"""
    
    def __init__(self):
        # 生物力学模型参数 - 与TypeScript版本完全一致
        self.BIOMECHANICAL_CONSTANTS = {
            # 人体比例参数 (基于国际标准)
            'THIGH_LENGTH_RATIO': 0.245,      # 大腿长度/身高比例
            'SHANK_LENGTH_RATIO': 0.246,      # 小腿长度/身高比例
            'FOOT_LENGTH_RATIO': 0.152,       # 足长/身高比例
            
            # 关节角度正常范围 (度)
            'NORMAL_HIP_FLEXION': {'min': 30, 'max': 60},
            'NORMAL_KNEE_FLEXION': {'min': 130, 'max': 170},
            'NORMAL_ANKLE_FLEXION': {'min': 0, 'max': 20},
            
            # 步态周期参数
            'STANCE_PHASE_RATIO': 0.62,       # 支撑相占比
            'SWING_PHASE_RATIO': 0.38,        # 摆动相占比
            
            # COP位置与关节角度关系系数
            'COP_TO_ANGLE_COEFFICIENT': 1.2,
            
            # 异常检测阈值
            'ABNORMAL_THRESHOLD': 2.0         # 标准差倍数
        }
        
        # 获取硬件物理参数 (与hardwareAdaptiveService同步)
        self.physical_params = self._get_physical_params()
    
    def _get_physical_params(self) -> Dict[str, float]:
        """获取硬件物理参数"""
        return {
            'grid_scale_x': 0.0516,  # X轴网格比例 (m/格)
            'grid_scale_y': 0.0297,  # Y轴网格比例 (m/格)
            'pressure_threshold': 20  # 压力阈值
        }
    
    def calculate_hip_joint_angles(self, cop_data: List[COPData], patient_height: float = 170) -> Dict[str, Any]:
        """
        髋关节角度分析
        基于COP轨迹推算髋关节三维角度变化
        """
        # 髋关节角度时间序列
        hip_flexion_series = []
        hip_abduction_series = []
        hip_rotation_series = []
        
        for i, cop in enumerate(cop_data):
            # 将COP坐标转换为物理坐标
            physical_x = cop.x * self.physical_params['grid_scale_x']
            physical_y = cop.y * self.physical_params['grid_scale_y']
            
            # 基于生物力学模型计算髋关节角度
            thigh_length = patient_height * self.BIOMECHANICAL_CONSTANTS['THIGH_LENGTH_RATIO'] / 100
            
            # 髋关节屈伸角度 (基于前后COP位移)
            flexion_angle = self._calculate_flexion_angle(physical_y, thigh_length)
            hip_flexion_series.append(flexion_angle)
            
            # 髋关节内外展角度 (基于左右COP位移)
            abduction_angle = self._calculate_abduction_angle(physical_x, thigh_length)
            hip_abduction_series.append(abduction_angle)
            
            # 髋关节内外旋角度 (基于COP轨迹曲率)
            rotation_angle = self._calculate_rotation_angle(cop_data[i-1], cop) if i > 0 else 0
            hip_rotation_series.append(rotation_angle)
        
        return {
            'flexion': self._calculate_average(hip_flexion_series),
            'abduction': self._calculate_average(hip_abduction_series),
            'rotation': self._calculate_average(hip_rotation_series),
            'time_series': [hip_flexion_series, hip_abduction_series, hip_rotation_series]
        }
    
    def calculate_knee_joint_angles(self, cop_data: List[COPData], patient_height: float = 170) -> Dict[str, Any]:
        """
        膝关节角度分析
        基于COP轨迹和步态周期推算膝关节角度
        """
        knee_flexion_series = []
        knee_abduction_series = []
        knee_rotation_series = []
        
        # 检测步态周期
        gait_cycles = self._detect_gait_cycles(cop_data)
        
        for i, cop in enumerate(cop_data):
            gait_phase = self._determine_gait_phase(i, gait_cycles)
            
            # 膝关节在不同步态相的角度特征
            shank_length = patient_height * self.BIOMECHANICAL_CONSTANTS['SHANK_LENGTH_RATIO'] / 100
            
            # 膝关节屈伸角度 (基于步态相和COP位置)
            if gait_phase == 'stance':
                # 支撑相：膝关节较伸直
                flexion_angle = 160 + (cop.y - 16) * 0.5
            else:
                # 摆动相：膝关节弯曲度增加
                flexion_angle = 140 + math.sin((i / len(cop_data)) * math.pi * 2) * 20
            
            knee_flexion_series.append(max(120, min(180, flexion_angle)))
            
            # 膝关节内外展 (较小幅度)
            abduction_angle = (cop.x - 16) * 0.3
            knee_abduction_series.append(max(-10, min(30, abduction_angle)))
            
            # 膝关节旋转 (最小)
            rotation_angle = np.random.uniform(-1, 1) if gait_phase == 'swing' else 0
            knee_rotation_series.append(rotation_angle)
        
        return {
            'flexion': self._calculate_average(knee_flexion_series),
            'abduction': self._calculate_average(knee_abduction_series),
            'rotation': self._calculate_average(knee_rotation_series),
            'time_series': [knee_flexion_series, knee_abduction_series, knee_rotation_series]
        }
    
    def calculate_ankle_joint_angles(self, cop_data: List[COPData], patient_height: float = 170) -> Dict[str, Any]:
        """
        踝关节角度分析
        基于足部压力分布和COP轨迹
        """
        ankle_flexion_series = []
        ankle_abduction_series = []
        ankle_rotation_series = []
        
        for i, cop in enumerate(cop_data):
            # 踝关节屈伸角度 (基于前后足压力分布)
            flexion_angle = (cop.y - 16) * 0.8
            ankle_flexion_series.append(max(-20, min(30, flexion_angle)))
            
            # 踝关节内外翻 (基于左右压力)
            abduction_angle = (cop.x - 16) * 0.6
            ankle_abduction_series.append(max(-15, min(25, abduction_angle)))
            
            # 踝关节内外旋 (较小范围)
            rotation_angle = (cop.x - cop_data[i-1].x) * 0.1 if i > 0 else 0
            ankle_rotation_series.append(max(-5, min(5, rotation_angle)))
        
        return {
            'flexion': self._calculate_average(ankle_flexion_series),
            'abduction': self._calculate_average(ankle_abduction_series),
            'rotation': self._calculate_average(ankle_rotation_series),
            'time_series': [ankle_flexion_series, ankle_abduction_series, ankle_rotation_series]
        }
    
    def calculate_comprehensive_joint_angles(
        self, 
        cop_data: List[COPData], 
        patient_height: float = 170, 
        patient_age: float = 65
    ) -> JointAngleMetrics:
        """
        综合关节角度分析
        主要入口方法
        """
        # 计算各关节角度
        hip_angles = self.calculate_hip_joint_angles(cop_data, patient_height)
        knee_angles = self.calculate_knee_joint_angles(cop_data, patient_height)
        ankle_angles = self.calculate_ankle_joint_angles(cop_data, patient_height)
        
        # 构建返回结果
        return JointAngleMetrics(
            # 时间序列数据
            hip_flexion=hip_angles['time_series'][0],
            hip_abduction=hip_angles['time_series'][1],
            hip_rotation=hip_angles['time_series'][2],
            knee_flexion=knee_angles['time_series'][0],
            knee_abduction=knee_angles['time_series'][1],
            knee_rotation=knee_angles['time_series'][2],
            ankle_flexion=ankle_angles['time_series'][0],
            ankle_abduction=ankle_angles['time_series'][1],
            ankle_rotation=ankle_angles['time_series'][2],
            
            # 平均值
            average_angles={
                'hip': {
                    'flexion': hip_angles['flexion'],
                    'abduction': hip_angles['abduction'],
                    'rotation': hip_angles['rotation']
                },
                'knee': {
                    'flexion': knee_angles['flexion'],
                    'abduction': knee_angles['abduction'],
                    'rotation': knee_angles['rotation']
                },
                'ankle': {
                    'flexion': ankle_angles['flexion'],
                    'abduction': ankle_angles['abduction'],
                    'rotation': ankle_angles['rotation']
                }
            },
            
            # 角度范围
            angle_ranges={
                'hip': {
                    'flexion': self._calculate_range(hip_angles['time_series'][0]),
                    'abduction': self._calculate_range(hip_angles['time_series'][1]),
                    'rotation': self._calculate_range(hip_angles['time_series'][2])
                },
                'knee': {
                    'flexion': self._calculate_range(knee_angles['time_series'][0]),
                    'abduction': self._calculate_range(knee_angles['time_series'][1]),
                    'rotation': self._calculate_range(knee_angles['time_series'][2])
                },
                'ankle': {
                    'flexion': self._calculate_range(ankle_angles['time_series'][0]),
                    'abduction': self._calculate_range(ankle_angles['time_series'][1]),
                    'rotation': self._calculate_range(ankle_angles['time_series'][2])
                }
            },
            
            # 异常检测
            abnormal_angles=self._detect_abnormal_angles(hip_angles, knee_angles, ankle_angles, patient_age),
            
            # 医学评估
            medical_assessment=self._generate_medical_assessment(hip_angles, knee_angles, ankle_angles, patient_age)
        )
    
    # 辅助方法
    
    def _calculate_flexion_angle(self, cop_y: float, segment_length: float) -> float:
        """基于COP前后位移计算屈伸角度"""
        displacement = (cop_y - 16) * 0.001  # 转换为米
        angle_rad = math.atan(displacement / segment_length)
        return 45 + (angle_rad * 180 / math.pi)  # 转换为度，基线45度
    
    def _calculate_abduction_angle(self, cop_x: float, segment_length: float) -> float:
        """基于COP左右位移计算内外展角度"""
        displacement = (cop_x - 16) * 0.001
        angle_rad = math.atan(displacement / segment_length)
        return angle_rad * 180 / math.pi
    
    def _calculate_rotation_angle(self, prev_cop: COPData, current_cop: COPData) -> float:
        """基于COP轨迹方向变化计算旋转角度"""
        dx = current_cop.x - prev_cop.x
        dy = current_cop.y - prev_cop.y
        angle = math.atan2(dy, dx) * 180 / math.pi
        return angle * 0.1  # 缩放到合理范围
    
    def _detect_gait_cycles(self, cop_data: List[COPData]) -> List[Dict[str, int]]:
        """简化的步态周期检测"""
        cycles = []
        cycle_length = len(cop_data) // 3  # 假设3个步态周期
        
        for i in range(3):
            cycles.append({
                'start': i * cycle_length,
                'end': (i + 1) * cycle_length - 1
            })
        
        return cycles
    
    def _determine_gait_phase(self, index: int, cycles: List[Dict[str, int]]) -> str:
        """确定当前时间点的步态相"""
        for cycle in cycles:
            if cycle['start'] <= index <= cycle['end']:
                phase_position = (index - cycle['start']) / (cycle['end'] - cycle['start'])
                return 'stance' if phase_position < self.BIOMECHANICAL_CONSTANTS['STANCE_PHASE_RATIO'] else 'swing'
        return 'stance'
    
    def _calculate_average(self, values: List[float]) -> float:
        """计算平均值"""
        return sum(values) / len(values) if values else 0
    
    def _calculate_range(self, values: List[float]) -> float:
        """计算范围"""
        return max(values) - min(values) if values else 0
    
    def _detect_abnormal_angles(
        self, 
        hip_angles: Dict[str, Any], 
        knee_angles: Dict[str, Any], 
        ankle_angles: Dict[str, Any], 
        patient_age: float
    ) -> List[str]:
        """检测异常角度"""
        abnormalities = []
        
        # 基于年龄调整正常范围
        age_adjustment = 0.8 if patient_age > 70 else (0.9 if patient_age > 60 else 1.0)
        
        # 髋关节异常检测
        if hip_angles['flexion'] < self.BIOMECHANICAL_CONSTANTS['NORMAL_HIP_FLEXION']['min'] * age_adjustment:
            abnormalities.append('髋关节屈曲幅度明显低于正常人群')
        if abs(hip_angles['abduction']) > 20 * age_adjustment:
            abnormalities.append('髋关节外展角度异常')
        
        # 膝关节异常检测
        if knee_angles['flexion'] < 140 * age_adjustment:
            abnormalities.append('膝关节屈曲幅度明显低于正常人群')
        if knee_angles['flexion'] > 170:
            abnormalities.append('膝关节伸展幅度明显低于正常人群')
        if abs(knee_angles['rotation']) > 5:
            abnormalities.append('膝关节旋转幅度明显低于正常人群')
        
        # 踝关节异常检测
        if ankle_angles['flexion'] < 0:
            abnormalities.append('踝关节屈曲时前屈角度明显低于正常人群')
        
        return abnormalities
    
    def _generate_medical_assessment(
        self,
        hip_angles: Dict[str, Any],
        knee_angles: Dict[str, Any],
        ankle_angles: Dict[str, Any],
        patient_age: float
    ) -> Dict[str, Any]:
        """生成医学评估"""
        # 计算各关节状态评分
        hip_score = self._calculate_joint_score(hip_angles, 'hip', patient_age)
        knee_score = self._calculate_joint_score(knee_angles, 'knee', patient_age)
        ankle_score = self._calculate_joint_score(ankle_angles, 'ankle', patient_age)
        
        return {
            'hip_status': self._score_to_status(hip_score),
            'knee_status': self._score_to_status(knee_score),
            'ankle_status': self._score_to_status(ankle_score),
            'overall_score': round((hip_score + knee_score + ankle_score) / 3)
        }
    
    def _calculate_joint_score(self, joint_angles: Dict[str, Any], joint_type: str, patient_age: float) -> float:
        """计算关节评分"""
        base_score = 100
        age_adjustment = 0.9 if patient_age > 70 else (0.95 if patient_age > 60 else 1.0)
        
        # 根据关节类型和角度偏差扣分
        if joint_type == 'hip':
            if joint_angles['flexion'] < 40:
                base_score -= 20
            if abs(joint_angles['abduction']) > 15:
                base_score -= 15
        elif joint_type == 'knee':
            if joint_angles['flexion'] < 150:
                base_score -= 25
            if abs(joint_angles['rotation']) > 3:
                base_score -= 10
        elif joint_type == 'ankle':
            if joint_angles['flexion'] < 5:
                base_score -= 15
            if abs(joint_angles['abduction']) > 10:
                base_score -= 10
        
        return max(0, min(100, round(base_score * age_adjustment)))
    
    def _score_to_status(self, score: float) -> str:
        """评分转状态"""
        if score >= 80:
            return 'normal'
        elif score >= 60:
            return 'mild'
        elif score >= 40:
            return 'moderate'
        else:
            return 'severe'


# 创建全局实例
joint_angle_analysis_service = JointAngleAnalysisService()