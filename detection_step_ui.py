#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
检测步骤界面组件
用于各个检测步骤的数据收集和界面显示
"""

import tkinter as tk
from tkinter import ttk, messagebox
import threading
import time
import os
from datetime import datetime
from sarcopenia_database import db
from window_manager import WindowManager, WindowLevel, setup_dialog

class DetectionStepDialog:
    """检测步骤对话框"""
    
    def __init__(self, parent, step_info, session_id, step_id):
        self.parent = parent
        self.step_info = step_info
        self.session_id = session_id
        self.step_id = step_id
        self.result = None
        self.is_running = False
        self.start_time = None
        self.data_file_path = None
        
        # 使用窗口管理器创建对话框（小窗口）
        self.dialog = WindowManager.create_managed_window(parent, WindowLevel.DIALOG,
                                                        f"第{step_info['number']}步：{step_info['name']}", 
                                                        (600, 500))
        self.dialog.grab_set()  # 模态对话框
        self.dialog.transient(parent)
        
        # 设置图标
        try:
            self.dialog.iconbitmap("icon.ico")
        except:
            pass
        
        # 创建界面
        self.create_ui()
        
        # 等待对话框关闭
        self.dialog.wait_window()
    
    
    def create_ui(self):
        """创建用户界面"""
        # 主框架
        main_frame = ttk.Frame(self.dialog, padding="20")
        main_frame.pack(fill="both", expand=True)
        
        # 标题区域
        title_frame = ttk.Frame(main_frame)
        title_frame.pack(fill="x", pady=(0, 20))
        
        title_label = ttk.Label(title_frame, 
                               text=f"第{self.step_info['number']}步：{self.step_info['name']}", 
                               font=('Microsoft YaHei UI', 16, 'bold'))
        title_label.pack()
        
        # 步骤信息区域
        info_frame = ttk.LabelFrame(main_frame, text="检测信息", padding="15")
        info_frame.pack(fill="x", pady=(0, 15))
        
        info_text = f"""设备类型：{self.step_info['device_type']}
检测时长：{self.step_info['duration']}秒
重复次数：{self.step_info['repetitions']}次

