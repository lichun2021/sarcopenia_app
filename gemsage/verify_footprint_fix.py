#!/usr/bin/env python3
"""
验证脚印修复效果
"""
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from gait_report_generator import CompleteGaitAnalyzer

def compare_before_after():
    """对比修复前后的效果"""
    print("🔍 对比脚印修复前后效果...")
    
    # 读取站立数据
    csv_file = "/Users/xidada/GemSage/for test/1/曾超08-第3步-静态站立-20250809_182406.csv"
    df = pd.read_csv(csv_file)
    
    analyzer = CompleteGaitAnalyzer()
    
    # 分析第一帧数据
    first_row = df.iloc[0]
    matrix = analyzer.parse_pressure_data(first_row['data'])
    
    # 应用医院级处理流程
    force_N = matrix * float(analyzer.force_calibration_factor)
    kpa = analyzer._to_kpa(force_N, sensor_area_cm2=4.688)
    
    # 创建对比图
    fig, axes = plt.subplots(2, 3, figsize=(18, 12))
    
    # 上排：修复前（原始方向）
    im1 = axes[0, 0].imshow(kpa, cmap='inferno', origin='upper')
    axes[0, 0].set_title('修复前：原始方向', fontsize=14, fontweight='bold')
    axes[0, 0].grid(True, alpha=0.3)
    plt.colorbar(im1, ax=axes[0, 0])
    
    # 上排：翻转后
    kpa_flipped = np.flipud(kpa)
    im2 = axes[0, 1].imshow(kpa_flipped, cmap='inferno', origin='upper')
    axes[0, 1].set_title('修复后：上下翻转', fontsize=14, fontweight='bold')
    axes[0, 1].grid(True, alpha=0.3)
    plt.colorbar(im2, ax=axes[0, 1])
    
    # 上排：旋转180度
    kpa_rotated = np.rot90(kpa, k=2)
    im3 = axes[0, 2].imshow(kpa_rotated, cmap='inferno', origin='upper')
    axes[0, 2].set_title('备选：旋转180度', fontsize=14, fontweight='bold')
    axes[0, 2].grid(True, alpha=0.3)
    plt.colorbar(im3, ax=axes[0, 2])
    
    # 下排：二值化对比
    threshold = 5.0  # 5 kPa阈值
    
    binary_orig = (kpa > threshold).astype(int)
    axes[1, 0].imshow(binary_orig, cmap='Reds', origin='upper')
    axes[1, 0].set_title(f'原始：压力区域 (>{threshold} kPa)', fontsize=12)
    axes[1, 0].grid(True, alpha=0.3)
    
    binary_flipped = (kpa_flipped > threshold).astype(int)
    axes[1, 1].imshow(binary_flipped, cmap='Reds', origin='upper')
    axes[1, 1].set_title(f'翻转：压力区域 (>{threshold} kPa)', fontsize=12)
    axes[1, 1].grid(True, alpha=0.3)
    
    binary_rotated = (kpa_rotated > threshold).astype(int)
    axes[1, 2].imshow(binary_rotated, cmap='Reds', origin='upper')
    axes[1, 2].set_title(f'旋转：压力区域 (>{threshold} kPa)', fontsize=12)
    axes[1, 2].grid(True, alpha=0.3)
    
    # 添加COP标记
    def add_cop_marker(ax, data, label):
        """添加COP标记"""
        mat_cop = np.where(data >= 1.0, data, 0.0)
        tot = mat_cop.sum()
        if tot > 1e-9:
            yy, xx = np.mgrid[0:32, 0:32]
            cx = float((mat_cop * xx).sum() / tot)
            cy = float((mat_cop * yy).sum() / tot)
            ax.plot([cx], [cy], 'wo', markersize=8, markeredgecolor='red', markeredgewidth=2)
            ax.text(cx + 1, cy - 1, f'COP_{label}', color='white', fontsize=10, fontweight='bold')
    
    add_cop_marker(axes[0, 0], kpa, 'orig')
    add_cop_marker(axes[0, 1], kpa_flipped, 'flip')
    add_cop_marker(axes[0, 2], kpa_rotated, 'rot')
    
    plt.tight_layout()
    plt.savefig('/Users/xidada/GemSage/footprint_fix_comparison.png', dpi=200, bbox_inches='tight')
    plt.close()
    
    print("✅ 对比图已保存: footprint_fix_comparison.png")
    
    # 分析哪种方式更像脚印
    print(f"\n📊 脚印形状分析:")
    
    def analyze_footprint_shape(data, name):
        """分析脚印形状特征"""
        # 找到压力中心区域
        center_y, center_x = np.unravel_index(data.argmax(), data.shape)
        
        # 分析垂直和水平方向的压力分布
        vertical_profile = data[:, center_x]
        horizontal_profile = data[center_y, :]
        
        # 计算压力分布的"长度"（连续非零区域）
        v_nonzero = np.where(vertical_profile > 1.0)[0]
        h_nonzero = np.where(horizontal_profile > 1.0)[0]
        
        v_span = v_nonzero[-1] - v_nonzero[0] if len(v_nonzero) > 0 else 0
        h_span = h_nonzero[-1] - h_nonzero[0] if len(h_nonzero) > 0 else 0
        
        # 脚印通常是垂直方向比水平方向长
        aspect_ratio = v_span / h_span if h_span > 0 else 0
        
        print(f"   {name}:")
        print(f"     压力中心位置: ({center_x}, {center_y})")
        print(f"     垂直跨度: {v_span} 像素")
        print(f"     水平跨度: {h_span} 像素") 
        print(f"     长宽比: {aspect_ratio:.2f}")
        print(f"     压力总和: {data.sum():.0f} kPa")
        
        return aspect_ratio, center_y
    
    ratio_orig, cy_orig = analyze_footprint_shape(kpa, "原始")
    ratio_flip, cy_flip = analyze_footprint_shape(kpa_flipped, "翻转")
    ratio_rot, cy_rot = analyze_footprint_shape(kpa_rotated, "旋转")
    
    print(f"\n💡 最佳方案推荐:")
    # 脚印通常应该在下半部分，长宽比大于1
    if cy_flip > 16 and ratio_flip > 1.0:
        print(f"   ✅ 推荐使用【上下翻转】方案")
        print(f"   理由：脚印在下半部分 (y={cy_flip}), 长宽比合理 ({ratio_flip:.2f})")
    elif cy_rot > 16 and ratio_rot > 1.0:
        print(f"   ✅ 推荐使用【旋转180度】方案") 
        print(f"   理由：脚印在下半部分 (y={cy_rot}), 长宽比合理 ({ratio_rot:.2f})")
    else:
        print(f"   ⚠️ 原始方向可能是正确的")
        print(f"   或需要尝试其他变换方式")

if __name__ == "__main__":
    compare_before_after()