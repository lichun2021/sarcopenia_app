#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
智能肌少症检测系统 - 压力传感器数据可视化界面
模块化重构版本 - 主UI控制器
"""

import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox, filedialog
import threading
import time
import os
import json
import sqlite3
from datetime import datetime

# 导入自定义模块
from serial_interface import SerialInterface
from data_processor import DataProcessor
from visualization import HeatmapVisualizer
from device_config import DeviceConfigDialog, DeviceManager
from patient_manager_ui import PatientManagerDialog
from sarcopenia_database import db
from detection_wizard_ui import DetectionWizardDialog

# 导入 SarcNeuro Edge 相关模块
try:
    from sarcneuro_service import SarcNeuroEdgeService
    from data_converter import SarcopeniaDataConverter
    from patient_info_dialog import PatientInfoDialog
    SARCNEURO_AVAILABLE = True
except ImportError as e:
    print(f"[WARN] SarcNeuro Edge 功能不可用: {e}")
    SARCNEURO_AVAILABLE = False

class PressureSensorUI:
    """主UI控制器类"""
    
    def __init__(self, root):
        self.root = root
        self.root.title("智能肌少症检测系统 - 压力传感器可视化 (模块化版本)")
        
        # 先隐藏窗口，避免初始化时的闪烁
        self.root.withdraw()
        
        # 禁用窗口调整大小，减少初始化时的布局计算
        self.root.resizable(False, False)
        
        # 预设置窗口位置（避免geometry计算延迟）
        self.root.geometry("1600x1100+200+50")
        
        # 延迟精确居中到UI完成后
        self._needs_centering = True
        
        # 设置背景和基本样式
        self.root.configure(bg='#ffffff')  # 纯白背景，医院风格
        
        # 启用双缓冲减少重绘闪烁
        self.root.option_add('*tearOff', False)
        
        # 设置窗口图标
        try:
            self.root.iconbitmap("icon.ico")
        except Exception:
            # 如果图标文件不存在，使用默认图标
            pass
        
        # 清理过期会话数据
        self._cleanup_expired_sessions()
        
        # 初始化多设备管理器
        self.device_manager = DeviceManager()
        self.serial_interface = None  # 将根据当前设备动态获取
        self.data_processor = DataProcessor(array_rows=32, array_cols=32)
        self.visualizer = None  # 在UI设置后创建
        
        # 设备配置状态
        self.device_configured = False
        
        # SarcNeuro Edge 服务
        self.sarcneuro_service = None
        self.init_sarcneuro_service()
        
        # 患者和检测管理
        self.current_patient = None
        self.current_session = None
        self.detection_in_progress = False
        
        # 数据监控
        self.is_running = False
        self.update_thread = None
        self.data_rate = 0
        self.last_frame_count = 0
        self.last_time = time.time()
        self.last_data_time = time.time()
        self.auto_reconnect_enabled = True
        self.device_lost_warned = False  # 防止重复弹窗
        
        # 活动的检测向导引用
        self._active_detection_wizard = None
        
        # 界面设置
        self.setup_ui()
        self.setup_visualizer()
        
        # 分阶段完成初始化以提升响应速度
        self._complete_initialization()
    
    def _complete_initialization(self):
        """分阶段完成初始化，提升启动响应速度"""
        # 第一阶段：立即显示窗口（100ms后）
        self.root.after(100, self._stage1_show_window)
    
    def _stage1_show_window(self):
        """第一阶段：显示窗口并居中"""
        # 精确居中显示
        if self._needs_centering:
            self.root.update_idletasks()
            window_width = 1600
            window_height = 1100
            screen_width = self.root.winfo_screenwidth()
            screen_height = self.root.winfo_screenheight()
            x = (screen_width - window_width) // 2
            y = (screen_height - window_height) // 2
            self.root.geometry(f"{window_width}x{window_height}+{x}+{y}")
            self._needs_centering = False
        
        # 重新启用调整大小并显示窗口
        self.root.resizable(True, True)
        self.root.deiconify()
        
        # 显示启动状态
        self._show_startup_status("🔄 正在初始化核心服务...")
        
        # 第二阶段：启动核心服务（200ms后）
        self.root.after(200, self._stage2_start_services)
    
    def _stage2_start_services(self):
        """第二阶段：启动核心服务"""
        # 更新启动状态
        self._show_startup_status("⚡ 启动数据更新服务...")
        
        # 启动更新循环
        self.start_update_loop()
        
        # 启动连接监控
        self.start_connection_monitor()
        
        # 第三阶段：集成扩展功能（400ms后）
        self.root.after(400, self._stage3_integrate_features)
    
    def _stage3_integrate_features(self):
        """第三阶段：集成扩展功能"""
        # 更新启动状态
        self._show_startup_status("🧠 集成智能分析功能...")
        
        # 集成肌少症分析功能
        self.integrate_sarcneuro_analysis()
        
        # 延迟2秒启动SarcNeuro Edge服务，避免影响UI启动速度
        self.root.after(2000, self._delayed_start_sarcneuro_service)
        
        # 第四阶段：自动加载配置（600ms后）
        self.root.after(600, self._stage4_load_config)
    
    def _stage4_load_config(self):
        """第四阶段：加载设备配置"""
        # 更新启动状态
        self._show_startup_status("⚙️ 正在加载设备配置...")
        
        # 延迟加载配置，给用户看到状态
        self.root.after(200, self._finalize_startup)
    
    def _finalize_startup(self):
        """完成启动流程"""
        # 隐藏启动状态
        self._hide_startup_status()
        
        # 加载配置
        self.auto_load_or_show_config()
    
    def _show_startup_status(self, message):
        """显示启动状态信息"""
        if hasattr(self, 'status_bar') and self.status_bar:
            self.status_bar.config(text=message, foreground='blue')
    
    def _hide_startup_status(self):
        """隐藏启动状态信息"""
        if hasattr(self, 'status_bar') and self.status_bar:
            self.status_bar.config(text="系统就绪", foreground='green')
    
    def auto_load_or_show_config(self):
        """自动加载已保存的配置，如果没有则显示配置对话框"""
        try:
            # 直接加载配置数据，无需创建完整的对话框实例
            from device_config import DeviceConfigDialog
            import sqlite3
            import os
            
            config_db = "device_config.db"
            saved_config = None
            
            # 直接从数据库加载配置
            if os.path.exists(config_db):
                try:
                    conn = sqlite3.connect(config_db, timeout=10.0)
                    cursor = conn.cursor()
                    
                    # 尝试新的数据库架构
                    try:
                        cursor.execute('''
                            SELECT device_id, ports, port, name, icon, array_size, com_ports, device_type 
                            FROM device_configs
                        ''')
                        rows = cursor.fetchall()
                        
                        if rows:
                            saved_config = {}
                            import json
                            for row in rows:
                                device_id, ports_str, port, name, icon, array_size, com_ports, device_type = row
                                
                                # 解析端口列表
                                try:
                                    ports_list = json.loads(ports_str)
                                except:
                                    ports_list = [port] if port else []
                                
                                saved_config[device_id] = {
                                    'ports': ports_list,
                                    'port': port,
                                    'name': name,
                                    'icon': icon,
                                    'array_size': array_size,
                                    'com_ports': com_ports,
                                    'device_type': device_type
                                }
                    except sqlite3.OperationalError:
                        # 尝试旧的数据库架构
                        cursor.execute('SELECT device_id, port, name, icon, array_size FROM device_configs')
                        rows = cursor.fetchall()
                        
                        if rows:
                            saved_config = {}
                            for row in rows:
                                device_id, port, name, icon, array_size = row
                                saved_config[device_id] = {
                                    'ports': [port] if port else [],
                                    'port': port,
                                    'name': name,
                                    'icon': icon,
                                    'array_size': array_size,
                                    'com_ports': 1,
                                    'device_type': 'single'
                                }
                    
                    conn.close()
                except Exception as e:
                    print(f"加载配置数据库失败: {e}")
                    saved_config = None
            
            if saved_config:
                # 找到已保存的配置，直接加载
                print(f"[OK] 检测到已保存的配置，包含 {len(saved_config)} 个设备，自动加载中...")
                self.log_message(f"[OK] 自动加载已保存的配置 ({len(saved_config)} 个设备)")
                
                # 直接设置设备配置，无需显示对话框
                if self.serial_interface:
                    current_port = self.serial_interface.get_current_port()
                    if current_port:
                        # 找到使用此端口的设备配置
                        for device_id, config in saved_config.items():
                            ports = config.get('ports', [])
                            if current_port in ports:
                                # 将现有接口添加到设备管理器
                                self.device_manager.serial_interfaces[device_id] = self.serial_interface
                                print(f"重用现有连接 {current_port} (设备: {config['name']})")
                                break
                
                # 设置设备配置
                self.device_manager.setup_devices(saved_config)
                self.device_configured = True
                
                # 更新设备选择列表
                self.update_device_list()
                
                # 自动选择第一个设备
                device_list = self.device_manager.get_device_list()
                if device_list:
                    first_device_id = device_list[0][0]
                    self.device_var.set(f"{saved_config[first_device_id]['icon']} {saved_config[first_device_id]['name']}")
                    
                    # 获取串口接口并设置设备模式
                    self.serial_interface = self.device_manager.get_current_serial_interface()
                    if self.serial_interface:
                        device_type = saved_config[first_device_id].get('device_type', 'single')
                        array_size = saved_config[first_device_id]['array_size']
                        com_ports = saved_config[first_device_id].get('com_ports', 1)
                        
                        # 根据接口类型设置模式
                        if com_ports > 1:
                            # 多端口接口
                            if hasattr(self.serial_interface, 'set_device_mode'):
                                self.serial_interface.set_device_mode(device_type)
                        else:
                            # 单端口接口
                            if hasattr(self.serial_interface, 'set_device_mode'):
                                self.serial_interface.set_device_mode(device_type)
                            elif array_size == '32x96' or device_type == 'walkway':
                                # 向后兼容
                                if hasattr(self.serial_interface, 'set_walkway_mode'):
                                    self.serial_interface.set_walkway_mode(True)
                        
                        # 重要：根据设备配置自动调整热力图大小
                        self.auto_config_array_size(array_size)
                    
                    self.on_device_changed(None)
                
                self.log_message("[OK] 设备配置自动加载完成！")
                
            else:
                # 没有找到已保存的配置，显示配置对话框
                print("[WARN] 未找到已保存的配置，显示配置对话框...")
                self.log_message("[WARN] 首次启动，需要配置设备")
                self.show_device_config()
                
        except Exception as e:
            print(f"[ERROR] 自动加载配置失败: {e}")
            self.log_message(f"[ERROR] 自动加载配置失败: {e}")
            # 出错时显示配置对话框
            self.show_device_config()
    
    def show_device_config(self):
        """显示设备配置对话框"""
        # 获取当前正在使用的端口，避免重复检测
        skip_ports = []
        
        # 方法1：从设备管理器获取已配置的端口
        if self.device_configured and self.device_manager:
            current_device_info = self.device_manager.get_current_device_info()
            if current_device_info:
                # 添加当前设备使用的所有端口到跳过列表
                ports = current_device_info.get('ports', [])
                if ports:
                    skip_ports.extend(ports)
                elif current_device_info.get('port'):
                    skip_ports.append(current_device_info['port'])
        
        # 方法2：从串口接口获取当前连接的端口
        if self.serial_interface:
            current_port = self.serial_interface.get_current_port()
            if current_port and current_port not in skip_ports:
                skip_ports.append(current_port)
        
        # 方法3：从设备管理器的所有串口接口获取端口
        if self.device_manager and hasattr(self.device_manager, 'serial_interfaces'):
            for serial_interface in self.device_manager.serial_interfaces.values():
                if serial_interface:
                    current_port = serial_interface.get_current_port()
                    if current_port and current_port not in skip_ports:
                        skip_ports.append(current_port)
        
        if skip_ports:
            print(f"跳过检测端口: {skip_ports} (主程序正在使用)")
        
        config_dialog = DeviceConfigDialog(self.root, skip_port_detection=skip_ports)
        device_configs = config_dialog.show_dialog()
        
        if device_configs:
            # 如果已有串口连接，将其传递给设备管理器以便重用
            if self.serial_interface:
                current_port = self.serial_interface.get_current_port()
                if current_port:
                    # 找到使用此端口的设备配置
                    for device_id, config in device_configs.items():
                        ports = config.get('ports', [])
                        com_ports = config.get('com_ports', 1)
                        
                        if current_port in ports:
                            # 检查是否为单端口设备
                            if com_ports == 1:
                                # 单端口设备：直接传递现有接口
                                self.device_manager.serial_interfaces[device_id] = self.serial_interface
                                print(f"传递现有单端口连接 {current_port} 给设备管理器 (设备: {config['name']})")
                            else:
                                # 多端口设备：不能直接使用现有单端口连接
                                # 设备管理器的setup_devices会检测到现有连接并正确处理转换
                                print(f"检测到多端口设备 {config['name']} 包含现有端口 {current_port}")
                                print(f"将由设备管理器处理单端口到多端口的转换 (端口: {', '.join(ports)})")
                            break
            
            # 设置设备配置
            self.device_manager.setup_devices(device_configs)
            self.device_configured = True
            
            # 更新设备选择列表
            self.update_device_list()
            
            # 自动选择第一个设备
            device_list = self.device_manager.get_device_list()
            if device_list:
                first_device_id = device_list[0][0]
                self.device_var.set(f"{device_configs[first_device_id]['icon']} {device_configs[first_device_id]['name']}")
                
                # 获取串口接口并设置步道模式
                self.serial_interface = self.device_manager.get_current_serial_interface()
                array_size = device_configs[first_device_id]['array_size']
                if array_size == '32x96':
                    self.serial_interface.set_walkway_mode(True)
                
                # 重要：根据设备配置自动调整热力图大小
                self.auto_config_array_size(array_size)
                
                self.on_device_changed(None)
                
            self.log_message("[OK] 设备配置完成！")
        else:
            # 用户取消配置，显示警告
            if not self.device_configured:
                messagebox.showwarning("配置取消", "需要配置设备才能使用系统！")
                self.root.after(2000, self.root.quit)  # 2秒后退出
    
    def update_device_list(self):
        """更新设备选择列表"""
        device_list = self.device_manager.get_device_list()
        device_options = [f"{icon} {name}" for _, name, icon in device_list]
        self.device_combo['values'] = device_options
        
        if device_options:
            self.device_combo.config(state="readonly")
        else:
            self.device_combo.config(state="disabled")
    
    def on_device_changed(self, event):
        """设备切换事件"""
        if not self.device_configured:
            return
            
        selected_display = self.device_var.get()
        if not selected_display:
            return
            
        # 找到对应的设备ID
        device_list = self.device_manager.get_device_list()
        for device_id, name, icon in device_list:
            if f"{icon} {name}" == selected_display:
                # 获取目标设备信息
                target_device_configs = self.device_manager.devices
                if device_id not in target_device_configs:
                    self.log_message(f"[ERROR] 设备配置不存在: {name}")
                    self.restore_current_device_selection()
                    return
                
                # 获取设备端口配置
                device_config = target_device_configs[device_id]
                com_ports = device_config.get('com_ports', 1)
                
                if com_ports == 1:
                    # 单端口设备
                    target_port = device_config.get('port') or device_config.get('ports', [None])[0]
                    
                    # 检查目标端口是否存在和有效
                    if not target_port or not self.check_port_availability(target_port):
                        self.log_message(f"[ERROR] 设备端口无效或不存在: {name} ({target_port})")
                        messagebox.showwarning("设备切换失败", 
                                             f"无法切换到 {icon} {name}\n端口 {target_port} 不存在或无有效数据")
                        self.restore_current_device_selection()
                        return
                else:
                    # 多端口设备
                    ports = device_config.get('ports', [])
                    if not ports or len(ports) != com_ports:
                        self.log_message(f"[ERROR] 多端口设备配置不完整: {name} (需要{com_ports}个端口，实际{len(ports)}个)")
                        messagebox.showwarning("设备切换失败", 
                                             f"无法切换到 {icon} {name}\n多端口设备配置不完整")
                        self.restore_current_device_selection()
                        return
                    
                    # 检查所有端口是否可用
                    invalid_ports = []
                    for port in ports:
                        if not self.check_port_availability(port):
                            invalid_ports.append(port)
                    
                    if invalid_ports:
                        self.log_message(f"[ERROR] 多端口设备部分端口无效: {name} ({', '.join(invalid_ports)})")
                        messagebox.showwarning("设备切换失败", 
                                             f"无法切换到 {icon} {name}\n以下端口不存在或无有效数据:\n{', '.join(invalid_ports)}")
                        self.restore_current_device_selection()
                        return
                
                # 断开当前设备
                if self.is_running:
                    self.stop_connection()
                
                # 切换设备
                self.device_manager.switch_device(device_id)
                self.serial_interface = self.device_manager.get_current_serial_interface()
                
                # 调试输出：显示当前接口信息
                if self.serial_interface:
                    interface_type = type(self.serial_interface).__name__
                    multi_config = getattr(self.serial_interface, 'multi_port_config', None)
                    device_type = getattr(self.serial_interface, 'device_type', 'unknown')
                
                # 更新UI显示
                device_info = self.device_manager.get_current_device_info()
                if device_info:
                    # 显示端口信息
                    com_ports = device_info.get('com_ports', 1)
                    if com_ports > 1:
                        ports = device_info.get('ports', [])
                        port_display = f"端口: {', '.join(ports)} ({com_ports}个)"
                    else:
                        port = device_info.get('port') or device_info.get('ports', ['未知'])[0]
                        port_display = f"端口: {port}"
                    self.port_info_label.config(text=port_display)
                    
                    # 自动根据设备类型配置数组大小
                    self.auto_config_array_size(device_info['array_size'])
                    
                    # 根据设备类型设置模式
                    device_type = device_info.get('device_type', 'single')
                    com_ports = device_info.get('com_ports', 1)
                    array_size = device_info['array_size']
                    
                    if com_ports > 1:
                        # 多端口设备
                        if hasattr(self.serial_interface, 'set_device_mode'):
                            self.serial_interface.set_device_mode(device_type)
                        self.log_message(f"[OK] 已启用多端口模式（{com_ports}个端口数据合并）")
                    elif array_size == '32x96' or device_type == 'walkway':
                        # 单端口步道设备
                        if hasattr(self.serial_interface, 'set_walkway_mode'):
                            self.serial_interface.set_walkway_mode(True)
                        elif hasattr(self.serial_interface, 'set_device_mode'):
                            self.serial_interface.set_device_mode(device_type)
                        self.log_message("[OK] 已启用步道模式（3帧数据合并）")
                    else:
                        # 普通单端口设备
                        if hasattr(self.serial_interface, 'set_walkway_mode'):
                            self.serial_interface.set_walkway_mode(False)
                        elif hasattr(self.serial_interface, 'set_device_mode'):
                            self.serial_interface.set_device_mode('single')
                    
                    # 更新标题
                    self.root.title(f"智能肌少症检测系统 - {device_info['icon']} {device_info['name']}")
                    
                    # 显示切换日志
                    com_ports = device_info.get('com_ports', 1)
                    if com_ports > 1:
                        ports = device_info.get('ports', [])
                        port_display = ', '.join(ports)
                    else:
                        port_display = device_info.get('port') or device_info.get('ports', ['未知'])[0]
                    
                    self.log_message(f"[OK] 已切换到设备: {device_info['icon']} {device_info['name']} ({port_display})")
                    
                    # 延迟自动连接设备，给端口释放时间
                    self.root.after(1000, self.auto_connect_device)  # 等待1秒后连接
                    
                break
    
    def check_port_availability(self, port_name):
        """快速检查端口是否可用"""
        try:
            # 简化检测：只检查端口是否存在即可
            from serial_interface import SerialInterface
            temp_serial = SerialInterface()
            ports = temp_serial.get_available_ports()
            available_ports = [port['device'] for port in ports]
            
            return port_name in available_ports
                
        except Exception as e:
            self.log_message(f"[ERROR] 检查端口失败: {e}")
            return False
    
    def restore_current_device_selection(self):
        """恢复当前设备选择"""
        try:
            if self.device_manager.current_device:
                current_device_info = self.device_manager.get_current_device_info()
                if current_device_info:
                    current_display = f"{current_device_info['icon']} {current_device_info['name']}"
                    self.device_var.set(current_display)
        except:
            pass
    
    def auto_connect_device(self):
        """自动连接当前设备"""
        if not self.device_configured or not self.serial_interface:
            return
            
        try:
            device_info = self.device_manager.get_current_device_info()
            if not device_info:
                return
                
            # 显示设备端口信息
            com_ports = device_info.get('com_ports', 1)
            if com_ports > 1:
                ports = device_info.get('ports', [])
                port_display = ', '.join(ports)
            else:
                port_display = device_info.get('port') or device_info.get('ports', ['未知'])[0]
            
            self.log_message(f"[REFRESH] 自动连接设备: {device_info['icon']} {device_info['name']} ({port_display})")
            
            if self.device_manager.connect_current_device():
                self.is_running = True
                self.last_data_time = time.time()
                self.device_lost_warned = False  # 重置警告状态
                
                # 更新UI状态
                self.status_label.config(text="🟢 已连接", foreground="green")
                self.log_message(f"[OK] 自动连接成功: {device_info['icon']} {device_info['name']}")
                
                # 连接成功后仍允许设备切换
                if self.device_configured:
                    self.device_combo.config(state="readonly")
                
            else:
                self.status_label.config(text="[ERROR] 连接失败", foreground="red")
                self.log_message(f"[ERROR] 自动连接失败: {device_info['icon']} {device_info['name']}")
                
        except Exception as e:
            self.status_label.config(text="[ERROR] 连接错误", foreground="red")
            self.log_message(f"[ERROR] 自动连接错误: {e}")
    
    def start_connection_monitor(self):
        """启动连接监控"""
        self.connection_monitor()
    
    def connection_monitor(self):
        """连接监控和自动重连"""
        try:
            if self.device_configured and self.is_running:
                current_time = time.time()
                
                # 检查是否超过10秒没有数据
                if current_time - self.last_data_time > 10:
                    if not self.device_lost_warned:
                        # 弹窗提示设备丢失
                        device_info = self.device_manager.get_current_device_info()
                        if device_info:
                            self.device_lost_warned = True
                            self.show_device_lost_warning(device_info)
                    
                    self.log_message("[WARN] 检测到连接异常，尝试重新连接...")
                    
                    # 断开当前连接
                    self.stop_connection()
                    
                    # 等待一下再重连
                    self.root.after(2000, self.auto_connect_device)
                    
        except Exception as e:
            self.log_message(f"[ERROR] 连接监控出错: {e}")
        
        # 每5秒检查一次连接状态
        self.root.after(5000, self.connection_monitor)
    
    def show_device_lost_warning(self, device_info):
        """显示设备丢失警告"""
        def show_warning():
            # 显示设备端口信息
            com_ports = device_info.get('com_ports', 1)
            if com_ports > 1:
                ports = device_info.get('ports', [])
                port_display = ', '.join(ports)
            else:
                port_display = device_info.get('port') or device_info.get('ports', ['未知'])[0]
            
            result = messagebox.askretrycancel(
                "设备连接丢失", 
                f"[WARN] 设备连接已丢失\n\n"
                f"设备: {device_info['icon']} {device_info['name']}\n"
                f"端口: {port_display}\n\n"
                f"请检查设备连接状态\n\n"
                f"点击'重试'继续尝试连接\n"
                f"点击'取消'停止重连"
            )
            
            if not result:
                # 用户选择取消，停止重连
                self.auto_reconnect_enabled = False
                self.stop_connection()
                self.log_message("[INFO] 用户取消重连，已停止自动连接")
        
        # 在主线程中显示警告
        self.root.after(0, show_warning)
        
    def create_menubar(self):
        """创建医院风格的专业菜单栏"""
        menubar = tk.Menu(self.root, 
                         bg='#ffffff',       # 纯白背景，医院清洁风格
                         fg='#1a1a1a',       # 深黑色文字，最高对比度
                         activebackground='#f0f8ff',  # 极淡蓝色悬停，医疗风格
                         activeforeground='#0066cc',  # 专业医疗蓝色文字
                         font=('Microsoft YaHei UI', 12, 'normal'),  # 增大字体提高高度
                         borderwidth=0,      # 无边框，清洁感
                         relief='flat',      # 平滑无立体效果
                         selectcolor='#4a90e2',  # 选中时的蓝色
                         activeborderwidth=1,  # 悬停时细边框
                         disabledforeground='#888888')  # 禁用项灰色
        self.root.config(menu=menubar)
        
        # 创建"文件"菜单 (医院风格配色)
        file_menu = tk.Menu(menubar, tearoff=0,
                           bg='#ffffff',        # 纯白背景，医院风格
                           fg='#37474f',        # 深灰色文字
                           activebackground='#e8f5e8',  # 淡绿色悬停（健康色调）
                           activeforeground='#2e7d32',   # 深绿色悬停文字
                           font=('Microsoft YaHei UI', 11),
                           borderwidth=1,
                           relief='solid',
                           selectcolor='#4caf50')
        menubar.add_cascade(label="  📄 文件  ", menu=file_menu, 
                          activebackground='#f0f8ff', activeforeground='#0066cc')
        
        # 添加文件菜单项
        file_menu.add_separator()
        file_menu.add_command(label="💾 导出设备日志", command=self.save_log)
        file_menu.add_command(label="📸 保存热力图快照", command=self.save_snapshot)
        file_menu.add_separator()
        file_menu.add_command(label="❌ 退出系统", command=self.on_closing)
        
        # 创建"检测"菜单（使用医疗蓝色主题）
        detection_menu = tk.Menu(menubar, tearoff=0,
                               bg='#ffffff',        # 纯白背景
                               fg='#37474f',        # 深灰色文字
                               activebackground='#e3f2fd',  # 淡蓝色悬停
                               activeforeground='#1976d2',   # 医疗蓝悬停文字
                               font=('Microsoft YaHei UI', 11),
                               borderwidth=1,
                               relief='solid',
                               selectcolor='#2196f3')
        menubar.add_cascade(label="  🔬 检测  ", menu=detection_menu, 
                          activebackground='#f0f8ff', activeforeground='#0066cc')
        
        # 添加检测菜单项
        detection_menu.add_command(label="🚀 开始检测", command=self.start_detection_process)
        detection_menu.add_separator()
        detection_menu.add_command(label="👥 患者档案管理", command=self.show_patient_manager)
        detection_menu.add_command(label="📋 检测会话管理", command=self.show_session_manager)
        detection_menu.add_command(label="📋 检测流程指导", command=self.show_detection_process_dialog)
        # detection_menu.add_separator()
        # detection_menu.add_command(label="⚙️ 设备配置管理", command=self.show_device_config)
        
        # 创建"设备"菜单（使用淡紫色医疗主题）
        device_menu = tk.Menu(menubar, tearoff=0,
                             bg='#ffffff',        # 纯白背景
                             fg='#37474f',        # 深灰色文字
                             activebackground='#f3e5f5',  # 淡紫色悬停
                             activeforeground='#7b1fa2',   # 深紫色悬停文字
                             font=('Microsoft YaHei UI', 11),
                             borderwidth=1,
                             relief='solid',
                             selectcolor='#9c27b0')
        menubar.add_cascade(label="  📱 设备  ", menu=device_menu,
                          activebackground='#f0f8ff', activeforeground='#0066cc')
        
        # 添加设备菜单项
        device_menu.add_command(label="🔍 设备配置", command=lambda: self.show_device_config())
  
        
        # 创建"分析"菜单（使用医疗红色主题）
        analysis_menu = tk.Menu(menubar, tearoff=0,
                              bg='#ffffff',        # 纯白背景
                              fg='#37474f',        # 深灰色文字
                              activebackground='#ffebee',  # 淡红色悬停
                              activeforeground='#c62828',   # 深红色悬停文字
                              font=('Microsoft YaHei UI', 11),
                              borderwidth=1,
                              relief='solid',
                              selectcolor='#f44336')
        menubar.add_cascade(label="  🧠 AI分析  ", menu=analysis_menu,
                          activebackground='#f0f8ff', activeforeground='#0066cc')
        
        # 添加分析菜单项
        analysis_menu.add_command(label="📄 导入CSV生成报告", command=self.import_csv_for_analysis)
        analysis_menu.add_command(label="🤖 Sarcneuro Edge服务状态", command=self.show_service_status)
        
        # 创建"帮助"菜单（使用医疗绿色主题）
        help_menu = tk.Menu(menubar, tearoff=0,
                           bg='#ffffff',        # 纯白背景
                           fg='#37474f',        # 深灰色文字
                           activebackground='#e8f5e8',  # 淡绿色悬停
                           activeforeground='#2e7d32',   # 深绿色悬停文字
                           font=('Microsoft YaHei UI', 11),
                           borderwidth=1,
                           relief='solid',
                           selectcolor='#4caf50')
        menubar.add_cascade(label="  ❓ 帮助  ", menu=help_menu,
                          activebackground='#f0f8ff', activeforeground='#0066cc')
        
        # 添加帮助菜单项
        help_menu.add_command(label="📖 操作指南手册", command=self.show_help_dialog)
        # help_menu.add_command(label="🚀 快速入门教程", command=lambda: messagebox.showinfo("快速入门", 
        #                         "智能肌少症检测系统快速入门:\n\n1️⃣ 设备配置\n   • 点击'设备配置'选择设备类型\n   • 配置COM端口连接\n\n2️⃣ 开始检测\n   • 确保设备连接正常\n   • 观察热力图实时显示\n\n3️⃣ 数据分析\n   • 查看右侧统计数据\n   • 保存检测快照和日志"))
        # help_menu.add_separator()
        # help_menu.add_command(label="🏥 产品介绍", command=lambda: messagebox.showinfo("产品介绍", 
        #                         "智能肌少症检测系统\n\n🔬 专业医疗设备\n• 压力传感器阵列技术\n• 实时数据可视化分析\n• 标准化检测流程\n\n🏥 适用场景\n• 医院康复科\n• 体检中心\n• 养老机构\n• 健康管理中心"))
        # help_menu.add_separator()
        # help_menu.add_command(label="🌐 官方网站", command=lambda: messagebox.showinfo("联系方式", 
        #                         "威海聚桥工业科技有限公司\n\n🌐 官方网站: www.jq-tech.com\n📧 技术支持: support@jq-tech.com\n📱 客服热线: 400-xxx-xxxx"))
        # help_menu.add_command(label="📞 技术支持", command=lambda: messagebox.showinfo("技术支持", 
        #                         "24小时技术支持服务:\n\n📧 邮箱: support@jq-tech.com\n📱 热线: 400-xxx-xxxx\n💬 微信: JQ-Tech-Support\n⏰ 服务时间: 7×24小时\n\n🔧 远程协助服务可用"))
        # help_menu.add_separator()
        help_menu.add_command(label="ℹ️ 关于本系统", command=self.show_about_dialog)
    
  

    def show_detection_process_dialog(self):
        """显示检测流程对话框"""
        dialog = tk.Toplevel(self.root)
        dialog.title("检测流程说明")
        dialog.geometry("750x600")
        dialog.resizable(True, True)
        dialog.grab_set()
        
        # 居中显示
        dialog.transient(self.root)
        x = self.root.winfo_x() + (self.root.winfo_width() - 750) // 2
        y = self.root.winfo_y() + (self.root.winfo_height() - 600) // 2
        dialog.geometry(f"750x600+{x}+{y}")
        
        # 创建滚动文本框架
        main_frame = ttk.Frame(dialog, padding=20)
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # 标题
        title_label = ttk.Label(main_frame, text="[INFO] 智能肌少症检测系统 - 检测流程指南", 
                               font=("Arial", 14, "bold"))
        title_label.pack(pady=(0, 20))
        
        # 创建带滚动条的文本框
        text_frame = ttk.Frame(main_frame)
        text_frame.pack(fill=tk.BOTH, expand=True)
        
        text_widget = scrolledtext.ScrolledText(text_frame, wrap=tk.WORD, font=("Microsoft YaHei", 11))
        text_widget.pack(fill=tk.BOTH, expand=True)
        
        # 检测流程内容（之前的帮助内容）
        process_content = """
