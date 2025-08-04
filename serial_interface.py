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
import numpy as np

# 导入date.py的函数
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from date import find_available_ports, test_port_connection, find_frame_start, extract_frame_content, auto_find_working_port
from data_processor import DataProcessor

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
        
        # 多设备数据累积缓冲区
        self.device_buffer = bytearray()
        self.device_frame_count = 0
        self.expected_device_frames = 1  # 默认1个1024字节帧
        self.is_multi_device_mode = False  # 是否为多设备模式
        self.device_type = "single"  # single, dual_1024, triple_1024, walkway
        
        # 多端口支持
        self.multi_port_config = None  # 多端口配置 [{'port': 'COM3', 'device_id': 0}, ...]
        self.serial_ports = {}  # 多个串口连接 {device_id: serial_port}
        self.multi_port_threads = {}  # 多个数据接收线程 {device_id: thread}
        self.device_data_buffers = {}  # 各设备的数据缓冲区 {device_id: buffer}
        self.device_frame_counts = {}  # 各设备的帧计数 {device_id: count}
        self.sync_lock = threading.Lock()  # 数据同步锁
        
        # JQ转换处理器
        self.jq_processor = DataProcessor(32, 32)
        
    def get_available_ports(self):
        """获取可用端口列表"""
        return find_available_ports()
    
    def test_port(self, port_name):
        """测试端口连接"""
        return test_port_connection(port_name, self.baudrate)
    
    def auto_detect_port(self):
        """自动检测工作端口"""
        return auto_find_working_port()
    
    def set_device_mode(self, device_type):
        """设置设备模式
        
        Args:
            device_type (str): 设备类型
                - "single": 单设备，1x1024字节
                - "dual_1024": 双设备，2x1024字节
                - "triple_1024": 三设备，3x1024字节  
                - "walkway": 步道设备，3x1024字节（向后兼容）
        """
        self.device_type = device_type
        
        if device_type == "single":
            self.expected_device_frames = 1
            self.is_multi_device_mode = False
        elif device_type == "dual_1024":
            self.expected_device_frames = 2
            self.is_multi_device_mode = True
        elif device_type == "triple_1024" or device_type == "walkway":
            self.expected_device_frames = 3
            self.is_multi_device_mode = True
        else:
            raise ValueError(f"不支持的设备类型: {device_type}")
            
        # 清空缓冲区
        self.device_buffer.clear()
        self.device_frame_count = 0
        
        # 向后兼容性设置
        self.is_walkway_mode = (device_type == "walkway")
        self.expected_walkway_frames = self.expected_device_frames
        
    def set_multi_port_config(self, port_configs):
        """设置多端口配置
        
        Args:
            port_configs (list): 端口配置列表
                [{'port': 'COM3', 'device_id': 0}, {'port': 'COM4', 'device_id': 1}]
        """
        self.multi_port_config = port_configs
        if port_configs and len(port_configs) > 1:
            # 根据端口数量自动设置设备模式
            if len(port_configs) == 2:
                self.set_device_mode("dual_1024")
            elif len(port_configs) == 3:
                self.set_device_mode("triple_1024")
            print(f"🔧 配置多端口设备: {len(port_configs)}个端口, 模式: {self.device_type}")
    
    def connect(self, port_name):
        """连接到指定端口或多端口"""
        try:
            # 检查是否为多端口模式
            if self.multi_port_config and len(self.multi_port_config) > 1:
                return self._connect_multi_port()
            else:
                # 单端口模式
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
    
    def _connect_multi_port(self):
        """多端口连接"""
        success_count = 0
        
        for config in self.multi_port_config:
            port_name = config['port']
            device_id = config['device_id']
            
            try:
                # 测试端口
                if not self.test_port(port_name):
                    print(f"❌ 端口 {port_name} (设备{device_id}) 测试失败")
                    continue
                
                # 连接端口
                serial_port = serial.Serial(port_name, self.baudrate, timeout=1)
                self.serial_ports[device_id] = serial_port
                self.device_data_buffers[device_id] = bytearray()
                self.device_frame_counts[device_id] = 0
                success_count += 1
                print(f"✅ 设备{device_id} 连接成功: {port_name}")
                
            except Exception as e:
                print(f"❌ 设备{device_id} 连接异常: {port_name} - {e}")
        
        if success_count == len(self.multi_port_config):
            print(f"🎉 所有 {len(self.multi_port_config)} 个端口连接成功")
            self.is_running = True
            self._start_multi_port_threads()
            return True
        else:
            print(f"⚠️ 只有 {success_count}/{len(self.multi_port_config)} 个端口连接成功")
            return False
    
    def _start_multi_port_threads(self):
        """启动多端口数据接收线程"""
        # 为每个端口启动数据接收线程
        for device_id, serial_port in self.serial_ports.items():
            thread = threading.Thread(
                target=self._multi_port_data_receiver, 
                args=(device_id, serial_port), 
                daemon=True
            )
            self.multi_port_threads[device_id] = thread
            thread.start()
        
        # 启动数据合并线程
        self.data_merge_thread = threading.Thread(target=self._multi_port_data_merger, daemon=True)
        self.data_merge_thread.start()
        print(f"🚀 多端口数据接收和合并线程已启动")
    
    def get_current_port(self):
        """获取当前连接的端口名称"""
        if self.multi_port_config and len(self.multi_port_config) > 1:
            # 多端口模式：返回第一个端口
            return self.multi_port_config[0]['port']
        elif self.serial_port and self.serial_port.is_open:
            return self.serial_port.name
        return None
    
    def disconnect(self):
        """断开连接"""
        self.is_running = False
        
        # 关闭单端口连接
        if self.serial_port and self.serial_port.is_open:
            self.serial_port.close()
        
        # 关闭多端口连接
        for device_id, serial_port in self.serial_ports.items():
            try:
                if serial_port and serial_port.is_open:
                    serial_port.close()
            except Exception as e:
                print(f"❌ 设备{device_id} 断开连接时出错: {e}")
        
        # 清理多端口资源
        self.serial_ports.clear()
        self.multi_port_threads.clear()
        self.device_data_buffers.clear()
        self.device_frame_counts.clear()
    
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
        if self.multi_port_config and len(self.multi_port_config) > 1:
            # 多端口模式：检查所有端口是否都连接
            if not self.is_running:
                return False
            for serial_port in self.serial_ports.values():
                if not (serial_port and serial_port.is_open):
                    return False
            return True
        else:
            # 单端口模式
            return self.is_running and self.serial_port and self.serial_port.is_open
    
    def _multi_port_data_receiver(self, device_id, serial_port):
        """多端口单个设备数据接收线程"""
        data_buffer = bytearray()
        
        while self.is_running:
            try:
                # 读取数据
                incoming_data = serial_port.read(2000)
                
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
                            
                        # 处理完整的1024字节帧
                        if len(frame_content) == 1024:
                            with self.sync_lock:
                                self.device_data_buffers[device_id] = frame_content
                                self.device_frame_counts[device_id] += 1
                        
                        data_buffer = data_buffer[next_frame_pos:]
                    
                    # 限制缓冲区大小
                    if len(data_buffer) > 5000:
                        data_buffer = data_buffer[-500:]
                        
                # 减少延迟
                if not incoming_data:
                    time.sleep(0.001)
                
            except Exception as e:
                if self.is_running:
                    print(f"设备{device_id}数据接收错误: {e}")
                break
    
    def _multi_port_data_merger(self):
        """多端口数据合并线程"""
        device_ready_data = {}  # 各设备准备好的数据
        
        while self.is_running:
            try:
                # 检查所有设备是否都有新数据
                all_devices_ready = True
                
                with self.sync_lock:
                    for device_id in self.serial_ports.keys():
                        if device_id in self.device_data_buffers and self.device_data_buffers[device_id]:
                            device_ready_data[device_id] = self.device_data_buffers[device_id]
                            self.device_data_buffers[device_id] = None  # 标记已使用
                        else:
                            all_devices_ready = False
                            break
                
                # 如果所有设备都有数据，进行合并
                if all_devices_ready and len(device_ready_data) == len(self.serial_ports):
                    # 按设备ID顺序进行JQ转换，然后水平合并
                    device_matrices = []
                    jq_transform_results = []
                    
                    for device_id in sorted(device_ready_data.keys()):
                        raw_data = device_ready_data[device_id]
                        
                        try:
                            # 必须进行JQ转换（用户强调这是必须的）
                            data_array = np.frombuffer(raw_data, dtype=np.uint8)
                            transformed_data = self.jq_processor.jqbed_transform(data_array)
                            # 将1024字节数据重塑为32x32矩阵
                            matrix_32x32 = transformed_data.reshape(32, 32)
                            device_matrices.append(matrix_32x32)
                            jq_transform_results.append(f"设备{device_id}: JQ转化成功")
                            
                        except Exception as e:
                            # JQ转换失败仍然使用原始数据，但记录错误
                            data_array = np.frombuffer(raw_data, dtype=np.uint8)
                            matrix_32x32 = data_array.reshape(32, 32)
                            device_matrices.append(matrix_32x32)
                            jq_transform_results.append(f"设备{device_id}: JQ转化失败({str(e)[:30]})")
                    
                    # 水平合并矩阵（左右拼接）
                    combined_matrix = np.hstack(device_matrices)  # 32x64 or 32x96
                    combined_data = combined_matrix.ravel().astype(np.uint8).tobytes()
                    
                    # 生成合并帧数据
                    self.frame_count += 1
                    timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]
                    
                    frame_data = {
                        'data': bytes(combined_data),
                        'timestamp': timestamp,
                        'frame_number': self.frame_count,
                        'data_length': len(combined_data),
                        'device_frames': len(device_ready_data),
                        'device_type': self.device_type,
                        'jq_transform_results': jq_transform_results
                    }
                    
                    # 向后兼容性字段
                    if self.device_type == "walkway":
                        frame_data['walkway_frames'] = len(device_ready_data)
                    
                    self.data_queue.put(frame_data)
                    
                    # 清空已处理的数据
                    device_ready_data.clear()
                    
                    # 调试输出 - 增强版
                    if self.frame_count % 100 == 0:
                        jq_success_count = len([r for r in jq_transform_results if "JQ转化成功" in r])
                        # print(f"📊 多端口数据水平合并 [帧#{self.frame_count}]:")
                        # print(f"   合并设备数: {len(self.serial_ports)}")
                        # print(f"   合并矩阵大小: {combined_matrix.shape} (水平拼接)")
                        # print(f"   合并数据长度: {len(combined_data)}字节")
                        # print(f"   JQ转化状态: {jq_success_count}/{len(self.serial_ports)} 成功")
                        # print(f"   JQ转化详情: {jq_transform_results}")
                        
                        # 显示每个设备的数据概览
                        for device_id in sorted(device_ready_data.keys()):
                            raw_data = device_ready_data[device_id]
                            data_sum = sum(raw_data) if raw_data else 0
                            print(f"     设备{device_id}: {len(raw_data)}字节, 数据和={data_sum}")
                
                # 短暂休眠
                time.sleep(0.001)
                
            except Exception as e:
                if self.is_running:
                    print(f"❌ 多端口数据合并错误: {e}")
                time.sleep(0.01)
    
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
                            
                            # 多设备模式：累积多个1024字节帧
                            if self.is_multi_device_mode and len(frame_content) == 1024:
                                self.device_buffer.extend(frame_content)
                                self.device_frame_count += 1
                                
                                # 调试信息
                                device_name = {
                                    "dual_1024": "双设备",
                                    "triple_1024": "三设备", 
                                    "walkway": "步道"
                                }.get(self.device_type, "多设备")
                                
                                # 检查是否收集够指定数量的帧
                                if self.device_frame_count >= self.expected_device_frames:
                                    # 将合并的数据放入队列
                                    combined_data = bytes(self.device_buffer)
                                    frame_data = {
                                        'data': combined_data,
                                        'timestamp': timestamp,
                                        'frame_number': self.frame_count,
                                        'data_length': len(combined_data),
                                        'device_frames': self.device_frame_count,
                                        'device_type': self.device_type
                                    }
                                    
                                    # 向后兼容性字段
                                    if self.device_type == "walkway":
                                        frame_data['walkway_frames'] = self.device_frame_count
                                    
                                    self.data_queue.put(frame_data)
                                    
                                    # 清空缓冲区准备下一组
                                    self.device_buffer.clear()
                                    self.device_frame_count = 0
                            else:
                                # 普通模式或非1024字节帧，直接处理
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
    
    # 向后兼容性方法
    def set_walkway_mode(self, is_walkway):
        """设置步道模式（向后兼容）"""
        if is_walkway:
            self.set_device_mode("walkway")
        else:
            self.set_device_mode("single")
            # 清空缓冲区
            self.device_buffer.clear()
            self.device_frame_count = 0