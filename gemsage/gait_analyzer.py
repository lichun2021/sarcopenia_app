#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
GemSage步态分析系统
专业的步态分析和跌倒风险评估算法

作者: Claude
版本: 1.0.0
"""

import pandas as pd
import numpy as np
import json
import matplotlib.pyplot as plt
import matplotlib.patches as patches
import seaborn as sns
from jinja2 import Template
import cv2
from scipy import ndimage, signal
from scipy.signal import find_peaks
import os
from datetime import datetime
import re
import warnings
warnings.filterwarnings('ignore')

# 设置中文字体支持
plt.rcParams['font.sans-serif'] = ['SimHei', 'Arial Unicode MS', 'DejaVu Sans']
plt.rcParams['axes.unicode_minus'] = False

class PressureDataProcessor:
    """压力数据处理类"""
    
    def __init__(self, grid_size=32, physical_size=40.0):
        """
        初始化压力数据处理器
        
        Args:
            grid_size (int): 网格大小 (32x32)
            physical_size (float): 物理尺寸 (cm)
        """
        self.grid_size = grid_size
        self.physical_size = physical_size  # cm
        self.cell_size = physical_size / grid_size  # cm per cell
        
    def parse_pressure_array(self, data_string):
        """
        解析压力数据字符串为32x32矩阵
        
        Args:
            data_string (str): 压力数据字符串 "[1,2,3,...]"
            
        Returns:
            np.array: 32x32压力矩阵
        """
        try:
            # 移除方括号并分割
            data_string = data_string.strip('[]')
            values = [float(x.strip()) for x in data_string.split(',')]
            
            # 确保数据长度正确
            if len(values) != self.grid_size * self.grid_size:
                raise ValueError(f"数据长度不匹配: 期望{self.grid_size * self.grid_size}, 实际{len(values)}")
            
            # 重塑为32x32矩阵
            matrix = np.array(values).reshape(self.grid_size, self.grid_size)
            return matrix
        
        except Exception as e:
            print(f"解析压力数据失败: {e}")
            return np.zeros((self.grid_size, self.grid_size))
    
    def calculate_center_of_pressure(self, pressure_matrix):
        """
        计算压力中心 (Center of Pressure, CoP)
        
        Args:
            pressure_matrix (np.array): 压力矩阵
            
        Returns:
            tuple: (cop_x, cop_y) 压力中心坐标 (cm)
        """
        if np.sum(pressure_matrix) == 0:
            return 0.0, 0.0
        
        # 创建坐标网格
        y_indices, x_indices = np.mgrid[0:self.grid_size, 0:self.grid_size]
        
        # 计算加权平均位置
        total_force = np.sum(pressure_matrix)
        cop_x = np.sum(pressure_matrix * x_indices) / total_force * self.cell_size
        cop_y = np.sum(pressure_matrix * y_indices) / total_force * self.cell_size
        
        return round(cop_x, 4), round(cop_y, 4)
    
    def calculate_pressure_stats(self, pressure_matrix):
        """
        计算压力统计信息
        
        Args:
            pressure_matrix (np.array): 压力矩阵
            
        Returns:
            dict: 压力统计信息
        """
        total_pressure = np.sum(pressure_matrix)
        max_pressure = np.max(pressure_matrix)
        active_area = np.sum(pressure_matrix > 0) * (self.cell_size ** 2)  # cm²
        
        return {
            'total_pressure': round(total_pressure, 4),
            'max_pressure': round(max_pressure, 4),
            'active_area': round(active_area, 4),
            'pressure_variance': round(np.var(pressure_matrix), 4)
        }


class GaitDataLoader:
    """步态数据加载器"""
    
    def __init__(self, data_folder):
        """
        初始化数据加载器
        
        Args:
            data_folder (str): 数据文件夹路径
        """
        self.data_folder = data_folder
        self.test_files = {}
        self.scan_data_files()
    
    def scan_data_files(self):
        """扫描数据文件"""
        if not os.path.exists(self.data_folder):
            raise FileNotFoundError(f"数据文件夹不存在: {self.data_folder}")
        
        # 定义测试步骤映射
        test_mapping = {
            '第1步-静坐检测': 'sitting',
            '第2步-起坐测试': 'sit_to_stand', 
            '第3步-静态站立': 'standing',
            '第4步-前后脚站立': 'tandem_standing',
            '第5步-双脚前后站立': 'side_standing',
            '第6步-4.5米步道折返': 'walking'
        }
        
        # 扫描文件
        for filename in os.listdir(self.data_folder):
            if filename.endswith('.csv'):
                for test_name, test_key in test_mapping.items():
                    if test_name in filename:
                        self.test_files[test_key] = os.path.join(self.data_folder, filename)
                        print(f"找到测试文件 {test_key}: {filename}")
                        break
    
    def load_test_data(self, test_type):
        """
        加载指定测试类型的数据
        
        Args:
            test_type (str): 测试类型
            
        Returns:
            pd.DataFrame: 测试数据
        """
        if test_type not in self.test_files:
            raise ValueError(f"未找到测试类型: {test_type}")
        
        try:
            df = pd.read_csv(self.test_files[test_type])
            print(f"加载{test_type}数据: {len(df)}条记录")
            return df
        except Exception as e:
            print(f"加载数据失败: {e}")
            return None


class SittingAnalyzer:
    """静坐分析器"""
    
    def __init__(self, processor):
        self.processor = processor
    
    def analyze(self, data):
        """
        分析静坐数据
        
        Args:
            data (pd.DataFrame): 静坐测试数据
            
        Returns:
            dict: 分析结果
        """
        results = {
            'front_pressure': 0.0,
            'back_pressure': 0.0,
            'left_pressure': 0.0,
            'right_pressure': 0.0,
            'micro_vibration': 0.0,
            'stability_score': 0.0
        }
        
        if data is None or len(data) == 0:
            return results
        
        cop_positions = []
        pressure_stats = []
        
        # 处理每一帧数据
        for _, row in data.iterrows():
            pressure_matrix = self.processor.parse_pressure_array(row['data'])
            cop_x, cop_y = self.processor.calculate_center_of_pressure(pressure_matrix)
            stats = self.processor.calculate_pressure_stats(pressure_matrix)
            
            cop_positions.append((cop_x, cop_y))
            pressure_stats.append(stats)
        
        if len(cop_positions) > 0:
            cops = np.array(cop_positions)
            
            # 计算四个方向的压力分布
            center_x, center_y = self.processor.physical_size / 2, self.processor.physical_size / 2
            
            # 前后左右压力计算 (基于压力中心分布)
            results['front_pressure'] = round(np.mean([p for x, y in cops if y < center_y for p in [np.mean([s['total_pressure'] for s in pressure_stats])]]) if any(y < center_y for x, y in cops) else 0, 4)
            results['back_pressure'] = round(np.mean([p for x, y in cops if y >= center_y for p in [np.mean([s['total_pressure'] for s in pressure_stats])]]) if any(y >= center_y for x, y in cops) else 0, 4)
            results['left_pressure'] = round(np.mean([p for x, y in cops if x < center_x for p in [np.mean([s['total_pressure'] for s in pressure_stats])]]) if any(x < center_x for x, y in cops) else 0, 4)
            results['right_pressure'] = round(np.mean([p for x, y in cops if x >= center_x for p in [np.mean([s['total_pressure'] for s in pressure_stats])]]) if any(x >= center_x for x, y in cops) else 0, 4)
            
            # 微抖动范围计算
            cop_std = np.std(cops, axis=0)
            results['micro_vibration'] = round(np.linalg.norm(cop_std), 4)
            
            # 稳定性评分 (抖动越小，稳定性越高)
            results['stability_score'] = round(max(0, 100 - results['micro_vibration'] * 10), 4)
        
        return results


class SitToStandAnalyzer:
    """起坐分析器"""
    
    def __init__(self, processor):
        self.processor = processor
    
    def analyze(self, data):
        """
        分析起坐数据
        
        Args:
            data (pd.DataFrame): 起坐测试数据
            
        Returns:
            dict: 分析结果
        """
        results = {
            'five_situp_time': 0.0,
            'standup_speed_max': 0.0,
            'sitdown_speed_max': 0.0,
            'sitstand_stability': 0.0
        }
        
        if data is None or len(data) == 0:
            return results
        
        # 计算总时间 (从第一条记录到最后一条记录)
        if len(data) > 1:
            start_time = data.iloc[0]['time']
            end_time = data.iloc[-1]['time']
            results['five_situp_time'] = round(end_time - start_time, 4)
        
        # 分析压力变化模式识别起坐动作
        pressure_sequence = []
        time_sequence = []
        
        for _, row in data.iterrows():
            pressure_matrix = self.processor.parse_pressure_array(row['data'])
            total_pressure = np.sum(pressure_matrix)
            pressure_sequence.append(total_pressure)
            time_sequence.append(row['time'])
        
        if len(pressure_sequence) > 1:
            # 计算压力变化速度
            pressure_diff = np.diff(pressure_sequence)
            time_diff = np.diff(time_sequence)
            
            # 避免除以零
            time_diff = np.where(time_diff == 0, 1e-6, time_diff)
            velocity = pressure_diff / time_diff
            
            # 站起速度 (压力减少的最大速度)
            negative_velocities = velocity[velocity < 0]
            if len(negative_velocities) > 0:
                results['standup_speed_max'] = round(abs(np.min(negative_velocities)), 4)
            
            # 坐下速度 (压力增加的最大速度)  
            positive_velocities = velocity[velocity > 0]
            if len(positive_velocities) > 0:
                results['sitdown_speed_max'] = round(np.max(positive_velocities), 4)
            
            # 动作稳定性 (速度变化的平滑程度)
            velocity_std = np.std(velocity)
            results['sitstand_stability'] = round(max(0, 100 - velocity_std / 10), 4)
        
        return results


class StandingAnalyzer:
    """站立分析器"""
    
    def __init__(self, processor):
        self.processor = processor
        
    def analyze_standing_data(self, data, test_type="normal"):
        """
        分析站立数据的通用方法
        
        Args:
            data (pd.DataFrame): 站立测试数据
            test_type (str): 测试类型
            
        Returns:
            dict: 分析结果
        """
        results = {
            'left_foot_max': 0.0,
            'left_foot_offset': 0.0,
            'left_foot_support_ratio': 0.0,
            'right_foot_max': 0.0,
            'right_foot_offset': 0.0,
            'right_foot_support_ratio': 0.0
        }
        
        if data is None or len(data) == 0:
            return results
        
        left_foot_data = []
        right_foot_data = []
        
        # 处理每一帧数据
        for _, row in data.iterrows():
            pressure_matrix = self.processor.parse_pressure_array(row['data'])
            
            # 假设左脚在左半部分，右脚在右半部分
            mid_col = self.processor.grid_size // 2
            left_foot_matrix = pressure_matrix[:, :mid_col]
            right_foot_matrix = pressure_matrix[:, mid_col:]
            
            left_pressure = np.sum(left_foot_matrix)
            right_pressure = np.sum(right_foot_matrix)
            
            left_foot_data.append(left_pressure)
            right_foot_data.append(right_pressure)
        
        if len(left_foot_data) > 0:
            # 左脚分析
            results['left_foot_max'] = round(np.max(left_foot_data), 4)
            results['left_foot_offset'] = round(np.std(left_foot_data), 4)
            
            # 右脚分析
            results['right_foot_max'] = round(np.max(right_foot_data), 4)
            results['right_foot_offset'] = round(np.std(right_foot_data), 4)
            
            # 支撑相占比
            total_pressure = np.array(left_foot_data) + np.array(right_foot_data)
            if np.sum(total_pressure) > 0:
                results['left_foot_support_ratio'] = round(np.sum(left_foot_data) / np.sum(total_pressure) * 100, 4)
                results['right_foot_support_ratio'] = round(np.sum(right_foot_data) / np.sum(total_pressure) * 100, 4)
        
        return results


class WalkingAnalyzer:
    """行走分析器"""
    
    def __init__(self, processor):
        self.processor = processor
    
    def analyze(self, data):
        """
        分析行走数据
        
        Args:
            data (pd.DataFrame): 行走测试数据
            
        Returns:
            dict: 分析结果
        """
        results = {
            'step_length_same_left': 0.0,
            'step_length_same_right': 0.0,
            'step_time_left': 0.0,
            'step_time_right': 0.0,
            'step_length_opposite_left': 0.0,
            'step_length_opposite_right': 0.0,
            'stride_speed_left': 0.0,
            'stride_speed_right': 0.0,
            'stride_length_left': 0.0,
            'stride_length_right': 0.0,
            'step_frequency_left': 0.0,
            'step_frequency_right': 0.0,
            'swing_phase_left': 0.0,
            'swing_phase_right': 0.0,
            'swing_speed_left': 0.0,
            'swing_speed_right': 0.0,
            'double_support_left': 0.0,
            'double_support_right': 0.0,
            'double_support_time': 0.0,
            'step_width': 0.0
        }
        
        if data is None or len(data) == 0:
            return results
        
        # 分析步态数据
        cop_positions = []
        timestamps = []
        left_foot_pressures = []
        right_foot_pressures = []
        
        for _, row in data.iterrows():
            pressure_matrix = self.processor.parse_pressure_array(row['data'])
            cop_x, cop_y = self.processor.calculate_center_of_pressure(pressure_matrix)
            
            cop_positions.append((cop_x, cop_y))
            timestamps.append(row['time'])
            
            # 分离左右脚压力
            mid_col = self.processor.grid_size // 2
            left_pressure = np.sum(pressure_matrix[:, :mid_col])
            right_pressure = np.sum(pressure_matrix[:, mid_col:])
            
            left_foot_pressures.append(left_pressure)
            right_foot_pressures.append(right_pressure)
        
        if len(cop_positions) > 3:
            # 检测步伐
            steps = self._detect_steps(cop_positions, timestamps, left_foot_pressures, right_foot_pressures)
            
            if len(steps) > 1:
                # 计算步态参数
                results.update(self._calculate_gait_parameters(steps))
        
        return results
    
    def _detect_steps(self, cop_positions, timestamps, left_pressures, right_pressures):
        """
        检测步伐事件
        
        Args:
            cop_positions: 压力中心位置列表
            timestamps: 时间戳列表
            left_pressures: 左脚压力列表
            right_pressures: 右脚压力列表
            
        Returns:
            list: 步伐事件列表
        """
        steps = []
        
        # 使用压力变化检测脚掌着地事件
        left_peaks, _ = find_peaks(left_pressures, height=np.max(left_pressures) * 0.3, distance=10)
        right_peaks, _ = find_peaks(right_pressures, height=np.max(right_pressures) * 0.3, distance=10)
        
        # 合并并排序所有步伐事件
        all_peaks = [(i, 'left') for i in left_peaks] + [(i, 'right') for i in right_peaks]
        all_peaks.sort(key=lambda x: x[0])
        
        for i, (peak_idx, foot) in enumerate(all_peaks):
            step = {
                'index': peak_idx,
                'time': timestamps[peak_idx],
                'foot': foot,
                'cop_x': cop_positions[peak_idx][0],
                'cop_y': cop_positions[peak_idx][1],
                'pressure': left_pressures[peak_idx] if foot == 'left' else right_pressures[peak_idx]
            }
            steps.append(step)
        
        return steps
    
    def _calculate_gait_parameters(self, steps):
        """
        计算步态参数
        
        Args:
            steps: 步伐事件列表
            
        Returns:
            dict: 步态参数
        """
        params = {}
        
        left_steps = [s for s in steps if s['foot'] == 'left']
        right_steps = [s for s in steps if s['foot'] == 'right']
        
        # 计算步长 (同侧脚相邻两步之间的距离)
        if len(left_steps) >= 2:
            left_distances = []
            left_times = []
            for i in range(1, len(left_steps)):
                dx = left_steps[i]['cop_x'] - left_steps[i-1]['cop_x']
                dy = left_steps[i]['cop_y'] - left_steps[i-1]['cop_y']
                distance = np.sqrt(dx*dx + dy*dy) / 10  # 转换为米
                time_diff = left_steps[i]['time'] - left_steps[i-1]['time']
                
                left_distances.append(distance)
                left_times.append(time_diff)
            
            params['step_length_same_left'] = round(np.mean(left_distances), 4) if left_distances else 0.0
            params['step_time_left'] = round(np.mean(left_times), 4) if left_times else 0.0
            
            # 步频计算 (步/分钟)
            if params['step_time_left'] > 0:
                params['step_frequency_left'] = round(60.0 / params['step_time_left'], 4)
            
            # 跨步速度
            if params['step_time_left'] > 0:
                params['stride_speed_left'] = round(params['step_length_same_left'] / params['step_time_left'], 4)
        
        if len(right_steps) >= 2:
            right_distances = []
            right_times = []
            for i in range(1, len(right_steps)):
                dx = right_steps[i]['cop_x'] - right_steps[i-1]['cop_x'] 
                dy = right_steps[i]['cop_y'] - right_steps[i-1]['cop_y']
                distance = np.sqrt(dx*dx + dy*dy) / 10  # 转换为米
                time_diff = right_steps[i]['time'] - right_steps[i-1]['time']
                
                right_distances.append(distance)
                right_times.append(time_diff)
            
            params['step_length_same_right'] = round(np.mean(right_distances), 4) if right_distances else 0.0
            params['step_time_right'] = round(np.mean(right_times), 4) if right_times else 0.0
            
            # 步频计算
            if params['step_time_right'] > 0:
                params['step_frequency_right'] = round(60.0 / params['step_time_right'], 4)
            
            # 跨步速度  
            if params['step_time_right'] > 0:
                params['stride_speed_right'] = round(params['step_length_same_right'] / params['step_time_right'], 4)
        
        # 计算对侧步长 (左右脚交替的距离)
        alternating_steps = []
        for i in range(len(steps) - 1):
            if steps[i]['foot'] != steps[i+1]['foot']:
                dx = steps[i+1]['cop_x'] - steps[i]['cop_x']
                dy = steps[i+1]['cop_y'] - steps[i]['cop_y'] 
                distance = np.sqrt(dx*dx + dy*dy) / 10
                alternating_steps.append({
                    'distance': distance,
                    'from_foot': steps[i]['foot'],
                    'to_foot': steps[i+1]['foot']
                })
        
        # 分离左到右和右到左的步长
        left_to_right = [s['distance'] for s in alternating_steps if s['from_foot'] == 'left']
        right_to_left = [s['distance'] for s in alternating_steps if s['from_foot'] == 'right']
        
        params['step_length_opposite_left'] = round(np.mean(right_to_left), 4) if right_to_left else 0.0
        params['step_length_opposite_right'] = round(np.mean(left_to_right), 4) if left_to_right else 0.0
        
        # 步幅 (步长的两倍)
        params['stride_length_left'] = round(params['step_length_same_left'] * 2, 4)
        params['stride_length_right'] = round(params['step_length_same_right'] * 2, 4)
        
        # 步宽计算 (相邻步伐的横向距离)
        if len(alternating_steps) > 0:
            widths = []
            for i in range(len(steps) - 1):
                if steps[i]['foot'] != steps[i+1]['foot']:
                    width = abs(steps[i]['cop_x'] - steps[i+1]['cop_x']) / 10  # 转换为米
                    widths.append(width)
            params['step_width'] = round(np.mean(widths), 4) if widths else 0.0
        
        # 其他参数的默认值
        params.setdefault('swing_phase_left', 40.0)
        params.setdefault('swing_phase_right', 40.0)  
        params.setdefault('swing_speed_left', params.get('stride_speed_left', 0.0))
        params.setdefault('swing_speed_right', params.get('stride_speed_right', 0.0))
        params.setdefault('double_support_left', 20.0)
        params.setdefault('double_support_right', 20.0)
        params.setdefault('double_support_time', 0.2)
        
        return params


class GaitAnalysisSystem:
    """步态分析系统主类"""
    
    def __init__(self, data_folder):
        """
        初始化步态分析系统
        
        Args:
            data_folder (str): 数据文件夹路径
        """
        self.data_folder = data_folder
        self.processor = PressureDataProcessor()
        self.loader = GaitDataLoader(data_folder)
        
        # 初始化各分析器
        self.sitting_analyzer = SittingAnalyzer(self.processor)
        self.sitstand_analyzer = SitToStandAnalyzer(self.processor)
        self.standing_analyzer = StandingAnalyzer(self.processor)
        self.walking_analyzer = WalkingAnalyzer(self.processor)
        
        self.results = {}
    
    def run_full_analysis(self):
        """运行完整分析"""
        print("开始步态分析...")
        
        # 分析各个测试步骤
        self._analyze_sitting()
        self._analyze_sit_to_stand()
        self._analyze_standing()
        self._analyze_tandem_standing()
        self._analyze_side_standing()
        self._analyze_walking()
        
        # 生成综合评估
        self._generate_summary()
        
        print("步态分析完成!")
        return self.results
    
    def _analyze_sitting(self):
        """分析静坐数据"""
        print("分析静坐检测...")
        data = self.loader.load_test_data('sitting')
        results = self.sitting_analyzer.analyze(data)
        self.results['sitting'] = results
        
    def _analyze_sit_to_stand(self):
        """分析起坐数据"""
        print("分析起坐测试...")
        data = self.loader.load_test_data('sit_to_stand')  
        results = self.sitstand_analyzer.analyze(data)
        self.results['sit_to_stand'] = results
        
    def _analyze_standing(self):
        """分析静态站立"""
        print("分析静态站立...")
        data = self.loader.load_test_data('standing')
        results = self.standing_analyzer.analyze_standing_data(data, "normal")
        self.results['standing'] = results
        
    def _analyze_tandem_standing(self):
        """分析前后脚站立"""  
        print("分析前后脚站立...")
        data = self.loader.load_test_data('tandem_standing')
        results = self.standing_analyzer.analyze_standing_data(data, "tandem")
        self.results['tandem_standing'] = results
        
    def _analyze_side_standing(self):
        """分析双脚前后站立"""
        print("分析双脚前后站立...")
        data = self.loader.load_test_data('side_standing')  
        results = self.standing_analyzer.analyze_standing_data(data, "side")
        self.results['side_standing'] = results
        
    def _analyze_walking(self):
        """分析行走数据"""
        print("分析4.5米步道折返...")
        data = self.loader.load_test_data('walking')
        results = self.walking_analyzer.analyze(data)
        self.results['walking'] = results
    
    def _generate_summary(self):
        """生成分析总结"""
        summary = {
            'test_date': datetime.now().strftime('%Y-%m-%d'),
            'test_time': datetime.now().strftime('%H:%M:%S'),
            'total_tests': len(self.results),
            'analysis_complete': True
        }
        self.results['summary'] = summary


def main():
    """主函数"""
    # 测试系统
    data_folder = "/Users/xidada/GemSage/for test/1"
    
    try:
        # 创建分析系统
        gait_system = GaitAnalysisSystem(data_folder)
        
        # 运行分析
        results = gait_system.run_full_analysis()
        
        # 打印结果
        print("\n=== 分析结果 ===")
        for test_type, data in results.items():
            print(f"\n{test_type}:")
            if isinstance(data, dict):
                for key, value in data.items():
                    print(f"  {key}: {value}")
        
    except Exception as e:
        print(f"分析失败: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()