📋 标准化健康检测流程说明

本系统采用7步标准化检测流程，通过顺序检测降噪提升检测精准度，确保结果的准确性和可重复性。

🎯 检测目标
通过压力传感器阵列监测人体平衡能力、肌力表现和步态稳定性，综合评估肌少症风险。

⏱️ 检测流程（总时长约2-3分钟）

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

第一步：静坐检测（10秒）    🪑
──────────────────────────────────────────
• 请坐在检测区域，保持自然坐姿
• 双脚平放，身体放松  
• 系统将记录基础压力分布数据
• 用途：建立个人基准数据，排除外界干扰

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

第二步：起坐测试（5次重复）    🏃
──────────────────────────────────────────
• 从坐姿快速起立至完全站直
• 重复5次，动作要连贯有力
• 系统监测起立时的力量变化
• 用途：评估下肢肌力和协调性

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

第三步：静态站立（10秒）    🧍
──────────────────────────────────────────
• 双脚并拢，身体直立
• 目视前方，保持平衡
• 避免左右摇摆或前后晃动
• 用途：测试静态平衡能力

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

第四步：前后脚站立（10秒）    🦶
──────────────────────────────────────────
• 一脚在前，一脚在后，呈一条直线
• 保持身体平衡，不扶任何支撑物
• 可选择左脚或右脚在前
• 用途：测试动态平衡和本体感觉

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

第五步：双脚前后站立（10秒）    👣
──────────────────────────────────────────
• 双脚前后交替站立
• 每只脚轮流承重，类似走路预备姿势
• 保持上身稳定
• 用途：评估步态预备能力和平衡调节

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

第六步：握力检测    ✋
──────────────────────────────────────────
• 站在检测区域，使用握力计测量
• 双手各测量3次，取最高值
• 与压力传感器数据同步记录
• 用途：评估上肢肌力表现

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

第七步：4.5米步道折返    🚶
──────────────────────────────────────────
• 以正常速度行走4.5米
• 转身后返回起点
• 系统记录完整步态数据
• 用途：分析步态稳定性和行走能力

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

⚠️ 注意事项
• 检测过程中请穿着舒适、防滑的鞋子
• 如有身体不适或平衡困难，请立即停止检测
• 检测区域周围应有安全保护措施  
• 建议由专业人员陪同指导完成

📊 数据分析
系统将综合所有检测数据，通过AI算法分析：
• 静态平衡评分
• 动态平衡评分
• 肌力指数
• 步态稳定性指数
• 综合健康风险评估

🎯 检测意义
通过多维度数据融合，提供科学、客观的肌少症风险评估，为健康管理和康复训练提供数据支持。

💡 温馨提示
定期检测有助于及时发现健康问题，建议每月进行一次完整检测，跟踪健康状态变化。
        """
        
        text_widget.insert(tk.END, process_content.strip())
        text_widget.config(state=tk.DISABLED)
        
        # 关闭按钮
        btn_frame = ttk.Frame(main_frame)
        btn_frame.pack(pady=(15, 0))
        ttk.Button(btn_frame, text="关闭", command=dialog.destroy, width=15).pack()
    
    def show_help_dialog(self):
        """显示操作帮助对话框"""
        dialog = tk.Toplevel(self.root)
        dialog.title("操作帮助")
        dialog.geometry("700x650")
        dialog.resizable(True, True)
        dialog.grab_set()
        
        # 居中显示
        dialog.transient(self.root)
        x = self.root.winfo_x() + (self.root.winfo_width() - 700) // 2
        y = self.root.winfo_y() + (self.root.winfo_height() - 650) // 2
        dialog.geometry(f"700x650+{x}+{y}")
        
        # 创建滚动文本框架
        main_frame = ttk.Frame(dialog, padding=20)
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # 标题
        title_label = ttk.Label(main_frame, text="❓ 智能肌少症检测系统 - 操作帮助", 
                               font=("Arial", 14, "bold"))
        title_label.pack(pady=(0, 20))
        
        # 创建带滚动条的文本框
        text_frame = ttk.Frame(main_frame)
        text_frame.pack(fill=tk.BOTH, expand=True)
        
        text_widget = scrolledtext.ScrolledText(text_frame, wrap=tk.WORD, font=("Microsoft YaHei", 11))
        text_widget.pack(fill=tk.BOTH, expand=True)
        
        # 操作帮助内容
        help_content = """
系统操作指南

本指南将帮助您快速掌握智能肌少症检测系统的各项功能和操作方法。

快速开始

1. 首次使用系统
   • 启动程序后会自动弹出设备配置对话框
   • 选择您的检测设备类型（32x32, 32x64, 32x96）
   • 配置COM端口和设备参数
   • 点击"确认配置"完成初始化

2. 设备连接
   • 确保压力传感器设备已正确连接电脑
   • 检查USB或串口线连接状态
   • 系统会自动检测并连接配置的设备
   • 连接成功后状态栏显示"已连接"

主界面操作

 热力图显示区域
   • 实时显示压力传感器数据的热力图
   • 颜色越红表示压力越大，越蓝表示压力越小
   • 支持32x32, 32x64, 32x96多种阵列规格
   • 自动适配显示比例和颜色映射

实时统计面板
   • 最大值：当前帧的最大压力值
   • 最小值：当前帧的最小压力值  
   • 平均值：所有传感器点的平均压力
   • 标准差：压力分布的离散程度
   • 有效点：非零压力点的数量

数据日志区域
   • 实时显示接收到的数据帧信息
   • 包含时间戳、帧编号、统计数据
   • JQ变换标识（已应用或原始数据）
   • 支持日志清除和保存功能

控制面板功能

设备管理
   • 设备选择：从下拉菜单选择当前使用的设备
   • 设备配置：重新配置设备参数和端口设置
   • 自动连接：系统会自动连接选择的设备
   • 连接监控：自动检测连接状态并尝试重连

功能按钮
   • 保存快照：保存当前热力图为PNG图片文件
   • 保存日志：将当前日志内容保存为文本文件
   • 清除日志：清空日志显示区域

菜单栏功能



其他菜单
   • 操作帮助：查看本操作指南（当前页面）
   • 关于系统：查看系统版本和开发信息

设备配置详解

支持的设备类型
   • 32x32阵列：标准检测模式，适用于静态平衡测试
   • 32x64阵列：扩展检测模式，适用于动态平衡测试
   • 32x96阵列：步道模式，适用于步态分析和行走测试

端口配置
   • 自动检测：系统会扫描可用的COM端口
   • 手动选择：可以指定特定的COM端口
   • 波特率：默认1,000,000 bps（无需修改）
   • 连接测试：配置时会自动测试端口连通性

性能优化设置

运行模式
   • 标准模式：run_ui.py - 20 FPS，平衡性能与稳定性
   • 快速模式：run_ui_fast.py - 100 FPS，高刷新率显示
   • 极速模式：run_ui_ultra.py - 200 FPS，极致响应速度

数据处理
   • JQ变换：威海聚桥工业科技专用数据变换算法
   • 自动应用于32x32和32x96阵列数据
   • 提供数据镜像翻转和重排序功能
   • 优化数据显示效果和分析精度

故障排除

常见问题
   • 设备无法连接：检查USB线缆和端口选择
   • 数据接收异常：确认设备电源和波特率设置
   • 热力图不更新：检查设备连接状态和数据流
   • 程序运行缓慢：尝试使用标准模式或重启程序

解决方案
   • 重启设备：断开并重新连接检测设备
   • 重新配置：通过"设备配置"重新设置参数
   • 端口切换：尝试不同的COM端口
   • 程序重启：关闭并重新启动检测软件

📞 技术支持

如果遇到无法解决的问题，请联系：
• 威海聚桥工业科技有限公司
• 技术支持邮箱：support@jq-tech.com
• 客服电话：400-xxx-xxxx

💡 使用技巧

✨ 提高检测精度
   • 确保检测环境安静无干扰
   • 检测前校准设备基准数据
   • 选择合适的数组大小和模式
   • 定期清洁传感器表面

   数据分析
   • 观察热力图的颜色分布模式
   • 关注压力峰值的位置和变化
   • 结合统计数据进行综合判断
   • 保存关键时刻的快照用于对比

