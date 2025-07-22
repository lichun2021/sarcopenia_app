#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
设备配置管理模块 - 负责多设备识别和配置
"""

import tkinter as tk
from tkinter import ttk, messagebox
import threading
import time
import queue
import json
import os
from datetime import datetime
from serial_interface import SerialInterface

class DeviceConfigDialog:
    """设备配置引导对话框"""
    
    def __init__(self, parent):
        self.parent = parent
        self.result = None
        self.dialog = None
        self.device_configs = {}
        self.scanning = True
        
        # 设备类型定义
        self.device_types = {
            'footpad': {'name': '脚垫', 'icon': '👣', 'array_size': '32x32'},
            'cushion': {'name': '坐垫', 'icon': '🪑', 'array_size': '32x32'}, 
            'walkway': {'name': '步道', 'icon': '🚶', 'array_size': '32x96'}
        }
        
        # COM口扫描
        self.serial_interface = SerialInterface()
        self.available_ports = []
        self.port_data_status = {}  # 端口数据状态
        
        # 线程安全的更新队列
        self.update_queue = queue.Queue()
        
        # 配置文件路径
        self.config_file = "device_config.json"
        
    def show_dialog(self):
        """显示配置对话框"""
        self.dialog = tk.Toplevel(self.parent)
        self.dialog.title("🔧 设备配置引导")
        self.dialog.geometry("800x600")
        self.dialog.resizable(False, False)
        self.dialog.grab_set()  # 模态对话框
        
        # 居中显示
        self.dialog.transient(self.parent)
        self.dialog.geometry("+%d+%d" % (
            self.parent.winfo_rootx() + 50, 
            self.parent.winfo_rooty() + 50
        ))
        
        self.setup_dialog_ui()
        
        # 尝试加载已保存的配置作为默认值显示
        saved_config = self.load_saved_config()
        if saved_config:
            # 延迟应用保存的配置作为默认值（等UI完全初始化后）
            self.dialog.after(500, lambda: self.apply_saved_config_to_ui(saved_config))
        
        self.start_port_scanning()
        self.start_ui_update_loop()
        
        # 绑定关闭事件
        self.dialog.protocol("WM_DELETE_WINDOW", self.on_dialog_close)
        
        # 等待用户操作
        self.dialog.wait_window()
        return self.result
    
    def start_ui_update_loop(self):
        """启动UI更新循环"""
        self.process_update_queue()
    
    def process_update_queue(self):
        """处理更新队列 - 持续运行，不依赖scanning状态"""
        try:
            if not self.dialog or not self.dialog.winfo_exists():
                return
                
            # 处理队列中的所有更新
            while not self.update_queue.empty():
                try:
                    update_type, data = self.update_queue.get_nowait()
                    if update_type == "port_status":
                        port_name, status = data
                        self.port_data_status[port_name] = status
                        self.update_ports_display()
                        # 实时更新所有使用该端口的设备状态
                        self.update_device_status_for_port(port_name)
                    elif update_type == "ports_found":
                        self.available_ports = data
                        self.update_ports_display()
                    elif update_type == "scan_complete":
                        # 初始扫描完成，更新状态标签
                        port_count = data
                        if port_count > 0:
                            self.scan_status_label.config(text=f"✅ 发现 {port_count} 个COM端口", foreground="green")
                        else:
                            self.scan_status_label.config(text="⚠️ 未发现COM端口", foreground="orange")
                    elif update_type == "refresh_complete":
                        # 刷新完成，更新状态标签
                        port_count = data
                        if port_count > 0:
                            self.scan_status_label.config(text=f"✅ 刷新完成，发现 {port_count} 个端口", foreground="green")
                        else:
                            self.scan_status_label.config(text="⚠️ 刷新完成，未发现端口", foreground="orange")
                    elif update_type == "scan_error":
                        self.scan_status_label.config(text=f"❌ 扫描失败: {data}", foreground="red")
                        self.ports_list_label.config(text="发现的端口: 无")
                        self.available_ports = []
                        self.update_ports_display()
                except queue.Empty:
                    break
            
            # 持续运行更新循环（不依赖scanning状态）
            self.dialog.after(100, self.process_update_queue)
                
        except Exception as e:
            pass
    
    def on_dialog_close(self):
        """对话框关闭事件"""
        self.scanning = False
        try:
            if self.dialog and self.dialog.winfo_exists():
                self.dialog.destroy()
        except:
            pass
    
    def load_saved_config(self):
        """加载保存的配置"""
        try:
            if os.path.exists(self.config_file):
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    file_data = json.load(f)
                    
                    # 处理新格式（包含时间戳）
                    if 'devices' in file_data:
                        config_data = file_data['devices']
                    else:
                        # 兼容旧格式
                        config_data = file_data
                    
                    # 验证配置数据的有效性
                    if self.validate_config_data(config_data):
                        return config_data
        except Exception as e:
            print(f"加载配置失败: {e}")
        return None
    
    def validate_config_data(self, config_data):
        """验证配置数据的有效性"""
        try:
            if not isinstance(config_data, dict):
                return False
            for device_id, config in config_data.items():
                required_keys = ['port', 'name', 'icon', 'array_size']
                if not all(key in config for key in required_keys):
                    return False
                if device_id not in self.device_types:
                    return False
            return True
        except:
            return False
    
    def validate_saved_config_ports(self, saved_config):
        """简单验证保存的配置中的端口是否存在（不检测有效性）"""
        try:
            # 只检查端口是否存在，不检查数据有效性
            ports = self.serial_interface.get_available_ports()
            available_port_names = [port['device'] for port in ports]
            
            for device_id, config in saved_config.items():
                port_name = config['port']
                if port_name not in available_port_names:
                    return False
            
            return True
        except:
            return False
    
    def apply_saved_config_to_ui(self, saved_config):
        """将保存的配置应用到UI界面并触发检测"""
        try:
            self.scan_status_label.config(text="✅ 已加载之前的配置", foreground="green")
            
            configured_count = 0
            port_list = []
            
            for device_id, config in saved_config.items():
                if device_id in self.device_rows:
                    port = config['port']
                    
                    # 获取当前下拉框选项
                    current_options = list(self.device_rows[device_id]['port_combo']['values'])
                    if not current_options:
                        current_options = [""]  # 确保有空选项
                    
                    # 如果保存的端口不在当前选项中，添加它
                    if port not in current_options:
                        current_options.append(port)
                        self.device_rows[device_id]['port_combo']['values'] = current_options
                    
                    # 设置为默认选择
                    self.device_rows[device_id]['port_var'].set(port)
                    
                    # 设置检测中状态
                    self.device_rows[device_id]['status_label'].config(text="🔍 检测中...", foreground="blue")
                    
                    # 立即触发1024字节检测
                    device_name = self.device_types[device_id]['name']
                    self.log_message(f"🔍 检测已保存的 {device_name} 端口 {port} 有效性...")
                    
                    def trigger_check(dev_id, port_name, dev_name):
                        def check_validity():
                            try:
                                result = self.check_port_validity_1024(port_name)
                                self.port_data_status[port_name] = result
                                
                                # 在主线程中更新UI
                                def update_ui():
                                    self.update_port_status_display(dev_id, port_name)
                                    self.update_ports_display()
                                    self.log_message(f"✅ {dev_name} 端口 {port_name} 检测完成: {result}")
                                
                                try:
                                    self.dialog.after(0, update_ui)
                                except:
                                    pass
                                    
                            except Exception as e:
                                error_result = f"❌ 检测失败: {str(e)[:20]}..."
                                self.port_data_status[port_name] = error_result
                                
                                def update_error():
                                    self.update_port_status_display(dev_id, port_name)
                                    self.log_message(f"❌ {dev_name} 端口 {port_name} 检测失败: {str(e)}")
                                
                                try:
                                    self.dialog.after(0, update_error)
                                except:
                                    pass
                        
                        # 启动检测线程
                        check_thread = threading.Thread(target=check_validity, daemon=True)
                        check_thread.start()
                    
                    # 延迟触发检测（避免UI阻塞）
                    self.dialog.after(100, lambda d=device_id, p=port, n=device_name: trigger_check(d, p, n))
                    
                    configured_count += 1
                    port_list.append(f"{config['icon']} {config['name']}: {port}")
            
            # 更新端口列表显示
            if port_list:
                self.ports_list_label.config(text=f"配置端口: {', '.join(port_list)}")
                
            self.log_message(f"✅ 已加载 {configured_count} 个设备配置，正在检测有效性...")
            
        except Exception as e:
            print(f"应用保存配置到UI失败: {e}")
    
    def log_message(self, message):
        """添加日志消息（如果有日志区域的话）"""
        try:
            print(f"[设备配置] {message}")  # 暂时输出到控制台
        except:
            pass
    
    
    def save_config(self, config_data):
        """保存配置到文件"""
        try:
            # 添加时间戳
            config_to_save = {
                'timestamp': datetime.now().isoformat(),
                'devices': config_data
            }
            
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(config_to_save, f, ensure_ascii=False, indent=2)
                
            print(f"配置已保存到: {self.config_file}")
            return True
        except Exception as e:
            print(f"保存配置失败: {e}")
            return False
        
    def setup_dialog_ui(self):
        """设置对话框UI"""
        # 主框架
        main_frame = ttk.Frame(self.dialog, padding=20)
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # 标题
        title_label = ttk.Label(main_frame, 
                               text="🔧 多设备压力传感器配置向导", 
                               font=("Arial", 16, "bold"))
        title_label.pack(pady=(0, 20))
        
        # 说明文字
        desc_label = ttk.Label(main_frame, 
                              text="请将需要使用的设备连接到计算机，系统将自动扫描并识别COM端口\n然后为每个设备选择对应的COM端口",
                              font=("Arial", 10),
                              justify=tk.CENTER)
        desc_label.pack(pady=(0, 20))
        
        # COM端口扫描状态
        scan_frame = ttk.LabelFrame(main_frame, text="📡 COM端口扫描", padding=10)
        scan_frame.pack(fill=tk.X, pady=(0, 20))
        
        self.scan_status_label = ttk.Label(scan_frame, text="正在扫描COM端口...", foreground="orange")
        self.scan_status_label.pack()
        
        self.ports_list_label = ttk.Label(scan_frame, text="发现的端口: 扫描中...", font=("Consolas", 9))
        self.ports_list_label.pack(pady=(5, 0))
        
        # 设备配置区域
        config_frame = ttk.LabelFrame(main_frame, text="🎯 设备配置", padding=10)
        config_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 20))
        
        # 设备配置表格
        self.setup_device_table(config_frame)
        
        # 按钮区域
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(fill=tk.X)
        
        ttk.Button(button_frame, text="🔄 重新扫描", command=self.refresh_ports).pack(side=tk.LEFT, padx=(0, 10))
        ttk.Button(button_frame, text="❌ 取消", command=self.cancel_config).pack(side=tk.RIGHT)
        ttk.Button(button_frame, text="✅ 确定", command=self.confirm_config).pack(side=tk.RIGHT, padx=(0, 10))
        
    def setup_device_table(self, parent):
        """设置设备配置表格"""
        # 表格框架
        table_frame = ttk.Frame(parent)
        table_frame.pack(fill=tk.BOTH, expand=True)
        
        # 表头
        header_frame = ttk.Frame(table_frame)
        header_frame.pack(fill=tk.X, pady=(0, 10))
        
        ttk.Label(header_frame, text="设备类型", width=15, font=("Arial", 10, "bold")).grid(row=0, column=0, padx=5)
        ttk.Label(header_frame, text="阵列大小", width=12, font=("Arial", 10, "bold")).grid(row=0, column=1, padx=5)
        ttk.Label(header_frame, text="COM端口", width=20, font=("Arial", 10, "bold")).grid(row=0, column=2, padx=5)
        ttk.Label(header_frame, text="状态", width=15, font=("Arial", 10, "bold")).grid(row=0, column=3, padx=5)
        
        # 设备配置行
        self.device_rows = {}
        for i, (device_id, device_info) in enumerate(self.device_types.items()):
            row_frame = ttk.Frame(table_frame)
            row_frame.pack(fill=tk.X, pady=2)
            
            # 设备类型
            device_label = ttk.Label(row_frame, 
                                   text=f"{device_info['icon']} {device_info['name']}", 
                                   width=15)
            device_label.grid(row=0, column=0, padx=5)
            
            # 阵列大小
            size_label = ttk.Label(row_frame, text=device_info['array_size'], width=12)
            size_label.grid(row=0, column=1, padx=5)
            
            # COM端口选择
            port_var = tk.StringVar()
            port_combo = ttk.Combobox(row_frame, textvariable=port_var, width=18, state="readonly")
            port_combo.grid(row=0, column=2, padx=5)
            
            # 状态显示
            status_label = ttk.Label(row_frame, text="未配置", width=15, foreground="gray")
            status_label.grid(row=0, column=3, padx=5)
            
            # 存储控件引用
            self.device_rows[device_id] = {
                'port_var': port_var,
                'port_combo': port_combo,
                'status_label': status_label
            }
            
            # 绑定选择事件
            port_combo.bind('<<ComboboxSelected>>', 
                           lambda e, dev_id=device_id: self.on_port_selected(dev_id))
    
    def start_port_scanning(self):
        """启动COM端口扫描 - 立即显示端口"""
        self.scanning = True
        scan_thread = threading.Thread(target=self.port_scanning_worker, daemon=True)
        scan_thread.start()
        
    def port_scanning_worker(self):
        """端口扫描工作线程 - 立即显示，不自动检测"""
        try:
            self.log_message("🔍 正在初始扫描可用端口...")
            
            # 快速获取所有可用端口
            ports = self.serial_interface.get_available_ports()
            new_ports = [port['device'] for port in ports]
            
            # 立即更新UI显示端口列表（不等待有效性检测）
            try:
                self.update_queue.put(("ports_found", new_ports))
                self.update_queue.put(("scan_complete", len(new_ports)))
            except:
                return
                
            self.log_message(f"✅ 初始扫描完成，发现 {len(new_ports)} 个端口，立即显示到UI")
            
        except Exception as e:
            self.log_message(f"❌ 初始扫描出错: {e}")
            try:
                self.update_queue.put(("scan_error", str(e)))
            except:
                pass
        
        # 扫描完成
        self.scanning = False
        
    def check_port_validity_1024(self, port_name):
        """检测端口是否有1024字节的有效数据帧"""
        try:
            import serial
            import time
            
            ser = serial.Serial(port_name, 1000000, timeout=1.0)
            
            # 读取数据检测是否有1024字节帧
            start_time = time.time()
            data_buffer = bytearray()
            frame_found = False
            
            while time.time() - start_time < 2.0 and not frame_found:  # 最多检测2秒
                data = ser.read(500)
                if data:
                    data_buffer.extend(data)
                    
                    # 查找帧头 AA 55 03 99
                    for i in range(len(data_buffer) - 3):
                        if (data_buffer[i] == 0xAA and data_buffer[i+1] == 0x55 and 
                            data_buffer[i+2] == 0x03 and data_buffer[i+3] == 0x99):
                            # 找到帧头，检查后续数据长度
                            if len(data_buffer) >= i + 4 + 1024:  # 帧头 + 1024字节数据
                                frame_found = True
                                break
                            # 如果数据不够，继续读取
                            elif len(data_buffer) >= i + 4 + 100:  # 至少有一些数据
                                # 检测数据的连续性，判断可能是1024字节帧
                                data_sample = data_buffer[i+4:i+104]  # 取100字节样本
                                if len([b for b in data_sample if b > 0]) > 10:  # 有足够的非零数据
                                    frame_found = True
                                    break
                else:
                    time.sleep(0.1)
            
            ser.close()
            
            if frame_found:
                return "✅ 1024字节有效数据"
            else:
                return "❌ 非1024字节数据"
                
        except Exception as e:
            error_msg = str(e)
            if "Access is denied" in error_msg or "PermissionError" in error_msg:
                return "❌ 端口被占用"
            elif "could not open port" in error_msg:
                return "❌ 端口不存在"
            else:
                return f"❌ 检测失败: {error_msg[:20]}..."
    
    def update_ports_display(self):
        """立即更新端口显示 - 不等待有效性检测"""
        try:
            if not self.dialog or not self.dialog.winfo_exists():
                return
        except:
            return
            
        try:
            if self.available_ports:
                self.scan_status_label.config(text=f"✅ 发现 {len(self.available_ports)} 个COM端口", 
                                            foreground="green")
                
                # 立即显示端口列表
                port_info = []
                for port in self.available_ports:
                    # 检查是否已有状态，没有则显示"未检测"
                    status = self.port_data_status.get(port, "未检测")
                    if "✅ 1024字节有效数据" in status:
                        simple_status = "有效"
                    elif "❌" in status:
                        simple_status = "无效"
                    elif "⚠️" in status:
                        simple_status = "警告"
                    else:
                        simple_status = "未检测"
                    port_info.append(f"{port}({simple_status})")
                
                self.ports_list_label.config(text=f"发现的端口: {', '.join(port_info)}")
                
                # 立即更新各设备的端口选项
                port_options = [""] + self.available_ports
                
                for device_id, row in self.device_rows.items():
                    current_value = row['port_var'].get()
                    row['port_combo']['values'] = port_options
                    
                    # 如果当前选择的端口不在端口列表中，清空选择
                    if current_value and current_value not in self.available_ports:
                        row['port_var'].set("")
                        row['status_label'].config(text="端口丢失", foreground="red")
                    elif current_value:
                        # 显示当前端口的检测状态
                        self.update_port_status_display(device_id, current_value)
                    else:
                        # 未选择端口
                        row['status_label'].config(text="未配置", foreground="gray")
                        
            else:
                self.scan_status_label.config(text="❌ 未发现COM端口", foreground="red")
                self.ports_list_label.config(text="发现的端口: 无")
                
                # 清空所有端口选项
                for device_id, row in self.device_rows.items():
                    row['port_combo']['values'] = [""]
                    row['port_var'].set("")
                    row['status_label'].config(text="无端口", foreground="red")
                    
        except Exception as e:
            print(f"更新端口显示出错: {e}")
    
    def update_port_status_display(self, device_id, port_name):
        """更新特定设备的端口状态显示"""
        try:
            status_label = self.device_rows[device_id]['status_label']
            data_status = self.port_data_status.get(port_name, "未检测")
            
            if "✅ 1024字节有效数据" in data_status:
                status_label.config(text="✅ 有效", foreground="green")
            elif "未检测" in data_status:
                status_label.config(text="⏳ 未检测", foreground="blue")
            elif "❌" in data_status:
                status_label.config(text="❌ 无效", foreground="red")
            elif "⚠️" in data_status:
                status_label.config(text="⚠️ 警告", foreground="orange")
            else:
                status_label.config(text="🔍 检测中", foreground="blue")
        except Exception as e:
            print(f"更新端口状态显示出错: {e}")
    
    def update_device_status_for_port(self, port_name):
        """更新所有使用指定端口的设备状态显示"""
        try:
            for device_id, row in self.device_rows.items():
                if row['port_var'].get() == port_name:
                    self.update_port_status_display(device_id, port_name)
        except Exception as e:
            print(f"更新设备端口状态出错: {e}")
    
    def on_port_selected(self, device_id):
        """端口选择事件 - 触发1024字节有效性检测"""
        selected_port = self.device_rows[device_id]['port_var'].get()
        status_label = self.device_rows[device_id]['status_label']
        device_name = self.device_types[device_id]['name']
        
        if selected_port:
            # 检查端口是否被其他设备占用，如果占用则直接替换
            for other_id, row in self.device_rows.items():
                if other_id != device_id and row['port_var'].get() == selected_port:
                    # 清空原设备的端口配置
                    other_device_name = self.device_types[other_id]['name']
                    row['port_var'].set("")  # 清空端口选择
                    row['status_label'].config(text="未配置", foreground="gray")  # 重置状态
                    
                    # 记录替换日志
                    self.log_message(f"🔄 端口 {selected_port} 从 {other_device_name} 转移到 {device_name}")
                    break
            
            # 显示检测中状态
            status_label.config(text="🔍 检测中...", foreground="blue")
            self.log_message(f"🔍 开始检测 {device_name} 端口 {selected_port} 的1024字节数据有效性...")
            
            # 在后台线程中进行有效性检测
            def check_validity():
                try:
                    result = self.check_port_validity_1024(selected_port)
                    self.port_data_status[selected_port] = result
                    
                    # 在主线程中更新UI
                    def update_ui():
                        self.update_port_status_display(device_id, selected_port)
                        self.update_ports_display()  # 更新端口列表显示
                        self.log_message(f"✅ {device_name} 端口 {selected_port} 检测完成: {result}")
                    
                    try:
                        self.dialog.after(0, update_ui)
                    except:
                        pass
                        
                except Exception as e:
                    error_result = f"❌ 检测失败: {str(e)[:20]}..."
                    self.port_data_status[selected_port] = error_result
                    
                    def update_error():
                        self.update_port_status_display(device_id, selected_port)
                        self.log_message(f"❌ {device_name} 端口 {selected_port} 检测失败: {str(e)}")
                    
                    try:
                        self.dialog.after(0, update_error)
                    except:
                        pass
            
            # 启动检测线程
            check_thread = threading.Thread(target=check_validity, daemon=True)
            check_thread.start()
            
        else:
            status_label.config(text="未配置", foreground="gray")
    
    def refresh_ports(self):
        """手动刷新端口 - 立即显示，不自动检测"""
        self.log_message("🔄 开始手动刷新端口...")
        self.scan_status_label.config(text="正在刷新...", foreground="orange")
        self.ports_list_label.config(text="发现的端口: 刷新中...")
        
        # 清空端口数据状态
        self.port_data_status.clear()
        
        # 清空当前端口列表
        self.available_ports = []
        
        # 重新启动扫描
        self.scanning = True
        refresh_thread = threading.Thread(target=self.refresh_worker, daemon=True)
        refresh_thread.start()
        
    def refresh_worker(self):
        """刷新工作线程 - 确保完成后更新UI状态"""
        try:
            self.log_message("🔍 正在扫描可用端口...")
            
            # 快速获取所有可用端口
            ports = self.serial_interface.get_available_ports()
            new_ports = [port['device'] for port in ports]
            
            self.log_message(f"✅ 扫描完成，发现 {len(new_ports)} 个端口")
            
            # 立即更新UI显示端口列表
            try:
                self.update_queue.put(("ports_found", new_ports))
                self.update_queue.put(("refresh_complete", len(new_ports)))
            except:
                return
                
        except Exception as e:
            self.log_message(f"❌ 刷新失败: {e}")
            try:
                self.update_queue.put(("scan_error", str(e)))
            except:
                pass
        
        # 刷新完成
        self.scanning = False
    
    def immediate_scan(self):
        """立即扫描 - 只扫描端口，不检测有效性"""
        try:
            self.log_message("🔍 立即扫描端口...")
            ports = self.serial_interface.get_available_ports()
            new_ports = [port['device'] for port in ports]
            
            # 通过队列通知更新
            try:
                self.update_queue.put(("ports_found", new_ports))
                self.update_queue.put(("scan_complete", len(new_ports)))
            except:
                pass
                
            self.log_message(f"✅ 立即扫描完成，发现 {len(new_ports)} 个端口")
                
        except Exception as e:
            self.log_message(f"❌ 立即扫描出错: {e}")
            try:
                self.update_queue.put(("scan_error", str(e)))
            except:
                pass
    
    def confirm_config(self):
        """确认配置"""
        # 收集配置结果
        config_result = {}
        configured_count = 0
        
        for device_id, row in self.device_rows.items():
            selected_port = row['port_var'].get()
            if selected_port:
                config_result[device_id] = {
                    'port': selected_port,
                    'name': self.device_types[device_id]['name'],
                    'icon': self.device_types[device_id]['icon'],
                    'array_size': self.device_types[device_id]['array_size']
                }
                configured_count += 1
        
        if configured_count == 0:
            messagebox.showwarning("配置警告", "请至少配置一个设备！")
            return
        
        # 确认配置
        msg = f"确定要配置 {configured_count} 个设备吗？\n\n"
        for device_id, config in config_result.items():
            msg += f"{config['icon']} {config['name']}: {config['port']} ({config['array_size']})\n"
            
        if messagebox.askyesno("确认配置", msg):
            # 保存配置
            if self.save_config(config_result):
                messagebox.showinfo("保存成功", "设备配置已保存，下次启动时将自动加载。")
            
            self.result = config_result
            self.scanning = False
            try:
                if self.dialog and self.dialog.winfo_exists():
                    self.dialog.destroy()
            except:
                pass
    
    def cancel_config(self):
        """取消配置"""
        self.result = None
        self.scanning = False
        try:
            if self.dialog and self.dialog.winfo_exists():
                self.dialog.destroy()
        except:
            pass

class DeviceManager:
    """设备管理器"""
    
    def __init__(self):
        self.devices = {}
        self.current_device = None
        self.serial_interfaces = {}
        
    def setup_devices(self, device_configs):
        """设置设备配置"""
        self.devices = device_configs
        
        # 为每个设备创建串口接口
        for device_id, config in device_configs.items():
            self.serial_interfaces[device_id] = SerialInterface(baudrate=1000000)
            
        # 设置默认设备
        if self.devices:
            self.current_device = list(self.devices.keys())[0]
            
    def get_device_list(self):
        """获取设备列表"""
        return [(device_id, config['name'], config['icon']) 
                for device_id, config in self.devices.items()]
    
    def switch_device(self, device_id):
        """切换当前设备"""
        if device_id in self.devices:
            self.current_device = device_id
            return True
        return False
    
    def get_current_device_info(self):
        """获取当前设备信息"""
        if self.current_device and self.current_device in self.devices:
            return self.devices[self.current_device]
        return None
    
    def get_current_serial_interface(self):
        """获取当前设备的串口接口"""
        if self.current_device and self.current_device in self.serial_interfaces:
            return self.serial_interfaces[self.current_device]
        return None
    
    def connect_current_device(self):
        """连接当前设备"""
        if self.current_device and self.current_device in self.devices:
            device_config = self.devices[self.current_device]
            serial_interface = self.serial_interfaces[self.current_device]
            
            try:
                return serial_interface.connect(device_config['port'])
            except Exception as e:
                print(f"连接设备失败: {e}")
                return False
        return False
    
    def disconnect_current_device(self):
        """断开当前设备"""
        if self.current_device and self.current_device in self.serial_interfaces:
            serial_interface = self.serial_interfaces[self.current_device]
            serial_interface.disconnect()