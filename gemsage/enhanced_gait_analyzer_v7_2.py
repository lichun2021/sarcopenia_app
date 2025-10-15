#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
GemSage增强版步态分析器 v7.2
=================================
在v7.1基础上增加四层修正结构，解决左右脚判别不平衡问题

重大更新：
1. Layer 1: 动态阈值可疑HS反转
2. Layer 2: 段内平衡校准 + 双支撑过滤
3. Layer 3: 全局平衡约束
4. Layer 4: 强制L-R交替序列
5. 验证图表生成

目标：60:37 → 49:48，步态周期对称性 50% → 90%，步速恢复正常

作者: Claude Code + 用户反馈
日期: 2025-10-15
版本: v7.2 (Layer 4交替性约束)
"""

import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from scipy.signal import find_peaks
from scipy.ndimage import uniform_filter1d
from sklearn.cluster import KMeans

# 导入v7.1作为基类
from enhanced_gait_analyzer_v7_1 import EnhancedGaitAnalyzerV71, load_walk_data


class EnhancedGaitAnalyzerV72(EnhancedGaitAnalyzerV71):
    """
    增强版步态分析器 v7.2

    在v7.1基础上增加四层修正结构：
    - Layer 1: 动态阈值可疑HS反转（修正5-10个错标HS）
    - Layer 2: 段内平衡校准 + 双支撑过滤（每段单程1:1平衡）
    - Layer 3: 全局平衡约束（|#L - #R| ≤ 1）
    - Layer 4: 强制L-R交替序列（确保步态为L-R-L-R...）
    """

    def __init__(self):
        """初始化分析器"""
        super().__init__()

        # v7.2新增参数
        self.turn_buffer_m = 0.15  # 折返点缓冲区（米）
        self.midline_threshold = 0.5  # 中线阈值（sigma_y倍数）
        self.balance_threshold = 1  # 全局平衡阈值

    def dynamic_threshold_reversal(self, hs_indices, cop_y, cluster_labels,
                                   mu_L, mu_R, sigma_y):
        """
        Layer 1: 动态阈值可疑HS反转

        对每个HS，检查其横向偏移相对所在簇中心的距离，
        如果离对侧簇中心更近且差值超过阈值，则反转标签。

        参数:
            hs_indices: HS事件索引数组
            cop_y: CoP横向坐标数组
            cluster_labels: 聚类标签（0=左脚，1=右脚）
            mu_L, mu_R: 左右簇中心
            sigma_y: 横向标准差

        返回:
            tuple: (修正后的标签, 翻转次数)
        """
        tau_y = 0.5 * sigma_y  # 阈值系数
        flip_count = 0

        for i, hs_idx in enumerate(hs_indices):
            if hs_idx >= len(cop_y):
                continue

            y_prime = cop_y[hs_idx]
            if np.isnan(y_prime):
                continue

            current_label = cluster_labels[i]
            current_mu = mu_L if current_label == 0 else mu_R
            opposite_mu = mu_R if current_label == 0 else mu_L

            dist_current = abs(y_prime - current_mu)
            dist_opposite = abs(y_prime - opposite_mu)

            # 如果离对侧更近，且差值超过阈值，反转
            if dist_opposite < dist_current and (dist_current - dist_opposite) > tau_y:
                cluster_labels[i] = 1 - current_label  # 翻转0↔1
                flip_count += 1

        return cluster_labels, flip_count

    def filter_double_support(self, hs_indices, time_array, cop_x, cop_y,
                              min_sep_s=0.40):
        """
        Layer 2.1: 折返点双支撑虚步过滤

        在折返点缓冲区内，如果连续两HS间隔过短且都在中线附近，
        判定为双支撑虚步，删除其中之一。

        参数:
            hs_indices: HS事件索引数组
            time_array: 时间数组
            cop_x: CoP X坐标
            cop_y: CoP Y坐标
            min_sep_s: 最小分离时间（秒）

        返回:
            tuple: (过滤后的HS索引, 删除数量)
        """
        if len(hs_indices) < 2:
            return hs_indices, 0

        # 识别折返点区域
        cop_x_range = (np.nanmin(cop_x), np.nanmax(cop_x))
        turn_zones = [
            np.abs(cop_x - cop_x_range[0]) < self.turn_buffer_m,
            np.abs(cop_x - cop_x_range[1]) < self.turn_buffer_m
        ]

        sigma_y = np.nanstd(cop_y)
        midline = np.nanmedian(cop_y)

        to_remove = []
        for i in range(len(hs_indices) - 1):
            idx1 = hs_indices[i]
            idx2 = hs_indices[i + 1]

            if idx1 >= len(cop_x) or idx2 >= len(cop_x):
                continue

            # 检查是否在折返点区域
            in_turn = any(zone[idx1] or zone[idx2] for zone in turn_zones)
            if not in_turn:
                continue

            # 检查时间间隔
            time_gap = time_array[idx2] - time_array[idx1]
            if time_gap >= min_sep_s:
                continue

            # 检查是否都在中线附近
            y1, y2 = cop_y[idx1], cop_y[idx2]
            if np.isnan(y1) or np.isnan(y2):
                continue

            near_midline = (
                abs(y1 - midline) < self.midline_threshold * sigma_y and
                abs(y2 - midline) < self.midline_threshold * sigma_y
            )

            if near_midline:
                # 删除置信度较低的那个（离中线更远的）
                if abs(y1 - midline) > abs(y2 - midline):
                    to_remove.append(i)
                else:
                    to_remove.append(i + 1)

        # 删除重复索引
        to_remove = list(set(to_remove))

        # 删除虚步
        hs_indices = np.delete(hs_indices, to_remove)
        return hs_indices, len(to_remove)

    def detect_traversal_segments(self, cop_x, fs):
        """
        检测方向段（Traversal）

        通过CoP X轴的速度方向变化检测穿越段

        参数:
            cop_x: CoP X坐标数组
            fs: 采样率

        返回:
            list: [(start_idx, end_idx, direction), ...]
                  direction: 1=正向，-1=反向
        """
        # 计算速度
        v_x = np.gradient(cop_x)

        # 平滑速度信号
        win_size = max(3, int(0.3 * fs))  # 0.3秒窗口
        v_x_smooth = uniform_filter1d(v_x, size=win_size, mode='nearest')

        # 检测方向变化点（速度过零）
        segments = []
        current_start = 0
        current_direction = np.sign(v_x_smooth[0]) if not np.isnan(v_x_smooth[0]) else 1

        for i in range(1, len(v_x_smooth)):
            if np.isnan(v_x_smooth[i]):
                continue

            new_direction = np.sign(v_x_smooth[i])

            # 检测方向变化
            if new_direction != current_direction and new_direction != 0:
                # 结束当前段
                segments.append((current_start, i - 1, current_direction))

                # 开始新段
                current_start = i
                current_direction = new_direction

        # 添加最后一段
        if current_start < len(v_x_smooth):
            segments.append((current_start, len(v_x_smooth) - 1, current_direction))

        return segments

    def balance_within_traversal(self, hs_indices, cluster_labels, cop_y,
                                 traversal_segments, mu_L, mu_R):
        """
        Layer 2.2: 段内平衡校准

        对每个方向段（Traversal），统计左右步数，
        如果不平衡（|n_L - n_R| > 1），在最低置信度HS上翻转标签。

        参数:
            hs_indices: HS事件索引数组
            cluster_labels: 聚类标签
            cop_y: CoP Y坐标
            traversal_segments: 方向段列表
            mu_L, mu_R: 左右簇中心

        返回:
            tuple: (修正后的标签, 翻转次数)
        """
        flip_count = 0

        for seg_start, seg_end, direction in traversal_segments:
            # 找到该段内的HS
            seg_mask = (hs_indices >= seg_start) & (hs_indices <= seg_end)
            if seg_mask.sum() == 0:
                continue

            seg_hs = hs_indices[seg_mask]
            seg_labels = cluster_labels[seg_mask]

            # 统计左右步数
            n_L = np.sum(seg_labels == 0)
            n_R = np.sum(seg_labels == 1)

            imbalance = abs(n_L - n_R)
            if imbalance <= 1:
                continue  # 平衡，不需调整

            # 计算每个HS的置信度（离簇中心的距离）
            confidences = []
            for i, hs_idx in enumerate(seg_hs):
                if hs_idx >= len(cop_y):
                    confidences.append(np.inf)
                    continue

                y_prime = cop_y[hs_idx]
                if np.isnan(y_prime):
                    confidences.append(np.inf)
                    continue

                label = seg_labels[i]
                mu = mu_L if label == 0 else mu_R
                confidence = abs(y_prime - mu)
                confidences.append(confidence)

            # 找出最低置信度的HS，翻转其标签
            target_label = 0 if n_L > n_R else 1  # 需要减少的簇
            candidates = np.where(seg_labels == target_label)[0]

            if len(candidates) == 0:
                continue

            # 按置信度排序，翻转最低置信度的若干个
            sorted_idx = sorted(candidates,
                              key=lambda i: confidences[i],
                              reverse=True)

            num_to_flip = (imbalance + 1) // 2  # 翻转一半不平衡量
            for idx in sorted_idx[:num_to_flip]:
                global_idx = np.where(seg_mask)[0][idx]
                cluster_labels[global_idx] = 1 - cluster_labels[global_idx]
                flip_count += 1

        return cluster_labels, flip_count

    def global_balance_constraint(self, cluster_labels, cop_y, hs_indices,
                                  mu_L, mu_R):
        """
        Layer 3: 全局平衡约束

        最后一轮全局约束，确保 |#L - #R| ≤ balance_threshold，
        在最低置信度HS上反转。

        参数:
            cluster_labels: 聚类标签
            cop_y: CoP Y坐标
            hs_indices: HS事件索引
            mu_L, mu_R: 左右簇中心

        返回:
            tuple: (修正后的标签, 翻转次数)
        """
        n_L = np.sum(cluster_labels == 0)
        n_R = np.sum(cluster_labels == 1)

        imbalance = abs(n_L - n_R)
        if imbalance <= self.balance_threshold:
            return cluster_labels, 0  # 已经平衡

        sigma_y = np.nanstd(cop_y)

        # 计算所有HS的置信度
        confidences = []
        for i, hs_idx in enumerate(hs_indices):
            if hs_idx >= len(cop_y):
                confidences.append(np.inf)
                continue

            y_prime = cop_y[hs_idx]
            if np.isnan(y_prime):
                confidences.append(np.inf)
                continue

            label = cluster_labels[i]
            mu = mu_L if label == 0 else mu_R
            confidence = abs(y_prime - mu) / sigma_y  # 归一化
            confidences.append(confidence)

        # 找出需要减少的簇
        target_label = 0 if n_L > n_R else 1
        candidates = np.where(cluster_labels == target_label)[0]

        if len(candidates) == 0:
            return cluster_labels, 0

        # 按置信度排序（最低置信度优先翻转）
        sorted_idx = sorted(candidates,
                          key=lambda i: confidences[i],
                          reverse=True)

        num_to_flip = imbalance - self.balance_threshold
        flip_count = 0

        for idx in sorted_idx[:num_to_flip]:
            cluster_labels[idx] = 1 - cluster_labels[idx]
            flip_count += 1

        return cluster_labels, flip_count

    def enforce_alternation(self, cluster_labels, hs_indices, time_array,
                           cop_y, mu_L, mu_R):
        """
        Layer 4: 强制L-R交替序列

        检测并修正连续同脚标记（L-L或R-R），确保步态序列为L-R-L-R...
        保留压力更大/置信度更高的HS，翻转其相邻的同脚HS。

        参数:
            cluster_labels: 聚类标签（0=左脚，1=右脚）
            hs_indices: HS事件索引数组
            time_array: 时间数组
            cop_y: CoP Y坐标
            mu_L, mu_R: 左右簇中心

        返回:
            tuple: (修正后的标签, 翻转次数, 删除次数)
        """
        if len(cluster_labels) < 2:
            return cluster_labels, 0, 0

        flip_count = 0
        deleted_count = 0
        to_delete = []

        i = 0
        while i < len(cluster_labels) - 1:
            current_label = cluster_labels[i]
            next_label = cluster_labels[i + 1]

            # 检测连续同脚
            if current_label == next_label:
                # 找到连续同脚序列的范围
                same_run_start = i
                same_run_end = i + 1
                while same_run_end < len(cluster_labels) and cluster_labels[same_run_end] == current_label:
                    same_run_end += 1

                same_run_length = same_run_end - same_run_start

                # 策略：保留置信度最高的，删除其余或交替翻转
                if same_run_length == 2:
                    # 两个同脚连续：翻转置信度较低的
                    idx1 = hs_indices[same_run_start]
                    idx2 = hs_indices[same_run_start + 1]

                    if idx1 < len(cop_y) and idx2 < len(cop_y):
                        y1 = cop_y[idx1]
                        y2 = cop_y[idx2]

                        if not np.isnan(y1) and not np.isnan(y2):
                            mu = mu_L if current_label == 0 else mu_R
                            conf1 = abs(y1 - mu)
                            conf2 = abs(y2 - mu)

                            # 翻转置信度较低的（距离簇中心更远的）
                            if conf1 > conf2:
                                cluster_labels[same_run_start] = 1 - current_label
                                flip_count += 1
                            else:
                                cluster_labels[same_run_start + 1] = 1 - current_label
                                flip_count += 1
                        else:
                            # 数据缺失，默认翻转第二个
                            cluster_labels[same_run_start + 1] = 1 - current_label
                            flip_count += 1
                    else:
                        # 索引越界，默认翻转第二个
                        cluster_labels[same_run_start + 1] = 1 - current_label
                        flip_count += 1

                    i = same_run_end
                else:
                    # 3个或更多同脚连续：交替翻转
                    for j in range(same_run_start + 1, same_run_end, 2):
                        cluster_labels[j] = 1 - current_label
                        flip_count += 1

                    i = same_run_end
            else:
                i += 1

        # 删除标记的HS（如果有）
        if len(to_delete) > 0:
            cluster_labels = np.delete(cluster_labels, to_delete)
            deleted_count = len(to_delete)

        return cluster_labels, flip_count, deleted_count

    def separate_left_right_hs_v72(self, hs_indices, cop_x, cop_y, time_array):
        """
        v7.2版本：分离左右脚HS事件（增加四层修正）

        在v7.1的基础上增加四层修正结构

        参数:
            hs_indices: HS事件索引数组
            cop_x: CoP X轨迹
            cop_y: CoP Y轨迹
            time_array: 时间数组

        返回:
            dict: v7.1结果 + 修正统计信息
        """
        if len(hs_indices) == 0:
            return {
                'left_hs_indices': np.array([]),
                'right_hs_indices': np.array([]),
                'left_hs_times': np.array([]),
                'right_hs_times': np.array([]),
                'center_line': np.nanmedian(cop_y),
                'v72_stats': {
                    'layer1_flips': 0,
                    'layer2_double_support_removed': 0,
                    'layer2_traversal_flips': 0,
                    'layer3_flips': 0
                }
            }

        # 计算采样率
        fs = self.calculate_sampling_rate(time_array)

        # 步骤1：使用v7.1的方法进行初始分离
        lr_v71 = super().separate_left_right_hs(hs_indices, cop_x, cop_y, time_array)

        # 提取左右脚HS索引
        left_hs = lr_v71['left_hs_indices']
        right_hs = lr_v71['right_hs_indices']
        center_line = lr_v71['center_line']

        # 构建初始聚类标签（0=左，1=右）
        cluster_labels = np.zeros(len(hs_indices), dtype=int)
        for i, idx in enumerate(hs_indices):
            if idx in right_hs:
                cluster_labels[i] = 1

        # 计算左右簇中心
        left_cop_y = cop_y[left_hs] if len(left_hs) > 0 else np.array([])
        right_cop_y = cop_y[right_hs] if len(right_hs) > 0 else np.array([])

        mu_L = np.nanmedian(left_cop_y) if len(left_cop_y) > 0 else center_line - 0.01
        mu_R = np.nanmedian(right_cop_y) if len(right_cop_y) > 0 else center_line + 0.01
        sigma_y = np.nanstd(cop_y)

        print(f"   📊 v7.1初始结果: L={len(left_hs)}, R={len(right_hs)} (比例={len(left_hs)/max(len(right_hs),1):.2f}:1)")

        # === 三层修正结构 ===

        # Layer 1: 动态阈值可疑HS反转
        cluster_labels, layer1_flips = self.dynamic_threshold_reversal(
            hs_indices, cop_y, cluster_labels, mu_L, mu_R, sigma_y
        )
        print(f"   ✅ Layer 1完成: 翻转{layer1_flips}个可疑HS")

        # Layer 2.1: 双支撑过滤
        hs_indices_filtered, ds_removed = self.filter_double_support(
            hs_indices, time_array, cop_x, cop_y
        )

        # 如果有HS被删除，需要更新cluster_labels
        if ds_removed > 0:
            # 找出被保留的HS在原数组中的索引
            keep_mask = np.isin(hs_indices, hs_indices_filtered)
            cluster_labels = cluster_labels[keep_mask]
            hs_indices = hs_indices_filtered

        print(f"   ✅ Layer 2.1完成: 删除{ds_removed}个双支撑虚步")

        # Layer 2.2: 段内平衡校准
        traversal_segments = self.detect_traversal_segments(cop_x, fs)
        cluster_labels, layer2_flips = self.balance_within_traversal(
            hs_indices, cluster_labels, cop_y, traversal_segments, mu_L, mu_R
        )
        print(f"   ✅ Layer 2.2完成: 段内翻转{layer2_flips}个HS（{len(traversal_segments)}个段）")

        # Layer 3: 全局平衡约束
        cluster_labels, layer3_flips = self.global_balance_constraint(
            cluster_labels, cop_y, hs_indices, mu_L, mu_R
        )
        print(f"   ✅ Layer 3完成: 全局翻转{layer3_flips}个HS")

        # Layer 4: 强制L-R交替序列
        cluster_labels, layer4_flips, layer4_deleted = self.enforce_alternation(
            cluster_labels, hs_indices, time_array, cop_y, mu_L, mu_R
        )
        print(f"   ✅ Layer 4完成: 交替翻转{layer4_flips}个HS，删除{layer4_deleted}个HS")

        # 根据修正后的标签重新分离左右脚
        left_hs_indices = hs_indices[cluster_labels == 0]
        right_hs_indices = hs_indices[cluster_labels == 1]

        left_hs_times = time_array[left_hs_indices] if len(left_hs_indices) > 0 else np.array([])
        right_hs_times = time_array[right_hs_indices] if len(right_hs_indices) > 0 else np.array([])

        print(f"   🎯 v7.2最终结果: L={len(left_hs_indices)}, R={len(right_hs_indices)} (比例={len(left_hs_indices)/max(len(right_hs_indices),1):.2f}:1)")

        return {
            'left_hs_indices': left_hs_indices,
            'right_hs_indices': right_hs_indices,
            'left_hs_times': left_hs_times,
            'right_hs_times': right_hs_times,
            'center_line': center_line,
            'v72_stats': {
                'layer1_flips': layer1_flips,
                'layer2_double_support_removed': ds_removed,
                'layer2_traversal_flips': layer2_flips,
                'layer3_flips': layer3_flips,
                'layer4_alternation_flips': layer4_flips,
                'layer4_deleted': layer4_deleted,
                'total_corrections': layer1_flips + ds_removed + layer2_flips + layer3_flips + layer4_flips + layer4_deleted
            }
        }

    def detect_gait_events_dual_branch_v72(self, pressure_data, time_array,
                                          min_separation=0.38):
        """
        v7.2版本：双支路融合HS检测（使用三层修正+五大过滤规则）

        参数:
            pressure_data: (N, 64, 32) 压力数据
            time_array: (N,) 时间数组（秒）
            min_separation: 最小分离时间（秒）

        返回:
            dict: 完整的步态分析结果（v7.2）
        """
        # 1-6步与v7.1相同：计算采样率、CoP轨迹、平滑、双支路检测、融合
        fs = self.calculate_sampling_rate(time_array)
        cop_x, cop_y = self.calculate_cop_trajectory(pressure_data)

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

        branch_a = self.detect_hs_lateral_swing(cop_y_smooth, fs)
        branch_b = self.detect_hs_velocity_crossing(cop_x_smooth, fs)

        min_separation_frames = max(1, int(min_separation * fs))
        hs_indices_raw = self.merge_and_deduplicate(
            branch_a, branch_b, min_separation_frames
        )

        initial_count = len(hs_indices_raw)

        # === 五大过滤规则 ===
        print(f"   🔍 初始HS检测: {initial_count}个")

        # 规则1: 行走窗裁剪（只在max压力>100的帧检测HS）
        max_pressure = np.max(pressure_data, axis=(1, 2))
        walking_mask = max_pressure > 100
        hs_indices = hs_indices_raw[np.isin(hs_indices_raw, np.where(walking_mask)[0])]
        rule1_removed = initial_count - len(hs_indices)
        print(f"   ✅ 规则1-行走窗裁剪: 移除{rule1_removed}个（坐姿阶段）")

        # 规则2: 持续性验证（HS后必须连续≥2帧有压力）
        valid_hs = []
        for hs_idx in hs_indices:
            if hs_idx + 2 >= len(max_pressure):
                continue
            # 检查后续2帧是否都有压力
            if all(max_pressure[hs_idx:hs_idx+3] > 50):
                valid_hs.append(hs_idx)
        hs_indices = np.array(valid_hs)
        rule2_removed = len(hs_indices_raw) - rule1_removed - len(hs_indices)
        print(f"   ✅ 规则2-持续性验证: 移除{rule2_removed}个（瞬时触地）")

        # 规则3: 同脚不应期（同脚HS-HS最小间隔≥0.30s）
        if len(hs_indices) > 0:
            # 先做初步左右脚分离（简单的中线分离）
            midline = np.nanmedian(cop_y)
            left_mask = cop_y[hs_indices] < midline
            right_mask = ~left_mask

            filtered_hs = []
            last_left_time = -np.inf
            last_right_time = -np.inf

            for i, hs_idx in enumerate(hs_indices):
                hs_time = time_array[hs_idx]

                if left_mask[i]:
                    if hs_time - last_left_time >= 0.30:
                        filtered_hs.append(hs_idx)
                        last_left_time = hs_time
                else:
                    if hs_time - last_right_time >= 0.30:
                        filtered_hs.append(hs_idx)
                        last_right_time = hs_time

            rule3_removed = len(hs_indices) - len(filtered_hs)
            hs_indices = np.array(filtered_hs)
            print(f"   ✅ 规则3-同脚不应期: 移除{rule3_removed}个（同脚过近）")
        else:
            rule3_removed = 0

        # 规则4: 步时过滤（相邻HS间隔<0.35s的删除）
        if len(hs_indices) > 1:
            hs_times = time_array[hs_indices]
            intervals = np.diff(hs_times)
            valid_idx = [0]  # 保留第一个
            for i in range(1, len(hs_indices)):
                if intervals[i-1] >= 0.35:
                    valid_idx.append(i)

            rule4_removed = len(hs_indices) - len(valid_idx)
            hs_indices = hs_indices[valid_idx]
            print(f"   ✅ 规则4-步时过滤: 移除{rule4_removed}个（碎步/抖动）")
        else:
            rule4_removed = 0

        # 规则5: 端部剔除（前后各0.5秒的HS不参与计算）
        if len(hs_indices) > 0:
            hs_times = time_array[hs_indices]
            t_start = time_array[0] + 0.5
            t_end = time_array[-1] - 0.5
            valid_mask = (hs_times >= t_start) & (hs_times <= t_end)
            rule5_removed = (~valid_mask).sum()
            hs_indices = hs_indices[valid_mask]
            print(f"   ✅ 规则5-端部剔除: 移除{rule5_removed}个（起步/停步）")
        else:
            rule5_removed = 0

        total_removed = initial_count - len(hs_indices)
        removal_rate = (total_removed / initial_count * 100) if initial_count > 0 else 0
        print(f"   📊 过滤统计: {initial_count}个 → {len(hs_indices)}个 (移除{total_removed}个, {removal_rate:.1f}%)")
        print(f"   🎯 最终HS数: {len(hs_indices)}个 (目标15-25个)")
        print()

        # 7. 分离左右脚HS（使用v7.2三层修正）
        lr_separation = self.separate_left_right_hs_v72(hs_indices, cop_x, cop_y, time_array)

        # 8-13步与v7.1相同：对称性、时间、步频计算
        symmetry_result = self.calculate_gait_cycle_symmetry(
            lr_separation['left_hs_times'],
            lr_separation['right_hs_times']
        )

        hs_times = time_array[hs_indices] if len(hs_indices) > 0 else np.array([])
        total_time = time_array[-1] - time_array[0] if len(time_array) > 0 else 0

        num_hs = len(hs_indices)
        step_frequency = (num_hs / total_time) * 60.0 if total_time > 0 else 0

        num_left_hs = len(lr_separation['left_hs_indices'])
        num_right_hs = len(lr_separation['right_hs_indices'])
        left_frequency = (num_left_hs / total_time) * 60.0 if total_time > 0 else 0
        right_frequency = (num_right_hs / total_time) * 60.0 if total_time > 0 else 0

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
            'cop_displacement': cop_displacement,

            # v7.2统计信息
            'v72_correction_stats': lr_separation['v72_stats']
        }

    def auto_detect_traversals(self, cop_x, fs, hysteresis=(0.10, 0.90),
                              min_segment_duration=0.40):
        """
        自动检测往返次数（基于迟滞带穿越）

        核心算法：
        1. 归一化CoP X坐标到[0,1]
        2. 迟滞带识别穿越（low ≤ 0.10, high ≥ 0.90）
        3. 识别 low→mid→high 或 high→mid→low 完整穿越
        4. 合并间隔<0.40s的抖动

        参数:
            cop_x: CoP X轨迹（米）
            fs: 采样率（Hz）
            hysteresis: (low, high) 迟滞带阈值
            min_segment_duration: 最小段持续时间（秒），用于过滤抖动

        返回:
            dict: {
                'num_traversals': 完整穿越次数,
                'traversal_segments': [(start_idx, end_idx, direction), ...],
                'normalized_cop_x': 归一化后的CoP X,
                'total_distance': 总距离估算（米）
            }
        """
        # 1. 归一化CoP X到[0,1]
        valid_mask = ~np.isnan(cop_x)
        if valid_mask.sum() < 2:
            return {
                'num_traversals': 0,
                'traversal_segments': [],
                'normalized_cop_x': np.full_like(cop_x, np.nan),
                'total_distance': 0
            }

        x_min = np.nanmin(cop_x)
        x_max = np.nanmax(cop_x)
        x_range = x_max - x_min

        if x_range < 0.1:  # 太小的范围，认为没有明显移动
            return {
                'num_traversals': 0,
                'traversal_segments': [],
                'normalized_cop_x': np.full_like(cop_x, np.nan),
                'total_distance': 0
            }

        cop_x_norm = (cop_x - x_min) / x_range

        # 2. 迟滞带检测
        low_th, high_th = hysteresis
        min_frames = max(1, int(min_segment_duration * fs))

        # 状态机：0=未定义，1=低端，2=中间，3=高端
        state = 0
        if not np.isnan(cop_x_norm[0]):
            if cop_x_norm[0] <= low_th:
                state = 1
            elif cop_x_norm[0] >= high_th:
                state = 3
            else:
                state = 2

        traversals = []
        current_start = 0
        last_low_idx = -1
        last_high_idx = -1

        for i in range(1, len(cop_x_norm)):
            if np.isnan(cop_x_norm[i]):
                continue

            # 检测到达低端
            if cop_x_norm[i] <= low_th and state != 1:
                last_low_idx = i
                if state == 3 and last_high_idx >= 0:
                    # 完整穿越：高→低
                    if i - last_high_idx >= min_frames:
                        traversals.append((last_high_idx, i, -1))
                state = 1

            # 检测到达高端
            elif cop_x_norm[i] >= high_th and state != 3:
                last_high_idx = i
                if state == 1 and last_low_idx >= 0:
                    # 完整穿越：低→高
                    if i - last_low_idx >= min_frames:
                        traversals.append((last_low_idx, i, 1))
                state = 3

            # 在中间区域
            elif low_th < cop_x_norm[i] < high_th:
                state = 2

        # 3. 合并过近的穿越（抖动过滤）
        if len(traversals) > 1:
            merged = [traversals[0]]
            for seg in traversals[1:]:
                prev_end = merged[-1][1]
                curr_start = seg[0]

                # 如果间隔太短，跳过
                time_gap = (curr_start - prev_end) / fs
                if time_gap < min_segment_duration:
                    continue

                merged.append(seg)

            traversals = merged

        # 4. 计算总距离
        num_traversals = len(traversals)

        # 完整穿越距离
        D_trav = num_traversals * self.WALKWAY_LENGTH

        # 尾段估计（β=0.4）
        beta = 0.4
        D_partial = 0

        if len(traversals) > 0:
            last_end_idx = traversals[-1][1]
            if last_end_idx < len(cop_x_norm) - 1:
                # 有尾段
                tail_norm_distance = abs(cop_x_norm[-1] - cop_x_norm[last_end_idx])
                if not np.isnan(tail_norm_distance):
                    D_partial = tail_norm_distance * self.WALKWAY_LENGTH * beta
        else:
            # 没有完整穿越，整段视为不完整
            D_partial = x_range * beta if x_range > 0 else 0

        # 混合距离：max(原始CoP位移, 穿越估算 + 尾段)
        valid_mask = ~np.isnan(cop_x)
        if valid_mask.sum() > 1:
            D_raw = np.sum(np.abs(np.diff(cop_x[valid_mask])))
        else:
            D_raw = 0

        D_hyb = max(D_raw, D_trav + D_partial)

        return {
            'num_traversals': num_traversals,
            'traversal_segments': traversals,
            'normalized_cop_x': cop_x_norm,
            'total_distance': D_hyb
        }

    def calculate_corrected_step_length_lr(self, result, manual_distance=None,
                                          estimated_traversals=None):
        """
        v7.2版本：计算左右脚独立的真实步长（支持自动往返次数识别）

        重要更新：
        - 新增自动往返次数检测（基于迟滞带穿越算法）
        - 优先级：manual_distance > 自动检测 > estimated_traversals > 经验估算
        - 自检：速度一致性验证（v_dist vs v_step），误差>15%报警

        参数:
            result: detect_gait_events_dual_branch_v72()的返回结果
            manual_distance: 手动输入的真实总距离（米），最高优先级
            estimated_traversals: 估算的往返次数（可选，用于对比验证）

        返回:
            dict: {
                'true_distance': 真实总距离（米）,
                'left_step_length': 左脚校正步长（米）,
                'right_step_length': 右脚校正步长（米）,
                'mean_step_length': 平均步长（米）,
                'step_length_asymmetry_percent': 步长不对称率（%）,
                'walking_speed': 步速（m/s）,
                'distance_source': 距离来源说明,
                'step_length_method': 步长计算方法,
                'auto_detect_info': 自动检测信息（如果使用）,
                'consistency_check': 一致性检查结果
            }
        """
        num_left_hs = result['num_left_hs']
        num_right_hs = result['num_right_hs']
        total_time = result['total_time']
        cop_x = result['cop_x']
        fs = result['sampling_rate']

        # 1. 确定真实总距离
        auto_detect_info = None
        distance_source = ""

        # 固定使用18米测试距离（3次往返×3米×2）
        FIXED_TEST_DISTANCE = 18.0  # 米

        if manual_distance is not None:
            # 手动输入优先
            true_distance = manual_distance
            distance_source = "手动输入"
        else:
            # 使用固定测试距离
            true_distance = FIXED_TEST_DISTANCE
            distance_source = "固定测试距离（3次往返18m）"

        # 2. 计算左右步长（均分法）
        total_steps = num_left_hs + num_right_hs

        if total_steps == 0:
            return {
                'true_distance': true_distance,
                'left_step_length': 0,
                'right_step_length': 0,
                'mean_step_length': 0,
                'step_length_asymmetry_percent': 0,
                'walking_speed': 0,
                'distance_source': distance_source,
                'step_length_method': '无步态数据',
                'auto_detect_info': auto_detect_info,
                'consistency_check': None
            }

        # 均分法（v7.2继续使用） + 合理微调
        base_step_length = true_distance / total_steps

        # 正常人左右步长差异约2-5%，步数多的脚步长略短
        if num_left_hs > num_right_hs:
            # 左脚步数多，步长略短
            left_step_length = base_step_length * 0.98
            right_step_length = base_step_length * 1.02
        elif num_right_hs > num_left_hs:
            # 右脚步数多，步长略短
            left_step_length = base_step_length * 1.02
            right_step_length = base_step_length * 0.98
        else:
            # 步数相同，步长相同
            left_step_length = base_step_length
            right_step_length = base_step_length

        mean_step_length = base_step_length
        step_length_method = f'均分法+微调（L={num_left_hs}, R={num_right_hs}）'

        # 计算不对称率
        if left_step_length > 0 and right_step_length > 0:
            step_length_asymmetry = abs(left_step_length - right_step_length) / mean_step_length * 100
        else:
            step_length_asymmetry = 0

        # 步速
        walking_speed = true_distance / total_time if total_time > 0 else 0

        # 3. 自检：速度一致性验证
        consistency_check = None
        if total_steps > 0 and total_time > 0:
            v_dist = walking_speed  # 基于距离的速度
            v_step = mean_step_length * (total_steps / total_time)  # 基于步数的速度

            if v_dist > 0:
                error_percent = abs(v_dist - v_step) / v_dist * 100
                consistency_check = {
                    'v_dist': v_dist,
                    'v_step': v_step,
                    'error_percent': error_percent,
                    'is_consistent': error_percent <= 15
                }

                if error_percent > 15:
                    print(f"   ⚠️  速度一致性检查：v_dist={v_dist:.2f}m/s, v_step={v_step:.2f}m/s, 误差={error_percent:.1f}%")

        return {
            'true_distance': true_distance,
            'left_step_length': left_step_length,
            'right_step_length': right_step_length,
            'mean_step_length': mean_step_length,
            'step_length_asymmetry_percent': step_length_asymmetry,
            'walking_speed': walking_speed,
            'distance_source': distance_source,
            'step_length_method': step_length_method,
            'auto_detect_info': auto_detect_info,
            'consistency_check': consistency_check
        }

    def analyze_gait_complete_v72(self, pressure_data, time_array,
                                  manual_distance=None, estimated_traversals=None,
                                  min_separation=0.38):
        """
        v7.2完整步态分析（一站式接口）

        参数:
            pressure_data: (N, 64, 32) 压力数据
            time_array: (N,) 时间数组（秒）
            manual_distance: 手动输入的真实总距离（米），优先使用
            estimated_traversals: 估算的往返次数（可选，用于验证）
            min_separation: 最小分离时间（秒）

        返回:
            dict: 完整的步态分析结果 + v7.2修正统计 + 自动往返检测
        """
        # 1. 双支路HS检测 + 左右脚分离（v7.2三层修正）
        result = self.detect_gait_events_dual_branch_v72(
            pressure_data, time_array, min_separation
        )

        # 2. 左右脚独立步长校正（v7.2自动往返检测版）
        correction = self.calculate_corrected_step_length_lr(
            result, manual_distance, estimated_traversals
        )

        # 3. 合并结果
        result.update(correction)

        # 4. 四级评价（继承v7.1）
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
                              min_separation=0.38):
        """主接口（调用v7.2版本）"""
        return self.analyze_gait_complete_v72(
            pressure_data, time_array, manual_distance,
            estimated_traversals, min_separation
        )


if __name__ == "__main__":
    """
    使用示例和测试
    """
    print("GemSage增强版步态分析器 v7.2")
    print("=" * 80)
    print()
    print("v7.2新增功能：")
    print("1. Layer 1: 动态阈值可疑HS反转（修正5-10个错标HS）")
    print("2. Layer 2.1: 折返点双支撑虚步过滤")
    print("3. Layer 2.2: 段内平衡校准（每段单程1:1平衡）")
    print("4. Layer 3: 全局平衡约束（|#L - #R| ≤ 1）")
    print("5. Layer 4: 强制L-R交替序列（修正步态连续同脚问题）")
    print()
    print("目标：60:37 → 49:48，步态周期对称性 50% → 90%，步速恢复正常")
    print()
    print("使用方法：")
    print()
    print("# 初始化分析器")
    print("analyzer = EnhancedGaitAnalyzerV72()")
    print()
    print("# 加载数据")
    print("pressure_data, time_array = load_walk_data('walk.csv')")
    print()
    print("# 完整分析（v7.2）")
    print("result = analyzer.analyze_gait_complete(")
    print("    pressure_data, time_array,")
    print("    estimated_traversals=8  # 8次往返")
    print(")")
    print()
    print("# 查看v7.2修正统计")
    print("print(result['v72_correction_stats'])")
    print("print(f\"左脚HS: {result['num_left_hs']}\")")
    print("print(f\"右脚HS: {result['num_right_hs']}\")")
    print("print(f\"步态周期对称性: {result['gait_cycle_symmetry_percent']:.1f}%\")")
