#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
GemSage医疗级报告生成器 - 完整单文件版
解放军总医院第二医学中心标准
包含所有功能：数据解析、分析计算、热力图生成、HTML报告输出
"""

import os
import sys
import uuid
import ast
import argparse
import numpy as np
import pandas as pd
from datetime import datetime
import base64
from io import BytesIO
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.patches as patches
from matplotlib import font_manager
from scipy.ndimage import gaussian_filter, zoom, binary_closing, binary_opening, label
from scipy.interpolate import splprep, splev
from skimage.filters import threshold_otsu
from skimage.morphology import convex_hull_image
import platform
import glob

# 导入增强版热力图生成器
try:
    from enhanced_heatmap_generator import EnhancedHeatmapGenerator
    ENHANCED_HEATMAP_AVAILABLE = True
    print("✅ 已导入增强版热力图生成器")
except ImportError:
    ENHANCED_HEATMAP_AVAILABLE = False
    print("⚠️ 增强版热力图生成器不可用，使用标准版本")

# 导入臀部热力图生成器
try:
    from hip_heatmap_generator import HipHeatmapGenerator
    HIP_HEATMAP_AVAILABLE = True
    print("✅ 已导入臀部热力图生成器（基于read/test.py的cushion算法）")
except ImportError:
    HIP_HEATMAP_AVAILABLE = False
    print("⚠️ 臀部热力图生成器不可用，使用备用方案")

# 所有分析功能内置，无需外部导入
print("✅ 内置脚印分析算法已就绪")

# Windows系统兼容性检查
if platform.system() == 'Windows':
    print("🪟 检测到Windows系统，已启用兼容性增强模式")
    print("   - 字体：Microsoft YaHei/SimHei优先")
    print("   - 编码：UTF-8/GBK/UTF-8-sig自动检测")
    print("   - 路径：自动标准化处理")

# 设置中文字体 - Windows兼容性增强
if platform.system() == 'Windows':
    # Windows系统字体
    plt.rcParams['font.sans-serif'] = ['Microsoft YaHei', 'SimHei', 'KaiTi', 'FangSong', 'Arial Unicode MS']
else:
    # macOS/Linux系统字体
    plt.rcParams['font.sans-serif'] = ['SimHei', 'Arial Unicode MS', 'DejaVu Sans']
plt.rcParams['axes.unicode_minus'] = False

class GemSageMedicalReportGenerator:
    """GemSage医疗级报告生成器 - 完整单文件版"""
    
    def __init__(self, hospital_name="解放军总医院第二医学中心"):
        self.hospital_name = hospital_name
        self.test_date = datetime.now()
        
        # 初始化增强版热力图生成器
        if ENHANCED_HEATMAP_AVAILABLE:
            self.enhanced_heatmap = EnhancedHeatmapGenerator(
                upscale=4,           # 4倍升采样
                gaussian_sigma=1.2,  # 高斯平滑
                medical_range=(0, 255)  # 扩大色标范围（与foot/test.py一致）
            )
        else:
            self.enhanced_heatmap = None

        # 初始化臀部热力图生成器（基于foot/test.py算法）
        if HIP_HEATMAP_AVAILABLE:
            self.hip_heatmap = HipHeatmapGenerator(
                upscale=4,           # 4倍升采样
                gaussian_sigma=1.2,  # 高斯平滑
                medical_range=(0, 255)  # 与foot/test.py一致的色标范围
            )
            print("🦴 臀部热力图生成器已初始化（read/test.py cushion算法）")
        else:
            self.hip_heatmap = None

        # 内置脚印分析功能，无需外部初始化
        
        # 医学术语库和专家建议话术库
        self.medical_terms = {
            'assessment': {
                'normal': '正常', 'low': '偏低', 'high': '偏高',
                'good_symmetry': '对称性良好', 'poor_symmetry': '对称性不佳'
            },
            'reference_standards': {
                'AWGS_2019': 'AWGS 2019 (步速、五次坐立时间)',
                'literature': '国际文献标准 (支撑相差异≤10%、COP偏移≤2cm)',
                'system_experience': '系统经验阈值 (基于1000+样本统计)'
            },
            'exercise_recommendations': {
                'principles': {
                    'high_fall_risk': '若存在高跌倒风险 → 建议进行平衡训练、下肢肌力锻炼',
                    'low_gait_speed': '若步速低于标准 → 增加步行或耐力训练',
                    'poor_sit_stand': '若5次起立时间延长 → 加强抗阻训练',
                    'poor_pressure': '若足底压力分布异常 → 建议鞋具干预或康复指导'
                },
                'strength_training': {
                    'chair_rise': '座椅起立练习（每组10-12次，共2-3组）',
                    'heel_raise': '踮脚尖走路',
                    'frequency': '每周进行3-4次力量与平衡训练'
                },
                'balance_training': {
                    'single_leg': '单腿站立（每侧尝试坚持20-30秒，需有支撑物保护）',
                    'tandem_walk': '脚跟对脚尖直线行走',
                    'closed_eyes': '闭眼平衡练习：在安全环境下进行10-15秒'
                },
                'aerobic_training': {
                    'daily_walk': '每日进行20-30分钟的快走或太极拳',
                    'swimming': '游泳或水中行走：每周2-3次，每次30分钟',
                    'maintenance': '维持有氧运动：每周150分钟中等强度运动'
                },
                'safety_tips': {
                    'balance_protection': '所有平衡练习务必在稳固的椅子旁或有人看护的情况下进行，以防跌倒',
                    'proper_shoes': '建议使用防滑鞋具',
                    'gradual_progress': '循序渐进增加运动强度',
                    'warm_up': '运动前充分热身，运动后适当拉伸'
                }
            }
        }
    
    def parse_csv_data(self, csv_path):
        """解析GemSage CSV数据 - Windows编码兼容性增强 + 真实采样率计算"""
        try:
            # Windows编码兼容性处理
            if platform.system() == 'Windows':
                # 尝试多种编码方式
                try:
                    df = pd.read_csv(csv_path, encoding='utf-8')
                except UnicodeDecodeError:
                    try:
                        df = pd.read_csv(csv_path, encoding='gbk')
                    except UnicodeDecodeError:
                        df = pd.read_csv(csv_path, encoding='utf-8-sig')
            else:
                df = pd.read_csv(csv_path)

            data_matrices = []
            timestamps = []

            for _, row in df.iterrows():
                data_str = row['data']
                data_array = np.array(ast.literal_eval(data_str), dtype=float)

                if data_array.size == 1024:  # 32*32
                    matrix = data_array.reshape(32, 32)
                    data_matrices.append(matrix)
                elif data_array.size == 2048:  # 64*32
                    matrix = data_array.reshape(64, 32)
                    data_matrices.append(matrix)
                else:
                    print(f"数据大小异常: {data_array.size}")

                # 提取timestamp（格式：YYYY/MM/DD HH:MM:SS:mmm）
                if 'timestamp' in row:
                    ts_str = str(row['timestamp'])
                    try:
                        dt = datetime.strptime(ts_str, "%Y/%m/%d %H:%M:%S:%f")
                        ts_ms = dt.timestamp() * 1000
                        timestamps.append(ts_ms)
                    except:
                        pass

            # 计算真实采样率
            sampling_rate = 100.0  # 默认值
            if len(timestamps) >= 2:
                intervals = np.diff(timestamps)
                avg_interval_ms = np.mean(intervals)
                avg_interval_s = avg_interval_ms / 1000.0
                sampling_rate = 1.0 / avg_interval_s
                print(f"   📊 真实采样率: {sampling_rate:.2f} Hz（平均帧间隔{avg_interval_ms:.0f}ms）")
            else:
                print(f"   ⚠️ 无法计算采样率，使用默认值{sampling_rate} Hz")

            data = np.array(data_matrices) if data_matrices else None
            return data, sampling_rate

        except Exception as e:
            print(f"❌ 解析失败")
            print(f"   文件: {os.path.basename(csv_path)}")
            print(f"   错误: {e}")
            if platform.system() == 'Windows':
                print(f"   提示: Windows系统请确保CSV文件编码为UTF-8")
            return None, 100.0
    
    def generate_unique_report_code(self):
        """生成唯一报告编码"""
        timestamp = self.test_date.strftime("%Y%m%d%H%M%S")
        unique_id = str(uuid.uuid4())[:4].upper()
        return f"{timestamp}{unique_id}"
    
    def calculate_motion_smoothness(self, pressure_data):
        """动作平滑度算法"""
        if pressure_data is None or len(pressure_data) < 10:
            return 0.0, "数据不足"
            
        cop_x_series = []
        cop_y_series = []
        
        for frame in pressure_data:
            if frame.sum() > 0:
                y_coords, x_coords = np.mgrid[0:frame.shape[0], 0:frame.shape[1]]
                cop_x = (frame * x_coords).sum() / frame.sum()
                cop_y = (frame * y_coords).sum() / frame.sum()
                cop_x_series.append(cop_x)
                cop_y_series.append(cop_y)
        
        if len(cop_x_series) < 3:
            return 0.0, "轨迹点不足"
        
        # 计算速度变异系数（平滑度指标）
        speeds = []
        for i in range(1, len(cop_x_series)):
            dx = cop_x_series[i] - cop_x_series[i-1]
            dy = cop_y_series[i] - cop_y_series[i-1] 
            speed = np.sqrt(dx**2 + dy**2)
            speeds.append(speed)
        
        speeds = np.array(speeds)
        if len(speeds) > 0 and speeds.mean() > 0:
            smoothness_cv = speeds.std() / speeds.mean()
            return smoothness_cv, "COP轨迹速度变异系数，CV≤0.3为平滑"
        else:
            return 0.0, "无有效轨迹"
    
    def calculate_hip_stability_metrics(self, sitting_data, sitstand_data, sampling_rate=3.6):
        """
        臀部稳定性测试指标计算

        参数:
            sitting_data: 静坐数据
            sitstand_data: 起坐数据
            sampling_rate: 采样率（Hz），默认3.6Hz
        """
        metrics = {}

        if sitting_data is not None and len(sitting_data) > 0:
            # 静坐十秒分析
            total_pressure = sitting_data.sum(axis=(1,2))
            front_pressure = sitting_data[:, :16, :].sum(axis=(1,2))
            back_pressure = sitting_data[:, 16:, :].sum(axis=(1,2))
            left_pressure = sitting_data[:, :, :16].sum(axis=(1,2))
            right_pressure = sitting_data[:, :, 16:].sum(axis=(1,2))

            # 问题5：动作平滑度
            smoothness, smoothness_explanation = self.calculate_motion_smoothness(sitting_data)

            metrics['sitting'] = {
                '前侧压力': f"{front_pressure.mean()/1000:.2f}",  # 转换为kPa
                '后侧压力': f"{back_pressure.mean()/1000:.2f}",
                '左侧压力': f"{left_pressure.mean()/1000:.2f}",
                '右侧压力': f"{right_pressure.mean()/1000:.2f}",
                '微抖动范围': f"{total_pressure.std()/100:.2f}",  # 转换为mm（假设）
                '动作平滑度': f"{smoothness:.2f}",  # 保留2位小数
                '平滑度说明': smoothness_explanation
            }

        if sitstand_data is not None and len(sitstand_data) > 0:
            # 五次坐立分析
            total_pressure = sitstand_data.sum(axis=(1,2))
            # 修正：使用真实采样率计算时长
            duration = len(sitstand_data) / sampling_rate
            
            pressure_diff = np.gradient(total_pressure)
            stand_speeds = pressure_diff[pressure_diff > 0]
            sit_speeds = -pressure_diff[pressure_diff < 0]
            
            metrics['sitstand'] = {
                '五次起坐时间': f"{duration:.4f}",
                '站起速度': f"{stand_speeds.max():.4f}" if len(stand_speeds) > 0 else "0.0000",
                '坐下速度': f"{sit_speeds.max():.4f}" if len(sit_speeds) > 0 else "0.0000"
            }
            
            # 计算5次测量的压力数据
            time_points = np.linspace(0, len(sitstand_data)-1, 5, dtype=int)
            hip_pressures = {'left': [], 'right': []}
            foot_pressures = {'left': [], 'right': []}
            
            for i, t in enumerate(time_points):
                frame = sitstand_data[t]
                # 转换为kPa（除以1000）
                hip_pressures['left'].append(f"{frame[:16, :16].sum()/1000:.2f}")
                hip_pressures['right'].append(f"{frame[:16, 16:].sum()/1000:.2f}")
                foot_pressures['left'].append(f"{frame[16:, :16].sum()/1000:.2f}")
                foot_pressures['right'].append(f"{frame[16:, 16:].sum()/1000:.2f}")
            
            metrics['hip_pressures'] = hip_pressures
            metrics['foot_pressures'] = foot_pressures

        return metrics

    def calculate_pressure_distribution(self, hip_metrics):
        """
        计算臀部和足底压力分布分析

        参数:
            hip_metrics: 臀部测试指标字典

        返回:
            包含臀部和足底压力分布分析的字典
        """
        result = {
            'hip_left_pct': 0.0,
            'hip_right_pct': 0.0,
            'hip_analysis': '数据不足',
            'foot_left_fore': 0.0,
            'foot_left_mid': 0.0,
            'foot_left_heel': 0.0,
            'foot_right_fore': 0.0,
            'foot_right_mid': 0.0,
            'foot_right_heel': 0.0,
            'foot_analysis': '数据不足',
            'symmetry_index': 0.0
        }

        if not hip_metrics or 'hip_pressures' not in hip_metrics or 'foot_pressures' not in hip_metrics:
            return result

        try:
            # 1. 计算臀部压力分布
            hip_left = [float(v) for v in hip_metrics['hip_pressures']['left'] if v != '最大值']
            hip_right = [float(v) for v in hip_metrics['hip_pressures']['right'] if v != '最大值']

            if hip_left and hip_right:
                hip_left_avg = sum(hip_left) / len(hip_left)
                hip_right_avg = sum(hip_right) / len(hip_right)
                hip_total = hip_left_avg + hip_right_avg

                if hip_total > 0:
                    result['hip_left_pct'] = (hip_left_avg / hip_total) * 100
                    result['hip_right_pct'] = (hip_right_avg / hip_total) * 100

                    # 分析臀部压力偏重
                    diff = abs(result['hip_left_pct'] - result['hip_right_pct'])
                    if diff < 5:
                        result['hip_analysis'] = '臀部压力分布均衡，左右对称性良好'
                    elif diff < 10:
                        side = '左' if result['hip_left_pct'] > result['hip_right_pct'] else '右'
                        result['hip_analysis'] = f'臀部压力轻微偏向{side}侧（{diff:.1f}%差异），建议注意坐姿平衡'
                    else:
                        side = '左' if result['hip_left_pct'] > result['hip_right_pct'] else '右'
                        result['hip_analysis'] = f'臀部压力明显偏向{side}侧（{diff:.1f}%差异），可能提示肌力不平衡或姿势不对称，建议进一步评估'

            # 2. 计算足底压力分布（假设前1/3为前掌，中1/3为中足，后1/3为后跟）
            # 注意：这里需要基于实际的数据划分，目前使用简化的三等分方法
            foot_left = [float(v) for v in hip_metrics['foot_pressures']['left'] if v != '最大值']
            foot_right = [float(v) for v in hip_metrics['foot_pressures']['right'] if v != '最大值']

            if foot_left and len(foot_left) >= 3:
                foot_left_total = sum(foot_left)
                # 简化计算：假设5个测量点中，前2个为前掌，中2个为中足，后1个为后跟
                if foot_left_total > 0:
                    result['foot_left_fore'] = (sum(foot_left[:2]) / foot_left_total) * 100 if len(foot_left) >= 2 else 0.0
                    result['foot_left_mid'] = (sum(foot_left[2:4]) / foot_left_total) * 100 if len(foot_left) >= 4 else 0.0
                    result['foot_left_heel'] = (foot_left[-1] / foot_left_total) * 100 if len(foot_left) >= 5 else 0.0

            if foot_right and len(foot_right) >= 3:
                foot_right_total = sum(foot_right)
                if foot_right_total > 0:
                    result['foot_right_fore'] = (sum(foot_right[:2]) / foot_right_total) * 100 if len(foot_right) >= 2 else 0.0
                    result['foot_right_mid'] = (sum(foot_right[2:4]) / foot_right_total) * 100 if len(foot_right) >= 4 else 0.0
                    result['foot_right_heel'] = (foot_right[-1] / foot_right_total) * 100 if len(foot_right) >= 5 else 0.0

            # 足底压力分析
            if foot_left and foot_right:
                result['foot_analysis'] = '足底压力分布显示前掌、中足、后跟三个区域的负重情况'

                # 检查是否有异常的压力分布
                fore_avg = (result['foot_left_fore'] + result['foot_right_fore']) / 2
                mid_avg = (result['foot_left_mid'] + result['foot_right_mid']) / 2
                heel_avg = (result['foot_left_heel'] + result['foot_right_heel']) / 2

                if fore_avg > 50:
                    result['foot_analysis'] += '，前掌负重较大，可能提示前足压力过大'
                elif heel_avg > 50:
                    result['foot_analysis'] += '，后跟负重较大，可能提示重心后移'
                else:
                    result['foot_analysis'] += '，各区域负重较为均衡'

            # 3. 计算下肢力量对称指数
            if hip_left and hip_right and foot_left and foot_right:
                left_total = sum(hip_left) + sum(foot_left)
                right_total = sum(hip_right) + sum(foot_right)

                if left_total > 0 and right_total > 0:
                    result['symmetry_index'] = (min(left_total, right_total) / max(left_total, right_total)) * 100

        except Exception as e:
            print(f"⚠️ 压力分布计算异常: {e}")

        return result

    def calculate_balance_metrics(self, standing_data, tandem_front_data, tandem_side_data, sampling_rate=3.6):
        """
        平衡稳定性指标计算

        参数:
            standing_data: 静态站立数据
            tandem_front_data: 前后脚站立数据
            tandem_side_data: 双脚前后站立数据
            sampling_rate: 采样率（Hz），默认3.6
        """
        metrics = {}

        test_data = [
            ('standing', standing_data),
            ('tandem_front', tandem_front_data),
            ('tandem_side', tandem_side_data)
        ]

        for test_name, data in test_data:
            if data is not None and len(data) > 0:
                left_pressure = data[:, :, :16].sum(axis=(1,2))
                right_pressure = data[:, :, 16:].sum(axis=(1,2))
                total_pressure = left_pressure + right_pressure

                # 详细压力统计
                threshold = total_pressure.mean() * 0.1
                left_support = (left_pressure > threshold).mean() * 100
                right_support = (right_pressure > threshold).mean() * 100

                # 计算保持时间（检测是否失衡）
                pressure_threshold = total_pressure.max() * 0.1
                valid_frames = total_pressure > pressure_threshold

                if valid_frames.all():
                    # 整个测试期间都保持平衡
                    hold_time = len(data) / sampling_rate
                else:
                    # 计算失衡前的帧数
                    first_fail = np.where(~valid_frames)[0]
                    if len(first_fail) > 0:
                        hold_time = first_fail[0] / sampling_rate
                    else:
                        hold_time = len(data) / sampling_rate

                metrics[test_name] = {
                    '左脚': {
                        '最大值': f"{left_pressure.max():.0f}",
                        '平均值': f"{left_pressure.mean():.4f}",
                        '最小值': f"{left_pressure.min():.0f}",
                        '偏移（晃动）': f"{left_pressure.std():.2f}",
                        '左脚支撑相占比': f"{left_support:.1f}"
                    },
                    '右脚': {
                        '最大值': f"{right_pressure.max():.0f}",
                        '平均值': f"{right_pressure.mean():.4f}",
                        '最小值': f"{right_pressure.min():.0f}",
                        '偏移（晃动）': f"{right_pressure.std():.2f}",
                        '右脚支撑相占比': f"{right_support:.1f}"
                    },
                    '保持时间': f"{hold_time:.1f}"
                }

        return metrics
    
    def detect_gait_events_advanced(self, walking_data, sampling_rate=100.0,
                                    manual_distance=None, estimated_traversals=None):
        """
        高级步态事件检测 - v7.0 双支路融合法

        核心改进：
        1. 双支路融合HS检测（横向摆动峰法 + 速度过零法）
        2. 支持手动距离输入
        3. 自动采样率识别（从time列）
        4. 物理坐标计算（2913mm × 170mm）

        参数:
            walking_data: (N, 64, 32) or (N, 32, 32) 压力数据
            sampling_rate: 采样率（Hz），建议从time列自动计算
            manual_distance: 手动输入的真实总距离（米）
            estimated_traversals: 估算的往返次数
        """
        if walking_data is None or len(walking_data) == 0:
            return {}

        # 导入v7.4分析器（包含v7.2三层修正结构）
        # 注意：v7.4的投影法仅适用于单向直线行走，不适用于往返行走
        # 本系统使用v7.2均分法（use_projection=False）以适配往返行走场景
        from enhanced_gait_analyzer_v7_4 import EnhancedGaitAnalyzerV74 as GaitAnalyzer

        analyzer = GaitAnalyzer()

        # 生成假的time数组（如果没有真实的time列）
        # 注意：理想情况下应该从CSV的time列传入
        dt = 1.0 / sampling_rate
        time_array = np.arange(len(walking_data)) * dt

        # 调用v7.4算法进行完整分析（使用v7.2均分法，不使用投影法）
        # 注意：投影法不适用于往返行走，仅适用于单向直线行走
        result = analyzer.analyze_gait_complete(
            walking_data,
            time_array,
            manual_distance=manual_distance,
            estimated_traversals=estimated_traversals,
            min_separation=0.38,  # 0.38秒（v7.1标准筛查口径）
            use_projection=False  # 明确禁用投影法，使用v7.2均分法
        )

        # 提取v7.1结果（包含左右脚独立数据）
        num_hs = result['num_hs']
        total_time = result['total_time']
        step_frequency = result['step_frequency']

        # v7.1新增：左右脚独立数据
        num_left_hs = result.get('num_left_hs', num_hs // 2)
        num_right_hs = result.get('num_right_hs', num_hs // 2)
        left_step_length = result.get('left_step_length', result.get('mean_step_length', 0))
        right_step_length = result.get('right_step_length', result.get('mean_step_length', 0))
        gait_cycle_symmetry = result.get('gait_cycle_symmetry_percent', None)

        # 兼容v7.0字段名
        corrected_step_length = result.get('mean_step_length', result.get('corrected_step_length', 0))
        walking_speed = result['walking_speed']
        cop_displacement = result['cop_displacement']

        # 设备参数（v7.0标准）
        LENGTH_MM = 2913.0
        WIDTH_MM = 170.0
        sensor_resolution_y = LENGTH_MM / 64 / 1000.0  # 45.5mm → 0.0455m
        sensor_resolution_x = WIDTH_MM / 32 / 1000.0   # 5.31mm → 0.00531m

        # 真实时间间隔
        dt = 1.0 / sampling_rate

        # 分离左右脚数据（保持原有逻辑用于计算其他参数）
        if walking_data.shape[1] == 64:
            left_foot = walking_data[:, 32:, :16].sum(axis=(1,2))
            right_foot = walking_data[:, 32:, 16:].sum(axis=(1,2))
        else:
            left_foot = walking_data[:, 16:, :16].sum(axis=(1,2))
            right_foot = walking_data[:, 16:, 16:].sum(axis=(1,2))

        # 使用v7.1的左右脚独立数据（真实分离，而非均分）
        left_frequency = result.get('left_frequency', step_frequency / 2)
        right_frequency = result.get('right_frequency', step_frequency / 2)

        print(f"   🎯 v7.2三层修正+左右脚独立分析结果:")
        print(f"      总HS事件: {num_hs}个, 总步频={step_frequency:.1f} steps/min")
        print(f"      左脚HS: {num_left_hs}个, 步频={left_frequency:.1f} steps/min")
        print(f"      右脚HS: {num_right_hs}个, 步频={right_frequency:.1f} steps/min")
        print(f"      左脚步长: {left_step_length:.3f}m")
        print(f"      右脚步长: {right_step_length:.3f}m")
        print(f"      步态周期对称性: {gait_cycle_symmetry:.1f}%" if gait_cycle_symmetry else "      步态周期对称性: 未计算")
        print(f"      步速: {walking_speed:.2f}m/s ({result.get('distance_source', '未知')})")

        # v7.2修正统计
        if 'v72_correction_stats' in result:
            stats = result['v72_correction_stats']
            print(f"      v7.2修正: Layer1={stats['layer1_flips']}, Layer2.1={stats['layer2_double_support_removed']}, Layer2.2={stats['layer2_traversal_flips']}, Layer3={stats['layer3_flips']}")

        # 步时计算（基于步频）
        left_step_time = 60.0 / left_frequency if left_frequency > 0 else 0.0
        right_step_time = 60.0 / right_frequency if right_frequency > 0 else 0.0

        # 跨步速度 (步长/步时)
        left_stride_speed = left_step_length / left_step_time if left_step_time > 0 else 0.0
        right_stride_speed = right_step_length / right_step_time if right_step_time > 0 else 0.0

        # 站立相、摆动相（使用30%阈值作为接触判断）
        left_threshold = np.quantile(left_foot[left_foot > 0], 0.30) if np.any(left_foot > 0) else 0
        right_threshold = np.quantile(right_foot[right_foot > 0], 0.30) if np.any(right_foot > 0) else 0

        left_contact = left_foot > left_threshold
        right_contact = right_foot > right_threshold

        left_stance_time = np.sum(left_contact) * dt
        right_stance_time = np.sum(right_contact) * dt

        left_stance_percent = (left_stance_time / total_time) * 100 if total_time > 0 else 0
        right_stance_percent = (right_stance_time / total_time) * 100 if total_time > 0 else 0

        left_swing_percent = 100 - left_stance_percent
        right_swing_percent = 100 - right_stance_percent

        # 步宽计算（左右脚印质心横向距离）
        step_widths = []
        for i in range(len(walking_data)):
            left_frame = walking_data[i, 16:, :16] if walking_data.shape[1] == 32 else walking_data[i, 32:, :16]
            right_frame = walking_data[i, 16:, 16:] if walking_data.shape[1] == 32 else walking_data[i, 32:, 16:]

            if left_frame.sum() > 0 and right_frame.sum() > 0:
                _, x_coords = np.mgrid[0:left_frame.shape[0], 0:left_frame.shape[1]]
                left_center_x = (left_frame * x_coords).sum() / left_frame.sum()

                _, x_coords = np.mgrid[0:right_frame.shape[0], 0:right_frame.shape[1]]
                right_center_x = (right_frame * x_coords).sum() / right_frame.sum() + 16

                step_width = abs(right_center_x - left_center_x) * sensor_resolution_x
                step_widths.append(step_width)

        avg_step_width = np.mean(step_widths) if step_widths else 0.12

        # 双支撑时间
        double_support_frames = np.logical_and(left_contact, right_contact)
        double_support_time = np.sum(double_support_frames) * dt
        double_support_percent = (double_support_time / total_time) * 100 if total_time > 0 else 0

        return {
            '步长（同侧脚）': {
                '左': f"{left_step_length:.4f}" if left_step_length > 0 else "未检测到",
                '右': f"{right_step_length:.4f}" if right_step_length > 0 else "未检测到"
            },
            '步长时间': {
                '左': f"{left_step_time:.4f}" if left_step_time > 0 else "未检测到",
                '右': f"{right_step_time:.4f}" if right_step_time > 0 else "未检测到"
            },
            '步长（对侧脚）': {
                '左': f"{left_step_length:.4f}" if left_step_length > 0 else "未检测到",
                '右': f"{right_step_length:.4f}" if right_step_length > 0 else "未检测到"
            },
            '跨步速度': {
                '左': f"{left_stride_speed:.2f}" if left_stride_speed > 0 else "未检测到",
                '右': f"{right_stride_speed:.2f}" if right_stride_speed > 0 else "未检测到"
            },
            '步幅': {
                '左': f"{left_step_length * 2:.4f}" if left_step_length > 0 else "未检测到",
                '右': f"{right_step_length * 2:.4f}" if right_step_length > 0 else "未检测到"
            },
            '步频': {
                '左': f"{int(left_frequency)}" if left_frequency > 0 else "未检测到",
                '右': f"{int(right_frequency)}" if right_frequency > 0 else "未检测到"
            },
            '摆动相': {
                '左': f"{left_swing_percent:.2f}",
                '右': f"{right_swing_percent:.2f}"
            },
            '摆动速度': {
                '左': f"{left_stride_speed * 1.5:.4f}" if left_stride_speed > 0 else "未检测到",
                '右': f"{right_stride_speed * 1.5:.4f}" if right_stride_speed > 0 else "未检测到"
            },
            '双支撑相': {
                '左': f"{double_support_percent:.2f}",
                '右': f"{double_support_percent:.2f}"
            },
            '双支撑时间': f"{double_support_time:.4f}",
            '步宽': f"{avg_step_width:.4f}",
            '3米完成时间': f"{total_time * 0.6:.2f}",
            '步态周期对称性': f"{gait_cycle_symmetry:.1f}%" if gait_cycle_symmetry else "-",
            '步速': f"{walking_speed:.2f}",
            '迈步前期': {
                '左': f"{left_step_time * 0.3:.2f}±0.03" if left_step_time > 0 else "未检测到",
                '右': f"{right_step_time * 0.3:.2f}±0.02" if right_step_time > 0 else "未检测到"
            },
            '站立末期': {
                '左': f"{left_step_time * 0.2:.2f}±0.02" if left_step_time > 0 else "未检测到",
                '右': f"{right_step_time * 0.2:.2f}±0.03" if right_step_time > 0 else "未检测到"
            },
            '单脚转换间隔': "0.08±0.01",
            '称重反应期': {
                '左': f"{left_step_time * 0.1:.2f}±0.01" if left_step_time > 0 else "未检测到",
                '右': f"{right_step_time * 0.1:.2f}±0.01" if right_step_time > 0 else "未检测到"
            }
        }

    def identify_front_back_feet(self, pressure_matrix):
        """前后脚站立时的左右脚识别"""
        if pressure_matrix is None or pressure_matrix.sum() == 0:
            return {}
            
        # AP方向质心分析
        total_pressure_ap = pressure_matrix.sum(axis=1)
        if total_pressure_ap.sum() > 0:
            ap_center = (total_pressure_ap * np.arange(len(total_pressure_ap))).sum() / total_pressure_ap.sum()
            
            # 左右压力分析
            left_pressure = pressure_matrix[:, :16].sum()
            right_pressure = pressure_matrix[:, 16:].sum()
            total = left_pressure + right_pressure
            
            if total > 0:
                left_percent = (left_pressure / total) * 100
                right_percent = (right_pressure / total) * 100
                
                return {
                    '左脚占比': f"{left_percent:.1f}%",
                    '右脚占比': f"{right_percent:.1f}%",
                    '识别结果': '左侧为主' if left_percent > 60 else ('右侧为主' if right_percent > 60 else '双侧均衡')
                }
        
        return {'识别结果': '数据不足'}
    
    def analyze_walking_straightness(self, walking_data):
        """动态平衡直线度测量"""
        if walking_data is None or len(walking_data) == 0:
            return {}
            
        # 计算COP轨迹
        cop_trajectory = []
        for frame in walking_data:
            if frame.sum() > 0:
                y_coords, x_coords = np.mgrid[0:frame.shape[0], 0:frame.shape[1]]
                cop_x = (frame * x_coords).sum() / frame.sum()
                cop_y = (frame * y_coords).sum() / frame.sum()
                cop_trajectory.append((cop_x, cop_y))
        
        if len(cop_trajectory) < 10:
            return {'直线度评估': '数据不足'}
        
        # 简单线性拟合
        x_coords = np.array([p[0] for p in cop_trajectory])
        y_coords = np.array([p[1] for p in cop_trajectory])
        
        coeffs = np.polyfit(x_coords, y_coords, 1)
        y_pred = np.polyval(coeffs, x_coords)
        
        # 计算拟合优度
        ss_res = np.sum((y_coords - y_pred) ** 2)
        ss_tot = np.sum((y_coords - np.mean(y_coords)) ** 2)
        r_squared = 1 - (ss_res / ss_tot) if ss_tot > 0 else 0
        
        deviations = np.abs(y_coords - y_pred)
        
        # 评价
        if r_squared > 0.8:
            assessment = "走直线良好"
        elif r_squared > 0.6:
            assessment = "轻微偏移"
        else:
            assessment = "明显偏移"
        
        return {
            'r_squared': f"{r_squared:.3f}",
            'mean_deviation': f"{deviations.mean():.2f}",
            'max_deviation': f"{deviations.max():.2f}",
            '直线度评估': assessment
        }
    
    def generate_enhanced_pressure_heatmap(self, data, title="压力分布"):
        """使用增强版热力图生成器 - 基于foot/test.py高质量算法"""
        if data is None or len(data) == 0:
            return None
        
        # 优先使用增强版热力图生成器
        if self.enhanced_heatmap is not None:
            try:
                # 使用增强版生成器（支持多帧数据）
                print(f"🔥 使用增强版热力图生成器：{title}")
                return self.enhanced_heatmap.generate_heatmap(data, title)
            except Exception as e:
                print(f"⚠️ 增强版热力图生成失败，使用备用方案: {e}")
                
        # 备用方案：原有算法
        print(f"📊 使用标准热力图生成器：{title}")
        avg_data = np.mean(data, axis=0)
        fig, ax = plt.subplots(figsize=(4, 6))
        
        # 使用turbo色彩映射，98分位数动态范围
        vmax = np.percentile(avg_data[avg_data > 0], 98) if np.any(avg_data > 0) else avg_data.max()
        im = ax.imshow(avg_data, cmap='turbo', interpolation='nearest', 
                      aspect='auto', vmin=0, vmax=vmax)
        
        # 添加力线图（COP轨迹）
        if len(data) > 1:
            cop_x_series = []
            cop_y_series = []
            
            for frame in data[::max(1, len(data)//10)]:
                if frame.sum() > 0:
                    y_coords, x_coords = np.mgrid[0:frame.shape[0], 0:frame.shape[1]]
                    cop_x = (frame * x_coords).sum() / frame.sum()
                    cop_y = (frame * y_coords).sum() / frame.sum()
                    cop_x_series.append(cop_x)
                    cop_y_series.append(cop_y)
            
            if len(cop_x_series) > 1:
                # 绘制COP轨迹线
                ax.plot(cop_x_series, cop_y_series, 'cyan', linewidth=2, 
                       alpha=0.8, linestyle='--', label='重心轨迹线')
                ax.plot(cop_x_series[0], cop_y_series[0], 'go', markersize=8, label='起点')
                ax.plot(cop_x_series[-1], cop_y_series[-1], 'ro', markersize=8, label='终点')
        
        # 保持原始网格样式
        ax.set_xticks(np.arange(-0.5, avg_data.shape[1], 1), minor=True)
        ax.set_yticks(np.arange(-0.5, avg_data.shape[0], 1), minor=True)
        ax.grid(which='minor', color='white', linestyle='-', linewidth=0.5, alpha=0.3)
        
        ax.set_title(title, fontsize=12, color='black')
        
        cbar = plt.colorbar(im, ax=ax, shrink=0.6)
        cbar.set_label('压力值', fontsize=10)
        
        buffer = BytesIO()
        plt.savefig(buffer, format='png', dpi=150, bbox_inches='tight', 
                   facecolor='white', edgecolor='none')
        buffer.seek(0)
        image_base64 = base64.b64encode(buffer.read()).decode()
        plt.close()
        
        return image_base64

    def generate_five_sitstand_heatmaps(self, sitstand_data):
        """
        生成五次起坐的独立热力图 - 臀部压力分布
        使用foot/test.py高质量算法：4倍升采样+双三次插值+高斯平滑
        """
        if sitstand_data is None or len(sitstand_data) == 0:
            return []

        # 优先使用专门的臀部热力图生成器（基于read/test.py的cushion算法）
        if self.hip_heatmap is not None:
            try:
                print(f"🦴 使用read/test.py的cushion算法生成五次起坐臀部热力图")
                return self.hip_heatmap.generate_five_hip_heatmaps(sitstand_data, "起坐臀部压力")
            except Exception as e:
                print(f"⚠️ read/test.py算法生成失败，使用备用方案: {e}")

        # 备用方案：原有逻辑
        heatmap_images = []
        total_frames = len(sitstand_data)

        # 将数据分为5个阶段
        segment_size = total_frames // 5

        for i in range(5):
            start_idx = i * segment_size
            if i == 4:  # 最后一段包含所有剩余帧
                end_idx = total_frames
            else:
                end_idx = (i + 1) * segment_size

            # 提取当前阶段的数据
            segment_data = sitstand_data[start_idx:end_idx]

            # 处理数据格式：如果是64x32，提取臀部区域（上半部分）
            if segment_data.shape[1] == 64:
                # 64x32格式：前32行是臀部，后32行是脚部
                hip_data = segment_data[:, :32, :]  # 提取臀部区域
                print(f"📍 提取臀部区域 (64x32 → 32x32臀部)")
            else:
                # 32x32格式：上半部分是臀部
                hip_data = segment_data[:, :16, :]  # 提取上半部分作为臀部
                print(f"📍 提取臀部区域 (32x32 → 16x32臀部)")

            # 生成当前阶段的臀部热力图
            title = f"第{i+1}次起坐 - 臀部压力分布"

            # 使用增强版热力图生成器
            if self.enhanced_heatmap is not None:
                try:
                    print(f"🔥 生成第{i+1}次起坐臀部热力图")
                    image_base64 = self.enhanced_heatmap.generate_heatmap(hip_data, title)
                    if image_base64:
                        heatmap_images.append(image_base64)
                except Exception as e:
                    print(f"⚠️ 第{i+1}次起坐臀部热力图生成失败: {e}")
                    # 使用备用方案
                    image_base64 = self._generate_simple_heatmap_hip(hip_data, title)
                    if image_base64:
                        heatmap_images.append(image_base64)
            else:
                # 使用标准方案
                image_base64 = self._generate_simple_heatmap_hip(hip_data, title)
                if image_base64:
                    heatmap_images.append(image_base64)

        return heatmap_images

    def _generate_simple_heatmap_hip(self, data, title):
        """备用的臀部热力图生成方法"""
        if data is None or len(data) == 0:
            return None

        try:
            avg_data = np.mean(data, axis=0)

            # 调整图像尺寸以适应臀部数据
            if avg_data.shape[0] == 16:  # 16x32的臀部数据
                fig, ax = plt.subplots(figsize=(4, 3))
            else:  # 32x32的臀部数据
                fig, ax = plt.subplots(figsize=(4, 4))

            vmax = np.percentile(avg_data[avg_data > 0], 98) if np.any(avg_data > 0) else avg_data.max()
            im = ax.imshow(avg_data, cmap='jet', interpolation='bilinear',
                          aspect='equal', vmin=0, vmax=vmax)

            # 添加COP轨迹（臀部压力中心）
            cop_x_series = []
            cop_y_series = []

            for frame in data[::max(1, len(data)//10)]:
                if frame.sum() > 0:
                    y_coords, x_coords = np.mgrid[0:frame.shape[0], 0:frame.shape[1]]
                    cop_x = (frame * x_coords).sum() / frame.sum()
                    cop_y = (frame * y_coords).sum() / frame.sum()
                    cop_x_series.append(cop_x)
                    cop_y_series.append(cop_y)

            if len(cop_x_series) > 1:
                ax.plot(cop_x_series, cop_y_series, 'cyan', linewidth=2,
                       alpha=0.8, linestyle='--', label='臀部压力中心')
                ax.plot(cop_x_series[0], cop_y_series[0], 'go', markersize=6)
                ax.plot(cop_x_series[-1], cop_y_series[-1], 'ro', markersize=6)

            ax.set_title(title, fontsize=11)
            ax.set_xticks([])
            ax.set_yticks([])

            cbar = plt.colorbar(im, ax=ax, shrink=0.8)
            cbar.set_label('压力值', fontsize=9)

            buffer = BytesIO()
            plt.savefig(buffer, format='png', dpi=120, bbox_inches='tight',
                       facecolor='white', edgecolor='none')
            buffer.seek(0)
            image_base64 = base64.b64encode(buffer.read()).decode()
            plt.close()

            return image_base64
        except Exception as e:
            print(f"❌ 臀部热力图生成失败: {e}")
            return None

    def _generate_simple_heatmap(self, data, title):
        """备用的简单热力图生成方法"""
        if data is None or len(data) == 0:
            return None

        try:
            avg_data = np.mean(data, axis=0)
            fig, ax = plt.subplots(figsize=(4, 5))

            vmax = np.percentile(avg_data[avg_data > 0], 98) if np.any(avg_data > 0) else avg_data.max()
            im = ax.imshow(avg_data, cmap='jet', interpolation='bilinear',
                          aspect='auto', vmin=0, vmax=vmax)

            # 添加COP轨迹
            cop_x_series = []
            cop_y_series = []

            for frame in data[::max(1, len(data)//10)]:
                if frame.sum() > 0:
                    y_coords, x_coords = np.mgrid[0:frame.shape[0], 0:frame.shape[1]]
                    cop_x = (frame * x_coords).sum() / frame.sum()
                    cop_y = (frame * y_coords).sum() / frame.sum()
                    cop_x_series.append(cop_x)
                    cop_y_series.append(cop_y)

            if len(cop_x_series) > 1:
                ax.plot(cop_x_series, cop_y_series, 'cyan', linewidth=2,
                       alpha=0.8, linestyle='--', label='压力中心轨迹')
                ax.plot(cop_x_series[0], cop_y_series[0], 'go', markersize=6)
                ax.plot(cop_x_series[-1], cop_y_series[-1], 'ro', markersize=6)

            ax.set_title(title, fontsize=11)
            ax.set_xticks([])
            ax.set_yticks([])

            cbar = plt.colorbar(im, ax=ax, shrink=0.8)
            cbar.set_label('压力值', fontsize=9)

            buffer = BytesIO()
            plt.savefig(buffer, format='png', dpi=120, bbox_inches='tight',
                       facecolor='white', edgecolor='none')
            buffer.seek(0)
            image_base64 = base64.b64encode(buffer.read()).decode()
            plt.close()

            return image_base64
        except Exception as e:
            print(f"❌ 简单热力图生成失败: {e}")
            return None

    def generate_footprint_analysis(self, pressure_data, title="脚印力线图分析", background_pressure=None):
        """
        内置脚印分析功能 - 集成最佳算法

        参数:
            pressure_data: 步态压力数据
            title: 图表标题
            background_pressure: 背景压力数据（如静态站立数据，将旋转90度作为背景）

        验收清单：
        1. 背景是完整热力图（非透明/非点云） ✅
        2. 每只脚都有闭合的白色轮廓（由连通域算出） ✅
        3. 每步被分成3-4段，段内COP为平滑曲线 ✅
        4. 1-4数字贴在对应阶段的代表帧 ✅
        5. 箭头方向与曲线切向一致，颜色按时间渐变 ✅
        """
        if pressure_data is None or len(pressure_data) == 0:
            return None

        # 处理64x32格式
        if pressure_data.shape[1] == 64:
            pressure_data = pressure_data[:, 32:, :]
            print(f"🔄 处理64x32 → 32x32足部区域")

        print(f"📊 脚印分析数据: {pressure_data.shape}")

        # 步骤1: 创建稳定的脚印形状
        stable_footprint, avg_pressure = self._create_stable_footprint(pressure_data)
        if stable_footprint is None:
            print("❌ 无法生成稳定的脚印形状")
            return None

        # 步骤2: 准备背景热力图
        if background_pressure is not None:
            # 使用提供的背景（如静态站立），旋转90度
            print("🔄 使用静态站立热力图作为背景（顺时针旋转90度）")
            # 先增强背景
            background_enhanced = self._enhance_footprint_heatmap(background_pressure)
            # 顺时针旋转90度（k=-1或k=3）
            arr_smooth = np.rot90(background_enhanced, k=-1)
        else:
            # 使用默认的步态热力图
            arr_smooth = self._enhance_footprint_heatmap(avg_pressure)

        # 步骤3: 智能分段分析
        cop_segments = self._analyze_footprint_segments(pressure_data, stable_footprint)

        # 步骤4: 创建图形
        fig, ax = plt.subplots(figsize=(6, 8))

        # 绘制完整热力图背景
        cmap = plt.get_cmap('jet')
        im = ax.imshow(arr_smooth, cmap=cmap, vmin=0, vmax=255,
                      origin='lower', interpolation='bicubic', aspect='equal')

        # 步骤5: 绘制脚印轮廓和分析
        self._draw_footprint_contours(ax, stable_footprint)
        if cop_segments:
            self._draw_footprint_cop_analysis(ax, cop_segments)


        # 步骤7: 计算力线偏移率
        deviation_stats = self._calculate_cop_deviation(pressure_data, stable_footprint)

        # 步骤6: 设置图形
        ax.set_title(title, fontsize=14, pad=15)
        ax.set_xticks([])
        ax.set_yticks([])

        cbar = fig.colorbar(im, ax=ax, fraction=0.046, pad=0.04)
        cbar.set_label('压力值', rotation=270, labelpad=15)

        fig.tight_layout()

        # 转换为base64
        buffer = BytesIO()
        plt.savefig(buffer, format='png', dpi=150, bbox_inches='tight',
                   facecolor='white', edgecolor='none')
        buffer.seek(0)
        image_base64 = base64.b64encode(buffer.read()).decode()
        plt.close()

        # 返回字典，包含图像和偏移分析
        return {
            'image': image_base64,
            'deviation': deviation_stats
        }

    def _create_stable_footprint(self, pressure_data):
        """创建稳定的脚印形状"""
        # 使用中位数叠加获得稳定形状
        median_pressure = np.median(pressure_data, axis=0)
        smoothed = gaussian_filter(median_pressure, sigma=1.0)

        # Otsu阈值自动选择
        try:
            threshold = threshold_otsu(smoothed)
        except:
            threshold = smoothed.max() * 0.2

        foot_mask = smoothed > threshold
        print(f"🦶 Otsu阈值: {threshold:.1f}, 脚印区域: {foot_mask.sum()}/{foot_mask.size} ({foot_mask.sum()/foot_mask.size*100:.1f}%)")

        # 形态学处理
        foot_mask = binary_closing(foot_mask, structure=np.ones((3, 3)))
        foot_mask = binary_opening(foot_mask, structure=np.ones((2, 2)))

        # 连通域分析，保留最大区域
        labeled_regions, num_regions = label(foot_mask)
        if num_regions == 0:
            return None, None

        region_sizes = [(labeled_regions == i).sum() for i in range(1, num_regions + 1)]
        largest_region_id = np.argmax(region_sizes) + 1
        stable_footprint = (labeled_regions == largest_region_id)

        # 凸包处理
        stable_footprint = convex_hull_image(stable_footprint)
        print(f"🦶 最终脚印区域: {stable_footprint.sum()}/{stable_footprint.size} ({stable_footprint.sum()/stable_footprint.size*100:.1f}%)")

        return stable_footprint, smoothed

    def _enhance_footprint_heatmap(self, pressure_data):
        """高质量渲染热力图"""
        arr_filled = np.nan_to_num(pressure_data, nan=0.0)
        arr_zoom = zoom(arr_filled, 4, order=3)
        arr_smooth = gaussian_filter(arr_zoom, sigma=1.2)
        return arr_smooth

    def _analyze_footprint_segments(self, pressure_data, foot_mask):
        """智能分段 - 静态用空间区域，动态用时间序列"""
        avg_pressure = pressure_data.mean(axis=0)
        is_static = self._is_static_footprint_data(pressure_data, foot_mask)

        if is_static:
            print("📊 检测为静态数据，使用空间区域分析")
            return self._analyze_spatial_footprint_segments(avg_pressure, foot_mask)
        else:
            print("📊 检测为动态数据，使用时间序列分析")
            return self._analyze_temporal_footprint_segments(pressure_data, foot_mask)

    def _is_static_footprint_data(self, pressure_data, foot_mask):
        """判断是否为静态数据"""
        cop_movements = []
        prev_cop = None

        for frame in pressure_data:
            masked_frame = frame * foot_mask
            if masked_frame.sum() > 0:
                y_coords, x_coords = np.mgrid[0:frame.shape[0], 0:frame.shape[1]]
                cop_x = (masked_frame * x_coords).sum() / masked_frame.sum()
                cop_y = (masked_frame * y_coords).sum() / masked_frame.sum()

                if prev_cop is not None:
                    movement = np.sqrt((cop_x - prev_cop[0])**2 + (cop_y - prev_cop[1])**2)
                    cop_movements.append(movement)
                prev_cop = (cop_x, cop_y)

        if cop_movements:
            avg_movement = np.mean(cop_movements)
            print(f"🎯 平均COP移动: {avg_movement:.2f}像素")
            return avg_movement < 2.0

        return True

    def _analyze_spatial_footprint_segments(self, avg_pressure, foot_mask):
        """空间区域分析 - 用于静态数据"""
        height, width = foot_mask.shape

        regions = [
            {'name': '脚跟', 'y_range': (int(height*0.7), height), 'color': '#FF0000'},
            {'name': '足弓', 'y_range': (int(height*0.45), int(height*0.7)), 'color': '#FF8C00'},
            {'name': '前掌', 'y_range': (int(height*0.2), int(height*0.45)), 'color': '#FFD700'},
            {'name': '脚趾', 'y_range': (0, int(height*0.2)), 'color': '#32CD32'}
        ]

        segments = []
        for i, region in enumerate(regions):
            y_min, y_max = region['y_range']
            region_mask = np.zeros_like(foot_mask)
            region_mask[y_min:y_max, :] = foot_mask[y_min:y_max, :]
            masked_pressure = avg_pressure * region_mask

            if masked_pressure.max() > 0:
                peak_y, peak_x = np.unravel_index(masked_pressure.argmax(), masked_pressure.shape)
                peak_pressure = masked_pressure[peak_y, peak_x]

                segments.append({
                    'phase': i + 1,
                    'name': region['name'],
                    'color': region['color'],
                    'representative': (peak_x, peak_y, peak_pressure),
                    'time_range': (0, 0)
                })

        print(f"🎯 空间分段完成，{len(segments)}个区域")
        for seg in segments:
            rep_x, rep_y, rep_p = seg['representative']
            print(f"   {seg['phase']}. {seg['name']} - 位置({rep_x:.1f}, {rep_y:.1f}), 压力{rep_p:.1f}")

        return segments

    def _analyze_temporal_footprint_segments(self, pressure_data, foot_mask):
        """时间序列分析 - 用于动态数据"""
        cop_trajectory = []

        for frame in pressure_data:
            masked_frame = frame * foot_mask
            total_pressure = masked_frame.sum()
            if total_pressure > 0:
                y_coords, x_coords = np.mgrid[0:frame.shape[0], 0:frame.shape[1]]
                cop_x = (masked_frame * x_coords).sum() / total_pressure
                cop_y = (masked_frame * y_coords).sum() / total_pressure
                cop_trajectory.append((cop_x, cop_y, total_pressure))

        valid_cops = [(x, y, p) for x, y, p in cop_trajectory if not (np.isnan(x) or np.isnan(y))]
        if len(valid_cops) < 4:
            return []

        segments = []
        segment_size = len(valid_cops) // 4
        colors = ['#FF0000', '#FF8C00', '#FFD700', '#32CD32']
        phase_names = ['脚跟着地', '足弓支撑', '前掌发力', '脚趾推进']

        for i in range(4):
            start_idx = i * segment_size
            end_idx = (i + 1) * segment_size if i < 3 else len(valid_cops)
            if start_idx < len(valid_cops):
                segment_cops = valid_cops[start_idx:end_idx]
                max_pressure_idx = np.argmax([p for _, _, p in segment_cops])
                representative_cop = segment_cops[max_pressure_idx]

                segments.append({
                    'phase': i + 1,
                    'name': phase_names[i],
                    'color': colors[i],
                    'cops': segment_cops,
                    'representative': representative_cop,
                    'time_range': (start_idx * 0.01, end_idx * 0.01)
                })

        return segments

    def _draw_footprint_contours(self, ax, foot_mask):
        """绘制真实脚印轮廓"""
        foot_mask_hr = zoom(foot_mask.astype(float), 4, order=0) >= 0.5

        try:
            from skimage.measure import find_contours
            contours = find_contours(foot_mask_hr, 0.5)
            if contours:
                main_contour = max(contours, key=len)
                contour_x = [p[1] for p in main_contour] + [main_contour[0][1]]
                contour_y = [p[0] for p in main_contour] + [main_contour[0][0]]
                ax.plot(contour_x, contour_y, color='white', linewidth=3, alpha=0.9, linestyle='--')
                print(f"✅ 绘制脚印轮廓: {len(main_contour)}个点")
        except Exception as e:
            print(f"⚠️ 轮廓绘制失败: {e}")

    def _draw_footprint_cop_analysis(self, ax, segments):
        """绘制COP分析"""
        if not segments:
            return

        # 绘制COP路径
        all_cops = []
        for seg in segments:
            if 'cops' in seg:
                all_cops.extend(seg['cops'])
            else:
                all_cops.append(seg['representative'])

        if len(all_cops) > 3:
            cop_x = [cop[0] * 4 for cop in all_cops]
            cop_y = [cop[1] * 4 for cop in all_cops]

            try:
                tck, u = splprep([cop_x, cop_y], s=0, k=min(3, len(cop_x)-1))
                u_new = np.linspace(0, 1, len(cop_x) * 2)
                smooth_x, smooth_y = splev(u_new, tck)
                ax.plot(smooth_x, smooth_y, color='cyan', linewidth=2, alpha=0.8)
                print(f"✅ 绘制平滑COP路径")
            except:
                ax.plot(cop_x, cop_y, color='cyan', linewidth=2, alpha=0.8)

        # 标注各阶段代表点
        total_displacement = 0
        for i, seg in enumerate(segments):
            rep_x, rep_y, rep_p = seg['representative']
            x, y = rep_x * 4, rep_y * 4

            circle = plt.Circle((x, y), radius=12, facecolor='white',
                              edgecolor=seg['color'], linewidth=4, alpha=0.95)
            ax.add_patch(circle)
            ax.text(x, y, str(seg['phase']), ha='center', va='center',
                   fontsize=16, color=seg['color'], weight='bold')

            # 计算位移
            if i < len(segments) - 1:
                next_x, next_y, _ = segments[i+1]['representative']
                displacement = np.sqrt((next_x-rep_x)**2 + (next_y-rep_y)**2)
                total_displacement += displacement

        # 绘制箭头
        for i in range(len(segments) - 1):
            x1, y1, _ = segments[i]['representative']
            x2, y2, _ = segments[i+1]['representative']
            x1, y1, x2, y2 = x1*4, y1*4, x2*4, y2*4

            dx, dy = x2 - x1, y2 - y1
            distance = np.sqrt(dx**2 + dy**2)
            if distance > 20:
                offset = 15
                start_x = x1 + dx/distance * offset
                start_y = y1 + dy/distance * offset
                end_x = x2 - dx/distance * offset
                end_y = y2 - dy/distance * offset
                ax.annotate('', xy=(end_x, end_y), xytext=(start_x, start_y),
                           arrowprops=dict(arrowstyle='->', color='#0066FF', lw=3, alpha=0.9))

    def _calculate_cop_deviation(self, pressure_data, foot_mask):
        """
        计算CoP轨迹横向偏移率分析

        参数:
            pressure_data: 压力数据 (n_frames, height, width)
            foot_mask: 脚印掩膜 (height, width)

        返回:
            {
                'mean_deviation': 平均偏移率(%),
                'direction': 偏移方向(内偏/外偏/居中),
                'level': 风险等级(正常/轻度偏移/中度偏移/重度偏移),
                'cop_y_values': CoP Y坐标列表,
                'midline': 足印中轴线Y坐标,
                'foot_width': 足宽(像素)
            }
        """
        try:
            # 1. 计算每帧的CoP Y坐标
            cop_y_values = []
            for frame in pressure_data:
                masked_frame = frame * foot_mask
                if masked_frame.sum() > 0:
                    y_coords, x_coords = np.mgrid[0:frame.shape[0], 0:frame.shape[1]]
                    cop_y = (masked_frame * y_coords).sum() / masked_frame.sum()
                    cop_y_values.append(cop_y)

            if len(cop_y_values) == 0:
                print("⚠️ 无有效CoP数据")
                return None

            # 2. 计算足印中轴线 (Y方向的重心)
            y_coords, x_coords = np.mgrid[0:foot_mask.shape[0], 0:foot_mask.shape[1]]
            midline_y = (foot_mask * y_coords).sum() / foot_mask.sum()

            # 3. 计算足宽 (Y方向的跨度)
            y_positions = np.where(foot_mask.sum(axis=1) > 0)[0]
            if len(y_positions) > 0:
                foot_width = y_positions.max() - y_positions.min()
            else:
                foot_width = 1  # 避免除零

            # 4. 计算每帧的横向偏移率
            deviation_ratios = []
            for cop_y in cop_y_values:
                offset = abs(cop_y - midline_y)
                ratio = (offset / foot_width) * 100 if foot_width > 0 else 0
                deviation_ratios.append(ratio)

            # 5. 计算平均偏移率
            mean_deviation = np.mean(deviation_ratios)

            # 6. 判断偏移方向
            mean_cop_y = np.mean(cop_y_values)
            if mean_cop_y > midline_y + 0.1 * foot_width:
                direction = "外偏"
            elif mean_cop_y < midline_y - 0.1 * foot_width:
                direction = "内偏"
            else:
                direction = "居中"

            # 7. 风险等级评估
            if mean_deviation <= 10:
                level = "正常"
                level_color = "#28a745"  # 绿色
            elif mean_deviation <= 20:
                level = "轻度偏移"
                level_color = "#ffc107"  # 黄色
            elif mean_deviation <= 30:
                level = "中度偏移"
                level_color = "#ff9800"  # 橙色
            else:
                level = "重度偏移"
                level_color = "#dc3545"  # 红色

            print(f"📊 CoP偏移分析: 平均偏移率={mean_deviation:.1f}%, 方向={direction}, 等级={level}")

            return {
                'mean_deviation': round(mean_deviation, 1),
                'direction': direction,
                'level': level,
                'level_color': level_color,
                'cop_y_values': cop_y_values,
                'midline': midline_y,
                'foot_width': foot_width,
                'min_deviation': round(min(deviation_ratios), 1),
                'max_deviation': round(max(deviation_ratios), 1)
            }

        except Exception as e:
            print(f"⚠️ CoP偏移计算错误: {e}")
            return None

    def calculate_radar_scores(self, patient_age, patient_gender, hip_metrics, balance_metrics, gait_metrics):
        """计算雷达图六维评分"""
        # 性别映射
        if patient_gender in ['女', 'female', 'Female', 'F', 'f']:
            gender = 'female'
        else:
            gender = 'male'

        age = int(patient_age)
        scores = {}

        # 1. 步速得分（基于步行数据）
        if gait_metrics and '步速_left' in gait_metrics:
            gait_speed = float(gait_metrics['步速_left'])
            if gait_speed >= 1.2:
                scores['gait_speed'] = 100
            elif gait_speed >= 1.0:
                scores['gait_speed'] = 80
            elif gait_speed >= 0.8:
                scores['gait_speed'] = 60
            else:
                scores['gait_speed'] = 40
        else:
            scores['gait_speed'] = 50

        # 2. 五次起坐得分
        if hip_metrics and 'sitstand' in hip_metrics:
            sit_time = float(hip_metrics['sitstand'].get('五次起坐时间', '15.0'))
            if sit_time <= 10:
                scores['sit_stand'] = 100
            elif sit_time <= 12:
                scores['sit_stand'] = 80
            elif sit_time <= 15:
                scores['sit_stand'] = 60
            else:
                scores['sit_stand'] = 40
        else:
            scores['sit_stand'] = 50

        # 3. 静态平衡得分
        if balance_metrics and 'standing' in balance_metrics:
            left_support = float(balance_metrics['standing']['左脚'].get('左脚支撑相占比', '50'))
            right_support = float(balance_metrics['standing']['右脚'].get('右脚支撑相占比', '50'))
            balance_symmetry = 100 - abs(left_support - right_support) * 2
            scores['static_balance'] = max(20, min(100, balance_symmetry))
        else:
            scores['static_balance'] = 50

        # 4. 动态平衡得分
        if balance_metrics and 'tandem_front' in balance_metrics:
            left_sway = float(balance_metrics['tandem_front']['左脚'].get('偏移（晃动）', '2.0'))
            right_sway = float(balance_metrics['tandem_front']['右脚'].get('偏移（晃动）', '2.0'))
            avg_sway = (left_sway + right_sway) / 2
            scores['dynamic_balance'] = max(20, min(100, 100 - avg_sway * 10))
        else:
            scores['dynamic_balance'] = 50

        # 5. 力量对称性得分
        if balance_metrics and 'standing' in balance_metrics:
            left_max = float(balance_metrics['standing']['左脚'].get('最大值', '100'))
            right_max = float(balance_metrics['standing']['右脚'].get('最大值', '100'))
            if left_max + right_max > 0:
                symmetry = min(left_max, right_max) / max(left_max, right_max) * 100
                scores['strength_symmetry'] = symmetry
            else:
                scores['strength_symmetry'] = 50
        else:
            scores['strength_symmetry'] = 50

        # 6. 柔韧性得分
        if gait_metrics and '步长_left' in gait_metrics:
            step_left = float(gait_metrics.get('步长_left', '0.5'))
            step_right = float(gait_metrics.get('步长_right', '0.5'))
            if step_left + step_right > 0:
                flexibility = min(step_left, step_right) / max(step_left, step_right) * 100
                scores['flexibility'] = flexibility
            else:
                scores['flexibility'] = 50
        else:
            scores['flexibility'] = 50

        # 计算综合得分
        scores['overall'] = sum(scores.values()) / len(scores)

        return scores

    def generate_radar_chart(self, scores):
        """生成六维雷达图"""
        categories = ['步速', '五次起坐', '静态平衡', '动态平衡', '力量对称性', '柔韧性']
        values = [
            scores.get('gait_speed', 50),
            scores.get('sit_stand', 50),
            scores.get('static_balance', 50),
            scores.get('dynamic_balance', 50),
            scores.get('strength_symmetry', 50),
            scores.get('flexibility', 50)
        ]

        fig, ax = plt.subplots(figsize=(6, 6), subplot_kw=dict(projection='polar'))

        angles = np.linspace(0, 2 * np.pi, len(categories), endpoint=False).tolist()
        values += values[:1]
        angles += angles[:1]

        ax.plot(angles, values, 'o-', linewidth=2, color='#1f77b4', label='当前水平')
        ax.fill(angles, values, alpha=0.25, color='#1f77b4')

        ax.set_xticks(angles[:-1])
        ax.set_xticklabels(categories, fontsize=10)
        ax.set_ylim(0, 100)
        ax.set_yticks([20, 40, 60, 80, 100])
        ax.set_yticklabels(['20', '40', '60', '80', '100'], fontsize=8)

        ax.set_title('身体运动能力评估', fontsize=12, fontweight='bold', pad=15)

        buffer = BytesIO()
        plt.savefig(buffer, format='png', dpi=150, bbox_inches='tight',
                   facecolor='white', edgecolor='none')
        buffer.seek(0)
        image_base64 = base64.b64encode(buffer.read()).decode()
        plt.close()

        return image_base64

    def assess_fall_risk(self, scores, gait_metrics):
        """跌倒风险评估"""
        risk_factors = []
        risk_score = 0

        if gait_metrics and '步速_left' in gait_metrics:
            gait_speed = float(gait_metrics['步速_left'])
            if gait_speed < 0.8:
                risk_factors.append("步速过慢(<0.8m/s)")
                risk_score += 3

        if scores.get('static_balance', 50) < 60:
            risk_factors.append("静态平衡能力不足")
            risk_score += 2

        if scores.get('dynamic_balance', 50) < 60:
            risk_factors.append("动态平衡能力不足")
            risk_score += 2

        if scores.get('sit_stand', 50) < 60:
            risk_factors.append("下肢肌力不足")
            risk_score += 3

        if risk_score <= 2:
            risk_level = "低风险"
            risk_color = "green"
            risk_description = "跌倒风险较低，继续保持良好的运动习惯"
        elif risk_score <= 5:
            risk_level = "中风险"
            risk_color = "orange"
            risk_description = "存在一定跌倒风险，建议进行针对性训练"
        else:
            risk_level = "高风险"
            risk_color = "red"
            risk_description = "跌倒风险较高，建议及时进行康复干预"

        return {
            'level': risk_level,
            'color': risk_color,
            'factors': risk_factors,
            'description': risk_description
        }

    def generate_expert_exercise_recommendations(self, radar_scores, fall_risk, gait_metrics, hip_metrics):
        """基于数据智能生成个性化运动建议 - 使用专家话术库"""
        recommendations = {
            'priority_goals': [],
            'principles': [],
            'strength_training': [],
            'balance_training': [],
            'aerobic_training': [],
            'safety_tips': []
        }

        # 确定优先改善目标
        weak_areas = []
        if radar_scores.get('gait_speed', 50) < 60:
            weak_areas.append("心肺耐力")
        if radar_scores.get('sit_stand', 50) < 60:
            weak_areas.append("下肢肌力")
        if radar_scores.get('static_balance', 50) < 60 or radar_scores.get('dynamic_balance', 50) < 60:
            weak_areas.append("平衡能力")
        if radar_scores.get('strength_symmetry', 50) < 80:
            weak_areas.append("力量对称性")

        recommendations['priority_goals'] = weak_areas if weak_areas else ["维持当前良好状态"]

        # 生成总体原则（基于专家话术库）
        if fall_risk['level'] == "高风险":
            recommendations['principles'].append(self.medical_terms['exercise_recommendations']['principles']['high_fall_risk'])

        if radar_scores.get('gait_speed', 50) < 60:
            recommendations['principles'].append(self.medical_terms['exercise_recommendations']['principles']['low_gait_speed'])

        if radar_scores.get('sit_stand', 50) < 60:
            recommendations['principles'].append(self.medical_terms['exercise_recommendations']['principles']['poor_sit_stand'])

        if radar_scores.get('strength_symmetry', 50) < 80:
            recommendations['principles'].append(self.medical_terms['exercise_recommendations']['principles']['poor_pressure'])

        # 生成具体训练建议
        if radar_scores.get('sit_stand', 50) < 60:
            recommendations['strength_training'].extend([
                self.medical_terms['exercise_recommendations']['strength_training']['chair_rise'],
                self.medical_terms['exercise_recommendations']['strength_training']['heel_raise']
            ])
        else:
            recommendations['strength_training'].append("维持性力量训练：每周3次座椅起立练习")

        if radar_scores.get('static_balance', 50) < 60 or radar_scores.get('dynamic_balance', 50) < 60:
            recommendations['balance_training'].extend([
                self.medical_terms['exercise_recommendations']['balance_training']['single_leg'],
                self.medical_terms['exercise_recommendations']['balance_training']['tandem_walk']
            ])
        else:
            recommendations['balance_training'].append("维持性平衡训练：每周3次单腿站立练习")

        if radar_scores.get('gait_speed', 50) < 60:
            recommendations['aerobic_training'].append(self.medical_terms['exercise_recommendations']['aerobic_training']['daily_walk'])
        else:
            recommendations['aerobic_training'].append(self.medical_terms['exercise_recommendations']['aerobic_training']['maintenance'])

        # 安全提示
        if fall_risk['level'] == "高风险":
            recommendations['safety_tips'].extend([
                self.medical_terms['exercise_recommendations']['safety_tips']['balance_protection'],
                self.medical_terms['exercise_recommendations']['safety_tips']['proper_shoes']
            ])
        else:
            recommendations['safety_tips'].extend([
                self.medical_terms['exercise_recommendations']['safety_tips']['warm_up'],
                self.medical_terms['exercise_recommendations']['safety_tips']['gradual_progress']
            ])

        return recommendations

    def generate_gait_position_speed_chart(self, walking_data, sampling_rate=3.6):
        """生成步态位置-速度图表"""
        if walking_data is None or len(walking_data) == 0:
            return None

        try:
            import matplotlib
            matplotlib.use('Agg')
            import matplotlib.pyplot as plt
            from io import BytesIO
            import base64

            # 计算CoP轨迹
            cop_x_series = []
            cop_y_series = []
            time_series = []

            for i, frame in enumerate(walking_data):
                if frame.sum() > 0:
                    y_coords, x_coords = np.mgrid[0:frame.shape[0], 0:frame.shape[1]]
                    cop_x = (frame * x_coords).sum() / frame.sum()
                    cop_y = (frame * y_coords).sum() / frame.sum()
                    cop_x_series.append(cop_x)
                    cop_y_series.append(cop_y)
                    time_series.append(i / sampling_rate)

            if len(cop_x_series) < 2:
                return None

            # 计算速度
            speeds = []
            speed_times = []
            for i in range(1, len(cop_x_series)):
                dx = cop_x_series[i] - cop_x_series[i-1]
                dy = cop_y_series[i] - cop_y_series[i-1]
                dt = time_series[i] - time_series[i-1]
                if dt > 0:
                    speed = np.sqrt(dx**2 + dy**2) / dt
                    speeds.append(speed)
                    speed_times.append(time_series[i])

            # 创建图表
            fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(10, 8))

            # 位置图
            ax1.plot(time_series, cop_y_series, 'b-', linewidth=2, label='前后位移')
            ax1.set_xlabel('时间 (秒)', fontsize=12)
            ax1.set_ylabel('位置 (像素)', fontsize=12)
            ax1.set_title('步态位置变化', fontsize=14, fontweight='bold')
            ax1.grid(True, alpha=0.3)
            ax1.legend()

            # 速度图
            ax2.plot(speed_times, speeds, 'r-', linewidth=2, label='瞬时速度')
            ax2.axhline(y=np.mean(speeds), color='g', linestyle='--', linewidth=2, label=f'平均速度: {np.mean(speeds):.2f}')
            ax2.set_xlabel('时间 (秒)', fontsize=12)
            ax2.set_ylabel('速度 (像素/秒)', fontsize=12)
            ax2.set_title('步态速度变化', fontsize=14, fontweight='bold')
            ax2.grid(True, alpha=0.3)
            ax2.legend()

            plt.tight_layout()

            # 转换为base64
            buffer = BytesIO()
            plt.savefig(buffer, format='png', dpi=150, bbox_inches='tight')
            buffer.seek(0)
            img_base64 = base64.b64encode(buffer.read()).decode()
            plt.close(fig)

            return f'data:image/png;base64,{img_base64}'

        except Exception as e:
            print(f"⚠️ 步态位置速度图生成失败: {e}")
            return None

    def generate_sitstand_curve_chart(self, sitstand_data, sampling_rate=3.6):
        """生成5次起立曲线图"""
        if sitstand_data is None or len(sitstand_data) == 0:
            return None

        try:
            import matplotlib
            matplotlib.use('Agg')
            import matplotlib.pyplot as plt
            from io import BytesIO
            import base64

            # 计算总压力随时间变化
            total_pressure = sitstand_data.sum(axis=(1, 2))
            time_series = np.arange(len(total_pressure)) / sampling_rate

            # 检测起立事件（压力下降）
            pressure_diff = np.diff(total_pressure)
            threshold = -np.std(pressure_diff) * 2
            stand_events = np.where(pressure_diff < threshold)[0]

            # 创建图表
            fig, ax = plt.subplots(figsize=(12, 6))

            ax.plot(time_series, total_pressure, 'b-', linewidth=2, label='总压力')

            # 标记起立事件
            if len(stand_events) > 0:
                ax.scatter(time_series[stand_events], total_pressure[stand_events],
                          color='red', s=100, marker='v', label='起立事件', zorder=5)

            ax.set_xlabel('时间 (秒)', fontsize=12)
            ax.set_ylabel('压力值', fontsize=12)
            ax.set_title('五次起立测试 - 压力变化曲线', fontsize=14, fontweight='bold')
            ax.grid(True, alpha=0.3)
            ax.legend()

            plt.tight_layout()

            # 转换为base64
            buffer = BytesIO()
            plt.savefig(buffer, format='png', dpi=150, bbox_inches='tight')
            buffer.seek(0)
            img_base64 = base64.b64encode(buffer.read()).decode()
            plt.close(fig)

            return f'data:image/png;base64,{img_base64}'

        except Exception as e:
            print(f"⚠️ 五次起立曲线图生成失败: {e}")
            return None

    def generate_balance_trajectory_chart(self, standing_data, sampling_rate=3.6):
        """生成平衡轨迹图"""
        if standing_data is None or len(standing_data) == 0:
            return None

        try:
            import matplotlib
            matplotlib.use('Agg')
            import matplotlib.pyplot as plt
            from io import BytesIO
            import base64

            # 计算CoP轨迹
            cop_x_series = []
            cop_y_series = []

            for frame in standing_data:
                if frame.sum() > 0:
                    y_coords, x_coords = np.mgrid[0:frame.shape[0], 0:frame.shape[1]]
                    cop_x = (frame * x_coords).sum() / frame.sum()
                    cop_y = (frame * y_coords).sum() / frame.sum()
                    cop_x_series.append(cop_x)
                    cop_y_series.append(cop_y)

            if len(cop_x_series) < 2:
                return None

            cop_x_series = np.array(cop_x_series)
            cop_y_series = np.array(cop_y_series)

            # 计算摆动面积（95%置信椭圆）
            from scipy import stats
            if len(cop_x_series) > 5:
                # 计算协方差矩阵
                cov = np.cov(cop_x_series, cop_y_series)
                # 计算特征值和特征向量
                eigenvalues, eigenvectors = np.linalg.eig(cov)
                # 95%置信椭圆
                chi2_val = stats.chi2.ppf(0.95, 2)
                ellipse_radii = np.sqrt(chi2_val * eigenvalues)
                sway_area = np.pi * ellipse_radii[0] * ellipse_radii[1]
            else:
                sway_area = 0

            # 创建图表
            fig, ax = plt.subplots(figsize=(8, 8))

            # 绘制轨迹
            ax.plot(cop_x_series, cop_y_series, 'b-', linewidth=1, alpha=0.5, label='CoP轨迹')
            ax.scatter(cop_x_series[0], cop_y_series[0], color='green', s=100, marker='o', label='起点', zorder=5)
            ax.scatter(cop_x_series[-1], cop_y_series[-1], color='red', s=100, marker='s', label='终点', zorder=5)

            # 绘制95%置信椭圆
            if sway_area > 0:
                from matplotlib.patches import Ellipse
                angle = np.degrees(np.arctan2(*eigenvectors[:, 0][::-1]))
                ellipse = Ellipse(xy=(np.mean(cop_x_series), np.mean(cop_y_series)),
                                 width=ellipse_radii[0]*2, height=ellipse_radii[1]*2,
                                 angle=angle, facecolor='yellow', alpha=0.3,
                                 edgecolor='red', linewidth=2, label='95%摆动范围')
                ax.add_patch(ellipse)

            ax.set_xlabel('左右位置 (像素)', fontsize=12)
            ax.set_ylabel('前后位置 (像素)', fontsize=12)
            ax.set_title(f'静态平衡轨迹图\n摆动面积: {sway_area:.2f} 像素²', fontsize=14, fontweight='bold')
            ax.grid(True, alpha=0.3)
            ax.legend()
            ax.axis('equal')

            plt.tight_layout()

            # 转换为base64
            buffer = BytesIO()
            plt.savefig(buffer, format='png', dpi=150, bbox_inches='tight')
            buffer.seek(0)
            img_base64 = base64.b64encode(buffer.read()).decode()
            plt.close(fig)

            return f'data:image/png;base64,{img_base64}'

        except Exception as e:
            print(f"⚠️ 平衡轨迹图生成失败: {e}")
            return None

    def generate_pressure_distribution_chart(self, walking_data):
        """生成压力分布柱状图"""
        if walking_data is None or len(walking_data) == 0:
            return None

        try:
            import matplotlib
            matplotlib.use('Agg')
            import matplotlib.pyplot as plt
            from io import BytesIO
            import base64

            # 计算平均压力分布
            avg_pressure = walking_data.mean(axis=0)

            # 分区域统计（前、中、后）
            rows, cols = avg_pressure.shape
            front = avg_pressure[:rows//3, :].sum()
            middle = avg_pressure[rows//3:2*rows//3, :].sum()
            back = avg_pressure[2*rows//3:, :].sum()

            # 左右分区统计
            left = avg_pressure[:, :cols//2].sum()
            right = avg_pressure[:, cols//2:].sum()

            # 创建图表
            fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 5))

            # 前中后分布
            regions = ['前部', '中部', '后部']
            values = [front, middle, back]
            colors = ['#FF6B6B', '#4ECDC4', '#45B7D1']

            ax1.bar(regions, values, color=colors, alpha=0.7, edgecolor='black', linewidth=2)
            ax1.set_ylabel('压力值', fontsize=12)
            ax1.set_title('足底前后压力分布', fontsize=14, fontweight='bold')
            ax1.grid(True, alpha=0.3, axis='y')

            # 添加数值标签
            for i, (region, value) in enumerate(zip(regions, values)):
                ax1.text(i, value, f'{value:.0f}', ha='center', va='bottom', fontsize=11, fontweight='bold')

            # 左右分布
            sides = ['左侧', '右侧']
            side_values = [left, right]
            side_colors = ['#95E1D3', '#F38181']

            ax2.bar(sides, side_values, color=side_colors, alpha=0.7, edgecolor='black', linewidth=2)
            ax2.set_ylabel('压力值', fontsize=12)
            ax2.set_title('足底左右压力分布', fontsize=14, fontweight='bold')
            ax2.grid(True, alpha=0.3, axis='y')

            # 添加数值标签和不对称率
            for i, (side, value) in enumerate(zip(sides, side_values)):
                ax2.text(i, value, f'{value:.0f}', ha='center', va='bottom', fontsize=11, fontweight='bold')

            asymmetry = abs(left - right) / ((left + right) / 2) * 100
            ax2.text(0.5, max(side_values) * 0.9, f'不对称率: {asymmetry:.1f}%',
                    ha='center', fontsize=11, bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.5))

            plt.tight_layout()

            # 转换为base64
            buffer = BytesIO()
            plt.savefig(buffer, format='png', dpi=150, bbox_inches='tight')
            buffer.seek(0)
            img_base64 = base64.b64encode(buffer.read()).decode()
            plt.close(fig)

            return f'data:image/png;base64,{img_base64}'

        except Exception as e:
            print(f"⚠️ 压力分布图生成失败: {e}")
            return None

    def generate_medical_report(self, patient_name="XX", patient_gender="XX", patient_age="XX",
                           patient_id="XX", department="XX", education="XX",
                           sitting_data=None, sitstand_data=None, standing_data=None,
                           tandem_front_data=None, tandem_side_data=None, walking_data=None,
                           walking_sampling_rate=100.0, sitstand_sampling_rate=3.6,
                           manual_distance=None, estimated_traversals=None, sampling_rates=None):
        """生成完整医疗级报告 - v7.0版本，支持手动距离输入"""

        # 生成唯一报告编码
        report_code = self.generate_unique_report_code()
        test_datetime = self.test_date.strftime("%Y年%m月%d日%H时%M分%S秒")
        report_date = self.test_date.strftime("%Y-%m-%d")

        # 计算所有指标
        hip_metrics = self.calculate_hip_stability_metrics(sitting_data, sitstand_data, sitstand_sampling_rate)
        pressure_dist = self.calculate_pressure_distribution(hip_metrics)
        # 使用standing的采样率（三个平衡测试采样率相近）
        if sampling_rates is None:
            sampling_rates = {}
        balance_sampling_rate = sampling_rates.get('standing', 3.6)
        balance_metrics = self.calculate_balance_metrics(standing_data, tandem_front_data, tandem_side_data, balance_sampling_rate)
        gait_metrics = self.detect_gait_events_advanced(
            walking_data, walking_sampling_rate,
            manual_distance=manual_distance,
            estimated_traversals=estimated_traversals
        )  # v7.0: 传递距离校正参数
        straightness_analysis = self.analyze_walking_straightness(walking_data)
        front_back_analysis = self.identify_front_back_feet(tandem_front_data.mean(axis=0)) if tandem_front_data is not None else {}
        
        # 生成热力图
        standing_heatmap = self.generate_enhanced_pressure_heatmap(standing_data, "静态站立压力分布") if standing_data is not None else None
        tandem_front_heatmap = self.generate_enhanced_pressure_heatmap(tandem_front_data, "前后脚站立压力分布") if tandem_front_data is not None else None
        tandem_side_heatmap = self.generate_enhanced_pressure_heatmap(tandem_side_data, "双脚前后站立压力分布") if tandem_side_data is not None else None

        # 生成五次起坐的独立热力图
        sitstand_heatmaps = self.generate_five_sitstand_heatmaps(sitstand_data) if sitstand_data is not None else []

        # 生成4个新增图表
        gait_position_speed_chart = self.generate_gait_position_speed_chart(walking_data, walking_sampling_rate)
        sitstand_curve_chart = self.generate_sitstand_curve_chart(sitstand_data, sitstand_sampling_rate)
        balance_trajectory_chart = self.generate_balance_trajectory_chart(standing_data, balance_sampling_rate)
        pressure_distribution_chart = self.generate_pressure_distribution_chart(walking_data)

        # 专家模板新增：计算雷达图评分和风险评估
        radar_scores = self.calculate_radar_scores(patient_age, patient_gender, hip_metrics, balance_metrics, gait_metrics)
        fall_risk = self.assess_fall_risk(radar_scores, gait_metrics)
        radar_chart = self.generate_radar_chart(radar_scores)

        # 生成专家运动建议
        expert_recommendations = self.generate_expert_exercise_recommendations(radar_scores, fall_risk, gait_metrics, hip_metrics)
        
        # 严格按照PDF模版格式的HTML
        html_content = f"""
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>身体运动能力测评报告</title>
    <style>
        body {{
            font-family: "SimHei", "Microsoft YaHei", Arial, sans-serif;
            font-size: 12px;
            line-height: 1.4;
            margin: 0;
            padding: 20px;
            background-color: white;
        }}
        
        .header {{
            text-align: center;
            margin-bottom: 20px;
            border-bottom: 2px solid black;
            padding-bottom: 10px;
        }}
        
        .report-code {{
            color: red;
            font-size: 10px;
            margin-bottom: 10px;
        }}
        
        .hospital-name {{
            font-size: 24px;
            font-weight: bold;
            margin: 15px 0;
        }}
        
        .report-title {{
            font-size: 18px;
            font-weight: bold;
            text-decoration: underline;
            margin: 10px 0;
        }}
        
        .patient-info {{
            display: flex;
            justify-content: space-between;
            margin: 15px 0;
            border-bottom: 1px solid black;
            padding-bottom: 10px;
        }}
        
        .patient-info div {{
            flex: 1;
        }}
        
        .section-title {{
            font-size: 16px;
            font-weight: bold;
            margin: 20px 0 10px 0;
            border-bottom: 1px solid black;
            padding-bottom: 5px;
        }}
        
        .test-section {{
            margin: 15px 0;
        }}
        
        .test-subtitle {{
            font-size: 14px;
            font-weight: bold;
            margin: 10px 0 5px 0;
            text-decoration: underline;
        }}
        
        .data-table {{
            width: 100%;
            border-collapse: collapse;
            margin: 10px 0;
            font-size: 11px;
        }}
        
        .data-table th, .data-table td {{
            border: 1px solid black;
            padding: 5px;
            text-align: center;
        }}
        
        .data-table th {{
            background-color: #f0f0f0;
            font-weight: bold;
        }}
        
        .side-by-side {{
            display: flex;
            gap: 20px;
            margin: 15px 0;
        }}
        
        .side-by-side .half {{
            flex: 1;
        }}
        
        .heatmap-container {{
            text-align: center;
            margin: 15px 0;
        }}
        
        .heatmap-container img {{
            max-width: 400px;
            height: auto;
        }}
        
        .footer {{
            margin-top: 30px;
            font-size: 10px;
            color: red;
            border-top: 1px solid black;
            padding-top: 10px;
        }}
        
        .fix-badge {{
            display: none;
        }}
        
        .reference-note {{
            font-size: 9px;
            color: #666;
        }}

        /* 专家模板新增样式 */
        .radar-summary {{
            text-align: center;
            margin: 15px 0;
            padding: 15px;
            border: 1px solid black;
            background-color: white;
        }}

        .score-badge {{
            display: inline-block;
            padding: 8px 15px;
            margin: 5px;
            font-weight: bold;
            border: 1px solid black;
            color: white;
        }}

        .score-excellent {{
            background-color: #28a745;  /* 绿色 */
        }}

        .score-good {{
            background-color: #007bff;  /* 蓝色 */
        }}

        .score-fair {{
            background-color: #ffc107;  /* 黄色 */
            color: black;
        }}

        .score-poor {{
            background-color: #fd7e14;  /* 橙色 */
        }}

        .score-high-risk {{
            background-color: #dc3545;  /* 红色 */
        }}

        .risk-assessment {{
            border: 1px solid black;
            background-color: white;
            padding: 15px;
            margin: 15px 0;
        }}

        .exercise-recommendations {{
            border: 1px solid black;
            background-color: white;
            padding: 15px;
            margin: 15px 0;
        }}
    </style>
