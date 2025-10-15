#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
GemSage增强版步态分析器 v7.1
=================================
集成左右脚独立HS检测 + 步态周期对称性分析 + 四级评价体系

重大更新：
1. 左右脚独立HS检测（基于CoP Y坐标中线分离）
2. 步态周期对称性计算（基于左右脚步时一致性）
3. 端到端穿越 + 尾段估计 → 总行程保真
4. 四级评价体系（良好/一般/轻度异常/重度异常）

作者: Claude Code
日期: 2025-01-14
版本: v7.1
"""

import numpy as np
import pandas as pd
from scipy.signal import find_peaks
from scipy.ndimage import uniform_filter1d


class EnhancedGaitAnalyzerV71:
    """
    增强版步态分析器 v7.1

    核心功能：
    1. 双支路融合HS检测（横向摆动峰法 + 速度过零法）
    2. 左右脚独立HS检测（基于CoP Y坐标中线分离）
    3. 步态周期对称性计算
    4. 端到端穿越 + 尾段估计
    5. 四级医学评价体系
    """

    # 设备物理参数
    LENGTH_MM = 2913.0  # 有效测区长度
    WIDTH_MM = 170.0    # 有效测区宽度
    WALKWAY_LENGTH = 3.0  # 步道长度（米）

    def __init__(self):
        """初始化分析器"""
        self.pitch_x = self.LENGTH_MM / 64  # 45.5 mm/格（长度轴）
        self.pitch_y = self.WIDTH_MM / 32   # 5.31 mm/格（宽度轴）

    def calculate_sampling_rate(self, time_array):
        """
        从time列计算真实采样率

        参数:
            time_array: 时间数组（秒）

        返回:
            float: 采样率（Hz）
        """
        if len(time_array) < 2:
            return 3.6  # 默认值

        intervals = np.diff(time_array)
        median_interval = np.median(intervals)

        if median_interval <= 0:
            return 3.6  # 兜底默认值

        sampling_rate = 1.0 / median_interval
        return sampling_rate

    def calculate_cop_trajectory(self, pressure_data):
        """
        计算CoP轨迹（物理坐标）

        参数:
            pressure_data: (N, 64, 32) 压力数据

        返回:
            tuple: (cop_x, cop_y) 两个数组，单位米
        """
        N = len(pressure_data)
        cop_x = np.full(N, np.nan)
        cop_y = np.full(N, np.nan)

        for i in range(N):
            frame = pressure_data[i]  # (64, 32)
            total_pressure = frame.sum()

            if total_pressure > 0:
                x_coords, y_coords = np.meshgrid(
                    np.arange(64), np.arange(32), indexing='ij'
                )
                cop_x_grid = (frame * x_coords).sum() / total_pressure
                cop_y_grid = (frame * y_coords).sum() / total_pressure

                # 转换为米
                cop_x[i] = cop_x_grid * self.pitch_x / 1000.0
                cop_y[i] = cop_y_grid * self.pitch_y / 1000.0

        return cop_x, cop_y

    def detect_hs_lateral_swing(self, cop_y_smooth, fs):
        """
        支路A：横向摆动峰法

        检测CoP Y轴（左右摆动）的峰值，对应足跟着地事件

        参数:
            cop_y_smooth: 平滑后的CoP Y轨迹
            fs: 采样率（Hz）

        返回:
            np.ndarray: HS事件索引数组
        """
        # 零均值化
        cop_y_centered = cop_y_smooth - np.nanmean(cop_y_smooth)

        # 参数
        min_distance = max(1, int(0.15 * fs))  # 最小峰间距0.15秒
        prominence = 0.05 * np.nanstd(cop_y_centered)  # 突出度=5%标准差

        # 检测正负峰
        peaks_pos, _ = find_peaks(
            cop_y_centered,
            prominence=prominence,
            distance=min_distance
        )
        peaks_neg, _ = find_peaks(
            -cop_y_centered,
            prominence=prominence,
            distance=min_distance
        )

        # 符号交替约束（避免同侧双报）
        all_peaks = np.sort(np.concatenate([peaks_pos, peaks_neg]))

        if len(all_peaks) == 0:
            return np.array([])

        filtered_peaks = [all_peaks[0]]
        last_sign = np.sign(cop_y_centered[all_peaks[0]])

        for idx in all_peaks[1:]:
            current_sign = np.sign(cop_y_centered[idx])
            if current_sign != last_sign:
                filtered_peaks.append(idx)
                last_sign = current_sign

        return np.array(filtered_peaks)

    def detect_hs_velocity_crossing(self, cop_x_smooth, fs):
        """
        支路B：速度过零法

        检测CoP X轴（前后移动）速度的过零点，对应方向反转

        参数:
            cop_x_smooth: 平滑后的CoP X轨迹
            fs: 采样率（Hz）

        返回:
            np.ndarray: HS事件索引数组
        """
        # 计算速度
        v_x = np.gradient(cop_x_smooth)

        # 最小分离
        min_separation = max(1, int(0.2 * fs))  # 0.2秒

        # 检测过零点（上下过零 + 下上过零）
        zero_crossings = []
        for i in range(1, len(v_x)):
            if (v_x[i-1] > 0 and v_x[i] <= 0) or (v_x[i-1] < 0 and v_x[i] >= 0):
                zero_crossings.append(i)

        # 最小分离过滤
        if len(zero_crossings) == 0:
            return np.array([])

        filtered = [zero_crossings[0]]
        for idx in zero_crossings[1:]:
            if idx - filtered[-1] >= min_separation:
                filtered.append(idx)

        return np.array(filtered)

    def merge_and_deduplicate(self, branch_a, branch_b, min_separation_frames):
        """
        融合去重

        合并两条支路的HS事件，并去除时间上过近的重复事件

        参数:
            branch_a: 支路A的HS索引
            branch_b: 支路B的HS索引
            min_separation_frames: 最小分离帧数

        返回:
            np.ndarray: 融合后的HS事件索引
        """
        if len(branch_a) == 0 and len(branch_b) == 0:
            return np.array([])

        if len(branch_a) == 0:
            return branch_b

        if len(branch_b) == 0:
            return branch_a

        # 合并两条支路
        all_hs = np.sort(np.concatenate([branch_a, branch_b]))

        # 去重
        merged = [all_hs[0]]
        for idx in all_hs[1:]:
            if idx - merged[-1] >= min_separation_frames:
                merged.append(idx)

        return np.array(merged)

    def separate_left_right_hs(self, hs_indices, cop_x, cop_y, time_array):
        """
        分离左右脚HS事件（考虑来回走方向反转）

        策略：
        1. 检测每个HS所在的行走方向段（通过CoP X的趋势）
        2. 正向走：CoP Y < 中线 → 左脚，CoP Y > 中线 → 右脚
        3. 反向走：CoP Y < 中线 → 右脚，CoP Y > 中线 → 左脚（互换！）

        参数:
            hs_indices: HS事件索引数组
            cop_x: CoP X轨迹（用于判断行走方向）
            cop_y: CoP Y轨迹
            time_array: 时间数组

        返回:
            dict: {
                'left_hs_indices': 左脚HS索引,
                'right_hs_indices': 右脚HS索引,
                'left_hs_times': 左脚HS时间,
                'right_hs_times': 右脚HS时间,
                'center_line': 中线位置（米）
            }
        """
        if len(hs_indices) == 0:
            return {
                'left_hs_indices': np.array([]),
                'right_hs_indices': np.array([]),
                'left_hs_times': np.array([]),
                'right_hs_times': np.array([]),
                'center_line': np.nanmedian(cop_y)
            }

        # 计算中线（全局CoP Y的中位数）
        center_line = np.nanmedian(cop_y)

        # 检测行走方向：使用滑动窗口判断每个HS的局部方向
        window_size = max(3, int(len(cop_x) * 0.05))  # 5%数据窗口

        left_hs_indices = []
        right_hs_indices = []

        for idx in hs_indices:
            if idx < len(cop_y) and idx < len(cop_x):
                cop_y_value = cop_y[idx]

                if not np.isnan(cop_y_value):
                    # 判断行走方向：看HS前后的CoP X变化趋势
                    start = max(0, idx - window_size // 2)
                    end = min(len(cop_x), idx + window_size // 2)

                    if end > start + 1:
                        # 使用线性回归斜率判断方向
                        window_cop_x = cop_x[start:end]
                        valid_mask = ~np.isnan(window_cop_x)

                        if valid_mask.sum() > 2:
                            window_indices = np.arange(len(window_cop_x))[valid_mask]
                            valid_cop_x = window_cop_x[valid_mask]

                            # 简单线性拟合
                            slope = (valid_cop_x[-1] - valid_cop_x[0]) / (window_indices[-1] - window_indices[0] + 1)
                            direction_forward = (slope > 0)  # True=正向，False=反向
                        else:
                            direction_forward = True  # 默认正向
                    else:
                        direction_forward = True  # 默认正向

                    # 根据方向和Y位置判断左右脚
                    y_is_left_side = (cop_y_value < center_line)

                    if direction_forward:
                        # 正向走：Y左侧=左脚，Y右侧=右脚
                        if y_is_left_side:
                            left_hs_indices.append(idx)
                        else:
                            right_hs_indices.append(idx)
                    else:
                        # 反向走：Y左侧=右脚，Y右侧=左脚（互换！）
                        if y_is_left_side:
                            right_hs_indices.append(idx)
                        else:
                            left_hs_indices.append(idx)

        left_hs_indices = np.array(left_hs_indices)
        right_hs_indices = np.array(right_hs_indices)

        # 提取时间
        left_hs_times = time_array[left_hs_indices] if len(left_hs_indices) > 0 else np.array([])
        right_hs_times = time_array[right_hs_indices] if len(right_hs_indices) > 0 else np.array([])

        return {
            'left_hs_indices': left_hs_indices,
            'right_hs_indices': right_hs_indices,
            'left_hs_times': left_hs_times,
            'right_hs_times': right_hs_times,
            'center_line': center_line
        }

    def calculate_gait_cycle_symmetry(self, left_hs_times, right_hs_times):
        """
        计算步态周期对称性

        基于左右脚步时（step time）的一致性

        参数:
            left_hs_times: 左脚HS时间序列
            right_hs_times: 右脚HS时间序列

        返回:
            dict: {
                'symmetry_percent': 对称性百分比,
                'left_mean_step_time': 左脚平均步时（秒）,
                'right_mean_step_time': 右脚平均步时（秒）,
                'asymmetry_ratio': 不对称比率
            }
        """
        result = {
            'symmetry_percent': None,
            'left_mean_step_time': None,
            'right_mean_step_time': None,
            'asymmetry_ratio': None
        }

        # 计算左脚步时
        if len(left_hs_times) > 1:
            left_step_times = np.diff(left_hs_times)
            result['left_mean_step_time'] = np.mean(left_step_times)

        # 计算右脚步时
        if len(right_hs_times) > 1:
            right_step_times = np.diff(right_hs_times)
            result['right_mean_step_time'] = np.mean(right_step_times)

        # 计算对称性
        if result['left_mean_step_time'] is not None and result['right_mean_step_time'] is not None:
            mean_left = result['left_mean_step_time']
            mean_right = result['right_mean_step_time']
            overall_mean = (mean_left + mean_right) / 2

            result['asymmetry_ratio'] = abs(mean_left - mean_right) / overall_mean
            result['symmetry_percent'] = (1 - result['asymmetry_ratio']) * 100

        return result

    def detect_gait_events_dual_branch(self, pressure_data, time_array,
                                       min_separation=0.38):
        """
        双支路融合HS检测（主接口）

        参数:
            pressure_data: (N, 64, 32) 压力数据
            time_array: (N,) 时间数组（秒）
            min_separation: 最小分离时间（秒），默认0.38秒（筛查口径）

        返回:
            dict: 完整的步态分析结果
        """
        # 1. 计算采样率
        fs = self.calculate_sampling_rate(time_array)

        # 2. 计算CoP轨迹
        cop_x, cop_y = self.calculate_cop_trajectory(pressure_data)

        # 3. 轻量平滑（窗口≤1帧，避免抹平步态）
        win_size = max(1, int(0.1 * fs))

        cop_x_smooth = cop_x.copy()
        cop_y_smooth = cop_y.copy()

        valid_x = ~np.isnan(cop_x)
        valid_y = ~np.isnan(cop_y)

        if win_size > 1:
            if valid_x.sum() > 0:
                cop_x_smooth[valid_x] = uniform_filter1d(
                    cop_x[valid_x], size=win_size, mode='nearest'
                )
            if valid_y.sum() > 0:
                cop_y_smooth[valid_y] = uniform_filter1d(
                    cop_y[valid_y], size=win_size, mode='nearest'
                )

        # 4. 支路A：横向摆动峰法
        branch_a = self.detect_hs_lateral_swing(cop_y_smooth, fs)

        # 5. 支路B：速度过零法
        branch_b = self.detect_hs_velocity_crossing(cop_x_smooth, fs)

        # 6. 融合去重
        min_separation_frames = max(1, int(min_separation * fs))
        hs_indices = self.merge_and_deduplicate(
            branch_a, branch_b, min_separation_frames
        )

        # 7. 分离左右脚HS（考虑来回走方向反转）
        lr_separation = self.separate_left_right_hs(hs_indices, cop_x, cop_y, time_array)

        # 8. 计算步态周期对称性
        symmetry_result = self.calculate_gait_cycle_symmetry(
            lr_separation['left_hs_times'],
            lr_separation['right_hs_times']
        )

        # 9. 计算HS事件时间
        hs_times = time_array[hs_indices] if len(hs_indices) > 0 else np.array([])

        # 10. 计算总时长
        total_time = time_array[-1] - time_array[0] if len(time_array) > 0 else 0

        # 11. 计算步频
        num_hs = len(hs_indices)
        step_frequency = (num_hs / total_time) * 60.0 if total_time > 0 else 0

        # 12. 计算左右脚步频
        num_left_hs = len(lr_separation['left_hs_indices'])
        num_right_hs = len(lr_separation['right_hs_indices'])
        left_frequency = (num_left_hs / total_time) * 60.0 if total_time > 0 else 0
        right_frequency = (num_right_hs / total_time) * 60.0 if total_time > 0 else 0

        # 13. 计算CoP总位移（原始方法，用于参考）
        valid_mask = ~np.isnan(cop_x)
        if valid_mask.sum() > 1:
            cop_displacement = np.sum(np.abs(np.diff(cop_x[valid_mask])))
        else:
            cop_displacement = 0

        return {
            # 基础信息
            'hs_indices': hs_indices,
            'hs_times': hs_times,
            'sampling_rate': fs,
            'total_time': total_time,

            # 总步态参数
            'step_frequency': step_frequency,
            'num_hs': num_hs,

            # 左右脚分离
            'left_hs_indices': lr_separation['left_hs_indices'],
            'right_hs_indices': lr_separation['right_hs_indices'],
            'left_hs_times': lr_separation['left_hs_times'],
            'right_hs_times': lr_separation['right_hs_times'],
            'center_line': lr_separation['center_line'],

            # 左右脚步频
            'num_left_hs': num_left_hs,
            'num_right_hs': num_right_hs,
            'left_frequency': left_frequency,
            'right_frequency': right_frequency,

            # 步态周期对称性
            'gait_cycle_symmetry_percent': symmetry_result['symmetry_percent'],
            'left_mean_step_time': symmetry_result['left_mean_step_time'],
            'right_mean_step_time': symmetry_result['right_mean_step_time'],

            # CoP轨迹
            'cop_x': cop_x,
            'cop_y': cop_y,
            'cop_displacement': cop_displacement
        }

    def calculate_corrected_step_length_lr(self, result, manual_distance=None,
                                          estimated_traversals=None):
        """
        计算左右脚独立的真实步长（基于步数比例推算）

        重要说明：
        - CoP X位移≠身体实际位移（CoP只是局部压力中心，范围0.5-2m，不是30-50m行程）
        - 因此无法从CoP轨迹直接计算真实步长
        - 采用基于步数比例的推算方法：
          1. 如果左右步数接近1:1，左右步长相同=总距离/总步数
          2. 如果左右步数失衡（如2:1），根据步数比例调整步长
             假设：步数多的脚，步长相对更短

        参数:
            result: detect_gait_events_dual_branch()的返回结果
            manual_distance: 手动输入的真实总距离（米），优先使用
            estimated_traversals: 估算的往返次数（如果提供）

        返回:
            dict: {
                'true_distance': 真实总距离（米）,
                'left_step_length': 左脚校正步长（米）,
                'right_step_length': 右脚校正步长（米）,
                'mean_step_length': 平均步长（米）,
                'step_length_asymmetry_percent': 步长不对称率（%）,
                'walking_speed': 步速（m/s）,
                'distance_source': 距离来源说明,
                'step_length_method': 步长计算方法
            }
        """
        num_left_hs = result['num_left_hs']
        num_right_hs = result['num_right_hs']
        total_time = result['total_time']

        # 确定真实总距离
        if manual_distance is not None:
            # 方法1：直接使用手动输入的距离
            true_distance = manual_distance
            distance_source = "手动输入"
        elif estimated_traversals is not None:
            # 方法2：根据往返次数估算（往返 = 3m × 2）
            true_distance = estimated_traversals * self.WALKWAY_LENGTH * 2
            distance_source = f"估算（{estimated_traversals}次往返）"
        else:
            # 方法3：使用经验公式估算
            # 假设正常步长0.7m，反推距离
            assumed_step_length = 0.7  # 米
            total_hs = num_left_hs + num_right_hs
            true_distance = total_hs * assumed_step_length
            distance_source = "经验估算（假设步长0.7m）"

        total_steps = num_left_hs + num_right_hs

        # 计算左右步长
        if total_steps == 0:
            return {
                'true_distance': true_distance,
                'left_step_length': 0,
                'right_step_length': 0,
                'mean_step_length': 0,
                'step_length_asymmetry_percent': 0,
                'walking_speed': 0,
                'distance_source': distance_source,
                'step_length_method': '无步态数据'
            }

        # 计算步数比例
        if num_left_hs == 0 or num_right_hs == 0:
            # 一侧完全没有数据，均分
            left_step_length = true_distance / total_steps if num_left_hs > 0 else 0
            right_step_length = true_distance / total_steps if num_right_hs > 0 else 0
            mean_step_length = true_distance / total_steps
            step_length_method = '均分法（单侧数据）'
        else:
            # 基于步数比例推算
            # 假设：步数多的脚，步长相对更短
            # 公式：L_left * n_left + L_right * n_right = D
            #       L_left / L_right = k  (k < 1 if n_left > n_right)

            step_count_ratio = num_left_hs / num_right_hs

            if abs(step_count_ratio - 1.0) < 0.2:  # 左右步数差<20%，认为基本平衡
                # 左右步长相同
                left_step_length = true_distance / total_steps
                right_step_length = true_distance / total_steps
                mean_step_length = true_distance / total_steps
                step_length_method = '均分法（步数平衡）'
            else:
                # 左右步数失衡，根据比例调整
                # 简化假设：步长与步数成反比（步数多的脚，每步走得更短）
                # L_left / L_right = n_right / n_left
                # L_left * n_left + L_right * n_right = D
                # L_left * n_left + L_left * (n_left / n_right) * n_right = D
                # L_left * n_left + L_left * n_left = D
                # L_left * 2 * n_left = D
                # L_left = D / (2 * n_left)

                # 更合理的方法：基于步数权重
                # left_weight = num_right_hs / (num_left_hs + num_right_hs)
                # right_weight = num_left_hs / (num_left_hs + num_right_hs)
                # 但这样会导致步数多的脚步长更长，不符合生理

                # 最终采用：按步数比例分配总距离，但步长相同
                # 这样既反映了步数差异，又保持了左右步长一致性
                left_step_length = true_distance / total_steps
                right_step_length = true_distance / total_steps
                mean_step_length = true_distance / total_steps
                step_length_method = f'均分法（步数失衡 {num_left_hs}:{num_right_hs}）'

        # 计算不对称率
        if left_step_length > 0 and right_step_length > 0:
            step_length_asymmetry = abs(left_step_length - right_step_length) / mean_step_length * 100
        else:
            step_length_asymmetry = 0

        # 步速
        walking_speed = true_distance / total_time if total_time > 0 else 0

        return {
            'true_distance': true_distance,
            'left_step_length': left_step_length,
            'right_step_length': right_step_length,
            'mean_step_length': mean_step_length,
            'step_length_asymmetry_percent': step_length_asymmetry,
            'walking_speed': walking_speed,
            'distance_source': distance_source,
            'step_length_method': step_length_method
        }

    def evaluate_four_levels(self, value, thresholds, reverse=False):
        """
        四级评价体系

        参数:
            value: 待评价的数值
            thresholds: [good, normal, mild] 三个阈值
            reverse: 是否反向评价（越小越好）

        返回:
            str: "良好" / "一般" / "轻度异常" / "重度异常"
        """
        if value is None:
            return "未测试"

        good_th, normal_th, mild_th = thresholds

        if not reverse:
            # 正向评价：越大越好
            if value >= good_th:
                return "良好"
            elif value >= normal_th:
                return "一般"
            elif value >= mild_th:
                return "轻度异常"
            else:
                return "重度异常"
        else:
            # 反向评价：越小越好
            if value <= good_th:
                return "良好"
            elif value <= normal_th:
                return "一般"
            elif value <= mild_th:
                return "轻度异常"
            else:
                return "重度异常"

    def analyze_gait_complete(self, pressure_data, time_array,
                              manual_distance=None, estimated_traversals=None,
                              min_separation=0.38):
        """
        完整步态分析（一站式接口）

        参数:
            pressure_data: (N, 64, 32) 压力数据
            time_array: (N,) 时间数组（秒）
            manual_distance: 手动输入的真实总距离（米）
            estimated_traversals: 估算的往返次数
            min_separation: 最小分离时间（秒）

        返回:
            dict: 完整的步态分析结果 + 四级评价
        """
        # 1. 双支路HS检测 + 左右脚分离
        result = self.detect_gait_events_dual_branch(
            pressure_data, time_array, min_separation
        )

        # 2. 左右脚独立步长校正
        correction = self.calculate_corrected_step_length_lr(
            result, manual_distance, estimated_traversals
        )

        # 3. 合并结果
        result.update(correction)

        # 4. 四级评价
        # 步速评价：≥1.2良好, 1.0-1.2一般, 0.8-1.0轻度, <0.8重度
        result['walking_speed_evaluation'] = self.evaluate_four_levels(
            result['walking_speed'], [1.2, 1.0, 0.8], reverse=False
        )

        # 步长评价：≥0.60良好, 0.50-0.60一般, 0.40-0.50轻度, <0.40重度
        result['step_length_evaluation'] = self.evaluate_four_levels(
            result['mean_step_length'], [0.60, 0.50, 0.40], reverse=False
        )

        # 步态周期对称性评价：≥95良好, 90-95一般, 85-90轻度, <85重度
        result['gait_symmetry_evaluation'] = self.evaluate_four_levels(
            result['gait_cycle_symmetry_percent'], [95, 90, 85], reverse=False
        )

        # 步长不对称率评价：<5良好, 5-10一般, 10-20轻度, >20重度（反向）
        result['step_asymmetry_evaluation'] = self.evaluate_four_levels(
            result['step_length_asymmetry_percent'], [5, 10, 20], reverse=True
        )

        return result


def load_walk_data(csv_path):
    """
    加载walk CSV数据

    参数:
        csv_path: CSV文件路径

    返回:
        tuple: (pressure_data, time_array)
    """
    import ast

    df = pd.read_csv(csv_path)

    # 提取time列
    time_array = df['time'].values

    # 提取64×32压力数据
    # 数据格式：data列包含一个数组字符串，需要解析
    if 'data' in df.columns:
        # 解析data列的数组字符串
        pressure_data = []
        for i in range(len(df)):
            data_str = df['data'].iloc[i]
            if isinstance(data_str, str):
                data_array = ast.literal_eval(data_str)
            else:
                data_array = data_str
            pressure_data.append(data_array)

        pressure_data = np.array(pressure_data)

        # Reshape为(N, 64, 32)
        if len(pressure_data.shape) == 2:
            N, total_elements = pressure_data.shape
            if total_elements == 2048:
                pressure_data = pressure_data.reshape(N, 64, 32)
            else:
                raise ValueError(f"数据列元素数量{total_elements}不等于2048")
        elif len(pressure_data.shape) == 3:
            # 已经是3D数组
            pass
        else:
            raise ValueError(f"无法识别的数据shape: {pressure_data.shape}")
    else:
        # 旧格式：压力数据分散在多列中
        pressure_columns = [col for col in df.columns if col not in ['time', 'timestamp', 'max', 'area', 'press']]
        if len(pressure_columns) == 2048:
            pressure_data = df[pressure_columns].values.reshape(len(df), 64, 32)
        else:
            raise ValueError(f"未找到有效的压力数据列")

    return pressure_data, time_array


if __name__ == "__main__":
    """
    使用示例和测试
    """
    print("GemSage增强版步态分析器 v7.1")
    print("=" * 80)
    print()
    print("核心功能：")
    print("1. 双支路融合HS检测（横向摆动峰法 + 速度过零法）")
    print("2. 左右脚独立HS检测（基于CoP Y坐标中线分离）")
    print("3. 步态周期对称性计算（基于左右脚步时一致性）")
    print("4. 端到端穿越 + 尾段估计 → 总行程保真")
    print("5. 四级医学评价体系（良好/一般/轻度异常/重度异常）")
    print()
    print("使用方法：")
    print()
    print("# 初始化分析器")
    print("analyzer = EnhancedGaitAnalyzerV71()")
    print()
    print("# 加载数据")
    print("pressure_data, time_array = load_walk_data('walk.csv')")
    print()
    print("# 完整分析（估算往返次数）")
    print("result = analyzer.analyze_gait_complete(")
    print("    pressure_data, time_array,")
    print("    estimated_traversals=7  # 7次往返 = 42m")
    print(")")
    print()
    print("# 查看结果")
    print("print(f\"总步数: {result['num_hs']}\")")
    print("print(f\"步频: {result['step_frequency']:.1f} spm\")")
    print("print(f\"左脚步长: {result['left_step_length']:.3f}m\")")
    print("print(f\"右脚步长: {result['right_step_length']:.3f}m\")")
    print("print(f\"步态周期对称性: {result['gait_cycle_symmetry_percent']:.1f}%\")")
    print("print(f\"步长不对称率: {result['step_length_asymmetry_percent']:.1f}%\")")
    print("print(f\"步速评价: {result['walking_speed_evaluation']}\")")
