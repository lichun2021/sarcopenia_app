#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
智能肌少症检测系统 - 高性能UI启动脚本
优化延迟和响应速度
"""

import sys
import os

def main():
    print("⚡ 智能肌少症检测系统 - 高性能低延迟版本启动中...")
    
    # 优化Python性能设置
    os.environ['PYTHONOPTIMIZE'] = '1'  # 启用优化
    os.environ['PYTHONUNBUFFERED'] = '1'  # 禁用缓冲
    
    # 检查依赖
    try:
        import numpy
        import matplotlib
        import serial
        import tkinter
        print("✅ 所有依赖包已安装")
    except ImportError as e:
        print(f"❌ 缺少依赖包: {e}")
        print("请运行: pip install -r requirements.txt")
        input("按回车键退出...")
        return
    
    try:
        # 导入并启动高性能UI
        from pressure_sensor_ui import main as ui_main
        
        print("🚀 已优化设置：")
        print("   📊 更新频率: 200 FPS (5ms) - 极致响应")
        print("   ⚡ 串口读取: 2000字节/次")
        print("   🔄 多帧处理: 5帧/更新")
        print("   📈 缓冲区优化: 减少50%")
        print("   🎨 实时绘图: 无延迟模式")
        print("   🔤 字体优化: 消除中文警告")
        print("   🚀 NumPy优化: 向量化操作")
        print()
        
        ui_main()
    except Exception as e:
        print(f"❌ 启动失败: {e}")
        input("按回车键退出...")

if __name__ == "__main__":
    main() 