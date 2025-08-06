#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
足部压力分析核心算法库
独立计算模块，集成渐进式硬件自适应功能
与平台算法完全同步 - 2025-08-04
"""

import numpy as np
import pandas as pd
from typing import Dict, List, Tuple, Optional
import json
import csv
from pathlib import Path

# 导入硬件自适应服务
try:
    from .hardware_adaptive_service import (
        hardware_adaptive_service, 
        smart_hardware_match, 
        get_hardware_parameters,
        HardwareMatchResult
    )
    HARDWARE_ADAPTIVE_AVAILABLE = True
except ImportError:
    try:
        from hardware_adaptive_service import (
            hardware_adaptive_service, 
            smart_hardware_match, 
            get_hardware_parameters,
            HardwareMatchResult
        )
        HARDWARE_ADAPTIVE_AVAILABLE = True
    except ImportError:
        print("⚠️  硬件自适应服务不可用，将使用默认硬件参数")
        HARDWARE_ADAPTIVE_AVAILABLE = False

class PressureAnalysisCore:
    """压力分析核心计算引擎 - 集成渐进式硬件自适应"""
    
    def __init__(self, hardware_spec=None):
        """
        初始化压力分析核心
        
        Args:
            hardware_spec: 硬件规格字典，包含width, height, grid_width, grid_height等
                          如果为None则使用默认规格
        """
        # 硬件自适应属性
        self.current_hardware = None
        self.hardware_match_info = None
        self.adaptive_enabled = HARDWARE_ADAPTIVE_AVAILABLE
        
        # 硬件自适应支持
        if hardware_spec:
            self._setup_hardware_params(hardware_spec)
        else:
            # 默认硬件规格 - 基于最终设备规格（2025-08-02更新）
            self._setup_default_hardware()
    
    def _setup_default_hardware(self):
        """设置默认硬件参数"""
        # 步道压力垫（实际只有1个传感器垫子，另1个为延长垫）
        self.WALKWAY_TOTAL_LENGTH = 3.13  # 总长度：3.13m（2张垫子）
        self.WALKWAY_SENSOR_WIDTH = 1.565  # 单个传感器垫宽度：1565mm
        self.WALKWAY_HEIGHT = 0.90  # 高度：900mm
        self.WALKWAY_SENSOR_AREA_WIDTH = 1.4565  # 有效传感区域宽度
        self.WALKWAY_SENSOR_AREA_HEIGHT = 0.870  # 有效传感区域高度
        
        # 臀部压力垫
        self.HIP_PAD_WIDTH = 0.55  # 外形宽度：550mm
        self.HIP_PAD_HEIGHT = 0.53  # 外形高度：530mm
        self.HIP_SENSOR_WIDTH = 0.40  # 传感区域：400mm
        self.HIP_SENSOR_HEIGHT = 0.40  # 传感区域：400mm
        
        # 默认使用步道传感器参数（向后兼容）
        self.PRESSURE_MAT_WIDTH = self.WALKWAY_SENSOR_WIDTH
        self.PRESSURE_MAT_HEIGHT = self.WALKWAY_HEIGHT
        self.SENSOR_GRID_SIZE = 32      # 传感器阵列尺寸：32×32
        self.GRID_SCALE_X = self.PRESSURE_MAT_WIDTH / self.SENSOR_GRID_SIZE
        self.GRID_SCALE_Y = self.PRESSURE_MAT_HEIGHT / self.SENSOR_GRID_SIZE
        self.PRESSURE_THRESHOLD = 20    # 压力阈值
        
        print("ℹ️  使用默认硬件规格: 1565×900mm 步道垫")
    
    def _setup_hardware_params(self, spec):
        """
        设置硬件参数
        
        Args:
            spec: 硬件规格字典，支持以下格式：
                  {'width': 2.0, 'height': 2.0, 'grid_width': 32, 'grid_height': 32}
                  或AdaptiveCOPAnalyzer的HardwareSpec对象
        """
        # 兼容不同的输入格式
        if hasattr(spec, 'width'):  # HardwareSpec对象
            width = spec.width
            height = spec.height
            grid_width = spec.grid_width
            grid_height = spec.grid_height
            threshold = getattr(spec, 'pressure_threshold', 20)
            name = getattr(spec, 'name', 'Custom Hardware')
        else:  # 字典格式
            width = spec.get('width', 1.565)
            height = spec.get('height', 0.90)
            grid_width = spec.get('grid_width', 32)
            grid_height = spec.get('grid_height', 32)
            threshold = spec.get('pressure_threshold', 20)
            name = spec.get('name', 'Custom Hardware')
        
        # 设置物理参数
        self.PRESSURE_MAT_WIDTH = width
        self.PRESSURE_MAT_HEIGHT = height
        self.SENSOR_GRID_SIZE = grid_width  # 主要维度
        self.GRID_WIDTH = grid_width
        self.GRID_HEIGHT = grid_height
        self.GRID_SCALE_X = width / grid_width
        self.GRID_SCALE_Y = height / grid_height
        self.PRESSURE_THRESHOLD = threshold
        
        # 记录硬件信息
        self.hardware_info = {
            'name': name,
            'width': width,
            'height': height,
            'grid_size': f"{grid_width}×{grid_height}",
            'resolution_x': self.GRID_SCALE_X * 100,  # cm/格
            'resolution_y': self.GRID_SCALE_Y * 100   # cm/格
        }
        
        print(f"✅ 硬件配置: {name}")
        print(f"   尺寸: {width}m × {height}m")
        print(f"   传感器网格: {grid_width}×{grid_height}")
        print(f"   分辨率: X={self.GRID_SCALE_X*100:.2f}cm/格, Y={self.GRID_SCALE_Y*100:.2f}cm/格")
    
    def initialize_hardware_adaptive(self, data: List, filename: str = "") -> bool:
        """
        渐进式硬件自适应初始化
        优先匹配固定硬件，格式不匹配时自动降级
        与平台算法(hardwareAdaptiveService.ts)完全同步
        
        Args:
            data: 压力数据
            filename: 文件名（用于硬件识别）
            
        Returns:
            bool: 初始化是否成功
        """
        if not self.adaptive_enabled:
            print("⚠️  硬件自适应服务不可用，使用默认配置")
            return False
        
        try:
            print("🔧 启动Python算法硬件自适应...")
            
            # 使用硬件自适应服务进行智能匹配
            match_info = smart_hardware_match(data, filename)
            self.hardware_match_info = match_info
            
            if match_info.hardware:
                # 获取物理参数用于算法计算
                params = get_hardware_parameters(match_info)
                
                # 更新硬件参数
                self._setup_hardware_params(params)
                self.current_hardware = match_info.hardware
                
                print(f"✅ Python算法硬件配置: {match_info.hardware.name}")
                print(f"   尺寸: {match_info.hardware.width}m × {match_info.hardware.height}m")
                print(f"   网格: {match_info.hardware.grid_width}×{match_info.hardware.grid_height}")
                print(f"   匹配结果: {match_info.result.value} (置信度: {match_info.confidence}%)")
                
                return True
            else:
                print("❌ Python硬件配置失败，但系统将继续运行")
                return False
                
        except Exception as e:
            print(f"⚠️ Python硬件自适应初始化失败，使用默认配置: {e}")
            
            # 错误恢复：使用回退规格
            if self.adaptive_enabled:
                try:
                    fallback_spec = hardware_adaptive_service.get_fallback_spec()
                    fallback_params = hardware_adaptive_service.get_physical_parameters(fallback_spec)
                    self._setup_hardware_params(fallback_params)
                    print("✅ 已启用错误恢复模式")
                except:
                    pass
            
            return False
    
    def get_physical_params(self) -> Dict:
        """
        获取当前硬件的物理计算参数
        与平台算法同步
        """
        return {
            'width': self.PRESSURE_MAT_WIDTH,
            'height': self.PRESSURE_MAT_HEIGHT,
            'grid_width': getattr(self, 'GRID_WIDTH', self.SENSOR_GRID_SIZE),
            'grid_height': getattr(self, 'GRID_HEIGHT', self.SENSOR_GRID_SIZE),
            'grid_scale_x': self.GRID_SCALE_X,
            'grid_scale_y': self.GRID_SCALE_Y,
            'threshold': self.PRESSURE_THRESHOLD,
            'name': getattr(self, 'hardware_info', {}).get('name', '默认配置')
        }
    
    def parse_csv_data(self, csv_content: str) -> List[List[float]]:
        """解析CSV数据为压力矩阵 - 支持多种格式"""
        lines = csv_content.strip().split('\n')
        if not lines:
            return []
            
        # 使用pandas CSV读取器正确处理引号包围的字段
        from io import StringIO
        import pandas as pd
        
        try:
            df = pd.read_csv(StringIO(csv_content))
            header_columns = [col.lower() for col in df.columns]
            
            # 检测CSV格式
            has_data_column = any('data' in col for col in header_columns)
            has_press_column = any('press' in col for col in header_columns)
            
            print(f"🔍 检测到CSV格式: 列数={len(header_columns)}, 包含data列={has_data_column}, 包含press列={has_press_column}")
            print(f"📋 列名: {list(df.columns)}")
            
            data_matrix = []
            
            for idx, row in df.iterrows():
                try:
                    if has_data_column:
                        # 肌少症标准格式: 获取data列
                        data_col_name = next(col for col in df.columns if 'data' in col.lower())
                        data_str = str(row[data_col_name]).strip()
                        
                        print(f"🔍 第{idx+1}行data字段: {data_str[:50]}..." if len(data_str) > 50 else f"🔍 第{idx+1}行data字段: {data_str}")
                        
                        # 解析JSON数组格式的传感器数据
                        if data_str.startswith('[') and data_str.endswith(']'):
                            # 移除方括号并分割
                            data_str = data_str[1:-1]
                            sensor_values = [float(val.strip()) for val in data_str.split(',')]
                            
                            print(f"📊 第{idx+1}行解析出{len(sensor_values)}个传感器值")
                            
                            # 转换为矩阵格式
                            if len(sensor_values) == 2048:  # 64x32 = 2048 (双垫子)
                                matrix_2d = []
                                for i in range(32):
                                    row_data = sensor_values[i*64:(i+1)*64]
                                    matrix_2d.append(row_data)
                                data_matrix.append(matrix_2d)
                            elif len(sensor_values) == 1024:  # 32x32 = 1024 (单垫子)
                                matrix_2d = []
                                for i in range(32):
                                    row_data = sensor_values[i*32:(i+1)*32]
                                    matrix_2d.append(row_data)
                                data_matrix.append(matrix_2d)
                                print(f"✅ 第{idx+1}行成功转换为32x32矩阵")
                            else:
                                print(f"⚠️  第{idx+1}行传感器数据点数不正确: {len(sensor_values)} (期望1024或2048)")
                                
                        else:
                            print(f"⚠️  第{idx+1}行data字段格式不识别: {data_str}")
                            
                    elif has_press_column:
                        # 简单时间-压力格式
                        press_col_name = next(col for col in df.columns if 'press' in col.lower())
                        pressure_value = float(row[press_col_name]) if pd.notna(row[press_col_name]) else 0.0
                        
                        # 创建简化的1x1"矩阵"用于时间序列分析
                        data_matrix.append([pressure_value])
                        
                except (ValueError, IndexError, KeyError) as e:
                    print(f"⚠️  第{idx+1}行解析失败: {e}")
                    continue
            
            print(f"✅ CSV解析完成: 解析出{len(data_matrix)}行数据")
            return data_matrix
            
        except Exception as e:
            print(f"❌ CSV解析失败: {e}")
            return []
    
    def calculate_cop_position(self, pressure_matrix: List[List[float]]) -> Optional[Dict]:
        """计算压力中心位置 - 使用硬件自适应参数"""
        if pressure_matrix is None or (isinstance(pressure_matrix, list) and len(pressure_matrix) == 0):
            return None
        
        # 获取当前硬件参数
        params = self.get_physical_params()
        grid_scale_x = params['grid_scale_x']
        grid_scale_y = params['grid_scale_y']
        threshold = params['threshold']
            
        total_pressure = 0
        weighted_x = 0
        weighted_y = 0
        active_cells = 0
        
        for row in range(len(pressure_matrix)):
            for col in range(len(pressure_matrix[row])):
                pressure = pressure_matrix[row][col]
                if pressure > threshold:
                    # 转换为物理坐标（使用动态参数）
                    x = col * grid_scale_x + grid_scale_x / 2
                    y = row * grid_scale_y + grid_scale_y / 2
                    
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
    
    def separate_foot_data(self, data_frames):
        """分离左右脚数据（与平台算法同步）
        
        Args:
            data_frames: 压力数据帧列表（包含data字段的字典列表）
            
        Returns:
            tuple: (left_foot_data, right_foot_data)
        """
        left_foot_data = []
        right_foot_data = []
        
        for frame in data_frames:
            data = frame.get('data', [])
            
            # 根据数据长度确定矩阵形状
            if len(data) == 1024:
                # 32x32矩阵，分为左右两半（各16列）
                matrix = np.array(data).reshape(32, 32)
                left_matrix = matrix[:, :16]  # 左半部分（列0-15）
                right_matrix = matrix[:, 16:]  # 右半部分（列16-31）
                
                left_foot_data.append({
                    'time': frame.get('time', 0),
                    'timestamp': frame.get('timestamp', ''),
                    'data': left_matrix.flatten().tolist(),
                    'max': int(np.max(left_matrix)),
                    'press': int(np.sum(left_matrix)),
                    'area': int(np.sum(left_matrix > 20))  # 活跃单元数
                })
                
                right_foot_data.append({
                    'time': frame.get('time', 0),
                    'timestamp': frame.get('timestamp', ''),
                    'data': right_matrix.flatten().tolist(),
                    'max': int(np.max(right_matrix)),
                    'press': int(np.sum(right_matrix)),
                    'area': int(np.sum(right_matrix > 20))
                })
                
            elif len(data) == 2048:
                # 32x64矩阵，分为左右两半（各32列）
                matrix = np.array(data).reshape(32, 64)
                left_matrix = matrix[:, :32]  # 左半部分（列0-31）
                right_matrix = matrix[:, 32:]  # 右半部分（列32-63）
                
                left_foot_data.append({
                    'time': frame.get('time', 0),
                    'timestamp': frame.get('timestamp', ''),
                    'data': left_matrix.flatten().tolist(),
                    'max': int(np.max(left_matrix)),
                    'press': int(np.sum(left_matrix)),
                    'area': int(np.sum(left_matrix > 20))
                })
                
                right_foot_data.append({
                    'time': frame.get('time', 0),
                    'timestamp': frame.get('timestamp', ''),
                    'data': right_matrix.flatten().tolist(),
                    'max': int(np.max(right_matrix)),
                    'press': int(np.sum(right_matrix)),
                    'area': int(np.sum(right_matrix > 20))
                })
        
        return left_foot_data, right_foot_data
    
    def detect_gait_events(self, pressure_data: List[List[List[float]]]) -> List[Dict]:
        """检测步态事件 - 使用硬件自适应参数"""
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
    
    def detect_physical_gait_events(self, data_frames):
        """检测物理步态事件（与平台算法同步）
        基于COP轨迹和压力峰值检测左右脚步态事件
        
        Args:
            data_frames: 包含time, data等字段的数据帧列表
            
        Returns:
            dict: 包含左右脚步态事件和参数
        """
        # 分离左右脚数据
        left_foot_data, right_foot_data = self.separate_foot_data(data_frames)
        
        # 计算COP轨迹
        cop_trajectory = []
        for frame in data_frames:
            data = frame.get('data', [])
            if len(data) == 1024:
                matrix = np.array(data).reshape(32, 32)
            elif len(data) == 2048:
                matrix = np.array(data).reshape(32, 64)
            else:
                continue
                
            cop = self.calculate_cop_position(matrix.tolist())
            if cop:
                cop_trajectory.append({
                    'time': frame.get('time', 0),
                    'x': cop['x'],
                    'y': cop['y'],
                    'pressure': cop['total_pressure']
                })
        
        if len(cop_trajectory) < 2:
            return {'error': 'Insufficient COP data'}
        
        # 确定前进方向（X或Y轴摆动范围更大的为前进方向）
        x_values = [c['x'] for c in cop_trajectory]
        y_values = [c['y'] for c in cop_trajectory]
        x_range = max(x_values) - min(x_values)
        y_range = max(y_values) - min(y_values)
        
        forward_axis = 'x' if x_range > y_range else 'y'
        sideward_axis = 'y' if forward_axis == 'x' else 'x'
        
        # 检测压力峰值作为步态事件
        peaks = []
        pressures = [c['pressure'] for c in cop_trajectory]
        min_peak_distance = 10  # 最小峰值间隔
        pressure_threshold = np.mean(pressures) * 0.8
        
        for i in range(1, len(pressures) - 1):
            if (pressures[i] > pressures[i-1] and 
                pressures[i] > pressures[i+1] and
                pressures[i] > pressure_threshold):
                if not peaks or (i - peaks[-1]['index']) >= min_peak_distance:
                    peaks.append({
                        'index': i,
                        'time': cop_trajectory[i]['time'],
                        'forward_pos': cop_trajectory[i][forward_axis],
                        'sideward_pos': cop_trajectory[i][sideward_axis],
                        'pressure': pressures[i]
                    })
        
        # 根据侧向位置区分左右脚（与平台算法相同）
        if not peaks:
            return {'error': 'No gait events detected'}
            
        sideward_positions = [p['sideward_pos'] for p in peaks]
        avg_sideward = np.mean(sideward_positions)
        
        left_steps = []
        right_steps = []
        
        for peak in peaks:
            if peak['sideward_pos'] < avg_sideward:
                left_steps.append(peak)
            else:
                right_steps.append(peak)
        
        # 计算左右脚步长
        left_step_lengths = []
        for i in range(1, len(left_steps)):
            step_length = abs(left_steps[i]['forward_pos'] - left_steps[i-1]['forward_pos'])
            left_step_lengths.append(step_length)
        
        right_step_lengths = []
        for i in range(1, len(right_steps)):
            step_length = abs(right_steps[i]['forward_pos'] - right_steps[i-1]['forward_pos'])
            right_step_lengths.append(step_length)
        
        # 计算平均值
        left_avg_step_length = np.mean(left_step_lengths) if left_step_lengths else 0
        right_avg_step_length = np.mean(right_step_lengths) if right_step_lengths else 0
        
        # 计算步频
        total_time = cop_trajectory[-1]['time'] - cop_trajectory[0]['time']
        left_cadence = (len(left_steps) / total_time) * 60 if total_time > 0 else 0
        right_cadence = (len(right_steps) / total_time) * 60 if total_time > 0 else 0
        
        return {
            'forward_axis': forward_axis,
            'left_steps': len(left_steps),
            'right_steps': len(right_steps),
            'left_step_length': left_avg_step_length,
            'right_step_length': right_avg_step_length,
            'left_cadence': left_cadence,
            'right_cadence': right_cadence,
            'total_steps': len(peaks),
            'cop_trajectory': cop_trajectory[:10]  # 返回前10个点作为示例
        }
    
    def calculate_step_metrics(self, gait_events: List[Dict]) -> Dict:
        """计算步态指标 - 使用改进的压力峰值检测算法"""
        if len(gait_events) < 10:
            return {'error': 'Insufficient data for step calculation (need at least 10 frames)'}
        
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
        
        if not steps:
            return {
                'error': 'No valid gait cycles detected',
                'debug_info': {
                    'total_events': len(gait_events),
                    'peaks_found': len(peaks),
                    'pressure_range': f"{min(pressures):.1f}-{max(pressures):.1f}",
                    'threshold': pressure_threshold
                }
            }
        
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
            'min_step_length': min(step_lengths),
            'max_step_length': max(step_lengths),
            'detected_peaks': len(peaks),
            'analysis_method': 'pressure_peak_detection',
            'individual_steps': steps
        }
    
    def analyze_balance(self, pressure_data: List[List[List[float]]]) -> Dict:
        """平衡分析 - 与平台算法同步更新"""
        cop_trajectory = []
        
        for frame in pressure_data:
            cop = self.calculate_cop_position(frame)
            if cop:
                cop_trajectory.append({
                    'x': cop['x'], 
                    'y': cop['y'],
                    'pressure': cop['total_pressure']
                })
        
        if len(cop_trajectory) < 3:
            return {'error': 'Insufficient data for balance analysis'}
        
        # 基础指标计算
        x_positions = [pos['x'] for pos in cop_trajectory]
        y_positions = [pos['y'] for pos in cop_trajectory]
        
        # 计算质心
        center_x = np.mean(x_positions)
        center_y = np.mean(y_positions)
        
        # 1. 基础摆动面积（外包矩形）
        sway_area = (max(x_positions) - min(x_positions)) * \
                   (max(y_positions) - min(y_positions))
        
        # 2. 轨迹总长度
        total_distance = 0
        for i in range(1, len(cop_trajectory)):
            dx = cop_trajectory[i]['x'] - cop_trajectory[i-1]['x']
            dy = cop_trajectory[i]['y'] - cop_trajectory[i-1]['y']
            total_distance += np.sqrt(dx**2 + dy**2)
        
        # 3. 平均速度
        avg_velocity = total_distance / len(cop_trajectory) if len(cop_trajectory) > 0 else 0
        
        # 4. 最大位移
        max_displacement = max([
            np.sqrt((pos['x'] - center_x)**2 + (pos['y'] - center_y)**2)
            for pos in cop_trajectory
        ])
        
        # === 新增：与平台同步的COP轨迹指标 ===
        
        # 5. COP轨迹面积（95%置信椭圆）
        cop_area = self._calculate_cop_95_percent_ellipse(cop_trajectory)
        
        # 6. 前后（AP）和左右（ML）摆动范围
        ap_range = max(y_positions) - min(y_positions)  # 前后范围
        ml_range = max(x_positions) - min(x_positions)  # 左右范围
        
        # 7. 轨迹复杂度
        complexity = self._calculate_trajectory_complexity(cop_trajectory)
        
        # 8. 稳定性指数（综合评分）
        stability_index = self._calculate_stability_index(
            total_distance, cop_area, avg_velocity, max_displacement
        )
        
        return {
            # 基础指标
            'copDisplacement': max_displacement * 100,  # 转换为cm
            'copVelocity': avg_velocity * 100,          # 转换为cm/s
            'swayArea': sway_area * 10000,              # 转换为cm²
            'stabilityIndex': stability_index,
            
            # 新增COP轨迹指标（与报告页面字段对应）
            'copArea': cop_area * 10000,                # COP轨迹面积 (cm²)
            'copPathLength': total_distance * 100,      # 轨迹总长度 (cm)
            'copComplexity': complexity,                # 轨迹复杂度 (/10)
            'anteroPosteriorRange': ap_range * 100,     # 前后摆动范围 (cm)
            'medioLateralRange': ml_range * 100,        # 左右摆动范围 (cm)
            
            # 兼容旧版本字段
            'average_velocity': avg_velocity,
            'max_displacement': max_displacement,
            'trajectory_length': total_distance,
            'stability_score': stability_index
        }
    
    def comprehensive_analysis(self, csv_file_path: str) -> Dict:
        """综合分析入口函数 - 集成硬件自适应功能"""
        try:
            # 读取CSV文件
            with open(csv_file_path, 'r', encoding='utf-8') as f:
                csv_content = f.read()
            
            # 解析数据
            pressure_matrix = self.parse_csv_data(csv_content)
            if not pressure_matrix:
                return {'error': 'Failed to parse CSV data'}
            
            # 🚀 渐进式硬件自适应初始化 - NEW!
            filename = Path(csv_file_path).name
            hardware_initialized = self.initialize_hardware_adaptive(pressure_matrix, filename)
            if not hardware_initialized:
                print("⚠️  Python硬件自适应初始化异常，但系统将继续使用默认配置")
            
            # 使用所有数据作为时间序列
            pressure_sequence = pressure_matrix  # pressure_matrix已经是时间序列了
            
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
    
    def _calculate_cop_95_percent_ellipse(self, positions: List[Dict]) -> float:
        """计算95%置信椭圆面积 - 与平台算法同步"""
        if len(positions) < 3:
            return 0.0
        
        # 计算质心
        center_x = np.mean([p['x'] for p in positions])
        center_y = np.mean([p['y'] for p in positions])
        
        # 计算协方差矩阵
        cov_xx = 0
        cov_yy = 0
        cov_xy = 0
        
        for pos in positions:
            dx = pos['x'] - center_x
            dy = pos['y'] - center_y
            cov_xx += dx * dx
            cov_yy += dy * dy
            cov_xy += dx * dy
        
        n = len(positions)
        cov_xx /= (n - 1)
        cov_yy /= (n - 1)
        cov_xy /= (n - 1)
        
        # 计算椭圆参数（95%置信区间）
        chi2 = 5.991  # 95%置信水平的卡方值，自由度=2
        a = np.sqrt(chi2 * cov_xx)
        b = np.sqrt(chi2 * cov_yy)
        
        # 椭圆面积
        return np.pi * a * b
    
    def _calculate_trajectory_complexity(self, positions: List[Dict]) -> float:
        """计算轨迹复杂度 - 与平台算法同步"""
        if len(positions) < 5:
            return 1.0
        
        # 计算方向变化次数
        direction_changes = 0
        
        for i in range(2, len(positions)):
            # 计算相邻两个向量
            v1x = positions[i-1]['x'] - positions[i-2]['x']
            v1y = positions[i-1]['y'] - positions[i-2]['y']
            v2x = positions[i]['x'] - positions[i-1]['x']
            v2y = positions[i]['y'] - positions[i-1]['y']
            
            # 计算叉积判断方向变化
            cross = v1x * v2y - v1y * v2x
            
            if abs(cross) > 0.001:  # 有明显方向改变
                direction_changes += 1
        
        # 复杂度评分（0-10分）
        complexity_ratio = direction_changes / len(positions)
        return min(10.0, round(complexity_ratio * 20, 1))
    
    def _calculate_stability_index(self, path_length: float, sway_area: float, 
                                 velocity: float, max_displacement: float) -> float:
        """计算稳定性指数 - 与平台算法同步"""
        score = 100.0  # 满分100分
        
        # 路径长度评分（越短越好）
        if path_length > 1.0:    # 100cm
            score -= 20
        elif path_length > 0.7:  # 70cm
            score -= 10
        elif path_length > 0.5:  # 50cm
            score -= 5
        
        # 摆动面积评分（越小越好）
        if sway_area > 0.001:    # 10cm²
            score -= 15
        elif sway_area > 0.0006: # 6cm²
            score -= 8
        elif sway_area > 0.0003: # 3cm²
            score -= 3
        
        # 速度评分（越慢越好）
        if velocity > 0.05:      # 5cm/s
            score -= 10
        elif velocity > 0.03:    # 3cm/s
            score -= 5
        elif velocity > 0.02:    # 2cm/s
            score -= 3
        
        # 最大位移评分（越小越好）
        if max_displacement > 0.05:  # 5cm
            score -= 10
        elif max_displacement > 0.03: # 3cm
            score -= 5
        elif max_displacement > 0.02: # 2cm
            score -= 3
        
        return max(0.0, min(100.0, score))

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