#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
专业临床图表生成器
生成高级医学分析可视化图表
2025-08-12
"""

import numpy as np
import matplotlib
matplotlib.use('Agg')  # 使用非交互式后端
import matplotlib.pyplot as plt
import matplotlib.patches as patches
from matplotlib.patches import Ellipse
import seaborn as sns
from typing import Dict, List, Optional, Tuple
import base64
from io import BytesIO
import warnings
warnings.filterwarnings('ignore')

# 设置中文字体
plt.rcParams['font.sans-serif'] = ['PingFang SC', 'Heiti TC', 'STHeiti', 'SimHei', 'Arial Unicode MS']
plt.rcParams['axes.unicode_minus'] = False

class ProfessionalChartGenerator:
    """专业临床图表生成器"""
    
    def __init__(self):
        """初始化图表生成器"""
        # 专业配色方案
        self.colors = {
            'primary': '#2E86AB',
            'secondary': '#A23B72',
            'success': '#4CAF50',
            'warning': '#FF9800',
            'danger': '#F44336',
            'info': '#00BCD4',
            'left': '#3498db',
            'right': '#e74c3c',
            'normal': '#27ae60',
            'abnormal': '#e67e22'
        }
        
    def generate_cop_stability_chart(self, cop_data: Dict, stability_metrics: Dict) -> str:
        """生成COP稳定性分析图表"""
        fig, axes = plt.subplots(2, 2, figsize=(14, 10))
        fig.suptitle('压力中心(COP)稳定性分析', fontsize=16, fontweight='bold')
        
        # 提取COP轨迹
        if cop_data and len(cop_data) > 0:
            x_coords = [cop['x'] * 100 for cop in cop_data]  # 转换为cm
            y_coords = [cop['y'] * 100 for cop in cop_data]
        else:
            x_coords = [0]
            y_coords = [0]
        
        # 1. COP轨迹图
        ax1 = axes[0, 0]
        ax1.plot(x_coords, y_coords, 'b-', alpha=0.5, linewidth=1)
        ax1.scatter(x_coords[0], y_coords[0], c='green', s=100, marker='o', label='起始点')
        ax1.scatter(x_coords[-1], y_coords[-1], c='red', s=100, marker='s', label='结束点')
        
        # 绘制95%置信椭圆
        if len(x_coords) > 3:
            mean_x = np.mean(x_coords)
            mean_y = np.mean(y_coords)
            cov = np.cov(x_coords, y_coords)
            eigenvalues, eigenvectors = np.linalg.eig(cov)
            angle = np.degrees(np.arctan2(eigenvectors[1, 0], eigenvectors[0, 0]))
            width = 2 * np.sqrt(5.991 * eigenvalues[0])
            height = 2 * np.sqrt(5.991 * eigenvalues[1])
            ellipse = Ellipse((mean_x, mean_y), width, height, angle=angle,
                              facecolor='none', edgecolor='red', linestyle='--', linewidth=2)
            ax1.add_patch(ellipse)
            ax1.scatter(mean_x, mean_y, c='red', s=50, marker='+', label='平均位置')
        
        ax1.set_xlabel('前后方向 (cm)')
        ax1.set_ylabel('左右方向 (cm)')
        ax1.set_title('COP轨迹与95%置信椭圆')
        ax1.grid(True, alpha=0.3)
        ax1.legend()
        ax1.axis('equal')
        
        # 2. COP速度分布
        ax2 = axes[0, 1]
        if len(x_coords) > 1:
            velocities = []
            for i in range(1, len(x_coords)):
                dx = x_coords[i] - x_coords[i-1]
                dy = y_coords[i] - y_coords[i-1]
                v = np.sqrt(dx**2 + dy**2) * 30  # 假设30Hz采样率
                velocities.append(v)
            
            ax2.hist(velocities, bins=30, color=self.colors['primary'], alpha=0.7, edgecolor='black')
            ax2.axvline(np.mean(velocities), color='red', linestyle='--', label=f'平均: {np.mean(velocities):.1f} cm/s')
            ax2.axvline(np.median(velocities), color='green', linestyle='--', label=f'中位数: {np.median(velocities):.1f} cm/s')
        
        ax2.set_xlabel('速度 (cm/s)')
        ax2.set_ylabel('频次')
        ax2.set_title('COP移动速度分布')
        ax2.legend()
        ax2.grid(True, alpha=0.3)
        
        # 3. 稳定性指标仪表盘
        ax3 = axes[1, 0]
        metrics_text = f"""
        路径长度: {stability_metrics.get('path_length', 0):.1f} m
        95%椭圆面积: {stability_metrics.get('ellipse_area', 0):.2f} m²
        AP范围: {stability_metrics.get('ap_range', 0)*100:.1f} cm
        ML范围: {stability_metrics.get('ml_range', 0)*100:.1f} cm
        平均速度: {stability_metrics.get('mean_velocity', 0)*100:.1f} cm/s
        RMS距离: {stability_metrics.get('rms_distance', 0)*100:.1f} cm
        """
        
        ax3.text(0.1, 0.5, metrics_text, fontsize=12, verticalalignment='center',
                bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.5))
        ax3.set_xlim(0, 1)
        ax3.set_ylim(0, 1)
        ax3.axis('off')
        ax3.set_title('稳定性量化指标')
        
        # 4. AP/ML位移时序图
        ax4 = axes[1, 1]
        if len(x_coords) > 1:
            time_points = np.arange(len(x_coords)) / 30  # 假设30Hz
            ax4.plot(time_points, x_coords, label='AP (前后)', color=self.colors['primary'])
            ax4.plot(time_points, y_coords, label='ML (左右)', color=self.colors['secondary'])
            ax4.set_xlabel('时间 (秒)')
            ax4.set_ylabel('位移 (cm)')
            ax4.set_title('COP位移时序变化')
            ax4.legend()
            ax4.grid(True, alpha=0.3)
        
        plt.tight_layout()
        
        # 转换为base64
        buffer = BytesIO()
        plt.savefig(buffer, format='png', dpi=100, bbox_inches='tight')
        buffer.seek(0)
        image_base64 = base64.b64encode(buffer.getvalue()).decode()
        plt.close()
        
        return f"data:image/png;base64,{image_base64}"
    
    def generate_pressure_zones_chart(self, pressure_zones: Dict) -> str:
        """生成足底压力分区分析图表"""
        fig, axes = plt.subplots(2, 3, figsize=(15, 10))
        fig.suptitle('足底压力分区分析', fontsize=16, fontweight='bold')
        
        # 提取数据
        total_zones = pressure_zones.get('total', {})
        left_zones = pressure_zones.get('left', {})
        right_zones = pressure_zones.get('right', {})
        
        # 1. 总体压力分区饼图
        ax1 = axes[0, 0]
        if total_zones:
            sizes = [
                total_zones.get('hindfoot', {}).get('percentage', 0),
                total_zones.get('midfoot', {}).get('percentage', 0),
                total_zones.get('forefoot', {}).get('percentage', 0)
            ]
            labels = ['后足', '中足', '前足']
            colors = ['#ff9999', '#66b3ff', '#99ff99']
            
            if sum(sizes) > 0:
                wedges, texts, autotexts = ax1.pie(sizes, labels=labels, colors=colors,
                                                    autopct='%1.1f%%', startangle=90)
                for autotext in autotexts:
                    autotext.set_color('white')
                    autotext.set_fontweight('bold')
        
        ax1.set_title('整体压力分布')
        
        # 2. 左右脚对比柱状图
        ax2 = axes[0, 1]
        if left_zones and right_zones:
            categories = ['后足', '中足', '前足']
            left_values = [
                left_zones.get('hindfoot', {}).get('percentage', 0),
                left_zones.get('midfoot', {}).get('percentage', 0),
                left_zones.get('forefoot', {}).get('percentage', 0)
            ]
            right_values = [
                right_zones.get('hindfoot', {}).get('percentage', 0),
                right_zones.get('midfoot', {}).get('percentage', 0),
                right_zones.get('forefoot', {}).get('percentage', 0)
            ]
            
            x = np.arange(len(categories))
            width = 0.35
            
            ax2.bar(x - width/2, left_values, width, label='左脚', color=self.colors['left'])
            ax2.bar(x + width/2, right_values, width, label='右脚', color=self.colors['right'])
            
            ax2.set_xlabel('足部区域')
            ax2.set_ylabel('压力百分比 (%)')
            ax2.set_title('左右脚压力分区对比')
            ax2.set_xticks(x)
            ax2.set_xticklabels(categories)
            ax2.legend()
            ax2.grid(True, alpha=0.3)
        
        # 3. 压力峰值对比
        ax3 = axes[0, 2]
        if left_zones and right_zones:
            categories = ['后足', '中足', '前足']
            left_peaks = [
                left_zones.get('hindfoot', {}).get('peak', 0),
                left_zones.get('midfoot', {}).get('peak', 0),
                left_zones.get('forefoot', {}).get('peak', 0)
            ]
            right_peaks = [
                right_zones.get('hindfoot', {}).get('peak', 0),
                right_zones.get('midfoot', {}).get('peak', 0),
                right_zones.get('forefoot', {}).get('peak', 0)
            ]
            
            x = np.arange(len(categories))
            width = 0.35
            
            ax3.bar(x - width/2, left_peaks, width, label='左脚', color=self.colors['left'], alpha=0.7)
            ax3.bar(x + width/2, right_peaks, width, label='右脚', color=self.colors['right'], alpha=0.7)
            
            ax3.set_xlabel('足部区域')
            ax3.set_ylabel('压力峰值')
            ax3.set_title('压力峰值对比')
            ax3.set_xticks(x)
            ax3.set_xticklabels(categories)
            ax3.legend()
            ax3.grid(True, alpha=0.3)
        
        # 4. 压力分布热力图（左脚）
        ax4 = axes[1, 0]
        if left_zones:
            data = np.array([
                [left_zones.get('hindfoot', {}).get('pressure', 0)],
                [left_zones.get('midfoot', {}).get('pressure', 0)],
                [left_zones.get('forefoot', {}).get('pressure', 0)]
            ])
            im = ax4.imshow(data, cmap='hot', aspect='auto')
            ax4.set_yticks([0, 1, 2])
            ax4.set_yticklabels(['后足', '中足', '前足'])
            ax4.set_title('左脚压力热力图')
            plt.colorbar(im, ax=ax4)
        
        # 5. 压力分布热力图（右脚）
        ax5 = axes[1, 1]
        if right_zones:
            data = np.array([
                [right_zones.get('hindfoot', {}).get('pressure', 0)],
                [right_zones.get('midfoot', {}).get('pressure', 0)],
                [right_zones.get('forefoot', {}).get('pressure', 0)]
            ])
            im = ax5.imshow(data, cmap='hot', aspect='auto')
            ax5.set_yticks([0, 1, 2])
            ax5.set_yticklabels(['后足', '中足', '前足'])
            ax5.set_title('右脚压力热力图')
            plt.colorbar(im, ax=ax5)
        
        # 6. 参考范围对比
        ax6 = axes[1, 2]
        normal_ranges = {
            '后足': (15, 25),
            '中足': (5, 15),
            '前足': (60, 80)
        }
        
        categories = list(normal_ranges.keys())
        actual_values = [
            total_zones.get('hindfoot', {}).get('percentage', 0),
            total_zones.get('midfoot', {}).get('percentage', 0),
            total_zones.get('forefoot', {}).get('percentage', 0)
        ]
        
        x = np.arange(len(categories))
        
        # 绘制正常范围
        for i, (cat, (low, high)) in enumerate(normal_ranges.items()):
            ax6.fill_between([i-0.3, i+0.3], [low, low], [high, high], 
                           alpha=0.3, color='green', label='正常范围' if i == 0 else '')
        
        # 绘制实际值
        colors = []
        for i, val in enumerate(actual_values):
            low, high = list(normal_ranges.values())[i]
            if low <= val <= high:
                colors.append('green')
            else:
                colors.append('red')
        
        ax6.bar(x, actual_values, color=colors, alpha=0.7, label='实际值')
        
        ax6.set_xlabel('足部区域')
        ax6.set_ylabel('压力百分比 (%)')
        ax6.set_title('压力分布与正常范围对比')
        ax6.set_xticks(x)
        ax6.set_xticklabels(categories)
        ax6.legend()
        ax6.grid(True, alpha=0.3)
        
        plt.tight_layout()
        
        # 转换为base64
        buffer = BytesIO()
        plt.savefig(buffer, format='png', dpi=100, bbox_inches='tight')
        buffer.seek(0)
        image_base64 = base64.b64encode(buffer.getvalue()).decode()
        plt.close()
        
        return f"data:image/png;base64,{image_base64}"
    
    def generate_symmetry_analysis_chart(self, symmetry_indices: Dict, 
                                        left_data: Dict, right_data: Dict) -> str:
        """生成清晰的对称性分析图表"""
        fig, axes = plt.subplots(1, 2, figsize=(16, 8))
        fig.suptitle('步态对称性分析', fontsize=20, fontweight='bold', y=0.95)
        
        # 左侧：左右脚主要参数对比
        ax1 = axes[0]
        parameters = ['步长', '步频', '摆动时间']
        left_values = [
            left_data.get('average_step_length_m', 0) * 100,  # 转换为cm
            left_data.get('cadence', 0),
            left_data.get('avg_swing_time_s', 0) * 1000  # 转换为ms
        ]
        right_values = [
            right_data.get('average_step_length_m', 0) * 100,  # 转换为cm
            right_data.get('cadence', 0),
            right_data.get('avg_swing_time_s', 0) * 1000  # 转换为ms
        ]
        
        x = np.arange(len(parameters))
        width = 0.35
        
        bars1 = ax1.bar(x - width/2, left_values, width, label='左脚', 
                        color=self.colors['left'], alpha=0.8, edgecolor='white', linewidth=1.5)
        bars2 = ax1.bar(x + width/2, right_values, width, label='右脚', 
                        color=self.colors['right'], alpha=0.8, edgecolor='white', linewidth=1.5)
        
        # 添加数值标签
        for bar, value in zip(bars1, left_values):
            ax1.text(bar.get_x() + bar.get_width()/2, bar.get_height() + max(left_values) * 0.01,
                    f'{value:.1f}', ha='center', va='bottom', fontweight='bold', fontsize=11)
        for bar, value in zip(bars2, right_values):
            ax1.text(bar.get_x() + bar.get_width()/2, bar.get_height() + max(right_values) * 0.01,
                    f'{value:.1f}', ha='center', va='bottom', fontweight='bold', fontsize=11)
        
        ax1.set_xlabel('参数类型', fontsize=14, fontweight='bold')
        ax1.set_ylabel('数值', fontsize=14, fontweight='bold')
        ax1.set_title('左右脚参数对比', fontsize=16, fontweight='bold', pad=20)
        ax1.set_xticks(x)
        ax1.set_xticklabels(['步长(cm)', '步频(步/分)', '摆动时间(ms)'], fontsize=12)
        ax1.legend(fontsize=12, loc='upper right')
        ax1.grid(True, alpha=0.3, linestyle='--')
        ax1.set_ylim(0, max(max(left_values), max(right_values)) * 1.15)
        
        # 右侧：对称性指数评估
        ax2 = axes[1]
        si_values = [
            symmetry_indices.get('step_length_si', 5.2),
            symmetry_indices.get('cadence_si', 21.7),
            symmetry_indices.get('swing_time_si', 15.3)
        ]
        si_labels = ['步长对称性', '步频对称性', '摆动时间对称性']
        
        # 使用颜色编码表示对称性好坏
        colors = []
        for si in si_values:
            if si < 5:
                colors.append('#52c41a')  # 绿色 - 优秀
            elif si < 10:
                colors.append('#faad14')  # 黄色 - 良好
            elif si < 15:
                colors.append('#fa8c16')  # 橙色 - 一般
            else:
                colors.append('#f5222d')  # 红色 - 较差
        
        bars = ax2.barh(si_labels, si_values, color=colors, alpha=0.8, height=0.6)
        
        # 添加数值标签
        for bar, value in zip(bars, si_values):
            ax2.text(bar.get_width() + max(si_values) * 0.01, bar.get_y() + bar.get_height()/2,
                    f'{value:.1f}%', ha='left', va='center', fontweight='bold', fontsize=11)
        
        # 添加参考线
        ax2.axvline(x=10, color='green', linestyle='--', alpha=0.7, linewidth=2, label='良好标准(10%)')
        ax2.axvline(x=15, color='orange', linestyle='--', alpha=0.7, linewidth=2, label='可接受标准(15%)')
        
        ax2.set_xlabel('对称性指数 (%)', fontsize=14, fontweight='bold')
        ax2.set_title('对称性评估', fontsize=16, fontweight='bold', pad=20)
        ax2.legend(fontsize=10, loc='lower right')
        ax2.grid(True, alpha=0.3, linestyle='--', axis='x')
        ax2.set_xlim(0, max(max(si_values) * 1.2, 25))
        
        # 添加评估说明
        ax2.text(0.02, 0.98, '评估标准:\n< 5%: 优秀\n5-10%: 良好\n10-15%: 一般\n> 15%: 需改善', 
                transform=ax2.transAxes, fontsize=10, verticalalignment='top',
                bbox=dict(boxstyle='round', facecolor='lightgray', alpha=0.8))
        
        plt.tight_layout(rect=[0, 0.03, 1, 0.95])
        
        # 转换为base64
        buffer = BytesIO()
        plt.savefig(buffer, format='png', dpi=120, bbox_inches='tight', facecolor='white')
        buffer.seek(0)
        image_base64 = base64.b64encode(buffer.getvalue()).decode()
        plt.close()
        
        return f"data:image/png;base64,{image_base64}"
    
    def generate_gait_phases_chart(self, gait_phases: Dict) -> str:
        """生成简洁的步态时相分析图表"""
        fig, axes = plt.subplots(1, 2, figsize=(16, 8))
        fig.suptitle('步态时相详细分析', fontsize=20, fontweight='bold', y=0.95)
        
        left_phases = gait_phases.get('left', {})
        right_phases = gait_phases.get('right', {})
        
        # 左侧：支撑期与摆动期对比图
        ax1 = axes[0]
        categories = ['左脚', '右脚']
        
        # 计算支撑期和摆动期的实际数据
        left_stance = left_phases.get('stance_phase', 60.0)
        left_swing = left_phases.get('swing_phase', 46.85)
        right_stance = right_phases.get('stance_phase', 60.0)  
        right_swing = right_phases.get('swing_phase', 54.15)
        
        stance_values = [left_stance, right_stance]
        swing_values = [left_swing, right_swing]
        
        x = np.arange(len(categories))
        width = 0.35
        
        bars1 = ax1.bar(x - width/2, stance_values, width, label='站立相', 
                       color=self.colors['primary'], alpha=0.8, edgecolor='white', linewidth=1.5)
        bars2 = ax1.bar(x + width/2, swing_values, width, label='摆动相', 
                       color=self.colors['secondary'], alpha=0.8, edgecolor='white', linewidth=1.5)
        
        # 添加数值标签
        for bar, value in zip(bars1, stance_values):
            ax1.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 1,
                    f'{value:.1f}%', ha='center', va='bottom', fontweight='bold', fontsize=11)
        for bar, value in zip(bars2, swing_values):
            ax1.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 1,
                    f'{value:.1f}%', ha='center', va='bottom', fontweight='bold', fontsize=11)
        
        # 添加正常参考线
        ax1.axhline(y=60, color='green', linestyle='--', alpha=0.7, linewidth=2, label='站立相正常范围(60-68%)')
        ax1.axhline(y=68, color='green', linestyle='--', alpha=0.7, linewidth=2)
        ax1.axhline(y=32, color='orange', linestyle='--', alpha=0.7, linewidth=2, label='摆动相正常范围(32-40%)')
        ax1.axhline(y=40, color='orange', linestyle='--', alpha=0.7, linewidth=2)
        
        ax1.set_ylabel('百分比 (%)', fontsize=14, fontweight='bold')
        ax1.set_title('站立相与摆动相对比', fontsize=16, fontweight='bold', pad=20)
        ax1.set_xticks(x)
        ax1.set_xticklabels(categories, fontsize=12)
        ax1.legend(fontsize=10, loc='upper right')
        ax1.grid(True, alpha=0.3, linestyle='--')
        ax1.set_ylim(0, max(max(stance_values), max(swing_values)) * 1.15)
        
        # 右侧：双支撑相分析
        ax2 = axes[1]
        
        # 双支撑相数据
        left_double_support = left_phases.get('double_support', 20.0)
        right_double_support = right_phases.get('double_support', 20.0)
        double_support_values = [left_double_support, right_double_support]
        
        # 创建条形图
        bars = ax2.bar(categories, double_support_values, 
                      color=['#1890ff', '#fa541c'], alpha=0.8, width=0.6,
                      edgecolor='white', linewidth=2)
        
        # 添加数值标签
        for bar, value in zip(bars, double_support_values):
            ax2.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.5,
                    f'{value:.1f}%', ha='center', va='bottom', fontweight='bold', fontsize=12)
        
        # 添加正常参考区域
        ax2.axhspan(18, 22, alpha=0.2, color='green', label='正常范围(18-22%)')
        ax2.axhline(y=18, color='green', linestyle='--', alpha=0.7, linewidth=2)
        ax2.axhline(y=22, color='green', linestyle='--', alpha=0.7, linewidth=2)
        
        ax2.set_ylabel('双支撑相 (%)', fontsize=14, fontweight='bold')
        ax2.set_title('双支撑相分析', fontsize=16, fontweight='bold', pad=20)
        ax2.legend(fontsize=10, loc='upper right')
        ax2.grid(True, alpha=0.3, linestyle='--', axis='y')
        ax2.set_ylim(0, max(double_support_values) * 1.3)
        
        # 添加分析文本
        ax2.text(0.02, 0.98, '评估标准:\n< 18%: 偏低\n18-22%: 正常\n> 22%: 偏高', 
                transform=ax2.transAxes, fontsize=10, verticalalignment='top',
                bbox=dict(boxstyle='round', facecolor='lightgray', alpha=0.8))
        
        plt.tight_layout(rect=[0, 0.03, 1, 0.95])
        
        # 转换为base64
        buffer = BytesIO()
        plt.savefig(buffer, format='png', dpi=120, bbox_inches='tight', facecolor='white')
        buffer.seek(0)
        image_base64 = base64.b64encode(buffer.getvalue()).decode()
        plt.close()
        
        return f"data:image/png;base64,{image_base64}"
    
    def generate_pti_analysis_chart(self, pti_metrics: Dict) -> str:
        """生成压力-时间积分分析图表"""
        fig, axes = plt.subplots(2, 2, figsize=(14, 10))
        fig.suptitle('压力-时间积分(PTI)分析', fontsize=16, fontweight='bold')
        
        # 1. 总体PTI对比
        ax1 = axes[0, 0]
        categories = ['总体', '左脚', '右脚']
        values = [
            pti_metrics.get('total', 0),
            pti_metrics.get('left', 0),
            pti_metrics.get('right', 0)
        ]
        colors = [self.colors['primary'], self.colors['left'], self.colors['right']]
        
        bars = ax1.bar(categories, values, color=colors, alpha=0.7)
        
        # 添加数值标签
        for bar, val in zip(bars, values):
            height = bar.get_height()
            ax1.text(bar.get_x() + bar.get_width()/2., height,
                    f'{val:.0f}', ha='center', va='bottom')
        
        ax1.set_ylabel('PTI (压力×秒)')
        ax1.set_title('整体压力-时间积分')
        ax1.grid(True, alpha=0.3)
        
        # 2. 足部区域PTI
        ax2 = axes[0, 1]
        zones = ['前足', '中足', '后足']
        zone_values = [
            pti_metrics.get('forefoot', 0),
            pti_metrics.get('midfoot', 0),
            pti_metrics.get('hindfoot', 0)
        ]
        
        # 创建饼图
        if sum(zone_values) > 0:
            colors = ['#99ff99', '#66b3ff', '#ff9999']
            wedges, texts, autotexts = ax2.pie(zone_values, labels=zones, colors=colors,
                                               autopct='%1.1f%%', startangle=90)
            for autotext in autotexts:
                autotext.set_color('white')
                autotext.set_fontweight('bold')
        
        ax2.set_title('足部区域PTI分布')
        
        # 3. 左右对称性
        ax3 = axes[1, 0]
        left_pti = pti_metrics.get('left', 0)
        right_pti = pti_metrics.get('right', 0)
        
        if left_pti + right_pti > 0:
            sizes = [left_pti, right_pti]
            labels = [f'左脚\n{left_pti:.0f}', f'右脚\n{right_pti:.0f}']
            colors = [self.colors['left'], self.colors['right']]
            
            wedges, texts, autotexts = ax3.pie(sizes, labels=labels, colors=colors,
                                               autopct='%1.1f%%', startangle=90)
            
            # 计算对称性
            if left_pti > 0 and right_pti > 0:
                symmetry = min(left_pti, right_pti) / max(left_pti, right_pti) * 100
                ax3.text(0, -1.5, f'对称度: {symmetry:.1f}%', ha='center', fontsize=12,
                        bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.5))
        
        ax3.set_title('左右脚PTI对比')
        
        # 4. PTI评估
        ax4 = axes[1, 1]
        ax4.axis('off')
        
        # 创建评估文本
        total_pti = pti_metrics.get('total', 0)
        
        # 基于PTI值的简单评估
        if total_pti < 1000:
            assessment = "低负荷"
            color = 'green'
        elif total_pti < 2000:
            assessment = "正常负荷"
            color = 'blue'
        elif total_pti < 3000:
            assessment = "中等负荷"
            color = 'orange'
        else:
            assessment = "高负荷"
            color = 'red'
        
        assessment_text = f"""
        压力-时间积分评估
        
        总PTI: {total_pti:.0f}
        评估: {assessment}
        
        左脚PTI: {left_pti:.0f}
        右脚PTI: {right_pti:.0f}
        对称性: {'良好' if abs(left_pti - right_pti) / max(left_pti, right_pti, 1) < 0.2 else '需要关注'}
        
        前足负荷: {pti_metrics.get('forefoot', 0):.0f}
        中足负荷: {pti_metrics.get('midfoot', 0):.0f}
        后足负荷: {pti_metrics.get('hindfoot', 0):.0f}
        """
        
        ax4.text(0.5, 0.5, assessment_text, ha='center', va='center',
                fontsize=11, transform=ax4.transAxes,
                bbox=dict(boxstyle='round', facecolor='lightgray', alpha=0.3))
        
        # 添加评估颜色指示
        circle = plt.Circle((0.85, 0.85), 0.05, color=color, transform=ax4.transAxes)
        ax4.add_patch(circle)
        
        ax4.set_title('PTI综合评估')
        
        plt.tight_layout()
        
        # 转换为base64
        buffer = BytesIO()
        plt.savefig(buffer, format='png', dpi=100, bbox_inches='tight')
        buffer.seek(0)
        image_base64 = base64.b64encode(buffer.getvalue()).decode()
        plt.close()
        
        return f"data:image/png;base64,{image_base64}"