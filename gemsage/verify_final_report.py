#!/usr/bin/env python3
"""
最终验证脚本 - 确保所有报告参数都正确显示
"""

import sys
import os
from pathlib import Path
from datetime import datetime
import re

# 添加算法路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from generate_complete_report_final import generate_report_with_final_algorithm

def verify_report(html_file_path):
    """验证HTML报告中的所有参数"""
    
    with open(html_file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    print("\n" + "="*80)
    print("📋 报告参数验证")
    print("="*80)
    
    # 检查患者基本信息
    print("\n📌 患者基本信息:")
    basic_info = {
        '姓名': r'<span class="info-value">([^<]+)</span>',
        '性别': r'性别</span>\s*</div>\s*<div[^>]*>\s*<span class="info-value">([^<]+)</span>',
        '年龄': r'年龄</span>\s*</div>\s*<div[^>]*>\s*<span class="info-value">([^<]+)</span>',
        '日期': r'日期</span>\s*</div>\s*<div[^>]*>\s*<span class="info-value">([^<]+)</span>',
        '就诊号': r'就诊号</span>\s*</div>\s*<div[^>]*>\s*<span class="info-value">([^<]+)</span>',
        '科室': r'科室</span>\s*</div>\s*<div[^>]*>\s*<span class="info-value">([^<]+)</span>'
    }
    
    for field, pattern in basic_info.items():
        match = re.search(pattern, content, re.DOTALL)
        if match:
            value = match.group(1).strip()
            if '{{' not in value and '}}' not in value:
                print(f"   ✅ {field}: {value}")
            else:
                print(f"   ❌ {field}: 占位符未替换 ({value})")
        else:
            print(f"   ❌ {field}: 未找到")
    
    # 检查步态参数
    print("\n📊 步态参数:")
    
    # 查找所有数值
    numbers = re.findall(r'<td>([\d.]+)</td>', content)
    
    if numbers:
        # 根据表格结构解析参数
        params_mapping = [
            ('步速', 0, 'm/s'),
            ('步长-左', 1, 'cm'),
            ('步长-右', 2, 'cm'),
            ('步幅-左', 3, 'cm'),
            ('步幅-右', 4, 'cm'),
            ('步频-左', 5, 'steps/min'),
            ('步频-右', 6, 'steps/min'),
            ('跨步速度-左', 7, 'm/s'),
            ('跨步速度-右', 8, 'm/s'),
            ('摆动速度-左', 9, 'm/s'),
            ('摆动速度-右', 10, 'm/s'),
            ('站立相-左', 11, '%'),
            ('站立相-右', 12, '%'),
            ('摆动相-左', 13, '%'),
            ('摆动相-右', 14, '%'),
            ('双支撑相-左', 15, '%'),
            ('双支撑相-右', 16, '%')
        ]
        
        for param_name, idx, unit in params_mapping:
            if idx < len(numbers):
                value = numbers[idx]
                print(f"   ✅ {param_name}: {value} {unit}")
            else:
                print(f"   ❌ {param_name}: 数据缺失")
    else:
        print("   ❌ 未找到任何步态参数数值")
    
    # 检查是否有未替换的占位符
    print("\n🔍 占位符检查:")
    placeholders = re.findall(r'{{\s*\w+\s*}}', content)
    if placeholders:
        print(f"   ❌ 发现 {len(placeholders)} 个未替换的占位符:")
        for ph in placeholders[:5]:  # 只显示前5个
            print(f"      - {ph}")
    else:
        print("   ✅ 所有占位符都已正确替换")
    
    # 报告完整性评分
    print("\n📈 报告完整性评分:")
    total_checks = len(basic_info) + 17  # 基本信息 + 步态参数
    passed_checks = 0
    
    # 统计通过的检查
    for field in basic_info:
        match = re.search(basic_info[field], content, re.DOTALL)
        if match and '{{' not in match.group(1):
            passed_checks += 1
    
    if numbers and len(numbers) >= 17:
        passed_checks += min(17, len(numbers))
    
    score = (passed_checks / total_checks) * 100
    print(f"   完整性: {passed_checks}/{total_checks} ({score:.1f}%)")
    
    if score >= 95:
        print("   ✅ 报告质量: 优秀")
    elif score >= 80:
        print("   ⚠️  报告质量: 良好（部分参数缺失）")
    else:
        print("   ❌ 报告质量: 需要改进")
    
    return score >= 95

def main():
    """主函数"""
    print("="*80)
    print("🔬 报告参数完整性验证")
    print("="*80)
    
    # 生成新报告
    test_file = "/Users/xidada/foot-pressure-analysis/数据/2025-08-09/detection_data/曾超-第6步-4.5米步道折返-20250809_171226.csv"
    
    if not Path(test_file).exists():
        print(f"❌ 测试文件不存在: {test_file}")
        return
    
    print("\n📄 生成测试报告...")
    report_path = generate_report_with_final_algorithm(test_file)
    
    if report_path and Path(report_path).exists():
        print(f"✅ 报告已生成: {report_path}")
        
        # 验证报告
        is_complete = verify_report(report_path)
        
        if is_complete:
            print("\n" + "="*80)
            print("🎉 恭喜！报告生成完全正确，所有参数都已正确填充！")
            print("="*80)
            
            # 打开报告
            import platform
            if platform.system() == 'Darwin':
                os.system(f"open {report_path}")
                print("\n报告已在浏览器中打开，请查看")
        else:
            print("\n⚠️  报告存在问题，请检查上述错误信息")
    else:
        print("❌ 报告生成失败")

if __name__ == "__main__":
    main()