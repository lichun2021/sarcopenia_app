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
        self.elevation = 75  # 稍微倾斜的俯视角度，更清晰
        self.azimuth = 45    # 45度方位角，显示立体感
        
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
        """设置3D热力图颜色映射 - 256级医院精度（与2D同步）"""
        # 创建256级精细渐变色谱，与2D完全一致
        # 医院级压力成像标准：黑→深蓝→蓝→青→绿→黄→橙→红→深红→紫→白
        
        # 定义关键颜色节点（11个节点创建平滑过渡）
        colors_nodes = [
            (0.0,    '#000000'),  # 0: 纯黑（无压力）
            (0.1,    '#000066'),  # 25.5: 深蓝
            (0.2,    '#0000FF'),  # 51: 纯蓝
            (0.3,    '#0066FF'),  # 76.5: 亮蓝
            (0.4,    '#00CCFF'),  # 102: 青色
            (0.5,    '#00FF00'),  # 127.5: 纯绿
            (0.6,    '#FFFF00'),  # 153: 黄色
            (0.7,    '#FF9900'),  # 178.5: 橙色
            (0.8,    '#FF0000'),  # 204: 纯红
            (0.9,    '#FF00FF'),  # 229.5: 洋红
            (1.0,    '#FFFFFF')   # 255: 纯白（最大压力）
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
        self.custom_cmap = colors.ListedColormap(colors_256, name='medical_pressure_3d_256', N=256)
        self.norm = colors.Normalize(vmin=0, vmax=255)
        self.pressure_scale = 60.0 / 255.0  # mmHg per unit
        
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
            # 数据已提交到队列
            
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
        loop_count = 0
        
        while not self.stop_event.is_set():
            try:
                loop_count += 1
                
                # 等待数据，带超时
                try:
                    data_item = self.data_queue.get(timeout=0.2)  # 增加超时时间匹配低帧率
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
                        # 减少频繁的旧结果移除输出
                    
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
                print(f"[3D热力图] 渲染错误: {e}")
                import traceback
                traceback.print_exc()
                time.sleep(0.01)  # 防止错误循环
    
    def _render_3d_frame(self, matrix_2d: np.ndarray, statistics: Optional[Dict]) -> Tuple[Figure, Dict]:
        """渲染单个3D帧 - 高性能版本，支持矩形设备"""
        
        # 检查数据
        if matrix_2d is None or matrix_2d.size == 0:
            return None, {}
        
        # 更新数组大小（如果改变）
        if matrix_2d.shape != (self.array_rows, self.array_cols):
            self.array_rows, self.array_cols = matrix_2d.shape
        
        try:
            # 根据数组尺寸调整图形大小，确保矩形设备显示正确
            aspect_ratio = self.array_cols / self.array_rows
            
            # 调整阈值，确保32x32正确识别为正方形
            if aspect_ratio > 1.6:  # 明显的宽矩形（如32x64=2.0）
                figsize = (12, 8)  # 宽矩形图形
            elif aspect_ratio < 0.625:  # 明显的高矩形（如32x64转置）
                figsize = (8, 12)  # 高矩形图形
            else:  # 正方形或接近正方形（包括32x32=1.0）
                figsize = (10, 10)
                
            fig = Figure(figsize=figsize, dpi=80, facecolor='none')
            fig.patch.set_facecolor('none')
            fig.patch.set_alpha(0)
            ax = fig.add_subplot(111, projection='3d')
            
        except Exception as e:
            print(f"[3D渲染] Figure或3D子图创建失败: {e}")
            import traceback
            traceback.print_exc()
            return None, {}
        
        try:
            # 创建基本网格坐标
            x = np.linspace(0, self.array_cols-1, self.array_cols)
            y = np.linspace(0, self.array_rows-1, self.array_rows)
            X, Y = np.meshgrid(x, y)
            
            # Z轴数据（更小的缩放因子）
            Z = matrix_2d * 0.15
            
            # 创建3D表面图，使用高精度颜色映射
            surf = ax.plot_surface(
                X, Y, Z,
                facecolors=self.custom_cmap(self.norm(matrix_2d)),  # 使用原始数据做颜色映射
                alpha=0.9,
                linewidth=0,
                antialiased=True,  # 开启抗锯齿提升细节
                shade=False,  # 关闭阴影保持颜色纯净
                rasterized=True
            )
            
        except Exception as e:
            print(f"[3D渲染] 创建3D表面图失败: {e}")
            import traceback
            traceback.print_exc()
            plt.close(fig)
            return None, {}
        
        try:
            # 设置固定俯视角度
            ax.view_init(elev=self.elevation, azim=self.azimuth)
            
            # 完全移除等高线（性能杀手）
            
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
            
            # 隐藏3D坐标轴的线框和边线
            ax.xaxis.pane.fill = False
            ax.yaxis.pane.fill = False
            ax.zaxis.pane.fill = False
            ax.xaxis.pane.set_edgecolor('none')
            ax.yaxis.pane.set_edgecolor('none')
            ax.zaxis.pane.set_edgecolor('none')
            ax.xaxis.pane.set_linewidth(0)
            ax.yaxis.pane.set_linewidth(0)
            ax.zaxis.pane.set_linewidth(0)
            
            # 设置背景为透明
            ax.xaxis.pane.set_facecolor('none')
            ax.yaxis.pane.set_facecolor('none')
            ax.zaxis.pane.set_facecolor('none')
            ax.xaxis.pane.set_alpha(0)
            ax.yaxis.pane.set_alpha(0)
            ax.zaxis.pane.set_alpha(0)
            
            # 隐藏3D立方体的边框线
            ax.xaxis.line.set_color((1.0, 1.0, 1.0, 0.0))
            ax.yaxis.line.set_color((1.0, 1.0, 1.0, 0.0))
            ax.zaxis.line.set_color((1.0, 1.0, 1.0, 0.0))
            
            # 设置坐标轴范围 - 真正居中
            ax.set_xlim(0, self.array_cols-1)
            ax.set_ylim(0, self.array_rows-1)
            ax.set_zlim(0, np.max(Z) * 1.2 if np.max(Z) > 0 else 50)
            
            # 设置3D轴的纵横比以防止变形和裁切，支持矩形设备
            aspect_ratio = self.array_cols / self.array_rows
            if aspect_ratio > 1.6:  # 明显的宽矩形（如32x64的步道）
                ax.set_box_aspect([aspect_ratio, 1, 0.3])  # 保持实际比例
            elif aspect_ratio < 0.625:  # 明显的高矩形
                ax.set_box_aspect([1, 1/aspect_ratio, 0.3])  # 保持实际比例
            else:  # 正方形或接近正方形（包括32x32）
                ax.set_box_aspect([1, 1, 0.3])  # 标准正方形比例
            
            # 设置适中的边距，确保不被裁切且尽可能填满
            fig.subplots_adjust(left=0.1, right=0.9, top=0.9, bottom=0.1)
            return fig, {
                'max_value': np.max(matrix_2d),
                'min_value': np.min(matrix_2d),
                'mean_value': np.mean(matrix_2d)
            }
            
        except Exception as e:
            print(f"[3D渲染] 设置3D属性失败: {e}")
            import traceback
            traceback.print_exc()
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
        self.elevation = 75  # 稍微倾斜的俯视角度
        self.azimuth = 45    # 45度方位角
        print(f"[3D热力图] 固定观察角度: 仰角=75°, 方位角=45°")
    
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
        
    
    def update_canvas_async(self, new_fig):
        """真正异步的canvas更新 - 使用after_idle避免阻塞UI"""
        if new_fig is None:
            return
        
        # 防止重复更新
        if self.is_updating:
            if new_fig:
                plt.close(new_fig)
            return
        
        # 使用after_idle在UI空闲时更新，不阻塞主线程
        try:
            self.parent_frame.after_idle(self._async_update_wrapper, new_fig)
        except Exception as e:
            if new_fig:
                plt.close(new_fig)
    
    def _async_update_wrapper(self, new_fig):
        """异步更新包装器"""
        if self.is_updating:
            if new_fig:
                plt.close(new_fig)
            return
            
        self.is_updating = True
        
        try:
            self._simple_update(new_fig)
        except Exception as e:
            if new_fig:
                plt.close(new_fig)
        finally:
            self.is_updating = False
    
    def _simple_update(self, new_fig):
        """简单直接的更新方式 - 最小化闪烁"""
        
        # 先暂停绘制避免中间状态闪烁
        if self.canvas:
            self.canvas.get_tk_widget().update_idletasks()
        
        # 如果是第一次创建canvas
        if self.canvas is None:
            self.canvas = FigureCanvasTkAgg(new_fig, master=self.canvas_container)
            canvas_widget = self.canvas.get_tk_widget()
            canvas_widget.pack(fill='both', expand=True)
            
            # 确保Canvas完全填满容器，没有任何边框
            canvas_widget.configure(highlightthickness=0, bd=0, relief='flat')
        else:
            # 快速替换canvas，减少闪烁时间
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
        
        # 使用最轻量级的绘制方式，避免阻塞UI
        try:
            # 尝试使用flush_events避免阻塞
            self.canvas.draw_idle()
            # 立即处理pending事件，不累积
            self.canvas.flush_events()
        except:
            # 如果flush_events不可用，使用标准draw_idle
            self.canvas.draw_idle()
        
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
                
            
            # 使用最简单的方式让图形填满Canvas
            if self.fig.axes:
                ax = self.fig.axes[0]
                
                # 设置适中的边距，确保不被裁切且居中显示
                self.fig.subplots_adjust(left=0.1, right=0.9, top=0.9, bottom=0.1)
                
                # 确保3D轴的纵横比合适，根据实际数据维度调整
                try:
                    # 尝试从当前图中获取数据维度
                    xlim = ax.get_xlim()
                    ylim = ax.get_ylim()
                    if xlim[1] > 0 and ylim[1] > 0:
                        data_aspect = xlim[1] / ylim[1]
                        if data_aspect > 1.6:  # 明显的宽矩形
                            ax.set_box_aspect([data_aspect, 1, 0.3])
                        elif data_aspect < 0.625:  # 明显的高矩形
                            ax.set_box_aspect([1, 1/data_aspect, 0.3])
                        else:  # 正方形或接近正方形
                            ax.set_box_aspect([1, 1, 0.3])
                    else:
                        ax.set_box_aspect([1, 1, 0.3])  # 默认比例
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


        
        # 初始化3D渲染器 - 大幅降低FPS以保护UI响应性
        self.renderer_3d = Heatmap3DRenderer(array_rows, array_cols, target_fps=1)
        
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
            
        self.current_mode = "2D"
        
        # 隐藏3D区域
        self.display_3d_frame.pack_forget()
        
        # 显示2D区域
        self.display_2d_frame.pack(fill='both', expand=True)
        
        self.status_var.set("2D模式 - 实时渲染")
    
    def switch_to_3d(self):
        """切换到3D模式"""
        if self.current_mode == "3D":
            return
            
        self.current_mode = "3D"
        
        # 隐藏2D区域
        self.display_2d_frame.pack_forget()
        
        # 显示3D区域
        self.display_3d_frame.pack(fill='both', expand=True)
        
        stats = self.renderer_3d.get_stats()
        self.status_var.set(f"3D模式 - FPS: {stats['actual_fps']:.1f}")
    
    def set_3d_view(self, elevation: float, azimuth: float):
        """设置3D视角（保留接口兼容性，但固定优化角度）"""
        # 固定使用优化的观察角度
        self.renderer_3d.set_view_angle(75, 45)
        
        if self.current_mode == "3D":
            stats = self.renderer_3d.get_stats()
            self.status_var.set(f"3D模式 - FPS: {stats['actual_fps']:.1f}")
    
    def update_data(self, matrix_2d, statistics=None):
        """更新显示数据"""
        try:
            # 检查数据有效性
            if matrix_2d is None or matrix_2d.size == 0:
                return
            
            # 根据当前模式选择性更新，节省资源
            if self.current_mode == "2D":
                # 2D模式：只更新2D，不更新3D
                self.visualizer_2d.update_data(matrix_2d, statistics)
            else:
                # 3D模式：更新2D（后台保持数据）和3D
                self.visualizer_2d.update_data(matrix_2d, statistics)
                
                # 只有当Canvas不在更新状态时才提交新数据到3D
                if not self.canvas_3d_container.is_updating:
                    self.renderer_3d.update_data(matrix_2d, statistics)
                
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
                        
                
        except Exception as e:
            print(f"[可视化] 3D结果检查错误: {e}")
            import traceback
            traceback.print_exc()
        finally:
            # 进一步降低检查频率，保护UI线程
            self.parent_frame.after(1000, self.check_3d_results)  # 1 FPS检查频率，保护UI响应性
    
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