#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
模块测试脚本 - 验证所有模块是否正常工作
"""

import sys
import numpy as np

def test_imports():
    """测试模块导入"""
    print("🔍 测试模块导入...")
    
    try:
        import serial_interface
        print("✅ serial_interface 导入成功")
    except Exception as e:
        print(f"❌ serial_interface 导入失败: {e}")
        return False
    
    try:
        import data_processor
        print("✅ data_processor 导入成功")
    except Exception as e:
        print(f"❌ data_processor 导入失败: {e}")
        return False
    
    try:
        import visualization
        print("✅ visualization 导入成功")
    except Exception as e:
        print(f"❌ visualization 导入失败: {e}")
        return False
    
    try:
        import pressure_sensor_ui
        print("✅ pressure_sensor_ui 导入成功")
    except Exception as e:
        print(f"❌ pressure_sensor_ui 导入失败: {e}")
        return False
    
    return True

def test_data_processor():
    """测试数据处理器"""
    print("\n🧪 测试数据处理器...")
    
    try:
        from data_processor import DataProcessor
        
        # 创建处理器实例
        processor = DataProcessor(32, 32)
        
        # 创建测试数据
        test_data = np.random.randint(0, 256, 1024, dtype=np.uint8)
        
        # 模拟帧数据
        frame_data = {
            'data': test_data,
            'timestamp': "12:34:56.789",
            'frame_number': 1,
            'data_length': 1024
        }
        
        # 处理数据
        result = processor.process_frame_data(frame_data)
        
        if 'error' in result:
            print(f"❌ 数据处理失败: {result['error']}")
            return False
        
        print("✅ JQ数据变换成功")
        print(f"📊 统计信息: {result['statistics']}")
        print(f"🔄 JQ变换已应用: {result['jq_transform_applied']}")
        
        return True
        
    except Exception as e:
        print(f"❌ 数据处理器测试失败: {e}")
        return False

def test_serial_interface():
    """测试串口接口"""
    print("\n🔌 测试串口接口...")
    
    try:
        from serial_interface import SerialInterface
        
        # 创建接口实例
        interface = SerialInterface()
        
        # 测试端口扫描
        ports = interface.get_available_ports()
        print(f"✅ 发现 {len(ports)} 个COM端口")
        
        for port in ports:
            print(f"  📍 {port['device']}: {port['description']}")
        
        return True
        
    except Exception as e:
        print(f"❌ 串口接口测试失败: {e}")
        return False

def main():
    print("🔬 智能肌少症检测系统 - 模块测试")
    print("=" * 50)
    
    # 测试导入
    if not test_imports():
        print("\n❌ 模块导入测试失败")
        return False
    
    # 测试数据处理器
    if not test_data_processor():
        print("\n❌ 数据处理器测试失败")
        return False
    
    # 测试串口接口
    if not test_serial_interface():
        print("\n❌ 串口接口测试失败")
        return False
    
    print("\n" + "=" * 50)
    print("🎉 所有模块测试通过！")
    print("💡 可以运行 python run_ui.py 启动完整应用")
    
    return True

if __name__ == "__main__":
    success = main()
    if not success:
        sys.exit(1) 