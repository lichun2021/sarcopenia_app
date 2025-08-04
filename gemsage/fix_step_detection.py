#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
修复步态检测算法 - 基于压力峰值检测真正的步态周期
"""

import numpy as np
from typing import List, Dict

def detect_real_steps(gait_events: List[Dict]) -> List[Dict]:
    """
    基于压力模式检测真正的步态周期
    
    步态周期识别原理：
    1. 压力峰值通常对应脚跟着地或全脚掌着地
    2. 压力谷值通常对应摆动相（脚离地）
    3. 一个完整的步态周期包含：着地->站立->离地->摆动->再次着地
    """
    if len(gait_events) < 10:
        return []
    
    # 提取压力序列
    pressures = [event['pressure'] for event in gait_events]
    timestamps = [event['timestamp'] for event in gait_events]
    cop_x = [event['cop_x'] for event in gait_events]
    cop_y = [event['cop_y'] for event in gait_events]
    
    # 平滑压力数据（5点移动平均）
    smoothed_pressures = []
    window_size = 5
    for i in range(len(pressures)):
        start = max(0, i - window_size // 2)
        end = min(len(pressures), i + window_size // 2 + 1)
        smoothed_pressures.append(np.mean(pressures[start:end]))
    
    # 计算压力的一阶导数（变化率）
    pressure_diff = np.diff(smoothed_pressures)
    
    # 寻找压力峰值（局部最大值）
    peaks = []
    min_peak_distance = 10  # 最小峰值间隔（帧数）
    pressure_threshold = np.mean(pressures) * 0.5  # 峰值阈值为平均压力的50%
    
    for i in range(1, len(smoothed_pressures) - 1):
        # 检查是否为局部最大值
        if (smoothed_pressures[i] > smoothed_pressures[i-1] and 
            smoothed_pressures[i] > smoothed_pressures[i+1] and
            smoothed_pressures[i] > pressure_threshold):
            
            # 检查与上一个峰值的距离
            if not peaks or (i - peaks[-1]) >= min_peak_distance:
                peaks.append(i)
    
    # 基于峰值计算步态参数
    steps = []
    for i in range(1, len(peaks)):
        prev_peak = peaks[i-1]
        curr_peak = peaks[i]
        
        # 计算步长（使用峰值位置的COP）
        dx = cop_x[curr_peak] - cop_x[prev_peak]
        dy = cop_y[curr_peak] - cop_y[prev_peak]
        step_length = np.sqrt(dx**2 + dy**2)
        
        # 计算步态时间
        step_time = (timestamps[curr_peak] - timestamps[prev_peak]) * 0.033  # 假设30Hz采样率
        
        if step_length > 0.1 and step_time > 0.3:  # 最小步长10cm，最小时间0.3秒
            steps.append({
                'start_frame': prev_peak,
                'end_frame': curr_peak,
                'length': step_length,
                'time': step_time,
                'velocity': step_length / step_time,
                'start_pressure': pressures[prev_peak],
                'end_pressure': pressures[curr_peak]
            })
    
    return steps

def calculate_improved_step_metrics(gait_events: List[Dict]) -> Dict:
    """改进的步态指标计算"""
    if len(gait_events) < 10:
        return {'error': 'Insufficient data for gait analysis (need at least 10 frames)'}
    
    # 检测真正的步态周期
    real_steps = detect_real_steps(gait_events)
    
    if not real_steps:
        return {'error': 'No valid gait cycles detected'}
    
    # 计算统计指标
    step_lengths = [step['length'] for step in real_steps]
    step_times = [step['time'] for step in real_steps]
    velocities = [step['velocity'] for step in real_steps]
    
    # 根据文件名判断测试类型，调整步长
    # 对于步道测试，需要考虑实际的物理布局
    # 步道4圈 = 80米，步道7圈 = 140米
    
    return {
        'step_count': len(real_steps),
        'average_step_length': np.mean(step_lengths),
        'step_length_variability': np.std(step_lengths),
        'average_step_time': np.mean(step_times),
        'average_velocity': np.mean(velocities),
        'cadence': 60 / np.mean(step_times) if step_times else 0,
        'min_step_length': min(step_lengths),
        'max_step_length': max(step_lengths),
        'detected_peaks': len(real_steps) + 1,  # 峰值数
        'analysis_method': 'pressure_peak_detection',
        'individual_steps': real_steps
    }

# 测试改进的算法
if __name__ == "__main__":
    import sys
    import os
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from core_calculator import PressureAnalysisCore
    
    # 测试文件
    csv_file = "/Users/xidada/foot-pressure-analysis/肌少症数据/刘云帆-步道4圈-29岁.csv"
    
    # 使用原始算法获取事件
    analyzer = PressureAnalysisCore()
    with open(csv_file, 'r', encoding='utf-8') as f:
        csv_content = f.read()
    
    pressure_matrix = analyzer.parse_csv_data(csv_content)
    gait_events = analyzer.detect_gait_events(pressure_matrix)
    
    print(f"检测到 {len(gait_events)} 个事件")
    
    # 使用改进的算法
    improved_metrics = calculate_improved_step_metrics(gait_events)
    
    print("\n改进的步态分析结果:")
    import json
    print(json.dumps(improved_metrics, indent=2, ensure_ascii=False))