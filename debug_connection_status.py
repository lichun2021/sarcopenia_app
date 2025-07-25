#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
调试连接状态 - 检查多端口设备是否正确连接
"""

import sys
import os

# 添加当前目录到路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def debug_connection_status():
    """调试当前连接状态"""
    print("🔍 调试连接状态")
    print("=" * 60)
    
    try:
        # 模拟检查设备配置
        from device_config import DeviceManager
        import sqlite3
        
        # 读取保存的配置
        config_db = "device_config.db"
        if os.path.exists(config_db):
            print("📋 检查已保存的设备配置:")
            conn = sqlite3.connect(config_db)
            cursor = conn.cursor()
            
            try:
                cursor.execute("SELECT * FROM device_configs")
                rows = cursor.fetchall()
                
                for row in rows:
                    device_id, name, icon, array_size, ports_json, device_type = row
                    import json
                    ports = json.loads(ports_json) if ports_json else []
                    
                    print(f"  设备ID: {device_id}")
                    print(f"  名称: {name}")  
                    print(f"  数组大小: {array_size}")
                    print(f"  端口配置: {ports}")
                    print(f"  设备类型: {device_type}")
                    print(f"  端口数量: {len(ports)}")
                    print("-" * 40)
                    
            except Exception as e:
                print(f"❌ 读取配置失败: {e}")
            finally:
                conn.close()
        else:
            print("❌ 没有找到设备配置数据库")
            
        # 检查SerialInterface的多端口支持
        print("\n🔧 检查SerialInterface多端口支持:")
        from serial_interface import SerialInterface
        
        interface = SerialInterface()
        
        # 检查多端口相关方法
        multi_port_methods = [
            'set_multi_port_config', '_connect_multi_port', 
            '_start_multi_port_threads', '_multi_port_data_receiver',
            '_multi_port_data_merger'
        ]
        
        for method in multi_port_methods:
            if hasattr(interface, method):
                print(f"  ✅ 方法 {method} 存在")
            else:
                print(f"  ❌ 方法 {method} 缺失")
        
        # 检查多端口属性
        multi_port_attrs = [
            'multi_port_config', 'serial_ports', 'multi_port_threads',
            'device_data_buffers', 'device_frame_counts', 'sync_lock'
        ]
        
        for attr in multi_port_attrs:
            if hasattr(interface, attr):
                print(f"  ✅ 属性 {attr} 存在")
            else:
                print(f"  ❌ 属性 {attr} 缺失")
                
        # 测试多端口配置
        print("\n🧪 测试多端口配置:")
        test_config = [
            {'port': 'COM6', 'device_id': 0},
            {'port': 'COM7', 'device_id': 1}
        ]
        
        try:
            interface.set_multi_port_config(test_config)
            print("  ✅ 多端口配置设置成功")
            
            if hasattr(interface, 'multi_port_config') and interface.multi_port_config:
                print(f"  ✅ 配置保存成功: {interface.multi_port_config}")
                print(f"  ✅ 设备模式: {getattr(interface, 'device_type', 'unknown')}")
                print(f"  ✅ 预期设备帧数: {getattr(interface, 'expected_device_frames', 'unknown')}")
            else:
                print("  ❌ 配置保存失败")
                
        except Exception as e:
            print(f"  ❌ 多端口配置测试失败: {e}")
            
        return True
        
    except Exception as e:
        print(f"❌ 调试过程失败: {e}")
        return False

def check_current_connection():
    """检查当前是否有活跃连接"""
    print("\n📡 检查当前连接状态:")
    print("-" * 40)
    
    try:
        # 检查可用端口
        from date import find_available_ports
        available_ports = find_available_ports()
        
        print(f"可用端口数量: {len(available_ports)}")
        for port in available_ports:
            print(f"  - {port['device']}: {port['description']}")
            
        return True
        
    except Exception as e:
        print(f"❌ 检查连接状态失败: {e}")
        return False

def main():
    """主函数"""
    print("🚀 连接状态调试工具")
    print("=" * 70)
    
    # 运行调试检查
    tests = [
        ("连接状态调试", debug_connection_status),
        ("当前连接检查", check_current_connection)
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        print(f"\n🔍 {test_name}:")
        try:
            if test_func():
                passed += 1
                print(f"✅ {test_name} 完成")
            else:
                print(f"❌ {test_name} 失败")
        except Exception as e:
            print(f"❌ {test_name} 异常: {e}")
    
    print("\n" + "=" * 70)
    print(f"📊 调试总结: {passed}/{total} 个检查完成")
    print("=" * 70)

if __name__ == "__main__":
    main()