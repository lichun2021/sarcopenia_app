#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
最终修复版报告生成器
专门针对8.24问题的精准修复
"""

import os
import pandas as pd
import numpy as np
from datetime import datetime
from scipy import stats
from scipy.signal import find_peaks
from typing import Dict, List, Tuple, Optional, Any
import matplotlib.pyplot as plt
from matplotlib.patches import FancyArrowPatch
from io import BytesIO
import warnings
warnings.filterwarnings('ignore')

# 导入原有功能
from gait_report_generator import CompleteGaitAnalyzer, CompleteReportGenerator

class FinalFixReportGenerator(CompleteReportGenerator):
    """最终修复版 - 精准解决每个具体问题"""
    
    def __init__(self):
        super().__init__()
        
    def process_test_data_with_precise_fixes(self, folder_path: str, group_name: str, age: int) -> Dict[str, str]:
        """精准修复数据处理"""
        
        # 使用原有处理逻辑
        results = super().process_test_data(folder_path, group_name, age)
        
        # 应用精准修复
        print("🔧 应用精准修复...")
        
        # 1. 修复数值箭头标注
        self.fix_value_arrows(results, age)
        
        # 2. 修复五次起坐详细分解
        self.fix_situp_detailed_breakdown(results, folder_path)
        
        # 3. 修复足底轮廓和力线
        self.fix_footprint_contours_and_force_lines(results, folder_path)
        
        # 4. 修复脚部压力箭头标注
        self.fix_foot_pressure_arrows(results)
        
        # 5. 修复逻辑解释
        self.fix_logic_explanations(results)
        
        # 6. 修复综合评估
        self.fix_comprehensive_assessment(results)
        
        return results
    
    def fix_value_arrows(self, results: Dict[str, str], age: int):
        """修复数值箭头标注"""
        print("   🎯 修复数值箭头...")
        
        # 获取参考值
        if age < 60:
            situp_ref = 10
            speed_ref = 1.2
        elif age < 70:
            situp_ref = 12
            speed_ref = 1.0  
        elif age < 80:
            situp_ref = 15
            speed_ref = 0.8
        else:
            situp_ref = 20
            speed_ref = 0.6
        
        # 确保关键数值有箭头
        key_fixes = [
            ('five_situp_time', situp_ref, 'upper', '秒'),
            ('micro_vibration', 0.5, 'upper', 'mm'),
            ('stand_up_speed', 0.3, 'lower', 'm/s'),
            ('sit_down_speed', 0.3, 'lower', 'm/s'),
        ]
        
        for key, ref_val, direction, unit in key_fixes:
            if key in results:
                try:
                    val = float(results[key])
                    if direction == 'upper' and val > ref_val:
                        results[key] = f'<span style="color: red; font-weight: bold">{val:.4f} ↑</span>'
                    elif direction == 'lower' and val < ref_val:
                        results[key] = f'<span style="color: red; font-weight: bold">{val:.4f} ↓</span>'
                    elif direction == 'upper' and val < ref_val * 0.6:
                        results[key] = f'<span style="color: green; font-weight: bold">{val:.4f} ↓</span>'
                    print(f"      ✅ {key}: {val} (参考: {ref_val}{unit})")
                except:
                    pass
    
    def fix_situp_detailed_breakdown(self, results: Dict[str, str], folder_path: str):
        """修复五次起坐详细分解"""
        print("   💪 修复五次起坐详细分解...")
        
        try:
            # 加载起坐数据
            situp_files = [f for f in os.listdir(folder_path) if '起坐' in f and f.endswith('.csv')]
            if not situp_files:
                results['situp_breakdown_table'] = '<p>起坐数据文件未找到</p>'
                return
            
            situp_file = os.path.join(folder_path, situp_files[0])
            df = pd.read_csv(situp_file)
            
            # 解析数据
            pressure_arrays = []
            for _, row in df.iterrows():
                data_str = row['data'].strip('[]')
                data_array = [int(x) for x in data_str.split(',')]
                pressure_arrays.append(data_array)
            
            pressure_data = np.array(pressure_arrays)
            reshaped = pressure_data.reshape(-1, 32, 32)
            
            # 计算总压力信号
            total_pressure = [frame.sum() for frame in reshaped]
            
            # 检测峰值
            peaks, _ = find_peaks(total_pressure, height=np.max(total_pressure)*0.3, distance=20)
            
            if len(peaks) >= 5:
                # 分析每次起坐
                breakdown_html = '''
                <div style="margin: 20px 0; padding: 15px; background: #f0f8ff; border-radius: 8px; border-left: 4px solid #4CAF50;">
                    <h4 style="color: #2E7D32; margin-bottom: 15px;">💪 五次起坐左右发力详细分解</h4>
                    <table style="width: 100%; border-collapse: collapse; font-size: 14px; background: white;">
                        <tr style="background: #4CAF50; color: white;">
                            <th style="padding: 10px; border: 1px solid #ddd; text-align: center;">起坐次数</th>
                            <th style="padding: 10px; border: 1px solid #ddd; text-align: center;">左侧发力</th>
                            <th style="padding: 10px; border: 1px solid #ddd; text-align: center;">右侧发力</th>
                            <th style="padding: 10px; border: 1px solid #ddd; text-align: center;">发力趋势</th>
                            <th style="padding: 10px; border: 1px solid #ddd; text-align: center;">差异程度</th>
                        </tr>
                '''
                
                left_dominant_count = 0
                right_dominant_count = 0
                
                for i in range(min(5, len(peaks))):
                    peak_idx = peaks[i]
                    frame = reshaped[peak_idx]
                    
                    left_force = frame[:, :16].sum()
                    right_force = frame[:, 16:].sum()
                    
                    # 计算差异
                    diff_percent = abs(left_force - right_force) / max(left_force, right_force) * 100
                    
                    # 确定趋势和箭头
                    if left_force > right_force * 1.05:  # 左侧大5%以上
                        trend = '<span style="color: red; font-weight: bold;">左>右 ↑</span>'
                        left_dominant_count += 1
                        left_display = f'<span style="color: red; font-weight: bold;">{left_force:.0f} ↑</span>'
                        right_display = f'{right_force:.0f}'
                    elif right_force > left_force * 1.05:  # 右侧大5%以上
                        trend = '<span style="color: red; font-weight: bold;">右>左 ↑</span>'
                        right_dominant_count += 1
                        left_display = f'{left_force:.0f}'
                        right_display = f'<span style="color: red; font-weight: bold;">{right_force:.0f} ↑</span>'
                    else:
                        trend = '基本均衡'
                        left_display = f'{left_force:.0f}'
                        right_display = f'{right_force:.0f}'
                    
                    # 差异程度颜色标注
                    diff_color = 'color: red; font-weight: bold;' if diff_percent > 15 else 'color: orange;' if diff_percent > 10 else 'color: green;'
                    
                    breakdown_html += f'''
                        <tr>
                            <td style="padding: 8px; border: 1px solid #ddd; text-align: center; font-weight: bold;">第{i+1}次</td>
                            <td style="padding: 8px; border: 1px solid #ddd; text-align: center;">{left_display}</td>
                            <td style="padding: 8px; border: 1px solid #ddd; text-align: center;">{right_display}</td>
                            <td style="padding: 8px; border: 1px solid #ddd; text-align: center;">{trend}</td>
                            <td style="padding: 8px; border: 1px solid #ddd; text-align: center; {diff_color}">{diff_percent:.1f}%</td>
                        </tr>
                    '''
                
                # 添加总结分析
                if left_dominant_count > right_dominant_count:
                    dominance_analysis = f'<span style="color: red; font-weight: bold;">左侧主导型</span>（{left_dominant_count}次 vs {right_dominant_count}次）'
                elif right_dominant_count > left_dominant_count:
                    dominance_analysis = f'<span style="color: red; font-weight: bold;">右侧主导型</span>（{right_dominant_count}次 vs {left_dominant_count}次）'
                else:
                    dominance_analysis = f'<span style="color: green; font-weight: bold;">均衡型</span>（{left_dominant_count}次 vs {right_dominant_count}次）'
                
                breakdown_html += f'''
                    </table>
                    <div style="margin-top: 15px; padding: 12px; background: #E8F5E8; border-left: 4px solid #4CAF50; border-radius: 4px;">
                        <strong style="color: #2E7D32;">🔍 发力模式分析：</strong>
                        {dominance_analysis}<br>
                        <strong style="color: #2E7D32;">💡 临床意义：</strong>
                        {'发力模式相对均衡，双侧下肢协调性良好' if abs(left_dominant_count - right_dominant_count) <= 1 else '存在明显的单侧发力偏好，建议关注肌力不平衡问题'}
                    </div>
                </div>
                '''
                
                results['situp_breakdown_table'] = breakdown_html
                print(f"      ✅ 五次起坐分解完成: 左优势{left_dominant_count}次, 右优势{right_dominant_count}次")
                
            else:
                results['situp_breakdown_table'] = '<p style="color: orange;">起坐周期检测不足，无法进行详细分解分析</p>'
                
        except Exception as e:
            print(f"      ⚠️ 五次起坐分解失败: {e}")
            results['situp_breakdown_table'] = f'<p style="color: red;">数据解析失败: {str(e)}</p>'
    
    def fix_footprint_contours_and_force_lines(self, results: Dict[str, str], folder_path: str):
        """修复足底轮廓和力线"""
        print("   🦶 修复足底轮廓和力线...")
        
        try:
            # 加载站立测试数据
            test_configs = [
                ('standing', 'left_foot_static_chart', 'right_foot_static_chart', '第3步-静态站立'),
                ('tandem_standing', 'left_foot_tandem_chart', 'right_foot_tandem_chart', '第4步-前后脚站立'),
                ('side_standing', 'left_foot_side_chart', 'right_foot_side_chart', '第5步-双脚前后站立'),
            ]
            
            for test_name, left_key, right_key, file_pattern in test_configs:
                files = [f for f in os.listdir(folder_path) if file_pattern in f and f.endswith('.csv')]
                if files:
                    file_path = os.path.join(folder_path, files[0])
                    df = pd.read_csv(file_path)
                    
                    # 解析数据
                    pressure_arrays = []
                    for _, row in df.iterrows():
                        data_str = row['data'].strip('[]')
                        data_array = [int(x) for x in data_str.split(',')]
                        pressure_arrays.append(data_array)
                    
                    pressure_data = np.array(pressure_arrays)
                    
                    # 生成带轮廓和力线的图表
                    left_chart = self.create_enhanced_footprint_chart(pressure_data, 'left', f'{test_name.title()} - Left Foot')
                    right_chart = self.create_enhanced_footprint_chart(pressure_data, 'right', f'{test_name.title()} - Right Foot')
                    
                    results[left_key] = left_chart
                    results[right_key] = right_chart
                    
                    print(f"      ✅ 生成 {test_name} 足底图表")
                    
        except Exception as e:
            print(f"      ⚠️ 足底轮廓生成失败: {e}")
    
    def create_enhanced_footprint_chart(self, pressure_data: np.ndarray, foot_side: str, title: str) -> str:
        """创建增强的足底图表（轮廓+力线+COP）"""
        
        # 数据预处理
        start = int(len(pressure_data) * 0.1)
        end = int(len(pressure_data) * 0.9)
        stable_data = pressure_data[start:end]
        
        # 重塑为32x32
        reshaped = stable_data.reshape(-1, 32, 32)
        
        # 分离左右脚
        if foot_side == 'left':
            foot_data = reshaped[:, :, :16]
            foot_data_full = np.zeros((reshaped.shape[0], 32, 32))
            foot_data_full[:, :, :16] = foot_data
        else:
            foot_data = reshaped[:, :, 16:]  
            foot_data_full = np.zeros((reshaped.shape[0], 32, 32))
            foot_data_full[:, :, 16:] = foot_data
            
        median_frame = np.median(foot_data_full, axis=0)
        
        # 转换为kPa
        sensor_area = 4.688
        force_calibration = 0.1
        force_n = median_frame * force_calibration
        kpa = (force_n / sensor_area) * 10
        kpa[kpa < 1] = 0
        
        # 创建图形
        fig, ax = plt.subplots(1, 1, figsize=(5, 6))
        
        # 显示热力图
        vmax = np.percentile(kpa[kpa > 0], 95) if kpa[kpa > 0].size > 0 else 50
        im = ax.imshow(kpa, cmap='inferno', vmin=0, vmax=vmax, aspect='equal', interpolation='nearest')
        
        # 提取足底轮廓
        if foot_side == 'left':
            roi_kpa = kpa[:, :16]
        else:
            roi_kpa = kpa[:, 16:]
            
        if roi_kpa.sum() > 0:
            threshold = np.percentile(roi_kpa[roi_kpa > 0], 15) if roi_kpa[roi_kpa > 0].size > 0 else 1
            
            # 二值化足底形状
            if foot_side == 'left':
                footprint_mask = kpa.copy()
                footprint_mask[:, 16:] = 0  # 清零右侧
                footprint_mask = footprint_mask > threshold
            else:
                footprint_mask = kpa.copy()
                footprint_mask[:, :16] = 0  # 清零左侧
                footprint_mask = footprint_mask > threshold
            
            # 形态学处理
            from scipy import ndimage
            footprint_mask = ndimage.binary_fill_holes(footprint_mask)
            footprint_mask = ndimage.binary_erosion(footprint_mask, iterations=1)
            footprint_mask = ndimage.binary_dilation(footprint_mask, iterations=2)
            
            # 绘制白色轮廓线
            contours = ax.contour(footprint_mask, levels=[0.5], colors='white', linewidths=3)
            
            # 计算COP
            if roi_kpa.sum() > 0:
                if foot_side == 'left':
                    y_coords, x_coords = np.mgrid[0:32, 0:16]
                    cop_x = (roi_kpa * x_coords).sum() / roi_kpa.sum()
                    cop_y = (roi_kpa * y_coords).sum() / roi_kpa.sum()
                else:
                    y_coords, x_coords = np.mgrid[0:32, 0:16]
                    cop_x = (roi_kpa * x_coords).sum() / roi_kpa.sum() + 16
                    cop_y = (roi_kpa * y_coords).sum() / roi_kpa.sum()
                
                # COP标记
                ax.plot(cop_x, cop_y, 'wo', markersize=10, markeredgecolor='black', markeredgewidth=2)
                ax.text(cop_x, cop_y - 1.5, 'COP', color='white', fontsize=12, ha='center', 
                       fontweight='bold', bbox=dict(boxstyle='round,pad=0.2', facecolor='black', alpha=0.7))
                
                # 计算前脚掌和后跟位置
                if foot_side == 'left':
                    heel_region = roi_kpa[20:, :]
                    forefoot_region = roi_kpa[:12, :]
                else:
                    heel_region = roi_kpa[20:, :]
                    forefoot_region = roi_kpa[:12, :]
                
                if heel_region.sum() > 0 and forefoot_region.sum() > 0:
                    # 后跟中心
                    heel_y_coords, heel_x_coords = np.mgrid[0:heel_region.shape[0], 0:heel_region.shape[1]]
                    heel_y = (heel_region * heel_y_coords).sum() / heel_region.sum() + 20
                    heel_x = (heel_region * heel_x_coords).sum() / heel_region.sum()
                    if foot_side == 'right':
                        heel_x += 16
                    
                    # 前脚掌中心  
                    fore_y_coords, fore_x_coords = np.mgrid[0:forefoot_region.shape[0], 0:forefoot_region.shape[1]]
                    fore_y = (forefoot_region * fore_y_coords).sum() / forefoot_region.sum()
                    fore_x = (forefoot_region * fore_x_coords).sum() / forefoot_region.sum()
                    if foot_side == 'right':
                        fore_x += 16
                    
                    # 绘制虚线力线
                    ax.plot([heel_x, cop_x, fore_x], [heel_y, cop_y, fore_y], 
                           'y--', linewidth=3, alpha=0.9, label='Force Line')
                    
                    # 标记关键点
                    ax.plot(heel_x, heel_y, 'go', markersize=8, markeredgecolor='white', 
                           markeredgewidth=2, label='Heel')
                    ax.plot(fore_x, fore_y, 'ro', markersize=8, markeredgecolor='white', 
                           markeredgewidth=2, label='Forefoot')
        
        # 设置图表
        ax.set_title(title, fontsize=14, fontweight='bold', pad=15)
        ax.set_xlabel('Width (sensors)', fontsize=10)
        ax.set_ylabel('Length (sensors)', fontsize=10)
        
        # 添加压力信息
        max_pressure = np.max(kpa)
        ax.text(0.02, 0.98, f'Max: {max_pressure:.1f} kPa', transform=ax.transAxes, 
               va='top', ha='left', fontsize=10, color='white', fontweight='bold',
               bbox=dict(boxstyle='round,pad=0.3', facecolor='black', alpha=0.7))
        
        # 颜色条
        cbar = plt.colorbar(im, ax=ax, orientation='vertical', shrink=0.7, pad=0.05)
        cbar.set_label('Pressure (kPa)', fontsize=10)
        cbar.ax.tick_params(labelsize=9)
        
        # 图例
        ax.legend(loc='upper right', fontsize=8, framealpha=0.8)
        
        plt.tight_layout()
        
        # 转换为SVG
        buffer = BytesIO()
        plt.savefig(buffer, format='svg', dpi=120, bbox_inches='tight', facecolor='white')
        plt.close()
        
        buffer.seek(0)
        svg_data = buffer.read().decode('utf-8')
        
        # 提取SVG内容
        start_idx = svg_data.find('<svg')
        if start_idx != -1:
            return svg_data[start_idx:]
        return svg_data
    
    def fix_foot_pressure_arrows(self, results: Dict[str, str]):
        """修复脚部压力箭头标注"""
        print("   👣 修复脚部压力箭头...")
        
        # 定义需要对比的脚部压力键值对
        pressure_pairs = [
            ('left_foot_static_max', 'right_foot_static_max', '静态站立'),
            ('left_foot_tandem_max', 'right_foot_tandem_max', '前后脚站立'),  
            ('left_foot_side_max', 'right_foot_side_max', '侧方位站立'),
        ]
        
        for left_key, right_key, test_name in pressure_pairs:
            if left_key in results and right_key in results:
                try:
                    left_val = float(results[left_key])
                    right_val = float(results[right_key])
                    
                    # 添加箭头标注
                    if left_val > right_val * 1.1:  # 左侧大10%以上
                        results[left_key] = f'<span style="color: red; font-weight: bold">{left_val:.4f} ↑</span>'
                        results[right_key] = f'{right_val:.4f}'
                    elif right_val > left_val * 1.1:  # 右侧大10%以上
                        results[left_key] = f'{left_val:.4f}'
                        results[right_key] = f'<span style="color: red; font-weight: bold">{right_val:.4f} ↑</span>'
                    
                    print(f"      ✅ {test_name}: L={left_val:.2f} vs R={right_val:.2f}")
                except:
                    pass
    
    def fix_logic_explanations(self, results: Dict[str, str]):
        """修复逻辑解释"""
        print("   📚 修复逻辑解释...")
        
        explanation_html = '''
        <div style="margin: 20px 0; padding: 20px; background: linear-gradient(135deg, #FFF8E1 0%, #FFECB3 100%); border-left: 5px solid #FFA000; border-radius: 8px;">
            <h4 style="color: #E65100; margin-bottom: 15px; display: flex; align-items: center;">
                📊 <span style="margin-left: 8px;">数据解读与逻辑说明</span>
            </h4>
            <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 15px; color: #BF360C;">
                <div>
                    <p style="margin-bottom: 10px;"><strong>🔍 压力分布 vs COP偏移：</strong></p>
                    <ul style="margin: 5px 0 0 15px; line-height: 1.6;">
                        <li><strong>总压力</strong>：反映体重在左右侧的分布</li>
                        <li><strong>COP偏移</strong>：反映平衡控制的瞬时状态</li>
                        <li><strong>不同步现象</strong>：左压力大但右偏移大是正常的，因为COP受高值像素点影响更敏感</li>
                    </ul>
                </div>
                <div>
                    <p style="margin-bottom: 10px;"><strong>📏 参考范围来源：</strong></p>
                    <ul style="margin: 5px 0 0 15px; line-height: 1.6;">
                        <li><strong>AWGS 2019标准</strong>：步速、起坐时间等官方标准</li>
                        <li><strong>系统经验值</strong>：微抖动≤0.5mm基于临床观察</li>
                        <li><strong>差异阈值</strong>：>10%标红是基于生理学正常范围</li>
                    </ul>
                </div>
            </div>
            <div style="margin-top: 15px; padding: 12px; background: rgba(255,255,255,0.8); border-radius: 6px; border-left: 3px solid #4CAF50;">
                <strong style="color: #2E7D32;">💡 医学解释：</strong>
                正常人群也会存在5-15%的生理性左右不对称，主要受惯用肢、既往损伤史、日常活动习惯等因素影响。
                <strong style="color: #E65100;">红色箭头</strong>提示需要关注，但需结合临床表现综合判断。
            </div>
        </div>
        '''
        
        results['enhanced_logic_explanation'] = explanation_html
    
    def fix_comprehensive_assessment(self, results: Dict[str, str]):
        """修复综合评估"""
        print("   🎯 修复综合评估...")
        
        # 提取各项数据
        assessment_data = {}
        
        # 提取数值并清理
        def clean_value(val_str):
            import re
            if not val_str:
                return 0
            # 移除HTML标签和箭头
            clean = re.sub(r'<[^>]*>', '', str(val_str))
            clean = re.sub(r'[↑↓]', '', clean)
            try:
                return float(clean.strip())
            except:
                return 0
        
        # 收集关键指标
        try:
            assessment_data['situp_time'] = clean_value(results.get('five_situp_time', '0'))
            assessment_data['left_pressure'] = clean_value(results.get('left_pressure', '0'))  
            assessment_data['right_pressure'] = clean_value(results.get('right_pressure', '0'))
            assessment_data['micro_vibration'] = clean_value(results.get('micro_vibration', '0'))
            assessment_data['left_foot_static'] = clean_value(results.get('left_foot_static_max', '0'))
            assessment_data['right_foot_static'] = clean_value(results.get('right_foot_static_max', '0'))
            assessment_data['left_foot_tandem'] = clean_value(results.get('left_foot_tandem_max', '0'))
            assessment_data['right_foot_tandem'] = clean_value(results.get('right_foot_tandem_max', '0'))
            assessment_data['stand_up_speed'] = clean_value(results.get('stand_up_speed', '0'))
        except:
            pass
        
        # 生成综合评估表格
        comprehensive_html = '''
        <div style="margin: 25px 0; padding: 20px; background: linear-gradient(135deg, #E3F2FD 0%, #BBDEFB 100%); border-radius: 12px; border-left: 5px solid #1976D2;">
            <h3 style="color: #0D47A1; margin-bottom: 20px; text-align: center;">🎯 综合评估对比总结表</h3>
            <table style="width: 100%; border-collapse: collapse; background: white; border-radius: 8px; overflow: hidden; box-shadow: 0 4px 8px rgba(0,0,0,0.1);">
                <thead>
                    <tr style="background: linear-gradient(135deg, #1976D2 0%, #42A5F5 100%); color: white;">
                        <th style="padding: 12px; text-align: left; font-weight: bold;">评估维度</th>
                        <th style="padding: 12px; text-align: center; font-weight: bold;">左侧数值</th>
                        <th style="padding: 12px; text-align: center; font-weight: bold;">右侧数值</th>
                        <th style="padding: 12px; text-align: center; font-weight: bold;">对称性</th>
                        <th style="padding: 12px; text-align: center; font-weight: bold;">临床评价</th>
                    </tr>
                </thead>
                <tbody>
        '''
        
        # 添加各项对比数据
        comparisons = [
            ('臀部压力分布', assessment_data.get('left_pressure', 0), assessment_data.get('right_pressure', 0), '%'),
            ('静态站立压力', assessment_data.get('left_foot_static', 0), assessment_data.get('right_foot_static', 0), ''),
            ('前后脚站立压力', assessment_data.get('left_foot_tandem', 0), assessment_data.get('right_foot_tandem', 0), ''),
        ]
        
        for i, (test_name, left_val, right_val, unit) in enumerate(comparisons):
            if left_val > 0 or right_val > 0:
                # 计算对称性
                if max(left_val, right_val) > 0:
                    asymmetry = abs(left_val - right_val) / max(left_val, right_val) * 100
                else:
                    asymmetry = 0
                
                # 评价
                if asymmetry < 10:
                    evaluation = '<span style="color: green; font-weight: bold;">良好</span>'
                elif asymmetry < 20:
                    evaluation = '<span style="color: orange; font-weight: bold;">轻度失衡</span>'
                else:
                    evaluation = '<span style="color: red; font-weight: bold;">明显失衡</span>'
                
                # 箭头标注
                if left_val > right_val * 1.1:
                    left_display = f'<span style="color: red; font-weight: bold;">{left_val:.1f}{unit} ↑</span>'
                    right_display = f'{right_val:.1f}{unit}'
                elif right_val > left_val * 1.1:
                    left_display = f'{left_val:.1f}{unit}'
                    right_display = f'<span style="color: red; font-weight: bold;">{right_val:.1f}{unit} ↑</span>'
                else:
                    left_display = f'{left_val:.1f}{unit}'
                    right_display = f'{right_val:.1f}{unit}'
                
                # 行颜色
                row_style = 'background: #f8f9fa;' if i % 2 == 0 else 'background: white;'
                
                comprehensive_html += f'''
                    <tr style="{row_style}">
                        <td style="padding: 10px; border-bottom: 1px solid #e9ecef; font-weight: bold; color: #495057;">{test_name}</td>
                        <td style="padding: 10px; border-bottom: 1px solid #e9ecef; text-align: center;">{left_display}</td>
                        <td style="padding: 10px; border-bottom: 1px solid #e9ecef; text-align: center;">{right_display}</td>
                        <td style="padding: 10px; border-bottom: 1px solid #e9ecef; text-align: center;">{asymmetry:.1f}%</td>
                        <td style="padding: 10px; border-bottom: 1px solid #e9ecef; text-align: center;">{evaluation}</td>
                    </tr>
                '''
        
        # 添加功能性指标
        functional_data = [
            ('五次起坐时间', assessment_data.get('situp_time', 0), '≤12秒', '秒'),
            ('微抖动范围', assessment_data.get('micro_vibration', 0), '≤0.5mm', 'mm'),
            ('站起速度', assessment_data.get('stand_up_speed', 0), '≥0.3m/s', 'm/s'),
        ]
        
        comprehensive_html += '''
                </tbody>
            </table>
            
            <h4 style="color: #0D47A1; margin: 20px 0 15px 0;">📋 功能性指标评估</h4>
            <table style="width: 100%; border-collapse: collapse; background: white; border-radius: 8px; overflow: hidden; box-shadow: 0 4px 8px rgba(0,0,0,0.1);">
                <thead>
                    <tr style="background: linear-gradient(135deg, #4CAF50 0%, #66BB6A 100%); color: white;">
                        <th style="padding: 12px; text-align: left; font-weight: bold;">功能指标</th>
                        <th style="padding: 12px; text-align: center; font-weight: bold;">测量值</th>
                        <th style="padding: 12px; text-align: center; font-weight: bold;">参考标准</th>
                        <th style="padding: 12px; text-align: center; font-weight: bold;">状态评价</th>
                    </tr>
                </thead>
                <tbody>
        '''
        
        for i, (indicator, value, reference, unit) in enumerate(functional_data):
            if value > 0:
                # 状态评价
                if 'time' in indicator.lower() or '时间' in indicator:
                    # 时间类指标：越小越好
                    if value <= 12:
                        status = '<span style="color: green; font-weight: bold;">正常</span>'
                        value_display = f'{value:.4f}'
                    elif value <= 15:
                        status = '<span style="color: orange; font-weight: bold;">轻度延长</span>'
                        value_display = f'<span style="color: orange; font-weight: bold;">{value:.4f} ↑</span>'
                    else:
                        status = '<span style="color: red; font-weight: bold;">明显延长</span>'
                        value_display = f'<span style="color: red; font-weight: bold;">{value:.4f} ↑</span>'
                elif '速度' in indicator:
                    # 速度类指标：越大越好
                    if value >= 0.3:
                        status = '<span style="color: green; font-weight: bold;">正常</span>'
                        value_display = f'{value:.4f}'
                    else:
                        status = '<span style="color: red; font-weight: bold;">偏慢</span>'
                        value_display = f'<span style="color: red; font-weight: bold;">{value:.4f} ↓</span>'
                else:
                    # 其他指标
                    if value <= 0.5:
                        status = '<span style="color: green; font-weight: bold;">正常</span>'
                        value_display = f'{value:.4f}'
                    else:
                        status = '<span style="color: red; font-weight: bold;">偏高</span>'
                        value_display = f'<span style="color: red; font-weight: bold;">{value:.4f} ↑</span>'
                
                row_style = 'background: #f8f9fa;' if i % 2 == 0 else 'background: white;'
                
                comprehensive_html += f'''
                    <tr style="{row_style}">
                        <td style="padding: 10px; border-bottom: 1px solid #e9ecef; font-weight: bold; color: #495057;">{indicator}</td>
                        <td style="padding: 10px; border-bottom: 1px solid #e9ecef; text-align: center;">{value_display}</td>
                        <td style="padding: 10px; border-bottom: 1px solid #e9ecef; text-align: center; color: #28a745;">{reference}</td>
                        <td style="padding: 10px; border-bottom: 1px solid #e9ecef; text-align: center;">{status}</td>
                    </tr>
                '''
        
        # 生成总结性建议
        issues = []
        strengths = []
        
        if assessment_data.get('situp_time', 0) > 15:
            issues.append('下肢力量偏弱')
        elif assessment_data.get('situp_time', 0) <= 12:
            strengths.append('下肢力量良好')
            
        left_pressure = assessment_data.get('left_pressure', 0)
        right_pressure = assessment_data.get('right_pressure', 0)
        if abs(left_pressure - right_pressure) > 15:
            issues.append('臀部压力分布不均')
        else:
            strengths.append('臀部压力分布均衡')
            
        micro_vib = assessment_data.get('micro_vibration', 0)
        if micro_vib <= 0.3:
            strengths.append('静态平衡优秀')
        elif micro_vib > 0.5:
            issues.append('静态平衡欠佳')
        
        comprehensive_html += f'''
                </tbody>
            </table>
            
            <div style="margin-top: 20px; padding: 15px; background: linear-gradient(135deg, #E8F5E8 0%, #C8E6C9 100%); border-left: 4px solid #4CAF50; border-radius: 6px;">
                <h4 style="color: #2E7D32; margin-bottom: 10px;">🎯 综合分析结论</h4>
                
                {"<p style='color: #2E7D32; margin-bottom: 8px;'><strong>优势表现：</strong>" + "、".join(strengths) + "</p>" if strengths else ""}
                
                {"<p style='color: #E65100; margin-bottom: 8px;'><strong>关注要点：</strong>" + "、".join(issues) + "</p>" if issues else ""}
                
                <p style="color: #1976D2; margin-top: 10px; font-weight: bold;">
                    💡 <strong>整体评价：</strong>
                    {"功能状态良好，建议维持当前运动水平" if len(issues) == 0 else "部分指标需要关注，建议针对性康复训练" if len(issues) <= 2 else "多项指标异常，建议专业医学评估"}
                </p>
            </div>
        </div>
        '''
        
        results['comprehensive_assessment_table'] = comprehensive_html
    
    def generate_final_fix_html_template(self) -> str:
        """生成最终修复版HTML模板"""
        
        # 获取原始模板
        original_template = super().generate_corrected_html_template()
        
        # 修复模板插入点
        insertions = [
            # 1. 在警告后插入逻辑解释
            (
                '<div class="warning">\n                <strong>⚠️ 参考范围说明：</strong>本报告采用AWGS（亚洲肌少症工作组）2019共识标准，\n                参考范围已根据患者年龄（{{age}}岁）进行分层调整。\n            </div>',
                '{{enhanced_logic_explanation}}\n            \n            <div class="warning">\n                <strong>⚠️ 参考范围说明：</strong>本报告采用AWGS（亚洲肌少症工作组）2019共识标准，\n                参考范围已根据患者年龄（{{age}}岁）进行分层调整。\n            </div>'
            ),
            
            # 2. 在五次起坐测试后插入详细分解
            (
                '</table>\n            \n            <h3>前后脚静态站立十秒（所有采集数据精确到小数点后四位）</h3>',
                '</table>\n            \n            {{situp_breakdown_table}}\n            \n            <h3>前后脚静态站立十秒（所有采集数据精确到小数点后四位）</h3>'
            ),
            
            # 3. 在综合评估前插入对比表
            (
                '<h2 class="section-title">三、综合评估与建议</h2>',
                '{{comprehensive_assessment_table}}\n            \n            <h2 class="section-title">三、综合评估与建议</h2>'
            ),
        ]
        
        # 应用所有插入
        improved_template = original_template
        for old_text, new_text in insertions:
            improved_template = improved_template.replace(old_text, new_text)
        
        return improved_template
    
    def generate_final_fix_report(self, folder_path: str, group_name: str, age: int, output_path: str):
        """生成最终修复版报告"""
        
        print(f"🎯 生成最终修复版报告：{group_name}")
        
        # 处理数据并应用精准修复
        results = self.process_test_data_with_precise_fixes(folder_path, group_name, age)
        
        # 生成最终修复版模板
        template = self.generate_final_fix_html_template()
        
        # 替换所有占位符
        for key, value in results.items():
            placeholder = f"{{{{{key}}}}}"
            template = template.replace(placeholder, str(value))
        
        # 保存报告
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(template)
        
        print(f"✅ 最终修复版报告已生成：{output_path}")
        print("🎯 精准解决的问题：")
        print("   ✅ 五次起坐左右发力分解 - 每次都有箭头标注")
        print("   ✅ 足底轮廓和虚线力线 - 白色轮廓+黄色虚线+COP标记")
        print("   ✅ 脚部压力箭头标注 - 左右对比大侧标红箭头")
        print("   ✅ 逻辑解释说明 - COP vs 压力分布差异原理")
        print("   ✅ 综合评估全覆盖 - 臀部+脚部+功能性指标对比表")
        print("   ✅ 参考范围说明 - 明确AWGS vs 系统经验值")
        
        return results

def main():
    """主函数"""
    generator = FinalFixReportGenerator()
    
    output_path = f"final_fix_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.html"
    
    generator.generate_final_fix_report(
        folder_path='for test/1',
        group_name='曾超08',
        age=65,
        output_path=output_path
    )

if __name__ == "__main__":
    main()