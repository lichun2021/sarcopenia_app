"""
AI多维度评估引擎 - Python版本
基于专业步态分析数据进行综合智能评估
提供6维度雷达图评估和详细诊断建议

2025-08-04 - 与平台算法同步
对应文件: /server/services/aiAssessmentEngine.ts
"""

import math
from typing import List, Dict, Any, Optional, Union, Tuple
from dataclasses import dataclass
from enum import Enum


class RiskLevel(Enum):
    LOW = "low"
    MODERATE = "moderate"
    HIGH = "high"
    SEVERE = "severe"


class SuggestionCategory(Enum):
    REHABILITATION = "rehabilitation"
    MEDICAL = "medical"
    LIFESTYLE = "lifestyle"
    MONITORING = "monitoring"


class Priority(Enum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


@dataclass
class AIAssessment:
    """AI评估结果数据类"""
    # 6大维度评分 (0-100分)
    步态时间: float     # 步态时间参数评估
    步态时域: float     # 步态时域特征评估
    关节角域: float     # 关节角度域评估
    关节力能: float     # 关节力矩功率评估
    姿态: float         # 姿态平衡评估
    地返力: float       # 地面反力评估
    
    # 综合评分
    overall_score: float  # 总体评分 (0-100)
    
    # 风险等级
    risk_level: RiskLevel
    
    # 置信度
    confidence: float    # AI评估置信度 (0-100)


@dataclass
class AssessmentDetail:
    """评估明细数据类"""
    # 评估明细列表
    评估明细: List[str]
    
    # 异常检测结果
    abnormal_findings: List[Dict[str, Any]]
    
    # 功能性评估
    functional_capacity: Dict[str, float]
    
    # 疾病风险评估
    disease_risk: Dict[str, float]


@dataclass
class DiagnosticSuggestion:
    """诊断建议数据类"""
    # 诊断建议分类
    category: SuggestionCategory
    
    # 建议优先级
    priority: Priority
    
    # 建议内容
    suggestion: str
    
    # 预期效果
    expected_outcome: str
    
    # 实施时间框架
    timeframe: str
    
    # 目标指标
    target_metrics: Optional[List[str]] = None


@dataclass
class ComprehensiveMetrics:
    """综合评估指标数据类"""
    # 基础步态指标
    gait_metrics: Dict[str, float]
    
    # 时域特征
    temporal_metrics: Dict[str, float]
    
    # 关节运动学（简化版，对应JointAngleMetrics）
    joint_metrics: Dict[str, Any]
    
    # 关节动力学（简化版，对应JointKinetics）
    power_metrics: Dict[str, Any]
    
    # 姿态控制
    posture_metrics: Dict[str, float]
    
    # 地面反力（简化版，对应GroundReactionForceAnalysis）
    grf_metrics: Dict[str, Any]
    
    # 患者基本信息
    patient_info: Dict[str, Union[float, str, List[str]]]


class AIAssessmentEngine:
    """AI多维度评估引擎"""
    
    def __init__(self):
        # AI评估算法参数 - 与TypeScript版本完全一致
        self.AI_PARAMETERS = {
            # 年龄调整系数
            'AGE_COEFFICIENTS': {
                'young': {'min': 18, 'max': 39, 'factor': 1.0},      # 年轻人
                'middle_aged': {'min': 40, 'max': 64, 'factor': 0.92}, # 中年人
                'elderly': {'min': 65, 'max': 79, 'factor': 0.85},    # 老年人
                'very_elderly': {'min': 80, 'max': 100, 'factor': 0.75} # 高龄人
            },
            
            # 性别调整系数
            'GENDER_COEFFICIENTS': {
                'male': 1.0,
                'female': 0.95  # 考虑到生理差异
            },
            
            # 权重系数 (各维度重要性)
            'DIMENSION_WEIGHTS': {
                '步态时间': 0.18,    # 基础步态参数权重
                '步态时域': 0.16,    # 时域特征权重
                '关节角域': 0.17,    # 关节角度权重
                '关节力能': 0.15,    # 关节力矩功率权重
                '姿态': 0.16,        # 姿态平衡权重
                '地返力': 0.18       # 地面反力权重
            },
            
            # 风险阈值
            'RISK_THRESHOLDS': {
                'low': 85,        # 低风险: ≥85分
                'moderate': 70,   # 中等风险: 70-84分
                'high': 50,       # 高风险: 50-69分
                'severe': 0       # 严重风险: <50分
            },
            
            # 置信度计算参数
            'CONFIDENCE_FACTORS': {
                'data_quality': 0.3,     # 数据质量权重
                'consistency': 0.25,     # 一致性权重
                'completeness': 0.25,    # 完整性权重
                'reliability': 0.2       # 可靠性权重
            }
        }
    
    def calculate_comprehensive_assessment(self, all_metrics: ComprehensiveMetrics) -> AIAssessment:
        """
        综合评估计算
        主要入口方法
        """
        # 计算6个维度评分
        步态时间 = self._assess_gait_timing(all_metrics.gait_metrics, all_metrics.patient_info)
        步态时域 = self._assess_gait_temporal(all_metrics.temporal_metrics, all_metrics.patient_info)
        关节角域 = self._assess_joint_angular(all_metrics.joint_metrics, all_metrics.patient_info)
        关节力能 = self._assess_joint_power(all_metrics.power_metrics, all_metrics.patient_info)
        姿态 = self._assess_posture(all_metrics.posture_metrics, all_metrics.patient_info)
        地返力 = self._assess_ground_reaction_force(all_metrics.grf_metrics, all_metrics.patient_info)
        
        # 计算综合评分
        overall_score = self._calculate_overall_score({
            '步态时间': 步态时间, '步态时域': 步态时域, '关节角域': 关节角域, 
            '关节力能': 关节力能, '姿态': 姿态, '地返力': 地返力
        })
        
        # 确定风险等级
        risk_level = self._determine_risk_level(overall_score)
        
        # 计算置信度
        confidence = self._calculate_confidence(all_metrics)
        
        return AIAssessment(
            步态时间=步态时间,
            步态时域=步态时域,
            关节角域=关节角域,
            关节力能=关节力能,
            姿态=姿态,
            地返力=地返力,
            overall_score=overall_score,
            risk_level=risk_level,
            confidence=confidence
        )
    
    def _assess_gait_timing(self, gait_metrics: Dict[str, float], patient_info: Dict[str, Any]) -> float:
        """步态时间参数评估"""
        score = 100
        age_adjustment = self._get_age_adjustment(patient_info.get('age', 65))
        gender_adjustment = self._get_gender_adjustment(patient_info.get('gender', 'male'))
        
        # 步长评估 (期望值: 0.6-0.8m)
        step_length = gait_metrics.get('step_length', 0.7)
        expected_step_length = 0.7 * age_adjustment
        step_length_deviation = abs(step_length - expected_step_length) / expected_step_length
        score -= step_length_deviation * 30
        
        # 步频评估 (期望值: 100-120 steps/min)
        cadence = gait_metrics.get('cadence', 110)
        expected_cadence = 110 * age_adjustment
        cadence_deviation = abs(cadence - expected_cadence) / expected_cadence
        score -= cadence_deviation * 25
        
        # 步行速度评估 (期望值: 1.2-1.4 m/s)
        velocity = gait_metrics.get('velocity', 1.3)
        expected_velocity = 1.3 * age_adjustment
        velocity_deviation = abs(velocity - expected_velocity) / expected_velocity
        score -= velocity_deviation * 25
        
        # 对称性评估
        symmetry_index = gait_metrics.get('symmetry_index', 95)
        if symmetry_index < 90:
            score -= (90 - symmetry_index) * 0.5
        
        return max(0, min(100, score * gender_adjustment))
    
    def _assess_gait_temporal(self, temporal_metrics: Dict[str, float], patient_info: Dict[str, Any]) -> float:
        """步态时域特征评估"""
        score = 100
        age_adjustment = self._get_age_adjustment(patient_info.get('age', 65))
        
        # 支撑相评估 (正常值: 60-62%)
        stance_phase = temporal_metrics.get('stance_phase', 0.61)
        stance_phase_deviation = abs(stance_phase - 0.61) / 0.61
        score -= stance_phase_deviation * 30
        
        # 摆动相评估 (正常值: 38-40%)
        swing_phase = temporal_metrics.get('swing_phase', 0.39)
        swing_phase_deviation = abs(swing_phase - 0.39) / 0.39
        score -= swing_phase_deviation * 25
        
        # 双支撑相评估 (正常值: 10-12%)
        double_support_phase = temporal_metrics.get('double_support_phase', 0.11)
        double_support_deviation = abs(double_support_phase - 0.11) / 0.11
        score -= double_support_deviation * 20
        
        # 步时变异性评估
        step_time = temporal_metrics.get('step_time', 0.55)
        expected_step_time = 0.55 * (1 / age_adjustment)  # 年龄越大步时越长
        step_time_deviation = abs(step_time - expected_step_time) / expected_step_time
        score -= step_time_deviation * 25
        
        return max(0, min(100, score * age_adjustment))
    
    def _assess_joint_angular(self, joint_metrics: Dict[str, Any], patient_info: Dict[str, Any]) -> float:
        """关节角度域评估"""
        score = 100
        age_adjustment = self._get_age_adjustment(patient_info.get('age', 65))
        
        # 获取关节角度数据（简化版）
        average_angles = joint_metrics.get('average_angles', {})
        angle_ranges = joint_metrics.get('angle_ranges', {})
        
        # 髋关节角度评估
        hip_angles = average_angles.get('hip', {'flexion': 45, 'abduction': 0, 'rotation': 0})
        hip_score = self._evaluate_joint_angles(hip_angles, 'hip', age_adjustment)
        
        # 膝关节角度评估
        knee_angles = average_angles.get('knee', {'flexion': 155, 'abduction': 0, 'rotation': 0})
        knee_score = self._evaluate_joint_angles(knee_angles, 'knee', age_adjustment)
        
        # 踝关节角度评估
        ankle_angles = average_angles.get('ankle', {'flexion': 10, 'abduction': 0, 'rotation': 0})
        ankle_score = self._evaluate_joint_angles(ankle_angles, 'ankle', age_adjustment)
        
        # 加权平均
        score = (hip_score * 0.4 + knee_score * 0.35 + ankle_score * 0.25)
        
        # 角度范围评估
        hip_range = angle_ranges.get('hip', {}).get('flexion', 35)
        knee_range = angle_ranges.get('knee', {}).get('flexion', 45)
        ankle_range = angle_ranges.get('ankle', {}).get('flexion', 20)
        
        # 运动范围不足扣分
        if hip_range < 30 * age_adjustment:
            score -= 10
        if knee_range < 40 * age_adjustment:
            score -= 15
        if ankle_range < 15 * age_adjustment:
            score -= 8
        
        return max(0, min(100, score))
    
    def _assess_joint_power(self, power_metrics: Dict[str, Any], patient_info: Dict[str, Any]) -> float:
        """关节力矩功率评估"""
        score = 100
        age_adjustment = self._get_age_adjustment(patient_info.get('age', 65))
        gender_adjustment = self._get_gender_adjustment(patient_info.get('gender', 'male'))
        patient_weight = patient_info.get('weight', 70)
        
        # 各关节功率评估
        hip_power = power_metrics.get('hip_power', {'normalized_power': 1.2})
        knee_power = power_metrics.get('knee_power', {'normalized_power': 0.8})
        ankle_power = power_metrics.get('ankle_power', {'normalized_power': 2.0})
        
        hip_power_score = self._evaluate_joint_power(hip_power, 'hip', patient_weight)
        knee_power_score = self._evaluate_joint_power(knee_power, 'knee', patient_weight)
        ankle_power_score = self._evaluate_joint_power(ankle_power, 'ankle', patient_weight)
        
        # 加权平均
        score = (hip_power_score * 0.3 + knee_power_score * 0.35 + ankle_power_score * 0.35)
        
        # 关节协调性评估
        joint_coordination = power_metrics.get('joint_coordination', 85)
        if joint_coordination < 80:
            score -= (80 - joint_coordination) * 0.3
        
        # 步态效率评估
        gait_efficiency = power_metrics.get('gait_efficiency', {}).get('efficiency', 65)
        if gait_efficiency < 60:
            score -= (60 - gait_efficiency) * 0.2
        
        return max(0, min(100, score * age_adjustment * gender_adjustment))
    
    def _assess_posture(self, posture_metrics: Dict[str, float], patient_info: Dict[str, Any]) -> float:
        """姿态控制评估"""
        score = 100
        age_adjustment = self._get_age_adjustment(patient_info.get('age', 65))
        
        # COP摆动面积评估 (期望值: <4 cm²)
        cop_area = posture_metrics.get('cop_area', 3.0)
        expected_cop_area = 4 * (1 / age_adjustment)
        if cop_area > expected_cop_area:
            score -= (cop_area - expected_cop_area) / expected_cop_area * 30
        
        # COP轨迹长度评估 (期望值: 15-25 cm)
        cop_path_length = posture_metrics.get('cop_path_length', 20)
        expected_path_length = 20 * (1 / age_adjustment)
        path_length_deviation = abs(cop_path_length - expected_path_length) / expected_path_length
        score -= path_length_deviation * 25
        
        # 摆动速度评估 (期望值: <2 cm/s)
        sway_velocity = posture_metrics.get('sway_velocity', 1.5)
        expected_sway_velocity = 2 * (1 / age_adjustment)
        if sway_velocity > expected_sway_velocity:
            score -= (sway_velocity - expected_sway_velocity) / expected_sway_velocity * 25
        
        # 稳定性指数评估
        stability_index = posture_metrics.get('stability_index', 85)
        if stability_index < 80:
            score -= (80 - stability_index) * 0.25
        
        return max(0, min(100, score * age_adjustment))
    
    def _assess_ground_reaction_force(self, grf_metrics: Dict[str, Any], patient_info: Dict[str, Any]) -> float:
        """地面反力评估"""
        score = 100
        age_adjustment = self._get_age_adjustment(patient_info.get('age', 65))
        body_weight = patient_info.get('weight', 70) * 9.8
        
        # 获取三方向反力数据
        vertical = grf_metrics.get('vertical', {'peak': body_weight * 1.1})
        antero_posterior = grf_metrics.get('antero_posterior', {'peak': body_weight * 0.15})
        medio_lateral = grf_metrics.get('medio_lateral', {'peak': body_weight * 0.08})
        
        # 垂直反力评估 (期望值: 1.0-1.2 BW)
        vertical_force_ratio = vertical['peak'] / body_weight
        expected_vertical_ratio = 1.1 * age_adjustment
        vertical_deviation = abs(vertical_force_ratio - expected_vertical_ratio) / expected_vertical_ratio
        score -= vertical_deviation * 30
        
        # 前后反力评估 (期望值: <0.2 BW)
        ap_force_ratio = antero_posterior['peak'] / body_weight
        expected_ap_ratio = 0.15 * (1 / age_adjustment)
        if ap_force_ratio > expected_ap_ratio:
            score -= (ap_force_ratio - expected_ap_ratio) / expected_ap_ratio * 25
        
        # 左右反力评估 (期望值: <0.1 BW)
        ml_force_ratio = medio_lateral['peak'] / body_weight
        expected_ml_ratio = 0.08 * (1 / age_adjustment)
        if ml_force_ratio > expected_ml_ratio:
            score -= (ml_force_ratio - expected_ml_ratio) / expected_ml_ratio * 20
        
        # 力的平衡性和对称性评估
        force_balance = grf_metrics.get('force_balance', 85)
        symmetry_index = grf_metrics.get('symmetry_index', 90)
        
        score -= (100 - force_balance) * 0.15
        score -= (100 - symmetry_index) * 0.1
        
        return max(0, min(100, score * age_adjustment))
    
    def generate_diagnostic_suggestions(
        self, 
        assessment: AIAssessment, 
        all_metrics: ComprehensiveMetrics
    ) -> List[DiagnosticSuggestion]:
        """智能诊断建议生成"""
        suggestions = []
        
        # 基于各维度评分生成针对性建议
        if assessment.步态时间 < 70:
            suggestions.append(DiagnosticSuggestion(
                category=SuggestionCategory.REHABILITATION,
                priority=Priority.HIGH,
                suggestion='进行步态节律训练，改善步长和步频协调性',
                expected_outcome='提高步态时间参数10-15分',
                timeframe='4-6周',
                target_metrics=['步长', '步频', '步行速度']
            ))
        
        if assessment.关节角域 < 70:
            suggestions.append(DiagnosticSuggestion(
                category=SuggestionCategory.REHABILITATION,
                priority=Priority.HIGH,
                suggestion='关节活动度训练，重点改善屈曲受限关节',
                expected_outcome='关节活动范围增加15-20°',
                timeframe='6-8周',
                target_metrics=['髋关节屈曲', '膝关节屈曲', '踝关节屈曲']
            ))
        
        if assessment.关节力能 < 60:
            suggestions.append(DiagnosticSuggestion(
                category=SuggestionCategory.REHABILITATION,
                priority=Priority.HIGH,
                suggestion='力量训练结合功能性训练，提升关节功率输出',
                expected_outcome='关节功率提升20-30%',
                timeframe='8-12周',
                target_metrics=['髋关节功率', '膝关节功率', '踝关节功率']
            ))
        
        if assessment.姿态 < 70:
            suggestions.append(DiagnosticSuggestion(
                category=SuggestionCategory.REHABILITATION,
                priority=Priority.MEDIUM,
                suggestion='平衡训练和本体感觉训练，改善姿态控制',
                expected_outcome='平衡能力提升15-20分',
                timeframe='4-6周',
                target_metrics=['COP摆动面积', '稳定性指数']
            ))
        
        if assessment.地返力 < 70:
            suggestions.append(DiagnosticSuggestion(
                category=SuggestionCategory.REHABILITATION,
                priority=Priority.MEDIUM,
                suggestion='地面反力模式训练，学习正确的力量传递技巧',
                expected_outcome='地面反力模式优化10-15%',
                timeframe='6-8周',
                target_metrics=['垂直反力', '力的对称性']
            ))
        
        # 综合风险建议
        if assessment.risk_level in [RiskLevel.HIGH, RiskLevel.SEVERE]:
            suggestions.append(DiagnosticSuggestion(
                category=SuggestionCategory.MEDICAL,
                priority=Priority.HIGH,
                suggestion='建议进行详细的医学评估，排除潜在疾病因素',
                expected_outcome='明确诊断，制定针对性治疗方案',
                timeframe='2-4周',
                target_metrics=['整体风险等级']
            ))
        
        # 生活方式建议
        if assessment.overall_score < 80:
            suggestions.append(DiagnosticSuggestion(
                category=SuggestionCategory.LIFESTYLE,
                priority=Priority.MEDIUM,
                suggestion='增加日常活动量，规律进行有氧运动',
                expected_outcome='整体运动能力提升5-10分',
                timeframe='持续进行',
                target_metrics=['综合评分']
            ))
        
        # 监测建议
        suggestions.append(DiagnosticSuggestion(
            category=SuggestionCategory.MONITORING,
            priority=Priority.LOW,
            suggestion='定期进行步态分析复查，监测康复进展',
            expected_outcome='及时发现问题，调整治疗方案',
            timeframe='每4-6周',
            target_metrics=['所有指标']
        ))
        
        return suggestions
    
    def generate_detailed_report(
        self, 
        assessment: AIAssessment, 
        all_metrics: ComprehensiveMetrics
    ) -> AssessmentDetail:
        """评估明细生成"""
        评估明细 = []
        abnormal_findings = []
        
        # 基于各维度评分生成评估明细
        if assessment.步态时间 < 85:
            gait_metrics = all_metrics.gait_metrics
            if gait_metrics.get('step_length', 0.7) < 0.5:
                评估明细.append('步长明显偏短，可能存在下肢力量不足或关节活动受限')
            if gait_metrics.get('cadence', 110) < 100:
                评估明细.append('步频偏低，步态节律性较差')
            if gait_metrics.get('velocity', 1.3) < 1.0:
                评估明细.append('步行速度偏慢，日常活动能力可能受影响')
            if gait_metrics.get('symmetry_index', 95) < 90:
                评估明细.append('步态不对称，可能存在单侧肢体功能障碍')
        
        if assessment.关节角域 < 85:
            joint_metrics = all_metrics.joint_metrics
            average_angles = joint_metrics.get('average_angles', {})
            
            hip_flexion = average_angles.get('hip', {}).get('flexion', 45)
            if hip_flexion < 40:
                评估明细.append('髋关节屈曲幅度明显低于正常人群')
            
            knee_flexion = average_angles.get('knee', {}).get('flexion', 155)
            if knee_flexion < 150:
                评估明细.append('膝关节屈曲幅度明显低于正常人群')
            
            ankle_flexion = average_angles.get('ankle', {}).get('flexion', 10)
            if ankle_flexion < 5:
                评估明细.append('踝关节屈曲时前屈角度明显低于正常人群')
        
        if assessment.姿态 < 85:
            posture_metrics = all_metrics.posture_metrics
            if posture_metrics.get('cop_area', 3.0) > 5:
                评估明细.append('重心摆动面积较大，姿态控制能力较差')
            if posture_metrics.get('cop_path_length', 20) > 30:
                评估明细.append('重心轨迹长度偏长，平衡调节较为频繁')
            
            评估明细.append('重心位置重心位移幅度较正常人群偏大')
            评估明细.append('重心外摆幅度明显低于正常人群')
            评估明细.append('重心前摆幅度明显低于正常人群')
        
        # 生成异常发现
        if assessment.overall_score < 70:
            abnormal_findings.append({
                'severity': 'severe' if assessment.overall_score < 50 else 'moderate',
                'description': '综合步态功能明显异常，存在多系统功能障碍',
                'affected_systems': ['运动系统', '神经系统', '平衡系统']
            })
        
        # 计算功能性评估
        functional_capacity = {
            'mobility_score': round((assessment.步态时间 + assessment.步态时域) / 2),
            'stability_score': assessment.姿态,
            'strength_score': assessment.关节力能,
            'coordination_score': assessment.关节角域
        }
        
        # 计算疾病风险
        disease_risk = {
            'sarcopenia_risk': round(100 - assessment.关节力能),
            'fall_risk': round(100 - assessment.姿态),
            'mobility_disorder_risk': round(100 - assessment.overall_score)
        }
        
        return AssessmentDetail(
            评估明细=评估明细,
            abnormal_findings=abnormal_findings,
            functional_capacity=functional_capacity,
            disease_risk=disease_risk
        )
    
    # 辅助方法
    
    def _get_age_adjustment(self, age: float) -> float:
        """获取年龄调整系数"""
        for key, range_data in self.AI_PARAMETERS['AGE_COEFFICIENTS'].items():
            if range_data['min'] <= age <= range_data['max']:
                return range_data['factor']
        return 0.75  # 默认为高龄系数
    
    def _get_gender_adjustment(self, gender: str) -> float:
        """获取性别调整系数"""
        return self.AI_PARAMETERS['GENDER_COEFFICIENTS'].get(gender, 1.0)
    
    def _calculate_overall_score(self, dimension_scores: Dict[str, float]) -> float:
        """计算综合评分"""
        weighted_sum = 0
        total_weight = 0
        
        for dimension, score in dimension_scores.items():
            weight = self.AI_PARAMETERS['DIMENSION_WEIGHTS'].get(dimension, 0)
            weighted_sum += score * weight
            total_weight += weight
        
        return round(weighted_sum / total_weight) if total_weight > 0 else 0
    
    def _determine_risk_level(self, overall_score: float) -> RiskLevel:
        """确定风险等级"""
        if overall_score >= self.AI_PARAMETERS['RISK_THRESHOLDS']['low']:
            return RiskLevel.LOW
        elif overall_score >= self.AI_PARAMETERS['RISK_THRESHOLDS']['moderate']:
            return RiskLevel.MODERATE
        elif overall_score >= self.AI_PARAMETERS['RISK_THRESHOLDS']['high']:
            return RiskLevel.HIGH
        else:
            return RiskLevel.SEVERE
    
    def _calculate_confidence(self, all_metrics: ComprehensiveMetrics) -> float:
        """计算置信度"""
        # 数据质量评估
        data_quality = self._assess_data_quality(all_metrics)
        
        # 数据一致性评估
        consistency = self._assess_data_consistency(all_metrics)
        
        # 数据完整性评估
        completeness = self._assess_data_completeness(all_metrics)
        
        # 数据可靠性评估
        reliability = self._assess_data_reliability(all_metrics)
        
        confidence = (
            data_quality * self.AI_PARAMETERS['CONFIDENCE_FACTORS']['data_quality'] +
            consistency * self.AI_PARAMETERS['CONFIDENCE_FACTORS']['consistency'] +
            completeness * self.AI_PARAMETERS['CONFIDENCE_FACTORS']['completeness'] +
            reliability * self.AI_PARAMETERS['CONFIDENCE_FACTORS']['reliability']
        )
        
        return round(confidence)
    
    def _evaluate_joint_angles(
        self, 
        angles: Dict[str, float], 
        joint_type: str, 
        age_adjustment: float
    ) -> float:
        """评估关节角度"""
        score = 100
        
        if joint_type == 'hip':
            if angles.get('flexion', 45) < 40 * age_adjustment:
                score -= 20
            if abs(angles.get('abduction', 0)) > 15:
                score -= 10
        elif joint_type == 'knee':
            if angles.get('flexion', 155) < 150 * age_adjustment:
                score -= 25
            if abs(angles.get('rotation', 0)) > 5:
                score -= 10
        elif joint_type == 'ankle':
            if angles.get('flexion', 10) < 5 * age_adjustment:
                score -= 15
            if abs(angles.get('abduction', 0)) > 10:
                score -= 10
        
        return max(0, score)
    
    def _evaluate_joint_power(
        self, 
        power_metrics: Dict[str, float], 
        joint_type: str, 
        body_weight: float
    ) -> float:
        """评估关节功率"""
        normalized_power = power_metrics.get('normalized_power', 1.0)
        expected_power = 1.0  # 默认期望功率 (W/kg)
        
        if joint_type == 'hip':
            expected_power = 1.5
        elif joint_type == 'knee':
            expected_power = 1.0
        elif joint_type == 'ankle':
            expected_power = 2.5
        
        deviation = abs(normalized_power - expected_power) / expected_power
        return max(0, 100 - deviation * 50)
    
    def _assess_data_quality(self, all_metrics: ComprehensiveMetrics) -> float:
        """评估数据质量"""
        score = 100
        gait_metrics = all_metrics.gait_metrics
        
        # 检查数据范围合理性
        step_length = gait_metrics.get('step_length', 0.7)
        if step_length < 0.2 or step_length > 1.2:
            score -= 20
        
        cadence = gait_metrics.get('cadence', 110)
        if cadence < 60 or cadence > 180:
            score -= 15
        
        velocity = gait_metrics.get('velocity', 1.3)
        if velocity < 0.3 or velocity > 2.5:
            score -= 15
        
        return max(0, score)
    
    def _assess_data_consistency(self, all_metrics: ComprehensiveMetrics) -> float:
        """评估数据一致性"""
        score = 100
        gait_metrics = all_metrics.gait_metrics
        
        # 检查步态参数的一致性
        step_length = gait_metrics.get('step_length', 0.7)
        cadence = gait_metrics.get('cadence', 110)
        velocity = gait_metrics.get('velocity', 1.3)
        
        expected_velocity = step_length * cadence / 60
        velocity_consistency = abs(velocity - expected_velocity) / expected_velocity if expected_velocity > 0 else 0
        score -= velocity_consistency * 30
        
        return max(0, score)
    
    def _assess_data_completeness(self, all_metrics: ComprehensiveMetrics) -> float:
        """评估数据完整性"""
        score = 100
        missing_data = 0
        
        # 检查关键数据是否缺失
        joint_metrics = all_metrics.joint_metrics
        if not joint_metrics.get('hip_flexion'):
            missing_data += 1
        if not joint_metrics.get('knee_flexion'):
            missing_data += 1
        if not joint_metrics.get('ankle_flexion'):
            missing_data += 1
        
        grf_metrics = all_metrics.grf_metrics
        if not grf_metrics.get('vertical', {}).get('time_series'):
            missing_data += 1
        
        score -= missing_data * 25
        
        return max(0, score)
    
    def _assess_data_reliability(self, all_metrics: ComprehensiveMetrics) -> float:
        """评估数据可靠性"""
        score = 100
        patient_info = all_metrics.patient_info
        
        # 基于患者信息的可靠性评估
        age = patient_info.get('age', 65)
        if age < 18 or age > 100:
            score -= 20
        
        weight = patient_info.get('weight', 70)
        if weight < 30 or weight > 200:
            score -= 15
        
        height = patient_info.get('height', 170)
        if height < 120 or height > 220:
            score -= 15
        
        return max(0, score)


# 创建全局实例
ai_assessment_engine = AIAssessmentEngine()