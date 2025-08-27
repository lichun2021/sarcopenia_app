#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
GemSage步态分析系统 - 可视化模块
生成专业的医疗报告图表和可视化内容

作者: Claude  
版本: 1.0.0
"""

import matplotlib.pyplot as plt
import matplotlib.patches as patches
import seaborn as sns
import numpy as np
import pandas as pd
from matplotlib.patches import Rectangle
import base64
from io import BytesIO
import cv2
from scipy import ndimage
import warnings
warnings.filterwarnings('ignore')

# 设置中文字体和样式
plt.rcParams['font.sans-serif'] = ['SimHei', 'Arial Unicode MS', 'DejaVu Sans']
plt.rcParams['axes.unicode_minus'] = False
plt.rcParams['figure.facecolor'] = 'white'
plt.style.use('seaborn-v0_8-whitegrid')

class PressureVisualizer:
    """压力数据可视化器"""
    
    def __init__(self, processor):
        """
        初始化可视化器
        
        Args:
            processor: PressureDataProcessor实例
        """
        self.processor = processor
        self.grid_size = processor.grid_size
        self.physical_size = processor.physical_size
        
    def create_pressure_heatmap(self, pressure_matrix, title="压力分布热力图", show_grid=True):
        """
        创建压力分布热力图
        
        Args:
            pressure_matrix (np.array): 压力矩阵
            title (str): 图表标题
            show_grid (bool): 是否显示网格
            
        Returns:
            str: Base64编码的图像
        """
        fig, ax = plt.subplots(1, 1, figsize=(8, 8))
        
        # 创建热力图
        im = ax.imshow(pressure_matrix, cmap='Reds', interpolation='nearest', 
                      extent=[0, self.physical_size, self.physical_size, 0])
        
        # 添加颜色条
        cbar = plt.colorbar(im, ax=ax, shrink=0.8)
        cbar.set_label('压力值', fontsize=12)
        
        # 设置标题和标签
        ax.set_title(title, fontsize=14, fontweight='bold', pad=20)
        ax.set_xlabel('X轴 (cm)', fontsize=12)
        ax.set_ylabel('Y轴 (cm)', fontsize=12)
        
        # 显示网格线
        if show_grid:
            # 创建网格线
            cell_size = self.physical_size / self.grid_size
            for i in range(self.grid_size + 1):
                ax.axhline(y=i * cell_size, color='white', linewidth=0.5, alpha=0.3)
                ax.axvline(x=i * cell_size, color='white', linewidth=0.5, alpha=0.3)
        
        # 添加最大压力点标记
        max_pos = np.unravel_index(np.argmax(pressure_matrix), pressure_matrix.shape)
        max_y, max_x = max_pos[0] * self.processor.cell_size, max_pos[1] * self.processor.cell_size
        ax.plot(max_x, max_y, 'b*', markersize=15, label=f'最大压力点 ({np.max(pressure_matrix):.1f})')
        
        # 计算并标记压力中心
        cop_x, cop_y = self.processor.calculate_center_of_pressure(pressure_matrix)
        ax.plot(cop_x, cop_y, 'go', markersize=10, label=f'压力中心 ({cop_x:.1f}, {cop_y:.1f})')
        
        ax.legend(fontsize=10)
        plt.tight_layout()
        
        # 转换为base64
        return self._fig_to_base64(fig)
    
    def create_pressure_contour(self, pressure_matrix, title="压力等高线图"):
        """
        创建压力等高线图
        
        Args:
            pressure_matrix (np.array): 压力矩阵
            title (str): 图表标题
            
        Returns:
            str: Base64编码的图像
        """
        fig, ax = plt.subplots(1, 1, figsize=(8, 8))
        
        # 创建坐标网格
        x = np.linspace(0, self.physical_size, self.grid_size)
        y = np.linspace(0, self.physical_size, self.grid_size)
        X, Y = np.meshgrid(x, y)
        
        # 创建等高线
        levels = np.linspace(0, np.max(pressure_matrix), 10)
        contour = ax.contour(X, Y, pressure_matrix, levels=levels, colors='blue', alpha=0.6)
        contourf = ax.contourf(X, Y, pressure_matrix, levels=levels, cmap='Reds', alpha=0.8)
        
        # 添加等高线标签
        ax.clabel(contour, inline=True, fontsize=8)
        
        # 添加颜色条
        cbar = plt.colorbar(contourf, ax=ax, shrink=0.8)
        cbar.set_label('压力值', fontsize=12)
        
        # 设置标题和标签
        ax.set_title(title, fontsize=14, fontweight='bold', pad=20)
        ax.set_xlabel('X轴 (cm)', fontsize=12)
        ax.set_ylabel('Y轴 (cm)', fontsize=12)
        
        plt.tight_layout()
        return self._fig_to_base64(fig)
    
    def create_3d_pressure_surface(self, pressure_matrix, title="3D压力表面图"):
        """
        创建3D压力表面图
        
        Args:
            pressure_matrix (np.array): 压力矩阵
            title (str): 图表标题
            
        Returns:
            str: Base64编码的图像
        """
        fig = plt.figure(figsize=(10, 8))
        ax = fig.add_subplot(111, projection='3d')
        
        # 创建坐标网格
        x = np.linspace(0, self.physical_size, self.grid_size)
        y = np.linspace(0, self.physical_size, self.grid_size)
        X, Y = np.meshgrid(x, y)
        
        # 创建3D表面
        surface = ax.plot_surface(X, Y, pressure_matrix, cmap='Reds', alpha=0.9,
                                rstride=2, cstride=2, linewidth=0.5, antialiased=True)
        
        # 添加颜色条
        fig.colorbar(surface, ax=ax, shrink=0.5, aspect=5, label='压力值')
        
        # 设置标题和标签
        ax.set_title(title, fontsize=14, fontweight='bold', pad=20)
        ax.set_xlabel('X轴 (cm)', fontsize=12)
        ax.set_ylabel('Y轴 (cm)', fontsize=12)
        ax.set_zlabel('压力值', fontsize=12)
        
        # 设置视角
        ax.view_init(elev=30, azim=45)
        
        plt.tight_layout()
        return self._fig_to_base64(fig)
    
    def _fig_to_base64(self, fig):
        """
        将matplotlib图形转换为base64字符串
        
        Args:
            fig: matplotlib图形对象
            
        Returns:
            str: base64编码的图像字符串
        """
        buffer = BytesIO()
        fig.savefig(buffer, format='png', dpi=150, bbox_inches='tight', 
                   facecolor='white', edgecolor='none')
        buffer.seek(0)
        img_base64 = base64.b64encode(buffer.read()).decode('utf-8')
        plt.close(fig)
        return f"data:image/png;base64,{img_base64}"


class GaitTrajectoryVisualizer:
    """步态轨迹可视化器"""
    
    def __init__(self, processor):
        self.processor = processor
        
    def create_cop_trajectory(self, cop_positions, timestamps, title="压力中心轨迹图"):
        """
        创建压力中心轨迹图
        
        Args:
            cop_positions: 压力中心位置列表 [(x, y), ...]
            timestamps: 时间戳列表
            title: 图表标题
            
        Returns:
            str: Base64编码的图像
        """
        fig, ax = plt.subplots(1, 1, figsize=(10, 8))
        
        if len(cop_positions) > 0:
            cops = np.array(cop_positions)
            
            # 绘制轨迹线
            ax.plot(cops[:, 0], cops[:, 1], 'b-', linewidth=2, alpha=0.7, label='CoP轨迹')
            
            # 标记起点和终点
            ax.plot(cops[0, 0], cops[0, 1], 'go', markersize=12, label='起点', zorder=5)
            ax.plot(cops[-1, 0], cops[-1, 1], 'ro', markersize=12, label='终点', zorder=5)
            
            # 添加时间颜色映射
            scatter = ax.scatter(cops[:, 0], cops[:, 1], c=timestamps, 
                               cmap='viridis', s=30, alpha=0.8, zorder=3)
            
            # 添加颜色条
            cbar = plt.colorbar(scatter, ax=ax)
            cbar.set_label('时间 (s)', fontsize=12)
            
            # 计算轨迹统计信息
            total_distance = 0
            for i in range(1, len(cops)):
                dx = cops[i, 0] - cops[i-1, 0]
                dy = cops[i, 1] - cops[i-1, 1]
                total_distance += np.sqrt(dx*dx + dy*dy)
            
            # 添加统计文本
            stats_text = f"总轨迹长度: {total_distance:.2f} cm\n"
            stats_text += f"轨迹点数: {len(cops)}\n"
            stats_text += f"时间跨度: {timestamps[-1] - timestamps[0]:.2f} s"
            
            ax.text(0.02, 0.98, stats_text, transform=ax.transAxes, 
                   fontsize=10, verticalalignment='top',
                   bbox=dict(boxstyle='round', facecolor='white', alpha=0.8))
        
        # 设置图表样式
        ax.set_title(title, fontsize=14, fontweight='bold', pad=20)
        ax.set_xlabel('X轴 (cm)', fontsize=12)
        ax.set_ylabel('Y轴 (cm)', fontsize=12)
        ax.grid(True, alpha=0.3)
        ax.legend()
        ax.set_aspect('equal', adjustable='box')
        
        plt.tight_layout()
        return self._fig_to_base64(fig)
    
    def create_step_pattern(self, steps, title="步伐模式图"):
        """
        创建步伐模式图
        
        Args:
            steps: 步伐数据列表
            title: 图表标题
            
        Returns:
            str: Base64编码的图像
        """
        fig, ax = plt.subplots(1, 1, figsize=(12, 8))
        
        if len(steps) > 0:
            left_steps = [(s['cop_x'], s['cop_y']) for s in steps if s['foot'] == 'left']
            right_steps = [(s['cop_x'], s['cop_y']) for s in steps if s['foot'] == 'right']
            
            # 绘制左脚步伐
            if left_steps:
                left_x, left_y = zip(*left_steps)
                ax.scatter(left_x, left_y, c='blue', s=100, marker='o', 
                          alpha=0.8, label=f'左脚 ({len(left_steps)}步)', zorder=4)
                
                # 连接左脚步伐
                ax.plot(left_x, left_y, 'b--', alpha=0.5, linewidth=1)
            
            # 绘制右脚步伐
            if right_steps:
                right_x, right_y = zip(*right_steps)
                ax.scatter(right_x, right_y, c='red', s=100, marker='s',
                          alpha=0.8, label=f'右脚 ({len(right_steps)}步)', zorder=4)
                
                # 连接右脚步伐
                ax.plot(right_x, right_y, 'r--', alpha=0.5, linewidth=1)
            
            # 连接交替步伐
            for i in range(len(steps) - 1):
                x1, y1 = steps[i]['cop_x'], steps[i]['cop_y']
                x2, y2 = steps[i+1]['cop_x'], steps[i+1]['cop_y']
                ax.plot([x1, x2], [y1, y2], 'gray', alpha=0.3, linewidth=1)
            
            # 标注步伐顺序
            for i, step in enumerate(steps):
                ax.annotate(str(i+1), (step['cop_x'], step['cop_y']), 
                          xytext=(5, 5), textcoords='offset points',
                          fontsize=8, color='white', weight='bold',
                          bbox=dict(boxstyle='circle', facecolor='black', alpha=0.7))
        
        # 设置图表样式
        ax.set_title(title, fontsize=14, fontweight='bold', pad=20)
        ax.set_xlabel('X轴 (cm)', fontsize=12)
        ax.set_ylabel('Y轴 (cm)', fontsize=12)
        ax.grid(True, alpha=0.3)
        ax.legend()
        ax.set_aspect('equal', adjustable='box')
        
        plt.tight_layout()
        return self._fig_to_base64(fig)
    
    def _fig_to_base64(self, fig):
        """将matplotlib图形转换为base64字符串"""
        buffer = BytesIO()
        fig.savefig(buffer, format='png', dpi=150, bbox_inches='tight',
                   facecolor='white', edgecolor='none')
        buffer.seek(0)
        img_base64 = base64.b64encode(buffer.read()).decode('utf-8')
        plt.close(fig)
        return f"data:image/png;base64,{img_base64}"


class TimeSeriesVisualizer:
    """时间序列可视化器"""
    
    def create_pressure_timeline(self, data, title="压力时间序列"):
        """
        创建压力时间序列图
        
        Args:
            data: 包含时间和压力数据的DataFrame
            title: 图表标题
            
        Returns:
            str: Base64编码的图像
        """
        fig, axes = plt.subplots(3, 1, figsize=(12, 10))
        
        if data is not None and len(data) > 0:
            times = data['time'].values
            
            # 计算各项指标
            total_pressures = []
            max_pressures = []
            active_areas = []
            
            for _, row in data.iterrows():
                try:
                    # 解析压力矩阵
                    data_str = row['data'].strip('[]')
                    values = [float(x.strip()) for x in data_str.split(',')]
                    pressure_matrix = np.array(values).reshape(32, 32)
                    
                    total_pressures.append(np.sum(pressure_matrix))
                    max_pressures.append(np.max(pressure_matrix))
                    active_areas.append(np.sum(pressure_matrix > 0))
                    
                except:
                    total_pressures.append(0)
                    max_pressures.append(0)
                    active_areas.append(0)
            
            # 绘制总压力
            axes[0].plot(times, total_pressures, 'b-', linewidth=2, label='总压力')
            axes[0].set_ylabel('总压力值', fontsize=12)
            axes[0].set_title('总压力变化', fontsize=12, fontweight='bold')
            axes[0].grid(True, alpha=0.3)
            axes[0].legend()
            
            # 绘制最大压力
            axes[1].plot(times, max_pressures, 'r-', linewidth=2, label='最大压力')
            axes[1].set_ylabel('最大压力值', fontsize=12)
            axes[1].set_title('最大压力变化', fontsize=12, fontweight='bold')
            axes[1].grid(True, alpha=0.3)
            axes[1].legend()
            
            # 绘制活跃区域
            axes[2].plot(times, active_areas, 'g-', linewidth=2, label='活跃面积')
            axes[2].set_ylabel('活跃点数', fontsize=12)
            axes[2].set_xlabel('时间 (s)', fontsize=12)
            axes[2].set_title('活跃面积变化', fontsize=12, fontweight='bold')
            axes[2].grid(True, alpha=0.3)
            axes[2].legend()
        
        # 设置整体标题
        fig.suptitle(title, fontsize=16, fontweight='bold', y=0.98)
        plt.tight_layout()
        
        return self._fig_to_base64(fig)
    
    def create_balance_analysis(self, cop_positions, timestamps, title="平衡分析"):
        """
        创建平衡分析图
        
        Args:
            cop_positions: 压力中心位置列表
            timestamps: 时间戳列表
            title: 图表标题
            
        Returns:
            str: Base64编码的图像
        """
        fig, axes = plt.subplots(2, 2, figsize=(12, 10))
        
        if len(cop_positions) > 0:
            cops = np.array(cop_positions)
            
            # CoP X方向变化
            axes[0, 0].plot(timestamps, cops[:, 0], 'b-', linewidth=2)
            axes[0, 0].set_ylabel('CoP X位置 (cm)', fontsize=10)
            axes[0, 0].set_title('X方向摆动', fontsize=12, fontweight='bold')
            axes[0, 0].grid(True, alpha=0.3)
            
            # CoP Y方向变化
            axes[0, 1].plot(timestamps, cops[:, 1], 'r-', linewidth=2)
            axes[0, 1].set_ylabel('CoP Y位置 (cm)', fontsize=10)
            axes[0, 1].set_title('Y方向摆动', fontsize=12, fontweight='bold')
            axes[0, 1].grid(True, alpha=0.3)
            
            # 计算摆动速度
            if len(cops) > 1:
                velocity = np.diff(cops, axis=0) / np.diff(timestamps).reshape(-1, 1)
                speed = np.sqrt(np.sum(velocity**2, axis=1))
                
                axes[1, 0].plot(timestamps[1:], speed, 'g-', linewidth=2)
                axes[1, 0].set_ylabel('摆动速度 (cm/s)', fontsize=10)
                axes[1, 0].set_xlabel('时间 (s)', fontsize=12)
                axes[1, 0].set_title('摆动速度', fontsize=12, fontweight='bold')
                axes[1, 0].grid(True, alpha=0.3)
            
            # 稳定性椭圆
            # 计算95%置信椭圆
            mean_x, mean_y = np.mean(cops[:, 0]), np.mean(cops[:, 1])
            cov_matrix = np.cov(cops.T)
            
            # 特征值和特征向量
            eigenvals, eigenvecs = np.linalg.eigh(cov_matrix)
            
            # 95%置信区间对应的卡方分布值
            chi2_val = 5.991  # chi2(0.05, df=2)
            
            # 椭圆参数
            width = 2 * np.sqrt(chi2_val * eigenvals[0])
            height = 2 * np.sqrt(chi2_val * eigenvals[1])
            angle = np.degrees(np.arctan2(eigenvecs[1, 0], eigenvecs[0, 0]))
            
            axes[1, 1].scatter(cops[:, 0], cops[:, 1], alpha=0.6, s=30)
            axes[1, 1].plot(mean_x, mean_y, 'ro', markersize=8, label='平均位置')
            
            # 添加置信椭圆
            ellipse = patches.Ellipse((mean_x, mean_y), width, height, 
                                    angle=angle, linewidth=2, fill=False, 
                                    color='red', label='95%置信椭圆')
            axes[1, 1].add_patch(ellipse)
            
            axes[1, 1].set_xlabel('CoP X位置 (cm)', fontsize=10)
            axes[1, 1].set_ylabel('CoP Y位置 (cm)', fontsize=10)
            axes[1, 1].set_title('稳定性分析', fontsize=12, fontweight='bold')
            axes[1, 1].grid(True, alpha=0.3)
            axes[1, 1].legend()
            axes[1, 1].set_aspect('equal', adjustable='box')
        
        # 设置整体标题
        fig.suptitle(title, fontsize=16, fontweight='bold', y=0.98)
        plt.tight_layout()
        
        return self._fig_to_base64(fig)
    
    def _fig_to_base64(self, fig):
        """将matplotlib图形转换为base64字符串"""
        buffer = BytesIO()
        fig.savefig(buffer, format='png', dpi=150, bbox_inches='tight',
                   facecolor='white', edgecolor='none')
        buffer.seek(0)
        img_base64 = base64.b64encode(buffer.read()).decode('utf-8')
        plt.close(fig)
        return f"data:image/png;base64,{img_base64}"


class ReportChartsGenerator:
    """报告图表生成器"""
    
    def __init__(self, processor):
        """
        初始化报告图表生成器
        
        Args:
            processor: PressureDataProcessor实例
        """
        self.processor = processor
        self.pressure_viz = PressureVisualizer(processor)
        self.trajectory_viz = GaitTrajectoryVisualizer(processor)
        self.timeseries_viz = TimeSeriesVisualizer()
    
    def generate_all_charts(self, gait_data, analysis_results):
        """
        生成所有报告图表
        
        Args:
            gait_data: 步态数据字典
            analysis_results: 分析结果字典
            
        Returns:
            dict: 包含所有图表的字典
        """
        charts = {}
        
        # 为每种测试类型生成图表
        for test_type, data in gait_data.items():
            if data is not None and len(data) > 0:
                charts[f'{test_type}_charts'] = self._generate_test_charts(data, test_type)
        
        return charts
    
    def _generate_test_charts(self, data, test_type):
        """
        为特定测试类型生成图表
        
        Args:
            data: 测试数据DataFrame
            test_type: 测试类型
            
        Returns:
            dict: 图表字典
        """
        charts = {}
        
        try:
            # 解析第一帧数据用于静态图表
            first_row = data.iloc[0] if len(data) > 0 else None
            if first_row is not None:
                pressure_matrix = self.processor.parse_pressure_array(first_row['data'])
                
                # 生成压力热力图
                charts['heatmap'] = self.pressure_viz.create_pressure_heatmap(
                    pressure_matrix, f"{test_type} - 压力分布热力图"
                )
                
                # 生成等高线图
                charts['contour'] = self.pressure_viz.create_pressure_contour(
                    pressure_matrix, f"{test_type} - 压力等高线图"
                )
            
            # 生成时间序列图
            charts['timeline'] = self.timeseries_viz.create_pressure_timeline(
                data, f"{test_type} - 压力时间序列"
            )
            
            # 计算压力中心轨迹
            cop_positions = []
            timestamps = []
            
            for _, row in data.iterrows():
                pressure_matrix = self.processor.parse_pressure_array(row['data'])
                cop_x, cop_y = self.processor.calculate_center_of_pressure(pressure_matrix)
                cop_positions.append((cop_x, cop_y))
                timestamps.append(row['time'])
            
            # 生成轨迹图
            charts['trajectory'] = self.trajectory_viz.create_cop_trajectory(
                cop_positions, timestamps, f"{test_type} - 压力中心轨迹"
            )
            
            # 生成平衡分析图
            charts['balance'] = self.timeseries_viz.create_balance_analysis(
                cop_positions, timestamps, f"{test_type} - 平衡分析"
            )
            
        except Exception as e:
            print(f"生成{test_type}图表时出错: {e}")
            charts['error'] = str(e)
        
        return charts


def main():
    """测试可视化功能"""
    # 这里可以添加测试代码
    print("可视化模块加载成功!")


if __name__ == "__main__":
    main()