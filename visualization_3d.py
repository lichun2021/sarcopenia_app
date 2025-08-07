#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
3D热力图可视化模块 - 增强版本
包含独立线程的3D热力图渲染，保持2D功能不变
"""

import numpy as np
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure
import matplotlib.colors as colors
import matplotlib.font_manager as fm
from mpl_toolkits.mplot3d import Axes3D
from scipy import ndimage
import threading
import time
import queue
from typing import Optional, Tuple, Dict, Any
import tkinter as tk
from tkinter import ttk
from concurrent.futures import ThreadPoolExecutor

# 导入原有的2D可视化类
from visualization import HeatmapVisualizer

# 解决中文字体警告问题
plt.rcParams['font.sans-serif'] = ['SimHei', 'DejaVu Sans', 'Arial Unicode MS', 'Microsoft YaHei']
plt.rcParams['axes.unicode_minus'] = False


class Heatmap3DRenderer:
    """3D热力图渲染器 - 独立线程处理"""
    
    def __init__(self, array_rows=32, array_cols=32, target_fps=5):
        self.array_rows = array_rows
        self.array_cols = array_cols
        self.target_fps = target_fps
        self.frame_interval = 1.0 / target_fps  # 目标帧间隔（降低到5FPS以减少负载）
        
        # 线程控制
        self.render_thread = None
        self.data_queue = queue.Queue(maxsize=1)  # 减小队列避免积压（设备12Hz vs 渲染4Hz）
        self.result_queue = queue.Queue(maxsize=1)  # 结果队列也限制大小
        self.is_running = False
        self.stop_event = threading.Event()
        
        # 3D视角参数 - 优化的观察角度
        self.elevation = 85  # 几乎垂直俯视
        self.azimuth = -90    # 正面观察
        
        # 渲染状态
        self.last_render_time = 0
        self.frame_count = 0
        self.render_stats = {
            'avg_render_time': 0,
            'fps': 0,
            'dropped_frames': 0
        }
        
        # 设置颜色映射
        self.setup_colormap()
        
    def setup_colormap(self):
        """设置3D热力图颜色映射 - 粒子式热力梯度"""
        # 粒子热力图颜色映射：蓝->青->绿->黄->橙->红
        colors_list = [
            '#0066FF',  # 蓝色（低压力）
            '#00CCFF',  # 青色
            '#00FF66',  # 绿色
            '#66FF00',  # 黄绿
            '#FFFF00',  # 黄色
            '#FF9900',  # 橙色
            '#FF3300',  # 红色（高压力）
            '#CC0000'   # 深红（最高压力）
        ]
        
        # 3D热力图专用颜色映射 - 提升精细度
        self.custom_cmap = colors.LinearSegmentedColormap.from_list(
            'pressure_3d_detailed', colors_list, N=256  # 增加到256级以提升精细度
        )
        self.norm = colors.Normalize(vmin=0, vmax=255)
        self.pressure_scale = 60.0 / 255.0  # mmHg per unit
    
    def _generate_footprint_particles(self, matrix_2d: np.ndarray) -> np.ndarray:
        """生成脚印粒子数据"""
        particles = []
        
        # 分析压力数据，识别脚印区域
        threshold = np.max(matrix_2d) * 0.1  # 压力阈值
        
        # 遍历每个点，根据压力值生成粒子
        for i in range(self.array_rows):
            for j in range(self.array_cols):
                pressure = matrix_2d[i, j]
                
                if pressure > threshold:
                    # 计算粒子密度（压力越大，粒子越多）
                    intensity = pressure / 255.0
                    particle_count = int(intensity * 5) + 1  # 1-5个粒子
                    
                    for _ in range(particle_count):
                        # 在该点周围随机生成粒子位置
                        x = j + np.random.normal(0, 0.3)
                        y = i + np.random.normal(0, 0.3)
                        z = intensity * 10 + np.random.uniform(0, 2)  # Z轴高度
                        
                        # 根据强度计算颜色
                        color = self._get_heatmap_color(intensity)
                        
                        # 粒子大小
                        size = (intensity * 30 + 10) * np.random.uniform(0.8, 1.2)
                        
                        particles.append([x, y, z, color[0], color[1], color[2], size])
        
        return np.array(particles) if particles else np.array([]).reshape(0, 7)
    
    def _get_heatmap_color(self, intensity: float) -> tuple:
        """根据强度获取热力图颜色"""
        # 蓝 -> 青 -> 绿 -> 黄 -> 橙 -> 红 渐变
        if intensity < 0.15:
            # 蓝色
            r, g, b = 0, 0.4, 1.0
        elif intensity < 0.3:
            # 蓝到青
            t = (intensity - 0.15) / 0.15
            r, g, b = 0, 0.4 + 0.4*t, 1.0
        elif intensity < 0.45:
            # 青到绿
            t = (intensity - 0.3) / 0.15
            r, g, b = 0, 0.8 + 0.2*t, 1.0 - 0.6*t
        elif intensity < 0.6:
            # 绿到黄
            t = (intensity - 0.45) / 0.15
            r, g, b = t, 1.0, 0.4 - 0.4*t
        elif intensity < 0.75:
            # 黄到橙
            t = (intensity - 0.6) / 0.15
            r, g, b = 1.0, 1.0 - 0.4*t, 0
        elif intensity < 0.9:
            # 橙到红
            t = (intensity - 0.75) / 0.15
            r, g, b = 1.0, 0.6 - 0.4*t, 0
        else:
            # 深红
            r, g, b = 0.8, 0.1, 0
        
        return (r, g, b)
        
    def start_rendering(self):
        """启动渲染线程"""
        if not self.is_running:
            self.is_running = True
            self.stop_event.clear()
            self.render_thread = threading.Thread(target=self._render_loop, daemon=True)
            self.render_thread.start()
    
    def stop_rendering(self):
        """停止渲染线程"""
        if self.is_running:
            self.is_running = False
            self.stop_event.set()
            if self.render_thread and self.render_thread.is_alive():
                self.render_thread.join(timeout=1.0)
    
    def update_data(self, matrix_2d: np.ndarray, statistics: Optional[Dict] = None):
        """提交新数据到渲染队列"""
        if not self.is_running:
            return
            
        try:
            # 非阻塞方式添加数据，如果队列满则丢弃旧数据
            if self.data_queue.full():
                try:
                    self.data_queue.get_nowait()  # 移除旧数据
                    self.render_stats['dropped_frames'] += 1
                except queue.Empty:
                    pass
            
            self.data_queue.put_nowait({
                'matrix': matrix_2d.copy(),
                'statistics': statistics,
                'timestamp': time.time()
            })
            
        except queue.Full:
            # 队列满，丢弃这一帧
            self.render_stats['dropped_frames'] += 1
    
    def get_rendered_result(self) -> Optional[Tuple[Figure, Dict]]:
        """获取渲染结果（非阻塞）"""
        try:
            return self.result_queue.get_nowait()
        except queue.Empty:
            return None
    
    def _render_loop(self):
        """渲染主循环"""
        while not self.stop_event.is_set():
            try:
                # 等待数据，带超时
                try:
                    data_item = self.data_queue.get(timeout=0.2)
                except queue.Empty:
                    continue
                
                # 检查帧率控制
                current_time = time.time()
                if current_time - self.last_render_time < self.frame_interval:
                    continue
                
                # 开始渲染
                render_start = time.time()
                
                # 执行3D渲染
                fig, render_info = self._render_3d_frame(
                    data_item['matrix'], 
                    data_item['statistics']
                )
                
                render_time = time.time() - render_start
                
                self.last_render_time = current_time
                self.frame_count += 1
                
                # 更新统计信息
                self._update_stats(render_time)
                
                # 将结果放入结果队列
                try:
                    if self.result_queue.full():
                        old_result = self.result_queue.get_nowait()
                        if old_result[0]:  # 关闭旧图形
                            plt.close(old_result[0])
                    
                    self.result_queue.put_nowait((fig, {
                        'render_time': render_time,
                        'frame_count': self.frame_count,
                        'stats': self.render_stats.copy()
                    }))
                    
                except queue.Full:
                    # 结果队列满，关闭旧图像以释放内存
                    if fig:
                        plt.close(fig)
                
            except Exception as e:
                # 只在严重错误时打印
                if "Figure" in str(e) or "memory" in str(e).lower():
                    print(f"[3D热力图] 严重错误: {e}")
                time.sleep(0.01)  # 防止错误循环
    
    def _render_3d_frame(self, matrix_2d: np.ndarray, statistics: Optional[Dict]) -> Tuple[Figure, Dict]:
        """渲染单个3D帧 - 粒子式脚印可视化"""
        # 检查数据
        if matrix_2d is None or matrix_2d.size == 0:
            return None, {}
        
        # 更新数组大小（如果改变）
        if matrix_2d.shape != (self.array_rows, self.array_cols):
            self.array_rows, self.array_cols = matrix_2d.shape
        
        try:
            # 创建适中尺寸的3D图形，深色背景
            fig = Figure(figsize=(10, 10), dpi=80, facecolor='#141428')
            fig.patch.set_facecolor('#141428')
            fig.patch.set_alpha(1.0)
            ax = fig.add_subplot(111, projection='3d', facecolor='#141428')
            
        except Exception as e:
            return None, {}
        
        try:
            # 检测脚印区域（基于压力数据）
            footprint_particles = self._generate_footprint_particles(matrix_2d)
            
            if len(footprint_particles) > 0:
                # 提取粒子数据
                x_coords = footprint_particles[:, 0]
                y_coords = footprint_particles[:, 1]
                z_coords = footprint_particles[:, 2]
                colors = footprint_particles[:, 3:6]
                sizes = footprint_particles[:, 6]
                
                # 绘制粒子散点图
                scatter = ax.scatter(
                    x_coords, y_coords, z_coords,
                    c=colors,
                    s=sizes,
                    alpha=0.8,
                    edgecolors='none',
                    marker='o'
                )
            
        except Exception as e:
            plt.close(fig)
            return None, {}
        
        try:
            # 设置固定俯视角度（稍微倾斜以显示3D效果）
            ax.view_init(elev=85, azim=-90)  # 几乎垂直俯视
            
            # 移除标题减少渲染
            ax.set_title('')
            
            # 完全隐藏所有坐标轴和边框
            ax.set_xlabel('')
            ax.set_ylabel('')
            ax.set_zlabel('')
            ax.set_xticks([])
            ax.set_yticks([])
            ax.set_zticks([])
            
            # 完全隐藏所有坐标轴线和网格
            ax.xaxis.set_visible(False)
            ax.yaxis.set_visible(False)
            ax.zaxis.set_visible(False)
            
            # 设置深色背景
            ax.xaxis.pane.fill = True
            ax.yaxis.pane.fill = True
            ax.zaxis.pane.fill = True
            ax.xaxis.pane.set_facecolor('#141428')
            ax.yaxis.pane.set_facecolor('#141428')
            ax.zaxis.pane.set_facecolor('#141428')
            ax.xaxis.pane.set_edgecolor('#141428')
            ax.yaxis.pane.set_edgecolor('#141428')
            ax.zaxis.pane.set_edgecolor('#141428')
            ax.xaxis.pane.set_alpha(1.0)
            ax.yaxis.pane.set_alpha(1.0)
            ax.zaxis.pane.set_alpha(1.0)
            
            # 隐藏3D立方体的边框线
            ax.xaxis.line.set_color((0.08, 0.08, 0.16, 0.0))
            ax.yaxis.line.set_color((0.08, 0.08, 0.16, 0.0))
            ax.zaxis.line.set_color((0.08, 0.08, 0.16, 0.0))
            
            # 设置坐标轴范围
            ax.set_xlim(0, self.array_cols-1)
            ax.set_ylim(0, self.array_rows-1)
            ax.set_zlim(0, 50)  # 固定Z轴范围
            
            # 设置3D轴的纵横比
            ax.set_box_aspect([1,1,0.2])  # x:y:z = 1:1:0.2，压缩z轴
            
            # 设置适中的边距，确保不被裁切且尽可能填满
            fig.subplots_adjust(left=0.1, right=0.9, top=0.9, bottom=0.1)
            
            return fig, {
                'max_value': np.max(matrix_2d),
                'min_value': np.min(matrix_2d),
                'mean_value': np.mean(matrix_2d)
            }
            
        except Exception as e:
            plt.close(fig)
            return None, {}
    
    def _update_stats(self, render_time: float):
        """更新渲染统计信息"""
        # 更新平均渲染时间（使用指数平滑）
        alpha = 0.1
        if self.render_stats['avg_render_time'] == 0:
            self.render_stats['avg_render_time'] = render_time
        else:
            self.render_stats['avg_render_time'] = (
                alpha * render_time + 
                (1 - alpha) * self.render_stats['avg_render_time']
            )
        
        # 计算实际FPS
        if self.render_stats['avg_render_time'] > 0:
            self.render_stats['fps'] = 1.0 / self.render_stats['avg_render_time']
        
    def set_view_angle(self, elevation: float, azimuth: float):
        """设置3D视角（优化的观察角度）"""
        # 使用优化的视角，忽略传入参数
        self.elevation = 85  # 几乎垂直俯视
        self.azimuth = -90    # 正面观察
    
    def get_stats(self) -> Dict:
        """获取渲染统计信息"""
        return {
            'is_running': self.is_running,
            'frame_count': self.frame_count,
            'target_fps': self.target_fps,
            'actual_fps': self.render_stats['fps'],
            'avg_render_time': self.render_stats['avg_render_time'],
            'dropped_frames': self.render_stats['dropped_frames'],
            'queue_size': self.data_queue.qsize()
        }


class IndependentCanvasContainer:
    """简化的独立Canvas容器"""
    
    def __init__(self, parent_frame):
        self.parent_frame = parent_frame
        self.canvas = None
        self.fig = None
        
        # 简化的更新控制 - 只防止重复更新
        self.is_updating = False
        
        # Canvas尺寸检测
        self.last_canvas_size = (0, 0)
        self.size_check_count = 0
        
        # 创建独立的canvas容器 - 完全填满，不要边距
        self.canvas_container = ttk.Frame(parent_frame)
        self.canvas_container.pack(fill='both', expand=True, padx=0, pady=0)
        
        # Canvas容器已创建
    
    def update_canvas_async(self, new_fig):
        """简化的canvas更新 - 基于测试成功的简单方案"""
        if new_fig is None:
            return
        
        # 防止重复更新
        if self.is_updating:
            print(f"[独立Canvas] 正在更新中，跳过")
            if new_fig:
                plt.close(new_fig)
            return
        
        print(f"[独立Canvas] 开始简化更新")
        self.is_updating = True
        
        try:
            # 直接在主线程更新，就像成功的简单测试一样
            self._simple_update(new_fig)
        except Exception as e:
            print(f"[独立Canvas] 更新失败: {e}")
            if new_fig:
                plt.close(new_fig)
        finally:
            self.is_updating = False
    
    def _simple_update(self, new_fig):
        """简单直接的更新方式 - 最小化闪烁"""
        print(f"[独立Canvas] 执行简单更新")
        
        # 先暂停绘制避免中间状态闪烁
        if self.canvas:
            self.canvas.get_tk_widget().update_idletasks()
        
        # 如果是第一次创建canvas
        if self.canvas is None:
            print(f"[独立Canvas] 首次创建canvas")
            self.canvas = FigureCanvasTkAgg(new_fig, master=self.canvas_container)
            canvas_widget = self.canvas.get_tk_widget()
            canvas_widget.pack(fill='both', expand=True)
            
            # 确保Canvas完全填满容器，没有任何边框
            canvas_widget.configure(highlightthickness=0, bd=0, relief='flat')
        else:
            # 快速替换canvas，减少闪烁时间
            print(f"[独立Canvas] 快速替换canvas")
            old_widget = self.canvas.get_tk_widget()
            
            # 关闭旧figure
            if self.fig:
                plt.close(self.fig)
            
            # 创建新canvas
            self.canvas = FigureCanvasTkAgg(new_fig, master=self.canvas_container)
            new_widget = self.canvas.get_tk_widget()
            new_widget.pack(fill='both', expand=True)
            new_widget.configure(highlightthickness=0, bd=0, relief='flat')
            
            # 销毁旧widget
            old_widget.destroy()
        
        # 直接绘制
        print(f"[独立Canvas] 执行绘制")
        self.canvas.draw_idle()
        print(f"[独立Canvas] 绘制完成")
        
        self.fig = new_fig
    
    def check_canvas_size(self):
        """检查Canvas尺寸变化"""
        try:
            if self.canvas and self.canvas.get_tk_widget():
                widget = self.canvas.get_tk_widget()
                current_width = widget.winfo_width()
                current_height = widget.winfo_height()
                current_size = (current_width, current_height)
                
                if current_size != self.last_canvas_size and current_width > 1 and current_height > 1:
                    print(f"[Canvas尺寸] 检测到尺寸变化: {self.last_canvas_size} -> {current_size}")
                    self.last_canvas_size = current_size
                    self.adjust_figure_centering()
                
        except Exception as e:
            print(f"[Canvas尺寸] 尺寸检测错误: {e}")
        finally:
            # 更频繁检查尺寸变化，特别是窗口最大化时
            self.parent_frame.after(2000, self.check_canvas_size)
    
    def adjust_figure_centering(self):
        """调整图形居中显示 - 简化版本，确保填满Canvas"""
        try:
            if not self.fig or not self.canvas:
                return
                
            print(f"[Canvas居中] 应用简化的居中布局")
            
            # 使用最简单的方式让图形填满Canvas
            if self.fig.axes:
                ax = self.fig.axes[0]
                
                # 设置适中的边距，确保不被裁切且居中显示
                self.fig.subplots_adjust(left=0.1, right=0.9, top=0.9, bottom=0.1)
                
                # 确保3D轴的纵横比合适
                try:
                    ax.set_box_aspect([1,1,0.3])  # 压缩z轴避免裁切
                except:
                    pass  # 某些matplotlib版本可能不支持
                
        except Exception as e:
            print(f"[Canvas居中] 居中调整错误: {e}")
    
    def clear(self):
        """清理canvas"""
        try:
            if self.canvas:
                self.canvas.get_tk_widget().destroy()
                self.canvas = None
            if self.fig:
                plt.close(self.fig)
                self.fig = None
        except Exception as e:
            print(f"[独立Canvas] 清理错误: {e}")
    
    def shutdown(self):
        """关闭容器"""
        try:
            self.clear()
            print("[独立Canvas] 已关闭")
        except Exception as e:
            print(f"[独立Canvas] 关闭错误: {e}")


class EnhancedHeatmapVisualizer:
    """增强热力图可视化器 - 支持2D和3D模式"""
    
    def __init__(self, parent_frame, array_rows=32, array_cols=32):
        self.parent_frame = parent_frame
        self.array_rows = array_rows
        self.array_cols = array_cols
        
        # 当前模式
        self.current_mode = "2D"  # "2D" 或 "3D"
        
        # 设置小尺寸的样式和白色背景
        style = ttk.Style()
        style.configure('Small.TRadiobutton', font=('Arial', 9), background='white')
        

        # 创建控制面板
        self.setup_control_panel()
        
        # 创建显示区域
        self.setup_display_area()
        
        # 初始化2D可视化器
        self.visualizer_2d = HeatmapVisualizer(
            self.display_2d_frame, 
            array_rows, 
            array_cols
        )


        
        # 初始化3D渲染器 - 进一步降低FPS减少闪烁
        self.renderer_3d = Heatmap3DRenderer(array_rows, array_cols, target_fps=2)
        
        # 创建独立的3D Canvas容器
        self.canvas_3d_container = IndependentCanvasContainer(self.display_3d_frame)
        
        # 启动3D渲染线程
        self.renderer_3d.start_rendering()
        
        # 定期检查3D渲染结果
        self.check_3d_results()
    
    def setup_control_panel(self):
        """设置控制面板"""
        # 创建白色背景的Frame
        self.control_frame = tk.Frame(self.parent_frame, bg='white')
        self.control_frame.pack(side='top', fill='x', padx=2, pady=1)
        
        # 模式切换按钮
        self.mode_var = tk.StringVar(value="2D")
        
        self.btn_2d = ttk.Radiobutton(
            self.control_frame, text="2D热力图", 
            variable=self.mode_var, value="2D",
            command=self.switch_to_2d,
            style='Small.TRadiobutton'
        )
        self.btn_2d.pack(side='left', padx=2)
        
        self.btn_3d = ttk.Radiobutton(
            self.control_frame, text="3D热力图", 
            variable=self.mode_var, value="3D",
            command=self.switch_to_3d,
            style='Small.TRadiobutton'
        )
        self.btn_3d.pack(side='left', padx=2)
        
        # 状态显示
        self.status_var = tk.StringVar(value="2D模式 - 实时渲染")
        self.status_label = ttk.Label(
            self.control_frame, 
            textvariable=self.status_var,
            font=('Arial', 8),
            background='white'
        )
        self.status_label.pack(side='right', padx=5)

    def setup_display_area(self):
        """设置分离的显示区域"""
        # 创建主显示容器
        self.main_display_frame = ttk.Frame(self.parent_frame)
        self.main_display_frame.pack(side='top', fill='both', expand=True)
        
        # 创建2D显示区域
        self.display_2d_frame = ttk.Frame(self.main_display_frame)
        self.display_2d_frame.pack(fill='both', expand=True)
        
        # 创建3D显示区域（初始隐藏）
        self.display_3d_frame = ttk.Frame(self.main_display_frame)
        # 不要pack，等切换到3D模式时再pack
    
    def switch_to_2d(self):
        """切换到2D模式"""
        if self.current_mode == "2D":
            return
            
        print("[可视化] 切换到2D模式")
        self.current_mode = "2D"
        
        # 隐藏3D区域
        self.display_3d_frame.pack_forget()
        
        # 显示2D区域
        self.display_2d_frame.pack(fill='both', expand=True)
        
        self.status_var.set("2D模式 - 实时渲染")
    
    def switch_to_3d(self):
        """切换到3D模式"""
        if self.current_mode == "3D":
            print("[可视化] 已经是3D模式，无需切换")
            return
            
        print("[可视化] 开始切换到3D模式")
        self.current_mode = "3D"
        
        print("[可视化] 隐藏2D区域")
        # 隐藏2D区域
        self.display_2d_frame.pack_forget()
        
        print("[可视化] 显示3D区域")
        # 显示3D区域
        self.display_3d_frame.pack(fill='both', expand=True)
        
        print("[可视化] 获取3D渲染器状态")
        stats = self.renderer_3d.get_stats()
        self.status_var.set(f"3D模式 - FPS: {stats['actual_fps']:.1f}")
        
        print("[可视化] 3D模式切换完成")
    
    def set_3d_view(self, elevation: float, azimuth: float):
        """设置3D视角（保留接口兼容性，但固定优化角度）"""
        # 固定使用优化的观察角度
        self.renderer_3d.set_view_angle(85, -90)
        
        if self.current_mode == "3D":
            stats = self.renderer_3d.get_stats()
            self.status_var.set(f"3D模式 - FPS: {stats['actual_fps']:.1f}")
    
    def update_data(self, matrix_2d, statistics=None):
        """更新显示数据"""
        try:
            # 检查数据有效性
            if matrix_2d is None or matrix_2d.size == 0:
                return
            
            # 总是更新2D（保持响应性）
            self.visualizer_2d.update_data(matrix_2d, statistics)
            
            # 如果是3D模式，也更新3D渲染器（但降低频率）
            if self.current_mode == "3D":
                # 只有当Canvas不在更新状态时才提交新数据
                if not self.canvas_3d_container.is_updating:
                    self.renderer_3d.update_data(matrix_2d, statistics)
                else:
                    print(f"[可视化] 3D Canvas正在更新，跳过数据更新")
                
        except Exception as e:
            print(f"[可视化] 数据更新错误: {e}")
    
    def check_3d_results(self):
        """定期检查3D渲染结果 - 使用独立Canvas容器"""
        try:
            if self.current_mode == "3D":
                result = self.renderer_3d.get_rendered_result()
                if result:
                    new_fig, render_info = result
                    
                    # 使用独立Canvas容器异步更新，不阻塞主UI
                    if new_fig:
                        self.canvas_3d_container.update_canvas_async(new_fig)
                        
                        # 更新状态
                        stats = render_info.get('stats', {})
                        fps = stats.get('actual_fps', 0)
                        self.status_var.set(f"3D模式 - FPS: {fps:.1f}")
                        
                        # 减少日志输出
                        frame_count = render_info.get('frame_count', 0)
                        if frame_count % 20 == 0:  # 每20帧打印一次
                            print(f"[可视化] 3D渲染正常，帧#{frame_count}, FPS: {fps:.1f}")
                # 移除"暂无结果"的日志，减少输出
                
        except Exception as e:
            print(f"[可视化] 3D结果检查错误: {e}")
            import traceback
            traceback.print_exc()
        finally:
            # 匹配更低帧率的检查频率，减少闪烁
            self.parent_frame.after(500, self.check_3d_results)  # 2 FPS检查频率，匹配渲染频率
    
    def set_array_size(self, rows, cols):
        """设置新的阵列大小"""
        self.array_rows = rows
        self.array_cols = cols
        
        # 更新2D可视化器
        self.visualizer_2d.set_array_size(rows, cols)
        
        # 更新3D渲染器
        self.renderer_3d.array_rows = rows
        self.renderer_3d.array_cols = cols
    
    def get_figure(self):
        """获取当前模式的图形对象"""
        if self.current_mode == "2D":
            return self.visualizer_2d.get_figure()
        else:
            return self.canvas_3d_container.fig
    
    def save_snapshot(self, filename):
        """保存当前显示的快照"""
        try:
            if self.current_mode == "2D":
                return self.visualizer_2d.save_snapshot(filename)
            else:
                if self.canvas_3d_container.fig:
                    self.canvas_3d_container.fig.savefig(filename, dpi=300, bbox_inches='tight')
                    return True
                return False
        except Exception as e:
            print(f"保存快照失败: {e}")
            return False
    
    def cleanup(self):
        """清理资源"""
        print("[可视化] 清理资源...")
        
        # 停止3D渲染线程
        self.renderer_3d.stop_rendering()
        
        # 关闭独立Canvas容器
        self.canvas_3d_container.shutdown()
        
        # 关闭图形对象
        if hasattr(self.visualizer_2d, 'fig'):
            plt.close(self.visualizer_2d.fig)
    
    def __del__(self):
        """析构函数"""
        try:
            self.cleanup()
        except:
            pass