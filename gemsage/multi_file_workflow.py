#!/usr/bin/env python3
"""
多文件工作流程 - 支持批量分析和报告生成
"""

import sys
import json
import os
import glob
from datetime import datetime
import subprocess
from pathlib import Path

# 导入新的分析引擎
from core_calculator_final import PressureAnalysisFinal
from full_medical_report_generator import FullMedicalReportGenerator
# 导入新的多文件分析功能
try:
    from generate_combined_report import analyze_directory_and_merge
    NEW_ENGINE_AVAILABLE = True
except ImportError:
    NEW_ENGINE_AVAILABLE = False
    print("注意: 新引擎的generate_combined_report模块不可用")

def analyze_multiple_files(csv_files, output_dir="analysis_results"):
    """
    第一步：批量分析多个CSV文件
    """
    print(f"🔍 第一步：批量分析 {len(csv_files)} 个CSV文件")
    print("=" * 60)
    
    # 创建输出目录
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
    
    analyzer = PressureAnalysisFinal()
    results = []
    
    for i, csv_file in enumerate(csv_files, 1):
        print(f"\n📊 分析文件 {i}/{len(csv_files)}: {os.path.basename(csv_file)}")
        
        try:
            result = analyzer.comprehensive_analysis_final(csv_file)
            if result:
                # 添加文件信息
                result['source_file'] = csv_file
                result['file_index'] = i
                
                gait_analysis = result.get('gait_analysis', {})
                print(f"   ✅ 检测步数: {gait_analysis.get('step_count', 0)}")
                print(f"   ✅ 平均步长: {gait_analysis.get('average_step_length', 0):.3f} m")
                print(f"   ✅ 平均速度: {gait_analysis.get('average_velocity', 0):.3f} m/s")
                
                # 保存单个文件的分析结果
                filename = os.path.basename(csv_file).replace('.csv', '_analysis.json')
                result_file = os.path.join(output_dir, filename)
                with open(result_file, 'w', encoding='utf-8') as f:
                    json.dump(result, f, ensure_ascii=False, indent=2, default=str)
                
                results.append(result)
                print(f"   💾 结果保存: {result_file}")
                
            else:
                print(f"   ❌ 分析失败")
                
        except Exception as e:
            print(f"   ❌ 分析出错: {e}")
    
    # 保存汇总结果
    if results:
        summary_file = os.path.join(output_dir, "analysis_summary.json")
        summary = {
            'timestamp': datetime.now().isoformat(),
            'total_files': len(csv_files),
            'successful_analyses': len(results),
            'results': results
        }
        
        with open(summary_file, 'w', encoding='utf-8') as f:
            json.dump(summary, f, ensure_ascii=False, indent=2, default=str)
        
        print(f"\n✅ 批量分析完成!")
        print(f"   📁 结果目录: {output_dir}")
        print(f"   📊 成功分析: {len(results)}/{len(csv_files)} 个文件")
        print(f"   📋 汇总文件: {summary_file}")
        
    return results, output_dir

