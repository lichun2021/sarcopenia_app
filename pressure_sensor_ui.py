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
from datetime import datetime

# 导入自定义模块
from serial_interface import SerialInterface
from data_processor import DataProcessor
from visualization import HeatmapVisualizer
from device_config import DeviceConfigDialog, DeviceManager

class PressureSensorUI:
    """主UI控制器类"""
    
    def __init__(self, root):
        self.root = root
        self.root.title("🔬 智能肌少症检测系统 - 压力传感器可视化 (模块化版本)")
        self.root.geometry("1600x1000")
        self.root.configure(bg='#f0f0f0')
        
        # 初始化多设备管理器
        self.device_manager = DeviceManager()
        self.serial_interface = None  # 将根据当前设备动态获取
        self.data_processor = DataProcessor(array_rows=32, array_cols=32)
        self.visualizer = None  # 在UI设置后创建
        
        # 设备配置状态
        self.device_configured = False
        
        # 数据监控
        self.is_running = False
        self.update_thread = None
        self.data_rate = 0
        self.last_frame_count = 0
        self.last_time = time.time()
        self.last_data_time = time.time()
        self.auto_reconnect_enabled = True
        self.device_lost_warned = False  # 防止重复弹窗
        
        # 界面设置
        self.setup_ui()
        self.setup_visualizer()
        
        # 启动更新循环
        self.start_update_loop()
        
        # 启动连接监控
        self.start_connection_monitor()
        
        # 显示设备配置对话框
        self.root.after(500, self.show_device_config)
    
    def show_device_config(self):
        """显示设备配置对话框"""
        config_dialog = DeviceConfigDialog(self.root)
        device_configs = config_dialog.show_dialog()
        
        if device_configs:
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
                if device_configs[first_device_id]['array_size'] == '32x96':
                    self.serial_interface.set_walkway_mode(True)
                
                self.on_device_changed(None)
                
            self.log_message("✅ 设备配置完成！")
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
                    self.log_message(f"❌ 设备配置不存在: {name}")
                    self.restore_current_device_selection()
                    return
                
                target_port = target_device_configs[device_id]['port']
                
                # 检查目标端口是否存在和有效
                if not self.check_port_availability(target_port):
                    self.log_message(f"❌ 设备端口无效或不存在: {name} ({target_port})")
                    messagebox.showwarning("设备切换失败", 
                                         f"无法切换到 {icon} {name}\n端口 {target_port} 不存在或无有效数据")
                    self.restore_current_device_selection()
                    return
                
                # 断开当前设备
                if self.is_running:
                    self.stop_connection()
                
                # 切换设备
                self.device_manager.switch_device(device_id)
                self.serial_interface = self.device_manager.get_current_serial_interface()
                
                # 更新UI显示
                device_info = self.device_manager.get_current_device_info()
                if device_info:
                    self.port_info_label.config(text=f"端口: {device_info['port']}")
                    
                    # 自动根据设备类型配置数组大小
                    self.auto_config_array_size(device_info['array_size'])
                    
                    # 根据设备类型设置步道模式
                    if device_info['array_size'] == '32x96':
                        self.serial_interface.set_walkway_mode(True)
                        self.log_message("🚶 已启用步道模式（3帧数据合并）")
                        # 显示调序按钮
                        self.order_button.grid()
                    else:
                        self.serial_interface.set_walkway_mode(False)
                        # 隐藏调序按钮
                        self.order_button.grid_remove()
                    
                    # 更新标题
                    self.root.title(f"🔬 智能肌少症检测系统 - {device_info['icon']} {device_info['name']}")
                    
                    self.log_message(f"✅ 已切换到设备: {device_info['icon']} {device_info['name']} ({device_info['port']})")
                    
                    # 自动连接设备
                    self.auto_connect_device()
                    
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
            self.log_message(f"❌ 检查端口失败: {e}")
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
                
            self.log_message(f"🔄 自动连接设备: {device_info['icon']} {device_info['name']} ({device_info['port']})")
            
            if self.device_manager.connect_current_device():
                self.is_running = True
                self.last_data_time = time.time()
                self.device_lost_warned = False  # 重置警告状态
                
                # 更新UI状态
                self.status_label.config(text="🟢 已连接", foreground="green")
                self.log_message(f"✅ 自动连接成功: {device_info['icon']} {device_info['name']}")
                
                # 连接成功后仍允许设备切换
                if self.device_configured:
                    self.device_combo.config(state="readonly")
                
            else:
                self.status_label.config(text="❌ 连接失败", foreground="red")
                self.log_message(f"❌ 自动连接失败: {device_info['icon']} {device_info['name']}")
                
        except Exception as e:
            self.status_label.config(text="❌ 连接错误", foreground="red")
            self.log_message(f"❌ 自动连接错误: {e}")
    
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
                    
                    self.log_message("⚠️ 检测到连接异常，尝试重新连接...")
                    
                    # 断开当前连接
                    self.stop_connection()
                    
                    # 等待一下再重连
                    self.root.after(2000, self.auto_connect_device)
                    
        except Exception as e:
            self.log_message(f"❌ 连接监控出错: {e}")
        
        # 每5秒检查一次连接状态
        self.root.after(5000, self.connection_monitor)
    
    def show_device_lost_warning(self, device_info):
        """显示设备丢失警告"""
        def show_warning():
            result = messagebox.askretrycancel(
                "设备连接丢失", 
                f"⚠️ 设备连接已丢失\n\n"
                f"设备: {device_info['icon']} {device_info['name']}\n"
                f"端口: {device_info['port']}\n\n"
                f"请检查设备连接状态\n\n"
                f"点击'重试'继续尝试连接\n"
                f"点击'取消'停止重连"
            )
            
            if not result:
                # 用户选择取消，停止重连
                self.auto_reconnect_enabled = False
                self.stop_connection()
                self.log_message("🔌 用户取消重连，已停止自动连接")
        
        # 在主线程中显示警告
        self.root.after(0, show_warning)
        
    def setup_ui(self):
        """设置用户界面"""
        # 主框架
        main_frame = ttk.Frame(self.root)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # 顶部控制面板
        control_frame = ttk.LabelFrame(main_frame, text="🎛️ 控制面板", padding=10)
        control_frame.pack(fill=tk.X, pady=(0, 10))
        
        # 第一行：设备和连接控制
        # 设备选择
        ttk.Label(control_frame, text="设备:").grid(row=0, column=0, padx=(0, 5))
        self.device_var = tk.StringVar()
        self.device_combo = ttk.Combobox(control_frame, textvariable=self.device_var, width=15, state="readonly")
        self.device_combo.grid(row=0, column=1, padx=(0, 10))
        self.device_combo.bind('<<ComboboxSelected>>', self.on_device_changed)
        
        # 设备配置按钮
        ttk.Button(control_frame, text="⚙️ 设备配置", command=self.show_device_config).grid(row=0, column=2, padx=(0, 20))
        
        # 状态标签
        self.status_label = ttk.Label(control_frame, text="⚙️ 未配置设备", foreground="orange")
        self.status_label.grid(row=0, column=3, padx=(0, 20))
        
        # 端口信息显示
        self.port_info_label = ttk.Label(control_frame, text="端口: 未知")
        self.port_info_label.grid(row=0, column=4, padx=(0, 10))
        
        # 第二行：功能按钮
        # 保存快照按钮
        ttk.Button(control_frame, text="📸 保存快照", command=self.save_snapshot).grid(row=1, column=0, padx=(0, 10), pady=(10, 0))
        
        # 调序按钮（仅32x32以上设备显示）
        self.order_button = ttk.Button(control_frame, text="🔄 调序", command=self.show_segment_order_dialog)
        self.order_button.grid(row=1, column=1, padx=(0, 10), pady=(10, 0))
        self.order_button.grid_remove()  # 默认隐藏
        
        # 中间内容区域
        content_frame = ttk.Frame(main_frame)
        content_frame.pack(fill=tk.BOTH, expand=True)
        
        # 左侧：热力图显示
        self.plot_frame = ttk.LabelFrame(content_frame, text="📊 压力传感器热力图 (32x32) - JQ工业科技", padding=10)
        self.plot_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 10))
        
        # 右侧：数据日志和统计
        right_frame = ttk.Frame(content_frame)
        right_frame.pack(side=tk.RIGHT, fill=tk.Y, padx=(0, 0))
        right_frame.config(width=450)
        
        # 统计信息面板
        stats_frame = ttk.LabelFrame(right_frame, text="📊 实时统计", padding=10)
        stats_frame.pack(fill=tk.X, pady=(0, 10))
        
        self.stats_labels = {}
        stats_items = [("最大值:", "max_value"), ("最小值:", "min_value"), ("平均值:", "mean_value"), 
                       ("标准差:", "std_value"), ("有效点:", "nonzero_count")]
        
        for i, (text, key) in enumerate(stats_items):
            row = i // 2
            col = (i % 2) * 2
            ttk.Label(stats_frame, text=text).grid(row=row, column=col, sticky="e", padx=(0, 5))
            label = ttk.Label(stats_frame, text="0", font=("Consolas", 10, "bold"))
            label.grid(row=row, column=col+1, sticky="w", padx=(0, 20))
            self.stats_labels[key] = label
        
        # 数据日志
        log_frame = ttk.LabelFrame(right_frame, text="📝 数据日志", padding=10)
        log_frame.pack(fill=tk.BOTH, expand=True)
        
        self.log_text = scrolledtext.ScrolledText(log_frame, width=55, height=25, font=("Consolas", 9))
        self.log_text.pack(fill=tk.BOTH, expand=True)
        
        # 日志控制按钮
        log_btn_frame = ttk.Frame(log_frame)
        log_btn_frame.pack(fill=tk.X, pady=(5, 0))
        
        ttk.Button(log_btn_frame, text="🗑️ 清除日志", command=self.clear_log).pack(side=tk.LEFT)
        ttk.Button(log_btn_frame, text="💾 保存日志", command=self.save_log).pack(side=tk.LEFT, padx=(10, 0))
        
        # 底部状态栏
        status_frame = ttk.Frame(main_frame)
        status_frame.pack(fill=tk.X, pady=(10, 0))
        
        self.frame_count_label = ttk.Label(status_frame, text="📦 接收帧数: 0")
        self.frame_count_label.pack(side=tk.LEFT)
        
        self.data_rate_label = ttk.Label(status_frame, text="📈 数据速率: 0 帧/秒")
        self.data_rate_label.pack(side=tk.RIGHT)
        
        
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
                self.log_message(f"❌ 不支持的阵列大小: {array_size_str}")
                return
            
            # 更新数据处理器
            self.data_processor.set_array_size(rows, cols)
            
            # 更新可视化器
            self.visualizer.set_array_size(rows, cols)
            
            # 更新标题
            self.plot_frame.config(text=f"📊 压力传感器热力图 ({rows}x{cols}) - JQ工业科技")
            
            self.log_message(f"✅ 已自动配置阵列大小: {rows}x{cols}")
            
        except Exception as e:
            self.log_message(f"❌ 自动配置阵列大小失败: {e}")
            
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
                self.log_message("❌ 保存快照失败")
        except Exception as e:
            self.log_message(f"❌ 保存快照出错: {e}")
    
    def show_segment_order_dialog(self):
        """显示段顺序调整对话框"""
        dialog = tk.Toplevel(self.root)
        dialog.title("🔄 调整段顺序")
        dialog.geometry("300x200")
        dialog.resizable(False, False)
        dialog.grab_set()
        
        # 居中显示
        dialog.transient(self.root)
        dialog.geometry("+%d+%d" % (
            self.root.winfo_rootx() + 200, 
            self.root.winfo_rooty() + 150
        ))
        
        # 主框架
        main_frame = ttk.Frame(dialog, padding=20)
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        ttk.Label(main_frame, text="32x96步道段顺序调整", font=("Arial", 12, "bold")).pack(pady=(0, 15))
        ttk.Label(main_frame, text="选择3个段的显示顺序:").pack(pady=(0, 10))
        
        # 当前顺序显示
        current_order = self.data_processor.get_segment_order()
        current_text = "当前顺序: " + " - ".join([f"段{i+1}" for i in current_order])
        ttk.Label(main_frame, text=current_text, foreground="blue").pack(pady=(0, 15))
        
        # 预设顺序按钮
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(fill=tk.X, pady=(0, 20))
        
        presets = [
            ("1-2-3", [0, 1, 2]),
            ("2-3-1", [1, 2, 0]), 
            ("3-1-2", [2, 0, 1]),
            ("1-3-2", [0, 2, 1]),
            ("2-1-3", [1, 0, 2]),
            ("3-2-1", [2, 1, 0])
        ]
        
        for i, (name, order) in enumerate(presets):
            row = i // 3
            col = i % 3
            btn = ttk.Button(button_frame, text=name, width=8,
                           command=lambda o=order: self.apply_segment_order(o, dialog))
            btn.grid(row=row, column=col, padx=5, pady=3)
        
        # 关闭按钮
        ttk.Button(main_frame, text="关闭", command=dialog.destroy).pack(pady=(10, 0))
    
    def apply_segment_order(self, order, dialog):
        """应用段顺序"""
        if self.data_processor.set_segment_order(order):
            order_text = " - ".join([f"段{i+1}" for i in order])
            self.log_message(f"🔄 段顺序已调整为: {order_text}")
            dialog.destroy()
        else:
            self.log_message("❌ 段顺序调整失败")
            
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
            self.log_message(f"💾 日志已保存: {filename}")
        except Exception as e:
            self.log_message(f"❌ 保存日志失败: {e}")
            
            
    def stop_connection(self):
        """停止连接"""
        try:
            self.is_running = False
            
            # 断开当前设备连接
            if self.device_configured:
                self.device_manager.disconnect_current_device()
            
            # 更新UI状态
            self.status_label.config(text="⚫ 未连接", foreground="red")
            self.log_message("🔌 连接已断开")
            
            # 重新启用设备选择
            if self.device_configured:
                self.device_combo.config(state="readonly")
            
        except Exception as e:
            self.log_message(f"❌ 断开连接时出错: {e}")
        
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
                    
                    # 只处理最新的帧，丢弃过旧的数据以减少延迟
                    frame_data = frame_data_list[-1]  # 取最新帧
                    # 根据设备类型决定是否使用JQ变换（32x32和32x96都使用JQ变换）
                    device_info = self.device_manager.get_current_device_info()
                    enable_jq = device_info and device_info.get('array_size') in ['32x32', '32x96']
                    processed_data = self.data_processor.process_frame_data(frame_data, enable_jq)
                    
                    
                    if 'error' not in processed_data:
                        # 更新可视化显示
                        matrix_2d = processed_data['matrix_2d']
                        statistics = processed_data['statistics']
                        
                        self.visualizer.update_data(matrix_2d, statistics)
                        
                        # 更新统计显示和日志
                        self.update_statistics_display(statistics)
                        self.log_processed_data(processed_data)
                        
                        # 显示丢弃的帧数（如果有）
                        dropped_frames = len(frame_data_list) - 1
                        if dropped_frames > 0:
                            self.log_message(f"⚡ Dropped {dropped_frames} old frames for real-time display")
                    else:
                        self.log_message(f"❌ Data processing error: {processed_data['error']}")
                
                # 计算数据速率
                self.calculate_data_rate()
                
        except Exception as e:
            self.log_message(f"❌ 更新数据时出错: {e}")
        
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
            self.log_message(f"❌ 更新统计显示出错: {e}")
            
    def log_processed_data(self, processed_data):
        """记录处理后的数据日志"""
        try:
            frame_info = processed_data['original_frame']
            stats = processed_data['statistics']
            
            timestamp = frame_info['timestamp']
            frame_num = frame_info['frame_number']
            array_size = processed_data['array_size']
            jq_applied = processed_data['jq_transform_applied']
            
            jq_indicator = "✨" if jq_applied else "📊"
            
            log_msg = (f"[{timestamp}] 帧#{frame_num:04d} {jq_indicator} ({array_size}) "
                      f"最大:{stats['max_value']:3d} 最小:{stats['min_value']:3d} "
                      f"平均:{stats['mean_value']:6.1f}")
            
            self.log_message(log_msg)
            
        except Exception as e:
            self.log_message(f"❌ 记录日志出错: {e}")
            
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
        """添加日志消息"""
        def add_log():
            self.log_text.insert(tk.END, message + "\n")
            self.log_text.see(tk.END)
            
            # 限制日志行数
            lines = self.log_text.get("1.0", tk.END).count('\n')
            if lines > 1000:
                self.log_text.delete("1.0", "100.0")
                
        # 在主线程中执行UI更新
        self.root.after(0, add_log)
        
    def clear_log(self):
        """清除日志"""
        self.log_text.delete("1.0", tk.END)
        self.log_message("📝 日志已清除")
        
    def on_closing(self):
        """窗口关闭事件"""
        try:
            self.stop_connection()
            self.root.quit()
            self.root.destroy()
        except Exception:
            pass

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