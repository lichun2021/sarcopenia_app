#!/usr/bin/env python3
"""
简单演示：多个CSV合并成一个JSON的核心逻辑
"""

import sys
import json
sys.path.append('/Users/xidada/foot-pressure-analysis/algorithms')
from core_calculator import PressureAnalysisCore

def merge_csvs_to_one_json(csv_files):
    """多个CSV合并成一个JSON"""
    
    analyzer = PressureAnalysisCore()
    all_results = []
    
    # 1. 分析每个CSV
    for csv_file in csv_files:
        result = analyzer.comprehensive_analysis_final(csv_file)
        if result:
            all_results.append(result)
    
    # 2. 合并所有数据
    if not all_results:
        return None
    
    # 把所有步数加起来，所有步长平均
    total_steps = 0
    total_step_length = 0
    total_velocity = 0
    count = 0
    
    for result in all_results:
        gait = result.get('gait_analysis', {})
        if gait.get('step_count', 0) > 0:
            total_steps += gait.get('step_count', 0)
            total_step_length += gait.get('average_step_length', 0)
            total_velocity += gait.get('average_velocity', 0)
            count += 1
    
    # 3. 生成合并后的JSON
    merged_json = {
        'gait_analysis': {
            'step_count': total_steps,  # 总步数
            'average_step_length': total_step_length / count if count > 0 else 0,  # 平均步长
            'average_velocity': total_velocity / count if count > 0 else 0,  # 平均速度
            'cadence': 120.0  # 简化
        },
        'balance_analysis': all_results[0].get('balance_analysis', {}),  # 用第一个的
        'file_info': {
            'total_files': len(csv_files),
            'merged_data': True
        }
    }
    
    return merged_json

# 演示
if __name__ == '__main__':
    # 假设有3个CSV文件
    csv_list = [
        "肌少症数据/刘云帆-步道4圈-29岁.csv",
        # 可以添加更多文件
    ]
    
    merged = merge_csvs_to_one_json(csv_list)
    
    # 保存合并后的JSON
    with open('merged_analysis.json', 'w', encoding='utf-8') as f:
        json.dump(merged, f, ensure_ascii=False, indent=2, default=str)
    
    print("✅ 多个CSV已合并成一个JSON: merged_analysis.json")
    print(f"总步数: {merged['gait_analysis']['step_count']}")
    print(f"平均步长: {merged['gait_analysis']['average_step_length']:.3f}m")