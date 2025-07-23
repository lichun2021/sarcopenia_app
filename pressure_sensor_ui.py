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
        self.root.configure(bg='#ffffff')  # 纯白背景，医院风格
        
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
        
        # 集成肌少症分析功能
        self.integrate_sarcneuro_analysis()
        
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
        file_menu.add_command(label="📁 新建检测档案", command=self.show_new_profile_dialog)
        file_menu.add_separator()
        file_menu.add_command(label="📊 导出检测数据", command=self.save_log)
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
        detection_menu.add_command(label="📋 检测流程指导", command=self.show_detection_process_dialog)
        detection_menu.add_command(label="👤 患者信息管理", command=self.show_new_profile_dialog)
        detection_menu.add_separator()
        detection_menu.add_command(label="⚙️ 设备配置管理", command=self.show_device_config)
        detection_menu.add_command(label="🔄 重新连接设备", command=self.auto_connect_device)
        
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
        device_menu.add_command(label="🔍 自动检测端口", command=lambda: self.show_device_config())
        device_menu.add_command(label="📊 实时数据监控", command=lambda: messagebox.showinfo("数据监控", "数据监控面板已在右侧显示"))
        device_menu.add_separator()
        device_menu.add_command(label="⚡ 性能模式设置", command=lambda: messagebox.showinfo("性能设置", "当前运行在标准模式\n可通过启动脚本切换:\n• run_ui.py (标准)\n• run_ui_fast.py (快速)\n• run_ui_ultra.py (极速)"))
        
        # 创建"视图"菜单（使用橙色健康主题）
        view_menu = tk.Menu(menubar, tearoff=0,
                           bg='#ffffff',        # 纯白背景
                           fg='#37474f',        # 深灰色文字
                           activebackground='#fff3e0',  # 淡橙色悬停
                           activeforeground='#f57c00',   # 深橙色悬停文字
                           font=('Microsoft YaHei UI', 11),
                           borderwidth=1,
                           relief='solid',
                           selectcolor='#ff9800')
        menubar.add_cascade(label="  👀 视图  ", menu=view_menu,
                          activebackground='#f0f8ff', activeforeground='#0066cc')
        
        # 添加视图菜单项
        view_menu.add_command(label="📈 统计数据面板", command=lambda: messagebox.showinfo("统计面板", "实时统计数据已在右侧显示\n包含最大值、最小值、平均值等"))
        view_menu.add_command(label="🎨 热力图显示设置", command=lambda: messagebox.showinfo("显示设置", "热力图显示功能:\n• 16级颜色梯度\n• 0-60mmHg压力范围\n• 实时数据更新"))
        view_menu.add_separator()
        view_menu.add_command(label="📝 清除日志记录", command=self.clear_log)
        view_menu.add_command(label="🔍 放大热力图", command=lambda: messagebox.showinfo("显示提示", "可拖拽调整窗口大小来放大显示"))
        
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
        help_menu.add_command(label="🚀 快速入门教程", command=lambda: messagebox.showinfo("快速入门", 
                                "智能肌少症检测系统快速入门:\n\n1️⃣ 设备配置\n   • 点击'设备配置'选择设备类型\n   • 配置COM端口连接\n\n2️⃣ 开始检测\n   • 确保设备连接正常\n   • 观察热力图实时显示\n\n3️⃣ 数据分析\n   • 查看右侧统计数据\n   • 保存检测快照和日志"))
        help_menu.add_separator()
        help_menu.add_command(label="🏥 产品介绍", command=lambda: messagebox.showinfo("产品介绍", 
                                "智能肌少症检测系统\n\n🔬 专业医疗设备\n• 压力传感器阵列技术\n• 实时数据可视化分析\n• 标准化检测流程\n\n🏥 适用场景\n• 医院康复科\n• 体检中心\n• 养老机构\n• 健康管理中心"))
        help_menu.add_separator()
        help_menu.add_command(label="🌐 官方网站", command=lambda: messagebox.showinfo("联系方式", 
                                "威海聚桥工业科技有限公司\n\n🌐 官方网站: www.jq-tech.com\n📧 技术支持: support@jq-tech.com\n📱 客服热线: 400-xxx-xxxx"))
        help_menu.add_command(label="📞 技术支持", command=lambda: messagebox.showinfo("技术支持", 
                                "24小时技术支持服务:\n\n📧 邮箱: support@jq-tech.com\n📱 热线: 400-xxx-xxxx\n💬 微信: JQ-Tech-Support\n⏰ 服务时间: 7×24小时\n\n🔧 远程协助服务可用"))
        help_menu.add_separator()
        help_menu.add_command(label="ℹ️ 关于本系统", command=self.show_about_dialog)
    
    def show_new_profile_dialog(self):
        """显示新建档案对话框"""
        dialog = tk.Toplevel(self.root)
        dialog.title("新建检测档案")
        dialog.geometry("600x500")
        dialog.resizable(False, False)
        dialog.grab_set()
        
        # 居中显示
        dialog.transient(self.root)
        x = self.root.winfo_x() + (self.root.winfo_width() - 600) // 2
        y = self.root.winfo_y() + (self.root.winfo_height() - 500) // 2
        dialog.geometry(f"600x500+{x}+{y}")
        
        # 主框架
        main_frame = ttk.Frame(dialog, padding=25)
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # 标题
        title_label = ttk.Label(main_frame, text="📁 新建检测档案", 
                               font=("Arial", 16, "bold"))
        title_label.pack(pady=(0, 20))
        
        # 基本信息框架
        info_frame = ttk.LabelFrame(main_frame, text="基本信息", padding=15)
        info_frame.pack(fill=tk.X, pady=(0, 15))
        
        # 姓名
        ttk.Label(info_frame, text="姓名:", font=("Microsoft YaHei", 10)).grid(
            row=0, column=0, sticky="e", padx=(0, 10), pady=5)
        name_entry = ttk.Entry(info_frame, width=20, font=("Microsoft YaHei", 10))
        name_entry.grid(row=0, column=1, sticky="w", pady=5)
        
        # 年龄
        ttk.Label(info_frame, text="年龄:", font=("Microsoft YaHei", 10)).grid(
            row=0, column=2, sticky="e", padx=(20, 10), pady=5)
        age_entry = ttk.Entry(info_frame, width=10, font=("Microsoft YaHei", 10))
        age_entry.grid(row=0, column=3, sticky="w", pady=5)
        
        # 性别
        ttk.Label(info_frame, text="性别:", font=("Microsoft YaHei", 10)).grid(
            row=1, column=0, sticky="e", padx=(0, 10), pady=5)
        gender_var = tk.StringVar(value="男")
        gender_frame = ttk.Frame(info_frame)
        gender_frame.grid(row=1, column=1, sticky="w", pady=5)
        ttk.Radiobutton(gender_frame, text="男", variable=gender_var, value="男").pack(side=tk.LEFT)
        ttk.Radiobutton(gender_frame, text="女", variable=gender_var, value="女").pack(side=tk.LEFT, padx=(10, 0))
        
        # 身高体重
        ttk.Label(info_frame, text="身高(cm):", font=("Microsoft YaHei", 10)).grid(
            row=1, column=2, sticky="e", padx=(20, 10), pady=5)
        height_entry = ttk.Entry(info_frame, width=10, font=("Microsoft YaHei", 10))
        height_entry.grid(row=1, column=3, sticky="w", pady=5)
        
        ttk.Label(info_frame, text="体重(kg):", font=("Microsoft YaHei", 10)).grid(
            row=2, column=0, sticky="e", padx=(0, 10), pady=5)
        weight_entry = ttk.Entry(info_frame, width=10, font=("Microsoft YaHei", 10))
        weight_entry.grid(row=2, column=1, sticky="w", pady=5)
        
        # 联系方式
        ttk.Label(info_frame, text="联系方式:", font=("Microsoft YaHei", 10)).grid(
            row=2, column=2, sticky="e", padx=(20, 10), pady=5)
        contact_entry = ttk.Entry(info_frame, width=15, font=("Microsoft YaHei", 10))
        contact_entry.grid(row=2, column=3, sticky="w", pady=5)
        
        # 检测配置框架
        config_frame = ttk.LabelFrame(main_frame, text="检测配置", padding=15)
        config_frame.pack(fill=tk.X, pady=(0, 15))
        
        # 检测模式
        ttk.Label(config_frame, text="检测模式:", font=("Microsoft YaHei", 10)).grid(
            row=0, column=0, sticky="e", padx=(0, 10), pady=5)
        mode_var = tk.StringVar(value="标准检测")
        mode_combo = ttk.Combobox(config_frame, textvariable=mode_var, width=18,
                                 values=["标准检测", "快速检测", "详细检测"], state="readonly")
        mode_combo.grid(row=0, column=1, sticky="w", pady=5)
        
        # 检测设备
        ttk.Label(config_frame, text="检测设备:", font=("Microsoft YaHei", 10)).grid(
            row=0, column=2, sticky="e", padx=(20, 10), pady=5)
        device_info = self.device_manager.get_current_device_info() if self.device_configured else None
        device_name = f"{device_info['icon']} {device_info['name']}" if device_info else "未配置设备"
        device_label = ttk.Label(config_frame, text=device_name, 
                                font=("Microsoft YaHei", 10), foreground="blue")
        device_label.grid(row=0, column=3, sticky="w", pady=5)
        
        # 备注框架
        notes_frame = ttk.LabelFrame(main_frame, text="备注信息", padding=15)
        notes_frame.pack(fill=tk.X, pady=(0, 20))
        
        notes_text = tk.Text(notes_frame, height=4, width=60, font=("Microsoft YaHei", 10))
        notes_scrollbar = ttk.Scrollbar(notes_frame, orient="vertical", command=notes_text.yview)
        notes_text.configure(yscrollcommand=notes_scrollbar.set)
        notes_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        notes_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # 按钮框架
        btn_frame = ttk.Frame(main_frame)
        btn_frame.pack(pady=(10, 0))
        
        def create_profile():
            """创建档案"""
            name = name_entry.get().strip()
            if not name:
                messagebox.showwarning("输入错误", "请输入姓名！")
                return
            
            try:
                age = int(age_entry.get()) if age_entry.get() else 0
                height = float(height_entry.get()) if height_entry.get() else 0
                weight = float(weight_entry.get()) if weight_entry.get() else 0
            except ValueError:
                messagebox.showwarning("输入错误", "年龄、身高、体重请输入数字！")
                return
            
            # 创建档案信息
            from datetime import datetime
            profile_data = {
                "name": name,
                "age": age,
                "gender": gender_var.get(),
                "height": height,
                "weight": weight,
                "contact": contact_entry.get().strip(),
                "detection_mode": mode_var.get(),
                "device": device_name,
                "notes": notes_text.get("1.0", tk.END).strip(),
                "create_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "profile_id": datetime.now().strftime("%Y%m%d_%H%M%S")
            }
            
            # 保存档案到文件
            try:
                import json
                filename = f"检测档案_{profile_data['profile_id']}.json"
                with open(filename, 'w', encoding='utf-8') as f:
                    json.dump(profile_data, f, ensure_ascii=False, indent=2)
                
                self.log_message(f"📁 新档案已创建: {name} ({filename})")
                messagebox.showinfo("档案创建成功", 
                                  f"检测档案创建成功！\n\n"
                                  f"姓名: {name}\n"
                                  f"档案编号: {profile_data['profile_id']}\n"
                                  f"保存位置: {filename}")
                dialog.destroy()
                
            except Exception as e:
                messagebox.showerror("保存失败", f"档案保存失败：{e}")
        
        ttk.Button(btn_frame, text="✅ 创建档案", command=create_profile, width=15).pack(side=tk.LEFT, padx=(0, 10))
        ttk.Button(btn_frame, text="❌ 取消", command=dialog.destroy, width=15).pack(side=tk.LEFT)

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
        title_label = ttk.Label(main_frame, text="📋 智能肌少症检测系统 - 检测流程指南", 
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

🎯 检测目标：
通过压力传感器阵列监测人体平衡能力、肌力表现和步态稳定性，综合评估肌少症风险。

📝 检测流程（总时长约2-3分钟）：

┌────────────────────────────────────────────┐
│  第一步：静坐检测（10秒）                    │
├────────────────────────────────────────────┤
│  • 请坐在检测区域，保持自然坐姿            │
│  • 双脚平放，身体放松                      │
│  • 系统将记录基础压力分布数据              │
│  • 用途：建立个人基准数据，排除外界干扰    │
└────────────────────────────────────────────┘

┌────────────────────────────────────────────┐
│  第二步：起坐测试（5次重复）               │
├────────────────────────────────────────────┤
│  • 从坐姿快速起立至完全站直                │
│  • 重复5次，动作要连贯有力                 │
│  • 系统监测起立时的力量变化                │
│  • 用途：评估下肢肌力和协调性              │
└────────────────────────────────────────────┘

┌────────────────────────────────────────────┐
│  第三步：静态站立（10秒）                  │
├────────────────────────────────────────────┤
│  • 双脚并拢，身体直立                      │
│  • 目视前方，保持平衡                      │
│  • 避免左右摇摆或前后晃动                  │
│  • 用途：测试静态平衡能力                  │
└────────────────────────────────────────────┘

┌────────────────────────────────────────────┐
│  第四步：前后脚站立（10秒）                │
├────────────────────────────────────────────┤
│  • 一脚在前，一脚在后，呈一条直线          │
│  • 保持身体平衡，不扶任何支撑物            │
│  • 可选择左脚或右脚在前                    │
│  • 用途：测试动态平衡和本体感觉            │
└────────────────────────────────────────────┘

┌────────────────────────────────────────────┐
│  第五步：双脚前后站立（10秒）              │
├────────────────────────────────────────────┤
│  • 双脚前后交替站立                        │
│  • 每只脚轮流承重，类似走路预备姿势        │
│  • 保持上身稳定                            │
│  • 用途：评估步态预备能力和平衡调节        │
└────────────────────────────────────────────┘

┌────────────────────────────────────────────┐
│  第六步：握力检测                          │
├────────────────────────────────────────────┤
│  • 站在检测区域，使用握力计测量            │
│  • 双手各测量3次，取最高值                 │
│  • 与压力传感器数据同步记录                │
│  • 用途：评估上肢肌力表现                  │
└────────────────────────────────────────────┘

┌────────────────────────────────────────────┐
│  第七步：4.5米步道折返                     │
├────────────────────────────────────────────┤
│  • 以正常速度行走4.5米                     │
│  • 转身后返回起点                          │
│  • 系统记录完整步态数据                    │
│  • 用途：分析步态稳定性和行走能力          │
└────────────────────────────────────────────┘

⚠️ 注意事项：
• 检测过程中请穿着舒适、防滑的鞋子
• 如有身体不适或平衡困难，请立即停止检测
• 检测区域周围应有安全保护措施
• 建议由专业人员陪同指导完成

📊 数据分析：
系统将综合所有检测数据，通过AI算法分析：
• 静态平衡评分
• 动态平衡评分  
• 肌力指数
• 步态稳定性指数
• 综合健康风险评估

🎯 检测意义：
通过多维度数据融合，提供科学、客观的肌少症风险评估，为健康管理和康复训练提供数据支持。

💡 温馨提示：
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
❓ 系统操作指南

本指南将帮助您快速掌握智能肌少症检测系统的各项功能和操作方法。

🚀 快速开始

1️⃣ 首次使用系统
   • 启动程序后会自动弹出设备配置对话框
   • 选择您的检测设备类型（32x32, 32x64, 32x96）
   • 配置COM端口和设备参数
   • 点击"确认配置"完成初始化

2️⃣ 设备连接
   • 确保压力传感器设备已正确连接电脑
   • 检查USB或串口线连接状态
   • 系统会自动检测并连接配置的设备
   • 连接成功后状态栏显示"🟢 已连接"

🎛️ 主界面操作

📊 热力图显示区域
   • 实时显示压力传感器数据的热力图
   • 颜色越红表示压力越大，越蓝表示压力越小
   • 支持32x32, 32x64, 32x96多种阵列规格
   • 自动适配显示比例和颜色映射

📈 实时统计面板
   • 最大值：当前帧的最大压力值
   • 最小值：当前帧的最小压力值  
   • 平均值：所有传感器点的平均压力
   • 标准差：压力分布的离散程度
   • 有效点：非零压力点的数量

📝 数据日志区域
   • 实时显示接收到的数据帧信息
   • 包含时间戳、帧编号、统计数据
   • JQ变换标识（✨表示已应用，📊表示原始数据）
   • 支持日志清除和保存功能

🎛️ 控制面板功能

🔧 设备管理
   • 设备选择：从下拉菜单选择当前使用的设备
   • 设备配置：重新配置设备参数和端口设置
   • 自动连接：系统会自动连接选择的设备
   • 连接监控：自动检测连接状态并尝试重连

⚙️ 功能按钮
   • 📸 保存快照：保存当前热力图为PNG图片文件
   • 🔄 调序：调整32x96步道模式的段显示顺序
   • 💾 保存日志：将当前日志内容保存为文本文件
   • 🗑️ 清除日志：清空日志显示区域

🍽️ 菜单栏功能

📋 检测菜单
   • 📁 新建档案：创建新的检测档案，录入被检测者信息
   • 📋 检测流程：查看标准化7步检测流程说明

🛠️ 其他菜单
   • ❓ 操作帮助：查看本操作指南（当前页面）
   • ℹ️ 关于系统：查看系统版本和开发信息

🔍 设备配置详解

📱 支持的设备类型
   • 32x32阵列：标准检测模式，适用于静态平衡测试
   • 32x64阵列：扩展检测模式，适用于动态平衡测试
   • 32x96阵列：步道模式，适用于步态分析和行走测试

🔌 端口配置
   • 自动检测：系统会扫描可用的COM端口
   • 手动选择：可以指定特定的COM端口
   • 波特率：默认1,000,000 bps（无需修改）
   • 连接测试：配置时会自动测试端口连通性

⚡ 性能优化设置

🏃 运行模式
   • 标准模式：run_ui.py - 20 FPS，平衡性能与稳定性
   • 快速模式：run_ui_fast.py - 100 FPS，高刷新率显示
   • 极速模式：run_ui_ultra.py - 200 FPS，极致响应速度

🔄 数据处理
   • JQ变换：威海聚桥工业科技专用数据变换算法
   • 自动应用于32x32和32x96阵列数据
   • 提供数据镜像翻转和重排序功能
   • 优化数据显示效果和分析精度

🚨 故障排除

❌ 常见问题
   • 设备无法连接：检查USB线缆和端口选择
   • 数据接收异常：确认设备电源和波特率设置
   • 热力图不更新：检查设备连接状态和数据流
   • 程序运行缓慢：尝试使用标准模式或重启程序

🔧 解决方案
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

📊 数据分析
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
        
        info_title = tk.Label(info_card, text="📋 系统信息", 
                             font=("Microsoft YaHei UI", 14, "bold"),
                             bg='#ffffff', fg='#2c3e50')
        info_title.pack(anchor="w", padx=20, pady=(15, 10))
        
        # 创建信息网格
        info_grid_frame = tk.Frame(info_card, bg='#ffffff')
        info_grid_frame.pack(fill=tk.X, padx=20, pady=(0, 15))
        
        info_items = [
            ("🏷️ 软件版本:", "v1.2.0 模块化专业版", "#27ae60"),
            ("🏢 开发公司:", "威海聚桥工业科技有限公司", "#3498db"),
            ("🔧 技术支持:", "JQ工业科技压力传感器阵列", "#e67e22"),
            ("📐 支持阵列:", "32×32, 32×64, 32×96 多规格", "#9b59b6"),
            ("📅 开发时间:", "2024年 (持续更新中)", "#34495e"),
            ("💻 运行环境:", "Windows 10/11, Python 3.7+", "#16a085"),
            ("⚡ 性能模式:", "标准/快速/极速 三种模式", "#f39c12"),
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
            "🎨 实时压力数据可视化热力图显示 (16级颜色梯度)",
            "🔄 多设备智能配置和无缝切换管理系统",
            "✨ JQ工业科技专用数据变换算法 (镜像+重排)",
            "⚡ 高性能数据处理引擎 (最高200FPS刷新率)",
            "📋 标准化健康检测流程指导和档案管理",
            "💾 数据导出、快照保存和日志记录功能",
            "🔍 智能端口检测和自动连接重连机制",
            "📊 实时统计分析 (最值/均值/标准差/有效点)",
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
📡 通信参数: 串口通信，波特率1,000,000 bps，帧头AA 55 03 99
📐 阵列规格: 支持32×32(1024点)、32×64(2048点)、32×96(3072点)
🎯 数据精度: 8位无符号整数 (0-255)，压力范围0-60mmHg
⚡ 刷新性能: 标准20FPS/快速100FPS/极速200FPS三种模式
💻 系统要求: Windows 10/11，Python 3.7+，4GB内存，USB端口
🔄 数据处理: JQ变换算法，NumPy向量化计算，多线程架构
        """
        
        specs_label = tk.Label(specs_card, text=specs_text.strip(), 
                              font=("Consolas", 9),
                              bg='#ffffff', fg='#34495e',
                              justify=tk.LEFT, anchor="w")
        specs_label.pack(anchor="w", padx=20, pady=(0, 15))
        
        # 联系方式卡片
        contact_card = tk.Frame(main_frame, bg='#2c3e50')
        contact_card.pack(fill=tk.X, pady=(0, 20))
        
        contact_title = tk.Label(contact_card, text="📞 联系方式与技术支持", 
                                font=("Microsoft YaHei UI", 14, "bold"),
                                bg='#2c3e50', fg='#ffffff')
        contact_title.pack(anchor="w", padx=20, pady=(15, 10))
        
        contact_info = [
            "🏢 威海聚桥工业科技有限公司",
            "🌐 官方网站: www.jq-tech.com",
            "📧 技术支持: support@jq-tech.com", 
            "📱 客服热线: 400-xxx-xxxx (工作日 9:00-18:00)",
            "📍 公司地址: 山东省威海市环翠区工业园区",
            "💬 微信客服: JQ-Tech-Support",
        ]
        
        for info in contact_info:
            info_label = tk.Label(contact_card, text=info, 
                                 font=("Microsoft YaHei UI", 10),
                                 bg='#2c3e50', fg='#ecf0f1')
            info_label.pack(anchor="w", padx=20, pady=2)
        
        contact_bottom = tk.Label(contact_card, text="🤝 感谢您使用智能肌少症检测系统！", 
                                 font=("Microsoft YaHei UI", 11, "bold"),
                                 bg='#2c3e50', fg='#f1c40f')
        contact_bottom.pack(anchor="center", pady=(10, 15))
        
        # 按钮区域
        btn_frame = tk.Frame(main_frame, bg='#f8f9fa')
        btn_frame.pack(pady=(20, 10))
        
        # 创建更美观的按钮
        close_btn = tk.Button(btn_frame, text="✅ 关闭", 
                             command=dialog.destroy,
                             font=("Microsoft YaHei UI", 11, "bold"),
                             bg='#3498db', fg='white',
                             activebackground='#2980b9',
                             activeforeground='white',
                             relief='flat', bd=0,
                             padx=25, pady=8,
                             cursor='hand2')
        close_btn.pack(side=tk.LEFT, padx=5)
        
        info_btn = tk.Button(btn_frame, text="🌐 官网", 
                            command=lambda: messagebox.showinfo("官方网站", "请访问: www.jq-tech.com"),
                            font=("Microsoft YaHei UI", 11),
                            bg='#27ae60', fg='white',
                            activebackground='#229954',
                            activeforeground='white',
                            relief='flat', bd=0,
                            padx=20, pady=8,
                            cursor='hand2')
        info_btn.pack(side=tk.LEFT, padx=5)
        
        # 打包滚动区域
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        
        # 绑定鼠标滚轮事件
        def _on_mousewheel(event):
            canvas.yview_scroll(int(-1*(event.delta/120)), "units")
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
        
        # 状态标签 - 医院配色
        self.status_label = tk.Label(control_frame, text="⚙️ 未配置设备", 
                                   foreground="#ff6b35", bg='#ffffff',
                                   font=('Microsoft YaHei UI', 10, 'bold'))
        self.status_label.grid(row=0, column=3, padx=(0, 25))
        
        # 端口信息显示
        self.port_info_label = tk.Label(control_frame, text="端口: 未知",
                                      bg='#ffffff', fg='#6c757d',
                                      font=('Microsoft YaHei UI', 9))
        self.port_info_label.grid(row=0, column=4, padx=(0, 15))
        
        # 第二行：功能按钮
        # 保存快照按钮
        ttk.Button(control_frame, text="📸 保存快照", 
                  command=self.save_snapshot,
                  style='Hospital.TButton').grid(row=1, column=0, padx=(0, 15), pady=(15, 0))
        
        # 调序按钮（仅32x32以上设备显示）
        self.order_button = ttk.Button(control_frame, text="🔄 调序", 
                                     command=self.show_segment_order_dialog,
                                     style='Hospital.TButton')
        self.order_button.grid(row=1, column=1, padx=(0, 15), pady=(15, 0))
        self.order_button.grid_remove()
        
        # 中间内容区域 - 医院白色背景
        content_frame = ttk.Frame(main_frame, style='Hospital.TFrame')
        content_frame.pack(fill=tk.BOTH, expand=True)
        
        # 左侧：热力图显示 - 医院风格边框
        self.plot_frame = ttk.LabelFrame(content_frame, 
                                       text="📊 压力传感器热力图 (32x32) - JQ工业科技", 
                                       padding=15, style='Hospital.TLabelframe')
        self.plot_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 15))
        
        # 右侧：数据日志和统计 - 医院白色
        right_frame = ttk.Frame(content_frame, style='Hospital.TFrame')
        right_frame.pack(side=tk.RIGHT, fill=tk.Y, padx=(0, 0))
        right_frame.config(width=450)
        
        # 统计信息面板 - 医院风格
        stats_frame = ttk.LabelFrame(right_frame, text="📊 实时统计", 
                                   padding=15, style='Hospital.TLabelframe')
        stats_frame.pack(fill=tk.X, pady=(0, 15))
        
        self.stats_labels = {}
        stats_items = [("最大值:", "max_value"), ("最小值:", "min_value"), ("平均值:", "mean_value"), 
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
        
        # 数据日志 - 医院风格
        log_frame = ttk.LabelFrame(right_frame, text="📝 数据日志", 
                                 padding=15, style='Hospital.TLabelframe')
        log_frame.pack(fill=tk.BOTH, expand=True)
        
        # 日志文本框 - 医院配色
        self.log_text = scrolledtext.ScrolledText(log_frame, width=55, height=25, 
                                                font=("Consolas", 9),
                                                bg='#ffffff',
                                                fg='#495057',
                                                selectbackground='#e3f2fd',
                                                selectforeground='#1976d2',
                                                insertbackground='#1976d2',
                                                borderwidth=1,
                                                relief='solid')
        self.log_text.pack(fill=tk.BOTH, expand=True)
        
        # 日志控制按钮
        log_btn_frame = ttk.Frame(log_frame, style='Hospital.TFrame')
        log_btn_frame.pack(fill=tk.X, pady=(10, 0))
        
        ttk.Button(log_btn_frame, text="💾 保存日志", 
                  command=self.save_log,
                  style='Hospital.TButton').pack(side=tk.LEFT, padx=(0, 10))
        ttk.Button(log_btn_frame, text="🗑️ 清除日志", 
                  command=self.clear_log,
                  style='Hospital.TButton').pack(side=tk.LEFT)
        
        # 底部状态栏 - 医院风格
        status_frame = ttk.Frame(main_frame, style='Hospital.TFrame')
        status_frame.pack(fill=tk.X, pady=(15, 0))
        
        # 创建状态栏背景
        status_bg = tk.Frame(status_frame, bg='#f8f9fa', height=35, relief='solid', bd=1)
        status_bg.pack(fill=tk.X)
        
        self.frame_count_label = tk.Label(status_bg, text="📦 接收帧数: 0",
                                        bg='#f8f9fa', fg='#495057',
                                        font=('Microsoft YaHei UI', 9))
        self.frame_count_label.pack(side=tk.LEFT, padx=(15, 0), pady=8)
        
        self.data_rate_label = tk.Label(status_bg, text="📈 数据速率: 0 帧/秒",
                                      bg='#f8f9fa', fg='#495057',
                                      font=('Microsoft YaHei UI', 9))
        self.data_rate_label.pack(side=tk.RIGHT, padx=(0, 15), pady=8)
    
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
        
    def integrate_sarcneuro_analysis(self):
        """集成肌少症分析功能"""
        try:
            from integration_ui import integrate_sarcneuro_analysis
            integrate_sarcneuro_analysis(self)
            print("✅ 肌少症分析功能集成成功")
        except Exception as e:
            print(f"⚠️ 肌少症分析功能集成失败: {e}")
            # 不影响主程序运行

    def on_closing(self):
        """窗口关闭事件"""
        try:
            # 停止肌少症分析服务
            if hasattr(self, 'sarcneuro_panel') and self.sarcneuro_panel:
                try:
                    if self.sarcneuro_panel.sarcneuro_service:
                        self.sarcneuro_panel.sarcneuro_service.stop_service()
                except:
                    pass
            
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