def generate_reports_from_analyses(analysis_dir="analysis_results", report_type="individual"):
    """
    第二步：基于分析结果生成报告
    
    report_type:
    - "individual": 每个分析结果生成一个独立报告
    - "combined": 所有结果合并成一个综合报告
    - "both": 生成独立报告 + 综合报告
    """
    print(f"\n📄 第二步：生成医疗报告 (模式: {report_type})")
    print("=" * 60)
    
    # 读取分析结果
    summary_file = os.path.join(analysis_dir, "analysis_summary.json")
    if not os.path.exists(summary_file):
        print("❌ 找不到分析汇总文件，请先运行批量分析")
        return False
    
    with open(summary_file, 'r', encoding='utf-8') as f:
        summary = json.load(f)
    
    results = summary.get('results', [])
    if not results:
        print("❌ 没有找到有效的分析结果")
        return False
    
    generator = FullMedicalReportGenerator()
    generated_reports = []
    
    # 生成独立报告
    if report_type in ["individual", "both"]:
        print(f"\n🔄 生成 {len(results)} 个独立报告...")
        
        for i, result in enumerate(results, 1):
            try:
                source_file = result.get('source_file', f'file_{i}')
                basename = os.path.basename(source_file).replace('.csv', '')
                
                # 从文件名提取患者信息（如果可能）
                patient_info = {
                    'name': extract_name_from_filename(basename),
                    'gender': '未知',
                    'age': extract_age_from_filename(basename),
                    'id': f'BATCH_{i:03d}'
                }
                
                # 生成报告
                report_html = generator.generate_report_from_algorithm(result, patient_info)
                
                # 保存报告
                report_filename = f"{basename}_report.html"
                with open(report_filename, 'w', encoding='utf-8') as f:
                    f.write(report_html)
                
                generated_reports.append(report_filename)
                print(f"   ✅ 报告 {i}: {report_filename}")
                
            except Exception as e:
                print(f"   ❌ 报告 {i} 生成失败: {e}")
    
    # 生成综合报告
    if report_type in ["combined", "both"]:
        print(f"\n🔄 生成综合报告...")
        
        try:
            # 合并所有分析数据
            combined_result = combine_analysis_results(results)
            
            # 综合患者信息 - 优先使用 original_patient_info
            if len(results) == 1 and 'original_patient_info' in results[0]:
                # 单个文件时，使用原始患者信息
                combined_patient_info = results[0]['original_patient_info'].copy()
                
                # 转换性别为中文
                gender_map = {'MALE': '男', 'FEMALE': '女', 'male': '男', 'female': '女'}
                if 'gender' in combined_patient_info:
                    combined_patient_info['gender'] = gender_map.get(combined_patient_info['gender'], combined_patient_info['gender'])
                
                print(f"   📋 使用原始患者信息: {combined_patient_info.get('name', '未知')}")
                print(f"   👤 性别转换: {results[0]['original_patient_info'].get('gender', '未知')} → {combined_patient_info.get('gender', '未知')}")
            else:
                # 多个文件时，创建综合信息
                avg_age = calculate_average_age(results)
                combined_patient_info = {
                    'name': f'{len(results)}个样本综合分析',
                    'gender': '综合',
                    'age': avg_age if avg_age > 0 else 35,
                    'id': 'COMBINED_ANALYSIS'
                }
                print(f"   📋 使用综合患者信息: {len(results)}个样本")
            
            # 生成综合报告
            combined_html = generator.generate_report_from_algorithm(combined_result, combined_patient_info)
            
            # 保存综合报告
            combined_filename = f"combined_analysis_report_{len(results)}files.html"
            with open(combined_filename, 'w', encoding='utf-8') as f:
                f.write(combined_html)
            
            generated_reports.append(combined_filename)
            print(f"   ✅ 综合报告: {combined_filename}")
            
        except Exception as e:
            print(f"   ❌ 综合报告生成失败: {e}")
    
    print(f"\n🎉 报告生成完成!")
    print(f"   📊 生成报告数量: {len(generated_reports)}")
    for report in generated_reports:
        print(f"   📄 {report}")
    
    return True

def extract_name_from_filename(filename):
    """从文件名提取患者姓名"""
    import re
    
    # 排除年龄相关的中文字符（岁、年）
    age_chars = {'岁', '年'}
    
    # 提取所有中文字符序列
    chinese_matches = re.findall(r'[\u4e00-\u9fff]+', filename)
    
    for match in chinese_matches:
        # 跳过年龄相关的字符和单字符（可能是其他描述词）
        if len(match) >= 2 and not any(char in age_chars for char in match):
            return match
    
    # 如果没有找到合适的中文姓名，尝试英文或第一个部分
    return filename.split('-')[0] if '-' in filename else '未知患者'

def extract_age_from_filename(filename):
    """从文件名提取年龄"""
    import re
    age_match = re.search(r'(\d+)岁', filename)
    if age_match:
        return int(age_match.group(1))
    return 0

def calculate_average_age(results):
    """计算平均年龄"""
    ages = []
    for result in results:
        filename = result.get('source_file', '')
        age = extract_age_from_filename(filename)
        if age > 0:
            ages.append(age)
    return sum(ages) // len(ages) if ages else 0