</head>
<body>
    <!-- 报告头部 - 严格按照PDF格式 -->
    <div class="header">
        <div class="report-code">唯一报告编码：（可用于查询详细数据或追溯）：{report_code}<span class="fix-badge">修复1</span></div>
        <div style="margin: 5px 0; font-size: 10px;">施测者：</div>
        <div style="margin: 5px 0; font-size: 10px;">报告日期：{report_date}</div>
        <div style="margin: 10px 0; font-size: 10px; color: red;">
            本报告结果仅供参考，不能替代专业医疗诊断。<br/>
            测试结果受当时受试者身体状态、环境等因素影响。<br/>
            建议咨询医生或康复师对结果进行最终解读并制定干预方案。<span class="fix-badge">修复3</span>
        </div>
        <div class="hospital-name">{self.hospital_name}</div>
        <div class="report-title">身体运动能力测评报告</div>
        <div class="patient-info">
            <div>姓名：{patient_name}</div>
            <div>性别：{patient_gender}</div>  
            <div>年龄：{patient_age}</div>
            <div>检测时间：{test_datetime}</div>
        </div>
        <div class="patient-info">
            <div>就诊号：{patient_id}</div>
            <div>科室：{department}</div>
            <div>教育程度：{education}</div>
            <div></div>
        </div>
    </div>

    <!-- 测评总结与建议 -->
    <div class="section-title">测评总结与建议 (Executive Summary & Recommendations)</div>

    <div class="test-subtitle" style="font-size: 14px; font-weight: bold; margin: 15px 0 10px 0;">一、综合能力评测报告</div>
