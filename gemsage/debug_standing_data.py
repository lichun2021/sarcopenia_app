#!/usr/bin/env python3
"""
调试站立数据处理问题
"""
import pandas as pd
import numpy as np
from gait_report_generator import CompleteGaitAnalyzer

def debug_standing_data():
    """调试站立数据的处理过程"""
    print("🔍 调试站立测试数据处理...")
    
    # 读取站立数据
    csv_file = "/Users/xidada/GemSage/for test/1/曾超08-第3步-静态站立-20250809_182406.csv"
    df = pd.read_csv(csv_file)
    
    print(f"📊 CSV数据基本信息:")
    print(f"   行数: {len(df)}")
    print(f"   列: {list(df.columns)}")
    print(f"   时间范围: {df['time'].min():.3f} - {df['time'].max():.3f}s")
    
    # 创建分析器
    analyzer = CompleteGaitAnalyzer()
    
    # 分析第一行数据
    first_row = df.iloc[0]
    print(f"\n📝 第一行数据:")
    print(f"   时间: {first_row['time']}")
    print(f"   最大值: {first_row['max']}")
    print(f"   面积: {first_row['area']}")
    print(f"   压力: {first_row['press']}")
    
    # 解析压力数据
    matrix = analyzer.parse_pressure_data(first_row['data'])
    print(f"\n🔢 压力矩阵分析:")
    print(f"   形状: {matrix.shape}")
    print(f"   数据类型: {matrix.dtype}")
    print(f"   值范围: {matrix.min()} - {matrix.max()}")
    print(f"   非零值数量: {np.count_nonzero(matrix)}")
    print(f"   总和: {matrix.sum()}")
    
    # 检查高值分布
    high_values = matrix[matrix > 200]
    if len(high_values) > 0:
        print(f"   高值(>200): {len(high_values)}个")
        print(f"   高值范围: {high_values.min()} - {high_values.max()}")
        
        # 找高值位置
        high_positions = np.where(matrix > 200)
        print(f"   高值位置 (前10个): {list(zip(high_positions[0][:10], high_positions[1][:10]))}")
    
    # 可视化矩阵
    print(f"\n🗂️ 矩阵形状分析:")
    if matrix.shape == (64, 32):
        print("   64x32矩阵 - 需要下采样到32x32")
        # 分析左右脚区域
        left_foot = matrix[:, :16]  # 左半部分
        right_foot = matrix[:, 16:]  # 右半部分
        
        print(f"   左脚区域: 总和={left_foot.sum():.0f}, 最大值={left_foot.max()}")
        print(f"   右脚区域: 总和={right_foot.sum():.0f}, 最大值={right_foot.max()}")
        
        # 检查脚印中心区域
        center_region = matrix[20:45, 5:27]  # 中心区域
        print(f"   中心区域: 总和={center_region.sum():.0f}, 最大值={center_region.max()}")
        
        # 检查边缘区域
        edges = np.concatenate([
            matrix[0, :], matrix[-1, :],  # 上下边
            matrix[:, 0], matrix[:, -1]   # 左右边
        ])
        print(f"   边缘区域: 总和={edges.sum():.0f}, 最大值={edges.max()}")
    
    # 测试下采样效果
    if matrix.shape == (64, 32):
        print(f"\n⬇️ 测试下采样:")
        downsampled = analyzer._block_reduce_mean(matrix, 2, 1)
        print(f"   下采样后形状: {downsampled.shape}")
        print(f"   下采样后范围: {downsampled.min()} - {downsampled.max()}")
        print(f"   下采样后总和: {downsampled.sum()}")
        
        # 检查下采样后的脚印区域
        ds_left = downsampled[:, :16]
        ds_right = downsampled[:, 16:]
        print(f"   下采样左脚: 总和={ds_left.sum():.0f}, 最大值={ds_left.max()}")
        print(f"   下采样右脚: 总和={ds_right.sum():.0f}, 最大值={ds_right.max()}")
    
    # 生成热力图测试
    print(f"\n🎨 生成热力图测试:")
    svg_result = analyzer.generate_pressure_svg(matrix, "Debug Standing Test")
    
    with open("/Users/xidada/GemSage/debug_standing_heatmap.svg", "w") as f:
        f.write(svg_result)
    print("   热力图已保存: debug_standing_heatmap.svg")
    
    # 处理多帧数据
    print(f"\n📊 分析多帧数据:")
    pressure_matrices = []
    for i, (_, row) in enumerate(df.iterrows()):
        if i >= 10:  # 只分析前10帧
            break
        matrix = analyzer.parse_pressure_data(row['data'])
        if matrix.sum() > 0:
            pressure_matrices.append(matrix)
            print(f"   帧{i}: 形状={matrix.shape}, 总和={matrix.sum():.0f}, 最大值={matrix.max()}")
    
    if pressure_matrices:
        print(f"\n📈 有效帧统计:")
        print(f"   总有效帧数: {len(pressure_matrices)}")
        
        # 计算平均矩阵
        avg_matrix = np.mean(pressure_matrices, axis=0)
        print(f"   平均矩阵: 形状={avg_matrix.shape}, 最大值={avg_matrix.max():.1f}")
        
        # 分析左右脚
        if avg_matrix.shape[1] >= 32:
            w = avg_matrix.shape[1]
            left_avg = avg_matrix[:, :w//2]
            right_avg = avg_matrix[:, w//2:]
            
            print(f"   平均左脚: 最大值={left_avg.max():.1f}, 总和={left_avg.sum():.0f}")
            print(f"   平均右脚: 最大值={right_avg.max():.1f}, 总和={right_avg.sum():.0f}")
            
            # 这里就是报告中显示的数值来源！
            left_max_n = analyzer.calibrate_force(left_avg.max())
            right_max_n = analyzer.calibrate_force(right_avg.max())
            print(f"   标定后左脚最大值: {left_max_n:.4f}N")
            print(f"   标定后右脚最大值: {right_max_n:.4f}N")

if __name__ == "__main__":
    debug_standing_data()