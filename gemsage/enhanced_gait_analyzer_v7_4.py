#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
GemSage增强版步态分析器 v7.4.2
=================================
在v7.2基础上增加足迹投影法（仅适用于单向直线行走）

重大更新：
1. 足迹CoP提取：压力加权质心（v7.4.2修正版）
2. 行走轴PCA计算：所有足迹中心点主成分分析
3. 步长投影法：足迹CoP投影到主轴，异侧HS步长计算
4. 端部剔除：保留有效投影范围（可选，默认禁用）
5. 步长过滤：20-120cm合理范围

⚠️ 投影法适用场景：
  ✅ 单向直线行走（跑步机、直线步道、6米步行测试）
  ❌ 往返行走（本系统主场景，使用v7.2均分法）

目标：实现真实左右脚步长分离，步长60-80cm，步速1.0-1.4m/s

使用建议：
- 往返行走：use_projection=False（v7.2均分法） ✅ 推荐
- 单向行走：use_projection=True（v7.4投影法）

作者: Claude Code + 用户专业方案
日期: 2025-10-15
版本: v7.4.2
"""

import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from scipy.signal import find_peaks
from scipy.ndimage import uniform_filter1d, label as nd_label
from sklearn.cluster import KMeans
from sklearn.decomposition import PCA

# 导入v7.2作为基类
from enhanced_gait_analyzer_v7_2 import EnhancedGaitAnalyzerV72, load_walk_data


class EnhancedGaitAnalyzerV74(EnhancedGaitAnalyzerV72):
    """
    增强版步态分析器 v7.4

    在v7.2基础上增加足迹投影法：
    - 足迹几何中心提取（非CoP）
    - 行走轴PCA计算
    - 步长投影到主轴
    - 真实左右脚步长分离
    """

    def __init__(self):
        """初始化分析器"""
        super().__init__()

        # v7.4新增参数
        self.foot_pressure_threshold = 0.2  # 足迹分割阈值（相对最大压力）
        self.endpoint_trim_m = 0.3  # 每段端部剔除距离（米）
        self.step_length_min = 0.2  # 最小合理步长（米）- 放宽到20cm
        self.step_length_max = 1.2  # 最大合理步长（米）- 放宽到120cm
        self.use_endpoint_trimming = False  # 默认禁用端部剔除（仅用步长过滤）

        # 设备物理参数（继承自v7.1，但明确声明）
        self.SENSOR_LENGTH_M = self.LENGTH_MM / 1000.0  # 2.913m
        self.SENSOR_WIDTH_M = self.WIDTH_MM / 1000.0    # 0.170m

    def extract_foot_geometric_center(self, frame):
        """
        提取单帧足迹压力中心（CoP）- v7.4.2修正版

        修正说明：
        - 改用压力加权质心（CoP）代替几何中心，对稀疏数据更鲁棒
        - 降低阈值到5%，确保捕捉所有有效压力
        - 简化算法，提高稳定性

        算法：
        1. 过滤噪声：P > 5% * max(P)
        2. 压力加权质心：CoP = Σ(P_i * pos_i) / Σ(P_i)

        参数:
            frame: (64, 32) 压力数据帧

        返回:
            tuple: (x_cop, y_cop) CoP坐标（米），无有效压力返回(nan, nan)
        """
        if frame is None or frame.size == 0:
            return (np.nan, np.nan)

        # 1. 过滤噪声（5%阈值，捕捉所有有效压力）
        max_pressure = np.nanmax(frame)
        if max_pressure <= 0 or np.isnan(max_pressure):
            return (np.nan, np.nan)

        threshold = 0.05 * max_pressure  # 5%阈值（降低from 20%）
        valid_pressure = frame.copy()
        valid_pressure[valid_pressure < threshold] = 0

        total_pressure = np.sum(valid_pressure)
        if total_pressure <= 0:
            return (np.nan, np.nan)

        # 2. 计算压力加权质心（CoP）
        rows, cols = np.meshgrid(np.arange(64), np.arange(32), indexing='ij')

        # 像素坐标CoP
        row_cop = np.sum(valid_pressure * rows) / total_pressure
        col_cop = np.sum(valid_pressure * cols) / total_pressure

        # 转换为物理坐标（米）
        # 64行 -> 2.913m, 32列 -> 0.170m
        x_cop = row_cop * (self.SENSOR_LENGTH_M / 64)
        y_cop = col_cop * (self.SENSOR_WIDTH_M / 32)

        return (x_cop, y_cop)

    def calculate_walkway_axis_pca(self, foot_centers):
        """
        基于所有足迹中心点做PCA，计算行走轴方向

        参数:
            foot_centers: [(x, y), ...] 足迹中心点列表

        返回:
            dict: {
                'u_hat': 单位方向向量 (ux, uy),
                'pca_explained_variance': 第一主成分解释方差比例,
                'mean_center': (mean_x, mean_y) 中心点均值
            }
        """
        if len(foot_centers) < 2:
            return {
                'u_hat': (1.0, 0.0),  # 默认X轴方向
                'pca_explained_variance': 0,
                'mean_center': (0, 0)
            }

        # 过滤无效点
        valid_centers = [(x, y) for x, y in foot_centers if not (np.isnan(x) or np.isnan(y))]

        if len(valid_centers) < 2:
            return {
                'u_hat': (1.0, 0.0),
                'pca_explained_variance': 0,
                'mean_center': (0, 0)
            }

        # 转换为numpy数组
        centers_array = np.array(valid_centers)  # (N, 2)

        # PCA分析
        pca = PCA(n_components=2)
        pca.fit(centers_array)

        # 第一主成分（行走方向）
        u_hat = pca.components_[0]  # (2,)

        # 归一化（确保单位向量）
        u_hat = u_hat / np.linalg.norm(u_hat)

        # 确保方向一致（X分量为正）
        if u_hat[0] < 0:
            u_hat = -u_hat

        mean_center = np.mean(centers_array, axis=0)

        return {
            'u_hat': tuple(u_hat),
            'pca_explained_variance': pca.explained_variance_ratio_[0],
            'mean_center': tuple(mean_center)
        }

    def calculate_step_length_projection(self, pressure_data, hs_indices,
                                        side_labels, time_array):
        """
        基于足迹投影法计算真实左右脚步长

        算法：
        1. 提取所有HS帧的足迹几何中心
        2. PCA计算行走轴u_hat
        3. 投影到主轴：s_k = (c_k - c_0) · u_hat（c_0为第一个HS位置）
        4. 端部剔除（可选，默认禁用）：剔除每段前后0.3m
        5. 步长：|s_k - s_{k-1}|（异侧HS）
        6. 步长过滤：0.3-1.1m（主要依赖此过滤）

        修正说明（v7.4.1）：
        - 投影参考点从PCA中心改为第一个HS位置，避免投影负值
        - 端部剔除默认禁用，主要依赖步长范围过滤
        - 保留更多有效步态数据，提高统计稳定性

        参数:
            pressure_data: (N, 64, 32) 压力数据
            hs_indices: HS事件索引数组
            side_labels: 左右脚标签（0=左，1=右）
            time_array: 时间数组

        返回:
            dict: {
                'left_step_lengths': [步长列表],
                'right_step_lengths': [步长列表],
                'left_mean_step_length': 左脚平均步长,
                'right_mean_step_length': 右脚平均步长,
                'mean_step_length': 总平均步长,
                'step_length_asymmetry_percent': 不对称率,
                'walking_speed': 步速,
                'projection_info': 投影详细信息,
                'pca_info': PCA信息
            }
        """
        if len(hs_indices) == 0:
            return {
                'left_step_lengths': [],
                'right_step_lengths': [],
                'left_mean_step_length': 0,
                'right_mean_step_length': 0,
                'mean_step_length': 0,
                'step_length_asymmetry_percent': 0,
                'walking_speed': 0,
                'projection_info': None,
                'pca_info': None
            }

        # 1. 提取所有HS帧的足迹几何中心
        foot_centers = []
        valid_hs_mask = []

        for idx in hs_indices:
            if idx >= len(pressure_data):
                foot_centers.append((np.nan, np.nan))
                valid_hs_mask.append(False)
                continue

            frame = pressure_data[idx]
            center = self.extract_foot_geometric_center(frame)
            foot_centers.append(center)

            # 标记是否有效
            valid_hs_mask.append(not (np.isnan(center[0]) or np.isnan(center[1])))

        valid_hs_mask = np.array(valid_hs_mask)

        if valid_hs_mask.sum() < 2:
            print("   ⚠️  有效足迹中心点不足2个，无法计算投影步长")
            return {
                'left_step_lengths': [],
                'right_step_lengths': [],
                'left_mean_step_length': 0,
                'right_mean_step_length': 0,
                'mean_step_length': 0,
                'step_length_asymmetry_percent': 0,
                'walking_speed': 0,
                'projection_info': None,
                'pca_info': None
            }

        # 2. PCA计算行走轴
        pca_result = self.calculate_walkway_axis_pca(foot_centers)
        u_hat = np.array(pca_result['u_hat'])

        # 使用第一个有效HS位置作为投影参考点（而非PCA中心）
        first_valid_idx = np.where(valid_hs_mask)[0][0]
        c_0 = np.array(foot_centers[first_valid_idx])

        print(f"   📐 PCA行走轴: u_hat=({u_hat[0]:.3f}, {u_hat[1]:.3f}), "
              f"解释方差={pca_result['pca_explained_variance']*100:.1f}%")
        print(f"   🎯 投影参考点: 第一个HS位置 c_0=({c_0[0]:.3f}, {c_0[1]:.3f})m")

        # 3. 投影到主轴（相对于第一个HS）
        projections = []
        for center in foot_centers:
            if np.isnan(center[0]) or np.isnan(center[1]):
                projections.append(np.nan)
            else:
                c_k = np.array(center)
                s_k = np.dot(c_k - c_0, u_hat)
                projections.append(s_k)

        projections = np.array(projections)

        # 4. 端部剔除（可选，默认禁用）
        if self.use_endpoint_trimming:
            # 计算每段的投影范围并剔除端部
            min_proj = np.nanmin(projections)
            max_proj = np.nanmax(projections)

            # 剔除每段的前后0.3m
            trim_min = min_proj + self.endpoint_trim_m
            trim_max = max_proj - self.endpoint_trim_m

            valid_projection_mask = (
                valid_hs_mask &
                (projections >= trim_min) &
                (projections <= trim_max)
            )

            num_removed = len(hs_indices) - valid_projection_mask.sum()
            if num_removed > 0:
                print(f"   🔍 端部剔除: 移除{num_removed}个HS（前后各{self.endpoint_trim_m}m）")
        else:
            # 不做端部剔除，仅过滤有效数据
            valid_projection_mask = valid_hs_mask
            num_removed = len(hs_indices) - valid_projection_mask.sum()
            if num_removed > 0:
                print(f"   🔍 过滤无效数据: 移除{num_removed}个HS（足迹提取失败）")

        # 过滤后的数据
        valid_indices = np.where(valid_projection_mask)[0]
        if len(valid_indices) < 2:
            print("   ⚠️  端部剔除后有效HS不足2个，无法计算步长")
            return {
                'left_step_lengths': [],
                'right_step_lengths': [],
                'left_mean_step_length': 0,
                'right_mean_step_length': 0,
                'mean_step_length': 0,
                'step_length_asymmetry_percent': 0,
                'walking_speed': 0,
                'projection_info': {
                    'projections': projections,
                    'valid_mask': valid_projection_mask,
                    'num_removed': num_removed
                },
                'pca_info': pca_result
            }

        filtered_projections = projections[valid_projection_mask]
        filtered_labels = side_labels[valid_projection_mask]
        filtered_hs_indices = hs_indices[valid_projection_mask]

        # 5. 强制交替序列处理
        # 问题：v7.2只保证平衡(|#L-#R|≤1)，不保证交替(L-R-L-R)
        # 解决：跳过同侧连续HS，只在异侧转换时计算步长

        # 5.1 构建严格交替的HS子序列
        alternating_indices = [0]  # 总是包含第一个HS
        alternating_projections = [filtered_projections[0]]
        alternating_labels = [filtered_labels[0]]

        for i in range(1, len(filtered_labels)):
            # 只添加与上一个不同侧的HS
            if filtered_labels[i] != alternating_labels[-1]:
                alternating_indices.append(i)
                alternating_projections.append(filtered_projections[i])
                alternating_labels.append(filtered_labels[i])

        print(f"   🔀 交替序列: {len(filtered_labels)}个HS → {len(alternating_labels)}个交替HS")

        # 5.2 在交替序列上计算步长
        left_step_lengths = []
        right_step_lengths = []

        for i in range(1, len(alternating_projections)):
            # 现在保证prev和curr是异侧
            step_length = abs(alternating_projections[i] - alternating_projections[i - 1])

            # 6. 步长过滤：这是主要的质量控制手段
            if self.step_length_min <= step_length <= self.step_length_max:
                if alternating_labels[i] == 0:  # 当前左脚
                    left_step_lengths.append(step_length)
                else:  # 当前右脚
                    right_step_lengths.append(step_length)

        # 7. 统计结果
        left_mean = np.mean(left_step_lengths) if len(left_step_lengths) > 0 else 0
        right_mean = np.mean(right_step_lengths) if len(right_step_lengths) > 0 else 0

        all_step_lengths = left_step_lengths + right_step_lengths
        mean_step_length = np.mean(all_step_lengths) if len(all_step_lengths) > 0 else 0

        # 不对称率
        if left_mean > 0 and right_mean > 0:
            asymmetry = abs(left_mean - right_mean) / mean_step_length * 100
        else:
            asymmetry = 0

        # 步速（基于步长总和，而非净位移）
        # 原因：往返行走中净位移接近0，但实际走了很长距离
        if len(all_step_lengths) > 0 and len(alternating_indices) > 1:
            total_distance_walked = sum(all_step_lengths)  # 所有步长之和
            # 使用交替序列的时间范围
            first_idx = filtered_hs_indices[alternating_indices[0]]
            last_idx = filtered_hs_indices[alternating_indices[-1]]
            total_time = time_array[last_idx] - time_array[first_idx]
            walking_speed = total_distance_walked / total_time if total_time > 0 else 0
        else:
            walking_speed = 0

        print(f"   📏 投影法步长: 左={left_mean*100:.1f}cm（{len(left_step_lengths)}步），"
              f"右={right_mean*100:.1f}cm（{len(right_step_lengths)}步），"
              f"不对称={asymmetry:.1f}%")
        print(f"   🚶 步速: {walking_speed:.2f}m/s")

        return {
            'left_step_lengths': left_step_lengths,
            'right_step_lengths': right_step_lengths,
            'left_mean_step_length': left_mean,
            'right_mean_step_length': right_mean,
            'mean_step_length': mean_step_length,
            'step_length_asymmetry_percent': asymmetry,
            'walking_speed': walking_speed,
            'projection_info': {
                'projections': projections,
                'valid_mask': valid_projection_mask,
                'num_removed': num_removed,
                'filtered_projections': filtered_projections,
                'filtered_labels': filtered_labels
            },
            'pca_info': pca_result
        }

    def analyze_gait_complete_v74(self, pressure_data, time_array,
                                  manual_distance=None, estimated_traversals=None,
                                  min_separation=0.38, use_projection=True):
        """
        v7.4完整步态分析（一站式接口）

        参数:
            pressure_data: (N, 64, 32) 压力数据
            time_array: (N,) 时间数组（秒）
            manual_distance: 手动输入的真实总距离（米），优先使用（仅均分法）
            estimated_traversals: 估算的往返次数（可选，仅均分法）
            min_separation: 最小分离时间（秒）
            use_projection: 是否使用投影法（默认True），False则使用v7.2均分法

        返回:
            dict: 完整的步态分析结果 + v7.4投影法结果
        """
        # 1. 双支路HS检测 + 左右脚分离（v7.2三层修正）
        result = self.detect_gait_events_dual_branch_v72(
            pressure_data, time_array, min_separation
        )

        # 2. 提取左右脚标签
        hs_indices = result['hs_indices']
        left_hs_indices = result['left_hs_indices']
        right_hs_indices = result['right_hs_indices']

        # 构建标签数组（0=左，1=右）
        side_labels = np.zeros(len(hs_indices), dtype=int)
        for i, idx in enumerate(hs_indices):
            if idx in right_hs_indices:
                side_labels[i] = 1

        # 3. 选择步长计算方法
        if use_projection:
            print("   🎯 使用v7.4足迹投影法计算步长")
            projection_result = self.calculate_step_length_projection(
                pressure_data, hs_indices, side_labels, time_array
            )

            # 更新结果
            result['left_step_length'] = projection_result['left_mean_step_length']
            result['right_step_length'] = projection_result['right_mean_step_length']
            result['mean_step_length'] = projection_result['mean_step_length']
            result['step_length_asymmetry_percent'] = projection_result['step_length_asymmetry_percent']
            result['walking_speed'] = projection_result['walking_speed']
            result['step_length_method'] = f'投影法（L={len(projection_result["left_step_lengths"])}步, R={len(projection_result["right_step_lengths"])}步）'
            result['v74_projection'] = projection_result
            result['distance_source'] = 'PCA投影计算'
        else:
            print("   📊 使用v7.2均分法计算步长")
            # 使用v7.2的方法
            correction = self.calculate_corrected_step_length_lr(
                result, manual_distance, estimated_traversals
            )
            result.update(correction)

        # 4. 四级评价
        result['walking_speed_evaluation'] = self.evaluate_four_levels(
            result['walking_speed'], [1.2, 1.0, 0.8], reverse=False
        )

        result['step_length_evaluation'] = self.evaluate_four_levels(
            result['mean_step_length'], [0.60, 0.50, 0.40], reverse=False
        )

        result['gait_symmetry_evaluation'] = self.evaluate_four_levels(
            result['gait_cycle_symmetry_percent'], [95, 90, 85], reverse=False
        )

        result['step_asymmetry_evaluation'] = self.evaluate_four_levels(
            result['step_length_asymmetry_percent'], [5, 10, 20], reverse=True
        )

        return result

    # 主接口别名（兼容性）
    def analyze_gait_complete(self, pressure_data, time_array,
                              manual_distance=None, estimated_traversals=None,
                              min_separation=0.38, use_projection=True):
        """主接口（调用v7.4版本）"""
        return self.analyze_gait_complete_v74(
            pressure_data, time_array, manual_distance,
            estimated_traversals, min_separation, use_projection
        )


if __name__ == "__main__":
    """
    使用示例和测试
    """
    print("GemSage增强版步态分析器 v7.4")
    print("=" * 80)
    print()
    print("v7.4新增功能：")
    print("1. 足迹几何中心提取（阈值分割 + 连通域分析）")
    print("2. 行走轴PCA计算（所有足迹中心点主成分分析）")
    print("3. 步长投影法（足迹中心投影到主轴，异侧HS步长计算）")
    print("4. 端部剔除（保留投影范围[0.4m, 2.5m]）")
    print("5. 步长过滤（0.3-1.1m合理范围）")
    print()
    print("目标：真实左右脚步长分离，步长60-80cm，步速1.0-1.4m/s")
    print()
    print("使用方法：")
    print()
    print("# 初始化分析器")
    print("analyzer = EnhancedGaitAnalyzerV74()")
    print()
    print("# 加载数据")
    print("pressure_data, time_array = load_walk_data('walk.csv')")
    print()
    print("# 完整分析（v7.4投影法）")
    print("result = analyzer.analyze_gait_complete(")
    print("    pressure_data, time_array,")
    print("    use_projection=True  # 使用投影法")
    print(")")
    print()
    print("# 查看v7.4投影法结果")
    print("print(f\"左脚步长: {result['left_step_length']*100:.1f}cm\")")
    print("print(f\"右脚步长: {result['right_step_length']*100:.1f}cm\")")
    print("print(f\"步速: {result['walking_speed']:.2f}m/s\")")
    print()
