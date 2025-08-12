#!/usr/bin/env python3
"""
最终测试脚本 - 足部压力分析系统
包含步态分析和报告生成的完整测试流程
"""

import sys
import os
from pathlib import Path
from datetime import datetime

# 添加算法路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# 导入核心模块
from core_calculator_final import PressureAnalysisFinal
from full_medical_report_generator import FullMedicalReportGenerator
from generate_complete_report_final import generate_report_with_final_algorithm

def print_header(title):
    """打印格式化标题"""
    print("\n" + "="*80)
    print(f"  {title}")
    print("="*80)

def test_single_file(csv_file_path, patient_info=None):
    """测试单个CSV文件"""
    
    print_header(f"📊 测试文件: {Path(csv_file_path).name}")
    
    # 1. 使用最终算法分析
    print("\n1️⃣ 步态分析...")
    analyzer = PressureAnalysisFinal()
    result = analyzer.comprehensive_analysis_final(csv_file_path)
    
    if 'error' in result:
        print(f"   ❌ 分析失败: {result['error']}")
        return None
    
    # 2. 提取关键参数
    gait_params = result.get('gait_parameters', {})
    print(f"   ✅ 分析成功")
    print(f"   - 测试类型: {result.get('test_type', '未知')}")
    print(f"   - 步数: {gait_params.get('step_count', 0)}")
    print(f"   - 步长: {gait_params.get('average_step_length', 0):.1f}cm")
    print(f"   - 步频: {gait_params.get('cadence', 0):.1f}步/分")
    print(f"   - 速度: {gait_params.get('average_velocity', 0):.2f}m/s")
    print(f"   - 站立相: {gait_params.get('stance_phase', 0):.1f}%")
    print(f"   - 摆动相: {gait_params.get('swing_phase', 0):.1f}%")
    print(f"   - 双支撑相: {gait_params.get('double_support', 0):.1f}%")
    
    # 3. 生成医疗报告
    print("\n2️⃣ 生成医疗报告...")
    
    if not patient_info:
        patient_info = {
            'name': '测试患者',
            'gender': '男',
            'age': 65,
            'id': f'PT{datetime.now().strftime("%Y%m%d%H%M")}',
            'height': 170,
            'weight': 65
        }
    
    # 使用报告生成器
    generator = FullMedicalReportGenerator()
    html_content = generator.generate_report_from_algorithm(
        algorithm_result=result,
        patient_info=patient_info
    )
    
    # 保存报告
    report_name = f"report_{Path(csv_file_path).stem}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.html"
    report_path = Path(report_name)
    
    with open(report_path, 'w', encoding='utf-8') as f:
        f.write(html_content)
    
    print(f"   ✅ 报告已生成: {report_path}")
    
    return {
        'analysis': result,
        'report_path': report_path
    }

def batch_test(data_dir=None):
    """批量测试多个文件"""
    
    print_header("🔬 批量测试模式")
    
    if not data_dir:
        data_dir = "/Users/xidada/foot-pressure-analysis/数据/2025-08-09/detection_data/"
    
    # 获取所有CSV文件
    csv_files = list(Path(data_dir).glob("*.csv"))
    
    if not csv_files:
        print(f"   ❌ 未找到CSV文件: {data_dir}")
        return
    
    print(f"   找到 {len(csv_files)} 个CSV文件")
    
    results = []
    for csv_file in csv_files:
        result = test_single_file(str(csv_file))
        if result:
            results.append(result)
    
    # 汇总统计
    print_header("📈 测试汇总")
    print(f"   成功分析: {len(results)}/{len(csv_files)} 个文件")
    
    if results:
        # 计算平均值
        avg_stance = sum(r['analysis']['gait_parameters'].get('stance_phase', 0) 
                        for r in results) / len(results)
        avg_swing = sum(r['analysis']['gait_parameters'].get('swing_phase', 0) 
                       for r in results) / len(results)
        
        print(f"   平均站立相: {avg_stance:.1f}%")
        print(f"   平均摆动相: {avg_swing:.1f}%")
        print(f"   参考范围: 站立相60-68%, 摆动相32-40%")

def interactive_test():
    """交互式测试"""
    
    print_header("🎯 足部压力分析系统 - 最终测试")
    
    print("\n请选择测试模式:")
    print("1. 测试单个文件")
    print("2. 批量测试目录")
    print("3. 生成完整报告（推荐）")
    print("4. 退出")
    
    choice = input("\n请输入选择 (1-4): ").strip()
    
    if choice == '1':
        file_path = input("请输入CSV文件路径: ").strip()
        if Path(file_path).exists():
            test_single_file(file_path)
        else:
            print(f"❌ 文件不存在: {file_path}")
    
    elif choice == '2':
        dir_path = input("请输入数据目录路径 (回车使用默认): ").strip()
        if not dir_path:
            batch_test()
        else:
            batch_test(dir_path)
    
    elif choice == '3':
        # 使用默认测试文件生成完整报告
        test_file = "/Users/xidada/foot-pressure-analysis/数据/2025-08-09/detection_data/曾超-第6步-4.5米步道折返-20250809_171226.csv"
        
        if Path(test_file).exists():
            print(f"\n使用测试文件: {Path(test_file).name}")
            
            # 设置患者信息
            patient_info = {
                'name': input("患者姓名 (回车使用'曾超'): ").strip() or '曾超',
                'gender': input("性别 (男/女, 回车使用'男'): ").strip() or '男',
                'age': int(input("年龄 (回车使用68): ").strip() or '68'),
                'id': f'PT{datetime.now().strftime("%Y%m%d%H%M")}',
                'height': int(input("身高cm (回车使用170): ").strip() or '170'),
                'weight': int(input("体重kg (回车使用65): ").strip() or '65')
            }
            
            # 生成报告
            report_path = generate_report_with_final_algorithm(test_file)
            
            if report_path:
                print(f"\n✅ 完整医疗报告已生成: {report_path}")
                
                # 自动打开报告
                import platform
                if platform.system() == 'Darwin':  # macOS
                    os.system(f"open {report_path}")
                elif platform.system() == 'Windows':
                    os.system(f"start {report_path}")
                else:  # Linux
                    os.system(f"xdg-open {report_path}")
        else:
            print(f"❌ 测试文件不存在: {test_file}")
    
    elif choice == '4':
        print("\n👋 再见！")
        return
    else:
        print("\n❌ 无效选择")

def main():
    """主函数"""
    
    # 检查命令行参数
    if len(sys.argv) > 1:
        if sys.argv[1] == '--batch':
            # 批量测试模式
            if len(sys.argv) > 2:
                batch_test(sys.argv[2])
            else:
                batch_test()
        elif sys.argv[1] == '--help':
            print("""
使用方法:
  python final_test.py              # 交互式模式
  python final_test.py --batch      # 批量测试默认目录
  python final_test.py --batch DIR  # 批量测试指定目录
  python final_test.py FILE.csv     # 测试单个文件
            """)
        else:
            # 测试单个文件
            test_single_file(sys.argv[1])
    else:
        # 交互式模式
        interactive_test()

if __name__ == "__main__":
    main()