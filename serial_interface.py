#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
串口接口模块 - 负责串口通信和数据获取
"""

import serial
import serial.tools.list_ports
import threading
import queue
import time
from datetime import datetime
import sys
import os

# 导入date.py的函数
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from date import find_available_ports, test_port_connection, find_frame_start, extract_frame_content, auto_find_working_port

class SerialInterface:
    """串口接口类"""
    
    def __init__(self, baudrate=1000000):
        self.baudrate = baudrate
        self.serial_port = None
        self.is_running = False
        self.data_queue = queue.Queue()
        self.frame_count = 0
        self.data_thread = None
        
        # 帧头定义
        self.FRAME_HEADER = [0xAA, 0x55, 0x03, 0x99]
        
    def get_available_ports(self):
        """获取可用端口列表"""
        return find_available_ports()
    
    def test_port(self, port_name):
        """测试端口连接"""
        return test_port_connection(port_name, self.baudrate)
    
    def auto_detect_port(self):
        """自动检测工作端口"""
        return auto_find_working_port()
    
    def connect(self, port_name):
        """连接到指定端口"""
        try:
            if not self.test_port(port_name):
                raise Exception(f"端口 {port_name} 测试失败")
            
            self.serial_port = serial.Serial(port_name, self.baudrate, timeout=1)
            self.is_running = True
            
            # 启动数据接收线程
            self.data_thread = threading.Thread(target=self._data_receiver_thread, daemon=True)
            self.data_thread.start()
            
            return True
            
        except Exception as e:
            raise Exception(f"连接失败: {e}")
    
    def disconnect(self):
        """断开连接"""
        self.is_running = False
        
        if self.serial_port and self.serial_port.is_open:
            self.serial_port.close()
    
    def get_data(self, timeout=0.1):
        """获取数据，非阻塞 - 优化版"""
        try:
            return self.data_queue.get_nowait()
        except queue.Empty:
            return None
    
    def get_multiple_data(self, max_count=5):
        """批量获取多个数据帧，减少调用开销"""
        data_list = []
        try:
            for _ in range(max_count):
                data = self.data_queue.get_nowait()
                data_list.append(data)
        except queue.Empty:
            pass
        return data_list
    
    def get_frame_count(self):
        """获取帧计数"""
        return self.frame_count
    
    def is_connected(self):
        """检查是否连接"""
        return self.is_running and self.serial_port and self.serial_port.is_open
    
    def _data_receiver_thread(self):
        """数据接收线程"""
        data_buffer = bytearray()
        
        while self.is_running:
            try:
                # 读取数据 - 增加读取量减少延迟
                incoming_data = self.serial_port.read(2000)
                
                if incoming_data:
                    data_buffer.extend(incoming_data)
                    
                    # 处理缓冲区中的完整帧
                    while len(data_buffer) >= 4:
                        frame_start = find_frame_start(data_buffer)
                        
                        if frame_start == -1:
                            if len(data_buffer) > 3:
                                data_buffer = data_buffer[-3:]
                            break
                            
                        if frame_start > 0:
                            data_buffer = data_buffer[frame_start:]
                            frame_start = 0
                            
                        frame_content, next_frame_pos = extract_frame_content(data_buffer, frame_start)
                        
                        if next_frame_pos == -1:
                            break
                            
                        # 处理完整帧
                        if len(frame_content) > 0:
                            self.frame_count += 1
                            timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]
                            
                            # 将数据和时间戳放入队列
                            frame_data = {
                                'data': frame_content,
                                'timestamp': timestamp,
                                'frame_number': self.frame_count,
                                'data_length': len(frame_content)
                            }
                            self.data_queue.put(frame_data)
                            
                        data_buffer = data_buffer[next_frame_pos:]
                    
                    # 限制缓冲区大小
                    if len(data_buffer) > 5000:  # 减少缓冲区大小，降低延迟
                        data_buffer = data_buffer[-500:]
                        
                # 减少延迟，只在没有数据时稍微休眠
                if not incoming_data:
                    time.sleep(0.001)
                
            except Exception as e:
                if self.is_running:
                    print(f"数据接收错误: {e}")
                break 