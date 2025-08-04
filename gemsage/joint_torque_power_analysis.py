"""
关节力矩功率分析服务 - Python版本
基于逆向动力学原理计算关节力矩和功率
符合生物力学标准的关节动力学分析

2025-08-04 - 与平台算法同步
对应文件: /server/services/jointTorquePowerService.ts
"""

import math
import numpy as np
from typing import List, Dict, Any, Optional
from dataclasses import dataclass


@dataclass
class TorqueMetrics:
    """关节力矩指标数据类"""
    # 关节力矩峰值 (N·m)
    peak_torque: float
    
    # 平均力矩 (N·m)
    average_torque: float
    
    # 力矩变异系数 (%)
    cv: float
    
    # 归一化力矩 (N·m/kg)
    normalized_torque: float
    
    # 力矩时间序列 (N·m)
    time_series: List[float]
    
    # 向心/离心期力矩
    concentric_torque: float    # 向心收缩期
    eccentric_torque: float     # 离心收缩期
    
    # 力矩特征
    characteristics: Dict[str, Any]


@dataclass
class PowerMetrics:
    """关节功率指标数据类"""
    # 功率峰值 (W)
    peak_power: float
    
    # 平均功率 (W)
    average_power: float
    
    # 归一化功率 (W/kg)
    normalized_power: float
    
    # 功率时间序列 (W)
    time_series: List[float]
    
    # 正负功功率
    positive_power: float       # 正功（产生功率）
    negative_power: float       # 负功（吸收功率）
    
    # 机械效率 (%)
    mechanical_efficiency: float
    
    # 能量回收率 (%)
    energy_recovery: float


@dataclass
class JointKinetics:
    """关节动力学综合分析结果"""
    # 各关节力矩
    hip_torque: TorqueMetrics
    knee_torque: TorqueMetrics
    ankle_torque: TorqueMetrics
    
    # 各关节功率
    hip_power: PowerMetrics
    knee_power: PowerMetrics
    ankle_power: PowerMetrics
    
    # 关节协调性指标
    joint_coordination: float       # 关节协调性评分 (0-100)
    
    # 步态效率
    gait_efficiency: Dict[str, float]
    
    # 总体评估
    overall_assessment: Dict[str, Any]


@dataclass
class AngleData:
    """角度数据"""
    data: List[float]
    timestamp: float


@dataclass
class ForceData:
    """力数据"""
    data: List[float]
    timestamp: float


