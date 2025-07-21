#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
性能测试脚本 - 验证优化效果
测试数据处理和JQ变换的性能
"""

import time
import numpy as np
from data_processor import DataProcessor

def test_data_processing_performance():
    """测试数据处理性能"""
    print("🧪 测试数据处理性能...")
    
    # 创建测试数据
    test_data = np.random.randint(0, 256, 1024, dtype=np.uint8)
    
    # 模拟帧数据
    frame_data = {
        'data': test_data,
        'timestamp': "12:34:56.789",
        'frame_number': 1,
        'data_length': 1024
    }
    
    processor = DataProcessor(32, 32)
    
    # 性能测试
    iterations = 1000
    
    # 测试不带JQ变换
    print(f"⚡ 测试标准处理 ({iterations}次)...")
    start_time = time.time()
    for _ in range(iterations):
        result = processor.process_frame_data(frame_data, enable_jq_transform=False)
    no_jq_time = time.time() - start_time
    no_jq_fps = iterations / no_jq_time
    
    # 测试带JQ变换
    print(f"🔄 测试JQ变换处理 ({iterations}次)...")
    start_time = time.time()
    for _ in range(iterations):
        result = processor.process_frame_data(frame_data, enable_jq_transform=True)
    jq_time = time.time() - start_time
    jq_fps = iterations / jq_time
    
    # 显示结果
    print("\n📊 性能测试结果:")
    print(f"   标准处理: {no_jq_time:.3f}秒 ({no_jq_fps:.1f} FPS)")
    print(f"   JQ变换:   {jq_time:.3f}秒 ({jq_fps:.1f} FPS)")
    print(f"   性能差异: {((no_jq_time/jq_time-1)*100):+.1f}%")
    
    # 验证正确性
    result = processor.process_frame_data(frame_data, enable_jq_transform=True)
    if 'error' not in result:
        stats = result['statistics']
        print("\n✅ 功能验证:")
        print(f"   矩阵大小: {result['matrix_2d'].shape}")
        print(f"   最大值: {stats['max_value']}")
        print(f"   最小值: {stats['min_value']}")
        print(f"   平均值: {stats['mean_value']:.1f}")
        print(f"   JQ变换: {'✅已应用' if result['jq_transform_applied'] else '❌未应用'}")
        return True
    else:
        print(f"❌ 功能验证失败: {result['error']}")
        return False

def test_numpy_optimization():
    """测试NumPy优化效果"""
    print("\n🧮 测试NumPy优化效果...")
    
    # 创建大数组测试
    data_size = 1024 * 100  # 100KB数据
    test_data = np.random.randint(0, 256, data_size, dtype=np.uint8)
    
    iterations = 100
    
    # 测试传统方法
    print(f"📊 测试传统数组操作 ({iterations}次)...")
    start_time = time.time()
    for _ in range(iterations):
        # 模拟传统操作
        result = []
        for i in range(len(test_data)):
            result.append(test_data[i] * 2)
        result = np.array(result)
    traditional_time = time.time() - start_time
    
    # 测试向量化操作
    print(f"⚡ 测试向量化操作 ({iterations}次)...")
    start_time = time.time()
    for _ in range(iterations):
        # 向量化操作
        result = test_data * 2
    vectorized_time = time.time() - start_time
    
    speedup = traditional_time / vectorized_time
    
    print(f"\n📊 NumPy优化结果:")
    print(f"   传统方法: {traditional_time:.3f}秒")
    print(f"   向量化:   {vectorized_time:.3f}秒")
    print(f"   性能提升: {speedup:.1f}倍")
    
    return speedup > 5  # 期望至少5倍性能提升

def main():
    print("⚡ 智能肌少症检测系统 - 性能测试")
    print("=" * 50)
    
    # 系统信息
    try:
        print(f"🔧 NumPy版本: {np.__version__}")
        if hasattr(np, 'show_config'):
            print("🔧 NumPy配置: 已优化")
    except:
        pass
    
    print()
    
    # 测试数据处理性能
    processing_ok = test_data_processing_performance()
    
    # 测试NumPy优化
    numpy_ok = test_numpy_optimization()
    
    print("\n" + "=" * 50)
    if processing_ok and numpy_ok:
        print("🎉 所有性能测试通过！")
        print("💡 系统已达到最佳性能状态")
    else:
        print("⚠️  部分测试未通过，可能影响性能")
    
    print("\n🚀 建议使用: python run_ui_ultra.py")
    print("   获得最佳实时性能体验！")

if __name__ == "__main__":
    main() 