检测说明：
{self.step_info['description']}"""
        
        ttk.Label(info_frame, text=info_text, font=('Microsoft YaHei UI', 10), 
                 justify="left").pack(anchor="w")
        
        # 状态显示区域
        status_frame = ttk.LabelFrame(main_frame, text="检测状态", padding="15")
        status_frame.pack(fill="x", pady=(0, 15))
        
        # 状态标签
        self.status_label = ttk.Label(status_frame, text="⏸️ 准备就绪", 
                                     font=('Microsoft YaHei UI', 12, 'bold'),
                                     foreground="#2196f3")
        self.status_label.pack(pady=(0, 10))
        
        # 时间显示
        time_info_frame = ttk.Frame(status_frame)
        time_info_frame.pack(fill="x")
        
        ttk.Label(time_info_frame, text="已用时间:").pack(side="left")
        self.time_label = ttk.Label(time_info_frame, text="00:00", 
                                   font=('Microsoft YaHei UI', 11, 'bold'),
                                   foreground="#ff5722")
        self.time_label.pack(side="left", padx=(10, 20))
        
        ttk.Label(time_info_frame, text="剩余时间:").pack(side="left")
        self.remaining_label = ttk.Label(time_info_frame, 
                                        text=f"{self.step_info['duration']:02d}:{0:02d}", 
                                        font=('Microsoft YaHei UI', 11, 'bold'),
                                        foreground="#4caf50")
        self.remaining_label.pack(side="left", padx=(10, 0))
        
        # 进度条
        progress_frame = ttk.Frame(status_frame)
        progress_frame.pack(fill="x", pady=(10, 0))
        
        ttk.Label(progress_frame, text="检测进度:").pack(anchor="w")
        self.progress_bar = ttk.Progressbar(progress_frame, mode='determinate', 
                                           length=400, style="TProgressbar")
        self.progress_bar.pack(fill="x", pady=(5, 0))
        
        # 数据收集区域
        data_frame = ttk.LabelFrame(main_frame, text="数据收集", padding="15")
        data_frame.pack(fill="both", expand=True, pady=(0, 15))
        
        # 数据日志
        self.data_log = tk.Text(data_frame, height=6, width=60, 
                               font=('Consolas', 9),
                               wrap=tk.WORD, relief='solid', borderwidth=1,
                               bg='#f8f9fa', fg='#495057')
        log_scrollbar = ttk.Scrollbar(data_frame, orient="vertical", 
                                     command=self.data_log.yview)
        self.data_log.configure(yscrollcommand=log_scrollbar.set)
        
        self.data_log.pack(side="left", fill="both", expand=True)
        log_scrollbar.pack(side="right", fill="y")
        
        # 添加初始日志
        self.add_log(f"检测步骤 {self.step_info['number']} 已准备就绪")
        self.add_log(f"设备类型: {self.step_info['device_type']}")
        self.add_log("请准备开始检测...")
        
        # 按钮区域
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(fill="x")
        
        # 开始/停止按钮
        self.start_btn = ttk.Button(button_frame, text="🚀 开始检测", 
                                   command=self.start_detection,
                                   style="Success.TButton")
        self.start_btn.pack(side="left", padx=(0, 10))
        
        # 暂停/继续按钮
        self.pause_btn = ttk.Button(button_frame, text="⏸️ 暂停", 
                                   command=self.pause_detection,
                                   state="disabled")
        self.pause_btn.pack(side="left", padx=(0, 10))
        
        # 完成按钮
        self.complete_btn = ttk.Button(button_frame, text="✅ 完成", 
                                      command=self.complete_detection,
                                      state="disabled")
        self.complete_btn.pack(side="left", padx=(0, 10))
        
        # 取消按钮
        cancel_btn = ttk.Button(button_frame, text="❌ 取消", 
                               command=self.cancel_detection)
        cancel_btn.pack(side="right")
        
        # 跳过按钮
        skip_btn = ttk.Button(button_frame, text="⏭️ 跳过", 
                             command=self.skip_detection)
        skip_btn.pack(side="right", padx=(0, 10))
        
        # 绑定关闭事件
        self.dialog.protocol("WM_DELETE_WINDOW", self.on_closing)
    
    def add_log(self, message):
        """添加日志信息"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        log_message = f"[{timestamp}] {message}\n"
        
        self.data_log.insert(tk.END, log_message)
        self.data_log.see(tk.END)
        self.dialog.update_idletasks()
    
    def start_detection(self):
        """开始检测"""
        try:
            self.is_running = True
            self.start_time = datetime.now()
            
            # 更新数据库步骤状态
            db.update_test_step_status(
                self.step_id, 
                'in_progress', 
                start_time=self.start_time.isoformat()
            )
            
            # 更新界面状态
            self.status_label.config(text="🔄 检测进行中", foreground="#ff9800")
            self.start_btn.config(state="disabled")
            self.pause_btn.config(state="normal")
            self.complete_btn.config(state="normal")
            
            self.add_log("检测已开始")
            
            # 创建数据文件
            self.create_data_file()
            
            # 启动计时器
            self.start_timer()
            
        except Exception as e:
            messagebox.showerror("错误", f"开始检测失败：{e}")
            print(f"[ERROR] 开始检测失败: {e}")
    
    def pause_detection(self):
        """暂停/继续检测"""
        if self.is_running:
            self.is_running = False
            self.pause_btn.config(text="▶️ 继续")
            self.status_label.config(text="⏸️ 检测暂停", foreground="#2196f3")
            self.add_log("检测已暂停")
        else:
            self.is_running = True
            self.pause_btn.config(text="⏸️ 暂停")
            self.status_label.config(text="🔄 检测进行中", foreground="#ff9800")
            self.add_log("检测已继续")
    
    def complete_detection(self):
        """完成检测"""
        try:
            self.is_running = False
            end_time = datetime.now()
            
            # 更新数据库步骤状态
            db.update_test_step_status(
                self.step_id, 
                'completed', 
                data_file_path=self.data_file_path,
                end_time=end_time.isoformat(),
                notes=f"检测完成，用时：{(end_time - self.start_time).seconds}秒"
            )
            
            # 更新界面状态
            self.status_label.config(text="✅ 检测完成", foreground="#4caf50")
            self.progress_bar['value'] = 100
            
            self.add_log("检测已完成")
            self.add_log(f"数据文件: {self.data_file_path}")
            
            # 禁用所有控制按钮
            self.start_btn.config(state="disabled")
            self.pause_btn.config(state="disabled") 
            self.complete_btn.config(state="disabled")
            
            self.result = "completed"
            
            # 自动关闭对话框（延迟2秒）
            self.dialog.after(2000, self.dialog.destroy)
            
        except Exception as e:
            messagebox.showerror("错误", f"完成检测失败：{e}")
            print(f"[ERROR] 完成检测失败: {e}")
    
    def skip_detection(self):
        """跳过检测"""
        if messagebox.askyesno("确认跳过", "确定要跳过这个检测步骤吗？"):
            try:
                # 更新数据库步骤状态
                db.update_test_step_status(
                    self.step_id, 
                    'skipped', 
                    notes="用户选择跳过此步骤"
                )
                
                self.add_log("检测步骤已跳过")
                self.result = "skipped"
                self.dialog.destroy()
                
            except Exception as e:
                messagebox.showerror("错误", f"跳过检测失败：{e}")
                print(f"[ERROR] 跳过检测失败: {e}")
    
    def cancel_detection(self):
        """取消检测"""
        if self.is_running:
            if not messagebox.askyesno("确认取消", "检测正在进行中，确定要取消吗？"):
                return
        
        self.is_running = False
        self.result = "cancelled"
        self.dialog.destroy()
    
    def create_data_file(self):
        """创建数据文件"""
        try:
            # 创建数据目录
            data_dir = "detection_data"
            if not os.path.exists(data_dir):
                os.makedirs(data_dir)
            
            # 生成文件名
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"step_{self.step_info['number']}_{self.step_info['name']}_{timestamp}.csv"
            self.data_file_path = os.path.join(data_dir, filename)
            
            # 创建CSV文件头
            with open(self.data_file_path, 'w', encoding='utf-8') as f:
                f.write("时间戳,步骤,设备,数据类型,数值\n")
                f.write(f"{datetime.now().isoformat()},步骤{self.step_info['number']},{self.step_info['device_type']},开始,0\n")
            
            self.add_log(f"数据文件已创建: {filename}")
            
        except Exception as e:
            self.add_log(f"创建数据文件失败: {e}")
            print(f"[ERROR] 创建数据文件失败: {e}")
    
    def start_timer(self):
        """启动计时器"""
        self.update_timer()
    
    def update_timer(self):
        """更新计时器显示"""
        if not self.is_running or not self.start_time:
            if self.is_running:  # 如果还在运行，继续更新
                self.dialog.after(1000, self.update_timer)
            return
        
        try:
            # 计算已用时间
            elapsed = (datetime.now() - self.start_time).seconds
            elapsed_minutes = elapsed // 60
            elapsed_seconds = elapsed % 60
            
            # 计算剩余时间
            total_duration = self.step_info['duration']
            remaining = max(0, total_duration - elapsed)
            remaining_minutes = remaining // 60
            remaining_seconds = remaining % 60
            
            # 更新显示
            self.time_label.config(text=f"{elapsed_minutes:02d}:{elapsed_seconds:02d}")
            self.remaining_label.config(text=f"{remaining_minutes:02d}:{remaining_seconds:02d}")
            
            # 更新进度条
            if total_duration > 0:
                progress = min(100, (elapsed / total_duration) * 100)
                self.progress_bar['value'] = progress
            
            # 检查是否到时间
            if elapsed >= total_duration:
                self.add_log("检测时间已到，建议完成检测")
                self.status_label.config(text="⏰ 时间已到", foreground="#ff5722")
            
            # 继续更新
            self.dialog.after(1000, self.update_timer)
            
        except Exception as e:
            print(f"[ERROR] 更新计时器失败: {e}")
    
    def on_closing(self):
        """窗口关闭事件"""
        if self.is_running:
            if messagebox.askyesno("确认关闭", "检测正在进行中，确定要关闭吗？"):
                self.is_running = False
                self.result = "cancelled"
                self.dialog.destroy()
        else:
            self.dialog.destroy()


