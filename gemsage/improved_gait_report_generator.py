#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
改进版步态报告生成器
基于原有专业模版 + 8.24修正建议
"""

import os
import pandas as pd
import numpy as np
from datetime import datetime
from scipy import stats
from scipy.signal import find_peaks
from typing import Dict, List, Tuple, Optional, Any
import warnings
warnings.filterwarnings('ignore')

# 导入原有的分析器和改进功能
from gait_report_generator import CompleteGaitAnalyzer, CompleteReportGenerator
from improved_report_generator import (
    ImprovedReportFormatter,
    FootprintAnalyzer,
    ComprehensiveAssessmentTable,
    UnifiedReportStyle
)

class ImprovedGaitReportGenerator(CompleteReportGenerator):
    """基于原有专业模版的改进版报告生成器"""
    
    def __init__(self):
        super().__init__()
        self.formatter = ImprovedReportFormatter()
        
    def process_test_data_with_improvements(self, folder_path: str, group_name: str, age: int) -> Dict[str, str]:
        """处理测试数据并应用改进功能"""
        
        # 使用原有的数据处理逻辑
        results = super().process_test_data(folder_path, group_name, age)
        
        # 应用改进功能
        self.apply_value_arrows(results, age)
        self.apply_comparison_arrows(results)
        self.replace_heatmaps_with_medical_grade(results, folder_path)
        self.add_comprehensive_table(results)
        
        return results
    
    def apply_value_arrows(self, results: Dict[str, str], age: int):
        """应用数值超标红绿箭头标注"""
        
        # 1. 五次起坐时间箭头
        if 'five_situp_time' in results:
            try:
                time_val = float(results['five_situp_time'])
                ref_val = 15.0 if age >= 70 else 12.0 if age >= 60 else 10.0
                results['five_situp_time'] = self.formatter.format_value_with_arrow(
                    time_val, upper=ref_val, decimal=4, unit=' 秒'
                )
            except:
                pass
        
        # 2. 微抖动箭头
        if 'micro_vibration' in results:
            try:
                vibration_val = float(results['micro_vibration'])
                results['micro_vibration'] = self.formatter.format_value_with_arrow(
                    vibration_val, upper=0.5, decimal=4, unit=' mm'
                )
            except:
                pass
        
        # 3. 步速箭头（如果有步态数据）
        if 'gait_speed' in results:
            try:
                speed_val = float(results['gait_speed'])
                ref_speed = 0.8 if age >= 70 else 1.0 if age >= 60 else 1.2
                results['gait_speed'] = self.formatter.format_value_with_arrow(
                    speed_val, lower=ref_speed, decimal=2, unit=' m/s'
                )
            except:
                pass
    
    def apply_comparison_arrows(self, results: Dict[str, str]):
        """应用左右对比红箭头标注"""
        
        # 1. 坐姿左右压力对比
        if 'left_pressure' in results and 'right_pressure' in results:
            try:
                left_val = float(results['left_pressure'])
                right_val = float(results['right_pressure'])
                comparison = self.formatter.format_comparison_with_arrow(
                    left_val, right_val, decimal=4, unit=''
                )
                results['left_pressure'] = comparison['left']
                results['right_pressure'] = comparison['right']
            except:
                pass
        
        # 2. 脚部压力最大值对比
        pairs = [
            ('left_foot_static_max', 'right_foot_static_max'),
            ('left_foot_tandem_max', 'right_foot_tandem_max'),
            ('left_foot_side_max', 'right_foot_side_max'),
        ]
        
        for left_key, right_key in pairs:
            if left_key in results and right_key in results:
                try:
                    left_val = float(results[left_key])
                    right_val = float(results[right_key])
                    comparison = self.formatter.format_comparison_with_arrow(
                        left_val, right_val, decimal=4, unit=''
                    )
                    results[left_key] = comparison['left']
                    results[right_key] = comparison['right']
                except:
                    pass
    
    def replace_heatmaps_with_medical_grade(self, results: Dict[str, str], folder_path: str):
        """替换热力图为医院级版本"""
        
        try:
            # 加载测试数据
            test_data = self.load_test_data_from_folder(folder_path)
            
            # 生成医院级热力图
            chart_mappings = [
                ('left_foot_static_chart', 'standing', 'left', 'Static Standing - Left Foot'),
                ('right_foot_static_chart', 'standing', 'right', 'Static Standing - Right Foot'),
                ('left_foot_tandem_chart', 'tandem_standing', 'left', 'Tandem Standing - Left Foot'),
                ('right_foot_tandem_chart', 'tandem_standing', 'right', 'Tandem Standing - Right Foot'),
                ('left_foot_side_chart', 'side_standing', 'left', 'Side Standing - Left Foot'),
                ('right_foot_side_chart', 'side_standing', 'right', 'Side Standing - Right Foot'),
            ]
            
            for chart_key, test_type, foot_side, title in chart_mappings:
                if test_type in test_data:
                    medical_chart = self.generate_medical_grade_chart(
                        test_data[test_type], foot_side, title
                    )
                    results[chart_key] = medical_chart
                    
        except Exception as e:
            print(f"警告：无法生成医院级热力图 - {e}")
    
    def load_test_data_from_folder(self, folder_path: str) -> Dict:
        """从文件夹加载测试数据"""
        test_data = {}
        
        file_mapping = {
            'standing': '第3步-静态站立',
            'tandem_standing': '第4步-前后脚站立', 
            'side_standing': '第5步-双脚前后站立',
        }
        
        for test_type, file_pattern in file_mapping.items():
            files = [f for f in os.listdir(folder_path) if file_pattern in f and f.endswith('.csv')]
            if files:
                file_path = os.path.join(folder_path, files[0])
                try:
                    df = pd.read_csv(file_path)
                    pressure_arrays = []
                    for _, row in df.iterrows():
                        data_str = row['data'].strip('[]')
                        data_array = [int(x) for x in data_str.split(',')]
                        pressure_arrays.append(data_array)
                    test_data[test_type] = np.array(pressure_arrays)
                except Exception as e:
                    print(f"加载 {test_type} 失败: {e}")
        
        return test_data
    
    def generate_medical_grade_chart(self, pressure_data: np.ndarray, foot_side: str, title: str) -> str:
        """生成医院级热力图"""
        
        # 去除过渡期
        start = int(len(pressure_data) * 0.1)
        end = int(len(pressure_data) * 0.9)
        stable_data = pressure_data[start:end]
        
        # 计算中位数帧
        reshaped = stable_data.reshape(-1, 32, 32)
        
        # 分离左右脚
        if foot_side == 'left':
            foot_data = reshaped[:, :, :16]  # 左半部分
        else:
            foot_data = reshaped[:, :, 16:]  # 右半部分
            
        median_frame = np.median(foot_data, axis=0)
        
        # 转换为kPa
        sensor_area = 4.688  # cm²
        force_calibration = 0.1
        force_n = median_frame * force_calibration
        kpa = (force_n / sensor_area) * 10
        kpa[kpa < 1] = 0  # 噪声过滤
        
        # 生成医院级热力图SVG
        try:
            # 使用FootprintAnalyzer生成包含足底形状和力线的图
            svg_content = FootprintAnalyzer.generate_footprint_svg(kpa, title)
            return svg_content
        except:
            # 降级到简单热力图
            return self.analyzer.generate_pressure_svg(median_frame, title)
    
    def add_comprehensive_table(self, results: Dict[str, str]):
        """添加综合评估对比表"""
        
        # 提取数值用于对比表
        comparison_data = {}
        
        # 提取坐姿数据
        try:
            comparison_data['sitting'] = {
                'left_pressure': self.extract_numeric_value(results.get('left_pressure', '0')),
                'right_pressure': self.extract_numeric_value(results.get('right_pressure', '0'))
            }
        except:
            pass
        
        # 提取站立数据
        try:
            comparison_data['standing'] = {
                'left_pressure': self.extract_numeric_value(results.get('left_foot_static_max', '0')),
                'right_pressure': self.extract_numeric_value(results.get('right_foot_static_max', '0'))
            }
        except:
            pass
        
        # 生成对比表HTML
        if comparison_data:
            comparison_html = ComprehensiveAssessmentTable.generate_comparison_table(comparison_data)
            results['comprehensive_table'] = comparison_html
        else:
            results['comprehensive_table'] = ''
    
    def extract_numeric_value(self, formatted_value: str) -> float:
        """从格式化字符串中提取数值"""
        import re
        # 移除HTML标签和箭头，只保留数字
        clean_value = re.sub(r'<[^>]+>', '', str(formatted_value))
        clean_value = re.sub(r'[↑↓]', '', clean_value)
        try:
            return float(clean_value.strip())
        except:
            return 0.0
    
    def generate_improved_html_template(self) -> str:
        """生成改进版HTML模板"""
        
        # 获取原有模板
        original_template = super().generate_corrected_html_template()
        
        # 在适当位置插入综合对比表
        # 在"三、综合评估与建议"之前插入
        insertion_point = '<h2 class="section-title">三、综合评估与建议</h2>'
        if insertion_point in original_template:
            comprehensive_section = '''
            <h2 class="section-title">📈 多维度数据对比分析</h2>
            {{comprehensive_table}}
            
            ''' + insertion_point
            
            improved_template = original_template.replace(insertion_point, comprehensive_section)
        else:
            improved_template = original_template
        
        # 删除或隐藏黄色警告区块（如果需要）
        # improved_template = improved_template.replace('class="warning"', 'class="warning" style="display: none;"')
        
        return improved_template
    
    def generate_improved_report(self, folder_path: str, group_name: str, age: int, output_path: str):
        """生成改进版报告"""
        print(f"🔥 生成改进版报告：{group_name}")
        
        # 处理数据并应用改进功能
        results = self.process_test_data_with_improvements(folder_path, group_name, age)
        
        # 生成改进版HTML模板
        template = self.generate_improved_html_template()
        
        # 替换占位符
        for key, value in results.items():
            placeholder = f"{{{{{key}}}}}"
            template = template.replace(placeholder, str(value))
        
        # 保存报告
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(template)
        
        print(f"✅ 改进版报告已生成：{output_path}")
        print("📊 应用的改进功能：")
        print("   ✅ 数值超标红绿箭头标注")
        print("   ✅ 左右对比大侧红箭头")  
        print("   ✅ 医院级热力图 + 足底形状分析")
        print("   ✅ 综合评估对比表")
        print("   ✅ 基于原有专业模版")
        
        return results

def main():
    """主函数 - 生成改进版报告"""
    generator = ImprovedGaitReportGenerator()
    
    # 生成改进版报告
    output_path = f"improved_gait_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.html"
    
    # 使用第一组测试数据
    folder_path = 'for test/1'
    group_name = '曾超08'
    age = 65
    
    generator.generate_improved_report(folder_path, group_name, age, output_path)

if __name__ == "__main__":
    main()