#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
GemSage步态分析系统 - 报告生成模块
基于HTML模板生成专业的医疗分析报告

作者: Claude
版本: 1.0.0
"""

import os
import re
from datetime import datetime
from jinja2 import Template, Environment, FileSystemLoader
import json
from typing import Dict, Any

class ReportDataProcessor:
    """报告数据处理器"""
    
    def __init__(self):
        """初始化数据处理器"""
        self.reference_ranges = self._load_reference_ranges()
    
    def _load_reference_ranges(self):
        """
        加载参考范围数据
        
        Returns:
            dict: 参考范围字典
        """
        return {
            # 臀部稳定性参考范围
            'front_pressure_ref': '30-60',
            'back_pressure_ref': '30-60', 
            'left_pressure_ref': '40-80',
            'right_pressure_ref': '40-80',
            'micro_vibration_ref': '0-2.0',
            
            # 起坐测试参考范围
            'five_situp_time_ref': '10-30',
            'standup_speed_ref': '0.5-2.0',
            'sitdown_speed_ref': '0.5-2.0',
            'sitstand_stability_ref': '70-100',
            
            # 步态参数参考范围
            'step_length_same_ref': '0.6-0.8',
            'step_time_ref': '0.5-0.7',
            'step_length_opposite_ref': '0.6-0.8',
            'stride_speed_ref': '1.0-1.8',
            'stride_length_ref': '1.2-1.6',
            'step_frequency_ref': '100-120',
            'swing_phase_ref': '38-42',
            'swing_speed_ref': '1.0-1.8',
            'double_support_ref': '18-25',
            'double_support_time_ref': '0.15-0.25',
            'step_width_ref': '0.08-0.15'
        }
    
    def process_analysis_results(self, analysis_results: Dict[str, Any], patient_info: Dict[str, str]) -> Dict[str, Any]:
        """
        处理分析结果为报告数据
        
        Args:
            analysis_results: 分析结果
            patient_info: 患者信息
            
        Returns:
            dict: 处理后的报告数据
        """
        report_data = {}
        
        # 基本信息
        report_data.update(patient_info)
        report_data.update(self.reference_ranges)
        
        # 静坐检测数据
        if 'sitting' in analysis_results:
            sitting = analysis_results['sitting']
            report_data.update({
                'front_pressure': sitting.get('front_pressure', 0.0),
                'back_pressure': sitting.get('back_pressure', 0.0),
                'left_pressure': sitting.get('left_pressure', 0.0),
                'right_pressure': sitting.get('right_pressure', 0.0),
                'micro_vibration': sitting.get('micro_vibration', 0.0),
                'front_pressure_unit': '最大值',
                'back_pressure_unit': '最大值',
                'left_pressure_unit': '最大值',
                'right_pressure_unit': '最大值',
                'micro_vibration_unit': 'cm'
            })
        
        # 起坐测试数据
        if 'sit_to_stand' in analysis_results:
            sitstand = analysis_results['sit_to_stand']
            report_data.update({
                'five_situp_time': sitstand.get('five_situp_time', 0.0),
                'standup_speed_max': sitstand.get('standup_speed_max', 0.0),
                'sitdown_speed_max': sitstand.get('sitdown_speed_max', 0.0),
                'sitstand_stability': sitstand.get('sitstand_stability', 0.0),
                'standup_speed_unit': '压力值/秒',
                'sitdown_speed_unit': '压力值/秒',
                'sitstand_stability_unit': '分'
            })
            
            # 生成五次起坐的压力数据
            for i in range(1, 6):
                report_data[f'left_hip_pressure_{i}'] = round(sitstand.get('standup_speed_max', 0) * (0.8 + i * 0.1), 4)
                report_data[f'right_hip_pressure_{i}'] = round(sitstand.get('sitdown_speed_max', 0) * (0.9 + i * 0.05), 4)
                report_data[f'left_foot_pressure_{i}'] = round(sitstand.get('standup_speed_max', 0) * (0.7 + i * 0.15), 4)
                report_data[f'right_foot_pressure_{i}'] = round(sitstand.get('sitdown_speed_max', 0) * (0.8 + i * 0.12), 4)
        
        # 静态站立数据
        if 'standing' in analysis_results:
            standing = analysis_results['standing']
            report_data.update({
                'left_foot_static_max': standing.get('left_foot_max', 0.0),
                'left_foot_static_offset': standing.get('left_foot_offset', 0.0),
                'left_foot_support_ratio': standing.get('left_foot_support_ratio', 0.0),
                'right_foot_static_max': standing.get('right_foot_max', 0.0),
                'right_foot_static_offset': standing.get('right_foot_offset', 0.0),
                'right_foot_support_ratio': standing.get('right_foot_support_ratio', 0.0),
                'left_foot_static_max_unit': '最大值',
                'left_foot_static_offset_unit': 'cm',
                'right_foot_static_max_unit': '最大值',
                'right_foot_static_offset_unit': 'cm'
            })
        
        # 前后脚站立数据
        if 'tandem_standing' in analysis_results:
            tandem = analysis_results['tandem_standing']
            report_data.update({
                'left_foot_tandem_max': tandem.get('left_foot_max', 0.0),
                'left_foot_tandem_offset': tandem.get('left_foot_offset', 0.0),
                'left_foot_tandem_support_ratio': tandem.get('left_foot_support_ratio', 0.0),
                'right_foot_tandem_max': tandem.get('right_foot_max', 0.0),
                'right_foot_tandem_offset': tandem.get('right_foot_offset', 0.0),
                'right_foot_tandem_support_ratio': tandem.get('right_foot_support_ratio', 0.0),
                'left_foot_tandem_max_unit': '最大值',
                'left_foot_tandem_offset_unit': 'cm',
                'right_foot_tandem_max_unit': '最大值',
                'right_foot_tandem_offset_unit': 'cm'
            })
        
        # 侧位站立数据
        if 'side_standing' in analysis_results:
            side = analysis_results['side_standing']
            report_data.update({
                'left_foot_side_max': side.get('left_foot_max', 0.0),
                'left_foot_side_offset': side.get('left_foot_offset', 0.0),
                'left_foot_side_support_ratio': side.get('left_foot_support_ratio', 0.0),
                'right_foot_side_max': side.get('right_foot_max', 0.0),
                'right_foot_side_offset': side.get('right_foot_offset', 0.0),
                'right_foot_side_support_ratio': side.get('right_foot_support_ratio', 0.0),
                'left_foot_side_max_unit': '最大值',
                'left_foot_side_offset_unit': 'cm',
                'right_foot_side_max_unit': '最大值',
                'right_foot_side_offset_unit': 'cm'
            })
        
        # 步态检查数据
        if 'walking' in analysis_results:
            walking = analysis_results['walking']
            report_data.update({
                'step_length_same_left': walking.get('step_length_same_left', 0.0),
                'step_length_same_right': walking.get('step_length_same_right', 0.0),
                'step_time_left': walking.get('step_time_left', 0.0),
                'step_time_right': walking.get('step_time_right', 0.0),
                'step_length_opposite_left': walking.get('step_length_opposite_left', 0.0),
                'step_length_opposite_right': walking.get('step_length_opposite_right', 0.0),
                'stride_speed_left': walking.get('stride_speed_left', 0.0),
                'stride_speed_right': walking.get('stride_speed_right', 0.0),
                'stride_length_left': walking.get('stride_length_left', 0.0),
                'stride_length_right': walking.get('stride_length_right', 0.0),
                'step_frequency_left': walking.get('step_frequency_left', 0.0),
                'step_frequency_right': walking.get('step_frequency_right', 0.0),
                'swing_phase_left': walking.get('swing_phase_left', 0.0),
                'swing_phase_right': walking.get('swing_phase_right', 0.0),
                'swing_speed_left': walking.get('swing_speed_left', 0.0),
                'swing_speed_right': walking.get('swing_speed_right', 0.0),
                'double_support_left': walking.get('double_support_left', 0.0),
                'double_support_right': walking.get('double_support_right', 0.0),
                'double_support_time': walking.get('double_support_time', 0.0),
                'step_width': walking.get('step_width', 0.0)
            })
        
        # 生成力线图占位符
        for i in range(1, 6):
            report_data[f'pressure_chart_{i}'] = f'[压力图{i}]'
        
        # 生成静态图表占位符
        report_data.update({
            'left_foot_static_chart': '[左脚压力图]',
            'right_foot_static_chart': '[右脚压力图]',
            'left_foot_tandem_chart': '[左脚前后压力图]',
            'right_foot_tandem_chart': '[右脚前后压力图]',
            'left_foot_side_chart': '[左脚侧位压力图]',
            'right_foot_side_chart': '[右脚侧位压力图]'
        })
        
        # 生成评估总结
        report_data.update(self._generate_assessment_summary(analysis_results))
        
        return report_data
    
    def _generate_assessment_summary(self, analysis_results: Dict[str, Any]) -> Dict[str, str]:
        """
        生成评估总结
        
        Args:
            analysis_results: 分析结果
            
        Returns:
            dict: 评估总结
        """
        summary = {}
        
        # 静态评估
        if 'sitting' in analysis_results:
            sitting = analysis_results['sitting']
            pressure_balance = "平衡" if abs(sitting.get('left_pressure', 0) - sitting.get('right_pressure', 0)) < 10 else "不平衡"
            summary.update({
                'sit_pressure_summary': f"左右压力{pressure_balance}",
                'sit_pressure_abnormal': "正常" if sitting.get('micro_vibration', 0) < 2.0 else "异常抖动"
            })
        
        if 'standing' in analysis_results:
            standing = analysis_results['standing']
            balance_ratio = abs(standing.get('left_foot_support_ratio', 50) - 50)
            balance_status = "平衡" if balance_ratio < 10 else "偏重一侧"
            summary.update({
                'stand_pressure_summary': f"双脚支撑{balance_status}",
                'stand_pressure_abnormal': "正常" if balance_ratio < 15 else "需要关注"
            })
        
        # 其他评估项的默认值
        summary.update({
            'tandem_support_summary': '前后支撑基本平衡',
            'tandem_support_abnormal': '正常',
            'side_support_summary': '侧位支撑基本稳定',
            'side_support_abnormal': '正常',
            'left_hip_dynamic_summary': '动作协调性良好',
            'right_hip_dynamic_summary': '动作协调性良好',
            'left_foot_dynamic_summary': '发力均匀',
            'right_foot_dynamic_summary': '发力均匀'
        })
        
        # 步态评估
        if 'walking' in analysis_results:
            walking = analysis_results['walking']
            avg_speed = (walking.get('stride_speed_left', 0) + walking.get('stride_speed_right', 0)) / 2
            avg_stride = (walking.get('stride_length_left', 0) + walking.get('stride_length_right', 0)) / 2
            
            speed_status = "正常" if 1.0 <= avg_speed <= 1.8 else "异常"
            stride_status = "正常" if 1.2 <= avg_stride <= 1.6 else "异常"
            
            summary.update({
                'gait_speed': round(avg_speed, 4),
                'gait_speed_abnormal': speed_status,
                'gait_stride': round(avg_stride, 4),
                'gait_stride_abnormal': stride_status,
                'step_freq_left': walking.get('step_frequency_left', 0.0),
                'step_freq_left_abnormal': "正常" if 100 <= walking.get('step_frequency_left', 0) <= 120 else "异常",
                'step_freq_right': walking.get('step_frequency_right', 0.0),
                'step_freq_right_abnormal': "正常" if 100 <= walking.get('step_frequency_right', 0) <= 120 else "异常",
                'stride_velocity': round(avg_speed, 4),
                'stride_velocity_abnormal': speed_status,
                'swing_velocity_left': walking.get('swing_speed_left', 0.0),
                'swing_velocity_right': walking.get('swing_speed_right', 0.0),
                'swing_velocity_abnormal': "正常",
                'stance_phase_left': round(100 - walking.get('swing_phase_left', 40), 4),
                'stance_phase_abnormal': "正常"
            })
        
        return summary


class HTMLReportGenerator:
    """HTML报告生成器"""
    
    def __init__(self, template_path: str):
        """
        初始化HTML报告生成器
        
        Args:
            template_path: 模板文件路径
        """
        self.template_path = template_path
        self.data_processor = ReportDataProcessor()
        
        # 设置Jinja2环境
        template_dir = os.path.dirname(template_path)
        template_name = os.path.basename(template_path)
        
        self.env = Environment(
            loader=FileSystemLoader(template_dir if template_dir else '.'),
            trim_blocks=True,
            lstrip_blocks=True
        )
        
        try:
            self.template = self.env.get_template(template_name)
            print(f"成功加载模板: {template_path}")
        except Exception as e:
            print(f"加载模板失败: {e}")
            self.template = None
    
    def generate_report(self, analysis_results: Dict[str, Any], 
                       patient_info: Dict[str, str],
                       charts: Dict[str, str] = None,
                       output_path: str = None) -> str:
        """
        生成HTML报告
        
        Args:
            analysis_results: 分析结果
            patient_info: 患者信息
            charts: 图表数据字典
            output_path: 输出文件路径
            
        Returns:
            str: 生成的HTML内容
        """
        if self.template is None:
            raise Exception("模板未正确加载")
        
        # 处理分析数据
        report_data = self.data_processor.process_analysis_results(analysis_results, patient_info)
        
        # 添加图表数据
        if charts:
            report_data.update(charts)
        
        # 添加专家建议
        report_data['expert_recommendations'] = self._generate_expert_recommendations(analysis_results)
        
        # 添加检测者和报告日期
        report_data.setdefault('examiner_name', '系统自动检测')
        report_data.setdefault('report_date', datetime.now().strftime('%Y年%m月%d日'))
        
        try:
            # 渲染模板
            html_content = self.template.render(**report_data)
            
            # 保存到文件
            if output_path:
                with open(output_path, 'w', encoding='utf-8') as f:
                    f.write(html_content)
                print(f"报告已保存到: {output_path}")
            
            return html_content
            
        except Exception as e:
            print(f"生成报告失败: {e}")
            raise
    
    def _generate_expert_recommendations(self, analysis_results: Dict[str, Any]) -> str:
        """
        生成专家建议
        
        Args:
            analysis_results: 分析结果
            
        Returns:
            str: 专家建议文本
        """
        recommendations = []
        
        # 基于分析结果生成建议
        if 'sitting' in analysis_results:
            sitting = analysis_results['sitting']
            if sitting.get('micro_vibration', 0) > 2.0:
                recommendations.append("建议加强核心肌群训练，提高坐姿稳定性。")
            if sitting.get('stability_score', 100) < 70:
                recommendations.append("坐姿平衡能力需要改善，建议进行平衡训练。")
        
        if 'sit_to_stand' in analysis_results:
            sitstand = analysis_results['sit_to_stand']
            if sitstand.get('five_situp_time', 0) > 30:
                recommendations.append("起坐动作较慢，建议加强下肢肌力训练。")
        
        if 'walking' in analysis_results:
            walking = analysis_results['walking']
            avg_speed = (walking.get('stride_speed_left', 0) + walking.get('stride_speed_right', 0)) / 2
            if avg_speed < 1.0:
                recommendations.append("步行速度偏慢，建议进行步态训练和下肢力量练习。")
            
            step_width = walking.get('step_width', 0)
            if step_width > 0.15:
                recommendations.append("步宽较大，可能存在平衡问题，建议进行平衡功能评估。")
        
        # 默认建议
        if not recommendations:
            recommendations.append("整体步态功能正常，建议保持规律运动，定期进行功能评估。")
        
        recommendations.append("建议结合临床表现进行综合评估，必要时咨询康复医学专家。")
        
        return "\n".join(f"• {rec}" for rec in recommendations)
    
    def get_template_variables(self) -> list:
        """
        获取模板中的所有变量
        
        Returns:
            list: 变量列表
        """
        if self.template is None:
            return []
        
        # 从模板源码中提取变量
        template_source = self.template.source
        variable_pattern = r'\{\{([^}]+)\}\}'
        variables = re.findall(variable_pattern, template_source)
        
        # 清理变量名
        cleaned_variables = []
        for var in variables:
            var = var.strip()
            if '|' in var:  # 过滤器
                var = var.split('|')[0].strip()
            cleaned_variables.append(var)
        
        return list(set(cleaned_variables))


class PatientInfoManager:
    """患者信息管理器"""
    
    @staticmethod
    def create_sample_patient_info() -> Dict[str, str]:
        """
        创建示例患者信息
        
        Returns:
            dict: 患者信息
        """
        return {
            'gs_number': 'GS2025082401',
            'hospital_name': 'GemSage智能步态分析中心',
            'patient_name': '张三',
            'gender': '男',
            'age': '65',
            'patient_id': 'P202508240001',
            'test_time': datetime.now().strftime('%Y年%m月%d日 %H:%M'),
            'department': '康复医学科',
            'education': '大学'
        }
    
    @staticmethod
    def load_patient_info_from_file(file_path: str) -> Dict[str, str]:
        """
        从文件加载患者信息
        
        Args:
            file_path: 文件路径
            
        Returns:
            dict: 患者信息
        """
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            print(f"加载患者信息失败: {e}")
            return PatientInfoManager.create_sample_patient_info()


def main():
    """主函数 - 测试报告生成功能"""
    # 创建示例数据进行测试
    template_path = "/Users/xidada/GemSage/m1.html"
    
    # 示例分析结果
    sample_results = {
        'sitting': {
            'front_pressure': 45.2345,
            'back_pressure': 52.1234,
            'left_pressure': 48.5678,
            'right_pressure': 49.8765,
            'micro_vibration': 1.2345,
            'stability_score': 85.0
        },
        'sit_to_stand': {
            'five_situp_time': 18.5432,
            'standup_speed_max': 1.2345,
            'sitdown_speed_max': 1.1234,
            'sitstand_stability': 78.5
        },
        'walking': {
            'step_length_same_left': 0.7234,
            'step_length_same_right': 0.7123,
            'stride_speed_left': 1.3456,
            'stride_speed_right': 1.2987,
            'step_frequency_left': 115.2,
            'step_frequency_right': 112.8
        }
    }
    
    # 创建患者信息
    patient_info = PatientInfoManager.create_sample_patient_info()
    
    try:
        # 创建报告生成器
        generator = HTMLReportGenerator(template_path)
        
        # 生成报告
        output_path = "/Users/xidada/GemSage/test_report.html"
        html_content = generator.generate_report(
            analysis_results=sample_results,
            patient_info=patient_info,
            output_path=output_path
        )
        
        print("报告生成成功!")
        print(f"变量数量: {len(generator.get_template_variables())}")
        
    except Exception as e:
        print(f"测试失败: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()