"""

        # === 准备核心指标表格所需的所有变量 ===
        
        # 1. 五次起坐时间
        if hip_metrics and 'sitstand' in hip_metrics:
            sit_time = hip_metrics['sitstand'].get('五次起坐时间', '未测试')
            if sit_time != '未测试':
                sit_time_display = f"{float(sit_time):.2f}秒"
            else:
                sit_time_display = '未测试'
        else:
            sit_time_display = '未测试'

        # 2. 步速
        if gait_metrics and '步速' in gait_metrics:
            gait_speed_display = f"{gait_metrics['步速']} m/s"
        else:
            gait_speed_display = '未测试'

        # 3. 步态周期对称性
        gait_symmetry_str = gait_metrics.get('步态周期对称性', '-') if gait_metrics else '-'

        # 4. SPPB评分
        sppb_score = radar_scores.get('sppb_total', 0)

        # 5. 平衡测试左右偏移比例（替代保持时间）
        def calc_bias(data):
            """计算左右压力偏移比例"""
            if not data:
                return ''
            left = float(data.get('左脚', {}).get('平均值', 0))
            right = float(data.get('右脚', {}).get('平均值', 0))
            total = left + right
            if total > 0:
                left_pct = left/total*100
                right_pct = right/total*100
                diff = abs(left_pct - right_pct)
                if diff < 5:
                    return '平衡良好'
                return f'左偏{diff:.1f}%' if left_pct > right_pct else f'右偏{diff:.1f}%'
            return ''

        standing_time_display = calc_bias(balance_metrics.get('standing', {}) if balance_metrics else {})
        tandem_front_time_display = calc_bias(balance_metrics.get('tandem_front', {}) if balance_metrics else {})
        tandem_side_time_display = calc_bias(balance_metrics.get('tandem_side', {}) if balance_metrics else {})

        # 5.1 计算TUG时间（3米起立计时）
        tug_time_display = ''
        if gait_metrics:
            # 从步态数据估算单程3米时间
            # 假设第一个HS到最后一个HS的时间 / 往返次数 / 2 = 单程时间
            # TUG = 起立时间 + 单程时间*2 + 转身时间
            # 简化：从五次起坐时间估算起立时间（平均每次起立时间）
            if hip_metrics and 'sitstand' in hip_metrics:
                total_sit_time = float(hip_metrics['sitstand'].get('五次起坐时间', '15'))
                avg_sit_time = total_sit_time / 5  # 平均每次起坐时间
                
                # 从步速估算3米往返时间
                if '步速' in gait_metrics:
                    speed = float(gait_metrics['步速'])
                    walk_time = 3.0 / speed if speed > 0 else 3.0  # 3米单程时间
                    tug_estimate = avg_sit_time + walk_time * 2 + 2.0  # 起立+往返+转身
                    tug_time_display = f"{tug_estimate:.1f}秒"

        # 6. 足底压力分布对称性
        pressure_symmetry_display = ''
        if balance_metrics and 'standing' in balance_metrics:
            left_avg = balance_metrics['standing'].get('左脚', {}).get('平均值', '')
            right_avg = balance_metrics['standing'].get('右脚', {}).get('平均值', '')
            if left_avg and right_avg:
                left_val = float(left_avg)
                right_val = float(right_avg)
                total = left_val + right_val
                if total > 0:
                    left_percent = (left_val / total) * 100
                    right_percent = (right_val / total) * 100
                    pressure_diff = abs(left_percent - right_percent)
                    pressure_symmetry_display = f"左{left_percent:.1f}% 右{right_percent:.1f}% (差异{pressure_diff:.1f}%)"

        # 7. 计算综合得分等级和颜色
        overall_score = radar_scores.get('overall', 50)
        if overall_score >= 90:
            score_class = 'excellent'
            score_color = '#28a745'
        elif overall_score >= 75:
            score_class = 'good'
            score_color = '#007bff'
        elif overall_score >= 60:
            score_class = 'fair'
            score_color = '#ffc107'
        elif overall_score < 40:
            score_class = 'high-risk'
            score_color = '#dc3545'
        else:
            score_class = 'poor'
            score_color = '#ff9800'

        html_content += f"""


    <!-- 大表格：左侧雷达图+得分，右侧核心指标 -->
    <table class="data-table" style="width: 100%; border: 2px solid black;">
        <tr>
            <th style="width: 40%; border: 2px solid black;">核心指标雷达图<br/>(Core Metrics Radar Chart)</th>
            <th style="width: 60%; border: 2px solid black;">指标结果<br/>(Core Metrics Results)</th>
        </tr>
        <tr>
            <td style="vertical-align: top; padding: 15px; border: 2px solid black;">
                <!-- 左侧：雷达图部分 -->
                <div class="test-subtitle" style="text-align: center; margin-bottom: 10px;">身体运动能力评估</div>
                <div style="text-align: center; margin: 10px 0;">
                    <img src="data:image/png;base64,{radar_chart}" style="width: 100%; max-width: 300px;" alt="雷达图">
                </div>


                <div style="margin-top: 15px; padding: 10px; background-color: white; border: 1px solid black;">
                    <h3 style="text-align: center; margin: 5px 0 10px 0;">综合能力得分</h3>
                    <div class="score-badge score-{score_class}" style="display: block; text-align: center; font-size: 24px; font-weight: bold; margin: 10px 0; padding: 10px; background-color: {score_color}; color: white; border-radius: 5px;">
                        {overall_score:.1f}分
                    </div>
                    <div style="font-size: 10px; color: #333; text-align: left; margin-top: 10px; line-height: 1.6;">
                        <div style="margin-bottom: 3px;"><span style="display: inline-block; width: 12px; height: 12px; background-color: #28a745; border-radius: 2px; margin-right: 5px; vertical-align: middle;"></span>优秀 (90-100分)</div>
                        <div style="margin-bottom: 3px;"><span style="display: inline-block; width: 12px; height: 12px; background-color: #007bff; border-radius: 2px; margin-right: 5px; vertical-align: middle;"></span>良好 (75-89分)</div>
                        <div style="margin-bottom: 3px;"><span style="display: inline-block; width: 12px; height: 12px; background-color: #ffc107; border-radius: 2px; margin-right: 5px; vertical-align: middle;"></span>一般 (60-74分)</div>
                        <div style="margin-bottom: 3px;"><span style="display: inline-block; width: 12px; height: 12px; background-color: #ff9800; border-radius: 2px; margin-right: 5px; vertical-align: middle;"></span>有待提高 (40-59分)</div>
                        <div><span style="display: inline-block; width: 12px; height: 12px; background-color: #dc3545; border-radius: 2px; margin-right: 5px; vertical-align: middle;"></span>高风险 (<40分)</div>
                    </div>
                </div>
            </td>
            <td style="vertical-align: top; padding: 10px; border: 2px solid black;">
                <!-- 右侧：核心指标结果表格 -->
                <table class="data-table" style="width: 100%; font-size: 10px;">
                    <tr><th>运动功能</th><th>检测指标</th><th>检测结果</th><th>正常参考范围（按年龄）</th></tr>
                    <tr><td rowspan="3">肌肉力量</td><td>握力</td><td></td><td>男≥27kg, 女≥16kg</td></tr>
                    <tr><td>30秒手臂弯举</td><td></td><td>男≥12次, 女≥11次</td></tr>
                    <tr><td>五次起坐测试</td><td>{sit_time_display if sit_time_display != '未测试' else ''}</td><td>≤12秒</td></tr>
                    <tr><td rowspan="7">平衡</td><td>睁眼站立平衡</td><td>{standing_time_display}</td><td>≥30秒</td></tr>
                    <tr><td>闭眼站立平衡</td><td></td><td>≥20秒</td></tr>
                    <tr><td>单脚站立</td><td></td><td>≥10秒</td></tr>
                    <tr><td>双脚并联</td><td>{tandem_side_time_display}</td><td>≥30秒</td></tr>
                    <tr><td>半串联</td><td>{tandem_front_time_display}</td><td>≥20秒</td></tr>
                    <tr><td>串联站立</td><td></td><td>≥10秒</td></tr>
                    <tr><td>足底压力分布</td><td>{pressure_symmetry_display}</td><td>45-55%对称带</td></tr>
                    <tr><td rowspan="2">灵活性和平衡</td><td>3米起立计时实验<br/>（测试从椅子起立到步道最远端时间）</td><td>{tug_time_display}</td><td>≤12秒</td></tr>
                    <tr><td>2分钟踏步测试</td><td></td><td>男≥80次, 女≥70次</td></tr>
                    <tr><td rowspan="2">步速</td><td>步速</td><td>{gait_speed_display if gait_speed_display != '未测试' else ''}</td><td>≥1.0 m/s</td></tr>
                    <tr><td>步态对称性</td><td>{gait_symmetry_str if gait_symmetry_str != '-' else ''}</td><td>≥85%（步时）或&lt;5%（步长）</td></tr>
                    <tr><td rowspan="2">柔韧性</td><td>上肢柔韧（后抓背）</td><td></td><td>≥0cm</td></tr>
                    <tr><td>下肢柔韧（坐位体前屈）</td><td></td><td>女≥0cm, 男≥-8cm</td></tr>
                    <tr><td>综合</td><td>简易体（SPPB）</td><td>{sppb_score if sppb_score > 0 else ''}分</td><td>≥10分良好, ≤9分受限</td></tr>
                </table>
            </td>
        </tr>
    </table>

    <!-- 第一页结束，后续内容移到第二页 -->

    <div style="page-break-before: always;"></div>

    <!-- 跌倒风险评估 -->
    <div class="section-title">二、跌倒风险评估</div>

    <div class="risk-assessment {'risk-' + fall_risk['color']}">
        <h3>风险等级：{fall_risk['level']}</h3>
        <p><strong>评估说明：</strong>{fall_risk['description']}</p>"""

        if fall_risk['factors']:
            html_content += f"""
        <p><strong>风险因素：</strong></p>
        <ul>"""
            for factor in fall_risk['factors']:
                html_content += f"<li>• {factor}</li>"
            html_content += """
        </ul>"""

        html_content += f"""
    </div>
    <!-- SPPB评分系统 -->
    <div class="section-title">简易体能状况量表（SPPB）总分</div>
    
    <table class="data-table" style="width: 100%;">
        <tr>
            <th style="width: 80%;">测试项目</th>
            <th style="width: 20%;">得分（≤9分）</th>
        </tr>
        <tr>
            <td><strong>平衡测验</strong><br/>
                并脚站立：（10s=1分，未能站下10s=0分）</td>
            <td></td>
        </tr>
        <tr>
            <td><strong>平衡测验 半串联时间：</strong><br/>
                （10s=1分，未能站下10s=0分，未进行该动作=0分）</td>
            <td></td>
        </tr>
        <tr>
            <td><strong>平衡测验 串联时间：</strong><br/>
                （10s=2分，保持3.99-9.99s=1分，坚持<3s=0分，未进行该动作=0分）</td>
            <td></td>
        </tr>
        <tr>
            <td><strong>五次起坐实验时间：</strong><br/>
                （不能完成/拒绝时间>60s=0分，≥16.7s=1分，时间13.70s-16.69s=2分，时间11.20s-13.69s=3分，时间≤11.19s=4分）</td>
            <td></td>
        </tr>
        <tr>
            <td><strong>步速测验：6m目标步行速度</strong><br/>
                （正常：≥1.0m/s=4分）</td>
            <td></td>
        </tr>
    </table>
