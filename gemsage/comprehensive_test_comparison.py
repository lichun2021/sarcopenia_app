#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
全面测试所有数据文件，生成详细对比报告
"""

import glob
import json
from pathlib import Path
from datetime import datetime
from generate_complete_report_final import generate_report_with_final_algorithm
from core_calculator_final import PressureAnalysisFinal
import re

def extract_report_values(html_content):
    """从HTML报告中提取关键数值"""
    values = {}
    
    # 使用正则表达式提取各项数值
    patterns = {
        'walking_speed': r'步速.*?<td>([\d.]+)</td>',
        'left_step_length': r'步长.*?左.*?<td>([\d.]+)</td>',
        'right_step_length': r'步长.*?右.*?<td>([\d.]+)</td>',
        'left_stride_length': r'步幅.*?左.*?<td>([\d.]+)</td>',
        'right_stride_length': r'步幅.*?右.*?<td>([\d.]+)</td>',
        'left_cadence': r'步频.*?左.*?<td>([\d.]+)</td>',
        'right_cadence': r'步频.*?右.*?<td>([\d.]+)</td>',
        'left_stride_speed': r'跨步速度.*?左.*?<td>([\d.]+)</td>',
        'right_stride_speed': r'跨步速度.*?右.*?<td>([\d.]+)</td>',
        'left_swing_speed': r'摆动速度.*?左.*?<td>([\d.]+)</td>',
        'right_swing_speed': r'摆动速度.*?右.*?<td>([\d.]+)</td>',
        'left_stance_phase': r'站立相.*?左.*?<td>([\d.]+)</td>',
        'right_stance_phase': r'站立相.*?右.*?<td>([\d.]+)</td>',
        'left_swing_phase': r'摆动相.*?左.*?<td>([\d.]+)</td>',
        'right_swing_phase': r'摆动相.*?右.*?<td>([\d.]+)</td>',
        'left_double_support': r'双支撑相.*?左.*?<td>([\d.]+)</td>',
        'right_double_support': r'双支撑相.*?右.*?<td>([\d.]+)</td>',
        'step_width': r'步宽.*?<td>([\d.]+)</td>',
        'turn_time': r'转身时间.*?<td>([\d.]+)</td>'
    }
    
    for key, pattern in patterns.items():
        match = re.search(pattern, html_content, re.DOTALL)
        if match:
            values[key] = float(match.group(1))
        else:
            values[key] = None
    
    return values

def comprehensive_test():
    """全面测试所有数据文件"""
    
    print("🔬 全面数据测试与对比分析")
    print("="*70)
    
    # 查找所有步态测试文件
    test_files = glob.glob("数据/*/detection_data/*第6步*.csv")
    test_files.sort()
    
    if not test_files:
        print("❌ 未找到测试文件")
        return
    
    print(f"📁 找到 {len(test_files)} 个测试文件\n")
    
    # 初始化分析器
    analyzer = PressureAnalysisFinal()
    
    # 存储所有结果
    all_results = []
    
    # 逐个分析文件
    for i, file_path in enumerate(test_files, 1):
        file_name = Path(file_path).name
        dataset_name = Path(file_path).parts[-3]
        
        print(f"[{i}/{len(test_files)}] 分析: {dataset_name}/{file_name}")
        print("-" * 60)
        
        try:
            # 1. 使用核心算法分析
            core_result = analyzer.comprehensive_analysis_final(file_path)
            
            if 'error' in core_result:
                print(f"   ❌ 核心算法分析失败: {core_result['error']}")
                continue
            
            # 2. 生成完整报告
            report_path = generate_report_with_final_algorithm(file_path)
            
            # 3. 读取生成的HTML报告
            with open('full_complete_report_final.html', 'r', encoding='utf-8') as f:
                html_content = f.read()
            
            # 4. 提取报告中的数值
            report_values = extract_report_values(html_content)
            
            # 5. 从核心算法提取原始数据
            gait_params = core_result.get('gait_parameters', {})
            left_foot = gait_params.get('left_foot', {})
            right_foot = gait_params.get('right_foot', {})
            
            # 6. 整合结果
            result = {
                'file': file_name,
                'dataset': dataset_name,
                'test_duration': core_result.get('file_info', {}).get('test_duration', 0),
                'total_distance': gait_params.get('total_distance', 0),
                'step_count': gait_params.get('step_count', 0),
                
                # 核心算法原始数据
                'core_data': {
                    'avg_velocity': gait_params.get('average_velocity', 0),
                    'avg_step_length': gait_params.get('average_step_length', 0),
                    'cadence': gait_params.get('cadence', 0),
                    'left_step_length': left_foot.get('average_step_length_m', 0) * 100,
                    'right_step_length': right_foot.get('average_step_length_m', 0) * 100,
                    'left_cadence': left_foot.get('cadence', 0),
                    'right_cadence': right_foot.get('cadence', 0),
                    'left_swing_speed': left_foot.get('swing_speed_mps', 0),
                    'right_swing_speed': right_foot.get('swing_speed_mps', 0),
                },
                
                # 报告显示数据
                'report_data': report_values,
                
                # 数据一致性检查
                'consistency_check': {}
            }
            
            # 7. 检查数据一致性
            if report_values.get('walking_speed'):
                diff = abs(report_values['walking_speed'] - gait_params.get('average_velocity', 0))
                result['consistency_check']['speed_diff'] = diff
                result['consistency_check']['speed_match'] = diff < 0.01
            
            # 8. 检查是否有0值
            zero_values = []
            for key, value in report_values.items():
                if value == 0 or value is None:
                    zero_values.append(key)
            result['zero_values'] = zero_values
            
            all_results.append(result)
            
            # 9. 打印摘要
            print(f"   ✅ 分析成功")
            print(f"   📊 步速: {report_values.get('walking_speed', 0):.2f} m/s")
            print(f"   📏 步长: 左={report_values.get('left_step_length', 0):.1f}cm, "
                  f"右={report_values.get('right_step_length', 0):.1f}cm")
            print(f"   🎵 步频: 左={report_values.get('left_cadence', 0):.1f}, "
                  f"右={report_values.get('right_cadence', 0):.1f} 步/分")
            print(f"   🚀 跨步速度: 左={report_values.get('left_stride_speed', 0):.2f}, "
                  f"右={report_values.get('right_stride_speed', 0):.2f} m/s")
            
            if zero_values:
                print(f"   ⚠️ 发现0值参数: {', '.join(zero_values)}")
            
        except Exception as e:
            print(f"   ❌ 处理异常: {e}")
            import traceback
            if "--debug" in sys.argv:
                traceback.print_exc()
    
    # 生成综合对比报告
    generate_comparison_report(all_results)
    
    return all_results

def generate_comparison_report(results):
    """生成综合对比报告"""
    
    print("\n" + "="*70)
    print("📊 综合对比分析报告")
    print("="*70)
    
    if not results:
        print("❌ 无有效结果")
        return
    
    # 1. 统计概览
    print(f"\n📈 统计概览:")
    print(f"   总文件数: {len(results)}")
    print(f"   成功分析: {len([r for r in results if r.get('report_data')])}")
    print(f"   存在0值: {len([r for r in results if r.get('zero_values')])}")
    
    # 2. 参数范围分析
    print(f"\n📊 参数范围分析:")
    
    params_to_analyze = [
        ('walking_speed', '步速', 'm/s'),
        ('left_step_length', '左步长', 'cm'),
        ('right_step_length', '右步长', 'cm'),
        ('left_cadence', '左步频', '步/分'),
        ('right_cadence', '右步频', '步/分'),
        ('left_stride_speed', '左跨步速度', 'm/s'),
        ('right_stride_speed', '右跨步速度', 'm/s')
    ]
    
    for param_key, param_name, unit in params_to_analyze:
        values = []
        for r in results:
            if r.get('report_data') and r['report_data'].get(param_key) is not None:
                values.append(r['report_data'][param_key])
        
        if values:
            min_val = min(values)
            max_val = max(values)
            avg_val = sum(values) / len(values)
            print(f"   {param_name}: {min_val:.2f} ~ {max_val:.2f} {unit} (平均: {avg_val:.2f})")
    
    # 3. 左右对称性分析
    print(f"\n⚖️ 左右对称性分析:")
    
    for r in results:
        if r.get('report_data'):
            rd = r['report_data']
            file_name = r['file']
            
            # 计算左右差异
            step_diff = abs(rd.get('left_step_length', 0) - rd.get('right_step_length', 0))
            cadence_diff = abs(rd.get('left_cadence', 0) - rd.get('right_cadence', 0))
            stride_speed_diff = abs(rd.get('left_stride_speed', 0) - rd.get('right_stride_speed', 0))
            
            print(f"\n   {file_name[:30]}:")
            print(f"      步长差异: {step_diff:.1f} cm")
            print(f"      步频差异: {cadence_diff:.1f} 步/分")
            print(f"      跨步速度差异: {stride_speed_diff:.2f} m/s")
    
    # 4. 异常值检测
    print(f"\n⚠️ 异常值检测:")
    
    for r in results:
        if r.get('report_data'):
            rd = r['report_data']
            file_name = r['file']
            anomalies = []
            
            # 检查异常值
            if rd.get('walking_speed', 0) < 0.3 or rd.get('walking_speed', 0) > 2.0:
                anomalies.append(f"步速异常: {rd.get('walking_speed', 0):.2f} m/s")
            
            if rd.get('left_cadence', 0) == 0 or rd.get('right_cadence', 0) == 0:
                anomalies.append(f"步频为0")
            
            if rd.get('left_double_support', 0) > 50:
                anomalies.append(f"双支撑相异常: {rd.get('left_double_support', 0):.1f}%")
            
            if anomalies:
                print(f"\n   {file_name[:30]}:")
                for anomaly in anomalies:
                    print(f"      - {anomaly}")
    
    # 5. 保存详细对比数据
    output_file = f"comprehensive_test_comparison_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    
    print(f"\n💾 详细对比数据已保存: {output_file}")
    
    # 6. 生成HTML对比表格
    generate_html_comparison_table(results)

def generate_html_comparison_table(results):
    """生成HTML对比表格"""
    
    html_content = """<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>步态分析数据对比表</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 20px; }
        h1 { color: #333; text-align: center; }
        table { border-collapse: collapse; width: 100%; margin: 20px 0; }
        th, td { border: 1px solid #ddd; padding: 8px; text-align: center; }
        th { background-color: #4CAF50; color: white; }
        tr:nth-child(even) { background-color: #f2f2f2; }
        .zero-value { color: red; font-weight: bold; }
        .high-value { color: orange; }
        .normal-value { color: green; }
    </style>
</head>
<body>
    <h1>步态分析数据对比表</h1>
    <table>
        <thead>
            <tr>
                <th>文件名</th>
                <th>步速(m/s)</th>
                <th>左步长(cm)</th>
                <th>右步长(cm)</th>
                <th>左步频</th>
                <th>右步频</th>
                <th>左跨步速度(m/s)</th>
                <th>右跨步速度(m/s)</th>
                <th>左摆动速度(m/s)</th>
                <th>右摆动速度(m/s)</th>
            </tr>
        </thead>
        <tbody>"""
    
    for r in results:
        if r.get('report_data'):
            rd = r['report_data']
            file_name = r['file'][:30]
            
            html_content += f"""
            <tr>
                <td>{file_name}</td>
                <td class="{'zero-value' if rd.get('walking_speed', 0) == 0 else 'normal-value'}">{rd.get('walking_speed', 0):.2f}</td>
                <td class="{'zero-value' if rd.get('left_step_length', 0) == 0 else ''}">{rd.get('left_step_length', 0):.1f}</td>
                <td class="{'zero-value' if rd.get('right_step_length', 0) == 0 else ''}">{rd.get('right_step_length', 0):.1f}</td>
                <td class="{'zero-value' if rd.get('left_cadence', 0) == 0 else ''}">{rd.get('left_cadence', 0):.1f}</td>
                <td class="{'zero-value' if rd.get('right_cadence', 0) == 0 else ''}">{rd.get('right_cadence', 0):.1f}</td>
                <td class="{'zero-value' if rd.get('left_stride_speed', 0) == 0 else ''}">{rd.get('left_stride_speed', 0):.2f}</td>
                <td class="{'zero-value' if rd.get('right_stride_speed', 0) == 0 else ''}">{rd.get('right_stride_speed', 0):.2f}</td>
                <td class="{'zero-value' if rd.get('left_swing_speed', 0) == 0 else ''}">{rd.get('left_swing_speed', 0):.2f}</td>
                <td class="{'zero-value' if rd.get('right_swing_speed', 0) == 0 else ''}">{rd.get('right_swing_speed', 0):.2f}</td>
            </tr>"""
    
    html_content += """
        </tbody>
    </table>
    <p style="text-align: center; color: #666;">生成时间: """ + datetime.now().strftime('%Y-%m-%d %H:%M:%S') + """</p>
</body>
</html>"""
    
    output_file = f"comparison_table_{datetime.now().strftime('%Y%m%d_%H%M%S')}.html"
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(html_content)
    
    print(f"📊 HTML对比表格已生成: {output_file}")

if __name__ == "__main__":
    import sys
    results = comprehensive_test()
    
    # 如果有结果，显示总结
    if results:
        print(f"\n✅ 测试完成，共分析 {len(results)} 个文件")