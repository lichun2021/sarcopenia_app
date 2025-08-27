#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
改进版报告生成器 - 实现8.24修正建议
包含：红绿箭头标注、左右对比、足底形状、力线图、统一样式、综合对比表
"""

import os
import pandas as pd
import numpy as np
from datetime import datetime
from scipy import stats
from scipy.signal import find_peaks
from scipy.ndimage import label, binary_erosion, binary_dilation
from typing import Dict, List, Tuple, Optional, Any
import matplotlib.pyplot as plt
import matplotlib.patches as patches
from matplotlib.patches import FancyArrowPatch
import base64
from io import BytesIO

class ImprovedReportFormatter:
    """改进的报告格式化工具"""
    
    @staticmethod
    def format_value_with_arrow(value: float, lower: Optional[float] = None, upper: Optional[float] = None, 
                                 decimal: int = 2, unit: str = '') -> str:
        """
        格式化数值并添加红绿箭头标注
        value: 实际值
        lower: 下限
        upper: 上限
        """
        formatted = f"{value:.{decimal}f}{unit}"
        
        if upper is not None and value > upper:
            return f'<span style="color: red; font-weight: bold">{formatted} ↑</span>'
        elif lower is not None and value < lower:
            return f'<span style="color: green; font-weight: bold">{formatted} ↓</span>'
        else:
            return formatted
    
    @staticmethod
    def format_comparison_with_arrow(left_value: float, right_value: float, 
                                    decimal: int = 2, unit: str = '') -> Dict[str, str]:
        """
        格式化左右对比值，大的一侧加红箭头
        """
        left_formatted = f"{left_value:.{decimal}f}{unit}"
        right_formatted = f"{right_value:.{decimal}f}{unit}"
        
        if left_value > right_value * 1.1:  # 左侧明显更大（>10%差异）
            return {
                'left': f'<span style="color: red; font-weight: bold">{left_formatted} ↑</span>',
                'right': right_formatted
            }
        elif right_value > left_value * 1.1:  # 右侧明显更大
            return {
                'left': left_formatted,
                'right': f'<span style="color: red; font-weight: bold">{right_formatted} ↑</span>'
            }
        else:
            return {
                'left': left_formatted,
                'right': right_formatted
            }

class FootprintAnalyzer:
    """足底形状和力线分析器"""
    
    @staticmethod
    def extract_footprint_shape(pressure_data: np.ndarray, threshold_percentile: int = 10) -> np.ndarray:
        """
        提取足底形状轮廓
        """
        # 使用阈值分割
        threshold = np.percentile(pressure_data[pressure_data > 0], threshold_percentile)
        binary_footprint = pressure_data > threshold
        
        # 形态学处理：去噪和平滑
        binary_footprint = binary_erosion(binary_footprint, iterations=1)
        binary_footprint = binary_dilation(binary_footprint, iterations=2)
        binary_footprint = binary_erosion(binary_footprint, iterations=1)
        
        return binary_footprint
    
    @staticmethod
    def find_force_lines(pressure_data: np.ndarray, footprint_mask: np.ndarray) -> Dict:
        """
        计算力线（从后跟到前脚掌的主要承重线）
        """
        # 计算压力中心（COP）
        y_coords, x_coords = np.mgrid[0:pressure_data.shape[0], 0:pressure_data.shape[1]]
        masked_pressure = pressure_data * footprint_mask
        total_pressure = masked_pressure.sum()
        
        if total_pressure > 0:
            cop_x = (masked_pressure * x_coords).sum() / total_pressure
            cop_y = (masked_pressure * y_coords).sum() / total_pressure
        else:
            cop_x, cop_y = pressure_data.shape[1] // 2, pressure_data.shape[0] // 2
        
        # 找前脚掌和后跟区域
        # 后跟：下部1/3
        heel_region = masked_pressure[int(pressure_data.shape[0]*2/3):, :]
        if heel_region.sum() > 0:
            heel_y = int(pressure_data.shape[0]*2/3) + (heel_region * np.arange(heel_region.shape[0])[:, None]).sum() / heel_region.sum()
            heel_x = (heel_region * np.arange(heel_region.shape[1])[None, :]).sum() / heel_region.sum()
        else:
            heel_x, heel_y = cop_x, pressure_data.shape[0] * 0.8
        
        # 前脚掌：上部1/3
        forefoot_region = masked_pressure[:int(pressure_data.shape[0]/3), :]
        if forefoot_region.sum() > 0:
            forefoot_y = (forefoot_region * np.arange(forefoot_region.shape[0])[:, None]).sum() / forefoot_region.sum()
            forefoot_x = (forefoot_region * np.arange(forefoot_region.shape[1])[None, :]).sum() / forefoot_region.sum()
        else:
            forefoot_x, forefoot_y = cop_x, pressure_data.shape[0] * 0.2
        
        return {
            'cop': (cop_x, cop_y),
            'heel': (heel_x, heel_y),
            'forefoot': (forefoot_x, forefoot_y)
        }
    
    @staticmethod
    def generate_footprint_svg(pressure_data: np.ndarray, title: str = "Footprint Analysis") -> str:
        """
        生成包含足底形状和力线的SVG图像
        """
        fig, ax = plt.subplots(1, 1, figsize=(8, 10))
        
        # 提取足底形状
        footprint_mask = FootprintAnalyzer.extract_footprint_shape(pressure_data)
        
        # 显示压力热力图
        im = ax.imshow(pressure_data, cmap='inferno', aspect='equal', interpolation='nearest')
        
        # 叠加足底轮廓
        contours = plt.contour(footprint_mask, levels=[0.5], colors='white', linewidths=2)
        
        # 计算并绘制力线
        force_lines = FootprintAnalyzer.find_force_lines(pressure_data, footprint_mask)
        
        # 绘制COP（压力中心）
        ax.plot(force_lines['cop'][0], force_lines['cop'][1], 'wo', markersize=12, markeredgecolor='black', markeredgewidth=2)
        ax.text(force_lines['cop'][0], force_lines['cop'][1] - 2, 'COP', color='white', fontsize=10, ha='center', fontweight='bold')
        
        # 绘制力线：后跟到COP
        arrow1 = FancyArrowPatch(force_lines['heel'], force_lines['cop'],
                                 connectionstyle="arc3,rad=0.1", 
                                 arrowstyle='->', linewidth=2,
                                 color='yellow', alpha=0.8)
        ax.add_patch(arrow1)
        
        # 绘制力线：COP到前脚掌
        arrow2 = FancyArrowPatch(force_lines['cop'], force_lines['forefoot'],
                                 connectionstyle="arc3,rad=-0.1",
                                 arrowstyle='->', linewidth=2,
                                 color='yellow', alpha=0.8)
        ax.add_patch(arrow2)
        
        # 标记前脚掌和后跟
        ax.plot(force_lines['heel'][0], force_lines['heel'][1], 'go', markersize=10, label='Heel')
        ax.plot(force_lines['forefoot'][0], force_lines['forefoot'][1], 'ro', markersize=10, label='Forefoot')
        
        # 添加标题和颜色条
        ax.set_title(title, fontsize=16, fontweight='bold', pad=20)
        ax.set_xlabel('Width (sensors)', fontsize=12)
        ax.set_ylabel('Length (sensors)', fontsize=12)
        ax.legend(loc='upper right', fontsize=10)
        
        # 添加颜色条
        cbar = plt.colorbar(im, ax=ax, orientation='vertical', pad=0.1)
        cbar.set_label('Pressure (kPa)', fontsize=12)
        
        # 添加网格
        ax.grid(True, alpha=0.3, linestyle='--')
        
        # 转换为SVG
        buffer = BytesIO()
        plt.savefig(buffer, format='svg', dpi=150, bbox_inches='tight', facecolor='white')
        plt.close()
        
        buffer.seek(0)
        svg_data = buffer.read().decode('utf-8')
        
        # 提取SVG内容（去除XML声明）
        start_idx = svg_data.find('<svg')
        if start_idx != -1:
            return svg_data[start_idx:]
        return svg_data

class ComprehensiveAssessmentTable:
    """综合评估对比表生成器"""
    
    @staticmethod
    def generate_comparison_table(all_results: Dict) -> str:
        """
        生成综合对比表HTML
        """
        formatter = ImprovedReportFormatter()
        html = '''
        <div class="comprehensive-table" style="margin: 20px 0;">
            <h3 style="font-size: 18px; color: #2c3e50; margin-bottom: 15px;">综合评估对比表</h3>
            <table style="width: 100%; border-collapse: collapse; font-size: 14px;">
                <thead>
                    <tr style="background-color: #3498db; color: white;">
                        <th style="padding: 10px; border: 1px solid #ddd; text-align: left;">测试项目</th>
                        <th style="padding: 10px; border: 1px solid #ddd; text-align: center;">左侧</th>
                        <th style="padding: 10px; border: 1px solid #ddd; text-align: center;">右侧</th>
                        <th style="padding: 10px; border: 1px solid #ddd; text-align: center;">对称性</th>
                        <th style="padding: 10px; border: 1px solid #ddd; text-align: center;">评价</th>
                    </tr>
                </thead>
                <tbody>
        '''
        
        # 静态坐姿压力
        if 'sitting' in all_results:
            sitting = all_results['sitting']
            formatter = ImprovedReportFormatter()
            left_right = formatter.format_comparison_with_arrow(
                sitting.get('left_pressure', 0),
                sitting.get('right_pressure', 0),
                decimal=1,
                unit=' N'
            )
            symmetry = abs(sitting.get('left_pressure', 0) - sitting.get('right_pressure', 0)) / max(sitting.get('left_pressure', 1), sitting.get('right_pressure', 1)) * 100
            evaluation = "正常" if symmetry < 10 else "轻度偏移" if symmetry < 20 else "明显偏移"
            
            html += f'''
                <tr>
                    <td style="padding: 8px; border: 1px solid #ddd;">静态坐姿臀部压力</td>
                    <td style="padding: 8px; border: 1px solid #ddd; text-align: center;">{left_right['left']}</td>
                    <td style="padding: 8px; border: 1px solid #ddd; text-align: center;">{left_right['right']}</td>
                    <td style="padding: 8px; border: 1px solid #ddd; text-align: center;">{symmetry:.1f}%</td>
                    <td style="padding: 8px; border: 1px solid #ddd; text-align: center;">{evaluation}</td>
                </tr>
            '''
        
        # 起坐测试压力
        if 'situp' in all_results:
            situp = all_results['situp']
            if 'hip_pressure' in situp:
                left_right = formatter.format_comparison_with_arrow(
                    situp['hip_pressure'].get('left', 0),
                    situp['hip_pressure'].get('right', 0),
                    decimal=1,
                    unit=' N'
                )
                html += f'''
                    <tr>
                        <td style="padding: 8px; border: 1px solid #ddd;">起坐臀部压力</td>
                        <td style="padding: 8px; border: 1px solid #ddd; text-align: center;">{left_right['left']}</td>
                        <td style="padding: 8px; border: 1px solid #ddd; text-align: center;">{left_right['right']}</td>
                        <td style="padding: 8px; border: 1px solid #ddd; text-align: center;">-</td>
                        <td style="padding: 8px; border: 1px solid #ddd; text-align: center;">-</td>
                    </tr>
                '''
            
            if 'foot_pressure' in situp:
                left_right = formatter.format_comparison_with_arrow(
                    situp['foot_pressure'].get('left', 0),
                    situp['foot_pressure'].get('right', 0),
                    decimal=1,
                    unit=' N'
                )
                html += f'''
                    <tr>
                        <td style="padding: 8px; border: 1px solid #ddd;">起坐脚部压力</td>
                        <td style="padding: 8px; border: 1px solid #ddd; text-align: center;">{left_right['left']}</td>
                        <td style="padding: 8px; border: 1px solid #ddd; text-align: center;">{left_right['right']}</td>
                        <td style="padding: 8px; border: 1px solid #ddd; text-align: center;">-</td>
                        <td style="padding: 8px; border: 1px solid #ddd; text-align: center;">-</td>
                    </tr>
                '''
        
        # 静态站立
        if 'standing' in all_results:
            standing = all_results['standing']
            left_right = formatter.format_comparison_with_arrow(
                standing.get('left_pressure', 0),
                standing.get('right_pressure', 0),
                decimal=1,
                unit=' N'
            )
            symmetry = abs(standing.get('left_pressure', 0) - standing.get('right_pressure', 0)) / max(standing.get('left_pressure', 1), standing.get('right_pressure', 1)) * 100
            evaluation = "平衡良好" if symmetry < 15 else "轻度失衡" if symmetry < 25 else "明显失衡"
            
            html += f'''
                <tr>
                    <td style="padding: 8px; border: 1px solid #ddd;">静态站立压力</td>
                    <td style="padding: 8px; border: 1px solid #ddd; text-align: center;">{left_right['left']}</td>
                    <td style="padding: 8px; border: 1px solid #ddd; text-align: center;">{left_right['right']}</td>
                    <td style="padding: 8px; border: 1px solid #ddd; text-align: center;">{symmetry:.1f}%</td>
                    <td style="padding: 8px; border: 1px solid #ddd; text-align: center;">{evaluation}</td>
                </tr>
            '''
        
        # 步态分析
        if 'gait' in all_results:
            gait = all_results['gait']
            # 步长对称性
            if 'left_step_length' in gait and 'right_step_length' in gait:
                left_right = formatter.format_comparison_with_arrow(
                    gait['left_step_length'],
                    gait['right_step_length'],
                    decimal=2,
                    unit=' m'
                )
                symmetry = abs(gait['left_step_length'] - gait['right_step_length']) / max(gait['left_step_length'], gait['right_step_length']) * 100
                evaluation = "对称" if symmetry < 10 else "轻度不对称" if symmetry < 20 else "明显不对称"
                
                html += f'''
                    <tr>
                        <td style="padding: 8px; border: 1px solid #ddd;">行走步长</td>
                        <td style="padding: 8px; border: 1px solid #ddd; text-align: center;">{left_right['left']}</td>
                        <td style="padding: 8px; border: 1px solid #ddd; text-align: center;">{left_right['right']}</td>
                        <td style="padding: 8px; border: 1px solid #ddd; text-align: center;">{symmetry:.1f}%</td>
                        <td style="padding: 8px; border: 1px solid #ddd; text-align: center;">{evaluation}</td>
                    </tr>
                '''
        
        html += '''
                </tbody>
            </table>
            <div style="margin-top: 15px; padding: 10px; background-color: #f0f8ff; border-left: 4px solid #3498db;">
                <h4 style="margin: 0 0 10px 0; color: #2c3e50;">综合分析结论：</h4>
                <p style="margin: 5px 0; font-size: 14px;">
        '''
        
        # 添加综合分析结论
        conclusions = []
        
        if 'sitting' in all_results:
            sitting = all_results['sitting']
            if abs(sitting.get('left_pressure', 0) - sitting.get('right_pressure', 0)) > 50:
                side = "左侧" if sitting.get('left_pressure', 0) > sitting.get('right_pressure', 0) else "右侧"
                conclusions.append(f"坐姿压力偏向{side}")
        
        if 'standing' in all_results:
            standing = all_results['standing']
            if abs(standing.get('left_pressure', 0) - standing.get('right_pressure', 0)) > 50:
                side = "左侧" if standing.get('left_pressure', 0) > standing.get('right_pressure', 0) else "右侧"
                conclusions.append(f"站立平衡偏向{side}")
        
        if 'gait' in all_results:
            gait = all_results['gait']
            if 'left_step_length' in gait and 'right_step_length' in gait:
                if abs(gait['left_step_length'] - gait['right_step_length']) > 0.05:
                    side = "左侧" if gait['left_step_length'] < gait['right_step_length'] else "右侧"
                    conclusions.append(f"{side}步长较短")
        
        if conclusions:
            html += " • ".join(conclusions)
            html += "，建议进行针对性康复训练。"
        else:
            html += "各项指标基本正常，身体平衡性良好。"
        
        html += '''
                </p>
            </div>
        </div>
        '''
        
        return html

class UnifiedReportStyle:
    """统一的报告样式"""
    
    @staticmethod
    def get_unified_css() -> str:
        """
        返回统一的CSS样式
        """
        return '''
        <style>
            * {
                margin: 0;
                padding: 0;
                box-sizing: border-box;
            }
            
            body {
                font-family: 'Microsoft YaHei', 'Arial', sans-serif;
                font-size: 14px;
                line-height: 1.6;
                color: #333;
                background: white;
                padding: 20px;
            }
            
            h1 {
                font-size: 24px;
                font-weight: bold;
                color: #2c3e50;
                margin-bottom: 20px;
                text-align: center;
                border-bottom: 3px solid #3498db;
                padding-bottom: 10px;
            }
            
            h2 {
                font-size: 18px;
                font-weight: bold;
                color: #34495e;
                margin: 20px 0 15px 0;
                padding-left: 10px;
                border-left: 4px solid #3498db;
            }
            
            h3 {
                font-size: 16px;
                font-weight: bold;
                color: #555;
                margin: 15px 0 10px 0;
            }
            
            .info-header {
                display: flex;
                justify-content: space-between;
                align-items: center;
                margin-bottom: 20px;
                padding: 15px;
                background: linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%);
                border-radius: 8px;
                box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            }
            
            .info-item {
                display: flex;
                align-items: center;
                font-size: 14px;
                color: #2c3e50;
            }
            
            .info-item strong {
                margin-right: 5px;
                color: #34495e;
            }
            
            table {
                width: 100%;
                border-collapse: collapse;
                margin: 15px 0;
                font-size: 14px;
                box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            }
            
            th {
                background-color: #3498db;
                color: white;
                padding: 10px;
                text-align: left;
                font-size: 14px;
                font-weight: bold;
            }
            
            td {
                padding: 8px 10px;
                border: 1px solid #ddd;
                font-size: 14px;
            }
            
            tr:nth-child(even) {
                background-color: #f8f9fa;
            }
            
            tr:hover {
                background-color: #e8f4ff;
            }
            
            .warning-section {
                display: none;  /* 隐藏黄色警告区块 */
            }
            
            .pressure-chart {
                margin: 20px 0;
                text-align: center;
                padding: 15px;
                background: #f8f9fa;
                border-radius: 8px;
            }
            
            .pressure-chart img, .pressure-chart svg {
                max-width: 100%;
                height: auto;
                border: 2px solid #ddd;
                border-radius: 4px;
                background: white;
            }
            
            .conclusion {
                margin-top: 30px;
                padding: 20px;
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                color: white;
                border-radius: 8px;
                box-shadow: 0 4px 6px rgba(0,0,0,0.1);
            }
            
            .conclusion h2 {
                color: white;
                border-left-color: white;
            }
            
            .conclusion p {
                font-size: 14px;
                line-height: 1.8;
            }
            
            @media print {
                body {
                    padding: 0;
                }
                
                .page-break {
                    page-break-after: always;
                }
            }
        </style>
        '''

# 示例：如何整合到现有的报告生成器
def enhance_existing_report(original_html: str, test_results: Dict) -> str:
    """
    增强现有的报告HTML
    """
    # 1. 添加统一样式
    style = UnifiedReportStyle.get_unified_css()
    
    # 2. 生成综合对比表
    comparison_table = ComprehensiveAssessmentTable.generate_comparison_table(test_results)
    
    # 3. 插入样式和对比表到HTML
    # 在</head>前插入样式
    if '</head>' in original_html:
        original_html = original_html.replace('</head>', style + '</head>')
    else:
        original_html = style + original_html
    
    # 在综合评估部分后插入对比表
    if '综合评估与建议' in original_html:
        insert_pos = original_html.find('综合评估与建议')
        insert_pos = original_html.find('</div>', insert_pos) + 6
        original_html = original_html[:insert_pos] + comparison_table + original_html[insert_pos:]
    
    return original_html

if __name__ == "__main__":
    # 测试代码
    print("改进版报告生成器已加载")
    
    # 测试格式化工具
    formatter = ImprovedReportFormatter()
    
    # 测试数值箭头标注
    print("\n测试数值箭头标注：")
    print(f"步速 0.6m/s (标准≥0.8): {formatter.format_value_with_arrow(0.6, lower=0.8, decimal=1, unit='m/s')}")
    print(f"步速 1.2m/s (标准≥0.8): {formatter.format_value_with_arrow(1.2, lower=0.8, decimal=1, unit='m/s')}")
    
    # 测试左右对比
    print("\n测试左右对比：")
    comparison = formatter.format_comparison_with_arrow(450.5, 380.2, decimal=1, unit='N')
    print(f"左脚: {comparison['left']}, 右脚: {comparison['right']}")
    
    # 测试足底形状分析
    print("\n生成测试用足底形状...")
    test_pressure = np.random.rand(64, 32) * 100
    test_pressure[20:40, 10:20] = np.random.rand(20, 10) * 500  # 模拟脚印
    
    footprint_svg = FootprintAnalyzer.generate_footprint_svg(test_pressure, "Test Footprint")
    print("足底形状SVG已生成")
    
    # 测试综合对比表
    print("\n生成综合对比表...")
    test_results = {
        'sitting': {'left_pressure': 450, 'right_pressure': 380},
        'standing': {'left_pressure': 320, 'right_pressure': 340},
        'gait': {'left_step_length': 0.65, 'right_step_length': 0.72}
    }
    
    comparison_html = ComprehensiveAssessmentTable.generate_comparison_table(test_results)
    print("综合对比表HTML已生成")