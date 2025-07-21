#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
智能肌少症检测系统 - UI应用启动脚本
"""

import sys
import os

def check_dependencies():
    """检查必要的依赖包"""
    try:
        import numpy
        import matplotlib
        import serial
        import tkinter
        print("✅ 所有依赖包已安装")
        return True
    except ImportError as e:
        print(f"❌ 缺少依赖包: {e}")
        print("请运行: pip install -r requirements.txt")
        return False

def main():
    print("🔬 智能肌少症检测系统 - UI应用启动中...")
    
    # 检查依赖
    if not check_dependencies():
        input("按回车键退出...")
        return
    
    try:
        # 导入并启动UI
        from pressure_sensor_ui import main as ui_main
        ui_main()
    except Exception as e:
        print(f"❌ 启动失败: {e}")
        input("按回车键退出...")

if __name__ == "__main__":
    main() 