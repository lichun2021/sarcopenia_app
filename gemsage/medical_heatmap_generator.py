#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
医院级热力图生成器 - 完全按照临床标准规范实现

特性：
- 统一色标（跨任务统一上限）
- 等值线（15%、40%、70%相对等值线）  
- 左右脚COP轨迹分离显示
- 95% COP置信椭圆
- 10cm物理比例尺
- 列=AP（前后）、行=ML（左右）坐标系
- 内嵌SVG矢量图表（非PNG）
- 300 DPI医疗级输出质量
"""

import matplotlib.pyplot as plt
import matplotlib.patches as patches
from matplotlib.patches import Ellipse
import numpy as np
import pandas as pd
import ast
import io
import base64
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass
import warnings
warnings.filterwarnings('ignore')

# 设置医疗级图表参数
plt.rcParams['font.sans-serif'] = ['SimHei', 'Arial Unicode MS', 'DejaVu Sans']
plt.rcParams['axes.unicode_minus'] = False
plt.rcParams['figure.facecolor'] = 'white'
plt.rcParams['savefig.facecolor'] = 'white'
plt.rcParams['figure.dpi'] = 300
plt.rcParams['savefig.dpi'] = 300


@dataclass
class MedicalHeatmapConfig:
    """医院级热力图配置"""
    # 矩阵规格
    ap_rows: int = 64           # AP方向（前后）= 行
    ml_cols: int = 32           # ML方向（左右）= 列  
    mat_len_cm: float = 300.0   # 3米毯子物理长度
    
    # 显示参数
    global_vmax_percentile: float = 99.0    # 全局色标上限（99百分位）
    contour_levels: List[float] = None      # 等值线级别 [15%, 40%, 70%]
    min_contact_threshold: float = 0.05     # 最小接触阈值（相对于最大值）
    
    # 输出规格
    fig_width: float = 10.0     # 图形宽度（英寸）
    fig_height: float = 6.0     # 图形高度（英寸）
    dpi: int = 300              # 医疗级DPI
    
    def __post_init__(self):
        if self.contour_levels is None:
            self.contour_levels = [0.15, 0.40, 0.70]  # 默认等值线级别


class MedicalHeatmapGenerator:
    """医院级热力图生成器"""
    
    def __init__(self, config: MedicalHeatmapConfig = None):
        self.config = config or MedicalHeatmapConfig()
        self.cm_per_row = self.config.mat_len_cm / self.config.ap_rows  # 4.6875 cm/格
        self.cm_per_col = self.config.mat_len_cm / self.config.ap_rows  # 假设正方形像素
        
    def parse_pressure_matrix(self, data_str: str) -> np.ndarray:
        """解析压力数据字符串为64×32矩阵"""
        try:
            # 去除方括号和引号，按逗号分割
            data_str = data_str.strip('[]"\'')
            values = [float(x.strip()) for x in data_str.split(',')]
            
            # 确保数据长度正确
            expected_size = self.config.ap_rows * self.config.ml_cols
            if len(values) != expected_size:
                raise ValueError(f"数据长度{len(values)}与期望的{expected_size}不匹配")
            
            # 重塑为64×32矩阵（行=AP，列=ML）
            return np.array(values).reshape(self.config.ap_rows, self.config.ml_cols)
            
        except Exception as e:
            print(f"⚠️ 压力矩阵解析失败: {e}")
            return np.zeros((self.config.ap_rows, self.config.ml_cols))
    
    def calculate_global_vmax(self, data_list: List[pd.DataFrame]) -> float:
        """计算全局色标上限（所有数据99百分位）"""
        all_values = []
        
        for df in data_list:
            if df is None or len(df) == 0:
                continue
                
            for _, row in df.iterrows():
                try:
                    matrix = self.parse_pressure_matrix(row['data'])
                    # 只考虑非零值
                    nonzero_values = matrix[matrix > 0]
                    if len(nonzero_values) > 0:
                        all_values.extend(nonzero_values)
                except:
                    continue
        
        if len(all_values) == 0:
            return 100.0  # 默认上限
            
        return float(np.percentile(all_values, self.config.global_vmax_percentile))
    
    def filter_effective_frames(self, df: pd.DataFrame, min_pressure_ratio: float = 0.2) -> pd.DataFrame:
        """筛选有效接触帧"""
        if df is None or len(df) == 0:
            return df
            
        effective_indices = []
        max_total_pressure = 0
        
        # 第一轮：找到最大总压力
        for idx, row in df.iterrows():
            try:
                matrix = self.parse_pressure_matrix(row['data'])
                total_pressure = matrix.sum()
                max_total_pressure = max(max_total_pressure, total_pressure)
            except:
                continue
        
        # 第二轮：筛选有效帧
        threshold = max_total_pressure * min_pressure_ratio
        for idx, row in df.iterrows():
            try:
                matrix = self.parse_pressure_matrix(row['data'])
                if matrix.sum() >= threshold:
                    effective_indices.append(idx)
            except:
                continue
        
        return df.loc[effective_indices] if effective_indices else df
    
    def calculate_cop_trajectory(self, df: pd.DataFrame) -> Tuple[List[Tuple[float, float]], List[Tuple[float, float]]]:
        """计算左右脚COP轨迹（分离）"""
        left_cops = []
        right_cops = []
        
        if df is None or len(df) == 0:
            return left_cops, right_cops
            
        for _, row in df.iterrows():
            try:
                matrix = self.parse_pressure_matrix(row['data'])
                
                # 分左右半区（沿ML方向分）
                mid_col = self.config.ml_cols // 2
                left_matrix = matrix[:, :mid_col]    # 左半区
                right_matrix = matrix[:, mid_col:]   # 右半区
                
                # 计算左脚COP
                left_total = left_matrix.sum()
                if left_total > 0:
                    # AP方向质心（行坐标）
                    ap_coords = np.arange(self.config.ap_rows)[:, None]
                    ml_coords = np.arange(mid_col)[None, :]
                    
                    cop_ap = (left_matrix * ap_coords).sum() / left_total * self.cm_per_row
                    cop_ml = (left_matrix * ml_coords).sum() / left_total * self.cm_per_col
                    left_cops.append((cop_ap, cop_ml))
                
                # 计算右脚COP
                right_total = right_matrix.sum()
                if right_total > 0:
                    ap_coords = np.arange(self.config.ap_rows)[:, None]
                    ml_coords = np.arange(right_matrix.shape[1])[None, :]
                    
                    cop_ap = (right_matrix * ap_coords).sum() / right_total * self.cm_per_row
                    cop_ml = ((right_matrix * ml_coords).sum() / right_total + mid_col) * self.cm_per_col
                    right_cops.append((cop_ap, cop_ml))
                    
            except Exception as e:
                continue
                
        return left_cops, right_cops
    
    def calculate_cop_ellipse(self, cop_positions: List[Tuple[float, float]], confidence: float = 0.95) -> Optional[Ellipse]:
        """计算95% COP置信椭圆"""
        if len(cop_positions) < 3:
            return None
            
        try:
            cops = np.array(cop_positions)
            mean_ap, mean_ml = np.mean(cops, axis=0)
            cov_matrix = np.cov(cops.T)
            
            # 特征值分解
            eigenvals, eigenvecs = np.linalg.eigh(cov_matrix)
            
            # 95%置信区间对应的卡方值
            chi2_val = 5.991 if confidence == 0.95 else 4.605  # chi2(0.05, df=2) or chi2(0.10, df=2)
            
            # 椭圆参数
            width = 2 * np.sqrt(chi2_val * eigenvals[0])
            height = 2 * np.sqrt(chi2_val * eigenvals[1])
            angle = np.degrees(np.arctan2(eigenvecs[1, 0], eigenvecs[0, 0]))
            
            return Ellipse((mean_ap, mean_ml), width, height, angle=angle,
                          linewidth=2, fill=False, alpha=0.8)
            
        except Exception as e:
            print(f"⚠️ 椭圆计算失败: {e}")
            return None
    
    def create_medical_heatmap(self, df: pd.DataFrame, title: str, 
                              global_vmax: float, mode: str = "average") -> str:
        """
        生成医院级热力图
        
        Args:
            df: 压力数据DataFrame
            title: 图表标题
            global_vmax: 全局色标上限
            mode: "average" 或 "peak" 模式
            
        Returns:
            str: SVG格式的图表字符串
        """
        
        fig, ax = plt.subplots(1, 1, figsize=(self.config.fig_width, self.config.fig_height))
        
        # 筛选有效帧
        effective_df = self.filter_effective_frames(df)
        if len(effective_df) == 0:
            # 返回空图
            ax.text(0.5, 0.5, '无有效数据', transform=ax.transAxes, 
                   ha='center', va='center', fontsize=16)
            ax.set_title(title, fontsize=14, fontweight='bold')
            return self._fig_to_svg(fig)
        
        # 生成热力图矩阵
        if mode == "average":
            # 平均热力图
            pressure_matrices = []
            for _, row in effective_df.iterrows():
                try:
                    matrix = self.parse_pressure_matrix(row['data'])
                    pressure_matrices.append(matrix)
                except:
                    continue
            
            if pressure_matrices:
                heatmap_matrix = np.mean(pressure_matrices, axis=0)
            else:
                heatmap_matrix = np.zeros((self.config.ap_rows, self.config.ml_cols))
        else:
            # 峰值帧热力图
            max_pressure = 0
            heatmap_matrix = np.zeros((self.config.ap_rows, self.config.ml_cols))
            
            for _, row in effective_df.iterrows():
                try:
                    matrix = self.parse_pressure_matrix(row['data'])
                    total_pressure = matrix.sum()
                    if total_pressure > max_pressure:
                        max_pressure = total_pressure
                        heatmap_matrix = matrix
                except:
                    continue
        
        # 设置物理坐标轴（列=AP，行=ML）
        ap_extent = self.config.ap_rows * self.cm_per_row  # AP方向总长度（cm）
        ml_extent = self.config.ml_cols * self.cm_per_col  # ML方向总长度（cm）
        
        # 绘制热力图
        im = ax.imshow(heatmap_matrix.T,  # 转置：行=ML显示为Y轴，列=AP显示为X轴
                      cmap='Reds', 
                      extent=[0, ap_extent, 0, ml_extent],
                      origin='lower',  # 固定方向一致性
                      aspect='equal',  # 保证像素正方形
                      vmin=0, vmax=global_vmax,
                      interpolation='bilinear')
        
        # 添加等值线
        if heatmap_matrix.max() > 0:
            # 创建坐标网格
            ap_coords = np.linspace(0, ap_extent, self.config.ap_rows)
            ml_coords = np.linspace(0, ml_extent, self.config.ml_cols)
            AP, ML = np.meshgrid(ap_coords, ml_coords)
            
            # 绘制相对等值线
            max_val = heatmap_matrix.max()
            contour_values = [level * max_val for level in self.config.contour_levels]
            
            contours = ax.contour(AP, ML, heatmap_matrix.T, 
                                levels=contour_values, 
                                colors=['white', 'yellow', 'orange'], 
                                linewidths=[1, 1.5, 2],
                                alpha=0.8)
            
            # 添加等值线标签
            ax.clabel(contours, inline=True, fontsize=8, fmt=lambda x: f'{x/max_val:.0%}')
        
        # 计算并绘制COP轨迹
        left_cops, right_cops = self.calculate_cop_trajectory(effective_df)
        
        if mode == "average":
            # 平均图：绘制完整轨迹
            if left_cops:
                left_array = np.array(left_cops)
                ax.plot(left_array[:, 0], left_array[:, 1], 'b-', 
                       linewidth=2, alpha=0.7, label=f'左脚轨迹 ({len(left_cops)}点)')
                
            if right_cops:
                right_array = np.array(right_cops)
                ax.plot(right_array[:, 0], right_array[:, 1], 'r-', 
                       linewidth=2, alpha=0.7, label=f'右脚轨迹 ({len(right_cops)}点)')
        else:
            # 峰值图：绘制当帧COP点
            if left_cops:
                left_array = np.array(left_cops)
                ax.scatter(left_array[:, 0], left_array[:, 1], 
                          c='blue', s=50, alpha=0.8, marker='o', label='左脚COP')
                
            if right_cops:
                right_array = np.array(right_cops)
                ax.scatter(right_array[:, 0], right_array[:, 1], 
                          c='red', s=50, alpha=0.8, marker='s', label='右脚COP')
        
        # 绘制95%置信椭圆
        all_cops = left_cops + right_cops
        if len(all_cops) >= 3:
            ellipse = self.calculate_cop_ellipse(all_cops)
            if ellipse:
                ellipse.set_edgecolor('darkgreen')
                ellipse.set_linewidth(2)
                ellipse.set_label('95%置信椭圆')
                ax.add_patch(ellipse)
        
        # 添加10cm比例尺
        scale_length = 100  # 10cm = 100mm
        scale_x = ap_extent * 0.05  # 左下角5%位置
        scale_y = ml_extent * 0.05
        
        ax.plot([scale_x, scale_x + scale_length], [scale_y, scale_y], 
               'k-', linewidth=4, solid_capstyle='butt')
        ax.text(scale_x + scale_length/2, scale_y - ml_extent*0.03, 
               '10 cm', ha='center', va='top', fontsize=10, fontweight='bold')
        
        # 添加统一色标
        cbar = plt.colorbar(im, ax=ax, shrink=0.8, aspect=20)
        cbar.set_label('Pressure (AU)', fontsize=12, fontweight='bold')  # 标定后可改为kPa或N
        
        # 设置坐标轴
        ax.set_xlabel('AP (cm)', fontsize=12, fontweight='bold')
        ax.set_ylabel('ML (cm)', fontsize=12, fontweight='bold')
        ax.set_title(title, fontsize=14, fontweight='bold', pad=20)
        
        # 添加网格和图例
        ax.grid(True, alpha=0.3, linewidth=0.5)
        if ax.get_legend_handles_labels()[0]:  # 如果有图例项
            ax.legend(loc='upper right', fontsize=10, framealpha=0.9)
        
        plt.tight_layout()
        return self._fig_to_svg(fig)
    
    def generate_medical_heatmap_set(self, standing_df: pd.DataFrame, 
                                   tandem_df: pd.DataFrame, 
                                   walking_df: pd.DataFrame,
                                   base_title: str = "医院级热力图") -> Dict[str, str]:
        """
        生成完整的医院级热力图集
        
        Returns:
            dict: 包含所有热力图的字典
        """
        
        # 计算全局色标上限
        all_data = [df for df in [standing_df, tandem_df, walking_df] if df is not None]
        global_vmax = self.calculate_global_vmax(all_data)
        
        heatmaps = {}
        
        # 第4步：静态站立
        if standing_df is not None and len(standing_df) > 0:
            heatmaps['standing_average'] = self.create_medical_heatmap(
                standing_df, f"{base_title} - 第4步静态站立（平均）", global_vmax, "average"
            )
            heatmaps['standing_peak'] = self.create_medical_heatmap(
                standing_df, f"{base_title} - 第4步静态站立（峰值帧）", global_vmax, "peak"
            )
        
        # 第5步：前后脚站立
        if tandem_df is not None and len(tandem_df) > 0:
            heatmaps['tandem_average'] = self.create_medical_heatmap(
                tandem_df, f"{base_title} - 第5步前后脚站立（平均）", global_vmax, "average"
            )
            heatmaps['tandem_peak'] = self.create_medical_heatmap(
                tandem_df, f"{base_title} - 第5步前后脚站立（峰值帧）", global_vmax, "peak"
            )
        
        # 第6步：步行测试
        if walking_df is not None and len(walking_df) > 0:
            heatmaps['walking_average'] = self.create_medical_heatmap(
                walking_df, f"{base_title} - 第6步步行测试（平均）", global_vmax, "average"
            )
            heatmaps['walking_peak'] = self.create_medical_heatmap(
                walking_df, f"{base_title} - 第6步步行测试（峰值帧）", global_vmax, "peak"
            )
        
        return heatmaps
    
    def _fig_to_svg(self, fig) -> str:
        """将matplotlib图形转换为SVG字符串"""
        try:
            svg_buffer = io.StringIO()
            fig.savefig(svg_buffer, format='svg', dpi=self.config.dpi, 
                       bbox_inches='tight', facecolor='white', edgecolor='none')
            svg_buffer.seek(0)
            svg_content = svg_buffer.getvalue()
            plt.close(fig)
            
            # 清理SVG，确保内嵌
            svg_content = svg_content.replace('<?xml version="1.0" encoding="utf-8"?>', '')
            svg_content = svg_content.replace('<!DOCTYPE svg', '<!-- <!DOCTYPE svg')
            svg_content = svg_content.replace('>', '> -->', 1) if '<!DOCTYPE svg' in svg_content else svg_content
            
            return svg_content
            
        except Exception as e:
            print(f"⚠️ SVG转换失败: {e}")
            plt.close(fig)
            return f'<svg><text x="50" y="50">图表生成失败: {e}</text></svg>'


def create_medical_heatmaps_for_report(standing_df: pd.DataFrame,
                                     tandem_df: pd.DataFrame, 
                                     walking_df: pd.DataFrame,
                                     patient_name: str = "患者") -> Dict[str, str]:
    """
    为报告生成医院级热力图的便捷函数
    
    Args:
        standing_df: 第4步静态站立数据
        tandem_df: 第5步前后脚站立数据
        walking_df: 第6步步行数据
        patient_name: 患者姓名
        
    Returns:
        dict: 包含所有热力图SVG的字典
    """
    
    config = MedicalHeatmapConfig(
        ap_rows=64, ml_cols=32, mat_len_cm=300.0,
        global_vmax_percentile=99.0,
        contour_levels=[0.15, 0.40, 0.70],
        fig_width=10.0, fig_height=6.0,
        dpi=300
    )
    
    generator = MedicalHeatmapGenerator(config)
    
    return generator.generate_medical_heatmap_set(
        standing_df, tandem_df, walking_df, 
        base_title=f"{patient_name}足底压力分析"
    )


if __name__ == "__main__":
    print("✅ 医院级热力图生成器加载成功！")
    print("📊 支持特性:")
    print("   - 64×32矩阵，3米毯子物理标定")
    print("   - 统一色标（99百分位全局上限）")
    print("   - 等值线显示（15%/40%/70%）")
    print("   - 左右脚COP轨迹分离")
    print("   - 95%置信椭圆")
    print("   - 10cm物理比例尺")
    print("   - SVG矢量输出（300 DPI医疗级）")