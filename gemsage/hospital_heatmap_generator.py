#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
医院级压力热力图生成器 - 优化版
基于提供的专业方案，针对GemSage系统优化

主要改进：
1. 修正压力值标定系数（500对应约50N而非4900N）
2. 支持64×32和32×32两种常见格式
3. 添加左右脚自动检测和分割
4. 使用中位数和稳定期平均值减少异常
5. 医学友好的配色和标注
"""

from dataclasses import dataclass
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.patches as patches
import pandas as pd
import os
from typing import Optional, Tuple, Dict, List
from datetime import datetime

try:
    from scipy.ndimage import gaussian_filter
    from scipy import signal
    _HAS_SCIPY = True
except Exception:
    _HAS_SCIPY = False


@dataclass
class HeatmapConfig:
    """热力图配置参数"""
    target_size: Tuple[int, int] = (32, 32)    # 目标显示网格
    colormap: str = "inferno"                   # 医学常用配色（避免jet误导）
    vmax_n: Optional[float] = None             # 颜色上限（牛顿），None=自适应
    vmin_n: float = 0.0                        # 颜色下限
    smoothing_sigma: float = 0.8               # 高斯平滑sigma
    threshold_n: float = 10.0                  # 分割阈值（牛顿）
    draw_contours: bool = True                 # 绘制等压线
    contour_levels: int = 8                    # 等压线数量
    draw_cop: bool = True                      # 叠加压力中心
    draw_grid: bool = True                     # 叠加网格线
    draw_regions: bool = True                  # 显示前/中/后足区域
    dpi: int = 150                            # 输出清晰度
    figsize: Tuple[float, float] = (8, 8)     # 图像尺寸
    calibration_factor: float = 0.1            # 原始值到牛顿的标定系数（修正后）
    use_median: bool = True                    # 使用中位数而非平均值
    stable_ratio: float = 0.8                  # 稳定期数据比例（去掉前后10%）


class HospitalHeatmapGenerator:
    """医院级热力图生成器"""
    
    def __init__(self, config: Optional[HeatmapConfig] = None):
        self.config = config or HeatmapConfig()
        
    def calibrate_pressure(self, raw_data: np.ndarray, 
                          zero_offset: Optional[np.ndarray] = None) -> np.ndarray:
        """
        压力标定：原始值转换为牛顿
        修正：500原始值 ≈ 50N（而非4900N）
        """
        if zero_offset is not None:
            calibrated = (raw_data - zero_offset) * self.config.calibration_factor
        else:
            # 自动基线校准：使用最低10%分位作为零点
            baseline = np.percentile(raw_data[raw_data > 0], 10) if np.any(raw_data > 0) else 0
            calibrated = (raw_data - baseline) * self.config.calibration_factor
        
        calibrated[calibrated < 0] = 0  # 负值截断
        return calibrated
    
    def extract_stable_data(self, data: np.ndarray) -> np.ndarray:
        """
        提取稳定期数据（去掉开始和结束的过渡期）
        """
        if len(data.shape) == 3:  # 时间序列
            n_frames = data.shape[0]
            start = int(n_frames * (1 - self.config.stable_ratio) / 2)
            end = int(n_frames * (1 + self.config.stable_ratio) / 2)
            return data[start:end]
        return data
    
    def compute_cop(self, pressure: np.ndarray) -> Optional[Tuple[float, float]]:
        """
        计算压力中心（COP）
        返回：(x, y) 相对坐标（0-1范围）
        """
        if pressure.max() < self.config.threshold_n:
            return None
            
        # 仅统计超过阈值的区域
        mask = pressure >= self.config.threshold_n
        weighted = pressure * mask
        total = weighted.sum()
        
        if total <= 0:
            return None
            
        h, w = pressure.shape
        y_coords, x_coords = np.mgrid[0:h, 0:w]
        
        cop_x = (weighted * x_coords).sum() / total / w  # 归一化到0-1
        cop_y = (weighted * y_coords).sum() / total / h
        
        return (float(cop_x), float(cop_y))
    
    def detect_foot_regions(self, pressure: np.ndarray) -> Dict[str, np.ndarray]:
        """
        检测足部区域：前足、中足、后足
        基于压力分布的解剖学分割
        """
        h, w = pressure.shape
        regions = {}
        
        # 基于压力分布检测
        pressure_profile = pressure.mean(axis=1)  # 纵向压力分布
        
        # 找峰值位置
        if _HAS_SCIPY:
            peaks, _ = signal.find_peaks(pressure_profile, height=self.config.threshold_n)
        else:
            # 简单峰值检测
            peaks = []
            for i in range(1, len(pressure_profile)-1):
                if (pressure_profile[i] > pressure_profile[i-1] and 
                    pressure_profile[i] > pressure_profile[i+1] and
                    pressure_profile[i] > self.config.threshold_n):
                    peaks.append(i)
        
        # 基于解剖学比例分割（前足40%、中足30%、后足30%）
        if len(peaks) >= 2:
            # 有明显的前后峰值
            boundary1 = int(h * 0.4)
            boundary2 = int(h * 0.7)
        else:
            # 使用默认比例
            boundary1 = int(h * 0.35)
            boundary2 = int(h * 0.65)
        
        regions['forefoot'] = pressure[:boundary1, :]
        regions['midfoot'] = pressure[boundary1:boundary2, :]
        regions['rearfoot'] = pressure[boundary2:, :]
        
        return regions
    
    def detect_left_right(self, pressure: np.ndarray) -> str:
        """
        自动检测左右脚
        基于压力分布的不对称性
        """
        h, w = pressure.shape
        left_half = pressure[:, :w//2]
        right_half = pressure[:, w//2:]
        
        # 计算内外侧压力差异
        left_total = left_half.sum()
        right_total = right_half.sum()
        
        # 检测大拇指区域（前内侧）
        toe_region = pressure[:h//3, :]
        toe_left = toe_region[:, :w//2].sum()
        toe_right = toe_region[:, w//2:].sum()
        
        # 左脚：内侧（右半部）压力更大
        # 右脚：外侧（左半部）压力更大
        if toe_right > toe_left * 1.1:
            return "left"
        elif toe_left > toe_right * 1.1:
            return "right"
        else:
            return "unknown"
    
    def resize_to_target(self, data: np.ndarray) -> np.ndarray:
        """
        调整到目标尺寸（32×32）
        优先使用块均值保持物理意义
        """
        if data.shape == self.config.target_size:
            return data
            
        h, w = data.shape
        th, tw = self.config.target_size
        
        # 64×32 → 32×32：块均值下采样
        if h == 64 and w == 32 and th == 32 and tw == 32:
            # 每2×1块取平均
            reshaped = data.reshape(32, 2, 32, 1)
            return reshaped.mean(axis=(1, 3))
        
        # 其他情况：双线性插值
        if _HAS_SCIPY:
            from scipy.ndimage import zoom
            zoom_factors = (th/h, tw/w)
            return zoom(data, zoom_factors, order=1)
        else:
            # 简单最近邻
            y_idx = np.round(np.linspace(0, h-1, th)).astype(int)
            x_idx = np.round(np.linspace(0, w-1, tw)).astype(int)
            return data[np.ix_(y_idx, x_idx)]
    
    def apply_smoothing(self, data: np.ndarray) -> np.ndarray:
        """
        应用高斯平滑去噪
        """
        if self.config.smoothing_sigma <= 0:
            return data
            
        if _HAS_SCIPY:
            return gaussian_filter(data, sigma=self.config.smoothing_sigma, mode='nearest')
        else:
            # 简单3×3均值滤波
            kernel = np.ones((3, 3)) / 9
            padded = np.pad(data, 1, mode='edge')
            result = np.zeros_like(data)
            for i in range(3):
                for j in range(3):
                    result += padded[i:i+data.shape[0], j:j+data.shape[1]] * kernel[i, j]
            return result
    
    def generate_heatmap(self, pressure_data: np.ndarray,
                        title: str = "足底压力分布",
                        patient_info: Optional[Dict] = None,
                        save_path: Optional[str] = None,
                        show: bool = False) -> Optional[str]:
        """
        生成医院级热力图
        
        Args:
            pressure_data: 压力数据（2D或3D时间序列）
            title: 图表标题
            patient_info: 患者信息字典
            save_path: 保存路径
            show: 是否显示
            
        Returns:
            保存的文件路径或None
        """
        # 处理时间序列：提取稳定期
        if len(pressure_data.shape) == 3:
            stable_data = self.extract_stable_data(pressure_data)
            if self.config.use_median:
                pressure = np.median(stable_data, axis=0)
            else:
                pressure = np.mean(stable_data, axis=0)
        else:
            pressure = pressure_data
        
        # 标定压力值
        pressure = self.calibrate_pressure(pressure)
        
        # 调整尺寸
        pressure = self.resize_to_target(pressure)
        
        # 平滑处理
        pressure = self.apply_smoothing(pressure)
        
        # 计算指标
        cop = self.compute_cop(pressure)
        foot_side = self.detect_left_right(pressure)
        regions = self.detect_foot_regions(pressure)
        
        # 确定颜色范围
        vmin = self.config.vmin_n
        if self.config.vmax_n is None:
            vmax = np.percentile(pressure, 98) if pressure.max() > 0 else 100
            vmax = max(vmax, 100)  # 至少100N
        else:
            vmax = self.config.vmax_n
        
        # 创建图形
        fig, ax = plt.subplots(figsize=self.config.figsize, dpi=self.config.dpi)
        
        # 绘制热力图
        im = ax.imshow(pressure, cmap=self.config.colormap,
                      vmin=vmin, vmax=vmax,
                      interpolation='nearest',  # 保持像素清晰
                      aspect='equal')
        
        # 绘制等压线
        if self.config.draw_contours and pressure.max() > self.config.threshold_n:
            masked = np.where(pressure >= self.config.threshold_n, pressure, np.nan)
            try:
                levels = np.linspace(self.config.threshold_n, pressure.max(), self.config.contour_levels)
                cs = ax.contour(masked, levels=levels,
                               linewidths=0.8, colors='white', alpha=0.7)
                ax.clabel(cs, inline=True, fontsize=7, fmt='%.0fN')
            except:
                pass
        
        # 绘制COP
        if self.config.draw_cop and cop is not None:
            h, w = pressure.shape
            cx = cop[0] * w
            cy = cop[1] * h
            
            # 白色十字和圆圈标记
            ax.plot(cx, cy, 'wo', markersize=8, markeredgecolor='red', markeredgewidth=2)
            ax.plot([cx-1, cx+1], [cy, cy], 'w-', linewidth=2)
            ax.plot([cx, cx], [cy-1, cy+1], 'w-', linewidth=2)
            
            # 添加COP坐标标注
            ax.annotate(f'COP\n({cx:.1f},{cy:.1f})', 
                       xy=(cx, cy), xytext=(cx+3, cy-3),
                       color='white', fontsize=8,
                       bbox=dict(boxstyle='round,pad=0.3', facecolor='black', alpha=0.5))
        
        # 绘制网格
        if self.config.draw_grid:
            h, w = pressure.shape
            ax.set_xticks(np.arange(-0.5, w, 1), minor=True)
            ax.set_yticks(np.arange(-0.5, h, 1), minor=True)
            ax.grid(which='minor', color='white', linestyle='-', linewidth=0.3, alpha=0.3)
        
        # 绘制区域分割线
        if self.config.draw_regions:
            h, w = pressure.shape
            ax.axhline(y=h*0.35, color='yellow', linestyle='--', linewidth=1, alpha=0.5)
            ax.axhline(y=h*0.65, color='yellow', linestyle='--', linewidth=1, alpha=0.5)
            
            # 添加区域标签
            ax.text(w*0.05, h*0.15, '前足', color='white', fontsize=9, 
                   bbox=dict(boxstyle='round,pad=0.3', facecolor='black', alpha=0.5))
            ax.text(w*0.05, h*0.5, '中足', color='white', fontsize=9,
                   bbox=dict(boxstyle='round,pad=0.3', facecolor='black', alpha=0.5))
            ax.text(w*0.05, h*0.85, '后足', color='white', fontsize=9,
                   bbox=dict(boxstyle='round,pad=0.3', facecolor='black', alpha=0.5))
        
        # 颜色条
        cbar = plt.colorbar(im, ax=ax, fraction=0.046, pad=0.04)
        cbar.set_label('压力 (N)', fontsize=10)
        cbar.ax.tick_params(labelsize=9)
        
        # 标题和信息
        full_title = f"{title}"
        if foot_side != "unknown":
            side_text = "左脚" if foot_side == "left" else "右脚"
            full_title += f" - {side_text}"
        
        ax.set_title(full_title, fontsize=14, weight='bold', pad=15)
        
        # 添加患者信息
        if patient_info:
            info_text = []
            if 'name' in patient_info:
                info_text.append(f"姓名: {patient_info['name']}")
            if 'age' in patient_info:
                info_text.append(f"年龄: {patient_info['age']}岁")
            if 'date' in patient_info:
                info_text.append(f"日期: {patient_info['date']}")
            
            if info_text:
                ax.text(0.02, 0.98, '\n'.join(info_text),
                       transform=ax.transAxes,
                       fontsize=9, verticalalignment='top',
                       bbox=dict(boxstyle='round,pad=0.5', facecolor='white', alpha=0.8))
        
        # 添加统计信息
        stats_text = [
            f"最大压力: {pressure.max():.1f}N",
            f"平均压力: {pressure[pressure > self.config.threshold_n].mean():.1f}N",
            f"接触面积: {(pressure > self.config.threshold_n).sum():.0f}格"
        ]
        
        # 计算区域峰值压力
        for region_name, region_data in regions.items():
            if region_data.max() > self.config.threshold_n:
                region_text = {
                    'forefoot': '前足',
                    'midfoot': '中足', 
                    'rearfoot': '后足'
                }[region_name]
                stats_text.append(f"{region_text}峰值: {region_data.max():.1f}N")
        
        ax.text(0.98, 0.02, '\n'.join(stats_text),
               transform=ax.transAxes,
               fontsize=9, horizontalalignment='right',
               bbox=dict(boxstyle='round,pad=0.5', facecolor='white', alpha=0.8))
        
        # 隐藏坐标轴刻度
        ax.set_xticks([])
        ax.set_yticks([])
        
        plt.tight_layout()
        
        # 保存或显示
        if save_path:
            os.makedirs(os.path.dirname(save_path) or ".", exist_ok=True)
            plt.savefig(save_path, dpi=self.config.dpi, bbox_inches='tight', 
                       facecolor='white', edgecolor='none')
            result_path = save_path
        else:
            result_path = None
            
        if show:
            plt.show()
        else:
            plt.close()
        
        return result_path
    
    def generate_comparison_heatmap(self, left_data: np.ndarray, right_data: np.ndarray,
                                   title: str = "左右脚压力对比",
                                   patient_info: Optional[Dict] = None,
                                   save_path: Optional[str] = None) -> Optional[str]:
        """
        生成左右脚对比热力图
        """
        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 6), dpi=self.config.dpi)
        
        # 处理数据
        for ax, data, side in [(ax1, left_data, "左脚"), (ax2, right_data, "右脚")]:
            # 处理时间序列
            if len(data.shape) == 3:
                stable_data = self.extract_stable_data(data)
                if self.config.use_median:
                    pressure = np.median(stable_data, axis=0)
                else:
                    pressure = np.mean(stable_data, axis=0)
            else:
                pressure = data
            
            # 标定和处理
            pressure = self.calibrate_pressure(pressure)
            pressure = self.resize_to_target(pressure)
            pressure = self.apply_smoothing(pressure)
            
            # 统一颜色范围
            vmax = max(np.percentile(left_data, 98), np.percentile(right_data, 98))
            vmax = max(vmax, 100)
            
            # 绘制
            im = ax.imshow(pressure, cmap=self.config.colormap,
                          vmin=0, vmax=vmax,
                          interpolation='nearest', aspect='equal')
            
            # COP
            cop = self.compute_cop(pressure)
            if cop:
                h, w = pressure.shape
                cx, cy = cop[0] * w, cop[1] * h
                ax.plot(cx, cy, 'wo', markersize=8, markeredgecolor='red', markeredgewidth=2)
            
            # 标题和统计
            ax.set_title(f"{side}\n最大: {pressure.max():.1f}N", fontsize=12)
            ax.set_xticks([])
            ax.set_yticks([])
        
        # 总标题
        fig.suptitle(title, fontsize=14, weight='bold')
        
        # 共享颜色条
        fig.subplots_adjust(right=0.85)
        cbar_ax = fig.add_axes([0.88, 0.15, 0.03, 0.7])
        fig.colorbar(im, cax=cbar_ax, label='压力 (N)')
        
        plt.tight_layout()
        
        if save_path:
            plt.savefig(save_path, dpi=self.config.dpi, bbox_inches='tight')
            return save_path
        
        return None


# 便捷函数
def create_hospital_heatmap(data_path: str = None,
                           raw_data: np.ndarray = None,
                           title: str = "足底压力分布",
                           save_path: str = None,
                           **kwargs) -> str:
    """
    便捷函数：快速生成医院级热力图
    
    Args:
        data_path: CSV文件路径
        raw_data: 原始数据数组
        title: 标题
        save_path: 保存路径
        **kwargs: 其他HeatmapConfig参数
        
    Returns:
        生成的图片路径
    """
    # 加载数据
    if data_path:
        if data_path.endswith('.csv'):
            df = pd.read_csv(data_path)
            if 'data' in df.columns:
                # 处理压力传感器CSV格式
                raw_data = []
                for row in df['data']:
                    values = [float(x) for x in str(row).split(',')]
                    raw_data.append(values)
                raw_data = np.array(raw_data)
            else:
                raw_data = df.values
        elif data_path.endswith('.npy'):
            raw_data = np.load(data_path)
    
    if raw_data is None:
        raise ValueError("需要提供data_path或raw_data")
    
    # 创建配置
    config = HeatmapConfig(**kwargs)
    
    # 生成热力图
    generator = HospitalHeatmapGenerator(config)
    
    if save_path is None:
        save_path = f"heatmap_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
    
    return generator.generate_heatmap(raw_data, title=title, save_path=save_path)


if __name__ == "__main__":
    # 测试：生成示例热力图
    print("生成医院级热力图示例...")
    
    # 创建模拟数据（高跟型脚印）
    test_data = np.zeros((64, 32))
    # 后跟区域
    y, x = np.ogrid[45:55, 10:22]
    test_data[y, x] = 400 + np.random.randn(10, 12) * 20
    # 前掌区域
    y, x = np.ogrid[10:25, 8:24]
    test_data[y, x] = 350 + np.random.randn(15, 16) * 30
    
    # 生成热力图
    config = HeatmapConfig(
        calibration_factor=1.0,  # 模拟数据已经是牛顿单位
        smoothing_sigma=1.0,
        contour_levels=10,
        draw_regions=True
    )
    
    generator = HospitalHeatmapGenerator(config)
    
    patient_info = {
        'name': '测试患者',
        'age': 65,
        'date': datetime.now().strftime('%Y-%m-%d')
    }
    
    output_path = generator.generate_heatmap(
        test_data,
        title="足底压力分布测试",
        patient_info=patient_info,
        save_path="test_hospital_heatmap.png",
        show=False
    )
    
    print(f"✅ 热力图已生成: {output_path}")
    
    # 测试左右脚对比
    right_data = test_data.copy()
    right_data = np.fliplr(right_data)  # 镜像作为右脚
    
    comparison_path = generator.generate_comparison_heatmap(
        test_data, right_data,
        title="左右脚压力对比分析",
        patient_info=patient_info,
        save_path="test_comparison_heatmap.png"
    )
    
    print(f"✅ 对比图已生成: {comparison_path}")