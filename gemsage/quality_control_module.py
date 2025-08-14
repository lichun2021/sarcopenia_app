#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
标准化质量控制模块
基于《步态分析标准化执行规划文档》的质量控制要求
"""

import numpy as np
from typing import Dict, List, Tuple, Optional
from datetime import datetime
import json
from pathlib import Path

class GaitDataQualityControl:
    """步态数据质量控制系统"""
    
    def __init__(self):
        self.quality_criteria = self._init_quality_criteria()
        self.validation_log = []
        
    def _init_quality_criteria(self) -> Dict:
        """初始化质量控制标准"""
        return {
            'data_completeness': {
                'min_frames': 30,  # 最少3秒数据（10Hz）
                'min_steps': 6,  # 最少3个完整步态周期
                'required_params': [
                    'average_velocity', 'average_step_length', 'cadence',
                    'stance_phase', 'swing_phase', 'double_support'
                ]
            },
            'data_validity': {
                'velocity_range': (0.1, 3.0),  # m/s
                'step_length_range': (10, 200),  # cm
                'cadence_range': (30, 200),  # 步/分
                'stance_phase_range': (45, 75),  # %
                'swing_phase_range': (25, 55),  # %
                'pressure_threshold': 0.1,  # 最小压力阈值
            },
            'data_consistency': {
                'max_step_length_cv': 30,  # 步长变异系数最大值%
                'max_missing_frames': 5,  # 最大连续缺失帧数
                'symmetry_index_threshold': 50,  # 对称性指数阈值%
            },
            'event_detection': {
                'min_hs_events': 3,  # 最少heel strike事件
                'min_to_events': 3,  # 最少toe off事件
                'max_event_interval': 3.0,  # 最大事件间隔(秒)
            },
            'calibration': {
                'last_calibration_days': 30,  # 设备校准有效期(天)
                'baseline_noise_level': 0.5,  # 基线噪声水平
            }
        }
    
    def validate_data_quality(self, data: Dict, metadata: Optional[Dict] = None) -> Dict:
        """
        全面的数据质量验证
        
        Args:
            data: 步态分析数据
            metadata: 元数据（如采集时间、设备信息等）
            
        Returns:
            质量控制报告
        """
        report = {
            'timestamp': datetime.now().isoformat(),
            'overall_quality': 'unknown',
            'quality_score': 0,
            'checks': {},
            'warnings': [],
            'errors': [],
            'recommendations': []
        }
        
        # 1. 数据完整性检查
        completeness_check = self._check_data_completeness(data)
        report['checks']['completeness'] = completeness_check
        
        # 2. 数据有效性检查
        validity_check = self._check_data_validity(data)
        report['checks']['validity'] = validity_check
        
        # 3. 数据一致性检查
        consistency_check = self._check_data_consistency(data)
        report['checks']['consistency'] = consistency_check
        
        # 4. 事件检测质量检查
        event_check = self._check_event_detection(data)
        report['checks']['event_detection'] = event_check
        
        # 5. 设备校准检查（如果有元数据）
        if metadata:
            calibration_check = self._check_calibration(metadata)
            report['checks']['calibration'] = calibration_check
        
        # 6. 计算总体质量分数
        report['quality_score'] = self._calculate_quality_score(report['checks'])
        
        # 7. 确定质量等级
        if report['quality_score'] >= 90:
            report['overall_quality'] = '优秀'
        elif report['quality_score'] >= 80:
            report['overall_quality'] = '良好'
        elif report['quality_score'] >= 70:
            report['overall_quality'] = '合格'
        elif report['quality_score'] >= 60:
            report['overall_quality'] = '需改进'
        else:
            report['overall_quality'] = '不合格'
        
        # 8. 生成警告和错误
        report['warnings'], report['errors'] = self._generate_alerts(report['checks'])
        
        # 9. 生成改进建议
        report['recommendations'] = self._generate_recommendations(report)
        
        # 10. 记录验证日志
        self._log_validation(report)
        
        return report
    
    def _check_data_completeness(self, data: Dict) -> Dict:
        """检查数据完整性"""
        check = {
            'passed': True,
            'score': 100,
            'details': {}
        }
        
        criteria = self.quality_criteria['data_completeness']
        
        # 检查帧数
        total_frames = data.get('file_info', {}).get('total_frames', 0)
        if total_frames < criteria['min_frames']:
            check['passed'] = False
            check['score'] -= 30
            check['details']['frames'] = f"帧数不足: {total_frames} < {criteria['min_frames']}"
        
        # 检查步数
        step_count = data.get('gait_parameters', {}).get('step_count', 0)
        if step_count < criteria['min_steps']:
            check['passed'] = False
            check['score'] -= 30
            check['details']['steps'] = f"步数不足: {step_count} < {criteria['min_steps']}"
        
        # 检查必需参数
        gait_params = data.get('gait_parameters', {})
        missing_params = []
        for param in criteria['required_params']:
            if param not in gait_params or gait_params[param] is None:
                missing_params.append(param)
        
        if missing_params:
            check['passed'] = False
            check['score'] -= 10 * len(missing_params)
            check['details']['missing_params'] = f"缺失参数: {', '.join(missing_params)}"
        
        check['score'] = max(0, check['score'])
        return check
    
    def _check_data_validity(self, data: Dict) -> Dict:
        """检查数据有效性"""
        check = {
            'passed': True,
            'score': 100,
            'details': {}
        }
        
        criteria = self.quality_criteria['data_validity']
        gait_params = data.get('gait_parameters', {})
        
        # 检查速度范围
        velocity = gait_params.get('average_velocity', 0)
        if not (criteria['velocity_range'][0] <= velocity <= criteria['velocity_range'][1]):
            check['passed'] = False
            check['score'] -= 25
            check['details']['velocity'] = f"速度异常: {velocity:.2f} m/s"
        
        # 检查步长范围
        step_length = gait_params.get('average_step_length', 0)
        if not (criteria['step_length_range'][0] <= step_length <= criteria['step_length_range'][1]):
            check['passed'] = False
            check['score'] -= 25
            check['details']['step_length'] = f"步长异常: {step_length:.1f} cm"
        
        # 检查步频范围
        cadence = gait_params.get('cadence', 0)
        if not (criteria['cadence_range'][0] <= cadence <= criteria['cadence_range'][1]):
            check['passed'] = False
            check['score'] -= 20
            check['details']['cadence'] = f"步频异常: {cadence:.1f} 步/分"
        
        # 检查步态相位
        phases = data.get('gait_phases', {})
        stance = phases.get('stance_phase', 0)
        swing = phases.get('swing_phase', 0)
        
        if not (criteria['stance_phase_range'][0] <= stance <= criteria['stance_phase_range'][1]):
            check['passed'] = False
            check['score'] -= 15
            check['details']['stance_phase'] = f"站立相异常: {stance:.1f}%"
        
        if not (criteria['swing_phase_range'][0] <= swing <= criteria['swing_phase_range'][1]):
            check['passed'] = False
            check['score'] -= 15
            check['details']['swing_phase'] = f"摆动相异常: {swing:.1f}%"
        
        check['score'] = max(0, check['score'])
        return check
    
    def _check_data_consistency(self, data: Dict) -> Dict:
        """检查数据一致性"""
        check = {
            'passed': True,
            'score': 100,
            'details': {}
        }
        
        criteria = self.quality_criteria['data_consistency']
        
        # 检查步长变异系数
        left_foot = data.get('gait_parameters', {}).get('left_foot', {})
        right_foot = data.get('gait_parameters', {}).get('right_foot', {})
        
        # 如果有步长序列数据，计算变异系数
        if 'step_lengths_cm' in left_foot:
            left_steps = left_foot['step_lengths_cm']
            if len(left_steps) > 1:
                cv = (np.std(left_steps) / np.mean(left_steps)) * 100 if np.mean(left_steps) > 0 else 0
                if cv > criteria['max_step_length_cv']:
                    check['passed'] = False
                    check['score'] -= 20
                    check['details']['left_cv'] = f"左脚步长变异过大: CV={cv:.1f}%"
        
        # 检查对称性
        symmetry = data.get('symmetry_indices', {}).get('overall_si', 0)
        if symmetry > criteria['symmetry_index_threshold']:
            check['passed'] = False
            check['score'] -= 30
            check['details']['symmetry'] = f"严重不对称: SI={symmetry:.1f}%"
        
        # 检查相位总和（应该接近100%）
        phases = data.get('gait_phases', {})
        stance = phases.get('stance_phase', 0)
        swing = phases.get('swing_phase', 0)
        phase_sum = stance + swing
        
        if abs(phase_sum - 100) > 5:  # 允许5%误差
            check['passed'] = False
            check['score'] -= 15
            check['details']['phase_sum'] = f"相位总和异常: {phase_sum:.1f}%"
        
        check['score'] = max(0, check['score'])
        return check
    
    def _check_event_detection(self, data: Dict) -> Dict:
        """检查事件检测质量"""
        check = {
            'passed': True,
            'score': 100,
            'details': {}
        }
        
        criteria = self.quality_criteria['event_detection']
        events = data.get('events', {})
        
        # 检查heel strike事件
        left_hs = events.get('left', {}).get('hs', [])
        right_hs = events.get('right', {}).get('hs', [])
        total_hs = len(left_hs) + len(right_hs)
        
        if total_hs < criteria['min_hs_events']:
            check['passed'] = False
            check['score'] -= 30
            check['details']['hs_events'] = f"HS事件不足: {total_hs} < {criteria['min_hs_events']}"
        
        # 检查toe off事件
        left_to = events.get('left', {}).get('to', [])
        right_to = events.get('right', {}).get('to', [])
        total_to = len(left_to) + len(right_to)
        
        if total_to < criteria['min_to_events']:
            check['passed'] = False
            check['score'] -= 30
            check['details']['to_events'] = f"TO事件不足: {total_to} < {criteria['min_to_events']}"
        
        # 检查事件间隔
        all_events = sorted(left_hs + right_hs, key=lambda x: x.get('time', 0))
        if len(all_events) > 1:
            max_interval = 0
            for i in range(1, len(all_events)):
                interval = all_events[i].get('time', 0) - all_events[i-1].get('time', 0)
                max_interval = max(max_interval, interval)
            
            if max_interval > criteria['max_event_interval']:
                check['passed'] = False
                check['score'] -= 20
                check['details']['event_interval'] = f"事件间隔过大: {max_interval:.2f}秒"
        
        check['score'] = max(0, check['score'])
        return check
    
    def _check_calibration(self, metadata: Dict) -> Dict:
        """检查设备校准状态"""
        check = {
            'passed': True,
            'score': 100,
            'details': {}
        }
        
        criteria = self.quality_criteria['calibration']
        
        # 检查校准日期
        last_calibration = metadata.get('last_calibration_date')
        if last_calibration:
            try:
                cal_date = datetime.fromisoformat(last_calibration)
                days_since = (datetime.now() - cal_date).days
                
                if days_since > criteria['last_calibration_days']:
                    check['passed'] = False
                    check['score'] -= 40
                    check['details']['calibration'] = f"校准过期: {days_since}天前"
            except:
                check['details']['calibration'] = "校准日期格式错误"
        
        # 检查基线噪声
        noise_level = metadata.get('baseline_noise', 0)
        if noise_level > criteria['baseline_noise_level']:
            check['passed'] = False
            check['score'] -= 30
            check['details']['noise'] = f"噪声水平过高: {noise_level:.2f}"
        
        check['score'] = max(0, check['score'])
        return check
    
    def _calculate_quality_score(self, checks: Dict) -> float:
        """计算总体质量分数"""
        weights = {
            'completeness': 0.25,
            'validity': 0.30,
            'consistency': 0.25,
            'event_detection': 0.15,
            'calibration': 0.05
        }
        
        total_score = 0
        total_weight = 0
        
        for check_name, check_result in checks.items():
            if check_name in weights:
                score = check_result.get('score', 0)
                weight = weights[check_name]
                total_score += score * weight
                total_weight += weight
        
        if total_weight > 0:
            return total_score / total_weight
        return 0
    
    def _generate_alerts(self, checks: Dict) -> Tuple[List[str], List[str]]:
        """生成警告和错误信息"""
        warnings = []
        errors = []
        
        for check_name, check_result in checks.items():
            if not check_result.get('passed', True):
                severity = 'error' if check_result.get('score', 100) < 50 else 'warning'
                
                for detail_key, detail_msg in check_result.get('details', {}).items():
                    if severity == 'error':
                        errors.append(f"[{check_name}] {detail_msg}")
                    else:
                        warnings.append(f"[{check_name}] {detail_msg}")
        
        return warnings, errors
    
    def _generate_recommendations(self, report: Dict) -> List[str]:
        """生成质量改进建议"""
        recommendations = []
        
        # 基于质量分数的通用建议
        if report['quality_score'] < 60:
            recommendations.append("数据质量不合格，建议重新采集数据")
        elif report['quality_score'] < 70:
            recommendations.append("数据质量需改进，建议检查采集流程")
        
        # 基于具体问题的建议
        for check_name, check_result in report['checks'].items():
            if not check_result.get('passed', True):
                if check_name == 'completeness':
                    if 'frames' in check_result.get('details', {}):
                        recommendations.append("增加数据采集时长，确保至少3秒以上")
                    if 'steps' in check_result.get('details', {}):
                        recommendations.append("增加步行距离，确保至少3个完整步态周期")
                
                elif check_name == 'validity':
                    if 'velocity' in check_result.get('details', {}):
                        recommendations.append("检查受试者状态，速度异常可能由疲劳或疾病引起")
                    if 'step_length' in check_result.get('details', {}):
                        recommendations.append("检查标记点放置和步行环境")
                
                elif check_name == 'consistency':
                    if 'symmetry' in check_result.get('details', {}):
                        recommendations.append("严重不对称，建议进行医学评估")
                    if 'left_cv' in check_result.get('details', {}) or 'right_cv' in check_result.get('details', {}):
                        recommendations.append("步态变异过大，建议让受试者适应后重测")
                
                elif check_name == 'event_detection':
                    recommendations.append("事件检测异常，检查传感器接触和算法参数")
                
                elif check_name == 'calibration':
                    recommendations.append("设备需要重新校准")
        
        return list(set(recommendations))  # 去重
    
    def _log_validation(self, report: Dict):
        """记录验证日志"""
        self.validation_log.append({
            'timestamp': report['timestamp'],
            'quality_score': report['quality_score'],
            'overall_quality': report['overall_quality'],
            'errors_count': len(report['errors']),
            'warnings_count': len(report['warnings'])
        })
        
        # 保持最近100条记录
        if len(self.validation_log) > 100:
            self.validation_log = self.validation_log[-100:]
    
    def export_quality_report(self, report: Dict, filepath: Optional[str] = None) -> str:
        """导出质量控制报告"""
        if filepath is None:
            filepath = f"quality_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2, ensure_ascii=False)
        
        return filepath
    
    def get_quality_statistics(self) -> Dict:
        """获取质量统计信息"""
        if not self.validation_log:
            return {
                'total_validations': 0,
                'average_score': 0,
                'pass_rate': 0,
                'common_issues': []
            }
        
        scores = [log['quality_score'] for log in self.validation_log]
        passed = [log['quality_score'] >= 70 for log in self.validation_log]
        
        return {
            'total_validations': len(self.validation_log),
            'average_score': np.mean(scores),
            'pass_rate': sum(passed) / len(passed) * 100,
            'score_distribution': {
                '优秀 (≥90)': sum(s >= 90 for s in scores),
                '良好 (80-89)': sum(80 <= s < 90 for s in scores),
                '合格 (70-79)': sum(70 <= s < 80 for s in scores),
                '需改进 (60-69)': sum(60 <= s < 70 for s in scores),
                '不合格 (<60)': sum(s < 60 for s in scores)
            },
            'recent_trend': 'improving' if len(scores) > 5 and np.mean(scores[-5:]) > np.mean(scores[-10:-5]) else 'stable'
        }

class DataPreprocessingQC:
    """数据预处理质量控制"""
    
    @staticmethod
    def validate_raw_data(pressure_data: List[List[List[float]]]) -> Dict:
        """验证原始压力数据"""
        validation = {
            'is_valid': True,
            'issues': [],
            'statistics': {}
        }
        
        if not pressure_data:
            validation['is_valid'] = False
            validation['issues'].append("无压力数据")
            return validation
        
        # 检查数据维度
        n_frames = len(pressure_data)
        if n_frames < 30:
            validation['issues'].append(f"帧数过少: {n_frames}")
        
        # 检查矩阵尺寸一致性
        matrix_shapes = set()
        for frame in pressure_data:
            if frame:
                shape = (len(frame), len(frame[0]) if frame[0] else 0)
                matrix_shapes.add(shape)
        
        if len(matrix_shapes) > 1:
            validation['is_valid'] = False
            validation['issues'].append(f"矩阵尺寸不一致: {matrix_shapes}")
        
        # 统计信息
        all_values = []
        for frame in pressure_data:
            for row in frame:
                all_values.extend(row)
        
        if all_values:
            validation['statistics'] = {
                'total_frames': n_frames,
                'matrix_shape': list(matrix_shapes)[0] if matrix_shapes else (0, 0),
                'min_pressure': float(np.min(all_values)),
                'max_pressure': float(np.max(all_values)),
                'mean_pressure': float(np.mean(all_values)),
                'std_pressure': float(np.std(all_values)),
                'zero_ratio': sum(1 for v in all_values if v == 0) / len(all_values)
            }
            
            # 检查数据范围
            if validation['statistics']['max_pressure'] > 1000:
                validation['issues'].append("压力值异常大")
            if validation['statistics']['zero_ratio'] > 0.95:
                validation['issues'].append("零值过多，可能无有效接触")
        
        if validation['issues']:
            validation['is_valid'] = False
        
        return validation
    
    @staticmethod
    def check_marker_tracking(marker_data: Optional[Dict]) -> Dict:
        """检查标记点跟踪质量"""
        if not marker_data:
            return {'quality': 'N/A', 'details': '无标记点数据'}
        
        quality = {
            'quality': 'good',
            'gaps': 0,
            'jumps': 0,
            'details': []
        }
        
        # 检查标记点轨迹连续性
        for marker_name, trajectory in marker_data.items():
            if len(trajectory) < 2:
                continue
            
            # 检查缺失
            gaps = sum(1 for point in trajectory if point is None or np.isnan(point).any())
            if gaps > 0:
                quality['gaps'] += gaps
                quality['details'].append(f"{marker_name}: {gaps}个缺失点")
            
            # 检查跳变
            valid_points = [p for p in trajectory if p is not None and not np.isnan(p).any()]
            if len(valid_points) > 1:
                diffs = np.diff(valid_points, axis=0)
                jumps = sum(1 for d in diffs if np.linalg.norm(d) > 0.1)  # 10cm跳变阈值
                if jumps > 0:
                    quality['jumps'] += jumps
                    quality['details'].append(f"{marker_name}: {jumps}个跳变")
        
        # 评定质量等级
        if quality['gaps'] > 10 or quality['jumps'] > 5:
            quality['quality'] = 'poor'
        elif quality['gaps'] > 5 or quality['jumps'] > 2:
            quality['quality'] = 'fair'
        
        return quality

# 示例使用
if __name__ == "__main__":
    # 创建质量控制实例
    qc = GaitDataQualityControl()
    
    # 模拟数据
    test_data = {
        'file_info': {
            'total_frames': 357,
            'duration': 35.7
        },
        'gait_parameters': {
            'step_count': 28,
            'average_velocity': 1.15,
            'average_step_length': 62.5,
            'cadence': 108,
            'stance_phase': 62,
            'swing_phase': 38,
            'double_support': 20,
            'left_foot': {
                'step_lengths_cm': [60, 62, 65, 63, 61, 64, 62]
            }
        },
        'gait_phases': {
            'stance_phase': 62,
            'swing_phase': 38,
            'double_support': 20
        },
        'symmetry_indices': {
            'overall_si': 8.5
        },
        'events': {
            'left': {
                'hs': [{'time': 0.5}, {'time': 1.2}, {'time': 1.9}],
                'to': [{'time': 0.8}, {'time': 1.5}, {'time': 2.2}]
            },
            'right': {
                'hs': [{'time': 0.9}, {'time': 1.6}, {'time': 2.3}],
                'to': [{'time': 1.1}, {'time': 1.8}, {'time': 2.5}]
            }
        }
    }
    
    # 执行质量控制
    quality_report = qc.validate_data_quality(test_data)
    
    # 打印报告
    print("=" * 50)
    print("数据质量控制报告")
    print("=" * 50)
    print(f"总体质量: {quality_report['overall_quality']}")
    print(f"质量分数: {quality_report['quality_score']:.1f}/100")
    print("\n各项检查结果:")
    for check_name, check_result in quality_report['checks'].items():
        status = "✓" if check_result['passed'] else "✗"
        print(f"  {status} {check_name}: {check_result['score']:.0f}/100")
        if check_result.get('details'):
            for detail in check_result['details'].values():
                print(f"     - {detail}")
    
    if quality_report['warnings']:
        print("\n⚠️ 警告:")
        for warning in quality_report['warnings']:
            print(f"  - {warning}")
    
    if quality_report['errors']:
        print("\n❌ 错误:")
        for error in quality_report['errors']:
            print(f"  - {error}")
    
    if quality_report['recommendations']:
        print("\n💡 改进建议:")
        for rec in quality_report['recommendations']:
            print(f"  - {rec}")
    
    # 导出报告
    filepath = qc.export_quality_report(quality_report)
    print(f"\n报告已保存至: {filepath}")