🎯 检测建议
   • 建议连续检测获得更准确结果
   • 注意观察被检测者的动作规范性
   • 记录检测过程中的特殊情况
   • 定期备份检测档案和数据
        """
        
        text_widget.insert(tk.END, help_content.strip())
        text_widget.config(state=tk.DISABLED)  # 设为只读
        
        # 关闭按钮
        btn_frame = ttk.Frame(main_frame)
        btn_frame.pack(pady=(15, 0))
        ttk.Button(btn_frame, text="关闭", command=dialog.destroy, width=15).pack()

    def show_about_dialog(self):
        """显示美观的关于对话框"""
        dialog = tk.Toplevel(self.root)
        dialog.title("关于 - 智能肌少症检测系统")
        dialog.geometry("720x650")  # 扩大尺寸以显示完整内容
        dialog.resizable(True, True)  # 允许调整大小
        dialog.grab_set()
        
        # 设置对话框图标和样式
        dialog.configure(bg='#f8f9fa')
        
        # 居中显示
        dialog.transient(self.root)
        x = self.root.winfo_x() + (self.root.winfo_width() - 720) // 2
        y = self.root.winfo_y() + (self.root.winfo_height() - 650) // 2
        dialog.geometry(f"720x650+{x}+{y}")
        
        # 创建滚动框架
        canvas = tk.Canvas(dialog, bg='#f8f9fa', highlightthickness=0)
        scrollbar = ttk.Scrollbar(dialog, orient="vertical", command=canvas.yview)
        scrollable_frame = ttk.Frame(canvas)
        
        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        
        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        
        # 主框架
        main_frame = ttk.Frame(scrollable_frame, padding=30)
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # 顶部装饰区域
        header_frame = tk.Frame(main_frame, bg='#2c3e50', height=120)
        header_frame.pack(fill=tk.X, pady=(0, 25))
        header_frame.pack_propagate(False)
        
        # 应用图标和标题 (在深色背景上)
        title_label = tk.Label(header_frame, text="🔬 智能肌少症检测系统", 
                               font=("Microsoft YaHei UI", 20, "bold"),
                               bg='#2c3e50', fg='#ffffff')
        title_label.pack(pady=(15, 5))
        
        subtitle_label = tk.Label(header_frame, text="Intelligent Sarcopenia Detection System", 
                                  font=("Arial", 12, "italic"),
                                  bg='#2c3e50', fg='#bdc3c7')
        subtitle_label.pack(pady=(0, 5))
        
        version_label = tk.Label(header_frame, text="压力传感器数据可视化界面 v1.2", 
                                font=("Microsoft YaHei UI", 10),
                                bg='#2c3e50', fg='#ecf0f1')
        version_label.pack(pady=(0, 15))
        
        # 系统信息卡片
        info_card = tk.Frame(main_frame, bg='#ffffff', relief='solid', bd=1)
        info_card.pack(fill=tk.X, pady=(0, 20))
        
        info_title = tk.Label(info_card, text="[INFO] 系统信息", 
                             font=("Microsoft YaHei UI", 14, "bold"),
                             bg='#ffffff', fg='#2c3e50')
        info_title.pack(anchor="w", padx=20, pady=(15, 10))
        
        # 创建信息网格
        info_grid_frame = tk.Frame(info_card, bg='#ffffff')
        info_grid_frame.pack(fill=tk.X, padx=20, pady=(0, 15))
        
        info_items = [
            ("🏷️ 软件版本:", "v1.2.0 模块化专业版", "#27ae60"),
            ("📐 支持阵列:", "32×32, 32×64, 32×96 多规格", "#9b59b6"),
            ("📅 开发时间:", "2024年 (持续更新中)", "#34495e"),
            ("💻 运行环境:", "Windows 10/11, Python 3.7+", "#16a085"),
            ("🌐 通信协议:", "串口 1000000 bps 高速传输", "#e74c3c"),
        ]
        
        for i, (label, value, color) in enumerate(info_items):
            row = i // 2
            col = (i % 2) * 3
            
            label_widget = tk.Label(info_grid_frame, text=label, 
                                   font=("Microsoft YaHei UI", 10, "bold"),
                                   bg='#ffffff', fg='#2c3e50')
            label_widget.grid(row=row, column=col, sticky="e", padx=(0, 8), pady=6)
            
            value_widget = tk.Label(info_grid_frame, text=value, 
                                   font=("Microsoft YaHei UI", 10),
                                   bg='#ffffff', fg=color)
            value_widget.grid(row=row, column=col+1, sticky="w", padx=(0, 30), pady=6)
        
        # 核心功能卡片
        features_card = tk.Frame(main_frame, bg='#ffffff', relief='solid', bd=1)
        features_card.pack(fill=tk.X, pady=(0, 20))
        
        features_title = tk.Label(features_card, text="⚡ 核心功能特性", 
                                 font=("Microsoft YaHei UI", 14, "bold"),
                                 bg='#ffffff', fg='#2c3e50')
        features_title.pack(anchor="w", padx=20, pady=(15, 10))
        
        features_frame = tk.Frame(features_card, bg='#ffffff')
        features_frame.pack(fill=tk.X, padx=20, pady=(0, 15))
        
        features_list = [
            "实时压力数据可视化热力图显示",
            "多设备智能配置和无缝切换管理系统",
            "标准化健康检测流程指导和档案管理",
            "智能端口检测和自动连接重连机制",
        ]
        
        for i, feature in enumerate(features_list):
            feature_label = tk.Label(features_frame, text=feature, 
                                    font=("Microsoft YaHei UI", 10),
                                    bg='#ffffff', fg='#2c3e50',
                                    justify=tk.LEFT, anchor="w")
            feature_label.pack(anchor="w", pady=3, padx=10)
        
        # 技术规格卡片
        specs_card = tk.Frame(main_frame, bg='#ffffff', relief='solid', bd=1)
        specs_card.pack(fill=tk.X, pady=(0, 20))
        
        specs_title = tk.Label(specs_card, text="⚙️ 技术规格", 
                              font=("Microsoft YaHei UI", 14, "bold"),
                              bg='#ffffff', fg='#2c3e50')
        specs_title.pack(anchor="w", padx=20, pady=(15, 10))
        
        specs_text = """
