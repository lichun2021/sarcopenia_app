#!/usr/bin/env python3
"""
将目录中的多个CSV(例如6个测试文件)合并分析，输出一份综合HTML报告。

用法:
  python3 generate_combined_report.py \
    --dir "/Users/xidada/algorithms/数据/2025-08-09 4/detection_data" \
    --name "曾超" --gender "男" --age 36 --height 170 --weight 65

说明:
  - 自动遍历目录中的 *.csv 文件，逐个使用 PressureAnalysisFinal 分析
  - 按“步数/时长”进行加权合并步态参数，输出一份综合报告
  - COP/热力图优先使用第一份数据的真实轨迹与快照
"""

from __future__ import annotations

import argparse
import os
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, List

from core_calculator_final import PressureAnalysisFinal
from full_medical_report_generator import FullMedicalReportGenerator


def _safe_float(x, default=0.0) -> float:
    try:
        return float(x)
    except Exception:
        return float(default)


def _classify_test_type(path: str) -> str:
    name = Path(path).name
    if '4.5米步道折返' in name or '步道折返' in name:
        return 'walkway_turn'
    if '静坐' in name:
        return 'sitting'
    if '起坐' in name:
        return 'sit_to_stand'
    if '静态站立' in name:
        return 'static_standing'
    if '前后脚站立' in name:
        return 'split_stance'
    if '双脚前后站立' in name:
        return 'double_split_stance'
    return 'unknown'


def analyze_directory_and_merge(dir_path: str) -> Dict[str, Any]:
    dir_p = Path(dir_path)
    csv_files = sorted([str(p) for p in dir_p.glob("*.csv")])
    if not csv_files:
        raise FileNotFoundError(f"目录中未找到CSV文件: {dir_path}")

    analyzer = PressureAnalysisFinal()
    analyses: List[Dict[str, Any]] = []
    by_type: Dict[str, Dict[str, Any]] = {}

    for csv_file in csv_files:
        res = analyzer.comprehensive_analysis_final(csv_file)
        if 'error' in res:
            print(f"⚠️ 跳过文件(无法分析): {csv_file} - {res['error']}")
            continue
        res['__test_type'] = _classify_test_type(csv_file)
        analyses.append(res)
        by_type[res['__test_type']] = res

    if not analyses:
        raise RuntimeError("目录内CSV均无法分析，未得到任何结果")

    # 1) 主报告：选择“步道折返”作为步态指标来源；若无，则选择包含最多步数的文件
    walkway = by_type.get('walkway_turn')
    if not walkway:
        walkway = max(analyses, key=lambda r: r.get('gait_parameters', {}).get('step_count', 0))
    gp = walkway.get('gait_parameters', {})

    # 2) 专项测试：静坐、起坐、静态、前后脚站立、双脚前后站立分别做定性/特征性展示
    sitting = by_type.get('sitting')
    sit_to_stand = by_type.get('sit_to_stand')
    static_standing = by_type.get('static_standing')
    split_stance = by_type.get('split_stance')
    double_split = by_type.get('double_split_stance')

    def _brief(g: Dict[str, Any]) -> str:
        if not g:
            return '无数据'
        _gp = g.get('gait_parameters', {})
        vel = _safe_float(_gp.get('average_velocity', 0.0))
        stance = _safe_float(_gp.get('stance_phase', 60.0))
        step_len = _safe_float(_gp.get('average_step_length', 0.0))
        return f"步速 {vel:.2f} m/s，站立相 {stance:.1f}% ，步长 {step_len:.1f} cm"

    appendix_html = f'''
<div class="section">
  <h3 class="section-title">专项测试附录</h3>
  <div style="font-size:14px;color:#333;line-height:1.8;">
    <p><strong>静坐检测：</strong>{_brief(sitting)}</p>
    <p><strong>起坐测试：</strong>{_brief(sit_to_stand)}</p>
    <p><strong>静态站立：</strong>{_brief(static_standing)}（关注 COP 面积、摆动范围与稳定指数）</p>
    <p><strong>前后脚站立：</strong>{_brief(split_stance)}（关注左右负载、相位与对称性）</p>
    <p><strong>双脚前后站立：</strong>{_brief(double_split)}（关注对称性、稳定性）</p>
  </div>
</div>
'''

    # 3) 可视化基准：优先使用“步道折返”的真实COP与快照
    base_ts = walkway.get('time_series', {}) if walkway else analyses[0].get('time_series', {})
    base_snapshot = walkway.get('pressure_snapshot') if walkway else analyses[0].get('pressure_snapshot')
    base_moments = walkway.get('moments', {}) if walkway else analyses[0].get('moments', {})
    hardware_config = walkway.get('hardware_config', {}) if walkway else analyses[0].get('hardware_config', {})

    gait_parameters = gp
    # 目录总时长（用于报告 file_info.duration）
    total_duration = sum(_safe_float(r.get('file_info', {}).get('duration', 0.0)) for r in analyses)

    combined_result: Dict[str, Any] = {
        'file_info': {
            'path': str(dir_p),
            'format': 'directory_combined',
            'total_frames': None,
            'duration': float(total_duration),
            'total_files': len(analyses),
        },
        'test_type': 'walk_combined',
        'gait_parameters': gait_parameters,
        'hardware_config': hardware_config,
        'time_series': base_ts,
        'pressure_snapshot': base_snapshot,
        'moments': base_moments,
        'analysis_timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'algorithm_version': 'combined_from_directory_final_2025_08_12'
    }

    # 专项附录传入报告生成器
    combined_result['multi_test_appendix_html'] = appendix_html

    return combined_result


def main():
    parser = argparse.ArgumentParser(description='合并目录内多个CSV生成一份综合报告')
    parser.add_argument('--dir', required=True, help='CSV目录路径')
    parser.add_argument('--name', default='合并患者')
    parser.add_argument('--gender', default='男')
    parser.add_argument('--age', type=int, default=60)
    parser.add_argument('--height', type=int, default=170)
    parser.add_argument('--weight', type=int, default=65)
    parser.add_argument('--output', default='combined_report.html')
    args = parser.parse_args()

    combined = analyze_directory_and_merge(args.dir)

    patient_info = {
        'name': args.name,
        'gender': args.gender,
        'age': args.age,
        'id': 'PT-COMBINED',
        'height': args.height,
        'weight': args.weight,
        'department': '康复医学科'
    }

    generator = FullMedicalReportGenerator()
    html = generator.generate_report_from_algorithm(combined, patient_info)

    out_path = Path(args.output)
    with open(out_path, 'w', encoding='utf-8') as f:
        f.write(html)

    print(f"✅ 综合报告已生成: {out_path}")
    if os.name == 'posix':
        os.system(f"open {out_path}")


if __name__ == '__main__':
    main()


