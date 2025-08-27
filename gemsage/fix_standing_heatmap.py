#!/usr/bin/env python3
"""
修复站立热力图显示问题
"""
import pandas as pd
import numpy as np
from gait_report_generator import CompleteGaitAnalyzer

def test_standing_analysis():
    """测试站立数据分析结果"""
    print("🔍 测试站立数据分析...")
    
    # 读取站立数据
    csv_file = "/Users/xidada/GemSage/for test/1/曾超08-第3步-静态站立-20250809_182406.csv"
    df = pd.read_csv(csv_file)
    
    # 创建分析器
    analyzer = CompleteGaitAnalyzer()
    
    # 分析站立数据
    results = analyzer.analyze_standing(df, 'standing')
    
    print("📊 站立分析结果:")
    for key, value in results.items():
        if 'chart' in key:
            print(f"   {key}: SVG长度={len(str(value)) if value else 0}")
        else:
            print(f"   {key}: {value}")
    
    # 检查关键变量是否存在
    expected_vars = [
        'left_foot_static_chart',
        'right_foot_static_chart', 
        'left_foot_static_max',
        'right_foot_static_max',
        'left_foot_static_offset',
        'right_foot_static_offset',
        'left_foot_static_support_ratio',
        'right_foot_static_support_ratio'
    ]
    
    print(f"\n✅ 关键变量检查:")
    for var in expected_vars:
        exists = var in results
        value = results.get(var, "不存在")
        print(f"   {var}: {'✅' if exists else '❌'} {value}")
    
    return results

def generate_test_report():
    """生成测试报告验证修复效果"""
    print("\n📋 生成测试报告...")
    
    # 仅处理第1组数据
    from gait_report_generator import CompleteReportGenerator
    
    generator = CompleteReportGenerator()
    test_data_groups = [
        {
            'name': '测试者A', 
            'age': 55, 
            'folder': '/Users/xidada/GemSage/for test/1'
        }
    ]
    
    for group in test_data_groups:
        print(f"\n🔄 处理 {group['name']} (年龄: {group['age']}岁)")
        report_file = f"/Users/xidada/GemSage/fixed_standing_report_{group['name']}.html"
        
        try:
            generator.generate_report(group['folder'], group['age'], group['name'], report_file)
            print(f"✅ 报告生成成功: {report_file}")
        except Exception as e:
            print(f"❌ 报告生成失败: {e}")

if __name__ == "__main__":
    # 先测试分析结果
    results = test_standing_analysis()
    
    # 再生成完整报告测试
    generate_test_report()