#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
实时调试多端口连接状态
"""

import sys
import os
import time

# 添加当前目录到路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def debug_device_config():
    """调试设备配置"""
    print("🔍 调试设备配置")
    print("=" * 60)
    
    try:
        # 检查是否有保存的设备配置
        import sqlite3
        import json
        
        config_db = "device_config.db"
        if not os.path.exists(config_db):
            print("❌ 设备配置数据库不存在")
            return False
            
        conn = sqlite3.connect(config_db)
        cursor = conn.cursor()
        
        try:
            cursor.execute("SELECT * FROM device_configs")
            rows = cursor.fetchall()
            
            if not rows:
                print("❌ 没有保存的设备配置")
                return False
            
            print(f"📋 找到 {len(rows)} 个设备配置:")
            for row in rows:
                device_id, name, icon, array_size, ports_json, device_type = row
                ports = json.loads(ports_json) if ports_json else []
                
                print(f"  设备: {name} ({device_id})")
                print(f"  端口: {ports} (数量: {len(ports)})")
                print(f"  类型: {device_type}")
                print(f"  数组: {array_size}")
                print("-" * 40)
                
                # 特别检查步道设备
                if '步道' in name or 'walkway' in device_id:
                    if len(ports) >= 2:
                        print(f"  ✅ 步道设备配置了多个端口: {ports}")
                    else:
                        print(f"  ❌ 步道设备只配置了 {len(ports)} 个端口")
                        
        except Exception as e:
            print(f"❌ 读取配置失败: {e}")
            return False
        finally:
            conn.close()
            
        return True
        
    except Exception as e:
        print(f"❌ 调试设备配置失败: {e}")
        return False

def test_multiport_interface():
    """测试多端口接口创建"""
    print("\n🔧 测试多端口接口创建")
    print("=" * 60)
    
    try:
        from serial_interface import SerialInterface
        
        # 创建接口
        interface = SerialInterface()
        print("✅ 创建SerialInterface成功")
        
        # 配置多端口
        test_config = [
            {'port': 'COM6', 'device_id': 0},
            {'port': 'COM7', 'device_id': 1}
        ]
        
        interface.set_multi_port_config(test_config)
        print(f"✅ 设置多端口配置: {test_config}")
        
        # 检查配置结果
        print(f"📊 配置检查:")
        print(f"  multi_port_config: {getattr(interface, 'multi_port_config', 'None')}")
        print(f"  device_type: {getattr(interface, 'device_type', 'None')}")
        print(f"  expected_device_frames: {getattr(interface, 'expected_device_frames', 'None')}")
        print(f"  is_multi_device_mode: {getattr(interface, 'is_multi_device_mode', 'None')}")
        
        # 检查多端口属性初始化
        attrs_to_check = [
            'serial_ports', 'multi_port_threads', 'device_data_buffers',
            'device_frame_counts', 'sync_lock'
        ]
        
        for attr in attrs_to_check:
            value = getattr(interface, attr, 'MISSING')
            if value != 'MISSING':
                print(f"  {attr}: {type(value)} - 已初始化")
            else:
                print(f"  {attr}: 缺失")
        
        return True
        
    except Exception as e:
        print(f"❌ 测试多端口接口失败: {e}")
        return False

def debug_connection_logic():
    """调试连接逻辑"""
    print("\n🔌 调试连接逻辑")
    print("=" * 60)
    
    try:
        from serial_interface import SerialInterface
        
        # 模拟现有连接场景
        print("📡 模拟现有单端口连接场景:")
        
        # 1. 创建单端口接口（模拟现有连接）
        old_interface = SerialInterface()
        old_interface.set_device_mode("single")
        print("  ✅ 创建模拟的现有单端口接口")
        
        # 2. 创建多端口接口（应该替换现有连接）
        new_interface = SerialInterface()
        multi_config = [
            {'port': 'COM6', 'device_id': 0},
            {'port': 'COM7', 'device_id': 1}
        ]
        new_interface.set_multi_port_config(multi_config)
        print("  ✅ 创建新的多端口接口")
        
        # 3. 比较两个接口
        print("📊 接口对比:")
        print(f"  旧接口类型: {getattr(old_interface, 'device_type', 'None')}")
        print(f"  新接口类型: {getattr(new_interface, 'device_type', 'None')}")
        print(f"  旧接口多端口配置: {getattr(old_interface, 'multi_port_config', 'None')}")
        print(f"  新接口多端口配置: {getattr(new_interface, 'multi_port_config', 'None')}")
        
        # 4. 检查连接方法差异
        print("🔍 连接方法检查:")
        
        # 检查旧接口的连接方法
        if hasattr(old_interface, 'connect'):
            print("  ✅ 旧接口有connect方法")
        else:
            print("  ❌ 旧接口缺少connect方法")
            
        # 检查新接口的多端口连接方法
        multi_methods = ['_connect_multi_port', '_multi_port_data_merger']
        for method in multi_methods:
            if hasattr(new_interface, method):
                print(f"  ✅ 新接口有{method}方法")
            else:
                print(f"  ❌ 新接口缺少{method}方法")
        
        return True
        
    except Exception as e:
        print(f"❌ 调试连接逻辑失败: {e}")
        return False

def identify_current_issue():
    """识别当前问题"""
    print("\n🧐 问题识别与分析")
    print("=" * 60)
    
    print("📋 当前状况分析:")
    print("  - 用户反馈：仍然显示同个COM口的数据")
    print("  - 预期：应该显示COM6+COM7合并的数据")
    print("  - 已修复：防止直接传递单端口连接给多端口设备")
    
    print("\n🔍 可能的问题原因:")
    print("  1. 设备配置中实际上只配置了一个端口")
    print("  2. 多端口接口创建失败，回退到单端口")
    print("  3. 多端口连接建立失败")
    print("  4. 数据合并线程未启动或工作异常")
    print("  5. 主程序仍在使用旧的接口引用")
    
    print("\n💡 调试建议:")
    print("  1. 检查设备配置对话框，确认步道设备配置了COM6和COM7")
    print("  2. 查看程序启动日志，确认看到'创建多端口接口'消息")
    print("  3. 确认看到'所有X个端口连接成功'消息")
    print("  4. 确认看到'多端口数据合并线程已启动'消息")
    print("  5. 检查是否有JQ转换成功的消息")
    
    print("\n🔧 立即检测方法:")
    print("  在程序中添加调试输出，显示:")
    print("  - 当前使用的接口类型")
    print("  - 接口的multi_port_config属性")
    print("  - 接口的device_type属性")
    print("  - 数据长度（单端口1024字节 vs 多端口2048字节）")

def main():
    """主函数"""
    print("🚀 多端口连接实时调试工具")
    print("=" * 70)
    
    tests = [
        ("设备配置调试", debug_device_config),
        ("多端口接口测试", test_multiport_interface),
        ("连接逻辑调试", debug_connection_logic),
        ("问题识别分析", identify_current_issue)
    ]
    
    for test_name, test_func in tests:
        try:
            print(f"\n🔍 {test_name}")
            test_func()
        except Exception as e:
            print(f"❌ {test_name} 异常: {e}")
    
    print("\n" + "=" * 70)
    print("📝 调试完成")
    print("\n💬 下一步操作建议:")
    print("   1. 重新打开设备配置对话框，确认步道设备确实配置了多个端口")
    print("   2. 重新选择设备，观察控制台输出，确认多端口接口创建成功")
    print("   3. 检查数据处理部分的调试输出，确认数据长度为2048字节")
    print("=" * 70)

if __name__ == "__main__":
    main()