def combine_analysis_results(results):
    """合并多个分析结果"""
    if not results:
        return None
    
    # 如果只有一个结果，直接返回
    if len(results) == 1:
        return results[0]
    
    # 合并步态分析数据
    total_steps = 0
    total_step_length = 0
    total_velocity = 0
    total_cadence = 0
    valid_count = 0
    
    for result in results:
        gait = result.get('gait_analysis', {})
        if gait.get('step_count', 0) > 0:
            total_steps += gait.get('step_count', 0)
            total_step_length += gait.get('average_step_length', 0)
            total_velocity += gait.get('average_velocity', 0)
            total_cadence += gait.get('cadence', 0)
            valid_count += 1
    
    # 计算平均值
    if valid_count > 0:
        combined_gait = {
            'step_count': total_steps,
            'average_step_length': total_step_length / valid_count,
            'average_velocity': total_velocity / valid_count,
            'cadence': total_cadence / valid_count
        }
    else:
        combined_gait = results[0].get('gait_analysis', {})
    
    # 合并其他分析数据（取第一个有效结果）
    combined_result = {
        'gait_analysis': combined_gait,
        'balance_analysis': results[0].get('balance_analysis', {}),
        'file_info': {
            'combined_files': len(results),
            'total_data_points': sum(r.get('file_info', {}).get('total_rows', 0) for r in results)
        },
        'analysis_timestamp': datetime.now().isoformat()
    }
    
    return combined_result

def generate_reports_from_analyses_json(analysis_results, report_type="combined"):
    """
    基于JSON数据生成报告（不依赖目录）
    
    参数:
        analysis_results: 分析结果列表（JSON格式）
        report_type: 报告类型
            - "individual": 每个分析结果生成一个独立报告
            - "combined": 所有结果合并成一个综合报告
            - "both": 生成独立报告 + 综合报告
    
    返回:
        str: HTML格式的报告内容（如果是单个报告）
        list: HTML格式的报告列表（如果是多个报告）
    """
    if not analysis_results:
        raise ValueError("分析结果不能为空")
    
    generator = FullMedicalReportGenerator()
    generated_reports = []
    
    # 生成独立报告
    if report_type in ["individual", "both"]:
        for i, result in enumerate(analysis_results, 1):
            try:
                # 获取患者信息
                if 'original_patient_info' in result:
                    patient_info = result['original_patient_info']
                else:
                    source_file = result.get('source_file', f'analysis_{i}')
                    basename = os.path.basename(source_file).replace('.csv', '') if source_file else f'patient_{i}'
                    patient_info = {
                        'name': extract_name_from_filename(basename),
                        'gender': '未知',
                        'age': extract_age_from_filename(basename),
                        'id': f'AUTO_{i:03d}'
                    }
                
                # 直接使用原有方法生成报告
                report_html = generator.generate_report_from_algorithm(result, patient_info)
                generated_reports.append(report_html)
                
            except Exception as e:
                raise ValueError(f"报告 {i} 生成失败: {e}")
    
    # 生成综合报告
    if report_type in ["combined", "both"]:
        try:
            # 合并所有分析数据
            combined_result = combine_analysis_results(analysis_results)
            
            # 综合患者信息
            if len(analysis_results) == 1 and 'original_patient_info' in analysis_results[0]:
                combined_patient_info = analysis_results[0]['original_patient_info'].copy()
                print(f"[DEBUG] multi_file_workflow: 使用单个分析结果的患者信息: {combined_patient_info}")
                
                # 转换性别为中文
                gender_map = {'MALE': '男', 'FEMALE': '女', 'male': '男', 'female': '女'}
                if 'gender' in combined_patient_info:
                    original_gender = combined_patient_info['gender']
                    combined_patient_info['gender'] = gender_map.get(
                        combined_patient_info['gender'], 
                        combined_patient_info['gender']
                    )
                    print(f"[DEBUG] 性别转换: {original_gender} -> {combined_patient_info['gender']}")
            else:
                print(f"[DEBUG] multi_file_workflow: 未找到original_patient_info，使用默认患者信息")
                print(f"[DEBUG] 分析结果数量: {len(analysis_results)}")
                if analysis_results:
                    print(f"[DEBUG] 第一个分析结果的keys: {list(analysis_results[0].keys())}")
                
                avg_age = calculate_average_age(analysis_results)
                combined_patient_info = {
                    'name': f'{len(analysis_results)}个样本综合分析',
                    'gender': '综合',
                    'age': avg_age if avg_age > 0 else 35,
                    'id': 'COMBINED_ANALYSIS'
                }
                print(f"[DEBUG] 使用默认患者信息: {combined_patient_info}")
            
            # 直接使用原有方法生成综合报告
            print(f"[DEBUG] multi_file_workflow: 最终传递给报告生成器的患者信息: {combined_patient_info}")
            combined_html = generator.generate_report_from_algorithm(combined_result, combined_patient_info)
            
            if report_type == "combined":
                return combined_html
            else:
                generated_reports.append(combined_html)
                
        except Exception as e:
            raise ValueError(f"综合报告生成失败: {e}")
    
    # 返回结果
    if len(generated_reports) == 1:
        return generated_reports[0]
    else:
        return generated_reports

