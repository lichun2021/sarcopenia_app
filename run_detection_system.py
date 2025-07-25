#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
肌少症检测系统启动脚本
集成了新的患者档案管理和6步检测流程
"""

import tkinter as tk
import sys
import os

def main():
    """启动肌少症检测系统"""
    try:
        # 确保当前目录正确
        script_dir = os.path.dirname(os.path.abspath(__file__))
        os.chdir(script_dir)
        
        print("🔬 启动智能肌少症检测系统...")
        print("=" * 50)
        
        # 检查关键模块
        required_modules = [
            'sarcopenia_database.py',
            'patient_manager_ui.py', 
            'detection_wizard_ui.py',
            'pressure_sensor_ui.py'
        ]
        
        missing_modules = []
        for module in required_modules:
            if not os.path.exists(module):
                missing_modules.append(module)
        
        if missing_modules:
            print(f"❌ 缺少关键模块: {', '.join(missing_modules)}")
            return
        
        print("✅ 所有关键模块检查完成")
        
        # 初始化数据库
        print("📊 初始化数据库...")
        from sarcopenia_database import db
        print("✅ 数据库初始化完成")
        
        # 创建主界面
        print("🖥️ 启动主界面...")
        root = tk.Tk()
        
        # 导入主界面类
        from pressure_sensor_ui import PressureSensorUI
        app = PressureSensorUI(root)
        
        # 设置关闭事件
        root.protocol("WM_DELETE_WINDOW", app.on_closing)
        
        print("🚀 系统启动成功！")
        print("=" * 50)
        print("功能概览:")
        print("• 👥 患者档案管理 - 新建、编辑、查询患者信息")
        print("• 🔬 6步检测流程 - 翻页式检测向导")
        print("• 📊 数据收集 - 自动保存检测数据为CSV文件")
        print("• 🤖 AI分析 - 智能分析并生成HTML报告")
        print("• 💾 进度保存 - 支持检测中断和恢复")
        print("=" * 50)
        
        # 启动界面事件循环
        root.mainloop()
        
    except ImportError as e:
        print(f"❌ 模块导入失败: {e}")
        print("请确保所有必需的模块都在当前目录中")
    except Exception as e:
        print(f"❌ 启动失败: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()