"""
地面反力分析服务 - Python版本
基于32×32压力传感器数据计算三个方向的地面反力
符合专业步态分析要求，提供医学级地面反力指标

2025-08-04 - 与平台算法同步
对应文件: /server/services/groundReactionForceService.ts
"""

import math
import numpy as np
from typing import List, Dict, Any, Optional
from dataclasses import dataclass


@dataclass
class ForceMetrics:
    """力学指标数据类"""
    # 力的峰值 (N)
    peak: float
    
    # 平均力值 (N)
    average: float
    
    # 变异系数 (%)
    cv: float
    
    # 力的时间序列数据 (N)
    time_series: List[float]
    
    # 力的冲量 (N·s)
    impulse: float
    
    # 加载率 (N/s)
    loading_rate: float
    
    # 力曲线特征点
    characteristics: Dict[str, Any]


@dataclass
class GroundReactionForceAnalysis:
    """地面反力综合分析结果"""
    # 三个方向的地面反力
    antero_posterior: ForceMetrics    # 前后方向反力
    medio_lateral: ForceMetrics       # 左右方向反力
    vertical: ForceMetrics           # 垂直方向反力
    
    # 综合分析
    total_force: float               # 合成力峰值
    force_balance: float             # 力的平衡性指数 (0-100)
    symmetry_index: float            # 对称性指数 (0-100)
    
    # 步态相分析
    gait_phases: Dict[str, Dict[str, float]]
    
    # 医学评估
    medical_assessment: Dict[str, Any]


@dataclass
class PressureMatrix:
    """压力矩阵数据"""
    data: List[List[float]]  # 32×32压力矩阵
    timestamp: float