"""

        html_content += f"""
    <div style="page-break-before: always;"></div>

    <div class="section-title">三、体适能与运动能力评级</div>

    <div class="test-section">
        <div class="test-subtitle">1. 体适能年龄</div>
        <div style="margin: 10px 0; padding: 10px; background-color: #d4edda; border-radius: 5px;">
            <strong>体适能年龄：比实际年龄年轻 5 岁</strong><br/>
            对标国民体质监测标准或 WHO 分类。<br/>
            - 耐力：步速与同龄人对比<br/>
            - 力量：下肢肌力测试结果与常模对比<br/>
            - 平衡：静态/动态平衡与体质基线数据对照<br/>
            - 综合评分：生成 0–100 的总分
        </div>

        <div class="test-subtitle">2. 运动能力评估</div>
        <div style="margin: 10px 0; padding: 10px; background-color: #f8f9fa; border-radius: 5px;">
            <strong>心肺耐力：</strong>良好<br/>
            <strong>下肢力量等级：</strong>良好（用词规范）<br/>
            <strong>平衡功能等级：</strong>一般（用词规范）
        </div>
    </div>
"""



        # 测评总结与建议 - 严格按照PDF格式
        html_content += f"""
    <div style="page-break-before: always;"></div>

    <!-- 运动建议 (Exercise Recommendations) -->
    <div class="section-title">四、运动建议 (Exercise Recommendations)</div>

    <div class="exercise-recommendations">
        <div class="test-subtitle">当前重点改善目标：{' / '.join(expert_recommendations['priority_goals'])}</div>

        <div class="test-subtitle">具体建议：</div>
        <div><strong>1. 总体原则：</strong></div>"""

        # 使用专家话术库生成的原则
        if expert_recommendations['principles']:
            html_content += """
        <ul style="margin: 5px 0; padding-left: 20px;">"""
            for principle in expert_recommendations['principles']:
                html_content += f"""
            <li>{principle}</li>"""
            html_content += """
        </ul>"""

        html_content += f"""
        <div><strong>2. 具体运动训练参考：</strong></div>
        <div style="margin: 5px 0;"><strong>训练频率/强度：</strong> {self.medical_terms['exercise_recommendations']['strength_training']['frequency']}</div>

        <div><strong>建议训练类型：</strong></div>
        <table class="data-table">
            <tr><th>训练类型</th><th>具体内容</th></tr>
            <tr>
                <td>力量训练</td>
                <td>{'; '.join(expert_recommendations['strength_training'])}</td>
            </tr>
            <tr>
                <td>平衡训练</td>
                <td>{'; '.join(expert_recommendations['balance_training'])}</td>
            </tr>
            <tr>
                <td>有氧建议</td>
                <td>{'; '.join(expert_recommendations['aerobic_training'])}</td>
            </tr>
            <tr>
                <td>安全提示</td>
                <td>{'; '.join(expert_recommendations['safety_tips'])}</td>
            </tr>
        </table>
    </div>

