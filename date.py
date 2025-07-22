#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
串口数据获取工具 - 智能肌少症检测系统
分割帧头并输出帧内容
"""

import serial
import serial.tools.list_ports
import time
from datetime import datetime

# 帧头定义
FRAME_HEADER = [0xAA, 0x55, 0x03, 0x99]
# 固定终止符
FRAME_TERMINATOR = [0xFF, 0xFF]

def find_available_ports():
    """
    查找所有可用的COM端口
    
    Returns:
        list: 可用端口列表
    """
    ports = serial.tools.list_ports.comports()
    available_ports = []
    
    for port in ports:
        available_ports.append({
            'device': port.device,
            'description': port.description,
            'hwid': port.hwid
        })
    
    return available_ports

def test_port_connection(port_name, baudrate=1000000, timeout=0.5):
    """
    快速测试端口连接
    
    Args:
        port_name (str): 端口名称
        baudrate (int): 波特率
        timeout (float): 超时时间（秒）- 减少到0.5秒
        
    Returns:
        bool: 是否连接成功并检测到数据
    """
    try:
        ser = serial.Serial(port_name, baudrate, timeout=timeout)
        time.sleep(0.1)  # 减少等待时间到0.1秒
        
        # 快速读取数据
        test_data = ser.read(50)  # 减少读取量
        ser.close()
        
        # 简化判断：有数据就认为成功
        return len(test_data) > 10
        
    except Exception:
        return False

def auto_find_working_port():
    """
    自动查找工作的COM端口
    
    Returns:
        str: 工作的端口名称，如果没有找到返回None
    """
    print("正在扫描可用的COM端口...")
    available_ports = find_available_ports()
    
    if not available_ports:
        print("❌ 未找到任何COM端口")
        return None
    
    print(f"发现 {len(available_ports)} 个COM端口:")
    for port in available_ports:
        print(f"  📍 {port['device']}: {port['description']}")
    
    print("\n正在测试端口连接...")
    for port in available_ports:
        port_name = port['device']
        print(f"  🔍 测试 {port_name}...", end="", flush=True)
        
        if test_port_connection(port_name):
            print(f" ✅ 连接成功！")
            return port_name
        else:
            print(f" ❌ 连接失败")
    
    print("❌ 未找到可用的端口")
    return None

def find_frame_start(data_buffer):
    """
    在数据缓冲区中查找帧头
    
    Args:
        data_buffer (bytearray): 数据缓冲区
        
    Returns:
        int: 帧头位置，如果未找到返回-1
    """
    for i in range(len(data_buffer) - 3):
        if (data_buffer[i] == FRAME_HEADER[0] and 
            data_buffer[i+1] == FRAME_HEADER[1] and 
            data_buffer[i+2] == FRAME_HEADER[2] and 
            data_buffer[i+3] == FRAME_HEADER[3]):
            return i
    return -1

def extract_frame_content(data_buffer, start_pos):
    """
    提取帧内容（帧头后的数据直到下一个帧头）
    
    Args:
        data_buffer (bytearray): 数据缓冲区
        start_pos (int): 当前帧头位置
        
    Returns:
        tuple: (帧内容, 下一个帧头位置)
    """
    content_start = start_pos + 4  # 跳过帧头
    
    # 查找下一个帧头
    next_frame_pos = find_frame_start(data_buffer[content_start:])
    
    if next_frame_pos == -1:
        # 没有找到下一个帧头，返回剩余所有数据
        return data_buffer[content_start:], -1
    else:
        # 找到下一个帧头，返回两个帧头之间的数据
        actual_next_pos = content_start + next_frame_pos
        return data_buffer[content_start:actual_next_pos], actual_next_pos

def format_hex_output(data):
    """
    格式化十六进制输出
    
    Args:
        data (bytearray): 要格式化的数据
        
    Returns:
        str: 格式化后的十六进制字符串
    """
    return ' '.join(f'{byte:02X}' for byte in data)

def add_terminator_to_frame(frame_data):
    """
    为帧数据添加固定终止符
    
    Args:
        frame_data (bytearray): 帧数据
        
    Returns:
        bytearray: 添加终止符后的数据
    """
    result = bytearray(frame_data)
    result.extend(FRAME_TERMINATOR)
    return result

def main():
    print("=" * 70)
    print("🔬 智能肌少症检测系统 - 串口数据获取工具")
    print("=" * 70)
    print(f"📡 目标波特率: 1000000 bps")
    print(f"📋 帧头: {' '.join(f'0x{b:02X}' for b in FRAME_HEADER)}")
    print(f"�� 固定终止符: {' '.join(f'0x{b:02X}' for b in FRAME_TERMINATOR)}")
    print("=" * 70)
    
    # 自动查找工作的COM端口
    working_port = auto_find_working_port()
    
    if not working_port:
        print("\n❌ 无法找到可用的COM端口，程序退出")
        return
    
    print(f"\n✅ 使用端口: {working_port}")
    
    try:
        # 打开串口 - 1000000 bps
        ser = serial.Serial(working_port, 1000000, timeout=1)
        print(f"🔌 串口已打开: {ser.name}")
        print("📡 正在接收数据... (按 Ctrl+C 停止)")
        print("📝 格式: [时间戳] 帧#编号 (字节数): 十六进制数据 + 终止符")
        print("=" * 70)
        
        # 数据缓冲区
        data_buffer = bytearray()
        frame_count = 0
        
        while True:
            # 读取数据
            incoming_data = ser.read(1000)  # 一次读取更多数据
            
            if incoming_data:
                # 将新数据添加到缓冲区
                data_buffer.extend(incoming_data)
                
                # 处理缓冲区中的完整帧
                while len(data_buffer) >= 4:
                    frame_start = find_frame_start(data_buffer)
                    
                    if frame_start == -1:
                        # 没有找到帧头，清空缓冲区（保留最后3个字节以防帧头被分割）
                        if len(data_buffer) > 3:
                            data_buffer = data_buffer[-3:]
                        break
                    
                    # 如果帧头不在开始位置，删除之前的数据
                    if frame_start > 0:
                        data_buffer = data_buffer[frame_start:]
                        frame_start = 0
                    
                    # 提取帧内容
                    frame_content, next_frame_pos = extract_frame_content(data_buffer, frame_start)
                    
                    if next_frame_pos == -1:
                        # 没有找到下一个帧头，等待更多数据
                        break
                    
                    # 处理完整帧
                    if len(frame_content) > 0:
                        frame_count += 1
                        timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]
                        
                        # 添加固定终止符
                        frame_with_terminator = add_terminator_to_frame(frame_content)
                        hex_output = format_hex_output(frame_with_terminator)
                        
                        print(f"📨 [{timestamp}] 帧#{frame_count:04d} ({len(frame_content):3d}字节): {hex_output}")
                    
                    # 移除已处理的数据
                    data_buffer = data_buffer[next_frame_pos:]
                
                # 限制缓冲区大小，防止内存溢出
                if len(data_buffer) > 10000:
                    data_buffer = data_buffer[-1000:]
            
            # 短暂延迟，避免CPU占用过高
            time.sleep(0.001)
            
    except serial.SerialException as e:
        print(f"❌ 串口错误: {e}")
        print("🔍 请检查:")
        print("   1. 设备是否已正确连接")
        print("   2. 端口是否被其他程序占用") 
        print("   3. 设备驱动是否正常安装")
        
    except KeyboardInterrupt:
        print(f"\n⏹️  程序已停止")
        print(f"📊 总共处理了 {frame_count} 个帧")
        
    except Exception as e:
        print(f"❌ 未知错误: {e}")
        
    finally:
        if 'ser' in locals() and ser.is_open:
            ser.close()
            print("🔌 串口已关闭")

if __name__ == "__main__":
    main()