通信参数: 串口通信，波特率1,000,000 bps，帧头AA 55 03 99
阵列规格: 支持32×32(1024点)、32×64(2048点)、32×96(3072点)
数据精度: 8位无符号整数 (0-255)，压力范围0-60mmHg
刷新性能: 标准20FPS/快速100FPS/极速200FPS三种模式
系统要求: Windows 10/11，Python 3.7+，4GB内存，USB端口
数据处理: JQ变换算法，NumPy向量化计算，多线程架构
        """
        
        specs_label = tk.Label(specs_card, text=specs_text.strip(), 
                              font=("Consolas", 9),
                              bg='#ffffff', fg='#34495e',
                              justify=tk.LEFT, anchor="w")
        specs_label.pack(anchor="w", padx=20, pady=(0, 15))
        
        # 联系方式卡片
        # contact_card = tk.Frame(main_frame, bg='#2c3e50')
        # contact_card.pack(fill=tk.X, pady=(0, 20))
        
        # contact_title = tk.Label(contact_card, text="📞 联系方式与技术支持", 
        #                         font=("Microsoft YaHei UI", 14, "bold"),
        #                         bg='#2c3e50', fg='#ffffff')
        # contact_title.pack(anchor="w", padx=20, pady=(15, 10))
        
        # contact_info = [
        #     "🏢 威海聚桥工业科技有限公司",
        #     "🌐 官方网站: www.jq-tech.com",
        #     "📧 技术支持: support@jq-tech.com", 
        #     "📱 客服热线: 400-xxx-xxxx (工作日 9:00-18:00)",
        #     "📍 公司地址: 山东省威海市环翠区工业园区",
        #     "💬 微信客服: JQ-Tech-Support",
        # ]
        
        # for info in contact_info:
        #     info_label = tk.Label(contact_card, text=info, 
        #                          font=("Microsoft YaHei UI", 10),
        #                          bg='#2c3e50', fg='#ecf0f1')
        #     info_label.pack(anchor="w", padx=20, pady=2)
        
        # contact_bottom = tk.Label(contact_card, text="🤝 感谢您使用智能肌少症检测系统！", 
        #                          font=("Microsoft YaHei UI", 11, "bold"),
        #                          bg='#2c3e50', fg='#f1c40f')
        # contact_bottom.pack(anchor="center", pady=(10, 15))
        
        # 按钮区域
        # btn_frame = tk.Frame(main_frame, bg='#f8f9fa')
        # btn_frame.pack(pady=(0, 0))
        

        
        info_btn = tk.Button(main_frame, text="https://www.jq-tech.com", 
                            command=self.open_website,
                            font=("Microsoft YaHei UI", 11),
                            bg='#27ae60', fg='white',
                            # activebackground='#229954',
                            # activeforeground='white',
                            relief='flat', bd=0,
                            # padx=20, pady=8,
                            cursor='hand2')
        info_btn.pack(anchor="center", pady=10)
        
        # 打包滚动区域
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        
        # 绑定鼠标滚轮事件（安全版本）
        def _on_mousewheel(event):
            try:
                if canvas.winfo_exists():
                    canvas.yview_scroll(int(-1*(event.delta/120)), "units")
            except tk.TclError:
                # 忽略widget已销毁的错误
                pass
        canvas.bind_all("<MouseWheel>", _on_mousewheel)
        
    def setup_ui(self):
        """设置用户界面"""
        # 创建菜单栏
        self.create_menubar()
        
        # 配置ttk样式为医院风格
        style = ttk.Style()
        style.theme_use('clam')  # 使用清洁的clam主题
        
        # 自定义医院风格样式
        style.configure('Hospital.TLabelframe', 
                       background='#ffffff',
                       foreground='#2c3e50',
                       borderwidth=1,
                       relief='solid')
        style.configure('Hospital.TLabelframe.Label', 
                       background='#ffffff',
                       foreground='#1976d2',
                       font=('Microsoft YaHei UI', 11, 'bold'))
        style.configure('Hospital.TFrame', background='#ffffff')
        style.configure('Hospital.TLabel', 
                       background='#ffffff',
                       foreground='#37474f',
                       font=('Microsoft YaHei UI', 10))
        style.configure('Hospital.TButton',
                       background='#f8f9fa',
                       foreground='#2c3e50',
                       borderwidth=1,
                       focuscolor='none',
                       font=('Microsoft YaHei UI', 9))
        style.map('Hospital.TButton',
                 background=[('active', '#e3f2fd'),
                           ('pressed', '#bbdefb')])
        
        # 成功按钮样式（绿色主题）
        style.configure('Success.TButton',
                       background='#28a745',
                       foreground='white',
                       borderwidth=2,
                       focuscolor='none',
                       font=('Microsoft YaHei UI', 10, 'bold'))
        style.map('Success.TButton',
                 background=[('active', '#218838'),
                           ('pressed', '#1e7e34')])
        
        # 主框架 - 医院白色
        main_frame = ttk.Frame(self.root, style='Hospital.TFrame')
        main_frame.pack(fill=tk.BOTH, expand=True, padx=15, pady=15)
        
        # 顶部控制面板 - 医院风格
        control_frame = ttk.LabelFrame(main_frame, text="🎛️ 控制面板", 
                                     padding=15, style='Hospital.TLabelframe')
        control_frame.pack(fill=tk.X, pady=(0, 15))
        
        # 第一行：设备和连接控制
        # 设备选择
        ttk.Label(control_frame, text="设备:", style='Hospital.TLabel').grid(row=0, column=0, padx=(0, 8))
        self.device_var = tk.StringVar()
        self.device_combo = ttk.Combobox(control_frame, textvariable=self.device_var, 
                                       width=15, state="readonly",
                                       font=('Microsoft YaHei UI', 10))
        self.device_combo.grid(row=0, column=1, padx=(0, 15))
        self.device_combo.bind('<<ComboboxSelected>>', self.on_device_changed)
        
        # 设备配置按钮
        ttk.Button(control_frame, text="⚙️ 设备配置", 
                  command=self.show_device_config, 
                  style='Hospital.TButton').grid(row=0, column=2, padx=(0, 25))
        
        # 创建一个Frame用于右对齐患者信息
        right_frame = ttk.Frame(control_frame)
        right_frame.grid(row=0, column=10, sticky='e', padx=(0, 10))
        control_frame.columnconfigure(10, weight=1)  # 让这一列占据剩余空间
        
        # 状态标签 - 医院配色
        self.status_label = tk.Label(right_frame, text="⚙️ 未选择患者", 
                                   foreground="#ff6b35", bg='#ffffff',
                                   font=('Microsoft YaHei UI', 10, 'bold'))
        self.status_label.pack(side='right')
        
        # 端口信息显示
        self.port_info_label = tk.Label(control_frame, text="端口: 未知",
                                      bg='#ffffff', fg='#6c757d',
                                      font=('Microsoft YaHei UI', 9))
        self.port_info_label.grid(row=0, column=4, padx=(0, 15))
        
        # 快速检测按钮 - 在第一行右边
        self.start_detection_btn = ttk.Button(control_frame, text="🚀 快速检测", 
                                            command=self.start_detection_process,
                                            style='Success.TButton')
        self.start_detection_btn.grid(row=0, column=5, padx=(0, 15), sticky='e')
        
        # 生成报告按钮 - 在快速检测按钮旁边
        self.generate_report_btn = ttk.Button(control_frame, text="📊 生成报告", 
                                            command=self.generate_report_for_patient,
                                            style='Hospital.TButton')
        self.generate_report_btn.grid(row=0, column=6, padx=(0, 0), sticky='e')
        
        
        
        
        # 中间内容区域 - 医院白色背景
        content_frame = ttk.Frame(main_frame, style='Hospital.TFrame')
        content_frame.pack(fill=tk.BOTH, expand=True)
        
        # 左侧：热力图显示 - 医院风格边框
        self.plot_frame = ttk.LabelFrame(content_frame, 
                                       text="压力传感器热力图", 
                                       padding=15, style='Hospital.TLabelframe')
        self.plot_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 15))
        
        # 右侧：数据日志和统计 - 医院白色
        right_frame = ttk.Frame(content_frame, style='Hospital.TFrame')
        right_frame.pack(side=tk.RIGHT, fill=tk.BOTH, padx=(0, 0))
        right_frame.config(width=450)
        
        # 统计信息面板 - 医院风格
        stats_frame = ttk.LabelFrame(right_frame, text="实时统计", 
                                   padding=15, style='Hospital.TLabelframe')
        stats_frame.pack(fill=tk.X, pady=(0, 15))
        
        self.stats_labels = {}
        stats_items = [("最大值:", "max_value"),  ("平均值:", "mean_value"), 
                       ("标准差:", "std_value"), ("有效点:", "nonzero_count")]
        
        for i, (text, key) in enumerate(stats_items):
            row = i // 2
            col = (i % 2) * 2
            # 标签使用医院风格
            label_text = tk.Label(stats_frame, text=text, 
                                bg='#ffffff', fg='#495057',
                                font=('Microsoft YaHei UI', 10))
            label_text.grid(row=row, column=col, sticky="e", padx=(0, 8))
            
            # 数值使用突出颜色
            label = tk.Label(stats_frame, text="0", 
                           font=("Consolas", 11, "bold"),
                           bg='#ffffff', fg='#1976d2')
            label.grid(row=row, column=col+1, sticky="w", padx=(0, 25))
            self.stats_labels[key] = label
        
        # 日志区域 - 使用grid布局确保均匀分配
        log_container = ttk.Frame(right_frame)
        log_container.pack(fill=tk.BOTH, expand=True)
        
        # 配置grid权重
        log_container.grid_rowconfigure(0, weight=1)
        log_container.grid_rowconfigure(1, weight=1)
        log_container.grid_columnconfigure(0, weight=1)
        
        # AI分析日志 - 上半部分
        ai_log_frame = ttk.LabelFrame(log_container, text="Sarcneuro Edge AI 日志", 
                                    padding=(10, 5, 10, 5), style='Hospital.TLabelframe')
        ai_log_frame.grid(row=0, column=0, sticky="nsew", pady=(0, 0), padx=0)
        
        # AI日志控制按钮 - 保持结构一致
        ai_btn_frame = ttk.Frame(ai_log_frame, style='Hospital.TFrame')
        ai_btn_frame.pack(fill=tk.X, pady=(0, 5))
        
        # 占位标签，保持视觉平衡
        ttk.Label(ai_btn_frame, text="AI分析状态", 
                 style='Hospital.TLabel').pack(side=tk.LEFT)
        
        self.ai_log_text = scrolledtext.ScrolledText(ai_log_frame, width=55, 
                                                   font=("Consolas", 9),
                                                   bg='#f8f9ff',  # 淡蓝色背景
                                                   fg='#2c3e50',
                                                   selectbackground='#e3f2fd',
                                                   selectforeground='#1976d2',
                                                   insertbackground='#1976d2',
                                                   borderwidth=1,
                                                   relief='solid')
        self.ai_log_text.pack(fill=tk.BOTH, expand=True)
        
        # 硬件设备日志 - 下半部分，带按钮
        hw_log_frame = ttk.LabelFrame(log_container, text="设备日志", 
                                    padding=(10, 5, 10, 5), style='Hospital.TLabelframe')
        hw_log_frame.grid(row=1, column=0, sticky="nsew", pady=(0, 0), padx=0)
        
        # 日志控制按钮 - 放在日志框标题旁边
        log_btn_frame = ttk.Frame(hw_log_frame, style='Hospital.TFrame')
        log_btn_frame.pack(fill=tk.X, pady=(0, 5))
        
        ttk.Button(log_btn_frame, text="💾 保存日志", 
                  command=self.save_log,
                  style='Hospital.TButton').pack(side=tk.LEFT, padx=(0, 10))
        ttk.Button(log_btn_frame, text="🗑️ 清除日志", 
                  command=self.clear_log,
                  style='Hospital.TButton').pack(side=tk.LEFT)
        
        self.log_text = scrolledtext.ScrolledText(hw_log_frame, width=55, 
                                                font=("Consolas", 9),
                                                bg='#ffffff',
                                                fg='#495057',
                                                selectbackground='#e8f5e8',
                                                selectforeground='#2e7d32',
                                                insertbackground='#2e7d32',
                                                borderwidth=1,
                                                relief='solid')
        self.log_text.pack(fill=tk.BOTH, expand=True)
        
        # 底部状态栏 - 医院风格
        status_frame = ttk.Frame(main_frame, style='Hospital.TFrame')
        status_frame.pack(fill=tk.X, pady=(15, 0))
        
        # 创建状态栏背景
        status_bg = tk.Frame(status_frame, bg='#ffffff', height=35, relief='flat', bd=0)
        status_bg.pack(fill=tk.X)
        
        self.frame_count_label = tk.Label(status_bg, text="📦 接收帧数: 0",
                                        bg='#ffffff', fg='#495057',
                                        font=('Microsoft YaHei UI', 9))
        self.frame_count_label.pack(side=tk.LEFT, padx=(15, 0), pady=8)
        
        self.data_rate_label = tk.Label(status_bg, text="📈 数据速率: 0 帧/秒",
                                      bg='#ffffff', fg='#495057',
                                      font=('Microsoft YaHei UI', 9))
        self.data_rate_label.pack(side=tk.RIGHT, padx=(0, 15), pady=8)
        
        # 启动状态指示器
        self.status_bar = tk.Label(status_bg, text="🔄 正在启动系统...",
                                 bg='#ffffff', fg='#007bff',
                                 font=('Microsoft YaHei UI', 9, 'bold'))
        self.status_bar.pack(side=tk.LEFT, padx=(30, 0), pady=8)
    
    def setup_visualizer(self):
        """设置可视化模块"""
        array_info = self.data_processor.get_array_info()
        self.visualizer = HeatmapVisualizer(
            self.plot_frame, 
            array_rows=array_info['rows'], 
            array_cols=array_info['cols']
        )
        
    def auto_config_array_size(self, array_size_str):
        """自动配置数组大小"""
        try:
            if array_size_str == "32x32":
                rows, cols = 32, 32
            elif array_size_str == "32x64":
                rows, cols = 32, 64
            elif array_size_str == "32x96":
                rows, cols = 32, 96
            else:
                self.log_message(f"[ERROR] 不支持的阵列大小: {array_size_str}")
                return
            
            # 更新数据处理器
            self.data_processor.set_array_size(rows, cols)
            
            # 更新可视化器
            if self.visualizer:
                self.visualizer.set_array_size(rows, cols)
            
            # 更新标题
            self.plot_frame.config(text=f"压力传感器热力图 ({rows}x{cols})")
            
            self.log_message(f"[OK] 已自动配置阵列大小: {rows}x{cols}")
            
        except Exception as e:
            self.log_message(f"[ERROR] 自动配置阵列大小失败: {e}")
            
    def save_snapshot(self):
        """保存热力图快照"""
        try:
            from datetime import datetime
            import os
            
            # 直接保存到当前目录，不弹窗选择
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            device_info = self.device_manager.get_current_device_info()
            device_name = device_info.get('name', 'Unknown') if device_info else 'Unknown'
            
            filename = f"压力传感器_{device_name}_{timestamp}.png"
            
            if self.visualizer.save_snapshot(filename):
                self.log_message(f"📸 快照已保存: {filename}")
            else:
                self.log_message("[ERROR] 保存快照失败")
        except Exception as e:
            self.log_message(f"[ERROR] 保存快照出错: {e}")
    
            
    def save_log(self):
        """保存日志"""
        try:
            from datetime import datetime
            
            # 直接保存到当前目录，不弹窗选择
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            device_info = self.device_manager.get_current_device_info()
            device_name = device_info.get('name', 'Unknown') if device_info else 'Unknown'
            
            filename = f"压力传感器日志_{device_name}_{timestamp}.txt"
            
            with open(filename, 'w', encoding='utf-8') as f:
                f.write(self.log_text.get("1.0", tk.END))
            self.log_message(f"[OK] 日志已保存: {filename}")
        except Exception as e:
            self.log_message(f"[ERROR] 保存日志失败: {e}")
            
            
    def stop_connection(self):
        """停止连接"""
        try:
            self.is_running = False
            
            # 断开串口接口连接
            if self.serial_interface:
                try:
                    self.serial_interface.disconnect()
                except Exception as e:
                    pass
            
            # 断开当前设备连接
            if self.device_configured:
                self.device_manager.disconnect_current_device()
            
            # 更新UI状态
            self.status_label.config(text="⚫ 未连接", foreground="red")
            self.log_message("[INFO] 连接已断开")
            
            # 重新启用设备选择
            if self.device_configured:
                self.device_combo.config(state="readonly")
            
        except Exception as e:
            self.log_message(f"[ERROR] 断开连接时出错: {e}")
        
    def start_update_loop(self):
        """启动数据更新循环"""
        self.update_data()
        
    def update_data(self):
        """数据更新循环 - 从串口接口获取数据并处理"""
        try:
            if self.is_running and self.serial_interface.is_connected():
                # 使用批量获取，减少函数调用开销
                frame_data_list = self.serial_interface.get_multiple_data(max_count=10)
                
                if frame_data_list:
                    # 更新数据接收时间
                    self.last_data_time = time.time()
                    self.device_lost_warned = False  # 重置警告状态
                    
                    # 先检查设备信息并设置正确的数组大小
                    device_info = self.device_manager.get_current_device_info()
                    if device_info and device_info.get('com_ports', 1) > 1:
                        # 多端口设备，先设置正确的数组大小
                        com_ports = device_info.get('com_ports', 1)
                        if com_ports == 2:
                            self.data_processor.set_array_size(32, 64)  # 32x64: 左右拼接两个32x32
                        elif com_ports == 3:
                            self.data_processor.set_array_size(32, 96)  # 32x96: 左右拼接三个32x32
                    
                    # 只处理最新的帧，丢弃过旧的数据以减少延迟
                    frame_data = frame_data_list[-1]  # 取最新帧
                    
                    # 调试：检查多端口设备的数据
                    if device_info and device_info.get('com_ports', 1) > 1:
                        com_ports = device_info.get('com_ports', 1)
                        expected_length = com_ports * 1024
                        actual_length = len(frame_data.get('data', b''))
                            
                    
                    # 正确的JQ转换逻辑：
                    # 单端口设备：这里需要JQ转换（原始数据→JQ转换→热力图）
                    # 多端口设备：这里不需要JQ转换（已在合并时对每个端口进行了JQ转换）
                    if device_info:
                        com_ports = device_info.get('com_ports', 1)
                        if com_ports == 1:
                            enable_jq = True
                            jq_reason = "单端口设备需要JQ转换"
                        else:
                            enable_jq = False
                            jq_reason = f"多端口设备({com_ports}端口)已在合并时JQ转换"
                    else:
                        enable_jq = True
                        jq_reason = "默认启用JQ转换"
                    
                    processed_data = self.data_processor.process_frame_data(frame_data, enable_jq)
                    
                    
                    if 'error' not in processed_data:
                        # 更新可视化显示
                        matrix_2d = processed_data['matrix_2d']
                        statistics = processed_data['statistics']
                        
                        self.visualizer.update_data(matrix_2d, statistics)
                        
                        # 更新统计显示和日志
                        self.update_statistics_display(statistics)
                        self.log_processed_data(processed_data)
                        
                        # 通知检测向导有新数据（如果向导正在运行且在记录数据）
                        has_wizard = hasattr(self, '_active_detection_wizard') and self._active_detection_wizard
                        is_recording = has_wizard and getattr(self._active_detection_wizard, '_recording_data', False)
                        
                        # 每隔一段时间打印一次调试信息（避免日志过多）
                        if not hasattr(self, '_debug_counter'):
                            self._debug_counter = 0
                        self._debug_counter += 1
                        
                        
                        if has_wizard:
                            if is_recording:
                                try:
                                    self._active_detection_wizard.write_csv_data_row(processed_data)
                                except Exception as e:
                                    import traceback
                                    traceback.print_exc()
                        
                        # 显示丢弃的帧数（如果有）
                        dropped_frames = len(frame_data_list) - 1
                        if dropped_frames > 0:
                            self.log_message(f"⚡ Dropped {dropped_frames} old frames for real-time display")
                    else:
                        # 详细的错误调试信息
                        error_msg = processed_data['error']
                        frame_info = processed_data.get('original_frame', {})
                        data_length = len(frame_info.get('data', b'')) if 'data' in frame_info else 0
                        data_type = type(frame_info.get('data', None)).__name__
                        
                        self.log_message(f"[ERROR] Data processing error: {error_msg}")
                        self.log_message(f"[DEBUG] Frame info - length: {data_length}, type: {data_type}")
                        
                        # 如果是字符串错误，显示前50个字符的十六进制
                        if 'data' in frame_info:
                            data_sample = frame_info['data']
                            if isinstance(data_sample, bytes):
                                hex_sample = data_sample[:20].hex()
                                self.log_message(f"[DEBUG] Data sample (hex): {hex_sample}")
                            elif isinstance(data_sample, str):
                                self.log_message(f"[DEBUG] String data detected: {repr(data_sample[:50])}")
                            else:
                                self.log_message(f"[DEBUG] Data type: {type(data_sample)}")
                        
                        # 获取当前设备信息
                        if device_info:
                            self.log_message(f"[DEBUG] Device info - ports: {device_info.get('com_ports', 1)}, "
                                           f"array_size: {device_info.get('array_size', 'unknown')}")
                        
                        # 获取数据处理器状态
                        self.log_message(f"[DEBUG] Processor - array: {self.data_processor.array_rows}x{self.data_processor.array_cols}")
                
                # 计算数据速率
                self.calculate_data_rate()
                
        except Exception as e:
            self.log_message(f"[ERROR] 更新数据时出错: {e}")
        
        # 继续更新循环 (5ms = 200 FPS，极致响应速度)
        self.root.after(5, self.update_data)
    
    def update_statistics_display(self, statistics):
        """更新统计信息显示"""
        try:
            for key, label in self.stats_labels.items():
                if key in statistics:
                    value = statistics[key]
                    if isinstance(value, float):
                        label.config(text=f"{value:.1f}")
                    else:
                        label.config(text=str(value))
        except Exception as e:
            self.log_message(f"[ERROR] 更新统计显示出错: {e}")
            
    def log_processed_data(self, processed_data):
        """记录处理后的数据日志"""
        try:
            frame_info = processed_data['original_frame']
            stats = processed_data['statistics']
            
            timestamp = frame_info['timestamp']
            frame_num = frame_info['frame_number']
            array_size = processed_data['array_size']
            jq_applied = processed_data['jq_transform_applied']
            
            jq_indicator = "✨" if jq_applied else "[DATA]"
            
            log_msg = (f"[{timestamp}] 帧#{frame_num:04d} {jq_indicator} ({array_size}) "
                      f"最大:{stats['max_value']:3d} 最小:{stats['min_value']:3d} "
                      f"平均:{stats['mean_value']:6.1f}")
            
            self.log_message(log_msg)
            
        except Exception as e:
            self.log_message(f"[ERROR] 记录日志出错: {e}")
            
    def calculate_data_rate(self):
        """计算数据速率"""
        try:
            current_time = time.time()
            current_frame_count = self.serial_interface.get_frame_count()
            
            if current_time - self.last_time >= 0.5:  # 更频繁的速率更新
                frame_diff = current_frame_count - self.last_frame_count
                time_diff = current_time - self.last_time
                self.data_rate = int(frame_diff / time_diff) if time_diff > 0 else 0
                self.last_frame_count = current_frame_count
                self.last_time = current_time
                
                # 更新状态栏
                self.frame_count_label.config(text=f"📦 接收帧数: {current_frame_count}")
                self.data_rate_label.config(text=f"📈 数据速率: {self.data_rate} 帧/秒")
        except:
            pass
                

            
    def log_message(self, message):
        """添加硬件设备日志消息"""
        def add_log():
            timestamp = datetime.now().strftime("%H:%M:%S")
            log_entry = f"[{timestamp}] {message}"
            self.log_text.insert(tk.END, log_entry + "\n")
            self.log_text.see(tk.END)
            
            # 限制日志行数
            lines = self.log_text.get("1.0", tk.END).count('\n')
            if lines > 1000:
                self.log_text.delete("1.0", "100.0")
                
        # 在主线程中执行UI更新
        self.root.after(0, add_log)
    
    def log_ai_message(self, message):
        """添加AI分析日志消息"""
        def add_ai_log():
            timestamp = datetime.now().strftime("%H:%M:%S")
            log_entry = f"[{timestamp}] {message}"
            
            if hasattr(self, 'ai_log_text'):
                self.ai_log_text.insert(tk.END, log_entry + "\n")
                self.ai_log_text.see(tk.END)
                
                # 限制日志行数
                lines = self.ai_log_text.get("1.0", tk.END).count('\n')
                if lines > 500:
                    self.ai_log_text.delete("1.0", "50.0")
            else:
                # 如果AI日志不存在，fallback到普通日志
                self.log_message(f"[AI] {message}")
                
        # 在主线程中执行UI更新
        self.root.after(0, add_ai_log)
        
    def clear_log(self):
        """清除日志"""
        self.log_text.delete("1.0", tk.END)
        self.log_message("📝 日志已清除")
        
    def integrate_sarcneuro_analysis(self):
        """集成肌少症分析功能"""
        try:
            from integration_ui import integrate_sarcneuro_analysis
            # 传递正确的参数类型
            integrate_sarcneuro_analysis(self)
            print("[OK] 肌少症分析功能集成成功")
        except Exception as e:
            print(f"[WARN] 肌少症分析功能集成失败: {e}")
            # 不影响主程序运行，继续使用原有功能
            self.sarcneuro_panel = None
    
    def _delayed_start_sarcneuro_service(self):
        """延迟启动SarcNeuro Edge服务"""
        try:
            self.init_sarcneuro_service()
            self.log_message("🚀 SarcNeuro Edge服务已在后台启动")
        except Exception as e:
            self.log_message(f"⚠️ SarcNeuro Edge服务启动失败: {e}")
    
    def _cleanup_expired_sessions(self):
        """清理过期的会话数据"""
        try:
            # 获取今天的日期
            today = datetime.now().strftime('%Y-%m-%d')
            
            # 由于没有get_all_test_sessions方法，我们需要通过其他方式清理
            # 这里可以通过SQL直接清理，或者后续完善数据库接口
            # 暂时跳过此功能，避免影响系统启动
            print(f"[INFO] 过期会话清理功能暂时跳过")
                
        except Exception as e:
            print(f"[ERROR] 清理过期会话失败: {e}")
    
    # ============= SarcNeuro Edge AI 分析功能 =============
    
    def init_sarcneuro_service(self):
        """初始化 SarcNeuro Edge 服务"""
        if not SARCNEURO_AVAILABLE:
            return
            
        try:
            # 使用标准服务管理器
            self.sarcneuro_service = SarcNeuroEdgeService(port=8000)
            self.data_converter = SarcopeniaDataConverter()
            print("[OK] SarcNeuro Edge 服务初始化完成")
        except Exception as e:
            print(f"[WARN] SarcNeuro Edge 服务初始化失败: {e}")
            self.sarcneuro_service = None
            self.data_converter = None
    
    def show_patient_info_dialog(self, csv_file_path):
        """显示患者信息收集对话框 - 医院风格"""
        import os
        import re
        
        dialog = tk.Toplevel(self.root)
        dialog.title("AI肌少症分析 - 患者信息录入")
        dialog.geometry("500x650")
        dialog.resizable(False, False)
        dialog.grab_set()
        dialog.transient(self.root)
        
        # 设置窗口图标（与主程序保持一致）
        try:
            dialog.iconbitmap("icon.ico")
        except:
            pass
        
        # 设置医院风格背景色
        dialog.config(bg='#f8f9fa')
        
        # 居中显示
        dialog.geometry("+%d+%d" % (
            self.root.winfo_rootx() + 50, 
            self.root.winfo_rooty() + 50
        ))
        
        result = {}
        
        # 从文件名尝试解析基本信息
        filename = os.path.basename(csv_file_path)
        filename_without_ext = os.path.splitext(filename)[0]
        
        default_name = ""
        default_age = ""
        default_activity = ""
        
        try:
            # 解析文件名格式: 姓名-活动描述-年龄岁.csv
            pattern = r'^(.+?)-(.+?)-(\d+)岁?$'
            match = re.match(pattern, filename_without_ext)
            if match:
                default_name = match.group(1).strip()
                default_activity = match.group(2).strip()
                default_age = str(match.group(3))
        except:
            pass
        
        # 主框架 - 医院风格
        main_frame = tk.Frame(dialog, bg='#ffffff', relief='raised', bd=1, padx=20, pady=15)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # 标题 - 医疗专业风格
        title_label = tk.Label(main_frame, 
                              text="[AI] 智能肌少症风险分析", 
                              font=("Microsoft YaHei", 16, "bold"),
                              bg='#ffffff', fg='#1a472a')
        title_label.pack(pady=(0, 5))
        
        subtitle_label = tk.Label(main_frame, 
                                 text="请完整填写患者信息以确保分析准确性", 
                                 font=("Microsoft YaHei", 10),
                                 bg='#ffffff', fg='#666666')
        subtitle_label.pack(pady=(0, 15))
        
        # 文件信息区域
        file_frame = tk.LabelFrame(main_frame, text=" 数据文件信息 ", 
                                  font=("Microsoft YaHei", 10, "bold"),
                                  bg='#ffffff', fg='#2c5282',
                                  relief='groove', bd=2, padx=15, pady=10)
        file_frame.pack(fill=tk.X, pady=(0, 10))
        
        file_label = tk.Label(file_frame, text=f"CSV文件: {filename}", 
                             font=("Consolas", 9), bg='#ffffff', fg='#4a5568')
        file_label.pack(anchor=tk.W)
        
        # 患者基本信息区域
        info_frame = tk.LabelFrame(main_frame, text=" 患者基本信息 (*必填) ", 
                                  font=("Microsoft YaHei", 10, "bold"),
                                  bg='#ffffff', fg='#2c5282',
                                  relief='groove', bd=2, padx=15, pady=15)
        info_frame.pack(fill=tk.X, pady=(0, 10))
        
        # 网格配置
        info_frame.grid_columnconfigure(1, weight=1)
        
        # 姓名
        tk.Label(info_frame, text="患者姓名 *:", font=("Microsoft YaHei", 10, "bold"),
                bg='#ffffff', fg='#2d3748', width=12, anchor='e').grid(row=0, column=0, sticky="e", padx=(0, 15), pady=8)
        name_var = tk.StringVar(value=default_name)
        name_entry = tk.Entry(info_frame, textvariable=name_var, font=("Microsoft YaHei", 10),
                             width=20, relief='solid', bd=1)
        name_entry.grid(row=0, column=1, sticky="w", pady=8)
        
        # 年龄
        tk.Label(info_frame, text="年龄 *:", font=("Microsoft YaHei", 10, "bold"),
                bg='#ffffff', fg='#2d3748', width=12, anchor='e').grid(row=1, column=0, sticky="e", padx=(0, 15), pady=8)
        age_var = tk.StringVar(value=default_age)
        age_frame = tk.Frame(info_frame, bg='#ffffff')
        age_frame.grid(row=1, column=1, sticky="w", pady=8)
        age_entry = tk.Entry(age_frame, textvariable=age_var, font=("Microsoft YaHei", 10),
                            width=10, relief='solid', bd=1)
        age_entry.pack(side=tk.LEFT)
        tk.Label(age_frame, text="岁", font=("Microsoft YaHei", 10),
                bg='#ffffff', fg='#666666').pack(side=tk.LEFT, padx=(5, 0))
        
        # 性别
        tk.Label(info_frame, text="性别 *:", font=("Microsoft YaHei", 10, "bold"),
                bg='#ffffff', fg='#2d3748', width=12, anchor='e').grid(row=2, column=0, sticky="e", padx=(0, 15), pady=8)
        gender_var = tk.StringVar(value="MALE")
        gender_frame = tk.Frame(info_frame, bg='#ffffff')
        gender_frame.grid(row=2, column=1, sticky="w", pady=8)
        tk.Radiobutton(gender_frame, text="男", variable=gender_var, value="MALE",
                      font=("Microsoft YaHei", 10), bg='#ffffff', fg='#2d3748',
                      selectcolor='#e6fffa', activebackground='#ffffff').pack(side=tk.LEFT)
        tk.Radiobutton(gender_frame, text="女", variable=gender_var, value="FEMALE",
                      font=("Microsoft YaHei", 10), bg='#ffffff', fg='#2d3748',
                      selectcolor='#e6fffa', activebackground='#ffffff').pack(side=tk.LEFT, padx=(20, 0))
        
        # 身高（可选）
        tk.Label(info_frame, text="身高:", font=("Microsoft YaHei", 10),
                bg='#ffffff', fg='#666666', width=12, anchor='e').grid(row=3, column=0, sticky="e", padx=(0, 15), pady=8)
        height_var = tk.StringVar()
        height_frame = tk.Frame(info_frame, bg='#ffffff')
        height_frame.grid(row=3, column=1, sticky="w", pady=8)
        height_entry = tk.Entry(height_frame, textvariable=height_var, font=("Microsoft YaHei", 10),
                               width=10, relief='solid', bd=1)
        height_entry.pack(side=tk.LEFT)
        tk.Label(height_frame, text="cm", font=("Microsoft YaHei", 10),
                bg='#ffffff', fg='#666666').pack(side=tk.LEFT, padx=(5, 0))
        
        # 体重（可选）
        tk.Label(info_frame, text="体重:", font=("Microsoft YaHei", 10),
                bg='#ffffff', fg='#666666', width=12, anchor='e').grid(row=4, column=0, sticky="e", padx=(0, 15), pady=8)
        weight_var = tk.StringVar()
        weight_frame = tk.Frame(info_frame, bg='#ffffff')
        weight_frame.grid(row=4, column=1, sticky="w", pady=8)
        weight_entry = tk.Entry(weight_frame, textvariable=weight_var, font=("Microsoft YaHei", 10),
                               width=10, relief='solid', bd=1)
        weight_entry.pack(side=tk.LEFT)
        tk.Label(weight_frame, text="kg", font=("Microsoft YaHei", 10),
                bg='#ffffff', fg='#666666').pack(side=tk.LEFT, padx=(5, 0))
        
        # 测试信息区域
        test_frame = tk.LabelFrame(main_frame, text=" 检测配置信息 ", 
                                  font=("Microsoft YaHei", 10, "bold"),
                                  bg='#ffffff', fg='#2c5282',
                                  relief='groove', bd=2, padx=15, pady=15)
        test_frame.pack(fill=tk.X, pady=(0, 10))
        
        # 网格配置
        test_frame.grid_columnconfigure(1, weight=1)
        
        # 测试项目选择（下拉框）
        tk.Label(test_frame, text="测试项目:", font=("Microsoft YaHei", 10, "bold"),
                bg='#ffffff', fg='#2d3748', width=12, anchor='e').grid(row=0, column=0, sticky="e", padx=(0, 15), pady=8)
        
        # 测试类型选项
        test_type_options = [
            ("COMPREHENSIVE", "综合评估"),
            ("WALK_4_LAPS", "步道4圈"),
            ("WALK_7_LAPS", "步道7圈"),
            ("STAND_LEFT", "左脚站立"),
            ("STAND_RIGHT", "右脚站立"),
            ("SIT_TO_STAND_5", "起坐5次")
        ]
        
        test_type_var = tk.StringVar(value="综合评估")
        test_type_combo = ttk.Combobox(test_frame, textvariable=test_type_var, 
                                      values=[text for _, text in test_type_options],
                                      state="readonly", width=18, font=("Microsoft YaHei", 10))
        test_type_combo.grid(row=0, column=1, sticky="w", pady=8)
        
        # 活动描述已移除，直接使用默认值
        
        # 按钮区域 - 医院风格
        button_frame = tk.Frame(main_frame, bg='#ffffff')
        button_frame.pack(fill=tk.X, pady=(15, 15))
        
        def on_confirm():
            # 验证必填字段
            if not name_var.get().strip():
                messagebox.showerror("输入错误", "请输入患者姓名", parent=dialog)
                name_entry.focus()
                return
            
            if not age_var.get().strip():
                messagebox.showerror("输入错误", "请输入患者年龄", parent=dialog)
                age_entry.focus()
                return
            
            try:
                age = int(age_var.get())
                if age <= 0 or age > 150:
                    raise ValueError()
            except ValueError:
                messagebox.showerror("输入错误", "请输入有效的年龄（1-150）", parent=dialog)
                age_entry.focus()
                return
            
            # 获取选中的测试类型（从下拉框）
            selected_text = test_type_combo.get()
            if not selected_text:
                messagebox.showerror("选择错误", "请选择测试项目", parent=dialog)
                return
            
            # 查找对应的API值
            primary_type = "COMPREHENSIVE"
            selected_name = selected_text
            for api_val, cn_name in test_type_options:
                if cn_name == selected_text:
                    primary_type = api_val
                    selected_name = cn_name
                    break
            
            selected_types = [primary_type]
            selected_names = [selected_name]
            
            # 构建患者信息
            result['patient_info'] = {
                'name': name_var.get().strip(),
                'age': age,
                'gender': gender_var.get(),
                'height': height_var.get().strip() if height_var.get().strip() else None,
                'weight': weight_var.get().strip() if weight_var.get().strip() else None,
                'test_date': datetime.now().strftime("%Y-%m-%d"),
                'test_type': primary_type,  # 主要测试类型
                'test_types': selected_types,  # 所有选中的测试类型
                'test_names': selected_names,  # 中文测试名称
                'notes': default_activity if default_activity else '从CSV文件导入的数据',
                'created_time': datetime.now().isoformat()
            }
            
            dialog.destroy()
        
        def on_cancel():
            dialog.destroy()
            
        # 医院风格按钮 - 居中显示
        cancel_btn = tk.Button(button_frame, text="取消", command=on_cancel,
                              font=("Microsoft YaHei", 11), 
                              bg='#dc3545', fg='white', relief='raised', bd=2,
                              activebackground='#c82333', activeforeground='white',
                              cursor='hand2', width=8, height=1)
        cancel_btn.pack(side=tk.LEFT, padx=(80, 15), pady=5)
        
        confirm_btn = tk.Button(button_frame, text="开始AI分析", command=on_confirm,
                               font=("Microsoft YaHei", 11, "bold"), 
                               bg='#28a745', fg='white', relief='raised', bd=2,
                               activebackground='#218838', activeforeground='white', 
                               cursor='hand2', width=12, height=1)
        confirm_btn.pack(side=tk.LEFT, pady=5)
        
        # 设置焦点到姓名输入框
        name_entry.focus()
        
        # 绑定回车键
        def on_enter(event):
            on_confirm()
        
        dialog.bind('<Return>', on_enter)
        
        # 等待用户操作
        dialog.wait_window()
        
        return result.get('patient_info', None)
    
    def send_multi_file_analysis(self, csv_files, patient_info):
        """发送多文件分析请求到 sarcneuro-edge"""
        try:
            import requests
            
            # 准备多文件上传数据
            files = []
            for csv_file in csv_files:
                files.append(('files', (csv_file['filename'], csv_file['content'], 'text/csv')))
            
            # 准备表单数据
            form_data = {
                'patient_name': patient_info['name'],
                'patient_age': str(patient_info['age']),
                'patient_gender': patient_info['gender'],
                'patient_height': patient_info.get('height', ''),
                'patient_weight': patient_info.get('weight', ''),
                'test_type': patient_info.get('test_type', 'COMPREHENSIVE')
            }
            
            # 调试：打印实际发送的请求参数
            self.log_ai_message(f"[DEBUG send_multi_file_analysis] 文件列表:")
            for i, (field, (filename, content, content_type)) in enumerate(files):
                content_preview = content[:100] + "..." if len(content) > 100 else content
                self.log_ai_message(f"  文件{i+1}: {filename} ({len(content)}字符) - {content_preview}")
            self.log_ai_message(f"[DEBUG send_multi_file_analysis] 表单数据: {form_data}")
            
            # 发送到 standalone_upload 的 /upload 接口
            response = requests.post(
                f"{self.sarcneuro_service.base_url}/upload",
                files=files,
                data=form_data,
                timeout=300  # 5分钟超时
            )
            
            if response.status_code == 200:
                upload_result = response.json()
                task_id = upload_result.get('task_id')
                
                if task_id:
                    # 轮询任务状态
                    return self.poll_analysis_result(task_id)
                else:
                    raise Exception("未获得任务ID")
            else:
                raise Exception(f"上传失败: HTTP {response.status_code}")
                
        except Exception as e:
            self.log_ai_message(f"[ERROR] 多文件分析失败: {e}")
            return {'status': 'error', 'message': str(e)}
    
    def poll_analysis_result(self, task_id):
        """轮询分析结果"""
        import requests
        import time
        
        max_attempts = 60  # 最多等待10分钟
        attempt = 0
        
        while attempt < max_attempts:
            try:
                response = requests.get(f"{self.sarcneuro_service.base_url}/status/{task_id}")
                
                if response.status_code == 200:
                    status_data = response.json()
                    status = status_data.get('status')
                    progress = status_data.get('progress', 0)
                    
                    self.log_ai_message(f"[STATUS] 分析进度: {progress}% - {status}")
                    
                    if status == "COMPLETED":
                        # 调试：记录服务返回的完整状态数据
                        self.log_ai_message(f"[DEBUG] SarcNeuro服务状态数据字段: {list(status_data.keys())}")
                        self.log_ai_message(f"[DEBUG] comprehensive_report_url: {status_data.get('comprehensive_report_url')}")
                        
                        # 分析完成，构造结果
                        return {
                            'status': 'success',
                            'data': {
                                'overall_score': status_data.get('overall_score', 85),
                                'risk_level': status_data.get('risk_level', 'LOW'),
                                'confidence': status_data.get('confidence', 0.75),
                                'analysis_summary': '多文件综合分析完成',
                                'report_url': status_data.get('comprehensive_report_url'),
                                'task_id': task_id,
                                'analysis_id': status_data.get('comprehensive_report_id', task_id),
                                'test_id': task_id,
                                'results': status_data.get('results', [])
                            }
                        }
                    elif status == "FAILED":
                        return {
                            'status': 'error',
                            'message': '分析任务失败'
                        }
                    
                    # 继续等待
                    time.sleep(10)  # 等待10秒
                    attempt += 1
                else:
                    raise Exception(f"状态查询失败: HTTP {response.status_code}")
                    
            except Exception as e:
                self.log_ai_message(f"[WARN] 状态查询错误: {e}")
                time.sleep(5)
                attempt += 1
        
        return {'status': 'error', 'message': '分析超时'}
    
    def import_csv_for_analysis(self):
        """导入CSV文件进行AI分析并生成报告"""
        if not SARCNEURO_AVAILABLE or not self.sarcneuro_service:
            messagebox.showerror("功能不可用", "SarcNeuro Edge AI分析功能不可用\n请检查相关模块是否正确安装")
            return
        
        # 选择CSV文件（支持多选）
        file_paths = filedialog.askopenfilenames(
            title="选择压力传感器CSV数据文件（可多选）",
            filetypes=[
                ("CSV files", "*.csv"),
                ("All files", "*.*")
            ],
            initialdir="."
        )
        
        if not file_paths:
            return
        
        # 显示患者信息收集对话框（传入第一个文件用于解析）
        patient_info = self.show_patient_info_dialog(file_paths[0])
        if not patient_info:
            return  # 用户取消了输入
        
        # 如果选择了多个文件，显示文件列表确认
        if len(file_paths) > 1:
            files_list = "\n".join([f"• {os.path.basename(f)}" for f in file_paths])
            confirm_msg = f"确认分析以下 {len(file_paths)} 个CSV文件？\n\n{files_list}\n\n患者：{patient_info['name']}\n测试项目：{', '.join(patient_info['test_names'])}"
            
            if not messagebox.askyesno("确认多文件分析", confirm_msg):
                return
        
        # 在后台线程中处理分析
        def analyze_csv():
            try:
                # 更新状态
                self.log_ai_message("[SCAN] 正在分析CSV文件...")
                self.root.config(cursor="wait")
                
                # 启动服务（如果未启动）
                if not self.sarcneuro_service.is_running:
                    self.log_ai_message("[START] 启动 SarcNeuro Edge 分析服务...")
                    if not self.sarcneuro_service.start_service():
                        raise Exception("无法启动 SarcNeuro Edge 服务")
                
                # 读取所有CSV文件
                import pandas as pd
                import json
                import os
                
                all_csv_data = []
                total_rows = 0
                
                for i, file_path in enumerate(file_paths):
                    self.log_ai_message(f"[FILE] 读取文件 {i+1}/{len(file_paths)}: {os.path.basename(file_path)}")
                    
                    df = pd.read_csv(file_path)
                    if 'data' not in df.columns:
                        raise Exception(f"CSV文件格式错误：{os.path.basename(file_path)} 必须包含'data'列")
                    
                    # 转换为CSV字符串
                    csv_content = df.to_csv(index=False)
                    all_csv_data.append({
                        'filename': os.path.basename(file_path),
                        'content': csv_content,
                        'rows': len(df)
                    })
                    total_rows += len(df)
                    
                    self.log_ai_message(f"[DATA] {os.path.basename(file_path)}: {len(df)} 行数据")
                
                self.log_ai_message(f"[INFO] 总计 {len(file_paths)} 个文件，{total_rows} 行数据")
                
                # 解析压力数据
                frames = []
                metadata = []  # 存储每帧的元数据
                
                for idx, row in df.iterrows():
                    try:
                        # 解析压力数据数组
                        if pd.isna(row['data']) or row['data'] == '':
                            continue
                            
                        data_array = json.loads(row['data'])
                        if len(data_array) in [256, 1024, 2048, 3072]:  # 支持16x16, 32x32, 32x64, 32x96
                            frames.append(data_array)
                            
                            # 收集元数据
                            frame_meta = {
                                'timestamp': row.get('time', ''),
                                'area': row.get('area', 0),
                                'total_pressure': row.get('press', 0),
                                'frame_index': idx
                            }
                            metadata.append(frame_meta)
                    except Exception as e:
                        # 跳过无效行，但记录警告
                        if idx < 5:  # 只显示前5个错误
                            self.log_ai_message(f"[WARN] 第{idx}行数据解析失败: {str(e)[:50]}")
                        continue
                
                if not frames:
                    raise Exception("CSV文件中没有有效的压力数据")
                
                # 数据统计分析
                total_frames = len(frames)
                array_size = len(frames[0]) if frames else 0
                
                # 计算数据质量指标
                valid_frames = sum(1 for meta in metadata if meta['total_pressure'] > 0)
                contact_ratio = (valid_frames / total_frames * 100) if total_frames > 0 else 0
                
                # 计算平均接触面积和压力
                avg_area = sum(meta['area'] for meta in metadata) / len(metadata) if metadata else 0
                avg_pressure = sum(meta['total_pressure'] for meta in metadata) / len(metadata) if metadata else 0
                
                # 确定传感器阵列类型
                if array_size == 256:
                    array_type = "16×16"
                elif array_size == 1024:
                    array_type = "32×32"
                elif array_size == 2048:
                    array_type = "32×64"
                elif array_size == 3072:
                    array_type = "32×96"
                else:
                    array_type = f"未知({array_size}点)"
                
                self.log_ai_message(f"[OK] 成功解析 {total_frames} 帧压力数据")
                self.log_ai_message(f"📐 传感器阵列: {array_type} ({array_size}个传感点)")
                self.log_ai_message(f"📏 平均接触面积: {avg_area:.1f} 像素")
                self.log_ai_message(f"⚖️ 平均总压力: {avg_pressure:.1f}")
                
                # 时间范围分析
                if metadata and metadata[0]['timestamp'] and metadata[-1]['timestamp']:
                    start_time = metadata[0]['timestamp']
                    end_time = metadata[-1]['timestamp']
                    self.log_ai_message(f"⏰ 采集时间: {start_time} ~ {end_time}")
                
                # 发送多文件分析请求到新的API接口
                self.log_ai_message("[AI] 发送多文件AI分析请求...")
                self.log_ai_message("[WAIT] AI分析正在进行中，请耐心等待...")
                self.log_ai_message("[STATUS] 分析状态：正在处理多个CSV文件...")
                
                # 使用新的多文件分析API
                self.log_ai_message(f"[DEBUG CSV导入] 上传文件数量: {len(all_csv_data)}")
                for i, csv_file in enumerate(all_csv_data):
                    self.log_ai_message(f"[DEBUG CSV导入] 文件{i+1}: {csv_file['filename']} ({csv_file['rows']}行)")
                self.log_ai_message(f"[DEBUG CSV导入] 患者信息: {patient_info}")
                result = self.send_multi_file_analysis(all_csv_data, patient_info)
                
                self.log_ai_message("📍 分析状态：检查分析结果...")
                
                # 检查分析结果
                self.log_ai_message("📍 分析状态：检查分析结果...")
                
                if result and result.get('status') == 'success':
                    analysis_data = result['data']
                    self.log_ai_message("[OK] AI分析完成！")
                    
                    # 显示分析结果摘要
                    overall_score = analysis_data.get('overall_score', 0)
                    risk_level = analysis_data.get('risk_level', 'UNKNOWN')
                    confidence = analysis_data.get('confidence', 0)
                    
                    self.log_ai_message(f"[DATA] 综合评分: {overall_score:.1f}/100")
                    self.log_ai_message(f"[WARN] 风险等级: {risk_level}")
                    self.log_ai_message(f"🎯 置信度: {confidence:.1%}")
                    
                    # 分析成功，获取完整结果并生成报告
                    analysis_id = analysis_data.get('analysis_id')
                    test_id = analysis_data.get('test_id')
                    
                    if analysis_id and test_id:
                        try:
                            self.log_ai_message(f"[INFO] 获取分析详细结果 (analysis_id: {analysis_id})")
                            
                            # 调用 /api/analysis/results/{analysis_id} 获取完整结果
                            detailed_result = self.get_analysis_result(analysis_id)
                            
                            if detailed_result:
                                # 详细记录返回的数据结构
                                self.log_ai_message(f"[DEBUG] 详细结果字段: {list(detailed_result.keys())}")
                                self.log_ai_message(f"[DEBUG] report_url: {detailed_result.get('report_url')}")
                                self.log_ai_message(f"[DEBUG] comprehensive_report_url: {detailed_result.get('comprehensive_report_url')}")
                                
                                # 检查是否已有报告URL (优先检查report_url，否则检查comprehensive_report_url)
                                report_url = detailed_result.get('report_url') or detailed_result.get('comprehensive_report_url')
                                if report_url:
                                    self.log_ai_message(f"📄 获取到HTML报告链接: {report_url}")
                                    # 下载HTML内容并保存到我们的目录结构
                                    local_report_path = self.download_and_save_html_report(report_url, patient_info)
                                    if local_report_path:
                                        self.log_ai_message(f"📄 HTML报告已保存: {local_report_path}")
                                        # 显示成功对话框，传递本地报告路径
                                        self.root.after(0, lambda: self.show_analysis_complete_dialog(analysis_data, local_report_path))
                                    else:
                                        self.log_ai_message("[WARN] HTML报告保存失败")
                                        self.root.after(0, lambda: self.show_analysis_complete_dialog(analysis_data, None))
                                else:
                                    self.log_ai_message("[WARN] 未找到报告链接")
                                    # 仍然显示分析完成，但没有报告
                                    self.root.after(0, lambda: self.show_analysis_complete_dialog(analysis_data, None))
                            else:
                                raise Exception("无法获取分析详细结果")
                                
                        except Exception as report_error:
                            self.log_ai_message(f"[WARN] 报告生成失败: {report_error}")
                            self.log_ai_message("[OK] 但AI分析已成功完成！")
                            
                            # 报告生成失败，但分析成功
                            success_msg = f"""[OK] AI分析成功完成！