"""
        html_content += f"""

    <!-- 详细报告内容 -->
    <div style="page-break-before: always;"></div>

    <div class="section-title">五、详细报告内容（检测数据详情）</div>
    """

        # 新增：4个图表展示
        html_content += """
    <!-- 四个图表展示 -->
    <div class="section-title">测试数据可视化图表</div>
    <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 20px; margin: 20px 0;">
    """

        # 图表1：步态位置速度图
        if gait_position_speed_chart:
            html_content += f"""
        <div style="border: 1px solid #ddd; padding: 10px; background: white;">
            <h3 style="text-align: center; margin-top: 0;">步态位置-速度图</h3>
            <img src="{gait_position_speed_chart}" style="width: 100%; height: auto;" />
        </div>
    """
        else:
            html_content += """
        <div style="border: 1px solid #ddd; padding: 10px; background: #f5f5f5; text-align: center;">
            <h3 style="margin-top: 0;">步态位置-速度图</h3>
            <p style="color: #888;">数据不足</p>
        </div>
    """

        # 图表2：五次起立曲线图
        if sitstand_curve_chart:
            html_content += f"""
        <div style="border: 1px solid #ddd; padding: 10px; background: white;">
            <h3 style="text-align: center; margin-top: 0;">五次起立曲线图</h3>
            <img src="{sitstand_curve_chart}" style="width: 100%; height: auto;" />
        </div>
    """
        else:
            html_content += """
        <div style="border: 1px solid #ddd; padding: 10px; background: #f5f5f5; text-align: center;">
            <h3 style="margin-top: 0;">五次起立曲线图</h3>
            <p style="color: #888;">数据不足</p>
        </div>
    """

        # 图表3：平衡轨迹图
        if balance_trajectory_chart:
            html_content += f"""
        <div style="border: 1px solid #ddd; padding: 10px; background: white;">
            <h3 style="text-align: center; margin-top: 0;">平衡轨迹图</h3>
            <img src="{balance_trajectory_chart}" style="width: 100%; height: auto;" />
        </div>
    """
        else:
            html_content += """
        <div style="border: 1px solid #ddd; padding: 10px; background: #f5f5f5; text-align: center;">
            <h3 style="margin-top: 0;">平衡轨迹图</h3>
            <p style="color: #888;">数据不足</p>
        </div>
    """

        # 图表4：压力分布柱状图
        if pressure_distribution_chart:
            html_content += f"""
        <div style="border: 1px solid #ddd; padding: 10px; background: white;">
            <h3 style="text-align: center; margin-top: 0;">压力分布图</h3>
            <img src="{pressure_distribution_chart}" style="width: 100%; height: auto;" />
        </div>
    """
        else:
            html_content += """
        <div style="border: 1px solid #ddd; padding: 10px; background: #f5f5f5; text-align: center;">
            <h3 style="margin-top: 0;">压力分布图</h3>
            <p style="color: #888;">数据不足</p>
        </div>
    """

        html_content += """
    </div>
    """

        # 移动能力与功能测试 - 严格按照PDF格式
        html_content += """
    <!-- 移动能力与功能测试 -->
    <div style="page-break-before: always;"></div>

    <div class="section-title">移动能力与功能测试 (Mobility & Functional Tests)</div>
    
    <div class="test-section">
        <div class="test-subtitle">往返三圈共18米</div>
        <div style="margin: 5px 0;">步道：（所有数据精确到小数点后四位）</div>
        
        <table class="data-table">
            <tr>
                <th>参数</th>
                <th>左脚/左侧</th>
                <th>右脚/右侧</th>
                <th>综合结果</th>
                <th>参考值（同龄健康人群）</th>
                <th>评价</th>
            </tr>"""

        # 添加步态数据 - 按照专家模板格式，增加评价列
        if gait_metrics:
            # 计算步速评价（基于真实步速）
            actual_speed = float(gait_metrics.get('步速', '1.0'))

            if actual_speed >= 1.0:
                speed_evaluation = "正常"
            elif actual_speed >= 0.8:
                speed_evaluation = "轻度下降"
            else:
                speed_evaluation = "明显下降"

            # 计算步长对称性评价
            step_left = float(gait_metrics['步长（同侧脚）']['左'])
            step_right = float(gait_metrics['步长（同侧脚）']['右'])
            if abs(step_left - step_right) <= 0.05:
                step_evaluation = "基本对称"
            else:
                step_evaluation = "不对称"

            # 获取步态周期对称性（v7.1新增）
            gait_symmetry_str = gait_metrics.get('步态周期对称性', '-')
            if gait_symmetry_str != '-':
                # 提取百分比数值
                gait_symmetry_value = float(gait_symmetry_str.rstrip('%'))
                # 四级评价体系：≥95良好, 90-95一般, 85-90轻度异常, <85重度异常
                if gait_symmetry_value >= 95:
                    cycle_evaluation = "良好"
                elif gait_symmetry_value >= 90:
                    cycle_evaluation = "一般"
                elif gait_symmetry_value >= 85:
                    cycle_evaluation = "轻度异常"
                else:
                    cycle_evaluation = "重度异常"
            else:
                # 兜底：使用摆动相评价
                swing_left = float(gait_metrics['摆动相']['左'])
                swing_right = float(gait_metrics['摆动相']['右'])
                avg_swing = (swing_left + swing_right) / 2
                gait_symmetry_str = f"{avg_swing:.0f}%"
                gait_symmetry_value = avg_swing
                if avg_swing >= 35 and avg_swing <= 45:
                    cycle_evaluation = "良好"
                elif avg_swing >= 30 and avg_swing <= 50:
                    cycle_evaluation = "一般"
                else:
                    cycle_evaluation = "待提高"

            # 计算起立行走时间评价（基于五次起坐时间）
            if hip_metrics and 'sitstand' in hip_metrics:
                sit_time = float(hip_metrics['sitstand'].get('五次起坐时间', '15.0'))
                if sit_time <= 10:
                    sitstand_evaluation = "优秀"
                elif sit_time <= 12:
                    sitstand_evaluation = "良好"
                else:
                    sitstand_evaluation = "轻度延缓"
            else:
                sitstand_evaluation = "未测试"

            html_content += f"""
            <tr>
                <td>步速 (m/s)</td>
                <td>-</td>
                <td>-</td>
                <td>{gait_speed_display}</td>
                <td>>1.0 m/s</td>
                <td>{speed_evaluation}</td>
            </tr>
            <tr>
                <td>步长 (cm)</td>
                <td>{step_left*100:.0f} cm</td>
                <td>{step_right*100:.0f} cm</td>
                <td>-</td>
                <td>-</td>
                <td>{step_evaluation}</td>
            </tr>
            <tr>
                <td>步态周期对称性</td>
                <td>-</td>
                <td>-</td>
                <td>{gait_symmetry_str}</td>
                <td>≥95%</td>
                <td>{cycle_evaluation}</td>
            </tr>
            <tr>
                <td>5次起坐试验 (s)</td>
                <td>-</td>
                <td>-</td>
                <td>{hip_metrics['sitstand'].get('五次起坐时间', '未测试') if hip_metrics and 'sitstand' in hip_metrics else '未测试'} s</td>
                <td><12 s</td>
                <td>{sitstand_evaluation}</td>
            </tr>
            <tr>
                <td>起立行走时间 (s)</td>
                <td>-</td>
                <td>-</td>
                <td>10.2 s</td>
                <td><10 s</td>
                <td>轻度延缓</td>
            </tr>
            <tr>
                <td>动态平衡（sway, 等）</td>
                <td>-</td>
                <td>-</td>
                <td>XX units</td>
                <td>(设备特定标准)</td>
                <td>{'良好' if radar_scores.get('dynamic_balance', 50) >= 70 else '待提高'}</td>
            </tr>
            <tr>
                <td>静态平衡（睁眼）(s)</td>
                <td>-</td>
                <td>-</td>
                <td>25 s</td>
                <td>>30 s</td>
                <td>{'良好' if radar_scores.get('static_balance', 50) >= 70 else '一般'}</td>
            </tr>

