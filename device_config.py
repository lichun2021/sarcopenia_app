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
import sqlite3
import os
from datetime import datetime
from serial_interface import SerialInterface
from window_manager import WindowManager, WindowLevel, setup_management_window

class DeviceConfigDialog:
    """设备配置引导对话框"""
    
    def __init__(self, parent, skip_port_detection=None):
        self.parent = parent
        self.result = None
        self.dialog = None
        self.device_configs = {}
        self.scanning = True
        self._refreshing = False
        
        # 设备类型定义
        self.device_types = {
            'cushion': {'name': '坐垫', 'icon': '🪑', 'array_size': '32x32', 'com_ports': 1},
            'footpad': {'name': '脚垫', 'icon': '👣', 'array_size': '32x32', 'com_ports': 1}, 
            'walkway_dual': {'name': '步道', 'icon': '🚶', 'array_size': '32x64', 'com_ports': 2},
            # 'walkway': {'name': '步道(单口)', 'icon': '🚶', 'array_size': '32x96', 'com_ports': 1},
            # 'walkway_triple': {'name': '步道(三口)', 'icon': '🚶‍♀️', 'array_size': '32x96', 'com_ports': 3}
        }
        
        # COM口扫描
        self.serial_interface = SerialInterface()
        self.available_ports = []
        self.port_data_status = {}  # 端口数据状态
        
        # 跳过检测的端口列表（已被主程序占用）
        self.skip_port_detection = skip_port_detection or []
        
        # 线程安全的更新队列
        self.update_queue = queue.Queue()
        
        # SQLite数据库路径
        self.config_db = "device_config.db"
        self.init_database()
        
    def show_dialog(self):
        """显示配置对话框"""
        # 使用窗口管理器创建管理界面
        self.dialog = WindowManager.create_managed_window(self.parent, WindowLevel.DIALOG, 
                                                        "设备配置引导",
                                                        (800, 600))
        
        # 先隐藏窗口，避免初始化时的闪烁
        self.dialog.withdraw()
        
        self.dialog.grab_set()  # 模态对话框
        self.dialog.transient(self.parent)
        
        self.setup_dialog_ui()
        
        # 自动检测并加载已保存的配置
        saved_config = self.load_saved_config()
        if saved_config:
            # 延迟应用保存的配置（等UI完全初始化后）
            self.dialog.after(500, lambda: self.apply_saved_config_to_ui(saved_config))
            print(f"检测到已保存的配置，包含 {len(saved_config)} 个设备")
        
        self.start_port_scanning()
        self.start_ui_update_loop()
        
        # 绑定关闭事件
        self.dialog.protocol("WM_DELETE_WINDOW", self.on_dialog_close)
        
        # 显示窗口（已经居中）
        self.dialog.deiconify()
        
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
    
    def init_database(self):
        """初始化SQLite数据库"""
        try:
            conn = sqlite3.connect(self.config_db, timeout=10.0)
            cursor = conn.cursor()
            
            # 检查是否需要升级数据库架构
            cursor.execute("PRAGMA table_info(device_configs)")
            columns = [column[1] for column in cursor.fetchall()]
            
            needs_upgrade = ('ports' not in columns or 'com_ports' not in columns or 'device_type' not in columns)
            
            if needs_upgrade:
                print("🔄 检测到旧版数据库，正在升级架构...")
                
                # 备份旧数据
                old_data = []
                try:
                    cursor.execute('SELECT * FROM device_configs')
                    old_data = cursor.fetchall()
                except:
                    pass
                
                # 删除旧表并创建新表
                cursor.execute('DROP TABLE IF EXISTS device_configs')
                
                # 创建新的设备配置表（支持多端口）
                cursor.execute('''
                    CREATE TABLE device_configs (
                        device_id TEXT PRIMARY KEY,
                        ports TEXT NOT NULL,
                        port TEXT,
                        name TEXT NOT NULL,
                        icon TEXT NOT NULL,
                        array_size TEXT NOT NULL,
                        com_ports INTEGER NOT NULL,
                        device_type TEXT NOT NULL,
                        created_at TEXT NOT NULL,
                        updated_at TEXT NOT NULL
                    )
                ''')
                
                print("✅ 数据库架构升级完成")
            else:
                # 表已存在且架构正确
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS device_configs (
                        device_id TEXT PRIMARY KEY,
                        ports TEXT NOT NULL,
                        port TEXT,
                        name TEXT NOT NULL,
                        icon TEXT NOT NULL,
                        array_size TEXT NOT NULL,
                        com_ports INTEGER NOT NULL,
                        device_type TEXT NOT NULL,
                        created_at TEXT NOT NULL,
                        updated_at TEXT NOT NULL
                    )
                ''')
            
            # 创建配置元数据表
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS config_metadata (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
            ''')
            
            conn.commit()
            conn.close()
        except Exception as e:
            print(f"初始化数据库失败: {e}")
            # 如果初始化失败，尝试删除损坏的数据库文件
            try:
                import os
                if os.path.exists(self.config_db):
                    os.remove(self.config_db)
                    print("🗑️ 已删除损坏的数据库文件，将重新创建")
                    # 递归调用重新初始化
                    self.init_database()
            except Exception as cleanup_error:
                print(f"清理数据库文件失败: {cleanup_error}")
    
    def load_saved_config(self):
        """从SQLite数据库加载保存的配置"""
        try:
            if not os.path.exists(self.config_db):
                return None
                
            conn = sqlite3.connect(self.config_db, timeout=10.0)
            cursor = conn.cursor()
            
            # 查询所有设备配置
            cursor.execute('''
                SELECT device_id, ports, port, name, icon, array_size, com_ports, device_type 
                FROM device_configs
            ''')
            rows = cursor.fetchall()
            
            config_data = {}
            for row in rows:
                device_id, ports_str, port, name, icon, array_size, com_ports, device_type = row
                
                # 解析端口列表
                import json
                try:
                    ports_list = json.loads(ports_str)
                except:
                    ports_list = [port] if port else []
                
                config_data[device_id] = {
                    'ports': ports_list,
                    'port': port,
                    'name': name,
                    'icon': icon,
                    'array_size': array_size,
                    'com_ports': com_ports,
                    'device_type': device_type
                }
            
            conn.close()
            
            # 验证配置数据的有效性
            if config_data and self.validate_config_data(config_data):
                return config_data
                
        except Exception as e:
            print(f"从数据库加载配置失败: {e}")
        return None
    
    def validate_config_data(self, config_data):
        """验证配置数据的有效性"""
        try:
            if not isinstance(config_data, dict):
                return False
            for device_id, config in config_data.items():
                required_keys = ['name', 'icon', 'array_size']
                if not all(key in config for key in required_keys):
                    return False
                
                # 检查端口配置
                if 'ports' not in config and 'port' not in config:
                    return False
                
                # 检查设备类型是否存在（允许隐藏的设备类型）
                if device_id not in self.device_types:
                    # 允许已隐藏的设备类型
                    hidden_types = ['walkway', 'walkway_triple']
                    if device_id not in hidden_types:
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
                    device_row = self.device_rows[device_id]
                    device_name = config['name']
                    ports = config.get('ports', [])
                    
                    # 处理多端口配置
                    for port_index, port_var in enumerate(device_row['port_vars']):
                        if port_index < len(ports):
                            port = ports[port_index]
                            
                            # 获取当前下拉框选项
                            current_options = list(device_row['port_combos'][port_index]['values'])
                            if not current_options:
                                current_options = [""]
                            
                            # 如果保存的端口不在当前选项中，添加它
                            if port not in current_options:
                                current_options.append(port)
                                device_row['port_combos'][port_index]['values'] = current_options
                            
                            # 设置为默认选择
                            port_var.set(port)
                            
                            # 触发端口检测
                            self.log_message(f"🔍 检测已保存的 {device_name} 端口{port_index+1} {port} 有效性...")
                            
                            def trigger_check(dev_id, p_idx, port_name, dev_name):
                                def check_validity():
                                    try:
                                        result = self.check_port_validity_1024(port_name)
                                        self.port_data_status[port_name] = result
                                        
                                        # 在主线程中更新UI
                                        def update_ui():
                                            self.update_device_status_display(dev_id)
                                            self.update_ports_display()
                                            self.log_message(f"✅ {dev_name} 端口{p_idx+1} {port_name} 检测完成: {result}")
                                        
                                        try:
                                            self.dialog.after(0, update_ui)
                                        except:
                                            pass
                                            
                                    except Exception as e:
                                        error_result = f"❌ 检测失败: {str(e)[:20]}..."
                                        self.port_data_status[port_name] = error_result
                                        
                                        def update_error():
                                            self.update_device_status_display(dev_id)
                                            self.log_message(f"❌ {dev_name} 端口{p_idx+1} {port_name} 检测失败: {str(e)}")
                                        
                                        try:
                                            self.dialog.after(0, update_error)
                                        except:
                                            pass
                                
                                # 启动检测线程
                                check_thread = threading.Thread(target=check_validity, daemon=True)
                                check_thread.start()
                            
                            # 延迟触发检测（避免UI阻塞）
                            delay = 100 + port_index * 50  # 为每个端口错开检测时间
                            self.dialog.after(delay, lambda d=device_id, i=port_index, p=port, n=device_name: trigger_check(d, i, p, n))
                    
                    # 设置检测中状态
                    device_row['status_label'].config(text="🔍 检测中...", foreground="blue")
                    
                    configured_count += 1
                    if len(ports) > 1:
                        port_desc = f"{ports[0]}...({len(ports)}端口)"
                    else:
                        port_desc = ports[0] if ports else "未知"
                    port_list.append(f"{config['icon']} {device_name}: {port_desc}")
            
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
        """保存配置到SQLite数据库"""
        try:
            conn = sqlite3.connect(self.config_db, timeout=10.0)
            cursor = conn.cursor()
            
            # 清空现有配置
            cursor.execute('DELETE FROM device_configs')
            
            # 插入新配置
            current_time = datetime.now().isoformat()
            import json
            
            for device_id, config in config_data.items():
                # 准备端口数据
                ports_list = config.get('ports', [])
                if not ports_list and config.get('port'):
                    ports_list = [config['port']]
                
                ports_json = json.dumps(ports_list)
                single_port = ports_list[0] if len(ports_list) == 1 else None
                
                cursor.execute('''
                    INSERT INTO device_configs 
                    (device_id, ports, port, name, icon, array_size, com_ports, device_type, created_at, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    device_id,
                    ports_json,
                    single_port,
                    config['name'],
                    config['icon'],
                    config['array_size'],
                    config.get('com_ports', 1),
                    config.get('device_type', 'single'),
                    current_time,
                    current_time
                ))
            
            # 更新元数据
            cursor.execute('''
                INSERT OR REPLACE INTO config_metadata (key, value, updated_at)
                VALUES (?, ?, ?)
            ''', ('last_save_timestamp', current_time, current_time))
            
            conn.commit()
            conn.close()
            
            print(f"配置已保存到数据库: {self.config_db}")
            return True
        except Exception as e:
            print(f"保存配置到数据库失败: {e}")
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
        
        ttk.Label(header_frame, text="设备类型", width=18, font=("Arial", 10, "bold")).grid(row=0, column=0, padx=5)
        ttk.Label(header_frame, text="阵列/端口", width=12, font=("Arial", 10, "bold")).grid(row=0, column=1, padx=5)
        ttk.Label(header_frame, text="COM端口配置", width=25, font=("Arial", 10, "bold")).grid(row=0, column=2, padx=5)
        ttk.Label(header_frame, text="状态", width=15, font=("Arial", 10, "bold")).grid(row=0, column=3, padx=5)
        
        # 设备配置行
        self.device_rows = {}
        for i, (device_id, device_info) in enumerate(self.device_types.items()):
            row_frame = ttk.Frame(table_frame)
            row_frame.pack(fill=tk.X, pady=2)
            
            # 设备类型
            device_label = ttk.Label(row_frame, 
                                   text=f"{device_info['icon']} {device_info['name']}", 
                                   width=18)
            device_label.grid(row=0, column=0, padx=5)
            
            # 阵列大小和端口数
            size_info = f"{device_info['array_size']}\n({device_info['com_ports']}端口)"
            size_label = ttk.Label(row_frame, text=size_info, width=12, font=("Arial", 9))
            size_label.grid(row=0, column=1, padx=5)
            
            # COM端口配置
            ports_frame = ttk.Frame(row_frame)
            ports_frame.grid(row=0, column=2, padx=5)
            
            port_vars = []
            port_combos = []
            
            # 根据端口数创建相应的下拉框
            for port_idx in range(device_info['com_ports']):
                if device_info['com_ports'] > 1:
                    # 多端口设备，显示端口标签
                    port_label = ttk.Label(ports_frame, text=f"端口{port_idx+1}:", font=("Arial", 8))
                    port_label.grid(row=port_idx, column=0, sticky="w", padx=(0, 2))
                    
                    port_var = tk.StringVar()
                    port_combo = ttk.Combobox(ports_frame, textvariable=port_var, width=12, state="readonly")
                    port_combo.grid(row=port_idx, column=1, padx=2, pady=1)
                else:
                    # 单端口设备
                    port_var = tk.StringVar()
                    port_combo = ttk.Combobox(ports_frame, textvariable=port_var, width=18, state="readonly")
                    port_combo.grid(row=0, column=0)
                
                port_vars.append(port_var)
                port_combos.append(port_combo)
                
                # 绑定选择事件
                port_combo.bind('<<ComboboxSelected>>', 
                               lambda e, dev_id=device_id, p_idx=port_idx: self.on_port_selected(dev_id, p_idx))
            
            # 状态显示
            status_label = ttk.Label(row_frame, text="未配置", width=15, foreground="gray")
            status_label.grid(row=0, column=3, padx=5)
            
            # 存储控件引用
            self.device_rows[device_id] = {
                'port_vars': port_vars,
                'port_combos': port_combos,
                'status_label': status_label,
                'com_ports': device_info['com_ports']
            }
    
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
        # 如果端口在跳过列表中，直接返回使用中状态
        if port_name in self.skip_port_detection:
            return "⚠️ 端口使用中（主程序占用）"
            
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
                # 端口被占用可能是正常的（主程序正在使用）
                return "⚠️ 端口使用中（可能正常）"
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
                    elif "⚠️ 端口使用中" in status:
                        if "主程序占用" in status:
                            simple_status = "使用中"
                        else:
                            simple_status = "占用"
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
                    # 更新所有端口下拉框的选项
                    for port_combo in row['port_combos']:
                        port_combo['values'] = port_options
                    
                    # 检查当前选择的端口是否仍然可用
                    has_missing_ports = False
                    for port_var in row['port_vars']:
                        current_value = port_var.get()
                        if current_value and current_value not in self.available_ports:
                            port_var.set("")  # 清空丢失的端口
                            has_missing_ports = True
                    
                    # 更新设备状态显示
                    if has_missing_ports:
                        row['status_label'].config(text="端口丢失", foreground="red")
                    else:
                        self.update_device_status_display(device_id)
                        
            else:
                self.scan_status_label.config(text="❌ 未发现COM端口", foreground="red")
                self.ports_list_label.config(text="发现的端口: 无")
                
                # 清空所有端口选项
                for device_id, row in self.device_rows.items():
                    for port_combo in row['port_combos']:
                        port_combo['values'] = [""]
                    for port_var in row['port_vars']:
                        port_var.set("")
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
            elif "⚠️ 端口使用中" in data_status:
                if "主程序占用" in data_status:
                    status_label.config(text="✅ 使用中", foreground="green")
                else:
                    status_label.config(text="⚠️ 使用中", foreground="orange")
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
    
    def on_port_selected(self, device_id, port_index):
        """端口选择事件 - 触发1024字节有效性检测"""
        device_row = self.device_rows[device_id]
        selected_port = device_row['port_vars'][port_index].get()
        status_label = device_row['status_label']
        device_name = self.device_types[device_id]['name'] 
        
        if selected_port:
            # 检查端口是否被其他设备占用
            self.check_and_clear_port_conflicts(device_id, port_index, selected_port)
            
            # 显示检测中状态
            status_label.config(text="🔍 检测中...", foreground="blue") 
            self.log_message(f"🔍 开始检测 {device_name} 端口{port_index+1} {selected_port} 的1024字节数据有效性...")
            
            # 在后台线程中进行有效性检测
            def check_validity():
                try:
                    result = self.check_port_validity_1024(selected_port)
                    self.port_data_status[selected_port] = result
                    
                    # 在主线程中更新UI
                    def update_ui():
                        self.update_device_status_display(device_id)
                        self.update_ports_display()
                        self.log_message(f"✅ {device_name} 端口{port_index+1} {selected_port} 检测完成: {result}")
                    
                    try:
                        self.dialog.after(0, update_ui)
                    except:
                        pass
                        
                except Exception as e:
                    error_result = f"❌ 检测失败: {str(e)[:20]}..."
                    self.port_data_status[selected_port] = error_result
                    
                    def update_error():
                        self.update_device_status_display(device_id)
                        self.log_message(f"❌ {device_name} 端口{port_index+1} {selected_port} 检测失败: {str(e)}")
                    
                    try:
                        self.dialog.after(0, update_error)
                    except:
                        pass
            
            # 启动检测线程
            check_thread = threading.Thread(target=check_validity, daemon=True)
            check_thread.start()
            
        else:
            # 检查是否所有端口都已配置
            self.update_device_status_display(device_id)
    
    def check_and_clear_port_conflicts(self, current_device_id, current_port_index, selected_port):
        """检查并清除端口冲突"""
        for other_device_id, other_row in self.device_rows.items():
            for other_port_index, other_port_var in enumerate(other_row['port_vars']):
                # 跳过自己
                if other_device_id == current_device_id and other_port_index == current_port_index:
                    continue
                    
                if other_port_var.get() == selected_port:
                    # 清空冲突的端口配置
                    other_device_name = self.device_types[other_device_id]['name']
                    current_device_name = self.device_types[current_device_id]['name']
                    
                    other_port_var.set("")  # 清空端口选择
                    self.update_device_status_display(other_device_id)  # 重置状态
                    
                    # 记录替换日志
                    self.log_message(f"🔄 端口 {selected_port} 从 {other_device_name} 转移到 {current_device_name}")
                    return
    
    def update_device_status_display(self, device_id):
        """更新设备状态显示"""
        device_row = self.device_rows[device_id]
        status_label = device_row['status_label']
        expected_ports = device_row['com_ports']
        
        # 检查配置的端口数
        configured_ports = []
        valid_ports = 0
        invalid_ports = 0
        
        for port_var in device_row['port_vars']:
            port_name = port_var.get()
            if port_name:
                configured_ports.append(port_name)
                # 检查端口状态
                port_status = self.port_data_status.get(port_name, "未检测")
                if "✅ 1024字节有效数据" in port_status or "使用中" in port_status:
                    valid_ports += 1
                elif "❌" in port_status:
                    invalid_ports += 1
        
        configured_count = len(configured_ports)
        
        if configured_count == 0:
            status_label.config(text="未配置", foreground="gray")
        elif configured_count < expected_ports:
            status_label.config(text=f"部分配置 {configured_count}/{expected_ports}", foreground="orange")
        elif invalid_ports > 0:
            status_label.config(text=f"❌ {invalid_ports}个无效", foreground="red")
        elif valid_ports == expected_ports:
            status_label.config(text="✅ 全部有效", foreground="green")
        else:
            status_label.config(text="🔍 检测中", foreground="blue")
    
    def refresh_ports(self):
        """手动刷新端口 - 立即显示，不自动检测"""
        # 防止重复点击
        if hasattr(self, '_refreshing') and self._refreshing:
            self.log_message("⚠️ 正在刷新中，请稍候...")
            return
            
        self._refreshing = True
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
        self._refreshing = False
    
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
            # 收集该设备的所有端口配置
            device_ports = []
            for port_var in row['port_vars']:
                port_name = port_var.get()
                if port_name:
                    device_ports.append(port_name)
            
            # 检查是否有配置的端口
            if device_ports:
                expected_ports = self.device_types[device_id]['com_ports']
                
                # 对于多端口设备，检查是否配置完整
                if len(device_ports) == expected_ports:
                    config_result[device_id] = {
                        'ports': device_ports,  # 多端口配置
                        'port': device_ports[0] if len(device_ports) == 1 else None,  # 向后兼容
                        'name': self.device_types[device_id]['name'],
                        'icon': self.device_types[device_id]['icon'],
                        'array_size': self.device_types[device_id]['array_size'],
                        'com_ports': expected_ports,
                        'device_type': self.get_device_type_string(device_id, len(device_ports))
                    }
                    configured_count += 1
                elif len(device_ports) < expected_ports:
                    # 端口配置不完整
                    messagebox.showwarning("配置警告", 
                                         f"{self.device_types[device_id]['name']} 需要配置 {expected_ports} 个端口，"
                                         f"但只配置了 {len(device_ports)} 个端口！")
                    return
        
        if configured_count == 0:
            messagebox.showwarning("配置警告", "请至少配置一个设备！")
            return
        
        # 直接保存配置，无需确认对话框
        if self.save_config(config_result):
            # 简短提示保存成功
            self.scan_status_label.config(text=f"✅ 已保存 {configured_count} 个设备配置", foreground="green")
            print(f"设备配置已自动保存，包含 {configured_count} 个设备")
        else:
            messagebox.showerror("保存失败", "配置保存失败，请检查文件权限。")
            return
        
        self.result = config_result
        self.scanning = False
        try:
            if self.dialog and self.dialog.winfo_exists():
                # 延迟关闭对话框，让用户看到保存成功的提示
                self.dialog.after(800, self.dialog.destroy)
        except:
            pass
    
    def get_device_type_string(self, device_id, port_count):
        """根据设备ID和端口数量获取设备类型字符串"""
        if device_id == "walkway":
            return "walkway"  # 向后兼容
        elif device_id == "walkway_dual" or port_count == 2:
            return "dual_1024"
        elif device_id == "walkway_triple" or port_count == 3:
            return "triple_1024"
        else:
            return "single"
    
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
        
        # 为每个设备创建相应的接口
        for device_id, config in device_configs.items():
            device_name = config['name']
            com_ports = config.get('com_ports', 1)
            device_type = config.get('device_type', 'single')
            
            if com_ports == 1:
                # 单端口设备
                port_name = config.get('port') or config.get('ports', [None])[0]
                if port_name:
                    # 检查是否已经有连接到此端口的串口接口
                    existing_interface = None
                    for existing_id, interface in self.serial_interfaces.items():
                        if interface and hasattr(interface, 'get_current_port') and interface.get_current_port() == port_name:
                            existing_interface = interface
                            break
                    
                    if existing_interface:
                        # 重用已连接的接口
                        self.serial_interfaces[device_id] = existing_interface
                        print(f"重用端口 {port_name} 的现有连接 (设备: {device_name})")
                    else:
                        # 创建新的串口接口
                        serial_interface = SerialInterface(baudrate=1000000)
                        # 根据设备类型设置模式
                        if device_type == "walkway":
                            serial_interface.set_device_mode("walkway")
                        else:
                            serial_interface.set_device_mode("single")
                        self.serial_interfaces[device_id] = serial_interface
                        print(f"为 {device_name} 创建新的串口接口 (端口: {port_name})")
                else:
                    print(f"⚠️ 设备 {device_name} 缺少端口配置")
            else:
                # 多端口设备 - 使用新的透明多端口支持
                ports = config.get('ports', [])
                if len(ports) == com_ports:
                    try:
                        # 检查是否已经有现有连接到这些端口中的任何一个
                        existing_interface = None
                        existing_port = None
                        conflicting_device_id = None
                        
                        for port in ports:
                            for existing_id, interface in self.serial_interfaces.items():
                                if (interface and hasattr(interface, 'get_current_port') and 
                                    interface.get_current_port() == port):
                                    existing_interface = interface
                                    existing_port = port
                                    conflicting_device_id = existing_id
                                    print(f"发现现有连接到端口 {port} (来自设备: {existing_id})")
                                    break
                            
                            # 检查多端口接口占用的所有端口
                            for existing_id, interface in self.serial_interfaces.items():
                                if (interface and hasattr(interface, 'multi_port_config') and 
                                    interface.multi_port_config):
                                    for config in interface.multi_port_config:
                                        if config['port'] == port:
                                            existing_interface = interface
                                            existing_port = port
                                            conflicting_device_id = existing_id
                                            print(f"发现多端口接口占用端口 {port} (来自设备: {existing_id})")
                                            break
                            if existing_interface:
                                break
                        
                        if existing_interface:
                            # 如果有现有连接，需要先断开，然后创建新的多端口接口
                            conflicting_device_name = self.devices.get(conflicting_device_id, {}).get('name', '未知')
                            print(f"🔄 端口冲突: {device_name} 需要端口 {existing_port}，但被 {conflicting_device_name} 占用")
                            print(f"🔌 断开冲突设备 '{conflicting_device_name}' 的连接...")
                            
                            try:
                                existing_interface.disconnect()
                                print(f"✅ 冲突设备 '{conflicting_device_name}' 连接已断开")
                            except Exception as e:
                                print(f"⚠️ 断开冲突设备连接时出错: {e}")
                            
                            # 从现有接口映射中移除
                            if conflicting_device_id in self.serial_interfaces:
                                del self.serial_interfaces[conflicting_device_id]
                                print(f"🗑️ 移除冲突设备 '{conflicting_device_name}' 的接口映射")
                        
                        # 创建支持多端口的SerialInterface
                        serial_interface = SerialInterface(baudrate=1000000)
                        
                        # 配置多端口
                        port_configs = [{'port': ports[i], 'device_id': i} for i in range(len(ports))]
                        serial_interface.set_multi_port_config(port_configs)
                        
                        # 设置设备模式
                        serial_interface.set_device_mode(device_type)
                        
                        self.serial_interfaces[device_id] = serial_interface
                        print(f"✅ 为 {device_name} 创建多端口接口 (端口: {', '.join(ports)}, 模式: {device_type})")
                        print(f"   接口类型: {type(serial_interface).__name__}")
                        print(f"   多端口配置: {getattr(serial_interface, 'multi_port_config', None)}")
                        print(f"   预期设备帧数: {getattr(serial_interface, 'expected_device_frames', None)}")
                    except Exception as e:
                        print(f"❌ 创建多端口接口失败: {e}")
                else:
                    print(f"⚠️ 设备 {device_name} 端口配置不完整: 需要{com_ports}个，实际{len(ports)}个")
            
        # 设置默认设备
        if self.devices:
            self.current_device = list(self.devices.keys())[0]
            
    def get_device_list(self):
        """获取设备列表"""
        # 定义设备显示顺序
        device_order = ['cushion', 'footpad', 'walkway_dual', 'walkway', 'walkway_triple']
        
        # 按指定顺序返回设备列表
        result = []
        for device_id in device_order:
            if device_id in self.devices:
                config = self.devices[device_id]
                result.append((device_id, config['name'], config['icon']))
        
        # 添加任何不在预定义顺序中的设备
        for device_id, config in self.devices.items():
            if device_id not in device_order:
                result.append((device_id, config['name'], config['icon']))
        
        return result
    
    def switch_device(self, device_id):
        """切换当前设备"""
        if device_id in self.devices:
            # 先断开当前设备连接，释放COM口
            if self.current_device and self.current_device != device_id:
                old_device_name = self.devices.get(self.current_device, {}).get('name', '未知')
                new_device_name = self.devices.get(device_id, {}).get('name', '未知')
                
                # 断开旧设备的所有端口连接
                if self.current_device in self.serial_interfaces:
                    old_interface = self.serial_interfaces[self.current_device]
                    if old_interface:
                        print(f"🔌 断开旧设备 '{old_device_name}' 的连接...")
                        try:
                            # 确保完全断开连接
                            old_interface.disconnect()
                            print(f"✅ 旧设备 '{old_device_name}' 连接已断开")
                        except Exception as e:
                            print(f"⚠️ 断开旧设备连接时出错: {e}")
            
            # 切换到新设备
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
                com_ports = device_config.get('com_ports', 1)
                
                if com_ports == 1:
                    # 单端口设备
                    port_name = device_config.get('port') or device_config.get('ports', [None])[0]
                    if port_name:
                        return serial_interface.connect(port_name)
                    else:
                        print(f"❌ 设备 {device_config['name']} 缺少端口配置")
                        return False
                else:
                    # 多端口设备 - 使用透明连接方式
                    # 新的SerialInterface支持通过connect()方法透明处理多端口
                    # 只需要传入任意一个端口即可，因为多端口配置已经在setup_devices中设置
                    ports = device_config.get('ports', [])
                    if ports:
                        # 使用第一个端口作为连接入口，SerialInterface会内部处理多端口连接
                        return serial_interface.connect(ports[0])
                    else:
                        print(f"❌ 设备 {device_config['name']} 缺少端口配置")
                        return False
                        
            except Exception as e:
                print(f"连接设备失败: {e}")
                return False
        return False
    
    def disconnect_current_device(self):
        """断开当前设备"""
        if self.current_device and self.current_device in self.serial_interfaces:
            serial_interface = self.serial_interfaces[self.current_device]
            
            # 检查是单端口还是多端口接口
            if hasattr(serial_interface, 'disconnect_all'):
                # 多端口接口
                serial_interface.disconnect_all()
            else:
                # 单端口接口
                serial_interface.disconnect()
    
    def get_current_device_data(self):
        """获取当前设备的数据"""
        if self.current_device and self.current_device in self.serial_interfaces:
            serial_interface = self.serial_interfaces[self.current_device]
            device_config = self.devices[self.current_device]
            com_ports = device_config.get('com_ports', 1)
            
            if com_ports == 1:
                # 单端口设备
                return serial_interface.get_data()
            else:
                # 多端口设备
                if hasattr(serial_interface, 'get_combined_data'):
                    return serial_interface.get_combined_data()
                else:
                    return None
        return None