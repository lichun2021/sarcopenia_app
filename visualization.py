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
from scipy.ndimage import zoom, gaussian_filter

# 解决中文字体警告问题
plt.rcParams['font.sans-serif'] = ['SimHei', 'DejaVu Sans', 'Arial Unicode MS', 'Microsoft YaHei']
plt.rcParams['axes.unicode_minus'] = False  # 解决保存图像是负号'-'显示为方块的问题

class HeatmapVisualizer:
    """热力图可视化器类"""
    
    def __init__(self, parent_frame, array_rows=32, array_cols=32):
        self.parent_frame = parent_frame
        self.array_rows = array_rows
        self.array_cols = array_cols
        
        # 高质量渲染参数
        self.enable_high_quality = True  # 启用高质量渲染
        self.upscale_factor = 4          # 升采样倍数（32x32 -> 128x128）
        self.gaussian_sigma = 1.2        # 高斯平滑参数
        self.interpolation_order = 3     # 双三次插值（order=3）
        
        # 平滑处理参数 - 用于快速模式
        self.enable_smoothing = False    # 快速模式的简单平滑
        self.smooth_sigma = 0.5          # 快速模式的sigma值
        
        # 性能优化参数
        self.frame_skip_counter = 0
        self.frame_skip_threshold = 2  # 每3帧渲染1帧
        self.last_render_time = 0
        self.min_render_interval = 0.033  # 最小渲染间隔33ms (30fps)
        
        # 创建强对比度颜色映射
        self.setup_colormap()
        
        # 创建matplotlib图形
        self.setup_figure()
        
    def setup_colormap(self):
        """设置医学专用热力图颜色映射 - 256级医院精度"""
        # 使用matplotlib内置的jet色谱作为基础，这是医学影像的标准配色
        import matplotlib.cm as cm
        
        # 获取jet色谱并创建副本
        self.jet_cmap = cm.get_cmap('jet').copy()
        
        # 设置坏值（NaN）为透明
        self.jet_cmap.set_bad(color=(0, 0, 0, 0))
        
        # 创建256级精细渐变色谱，确保每个压力值都有独特的颜色
        # 医院级压力成像标准：深蓝→蓝→青→绿→黄→橙→红→深红
        
        # 定义关键颜色节点（基于jet色谱的改进版）
        colors_nodes = [
            (0.0,    '#000033'),  # 0: 深蓝黑（无压力）
            (0.125,  '#0000FF'),  # 32: 纯蓝
            (0.25,   '#0080FF'),  # 64: 亮蓝
            (0.375,  '#00FFFF'),  # 96: 青色
            (0.5,    '#00FF00'),  # 128: 纯绿
            (0.625,  '#FFFF00'),  # 160: 黄色
            (0.75,   '#FF8000'),  # 192: 橙色
            (0.875,  '#FF0000'),  # 224: 纯红
            (1.0,    '#800000')   # 255: 深红（最大压力）
        ]
        
        # 创建256个离散颜色值，确保每个0-255的值都有唯一颜色
        import numpy as np
        positions = np.array([node[0] for node in colors_nodes])
        colors_hex = [node[1] for node in colors_nodes]
        
        # 转换hex颜色到RGB
        colors_rgb = []
        for hex_color in colors_hex:
            r = int(hex_color[1:3], 16) / 255.0
            g = int(hex_color[3:5], 16) / 255.0
            b = int(hex_color[5:7], 16) / 255.0
            colors_rgb.append((r, g, b))
        
        # 创建256个插值颜色
        colors_256 = []
        for i in range(256):
            # 归一化位置 (0-255 -> 0-1)
            norm_pos = i / 255.0
            
            # 找到插值区间
            idx = np.searchsorted(positions, norm_pos)
            if idx == 0:
                colors_256.append(colors_rgb[0])
            elif idx >= len(positions):
                colors_256.append(colors_rgb[-1])
            else:
                # 线性插值
                pos1, pos2 = positions[idx-1], positions[idx]
                c1, c2 = colors_rgb[idx-1], colors_rgb[idx]
                t = (norm_pos - pos1) / (pos2 - pos1)
                
                r = c1[0] * (1-t) + c2[0] * t
                g = c1[1] * (1-t) + c2[1] * t
                b = c1[2] * (1-t) + c2[2] * t
                colors_256.append((r, g, b))
        
        # 创建256级离散颜色映射，每个值对应一个独特颜色
        self.custom_cmap = colors.ListedColormap(colors_256, name='medical_pressure_256', N=256)
        
        # 也创建连续版本用于平滑显示
        self.continuous_cmap = colors.LinearSegmentedColormap.from_list(
            'medical_pressure_continuous', 
            [node[1] for node in colors_nodes], 
            N=256  # 256级插值精度
        )
        
        # 使用简单线性归一化
        self.norm = colors.Normalize(vmin=0, vmax=255)
        
        # 压力单位转换：0-255 对应 0-60mmHg（硬件标定压力范围）
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
    
    def apply_high_quality_rendering(self, data_matrix):
        """应用高质量渲染：升采样 + 双三次插值 + 高斯平滑"""
        if not self.enable_high_quality:
            return self.smooth_data(data_matrix)
        
        try:
            # 1. 先进行升采样（双三次插值）
            upscaled = zoom(data_matrix, self.upscale_factor, order=self.interpolation_order)
            
            # 2. 应用高斯平滑，消除像素化边界
            smoothed = gaussian_filter(upscaled, sigma=self.gaussian_sigma)
            
            return smoothed
        except Exception as e:
            # 如果高质量渲染失败，回退到普通平滑
            print(f"高质量渲染失败，使用普通模式: {e}")
            return self.smooth_data(data_matrix)
        
    def setup_figure(self):
        """设置matplotlib图形"""
        # 根据数组尺寸调整图形大小
        aspect_ratio = self.array_cols / self.array_rows
        
        # 基于数据真实比例计算最佳显示尺寸，同时最大化利用显示空间
        if aspect_ratio > 1.5:  # 宽矩形（如32x64=2.0, 32x96=3.0）
            # 让宽矩形尽可能占满水平空间
            base_width = 16  # 更大的宽度
            figsize = (base_width, base_width / aspect_ratio)
        elif aspect_ratio < 0.7:  # 高矩形（如64x32, 96x32）
            # 让高矩形尽可能占满垂直空间
            base_height = 12
            figsize = (base_height * aspect_ratio, base_height)
        else:  # 接近正方形
            figsize = (12, 12)
        
        self.fig = Figure(figsize=figsize, dpi=100, facecolor='#1a1a1a')  # 深灰色背景
        self.ax = self.fig.add_subplot(111, facecolor='black')  # 纯黑色数据区域
        
        # 初始化数据
        initial_data = np.zeros((self.array_rows, self.array_cols))
        
        # 创建热力图 - 医院级精度设置
        # 根据是否启用高质量模式选择插值方法
        interpolation_method = 'bicubic' if self.enable_high_quality else 'nearest'
        
        self.im = self.ax.imshow(
            initial_data, 
            cmap=self.continuous_cmap if self.enable_high_quality else self.custom_cmap,  # 高质量用连续色谱
            norm=self.norm,
            interpolation=interpolation_method,  # 高质量用双三次，否则最近邻
            aspect='equal',            # 保持像素点正方形，确保正确比例显示
            animated=True,             # 启用动画模式提高性能
            alpha=1.0,                 # 去掉透明度提升性能
            rasterized=True            # 栅格化渲染提升性能
        )
        
        # 设置标题和标签 - 移除轴标签，只保留刻度
        # self.update_title()
        # 移除X/Y轴标签以简化界面
        
        # 为提升性能，完全移除网格线
        # 网格线会增加渲染开销，影响实时性能
        
        # 设置坐标轴标签（白色文字）
        self.ax.set_xticks(range(0, self.array_cols, max(1, self.array_cols//8)))
        self.ax.set_yticks(range(0, self.array_rows, max(1, self.array_rows//8)))
        self.ax.tick_params(colors='white', which='both')  # 设置刻度颜色为白色
        
        # 添加颜色条（医学风格）
        self.colorbar = self.fig.colorbar(self.im, ax=self.ax, fraction=0.046, pad=0.04)
        self.colorbar.set_label('Pressure (mmHg)', rotation=270, labelpad=25, fontsize=14, 
                                fontweight='bold', color='white')
        self.colorbar.ax.yaxis.set_tick_params(color='white', labelcolor='white')
        
        # 设置颜色条标签 - 医院级精度，256级显示
        # 更密集的刻度点，展示256级精度
        tick_positions = [0, 32, 64, 96, 128, 160, 192, 224, 255]  # 9个刻度点
        tick_labels = [f'{int(pos * self.pressure_scale):.0f}' for pos in tick_positions]
        self.colorbar.set_ticks(tick_positions)
        self.colorbar.set_ticklabels(tick_labels)
        
        # 添加次要刻度，展示更高精度
        minor_ticks = list(range(0, 256, 16))  # 每16个值一个次要刻度
        self.colorbar.ax.yaxis.set_ticks(minor_ticks, minor=True)
        self.colorbar.ax.yaxis.set_tick_params(which='minor', length=3, color='white')
        
        # 设置坐标轴范围，确保热力图填满整个显示区域
        self.ax.set_xlim(-0.5, self.array_cols - 0.5)
        self.ax.set_ylim(self.array_rows - 0.5, -0.5)  # 翻转Y轴，让(0,0)在左上角
        
        # 调整布局，为颜色条预留空间，让热力图尽可能大
        self.fig.subplots_adjust(left=0.05, right=0.8, top=0.95, bottom=0.05)
        
        # 嵌入到tkinter
        self.canvas = FigureCanvasTkAgg(self.fig, master=self.parent_frame)
        self.canvas.draw()
        self.canvas.get_tk_widget().pack(fill='both', expand=True)
        
    # def update_title(self):
    #     """更新标题"""
    #     title = f'Medical Pressure Imaging ({self.array_rows}x{self.array_cols})'
    #     self.ax.set_title(title, fontsize=16, fontweight='bold', pad=20, color='white')
        
    def update_data(self, matrix_2d, statistics=None):
        """更新显示数据 - 带帧跳跃优化"""
        try:
            # 检查数据有效性
            if matrix_2d is None or matrix_2d.size == 0:
                return
            
            # 帧跳跃优化：控制渲染频率
            import time
            current_time = time.time()
            
            # 如果距离上次渲染时间太短，跳过此帧
            if current_time - self.last_render_time < self.min_render_interval:
                self.frame_skip_counter += 1
                if self.frame_skip_counter < self.frame_skip_threshold:
                    return
            
            # 重置计数器并记录渲染时间
            self.frame_skip_counter = 0
            self.last_render_time = current_time
            
            # 应用高质量渲染或平滑处理
            if self.enable_high_quality:
                smoothed_matrix = self.apply_high_quality_rendering(matrix_2d)
            else:
                smoothed_matrix = self.smooth_data(matrix_2d)
            
            # 检查数组大小是否改变，如果改变需要重新配置
            if matrix_2d.shape != (self.array_rows, self.array_cols):
                self.array_rows, self.array_cols = matrix_2d.shape
                # 需要重新设置图像大小
                self.set_array_size(self.array_rows, self.array_cols)
                # 重新设置后，继续用新数据更新（不要return）
                if self.enable_high_quality:
                    smoothed_matrix = self.apply_high_quality_rendering(matrix_2d)
                else:
                    smoothed_matrix = self.smooth_data(matrix_2d)
            
            # 更新热力图数据
            self.im.set_array(smoothed_matrix)
            
            # 确保颜色映射范围正确
            self.im.set_clim(0, 255)
            
            # 更新标题包含统计信息（白色文字）
            # if statistics:
                # max_mmhg = statistics["max_value"] * self.pressure_scale
                # min_mmhg = statistics["min_value"] * self.pressure_scale
                # avg_mmhg = statistics["mean_value"] * self.pressure_scale
                # title = f'Medical Pressure Imaging ({self.array_rows}x{self.array_cols}) - '
                # title += f'Max:{max_mmhg:.1f} Min:{min_mmhg:.1f} Avg:{avg_mmhg:.1f}mmHg'
                # self.ax.set_title(title, fontsize=16, fontweight='bold', pad=20, color='white')
            
            # 使用快速重绘，只更新数据区域
            self.canvas.draw_idle()  # 使用idle绘制，减少频繁重绘
            
        except Exception as e:
            pass
            
    def set_array_size(self, rows, cols):
        """设置新的阵列大小"""
        if rows != self.array_rows or cols != self.array_cols:
            self.array_rows = rows
            self.array_cols = cols
            
            # 根据新的数组尺寸调整图形大小
            aspect_ratio = self.array_cols / self.array_rows
            
            # 基于数据真实比例计算最佳显示尺寸，同时最大化利用显示空间
            if aspect_ratio > 1.5:  # 宽矩形（如32x64=2.0, 32x96=3.0）
                # 让宽矩形尽可能占满水平空间
                base_width = 16  # 更大的宽度
                figsize = (base_width, base_width / aspect_ratio)
            elif aspect_ratio < 0.7:  # 高矩形（如64x32, 96x32）
                # 让高矩形尽可能占满垂直空间
                base_height = 12
                figsize = (base_height * aspect_ratio, base_height)
            else:  # 接近正方形
                figsize = (12, 12)
                
            self.fig.set_figwidth(figsize[0])
            self.fig.set_figheight(figsize[1])
            
            # 清除旧的图形
            self.ax.clear()
            
            # 重新创建图形组件
            initial_data = np.zeros((self.array_rows, self.array_cols))
            
            # 创建热力图 - 医院级精度设置
            # 根据是否启用高质量模式选择插值方法
            interpolation_method = 'bicubic' if self.enable_high_quality else 'nearest'
            
            self.im = self.ax.imshow(
                initial_data, 
                cmap=self.continuous_cmap if self.enable_high_quality else self.custom_cmap,  # 高质量用连续色谱
                norm=self.norm,
                interpolation=interpolation_method,  # 高质量用双三次，否则最近邻
                aspect='equal',
                animated=True,
                alpha=1.0,
                rasterized=True
            )
            
            # 更新标题
            # self.update_title()
            
            # 设置坐标轴
            self.ax.set_xticks(range(0, self.array_cols, max(1, self.array_cols//8)))
            self.ax.set_yticks(range(0, self.array_rows, max(1, self.array_rows//8)))
            
            # 重新添加颜色条（如果不存在）
            if not hasattr(self, 'colorbar') or self.colorbar is None:
                self.colorbar = self.fig.colorbar(self.im, ax=self.ax, fraction=0.046, pad=0.04)
                self.colorbar.set_label('Pressure (mmHg)', rotation=270, labelpad=25, fontsize=14, fontweight='bold')
                
                # 设置颜色条标签 - 医院级精度
                tick_positions = [0, 32, 64, 96, 128, 160, 192, 224, 255]
                tick_labels = [f'{int(pos * self.pressure_scale):.0f}' for pos in tick_positions]
                self.colorbar.set_ticks(tick_positions)
                self.colorbar.set_ticklabels(tick_labels)
                
                # 添加次要刻度
                minor_ticks = list(range(0, 256, 16))
                self.colorbar.ax.yaxis.set_ticks(minor_ticks, minor=True)
                self.colorbar.ax.yaxis.set_tick_params(which='minor', length=3, color='white')
            
            # 设置坐标轴范围，确保热力图填满整个显示区域
            self.ax.set_xlim(-0.5, self.array_cols - 0.5)
            self.ax.set_ylim(self.array_rows - 0.5, -0.5)  # 翻转Y轴，让(0,0)在左上角
            
            # 调整布局，为颜色条预留空间，让热力图尽可能大
            self.fig.subplots_adjust(left=0.05, right=0.8, top=0.95, bottom=0.05)
            
            # 关键：重新计算紧凑布局，适应新的宽高比
            self.fig.tight_layout()
            
            # 强制canvas重新调整大小以适应新的figure
            canvas_widget = self.canvas.get_tk_widget()
            canvas_widget.pack_forget()  # 先取消pack
            canvas_widget.pack(fill='both', expand=True)  # 重新pack
            
            # 关键：强制更新tkinter布局，获取正确的canvas大小
            canvas_widget.update_idletasks()
            
            # 手动触发matplotlib的resize事件，模拟窗口缩放的效果
            # 获取canvas的当前大小
            canvas_width = canvas_widget.winfo_width()
            canvas_height = canvas_widget.winfo_height()
            
            # 只有当canvas有有效大小时才触发resize
            if canvas_width > 1 and canvas_height > 1:
                # 手动触发matplotlib的resize，模拟窗口大小变化
                # 创建一个resize事件并处理
                try:
                    self.canvas.resize(canvas_width, canvas_height)
                except:
                    # 如果resize方法不存在，尝试其他方法
                    try:
                        # 强制重新计算figure大小
                        self.fig.set_size_inches(canvas_width/100, canvas_height/100)
                        self.fig.tight_layout()
                    except:
                        pass
            
            # 重绘画布
            self.canvas.draw()
            
    def get_figure(self):
        """获取matplotlib图形对象"""
        return self.fig
    
    def set_quality_mode(self, high_quality=True):
        """切换渲染质量模式
        
        Args:
            high_quality: True为高质量模式（升采样+平滑），False为快速模式
        """
        self.enable_high_quality = high_quality
        if high_quality:
            # 高质量模式参数
            self.upscale_factor = 4
            self.gaussian_sigma = 1.2
            self.interpolation_order = 3
            print("已切换到高质量渲染模式（128x128，双三次插值）")
        else:
            # 快速模式参数
            self.enable_smoothing = False
            print("已切换到快速渲染模式（原始分辨率）")
        
        # 重新设置图像插值方法
        if hasattr(self, 'im'):
            interpolation_method = 'bicubic' if high_quality else 'nearest'
            cmap = self.continuous_cmap if high_quality else self.custom_cmap
            self.im.set_interpolation(interpolation_method)
            self.im.set_cmap(cmap)
            self.canvas.draw_idle()
    
    def save_snapshot(self, filename):
        """保存热力图快照"""
        try:
            self.fig.savefig(filename, dpi=300, bbox_inches='tight')
            return True
        except Exception as e:
            print(f"保存快照失败: {e}")
            return False 