# 检测步骤信息配置
DETECTION_STEPS = {
    1: {
        "number": 1,
        "name": "静坐检测",
        "device_type": "坐垫",
        "duration": 10,
        "repetitions": 1,
        "description": "请患者在坐垫上保持静坐姿势，身体放松，双脚平放在地面上。\n此步骤用于测量静态坐位时的压力分布。"
    },
    2: {
        "number": 2,
        "name": "起坐测试", 
        "device_type": "坐垫",
        "duration": 30,
        "repetitions": 5,
        "description": "请患者进行5次起坐动作，从坐位到站立再到坐位。\n动作要缓慢平稳，测量动态起坐过程中的压力变化。"
    },
    3: {
        "number": 3,
        "name": "静态站立",
        "device_type": "脚垫", 
        "duration": 10,
        "repetitions": 1,
        "description": "请患者在脚垫上保持自然站立姿势，双脚分开与肩同宽。\n此步骤用于测量静态站立时的压力分布和平衡能力。"
    },
    4: {
        "number": 4,
        "name": "前后脚站立",
        "device_type": "脚垫",
        "duration": 10, 
        "repetitions": 1,
        "description": "请患者在脚垫上采用前后脚站立姿势（一脚在前，一脚在后）。\n此步骤用于测量非对称站立时的平衡控制能力。"
    },
    5: {
        "number": 5,
        "name": "双脚前后站立",
        "device_type": "脚垫",
        "duration": 10,
        "repetitions": 1, 
        "description": "请患者在脚垫上采用双脚前后站立姿势，脚跟对脚尖排列。\n此步骤用于测量更高难度的平衡控制能力。"
    },
    6: {
        "number": 6,
        "name": "4.5米步道折返",
        "device_type": "步道",
        "duration": 60,
        "repetitions": 1,
        "description": "请患者在4.5米长的步道上来回行走，保持正常步行速度。\n此步骤用于测量步态参数和行走过程中的压力分布。"
    }
}


# 测试代码
if __name__ == "__main__":
    root = tk.Tk()
    root.withdraw()  # 隐藏主窗口
    
    # 测试检测步骤对话框
    step_info = DETECTION_STEPS[1]  # 测试第一步
    dialog = DetectionStepDialog(root, step_info, session_id=1, step_id=1)
    
    print(f"检测结果: {dialog.result}")
    
    root.destroy()