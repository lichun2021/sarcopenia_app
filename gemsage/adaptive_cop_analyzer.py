#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
硬件自适应COP轨迹分析器
解决不同硬件规格下COP算法的兼容性问题
"""

import numpy as np
import pandas as pd
from typing import Dict, List, Tuple, Optional, Union
import json
from dataclasses import dataclass
from enum import Enum

class HardwareType(Enum):
    """硬件设备类型"""
    FOOT_PRESSURE_PAD = "foot_pressure_pad"       # 足压垫
    HIP_PRESSURE_PAD = "hip_pressure_pad"         # 臀部压力垫
    GAIT_WALKWAY = "gait_walkway"                 # 步道
    CUSTOM = "custom"                             # 自定义

@dataclass
class HardwareSpec:
    """硬件规格定义"""
    # 基本信息
    name: str
    hardware_type: HardwareType
    
    # 物理尺寸 (米)
    width: float          # 宽度
    height: float         # 高度
    
    # 传感器规格
    grid_width: int       # 传感器网格宽度
    grid_height: int      # 传感器网格高度
    
    # 传感器特性
    pressure_range: Tuple[float, float]  # 压力范围 (min, max)
    pressure_threshold: float = 20       # 有效压力阈值
    
    # 应用场景
    typical_test_types: List[str] = None
    
    def __post_init__(self):
        if self.typical_test_types is None:
            self.typical_test_types = []
        
        # 计算物理分辨率
        self.grid_scale_x = self.width / self.grid_width
        self.grid_scale_y = self.height / self.grid_height
        
        # 计算总传感器数量
        self.total_sensors = self.grid_width * self.grid_height

class HardwareDatabase:
    """硬件数据库 - 预定义常见硬件规格"""
    
    @staticmethod
    def get_predefined_specs() -> Dict[str, HardwareSpec]:
        """获取预定义的硬件规格"""
        return {
            # 足压感知垫 (静态评估)
            "foot_pad_1100x650": HardwareSpec(
                name="足压感知垫 1100×650mm",
                hardware_type=HardwareType.FOOT_PRESSURE_PAD,
                width=1.10, height=0.65,
                grid_width=32, grid_height=32,
                pressure_range=(0, 500),
                typical_test_types=["静态站立", "单脚站立", "平衡测试"]
            ),
            
            # 臀部压力垫 (坐立测试)
            "hip_pad_550x530": HardwareSpec(
                name="臀部压力垫 550×530mm",
                hardware_type=HardwareType.HIP_PRESSURE_PAD,
                width=0.55, height=0.53,
                grid_width=32, grid_height=32,
                pressure_range=(0, 800),
                typical_test_types=["五次坐立", "静坐平衡"]
            ),
            
            # 步道压力垫 (步态分析)  
            "gait_walkway_1565x900": HardwareSpec(
                name="步道压力垫 1565×900mm",
                hardware_type=HardwareType.GAIT_WALKWAY,
                width=1.565, height=0.90,
                grid_width=32, grid_height=32,
                pressure_range=(0, 1000),
                typical_test_types=["步态分析", "行走测试"]
            ),
            
            # 大型步道 (多块拼接)
            "large_walkway_3000x1500": HardwareSpec(
                name="大型步道 3000×1500mm",
                hardware_type=HardwareType.GAIT_WALKWAY,
                width=3.00, height=1.50,
                grid_width=64, grid_height=32,  # 假设是2×1拼接
                pressure_range=(0, 1000),
                typical_test_types=["长距离步态", "步态周期分析"]
            ),
            
            # 标准2×2米测试平台
            "standard_2x2_platform": HardwareSpec(
                name="标准测试平台 2000×2000mm",
                hardware_type=HardwareType.CUSTOM,
                width=2.00, height=2.00,
                grid_width=32, grid_height=32,
                pressure_range=(0, 1000),
                typical_test_types=["综合平衡", "动态测试"]
            )
        }

class AdaptiveCOPAnalyzer:
    """硬件自适应COP轨迹分析器"""
    
    def __init__(self, hardware_spec: Optional[HardwareSpec] = None):
        """
        初始化分析器
        
        Args:
            hardware_spec: 硬件规格，如果为None则尝试自动识别
        """
        self.hardware_spec = hardware_spec
        self.hardware_db = HardwareDatabase.get_predefined_specs()
        
        if hardware_spec:
            self._setup_hardware_params(hardware_spec)
    
    def _setup_hardware_params(self, spec: HardwareSpec):
        """设置硬件参数"""
        self.width = spec.width
        self.height = spec.height
        self.grid_width = spec.grid_width
        self.grid_height = spec.grid_height
        self.grid_scale_x = spec.grid_scale_x
        self.grid_scale_y = spec.grid_scale_y
        self.pressure_threshold = spec.pressure_threshold
        self.hardware_type = spec.hardware_type
        
        print(f"✅ 硬件配置: {spec.name}")
        print(f"   物理尺寸: {self.width}m × {self.height}m")
        print(f"   传感器网格: {self.grid_width}×{self.grid_height}")
        print(f"   分辨率: X={self.grid_scale_x*100:.2f}cm/格, Y={self.grid_scale_y*100:.2f}cm/格")
    
    def auto_detect_hardware(self, csv_data: Union[str, List[List[float]]], 
                           file_name: str = "") -> Optional[HardwareSpec]:
        """
        自动检测硬件规格
        
        Args:
            csv_data: CSV数据内容或已解析的矩阵
            file_name: 文件名（可能包含硬件信息）
            
        Returns:
            检测到的硬件规格，如果无法确定则返回None
        """
        print("🔍 开始自动检测硬件规格...")
        
        # 解析数据获取基本信息
        if isinstance(csv_data, str):
            matrix = self._parse_csv_data(csv_data)
        else:
            matrix = csv_data
        
        if not matrix:
            print("❌ 无法解析数据，使用默认硬件规格")
            return None
        
        # 获取数据特征
        data_rows = len(matrix)
        data_cols = len(matrix[0]) if matrix else 0
        total_sensors = data_rows * data_cols
        
        print(f"   数据维度: {data_rows}×{data_cols} ({total_sensors}个传感器)")
        
        # 分析文件名线索
        file_hints = self._analyze_filename_hints(file_name.lower())
        print(f"   文件名线索: {file_hints}")
        
        # 基于数据维度匹配硬件
        candidates = []
        
        for spec_id, spec in self.hardware_db.items():
            # 检查传感器数量是否匹配
            if (spec.grid_width == data_cols and spec.grid_height == data_rows) or \
               (spec.total_sensors == total_sensors):
                confidence = 50  # 基础匹配度
                
                # 文件名匹配加分
                for hint in file_hints:
                    if any(test_type in hint for test_type in spec.typical_test_types):
                        confidence += 20
                    if spec.hardware_type.value.replace('_', '') in hint.replace('_', ''):
                        confidence += 15
                
                candidates.append((spec, confidence))
        
        if not candidates:
            print("❌ 未找到匹配的硬件规格，建议手动指定")
            return None
        
        # 选择置信度最高的硬件
        best_spec, best_confidence = max(candidates, key=lambda x: x[1])
        
        print(f"✅ 检测到硬件: {best_spec.name} (置信度: {best_confidence}%)")
        
        if best_confidence < 70:
            print("⚠️  置信度较低，建议手动确认硬件规格")
        
        return best_spec
    
    def _analyze_filename_hints(self, filename: str) -> List[str]:
        """分析文件名中的硬件线索"""
        hints = []
        
        # 测试类型关键词
        test_keywords = {
            "步态": ["gait", "walk", "步态", "行走"],
            "平衡": ["balance", "站立", "平衡", "稳定"],
            "坐立": ["sit", "stand", "坐立", "起立"],
            "足压": ["foot", "pressure", "足压", "脚部"],
            "臀部": ["hip", "臀部", "坐垫"]
        }
        
        for category, keywords in test_keywords.items():
            if any(keyword in filename for keyword in keywords):
                hints.append(category)
        
        return hints
    
    def _parse_csv_data(self, csv_content: str) -> List[List[float]]:
        """解析CSV数据为压力矩阵"""
        lines = csv_content.strip().split('\n')
        data_matrix = []
        
        for line in lines[1:]:  # 跳过表头
            if line.strip():
                values = line.split(',')
                # 自动检测数据列数
                if len(values) >= 32:  # 标准32列格式
                    row_data = [float(val) if val.strip() else 0.0 
                               for val in values[:32]]
                    data_matrix.append(row_data)
                elif len(values) == 6:  # 肌少症6列格式
                    # 解析data字段中的1024个数值
                    data_field = values[5].strip('[]')
                    if data_field:
                        pressure_values = [float(x) for x in data_field.split()]
                        if len(pressure_values) == 1024:
                            # 重塑为32×32矩阵
                            matrix_32x32 = np.array(pressure_values).reshape(32, 32)
                            data_matrix.extend(matrix_32x32.tolist())
        
        return data_matrix
    
    def calculate_cop_position(self, pressure_matrix: List[List[float]]) -> Optional[Dict]:
        """
        计算COP位置 - 硬件自适应版本
        
        Args:
            pressure_matrix: 压力矩阵
            
        Returns:
            COP位置信息，包含物理坐标
        """
        if not self.hardware_spec:
            raise ValueError("未设置硬件规格，无法计算物理坐标")
        
        if not pressure_matrix:
            return None
            
        total_pressure = 0
        weighted_x = 0
        weighted_y = 0
        active_cells = 0
        
        rows = len(pressure_matrix)
        cols = len(pressure_matrix[0]) if pressure_matrix else 0
        
        for row in range(rows):
            for col in range(min(cols, len(pressure_matrix[row]))):
                pressure = pressure_matrix[row][col]
                if pressure > self.pressure_threshold:
                    # 转换为物理坐标 - 硬件自适应
                    x = col * self.grid_scale_x + self.grid_scale_x / 2
                    y = row * self.grid_scale_y + self.grid_scale_y / 2
                    
                    total_pressure += pressure
                    weighted_x += x * pressure
                    weighted_y += y * pressure
                    active_cells += 1
        
        if total_pressure > 0.5 and active_cells >= 3:
            return {
                'x': weighted_x / total_pressure,
                'y': weighted_y / total_pressure,
                'total_pressure': total_pressure,
                'active_cells': active_cells,
                'hardware_type': self.hardware_type.value,
                'physical_bounds': {
                    'width': self.width,
                    'height': self.height
                }
            }
        
        return None
    
    def analyze_balance_adaptive(self, pressure_data: List[List[List[float]]]) -> Dict:
        """
        硬件自适应平衡分析
        
        Args:
            pressure_data: 时间序列压力数据
            
        Returns:
            平衡分析结果，包含硬件校正后的指标
        """
        if not self.hardware_spec:
            raise ValueError("未设置硬件规格，无法进行自适应分析")
        
        cop_trajectory = []
        
        for frame in pressure_data:
            cop = self.calculate_cop_position(frame)
            if cop:
                cop_trajectory.append({
                    'x': cop['x'], 
                    'y': cop['y'],
                    'pressure': cop['total_pressure']
                })
        
        if len(cop_trajectory) < 3:
            return {'error': 'Insufficient data for balance analysis'}
        
        # 标准COP分析
        result = self._calculate_standard_cop_metrics(cop_trajectory)
        
        # 添加硬件信息
        result['hardware_info'] = {
            'name': self.hardware_spec.name,
            'type': self.hardware_spec.hardware_type.value,
            'physical_size': f"{self.width}m×{self.height}m",
            'resolution': f"{self.grid_scale_x*100:.2f}×{self.grid_scale_y*100:.2f}cm/格"
        }
        
        # 硬件特定的归一化处理
        result = self._normalize_metrics_by_hardware(result)
        
        return result
    
    def _calculate_standard_cop_metrics(self, trajectory: List[Dict]) -> Dict:
        """计算标准COP指标"""
        x_positions = [pos['x'] for pos in trajectory]
        y_positions = [pos['y'] for pos in trajectory]
        
        # 质心计算
        center_x = np.mean(x_positions)
        center_y = np.mean(y_positions)
        
        # 95%置信椭圆面积
        cop_area = self._calculate_cop_95_percent_ellipse(trajectory)
        
        # 轨迹总长度
        total_distance = 0
        for i in range(1, len(trajectory)):
            dx = trajectory[i]['x'] - trajectory[i-1]['x']
            dy = trajectory[i]['y'] - trajectory[i-1]['y']
            total_distance += np.sqrt(dx**2 + dy**2)
        
        # 前后、左右摆动范围
        ap_range = max(y_positions) - min(y_positions)
        ml_range = max(x_positions) - min(x_positions)
        
        # 轨迹复杂度
        complexity = self._calculate_trajectory_complexity(trajectory)
        
        # 稳定性指数
        stability_index = self._calculate_stability_index(
            total_distance, cop_area, total_distance/len(trajectory), 
            max([np.sqrt((pos['x'] - center_x)**2 + (pos['y'] - center_y)**2) 
                 for pos in trajectory])
        )
        
        return {
            'copArea': cop_area * 10000,                # cm²
            'copPathLength': total_distance * 100,      # cm
            'copComplexity': complexity,                # /10
            'anteroPosteriorRange': ap_range * 100,     # cm
            'medioLateralRange': ml_range * 100,        # cm
            'stabilityIndex': stability_index,          # %
            'center_x': center_x,
            'center_y': center_y
        }
    
    def _normalize_metrics_by_hardware(self, metrics: Dict) -> Dict:
        """根据硬件特性归一化指标"""
        # 根据硬件类型调整参考标准
        if self.hardware_type == HardwareType.HIP_PRESSURE_PAD:
            # 臀部压力垫的参考范围不同
            metrics['reference_ranges'] = {
                'copArea': '<30 cm² (正常)',
                'copPathLength': '10-25 cm (正常)',
                'anteroPosteriorRange': '1-4 cm (正常)',
                'medioLateralRange': '1-3 cm (正常)'
            }
        elif self.hardware_type == HardwareType.FOOT_PRESSURE_PAD:
            # 足压垫标准参考范围
            metrics['reference_ranges'] = {
                'copArea': '<50 cm² (正常)',
                'copPathLength': '15-40 cm (正常)',
                'anteroPosteriorRange': '2-6 cm (正常)',
                'medioLateralRange': '1-4 cm (正常)'
            }
        else:
            # 其他硬件使用通用标准
            metrics['reference_ranges'] = {
                'copArea': '<80 cm² (正常)',
                'copPathLength': '20-60 cm (正常)',
                'anteroPosteriorRange': '3-10 cm (正常)',
                'medioLateralRange': '2-8 cm (正常)'
            }
        
        return metrics
    
    def _calculate_cop_95_percent_ellipse(self, positions: List[Dict]) -> float:
        """计算95%置信椭圆面积"""
        if len(positions) < 3:
            return 0.0
        
        center_x = np.mean([p['x'] for p in positions])
        center_y = np.mean([p['y'] for p in positions])
        
        # 协方差矩阵计算
        cov_xx = np.mean([(p['x'] - center_x)**2 for p in positions])
        cov_yy = np.mean([(p['y'] - center_y)**2 for p in positions])
        
        # 95%置信椭圆
        chi2 = 5.991  # 卡方分布95%置信度，自由度=2
        a = np.sqrt(chi2 * cov_xx)
        b = np.sqrt(chi2 * cov_yy)
        
        return np.pi * a * b
    
    def _calculate_trajectory_complexity(self, positions: List[Dict]) -> float:
        """计算轨迹复杂度"""
        if len(positions) < 5:
            return 1.0
        
        direction_changes = 0
        
        for i in range(2, len(positions)):
            v1x = positions[i-1]['x'] - positions[i-2]['x']
            v1y = positions[i-1]['y'] - positions[i-2]['y']
            v2x = positions[i]['x'] - positions[i-1]['x']
            v2y = positions[i]['y'] - positions[i-1]['y']
            
            cross = v1x * v2y - v1y * v2x
            
            if abs(cross) > 0.001:
                direction_changes += 1
        
        complexity_ratio = direction_changes / len(positions)
        return min(10.0, round(complexity_ratio * 20, 1))
    
    def _calculate_stability_index(self, path_length: float, sway_area: float, 
                                 velocity: float, max_displacement: float) -> float:
        """计算稳定性指数"""
        score = 100.0
        
        # 根据硬件尺寸调整评分标准
        size_factor = np.sqrt(self.width * self.height)  # 硬件尺寸因子
        
        # 路径长度评分（考虑硬件尺寸）
        norm_path_length = path_length / size_factor
        if norm_path_length > 0.5:
            score -= 20
        elif norm_path_length > 0.35:
            score -= 10
        elif norm_path_length > 0.25:
            score -= 5
        
        # 摆动面积评分
        norm_sway_area = sway_area / (size_factor ** 2)
        if norm_sway_area > 0.0005:
            score -= 15
        elif norm_sway_area > 0.0003:
            score -= 8
        elif norm_sway_area > 0.0001:
            score -= 3
        
        return max(0.0, min(100.0, score))

def create_analyzer_from_csv(csv_file_path: str, 
                           hardware_spec: Optional[HardwareSpec] = None) -> AdaptiveCOPAnalyzer:
    """
    从CSV文件创建自适应分析器
    
    Args:
        csv_file_path: CSV文件路径
        hardware_spec: 可选的硬件规格，如果不提供则自动检测
        
    Returns:
        配置好的自适应COP分析器
    """
    with open(csv_file_path, 'r', encoding='utf-8') as f:
        csv_content = f.read()
    
    analyzer = AdaptiveCOPAnalyzer(hardware_spec)
    
    if not hardware_spec:
        detected_spec = analyzer.auto_detect_hardware(csv_content, csv_file_path)
        if detected_spec:
            analyzer.hardware_spec = detected_spec
            analyzer._setup_hardware_params(detected_spec)
        else:
            print("⚠️  无法自动检测硬件，使用默认配置")
            # 使用最常见的配置作为默认值
            default_spec = HardwareDatabase.get_predefined_specs()["foot_pad_1100x650"]
            analyzer.hardware_spec = default_spec
            analyzer._setup_hardware_params(default_spec)
    
    return analyzer

# 使用示例
if __name__ == "__main__":
    print("🔧 硬件自适应COP分析器测试")
    
    # 列出所有预定义硬件
    print("\n📋 支持的硬件规格:")
    specs = HardwareDatabase.get_predefined_specs()
    for spec_id, spec in specs.items():
        print(f"  {spec_id}: {spec.name}")
        print(f"    尺寸: {spec.width}m×{spec.height}m")
        print(f"    传感器: {spec.grid_width}×{spec.grid_height}")
        print(f"    分辨率: {spec.grid_scale_x*100:.2f}×{spec.grid_scale_y*100:.2f}cm/格")
        print()
    
    # 测试自动检测功能
    print("🧪 测试不同硬件规格下的COP计算:")
    
    # 创建测试数据
    test_data_32x32 = np.random.rand(32, 32) * 100
    test_data_32x32[15:18, 15:18] = 200  # 中心区域高压力
    
    for spec_id, spec in list(specs.items())[:2]:  # 测试前两个规格
        print(f"\n--- 测试 {spec.name} ---")
        analyzer = AdaptiveCOPAnalyzer(spec)
        
        # 计算COP
        cop = analyzer.calculate_cop_position(test_data_32x32.tolist())
        if cop:
            print(f"COP位置: ({cop['x']:.3f}m, {cop['y']:.3f}m)")
            print(f"物理坐标: ({cop['x']*100:.1f}cm, {cop['y']*100:.1f}cm)")
        
        # 模拟时间序列数据
        sequence = [test_data_32x32.tolist() for _ in range(10)]
        result = analyzer.analyze_balance_adaptive(sequence)
        
        if 'error' not in result:
            print(f"COP轨迹面积: {result['copArea']:.2f} cm²")
            print(f"参考范围: {result['reference_ranges']['copArea']}")