[DATA] 分析结果：
• 综合评分：{overall_score:.1f}/100  
• 风险等级：{risk_level}
• 置信度：{confidence:.1%}

[WARN] 注意：报告生成失败，但AI分析数据完整。"""
                            
                            self.root.after(0, lambda: messagebox.showinfo("分析完成", success_msg))
                    else:
                        self.log_ai_message("[WARN] 分析结果中缺少analysis_id或test_id")
                        
                        success_msg = f"""[OK] AI分析成功完成！

[DATA] 分析结果：
• 综合评分：{overall_score:.1f}/100  
• 风险等级：{risk_level}
• 置信度：{confidence:.1%}

[WARN] 注意：无法生成报告（缺少必要ID）。"""
                        
                        self.root.after(0, lambda: messagebox.showinfo("分析完成", success_msg))
                    
                    # 分析成功，直接返回，不要继续到异常处理
                    return
                    
                else:
                    # 分析失败的详细信息
                    if result is None:
                        error_msg = "AI分析服务无响应 - 可能是服务超时或崩溃"
                        self.log_ai_message("[ERROR] 分析结果为空，服务可能无响应")
                    elif result.get('status') != 'success':
                        error_msg = result.get('message', '未知分析错误')
                        self.log_ai_message(f"[ERROR] 分析失败: {error_msg}")
                        # 如果有详细错误信息，也打印出来
                        if 'error' in result:
                            self.log_ai_message(f"[SCAN] 错误详情: {result['error']}")
                    else:
                        error_msg = "分析结果格式异常"
                        self.log_ai_message(f"[ERROR] 结果格式异常: {result}")
                    
                    # 只有真正分析失败才显示错误
                    self.log_ai_message(f"[ERROR] CSV分析失败: {error_msg}")
                    self.root.after(0, lambda: messagebox.showerror("分析失败", f"CSV分析失败: {error_msg}"))
                
            except Exception as e:
                # 只有程序异常才到这里
                error_msg = f"程序异常: {str(e)}"
                self.log_ai_message(f"[ERROR] {error_msg}")
                self.root.after(0, lambda: messagebox.showerror("程序错误", error_msg))
            
            finally:
                self.root.after(0, lambda: self.root.config(cursor=""))
        
        # 启动分析线程
        threading.Thread(target=analyze_csv, daemon=True).start()
    
    def generate_pdf_report(self):
        """生成当前数据的报告"""
        if not SARCNEURO_AVAILABLE or not self.sarcneuro_service:
            messagebox.showerror("功能不可用", "SarcNeuro Edge AI分析功能不可用")
            return
        
        # 检查是否有数据
        if not hasattr(self.data_processor, 'latest_pressure_array') or self.data_processor.latest_pressure_array is None:
            messagebox.showwarning("无数据", "当前没有压力传感器数据\n请先连接设备并采集数据")
            return
        
        # 显示患者信息输入对话框
        patient_dialog = PatientInfoDialog(self.root)
        if not patient_dialog.result:
            return
        
        patient_info = patient_dialog.result
        
        # 收集当前数据
        messagebox.showinfo("数据收集", "将收集30秒的实时数据进行分析\n请保持设备连接正常")
        
        # 实现数据收集和分析逻辑
        self.collect_and_analyze_data(patient_info)
    
    def start_sarcneuro_service(self):
        """启动SarcNeuro Edge服务"""
        if not SARCNEURO_AVAILABLE or not self.sarcneuro_service:
            messagebox.showerror("服务不可用", "SarcNeuro Edge 服务不可用")
            return
        
        def start_service():
            try:
                self.log_ai_message("[START] 启动 SarcNeuro Edge 服务...")
                if self.sarcneuro_service.start_service():
                    self.log_ai_message("[OK] SarcNeuro Edge 服务启动成功！")
                    status = self.sarcneuro_service.get_service_status()
                    self.root.after(0, lambda: messagebox.showinfo("服务启动成功", 
                        f"SarcNeuro Edge 服务已启动\n\n端口: {status['port']}\n进程ID: {status.get('process_id', 'N/A')}"))
                else:
                    self.log_ai_message("[ERROR] SarcNeuro Edge 服务启动失败")
                    self.root.after(0, lambda: messagebox.showerror("启动失败", "无法启动 SarcNeuro Edge 服务\n请检查端口是否被占用"))
            except Exception as e:
                self.log_ai_message(f"[ERROR] 服务启动异常: {e}")
                self.root.after(0, lambda: messagebox.showerror("启动异常", f"服务启动时发生异常:\n{e}"))
        
        threading.Thread(target=start_service, daemon=True).start()
    
    def show_analysis_history(self):
        """显示分析历史"""
        messagebox.showinfo("分析历史", "分析历史功能正在开发中\n\n当前会话的分析结果将显示在日志中\n未来版本将提供完整的历史记录管理")
    
    def show_service_status(self):
        """显示AI服务状态"""
        if not SARCNEURO_AVAILABLE or not self.sarcneuro_service:
            messagebox.showwarning("服务不可用", "SarcNeuro Edge AI分析功能不可用\n请检查相关模块是否正确安装")
            return
        
        try:
            status = self.sarcneuro_service.get_service_status()
            is_running = "🟢 运行中" if status['is_running'] else "🔴 未启动"
            
            status_info = f"""🧠 SarcNeuro Edge AI 服务状态

