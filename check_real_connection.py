#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
检查实际连接状态 - 确认是否真的连接到多个COM口
"""

import sys
import os
import time

# 添加当前目录到路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def check_serial_interface_status():
    """检查当前运行程序的串口接口状态"""
    print("🔍 检查当前运行程序的串口接口状态")
    print("=" * 60)
    
    try:
        # 检查date.py中的端口扫描
        from date import find_available_ports
        
        print("📡 扫描可用端口:")
        available_ports = find_available_ports()
        for port in available_ports:
            print(f"  - {port['device']}: {port['description']}")
        
        print(f"\n可用端口总数: {len(available_ports)}")
        
    except Exception as e:
        print(f"❌ 端口扫描失败: {e}")

def simulate_multi_port_check():
    """模拟检查多端口配置"""
    print("\n🔧 模拟多端口接口配置检查")
    print("=" * 60)
    
    try:
        from serial_interface import SerialInterface
        
        # 创建接口实例
        interface = SerialInterface()
        
        # 测试双端口配置
        dual_config = [
            {'port': 'COM6', 'device_id': 0},
            {'port': 'COM7', 'device_id': 1}
        ]
        
        print(f"📋 测试配置: {dual_config}")
        
        # 设置多端口配置
        interface.set_multi_port_config(dual_config)
        
        # 检查配置结果
        print(f"🔍 配置结果检查:")
        print(f"  - multi_port_config: {getattr(interface, 'multi_port_config', 'None')}")
        print(f"  - device_type: {getattr(interface, 'device_type', 'None')}")
        print(f"  - expected_device_frames: {getattr(interface, 'expected_device_frames', 'None')}")
        print(f"  - is_multi_device_mode: {getattr(interface, 'is_multi_device_mode', 'None')}")
        
        # 检查多端口相关属性
        print(f"  - serial_ports: {getattr(interface, 'serial_ports', 'None')}")
        print(f"  - device_data_buffers: {getattr(interface, 'device_data_buffers', 'None')}")
        
        # 模拟连接测试
        print(f"\n🔌 模拟连接测试:")
        try:
            # 注意：这里不会真正连接，只是测试连接逻辑
            print("  准备连接多端口设备...")
            if hasattr(interface, '_connect_multi_port'):
                print("  ✅ _connect_multi_port 方法存在")
            else:
                print("  ❌ _connect_multi_port 方法缺失")
                
            if hasattr(interface, '_multi_port_data_merger'):
                print("  ✅ _multi_port_data_merger 方法存在")
            else:
                print("  ❌ _multi_port_data_merger 方法缺失")
                
        except Exception as e:
            print(f"  ❌ 连接测试失败: {e}")
        
        return True
        
    except Exception as e:
        print(f"❌ 多端口配置检查失败: {e}")
        return False

def check_device_manager_config():
    """检查设备管理器配置"""
    print("\n📱 检查设备管理器配置")
    print("=" * 60)
    
    try:
        from device_config import DeviceManager
        
        # 模拟设备配置
        test_device_configs = {
            'walkway_dual': {
                'name': '步道',
                'icon': '🚶',
                'array_size': '32x64',
                'com_ports': 2,
                'ports': ['COM6', 'COM7'],
                'device_type': 'dual_1024'
            }
        }
        
        print(f"📋 测试设备配置: {test_device_configs}")
        
        # 创建设备管理器
        device_manager = DeviceManager()
        device_manager.setup_devices(test_device_configs)
        
        # 检查设备接口
        print(f"🔍 设备接口检查:")
        for device_id, interface in device_manager.serial_interfaces.items():
            print(f"  设备ID: {device_id}")
            print(f"  接口类型: {type(interface)}")
            
            if hasattr(interface, 'multi_port_config'):
                print(f"  多端口配置: {interface.multi_port_config}")
            else:
                print(f"  多端口配置: 未设置")
                
            if hasattr(interface, 'device_type'):
                print(f"  设备类型: {interface.device_type}")
            else:
                print(f"  设备类型: 未设置")
                
            print("-" * 30)
        
        return True
        
    except Exception as e:
        print(f"❌ 设备管理器配置检查失败: {e}")
        return False

def analyze_current_issue():
    """分析当前问题"""
    print("\n🧐 问题分析")
    print("=" * 60)
    
    print("📊 根据用户反馈：")
    print("  - ✅ 有图像显示（说明数据处理正常）")
    print("  - ❌ 显示的是同个COM口的数据")
    print("  - ❓ 步道设备应该是多个COM口数据合并")
    
    print("\n🔍 可能的问题原因：")
    print("  1. 设备配置时只连接了一个COM口")
    print("  2. 多端口连接建立失败，回退到单端口模式")
    print("  3. 多端口数据合并线程未启动")
    print("  4. 现有单端口连接未正确断开和转换")
    
    print("\n💡 建议检查步骤：")
    print("  1. 确认设备配置中确实配置了多个端口")
    print("  2. 检查多端口连接是否成功建立")
    print("  3. 确认数据合并线程是否正在运行")
    print("  4. 验证JQ转换是否对每个端口的数据都执行了")

def main():
    """主函数"""
    print("🚀 实际连接状态检查工具")
    print("=" * 70)
    
    # 运行检查
    tests = [
        ("串口接口状态", check_serial_interface_status),
        ("多端口配置模拟", simulate_multi_port_check),
        ("设备管理器配置", check_device_manager_config),
        ("问题分析", analyze_current_issue)
    ]
    
    for test_name, test_func in tests:
        try:
            print(f"\n🔍 {test_name}")
            test_func()
        except Exception as e:
            print(f"❌ {test_name} 异常: {e}")
    
    print("\n" + "=" * 70)
    print("📋 检查完成")
    print("\n💬 如果步道设备应该连接多个COM口但实际只显示单个COM口数据：")
    print("   1. 检查设备配置对话框中是否真的配置了COM6和COM7两个端口")
    print("   2. 确认多端口连接建立成功（应该看到'所有X个端口连接成功'的消息）")
    print("   3. 检查是否有'多端口数据合并线程已启动'的日志")
    print("   4. 确认数据处理中看到JQ转换成功的消息")
    print("=" * 70)

if __name__ == "__main__":
    main()