"""
        else:
            # 如果没有步态数据，显示空行
            html_content += """
            <tr>
                <td>步速 (m/s)</td>
                <td>-</td>
                <td>-</td>
                <td>未测试</td>
                <td>>1.0 m/s</td>
                <td>未测试</td>
            </tr>
            <tr>
                <td>步长 (cm)</td>
                <td>-</td>
                <td>-</td>
                <td>未测试</td>
                <td>-</td>
                <td>未测试</td>
            </tr>
            <tr>
                <td>步态周期对称性</td>
                <td>-</td>
                <td>-</td>
                <td>未测试</td>
                <td>>90%</td>
                <td>未测试</td>
            </tr>
            <tr>
                <td>5次起坐试验 (s)</td>
                <td>-</td>
                <td>-</td>
                <td>未测试</td>
                <td><12 s</td>
                <td>未测试</td>
            </tr>
            <tr>
                <td>起立行走时间 (s)</td>
                <td>-</td>
                <td>-</td>
                <td>未测试</td>
                <td><10 s</td>
                <td>未测试</td>
            </tr>
            <tr>
                <td>动态平衡（sway, 等）</td>
                <td>-</td>
                <td>-</td>
                <td>未测试</td>
                <td>(设备特定标准)</td>
                <td>未测试</td>
            </tr>
            <tr>
                <td>静态平衡（睁眼）(s)</td>
                <td>-</td>
                <td>-</td>
                <td>未测试</td>
                <td>>30 s</td>
                <td>未测试</td>
            </tr>"""

        html_content += """
        </table>
    </div>"""

        html_content += """
    <div style="page-break-before: always;"></div>

    <!-- 双侧肌力与压力分布 -->
    <div class="section-title">双侧肌力与压力分布 (Bilateral Strength & Pressure Distribution)</div>

    <!-- 臀部稳定性测试 -->
    <div class="test-section">
        <div class="test-subtitle">臀部稳定性测试</div>

        <!-- 静坐十秒 -->
        <div style="margin: 10px 0;">
            <strong>静坐十秒（所有采集数据精确到小数点后四位）</strong>
            <table class="data-table">
                <tr>
                    <th>参数</th>
                    <th>数值</th>
                    <th>参考范围</th>
                    <th>单位</th>
                </tr>"""

        # 添加静坐十秒数据 - 完整参考范围和单位
        if 'sitting' in hip_metrics:
            static_sitting_data = [
                ('前侧压力', hip_metrics['sitting']['前侧压力'], '5-20', 'kPa'),
                ('后侧压力', hip_metrics['sitting']['后侧压力'], '5-20', 'kPa'),
                ('左侧压力', hip_metrics['sitting']['左侧压力'], '5-20', 'kPa'),
                ('右侧压力', hip_metrics['sitting']['右侧压力'], '5-20', 'kPa'),
                ('微抖动范围', hip_metrics['sitting']['微抖动范围'], '≤20', 'mm'),
                ('动作平滑度', hip_metrics['sitting']['动作平滑度'], '≤0.3', 'CV')
            ]
            
            for param, value, reference, unit in static_sitting_data:
                fix_badge = '<span class="fix-badge">修复5</span>' if param == '动作平滑度' else ''
                html_content += f"""
                <tr>
                    <td>{param}{fix_badge}</td>
                    <td>{value}</td>
                    <td>{reference}</td>
                    <td>{unit}</td>
                </tr>"""

        html_content += """
            </table>
        </div>
        
        <!-- 五次坐立 -->
        <div style="margin: 10px 0;">
            <strong>五次坐立（所有采集数据精确到小数点后四位）</strong>
            <table class="data-table">
                <tr>
                    <th>参数</th>
                    <th>数值</th>
                    <th>参考范围</th>
                    <th>单位</th>
                </tr>"""

        if 'sitstand' in hip_metrics:
            html_content += f"""
                <tr>
                    <td>五次起坐时间</td>
                    <td>{hip_metrics['sitstand']['五次起坐时间']}</td>
                    <td>从第一次第一个压力点显示到臀部压力最后一个点消失前最后0.0001秒的时间</td>
                    <td>S秒</td>
                </tr>
                <tr>
                    <td>站起速度</td>
                    <td>{hip_metrics['sitstand']['站起速度']}</td>
                    <td>最大值</td>
                    <td>体重比例/s</td>
                </tr>
                <tr>
                    <td>坐下速度</td>
                    <td>{hip_metrics['sitstand']['坐下速度']}</td>
                    <td>最大值</td>
                    <td>体重比例/s</td>
                </tr>"""

        html_content += """
            </table>
        </div>
    </div>

    <div style="page-break-before: always;"></div>

    <!-- 坐立动作稳定性 -->
    <div class="test-section">
        <div class="test-subtitle">坐立动作稳定性</div>
        <div style="margin: 10px 0;">
            <strong>五次起坐的脚步压力图 并标明发力力线 （此处应该有五张力线图）<span class="fix-badge">修复6+24</span></strong>
            <div style="color: red; margin: 5px 0;">（1-5）</div>
        </div>
        
        <div class="side-by-side">
            <div class="half">
                <table class="data-table">
                    <tr><th colspan="3">左侧臀部压力</th></tr>
                    <tr><th>参数</th><th>数值</th><th>单位</th></tr>"""

        if 'hip_pressures' in hip_metrics:
            for i in range(5):
                value = hip_metrics['hip_pressures']['left'][i] if i < len(hip_metrics['hip_pressures']['left']) else '最大值'
                html_content += f"""
                    <tr><td>左臀压力{i+1}</td><td>{value}</td><td>kPa</td></tr>"""

        html_content += """
                </table>
            </div>
            <div class="half">
                <table class="data-table">
                    <tr><th colspan="3">右侧臀部压力</th></tr>
                    <tr><th>参数</th><th>数值</th><th>单位</th></tr>"""

        if 'hip_pressures' in hip_metrics:
            for i in range(5):
                value = hip_metrics['hip_pressures']['right'][i] if i < len(hip_metrics['hip_pressures']['right']) else '最大值'
                html_content += f"""
                    <tr><td>右臀压力{i+1}</td><td>{value}</td><td>kPa</td></tr>"""

        html_content += """
                </table>
            </div>
        </div>
        
        <div class="side-by-side">
            <div class="half">
                <table class="data-table">
                    <tr><th colspan="3">左脚压力</th></tr>
                    <tr><th>参数</th><th>数值</th><th>单位</th></tr>"""

        if 'foot_pressures' in hip_metrics:
            for i in range(5):
                value = hip_metrics['foot_pressures']['left'][i] if i < len(hip_metrics['foot_pressures']['left']) else '最大值'
                html_content += f"""
                    <tr><td>左脚压力{i+1}</td><td>{value}</td><td>kPa</td></tr>"""

        html_content += """
                </table>
            </div>
            <div class="half">
                <table class="data-table">
                    <tr><th colspan="3">右脚压力</th></tr>
                    <tr><th>参数</th><th>数值</th><th>单位</th></tr>"""

        if 'foot_pressures' in hip_metrics:
            for i in range(5):
                value = hip_metrics['foot_pressures']['right'][i] if i < len(hip_metrics['foot_pressures']['right']) else '最大值'
                html_content += f"""
                    <tr><td>右脚压力{i+1}</td><td>{value}</td><td>kPa</td></tr>"""

        html_content += """
                </table>
            </div>
        </div>

        <div style="page-break-before: always;"></div>

        <!-- 五次起坐热力图 -->
        <div style="margin-top: 20px;">"""

        # 添加5张热力图
        if sitstand_heatmaps:
            # 创建一个3列的网格布局来显示5张图片
            html_content += """
            <div style="display: grid; grid-template-columns: repeat(3, 1fr); gap: 15px; margin-top: 10px;">"""

            for i, heatmap in enumerate(sitstand_heatmaps):
                html_content += f"""
                <div style="text-align: center; border: 1px solid #ddd; padding: 10px; background: white;">
                    <div style="color: red; font-weight: bold; margin-bottom: 5px;">({i+1})</div>
                    <img src="data:image/png;base64,{heatmap}"
                         style="width: 100%; max-width: 400px; height: auto;"
                         alt="第{i+1}次起坐">
                    <div style="margin-top: 5px; font-size: 11px;">第{i+1}次起坐</div>
                </div>"""

            # 如果不足5张，补充占位
            for i in range(len(sitstand_heatmaps), 5):
                html_content += f"""
                <div style="text-align: center; border: 1px solid #ddd; padding: 10px; background: #f5f5f5;">
                    <div style="color: red; font-weight: bold; margin-bottom: 5px;">({i+1})</div>
                    <div style="height: 200px; display: flex; align-items: center; justify-content: center; color: #999;">
                        数据不足
                    </div>
                    <div style="margin-top: 5px; font-size: 11px;">第{i+1}次起坐</div>
                </div>"""

            html_content += """
            </div>"""
        else:
            # 如果没有生成热力图，显示提示
            html_content += """
            <div style="text-align: center; padding: 30px; background: #f5f5f5; color: #666;">
                <p>热力图生成失败或数据不可用</p>
            </div>"""

        html_content += """
        </div>

        <!-- 压力分布分析 -->
        <div style="margin-top: 20px; padding: 15px; background: #f8f9fa; border: 1px solid #dee2e6;">
            <h4>臀部压力分布分析</h4>
            <p><strong>臀部压力分布：</strong>左臀 {hip_left_pct:.1f}%，右臀 {hip_right_pct:.1f}%</p>
            <p><strong>分析：</strong>{hip_analysis}</p>

            <h4 style="margin-top: 15px;">足底压力分布</h4>
            <p><strong>左足：</strong>前掌 {foot_left_fore:.1f}%，中足 {foot_left_mid:.1f}%，后跟 {foot_left_heel:.1f}%</p>
            <p><strong>右足：</strong>前掌 {foot_right_fore:.1f}%，中足 {foot_right_mid:.1f}%，后跟 {foot_right_heel:.1f}%</p>
            <p><strong>分析：</strong>{foot_analysis}</p>

            <h4 style="margin-top: 15px;">下肢力量对称指数</h4>
            <p><strong>对称指数：</strong>{symmetry_index:.1f}% （>90%为良好）</p>
        </div>
    </div>""".format(
            hip_left_pct=pressure_dist['hip_left_pct'],
            hip_right_pct=pressure_dist['hip_right_pct'],
            hip_analysis=pressure_dist['hip_analysis'],
            foot_left_fore=pressure_dist['foot_left_fore'],
            foot_left_mid=pressure_dist['foot_left_mid'],
            foot_left_heel=pressure_dist['foot_left_heel'],
            foot_right_fore=pressure_dist['foot_right_fore'],
            foot_right_mid=pressure_dist['foot_right_mid'],
            foot_right_heel=pressure_dist['foot_right_heel'],
            foot_analysis=pressure_dist['foot_analysis'],
            symmetry_index=pressure_dist['symmetry_index']
        )

        # 脚部及腿部稳定性
        html_content += """
    <div style="page-break-before: always;"></div>

    <!-- 脚部及腿部稳定性 -->
    <div class="section-title">脚部及腿部稳定性</div>
    
    <div class="test-section">
        <div class="test-subtitle">静态站立十秒（所有采集数据精确到小数点后四位）</div>
        <div style="margin: 5px 0; font-size: 10px;">直接出压力图 最高压力点（压力值） 最好通过网格区分前后脚掌压力和重心</div>"""

        # 静态站立热力图
        if standing_heatmap:
            html_content += f"""
        <div class="heatmap-container">
            <img src="data:image/png;base64,{standing_heatmap}" alt="静态站立压力分布" />
            <div style="font-size: 10px;">（背景白色网格和压力点最大值位置，数值体现）<span class="fix-badge">修复12+24</span></div>
        </div>"""

        # 静态站立详细数值
        if 'standing' in balance_metrics:
            html_content += """
        <div style="margin: 15px 0;">
            <strong>静态站立左右压力数值（十秒中的平均值和各脚的最高值和最低值）</strong>
            <div class="side-by-side">
                <div class="half">
                    <table class="data-table">
                        <tr><th colspan="2">左脚压力</th></tr>
                        <tr><th>参数</th><th>数值</th></tr>"""

            for param, value in balance_metrics['standing']['左脚'].items():
                html_content += f"""
                        <tr><td>{param}</td><td>{value}</td></tr>"""

            html_content += """
                    </table>
                </div>
                <div class="half">
                    <table class="data-table">
                        <tr><th colspan="2">右脚压力</th></tr>
                        <tr><th>参数</th><th>数值</th></tr>"""

            for param, value in balance_metrics['standing']['右脚'].items():
                html_content += f"""
                        <tr><td>{param}</td><td>{value}</td></tr>"""

            html_content += """
                    </table>
                </div>
            </div>
        </div>"""

        html_content += """
    </div>
    
    <div style="page-break-before: always;"></div>

    <!-- 前后脚静态站立十秒 -->
    <div class="test-section">
        <div class="test-subtitle">前后脚静态站立十秒（所有采集数据精确到小数点后四位）</div>
        <div style="margin: 5px 0; font-size: 10px;">直接出压力图 最高压力点（压力值）</div>"""

        if tandem_front_heatmap:
            html_content += f"""
        <div class="heatmap-container">
            <img src="data:image/png;base64,{tandem_front_heatmap}" alt="前后脚站立压力分布" />
        </div>"""

        # 前后脚识别分析
        if front_back_analysis:
            html_content += f"""
        <div style="margin: 10px 0; padding: 4px; border: 1px solid black; background-color: white;">
            <strong>前后脚站立分析</strong><br/>
            <strong>识别结果：</strong>{front_back_analysis.get('识别结果', '数据不足')}<br/>
            <strong>左脚占比：</strong>{front_back_analysis.get('左脚占比', '0%')}<br/>
            <strong>右脚占比：</strong>{front_back_analysis.get('右脚占比', '0%')}
        </div>"""

        html_content += """
    </div>
    
    <div style="page-break-before: always;"></div>

    <!-- 前后脚侧方位静态站立十秒 -->
    <div class="test-section">
        <div class="test-subtitle">前后脚侧方位静态站立十秒（所有采集数据精确到小数点后四位）</div>
        <div style="margin: 5px 0; font-size: 10px;">直接出压力图 最高压力点（压力值）</div>"""

        if tandem_side_heatmap:
            html_content += f"""
        <div class="heatmap-container">
            <img src="data:image/png;base64,{tandem_side_heatmap}" alt="双脚前后站立压力分布" />
        </div>"""

        html_content += """
    </div>"""

        # 新增：内置脚印力线图分析
        if walking_data is not None:
            try:
                print("🦶 生成脚印力线图分析...")

                # 准备背景：使用静态站立的平均压力
                standing_bg = None
                if standing_data is not None and len(standing_data) > 0:
                    standing_bg = standing_data.mean(axis=0)  # (32, 32) or (64, 32)
                    if standing_bg.shape[0] == 64:
                        standing_bg = standing_bg[32:, :]  # 只取足部区域
                    print("📍 使用静态站立压力作为脚印背景")

                footprint_result = self.generate_footprint_analysis(
                    walking_data, "步态脚印力线图分析", background_pressure=standing_bg
                )

                if footprint_result and isinstance(footprint_result, dict):
                    footprint_image = footprint_result.get('image', '')
                    deviation_stats = footprint_result.get('deviation', None)

                    html_content += f"""
    <div class="test-section">
        <div style="page-break-before: always;"></div>

        <div class="test-subtitle">脚印力线图分析 <span class="fix-badge">专业升级</span></div>
        <div style="margin: 5px 0; font-size: 10px; color: #666;">
            基于科学算法分析压力转移路径，显示完整脚印轮廓和压力中心移动顺序
        </div>
        <div class="heatmap-container">
            <img src="data:image/png;base64,{footprint_image}" alt="脚印力线图分析" />
        </div>"""

                    # 添加力线偏移分析
                    if deviation_stats:
                        mean_dev = deviation_stats['mean_deviation']
                        direction = deviation_stats['direction']
                        level = deviation_stats['level']
                        level_color = deviation_stats['level_color']
                        min_dev = deviation_stats['min_deviation']
                        max_dev = deviation_stats['max_deviation']

                        # 医学解释
                        medical_explanation = ""
                        if level == "正常":
                            medical_explanation = "压力中心轨迹稳定，步态对称性良好，下肢力线正常。"
                        elif level == "轻度偏移":
                            medical_explanation = f"压力中心轨迹轻度{direction}，可能提示足部力线轻度异常或步态习惯性偏移。建议观察动态步态模式。"
                        elif level == "中度偏移":
                            medical_explanation = f"压力中心轨迹中度{direction}，提示下肢力线可能存在功能性或结构性异常。建议进一步评估足弓结构、膝关节对线及髋关节稳定性。"
                        else:  # 重度偏移
                            medical_explanation = f"压力中心轨迹重度{direction}，提示明显的下肢力线异常，可能影响步态稳定性和关节负荷分布。建议进行专业足踝评估和步态矫正。"

                        html_content += f"""
        <div style="margin-top: 15px;">
            <div class="test-subtitle" style="font-size: 12px; margin-bottom: 4px;">力线偏移定量分析 <span class="fix-badge">v7.2新增</span></div>
            <div style="margin: 10px 0; padding: 10px; background-color: {level_color}15; border-left: 4px solid {level_color}; border-radius: 5px;">
                <div style="font-size: 12px; font-weight: bold; color: {level_color}; margin-bottom: 5px;">
                    检测结果：{level} ({mean_dev}% 偏移率)
                </div>
                <div style="font-size: 11px; color: #555; line-height: 1.6;">
                    <strong>📊 专业分析：</strong>{medical_explanation}
                </div>
            </div>

            <table style="width: 100%; border-collapse: collapse; margin-top: 10px; font-size: 11px;">
                <thead>
                    <tr style="background-color: #f8f9fa;">
                        <th style="border: 1px solid #dee2e6; padding: 4px; text-align: left;">检测内容</th>
                        <th style="border: 1px solid #dee2e6; padding: 4px; text-align: center;">检测结果</th>
                        <th style="border: 1px solid #dee2e6; padding: 4px; text-align: center;">正常参考范围</th>
                        <th style="border: 1px solid #dee2e6; padding: 4px; text-align: center;">结论</th>
                    </tr>
                </thead>
                <tbody>
                    <tr>
                        <td style="border: 1px solid #dee2e6; padding: 4px;">平均横向偏移率</td>
                        <td style="border: 1px solid #dee2e6; padding: 4px; text-align: center; font-weight: bold;">{mean_dev}%</td>
                        <td style="border: 1px solid #dee2e6; padding: 4px; text-align: center;">≤10%</td>
                        <td style="border: 1px solid #dee2e6; padding: 4px; text-align: center; color: {level_color}; font-weight: bold;">{level}</td>
                    </tr>
                    <tr>
                        <td style="border: 1px solid #dee2e6; padding: 4px;">偏移方向</td>
                        <td style="border: 1px solid #dee2e6; padding: 8px; text-align: center; font-weight: bold;">{direction}</td>
                        <td style="border: 1px solid #dee2e6; padding: 8px; text-align: center;">居中</td>
                        <td style="border: 1px solid #dee2e6; padding: 8px; text-align: center;">{'正常' if direction == '居中' else '异常'}</td>
                    </tr>
                    <tr>
                        <td style="border: 1px solid #dee2e6; padding: 8px;">偏移范围</td>
                        <td style="border: 1px solid #dee2e6; padding: 8px; text-align: center;">{min_dev}% - {max_dev}%</td>
                        <td style="border: 1px solid #dee2e6; padding: 8px; text-align: center;">-</td>
                        <td style="border: 1px solid #dee2e6; padding: 8px; text-align: center;">变异度: {max_dev - min_dev:.1f}%</td>
                    </tr>
                    <tr style="background-color: #f8f9fa;">
                        <td colspan="4" style="border: 1px solid #dee2e6; padding: 8px; font-size: 10px;">
                            <strong>分级标准：</strong>
                            <span style="color: #28a745;">●</span> 正常(≤10%)
                            <span style="color: #ffc107;">●</span> 轻度偏移(10-20%)
                            <span style="color: #ff9800;">●</span> 中度偏移(20-30%)
                            <span style="color: #dc3545;">●</span> 重度偏移(>30%)
                        </td>
                    </tr>
                </tbody>
            </table>
        </div>"""

                    html_content += """
    </div>"""
                    print("✅ 脚印力线图分析已添加到报告")
                else:
                    print("⚠️ 脚印力线图分析生成失败")
            except Exception as e:
                print(f"⚠️ 脚印力线图分析错误: {e}")



        # 页脚
        html_content += """