[START] 运行状态: {is_running}
🌐 服务端口: {status['port']}
🔗 服务地址: {status['base_url']}
🆔 进程ID: {status.get('process_id', 'N/A')}

{'[OK] 服务正常运行，可以进行AI分析' if status['is_running'] else '[WARN] 服务未启动，将在需要时自动启动'}"""
            
            messagebox.showinfo("AI服务状态", status_info)
            
        except Exception as e:
            messagebox.showerror("状态查询失败", f"无法获取服务状态:\n{e}")
    
    def generate_analysis_pdf(self, analysis_data, patient_info, source_file, metadata=None):
        """生成分析报告文件"""
        try:
            from datetime import datetime
            import os
            
            # 生成报告文件名
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            patient_name = patient_info.get('name', '未知患者').replace(' ', '_')
            report_filename = f"肌少症分析报告_{patient_name}_{timestamp}.txt"
            
            # 确保在当前工作目录生成
            report_path = os.path.join(os.getcwd(), report_filename)
            
            self.log_ai_message(f"📁 报告文件路径: {report_path}")
            
            # 生成详细的分析报告
            report_content = f"""
==========================================
🧠 SarcNeuro 肌少症智能分析报告
==========================================

[INFO] 患者基本信息
------------------------------------------
• 姓名: {patient_info.get('name', 'N/A')}
• 年龄: {patient_info.get('age', 'N/A')} 岁
• 性别: {patient_info.get('gender', 'N/A')}
• 身高: {patient_info.get('height', 'N/A')} cm
• 体重: {patient_info.get('weight', 'N/A')} kg
• 检测日期: {patient_info.get('test_date', 'N/A')}
• 检测类型: {patient_info.get('test_type', '综合分析')}

[DATA] AI分析结果
------------------------------------------
• 综合评分: {analysis_data.get('overall_score', 0):.1f}/100
• 风险等级: {analysis_data.get('risk_level', 'UNKNOWN')}
• 分析置信度: {analysis_data.get('confidence', 0):.1%}

🔬 详细分析数据
------------------------------------------"""

            # 添加详细分析数据
            detailed = analysis_data.get('detailed_analysis', {})
            if detailed:
                # 步态分析
                gait = detailed.get('gait_analysis', {})
                if gait:
                    report_content += f"""
🚶 步态分析:
  - 步行速度: {gait.get('walking_speed', 0):.3f} m/s
  - 步长: {gait.get('step_length', 0):.1f} cm
  - 步频: {gait.get('cadence', 0):.1f} 步/分钟
  - 步态不对称指数: {gait.get('asymmetry_index', 0):.3f}
  - 步态稳定性评分: {gait.get('stability_score', 0):.1f}/100"""

                # 平衡分析
                balance = detailed.get('balance_analysis', {})
                if balance:
                    report_content += f"""
⚖️ 平衡分析:
  - 压力中心位移: {balance.get('cop_displacement', 0):.2f} mm
  - 身体摆动面积: {balance.get('sway_area', 0):.2f} mm²
  - 摆动速度: {balance.get('sway_velocity', 0):.2f} mm/s
  - 平衡稳定性指数: {balance.get('stability_index', 0):.2f}
  - 跌倒风险评估: {balance.get('fall_risk_score', 0):.1%}"""

            # 医学解释
            interpretation = analysis_data.get('interpretation', '无详细解释')
            report_content += f"""

🏥 医学解释与建议
------------------------------------------
{interpretation}
"""

            # 异常检测
            abnormalities = analysis_data.get('abnormalities', [])
            if abnormalities:
                report_content += f"""
[WARN] 检测到的异常情况 ({len(abnormalities)}项)
------------------------------------------"""
                for i, abnormality in enumerate(abnormalities, 1):
                    report_content += f"""
{i}. {abnormality}"""

            # 康复建议
            recommendations = analysis_data.get('recommendations', [])
            if recommendations:
                report_content += f"""

💡 个性化康复建议 ({len(recommendations)}项)
------------------------------------------"""
                for i, recommendation in enumerate(recommendations, 1):
                    report_content += f"""
{i}. {recommendation}"""

            # 数据来源信息
            report_content += f"""

📁 数据来源信息
------------------------------------------
• 源文件: {os.path.basename(source_file)}
• 文件路径: {source_file}
• 分析时间: {datetime.now().strftime('%Y年%m月%d日 %H:%M:%S')}
• 分析版本: SarcNeuro Edge v1.0.0
• 技术支持: 威海聚桥工业科技有限公司

------------------------------------------
本报告由SarcNeuro AI智能分析系统生成
仅供医疗专业人员参考，不可替代临床诊断
==========================================
"""
            
            # 保存为文本文件（将来可改为PDF）
            with open(report_path, 'w', encoding='utf-8') as f:
                f.write(report_content)
            
            return report_path
            
        except Exception as e:
            raise Exception(f"报告生成失败: {e}")

    def generate_sarcneuro_report(self, test_id, format_type="pdf", csv_file_path=None, patient_info=None):
        """调用sarcneuro-edge API生成报告"""
        try:
            import requests
            import os
            from datetime import datetime
            
            if not self.sarcneuro_service or not self.sarcneuro_service.is_running:
                raise Exception("SarcNeuro Edge服务未运行")
            
            base_url = self.sarcneuro_service.base_url
            
            # 1. 调用报告生成API
            self.log_ai_message(f"🔗 调用报告生成API (test_id: {test_id})")
            
            generate_data = {
                "test_id": test_id,
                "report_type": "comprehensive",
                "format": format_type
            }
            
            response = requests.post(
                f"{base_url}/api/reports/generate",
                json=generate_data,
                timeout=60,
                headers={"Content-Type": "application/json"}
            )
            
            if response.status_code != 200:
                raise Exception(f"报告生成API调用失败: HTTP {response.status_code} - {response.text}")
            
            result = response.json()
            if result.get('status') != 'success':
                raise Exception(f"报告生成失败: {result.get('message', '未知错误')}")
            
            data = result.get('data', {})
            report_id = data.get('report_id')
            report_number = data.get('report_number')
            
            if not report_id:
                raise Exception("报告生成成功但未返回report_id")
            
            self.log_ai_message(f"[OK] 报告生成成功 (ID: {report_id}, 编号: {report_number})")
            
            # 2. 下载报告文件
            self.log_ai_message("📥 下载报告文件...")
            
            download_response = requests.get(
                f"{base_url}/api/reports/{report_id}/download",
                timeout=30
            )
            
            if download_response.status_code != 200:
                raise Exception(f"报告下载失败: HTTP {download_response.status_code}")
            
            # 3. 按用户要求的规则保存文件
            today = datetime.now().strftime("%Y-%m-%d")
            patient_name = patient_info.get('name', '未知患者') if patient_info else '未知患者'
            
            # 创建日期目录
            date_dir = os.path.join(os.getcwd(), today)
            if not os.path.exists(date_dir):
                os.makedirs(date_dir)
                self.log_ai_message(f"📁 创建日期目录: {date_dir}")
            
            # 使用原CSV文件名，但改为PDF扩展名
            if csv_file_path:
                csv_basename = os.path.splitext(os.path.basename(csv_file_path))[0]
                local_filename = f"{csv_basename}.{format_type}"
            else:
                local_filename = f"{patient_name}_肌少症分析报告.{format_type}"
            
            local_path = os.path.join(date_dir, local_filename)
            
            # 如果同名文件存在，添加时间戳
            if os.path.exists(local_path):
                timestamp = datetime.now().strftime("_%H%M%S")
                name_part = os.path.splitext(local_filename)[0]
                local_filename = f"{name_part}{timestamp}.{format_type}"
                local_path = os.path.join(date_dir, local_filename)
            
            # 写入文件
            with open(local_path, 'wb') as f:
                f.write(download_response.content)
            
            file_size = os.path.getsize(local_path)
            self.log_ai_message(f"💾 报告已保存到: {today}\\{local_filename} ({file_size} 字节)")
            
            return local_path
            
        except requests.exceptions.Timeout:
            raise Exception("报告生成请求超时")
        except requests.exceptions.RequestException as e:
            raise Exception(f"网络请求失败: {e}")
        except Exception as e:
            self.log_ai_message(f"[ERROR] 报告生成详细错误: {e}")
            raise
    
    def download_and_save_html_report(self, report_url, patient_info):
        """下载HTML报告并保存到我们的目录结构"""
        try:
            import requests
            from datetime import datetime
            import os
            import sys
            
            if not self.sarcneuro_service or not self.sarcneuro_service.is_running:
                raise Exception("SarcNeuro Edge服务未运行")
            
            # 构建完整的下载URL
            base_url = self.sarcneuro_service.base_url
            full_url = f"{base_url}{report_url}"
            
            self.log_ai_message(f"🔗 下载HTML报告: {full_url}")
            
            # 下载HTML内容
            response = requests.get(full_url, timeout=30)
            if response.status_code != 200:
                raise Exception(f"下载失败: HTTP {response.status_code}")
            
            html_content = response.text
            
            # 获取exe所在目录
            if getattr(sys, 'frozen', False):
                # 打包后的环境，使用exe所在目录
                exe_dir = os.path.dirname(sys.executable)
                base_dir = exe_dir
            else:
                # 开发环境
                base_dir = os.getcwd()
            
            # 创建按日期组织的目录结构
            today = datetime.now().strftime("%Y-%m-%d")
            report_dir = os.path.join(base_dir, "tmp", today, "reports")
            os.makedirs(report_dir, exist_ok=True)
            
            # 生成本地文件名
            patient_name = patient_info.get('name', '未知患者')
            test_type_raw = patient_info.get('test_type', 'COMPREHENSIVE')
            
            # 将英文测试类型转换为中文
            test_type_map = {
                'COMPREHENSIVE': '综合分析',
                'BALANCE': '平衡测试', 
                'GAIT': '步态分析',
                'STRENGTH': '力量测试',
                'FLEXIBILITY': '柔韧性测试'
            }
            test_type = test_type_map.get(test_type_raw, test_type_raw)
            
            timestamp = datetime.now().strftime("%H%M%S")
            filename = f"{patient_name}-{test_type}-综合报告-{timestamp}.html"
            
            # 保存到本地
            local_path = os.path.join(report_dir, filename)
            with open(local_path, 'w', encoding='utf-8') as f:
                f.write(html_content)
            
            self.log_ai_message(f"💾 HTML报告已保存到: {local_path}")
            return local_path
            
        except Exception as e:
            self.log_ai_message(f"[ERROR] HTML报告保存失败: {e}")
            return None

    def get_analysis_result(self, analysis_id):
        """调用sarcneuro-edge API获取分析详细结果"""
        try:
            import requests
            
            if not self.sarcneuro_service or not self.sarcneuro_service.is_running:
                raise Exception("SarcNeuro Edge服务未运行")
            
            base_url = self.sarcneuro_service.base_url
            
            # 调用 /api/analysis/results/{analysis_id}
            response = requests.get(
                f"{base_url}/api/analysis/results/{analysis_id}",
                timeout=30,
                headers={"Content-Type": "application/json"}
            )
            
            if response.status_code != 200:
                raise Exception(f"获取分析结果失败: HTTP {response.status_code} - {response.text}")
            
            result = response.json()
            if result.get('status') != 'success':
                raise Exception(f"获取分析结果失败: {result.get('message', '未知错误')}")
            
            self.log_ai_message("[OK] 成功获取分析详细结果")
            return result
            
        except requests.exceptions.Timeout:
            raise Exception("获取分析结果请求超时")
        except requests.exceptions.RequestException as e:
            raise Exception(f"网络请求失败: {e}")
        except Exception as e:
            self.log_ai_message(f"[ERROR] 获取分析结果错误: {e}")
            raise
    
    def show_analysis_complete_dialog(self, analysis_data, report_path):
        """显示分析完成对话框"""
        overall_score = analysis_data.get('overall_score', 0)
        risk_level = analysis_data.get('risk_level', 'UNKNOWN')
        confidence = analysis_data.get('confidence', 0)
        
        # 检查报告文件类型
        import os
        if report_path:
            file_ext = os.path.splitext(report_path)[1].lower()
            file_type = "报告" if file_ext == ".pdf" else "HTML报告" if file_ext == ".html" else "报告文件"
            filename = os.path.basename(report_path)
        else:
            file_ext = ""
            file_type = "分析报告"
            filename = "未保存"
        
        message = f"""🧠 AI分析完成！

[DATA] 分析结果:
• 综合评分: {overall_score:.1f}/100
• 风险等级: {risk_level}
• 置信度: {confidence:.1%}

[INFO] {file_type}已生成: {filename}

