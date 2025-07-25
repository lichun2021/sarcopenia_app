#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试水平合并逻辑的简单脚本
"""

import numpy as np
import sys
import os

# 添加当前目录到路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from data_processor import DataProcessor

def test_horizontal_merge():
    """测试水平合并逻辑"""
    print("🧪 测试水平数据合并逻辑")
    
    # 创建JQ转换处理器
    jq_processor = DataProcessor(32, 32)
    
    # 模拟两个设备的原始数据（每个1024字节）
    device1_data = np.random.randint(0, 100, 1024, dtype=np.uint8)
    device2_data = np.random.randint(100, 200, 1024, dtype=np.uint8)
    
    print(f"设备1数据: {len(device1_data)}字节, 数据范围: {device1_data.min()}-{device1_data.max()}")
    print(f"设备2数据: {len(device2_data)}字节, 数据范围: {device2_data.min()}-{device2_data.max()}")
    
    # 模拟JQ转换过程
    device_matrices = []
    
    for i, raw_data in enumerate([device1_data, device2_data], 1):
        try:
            # JQ转换
            transformed_data = jq_processor.jqbed_transform(raw_data)
            matrix_32x32 = transformed_data.reshape(32, 32)
            device_matrices.append(matrix_32x32)
            print(f"设备{i}: JQ转换成功, 矩阵形状: {matrix_32x32.shape}")
        except Exception as e:
            # 转换失败，使用原始数据
            matrix_32x32 = raw_data.reshape(32, 32)
            device_matrices.append(matrix_32x32)
            print(f"设备{i}: JQ转换失败({e}), 使用原始数据")
    
    # 水平合并矩阵（左右拼接）
    combined_matrix = np.hstack(device_matrices)  # 32x64
    print(f"水平合并结果: {combined_matrix.shape}")
    
    # 转换为字节数据
    combined_data = combined_matrix.ravel().astype(np.uint8).tobytes()
    print(f"合并后数据长度: {len(combined_data)}字节")
    
    # 验证数据完整性
    left_half = combined_matrix[:, :32]  # 左半部分
    right_half = combined_matrix[:, 32:]  # 右半部分
    
    print(f"左半部分数据范围: {left_half.min()}-{left_half.max()}")
    print(f"右半部分数据范围: {right_half.min()}-{right_half.max()}")
    
    # 检查是否正确分离
    if np.array_equal(left_half, device_matrices[0]):
        print("✅ 左半部分数据正确对应设备1")
    else:
        print("❌ 左半部分数据不匹配设备1")
        
    if np.array_equal(right_half, device_matrices[1]):
        print("✅ 右半部分数据正确对应设备2")
    else:
        print("❌ 右半部分数据不匹配设备2")
    
    return combined_matrix, combined_data

def test_data_processor_with_horizontal_data():
    """测试数据处理器处理水平合并数据"""
    print("\n🔄 测试数据处理器处理32x64数据")
    
    # 创建数据处理器，设置为32x64
    data_processor = DataProcessor(32, 64)
    
    # 获取上一步的合并数据
    combined_matrix, combined_data = test_horizontal_merge()
    
    # 创建模拟帧数据
    frame_data = {
        'data': combined_data,
        'timestamp': '12:34:56.789',
        'frame_number': 1,
        'data_length': len(combined_data)
    }
    
    # 处理数据（不启用JQ转换，因为已经在合并时处理了）
    result = data_processor.process_frame_data(frame_data, enable_jq_transform=False)
    
    if 'error' in result:
        print(f"❌ 数据处理失败: {result['error']}")
        return False
    
    processed_matrix = result['matrix_2d']
    print(f"处理后矩阵形状: {processed_matrix.shape}")
    
    # 验证数据一致性
    if np.array_equal(processed_matrix, combined_matrix):
        print("✅ 处理后的矩阵与原始合并矩阵一致")
    else:
        print("❌ 处理后的矩阵与原始合并矩阵不一致")
    
    # 显示统计信息
    stats = result['statistics']
    print(f"统计信息: Max={stats['max_value']}, Min={stats['min_value']}, Mean={stats['mean_value']:.1f}")
    
    return True

if __name__ == "__main__":
    print("=" * 60)
    test_horizontal_merge()
    print("=" * 60)
    test_data_processor_with_horizontal_data()
    print("=" * 60)