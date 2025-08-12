#!/usr/bin/env python3
"""
多文件测试运行器：遍历目录中的CSV，逐个计算核心指标，输出控制台摘要，并保存JSON/CSV汇总；
同时生成一份综合HTML报告（主报告基于步道折返，第1-5步作为专项附录）。

用法示例：
  python3 run_multi_tests.py \
    --dir "/Users/xidada/algorithms/数据/2025-08-09 4/detection_data" \
    --name "曾超" --gender "男" --age 36 --height 170 --weight 65 \
    --html combined_report.html --json summary.json --csv summary.csv
"""

from __future__ import annotations

import argparse
import csv
import json
import os
from pathlib import Path
from typing import Dict, Any, List

from core_calculator_final import PressureAnalysisFinal
from full_medical_report_generator import FullMedicalReportGenerator
from generate_combined_report import analyze_directory_and_merge


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


def analyze_directory(dir_path: str) -> List[Dict[str, Any]]:
    dir_p = Path(dir_path)
    csv_files = sorted([str(p) for p in dir_p.glob('*.csv')])
    if not csv_files:
        raise FileNotFoundError(f'目录中未找到CSV文件: {dir_path}')

    analyzer = PressureAnalysisFinal()
    rows: List[Dict[str, Any]] = []

    for csv_file in csv_files:
        result = analyzer.comprehensive_analysis_final(csv_file)
        if 'error' in result:
            print(f"⚠️ 跳过: {csv_file} - {result['error']}")
            continue
        gp = result.get('gait_parameters', {})
        lf = gp.get('left_foot', {})
        rf = gp.get('right_foot', {})
        info = result.get('file_info', {})
        rows.append({
            'file': Path(csv_file).name,
            'type': _classify_test_type(csv_file),
            'frames': info.get('total_frames'),
            'duration_s': info.get('duration'),
            'steps_total': gp.get('step_count'),
            'velocity_mps': gp.get('average_velocity'),
            'avg_step_len_cm': gp.get('average_step_length'),
            'cadence_spm': gp.get('cadence'),
            'left_step_len_m': lf.get('average_step_length_m', 0.0),
            'right_step_len_m': rf.get('average_step_length_m', 0.0),
            'left_cadence': lf.get('cadence', 0.0),
            'right_cadence': rf.get('cadence', 0.0),
            'stance_phase': gp.get('stance_phase', 0.0),
            'left_stance': gp.get('left_stance_phase', 0.0),
            'right_stance': gp.get('right_stance_phase', 0.0),
            'double_support': gp.get('double_support', 0.0),
            'turn_time': gp.get('turn_time', 0.0),
        })

    return rows


def save_json(rows: List[Dict[str, Any]], out_path: str) -> None:
    with open(out_path, 'w', encoding='utf-8') as f:
        json.dump(rows, f, ensure_ascii=False, indent=2)
    print(f'✅ 已保存JSON汇总: {out_path}')


def save_csv(rows: List[Dict[str, Any]], out_path: str) -> None:
    if not rows:
        print('⚠️ 无数据可保存CSV')
        return
    fields = list(rows[0].keys())
    with open(out_path, 'w', encoding='utf-8', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)
    print(f'✅ 已保存CSV汇总: {out_path}')


def generate_combined_html(dir_path: str, patient_info: Dict[str, Any], out_html: str) -> None:
    combined = analyze_directory_and_merge(dir_path)
    generator = FullMedicalReportGenerator()
    html = generator.generate_report_from_algorithm(combined, patient_info)
    with open(out_html, 'w', encoding='utf-8') as f:
        f.write(html)
    print(f'✅ 综合报告已生成: {out_html}')
    if os.name == 'posix':
        os.system(f'open {out_html}')


def main():
    parser = argparse.ArgumentParser(description='多文件测试运行器：目录内CSV逐个计算并汇总，生成综合报告')
    parser.add_argument('--dir', required=True, help='CSV目录')
    parser.add_argument('--name', default='合并患者')
    parser.add_argument('--gender', default='男')
    parser.add_argument('--age', type=int, default=60)
    parser.add_argument('--height', type=int, default=170)
    parser.add_argument('--weight', type=int, default=65)
    parser.add_argument('--html', default='combined_report.html')
    parser.add_argument('--json', default='multi_test_summary.json')
    parser.add_argument('--csv', default='multi_test_summary.csv')
    args = parser.parse_args()

    rows = analyze_directory(args.dir)

    # 控制台摘要
    print('\n=== 多文件指标摘要 ===')
    for r in rows:
        print(f"- {r['file']} [{r['type']}]  步数:{r['steps_total']}  速:{r['velocity_mps']:.2f}m/s  平均步长:{r['avg_step_len_cm']:.1f}cm  L/R步长:{r['left_step_len_m']:.2f}/{r['right_step_len_m']:.2f}m  L/R步频:{r['left_cadence']:.1f}/{r['right_cadence']:.1f}")

    save_json(rows, args.json)
    save_csv(rows, args.csv)

    patient_info = {
        'name': args.name,
        'gender': args.gender,
        'age': args.age,
        'id': 'PT-COMBINED',
        'height': args.height,
        'weight': args.weight,
        'department': '康复医学科'
    }
    generate_combined_html(args.dir, patient_info, args.html)


if __name__ == '__main__':
    main()