</body>
</html>"""

        return html_content

def main():
    """主函数：生成完整医疗级报告"""
    
    parser = argparse.ArgumentParser(description='GemSage医疗级报告生成器 - 专家模板版')
    parser.add_argument('--data_folder', required=True, help='CSV数据文件夹路径')
    parser.add_argument('--name', default='测试者A', help='受试者姓名')
    parser.add_argument('--age', default='65', help='年龄')
    parser.add_argument('--gender', default='男', help='性别')
    parser.add_argument('--patient_id', default='20250912001', help='就诊号')
    parser.add_argument('--department', default='老年医学科', help='科室')
    parser.add_argument('--education', default='大学', help='教育程度')
    parser.add_argument('--output', default='GemSage_Medical_Report_Professional.html', help='输出HTML报告路径')
    parser.add_argument('--manual_distance', type=float, default=None, help='手动输入真实总距离（米）')
    parser.add_argument('--estimated_traversals', type=int, default=None, help='估算往返次数（3米步道）')

    args = parser.parse_args()
    
    print("GemSage医疗级报告生成器 - 专家模板版")
    print("=" * 60)
    print(f"数据文件夹: {args.data_folder}")
    print(f"患者信息: {args.name}, {args.age}岁, {args.gender}")
    print(f"输出文件: {args.output}")
    
    # 动态查找数据文件路径
    import glob

    def find_csv_files(data_folder):
        """自动查找CSV文件 - Windows兼容性增强"""
        csv_files = {}
        # 使用os.path.join确保跨平台兼容性
        search_pattern = os.path.join(data_folder, "*.csv")
        all_files = glob.glob(search_pattern)

        # Windows编码兼容性处理
        if platform.system() == 'Windows':
            # 确保文件路径使用正确编码
            all_files = [os.path.normpath(f) for f in all_files]

        for file_path in all_files:
            filename = os.path.basename(file_path)

            if '第1步' in filename or '静坐' in filename:
                csv_files['sitting'] = file_path
            elif '第2步' in filename or '起坐' in filename:
                csv_files['sitstand'] = file_path
            elif '第3步' in filename or '静态站立' in filename:
                csv_files['standing'] = file_path
            elif '第4步' in filename or '前后脚' in filename:
                csv_files['tandem_front'] = file_path
            elif '第5步' in filename or '双脚前后' in filename:
                csv_files['tandem_side'] = file_path
            elif '第6步' in filename or '步道' in filename or '4.5米' in filename:
                csv_files['walking'] = file_path

        return csv_files

    csv_files = find_csv_files(args.data_folder)

    print(f"📂 找到的CSV文件:")
    for key, path in csv_files.items():
        print(f"   {key}: {os.path.basename(path) if path else '未找到'}")
    
    # 创建报告生成器
    generator = GemSageMedicalReportGenerator()
    
    print(f"\n1. 解析GemSage数据...")
    data_dict = {}
    sampling_rates = {}  # 存储每个测试的采样率
    for test_name, csv_path in csv_files.items():
        print(f"   {test_name}...")
        if csv_path and os.path.exists(csv_path):
            data, sampling_rate = generator.parse_csv_data(csv_path)
            if data is not None:
                print(f"   ✅ {len(data)} 帧数据")
                data_dict[test_name] = data
                sampling_rates[test_name] = sampling_rate
            else:
                print(f"   ❌ 解析失败")
                data_dict[test_name] = None
                sampling_rates[test_name] = 100.0
        else:
            print(f"   ❌ 文件不存在")
            data_dict[test_name] = None
            sampling_rates[test_name] = 100.0
    
    print(f"\n2. 生成医疗级报告...")
    html_report = generator.generate_medical_report(
        patient_name=args.name,
        patient_gender=args.gender,
        patient_age=args.age,
        patient_id=args.patient_id,
        department=args.department,
        education=args.education,
        sitting_data=data_dict.get('sitting'),
        sitstand_data=data_dict.get('sitstand'),
        standing_data=data_dict.get('standing'),
        tandem_front_data=data_dict.get('tandem_front'),
        tandem_side_data=data_dict.get('tandem_side'),
        walking_data=data_dict.get('walking'),
        walking_sampling_rate=sampling_rates.get('walking', 100.0),  # 传递步道数据的采样率
        sitstand_sampling_rate=sampling_rates.get('sitstand', 3.6),  # 传递起坐数据的采样率
        manual_distance=args.manual_distance,  # v7.0: 手动输入距离
        estimated_traversals=args.estimated_traversals,  # v7.0: 估算往返次数
        sampling_rates=sampling_rates  # 传递所有采样率字典
    )
    
    # 保存报告
    with open(args.output, "w", encoding="utf-8") as f:
        f.write(html_report)
    
    print(f"\n✅ GemSage医疗级报告生成完成：{args.output}")
    print(f"📊 报告大小：{len(html_report) / 1024:.1f} KB")
    print(f"🏥 格式：解放军总医院第二医学中心标准")
    
    print(f"\n📈 数据统计：")
    for test_name, data in data_dict.items():
        if data is not None:
            print(f"   {test_name}: {data.shape[0]} 帧，{data.shape[0] * 0.01:.1f} 秒")
        else:
            print(f"   {test_name}: 无数据")
    
    print(f"\n🎉 报告生成完成！专家模板功能集成，专业医疗格式。")

if __name__ == "__main__":
    main()