def analyze_directory_direct(directory_path, patient_info=None, output_html="combined_report.html"):
    """
    直接使用新引擎分析目录（不通过命令行）
    
    参数:
        directory_path: CSV文件所在目录路径
        patient_info: 患者信息字典，包含 name, gender, age
        output_html: HTML报告输出文件名
    
    返回:
        str: 生成的HTML报告内容，失败返回None
    """
    if not NEW_ENGINE_AVAILABLE:
        print("⚠️ 新引擎不可用，使用命令行方式")
        return None
    
    print(f"🚀 直接使用新引擎分析目录: {directory_path}")
    print("=" * 60)
    
    # 验证目录是否存在
    if not os.path.exists(directory_path):
        print(f"❌ 目录不存在: {directory_path}")
        return None
    
    # 默认患者信息
    if patient_info is None:
        patient_info = {
            'name': '测试患者',
            'gender': '男',
            'age': 35
        }
    
    try:
        # 使用新引擎分析目录
        print(f"📊 开始分析目录中的CSV文件...")
        combined_result = analyze_directory_and_merge(directory_path)
        
        # 生成报告
        print(f"📄 生成综合报告...")
        generator = FullMedicalReportGenerator()
        html_content = generator.generate_report_from_algorithm(combined_result, patient_info)
        
        # 保存报告
        if output_html:
            with open(output_html, 'w', encoding='utf-8') as f:
                f.write(html_content)
            print(f"✅ 报告已保存: {output_html}")
        
        return html_content
        
    except Exception as e:
        print(f"❌ 分析失败: {e}")
        import traceback
        traceback.print_exc()
        return None

def analyze_directory_with_new_engine(directory_path, patient_info=None, output_html="combined_report.html", output_json="summary.json", output_csv="summary.csv"):
    """
    使用新的 run_multi_tests.py 引擎分析整个目录
    
    参数:
        directory_path: CSV文件所在目录路径
        patient_info: 患者信息字典，包含 name, gender, age, height, weight
        output_html: HTML报告输出文件名
        output_json: JSON汇总输出文件名
        output_csv: CSV汇总输出文件名
    
    返回:
        bool: 是否成功
    """
    print(f"🚀 使用新引擎分析目录: {directory_path}")
    print("=" * 60)
    
    # 验证目录是否存在
    if not os.path.exists(directory_path):
        print(f"❌ 目录不存在: {directory_path}")
        return False
    
    # 默认患者信息
    if patient_info is None:
        patient_info = {
            'name': '测试患者',
            'gender': '男',
            'age': 35,
            'height': 170,
            'weight': 65
        }
    
    # 构建命令行参数
    cmd = [
        sys.executable,  # 使用当前Python解释器
        os.path.join(os.path.dirname(__file__), 'run_multi_tests.py'),
        '--dir', str(directory_path),
        '--name', str(patient_info.get('name', '测试患者')),
        '--gender', str(patient_info.get('gender', '男')),
        '--age', str(patient_info.get('age', 35)),
        '--height', str(patient_info.get('height', 170)),
        '--weight', str(patient_info.get('weight', 65)),
        '--html', str(output_html),
        '--json', str(output_json),
        '--csv', str(output_csv)
    ]
    
    print(f"📝 执行命令: {' '.join(cmd)}")
    
    try:
        # 执行命令
        result = subprocess.run(cmd, capture_output=True, text=True, encoding='utf-8')
        
        # 输出执行结果
        if result.stdout:
            print("\n📊 执行输出:")
            print(result.stdout)
        
        if result.stderr:
            print("\n⚠️ 错误信息:")
            print(result.stderr)
        
        # 检查是否成功
        if result.returncode == 0:
            print(f"\n✅ 分析成功!")
            print(f"   📄 HTML报告: {output_html}")
            print(f"   📊 JSON汇总: {output_json}")
            print(f"   📋 CSV汇总: {output_csv}")
            return True
        else:
            print(f"\n❌ 分析失败，返回码: {result.returncode}")
            return False
            
    except Exception as e:
        print(f"❌ 执行命令时出错: {e}")
        return False

