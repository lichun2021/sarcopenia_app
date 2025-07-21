#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
可视化模块 - 负责压力传感器数据的图形显示
"""

import numpy as np
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure
import matplotlib.colors as colors
import matplotlib.font_manager as fm
from scipy import ndimage

# 解决中文字体警告问题
plt.rcParams['font.sans-serif'] = ['SimHei', 'DejaVu Sans', 'Arial Unicode MS', 'Microsoft YaHei']
plt.rcParams['axes.unicode_minus'] = False  # 解决保存图像是负号'-'显示为方块的问题

class HeatmapVisualizer:
    """热力图可视化器类"""
    
    def __init__(self, parent_frame, array_rows=32, array_cols=32):
        self.parent_frame = parent_frame
        self.array_rows = array_rows
        self.array_cols = array_cols
        
        # 平滑处理参数 - 默认关闭以提升性能
        self.enable_smoothing = False  # 关闭平滑处理提升性能
        self.smooth_sigma = 0.5        # 减小sigma值降低计算量
        
        # 创建强对比度颜色映射
        self.setup_colormap()
        
        # 创建matplotlib图形
        self.setup_figure()
        
    def setup_colormap(self):
        """设置高性能颜色映射 - 简化版本保持效果但提升性能"""
        # 简化为8个关键颜色点，保持低压力区域对比度
        colors_list = [
            '#FFFFFF',  # 纯白（0压力）
            '#80C0FF',  # 明亮浅蓝（低压力明显）
            '#1A8CFF',  # 明亮蓝
            '#0066CC',  # 深蓝
            '#003366',  # 深蓝紫
            '#4A148C',  # 紫色
            '#B71C1C',  # 深红
            '#2E0000'   # 极深（最高压力）
        ]
        
        # 简单线性分布，减少计算开销
        self.custom_cmap = colors.LinearSegmentedColormap.from_list(
            'fast_pressure', colors_list, N=64  # 减少到64级，提升性能
        )
        
        # 使用简单线性归一化，取消Gamma校正以提升性能
        self.norm = colors.Normalize(vmin=0, vmax=255)
        
        # 压力单位转换：0-255 对应 0-60mmHg
        self.pressure_scale = 60.0 / 255.0  # mmHg per unit
    
    def smooth_data(self, data_matrix):
        """对数据进行高斯平滑处理，进一步消除边界感"""
        if not self.enable_smoothing:
            return data_matrix
        
        try:
            # 使用高斯滤波进行平滑处理
            smoothed = ndimage.gaussian_filter(data_matrix, sigma=self.smooth_sigma, mode='nearest')
            return smoothed
        except:
            # 如果scipy不可用，返回原数据
            return data_matrix
        
    def setup_figure(self):
        """设置matplotlib图形"""
        # 创建图形，增大尺寸以便看清细节
        self.fig = Figure(figsize=(10, 10), dpi=100, facecolor='white')
        self.ax = self.fig.add_subplot(111)
        
        # 初始化数据
        initial_data = np.zeros((self.array_rows, self.array_cols))
        
        # 创建热力图 - 优化性能设置
        self.im = self.ax.imshow(
            initial_data, 
            cmap=self.custom_cmap,
            norm=self.norm,
            interpolation='bilinear',  # 双线性插值，性能与效果的平衡
            aspect='equal',
            animated=True,             # 启用动画模式提高性能
            alpha=1.0,                 # 去掉透明度提升性能
            rasterized=True            # 栅格化渲染提升性能
        )
        
        # 设置标题和标签 - 移除轴标签，只保留刻度
        self.update_title()
        # 移除X/Y轴标签以简化界面
        
        # 为提升性能，完全移除网格线
        # 网格线会增加渲染开销，影响实时性能
        
        # 设置坐标轴标签
        self.ax.set_xticks(range(0, self.array_cols, max(1, self.array_cols//8)))
        self.ax.set_yticks(range(0, self.array_rows, max(1, self.array_rows//8)))
        
        # 添加颜色条
        cbar = self.fig.colorbar(self.im, ax=self.ax, fraction=0.046, pad=0.04)
        cbar.set_label('Pressure (mmHg)', rotation=270, labelpad=25, fontsize=14, fontweight='bold')
        
        # 设置颜色条标签 - 显示mmHg单位，0-255对应0-60mmHg
        tick_positions = [0, 42, 85, 128, 170, 213, 255]  # 更多刻度点
        tick_labels = [f'{int(pos * self.pressure_scale)}' for pos in tick_positions]
        cbar.set_ticks(tick_positions)
        cbar.set_ticklabels(tick_labels)
        
        # 调整布局
        self.fig.tight_layout()
        
        # 嵌入到tkinter
        self.canvas = FigureCanvasTkAgg(self.fig, master=self.parent_frame)
        self.canvas.draw()
        self.canvas.get_tk_widget().pack(fill='both', expand=True)
        
    def update_title(self):
        """更新标题"""
        title = f'Pressure Sensor ({self.array_rows}x{self.array_cols}) - Smooth Gradient'
        self.ax.set_title(title, fontsize=16, fontweight='bold', pad=20)
        
    def update_data(self, matrix_2d, statistics=None):
        """更新显示数据"""
        try:
            # 应用平滑处理
            smoothed_matrix = self.smooth_data(matrix_2d)
            
            # 更新热力图数据
            self.im.set_array(smoothed_matrix)
            
            # 简化数组大小检查，减少重配置开销
            if matrix_2d.shape != (self.array_rows, self.array_cols):
                self.array_rows, self.array_cols = matrix_2d.shape
                # 只更新标题，其他配置保持不变以提升性能
            
            # 更新标题包含统计信息
            if statistics:
                max_mmhg = statistics["max_value"] * self.pressure_scale
                min_mmhg = statistics["min_value"] * self.pressure_scale
                avg_mmhg = statistics["mean_value"] * self.pressure_scale
                title = f'Pressure ({self.array_rows}x{self.array_cols}) - '
                title += f'Max:{max_mmhg:.1f} Min:{min_mmhg:.1f} Avg:{avg_mmhg:.1f}mmHg'
                self.ax.set_title(title, fontsize=16, fontweight='bold', pad=20)
            
            # 使用快速重绘，只更新数据区域
            self.canvas.draw_idle()  # 使用idle绘制，减少频繁重绘
            
        except Exception as e:
            print(f"更新热力图时出错: {e}")
            
    def set_array_size(self, rows, cols):
        """设置新的阵列大小"""
        if rows != self.array_rows or cols != self.array_cols:
            self.array_rows = rows
            self.array_cols = cols
            
            # 清除旧的图形
            self.ax.clear()
            
            # 重新设置图形
            self.setup_figure()
            
    def get_figure(self):
        """获取matplotlib图形对象"""
        return self.fig
    
    def save_snapshot(self, filename):
        """保存热力图快照"""
        try:
            self.fig.savefig(filename, dpi=300, bbox_inches='tight')
            return True
        except Exception as e:
            print(f"保存快照失败: {e}")
            return False 