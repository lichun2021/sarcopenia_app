#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
足部压力分析核心算法库 - 基于实际设备图的最终版本
设备规格：3.13米长 × 0.9米宽的单个压力垫
2025-08-12
"""

import numpy as np
import pandas as pd
from typing import Dict, List, Tuple, Optional, Any
import json
from pathlib import Path

class PressureAnalysisFinal:
    """压力分析核心计算引擎 - 最终版本"""
    
    def __init__(self):
        """初始化压力分析核心"""
        self._setup_hardware_final()
        # 统一的测试协议配置（参数化，避免硬编码在算法里）
        self.TEST_PROTOCOL = {
            'walkway': {
                'single_leg_distance_m': 4.5,   # 单程距离（可由外部修改）
                'round_trip': True              # 是否往返
            }
        }
    
    def _setup_hardware_final(self):
        """设置基于实际设备图的硬件参数"""
        # 实际设备尺寸（基于图纸）
        self.MAT_TOTAL_LENGTH = 3.13  # 总长度 3130mm = 3.13米  (前后/AP)
        self.MAT_EFFECTIVE_LENGTH = 2.913  # 有效长度 2913mm = 2.913米
        self.MAT_WIDTH = 0.9  # 宽度 900mm = 0.9米  (左右/ML)
        
        # 传感器配置
        self.SENSOR_GRID_SIZE = 32  # 32×32传感器阵列
        
        # 物理坐标比例（显式定义：x=AP(前后)、y=ML(左右)）
        self.GRID_SCALE_AP = self.MAT_EFFECTIVE_LENGTH / self.SENSOR_GRID_SIZE
        self.GRID_SCALE_ML = self.MAT_WIDTH / self.SENSOR_GRID_SIZE
        
        # 其他参数
        self.PRESSURE_THRESHOLD = 20  # 压力阈值
        self.SAMPLING_RATE = 30  # 30Hz采样率
        
        print(f"✅ 最终硬件配置（基于设备图）:")
        print(f"   - 设备总长(AP): {self.MAT_TOTAL_LENGTH}米")
        print(f"   - 有效感应长度(AP): {self.MAT_EFFECTIVE_LENGTH}米")
        print(f"   - 设备宽度(ML): {self.MAT_WIDTH}米")
        print(f"   - 传感器分辨率: AP={self.GRID_SCALE_AP*100:.1f}cm/格, ML={self.GRID_SCALE_ML*100:.1f}cm/格")
    
    def load_csv_data(self, file_path: str) -> Dict:
        """加载CSV数据，统一返回32×32帧列表"""
        try:
            df = pd.read_csv(file_path, header=None)
            
            # 肌少症6列格式
            if df.shape[1] == 6:
                df.columns = ['time', 'max_pressure', 'timestamp', 'contact_area', 'total_pressure', 'data']
                frames: List[List[List[float]]] = []
                for _, row in df.iterrows():
                    data_str = str(row['data']).strip()
                    if not data_str or data_str == 'nan':
                        continue
                    try:
                        data_str = data_str.strip('"').strip("'")
                        if data_str.startswith('[') and data_str.endswith(']'):
                            data_str = data_str[1:-1]
                        values = list(map(float, data_str.split(',')))
                        if len(values) >= 1024:
                            values = values[:1024]
                            matrix = np.array(values, dtype=float).reshape(32, 32)
                            frames.append(matrix.tolist())
                    except Exception:
                        continue
                return {
                    'format': 'sarcopenia_6_column',
                    'total_frames': len(frames),
                    'pressure_data': frames,
                    'metadata': {'duration': len(frames) / self.SAMPLING_RATE}
                }
            
            # 标准矩阵格式：每帧包含1024列或按行堆叠为32行×32列
            frames: List[List[List[float]]] = []
            data_values = df.values
            n_rows, n_cols = data_values.shape
            if n_cols >= 1024:
                # 每行即一帧（扁平）
                for r in range(n_rows):
                    vals = data_values[r, :1024].astype(float)
                    frames.append(vals.reshape(32, 32).tolist())
            elif n_cols in (32, 64):
                # 将连续32行拼一帧
                rows_per_frame = 32
                total_frames = n_rows // rows_per_frame
                for f in range(total_frames):
                    block = data_values[f*rows_per_frame:(f+1)*rows_per_frame, :32].astype(float)
                    if block.shape == (32, 32):
                        frames.append(block.tolist())
            else:
                # 无法识别时，尝试将每行按sqrt列数还原
                side = int(np.sqrt(n_cols))
                if side * side == n_cols:
                    for r in range(n_rows):
                        vals = data_values[r, :side*side].astype(float)
                        frames.append(vals.reshape(side, side).tolist())
                else:
                    return {'error': f'Unsupported CSV shape: {n_rows}x{n_cols}'}
            
            return {
                'format': 'standard_matrix',
                'total_frames': len(frames),
                'pressure_data': frames,
                'metadata': {'duration': len(frames) / self.SAMPLING_RATE}
            }
        except Exception as e:
            return {'error': f'Failed to load CSV: {str(e)}'}
    
    def calculate_cop_position(self, pressure_matrix: List[List[float]]) -> Optional[Dict]:
        """计算压力中心(COP)位置（x=AP, y=ML）。
        约定：列索引→AP(前后)，行索引→ML(左右)。与既有步长/速度计算保持一致。
        """
        matrix = np.array(pressure_matrix, dtype=float)
        mask = matrix > self.PRESSURE_THRESHOLD
        if not np.any(mask):
            return None
        total_pressure = float(matrix[mask].sum())
        # 列作为AP，行作为ML（与历史实现一致）
        ap_idx = np.arange(matrix.shape[1])  # 列 → AP
        ml_idx = np.arange(matrix.shape[0])  # 行 → ML
        ap_grid, ml_grid = np.meshgrid(ap_idx, ml_idx)
        x_ap = ap_grid * self.GRID_SCALE_AP
        y_ml = ml_grid * self.GRID_SCALE_ML
        x = float((x_ap[mask] * matrix[mask]).sum() / total_pressure)
        y = float((y_ml[mask] * matrix[mask]).sum() / total_pressure)
        return {'x': x, 'y': y, 'total_pressure': total_pressure}
    
    def _smooth(self, arr: np.ndarray, window_frames: int) -> np.ndarray:
        window_frames = max(1, int(window_frames))
        if window_frames <= 1 or arr.size == 0:
            return arr
        kernel = np.ones(window_frames) / window_frames
        return np.convolve(arr, kernel, mode='same')
    
    def _detect_events_1d(self, signal: np.ndarray) -> Tuple[List[int], List[int]]:
        """在一维压力序列上检测HS(峰)与TO(谷)的索引"""
        if signal.size < 5:
            return [], []
        s = signal.astype(float)
        s = self._smooth(s, max(3, int(0.2 * self.SAMPLING_RATE)))
        high = float(np.percentile(s, 70))
        low = float(np.percentile(s, 30))
        min_gap = max(2, int(0.4 * self.SAMPLING_RATE))
        hs: List[int] = []
        to: List[int] = []
        last = -10_000
        for i in range(1, len(s) - 1):
            if s[i] > s[i-1] and s[i] > s[i+1] and s[i] > high and (i - last) >= min_gap:
                hs.append(i); last = i
        last = -10_000
        for i in range(1, len(s) - 1):
            if s[i] < s[i-1] and s[i] < s[i+1] and s[i] < low and (i - last) >= min_gap:
                to.append(i); last = i
        return hs, to
    
    def detect_gait_events_final(self, pressure_data: List[List[List[float]]]) -> Dict[str, Any]:
        """检测事件：返回总序列与左右脚分离的HS/TO、COP轨迹等
        - 左右半区按列中线分割（列=ML）
        - 采用接触布尔序列（迟滞阈值）在左右侧分别检测 HS(上升沿) 与 TO(下降沿)
        """
        cop_trajectory = []
        total_pressures = []
        left_pressures = []
        right_pressures = []
        # 前掌/后跟分通道信号（左右）
        left_heel_pressures = []
        left_fore_pressures = []
        right_heel_pressures = []
        right_fore_pressures = []
        ml_bias = []
        for frame_idx, frame in enumerate(pressure_data):
            cop = self.calculate_cop_position(frame)
            if cop:
                cop['frame'] = frame_idx
                cop['time'] = frame_idx / self.SAMPLING_RATE
                cop_trajectory.append(cop)
                total_pressures.append(cop['total_pressure'])
                ml_bias.append(cop['y'])  # ML位置（米）
            else:
                ml_bias.append(0.0)
            # 先用几何中线按列(ML)分半区作为初判（列前半=左，列后半=右）
            m = np.array(frame, dtype=float)
            mid_col = m.shape[1] // 2
            left_region = m[:, :mid_col]
            right_region = m[:, mid_col:]
            left_pressures.append(float(np.sum(left_region)))
            right_pressures.append(float(np.sum(right_region)))
            # AP 方向按列切分前后（后跟=AP前1/3，前掌=AP后1/3）
            ap_cols = m.shape[1]
            third = max(1, ap_cols // 3)
            # 左侧
            left_heel_pressures.append(float(np.sum(left_region[:, :third])))
            left_fore_pressures.append(float(np.sum(left_region[:, -third:])))
            # 右侧
            right_heel_pressures.append(float(np.sum(right_region[:, :third])))
            right_fore_pressures.append(float(np.sum(right_region[:, -third:])))
        total_pressures = np.array(total_pressures, dtype=float)
        left_pressures = np.array(left_pressures, dtype=float)
        right_pressures = np.array(right_pressures, dtype=float)
        ml_bias = np.array(ml_bias, dtype=float)
        left_heel_pressures = np.array(left_heel_pressures, dtype=float)
        left_fore_pressures = np.array(left_fore_pressures, dtype=float)
        right_heel_pressures = np.array(right_heel_pressures, dtype=float)
        right_fore_pressures = np.array(right_fore_pressures, dtype=float)
        
        # 迟滞接触：高/低阈值（基于非零分位数，默认 high=0.85, low=0.65）
        def hysteresis_contact(sig: np.ndarray, high_q: float = 0.85, low_q: float = 0.65) -> np.ndarray:
            if sig.size == 0:
                return np.zeros(0, dtype=bool)
            s = self._smooth(sig, max(3, int(0.2 * self.SAMPLING_RATE)))
            nz = s[s > 0]
            if nz.size == 0:
                return np.zeros_like(s, dtype=bool)
            high = float(np.quantile(nz, high_q))
            low = float(np.quantile(nz, low_q))
            state = False
            out = np.zeros_like(s, dtype=bool)
            for i, v in enumerate(s):
                if not state and v >= high:
                    state = True
                elif state and v <= low:
                    state = False
                out[i] = state
            return out

        # 通道融合：前掌/后跟分别判定接触，最后用 OR 融合
        lh_c = hysteresis_contact(left_heel_pressures)
        lf_c = hysteresis_contact(left_fore_pressures)
        rh_c = hysteresis_contact(right_heel_pressures)
        rf_c = hysteresis_contact(right_fore_pressures)
        left_contact = lh_c | lf_c
        right_contact = rh_c | rf_c

        # 上升沿=HS，下降沿=TO（仅在对应侧接触变化时识别）
        from typing import Tuple
        def edges(contact: np.ndarray) -> Tuple[List[int], List[int]]:
            if contact.size == 0:
                return [], []
            prev = np.concatenate([[False], contact[:-1]])
            hs_idx = list(np.where((~prev) & contact)[0])
            to_idx = list(np.where(prev & (~contact))[0])
            return hs_idx, to_idx

        hs_left_idx, to_left_idx = edges(left_contact)
        hs_right_idx, to_right_idx = edges(right_contact)
        # 总序列用总压力峰谷辅助（非关键，仅供参考）
        hs_total, to_total = self._detect_events_1d(total_pressures)
        
        def index_to_events(indices: List[int]) -> List[Dict[str, float]]:
            ev = []
            for i in indices:
                if i < len(cop_trajectory):
                    ev.append({'frame': cop_trajectory[i]['frame'], 'time': cop_trajectory[i]['time'], 'x': cop_trajectory[i]['x'], 'y': cop_trajectory[i]['y']})
            return ev
        events = {
            'total': {'hs': index_to_events(hs_total), 'to': index_to_events(to_total)},
            'left': {'hs': index_to_events(hs_left_idx), 'to': index_to_events(to_left_idx)},
            'right': {'hs': index_to_events(hs_right_idx), 'to': index_to_events(to_right_idx)},
            'cop_trajectory': cop_trajectory,
            'total_pressure_smooth': self._smooth(total_pressures, max(3, int(0.2*self.SAMPLING_RATE))).tolist(),
            'left_contact': left_contact.tolist(),
            'right_contact': right_contact.tolist()
        }
        return events
    
    def _compute_phases_from_events(self, hs: List[Dict], to: List[Dict]) -> Tuple[float, float]:
        """基于事件的支撑/摆动相（同侧）平均百分比"""
        if len(hs) < 2 or len(to) == 0:
            return 62.0, 38.0
        stance_percentages = []
        for k in range(len(hs) - 1):
            hs_t = hs[k]['time']
            next_hs_t = hs[k+1]['time']
            # 找到此周期内的最近TO
            next_to = None
            for t in to:
                if hs_t < t['time'] < next_hs_t:
                    next_to = t
                    break
            if next_to is None:
                continue
            cycle = next_hs_t - hs_t
            stance = next_to['time'] - hs_t
            if 0.3 <= stance <= 1.5 and 0.4 <= cycle <= 2.5:
                stance_percentages.append((stance / cycle) * 100.0)
        if not stance_percentages:
            return 62.0, 38.0
        stance_pct = float(np.mean(stance_percentages))
        return stance_pct, 100.0 - stance_pct
    
    def _compute_double_support(self, left_hs: List[Dict], left_to: List[Dict], right_hs: List[Dict], right_to: List[Dict]) -> float:
        """平均双支撑百分比（两个支撑区间的重叠/周期）"""
        # 构建支撑区间
        def intervals(hs: List[Dict], to: List[Dict]) -> List[Tuple[float,float]]:
            iv = []
            for k in range(min(len(hs)-1, len(to))):
                if hs[k]['time'] < to[k]['time'] < hs[k+1]['time']:
                    iv.append((hs[k]['time'], to[k]['time']))
            return iv
        L = intervals(left_hs, left_to)
        R = intervals(right_hs, right_to)
        if not L or not R or len(left_hs) < 2 or len(right_hs) < 2:
            return 20.0
        # 以总周期为平均（使用最短的同侧周期）
        def overlap(a: Tuple[float,float], b: Tuple[float,float]) -> float:
            return max(0.0, min(a[1], b[1]) - max(a[0], b[0]))
        # 取对齐的周期数目
        cycles = min(len(left_hs)-1, len(right_hs)-1)
        overlaps = []
        for i in range(cycles):
            l_iv = L[i] if i < len(L) else None
            r_iv = R[i] if i < len(R) else None
            if l_iv and r_iv:
                o = overlap(l_iv, r_iv)
                cycle = min(left_hs[i+1]['time'] - left_hs[i]['time'], right_hs[i+1]['time'] - right_hs[i]['time'])
                if cycle > 0:
                    overlaps.append((o / cycle) * 100.0)
        return float(np.mean(overlaps)) if overlaps else 20.0
    
    def calculate_gait_parameters_final(self, pressure_data: List[List[List[float]]], events: Dict[str, Any]) -> Dict:
        """基于事件的步态参数计算（无硬限幅）"""
        left_hs = events['left']['hs']; left_to = events['left']['to']
        right_hs = events['right']['hs']; right_to = events['right']['to']
        total_frames = len(pressure_data)
        duration = total_frames / self.SAMPLING_RATE

        # 活动门限：COP AP 位移不足则判定为非步行，步态相关置零
        cop = events.get('cop_trajectory', [])
        ap_range = 0.0
        if len(cop) >= 2:
            ap_vals = np.array([c['x'] for c in cop], dtype=float)
            ap_range = float(np.ptp(ap_vals))
        is_walking = ap_range >= max(0.30, 0.10 * self.MAT_EFFECTIVE_LENGTH)
        
        # 步数：左右HS总和
        step_count = len(left_hs) + len(right_hs) if is_walking else 0
        
        # 计算“同侧HS间距”= stride length；随后步长=stride/2（临床定义）
        def stride_lengths_cm(hs: List[Dict]) -> List[float]:
            d = []
            for i in range(1, len(hs)):
                d.append(abs(hs[i]['x'] - hs[i-1]['x']) * 100.0)
            return d
        # 最小 AP 位移阈值（同侧 stride）
        MIN_STRIDE_AP_M = 0.35
        left_stride_cm_raw = stride_lengths_cm(left_hs) if is_walking else []
        right_stride_cm_raw = stride_lengths_cm(right_hs) if is_walking else []
        left_stride_cm = [v for v in left_stride_cm_raw if (v/100.0) >= MIN_STRIDE_AP_M]
        right_stride_cm = [v for v in right_stride_cm_raw if (v/100.0) >= MIN_STRIDE_AP_M]
        left_step_cm = [v / 2.0 for v in left_stride_cm]
        right_step_cm = [v / 2.0 for v in right_stride_cm]
        # 平均步长（cm）
        all_steps_cm = left_step_cm + right_step_cm
        avg_step_length_cm = float(np.mean(all_steps_cm)) if all_steps_cm else 0.0
        # 左右“步长(m)”
        left_avg_len_m = (float(np.mean(left_step_cm)) if left_step_cm else 0.0) / 100.0
        right_avg_len_m = (float(np.mean(right_step_cm)) if right_step_cm else 0.0) / 100.0
        
        # 速度（m/s）：用所有相邻HS的AP累计位移 / 首尾事件时间（自然包含转身）
        all_hs = sorted(left_hs + right_hs, key=lambda e: e['time']) if is_walking else []
        if len(all_hs) >= 2:
            ap_cum = 0.0
            for i in range(1, len(all_hs)):
                ap_cum += abs(all_hs[i]['x'] - all_hs[i-1]['x'])
            time_span = all_hs[-1]['time'] - all_hs[0]['time']
            avg_velocity = ap_cum / max(1e-6, time_span)
        else:
            avg_velocity = 0.0
        
        # 步频（步/分）
        # 基于同侧周期的步频（用有效周期：HS[k+1]-HS[k]）
        def cadence_from_hs(hs: List[Dict]) -> float:
            if len(hs) < 2:
                return 0.0
            intervals = [hs[i+1]['time'] - hs[i]['time'] for i in range(len(hs)-1)]
            intervals = [iv for iv in intervals if 0.4 <= iv <= 2.5]
            if not intervals:
                return 0.0
            return 60.0 / float(np.mean(intervals))
        left_cadence = cadence_from_hs(left_hs) if is_walking else 0.0
        right_cadence = cadence_from_hs(right_hs) if is_walking else 0.0
        # total cadence（全部 HS 的节律）
        total_cadence = cadence_from_hs(all_hs) if is_walking else 0.0
        cadence = total_cadence if (is_walking and step_count >= 4 and duration >= 5.0) else 0.0
        
        # 相位（逐脚）
        left_stance, left_swing = self._compute_phases_from_events(left_hs, left_to) if is_walking else (62.0, 38.0)
        right_stance, right_swing = self._compute_phases_from_events(right_hs, right_to) if is_walking else (62.0, 38.0)
        
        # 摆动时间与摆动速度（同侧 TO->下次HS）
        def swing_times(hs: List[Dict], to: List[Dict]) -> List[float]:
            times = []
            for i in range(min(len(hs)-1, len(to))):
                if hs[i]['time'] < to[i]['time'] < hs[i+1]['time']:
                    times.append(hs[i+1]['time'] - to[i]['time'])
            return times
        left_swing_times = swing_times(left_hs, left_to) if is_walking else []
        right_swing_times = swing_times(right_hs, right_to) if is_walking else []
        # 缺失补偿：若一侧缺失，用对侧均值替代，避免0
        if (not left_swing_times) and right_swing_times:
            left_swing_times = right_swing_times
        if (not right_swing_times) and left_swing_times:
            right_swing_times = left_swing_times
        left_avg_swing_t = float(np.mean(left_swing_times)) if left_swing_times else 0.0
        right_avg_swing_t = float(np.mean(right_swing_times)) if right_swing_times else 0.0
        left_swing_speed = (left_avg_len_m / left_avg_swing_t) if left_avg_swing_t > 0 else 0.0
        right_swing_speed = (right_avg_len_m / right_avg_swing_t) if right_avg_swing_t > 0 else 0.0
        
        # 转身时间估计：基于COP AP速度符号翻转+低速区间
        turn_time = 0.0
        if len(cop) >= 3:
            ap = np.array([c['x'] for c in cop], dtype=float)
            t = np.array([c['time'] for c in cop], dtype=float)
            v = np.gradient(ap, t, edge_order=1)
            # 找到符号翻转点
            sign = np.sign(v)
            flips = np.where(np.diff(sign) != 0)[0]
            if flips.size > 0:
                k = flips[0]
                # 在翻转点附近找低速连续区间（|v| < 阈值）
                thr = max(0.05, 0.2 * np.nanmax(np.abs(v)))
                low = np.where(np.abs(v) < thr)[0]
                if low.size > 0:
                    # 扩展包含翻转的最长低速段
                    seg = np.sort(low)
                    # 找包含k的连续段
                    start = k; end = k+1
                    while start-1 in seg: start -= 1
                    while end in seg: end += 1
                    start = max(0, start); end = min(len(t)-1, end)
                    turn_time = float(max(0.0, t[end] - t[start]))
        
        # 总体相位取平均
        stance_phase = float(np.mean([left_stance, right_stance])) if step_count > 0 else 62.0
        swing_phase = 100.0 - stance_phase
        double_support_overlap = self._compute_double_support(left_hs, left_to, right_hs, right_to) if is_walking else 20.0
        # 由左右站立相估算双支撑（稳健近似）
        ds_estimated = max(0.0, min(40.0, left_stance + right_stance - 100.0)) if is_walking else 20.0
        # 选择更合理的值：若重叠法过低(<1%)或异常，则采用估算值
        if not is_walking:
            double_support = 20.0
        else:
            double_support = double_support_overlap if double_support_overlap >= 1.0 else ds_estimated
        
        return {
            'is_walking': bool(is_walking),
            'step_count': int(step_count),
            'average_step_length': avg_step_length_cm,
            'average_velocity': float(avg_velocity),
            'cadence': float(cadence),
            'stance_phase': stance_phase,
            'swing_phase': swing_phase,
            'double_support': float(double_support),
            'left_stance_phase': left_stance,
            'right_stance_phase': right_stance,
            'turn_time': turn_time,
            'left_foot': {
                'average_step_length_m': left_avg_len_m,
                'cadence': float(left_cadence),
                'avg_swing_time_s': left_avg_swing_t,
                'swing_speed_mps': left_swing_speed,
            },
            'right_foot': {
                'average_step_length_m': right_avg_len_m,
                'cadence': float(right_cadence),
                'avg_swing_time_s': right_avg_swing_t,
                'swing_speed_mps': right_swing_speed,
            }
        }
    
    def comprehensive_analysis_final(self, csv_file_path: str) -> Dict:
        """综合分析 - 最终版本（统一真源）"""
        print(f"🔍 最终算法分析文件: {csv_file_path}")
        data = self.load_csv_data(csv_file_path)
        if 'error' in data:
            return data
        pressure_data = data['pressure_data']
        duration = data.get('metadata', {}).get('duration', 0)
        print(f"   数据帧数: {len(pressure_data)}")
        print(f"   测试时长: {duration:.1f}秒")
        
        # 事件检测（含左右分离）
        events = self.detect_gait_events_final(pressure_data)
        
        # 步态参数
        gait_params = self.calculate_gait_parameters_final(pressure_data, events)

        # 基于文件名推断测试类型
        def _infer_test_type(path: str) -> str:
            name = str(Path(path).name)
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
            return 'walk'

        inferred_type = _infer_test_type(csv_file_path)

        # 折返校正：基于9米总距离直接计算平均步长
        if inferred_type == 'walkway_turn' and gait_params.get('step_count', 0) > 0:
            walkway_distance_m = self.TEST_PROTOCOL['walkway']['single_leg_distance_m'] * (2 if self.TEST_PROTOCOL['walkway']['round_trip'] else 1)
            
            # 方案1：直接使用检测到的步数计算（假设步数检测准确）
            detected_steps = gait_params.get('step_count', 0)
            if detected_steps > 0:
                # 9米路程的实际平均步长
                target_avg_step_cm = (walkway_distance_m / detected_steps) * 100.0
                
                # 更新步长参数
                current_avg_cm = float(gait_params.get('average_step_length', 0.0))
                if current_avg_cm > 0:
                    scale = float(target_avg_step_cm / max(1e-6, current_avg_cm))
                    gait_params['average_step_length'] = target_avg_step_cm
                    if 'left_foot' in gait_params:
                        gait_params['left_foot']['average_step_length_m'] = float(gait_params['left_foot'].get('average_step_length_m', 0.0) * scale)
                    if 'right_foot' in gait_params:
                        gait_params['right_foot']['average_step_length_m'] = float(gait_params['right_foot'].get('average_step_length_m', 0.0) * scale)
        
        return {
            'file_info': {
                'path': csv_file_path,
                'format': data['format'],
                'total_frames': data['total_frames'],
                'duration': duration
            },
            'test_type': inferred_type,
            'gait_parameters': gait_params,
            'metadata': data.get('metadata', {}),
            'hardware_config': {
                'mat_length': self.MAT_TOTAL_LENGTH,
                'effective_length': self.MAT_EFFECTIVE_LENGTH,
                'mat_width': self.MAT_WIDTH,
                'grid_resolution': f'{self.GRID_SCALE_AP*100:.1f}×{self.GRID_SCALE_ML*100:.1f}cm/格'
            },
            'time_series': {
                'cop': events['cop_trajectory'],
                'total_pressure': events['total_pressure_smooth']
            },
            'pressure_snapshot': pressure_data[int(np.argmax(events['total_pressure_smooth']))] if events['total_pressure_smooth'] else None,
            'moments': {
                'heel_strikes_left': events['left']['hs'],
                'toe_offs_left': events['left']['to'],
                'heel_strikes_right': events['right']['hs'],
                'toe_offs_right': events['right']['to']
            },
            'algorithm_version': 'final_device_based_2025_08_12_events'
        }

if __name__ == "__main__":
    analyzer = PressureAnalysisFinal()
    test_file = "/Users/xidada/foot-pressure-analysis/数据/2025-08-09/detection_data/曾超-第6步-4.5米步道折返-20250809_171226.csv"
    if Path(test_file).exists():
        res = analyzer.comprehensive_analysis_final(test_file)
        print(json.dumps({k: (len(v) if isinstance(v, list) else v) for k, v in res.get('gait_parameters', {}).items()}, ensure_ascii=False, indent=2))