def main():
    """主程序 - 演示多文件工作流程"""
    print("🧪 多文件工作流程演示")
    print("=" * 70)
    
    # 演示新引擎的使用
    print("\n📌 使用新引擎分析目录示例:")
    print("-" * 40)
    
    # 示例1：使用命令行方式
    test_dir = "D:\\sarcopenia_app\\202520809第八次测试\\2025-08-09\\detection_data"
    patient_info = {
        'name': '测试患者',
        'gender': '男',
        'age': 36,
        'height': 170,
        'weight': 65
    }
    
    print(f"\n1️⃣ 命令行方式调用新引擎:")
    print(f"   目录: {test_dir}")
    if os.path.exists(test_dir):
        success = analyze_directory_with_new_engine(
            test_dir,
            patient_info,
            "test_combined_report.html",
            "test_summary.json",
            "test_summary.csv"
        )
        if success:
            print("   ✅ 新引擎分析成功!")
    else:
        print(f"   ⚠️ 测试目录不存在: {test_dir}")
    
    print(f"\n2️⃣ 直接调用方式:")
    if NEW_ENGINE_AVAILABLE:
        html_content = analyze_directory_direct(test_dir, patient_info, "test_direct_report.html")
        if html_content:
            print("   ✅ 直接调用成功!")
    else:
        print("   ⚠️ 新引擎模块不可用")
    
    print("\n" + "-" * 40)
    print("传统方式演示:")
    
    # 查找CSV文件
    csv_pattern = "肌少症数据/*.csv"
    csv_files = glob.glob(csv_pattern)
    
    if not csv_files:
        print(f"❌ 在 {csv_pattern} 中没有找到CSV文件")
        # 尝试使用新的目录结构
        csv_pattern = "*/detection_data/*.csv"
        csv_files = glob.glob(csv_pattern)
    
    if csv_files:
        print(f"📁 找到 {len(csv_files)} 个CSV文件:")
        for i, file in enumerate(csv_files[:5], 1):  # 只显示前5个
            print(f"   {i}. {os.path.basename(file)}")
        if len(csv_files) > 5:
            print(f"   ... 还有 {len(csv_files)-5} 个文件")
        
        # 第一步：批量分析
        results, analysis_dir = analyze_multiple_files(csv_files[:3])  # 只分析前3个作为演示
        
        if results:
            # 第二步：生成报告
            generate_reports_from_analyses(analysis_dir, "combined")
            print("\n✅ 传统方式分析完成")
    
    print("\n" + "=" * 70)
    print("✅ 多文件工作流程演示完成")
    print("\n📂 可用的分析方式:")
    print("   1. analyze_directory_with_new_engine() - 命令行调用新引擎")
    print("   2. analyze_directory_direct() - 直接调用新引擎")
    print("   3. analyze_multiple_files() - 传统批量分析")
    print("   4. generate_reports_from_analyses() - 基于分析结果生成报告")

if __name__ == '__main__':
    main()