是否立即打开报告文件？"""
        
        result = messagebox.askyesno("分析完成", message)
        if result and report_path:
            try:
                import os
                import subprocess
                import platform
                
                if platform.system() == "Windows":
                    os.startfile(report_path)  # Windows
                elif platform.system() == "Darwin":
                    subprocess.run(['open', report_path])  # macOS
                else:
                    subprocess.run(['xdg-open', report_path])  # Linux
            except Exception as e:
                messagebox.showinfo("打开文件", f"请手动打开报告文件:\n{report_path}")
        elif result and not report_path:
            messagebox.showinfo("提示", "报告文件未保存，请检查分析服务状态或重试分析")
    
    def collect_and_analyze_data(self, patient_info):
        """收集实时数据并进行分析"""
        # 实现30秒数据收集逻辑
        # 这里可以复用integration_ui.py中的收集逻辑
        messagebox.showinfo("功能开发中", "实时数据收集分析功能正在开发中\n请使用CSV导入功能进行分析")

    def on_closing(self):
        """窗口关闭事件"""
        try:
            # 重置检测状态，避免影响下次启动
            self.detection_in_progress = False
            self.current_session = None
            self._selecting_for_detection = False
            
            # 重置按钮状态
            if hasattr(self, 'start_detection_btn'):
                try:
                    self.start_detection_btn.config(text="🚀 开始检测", state="normal")
                except:
                    pass
            
            # 停止肌少症分析服务
            if hasattr(self, 'sarcneuro_panel') and self.sarcneuro_panel:
                try:
                    if self.sarcneuro_panel.sarcneuro_service:
                        self.sarcneuro_panel.sarcneuro_service.stop_service()
                except:
                    pass
            
            # 停止菜单栏的 SarcNeuro 服务
            if hasattr(self, 'sarcneuro_service') and self.sarcneuro_service:
                try:
                    self.sarcneuro_service.stop_service()
                except:
                    pass
            
            self.stop_connection()
            self.root.quit()
            self.root.destroy()
        except Exception:
            pass
    
    # ==================== 患者档案管理方法 ====================
    def show_patient_manager(self):
        """显示患者档案管理界面"""
        try:
            manager = PatientManagerDialog(self.root, title="患者档案管理", select_mode=False)
            # 如果用户在管理界面中选择了患者，则设置为当前患者
            if hasattr(manager, 'selected_patient') and manager.selected_patient:
                self.current_patient = manager.selected_patient
                self.update_patient_status()
        except Exception as e:
            messagebox.showerror("错误", f"打开患者档案管理失败：{e}")
            print(f"[ERROR] 患者档案管理错误: {e}")
    
    def show_session_manager(self):
        """显示检测会话管理界面"""
        try:
            # 获取所有患者的当天检测会话
            today_sessions = self.get_all_today_sessions()
            
            if not today_sessions:
                messagebox.showinfo("无检测会话", "今天还没有任何检测会话记录")
                return
            
            # 显示会话管理界面
            self.create_session_manager_dialog(today_sessions)
            
        except Exception as e:
            messagebox.showerror("错误", f"打开检测会话管理失败：{e}")
            print(f"[ERROR] 检测会话管理错误: {e}")
    
    def get_all_today_sessions(self):
        """获取所有患者的当天会话"""
        try:
            # 获取所有患者
            patients = db.get_all_patients()
            today = datetime.now().strftime('%Y-%m-%d')
            all_today_sessions = []
            
            print(f"[DEBUG] 检查当天会话，今天日期: {today}")
            
            for patient in patients:
                sessions = db.get_patient_test_sessions(patient['id'])
                print(f"[DEBUG] 患者 {patient['name']} 有 {len(sessions)} 个会话")
                
                for s in sessions:
                    # 解析会话创建时间
                    created_time = s['created_time']
                    print(f"[DEBUG] 会话创建时间: {created_time}")
                    
                    # 处理ISO格式的时间
                    if 'T' in created_time:
                        session_date = created_time.split('T')[0]
                    else:
                        session_date = created_time.split(' ')[0] if ' ' in created_time else created_time
                    
                    print(f"[DEBUG] 解析的日期: {session_date}, 比较: {session_date == today}")
                    
                    if session_date == today:
                        # 添加患者信息到会话
                        s['patient_name'] = patient['name']
                        s['patient_id'] = patient['id']
                        s['patient_gender'] = patient['gender']
                        s['patient_age'] = patient['age']
                        all_today_sessions.append(s)
            
            print(f"[DEBUG] 找到 {len(all_today_sessions)} 个当天会话")
            
            # 按创建时间排序
            all_today_sessions.sort(key=lambda x: x['created_time'], reverse=True)
            return all_today_sessions
            
        except Exception as e:
            print(f"[ERROR] 获取当天所有会话失败: {e}")
            return []
    
    def create_session_manager_dialog(self, sessions):
        """创建检测会话管理对话框"""
        dialog = tk.Toplevel(self.root)
        dialog.title("检测会话管理 - 今日会话")
        dialog.resizable(True, True)
        dialog.grab_set()
        dialog.transient(self.root)
        
        # 设置窗口图标
        try:
            dialog.iconbitmap("icon.ico")
        except Exception:
            # 如果图标文件不存在，使用默认图标
            pass
        
        # 居中显示
        dialog.update_idletasks()
        screen_width = dialog.winfo_screenwidth()
        screen_height = dialog.winfo_screenheight()
        
        # 设置合适的窗口大小
        window_width = 1000
        window_height = 650
        x = (screen_width - window_width) // 2
        y = (screen_height - window_height) // 2
        dialog.geometry(f"{window_width}x{window_height}+{x}+{y}")
        
        # 主框架
        main_frame = ttk.Frame(dialog, padding="20")
        main_frame.pack(fill="both", expand=True)
        
        # 标题
        title_label = ttk.Label(main_frame, 
                               text="今日所有检测会话",
                               font=('Microsoft YaHei UI', 14, 'bold'))
        title_label.pack(pady=(0, 15))
        
        # 会话列表
        list_frame = ttk.LabelFrame(main_frame, text="检测会话列表", padding="10")
        list_frame.pack(fill="both", expand=True, pady=(0, 20))
        
        # 创建树状视图
        columns = ("患者姓名", "性别", "年龄", "会话名称", "状态", "进度", "创建时间")
        session_tree = ttk.Treeview(list_frame, columns=columns, show="headings", height=15)
        
        # 设置列标题和宽度
        column_widths = {"患者姓名": 100, "性别": 60, "年龄": 60, "会话名称": 180, "状态": 80, "进度": 80, "创建时间": 150}
        for col in columns:
            session_tree.heading(col, text=col)
            session_tree.column(col, width=column_widths.get(col, 100), minwidth=60, anchor="center")
        
        # 填充数据
        for i, session in enumerate(sessions):
            status_text = "已完成" if session['status'] == 'completed' else \
                         "进行中" if session['status'] == 'in_progress' else \
                         "已中断" if session['status'] == 'interrupted' else \
                         "等待中" if session['status'] == 'pending' else session['status']
            
            values = (
                session.get('patient_name', '未知'),
                session.get('patient_gender', ''),
                f"{session.get('patient_age', '')}岁",
                session['session_name'],
                status_text,
                f"{session['current_step']}/{session['total_steps']}",
                session['created_time'][:19].replace('T', ' ')
            )
            session_tree.insert("", "end", values=values, tags=(str(i),))
        
        # 添加滚动条
        scrollbar = ttk.Scrollbar(list_frame, orient="vertical", command=session_tree.yview)
        session_tree.configure(yscrollcommand=scrollbar.set)
        
        session_tree.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        
        # 按钮区域 - 增加垂直间距和高度
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(fill="x", pady=(10, 0))
        
        def on_resume():
            selection = session_tree.selection()
            if selection:
                # 获取选中项的索引
                tags = session_tree.item(selection[0])['tags']
                if tags:
                    session_index = int(tags[0])  # 获取会话索引
                    session = sessions[session_index]  # 从sessions列表中获取会话对象
                    
                    # 先选中对应的患者
                    patient_info = {
                        'id': session['patient_id'],
                        'name': session['patient_name'],
                        'gender': session.get('patient_gender', ''),
                        'age': session.get('patient_age', 0)
                    }
                    self.current_patient = patient_info
                    
                    # 标记正在恢复会话，避免触发自动检查
                    self._resuming_session = True
                    self.update_patient_status()
                    self._resuming_session = False
                    
                    if session['status'] in ['pending', 'in_progress', 'interrupted']:
                        # 设置当前会话
                        self.current_session = {
                            'id': session['id'],
                            'name': session['session_name'],
                            'patient_id': session['patient_id'],
                            'current_step': session['current_step'],
                            'total_steps': session['total_steps']
                        }
                        self.detection_in_progress = True
                        dialog.destroy()
                        # 直接显示检测向导，它会自动跳转到正确的步骤
                        self.show_detection_wizard()
                    else:
                        messagebox.showwarning("无法恢复", "只能恢复未完成的检测会话")
            else:
                messagebox.showwarning("提示", "请选择要恢复的检测会话")
        
        def on_generate_report():
            selection = session_tree.selection()
            if selection:
                # 获取选中项的索引
                tags = session_tree.item(selection[0])['tags']
                if tags:
                    session_index = int(tags[0])
                    session = sessions[session_index]
                    if session['status'] == 'completed':
                        dialog.destroy()
                        self.generate_report_for_session(session['id'])
                    else:
                        messagebox.showwarning("无法生成报告", "只能为已完成的检测会话生成报告")
            else:
                messagebox.showwarning("提示", "请选择要生成报告的检测会话")
        
        def on_delete_session():
            selection = session_tree.selection()
            if selection:
                # 获取选中项的索引
                tags = session_tree.item(selection[0])['tags']
                if tags:
                    session_index = int(tags[0])
                    session = sessions[session_index]
                    
                    # 确认删除
                    if messagebox.askyesno("确认删除", 
                                         f"确定要删除患者 {session['patient_name']} 的会话吗？\n\n"
                                         f"会话：{session['session_name']}\n"
                                         f"状态：{session['status']}\n\n"
                                         "此操作不可恢复！"):
                        try:
                            # 删除会话
                            if db.delete_test_session(session['id']):
                                messagebox.showinfo("删除成功", "会话已成功删除")
                                dialog.destroy()
                                # 重新打开会话管理界面
                                self.show_session_manager()
                            else:
                                messagebox.showerror("删除失败", "删除会话时发生错误")
                        except Exception as e:
                            messagebox.showerror("删除失败", f"删除会话失败：{e}")
            else:
                messagebox.showwarning("提示", "请选择要删除的检测会话")
        
        # 按钮布局 - 删除在左边，其他在右边
        # 左侧删除按钮
        delete_btn = ttk.Button(button_frame, text="🗑️ 删除会话", command=on_delete_session)
        delete_btn.pack(side="left", padx=(0, 10))
        
        # 右侧操作按钮
        right_buttons = ttk.Frame(button_frame)
        right_buttons.pack(side="right")
        
        resume_btn = ttk.Button(right_buttons, text="🔄 恢复检测", command=on_resume)
        resume_btn.pack(side="right", padx=(10, 0))
        
        report_btn = ttk.Button(right_buttons, text="📄 生成报告", command=on_generate_report)
        report_btn.pack(side="right", padx=(10, 0))
        
        # 绑定双击事件
        def on_double_click(event):
            on_resume()
        session_tree.bind("<Double-1>", on_double_click)
    
    def select_patient_for_detection(self):
        """为检测选择患者"""
        try:
            # 标记正在为检测选择患者，避免重复弹窗
            self._selecting_for_detection = True
            
            selector = PatientManagerDialog(self.root, title="选择患者档案", select_mode=True)
            if selector.selected_patient:
                self.current_patient = selector.selected_patient
                self.update_patient_status()
                return True
            return False
        except Exception as e:
            messagebox.showerror("错误", f"选择患者失败：{e}")
            print(f"[ERROR] 选择患者错误: {e}")
            return False
        finally:
            # 清除标记
            self._selecting_for_detection = False
    
    def update_patient_status(self):
        """更新患者状态显示"""
        if self.current_patient:
            patient_info = f"患者: {self.current_patient['name']} ({self.current_patient['gender']}, {self.current_patient['age']}岁)"
            self.status_label.config(text=patient_info, foreground="#28a745")
            
            
            # 只在非检测流程中检查未完成检测，避免重复弹窗
            # 通过标记来区分是否是从开始检测按钮触发的患者选择或正在恢复会话
            if not getattr(self, '_selecting_for_detection', False) and not getattr(self, '_resuming_session', False):
                self.root.after(500, self.check_and_resume_detection)
        else:
            self.status_label.config(text="⚙️ 未选择患者", foreground="#ff6b35")
    
    # ==================== 检测流程管理方法 ====================
    def start_detection_process(self):
        """开始检测流程"""
        try:
            # 检查设备配置
            if not self.device_configured:
                messagebox.showwarning("设备未配置", "请先配置检测设备后再开始检测！")
                self.show_device_config()
                return
            
            # 检查是否选择了患者
            if not self.current_patient:
                if not self.select_patient_for_detection():
                    return
            
            # 先检查当天是否有未完成的会话
            sessions = db.get_patient_test_sessions(self.current_patient['id'])
            
            # 只保留当天的会话
            today = datetime.now().strftime('%Y-%m-%d')
            today_sessions = []
            for s in sessions:
                # 解析会话创建时间
                created_time = s['created_time']
                # 处理ISO格式的时间
                if 'T' in created_time:
                    session_date = created_time.split('T')[0]
                else:
                    session_date = created_time.split(' ')[0] if ' ' in created_time else created_time
                
                if session_date == today:
                    today_sessions.append(s)
            
            # 从当天会话中筛选未完成的
            unfinished_sessions = [s for s in today_sessions if s['status'] in ['pending', 'in_progress', 'interrupted']]
            
            # 如果有未完成的会话，检查是否需要恢复
            if unfinished_sessions:
                # 优先找进行中的会话
                active_session = None
                for session in unfinished_sessions:
                    if session['status'] == 'in_progress':
                        active_session = session
                        break
                
                # 如果没有进行中的，找最新的未完成会话
                if not active_session:
                    active_session = unfinished_sessions[0]  # 已按时间排序，第一个是最新的
                
                # 检查会话的进度
                print(f"[DEBUG] 检查会话: {active_session['session_name']}, 状态: {active_session['status']}, 步骤: {active_session['current_step']}/{active_session['total_steps']}")
                
                # 如果已经有步骤进展（不是第0步），则提示恢复
                if active_session['current_step'] > 0:
                    if messagebox.askyesno("发现未完成检测", 
                                     f"患者 {self.current_patient['name']} 有未完成的检测会话。\n\n"
                                     f"会话：{active_session['session_name']}\n"
                                     f"进度：第 {active_session['current_step']}/{active_session['total_steps']} 步\n\n"
                                     "是否要恢复检测？"):
                        # 设置当前会话信息并恢复
                        self.current_session = {
                            'id': active_session['id'],
                            'name': active_session['session_name'],
                            'patient_id': self.current_patient['id'],
                            'current_step': active_session['current_step'],
                            'total_steps': active_session['total_steps']
                        }
                        self.detection_in_progress = True
                        self.show_detection_wizard()
                    else:
                        # 用户选择不恢复，删除旧会话并新建
                        self.delete_old_sessions_and_start_new()
                else:
                    # 会话存在但还没开始任何步骤，可以选择继续或新建
                    if messagebox.askyesno("发现未开始的检测会话", 
                                         f"患者 {self.current_patient['name']} 有一个未开始的检测会话。\n\n"
                                         f"会话：{active_session['session_name']}\n\n"
                                         "是否要继续这个会话？"):
                        # 继续使用这个会话
                        self.current_session = {
                            'id': active_session['id'],
                            'name': active_session['session_name'],
                            'patient_id': self.current_patient['id'],
                            'current_step': 0,
                            'total_steps': active_session['total_steps']
                        }
                        self.detection_in_progress = True
                        self.show_detection_wizard()
                    else:
                        # 用户选择不继续，删除旧会话并新建
                        self.delete_old_sessions_and_start_new()
            else:
                self.start_new_detection()
                
        except Exception as e:
            messagebox.showerror("错误", f"启动检测失败：{e}")
            print(f"[ERROR] 启动检测错误: {e}")
    
    def delete_old_sessions_and_start_new(self):
        """删除旧会话并开始新的检测"""
        try:
            # 获取当前患者的所有会话
            sessions = db.get_patient_test_sessions(self.current_patient['id'])
            
            # 删除所有旧会话
            deleted_count = 0
            for session in sessions:
                if db.delete_test_session(session['id']):
                    deleted_count += 1
            
            if deleted_count > 0:
                print(f"[INFO] 已删除 {deleted_count} 个旧会话")
            
            # 开始新的检测
            self.start_new_detection()
            
        except Exception as e:
            print(f"[ERROR] 删除旧会话失败: {e}")
            messagebox.showerror("错误", f"删除旧会话失败：{e}")
    
    def start_new_detection(self):
        """开始新的检测"""
        try:
            # 创建新的检测会话
            session_name = f"检测-{datetime.now().strftime('%Y%m%d%H%M%S')}"
            print(f"[DEBUG] 创建会话: 患者ID={self.current_patient['id']}, 会话名={session_name}")
            session_id = db.create_test_session(self.current_patient['id'], session_name)
            print(f"[DEBUG] 创建会话结果: session_id={session_id}")
            
            if session_id > 0:
                self.current_session = {
                    'id': session_id,
                    'name': session_name,
                    'patient_id': self.current_patient['id'],
                    'current_step': 0,
                    'total_steps': 6
                }
                
                self.detection_in_progress = True
                messagebox.showinfo("检测开始", 
                                  f"患者 {self.current_patient['name']} 的检测已开始！\n"
                                  f"检测会话: {session_name}\n\n"
                                  "即将开始第一步：静坐检测（10秒）")
                
                # 更新按钮状态
                self.start_detection_btn.config(text="🔄 检测中...", state="disabled")
                
                # 启动检测向导
                self.show_detection_wizard()
                
            else:
                messagebox.showerror("错误", "创建检测会话失败！")
                
        except Exception as e:
            messagebox.showerror("错误", f"开始检测失败：{e}")
            print(f"[ERROR] 开始检测错误: {e}")
    
    def resume_detection(self):
        """恢复检测"""
        try:
            if not self.current_patient:
                messagebox.showwarning("未选择患者", "请先选择患者档案")
                return
            
            # 获取患者的未完成检测会话
            sessions = db.get_patient_test_sessions(self.current_patient['id'])
            
            # 只保留当天的会话
            today = datetime.now().strftime('%Y-%m-%d')
            today_sessions = []
            for s in sessions:
                # 解析会话创建时间
                created_time = s['created_time']
                # 处理ISO格式的时间
                if 'T' in created_time:
                    session_date = created_time.split('T')[0]
                else:
                    session_date = created_time.split(' ')[0] if ' ' in created_time else created_time
                
                if session_date == today:
                    today_sessions.append(s)
            
            # 从当天会话中筛选未完成的
            unfinished_sessions = [s for s in today_sessions if s['status'] in ['pending', 'in_progress', 'interrupted']]
            
            if not unfinished_sessions:
                messagebox.showinfo("无未完成检测", "该患者没有未完成的检测会话")
                return
            
            # 如果有多个未完成会话，让用户选择
            if len(unfinished_sessions) > 1:
                session = self.select_session_to_resume(unfinished_sessions)
                if not session:
                    return
            else:
                session = unfinished_sessions[0]
            
            # 恢复会话状态
            self.current_session = {
                'id': session['id'],
                'name': session['session_name'],
                'patient_id': session['patient_id'] if 'patient_id' in session else self.current_patient['id'],
                'current_step': session['current_step'],
                'total_steps': session['total_steps']
            }
            
            self.detection_in_progress = True
            
            # 更新按钮状态
            self.start_detection_btn.config(text="🔄 检测中...", state="disabled")
            
            # 显示恢复信息
            messagebox.showinfo("恢复检测", 
                              f"已恢复患者 {self.current_patient['name']} 的检测\n"
                              f"检测会话: {session['session_name']}\n"
                              f"当前进度: {session['current_step']}/{session['total_steps']}")
            
            # 启动检测向导（从当前进度继续）
            self.show_detection_wizard()
                
        except Exception as e:
            messagebox.showerror("错误", f"恢复检测失败：{e}")
            print(f"[ERROR] 恢复检测失败: {e}")
    
    def select_session_to_resume(self, sessions):
        """选择要恢复的检测会话"""
        # 创建会话选择对话框
        dialog = tk.Toplevel(self.root)
        dialog.title("选择检测会话")
        dialog.geometry("700x450")
        dialog.resizable(True, True)
        dialog.grab_set()
        dialog.transient(self.root)
        
        # 居中显示
        dialog.update_idletasks()
        screen_width = dialog.winfo_screenwidth()
        screen_height = dialog.winfo_screenheight()
        x = (screen_width - 700) // 2
        y = (screen_height - 450) // 2
        dialog.geometry(f"700x450+{x}+{y}")
        
        result = None
        
        # 标题
        ttk.Label(dialog, text="选择要恢复的检测会话", 
                 font=('Microsoft YaHei UI', 12, 'bold')).pack(pady=10)
        
        # 会话列表
        list_frame = ttk.Frame(dialog)
        list_frame.pack(fill="both", expand=True, padx=20, pady=10)
        
        # 创建列表框
        columns = ("会话名称", "状态", "进度", "创建时间")
        session_tree = ttk.Treeview(list_frame, columns=columns, show="headings", height=12)
        
        # 设置列标题和宽度
        column_widths = {"会话名称": 200, "状态": 100, "进度": 100, "创建时间": 150}
        for col in columns:
            session_tree.heading(col, text=col)
            session_tree.column(col, width=column_widths.get(col, 120), minwidth=80)
        
        # 填充数据
        for session in sessions:
            values = (
                session['session_name'],
                session['status'],
                f"{session['current_step']}/{session['total_steps']}",
                session['created_time'][:19].replace('T', ' ')
            )
            session_tree.insert("", "end", values=values)
        
        # 添加滚动条
        scrollbar = ttk.Scrollbar(list_frame, orient="vertical", command=session_tree.yview)
        session_tree.configure(yscrollcommand=scrollbar.set)
        
        session_tree.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        
        # 按钮区域
        button_frame = ttk.Frame(dialog)
        button_frame.pack(fill="x", padx=20, pady=15)
        
        def on_confirm():
            nonlocal result
            selection = session_tree.selection()
            if selection:
                item = session_tree.item(selection[0])
                session_name = item['values'][0]
                # 根据名称找到对应的会话
                for s in sessions:
                    if s['session_name'] == session_name:
                        result = s
                        break
            dialog.destroy()
        
        def on_cancel():
            dialog.destroy()
        
        ttk.Button(button_frame, text="✅ 确认", command=on_confirm).pack(side="right", padx=(10, 0))
        ttk.Button(button_frame, text="❌ 取消", command=on_cancel).pack(side="right")
        
        # 等待对话框关闭
        dialog.wait_window()
        return result
    
    def check_and_resume_detection(self):
        """检查并提示恢复检测"""
        try:
            if not self.current_patient:
                return
            
            # 获取患者的未完成检测会话
            sessions = db.get_patient_test_sessions(self.current_patient['id'])
            
            # 只保留当天的会话
            today = datetime.now().strftime('%Y-%m-%d')
            today_sessions = []
            for s in sessions:
                # 解析会话创建时间
                created_time = s['created_time']
                # 处理ISO格式的时间
                if 'T' in created_time:
                    session_date = created_time.split('T')[0]
                else:
                    session_date = created_time.split(' ')[0] if ' ' in created_time else created_time
                
                if session_date == today:
                    today_sessions.append(s)
            
            # 从当天会话中筛选未完成的
            unfinished_sessions = [s for s in today_sessions if s['status'] in ['pending', 'in_progress', 'interrupted']]
            
            # 只有确实存在未完成的检测会话才提示
            if unfinished_sessions and len(unfinished_sessions) > 0:
                # 检查是否有真正开始的步骤（避免对新创建但未开始的会话误报）
                has_started_steps = False
                for session in unfinished_sessions:
                    steps = db.get_session_steps(session['id'])
                    for step in steps:
                        if step['status'] in ['in_progress', 'completed']:
                            has_started_steps = True
                            break
                    if has_started_steps:
                        break
                
                # 只有真正开始过步骤的会话才提示恢复
                if has_started_steps:
                    if messagebox.askyesno("发现未完成检测", 
                                         f"患者 {self.current_patient['name']} 有 {len(unfinished_sessions)} 个未完成的检测会话。\n\n是否要恢复检测？"):
                        self.resume_detection()
                    
        except Exception as e:
            print(f"[ERROR] 检查恢复检测失败: {e}")
    
    def show_detection_wizard(self):
        """显示检测向导界面"""
        try:
            if not self.current_session or not self.current_patient:
                messagebox.showerror("错误", "没有有效的检测会话或患者信息")
                return
            
            print(f"[DEBUG] 准备创建检测向导")
            
            # 初始化活动检测向导引用
            self._active_detection_wizard = None
            
            # 创建检测向导（它会自动将自己注册为活动向导）
            # 注意：传递self而不是self.root，这样检测向导可以访问主界面对象
            wizard = DetectionWizardDialog(self, self.current_patient, self.current_session)
            
            print(f"[DEBUG] 检测向导对话框已关闭")
            
            # 检测向导关闭后，无论如何都要重置状态，确保用户可以重新开始
            self.detection_in_progress = False
            self.start_detection_btn.config(text="🚀 开始检测", state="normal")
            
            # 清除活动检测向导引用
            self._active_detection_wizard = None
            print(f"[DEBUG] 活动检测向导已清除")
            
            # 检查检测状态
            self.check_detection_completion()
                
        except Exception as e:
            messagebox.showerror("错误", f"显示检测向导失败：{e}")
            print(f"[ERROR] 显示检测向导失败: {e}")
            # 即使出错也要重置状态
            self.detection_in_progress = False
            self.start_detection_btn.config(text="🚀 开始检测", state="normal")
            self._active_detection_wizard = None
    
    def check_detection_completion(self):
        """检查检测完成状态"""
        try:
            # 无论如何都要重置按钮状态，确保用户可以重新开始
            self.start_detection_btn.config(text="🚀 开始检测", state="normal")
            
            if not self.current_session:
                # 没有当前会话，重置状态
                self.detection_in_progress = False
                return
            
            # 获取会话信息
            sessions = db.get_patient_test_sessions(self.current_patient['id'])
            current_session = None
            for session in sessions:
                if session['id'] == self.current_session['id']:
                    current_session = session
                    break
            
            if current_session:
                if current_session['status'] == 'completed':
                    # 检测已完成
                    self.detection_in_progress = False
                    self.current_session = None
                    
                    # 提供AI分析选项
                    if messagebox.askyesno("检测完成", 
                                         f"患者 {self.current_patient['name']} 的检测已完成！\n\n"
                                         "是否要进行AI分析并生成报告？"):
                        self.start_ai_analysis_for_session(current_session['id'])
                    
                
                elif current_session['status'] == 'interrupted':
                    # 检测被中断，但仍可以重新开始
                    self.detection_in_progress = False  # 重置状态，允许重新开始
                    self.add_log("检测已暂停，可重新开始")
                
                else:
                    # 其他状态，重置
                    self.detection_in_progress = False
            else:
                # 找不到会话，重置状态
                self.detection_in_progress = False
                self.current_session = None
            
        except Exception as e:
            print(f"[ERROR] 检查检测完成状态失败: {e}")
    
    def start_ai_analysis_for_session(self, session_id):
        """为指定会话启动AI分析"""
        try:
            # 临时设置会话ID用于分析
            original_session = self.current_session
            self.current_session = {'id': session_id}
            
            # 启动AI分析
            self.start_ai_analysis()
            
            # 恢复原会话
            self.current_session = original_session
            
        except Exception as e:
            messagebox.showerror("错误", f"启动AI分析失败：{e}")
            print(f"[ERROR] 启动AI分析失败: {e}")
    
    def start_sarcneuro_analysis_for_session(self):
        """使用SarcNeuro Edge API为检测会话进行分析"""
        try:
            # 启动服务（如果未启动）
            if not self.sarcneuro_service.is_running:
                self.log_ai_message("[START] 启动 SarcNeuro Edge 分析服务...")
                if not self.sarcneuro_service.start_service():
                    raise Exception("无法启动 SarcNeuro Edge 服务")
            
            # 获取会话的检测数据
            session_steps = db.get_session_steps(self.current_session['id'])
            if not session_steps:
                raise Exception("没有找到检测数据")
            
            # 准备患者信息（与导入CSV相同的格式）
            # 性别字段转换：中文转英文，匹配CSV导入的格式
            gender_map = {'男': 'MALE', '女': 'FEMALE'}
            patient_gender = gender_map.get(self.current_patient['gender'], self.current_patient['gender'])
            
            patient_info = {
                'name': self.current_patient['name'],
                'age': self.current_patient['age'],
                'gender': patient_gender,  # 使用转换后的英文性别
                'height': str(self.current_patient.get('height', '')),  # 转为字符串
                'weight': str(self.current_patient.get('weight', '')),  # 转为字符串
                'test_type': 'COMPREHENSIVE',
                'test_names': [f"第{step['step_number']}步检测" for step in session_steps if step['status'] == 'completed']
            }
            
            # 创建临时CSV文件用于上传
            import tempfile
            import csv
            temp_files = []
            
            try:
                missing_files = []  # 记录丢失的文件
                for step in session_steps:
                    if step['status'] == 'completed':
                        if step['data_file_path'] and os.path.exists(step['data_file_path']):
                            # 直接使用现有的CSV文件
                            temp_files.append(step['data_file_path'])
                            self.log_ai_message(f"[OK] 找到数据文件: {os.path.basename(step['data_file_path'])}")
                        else:
                            # 记录丢失的文件信息
                            missing_files.append({
                                'step_number': step['step_number'],
                                'step_name': step['step_name'],
                                'original_path': step['data_file_path']
                            })
                            self.log_ai_message(f"[WARN] 步骤{step['step_number']}数据文件丢失: {step['data_file_path'] or '未记录路径'}")
                
                # 如果有丢失的文件，询问用户是否手动选择
                if missing_files:
                    manually_selected_files = self.ask_for_missing_files(missing_files)
                    if manually_selected_files:
                        temp_files.extend(manually_selected_files)
                
                if not temp_files:
                    raise Exception("没有有效的检测数据可供分析，请确保CSV数据文件存在")
                
                self.log_ai_message(f"[INFO] 准备上传 {len(temp_files)} 个检测数据文件到SarcNeuro Edge")
                
                # 读取CSV文件内容，准备上传数据
                all_csv_data = []
                for file_path in temp_files:
                    try:
                        with open(file_path, 'r', encoding='utf-8') as f:
                            csv_content = f.read()
                        all_csv_data.append({
                            'filename': os.path.basename(file_path),
                            'content': csv_content,
                            'rows': len(csv_content.split('\n')) - 1  # 减去标题行
                        })
                        self.log_ai_message(f"[DATA] 读取文件: {os.path.basename(file_path)}")
                    except Exception as e:
                        self.log_ai_message(f"[ERROR] 读取文件失败 {file_path}: {e}")
                        continue
                
                if not all_csv_data:
                    raise Exception("无法读取检测数据文件")
                
                # 使用与导入CSV相同的上传逻辑
                self.log_ai_message(f"[DEBUG 会话分析] 上传文件数量: {len(all_csv_data)}")
                for i, csv_file in enumerate(all_csv_data):
                    self.log_ai_message(f"[DEBUG 会话分析] 文件{i+1}: {csv_file['filename']} ({csv_file['rows']}行)")
                self.log_ai_message(f"[DEBUG 会话分析] 患者信息: {patient_info}")
                result = self.send_multi_file_analysis(all_csv_data, patient_info)
                
                if result and result.get('status') == 'success':
                    analysis_data = result['data']
                    
                    self.log_ai_message("[OK] AI分析完成！")
                    
                    # 显示分析结果摘要
                    overall_score = analysis_data.get('overall_score', 0)
                    risk_level = analysis_data.get('risk_level', 'UNKNOWN')
                    confidence = analysis_data.get('confidence', 0)
                    
                    self.log_ai_message(f"[DATA] 综合评分: {overall_score:.1f}/100")
                    self.log_ai_message(f"[WARN] 风险等级: {risk_level}")
                    self.log_ai_message(f"🎯 置信度: {confidence:.1%}")
                    
                    # 首先检查 analysis_data 是否已包含报告URL（和CSV导入一样）
                    report_url = analysis_data.get('report_url')
                    if report_url:
                        self.log_ai_message(f"📄 从分析结果获取到HTML报告链接: {report_url}")
                        # 下载HTML内容并保存到我们的目录结构
                        local_report_path = self.download_and_save_html_report(report_url, patient_info)
                        if local_report_path:
                            self.log_ai_message(f"📄 HTML报告已保存: {local_report_path}")
                            # 显示成功对话框，传递本地报告路径
                            self.show_analysis_complete_dialog(analysis_data, local_report_path)
                        else:
                            self.log_ai_message("[WARN] HTML报告保存失败")
                            self.show_analysis_complete_dialog(analysis_data, None)
                    else:
                        # 如果 analysis_data 中没有报告URL，再尝试获取详细结果（备用方案）
                        analysis_id = analysis_data.get('analysis_id')
                        test_id = analysis_data.get('test_id')
                        
                        if analysis_id and test_id:
                            self.log_ai_message(f"[INFO] 获取分析详细结果 (analysis_id: {analysis_id})")
                            
                            # 调用 /api/analysis/results/{analysis_id} 获取完整结果
                            detailed_result = self.get_analysis_result(analysis_id)
                            
                            if detailed_result:
                                # 详细记录返回的数据结构
                                self.log_ai_message(f"[DEBUG] 详细结果字段: {list(detailed_result.keys())}")
                                self.log_ai_message(f"[DEBUG] report_url: {detailed_result.get('report_url')}")
                                self.log_ai_message(f"[DEBUG] comprehensive_report_url: {detailed_result.get('comprehensive_report_url')}")
                                
                                # 检查是否已有报告URL (优先检查report_url，否则检查comprehensive_report_url)
                                report_url = detailed_result.get('report_url') or detailed_result.get('comprehensive_report_url')
                                if report_url:
                                    self.log_ai_message(f"📄 获取到HTML报告链接: {report_url}")
                                    # 下载HTML内容并保存到我们的目录结构
                                    local_report_path = self.download_and_save_html_report(report_url, patient_info)
                                    if local_report_path:
                                        self.log_ai_message(f"📄 HTML报告已保存: {local_report_path}")
                                        # 显示成功对话框，传递本地报告路径
                                        self.show_analysis_complete_dialog(analysis_data, local_report_path)
                                    else:
                                        self.log_ai_message("[WARN] HTML报告保存失败")
                                        self.show_analysis_complete_dialog(analysis_data, None)
                                else:
                                    self.log_ai_message("[WARN] 未找到报告链接")
                                    self.show_analysis_complete_dialog(analysis_data, None)
                            else:
                                raise Exception("无法获取分析详细结果")
                        else:
                            self.log_ai_message("[WARN] 分析结果中缺少必要的ID信息")
                            self.show_analysis_complete_dialog(analysis_data, None)
                else:
                    raise Exception(f"分析失败: {result.get('message', '未知错误')}")
                        
            finally:
                # 注意：这里不需要清理文件，因为我们使用的是实际的数据文件
                # 如果以后需要创建临时文件，可以在这里添加清理逻辑
                pass
                        
        except Exception as e:
            self.log_ai_message(f"[ERROR] SarcNeuro Edge分析失败: {e}")
            raise
    
    def ask_for_missing_files(self, missing_files):
        """询问用户手动选择丢失的CSV文件"""
        from tkinter import filedialog
        
        # 显示丢失文件的对话框
        missing_count = len(missing_files)
        missing_steps = ', '.join([f"步骤{f['step_number']}({f['step_name']})" for f in missing_files])
        
        msg = f"检测已完成，但有 {missing_count} 个数据文件丢失：\n\n{missing_steps}\n\n是否要手动选择这些CSV数据文件进行分析？"
        
        if not messagebox.askyesno("数据文件丢失", msg):
            return []
        
        selected_files = []
        
        for missing_file in missing_files:
            while True:
                file_path = filedialog.askopenfilename(
                    title=f"选择步骤{missing_file['step_number']}的CSV数据文件 - {missing_file['step_name']}",
                    filetypes=[
                        ("CSV files", "*.csv"),
                        ("All files", "*.*")
                    ],
                    initialdir="detection_data"  # 默认从检测数据目录开始
                )
                
                if not file_path:
                    # 用户取消了选择
                    if messagebox.askyesno("跳过文件", f"跳过步骤{missing_file['step_number']}的数据文件吗？\n\n注意：跳过此文件可能影响分析结果的完整性。"):
                        break  # 跳过这个文件
                    else:
                        continue  # 重新选择
                
                # 验证选择的文件
                try:
                    # 简单验证CSV文件格式
                    import pandas as pd
                    df = pd.read_csv(file_path)
                    if 'data' not in df.columns:
                        messagebox.showerror("文件格式错误", "选择的CSV文件格式不正确，必须包含'data'列")
                        continue
                    
                    selected_files.append(file_path)
                    self.log_ai_message(f"[OK] 手动选择文件: {os.path.basename(file_path)} (步骤{missing_file['step_number']})")
                    break
                    
                except Exception as e:
                    messagebox.showerror("文件读取错误", f"无法读取选择的文件：{e}")
                    continue
        
        return selected_files
    
    def generate_report_for_patient(self):
        """为当前选中的患者生成报告"""
        try:
            # 检查是否选中了患者
            if not self.current_patient:
                messagebox.showwarning("提示", "请先选择一个患者")
                return
            
            # 查找该患者的已完成检测会话
            completed_sessions = self.get_patient_completed_sessions(self.current_patient['id'])
            
            if not completed_sessions:
                messagebox.showwarning("提示", f"患者 {self.current_patient['name']} 还没有完成的检测记录")
                return
            
            # 如果有多个完成的会话，让用户选择
            if len(completed_sessions) > 1:
                session_id = self.select_session_for_report(completed_sessions)
                if not session_id:
                    return  # 用户取消选择
            else:
                session_id = completed_sessions[0]['id']
            
            # 为选中的会话生成报告
            self.generate_report_for_session(session_id)
            
        except Exception as e:
            messagebox.showerror("错误", f"生成报告失败：{e}")
            print(f"[ERROR] 生成报告失败: {e}")
    
    def generate_report_for_patient_id(self, patient_id):
        """为指定患者ID生成报告"""
        try:
            # 获取患者信息
            patient = db.get_patient_by_id(patient_id)
            if not patient:
                messagebox.showerror("错误", "未找到指定的患者")
                return
            
            # 查找该患者的已完成检测会话
            completed_sessions = self.get_patient_completed_sessions(patient_id)
            
            if not completed_sessions:
                messagebox.showwarning("提示", f"患者 {patient['name']} 还没有完成的检测记录")
                return
            
            # 如果有多个完成的会话，让用户选择
            if len(completed_sessions) > 1:
                session_id = self.select_session_for_report(completed_sessions)
                if not session_id:
                    return  # 用户取消选择
            else:
                session_id = completed_sessions[0]['id']
            
            # 临时设置为当前患者以便生成报告
            original_patient = self.current_patient
            self.current_patient = patient
            
            try:
                # 为选中的会话生成报告
                self.generate_report_for_session(session_id)
            finally:
                # 恢复原患者
                self.current_patient = original_patient
            
        except Exception as e:
            messagebox.showerror("错误", f"生成报告失败：{e}")
            print(f"[ERROR] 生成报告失败: {e}")
    
    def get_patient_completed_sessions(self, patient_id):
        """获取患者的已完成检测会话"""
        try:
            conn = sqlite3.connect(db.db_path)
            cursor = conn.cursor()
            
            # 查询已完成的检测会话
            cursor.execute('''
                SELECT s.*, 
                       COUNT(st.id) as total_steps,
                       COUNT(CASE WHEN st.status = 'completed' THEN 1 END) as completed_steps
                FROM test_sessions s
                LEFT JOIN test_steps st ON s.id = st.session_id
                WHERE s.patient_id = ? AND s.status = 'completed'
                GROUP BY s.id
                HAVING completed_steps >= 3
                ORDER BY s.created_time DESC
            ''', (patient_id,))
            
            sessions = []
            for row in cursor.fetchall():
                sessions.append({
                    'id': row[0],
                    'patient_id': row[1], 
                    'session_name': row[2],
                    'status': row[3],
                    'created_time': row[4],
                    'total_steps': row[6],
                    'completed_steps': row[7]
                })
            
            conn.close()
            return sessions
            
        except Exception as e:
            print(f"[ERROR] 查询已完成会话失败: {e}")
            return []
    
    def select_session_for_report(self, sessions):
        """让用户选择要生成报告的检测会话"""
        # 创建选择对话框
        dialog = tk.Toplevel(self.root)
        dialog.title("选择检测会话")
        dialog.geometry("600x400")
        dialog.resizable(True, True)
        dialog.grab_set()
        dialog.transient(self.root)
        
        # 居中显示
        dialog.update_idletasks()
        screen_width = dialog.winfo_screenwidth()
        screen_height = dialog.winfo_screenheight()
        x = (screen_width - 600) // 2
        y = (screen_height - 400) // 2
        dialog.geometry(f"600x400+{x}+{y}")
        
        selected_session_id = None
        
        # 主框架
        main_frame = ttk.Frame(dialog, padding=20)
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        ttk.Label(main_frame, text="请选择要生成报告的检测会话：", font=("Arial", 12, "bold")).pack(pady=(0, 15))
        
        # 会话列表
        list_frame = ttk.Frame(main_frame)
        list_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 15))
        
        # 创建列表框
        session_listbox = tk.Listbox(list_frame, font=("Arial", 10))
        scrollbar = ttk.Scrollbar(list_frame, orient="vertical", command=session_listbox.yview)
        session_listbox.configure(yscrollcommand=scrollbar.set)
        
        session_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # 填充会话数据
        for i, session in enumerate(sessions):
            created_time = session['created_time']
            if isinstance(created_time, str):
                try:
                    created_time = datetime.fromisoformat(created_time).strftime('%Y-%m-%d %H:%M')
                except:
                    pass
            
            session_text = f"{session['session_name']} ({created_time}) - {session['completed_steps']}个步骤"
            session_listbox.insert(tk.END, session_text)
        
        # 默认选中第一个
        if sessions:
            session_listbox.selection_set(0)
        
        # 按钮框架
        btn_frame = ttk.Frame(main_frame)
        btn_frame.pack(fill=tk.X)
        
        def on_confirm():
            nonlocal selected_session_id
            selection = session_listbox.curselection()
            if selection:
                selected_session_id = sessions[selection[0]]['id']
                dialog.destroy()
        
        def on_cancel():
            dialog.destroy()
        
        ttk.Button(btn_frame, text="确定", command=on_confirm).pack(side=tk.RIGHT, padx=(10, 0))
        ttk.Button(btn_frame, text="取消", command=on_cancel).pack(side=tk.RIGHT)
        
        # 等待用户选择
        dialog.wait_window()
        return selected_session_id
    
    def generate_report_for_session(self, session_id):
        """为指定的检测会话生成报告"""
        try:
            # 临时设置会话ID和患者信息
            original_session = self.current_session
            self.current_session = {'id': session_id}
            
            # 启动AI分析（会调用SarcNeuro Edge API）
            self.start_ai_analysis()
            
            # 恢复原会话
            self.current_session = original_session
            
        except Exception as e:
            self.current_session = original_session  # 确保恢复原会话
            raise
    
    def add_log(self, message):
        """添加日志信息（如果有日志控件的话）"""
        try:
            # 尝试在数据日志中添加信息
            if hasattr(self, 'data_log_text'):
                timestamp = datetime.now().strftime("%H:%M:%S")
                log_message = f"[{timestamp}] {message}\n"
                self.data_log_text.insert(tk.END, log_message)
                self.data_log_text.see(tk.END)
            
            # 同时打印到控制台
            print(f"[INFO] {message}")
            
        except Exception:
            print(f"[INFO] {message}")
    
    
    # ==================== AI分析和报告生成 ====================
    def start_ai_analysis(self):
        """开始AI分析并生成报告"""
        try:
            if not self.current_session or not self.current_patient:
                messagebox.showerror("错误", "没有有效的检测会话或患者信息")
                return
            
            # 检查是否有可用的AI分析服务
            if not SARCNEURO_AVAILABLE or not self.sarcneuro_service:
                messagebox.showwarning("AI服务不可用", 
                                     "AI分析服务不可用，无法生成智能报告。\n\n"
                                     "您可以手动导出检测数据进行分析。")
                return
            
            # 只使用SarcNeuro Edge API进行分析
            self.start_sarcneuro_analysis_for_session()
            
        except Exception as e:
            messagebox.showerror("错误", f"AI分析失败：{e}")
            print(f"[ERROR] AI分析失败: {e}")
    
    def open_website(self):
        """打开官方网站"""
        import webbrowser
        try:
            webbrowser.open("https://www.jq-tech.com")
        except Exception as e:
            # 如果无法打开浏览器，显示网址
            messagebox.showinfo("官方网站", 
                              "无法自动打开浏览器，请手动访问:\n\n"
                              "https://www.jq-tech.com\n\n"
                              "您可以复制此链接到浏览器地址栏访问。")
            print(f"[ERROR] 打开网站失败: {e}")
    

def main():
    # 创建主窗口
    root = tk.Tk()
    app = PressureSensorUI(root)
    
    # 设置关闭事件
    root.protocol("WM_DELETE_WINDOW", app.on_closing)
    
    # 启动界面
    root.mainloop()

if __name__ == "__main__":
    main() 