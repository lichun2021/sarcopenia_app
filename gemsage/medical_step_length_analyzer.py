#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
医学标准步长计算（确定性·最终版）
- 帧尺寸：64×32（AP=rows, ML=cols）
- 毯子长度：300 cm → 4.6875 cm/row
- 事件法：迟滞接触 + HS 上升沿
- 位置法：HS帧后沿代表点（heel-marker）
- 质控：时间窗（Δframe自适应）、步长范围、可选IQR去极端
"""

from __future__ import annotations
from dataclasses import dataclass
from typing import Dict, List, Tuple, Optional

import ast
import numpy as np
import pandas as pd

# 可选：scipy 形态学更稳健；若不可用则退化为简单阈值
try:
    from scipy import ndimage
    _HAVE_SCIPY = True
except Exception:
    _HAVE_SCIPY = False


@dataclass
class AnalyzerConfig:
    # 几何与标定
    ap_rows: int = 64
    ml_cols: int = 32
    mat_len_cm: float = 300.0              # 3米毯子
    rear_is_small_row: bool = True         # True=行号越小越靠后（默认）
    # 迟滞与事件
    contact_hi_q: float = 0.30             # 高阈值分位（非零）
    contact_lo_q: float = 0.20             # 低阈值分位（非零）
    hs_window_frames: int = 0              # HS邻域窗口（0=仅HS帧；2=±2帧择优）
    # heel-marker 口径
    footprint_thr_ratio: float = 0.12      # 足迹相对阈值（max×ratio）
    heel_percentile: float = 0.05          # AP后沿分位（5%）
    use_rear_zone_centroid: bool = False   # 用"后30%区域加权质心"替代分位
    rear_zone_ratio: float = 0.30          # "后区"占足迹AP范围比例
    # 质控
    keep_range_cm: Tuple[float, float] = (20.0, 150.0)  # 步长物理门槛
    iqr_trim: bool = False                 # 是否做IQR去极端（展示/统计用）
    iqr_k: float = 1.5                     # Tukey fence 系数
    # 打印/调试
    verbose: bool = True


class MedicalStepLengthAnalyzer:
    def __init__(self, cfg: AnalyzerConfig | None = None):
        self.cfg = cfg or AnalyzerConfig()
        self.cm_per_row = self.cfg.mat_len_cm / self.cfg.ap_rows

    # ---------- 解析 ----------
    def _parse_row_matrix(self, data_str: str) -> np.ndarray:
        """
        把 'data' 字符串解析成 64x32 (rows x cols) 数组（AP=rows）。
        """
        vals = np.array(ast.literal_eval(data_str), dtype=float)
        if vals.size != self.cfg.ap_rows * self.cfg.ml_cols:
            raise ValueError(f"帧数据长度={vals.size} 与 {self.cfg.ap_rows}x{self.cfg.ml_cols} 不符")
        return vals.reshape(self.cfg.ap_rows, self.cfg.ml_cols)

    def _load_stack(self, df: pd.DataFrame) -> np.ndarray:
        mats = [self._parse_row_matrix(s) for s in df["data"]]
        return np.stack(mats, axis=0)  # [T, 64, 32]

    # ---------- 迟滞接触 ----------
    @staticmethod
    def _hysteresis(series: np.ndarray, hi_q: float, lo_q: float) -> np.ndarray:
        nz = series[series > 0]
        hi = np.quantile(nz, hi_q) if nz.size else 0.0
        lo = np.quantile(nz, lo_q) if nz.size else 0.0
        on = False
        out = np.zeros(series.shape[0], dtype=bool)
        for i, v in enumerate(series):
            if not on and v >= hi:
                on = True
            if on and v <= lo:
                on = False
            out[i] = on
        return out

    @staticmethod
    def _hs_indices(contact: np.ndarray) -> np.ndarray:
        # 上升沿作为 HS
        if contact.size < 2:
            return np.empty(0, dtype=int)
        return np.flatnonzero((~contact[:-1]) & contact[1:]) + 1

    # ---------- heel-marker ----------
    def _foot_mask(self, foot_frame: np.ndarray) -> np.ndarray:
        mx = float(foot_frame.max())
        if mx <= 1e-9:
            return np.zeros_like(foot_frame, dtype=bool)
        mask = foot_frame >= (mx * self.cfg.footprint_thr_ratio)
        if _HAVE_SCIPY:
            mask = ndimage.binary_closing(mask, structure=np.ones((3, 3), bool))
        return mask

    def _heel_marker_row(self, foot_frame: np.ndarray) -> Optional[float]:
        """
        在给定帧（左或右半区）的足迹上计算"后沿代表点"的 AP 行坐标（row）。
        - rear_is_small_row=True：行号越小越靠后 → 取 mask.rows 的 5% 分位
        - rear_is_small_row=False：取 95% 分位
        可选：用"后30%区域"的加权质心。
        """
        mask = self._foot_mask(foot_frame)
        if not mask.any():
            return None

        rows = np.where(mask)[0]
        if rows.size == 0:
            return None

        if self.cfg.use_rear_zone_centroid:
            # 用足迹 AP 范围的后30%区域的加权质心（行坐标）
            rmin, rmax = rows.min(), rows.max()
            span = max(1, rmax - rmin + 1)
            if self.cfg.rear_is_small_row:
                r_boundary = int(np.floor(rmin + span * self.cfg.rear_zone_ratio))
                zone = np.arange(rmin, r_boundary + 1)
            else:
                r_boundary = int(np.ceil(rmax - span * self.cfg.rear_zone_ratio))
                zone = np.arange(r_boundary, rmax + 1)
            zone_mask = np.zeros_like(mask, dtype=bool)
            zone_mask[zone, :] = True
            Z = foot_frame * (mask & zone_mask)
            tot = Z.sum()
            if tot <= 1e-9:
                return float(rows.min() if self.cfg.rear_is_small_row else rows.max())
            ys = np.arange(foot_frame.shape[0])[:, None]
            return float((Z * ys).sum() / tot)

        # 分位数法（默认）
        rows_sorted = np.sort(rows)
        q = self.cfg.heel_percentile if self.cfg.rear_is_small_row else (1.0 - self.cfg.heel_percentile)
        k = int(np.clip(np.floor(q * rows_sorted.size), 0, rows_sorted.size - 1))
        return float(rows_sorted[k])

    # ---------- HS 配对 ----------
    @staticmethod
    def _pair_steps(left_hs: np.ndarray, right_hs: np.ndarray) -> Tuple[List[Tuple[int, int]], List[Tuple[int, int]], Tuple[int, int]]:
        """
        就近配对 + 自适应Δframe窗口：
          - 先用 L_HS → 最近的 R_HS 做粗配对，估计 Δframe 分位 [q10,q90]
          - 窗口 = [floor(q10*0.8), ceil(q90*1.2)]，用于严格配对
        返回：左步配对[(tL,tR)]，右步配对[(tR,tL)]，窗口
        """
        if left_hs.size == 0 or right_hs.size == 0:
            return [], [], (0, 0)

        prelim = []
        for tL in left_hs:
            later = right_hs[right_hs > tL]
            if later.size:
                prelim.append(later[0] - tL)
        if len(prelim) == 0:
            return [], [], (0, 0)

        deltas = np.array(prelim, float)
        q10, q90 = np.quantile(deltas, 0.10), np.quantile(deltas, 0.90)
        win_lo = max(1, int(np.floor(q10 * 0.8)))
        win_hi = int(np.ceil(q90 * 1.2))

        pairs_L: List[Tuple[int, int]] = []
        for tL in left_hs:
            cand = right_hs[(right_hs > tL) & (right_hs - tL >= win_lo) & (right_hs - tL <= win_hi)]
            if cand.size:
                pairs_L.append((tL, int(cand[0])))

        pairs_R: List[Tuple[int, int]] = []
        for tR in right_hs:
            cand = left_hs[(left_hs > tR) & (left_hs - tR >= win_lo) & (left_hs - tR <= win_hi)]
            if cand.size:
                pairs_R.append((tR, int(cand[0])))

        return pairs_L, pairs_R, (win_lo, win_hi)

    # ---------- 主流程 ----------
    def calculate_step_lengths(self, walking_df: pd.DataFrame) -> Dict[str, object]:
        """
        输入：包含 'data' 列（每行为2048个数，64×32）的步行CSV DataFrame
        输出：左右步长分布的中位数/四分位等，以及步幅与对称性指数
        """
        cfg = self.cfg
        S = self._load_stack(walking_df)                  # [T,64,32]
        left  = S[:, :, :cfg.ml_cols // 2]                # 左半区（列0..15）
        right = S[:, :, cfg.ml_cols // 2:]                # 右半区（列16..31）

        # 迟滞接触 & HS
        L_on = self._hysteresis(left.sum(axis=(1, 2)), cfg.contact_hi_q, cfg.contact_lo_q)
        R_on = self._hysteresis(right.sum(axis=(1, 2)), cfg.contact_hi_q, cfg.contact_lo_q)
        L_HS = self._hs_indices(L_on)
        R_HS = self._hs_indices(R_on)

        # HS就近配对 + Δframe窗口
        pairs_L, pairs_R, win = self._pair_steps(L_HS, R_HS)

        # HS帧（或邻域）计算 heel-marker 行坐标
        def best_heel_row(block: np.ndarray, t: int) -> Optional[float]:
            if cfg.hs_window_frames <= 0:
                return self._heel_marker_row(block[t])
            # 在 HS±w 内择优（半区总压最大的一帧）
            w = cfg.hs_window_frames
            t0 = max(0, t - w)
            t1 = min(block.shape[0], t + w + 1)
            seg = block[t0:t1]
            idx_local = int(np.argmax(seg.sum(axis=(1, 2))))
            return self._heel_marker_row(block[t0 + idx_local])

        L_row_at: Dict[int, float] = {}
        R_row_at: Dict[int, float] = {}

        for tL, _ in pairs_L:
            val = best_heel_row(left, tL)
            if val is not None:
                L_row_at[tL] = val
        for tR, _ in pairs_R:
            val = best_heel_row(right, tR)
            if val is not None:
                R_row_at[tR] = val

        # 对侧HS的 heel-marker
        R_row_next: Dict[int, float] = {}
        L_row_next: Dict[int, float] = {}
        for _, tR in pairs_L:
            val = best_heel_row(right, tR)
            if val is not None:
                R_row_next[tR] = val
        for _, tL in pairs_R:
            val = best_heel_row(left, tL)
            if val is not None:
                L_row_next[tL] = val

        # 步长（cm），含物理门槛
        cm_per_row = self.cm_per_row
        L_cm, R_cm = [], []

        def _append_if_ok(dist_rows: float, bag: List[float]):
            length_cm = abs(dist_rows) * cm_per_row
            lo, hi = cfg.keep_range_cm
            if lo <= length_cm <= hi:
                bag.append(float(length_cm))

        # 左：L_HS → 下一个 R_HS
        for tL, tR in pairs_L:
            r0 = L_row_at.get(tL, None)
            r1 = R_row_next.get(tR, None)
            if r0 is not None and r1 is not None:
                # rear_is_small_row=True → 行号越小越靠后
                dist_rows = (r1 - r0) if cfg.rear_is_small_row else (r0 - r1)
                _append_if_ok(dist_rows, L_cm)

        # 右：R_HS → 下一个 L_HS
        for tR, tL in pairs_R:
            r0 = R_row_at.get(tR, None)
            r1 = L_row_next.get(tL, None)
            if r0 is not None and r1 is not None:
                dist_rows = (r1 - r0) if cfg.rear_is_small_row else (r0 - r1)
                _append_if_ok(dist_rows, R_cm)

        def _summary(v: List[float]) -> Dict[str, float]:
            a = np.array(v, float)
            if a.size == 0:
                return dict(n=0, median=np.nan, p25=np.nan, p75=np.nan, min=np.nan, max=np.nan)
            if cfg.iqr_trim and a.size >= 5:
                q1, q3 = np.quantile(a, [0.25, 0.75])
                iqr = q3 - q1
                lo, hi = q1 - cfg.iqr_k * iqr, q3 + cfg.iqr_k * iqr
                a = a[(a >= lo) & (a <= hi)]
            return dict(
                n=int(a.size),
                median=float(np.median(a)),
                p25=float(np.quantile(a, 0.25)),
                p75=float(np.quantile(a, 0.75)),
                min=float(np.min(a)),
                max=float(np.max(a)),
            )

        left_stats = _summary(L_cm)
        right_stats = _summary(R_cm)

        # 步幅（≈ 左中位 + 右中位）与对称性
        stride_cm = (left_stats["median"] + right_stats["median"]) if np.isfinite(left_stats["median"]) and np.isfinite(right_stats["median"]) else np.nan
        si = (abs(left_stats["median"] - right_stats["median"]) / ((left_stats["median"] + right_stats["median"]) / 2) * 100.0
              if np.isfinite(stride_cm) and stride_cm > 0 else np.nan)

        return dict(
            config=dict(ap_rows=self.cfg.ap_rows, ml_cols=self.cfg.ml_cols, cm_per_row=self.cm_per_row,
                        rear_is_small_row=self.cfg.rear_is_small_row, win=win, keep_range_cm=self.cfg.keep_range_cm),
            left=left_stats,
            right=right_stats,
            stride_cm=float(stride_cm) if np.isfinite(stride_cm) else np.nan,
            symmetry_index=float(si) if np.isfinite(si) else np.nan,
            pairs=dict(left=len(pairs_L), right=len(pairs_R))
        )


# ---------------------- 命令行/示例 ----------------------

def analyze_csv(walking_csv_path: str, cfg: AnalyzerConfig | None = None) -> Dict[str, object]:
    """
    读取 CSV 并返回分析结果（字典）
    walking_csv_path: 含 'data' 列（2048=64×32）
    """
    df = pd.read_csv(walking_csv_path)
    analyzer = MedicalStepLengthAnalyzer(cfg)
    return analyzer.calculate_step_lengths(df)


if __name__ == "__main__":
    # 示例：python medical_step_length_analyzer.py /path/to/步行.csv
    import sys, json
    if len(sys.argv) < 2:
        print("用法：python medical_step_length_analyzer.py <步行CSV路径>")
        sys.exit(1)
    path = sys.argv[1]
    res = analyze_csv(path, AnalyzerConfig(
        ap_rows=64, ml_cols=32, mat_len_cm=300.0,
        rear_is_small_row=True,
        contact_hi_q=0.30, contact_lo_q=0.20,
        hs_window_frames=0,                # 需要在HS±2帧择优时改成 2
        footprint_thr_ratio=0.12,
        heel_percentile=0.05,
        use_rear_zone_centroid=False,      # 想用"后30%质心"时设 True
        keep_range_cm=(20.0, 150.0),
        iqr_trim=False, iqr_k=1.5,
        verbose=False
    ))
    print(json.dumps(res, ensure_ascii=False, indent=2))