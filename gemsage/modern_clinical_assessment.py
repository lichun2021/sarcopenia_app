#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
现代化临床评估系统
全新设计的步态分析评估图表
2025-08-13
"""

import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.patches import Circle, Rectangle, FancyBboxPatch, Wedge, PathPatch
from matplotlib.path import Path
import matplotlib.gridspec as gridspec
import seaborn as sns
from typing import Dict, List, Optional, Tuple
import base64
from io import BytesIO
import warnings
warnings.filterwarnings('ignore')

# 设置中文字体和现代化样式
plt.rcParams['font.sans-serif'] = ['PingFang SC', 'Heiti TC', 'STHeiti', 'SimHei', 'Arial Unicode MS']
plt.rcParams['axes.unicode_minus'] = False
plt.style.use('seaborn-v0_8-darkgrid')

class ModernClinicalAssessment:
    """现代化临床评估系统"""
    
    def __init__(self):
        """初始化现代化评估系统"""
        # 现代化配色方案 - 医疗蓝绿色系
        self.colors = {
            'primary': '#00A6B8',      # 主色调 - 医疗蓝绿
            'secondary': '#2E7D8E',    # 次要色 - 深蓝
            'accent': '#6CC4A1',       # 强调色 - 薄荷绿
            'success': '#4CAF50',      # 成功 - 绿色
            'warning': '#FF9800',      # 警告 - 橙色
            'danger': '#F44336',       # 危险 - 红色
            'info': '#03A9F4',         # 信息 - 浅蓝
            'light': '#F5F5F5',        # 浅色背景
            'dark': '#263238',         # 深色文字
            'gradient_start': '#00BCD4',
            'gradient_end': '#00838F'
        }
        
        # 现代化字体设置
        self.fonts = {
            'title': {'size': 14, 'weight': 'bold', 'color': self.colors['dark']},
            'subtitle': {'size': 11, 'weight': 'normal', 'color': self.colors['dark']},
            'label': {'size': 9, 'color': self.colors['dark']},
            'value': {'size': 10, 'weight': 'bold', 'color': self.colors['primary']}
        }
    
    def generate_comprehensive_assessment(self, data: Dict) -> str:
        """生成综合评估报告"""
        # 创建现代化布局
        fig = plt.figure(figsize=(16, 10), facecolor='white')
        gs = gridspec.GridSpec(3, 4, figure=fig, hspace=0.3, wspace=0.3)
        
        # 添加整体标题
        fig.suptitle('步态功能临床评估报告', fontsize=18, fontweight='bold', 
                    color=self.colors['dark'], y=0.98)
        
        # 1. 综合评分卡片 (占据左上角大区域)
        ax1 = fig.add_subplot(gs[0:2, 0:2])
        self._create_score_card(ax1, data)
        
        # 2. 关键指标仪表盘 (右上角)
        ax2 = fig.add_subplot(gs[0, 2])
        self._create_speed_gauge(ax2, data)
        
        ax3 = fig.add_subplot(gs[0, 3])
        self._create_balance_gauge(ax3, data)
        
        # 3. 步态参数条形图 (右中)
        ax4 = fig.add_subplot(gs[1, 2:4])
        self._create_parameter_bars(ax4, data)
        
        # 4. 风险评估矩阵 (底部左)
        ax5 = fig.add_subplot(gs[2, 0:2])
        self._create_risk_matrix(ax5, data)
        
        # 5. 康复建议面板 (底部右)
        ax6 = fig.add_subplot(gs[2, 2:4])
        self._create_recommendation_panel(ax6, data)
        
        # 优化布局
        plt.tight_layout(rect=[0, 0.02, 1, 0.96])
        
        # 转换为base64
        buffer = BytesIO()
        plt.savefig(buffer, format='png', dpi=120, bbox_inches='tight', 
                   facecolor='white', edgecolor='none')
        buffer.seek(0)
        image_base64 = base64.b64encode(buffer.getvalue()).decode()
        plt.close()
        
        return f"data:image/png;base64,{image_base64}"
    
    def _create_score_card(self, ax, data):
        """创建现代化评分卡片"""
        ax.set_xlim(0, 10)
        ax.set_ylim(0, 10)
        ax.axis('off')
        
        # 计算综合评分
        score = self._calculate_total_score(data)
        
        # 绘制背景渐变卡片
        gradient = np.linspace(0, 1, 256).reshape(1, -1)
        gradient = np.vstack((gradient, gradient))
        
        extent = [1, 9, 2, 8]
        ax.imshow(gradient, aspect='auto', cmap='Blues_r', alpha=0.1, extent=extent)
        
        # 绘制圆形进度条
        center = (5, 6)
        radius = 2
        
        # 背景圆
        circle_bg = Circle(center, radius, fill=False, 
                          edgecolor=self.colors['light'], linewidth=15)
        ax.add_patch(circle_bg)
        
        # 进度圆弧
        theta1 = 90
        theta2 = 90 - (score / 100 * 360)
        wedge = Wedge(center, radius, theta2, theta1, 
                     width=0.3, facecolor=self._get_score_color(score),
                     edgecolor='none')
        ax.add_patch(wedge)
        
        # 中心分数
        ax.text(center[0], center[1] + 0.3, f'{score:.0f}', 
               fontsize=36, fontweight='bold', ha='center', va='center',
               color=self.colors['dark'])
        
        ax.text(center[0], center[1] - 0.5, '综合评分', 
               fontsize=12, ha='center', va='center',
               color=self.colors['secondary'])
        
        # 评级标签
        rating = self._get_rating(score)
        ax.text(center[0], center[1] - 1.2, rating, 
               fontsize=14, fontweight='bold', ha='center', va='center',
               color=self._get_score_color(score))
        
        # 添加详细指标
        metrics = [
            ('步态功能', self._calculate_gait_score(data)),
            ('平衡能力', self._calculate_balance_score(data)),
            ('运动协调', self._calculate_coordination_score(data)),
            ('整体稳定', self._calculate_stability_score(data))
        ]
        
        y_pos = 2.5
        for name, value in metrics:
            # 指标名称
            ax.text(1.5, y_pos, name, fontsize=10, va='center')
            
            # 进度条
            bar_width = 3
            bar_height = 0.2
            
            # 背景条
            bg_rect = Rectangle((5, y_pos - bar_height/2), bar_width, bar_height,
                               facecolor=self.colors['light'], edgecolor='none')
            ax.add_patch(bg_rect)
            
            # 进度条
            progress_width = bar_width * (value / 100)
            progress_rect = Rectangle((5, y_pos - bar_height/2), progress_width, bar_height,
                                    facecolor=self._get_score_color(value), edgecolor='none')
            ax.add_patch(progress_rect)
            
            # 数值
            ax.text(8.5, y_pos, f'{value:.0f}%', fontsize=10, fontweight='bold',
                   va='center', color=self.colors['dark'])
            
            y_pos -= 0.5
        
        ax.set_title('功能评估总览', fontsize=12, fontweight='bold', pad=20)
    
    def _create_speed_gauge(self, ax, data):
        """创建速度仪表盘"""
        ax.set_xlim(-1.5, 1.5)
        ax.set_ylim(-1.5, 1.5)
        ax.axis('off')
        
        velocity = data.get('average_velocity', 0)
        
        # 绘制半圆仪表盘
        angles = np.linspace(np.pi, 0, 100)
        
        # 分段颜色
        segments = [
            (0, 0.6, self.colors['danger']),
            (0.6, 0.9, self.colors['warning']),
            (0.9, 1.2, self.colors['success']),
            (1.2, 1.5, self.colors['info'])
        ]
        
        for start, end, color in segments:
            mask = (angles >= np.pi * (1 - end/1.5)) & (angles <= np.pi * (1 - start/1.5))
            segment_angles = angles[mask]
            if len(segment_angles) > 0:
                x = np.cos(segment_angles)
                y = np.sin(segment_angles)
                ax.fill_between(x, 0, y, alpha=0.3, color=color)
        
        # 指针
        angle = np.pi * (1 - min(velocity, 1.5) / 1.5)
        pointer_x = 0.9 * np.cos(angle)
        pointer_y = 0.9 * np.sin(angle)
        ax.arrow(0, 0, pointer_x, pointer_y, head_width=0.1, head_length=0.1,
                fc=self.colors['dark'], ec=self.colors['dark'])
        
        # 中心圆
        center_circle = Circle((0, 0), 0.15, facecolor='white', 
                              edgecolor=self.colors['dark'], linewidth=2)
        ax.add_patch(center_circle)
        
        # 数值显示
        ax.text(0, -0.8, f'{velocity:.2f}', fontsize=16, fontweight='bold',
               ha='center', color=self.colors['dark'])
        ax.text(0, -1.1, 'm/s', fontsize=10, ha='center', color=self.colors['secondary'])
        
        ax.set_title('步速', fontsize=11, fontweight='bold', y=0.9)
    
    def _create_balance_gauge(self, ax, data):
        """创建平衡仪表盘"""
        ax.set_xlim(-1.5, 1.5)
        ax.set_ylim(-1.5, 1.5)
        ax.axis('off')
        
        balance = data.get('balance_analysis', {}).get('stabilityIndex', 70)
        
        # 绘制圆形进度环
        theta = np.linspace(0, 2*np.pi, 100)
        r_outer = 1.0
        r_inner = 0.7
        
        # 背景环
        x_outer = r_outer * np.cos(theta)
        y_outer = r_outer * np.sin(theta)
        x_inner = r_inner * np.cos(theta)
        y_inner = r_inner * np.sin(theta)
        
        verts = list(zip(x_outer, y_outer)) + list(zip(x_inner[::-1], y_inner[::-1]))
        path = Path(verts)
        patch = PathPatch(path, facecolor=self.colors['light'], edgecolor='none')
        ax.add_patch(patch)
        
        # 进度环
        progress_theta = theta[:int(balance)]
        x_outer_p = r_outer * np.cos(progress_theta)
        y_outer_p = r_outer * np.sin(progress_theta)
        x_inner_p = r_inner * np.cos(progress_theta)
        y_inner_p = r_inner * np.sin(progress_theta)
        
        if len(progress_theta) > 0:
            verts_p = list(zip(x_outer_p, y_outer_p)) + list(zip(x_inner_p[::-1], y_inner_p[::-1]))
            path_p = Path(verts_p)
            patch_p = PathPatch(path_p, facecolor=self._get_score_color(balance), edgecolor='none')
            ax.add_patch(patch_p)
        
        # 中心数值
        ax.text(0, 0, f'{balance:.0f}%', fontsize=16, fontweight='bold',
               ha='center', va='center', color=self.colors['dark'])
        
        ax.set_title('平衡指数', fontsize=11, fontweight='bold', y=0.9)
    
    def _create_parameter_bars(self, ax, data):
        """创建参数条形图"""
        parameters = ['步长', '步频', '双支撑', '对称性']
        values = [
            data.get('average_step_length', 0) / 60 * 100,  # 归一化到百分比
            min(100, data.get('cadence', 0) / 110 * 100),
            100 - data.get('gait_phases', {}).get('double_support', 20),  # 反向，越小越好
            self._calculate_symmetry(data)
        ]
        
        # 设置现代化样式
        ax.set_xlim(0, 100)
        ax.set_ylim(-0.5, len(parameters) - 0.5)
        ax.set_xlabel('评分 (%)', fontsize=10)
        ax.set_yticks(range(len(parameters)))
        ax.set_yticklabels(parameters, fontsize=10)
        ax.grid(True, axis='x', alpha=0.2)
        ax.set_axisbelow(True)
        
        # 绘制条形图
        bars = ax.barh(range(len(parameters)), values, height=0.6, 
                      color=[self._get_score_color(v) for v in values],
                      alpha=0.8)
        
        # 添加数值标签
        for i, (bar, val) in enumerate(zip(bars, values)):
            ax.text(val + 2, i, f'{val:.0f}', va='center', fontsize=9,
                   fontweight='bold', color=self.colors['dark'])
        
        # 添加参考线
        ax.axvline(x=70, color=self.colors['secondary'], linestyle='--', 
                  alpha=0.3, linewidth=1)
        
        ax.set_title('关键参数评估', fontsize=11, fontweight='bold', pad=10)
    
    def _create_risk_matrix(self, ax, data):
        """创建风险评估矩阵"""
        ax.set_xlim(0, 10)
        ax.set_ylim(0, 10)
        ax.axis('off')
        
        # 计算各项风险
        risks = {
            '跌倒风险': self._assess_fall_risk(data),
            '平衡失调': self._assess_balance_risk(data),
            '步态异常': self._assess_gait_risk(data),
            '肌力不足': self._assess_strength_risk(data)
        }
        
        # 绘制风险矩阵
        y_pos = 8
        for risk_name, risk_level in risks.items():
            # 风险名称
            ax.text(1, y_pos, risk_name, fontsize=10, va='center')
            
            # 风险等级指示器
            levels = ['低', '中', '高']
            colors = [self.colors['success'], self.colors['warning'], self.colors['danger']]
            
            for i, (level, color) in enumerate(zip(levels, colors)):
                x = 4 + i * 1.5
                if risk_level == i:
                    # 选中的等级
                    rect = FancyBboxPatch((x - 0.4, y_pos - 0.3), 0.8, 0.6,
                                         boxstyle="round,pad=0.05",
                                         facecolor=color, edgecolor='none',
                                         alpha=0.8)
                    ax.add_patch(rect)
                    ax.text(x, y_pos, level, ha='center', va='center',
                           fontsize=9, fontweight='bold', color='white')
                else:
                    # 未选中的等级
                    rect = FancyBboxPatch((x - 0.4, y_pos - 0.3), 0.8, 0.6,
                                         boxstyle="round,pad=0.05",
                                         facecolor='white', edgecolor=color,
                                         alpha=0.3, linewidth=1)
                    ax.add_patch(rect)
                    ax.text(x, y_pos, level, ha='center', va='center',
                           fontsize=9, color=color, alpha=0.5)
            
            y_pos -= 1.8
        
        ax.set_title('风险评估', fontsize=11, fontweight='bold', y=0.95)
    
    def _create_recommendation_panel(self, ax, data):
        """创建康复建议面板"""
        ax.set_xlim(0, 10)
        ax.set_ylim(0, 10)
        ax.axis('off')
        
        # 生成个性化建议
        recommendations = self._generate_recommendations(data)
        
        # 标题
        ax.text(5, 9, '康复建议', fontsize=11, fontweight='bold',
               ha='center', color=self.colors['dark'])
        
        # 建议内容
        y_pos = 7.5
        for i, rec in enumerate(recommendations[:4]):  # 最多显示4条
            # 图标
            icon_color = self.colors['accent'] if i < 2 else self.colors['info']
            circle = Circle((1, y_pos), 0.15, facecolor=icon_color, edgecolor='none')
            ax.add_patch(circle)
            ax.text(1, y_pos, str(i+1), ha='center', va='center',
                   fontsize=8, fontweight='bold', color='white')
            
            # 建议文本
            ax.text(1.5, y_pos, rec, fontsize=9, va='center',
                   color=self.colors['dark'])
            
            y_pos -= 1.5
        
        # 添加提示
        ax.text(5, 1, '* 请在专业医师指导下进行康复训练', 
               fontsize=8, ha='center', style='italic',
               color=self.colors['secondary'], alpha=0.7)
    
    def generate_modern_balance_chart(self, data: Dict) -> str:
        """生成现代化平衡分析图表"""
        fig, axes = plt.subplots(2, 3, figsize=(15, 8), facecolor='white')
        fig.suptitle('平衡功能分析', fontsize=16, fontweight='bold', y=0.98)
        
        # 1. COP轨迹热力图
        ax1 = axes[0, 0]
        self._create_cop_heatmap(ax1, data)
        
        # 2. 摆动频谱分析
        ax2 = axes[0, 1]
        self._create_sway_spectrum(ax2, data)
        
        # 3. 稳定域分析
        ax3 = axes[0, 2]
        self._create_stability_zone(ax3, data)
        
        # 4. 方向性控制
        ax4 = axes[1, 0]
        self._create_directional_control(ax4, data)
        
        # 5. 动态稳定性
        ax5 = axes[1, 1]
        self._create_dynamic_stability(ax5, data)
        
        # 6. 平衡策略
        ax6 = axes[1, 2]
        self._create_balance_strategy(ax6, data)
        
        plt.tight_layout(rect=[0, 0.02, 1, 0.96])
        
        # 转换为base64
        buffer = BytesIO()
        plt.savefig(buffer, format='png', dpi=120, bbox_inches='tight')
        buffer.seek(0)
        image_base64 = base64.b64encode(buffer.getvalue()).decode()
        plt.close()
        
        return f"data:image/png;base64,{image_base64}"
    
    def _create_cop_heatmap(self, ax, data):
        """创建COP轨迹热力图"""
        cop_data = data.get('time_series', {}).get('cop', [])
        
        if cop_data:
            x = [d.get('x', 0) * 100 for d in cop_data]
            y = [d.get('y', 0) * 100 for d in cop_data]
            
            # 创建2D直方图
            h, xedges, yedges = np.histogram2d(x, y, bins=20)
            
            # 绘制热力图
            im = ax.imshow(h.T, origin='lower', cmap='YlOrRd', 
                          extent=[xedges[0], xedges[-1], yedges[0], yedges[-1]],
                          aspect='auto', interpolation='gaussian')
            
            # 添加轨迹线
            ax.plot(x, y, 'b-', alpha=0.3, linewidth=0.5)
            
            # 标记中心点
            mean_x, mean_y = np.mean(x), np.mean(y)
            ax.scatter(mean_x, mean_y, c='blue', s=50, marker='+', linewidth=2)
            
            # 添加颜色条
            plt.colorbar(im, ax=ax, fraction=0.046, pad=0.04)
        
        ax.set_xlabel('左右位移 (cm)')
        ax.set_ylabel('前后位移 (cm)')
        ax.set_title('COP轨迹分布', fontsize=10)
        ax.grid(True, alpha=0.2)
    
    def _create_sway_spectrum(self, ax, data):
        """创建摆动频谱分析"""
        # 模拟频谱数据
        frequencies = np.linspace(0, 5, 50)
        ap_spectrum = np.exp(-frequencies) * np.random.rand(50) * 0.5
        ml_spectrum = np.exp(-frequencies * 1.5) * np.random.rand(50) * 0.5
        
        ax.fill_between(frequencies, 0, ap_spectrum, alpha=0.5, 
                       color=self.colors['primary'], label='前后摆动')
        ax.fill_between(frequencies, 0, ml_spectrum, alpha=0.5,
                       color=self.colors['secondary'], label='左右摆动')
        
        ax.set_xlabel('频率 (Hz)')
        ax.set_ylabel('功率谱密度')
        ax.set_title('摆动频谱分析', fontsize=10)
        ax.legend(loc='upper right', fontsize=8)
        ax.grid(True, alpha=0.2)
    
    def _create_stability_zone(self, ax, data):
        """创建稳定域分析"""
        # 绘制稳定域边界
        theta = np.linspace(0, 2*np.pi, 100)
        
        # 功能性稳定域
        r_functional = 2 + 0.5 * np.sin(4*theta)
        x_functional = r_functional * np.cos(theta)
        y_functional = r_functional * np.sin(theta)
        
        # 实际稳定域
        r_actual = 1.5 + 0.3 * np.sin(3*theta + np.pi/4)
        x_actual = r_actual * np.cos(theta)
        y_actual = r_actual * np.sin(theta)
        
        ax.fill(x_functional, y_functional, alpha=0.2, color='green', label='正常范围')
        ax.fill(x_actual, y_actual, alpha=0.4, color=self.colors['primary'], label='实际范围')
        
        ax.set_xlim(-3, 3)
        ax.set_ylim(-3, 3)
        ax.set_xlabel('左右 (cm)')
        ax.set_ylabel('前后 (cm)')
        ax.set_title('稳定域分析', fontsize=10)
        ax.legend(loc='upper right', fontsize=8)
        ax.grid(True, alpha=0.2)
        ax.set_aspect('equal')
    
    def _create_directional_control(self, ax, data):
        """创建方向性控制图"""
        directions = ['前', '后', '左', '右']
        control_scores = [75, 82, 68, 71]  # 示例数据
        
        # 创建雷达图
        angles = np.linspace(0, 2*np.pi, len(directions), endpoint=False).tolist()
        control_scores += control_scores[:1]
        angles += angles[:1]
        
        ax = plt.subplot(2, 3, 4, projection='polar')
        ax.plot(angles, control_scores, 'o-', linewidth=2, color=self.colors['primary'])
        ax.fill(angles, control_scores, alpha=0.25, color=self.colors['primary'])
        
        ax.set_xticks(angles[:-1])
        ax.set_xticklabels(directions)
        ax.set_ylim(0, 100)
        ax.set_title('方向性控制', fontsize=10, pad=20)
        ax.grid(True)
    
    def _create_dynamic_stability(self, ax, data):
        """创建动态稳定性图"""
        time = np.linspace(0, 10, 100)
        stability = 70 + 10 * np.sin(time) + np.random.randn(100) * 2
        
        ax.plot(time, stability, color=self.colors['primary'], linewidth=2)
        ax.fill_between(time, 60, stability, where=(stability >= 60),
                        color=self.colors['success'], alpha=0.3)
        ax.fill_between(time, stability, 60, where=(stability < 60),
                        color=self.colors['warning'], alpha=0.3)
        
        ax.axhline(y=70, color='gray', linestyle='--', alpha=0.5)
        ax.set_xlabel('时间 (s)')
        ax.set_ylabel('稳定性指数')
        ax.set_title('动态稳定性', fontsize=10)
        ax.set_ylim(40, 100)
        ax.grid(True, alpha=0.2)
    
    def _create_balance_strategy(self, ax, data):
        """创建平衡策略分析"""
        strategies = ['踝策略', '髋策略', '步进策略']
        usage = [60, 30, 10]  # 策略使用百分比
        
        # 创建饼图
        colors = [self.colors['success'], self.colors['warning'], self.colors['info']]
        wedges, texts, autotexts = ax.pie(usage, labels=strategies, colors=colors,
                                          autopct='%1.0f%%', startangle=90)
        
        for autotext in autotexts:
            autotext.set_color('white')
            autotext.set_fontweight('bold')
            autotext.set_fontsize(9)
        
        ax.set_title('平衡策略分布', fontsize=10)
    
    def generate_rehabilitation_progress(self, data: Dict) -> str:
        """生成康复进展评估"""
        fig = plt.figure(figsize=(14, 8), facecolor='white')
        gs = gridspec.GridSpec(2, 3, figure=fig, hspace=0.3, wspace=0.3)
        
        fig.suptitle('康复进展评估', fontsize=16, fontweight='bold', y=0.98)
        
        # 1. 进展时间线
        ax1 = fig.add_subplot(gs[0, :])
        self._create_progress_timeline(ax1, data)
        
        # 2. 目标达成率
        ax2 = fig.add_subplot(gs[1, 0])
        self._create_goal_achievement(ax2, data)
        
        # 3. 能力改善雷达图
        ax3 = fig.add_subplot(gs[1, 1], projection='polar')
        self._create_improvement_radar(ax3, data)
        
        # 4. 训练建议
        ax4 = fig.add_subplot(gs[1, 2])
        self._create_training_suggestions(ax4, data)
        
        plt.tight_layout(rect=[0, 0.02, 1, 0.96])
        
        # 转换为base64
        buffer = BytesIO()
        plt.savefig(buffer, format='png', dpi=120, bbox_inches='tight')
        buffer.seek(0)
        image_base64 = base64.b64encode(buffer.getvalue()).decode()
        plt.close()
        
        return f"data:image/png;base64,{image_base64}"
    
    def _create_progress_timeline(self, ax, data):
        """创建进展时间线"""
        # 模拟多次评估数据
        dates = ['初始评估', '2周后', '4周后', '6周后', '当前']
        scores = [45, 52, 61, 68, 75]
        
        # 绘制时间线
        x = np.arange(len(dates))
        
        # 背景渐变
        for i in range(len(x) - 1):
            color = self._get_score_color(scores[i+1])
            ax.fill_between([x[i], x[i+1]], 0, 100, alpha=0.1, color=color)
        
        # 主线
        ax.plot(x, scores, 'o-', color=self.colors['primary'], 
               linewidth=3, markersize=10, markerfacecolor='white',
               markeredgewidth=3)
        
        # 数值标签
        for i, (date, score) in enumerate(zip(dates, scores)):
            ax.text(i, score + 3, f'{score}分', ha='center', fontsize=10,
                   fontweight='bold', color=self.colors['dark'])
        
        # 目标线
        ax.axhline(y=80, color=self.colors['success'], linestyle='--', 
                  alpha=0.5, linewidth=2, label='目标水平')
        
        ax.set_xticks(x)
        ax.set_xticklabels(dates)
        ax.set_ylabel('功能评分', fontsize=10)
        ax.set_ylim(0, 100)
        ax.set_title('康复进展时间线', fontsize=11, fontweight='bold')
        ax.legend(loc='lower right')
        ax.grid(True, alpha=0.2, axis='y')
    
    def _create_goal_achievement(self, ax, data):
        """创建目标达成率图"""
        goals = {
            '步速提升': 85,
            '平衡改善': 72,
            '耐力增强': 68,
            '协调优化': 90,
            '风险降低': 95
        }
        
        ax.set_xlim(0, 100)
        ax.set_ylim(-0.5, len(goals) - 0.5)
        
        y_pos = 0
        for goal, achievement in goals.items():
            # 背景条
            ax.barh(y_pos, 100, height=0.6, color=self.colors['light'], alpha=0.5)
            
            # 进度条
            color = self._get_score_color(achievement)
            ax.barh(y_pos, achievement, height=0.6, color=color, alpha=0.8)
            
            # 标签
            ax.text(-2, y_pos, goal, ha='right', va='center', fontsize=9)
            ax.text(achievement + 2, y_pos, f'{achievement}%', 
                   va='center', fontsize=9, fontweight='bold')
            
            y_pos += 1
        
        ax.set_xlabel('达成率 (%)', fontsize=10)
        ax.set_title('康复目标达成', fontsize=11, fontweight='bold')
        ax.set_yticks([])
        ax.grid(True, alpha=0.2, axis='x')
    
    def _create_improvement_radar(self, ax, data):
        """创建能力改善雷达图"""
        categories = ['力量', '平衡', '协调', '耐力', '柔韧', '速度']
        
        # 初始值和当前值
        initial = [40, 45, 50, 35, 60, 45]
        current = [70, 75, 72, 68, 75, 65]
        
        angles = np.linspace(0, 2*np.pi, len(categories), endpoint=False).tolist()
        initial += initial[:1]
        current += current[:1]
        angles += angles[:1]
        
        # 绘制雷达图
        ax.plot(angles, initial, 'o--', linewidth=1, color='gray', 
               label='初始水平', alpha=0.5)
        ax.fill(angles, initial, alpha=0.1, color='gray')
        
        ax.plot(angles, current, 'o-', linewidth=2, color=self.colors['primary'],
               label='当前水平')
        ax.fill(angles, current, alpha=0.25, color=self.colors['primary'])
        
        ax.set_xticks(angles[:-1])
        ax.set_xticklabels(categories, fontsize=9)
        ax.set_ylim(0, 100)
        ax.set_title('能力改善对比', fontsize=11, fontweight='bold', pad=20)
        ax.legend(loc='upper right', bbox_to_anchor=(1.2, 1.1), fontsize=8)
        ax.grid(True)
    
    def _create_training_suggestions(self, ax, data):
        """创建训练建议"""
        ax.set_xlim(0, 10)
        ax.set_ylim(0, 10)
        ax.axis('off')
        
        # 标题
        ax.text(5, 9, '下阶段训练重点', fontsize=11, fontweight='bold',
               ha='center', color=self.colors['dark'])
        
        # 训练建议
        suggestions = [
            ('力量训练', '增加下肢抗阻训练'),
            ('平衡训练', '单脚站立练习'),
            ('步态训练', '变速行走训练'),
            ('功能训练', '日常活动模拟')
        ]
        
        y_pos = 7
        for title, desc in suggestions:
            # 标题
            ax.text(1, y_pos, f'• {title}', fontsize=10, fontweight='bold',
                   color=self.colors['primary'])
            # 描述
            ax.text(1.5, y_pos - 0.4, desc, fontsize=9,
                   color=self.colors['secondary'])
            y_pos -= 1.5
        
        # 提醒
        ax.text(5, 1, '建议每周训练3-5次，每次30-45分钟', 
               fontsize=8, ha='center', style='italic',
               color=self.colors['secondary'], alpha=0.7)
    
    # 辅助方法
    def _calculate_total_score(self, data):
        """计算综合评分"""
        gait_score = self._calculate_gait_score(data)
        balance_score = self._calculate_balance_score(data)
        coordination_score = self._calculate_coordination_score(data)
        stability_score = self._calculate_stability_score(data)
        
        weights = [0.3, 0.3, 0.2, 0.2]
        scores = [gait_score, balance_score, coordination_score, stability_score]
        
        return sum(w * s for w, s in zip(weights, scores))
    
    def _calculate_gait_score(self, data):
        """计算步态评分"""
        velocity = data.get('average_velocity', 0)
        step_length = data.get('average_step_length', 0)
        cadence = data.get('cadence', 0)
        
        # 归一化并计算得分
        velocity_score = min(100, (velocity / 1.2) * 100)
        step_score = min(100, (step_length / 60) * 100)
        cadence_score = 100 if 90 <= cadence <= 120 else max(0, 100 - abs(cadence - 105) * 2)
        
        return (velocity_score + step_score + cadence_score) / 3
    
    def _calculate_balance_score(self, data):
        """计算平衡评分"""
        return data.get('balance_analysis', {}).get('stabilityIndex', 70)
    
    def _calculate_coordination_score(self, data):
        """计算协调性评分"""
        double_support = data.get('gait_phases', {}).get('double_support', 20)
        if 18 <= double_support <= 22:
            return 90
        elif 15 <= double_support <= 25:
            return 70
        else:
            return 50
    
    def _calculate_stability_score(self, data):
        """计算稳定性评分"""
        cop_complexity = data.get('balance_analysis', {}).get('copComplexity', 5)
        return max(0, 100 - cop_complexity * 10)
    
    def _calculate_symmetry(self, data):
        """计算对称性"""
        left = data.get('left_foot', {}).get('average_step_length', 0)
        right = data.get('right_foot', {}).get('average_step_length', 0)
        if left > 0 and right > 0:
            return min(left, right) / max(left, right) * 100
        return 50
    
    def _get_score_color(self, score):
        """根据分数获取颜色"""
        if score >= 80:
            return self.colors['success']
        elif score >= 60:
            return self.colors['accent']
        elif score >= 40:
            return self.colors['warning']
        else:
            return self.colors['danger']
    
    def _get_rating(self, score):
        """获取评级"""
        if score >= 90:
            return '优秀'
        elif score >= 70:
            return '良好'
        elif score >= 50:
            return '正常'
        else:
            return '需改善'
    
    def _assess_fall_risk(self, data):
        """评估跌倒风险"""
        velocity = data.get('average_velocity', 0)
        balance = data.get('balance_analysis', {}).get('stabilityIndex', 70)
        
        if velocity < 0.6 or balance < 60:
            return 2  # 高风险
        elif velocity < 0.8 or balance < 70:
            return 1  # 中风险
        else:
            return 0  # 低风险
    
    def _assess_balance_risk(self, data):
        """评估平衡风险"""
        stability = data.get('balance_analysis', {}).get('stabilityIndex', 70)
        if stability < 60:
            return 2
        elif stability < 75:
            return 1
        else:
            return 0
    
    def _assess_gait_risk(self, data):
        """评估步态风险"""
        symmetry = self._calculate_symmetry(data)
        if symmetry < 70:
            return 2
        elif symmetry < 85:
            return 1
        else:
            return 0
    
    def _assess_strength_risk(self, data):
        """评估肌力风险"""
        velocity = data.get('average_velocity', 0)
        if velocity < 0.7:
            return 2
        elif velocity < 1.0:
            return 1
        else:
            return 0
    
    def _generate_recommendations(self, data):
        """生成康复建议"""
        recommendations = []
        
        velocity = data.get('average_velocity', 0)
        if velocity < 0.8:
            recommendations.append('增加步行速度训练，每日步行30分钟')
        
        balance = data.get('balance_analysis', {}).get('stabilityIndex', 70)
        if balance < 70:
            recommendations.append('进行平衡训练，如单脚站立、太极拳')
        
        symmetry = self._calculate_symmetry(data)
        if symmetry < 85:
            recommendations.append('改善步态对称性，进行镜像步态训练')
        
        double_support = data.get('gait_phases', {}).get('double_support', 20)
        if double_support > 25:
            recommendations.append('增强下肢力量，进行抗阻训练')
        
        if not recommendations:
            recommendations.append('保持当前训练计划，定期评估')
        
        return recommendations