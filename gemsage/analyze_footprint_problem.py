#!/usr/bin/env python3
"""
深度分析脚印显示问题
"""
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from gait_report_generator import CompleteGaitAnalyzer

def analyze_raw_data_distribution():
    """分析原始数据的空间分布"""
    print("🔍 分析原始数据的空间分布...")
    
    # 读取站立数据
    csv_file = "/Users/xidada/GemSage/for test/1/曾超08-第3步-静态站立-20250809_182406.csv"
    df = pd.read_csv(csv_file)
    
    analyzer = CompleteGaitAnalyzer()
    
    # 分析第一帧数据
    first_row = df.iloc[0]
    matrix = analyzer.parse_pressure_data(first_row['data'])
    
    print(f"📊 原始矩阵分析:")
    print(f"   形状: {matrix.shape}")
    print(f"   数据范围: {matrix.min()} - {matrix.max()}")
    print(f"   非零元素: {np.count_nonzero(matrix)}")
    
    # 检查不同区域的数据分布
    if matrix.shape == (32, 32):
        print(f"\n🗺️ 区域分析 (32x32):")
        
        # 分析不同区域
        regions = {
            "左上角 (0:8, 0:8)": matrix[0:8, 0:8],
            "右上角 (0:8, 24:32)": matrix[0:8, 24:32], 
            "左中部 (8:24, 0:16)": matrix[8:24, 0:16],
            "右中部 (8:24, 16:32)": matrix[8:24, 16:32],
            "左下角 (24:32, 0:8)": matrix[24:32, 0:8],
            "右下角 (24:32, 24:32)": matrix[24:32, 24:32],
            "中心区域 (10:22, 10:22)": matrix[10:22, 10:22],
            "边缘区域": np.concatenate([
                matrix[0, :], matrix[-1, :],  # 上下边
                matrix[:, 0], matrix[:, -1]   # 左右边
            ])
        }
        
        for name, region in regions.items():
            total = region.sum()
            max_val = region.max()
            nonzero = np.count_nonzero(region)
            print(f"   {name}: 总和={total:.0f}, 最大值={max_val:.0f}, 非零={nonzero}")
    
    # 可视化原始数据分布
    print(f"\n🎨 生成原始数据可视化...")
    
    fig, axes = plt.subplots(1, 3, figsize=(15, 5))
    
    # 原始数据热力图
    im1 = axes[0].imshow(matrix, cmap='hot', origin='upper')
    axes[0].set_title('原始数据分布')
    axes[0].grid(True, alpha=0.3)
    plt.colorbar(im1, ax=axes[0])
    
    # 二值化显示（>10的区域）
    binary = (matrix > 10).astype(int)
    im2 = axes[1].imshow(binary, cmap='gray', origin='upper')
    axes[1].set_title('压力区域 (>10)')
    axes[1].grid(True, alpha=0.3)
    plt.colorbar(im2, ax=axes[1])
    
    # 高值区域显示（>100的区域）
    high_values = (matrix > 100).astype(int)
    im3 = axes[2].imshow(high_values, cmap='Reds', origin='upper')
    axes[2].set_title('高压力区域 (>100)')
    axes[2].grid(True, alpha=0.3)
    plt.colorbar(im3, ax=axes[2])
    
    plt.tight_layout()
    plt.savefig('/Users/xidada/GemSage/raw_data_analysis.png', dpi=150, bbox_inches='tight')
    plt.close()
    print("   原始数据分析图已保存: raw_data_analysis.png")
    
    return matrix

