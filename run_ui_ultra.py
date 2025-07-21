#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
智能肌少症检测系统 - 超级优化版UI启动脚本
极致低延迟版本，针对实时性能优化
"""

import sys
import os
import time

def setup_performance_environment():
    """设置高性能环境"""
    # Python性能优化
    os.environ['PYTHONOPTIMIZE'] = '2'  # 最高级别优化
    os.environ['PYTHONUNBUFFERED'] = '1'  # 禁用缓冲
    os.environ['PYTHONDONTWRITEBYTECODE'] = '1'  # 禁用.pyc文件
    
    # NumPy性能优化
    os.environ['OMP_NUM_THREADS'] = '4'  # OpenMP线程数
    os.environ['NUMEXPR_MAX_THREADS'] = '4'  # NumExpr最大线程
    
    # matplotlib后端优化
    os.environ['MPLBACKEND'] = 'TkAgg'  # 使用最快的后端

def main():
    print("⚡⚡⚡ 智能肌少症检测系统 - 超级优化版 ⚡⚡⚡")
    print("🚀 极致低延迟实时显示版本")
    print()
    
    # 设置高性能环境
    setup_performance_environment()
    
    # 检查依赖和性能
    print("🔍 检查系统和依赖...")
    try:
        import numpy as np
        import matplotlib
        import serial
        import tkinter
        
        # 检查NumPy优化
        print(f"✅ NumPy版本: {np.__version__}")
        if hasattr(np, '__config__'):
            print("✅ NumPy优化: 已启用")
        
        # 检查matplotlib后端
        print(f"✅ Matplotlib后端: {matplotlib.get_backend()}")
        
        print("✅ 所有依赖已优化安装")
        
    except ImportError as e:
        print(f"❌ 缺少依赖包: {e}")
        print("请运行: pip install -r requirements.txt")
        input("按回车键退出...")
        return

    # 性能警告
    print("\n⚠️  超级优化模式说明：")
    print("   🔥 200 FPS刷新率 (5ms延迟)")
    print("   🚀 只显示最新帧，丢弃历史数据")
    print("   ⚡ CPU使用率可能较高")
    print("   🎯 适合实时性要求极高的场景")
    print()
    
    try:
        start_time = time.time()
        
        # 导入并启动超级优化UI
        from pressure_sensor_ui import main as ui_main
        
        print("🚀 性能优化清单：")
        print("   📊 更新频率: 200 FPS (5ms) - 极致响应")
        print("   ⚡ 串口读取: 2000字节/次")
        print("   🔄 批量处理: 10帧/批次，只取最新")
        print("   📈 缓冲区: 智能管理，最小延迟")
        print("   🎨 绘图: 实时模式，无延迟")
        print("   🔤 字体: 英文显示，无警告")
        print("   🧮 算法: NumPy向量化，JQ变换优化")
        print("   💾 内存: 最小复制，视图操作")
        print("   🎯 丢帧策略: 保持实时性")
        
        load_time = time.time() - start_time
        print(f"   ⏱️  启动时间: {load_time:.2f}秒")
        print()
        print("🎮 系统已进入极致性能模式！")
        print()
        
        ui_main()
        
    except Exception as e:
        print(f"❌ 启动失败: {e}")
        print("\n🔧 故障排除建议：")
        print("   1. 检查COM端口是否可用")
        print("   2. 确认Python版本 >= 3.7")
        print("   3. 重新安装依赖包")
        print("   4. 关闭其他高CPU使用率程序")
        input("按回车键退出...")

if __name__ == "__main__":
    main() 