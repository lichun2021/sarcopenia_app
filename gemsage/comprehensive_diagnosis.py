#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
全面诊断数据不足问题
"""

import os
import sys
import json
import pandas as pd
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from core_calculator import PressureAnalysisCore

def diagnose_csv_file(csv_path):
    """深度诊断CSV文件"""
    print(f"\n{'='*60}")
    print(f"诊断文件: {csv_path}")
    print(f"{'='*60}")
    
    # 1. 检查文件基本信息
    if not os.path.exists(csv_path):
        print("❌ 文件不存在")
        return
    
    file_size = os.path.getsize(csv_path) / 1024  # KB
    print(f"文件大小: {file_size:.2f} KB")
    
    # 2. 读取CSV查看结构
    try:
        df = pd.read_csv(csv_path)
        print(f"CSV行数: {len(df)}")
        print(f"CSV列数: {len(df.columns)}")
        print(f"列名: {list(df.columns)}")
        
        # 检查data列
        if 'data' in df.columns:
            # 统计data列的情况
            non_empty_data = 0
            valid_data_rows = []
            
            for idx, row in df.iterrows():
                data_str = str(row['data']).strip()
                if data_str and data_str != 'nan':
                    non_empty_data += 1
                    # 检查是否是有效的数组格式
                    if data_str.startswith('[') and data_str.endswith(']'):
                        try:
                            # 尝试解析数据
                            data_str_clean = data_str[1:-1]
                            values = [float(x.strip()) for x in data_str_clean.split(',') if x.strip()]
                            if len(values) == 1024:
                                valid_data_rows.append(idx)
                        except:
                            pass
            
            print(f"\n数据分析:")
            print(f"  非空data行: {non_empty_data}/{len(df)}")
            print(f"  有效1024点数据行: {len(valid_data_rows)}")
            
            if valid_data_rows:
                print(f"  有效数据行索引: {valid_data_rows[:5]}{'...' if len(valid_data_rows) > 5 else ''}")
        
        # 检查press列
        if 'press' in df.columns:
            non_zero_press = (df['press'] > 0).sum()
            print(f"  非零压力值行: {non_zero_press}/{len(df)}")
            print(f"  压力值范围: {df['press'].min()} - {df['press'].max()}")
    
    except Exception as e:
        print(f"❌ CSV读取错误: {e}")
        return
    
    # 3. 使用算法分析
    print("\n使用算法分析...")
    analyzer = PressureAnalysisCore()
    
    # 3.1 测试数据解析
    with open(csv_path, 'r', encoding='utf-8') as f:
        csv_content = f.read()
    
    print("\n解析数据...")
    pressure_matrix = analyzer.parse_csv_data(csv_content)
    print(f"解析结果: {len(pressure_matrix)} 个数据帧")
    
    if pressure_matrix:
        # 检查数据结构
        print(f"第一帧类型: {type(pressure_matrix[0])}")
        if isinstance(pressure_matrix[0], list):
            print(f"第一帧大小: {len(pressure_matrix[0])}x{len(pressure_matrix[0][0]) if pressure_matrix[0] else 0}")
    
    # 3.2 测试步态事件检测
    print("\n检测步态事件...")
    gait_events = analyzer.detect_gait_events(pressure_matrix)
    print(f"检测到的事件数: {len(gait_events)}")
    
    if gait_events:
        print("\n前5个事件:")
        for i, event in enumerate(gait_events[:5]):
            print(f"  事件{i+1}: 时间={event['timestamp']}, X={event['cop_x']:.2f}, Y={event['cop_y']:.2f}, 压力={event['pressure']:.2f}")
        
        # 检查事件的有效性
        valid_events = 0
        for event in gait_events:
            if event['pressure'] > 50:  # 压力阈值
                valid_events += 1
        print(f"\n有效事件数（压力>50）: {valid_events}")
    
    # 3.3 测试步态指标计算
    print("\n计算步态指标...")
    step_metrics = analyzer.calculate_step_metrics(gait_events)
    print(f"步态指标结果: {json.dumps(step_metrics, indent=2, ensure_ascii=False)}")
    
    # 3.4 测试平衡分析
    print("\n执行平衡分析...")
    balance_metrics = analyzer.analyze_balance(pressure_matrix)
    print(f"平衡分析结果: {json.dumps(balance_metrics, indent=2, ensure_ascii=False)}")
    
    # 4. 完整分析
    print("\n执行完整分析...")
    full_result = analyzer.comprehensive_analysis_final(csv_path)
    
    print("\n完整分析结果摘要:")
    if 'error' in full_result:
        print(f"❌ 总体错误: {full_result['error']}")
    
    if 'gait_analysis' in full_result:
        if 'error' in full_result['gait_analysis']:
            print(f"❌ 步态分析错误: {full_result['gait_analysis']['error']}")
        else:
            print(f"✅ 步态分析成功")
    
    if 'balance_analysis' in full_result:
        if 'error' in full_result['balance_analysis']:
            print(f"❌ 平衡分析错误: {full_result['balance_analysis']['error']}")
        else:
            print(f"✅ 平衡分析成功")
    
    return full_result

def diagnose_all_files():
    """诊断所有测试文件"""
    # 测试不同类型的文件
    test_files = [
        "/Users/xidada/foot-pressure-analysis/肌少症数据/刘云帆-步道4圈-29岁.csv",
        "/Users/xidada/foot-pressure-analysis/肌少症数据/刘云帆-左脚站立.csv",
        "/Users/xidada/foot-pressure-analysis/肌少症数据/刘云帆-起坐5次-臀部.csv",
        "/Users/xidada/foot-pressure-analysis/肌少症数据/刘云帆-静坐10s.csv"
    ]
    
    results = {}
    for file_path in test_files:
        if os.path.exists(file_path):
            result = diagnose_csv_file(file_path)
            results[os.path.basename(file_path)] = result
    
    # 汇总分析
    print("\n\n" + "="*60)
    print("诊断汇总")
    print("="*60)
    
    for filename, result in results.items():
        print(f"\n{filename}:")
        if result:
            has_gait_error = 'gait_analysis' in result and 'error' in result['gait_analysis']
            has_balance_error = 'balance_analysis' in result and 'error' in result['balance_analysis']
            
            if has_gait_error:
                print(f"  步态分析: ❌ {result['gait_analysis']['error']}")
            else:
                print(f"  步态分析: ✅")
            
            if has_balance_error:
                print(f"  平衡分析: ❌ {result['balance_analysis']['error']}")
            else:
                print(f"  平衡分析: ✅")

if __name__ == "__main__":
    diagnose_all_files()