def check_data_parsing():
    """检查数据解析是否正确"""
    print("\n🔍 检查数据解析过程...")
    
    csv_file = "/Users/xidada/GemSage/for test/1/曾超08-第3步-静态站立-20250809_182406.csv"
    df = pd.read_csv(csv_file)
    
    # 直接解析第一行的数据字符串
    data_str = df.iloc[0]['data']
    print(f"📝 原始数据字符串长度: {len(data_str)}")
    print(f"   开始部分: {data_str[:100]}...")
    print(f"   结束部分: ...{data_str[-50:]}")
    
    # 手动解析
    data_str = data_str.strip()
    if data_str.startswith('['):
        data_str = data_str[1:]
    if data_str.endswith(']'):
        data_str = data_str[:-1]
    
    values = [float(x.strip()) for x in data_str.split(',') if x.strip()]
    print(f"📊 解析后数据:")
    print(f"   数值数量: {len(values)}")
    print(f"   数值范围: {min(values)} - {max(values)}")
    print(f"   非零数量: {sum(1 for v in values if v > 0)}")
    
    # 检查不同的重塑方式
    if len(values) == 1024:  # 32x32
        print(f"\n🔄 32x32 重塑测试:")
        matrix_32x32 = np.array(values).reshape(32, 32)
        print(f"   形状: {matrix_32x32.shape}")
        print(f"   最大值位置: {np.unravel_index(matrix_32x32.argmax(), matrix_32x32.shape)}")
        print(f"   最大值区域 (15:17, 15:17): {matrix_32x32[15:17, 15:17]}")
        
        # 检查是否数据在边缘
        edge_sum = (matrix_32x32[0, :].sum() + matrix_32x32[-1, :].sum() + 
                   matrix_32x32[:, 0].sum() + matrix_32x32[:, -1].sum())
        total_sum = matrix_32x32.sum()
        edge_ratio = edge_sum / total_sum if total_sum > 0 else 0
        print(f"   边缘数据占比: {edge_ratio:.2%}")
        
    elif len(values) == 2048:  # 64x32
        print(f"\n🔄 64x32 重塑测试:")
        matrix_64x32 = np.array(values).reshape(64, 32)
        print(f"   形状: {matrix_64x32.shape}")
        print(f"   最大值位置: {np.unravel_index(matrix_64x32.argmax(), matrix_64x32.shape)}")
        
        # 测试不同的脚部区域
        left_foot_region = matrix_64x32[20:50, 5:15]  # 左脚区域
        right_foot_region = matrix_64x32[20:50, 20:30]  # 右脚区域
        print(f"   左脚区域总和: {left_foot_region.sum()}")
        print(f"   右脚区域总和: {right_foot_region.sum()}")
    
    return values

def test_different_reshaping():
    """测试不同的数据重塑方式"""
    print("\n🧪 测试不同的数据重塑方式...")
    
    csv_file = "/Users/xidada/GemSage/for test/1/曾超08-第3步-静态站立-20250809_182406.csv"
    df = pd.read_csv(csv_file)
    analyzer = CompleteGaitAnalyzer()
    
    # 获取原始数据
    data_str = df.iloc[0]['data']
    data_str = data_str.strip()
    if data_str.startswith('['):
        data_str = data_str[1:]
    if data_str.endswith(']'):
        data_str = data_str[:-1]
    values = [float(x.strip()) for x in data_str.split(',') if x.strip()]
    
    if len(values) == 1024:
        # 测试不同的排列方式
        print(f"📊 测试不同的32x32排列:")
        
        # 标准行优先 (row-major)
        matrix_row = np.array(values).reshape(32, 32)
        print(f"   行优先最大值: {matrix_row.max()}")
        print(f"   行优先最大值位置: {np.unravel_index(matrix_row.argmax(), matrix_row.shape)}")
        
        # 列优先 (column-major)
        matrix_col = np.array(values).reshape(32, 32, order='F')
        print(f"   列优先最大值: {matrix_col.max()}")
        print(f"   列优先最大值位置: {np.unravel_index(matrix_col.argmax(), matrix_col.shape)}")
        
        # 尝试转置
        matrix_transpose = matrix_row.T
        print(f"   转置最大值: {matrix_transpose.max()}")
        print(f"   转置最大值位置: {np.unravel_index(matrix_transpose.argmax(), matrix_transpose.shape)}")
        
        # 可视化对比
        fig, axes = plt.subplots(1, 3, figsize=(15, 5))
        
        im1 = axes[0].imshow(matrix_row, cmap='hot', origin='upper')
        axes[0].set_title('行优先 (当前使用)')
        plt.colorbar(im1, ax=axes[0])
        
        im2 = axes[1].imshow(matrix_col, cmap='hot', origin='upper')  
        axes[1].set_title('列优先')
        plt.colorbar(im2, ax=axes[1])
        
        im3 = axes[2].imshow(matrix_transpose, cmap='hot', origin='upper')
        axes[2].set_title('转置')
        plt.colorbar(im3, ax=axes[2])
        
        plt.tight_layout()
        plt.savefig('/Users/xidada/GemSage/reshape_comparison.png', dpi=150, bbox_inches='tight')
        plt.close()
        print("   重塑方式对比图已保存: reshape_comparison.png")

def main():
    """主函数"""
    print("🕵️ 深度分析脚印显示问题")
    print("=" * 50)
    
    # 分析原始数据分布
    matrix = analyze_raw_data_distribution()
    
    # 检查数据解析
    values = check_data_parsing()
    
    # 测试不同重塑方式
    test_different_reshaping()
    
    print(f"\n💡 问题分析结论:")
    print(f"   1. 数据解析正确，包含{len(values)}个数值")
    print(f"   2. 数据重塑可能有问题，需要验证行列映射关系")
    print(f"   3. 可能的脚印区域分布与预期不符")
    print(f"   4. 传感器布局可能与代码假设不一致")

if __name__ == "__main__":
    main()