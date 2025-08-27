#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
GemSage步态分析系统 - 主控制程序
集成所有功能模块，提供完整的步态分析和报告生成服务

作者: Claude
版本: 1.0.0
使用方法: python main_gait_system.py --data_folder "for test/1" --output report.html
"""

import os
import sys
import argparse
import json
from datetime import datetime
import traceback

# 导入自定义模块
from gait_analyzer import PressureDataProcessor, GaitAnalysisSystem
from advanced_gait_analyzer import AdvancedWalkingAnalyzer
from visualization import ReportChartsGenerator  
from report_generator import HTMLReportGenerator, PatientInfoManager

class GemSageSystem:
    """GemSage步态分析系统主类"""
    
    def __init__(self, data_folder, template_path="m1.html"):
        """
        初始化系统
        
        Args:
            data_folder: 测试数据文件夹路径
            template_path: HTML模板路径
        """
        self.data_folder = data_folder
        self.template_path = template_path
        
        # 初始化核心组件
        self.processor = PressureDataProcessor()
        self.gait_system = GaitAnalysisSystem(data_folder)
        self.advanced_analyzer = AdvancedWalkingAnalyzer(self.processor)
        self.chart_generator = ReportChartsGenerator(self.processor)
        
        # 检查模板文件
        if not os.path.exists(template_path):
            print(f"警告: 模板文件不存在 {template_path}")
            print("将使用简化报告格式")
            self.report_generator = None
        else:
            self.report_generator = HTMLReportGenerator(template_path)
        
        # 存储结果
        self.analysis_results = {}
        self.charts_data = {}
        self.test_data = {}
        
    def run_complete_analysis(self, patient_info=None):
        """
        运行完整分析流程
        
        Args:
            patient_info: 患者信息字典
            
        Returns:
            dict: 完整分析结果
        """
        print("=" * 60)
        print("GemSage步态分析系统 - 开始分析")
        print("=" * 60)
        
        try:
            # 1. 基础步态分析
            print("\n📊 第一阶段: 基础步态分析")
            self.analysis_results = self.gait_system.run_full_analysis()
            self._print_basic_results()
            
            # 2. 高级分析 (处理转身等复杂情况)  
            print("\n🔄 第二阶段: 高级步态分析")
            self._run_advanced_analysis()
            
            # 3. 生成图表
            print("\n📈 第三阶段: 生成可视化图表")
            self._generate_charts()
            
            # 4. 生成报告
            print("\n📋 第四阶段: 生成分析报告")
            if patient_info is None:
                patient_info = PatientInfoManager.create_sample_patient_info()
            
            report_path = self._generate_report(patient_info)
            
            # 5. 验证结果
            print("\n✅ 第五阶段: 验证分析结果")
            validation_results = self._validate_results()
            
            # 汇总结果
            complete_results = {
                'analysis_results': self.analysis_results,
                'advanced_results': getattr(self, 'advanced_results', {}),
                'validation': validation_results,
                'report_path': report_path,
                'charts_generated': len(self.charts_data),
                'timestamp': datetime.now().isoformat()
            }
            
            print(f"\n🎉 分析完成! 报告已保存至: {report_path}")
            return complete_results
            
        except Exception as e:
            print(f"\n❌ 分析过程中出现错误: {e}")
            traceback.print_exc()
            return {'error': str(e), 'timestamp': datetime.now().isoformat()}
    
    def _run_advanced_analysis(self):
        """运行高级分析"""
        try:
            # 加载行走和站立数据
            walking_data = self.gait_system.loader.load_test_data('walking')
            standing_data = self.gait_system.loader.load_test_data('standing')
            
            if walking_data is not None:
                # 进行高级行走分析
                advanced_results = self.advanced_analyzer.analyze_walking_with_turns(
                    walking_data, standing_data
                )
                
                self.advanced_results = advanced_results
                
                # 打印高级分析结果  
                print(f"   检测到 {advanced_results.get('segment_count', 0)} 个步态段落")
                print(f"   检测到 {advanced_results.get('turn_count', 0)} 次转身")
                
                if 'overall_gait_parameters' in advanced_results:
                    gait_params = advanced_results['overall_gait_parameters']
                    print(f"   综合步长: {gait_params.get('left_step_length', 0):.3f}m (左), {gait_params.get('right_step_length', 0):.3f}m (右)")
                    print(f"   综合步频: {gait_params.get('left_step_frequency', 0):.1f} steps/min (左), {gait_params.get('right_step_frequency', 0):.1f} steps/min (右)")
            else:
                print("   警告: 未找到行走数据，跳过高级分析")
                self.advanced_results = {}
                
        except Exception as e:
            print(f"   高级分析出错: {e}")
            self.advanced_results = {}
    
    def _generate_charts(self):
        """生成可视化图表"""
        try:
            # 加载所有测试数据
            test_types = ['sitting', 'sit_to_stand', 'standing', 'tandem_standing', 'side_standing', 'walking']
            
            for test_type in test_types:
                try:
                    data = self.gait_system.loader.load_test_data(test_type)
                    if data is not None and len(data) > 0:
                        self.test_data[test_type] = data
                        print(f"   ✓ {test_type}: {len(data)} 帧数据")
                    else:
                        print(f"   ⚠ {test_type}: 无数据")
                except Exception as e:
                    print(f"   ✗ {test_type}: 加载失败 - {e}")
            
            # 生成图表
            if self.test_data:
                self.charts_data = self.chart_generator.generate_all_charts(
                    self.test_data, self.analysis_results
                )
                print(f"   成功生成 {len(self.charts_data)} 套图表")
            else:
                print("   警告: 没有可用数据生成图表")
                
        except Exception as e:
            print(f"   图表生成出错: {e}")
            self.charts_data = {}
    
    def _generate_report(self, patient_info):
        """生成分析报告"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        if self.report_generator is not None:
            # 生成HTML报告
            report_path = f"gait_analysis_report_{timestamp}.html"
            try:
                self.report_generator.generate_report(
                    analysis_results=self.analysis_results,
                    patient_info=patient_info,
                    charts=self.charts_data,
                    output_path=report_path
                )
                return os.path.abspath(report_path)
            except Exception as e:
                print(f"   HTML报告生成失败: {e}")
                return self._generate_text_report(patient_info, timestamp)
        else:
            # 生成纯文本报告
            return self._generate_text_report(patient_info, timestamp)
    
    def _generate_text_report(self, patient_info, timestamp):
        """生成纯文本报告"""
        report_path = f"gait_analysis_report_{timestamp}.txt"
        
        with open(report_path, 'w', encoding='utf-8') as f:
            f.write("GemSage步态分析报告\n")
            f.write("=" * 50 + "\n\n")
            
            # 患者信息
            f.write("患者信息:\n")
            for key, value in patient_info.items():
                f.write(f"  {key}: {value}\n")
            f.write("\n")
            
            # 分析结果
            f.write("分析结果:\n")
            for test_type, results in self.analysis_results.items():
                f.write(f"\n{test_type}:\n")
                if isinstance(results, dict):
                    for param, value in results.items():
                        f.write(f"  {param}: {value}\n")
                else:
                    f.write(f"  结果: {results}\n")
            
            # 高级分析结果
            if hasattr(self, 'advanced_results') and self.advanced_results:
                f.write(f"\n高级分析结果:\n")
                f.write(f"  段落数量: {self.advanced_results.get('segment_count', 0)}\n")
                f.write(f"  转身次数: {self.advanced_results.get('turn_count', 0)}\n")
            
            f.write(f"\n报告生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        
        return os.path.abspath(report_path)
    
    def _print_basic_results(self):
        """打印基础分析结果"""
        for test_type, results in self.analysis_results.items():
            if test_type == 'summary':
                continue
            print(f"   ✓ {test_type}: ", end="")
            if isinstance(results, dict):
                key_params = list(results.keys())[:3]  # 显示前3个参数
                param_str = ", ".join([f"{k}={results[k]:.3f}" for k in key_params if isinstance(results[k], (int, float))])
                print(param_str + ("..." if len(results) > 3 else ""))
            else:
                print(f"完成")
    
    def _validate_results(self):
        """验证分析结果"""
        validation = {
            'data_quality': {},
            'result_consistency': {},
            'parameter_ranges': {}
        }
        
        try:
            # 数据质量验证
            for test_type, data in self.test_data.items():
                if data is not None:
                    validation['data_quality'][test_type] = {
                        'frame_count': len(data),
                        'time_range': f"{data['time'].min():.2f} - {data['time'].max():.2f}s",
                        'data_completeness': (data['data'].notna().sum() / len(data) * 100)
                    }
                    print(f"   ✓ {test_type}: {len(data)} 帧, 完整度 {validation['data_quality'][test_type]['data_completeness']:.1f}%")
            
            # 结果一致性验证  
            if 'walking' in self.analysis_results:
                walking = self.analysis_results['walking']
                left_speed = walking.get('stride_speed_left', 0)
                right_speed = walking.get('stride_speed_right', 0)
                
                if left_speed > 0 and right_speed > 0:
                    speed_difference = abs(left_speed - right_speed) / ((left_speed + right_speed) / 2) * 100
                    validation['result_consistency']['gait_symmetry'] = f"{100 - speed_difference:.1f}%"
                    print(f"   步态对称性: {validation['result_consistency']['gait_symmetry']}")
            
            # 参数范围验证
            range_checks = {
                'sitting_stability': self.analysis_results.get('sitting', {}).get('micro_vibration', 0) < 3.0,
                'walking_speed_reasonable': 0.5 <= ((
                    self.analysis_results.get('walking', {}).get('stride_speed_left', 0) + 
                    self.analysis_results.get('walking', {}).get('stride_speed_right', 0)
                ) / 2) <= 2.5
            }
            
            validation['parameter_ranges'] = range_checks
            passed_checks = sum(range_checks.values())
            print(f"   参数范围检查: {passed_checks}/{len(range_checks)} 通过")
            
        except Exception as e:
            print(f"   验证过程出错: {e}")
            validation['error'] = str(e)
        
        return validation


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description='GemSage步态分析系统')
    parser.add_argument('--data_folder', type=str, required=True, help='测试数据文件夹路径')
    parser.add_argument('--template', type=str, default='m1.html', help='HTML模板文件路径')  
    parser.add_argument('--patient_info', type=str, help='患者信息JSON文件路径')
    parser.add_argument('--output', type=str, help='输出报告文件名')
    
    args = parser.parse_args()
    
    # 检查数据文件夹
    if not os.path.exists(args.data_folder):
        print(f"❌ 错误: 数据文件夹不存在 - {args.data_folder}")
        print("请确认路径正确，例如: --data_folder 'for test/1'")
        sys.exit(1)
    
    # 加载患者信息
    if args.patient_info and os.path.exists(args.patient_info):
        patient_info = PatientInfoManager.load_patient_info_from_file(args.patient_info)
    else:
        patient_info = PatientInfoManager.create_sample_patient_info()
    
    try:
        # 创建分析系统
        system = GemSageSystem(args.data_folder, args.template)
        
        # 运行完整分析
        results = system.run_complete_analysis(patient_info)
        
        if 'error' not in results:
            print("\n" + "=" * 60)
            print("✅ 分析成功完成!")
            print(f"📊 测试项目: {len(system.analysis_results)} 个")
            print(f"📈 生成图表: {results.get('charts_generated', 0)} 套")
            print(f"📋 报告文件: {results.get('report_path', 'N/A')}")
            
            if system.advanced_results:
                print(f"🔄 检测转身: {system.advanced_results.get('turn_count', 0)} 次")
                print(f"📏 步态段落: {system.advanced_results.get('segment_count', 0)} 段")
            
            print("=" * 60)
        else:
            print(f"\n❌ 分析失败: {results['error']}")
            sys.exit(1)
            
    except KeyboardInterrupt:
        print("\n\n⛔ 用户中断分析")
        sys.exit(0)
    except Exception as e:
        print(f"\n❌ 系统错误: {e}")
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()