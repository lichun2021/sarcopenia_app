#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
基于专业模版的改进版报告生成器
集成 gait_report_generator.py 的专业模版和改进功能
"""

import os
import pandas as pd
import numpy as np
from datetime import datetime
from scipy.signal import find_peaks
import matplotlib.pyplot as plt
from matplotlib.patches import FancyArrowPatch
from io import BytesIO
import warnings
warnings.filterwarnings('ignore')

# 导入专业报告生成器和改进功能
from gait_report_generator import CompleteGaitAnalyzer
from improved_report_generator import (
    ImprovedReportFormatter,
    FootprintAnalyzer,
    ComprehensiveAssessmentTable,
    UnifiedReportStyle
)

def generate_professional_improved_report():
    """使用专业模版生成改进版报告"""
    
    print("🔥 使用专业模版生成改进版报告...")
    
    # 初始化专业分析器
    analyzer = CompleteGaitAnalyzer()
    
    # 加载所有测试数据
    test_data = {}
    data_dir = 'for test/1'
    
    # 定义文件映射
    file_mapping = {
        'sitting': '曾超08-第1步-静止坐姿-20250809_182344.csv',
        'situp': '曾超08-第2步-五次起坐-20250809_182352.csv', 
        'standing': '曾超08-第3步-静态站立-20250809_182406.csv',
        'tandem_standing': '曾超08-第4步-前后脚站立-20250809_182418.csv',
        'side_standing': '曾超08-第5步-双脚前后站立-20250809_182431.csv',
        'walking': '曾超08-第6步-步态行走-20250809_182440.csv'
    }
    
    # 加载数据
    for test_name, filename in file_mapping.items():
        file_path = os.path.join(data_dir, filename)
        if os.path.exists(file_path):
            try:
                df = pd.read_csv(file_path)
                # 解析data列
                pressure_arrays = []
                for _, row in df.iterrows():
                    data_str = row['data'].strip('[]')
                    data_array = [int(x) for x in data_str.split(',')]
                    pressure_arrays.append(data_array)
                test_data[test_name] = np.array(pressure_arrays)
                print(f"✓ 已加载 {test_name}: {test_data[test_name].shape}")
            except Exception as e:
                print(f"✗ 加载 {test_name} 失败: {e}")
    
    # 使用专业分析器分析数据
    all_results = {}
    formatter = ImprovedReportFormatter()
    
    # 分析各项测试
    if 'sitting' in test_data:
        print("📊 分析静态坐姿...")
        all_results['sitting'] = analyzer.analyze_sitting(test_data['sitting'])
    
    if 'situp' in test_data:
        print("📊 分析五次起坐...")
        all_results['situp'] = analyzer.analyze_situp(test_data['situp'])
    
    if 'standing' in test_data:
        print("📊 分析静态站立...")
        all_results['standing'] = analyzer.analyze_standing(test_data['standing'], 'standing')
    
    if 'tandem_standing' in test_data:
        print("📊 分析前后脚站立...")
        all_results['tandem_standing'] = analyzer.analyze_standing(test_data['tandem_standing'], 'tandem')
    
    if 'side_standing' in test_data:
        print("📊 分析侧方位站立...")
        all_results['side_standing'] = analyzer.analyze_standing(test_data['side_standing'], 'side')
    
    if 'walking' in test_data:
        print("📊 分析步态行走...")
        all_results['gait'] = analyzer.analyze_gait(test_data['walking'])
    
    # 患者信息
    patient_info = {
        'name': '曾超08',
        'age': 65,
        'gender': '男',
        'patient_id': '20250826001',
        'hospital': '测试医院',
        'department': '康复医学科'
    }
    
    # 使用专业分析器生成HTML报告，并应用改进功能
    print("🎨 生成专业HTML报告...")
    
    # 生成基础的专业报告
    professional_html = analyzer.generate_html_report(all_results, patient_info)
    
    # 应用改进功能
    print("✨ 应用改进功能...")
    
    # 增强现有的HTML报告
    enhanced_html = enhance_professional_report(professional_html, all_results, formatter)
    
    # 保存报告
    report_filename = f"professional_improved_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.html"
    with open(report_filename, 'w', encoding='utf-8') as f:
        f.write(enhanced_html)
    
    print(f"✅ 专业改进版报告已生成：{report_filename}")
    return report_filename

def enhance_professional_report(original_html: str, test_results: Dict, formatter: ImprovedReportFormatter) -> str:
    """增强专业报告，添加改进功能"""
    
    # 1. 添加统一样式
    style = UnifiedReportStyle.get_unified_css()
    
    # 2. 生成综合对比表
    comparison_table = ComprehensiveAssessmentTable.generate_comparison_table(test_results)
    
    # 3. 应用数值箭头标注
    enhanced_html = apply_value_arrows(original_html, test_results, formatter)
    
    # 4. 应用左右对比箭头
    enhanced_html = apply_comparison_arrows(enhanced_html, test_results, formatter)
    
    # 5. 插入样式和对比表
    if '</head>' in enhanced_html:
        enhanced_html = enhanced_html.replace('</head>', style + '</head>')
    else:
        enhanced_html = style + enhanced_html
    
    # 在综合评估部分前插入对比表
    if '综合评估与建议' in enhanced_html:
        insert_pos = enhanced_html.find('<h2>综合评估与建议</h2>')
        if insert_pos != -1:
            enhanced_html = enhanced_html[:insert_pos] + comparison_table + enhanced_html[insert_pos:]
    
    return enhanced_html

def apply_value_arrows(html: str, results: Dict, formatter: ImprovedReportFormatter) -> str:
    """应用数值超标箭头标注"""
    
    # 替换步速值
    if 'gait' in results and 'gait_speed' in results['gait']:
        speed = results['gait']['gait_speed']
        formatted_speed = formatter.format_value_with_arrow(speed, lower=0.8, decimal=2, unit=' m/s')
        # 查找并替换HTML中的步速值
        import re
        html = re.sub(r'(\d+\.\d+)\s*m/s', formatted_speed, html, count=1)
    
    # 替换五次起坐时间
    if 'situp' in results and 'total_time' in results['situp']:
        time_val = results['situp']['total_time']
        formatted_time = formatter.format_value_with_arrow(time_val, upper=15, decimal=1, unit='秒')
        html = re.sub(r'(\d+\.\d+)\s*秒', formatted_time, html, count=1)
    
    return html

def apply_comparison_arrows(html: str, results: Dict, formatter: ImprovedReportFormatter) -> str:
    """应用左右对比箭头标注"""
    
    # 替换坐姿压力对比
    if 'sitting' in results:
        sitting = results['sitting']
        if 'left_pressure' in sitting and 'right_pressure' in sitting:
            comparison = formatter.format_comparison_with_arrow(
                sitting['left_pressure'], 
                sitting['right_pressure'],
                decimal=1,
                unit=' N'
            )
            # 查找并替换左右压力值
            import re
            # 这里需要根据专业模版的具体格式来替换
            html = re.sub(r'左侧[：:]\s*(\d+\.\d+)\s*N', f'左侧：{comparison["left"]}', html)
            html = re.sub(r'右侧[：:]\s*(\d+\.\d+)\s*N', f'右侧：{comparison["right"]}', html)
    
    return html

if __name__ == "__main__":
    generate_professional_improved_report()
    
    <div class="info-header">
        <div class="info-item"><strong>姓名：</strong>测试患者</div>
        <div class="info-item"><strong>年龄：</strong>65岁</div>
        <div class="info-item"><strong>性别：</strong>男</div>
        <div class="info-item"><strong>就诊号：</strong>2025082601</div>
        <div class="info-item"><strong>检测时间：</strong>{datetime.now().strftime('%Y-%m-%d %H:%M')}</div>
    </div>
    
    <h2>✅ 改进功能展示</h2>
    
    <h3>1. 数值超标红绿箭头标注</h3>
    <table>
        <tr>
            <th>测试项目</th>
            <th>测量值</th>
            <th>参考标准</th>
            <th>评价</th>
        </tr>
        <tr>
            <td>步速</td>
            <td>{formatter.format_value_with_arrow(0.75, lower=0.8, decimal=2, unit=' m/s')}</td>
            <td>≥0.8 m/s</td>
            <td>偏慢</td>
        </tr>
        <tr>
            <td>五次起坐时间</td>
            <td>{formatter.format_value_with_arrow(13.5, upper=12, decimal=1, unit=' 秒')}</td>
            <td>≤12秒</td>
            <td>偏慢</td>
        </tr>
        <tr>
            <td>微抖动</td>
            <td>{formatter.format_value_with_arrow(0.45, upper=0.5, decimal=2, unit=' mm')}</td>
            <td>≤0.5 mm</td>
            <td>正常</td>
        </tr>
    </table>
    
    <h3>2. 左右对比大侧红箭头</h3>
    <table>
        <tr>
            <th>测试项目</th>
            <th>左侧</th>
            <th>右侧</th>
            <th>对称性评价</th>
        </tr>
"""
    
    # 坐姿压力对比
    sitting_comparison = formatter.format_comparison_with_arrow(420.5, 380.2, decimal=1, unit=' N')
    html += f"""
        <tr>
            <td>静态坐姿压力</td>
            <td>{sitting_comparison['left']}</td>
            <td>{sitting_comparison['right']}</td>
            <td>左侧偏重</td>
        </tr>
"""
    
    # 站立压力对比
    standing_comparison = formatter.format_comparison_with_arrow(340.2, 365.8, decimal=1, unit=' N')
    html += f"""
        <tr>
            <td>静态站立压力</td>
            <td>{standing_comparison['left']}</td>
            <td>{standing_comparison['right']}</td>
            <td>右侧偏重</td>
        </tr>
"""
    
    # 步长对比
    step_comparison = formatter.format_comparison_with_arrow(0.62, 0.68, decimal=2, unit=' m')
    html += f"""
        <tr>
            <td>行走步长</td>
            <td>{step_comparison['left']}</td>
            <td>{step_comparison['right']}</td>
            <td>右侧步长较大</td>
        </tr>
    </table>
    
    <h3>3. 足底形状和力线图</h3>
    <div class="pressure-chart">
"""
    
    # 生成足底形状和力线图
    footprint_svg = FootprintAnalyzer.generate_footprint_svg(kpa, "Standing Test with Force Lines")
    html += footprint_svg
    
    html += f"""
    </div>
    
    <h3>4. 综合评估对比表</h3>
    {ComprehensiveAssessmentTable.generate_comparison_table(test_results)}
    
    <div class="conclusion">
        <h2>改进特性说明</h2>
        <p>本报告已实现以下改进功能：</p>
        <ul style="margin: 10px 0; padding-left: 20px; color: white;">
            <li>✅ 数值超标自动标注：超上限显示红↑，低于下限显示绿↓</li>
            <li>✅ 左右对比智能标注：较大一侧自动加红色箭头</li>
            <li>✅ 足底形状可视化：自动提取足印轮廓，显示白色边界</li>
            <li>✅ 力线分析：黄色箭头显示从后跟→COP→前脚掌的力传导路径</li>
            <li>✅ 统一样式系统：所有文字使用14px，标题分级清晰</li>
            <li>✅ 综合对比表：多维度数据对比，自动计算对称性百分比</li>
        </ul>
    </div>
    
</body>
</html>
"""
    
    # 保存报告
    report_filename = f"improved_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.html"
    with open(report_filename, 'w', encoding='utf-8') as f:
        f.write(html)
    
    print(f"✅ 改进版报告已生成：{report_filename}")
    print("\n📊 改进功能：")
    print("   1. 数值超标红绿箭头标注 ✅")
    print("   2. 左右对比大侧红箭头 ✅")  
    print("   3. 足底形状和力线图 ✅")
    print("   4. 统一字体样式 ✅")
    print("   5. 步态左右脚力量标注 ✅")
    print("   6. 综合评估对比表 ✅")
    print(f"\n请在浏览器中打开 {report_filename} 查看效果")

if __name__ == "__main__":
    quick_analyze_and_report()