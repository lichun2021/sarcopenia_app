#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
多串口接口模块 - 负责多COM口步道设备的数据合并处理
"""

import serial
import threading
import queue
import time
from datetime import datetime
import sys
import os
import numpy as np

# 导入单串口接口
from serial_interface import SerialInterface
from date import find_available_ports, test_port_connection
from data_processor import DataProcessor

class MultiPortInterface:
    """多串口接口类 - 处理多个COM口的步道设备"""
    
    def __init__(self, port_configs, baudrate=1000000):
        """
        初始化多串口接口
        
        Args:
            port_configs (list): 端口配置列表
                [{'port': 'COM3', 'device_id': 0}, {'port': 'COM4', 'device_id': 1}]
            baudrate (int): 波特率，默认1000000
        """
        self.baudrate = baudrate
        self.port_configs = port_configs
        self.serial_interfaces = {}
        self.is_running = False
        self.combined_data_queue = queue.Queue()
        self.frame_count = 0
        
        # 数据同步相关
        self.device_data_buffers = {}  # 各设备的数据缓冲区
        self.device_frame_counts = {}  # 各设备的帧计数
        self.sync_lock = threading.Lock()
        
        # 预期设备数量
        self.expected_devices = len(port_configs)
        self.expected_frame_size = 1024  # 每个设备1024字节
        
        # 帧头定义
        self.FRAME_HEADER = [0xAA, 0x55, 0x03, 0x99]
        
        # 初始化数据处理器用于JQ转化
        self.data_processor = DataProcessor(32, 32)  # 每个设备都是32x32
        
        print(f"🔧 初始化多串口接口，预期 {self.expected_devices} 个设备")
        
    def connect_all_ports(self):
        """连接所有配置的端口"""
        success_count = 0
        
        for config in self.port_configs:
            port_name = config['port']
            device_id = config['device_id']
            
            try:
                # 测试端口
                if not test_port_connection(port_name, self.baudrate):
                    print(f"❌ 端口 {port_name} (设备{device_id}) 测试失败")
                    continue
                
                # 创建串口接口
                serial_interface = SerialInterface(self.baudrate)
                serial_interface.set_device_mode("single")  # 每个端口都是单设备模式
                
                # 连接端口
                if serial_interface.connect(port_name):
                    self.serial_interfaces[device_id] = serial_interface
                    self.device_data_buffers[device_id] = None
                    self.device_frame_counts[device_id] = 0
                    success_count += 1
                    print(f"✅ 设备{device_id} 连接成功: {port_name}")
                else:
                    print(f"❌ 设备{device_id} 连接失败: {port_name}")
                    
            except Exception as e:
                print(f"❌ 设备{device_id} 连接异常: {port_name} - {e}")
        
        if success_count == self.expected_devices:
            print(f"🎉 所有 {self.expected_devices} 个设备连接成功")
            self.is_running = True
            self.start_data_collection()
            return True
        else:
            print(f"⚠️ 只有 {success_count}/{self.expected_devices} 个设备连接成功")
            return False
    
    def start_data_collection(self):
        """启动数据收集线程"""
        if not self.is_running:
            return
            
        # 启动数据合并线程
        self.data_merge_thread = threading.Thread(target=self._data_merge_worker, daemon=True)
        self.data_merge_thread.start()
        print("🚀 多设备数据合并线程已启动")
    
    def _data_merge_worker(self):
        """数据合并工作线程"""
        print("🔄 数据合并线程开始运行")
        
        while self.is_running:
            try:
                # 从各个设备收集数据
                all_devices_ready = True
                collected_data = {}
                collected_timestamps = {}
                
                with self.sync_lock:
                    for device_id in self.serial_interfaces:
                        serial_interface = self.serial_interfaces[device_id]
                        
                        # 尝试获取数据
                        frame_data = serial_interface.get_data()
                        
                        if frame_data and len(frame_data['data']) == self.expected_frame_size:
                            # 收到有效的1024字节数据
                            collected_data[device_id] = frame_data['data']
                            collected_timestamps[device_id] = frame_data['timestamp']
                            self.device_frame_counts[device_id] += 1
                        else:
                            # 该设备暂无数据
                            all_devices_ready = False
                            break
                
                # 检查是否所有设备都有数据
                if all_devices_ready and len(collected_data) == self.expected_devices:
                    # 先对每个1024字节数据进行JQ转化，然后合并
                    combined_data = bytearray()
                    jq_transform_results = []
                    
                    # 按设备ID顺序处理和合并数据
                    for device_id in sorted(collected_data.keys()):
                        raw_data = collected_data[device_id]
                        
                        try:
                            # 对每个1024字节数据进行JQ转化
                            if len(raw_data) == 1024:
                                # 转换为numpy数组
                                data_array = np.frombuffer(raw_data, dtype=np.uint8)
                                # 应用JQ转化
                                transformed_data = self.data_processor.jqbed_transform(data_array)
                                # 转换回字节
                                transformed_bytes = transformed_data.astype(np.uint8).tobytes()
                                combined_data.extend(transformed_bytes)
                                jq_transform_results.append(f"设备{device_id}: JQ转化成功")
                            else:
                                # 数据长度不是1024，直接使用原始数据
                                combined_data.extend(raw_data)
                                jq_transform_results.append(f"设备{device_id}: 跳过JQ转化(长度{len(raw_data)})")
                                
                        except Exception as e:
                            # JQ转化失败，使用原始数据
                            combined_data.extend(raw_data)
                            jq_transform_results.append(f"设备{device_id}: JQ转化失败({str(e)[:30]})")
                    
                    # 生成合并后的帧数据
                    self.frame_count += 1
                    combined_frame = {
                        'data': bytes(combined_data),
                        'timestamp': max(collected_timestamps.values()),  # 使用最新时间戳
                        'frame_number': self.frame_count,
                        'data_length': len(combined_data),
                        'device_frames': self.expected_devices,
                        'device_type': f"{self.expected_devices}x1024_multi_port",
                        'source_devices': list(collected_data.keys()),
                        'jq_transform_results': jq_transform_results  # JQ转化结果信息
                    }
                    
                    # 放入合并数据队列
                    self.combined_data_queue.put(combined_frame)
                    
                    # 调试输出
                    if self.frame_count % 100 == 0:  # 每100帧输出一次
                        jq_success_count = len([r for r in jq_transform_results if "JQ转化成功" in r])
                        print(f"📊 已合并 {self.frame_count} 帧数据 "
                              f"({self.expected_devices}个设备, 总长度: {len(combined_data)}字节, "
                              f"JQ转化: {jq_success_count}/{self.expected_devices})")
                
                # 短暂休眠，避免CPU占用过高
                time.sleep(0.001)
                
            except Exception as e:
                if self.is_running:
                    print(f"❌ 数据合并错误: {e}")
                time.sleep(0.01)
    
    def get_combined_data(self, timeout=0.1):
        """获取合并后的数据"""
        try:
            return self.combined_data_queue.get_nowait()
        except queue.Empty:
            return None
    
    def get_multiple_combined_data(self, max_count=5):
        """批量获取多个合并数据帧"""
        data_list = []
        try:
            for _ in range(max_count):
                data = self.combined_data_queue.get_nowait()
                data_list.append(data)
        except queue.Empty:
            pass
        return data_list
    
    def get_frame_count(self):
        """获取合并帧计数"""
        return self.frame_count
    
    def get_device_status(self):
        """获取各设备状态"""
        status = {}
        for device_id, serial_interface in self.serial_interfaces.items():
            status[device_id] = {
                'connected': serial_interface.is_connected(),
                'port': serial_interface.get_current_port(),
                'frame_count': self.device_frame_counts.get(device_id, 0)
            }
        return status
    
    def is_connected(self):
        """检查是否所有设备都已连接"""
        if not self.is_running:
            return False
        
        for serial_interface in self.serial_interfaces.values():
            if not serial_interface.is_connected():
                return False
        return True
    
    def disconnect_all(self):
        """断开所有设备连接"""
        self.is_running = False
        
        for device_id, serial_interface in self.serial_interfaces.items():
            try:
                serial_interface.disconnect()
                print(f"🔌 设备{device_id} 已断开连接")
            except Exception as e:
                print(f"❌ 设备{device_id} 断开连接时出错: {e}")
        
        self.serial_interfaces.clear()
        self.device_data_buffers.clear()
        self.device_frame_counts.clear()
        
        print("🔚 所有设备已断开连接")
    
    # 兼容性方法，用于与主程序接口保持一致
    def disconnect(self):
        """断开连接（兼容性方法）"""
        return self.disconnect_all()
    
    def get_current_port(self):
        """获取当前端口（兼容性方法）- 返回第一个端口"""
        if self.port_configs:
            return self.port_configs[0]['port']
        return None
    
    def get_data(self, timeout=0.1):
        """获取数据（兼容性方法）"""
        return self.get_combined_data(timeout)
    
    def set_walkway_mode(self, is_walkway):
        """设置步道模式（兼容性方法）"""
        # 多端口接口本身就是为步道设备设计的，这里只是兼容性接口
        print(f"🔧 多端口接口步道模式: {'启用' if is_walkway else '禁用'}")
        
    def set_device_mode(self, device_type):
        """设置设备模式（兼容性方法）"""
        print(f"🔧 多端口接口设备类型: {device_type}")
        # 多端口接口的设备类型在创建时已确定，这里只是兼容性接口
    
    def get_multiple_data(self, max_count=5):
        """批量获取多个数据帧（兼容性方法）"""
        return self.get_multiple_combined_data(max_count)

def create_multi_port_interface(device_type, ports):
    """
    创建多串口接口的工厂函数
    
    Args:
        device_type (str): 设备类型 ("dual_1024" 或 "triple_1024")
        ports (list): 端口名称列表 ["COM3", "COM4"] 或 ["COM3", "COM4", "COM5"]
        
    Returns:
        MultiPortInterface: 多串口接口实例
    """
    if device_type == "dual_1024" and len(ports) == 2:
        port_configs = [
            {'port': ports[0], 'device_id': 0},
            {'port': ports[1], 'device_id': 1}
        ]
        print(f"🔧 创建双设备多串口接口: {ports}")
        
    elif device_type == "triple_1024" and len(ports) == 3:
        port_configs = [
            {'port': ports[0], 'device_id': 0},
            {'port': ports[1], 'device_id': 1},
            {'port': ports[2], 'device_id': 2}
        ]
        print(f"🔧 创建三设备多串口接口: {ports}")
        
    else:
        raise ValueError(f"不支持的设备类型或端口数量: {device_type}, 端口数: {len(ports)}")
    
    return MultiPortInterface(port_configs)

# 测试函数
def test_multi_port_interface():
    """测试多串口接口功能"""
    print("🧪 测试多串口接口...")
    
    # 获取可用端口
    available_ports = find_available_ports()
    if len(available_ports) < 2:
        print("❌ 需要至少2个可用端口进行测试")
        return
        
    # 选择前两个端口进行双设备测试
    test_ports = [available_ports[0]['device'], available_ports[1]['device']]
    print(f"🔍 使用端口进行测试: {test_ports}")
    
    try:
        # 创建双设备接口
        multi_interface = create_multi_port_interface("dual_1024", test_ports)
        
        # 连接所有端口
        if multi_interface.connect_all_ports():
            print("✅ 多端口连接成功，开始数据采集测试...")
            
            # 测试数据采集
            test_duration = 5  # 测试5秒
            start_time = time.time()
            
            while time.time() - start_time < test_duration:
                combined_data = multi_interface.get_combined_data()
                if combined_data:
                    jq_results = combined_data.get('jq_transform_results', [])
                    jq_success_count = len([r for r in jq_results if "JQ转化成功" in r])
                    print(f"📨 收到合并数据: {combined_data['data_length']}字节, "
                          f"帧#{combined_data['frame_number']}, "
                          f"来源设备: {combined_data['source_devices']}, "
                          f"JQ转化: {jq_success_count}/{len(combined_data['source_devices'])}")
                
                time.sleep(0.1)
            
            print(f"📊 测试完成，总共处理 {multi_interface.get_frame_count()} 帧合并数据")
            
            # 显示设备状态
            status = multi_interface.get_device_status()
            for device_id, device_status in status.items():
                print(f"  设备{device_id}: 端口{device_status['port']}, "
                      f"帧数{device_status['frame_count']}, "
                      f"连接状态: {'✅' if device_status['connected'] else '❌'}")
            
        else:
            print("❌ 多端口连接失败")
            
    except Exception as e:
        print(f"❌ 测试过程中出现错误: {e}")
        
    finally:
        # 清理资源
        try:
            multi_interface.disconnect_all()
        except:
            pass

if __name__ == "__main__":
    test_multi_port_interface()