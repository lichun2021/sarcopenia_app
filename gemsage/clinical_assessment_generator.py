#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
临床评估分析图表生成器
生成专业的步态功能评估图表
2025-08-13
"""

import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.patches import Rectangle, FancyBboxPatch
import seaborn as sns
from typing import Dict, List, Optional, Tuple
import base64
from io import BytesIO
import warnings
warnings.filterwarnings('ignore')

# 设置中文字体
plt.rcParams['font.sans-serif'] = ['PingFang SC', 'Heiti TC', 'STHeiti', 'SimHei', 'Arial Unicode MS']
plt.rcParams['axes.unicode_minus'] = False

class ClinicalAssessmentGenerator:
    """临床评估分析图表生成器"""
    
    def __init__(self):
        """初始化评估生成器"""
        # 专业配色方案
        self.colors = {
            'excellent': '#2ECC71',  # 优秀 - 绿色
            'good': '#3498DB',       # 良好 - 蓝色
            'normal': '#F39C12',     # 正常 - 橙色
            'warning': '#E74C3C',    # 警告 - 红色
            'primary': '#2E86AB',
            'secondary': '#A23B72',
            'gray': '#95A5A6',
            'light_gray': '#ECF0F1'
        }
        
        # 步态功能评级标准
        self.gait_standards = {
            'excellent': {'min': 90, 'max': 100, 'label': '优秀'},
            'good': {'min': 70, 'max': 89, 'label': '良好'},
            'normal': {'min': 50, 'max': 69, 'label': '正常'},
            'warning': {'min': 0, 'max': 49, 'label': '需关注'}
        }
    
    def calculate_gait_score(self, gait_data: Dict) -> float:
        """计算综合步态评分（0-100分）"""
        score = 100.0
        
        # 步速评分（占30%）
        velocity = gait_data.get('average_velocity', 0)
        if velocity < 0.8:
            velocity_score = velocity / 0.8 * 30
        elif velocity <= 1.4:
            velocity_score = 30
        else:
            velocity_score = max(20, 30 - (velocity - 1.4) * 20)
        
        # 步长对称性评分（占20%）
        left_length = gait_data.get('left_foot', {}).get('average_step_length', 0)
        right_length = gait_data.get('right_foot', {}).get('average_step_length', 0)
        if left_length > 0 and right_length > 0:
            symmetry = min(left_length, right_length) / max(left_length, right_length)
            symmetry_score = symmetry * 20
        else:
            symmetry_score = 10
        
        # 步态相位评分（占20%）
        stance_phase = gait_data.get('gait_phases', {}).get('stance_phase', 62)
        phase_deviation = abs(stance_phase - 62)
        phase_score = max(0, 20 - phase_deviation * 0.5)
        
        # 步频评分（占15%）
        cadence = gait_data.get('cadence', 0)
        if 90 <= cadence <= 120:
            cadence_score = 15
        else:
            deviation = min(abs(cadence - 90), abs(cadence - 120))
            cadence_score = max(0, 15 - deviation * 0.2)
        
        # 稳定性评分（占15%）
        stability_index = gait_data.get('balance_analysis', {}).get('stabilityIndex', 70)
        stability_score = stability_index / 100 * 15
        
        total_score = velocity_score + symmetry_score + phase_score + cadence_score + stability_score
        return min(100, max(0, total_score))
    
    def generate_gait_assessment_chart(self, gait_data: Dict) -> str:
        """生成步态功能综合评估图表"""
        fig, axes = plt.subplots(2, 3, figsize=(15, 10))
        fig.suptitle('步态功能临床评估', fontsize=16, fontweight='bold')
        
        # 计算综合评分
        total_score = self.calculate_gait_score(gait_data)
        
        # 1. 综合评分仪表盘
        ax1 = axes[0, 0]
        self._create_gauge_chart(ax1, total_score, '综合评分')
        
        # 2. 功能指标雷达图
        ax2 = plt.subplot(2, 3, 2, projection='polar')
        self._create_radar_chart(ax2, gait_data)
        
        # 3. 跌倒风险评估
        ax3 = axes[0, 2]
        fall_risk = self._assess_fall_risk(gait_data)
        self._create_risk_assessment(ax3, fall_risk)
        
        # 4. 步态参数对比
        ax4 = axes[1, 0]
        self._create_parameter_comparison(ax4, gait_data)
        
        # 5. 功能状态评级
        ax5 = axes[1, 1]
        self._create_functional_rating(ax5, gait_data)
        
        # 6. 临床建议
        ax6 = axes[1, 2]
        self._create_clinical_recommendations(ax6, total_score, gait_data)
        
        plt.tight_layout()
        
        # 转换为base64
        buffer = BytesIO()
        plt.savefig(buffer, format='png', dpi=100, bbox_inches='tight')
        buffer.seek(0)
        image_base64 = base64.b64encode(buffer.getvalue()).decode()
        plt.close()
        
        return f"data:image/png;base64,{image_base64}"
    
    def _create_gauge_chart(self, ax, score, title):
        """创建仪表盘图表"""
        ax.set_xlim(0, 10)
        ax.set_ylim(0, 10)
        ax.axis('off')
        
        # 绘制半圆弧
        theta = np.linspace(np.pi, 0, 100)
        for level, info in self.gait_standards.items():
            start_angle = np.pi * (1 - info['min'] / 100)
            end_angle = np.pi * (1 - info['max'] / 100)
            theta_range = np.linspace(start_angle, end_angle, 20)
            x = 5 + 4 * np.cos(theta_range)
            y = 2 + 4 * np.sin(theta_range)
            ax.fill_between(x, 2, y, alpha=0.3, color=self.colors[level])
        
        # 绘制指针
        angle = np.pi * (1 - score / 100)
        x_pointer = 5 + 3.5 * np.cos(angle)
        y_pointer = 2 + 3.5 * np.sin(angle)
        ax.arrow(5, 2, x_pointer - 5, y_pointer - 2, 
                head_width=0.3, head_length=0.2, fc='black', ec='black')
        
        # 添加分数
        ax.text(5, 1, f'{score:.1f}分', ha='center', fontsize=20, fontweight='bold')
        
        # 添加评级
        for level, info in self.gait_standards.items():
            if info['min'] <= score <= info['max']:
                ax.text(5, 0, info['label'], ha='center', fontsize=14, 
                       color=self.colors[level], fontweight='bold')
                break
        
        ax.set_title(title, fontsize=12, pad=20)
    
    def _create_radar_chart(self, ax, gait_data):
        """创建功能指标雷达图"""
        categories = ['步速', '步长', '步频', '平衡', '对称性', '协调性']
        N = len(categories)
        
        # 计算各项指标得分（0-100）
        scores = []
        
        # 步速得分
        velocity = gait_data.get('average_velocity', 0)
        velocity_score = min(100, max(0, (velocity / 1.2) * 100))
        scores.append(velocity_score)
        
        # 步长得分
        step_length = gait_data.get('average_step_length', 0)
        step_score = min(100, max(0, (step_length / 60) * 100))
        scores.append(step_score)
        
        # 步频得分
        cadence = gait_data.get('cadence', 0)
        if 90 <= cadence <= 120:
            cadence_score = 100
        else:
            cadence_score = max(0, 100 - abs(cadence - 105) * 2)
        scores.append(cadence_score)
        
        # 平衡得分
        balance_score = gait_data.get('balance_analysis', {}).get('stabilityIndex', 70)
        scores.append(balance_score)
        
        # 对称性得分
        left_foot = gait_data.get('left_foot', {})
        right_foot = gait_data.get('right_foot', {})
        if left_foot and right_foot:
            left_length = left_foot.get('average_step_length', 0)
            right_length = right_foot.get('average_step_length', 0)
            if left_length > 0 and right_length > 0:
                symmetry = min(left_length, right_length) / max(left_length, right_length) * 100
            else:
                symmetry = 50
        else:
            symmetry = 50
        scores.append(symmetry)
        
        # 协调性得分（基于双支撑相）
        double_support = gait_data.get('gait_phases', {}).get('double_support', 20)
        if 15 <= double_support <= 25:
            coordination_score = 100
        else:
            coordination_score = max(0, 100 - abs(double_support - 20) * 5)
        scores.append(coordination_score)
        
        # 设置角度
        angles = [n / float(N) * 2 * np.pi for n in range(N)]
        scores += scores[:1]
        angles += angles[:1]
        
        # 绘制雷达图
        ax.plot(angles, scores, 'o-', linewidth=2, color=self.colors['primary'])
        ax.fill(angles, scores, alpha=0.25, color=self.colors['primary'])
        
        # 添加参考线
        for i in range(20, 101, 20):
            ax.plot(angles, [i] * (N + 1), '--', linewidth=0.5, color='gray', alpha=0.3)
        
        # 设置标签
        ax.set_xticks(angles[:-1])
        ax.set_xticklabels(categories)
        ax.set_ylim(0, 100)
        ax.set_title('功能指标评估', fontsize=12, pad=20)
    
    def _assess_fall_risk(self, gait_data) -> Dict:
        """评估跌倒风险"""
        risk_factors = []
        risk_level = 'low'
        
        # 步速风险
        velocity = gait_data.get('average_velocity', 0)
        if velocity < 0.6:
            risk_factors.append('步速过慢')
            risk_level = 'high'
        elif velocity < 0.8:
            risk_factors.append('步速偏慢')
            if risk_level == 'low':
                risk_level = 'medium'
        
        # 稳定性风险
        stability = gait_data.get('balance_analysis', {}).get('stabilityIndex', 70)
        if stability < 60:
            risk_factors.append('平衡能力差')
            risk_level = 'high'
        elif stability < 70:
            risk_factors.append('平衡能力欠佳')
            if risk_level == 'low':
                risk_level = 'medium'
        
        # 对称性风险
        left_length = gait_data.get('left_foot', {}).get('average_step_length', 0)
        right_length = gait_data.get('right_foot', {}).get('average_step_length', 0)
        if left_length > 0 and right_length > 0:
            asymmetry = abs(left_length - right_length) / max(left_length, right_length)
            if asymmetry > 0.2:
                risk_factors.append('步态不对称')
                if risk_level == 'low':
                    risk_level = 'medium'
        
        # 双支撑相风险
        double_support = gait_data.get('gait_phases', {}).get('double_support', 20)
        if double_support > 30:
            risk_factors.append('双支撑相延长')
            if risk_level == 'low':
                risk_level = 'medium'
        
        return {
            'level': risk_level,
            'factors': risk_factors,
            'score': {'low': 30, 'medium': 60, 'high': 90}[risk_level]
        }
    
    def _create_risk_assessment(self, ax, fall_risk):
        """创建跌倒风险评估图"""
        ax.set_xlim(0, 10)
        ax.set_ylim(0, 10)
        ax.axis('off')
        
        # 风险等级颜色
        risk_colors = {
            'low': self.colors['excellent'],
            'medium': self.colors['normal'],
            'high': self.colors['warning']
        }
        
        risk_labels = {
            'low': '低风险',
            'medium': '中风险',
            'high': '高风险'
        }
        
        # 绘制风险条
        ax.add_patch(Rectangle((1, 6), 8, 1.5, 
                               facecolor=risk_colors[fall_risk['level']], 
                               edgecolor='black', linewidth=2))
        
        # 添加风险等级文字
        ax.text(5, 6.75, risk_labels[fall_risk['level']], 
               ha='center', va='center', fontsize=14, 
               fontweight='bold', color='white')
        
        # 添加风险因素
        ax.text(5, 4.5, '风险因素：', ha='center', fontsize=11, fontweight='bold')
        
        if fall_risk['factors']:
            factors_text = '\n'.join(f'• {factor}' for factor in fall_risk['factors'])
        else:
            factors_text = '无明显风险因素'
        
        ax.text(5, 3, factors_text, ha='center', va='top', fontsize=10)
        
        ax.set_title('跌倒风险评估', fontsize=12, pad=20)
    
    def _create_parameter_comparison(self, ax, gait_data):
        """创建步态参数对比图"""
        parameters = []
        values = []
        normal_ranges = []
        
        # 步速
        parameters.append('步速\n(m/s)')
        values.append(gait_data.get('average_velocity', 0))
        normal_ranges.append((0.9, 1.4))
        
        # 步长
        parameters.append('步长\n(cm)')
        values.append(gait_data.get('average_step_length', 0))
        normal_ranges.append((50, 65))
        
        # 步频
        parameters.append('步频\n(步/分)')
        values.append(gait_data.get('cadence', 0))
        normal_ranges.append((90, 120))
        
        # 站立相
        parameters.append('站立相\n(%)')
        values.append(gait_data.get('gait_phases', {}).get('stance_phase', 62))
        normal_ranges.append((60, 65))
        
        x = np.arange(len(parameters))
        width = 0.35
        
        # 绘制正常范围
        for i, (low, high) in enumerate(normal_ranges):
            ax.axhspan(low, high, xmin=i/len(parameters), xmax=(i+1)/len(parameters), 
                      alpha=0.2, color='green')
        
        # 绘制实际值
        colors = []
        for val, (low, high) in zip(values, normal_ranges):
            if low <= val <= high:
                colors.append(self.colors['excellent'])
            elif val < low * 0.8 or val > high * 1.2:
                colors.append(self.colors['warning'])
            else:
                colors.append(self.colors['normal'])
        
        bars = ax.bar(x, values, width, color=colors)
        
        # 添加数值标签
        for bar, val in zip(bars, values):
            height = bar.get_height()
            ax.text(bar.get_x() + bar.get_width()/2., height,
                   f'{val:.1f}' if val < 10 else f'{val:.0f}',
                   ha='center', va='bottom', fontsize=10)
        
        ax.set_xlabel('参数')
        ax.set_ylabel('数值')
        ax.set_title('关键参数评估')
        ax.set_xticks(x)
        ax.set_xticklabels(parameters)
        ax.grid(True, alpha=0.3, axis='y')
    
    def _create_functional_rating(self, ax, gait_data):
        """创建功能状态评级"""
        ax.axis('off')
        
        # 计算各项功能评级
        ratings = []
        
        # 移动能力
        velocity = gait_data.get('average_velocity', 0)
        if velocity >= 1.2:
            mobility = ('移动能力', '优秀', self.colors['excellent'])
        elif velocity >= 0.8:
            mobility = ('移动能力', '良好', self.colors['good'])
        elif velocity >= 0.6:
            mobility = ('移动能力', '正常', self.colors['normal'])
        else:
            mobility = ('移动能力', '需改善', self.colors['warning'])
        ratings.append(mobility)
        
        # 平衡能力
        stability = gait_data.get('balance_analysis', {}).get('stabilityIndex', 70)
        if stability >= 85:
            balance = ('平衡能力', '优秀', self.colors['excellent'])
        elif stability >= 70:
            balance = ('平衡能力', '良好', self.colors['good'])
        elif stability >= 60:
            balance = ('平衡能力', '正常', self.colors['normal'])
        else:
            balance = ('平衡能力', '需改善', self.colors['warning'])
        ratings.append(balance)
        
        # 耐力状态
        cadence = gait_data.get('cadence', 0)
        if 100 <= cadence <= 115:
            endurance = ('耐力状态', '优秀', self.colors['excellent'])
        elif 90 <= cadence <= 120:
            endurance = ('耐力状态', '良好', self.colors['good'])
        elif 80 <= cadence <= 130:
            endurance = ('耐力状态', '正常', self.colors['normal'])
        else:
            endurance = ('耐力状态', '需改善', self.colors['warning'])
        ratings.append(endurance)
        
        # 协调性
        double_support = gait_data.get('gait_phases', {}).get('double_support', 20)
        if 18 <= double_support <= 22:
            coordination = ('协调性', '优秀', self.colors['excellent'])
        elif 15 <= double_support <= 25:
            coordination = ('协调性', '良好', self.colors['good'])
        elif 10 <= double_support <= 30:
            coordination = ('协调性', '正常', self.colors['normal'])
        else:
            coordination = ('协调性', '需改善', self.colors['warning'])
        ratings.append(coordination)
        
        # 绘制评级表
        y_pos = 0.8
        for name, rating, color in ratings:
            # 功能名称
            ax.text(0.2, y_pos, name, fontsize=11, va='center')
            
            # 评级框
            bbox = FancyBboxPatch((0.5, y_pos - 0.05), 0.3, 0.1,
                                  boxstyle="round,pad=0.02",
                                  facecolor=color, edgecolor='none',
                                  alpha=0.7)
            ax.add_patch(bbox)
            
            # 评级文字
            ax.text(0.65, y_pos, rating, ha='center', va='center',
                   fontsize=10, color='white', fontweight='bold')
            
            y_pos -= 0.2
        
        ax.set_xlim(0, 1)
        ax.set_ylim(0, 1)
        ax.set_title('功能状态评级', fontsize=12)
    
    def _create_clinical_recommendations(self, ax, total_score, gait_data):
        """创建临床建议"""
        ax.axis('off')
        
        recommendations = []
        
        # 基于总分的建议
        if total_score >= 90:
            recommendations.append("• 保持当前运动习惯")
            recommendations.append("• 定期进行平衡训练")
        elif total_score >= 70:
            recommendations.append("• 增加步行训练")
            recommendations.append("• 加强下肢力量训练")
        elif total_score >= 50:
            recommendations.append("• 建议康复训练")
            recommendations.append("• 使用辅助行走设备")
            recommendations.append("• 定期医疗评估")
        else:
            recommendations.append("• 需要专业康复指导")
            recommendations.append("• 防跌倒措施")
            recommendations.append("• 密切医疗监护")
        
        # 特定问题建议
        velocity = gait_data.get('average_velocity', 0)
        if velocity < 0.8:
            recommendations.append("• 提高步行速度训练")
        
        stability = gait_data.get('balance_analysis', {}).get('stabilityIndex', 70)
        if stability < 70:
            recommendations.append("• 平衡功能训练")
        
        # 显示建议
        ax.text(0.5, 0.9, '临床建议', ha='center', fontsize=12, fontweight='bold')
        
        rec_text = '\n'.join(recommendations[:5])  # 最多显示5条
        ax.text(0.5, 0.7, rec_text, ha='center', va='top', fontsize=10,
               bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.5))
        
        ax.set_xlim(0, 1)
        ax.set_ylim(0, 1)
        ax.set_title('个性化建议', fontsize=12)
    
    def generate_balance_assessment_chart(self, balance_data: Dict, cop_data: List[Dict]) -> str:
        """生成平衡功能评估图表"""
        fig, axes = plt.subplots(2, 2, figsize=(12, 10))
        fig.suptitle('平衡功能临床评估', fontsize=16, fontweight='bold')
        
        # 1. 稳定性评分
        ax1 = axes[0, 0]
        stability_score = balance_data.get('stabilityIndex', 70)
        self._create_stability_gauge(ax1, stability_score)
        
        # 2. COP摆动分析
        ax2 = axes[0, 1]
        self._create_sway_analysis(ax2, balance_data)
        
        # 3. 姿势控制评估
        ax3 = axes[1, 0]
        self._create_postural_control(ax3, cop_data)
        
        # 4. 平衡策略分析
        ax4 = axes[1, 1]
        self._create_balance_strategy(ax4, balance_data)
        
        plt.tight_layout()
        
        # 转换为base64
        buffer = BytesIO()
        plt.savefig(buffer, format='png', dpi=100, bbox_inches='tight')
        buffer.seek(0)
        image_base64 = base64.b64encode(buffer.getvalue()).decode()
        plt.close()
        
        return f"data:image/png;base64,{image_base64}"
    
    def _create_stability_gauge(self, ax, score):
        """创建稳定性仪表盘"""
        self._create_gauge_chart(ax, score, '稳定性指数')
    
    def _create_sway_analysis(self, ax, balance_data):
        """创建摆动分析图"""
        categories = ['前后摆动', '左右摆动', '轨迹长度', '摆动面积']
        values = [
            balance_data.get('anteroPosteriorRange', 0),
            balance_data.get('medioLateralRange', 0),
            balance_data.get('copPathLength', 0) / 10,  # 归一化
            balance_data.get('copArea', 0) / 10  # 归一化
        ]
        
        x = np.arange(len(categories))
        colors = [self.colors['primary'], self.colors['secondary'], 
                 self.colors['normal'], self.colors['good']]
        
        bars = ax.bar(x, values, color=colors, alpha=0.7)
        
        for bar, val in zip(bars, values):
            height = bar.get_height()
            ax.text(bar.get_x() + bar.get_width()/2., height,
                   f'{val:.1f}', ha='center', va='bottom')
        
        ax.set_xlabel('参数')
        ax.set_ylabel('数值')
        ax.set_title('摆动参数分析')
        ax.set_xticks(x)
        ax.set_xticklabels(categories, rotation=15)
        ax.grid(True, alpha=0.3, axis='y')
    
    def _create_postural_control(self, ax, cop_data):
        """创建姿势控制评估"""
        if not cop_data or len(cop_data) < 2:
            ax.text(0.5, 0.5, '数据不足', ha='center', va='center')
            ax.axis('off')
            return
        
        # 提取COP数据
        x_coords = [d.get('x', 0) * 100 for d in cop_data[:100]]  # 取前100个点
        y_coords = [d.get('y', 0) * 100 for d in cop_data[:100]]
        
        # 计算质心偏移
        mean_x = np.mean(x_coords)
        mean_y = np.mean(y_coords)
        
        # 绘制COP分布
        ax.scatter(x_coords, y_coords, alpha=0.3, s=10, c=range(len(x_coords)), cmap='viridis')
        ax.scatter(mean_x, mean_y, c='red', s=100, marker='+', label='平均位置')
        
        # 添加参考圆
        circle = plt.Circle((mean_x, mean_y), np.std(x_coords + y_coords), 
                           fill=False, linestyle='--', color='gray', label='标准偏差圆')
        ax.add_patch(circle)
        
        ax.set_xlabel('左右位移 (cm)')
        ax.set_ylabel('前后位移 (cm)')
        ax.set_title('姿势控制分布')
        ax.legend()
        ax.grid(True, alpha=0.3)
        ax.axis('equal')
    
    def _create_balance_strategy(self, ax, balance_data):
        """创建平衡策略分析"""
        ax.axis('off')
        
        # 评估平衡策略
        strategies = []
        
        ap_range = balance_data.get('anteroPosteriorRange', 0)
        ml_range = balance_data.get('medioLateralRange', 0)
        
        if ap_range < 3:
            strategies.append(('踝策略', '正常', self.colors['excellent']))
        elif ap_range < 5:
            strategies.append(('踝策略', '轻度受损', self.colors['normal']))
        else:
            strategies.append(('髋策略', '代偿', self.colors['warning']))
        
        if ml_range < 2:
            strategies.append(('侧向控制', '良好', self.colors['excellent']))
        elif ml_range < 4:
            strategies.append(('侧向控制', '一般', self.colors['normal']))
        else:
            strategies.append(('侧向控制', '差', self.colors['warning']))
        
        cop_complexity = balance_data.get('copComplexity', 0)
        if cop_complexity < 5:
            strategies.append(('控制复杂度', '简单', self.colors['excellent']))
        elif cop_complexity < 10:
            strategies.append(('控制复杂度', '中等', self.colors['normal']))
        else:
            strategies.append(('控制复杂度', '复杂', self.colors['warning']))
        
        # 显示策略评估
        ax.text(0.5, 0.9, '平衡策略评估', ha='center', fontsize=12, fontweight='bold')
        
        y_pos = 0.7
        for name, status, color in strategies:
            ax.text(0.3, y_pos, f'{name}:', fontsize=10, va='center')
            
            bbox = FancyBboxPatch((0.5, y_pos - 0.03), 0.2, 0.06,
                                  boxstyle="round,pad=0.01",
                                  facecolor=color, edgecolor='none',
                                  alpha=0.7)
            ax.add_patch(bbox)
            
            ax.text(0.6, y_pos, status, ha='center', va='center',
                   fontsize=9, color='white', fontweight='bold')
            
            y_pos -= 0.15
        
        ax.set_xlim(0, 1)
        ax.set_ylim(0, 1)
        ax.set_title('策略分析', fontsize=12)
    
    def generate_rehabilitation_progress_chart(self, current_data: Dict, reference_data: Optional[Dict] = None) -> str:
        """生成康复进展评估图表"""
        fig, axes = plt.subplots(2, 2, figsize=(12, 10))
        fig.suptitle('康复进展评估', fontsize=16, fontweight='bold')
        
        # 1. 功能改善趋势
        ax1 = axes[0, 0]
        self._create_improvement_trend(ax1, current_data, reference_data)
        
        # 2. 目标达成度
        ax2 = axes[0, 1]
        self._create_goal_achievement(ax2, current_data)
        
        # 3. 能力对比
        ax3 = axes[1, 0]
        self._create_capability_comparison(ax3, current_data, reference_data)
        
        # 4. 康复建议
        ax4 = axes[1, 1]
        self._create_rehabilitation_advice(ax4, current_data)
        
        plt.tight_layout()
        
        # 转换为base64
        buffer = BytesIO()
        plt.savefig(buffer, format='png', dpi=100, bbox_inches='tight')
        buffer.seek(0)
        image_base64 = base64.b64encode(buffer.getvalue()).decode()
        plt.close()
        
        return f"data:image/png;base64,{image_base64}"
    
    def _create_improvement_trend(self, ax, current_data, reference_data):
        """创建功能改善趋势图"""
        parameters = ['步速', '步长', '平衡', '耐力']
        
        # 当前值
        current_values = [
            current_data.get('average_velocity', 0) / 1.2 * 100,
            current_data.get('average_step_length', 0) / 60 * 100,
            current_data.get('balance_analysis', {}).get('stabilityIndex', 70),
            min(100, current_data.get('cadence', 0) / 100 * 100)
        ]
        
        # 参考值（如果没有历史数据，使用正常值）
        if reference_data:
            reference_values = [
                reference_data.get('average_velocity', 1.0) / 1.2 * 100,
                reference_data.get('average_step_length', 55) / 60 * 100,
                reference_data.get('balance_analysis', {}).get('stabilityIndex', 75),
                min(100, reference_data.get('cadence', 105) / 100 * 100)
            ]
        else:
            reference_values = [83, 92, 75, 100]  # 正常参考值
        
        x = np.arange(len(parameters))
        width = 0.35
        
        bars1 = ax.bar(x - width/2, reference_values, width, label='参考值', 
                      color=self.colors['gray'], alpha=0.5)
        bars2 = ax.bar(x + width/2, current_values, width, label='当前值',
                      color=self.colors['primary'], alpha=0.7)
        
        # 添加改善箭头
        for i, (ref, cur) in enumerate(zip(reference_values, current_values)):
            if cur > ref:
                ax.annotate('', xy=(i + width/2, cur), xytext=(i - width/2, ref),
                           arrowprops=dict(arrowstyle='->', color='green', lw=2))
            elif cur < ref:
                ax.annotate('', xy=(i + width/2, cur), xytext=(i - width/2, ref),
                           arrowprops=dict(arrowstyle='->', color='red', lw=2))
        
        ax.set_xlabel('功能指标')
        ax.set_ylabel('评分 (%)')
        ax.set_title('功能改善趋势')
        ax.set_xticks(x)
        ax.set_xticklabels(parameters)
        ax.legend()
        ax.grid(True, alpha=0.3, axis='y')
    
    def _create_goal_achievement(self, ax, current_data):
        """创建目标达成度图表"""
        # 设定康复目标
        goals = {
            '步速 > 1.0 m/s': current_data.get('average_velocity', 0) >= 1.0,
            '步长 > 55 cm': current_data.get('average_step_length', 0) >= 55,
            '步频正常': 90 <= current_data.get('cadence', 0) <= 120,
            '平衡稳定': current_data.get('balance_analysis', {}).get('stabilityIndex', 0) >= 70,
            '对称性良好': self._check_symmetry(current_data)
        }
        
        achieved = sum(goals.values())
        total = len(goals)
        achievement_rate = achieved / total * 100
        
        # 绘制饼图
        sizes = [achieved, total - achieved]
        colors = [self.colors['excellent'], self.colors['light_gray']]
        labels = [f'已达成 ({achieved})', f'未达成 ({total - achieved})']
        
        wedges, texts, autotexts = ax.pie(sizes, labels=labels, colors=colors,
                                          autopct='%1.0f%%', startangle=90)
        
        # 显示具体目标
        goal_text = '\n'.join([f'{"✓" if achieved else "✗"} {goal}' 
                              for goal, achieved in goals.items()])
        
        ax.text(1.5, 0, goal_text, fontsize=9, va='center')
        
        ax.set_title(f'目标达成度: {achievement_rate:.0f}%', fontsize=12)
    
    def _check_symmetry(self, data):
        """检查步态对称性"""
        left = data.get('left_foot', {}).get('average_step_length', 0)
        right = data.get('right_foot', {}).get('average_step_length', 0)
        if left > 0 and right > 0:
            return abs(left - right) / max(left, right) < 0.1
        return False
    
    def _create_capability_comparison(self, ax, current_data, reference_data):
        """创建能力对比雷达图"""
        ax = plt.subplot(2, 2, 3, projection='polar')
        
        categories = ['行走', '平衡', '协调', '耐力', '稳定']
        N = len(categories)
        
        # 计算能力值
        current_scores = [
            min(100, current_data.get('average_velocity', 0) / 1.2 * 100),
            current_data.get('balance_analysis', {}).get('stabilityIndex', 70),
            self._calculate_coordination_score(current_data),
            self._calculate_endurance_score(current_data),
            100 - current_data.get('balance_analysis', {}).get('copComplexity', 5) * 10
        ]
        
        # 正常参考值
        normal_scores = [85, 75, 80, 85, 80]
        
        angles = [n / float(N) * 2 * np.pi for n in range(N)]
        current_scores += current_scores[:1]
        normal_scores += normal_scores[:1]
        angles += angles[:1]
        
        # 绘制雷达图
        ax.plot(angles, normal_scores, 'o--', linewidth=1, color='gray', label='正常范围')
        ax.fill(angles, normal_scores, alpha=0.1, color='gray')
        
        ax.plot(angles, current_scores, 'o-', linewidth=2, color=self.colors['primary'], label='当前能力')
        ax.fill(angles, current_scores, alpha=0.25, color=self.colors['primary'])
        
        ax.set_xticks(angles[:-1])
        ax.set_xticklabels(categories)
        ax.set_ylim(0, 100)
        ax.legend(loc='upper right', bbox_to_anchor=(1.3, 1.1))
        ax.set_title('能力评估对比', y=1.08)
    
    def _calculate_coordination_score(self, data):
        """计算协调性评分"""
        double_support = data.get('gait_phases', {}).get('double_support', 20)
        if 18 <= double_support <= 22:
            return 100
        elif 15 <= double_support <= 25:
            return 80
        else:
            return 60
    
    def _calculate_endurance_score(self, data):
        """计算耐力评分"""
        cadence = data.get('cadence', 0)
        if 100 <= cadence <= 115:
            return 100
        elif 90 <= cadence <= 120:
            return 80
        else:
            return 60
    
    def _create_rehabilitation_advice(self, ax, current_data):
        """创建康复建议"""
        ax.axis('off')
        
        # 分析当前状态并给出建议
        advice = []
        priority = []
        
        # 步速建议
        velocity = current_data.get('average_velocity', 0)
        if velocity < 0.8:
            priority.append('提升步行速度')
            advice.append('• 逐步增加步行距离')
            advice.append('• 进行快走训练')
        
        # 平衡建议
        stability = current_data.get('balance_analysis', {}).get('stabilityIndex', 70)
        if stability < 70:
            priority.append('改善平衡能力')
            advice.append('• 单脚站立训练')
            advice.append('• 太极拳或瑜伽')
        
        # 对称性建议
        if not self._check_symmetry(current_data):
            priority.append('纠正步态不对称')
            advice.append('• 镜像步态训练')
            advice.append('• 双侧协调练习')
        
        # 显示优先级
        ax.text(0.5, 0.95, '康复重点', ha='center', fontsize=12, fontweight='bold')
        
        if priority:
            priority_text = ' > '.join(priority[:3])
            ax.text(0.5, 0.85, priority_text, ha='center', fontsize=10,
                   bbox=dict(boxstyle='round', facecolor='lightcoral', alpha=0.3))
        
        # 显示具体建议
        ax.text(0.5, 0.7, '训练建议', ha='center', fontsize=11, fontweight='bold')
        
        if advice:
            advice_text = '\n'.join(advice[:5])
        else:
            advice_text = '保持当前训练计划'
        
        ax.text(0.5, 0.5, advice_text, ha='center', va='top', fontsize=10,
               bbox=dict(boxstyle='round', facecolor='lightgreen', alpha=0.3))
        
        # 添加注意事项
        ax.text(0.5, 0.2, '注意：请在专业指导下进行训练', 
               ha='center', fontsize=9, style='italic', color='gray')
        
        ax.set_xlim(0, 1)
        ax.set_ylim(0, 1)
        ax.set_title('个性化康复方案', fontsize=12)