class GroundReactionForceService:
    """地面反力分析服务"""
    
    def __init__(self):
        # 生物力学常数 - 与TypeScript版本完全一致
        self.BIOMECHANICAL_CONSTANTS = {
            # 体重转换系数 (压力单位到力的转换)
            'PRESSURE_TO_FORCE_RATIO': 9.8,        # 1kg/cm² ≈ 9.8N/cm²
            
            # 正常地面反力范围 (倍体重)
            'NORMAL_VERTICAL_FORCE': {'min': 0.8, 'max': 1.4},      # 垂直反力
            'NORMAL_AP_FORCE': {'min': 0.1, 'max': 0.25},           # 前后反力
            'NORMAL_ML_FORCE': {'min': 0.05, 'max': 0.15},          # 左右反力
            
            # 步态相时间比例
            'STANCE_PHASE_RATIO': 0.62,
            'SWING_PHASE_RATIO': 0.38,
            'DOUBLE_SUPPORT_RATIO': 0.12,
            
            # 力曲线特征点时间比例
            'FIRST_PEAK_TIME': 0.15,     # 第一个峰值出现时间
            'VALLEY_TIME': 0.50,         # 谷值出现时间
            'SECOND_PEAK_TIME': 0.80,    # 第二个峰值出现时间
            
            # 异常检测阈值
            'ABNORMAL_CV_THRESHOLD': 20,     # 变异系数异常阈值(%)
            'ASYMMETRY_THRESHOLD': 15        # 不对称异常阈值(%)
        }
        
        # 获取硬件物理参数
        self.physical_params = self._get_physical_params()
    
    def _get_physical_params(self) -> Dict[str, float]:
        """获取硬件物理参数"""
        return {
            'grid_scale_x': 0.0516,  # X轴网格比例 (m/格)
            'grid_scale_y': 0.0297,  # Y轴网格比例 (m/格)
            'pressure_threshold': 20  # 压力阈值
        }
    
    def calculate_antero_posterior_force(self, pressure_data: List[PressureMatrix], patient_weight: float = 70) -> ForceMetrics:
        """
        前后方向地面反力分析
        分析步态过程中的制动力和推进力
        """
        force_time_series = []
        
        for matrix in pressure_data:
            total_force = 0
            weighted_y = 0
            total_pressure = 0
            
            # 计算压力中心和前后方向压力梯度
            for row in range(32):
                for col in range(32):
                    pressure = matrix.data[row][col]
                    if pressure > 0.1:
                        physical_y = row * self.physical_params['grid_scale_y']
                        total_pressure += pressure
                        weighted_y += physical_y * pressure
                        
                        # 前后方向力分量：基于压力梯度
                        force_component = self._calculate_ap_force_component(row, col, pressure, matrix.data)
                        total_force += force_component
            
            # 转换为牛顿 (N)
            force_in_newtons = total_force * self.BIOMECHANICAL_CONSTANTS['PRESSURE_TO_FORCE_RATIO'] * 0.01
            force_time_series.append(force_in_newtons)
        
        return self._calculate_force_metrics(force_time_series, patient_weight, 'antero_posterior')
    
    def calculate_medio_lateral_force(self, pressure_data: List[PressureMatrix], patient_weight: float = 70) -> ForceMetrics:
        """
        左右方向地面反力分析
        分析步态中的侧向稳定性和平衡控制
        """
        force_time_series = []
        
        for matrix in pressure_data:
            total_force = 0
            
            # 计算左右方向压力梯度
            for row in range(32):
                for col in range(32):
                    pressure = matrix.data[row][col]
                    if pressure > 0.1:
                        # 左右方向力分量：基于横向压力分布
                        force_component = self._calculate_ml_force_component(row, col, pressure, matrix.data)
                        total_force += force_component
            
            # 转换为牛顿 (N)
            force_in_newtons = total_force * self.BIOMECHANICAL_CONSTANTS['PRESSURE_TO_FORCE_RATIO'] * 0.01
            force_time_series.append(force_in_newtons)
        
        return self._calculate_force_metrics(force_time_series, patient_weight, 'medio_lateral')
    
    def calculate_vertical_force(self, pressure_data: List[PressureMatrix], patient_weight: float = 70) -> ForceMetrics:
        """
        垂直方向地面反力分析
        分析支撑相的垂直承重特征
        """
        force_time_series = []
        
        for matrix in pressure_data:
            total_force = 0
            
            # 垂直方向力 = 所有压力的总和
            for row in range(32):
                for col in range(32):
                    pressure = matrix.data[row][col]
                    if pressure > 0.1:
                        total_force += pressure
            
            # 转换为牛顿 (N)：垂直反力通常是体重的倍数
            force_in_newtons = total_force * self.BIOMECHANICAL_CONSTANTS['PRESSURE_TO_FORCE_RATIO'] * 0.1
            force_time_series.append(force_in_newtons)
        
        return self._calculate_force_metrics(force_time_series, patient_weight, 'vertical')
    
    def analyze_ground_reaction_forces(
        self,
        pressure_data: List[PressureMatrix],
        patient_weight: float = 70,
        patient_age: float = 65,
        patient_height: float = 170
    ) -> GroundReactionForceAnalysis:
        """
        综合地面反力分析
        主要入口方法
        """
        # 计算三个方向的反力
        ap_force = self.calculate_antero_posterior_force(pressure_data, patient_weight)
        ml_force = self.calculate_medio_lateral_force(pressure_data, patient_weight)
        vertical_force = self.calculate_vertical_force(pressure_data, patient_weight)
        
        # 综合分析
        total_force = math.sqrt(ap_force.peak ** 2 + ml_force.peak ** 2 + vertical_force.peak ** 2)
        
        force_balance = self._calculate_force_balance(ap_force, ml_force, vertical_force)
        symmetry_index = self._calculate_symmetry_index(ap_force, ml_force, vertical_force)
        
        # 步态相分析
        gait_phases = self._analyze_gait_phases(vertical_force.time_series, len(pressure_data))
        
        # 医学评估
        medical_assessment = self._generate_medical_assessment(
            {'ap_force': ap_force, 'ml_force': ml_force, 'vertical_force': vertical_force},
            patient_weight,
            patient_age
        )
        
        return GroundReactionForceAnalysis(
            antero_posterior=ap_force,
            medio_lateral=ml_force,
            vertical=vertical_force,
            total_force=total_force,
            force_balance=force_balance,
            symmetry_index=symmetry_index,
            gait_phases=gait_phases,
            medical_assessment=medical_assessment
        )
    
    # 辅助计算方法
    
    def _calculate_ap_force_component(self, row: int, col: int, pressure: float, matrix: List[List[float]]) -> float:
        """前后方向力分量计算：基于压力梯度"""
        front_gradient = (pressure - matrix[row-1][col]) if row > 0 else 0
        back_gradient = (pressure - matrix[row+1][col]) if row < 31 else 0
        
        # 制动力（负值）和推进力（正值）
        force_component = (front_gradient - back_gradient) * pressure * 0.1
        return force_component
    
    def _calculate_ml_force_component(self, row: int, col: int, pressure: float, matrix: List[List[float]]) -> float:
        """左右方向力分量计算：基于横向压力梯度"""
        left_gradient = (pressure - matrix[row][col-1]) if col > 0 else 0
        right_gradient = (pressure - matrix[row][col+1]) if col < 31 else 0
        
        # 内外侧力分量
        force_component = (right_gradient - left_gradient) * pressure * 0.05
        return force_component
    
    def _calculate_force_metrics(self, time_series: List[float], patient_weight: float, force_type: str) -> ForceMetrics:
        """计算力学指标"""
        if not time_series:
            return ForceMetrics(
                peak=0, average=0, cv=0, time_series=[], impulse=0, loading_rate=0,
                characteristics={
                    'first_peak': {'value': 0, 'time': 0},
                    'valley': {'value': 0, 'time': 0},
                    'second_peak': {'value': 0, 'time': 0},
                    'active_phase_start': 0,
                    'active_phase_end': 0
                }
            )
        
        # 基本统计指标
        peak = max([abs(x) for x in time_series])
        average = sum([abs(x) for x in time_series]) / len(time_series)
        cv = (self._calculate_standard_deviation(time_series) / average) * 100 if average > 0 else 0
        
        # 冲量计算（力与时间的积分）
        impulse = average * len(time_series) * 0.033  # 假设采样间隔33ms
        
        # 加载率计算（力的变化率）
        loading_rate = self._calculate_loading_rate(time_series)
        
        # 力曲线特征点识别
        characteristics = self._identify_force_characteristics(time_series, force_type)
        
        return ForceMetrics(
            peak=peak,
            average=average,
            cv=cv,
            time_series=time_series,
            impulse=impulse,
            loading_rate=loading_rate,
            characteristics=characteristics
        )
    
    def _calculate_standard_deviation(self, values: List[float]) -> float:
        """计算标准差"""
        if len(values) <= 1:
            return 0
        
        avg = sum(values) / len(values)
        squared_diffs = [(val - avg) ** 2 for val in values]
        avg_squared_diff = sum(squared_diffs) / len(values)
        return math.sqrt(avg_squared_diff)
    
    def _calculate_loading_rate(self, time_series: List[float]) -> float:
        """计算加载率"""
        if len(time_series) < 10:
            return 0
        
        # 计算前10%数据点的加载率
        loading_phase_end = int(len(time_series) * 0.1)
        max_force_in_loading = max(time_series[:loading_phase_end])
        
        return max_force_in_loading / (loading_phase_end * 0.033)  # N/s
    
    def _identify_force_characteristics(self, time_series: List[float], force_type: str) -> Dict[str, Any]:
        """识别力曲线特征点"""
        length = len(time_series)
        
        # 根据力的类型调整特征点识别策略
        if force_type == 'vertical':
            # 垂直反力典型的双峰特征
            first_peak_index = int(length * self.BIOMECHANICAL_CONSTANTS['FIRST_PEAK_TIME'])
            valley_index = int(length * self.BIOMECHANICAL_CONSTANTS['VALLEY_TIME'])
            second_peak_index = int(length * self.BIOMECHANICAL_CONSTANTS['SECOND_PEAK_TIME'])
            
            return {
                'first_peak': {
                    'value': time_series[first_peak_index] if first_peak_index < length else 0,
                    'time': first_peak_index * 0.033
                },
                'valley': {
                    'value': time_series[valley_index] if valley_index < length else 0,
                    'time': valley_index * 0.033
                },
                'second_peak': {
                    'value': time_series[second_peak_index] if second_peak_index < length else 0,
                    'time': second_peak_index * 0.033
                },
                'active_phase_start': self._find_active_phase_start(time_series) * 0.033,
                'active_phase_end': self._find_active_phase_end(time_series) * 0.033
            }
        else:
            # 前后和左右反力的单峰特征
            peak_index = time_series.index(max(time_series, key=abs))
            
            return {
                'first_peak': {
                    'value': time_series[peak_index],
                    'time': peak_index * 0.033
                },
                'valley': {'value': 0, 'time': 0},
                'second_peak': {'value': 0, 'time': 0},
                'active_phase_start': self._find_active_phase_start(time_series) * 0.033,
                'active_phase_end': self._find_active_phase_end(time_series) * 0.033
            }
    
    def _find_active_phase_start(self, time_series: List[float]) -> int:
        """找到活跃相开始"""
        threshold = max([abs(x) for x in time_series]) * 0.1
        for i, val in enumerate(time_series):
            if abs(val) > threshold:
                return i
        return 0
    
    def _find_active_phase_end(self, time_series: List[float]) -> int:
        """找到活跃相结束"""
        threshold = max([abs(x) for x in time_series]) * 0.1
        for i in range(len(time_series) - 1, -1, -1):
            if abs(time_series[i]) > threshold:
                return i
        return len(time_series) - 1
    
    def _calculate_force_balance(self, ap_force: ForceMetrics, ml_force: ForceMetrics, vertical_force: ForceMetrics) -> float:
        """计算力平衡指数"""
        total_force = ap_force.peak + ml_force.peak + vertical_force.peak
        if total_force == 0:
            return 0
        
        # 理想比例：垂直力占主导，前后和左右力较小
        vertical_ratio = vertical_force.peak / total_force
        ap_ratio = ap_force.peak / total_force
        ml_ratio = ml_force.peak / total_force
        
        # 评分：垂直力比例越高，前后和左右力比例越低，平衡性越好
        ideal_vertical_ratio = 0.8
        max_side_ratio = 0.15
        
        score = 100
        score -= abs(vertical_ratio - ideal_vertical_ratio) * 200
        score -= max(0, ap_ratio - max_side_ratio) * 300
        score -= max(0, ml_ratio - max_side_ratio) * 300
        
        return max(0, min(100, score))
    
    def _calculate_symmetry_index(self, ap_force: ForceMetrics, ml_force: ForceMetrics, vertical_force: ForceMetrics) -> float:
        """计算对称性指数"""
        # 对称性指数：基于变异系数评估力的对称性
        average_cv = (ap_force.cv + ml_force.cv + vertical_force.cv) / 3
        
        # CV越小，对称性越好
        if average_cv <= 10:
            return 100
        elif average_cv <= 15:
            return 85
        elif average_cv <= 20:
            return 70
        elif average_cv <= 30:
            return 50
        else:
            return 30
    
    def _analyze_gait_phases(self, vertical_force_time_series: List[float], total_length: int) -> Dict[str, Dict[str, float]]:
        """分析步态相"""
        stance_phase_duration = total_length * self.BIOMECHANICAL_CONSTANTS['STANCE_PHASE_RATIO']
        swing_phase_duration = total_length * self.BIOMECHANICAL_CONSTANTS['SWING_PHASE_RATIO']
        double_support_duration = total_length * self.BIOMECHANICAL_CONSTANTS['DOUBLE_SUPPORT_RATIO']
        
        stance_phase_end = int(stance_phase_duration)
        stance_forces = vertical_force_time_series[:stance_phase_end]
        swing_forces = vertical_force_time_series[stance_phase_end:]
        
        return {
            'stance_phase': {
                'duration': stance_phase_duration * 0.033,  # 转换为秒
                'avg_force': sum(stance_forces) / len(stance_forces) if stance_forces else 0
            },
            'swing_phase': {
                'duration': swing_phase_duration * 0.033,
                'avg_force': sum(swing_forces) / len(swing_forces) if swing_forces else 0
            },
            'double_support_phase': {
                'duration': double_support_duration * 0.033,
                'avg_force': (sum(stance_forces) / len(stance_forces) * 0.7) if stance_forces else 0
            }
        }
    
    def _generate_medical_assessment(
        self,
        forces: Dict[str, ForceMetrics],
        patient_weight: float,
        patient_age: float
    ) -> Dict[str, Any]:
        """生成医学评估"""
        risk_factors = []
        recommendations = []
        score = 100
        
        # 年龄调整系数
        age_adjustment = 0.85 if patient_age > 70 else (0.92 if patient_age > 60 else 1.0)
        
        # 垂直反力评估
        vertical_force_ratio = forces['vertical_force'].peak / (patient_weight * 9.8)
        if vertical_force_ratio < self.BIOMECHANICAL_CONSTANTS['NORMAL_VERTICAL_FORCE']['min'] * age_adjustment:
            risk_factors.append('垂直地面反力偏低，可能存在承重能力下降')
            recommendations.append('建议进行下肢力量训练')
            score -= 15
        if vertical_force_ratio > self.BIOMECHANICAL_CONSTANTS['NORMAL_VERTICAL_FORCE']['max'] / age_adjustment:
            risk_factors.append('垂直地面反力过高，步态较为沉重')
            recommendations.append('建议优化步态模式，学习轻柔着地技巧')
            score -= 10
        
        # 前后反力评估
        ap_force_ratio = forces['ap_force'].peak / (patient_weight * 9.8)
        if ap_force_ratio > self.BIOMECHANICAL_CONSTANTS['NORMAL_AP_FORCE']['max'] / age_adjustment:
            risk_factors.append('前后方向反力异常，步态稳定性较差')
            recommendations.append('建议进行平衡训练和步态矫正')
            score -= 12
        
        # 左右反力评估
        ml_force_ratio = forces['ml_force'].peak / (patient_weight * 9.8)
        if ml_force_ratio > self.BIOMECHANICAL_CONSTANTS['NORMAL_ML_FORCE']['max'] / age_adjustment:
            risk_factors.append('侧向反力异常，可能存在下肢不平衡')
            recommendations.append('建议检查下肢力量平衡，进行单侧力量训练')
            score -= 8
        
        # 变异系数评估
        avg_cv = (forces['ap_force'].cv + forces['ml_force'].cv + forces['vertical_force'].cv) / 3
        if avg_cv > self.BIOMECHANICAL_CONSTANTS['ABNORMAL_CV_THRESHOLD']:
            risk_factors.append('地面反力变异性较大，步态一致性较差')
            recommendations.append('建议进行步态训练，提高动作一致性')
            score -= 10
        
        # 确定总体状态
        if score >= 85:
            status = 'normal'
        elif score >= 70:
            status = 'mild'
        elif score >= 50:
            status = 'moderate'
        else:
            status = 'severe'
        
        return {
            'status': status,
            'risk_factors': risk_factors,
            'recommendations': recommendations,
            'overall_score': max(0, min(100, round(score * age_adjustment)))
        }


# 创建全局实例
ground_reaction_force_service = GroundReactionForceService()