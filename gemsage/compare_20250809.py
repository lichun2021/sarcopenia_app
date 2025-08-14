#!/usr/bin/env python3
"""
对比分析2025-08-09数据集与其他数据
"""

import sys
import os
from pathlib import Path
import json

# 添加路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from core_calculator_final import PressureAnalysisFinal

def analyze_and_compare():
    """分析并对比多组数据"""
    
    # 定义测试文件
    test_files = {
        "2025-08-09 最新": "/Users/xidada/algorithms/数据/2025-08-09/detection_data/曾超08-第6步-4.5米步道折返-20250809_182444.csv",
        "2025-08-09-2": "/Users/xidada/algorithms/数据/2025-08-09 2/detection_data/曾超0809-第6步-4.5米步道折返-20250809_172526.csv",
        "2025-08-09-3": "/Users/xidada/algorithms/数据/2025-08-09 3/detection_data/曾超080902-第6步-4.5米步道折返-20250809_173907.csv",
        "2025-08-09-4": "/Users/xidada/algorithms/数据/2025-08-09 4/detection_data/曾超080903-第6步-4.5米步道折返-20250809_174704.csv",
    }
    
    analyzer = PressureAnalysisFinal()
    results = {}
    
    print("="*80)
    print("📊 多数据集对比分析")
    print("="*80)
    
    for name, file_path in test_files.items():
        if not Path(file_path).exists():
            print(f"\n❌ {name}: 文件不存在")
            continue
            
        print(f"\n📁 分析 {name}:")
        print("-"*60)
        
        try:
            result = analyzer.comprehensive_analysis_final(file_path)
            
            if 'error' in result:
                print(f"   ❌ 分析失败: {result['error']}")
                continue
            
            gait_params = result.get('gait_parameters', {})
            
            # 保存结果
            data = {
                'name': name,
                'step_count': gait_params.get('step_count', 0),
                'average_step_length': gait_params.get('average_step_length', 0),
                'cadence': gait_params.get('cadence', 0),
                'velocity': gait_params.get('average_velocity', 0),
                'stance_phase': gait_params.get('stance_phase', 0),
                'swing_phase': gait_params.get('swing_phase', 0),
                'double_support': gait_params.get('double_support', 0),
            }
            results[name] = data
            
            # 打印结果
            print(f"   步数: {data['step_count']}")
            print(f"   步长: {data['average_step_length']:.2f} cm")
            print(f"   步频: {data['cadence']:.2f} 步/分")
            print(f"   速度: {data['velocity']:.2f} m/s")
            print(f"   站立相: {data['stance_phase']:.1f}%")
            print(f"   双支撑相: {data['double_support']:.1f}%")
            
        except Exception as e:
            print(f"   ❌ 处理错误: {e}")
    
    # 对比分析
    if results:
        print("\n" + "="*80)
        print("📈 对比分析结果")
        print("="*80)
        
        # 计算平均值
        avg_step_length = sum(r['average_step_length'] for r in results.values()) / len(results)
        avg_cadence = sum(r['cadence'] for r in results.values()) / len(results)
        avg_velocity = sum(r['velocity'] for r in results.values()) / len(results)
        
        print(f"\n平均指标:")
        print(f"   平均步长: {avg_step_length:.2f} cm")
        print(f"   平均步频: {avg_cadence:.2f} 步/分")
        print(f"   平均速度: {avg_velocity:.2f} m/s")
        
        # 找出最优和最差
        best_velocity = max(results.values(), key=lambda x: x['velocity'])
        worst_velocity = min(results.values(), key=lambda x: x['velocity'])
        
        print(f"\n最佳速度: {best_velocity['name']} - {best_velocity['velocity']:.2f} m/s")
        print(f"最低速度: {worst_velocity['name']} - {worst_velocity['velocity']:.2f} m/s")
        
        # 评估2025-08-09最新数据
        if "2025-08-09 最新" in results:
            latest = results["2025-08-09 最新"]
            print(f"\n🎯 2025-08-09最新数据评估:")
            
            # 步长评估
            if 60 <= latest['average_step_length'] <= 85:
                print(f"   ✅ 步长 {latest['average_step_length']:.2f}cm - 正常范围")
            else:
                print(f"   ⚠️ 步长 {latest['average_step_length']:.2f}cm - 偏离正常")
            
            # 速度评估
            if 1.0 <= latest['velocity'] <= 1.4:
                print(f"   ✅ 速度 {latest['velocity']:.2f}m/s - 正常范围")
            else:
                print(f"   ⚠️ 速度 {latest['velocity']:.2f}m/s - 偏离正常")
            
            # 站立相评估
            if 60 <= latest['stance_phase'] <= 70:
                print(f"   ✅ 站立相 {latest['stance_phase']:.1f}% - 正常范围")
            else:
                print(f"   ⚠️ 站立相 {latest['stance_phase']:.1f}% - 偏离正常")
    
    # 保存结果
    with open('comparison_20250809.json', 'w', encoding='utf-8') as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    print(f"\n💾 对比结果已保存到: comparison_20250809.json")

if __name__ == "__main__":
    analyze_and_compare()