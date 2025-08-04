#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
调试数据结构问题
"""

import os
import sys
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from core_calculator import PressureAnalysisCore

def debug_data_structure():
    """调试数据结构"""
    # 创建测试分析器
    analyzer = PressureAnalysisCore()
    
    # 读取CSV文件
    csv_file = "/Users/xidada/foot-pressure-analysis/肌少症数据/刘云帆-步道4圈-29岁.csv"
    
    with open(csv_file, 'r', encoding='utf-8') as f:
        csv_content = f.read()
    
    # 解析数据
    print("解析CSV数据...")
    pressure_matrix = analyzer.parse_csv_data(csv_content)
    
    print(f"\n数据结构分析:")
    print(f"pressure_matrix 类型: {type(pressure_matrix)}")
    print(f"pressure_matrix 长度: {len(pressure_matrix)}")
    
    if pressure_matrix:
        print(f"第一个元素类型: {type(pressure_matrix[0])}")
        print(f"第一个元素长度: {len(pressure_matrix[0])}")
        
        if pressure_matrix[0]:
            print(f"第一个元素的第一个子元素类型: {type(pressure_matrix[0][0])}")
            
            # 检查是否所有元素都是32x32矩阵
            matrix_sizes = []
            for i, matrix in enumerate(pressure_matrix[:5]):  # 只检查前5个
                if isinstance(matrix, list) and len(matrix) > 0:
                    size = (len(matrix), len(matrix[0]) if isinstance(matrix[0], list) else 1)
                    matrix_sizes.append(size)
                    print(f"第{i+1}个矩阵大小: {size}")
    
    # 测试detect_gait_events方法
    print("\n测试detect_gait_events方法...")
    
    # 直接传递pressure_matrix
    print("直接传递pressure_matrix...")
    events1 = analyzer.detect_gait_events(pressure_matrix)
    print(f"检测到的事件数: {len(events1)}")
    
    # 如果events1为空，尝试修改数据结构
    if len(events1) == 0:
        print("\n没有检测到事件，尝试修改数据结构...")
        # 如果pressure_matrix是2D列表的列表，需要包装成3D
        if pressure_matrix and isinstance(pressure_matrix[0], list) and isinstance(pressure_matrix[0][0], (int, float)):
            # pressure_matrix是[时间帧][1024个值]，需要转换为[时间帧][32][32]
            print("检测到扁平化的数据，尝试重塑...")
            reshaped_data = []
            for frame in pressure_matrix:
                if len(frame) == 1024:  # 32x32 = 1024
                    matrix_2d = []
                    for i in range(32):
                        row = frame[i*32:(i+1)*32]
                        matrix_2d.append(row)
                    reshaped_data.append(matrix_2d)
            
            print(f"重塑后的数据长度: {len(reshaped_data)}")
            events2 = analyzer.detect_gait_events(reshaped_data)
            print(f"重塑后检测到的事件数: {len(events2)}")
            
            if events2:
                print("\n前5个事件:")
                for i, event in enumerate(events2[:5]):
                    print(f"事件{i+1}: 时间={event['timestamp']}, X={event['cop_x']:.2f}, Y={event['cop_y']:.2f}, 压力={event['pressure']:.2f}")

if __name__ == "__main__":
    debug_data_structure()