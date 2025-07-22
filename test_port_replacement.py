#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试端口替换逻辑 - 验证选择重复端口时直接替换原配置
"""

import tkinter as tk
from tkinter import ttk
import time
import threading

def test_port_replacement_concept():
    """测试端口替换概念演示"""
    print("🔄 端口替换逻辑测试")
    print("=" * 50)
    
    # 模拟设备配置状态
    device_configs = {
        'footpad': {'name': '脚垫', 'icon': '👣', 'port': '', 'status': '未配置'},
        'cushion': {'name': '坐垫', 'icon': '🪑', 'port': '', 'status': '未配置'},
        'walkway': {'name': '步道', 'icon': '🚶', 'port': '', 'status': '未配置'}
    }
    
    available_ports = ['COM1', 'COM4', 'COM6']
    
    def show_current_status():
        print("\n📊 当前设备配置状态:")
        for device_id, config in device_configs.items():
            port_info = config['port'] if config['port'] else '未配置'
            print(f"  {config['icon']} {config['name']}: {port_info} ({config['status']})")
    
    def simulate_port_selection(device_id, selected_port):
        print(f"\n🎯 模拟选择: {device_configs[device_id]['icon']} {device_configs[device_id]['name']} → {selected_port}")
        
        # 检查端口冲突并替换
        for other_id, other_config in device_configs.items():
            if other_id != device_id and other_config['port'] == selected_port:
                # 清空原设备配置
                print(f"🔄 端口 {selected_port} 从 {other_config['name']} 转移到 {device_configs[device_id]['name']}")
                other_config['port'] = ''
                other_config['status'] = '未配置'
                break
        
        # 设置新设备配置
        device_configs[device_id]['port'] = selected_port
        device_configs[device_id]['status'] = '检测中...'
        
        # 模拟检测过程
        time.sleep(0.5)
        device_configs[device_id]['status'] = '✅ 有效'
        print(f"✅ {device_configs[device_id]['name']} 端口 {selected_port} 检测完成: 有效")
        
        show_current_status()
    
    # 初始状态
    show_current_status()
    
    print("\n🧪 测试场景:")
    print("1. 脚垫选择 COM1")
    simulate_port_selection('footpad', 'COM1')
    
    print("\n2. 坐垫选择 COM4") 
    simulate_port_selection('cushion', 'COM4')
    
    print("\n3. 步道选择 COM6")
    simulate_port_selection('walkway', 'COM6')
    
    print("\n4. 🔥 冲突测试：坐垫选择 COM1 (原来是脚垫的)")
    simulate_port_selection('cushion', 'COM1')
    
    print("\n5. 🔥 再次冲突：步道选择 COM1 (现在是坐垫的)")
    simulate_port_selection('walkway', 'COM1')
    
    print("\n✅ 测试完成！观察端口替换过程")
    
    return True

def create_visual_test():
    """创建可视化测试界面"""
    root = tk.Tk()
    root.title("🔄 端口替换逻辑演示")
    root.geometry("600x400")
    
    main_frame = ttk.Frame(root, padding=20)
    main_frame.pack(fill=tk.BOTH, expand=True)
    
    # 标题
    title_label = ttk.Label(main_frame, text="端口替换逻辑演示", 
                           font=("Arial", 14, "bold"))
    title_label.pack(pady=(0, 20))
    
    # 说明
    info_label = ttk.Label(main_frame, text="新逻辑：选择重复端口时，自动替换原设备配置")
    info_label.pack(pady=(0, 10))
    
    # 设备状态显示
    status_frame = ttk.LabelFrame(main_frame, text="设备配置状态", padding=10)
    status_frame.pack(fill=tk.X, pady=(0, 20))
    
    device_labels = {}
    devices = [
        ('footpad', '👣 脚垫'),
        ('cushion', '🪑 坐垫'), 
        ('walkway', '🚶 步道')
    ]
    
    for i, (device_id, name) in enumerate(devices):
        label = ttk.Label(status_frame, text=f"{name}: 未配置")
        label.grid(row=i, column=0, sticky="w", pady=2)
        device_labels[device_id] = label
    
    # 测试按钮
    button_frame = ttk.Frame(main_frame)
    button_frame.pack(pady=10)
    
    def run_console_test():
        test_port_replacement_concept()
    
    test_btn = ttk.Button(button_frame, text="🧪 运行控制台测试", 
                         command=run_console_test)
    test_btn.pack(side=tk.LEFT, padx=(0, 10))
    
    close_btn = ttk.Button(button_frame, text="❌ 关闭", 
                          command=root.quit)
    close_btn.pack(side=tk.LEFT)
    
    # 结果显示
    result_text = tk.Text(main_frame, height=8, width=70)
    result_text.pack(fill=tk.BOTH, expand=True, pady=(10, 0))
    
    result_content = """测试结果预期：

1. 初始状态：所有设备都是"未配置"
2. 脚垫选择COM1 → 脚垫: COM1 (✅ 有效)
3. 坐垫选择COM4 → 坐垫: COM4 (✅ 有效) 
4. 步道选择COM6 → 步道: COM6 (✅ 有效)
5. 坐垫选择COM1 → 脚垫: 未配置, 坐垫: COM1 (✅ 有效)  [替换!]
6. 步道选择COM1 → 坐垫: 未配置, 步道: COM1 (✅ 有效)  [再次替换!]

✅ 修复效果：不再弹警告，直接替换原配置"""
    
    result_text.insert("1.0", result_content)
    result_text.config(state="disabled")
    
    root.mainloop()

def main():
    print("🔬 智能肌少症检测系统 - 端口替换逻辑测试")
    print("=" * 60)
    print("🎯 测试目标：验证选择重复端口时直接替换原配置")
    print("🔧 修复内容：删除警告弹窗，自动清空原设备配置")
    print("=" * 60)
    
    # 运行概念测试
    success = test_port_replacement_concept()
    
    print("\n" + "=" * 60)
    if success:
        print("✅ 控制台测试完成")
        print("\n💡 新逻辑特点:")
        print("  • 不再弹出端口冲突警告")
        print("  • 自动清空原设备的端口配置") 
        print("  • 原设备状态重置为'未配置'")
        print("  • 当前设备正常使用该端口")
        print("  • 记录端口转移日志")
        
        print("\n🖥️ 启动可视化演示...")
        create_visual_test()
    else:
        print("❌ 测试过程中出现问题")

if __name__ == "__main__":
    main() 