class JointTorquePowerService:
    """关节力矩功率分析服务"""
    
    def __init__(self):
        # 生物力学模型参数 - 与TypeScript版本完全一致
        self.BIOMECHANICAL_CONSTANTS = {
            # 人体分段质量比例 (Dempster 1955)
            'SEGMENT_MASS_RATIO': {
                'thigh': 0.10,      # 大腿质量/体重比例
                'shank': 0.0465,    # 小腿质量/体重比例
                'foot': 0.0145      # 足部质量/体重比例
            },
            
            # 分段长度比例 (基于身高)
            'SEGMENT_LENGTH_RATIO': {
                'thigh': 0.245,     # 大腿长度/身高比例
                'shank': 0.246,     # 小腿长度/身高比例
                'foot': 0.152       # 足长/身高比例
            },
            
            # 质心位置比例 (距近端关节)
            'COM_RATIO': {
                'thigh': 0.433,     # 大腿质心位置
                'shank': 0.433,     # 小腿质心位置
                'foot': 0.50        # 足部质心位置
            },
            
            # 转动惯量系数 (kg·m²/kg)
            'INERTIA_RATIO': {
                'thigh': 0.323,     # 大腿转动惯量
                'shank': 0.302,     # 小腿转动惯量
                'foot': 0.475       # 足部转动惯量
            },
            
            # 重力加速度
            'GRAVITY': 9.81,
            
            # 正常关节力矩范围 (N·m/kg)
            'NORMAL_TORQUE_RANGE': {
                'hip': {'min': 0.8, 'max': 2.5},
                'knee': {'min': 0.5, 'max': 1.8},
                'ankle': {'min': 1.0, 'max': 4.0}
            },
            
            # 正常关节功率范围 (W/kg)
            'NORMAL_POWER_RANGE': {
                'hip': {'min': 0.8, 'max': 1.8},
                'knee': {'min': 0.3, 'max': 1.2},
                'ankle': {'min': 1.5, 'max': 3.5}
            },
            
            # 步态相时间比例
            'GAIT_PHASE_RATIO': {
                'stance': 0.62,
                'swing': 0.38,
                'loading': 0.12,    # 加载期
                'midstance': 0.31,  # 中期支撑
                'pushoff': 0.19     # 推进期
            }
        }
        
        # 获取硬件物理参数
        self.physical_params = self._get_physical_params()
    
    def _get_physical_params(self) -> Dict[str, float]:
        """获取硬件物理参数"""
        return {
            'sampling_frequency': 100,  # 采样频率 (Hz)
            'gravity': 9.81,           # 重力加速度
            'force_threshold': 20       # 力的阈值
        }
    
    def calculate_joint_torque(
        self,
        angle_data: List[AngleData],
        force_data: List[ForceData],
        patient_weight: float = 70,
        patient_height: float = 170
    ) -> TorqueMetrics:
        """
        计算关节力矩
        使用Newton-Euler逆动力学方程
        """
        if not angle_data or not force_data:
            return self._create_empty_torque_metrics()
        
        # 计算人体分段参数
        segment_params = self._calculate_segment_parameters(patient_weight, patient_height)
        
        # 计算角加速度（二阶差分）
        angular_acceleration = self._calculate_angular_acceleration(angle_data)
        
        # 逆动力学计算
        torque_time_series = []
        concentric_torques = []
        eccentric_torques = []
        
        for i, (angle, force) in enumerate(zip(angle_data, force_data)):
            if i < len(angular_acceleration):
                # Newton-Euler方程计算关节力矩
                torque = self._calculate_newton_euler_torque(
                    angular_acceleration[i],
                    force.data[0] if force.data else 0,
                    segment_params
                )
                
                torque_time_series.append(torque)
                
                # 区分向心和离心收缩
                if angular_acceleration[i] > 0:
                    concentric_torques.append(abs(torque))
                else:
                    eccentric_torques.append(abs(torque))
        
        # 计算指标
        peak_torque = max([abs(t) for t in torque_time_series]) if torque_time_series else 0
        average_torque = sum([abs(t) for t in torque_time_series]) / len(torque_time_series) if torque_time_series else 0
        cv = (self._calculate_standard_deviation(torque_time_series) / average_torque) * 100 if average_torque > 0 else 0
        normalized_torque = average_torque / patient_weight if patient_weight > 0 else 0
        
        concentric_torque = sum(concentric_torques) / len(concentric_torques) if concentric_torques else 0
        eccentric_torque = sum(eccentric_torques) / len(eccentric_torques) if eccentric_torques else 0
        
        # 力矩特征识别
        characteristics = self._identify_torque_characteristics(torque_time_series)
        
        return TorqueMetrics(
            peak_torque=peak_torque,
            average_torque=average_torque,
            cv=cv,
            normalized_torque=normalized_torque,
            time_series=torque_time_series,
            concentric_torque=concentric_torque,
            eccentric_torque=eccentric_torque,
            characteristics=characteristics
        )
    
    def calculate_joint_power(
        self,
        torque_data: TorqueMetrics,
        velocity_data: List[float],
        patient_weight: float = 70
    ) -> PowerMetrics:
        """
        计算关节功率
        功率 = 力矩 × 角速度
        """
        if not torque_data.time_series or not velocity_data:
            return self._create_empty_power_metrics()
        
        # 计算功率时间序列
        power_time_series = []
        positive_powers = []
        negative_powers = []
        
        min_length = min(len(torque_data.time_series), len(velocity_data))
        
        for i in range(min_length):
            power = torque_data.time_series[i] * velocity_data[i]
            power_time_series.append(power)
            
            if power > 0:
                positive_powers.append(power)
            else:
                negative_powers.append(abs(power))
        
        # 计算指标
        peak_power = max([abs(p) for p in power_time_series]) if power_time_series else 0
        average_power = sum([abs(p) for p in power_time_series]) / len(power_time_series) if power_time_series else 0
        normalized_power = average_power / patient_weight if patient_weight > 0 else 0
        
        positive_power = sum(positive_powers) / len(positive_powers) if positive_powers else 0
        negative_power = sum(negative_powers) / len(negative_powers) if negative_powers else 0
        
        # 机械效率计算
        total_positive_work = sum([p for p in power_time_series if p > 0])
        total_negative_work = sum([abs(p) for p in power_time_series if p < 0])
        mechanical_efficiency = (total_positive_work / (total_positive_work + total_negative_work)) * 100 if (total_positive_work + total_negative_work) > 0 else 0
        
        # 能量回收率
        energy_recovery = (total_negative_work / total_positive_work) * 100 if total_positive_work > 0 else 0
        
        return PowerMetrics(
            peak_power=peak_power,
            average_power=average_power,
            normalized_power=normalized_power,
            time_series=power_time_series,
            positive_power=positive_power,
            negative_power=negative_power,
            mechanical_efficiency=mechanical_efficiency,
            energy_recovery=energy_recovery
        )
    
    def analyze_joint_kinetics(
        self,
        hip_angle_data: List[AngleData],
        knee_angle_data: List[AngleData],
        ankle_angle_data: List[AngleData],
        ground_force_data: List[ForceData],
        patient_weight: float = 70,
        patient_height: float = 170,
        patient_age: float = 65
    ) -> JointKinetics:
        """
        综合关节动力学分析
        主要入口方法
        """
        # 计算各关节力矩
        hip_torque = self.calculate_joint_torque(hip_angle_data, ground_force_data, patient_weight, patient_height)
        knee_torque = self.calculate_joint_torque(knee_angle_data, ground_force_data, patient_weight, patient_height)
        ankle_torque = self.calculate_joint_torque(ankle_angle_data, ground_force_data, patient_weight, patient_height)
        
        # 计算角速度
        hip_velocity = self._calculate_angular_velocity(hip_angle_data)
        knee_velocity = self._calculate_angular_velocity(knee_angle_data)
        ankle_velocity = self._calculate_angular_velocity(ankle_angle_data)
        
        # 计算各关节功率
        hip_power = self.calculate_joint_power(hip_torque, hip_velocity, patient_weight)
        knee_power = self.calculate_joint_power(knee_torque, knee_velocity, patient_weight)
        ankle_power = self.calculate_joint_power(ankle_torque, ankle_velocity, patient_weight)
        
        # 关节协调性分析
        joint_coordination = self._calculate_joint_coordination(hip_power, knee_power, ankle_power)
        
        # 步态效率评估
        gait_efficiency = self._calculate_gait_efficiency(hip_power, knee_power, ankle_power)
        
        # 总体评估
        overall_assessment = self._generate_overall_assessment(
            hip_torque, knee_torque, ankle_torque,
            hip_power, knee_power, ankle_power,
            patient_age
        )
        
        return JointKinetics(
            hip_torque=hip_torque,
            knee_torque=knee_torque,
            ankle_torque=ankle_torque,
            hip_power=hip_power,
            knee_power=knee_power,
            ankle_power=ankle_power,
            joint_coordination=joint_coordination,
            gait_efficiency=gait_efficiency,
            overall_assessment=overall_assessment
        )
    
    # 辅助计算方法
    
    def _calculate_segment_parameters(self, weight: float, height: float) -> Dict[str, Dict[str, float]]:
        """计算人体分段参数"""
        height_m = height / 100  # 转换为米
        
        return {
            'thigh': {
                'mass': weight * self.BIOMECHANICAL_CONSTANTS['SEGMENT_MASS_RATIO']['thigh'],
                'length': height_m * self.BIOMECHANICAL_CONSTANTS['SEGMENT_LENGTH_RATIO']['thigh'],
                'com': height_m * self.BIOMECHANICAL_CONSTANTS['SEGMENT_LENGTH_RATIO']['thigh'] * self.BIOMECHANICAL_CONSTANTS['COM_RATIO']['thigh'],
                'inertia': weight * (height_m ** 2) * self.BIOMECHANICAL_CONSTANTS['INERTIA_RATIO']['thigh']
            },
            'shank': {
                'mass': weight * self.BIOMECHANICAL_CONSTANTS['SEGMENT_MASS_RATIO']['shank'],
                'length': height_m * self.BIOMECHANICAL_CONSTANTS['SEGMENT_LENGTH_RATIO']['shank'],
                'com': height_m * self.BIOMECHANICAL_CONSTANTS['SEGMENT_LENGTH_RATIO']['shank'] * self.BIOMECHANICAL_CONSTANTS['COM_RATIO']['shank'],
                'inertia': weight * (height_m ** 2) * self.BIOMECHANICAL_CONSTANTS['INERTIA_RATIO']['shank']
            },
            'foot': {
                'mass': weight * self.BIOMECHANICAL_CONSTANTS['SEGMENT_MASS_RATIO']['foot'],
                'length': height_m * self.BIOMECHANICAL_CONSTANTS['SEGMENT_LENGTH_RATIO']['foot'],
                'com': height_m * self.BIOMECHANICAL_CONSTANTS['SEGMENT_LENGTH_RATIO']['foot'] * self.BIOMECHANICAL_CONSTANTS['COM_RATIO']['foot'],
                'inertia': weight * (height_m ** 2) * self.BIOMECHANICAL_CONSTANTS['INERTIA_RATIO']['foot']
            }
        }
    
    def _calculate_angular_acceleration(self, angle_data: List[AngleData]) -> List[float]:
        """计算角加速度（二阶差分）"""
        if len(angle_data) < 3:
            return []
        
        accelerations = []
        dt = 0.01  # 采样间隔，假设100Hz
        
        for i in range(1, len(angle_data) - 1):
            prev_angle = math.radians(angle_data[i-1].data[0]) if angle_data[i-1].data else 0
            curr_angle = math.radians(angle_data[i].data[0]) if angle_data[i].data else 0
            next_angle = math.radians(angle_data[i+1].data[0]) if angle_data[i+1].data else 0
            
            # 二阶差分计算角加速度
            acceleration = (next_angle - 2 * curr_angle + prev_angle) / (dt ** 2)
            accelerations.append(acceleration)
        
        return accelerations
    
    def _calculate_angular_velocity(self, angle_data: List[AngleData]) -> List[float]:
        """计算角速度（一阶差分）"""
        if len(angle_data) < 2:
            return []
        
        velocities = []
        dt = 0.01  # 采样间隔
        
        for i in range(len(angle_data) - 1):
            curr_angle = math.radians(angle_data[i].data[0]) if angle_data[i].data else 0
            next_angle = math.radians(angle_data[i+1].data[0]) if angle_data[i+1].data else 0
            
            velocity = (next_angle - curr_angle) / dt
            velocities.append(velocity)
        
        return velocities
    
    def _calculate_newton_euler_torque(
        self,
        angular_acceleration: float,
        ground_force: float,
        segment_params: Dict[str, Dict[str, float]]
    ) -> float:
        """Newton-Euler方程计算关节力矩"""
        # 简化的力矩计算（实际应用中需要更复杂的3D逆动力学）
        # 力矩 = 转动惯量 × 角加速度 + 重力力矩 + 外力力矩
        
        # 使用大腿参数作为示例
        thigh = segment_params['thigh']
        
        # 惯性力矩
        inertial_torque = thigh['inertia'] * angular_acceleration
        
        # 重力力矩
        gravity_torque = thigh['mass'] * self.BIOMECHANICAL_CONSTANTS['GRAVITY'] * thigh['com']
        
        # 地面反力产生的外力矩（简化）
        external_torque = ground_force * 0.01  # 力臂假设为1cm
        
        total_torque = inertial_torque + gravity_torque + external_torque
        
        return total_torque
    
    def _calculate_standard_deviation(self, values: List[float]) -> float:
        """计算标准差"""
        if len(values) <= 1:
            return 0
        
        avg = sum(values) / len(values)
        squared_diffs = [(val - avg) ** 2 for val in values]
        avg_squared_diff = sum(squared_diffs) / len(values)
        return math.sqrt(avg_squared_diff)
    
    def _identify_torque_characteristics(self, torque_time_series: List[float]) -> Dict[str, Any]:
        """识别力矩特征"""
        if not torque_time_series:
            return {}
        
        # 识别峰值、谷值等特征点
        peak_index = torque_time_series.index(max(torque_time_series, key=abs))
        peak_value = torque_time_series[peak_index]
        
        return {
            'peak_torque_time': peak_index * 0.01,  # 转换为时间
            'peak_torque_value': peak_value,
            'torque_impulse': sum([abs(t) for t in torque_time_series]) * 0.01,  # 力矩冲量
            'active_phase_duration': len(torque_time_series) * 0.01
        }
    
    def _calculate_joint_coordination(
        self,
        hip_power: PowerMetrics,
        knee_power: PowerMetrics,
        ankle_power: PowerMetrics
    ) -> float:
        """计算关节协调性"""
        # 基于功率模式的相似性评估协调性
        hip_pattern = np.array(hip_power.time_series[:min(len(hip_power.time_series), 100)])
        knee_pattern = np.array(knee_power.time_series[:min(len(knee_power.time_series), 100)])
        ankle_pattern = np.array(ankle_power.time_series[:min(len(ankle_power.time_series), 100)])
        
        if len(hip_pattern) == 0 or len(knee_pattern) == 0 or len(ankle_pattern) == 0:
            return 0
        
        # 归一化功率模式
        hip_normalized = hip_pattern / np.max(np.abs(hip_pattern)) if np.max(np.abs(hip_pattern)) > 0 else hip_pattern
        knee_normalized = knee_pattern / np.max(np.abs(knee_pattern)) if np.max(np.abs(knee_pattern)) > 0 else knee_pattern
        ankle_normalized = ankle_pattern / np.max(np.abs(ankle_pattern)) if np.max(np.abs(ankle_pattern)) > 0 else ankle_pattern
        
        # 计算相关系数作为协调性指标
        min_length = min(len(hip_normalized), len(knee_normalized), len(ankle_normalized))
        if min_length < 2:
            return 50  # 默认中等协调性
        
        hip_knee_corr = np.corrcoef(hip_normalized[:min_length], knee_normalized[:min_length])[0, 1]
        knee_ankle_corr = np.corrcoef(knee_normalized[:min_length], ankle_normalized[:min_length])[0, 1]
        hip_ankle_corr = np.corrcoef(hip_normalized[:min_length], ankle_normalized[:min_length])[0, 1]
        
        # 处理NaN值
        correlations = []
        if not np.isnan(hip_knee_corr):
            correlations.append(abs(hip_knee_corr))
        if not np.isnan(knee_ankle_corr):
            correlations.append(abs(knee_ankle_corr))
        if not np.isnan(hip_ankle_corr):
            correlations.append(abs(hip_ankle_corr))
        
        if not correlations:
            return 50
        
        avg_correlation = sum(correlations) / len(correlations)
        coordination_score = avg_correlation * 100
        
        return max(0, min(100, coordination_score))
    
    def _calculate_gait_efficiency(
        self,
        hip_power: PowerMetrics,
        knee_power: PowerMetrics,
        ankle_power: PowerMetrics
    ) -> Dict[str, float]:
        """计算步态效率"""
        # 总体机械效率
        total_positive_work = hip_power.positive_power + knee_power.positive_power + ankle_power.positive_power
        total_negative_work = hip_power.negative_power + knee_power.negative_power + ankle_power.negative_power
        
        overall_efficiency = (total_positive_work / (total_positive_work + total_negative_work)) * 100 if (total_positive_work + total_negative_work) > 0 else 0
        
        # 能量传递效率
        ankle_contribution = ankle_power.positive_power / total_positive_work * 100 if total_positive_work > 0 else 0
        hip_contribution = hip_power.positive_power / total_positive_work * 100 if total_positive_work > 0 else 0
        knee_contribution = knee_power.positive_power / total_positive_work * 100 if total_positive_work > 0 else 0
        
        return {
            'efficiency': overall_efficiency,
            'ankle_contribution': ankle_contribution,
            'hip_contribution': hip_contribution,
            'knee_contribution': knee_contribution,
            'energy_recovery_rate': (hip_power.energy_recovery + knee_power.energy_recovery + ankle_power.energy_recovery) / 3
        }
    
    def _generate_overall_assessment(
        self,
        hip_torque: TorqueMetrics,
        knee_torque: TorqueMetrics,
        ankle_torque: TorqueMetrics,
        hip_power: PowerMetrics,
        knee_power: PowerMetrics,
        ankle_power: PowerMetrics,
        patient_age: float
    ) -> Dict[str, Any]:
        """生成总体评估"""
        # 年龄调整系数
        age_adjustment = 0.85 if patient_age > 70 else (0.92 if patient_age > 60 else 1.0)
        
        # 力矩评估
        torque_scores = []
        
        # 髋关节力矩评估
        hip_torque_normal = self.BIOMECHANICAL_CONSTANTS['NORMAL_TORQUE_RANGE']['hip']
        if hip_torque_normal['min'] * age_adjustment <= hip_torque.normalized_torque <= hip_torque_normal['max'] * age_adjustment:
            torque_scores.append(100)
        else:
            deviation = min(
                abs(hip_torque.normalized_torque - hip_torque_normal['min'] * age_adjustment),
                abs(hip_torque.normalized_torque - hip_torque_normal['max'] * age_adjustment)
            )
            torque_scores.append(max(0, 100 - deviation / hip_torque_normal['max'] * 100))
        
        # 膝关节力矩评估
        knee_torque_normal = self.BIOMECHANICAL_CONSTANTS['NORMAL_TORQUE_RANGE']['knee']
        if knee_torque_normal['min'] * age_adjustment <= knee_torque.normalized_torque <= knee_torque_normal['max'] * age_adjustment:
            torque_scores.append(100)
        else:
            deviation = min(
                abs(knee_torque.normalized_torque - knee_torque_normal['min'] * age_adjustment),
                abs(knee_torque.normalized_torque - knee_torque_normal['max'] * age_adjustment)
            )
            torque_scores.append(max(0, 100 - deviation / knee_torque_normal['max'] * 100))
        
        # 踝关节力矩评估
        ankle_torque_normal = self.BIOMECHANICAL_CONSTANTS['NORMAL_TORQUE_RANGE']['ankle']
        if ankle_torque_normal['min'] * age_adjustment <= ankle_torque.normalized_torque <= ankle_torque_normal['max'] * age_adjustment:
            torque_scores.append(100)
        else:
            deviation = min(
                abs(ankle_torque.normalized_torque - ankle_torque_normal['min'] * age_adjustment),
                abs(ankle_torque.normalized_torque - ankle_torque_normal['max'] * age_adjustment)
            )
            torque_scores.append(max(0, 100 - deviation / ankle_torque_normal['max'] * 100))
        
        # 功率评估
        power_scores = []
        
        # 各关节功率评估（类似力矩评估逻辑）
        for joint_power, joint_name in [(hip_power, 'hip'), (knee_power, 'knee'), (ankle_power, 'ankle')]:
            power_normal = self.BIOMECHANICAL_CONSTANTS['NORMAL_POWER_RANGE'][joint_name]
            if power_normal['min'] * age_adjustment <= joint_power.normalized_power <= power_normal['max'] * age_adjustment:
                power_scores.append(100)
            else:
                deviation = min(
                    abs(joint_power.normalized_power - power_normal['min'] * age_adjustment),
                    abs(joint_power.normalized_power - power_normal['max'] * age_adjustment)
                )
                power_scores.append(max(0, 100 - deviation / power_normal['max'] * 100))
        
        # 综合评分
        torque_score = sum(torque_scores) / len(torque_scores) if torque_scores else 0
        power_score = sum(power_scores) / len(power_scores) if power_scores else 0
        
        overall_score = (torque_score * 0.6 + power_score * 0.4) * age_adjustment
        
        # 状态判定
        if overall_score >= 85:
            status = 'excellent'
        elif overall_score >= 70:
            status = 'good'
        elif overall_score >= 50:
            status = 'fair'
        else:
            status = 'poor'
        
        return {
            'overall_score': round(overall_score),
            'status': status,
            'torque_score': round(torque_score),
            'power_score': round(power_score),
            'age_adjustment': age_adjustment
        }
    
    def _create_empty_torque_metrics(self) -> TorqueMetrics:
        """创建空的力矩指标"""
        return TorqueMetrics(
            peak_torque=0,
            average_torque=0,
            cv=0,
            normalized_torque=0,
            time_series=[],
            concentric_torque=0,
            eccentric_torque=0,
            characteristics={}
        )
    
    def _create_empty_power_metrics(self) -> PowerMetrics:
        """创建空的功率指标"""
        return PowerMetrics(
            peak_power=0,
            average_power=0,
            normalized_power=0,
            time_series=[],
            positive_power=0,
            negative_power=0,
            mechanical_efficiency=0,
            energy_recovery=0
        )


# 创建全局实例
joint_torque_power_service = JointTorquePowerService()