#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
标准化步态评估与医学建议模块
基于《步态分析标准化执行规划文档》实现
"""

import numpy as np
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass
from enum import Enum

class GaitAbnormalityType(Enum):
    """步态异常类型分类"""
    HEMIPLEGIC = "偏瘫步态"  # 脑卒中后常见
    PARKINSONIAN = "帕金森步态"  # 小碎步、冻结步态
    ATAXIC = "共济失调步态"  # 小脑疾病
    STEPPAGE = "跨阈步态"  # 足下垂
    TRENDELENBURG = "Trendelenburg步态"  # 髋关节外展肌无力
    ANTALGIC = "疼痛性步态"  # 避痛步态
    SENILE = "老年性步态"  # 谨慎步态
    NORMAL = "正常步态"

@dataclass
class StandardizedReference:
    """标准化参考值（基于文档标准）"""
    # 时空参数标准值
    step_length: Tuple[float, float] = (50.0, 80.0)  # cm
    stride_length: Tuple[float, float] = (100.0, 160.0)  # cm
    step_width: Tuple[float, float] = (10.0, 20.0)  # cm
    walking_speed: Tuple[float, float] = (1.0, 1.5)  # m/s
    cadence: Tuple[float, float] = (100.0, 120.0)  # 步/分
    
    # 步态周期标准值（百分比）
    stance_phase: Tuple[float, float] = (58.0, 62.0)  # 支撑相60%±2%
    swing_phase: Tuple[float, float] = (38.0, 42.0)  # 摆动相40%±2%
    double_support: Tuple[float, float] = (18.0, 22.0)  # 双支撑相20%±2%
    
    # 步态周期细分（基于文档）
    initial_contact: Tuple[float, float] = (0.0, 2.0)  # 首次着地
    loading_response: Tuple[float, float] = (8.0, 12.0)  # 承重反应期
    mid_stance: Tuple[float, float] = (18.0, 22.0)  # 站立中期
    terminal_stance: Tuple[float, float] = (18.0, 22.0)  # 站立末期
    pre_swing: Tuple[float, float] = (10.0, 14.0)  # 迈步前期
    
    # 对称性指数阈值
    symmetry_excellent: float = 5.0  # SI < 5% 优秀
    symmetry_good: float = 10.0  # SI 5-10% 良好
    symmetry_fair: float = 15.0  # SI 10-15% 一般
    
    # 年龄相关调整系数
    age_adjustment = {
        'child': {'speed': 1.1, 'cadence': 1.2},  # <18岁
        'young': {'speed': 1.0, 'cadence': 1.0},  # 18-35岁
        'middle': {'speed': 0.95, 'cadence': 0.95},  # 35-50岁
        'elderly': {'speed': 0.85, 'cadence': 0.9},  # 50-70岁
        'senior': {'speed': 0.7, 'cadence': 0.85}  # >70岁
    }

class StandardizedGaitAssessment:
    """标准化步态评估系统"""
    
    def __init__(self):
        self.reference = StandardizedReference()
        self.abnormality_patterns = self._init_abnormality_patterns()
        
    def _init_abnormality_patterns(self) -> Dict:
        """初始化异常步态模式识别规则"""
        return {
            GaitAbnormalityType.HEMIPLEGIC: {
                'indicators': {
                    'symmetry_index': lambda x: x > 20,  # 严重不对称
                    'swing_phase_affected': lambda x: x < 30,  # 患侧摆动相减少
                    'step_length_ratio': lambda l, r: abs(l-r)/max(l,r) > 0.3,  # 步长差异大
                    'circumduction': True  # 环形步态
                },
                'description': '偏瘫步态：患侧下肢僵直，摆动相减少，呈环形摆动',
                'common_causes': ['脑卒中', '脑外伤', '脑肿瘤'],
                'risk_level': 'high'
            },
            GaitAbnormalityType.PARKINSONIAN: {
                'indicators': {
                    'step_length': lambda x: x < 40,  # 步长明显减小
                    'cadence': lambda x: x > 130,  # 步频增快（小碎步）
                    'arm_swing': lambda x: x < 10,  # 臂摆减少
                    'freezing_episodes': True  # 冻结现象
                },
                'description': '帕金森步态：小碎步、前冲步态、起步困难、冻结',
                'common_causes': ['帕金森病', '帕金森综合征', '药物副作用'],
                'risk_level': 'high'
            },
            GaitAbnormalityType.ATAXIC: {
                'indicators': {
                    'step_width': lambda x: x > 25,  # 步宽增大
                    'step_length_variability': lambda x: x > 20,  # 步长变异大
                    'lateral_deviation': lambda x: x > 15,  # 左右摇摆
                },
                'description': '共济失调步态：步基宽、步态不稳、左右摇摆',
                'common_causes': ['小脑疾病', '前庭功能障碍', '深感觉障碍'],
                'risk_level': 'medium'
            },
            GaitAbnormalityType.ANTALGIC: {
                'indicators': {
                    'stance_phase_affected': lambda x: x < 55,  # 患侧支撑相减少
                    'walking_speed': lambda x: x < 0.8,  # 步速减慢
                    'asymmetric_weight_bearing': True  # 不对称负重
                },
                'description': '疼痛性步态：患侧支撑相缩短，避免负重',
                'common_causes': ['关节炎', '外伤', '骨折愈合期'],
                'risk_level': 'medium'
            },
            GaitAbnormalityType.SENILE: {
                'indicators': {
                    'walking_speed': lambda x: x < 0.9,  # 步速慢
                    'step_length': lambda x: x < 50,  # 步长短
                    'double_support': lambda x: x > 25,  # 双支撑相延长
                    'arm_swing': lambda x: x < 20,  # 臂摆减少
                },
                'description': '老年性步态：谨慎步态、步速慢、双支撑期延长',
                'common_causes': ['正常老化', '平衡功能下降', '肌力减退'],
                'risk_level': 'low'
            }
        }
    
    def assess_gait_quality(self, gait_params: Dict) -> Dict:
        """
        综合评估步态质量
        
        Args:
            gait_params: 步态参数字典
            
        Returns:
            评估结果字典，包含质量评分、异常指标、风险等级
        """
        assessment = {
            'overall_score': 0,
            'quality_grade': '',
            'abnormal_indicators': [],
            'suspected_patterns': [],
            'risk_assessment': {},
            'detailed_evaluation': {},
            'recommendations': []
        }
        
        # 1. 计算各维度评分
        scores = {}
        
        # 时空参数评分
        scores['temporal_spatial'] = self._assess_temporal_spatial(gait_params)
        
        # 对称性评分
        scores['symmetry'] = self._assess_symmetry(gait_params)
        
        # 稳定性评分
        scores['stability'] = self._assess_stability(gait_params)
        
        # 步态周期评分
        scores['gait_cycle'] = self._assess_gait_cycle(gait_params)
        
        # 2. 计算综合评分（加权平均）
        weights = {
            'temporal_spatial': 0.3,
            'symmetry': 0.25,
            'stability': 0.25,
            'gait_cycle': 0.2
        }
        
        overall_score = sum(scores[k] * weights[k] for k in scores)
        assessment['overall_score'] = round(overall_score, 1)
        assessment['detailed_evaluation'] = scores
        
        # 3. 评定质量等级
        if overall_score >= 90:
            assessment['quality_grade'] = '优秀'
        elif overall_score >= 80:
            assessment['quality_grade'] = '良好'
        elif overall_score >= 70:
            assessment['quality_grade'] = '一般'
        elif overall_score >= 60:
            assessment['quality_grade'] = '较差'
        else:
            assessment['quality_grade'] = '异常'
        
        # 4. 识别异常指标
        assessment['abnormal_indicators'] = self._identify_abnormalities(gait_params)
        
        # 5. 模式识别
        assessment['suspected_patterns'] = self._detect_gait_patterns(gait_params)
        
        # 6. 风险评估
        assessment['risk_assessment'] = self._assess_fall_risk(gait_params)
        
        # 7. 生成建议
        assessment['recommendations'] = self._generate_recommendations(assessment)
        
        return assessment
    
    def _assess_temporal_spatial(self, params: Dict) -> float:
        """评估时空参数"""
        score = 100.0
        penalties = []
        
        # 步速评估
        speed = params.get('average_velocity', 0)
        if speed < self.reference.walking_speed[0]:
            penalty = (self.reference.walking_speed[0] - speed) / self.reference.walking_speed[0] * 30
            penalties.append(min(30, penalty))
        elif speed > self.reference.walking_speed[1]:
            penalty = (speed - self.reference.walking_speed[1]) / self.reference.walking_speed[1] * 20
            penalties.append(min(20, penalty))
        
        # 步长评估
        step_length = params.get('average_step_length', 0)
        if step_length < self.reference.step_length[0]:
            penalty = (self.reference.step_length[0] - step_length) / self.reference.step_length[0] * 25
            penalties.append(min(25, penalty))
        elif step_length > self.reference.step_length[1]:
            penalty = (step_length - self.reference.step_length[1]) / self.reference.step_length[1] * 15
            penalties.append(min(15, penalty))
        
        # 步频评估
        cadence = params.get('cadence', 0)
        if cadence < self.reference.cadence[0]:
            penalty = (self.reference.cadence[0] - cadence) / self.reference.cadence[0] * 20
            penalties.append(min(20, penalty))
        elif cadence > self.reference.cadence[1]:
            penalty = (cadence - self.reference.cadence[1]) / self.reference.cadence[1] * 15
            penalties.append(min(15, penalty))
        
        return max(0, score - sum(penalties))
    
    def _assess_symmetry(self, params: Dict) -> float:
        """评估对称性"""
        score = 100.0
        
        # 获取对称性指数
        symmetry_indices = params.get('symmetry_indices', {})
        step_si = symmetry_indices.get('step_length_si', 0)
        cadence_si = symmetry_indices.get('cadence_si', 0)
        swing_si = symmetry_indices.get('swing_time_si', 0)
        
        # 根据SI值扣分
        for si in [step_si, cadence_si, swing_si]:
            if si < self.reference.symmetry_excellent:
                continue  # 优秀，不扣分
            elif si < self.reference.symmetry_good:
                score -= 5  # 良好，轻微扣分
            elif si < self.reference.symmetry_fair:
                score -= 10  # 一般，中度扣分
            else:
                score -= 20  # 较差，重度扣分
        
        return max(0, score)
    
    def _assess_stability(self, params: Dict) -> float:
        """评估稳定性"""
        score = 100.0
        
        # COP稳定性指标
        cop_stability = params.get('cop_stability', {})
        
        # 椭圆面积评估（越小越稳定）
        ellipse_area = cop_stability.get('ellipse_area', 0)
        if ellipse_area > 10:
            score -= 30
        elif ellipse_area > 5:
            score -= 15
        elif ellipse_area > 2:
            score -= 5
        
        # 双支撑相评估（正常20%±2%）
        double_support = params.get('gait_phases', {}).get('double_support', 20)
        if double_support < self.reference.double_support[0]:
            score -= 15  # 双支撑过短，稳定性差
        elif double_support > self.reference.double_support[1]:
            score -= 10  # 双支撑过长，谨慎步态
        
        # 步宽评估
        step_width = params.get('step_width', 15)
        if step_width > 25:
            score -= 20  # 步基过宽，稳定性问题
        
        return max(0, score)
    
    def _assess_gait_cycle(self, params: Dict) -> float:
        """评估步态周期"""
        score = 100.0
        phases = params.get('gait_phases', {})
        
        # 支撑相评估
        stance = phases.get('stance_phase', 60)
        if not (self.reference.stance_phase[0] <= stance <= self.reference.stance_phase[1]):
            deviation = min(abs(stance - self.reference.stance_phase[0]),
                          abs(stance - self.reference.stance_phase[1]))
            score -= min(30, deviation * 2)
        
        # 摆动相评估
        swing = phases.get('swing_phase', 40)
        if not (self.reference.swing_phase[0] <= swing <= self.reference.swing_phase[1]):
            deviation = min(abs(swing - self.reference.swing_phase[0]),
                          abs(swing - self.reference.swing_phase[1]))
            score -= min(30, deviation * 2)
        
        return max(0, score)
    
    def _identify_abnormalities(self, params: Dict) -> List[Dict]:
        """识别异常指标"""
        abnormalities = []
        
        # 检查各项参数是否异常
        checks = [
            ('步速过慢', params.get('average_velocity', 1.2) < 0.8, 'high'),
            ('步速过快', params.get('average_velocity', 1.2) > 1.8, 'medium'),
            ('步长过短', params.get('average_step_length', 60) < 40, 'high'),
            ('步频异常', not (80 <= params.get('cadence', 110) <= 140), 'medium'),
            ('严重不对称', params.get('symmetry_indices', {}).get('overall_si', 0) > 15, 'high'),
            ('双支撑期延长', params.get('gait_phases', {}).get('double_support', 20) > 25, 'medium'),
            ('摆动相缩短', params.get('gait_phases', {}).get('swing_phase', 40) < 35, 'medium'),
        ]
        
        for name, condition, severity in checks:
            if condition:
                abnormalities.append({
                    'indicator': name,
                    'severity': severity,
                    'value': self._get_actual_value(name, params)
                })
        
        return abnormalities
    
    def _detect_gait_patterns(self, params: Dict) -> List[Dict]:
        """检测异常步态模式"""
        detected_patterns = []
        
        for pattern_type, pattern_rules in self.abnormality_patterns.items():
            match_score = 0
            matched_indicators = []
            
            for indicator_name, check_func in pattern_rules['indicators'].items():
                if indicator_name == 'step_length_ratio':
                    left = params.get('gait_parameters', {}).get('left_foot', {}).get('average_step_length_m', 0.5) * 100
                    right = params.get('gait_parameters', {}).get('right_foot', {}).get('average_step_length_m', 0.5) * 100
                    if check_func(left, right):
                        match_score += 1
                        matched_indicators.append(indicator_name)
                elif indicator_name in ['circumduction', 'freezing_episodes', 'asymmetric_weight_bearing']:
                    # 这些需要额外的检测逻辑
                    continue
                else:
                    value = self._extract_pattern_value(indicator_name, params)
                    if value is not None and callable(check_func) and check_func(value):
                        match_score += 1
                        matched_indicators.append(indicator_name)
            
            # 如果匹配度超过50%，认为可能存在该模式
            if match_score >= len(pattern_rules['indicators']) * 0.5:
                detected_patterns.append({
                    'pattern_type': pattern_type.value,
                    'confidence': match_score / len(pattern_rules['indicators']),
                    'matched_indicators': matched_indicators,
                    'description': pattern_rules['description'],
                    'common_causes': pattern_rules['common_causes'],
                    'risk_level': pattern_rules['risk_level']
                })
        
        return detected_patterns
    
    def _assess_fall_risk(self, params: Dict) -> Dict:
        """评估跌倒风险"""
        risk_factors = []
        risk_score = 0
        
        # 主要风险因素评估
        factors = [
            ('步速<0.8m/s', params.get('average_velocity', 1.2) < 0.8, 30),
            ('步长<40cm', params.get('average_step_length', 60) < 40, 25),
            ('双支撑期>25%', params.get('gait_phases', {}).get('double_support', 20) > 25, 20),
            ('对称性指数>15%', params.get('symmetry_indices', {}).get('overall_si', 0) > 15, 20),
            ('步宽>25cm', params.get('step_width', 15) > 25, 15),
            ('COP椭圆面积>10cm²', params.get('cop_stability', {}).get('ellipse_area', 0) > 10, 25),
        ]
        
        for factor_name, condition, weight in factors:
            if condition:
                risk_factors.append(factor_name)
                risk_score += weight
        
        # 确定风险等级
        if risk_score >= 60:
            risk_level = '高风险'
            risk_description = '存在多个跌倒风险因素，建议立即进行干预'
        elif risk_score >= 40:
            risk_level = '中风险'
            risk_description = '存在一定跌倒风险，建议密切观察并采取预防措施'
        elif risk_score >= 20:
            risk_level = '低风险'
            risk_description = '跌倒风险较低，建议定期评估'
        else:
            risk_level = '极低风险'
            risk_description = '步态稳定，跌倒风险极低'
        
        return {
            'risk_level': risk_level,
            'risk_score': risk_score,
            'risk_factors': risk_factors,
            'description': risk_description
        }
    
    def _generate_recommendations(self, assessment: Dict) -> List[Dict]:
        """生成个性化康复建议"""
        recommendations = []
        
        # 基于总体评分的建议
        if assessment['overall_score'] < 60:
            recommendations.append({
                'category': '紧急建议',
                'priority': 'high',
                'content': '步态功能明显异常，建议立即就医进行专业评估',
                'actions': [
                    '尽快预约康复科或神经内科',
                    '进行全面的神经肌肉骨骼系统检查',
                    '考虑使用助行器具以确保安全'
                ]
            })
        
        # 基于异常指标的建议
        for abnormal in assessment['abnormal_indicators']:
            if abnormal['indicator'] == '步速过慢':
                recommendations.append({
                    'category': '步速训练',
                    'priority': 'medium',
                    'content': '步行速度明显降低，需要进行步速提升训练',
                    'actions': [
                        '每日进行10-15分钟快走训练',
                        '使用节拍器辅助维持稳定节奏',
                        '逐渐增加步行距离和速度'
                    ]
                })
            elif abnormal['indicator'] == '严重不对称':
                recommendations.append({
                    'category': '对称性训练',
                    'priority': 'high',
                    'content': '左右步态明显不对称，需要针对性康复训练',
                    'actions': [
                        '进行单侧肢体强化训练',
                        '镜像步态训练',
                        '平衡协调性练习',
                        '考虑物理治疗介入'
                    ]
                })
            elif abnormal['indicator'] == '双支撑期延长':
                recommendations.append({
                    'category': '平衡训练',
                    'priority': 'medium',
                    'content': '双支撑期延长提示平衡能力下降',
                    'actions': [
                        '单腿站立训练（每次30秒，每日3组）',
                        '太极拳或瑜伽练习',
                        '使用平衡板进行训练',
                        '强化核心肌群'
                    ]
                })
        
        # 基于检测到的步态模式的建议
        for pattern in assessment['suspected_patterns']:
            if pattern['pattern_type'] == GaitAbnormalityType.PARKINSONIAN.value:
                recommendations.append({
                    'category': '帕金森步态管理',
                    'priority': 'high',
                    'content': '检测到帕金森样步态特征',
                    'actions': [
                        '神经内科专科评估',
                        '药物治疗优化',
                        '节律性听觉提示训练',
                        '大步幅练习',
                        '防冻结步态策略训练'
                    ]
                })
            elif pattern['pattern_type'] == GaitAbnormalityType.HEMIPLEGIC.value:
                recommendations.append({
                    'category': '偏瘫康复',
                    'priority': 'high',
                    'content': '检测到偏瘫步态特征',
                    'actions': [
                        '专业康复治疗',
                        '患侧负重训练',
                        '步态再训练',
                        '考虑使用踝足矫形器(AFO)',
                        '肌肉电刺激治疗'
                    ]
                })
        
        # 基于跌倒风险的建议
        risk = assessment['risk_assessment']
        if risk['risk_level'] in ['高风险', '中风险']:
            recommendations.append({
                'category': '跌倒预防',
                'priority': 'high',
                'content': f"跌倒风险评估为{risk['risk_level']}",
                'actions': [
                    '家居环境改造（移除地毯、安装扶手）',
                    '视力检查和矫正',
                    '药物评估（避免引起头晕的药物）',
                    '穿着防滑鞋',
                    '使用合适的助行器具',
                    '定期进行平衡和力量训练'
                ]
            })
        
        # 通用健康建议
        recommendations.append({
            'category': '日常保健',
            'priority': 'low',
            'content': '维持和改善步态功能的日常建议',
            'actions': [
                '每日步行30分钟',
                '保持健康体重',
                '充足的营养摄入（特别是蛋白质和维生素D）',
                '定期体检和步态评估',
                '参加团体运动课程提高积极性'
            ]
        })
        
        return recommendations
    
    def _extract_pattern_value(self, indicator_name: str, params: Dict) -> Optional[float]:
        """从参数中提取特定指标值"""
        mapping = {
            'step_length': lambda: params.get('average_step_length', 0),
            'cadence': lambda: params.get('cadence', 0),
            'arm_swing': lambda: params.get('arm_swing_amplitude', 30),  # 需要额外计算
            'step_width': lambda: params.get('step_width', 15),
            'step_length_variability': lambda: params.get('step_length_cv', 5),  # 变异系数
            'lateral_deviation': lambda: params.get('cop_stability', {}).get('ml_range', 0) * 10,
            'stance_phase_affected': lambda: min(
                params.get('gait_phases', {}).get('left_stance_phase', 60),
                params.get('gait_phases', {}).get('right_stance_phase', 60)
            ),
            'walking_speed': lambda: params.get('average_velocity', 0),
            'swing_phase_affected': lambda: min(
                params.get('gait_phases', {}).get('left_swing_phase', 40),
                params.get('gait_phases', {}).get('right_swing_phase', 40)
            ),
            'double_support': lambda: params.get('gait_phases', {}).get('double_support', 20),
        }
        
        if indicator_name in mapping:
            return mapping[indicator_name]()
        return None
    
    def _get_actual_value(self, indicator_name: str, params: Dict) -> str:
        """获取实际参数值的字符串表示"""
        value_map = {
            '步速过慢': f"{params.get('average_velocity', 0):.2f} m/s",
            '步速过快': f"{params.get('average_velocity', 0):.2f} m/s",
            '步长过短': f"{params.get('average_step_length', 0):.1f} cm",
            '步频异常': f"{params.get('cadence', 0):.1f} 步/分",
            '严重不对称': f"{params.get('symmetry_indices', {}).get('overall_si', 0):.1f}%",
            '双支撑期延长': f"{params.get('gait_phases', {}).get('double_support', 0):.1f}%",
            '摆动相缩短': f"{params.get('gait_phases', {}).get('swing_phase', 0):.1f}%",
        }
        return value_map.get(indicator_name, 'N/A')

def generate_clinical_report_section(assessment: Dict) -> str:
    """生成临床评估报告章节"""
    
    report = f"""
    ============================================
    标准化步态分析临床评估报告
    ============================================
    
    一、综合评估结果
    ------------------
    总体评分：{assessment['overall_score']}/100
    质量等级：{assessment['quality_grade']}
    
    各维度评分：
    - 时空参数：{assessment['detailed_evaluation'].get('temporal_spatial', 0):.1f}/100
    - 对称性：{assessment['detailed_evaluation'].get('symmetry', 0):.1f}/100
    - 稳定性：{assessment['detailed_evaluation'].get('stability', 0):.1f}/100
    - 步态周期：{assessment['detailed_evaluation'].get('gait_cycle', 0):.1f}/100
    
    二、异常指标
    ------------------
    """
    
    if assessment['abnormal_indicators']:
        for abnormal in assessment['abnormal_indicators']:
            severity_cn = {'high': '严重', 'medium': '中度', 'low': '轻度'}.get(abnormal['severity'], '未知')
            report += f"• {abnormal['indicator']} ({severity_cn}): {abnormal['value']}\n    "
    else:
        report += "未发现明显异常指标\n    "
    
    report += """
    三、步态模式识别
    ------------------
    """
    
    if assessment['suspected_patterns']:
        for pattern in assessment['suspected_patterns']:
            report += f"""
    【{pattern['pattern_type']}】
    置信度：{pattern['confidence']*100:.1f}%
    描述：{pattern['description']}
    可能原因：{', '.join(pattern['common_causes'])}
    风险等级：{pattern['risk_level']}
    匹配指标：{', '.join(pattern['matched_indicators'])}
    """
    else:
        report += "未检测到特异性异常步态模式\n    "
    
    report += f"""
    四、跌倒风险评估
    ------------------
    风险等级：{assessment['risk_assessment']['risk_level']}
    风险评分：{assessment['risk_assessment']['risk_score']}/100
    {assessment['risk_assessment']['description']}
    
    风险因素：
    """
    
    if assessment['risk_assessment']['risk_factors']:
        for factor in assessment['risk_assessment']['risk_factors']:
            report += f"• {factor}\n    "
    else:
        report += "无明显风险因素\n    "
    
    report += """
    五、康复建议
    ------------------
    """
    
    # 按优先级排序建议
    sorted_recommendations = sorted(assessment['recommendations'], 
                                  key=lambda x: {'high': 0, 'medium': 1, 'low': 2}.get(x['priority'], 3))
    
    for i, rec in enumerate(sorted_recommendations, 1):
        priority_cn = {'high': '高', 'medium': '中', 'low': '低'}.get(rec['priority'], '一般')
        report += f"""
    {i}. 【{rec['category']}】优先级：{priority_cn}
    {rec['content']}
    具体措施：
    """
        for action in rec['actions']:
            report += f"   - {action}\n    "
    
    report += """
    ============================================
    注：本评估基于《步态分析标准化执行规划文档》
    建议结合临床表现和其他检查结果综合判断
    ============================================
    """
    
    return report

# 集成到现有系统的接口
def enhance_gait_analysis_with_standards(gait_params: Dict) -> Dict:
    """
    增强现有步态分析结果，添加标准化评估
    
    Args:
        gait_params: 原始步态分析参数
        
    Returns:
        增强后的分析结果
    """
    assessor = StandardizedGaitAssessment()
    
    # 执行标准化评估
    assessment = assessor.assess_gait_quality(gait_params)
    
    # 生成临床报告
    clinical_report = generate_clinical_report_section(assessment)
    
    # 将评估结果集成到原始参数中
    enhanced_params = gait_params.copy()
    enhanced_params['standardized_assessment'] = assessment
    enhanced_params['clinical_report_text'] = clinical_report
    
    return enhanced_params

if __name__ == "__main__":
    # 测试示例
    test_params = {
        'average_velocity': 0.75,  # 步速偏慢
        'average_step_length': 45,  # 步长偏短
        'cadence': 95,  # 步频偏低
        'step_width': 18,
        'gait_phases': {
            'stance_phase': 65,
            'swing_phase': 35,
            'double_support': 25,  # 双支撑期延长
            'left_stance_phase': 62,
            'right_stance_phase': 68,
            'left_swing_phase': 38,
            'right_swing_phase': 32
        },
        'symmetry_indices': {
            'step_length_si': 12,  # 中度不对称
            'cadence_si': 8,
            'swing_time_si': 15,
            'overall_si': 11.7
        },
        'cop_stability': {
            'ellipse_area': 8.5,
            'ap_range': 0.15,
            'ml_range': 0.08
        },
        'gait_parameters': {
            'left_foot': {
                'average_step_length_m': 0.42
            },
            'right_foot': {
                'average_step_length_m': 0.48
            }
        }
    }
    
    # 执行评估
    enhanced = enhance_gait_analysis_with_standards(test_params)
    
    # 打印临床报告
    print(enhanced['clinical_report_text'])
    
    # 打印JSON格式的评估结果
    import json
    print("\n详细评估结果（JSON）：")
    print(json.dumps(enhanced['standardized_assessment'], 
                     indent=2, ensure_ascii=False))