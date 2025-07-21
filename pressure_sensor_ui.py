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

class PressureSensorUI:
    """主UI控制器类"""
    
    def __init__(self, root):
        self.root = root
        self.root.title("🔬 智能肌少症检测系统 - 压力传感器可视化 (模块化版本)")
        self.root.geometry("1600x1000")
        self.root.configure(bg='#f0f0f0')
        
        # 初始化模块
        self.serial_interface = SerialInterface(baudrate=1000000)
        self.data_processor = DataProcessor(array_rows=32, array_cols=32)
        self.visualizer = None  # 在UI设置后创建
        
        # 数据监控
        self.is_running = False
        self.update_thread = None
        self.data_rate = 0
        self.last_frame_count = 0
        self.last_time = time.time()
        
        # 界面设置
        self.setup_ui()
        self.setup_visualizer()
        
        # 启动更新循环
        self.start_update_loop()
        
    def setup_ui(self):
        """设置用户界面"""
        # 主框架
        main_frame = ttk.Frame(self.root)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # 顶部控制面板
        control_frame = ttk.LabelFrame(main_frame, text="🎛️ 控制面板", padding=10)
        control_frame.pack(fill=tk.X, pady=(0, 10))
        
        # 第一行：端口控制
        # COM端口选择
        ttk.Label(control_frame, text="COM端口:").grid(row=0, column=0, padx=(0, 10))
        self.port_var = tk.StringVar()
        self.port_combo = ttk.Combobox(control_frame, textvariable=self.port_var, width=15)
        self.port_combo.grid(row=0, column=1, padx=(0, 10))
        
        # 刷新端口按钮
        ttk.Button(control_frame, text="🔍 刷新端口", command=self.refresh_ports).grid(row=0, column=2, padx=(0, 10))
        
        # 自动检测端口按钮
        ttk.Button(control_frame, text="🔍 自动检测", command=self.auto_detect_port).grid(row=0, column=3, padx=(0, 20))
        
        # 连接/断开按钮
        self.connect_btn = ttk.Button(control_frame, text="🔌 连接", command=self.toggle_connection)
        self.connect_btn.grid(row=0, column=4, padx=(0, 10))
        
        # 状态标签
        self.status_label = ttk.Label(control_frame, text="⚫ 未连接", foreground="red")
        self.status_label.grid(row=0, column=5, padx=(20, 0))
        
        # 第二行：阵列配置和功能按钮
        ttk.Label(control_frame, text="阵列大小:").grid(row=1, column=0, padx=(0, 10), pady=(10, 0))
        self.array_var = tk.StringVar(value="32x32")
        array_combo = ttk.Combobox(control_frame, textvariable=self.array_var, values=["32x32", "32x64", "32x96"], width=10, state="readonly")
        array_combo.grid(row=1, column=1, padx=(0, 10), pady=(10, 0))
        array_combo.bind("<<ComboboxSelected>>", self.on_array_size_changed)
        
        ttk.Button(control_frame, text="🔄 应用配置", command=self.apply_array_config).grid(row=1, column=2, padx=(0, 10), pady=(10, 0))
        
        # JQ变换开关
        self.jq_transform_var = tk.BooleanVar(value=True)
        jq_check = ttk.Checkbutton(control_frame, text="✨ JQ数据变换", variable=self.jq_transform_var)
        jq_check.grid(row=1, column=3, padx=(0, 10), pady=(10, 0))
        
        # 保存快照按钮
        ttk.Button(control_frame, text="📸 保存快照", command=self.save_snapshot).grid(row=1, column=4, padx=(0, 10), pady=(10, 0))
        
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
        
        # 初始化端口列表并自动检测
        self.refresh_ports()
        
        # 启动时延迟自动检测可用端口
        self.root.after(1000, self.auto_detect_port)
        
    def setup_visualizer(self):
        """设置可视化模块"""
        array_info = self.data_processor.get_array_info()
        self.visualizer = HeatmapVisualizer(
            self.plot_frame, 
            array_rows=array_info['rows'], 
            array_cols=array_info['cols']
        )
        
    def refresh_ports(self):
        """刷新COM端口列表"""
        try:
            ports = self.serial_interface.get_available_ports()
            port_names = [port['device'] for port in ports]
            self.port_combo['values'] = port_names
            
            if port_names:
                if not self.port_var.get() or self.port_var.get() not in port_names:
                    self.port_combo.set(port_names[0])
                self.log_message(f"🔍 发现 {len(port_names)} 个COM端口: {', '.join(port_names)}")
            else:
                self.port_combo.set("")
                self.log_message("❌ 未发现任何COM端口")
        except Exception as e:
            self.log_message(f"❌ 刷新端口失败: {e}")
    
    def auto_detect_port(self):
        """自动检测可用的COM端口"""
        self.log_message("🔍 开始自动检测COM端口...")
        
        try:
            working_port = self.serial_interface.auto_detect_port()
            
            if working_port:
                self.port_combo.set(working_port)
                self.log_message(f"✅ 自动检测成功！找到可用端口: {working_port}")
            else:
                self.log_message("❌ 自动检测失败，未找到可用端口")
        except Exception as e:
            self.log_message(f"❌ 自动检测过程中出错: {e}")
            
    def on_array_size_changed(self, event=None):
        """阵列大小选择改变时的回调"""
        array_size = self.array_var.get()
        self.log_message(f"📐 阵列大小选择改变为: {array_size}")
        
    def apply_array_config(self):
        """应用阵列配置"""
        array_size = self.array_var.get()
        
        try:
            if array_size == "32x32":
                rows, cols = 32, 32
            elif array_size == "32x64":
                rows, cols = 32, 64
            elif array_size == "32x96":
                rows, cols = 32, 96
            else:
                self.log_message("❌ 不支持的阵列大小")
                return
            
            # 更新数据处理器
            self.data_processor.set_array_size(rows, cols)
            
            # 更新可视化器
            self.visualizer.set_array_size(rows, cols)
            
            # 更新标题
            self.plot_frame.config(text=f"📊 压力传感器热力图 ({rows}x{cols}) - JQ工业科技")
            
            self.log_message(f"✅ 阵列配置已应用: {rows}x{cols}")
            
        except Exception as e:
            self.log_message(f"❌ 应用阵列配置失败: {e}")
            
    def save_snapshot(self):
        """保存热力图快照"""
        try:
            from datetime import datetime
            filename = filedialog.asksaveasfilename(
                defaultextension=".png",
                filetypes=[("PNG图片", "*.png"), ("JPG图片", "*.jpg"), ("所有文件", "*.*")],
                initialname=f"压力传感器数据_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
            )
            
            if filename:
                if self.visualizer.save_snapshot(filename):
                    self.log_message(f"📸 快照已保存: {filename}")
                else:
                    self.log_message("❌ 保存快照失败")
        except Exception as e:
            self.log_message(f"❌ 保存快照出错: {e}")
            
    def save_log(self):
        """保存日志"""
        try:
            filename = filedialog.asksaveasfilename(
                defaultextension=".txt",
                filetypes=[("文本文件", "*.txt"), ("所有文件", "*.*")],
                initialname=f"压力传感器日志_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
            )
            
            if filename:
                with open(filename, 'w', encoding='utf-8') as f:
                    f.write(self.log_text.get("1.0", tk.END))
                self.log_message(f"💾 日志已保存: {filename}")
        except Exception as e:
            self.log_message(f"❌ 保存日志失败: {e}")
            
    def toggle_connection(self):
        """切换连接状态"""
        if not self.is_running:
            self.start_connection()
        else:
            self.stop_connection()
            
    def start_connection(self):
        """启动连接"""
        port_name = self.port_var.get()
        if not port_name:
            self.log_message("❌ 请选择COM端口")
            messagebox.showwarning("警告", "请先选择COM端口")
            return
            
        try:
            self.log_message(f"🔍 正在连接到端口 {port_name}...")
            
            # 使用串口接口模块连接
            if self.serial_interface.connect(port_name):
                self.is_running = True
                
                # 更新UI状态
                self.connect_btn.config(text="🔌 断开", state="normal")
                self.status_label.config(text="🟢 已连接", foreground="green")
                self.log_message(f"✅ 成功连接到 {port_name}")
                
                # 禁用端口选择控件
                self.port_combo.config(state="disabled")
                
            else:
                self.log_message(f"❌ 连接到端口 {port_name} 失败")
                messagebox.showerror("连接失败", f"无法连接到端口 {port_name}")
                
        except Exception as e:
            self.log_message(f"❌ 连接错误: {e}")
            messagebox.showerror("连接错误", str(e))
            
    def stop_connection(self):
        """停止连接"""
        try:
            self.is_running = False
            
            # 断开串口连接
            self.serial_interface.disconnect()
            
            # 更新UI状态
            self.connect_btn.config(text="🔌 连接", state="normal")
            self.status_label.config(text="⚫ 未连接", foreground="red")
            self.log_message("🔌 连接已断开")
            
            # 重新启用端口选择控件
            self.port_combo.config(state="normal")
            
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
                    # 只处理最新的帧，丢弃过旧的数据以减少延迟
                    frame_data = frame_data_list[-1]  # 取最新帧
                    # 使用数据处理器处理数据，传递JQ变换开关状态
                    enable_jq = self.jq_transform_var.get()
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