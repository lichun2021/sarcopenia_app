#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
足部压力分析核心算法库
独立计算模块，无外部依赖
"""

import numpy as np
import pandas as pd
from typing import Dict, List, Tuple, Optional
import json
import csv
from pathlib import Path

class PressureAnalysisCore:
    """压力分析核心计算引擎"""
    
    def __init__(self):
        # 物理参数配置
        self.PRESSURE_MAT_WIDTH = 1.65  # 压力垫宽度（米）
        self.PRESSURE_MAT_HEIGHT = 0.95  # 压力垫高度（米）
        self.SENSOR_GRID_SIZE = 32      # 传感器阵列尺寸
        self.GRID_SCALE_X = self.PRESSURE_MAT_WIDTH / self.SENSOR_GRID_SIZE
        self.GRID_SCALE_Y = self.PRESSURE_MAT_HEIGHT / self.SENSOR_GRID_SIZE
        self.PRESSURE_THRESHOLD = 20    # 压力阈值
    
    def parse_csv_data(self, csv_content: str) -> List[List[float]]:
        """解析CSV数据为压力矩阵"""
        lines = csv_content.strip().split('\n')
        data_matrix = []
        
        for line in lines[1:]:  # 跳过表头
            if line.strip():
                values = line.split(',')
                if len(values) >= 32:  # 确保有足够的数据列
                    row_data = [float(val) if val.strip() else 0.0 
                               for val in values[:32]]
                    data_matrix.append(row_data)
        
        return data_matrix
    
    def calculate_cop_position(self, pressure_matrix: List[List[float]]) -> Optional[Dict]:
        """计算压力中心位置"""
        if not pressure_matrix:
            return None
            
        total_pressure = 0
        weighted_x = 0
        weighted_y = 0
        active_cells = 0
        
        for row in range(len(pressure_matrix)):
            for col in range(len(pressure_matrix[row])):
                pressure = pressure_matrix[row][col]
                if pressure > self.PRESSURE_THRESHOLD:
                    # 转换为物理坐标
                    x = col * self.GRID_SCALE_X + self.GRID_SCALE_X / 2
                    y = row * self.GRID_SCALE_Y + self.GRID_SCALE_Y / 2
                    
                    total_pressure += pressure
                    weighted_x += x * pressure
                    weighted_y += y * pressure
                    active_cells += 1
        
        if total_pressure > 0.5 and active_cells >= 3:
            return {
                'x': weighted_x / total_pressure,
                'y': weighted_y / total_pressure,
                'total_pressure': total_pressure,
                'active_cells': active_cells
            }
        
        return None
    
    def detect_gait_events(self, pressure_data: List[List[List[float]]]) -> List[Dict]:
        """检测步态事件"""
        events = []
        
        for i, frame in enumerate(pressure_data):
            cop = self.calculate_cop_position(frame)
            if cop:
                events.append({
                    'timestamp': i,
                    'cop_x': cop['x'],
                    'cop_y': cop['y'],
                    'pressure': cop['total_pressure']
                })
        
        return events
    
    def calculate_step_metrics(self, gait_events: List[Dict]) -> Dict:
        """计算步态指标"""
        if len(gait_events) < 2:
            return {'error': 'Insufficient data for step calculation'}
        
        # 检测步态周期
        steps = []
        for i in range(1, len(gait_events)):
            prev_event = gait_events[i-1]
            curr_event = gait_events[i]
            
            # 计算步长（前进方向的位移）
            dx = abs(curr_event['cop_x'] - prev_event['cop_x'])
            dy = abs(curr_event['cop_y'] - prev_event['cop_y'])
            
            # 选择变化更大的轴作为前进方向
            step_length = max(dx, dy)
            time_interval = curr_event['timestamp'] - prev_event['timestamp']
            
            if step_length > 0.05:  # 最小步长阈值5cm
                steps.append({
                    'length': step_length,
                    'time': time_interval,
                    'velocity': step_length / (time_interval + 0.001)
                })
        
        if not steps:
            return {'error': 'No valid steps detected'}
        
        # 计算统计指标
        step_lengths = [step['length'] for step in steps]
        step_times = [step['time'] for step in steps]
        velocities = [step['velocity'] for step in steps]
        
        return {
            'step_count': len(steps),
            'average_step_length': np.mean(step_lengths),
            'step_length_variability': np.std(step_lengths),
            'average_step_time': np.mean(step_times),
            'average_velocity': np.mean(velocities),
            'cadence': 60 / np.mean(step_times) if step_times else 0,
            'step_lengths': step_lengths,
            'individual_steps': steps
        }
    
    def analyze_balance(self, pressure_data: List[List[List[float]]]) -> Dict:
        """平衡分析"""
        cop_trajectory = []
        
        for frame in pressure_data:
            cop = self.calculate_cop_position(frame)
            if cop:
                cop_trajectory.append((cop['x'], cop['y']))
        
        if len(cop_trajectory) < 10:
            return {'error': 'Insufficient data for balance analysis'}
        
        # 计算摆动指标
        x_positions = [pos[0] for pos in cop_trajectory]
        y_positions = [pos[1] for pos in cop_trajectory]
        
        # 摆动面积（外包矩形）
        sway_area = (max(x_positions) - min(x_positions)) * \
                   (max(y_positions) - min(y_positions))
        
        # 平均摆动速度
        total_distance = 0
        for i in range(1, len(cop_trajectory)):
            dx = cop_trajectory[i][0] - cop_trajectory[i-1][0]
            dy = cop_trajectory[i][1] - cop_trajectory[i-1][1]
            total_distance += np.sqrt(dx**2 + dy**2)
        
        avg_velocity = total_distance / len(cop_trajectory)
        
        # 最大位移
        center_x = np.mean(x_positions)
        center_y = np.mean(y_positions)
        
        max_displacement = max([
            np.sqrt((x - center_x)**2 + (y - center_y)**2)
            for x, y in cop_trajectory
        ])
        
        return {
            'sway_area': sway_area,
            'average_velocity': avg_velocity,
            'max_displacement': max_displacement,
            'trajectory_length': total_distance,
            'stability_score': 100 / (1 + sway_area * 10)  # 稳定性评分
        }
    
    def comprehensive_analysis(self, csv_file_path: str) -> Dict:
        """综合分析入口函数"""
        try:
            # 读取CSV文件
            with open(csv_file_path, 'r', encoding='utf-8') as f:
                csv_content = f.read()
            
            # 解析数据
            pressure_matrix = self.parse_csv_data(csv_content)
            if not pressure_matrix:
                return {'error': 'Failed to parse CSV data'}
            
            # 将2D数据转换为时间序列（简化处理）
            pressure_sequence = [pressure_matrix]  # 实际应该是时间序列
            
            # 步态分析
            gait_events = self.detect_gait_events(pressure_sequence)
            step_metrics = self.calculate_step_metrics(gait_events)
            
            # 平衡分析
            balance_metrics = self.analyze_balance(pressure_sequence)
            
            # 综合评估
            result = {
                'file_info': {
                    'path': csv_file_path,
                    'data_points': len(pressure_matrix)
                },
                'gait_analysis': step_metrics,
                'balance_analysis': balance_metrics,
                'analysis_timestamp': pd.Timestamp.now().isoformat()
            }
            
            return result
            
        except Exception as e:
            return {'error': f'Analysis failed: {str(e)}'}

def main():
    """命令行接口"""
    import sys
    
    if len(sys.argv) != 2:
        print("Usage: python core_calculator.py <csv_file_path>")
        sys.exit(1)
    
    csv_file = sys.argv[1]
    if not Path(csv_file).exists():
        print(f"Error: File {csv_file} not found")
        sys.exit(1)
    
    # 执行分析
    analyzer = PressureAnalysisCore()
    result = analyzer.comprehensive_analysis(csv_file)
    
    # 输出结果
    print(json.dumps(result, indent=2, default=str))

if __name__ == "__main__":
    main()