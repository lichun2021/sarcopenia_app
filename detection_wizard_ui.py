#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
检测向导界面组件 - 翻页式检测流程
用于6步检测流程的连续界面显示
"""

import tkinter as tk
from tkinter import ttk, messagebox
import threading
import time
import os
from datetime import datetime
from sarcopenia_database import db

class DetectionWizardDialog:
    """检测向导对话框 - 翻页式6步检测"""
    
    def __init__(self, parent, patient_info, session_info):
        # 区分UI parent和主界面对象
        if hasattr(parent, 'root'):
            # parent是主界面对象
            self.main_ui = parent
            self.parent = parent.root  # 用于创建Tkinter对话框
        else:
            # parent是Tkinter root对象
            self.parent = parent
            self.main_ui = None
        
        self.patient_info = patient_info
        self.session_info = session_info
        self.total_steps = 6
        
        # 从会话信息中恢复当前步骤
        if session_info and 'current_step' in session_info:
            # 获取会话的当前步骤
            current = session_info['current_step']
            # 获取已完成的步骤信息
            session_steps = db.get_session_steps(session_info['id'])
            
            # 找到最后一个未完成的步骤
            last_incomplete_step = 1
            for step in session_steps:
                if step['status'] != 'completed':
                    last_incomplete_step = step['step_number']
                    break
                elif step['step_number'] == self.total_steps:
                    # 所有步骤都完成了
                    last_incomplete_step = self.total_steps
            
            self.current_step = max(1, min(last_incomplete_step, self.total_steps))
            
            # 恢复已完成步骤的结果
            self.step_results = {}
            for step in session_steps:
                if step['status'] == 'completed':
                    self.step_results[step['step_number']] = {
                        'status': 'completed',
                        'data_file': step.get('data_file', ''),
                        'start_time': step.get('start_time', ''),
                        'end_time': step.get('end_time', '')
                    }
        else:
            self.current_step = 1
            self.step_results = {}
        self.is_running = False
        self.start_time = None
        self.timer_thread = None
        self.auto_finish = False
        self._recording_data = False  # CSV数据记录状态
        
        # 将自己注册到主界面作为活动检测向导
        if self.main_ui and hasattr(self.main_ui, '_active_detection_wizard'):
            self.main_ui._active_detection_wizard = self
        
        # 6步检测配置
        self.steps_config = {
            1: {
                "name": "静坐检测",
                "device": "坐垫", 
                "duration": 10,
                "auto_finish": True,
                "description": "请患者在坐垫上保持静坐姿势，身体放松，双脚平放在地面上。\n此步骤用于测量静态坐位时的压力分布。"
            },
            2: {
                "name": "起坐测试",
                "device": "坐垫",
                "duration": 30, 
                "auto_finish": True,
                "description": "请患者进行5次起坐动作，从坐位到站立再到坐位。\n动作要缓慢平稳，测量动态起坐过程中的压力变化。"
            },
            3: {
                "name": "静态站立",
                "device": "脚垫",
                "duration": 10,
                "auto_finish": True,
                "description": "请患者在脚垫上保持自然站立姿势，双脚分开与肩同宽。\n此步骤用于测量静态站立时的压力分布和平衡能力。"
            },
            4: {
                "name": "前后脚站立", 
                "device": "脚垫",
                "duration": 10,
                "auto_finish": True,
                "description": "请患者在脚垫上采用前后脚站立姿势（一脚在前，一脚在后）。\n此步骤用于测量非对称站立时的平衡控制能力。"
            },
            5: {
                "name": "双脚前后站立",
                "device": "脚垫", 
                "duration": 10,
                "auto_finish": True,
                "description": "请患者在脚垫上采用双脚前后站立姿势，脚跟对脚尖排列。\n此步骤用于测量更高难度的平衡控制能力。"
            },
            6: {
                "name": "4.5米步道折返",
                "device": "步道",
                "duration": 60,
                "auto_finish": False,
                "description": "请患者在4.5米长的步道上来回行走，保持正常步行速度。\n此步骤用于测量步态参数和行走过程中的压力分布。"
            }
        }
        
        # 创建对话框窗口 - 优化显示避免闪烁
        self.dialog = tk.Toplevel(self.parent)
        self.dialog.title(f"🔬 肌少症检测向导 - {patient_info['name']}")
        
        # 先隐藏窗口，避免初始化时的闪烁
        self.dialog.withdraw()
        
        self.dialog.geometry("800x800")  # 增加窗口高度
        self.dialog.resizable(False, False)
        self.dialog.grab_set()  # 模态对话框
        
        # 居中显示
        self.dialog.transient(self.parent)
        
        # 设置图标
        try:
            self.dialog.iconbitmap("icon.ico")
        except:
            pass
        
        # 创建界面
        self.create_ui()
        self.update_step_content()
        
        # 绑定关闭事件
        self.dialog.protocol("WM_DELETE_WINDOW", self.on_closing)
        
        # 居中显示并显示窗口
        self.center_window()
        self.dialog.deiconify()
        
        # 等待对话框关闭
        self.dialog.wait_window()
    
    def center_window(self):
        """居中显示窗口"""
        self.dialog.update_idletasks()
        screen_width = self.dialog.winfo_screenwidth()
        screen_height = self.dialog.winfo_screenheight()
        x = (screen_width - 800) // 2
        y = (screen_height - 800) // 2
        self.dialog.geometry(f"800x800+{x}+{y}")
    
    def create_ui(self):
        """创建用户界面"""
        # 主框架
        main_frame = ttk.Frame(self.dialog, padding="20")
        main_frame.pack(fill="both", expand=True)
        
        # 顶部患者信息和进度
        header_frame = ttk.Frame(main_frame)
        header_frame.pack(fill="x", pady=(0, 20))
        
        # 患者信息
        patient_label = ttk.Label(header_frame, 
                                 text=f"👤 患者: {self.patient_info['name']} ({self.patient_info['gender']}, {self.patient_info['age']}岁)",
                                 font=('Microsoft YaHei UI', 12, 'bold'))
        patient_label.pack(side="left")
        
        # 进度显示
        self.progress_label = ttk.Label(header_frame, 
                                       text=f"第 {self.current_step}/{self.total_steps} 步",
                                       font=('Microsoft YaHei UI', 14, 'bold'),
                                       foreground="#2196f3")
        self.progress_label.pack(side="right")
        
        # 进度条
        progress_frame = ttk.Frame(main_frame)
        progress_frame.pack(fill="x", pady=(0, 20))
        
        self.step_progress = ttk.Progressbar(progress_frame, mode='determinate', 
                                           length=600, style="TProgressbar")
        self.step_progress.pack(fill="x")
        self.step_progress['maximum'] = self.total_steps
        self.step_progress['value'] = self.current_step
        
        # 步骤内容区域
        content_frame = ttk.LabelFrame(main_frame, text="检测步骤", padding="20")
        content_frame.pack(fill="x", pady=(0, 15))
        
        # 步骤标题
        self.step_title = ttk.Label(content_frame, 
                                   text="",
                                   font=('Microsoft YaHei UI', 16, 'bold'))
        self.step_title.pack(pady=(0, 15))
        
        # 设备信息
        device_frame = ttk.Frame(content_frame)
        device_frame.pack(fill="x", pady=(0, 15))
        
        ttk.Label(device_frame, text="🔧 检测设备:", 
                 font=('Microsoft YaHei UI', 11, 'bold')).pack(side="left")
        self.device_label = ttk.Label(device_frame, text="", 
                                     font=('Microsoft YaHei UI', 11),
                                     foreground="#ff5722")
        self.device_label.pack(side="left", padx=(10, 0))
        
        ttk.Label(device_frame, text="⏱️ 检测时长:", 
                 font=('Microsoft YaHei UI', 11, 'bold')).pack(side="left", padx=(30, 0))
        self.duration_label = ttk.Label(device_frame, text="", 
                                       font=('Microsoft YaHei UI', 11),
                                       foreground="#4caf50")
        self.duration_label.pack(side="left", padx=(10, 0))
        
        # 检测说明
        desc_frame = ttk.LabelFrame(content_frame, text="检测说明", padding="15")
        desc_frame.pack(fill="x", pady=(0, 15))
        
        self.description_text = tk.Text(desc_frame, height=3, width=70,
                                       font=('Microsoft YaHei UI', 10),
                                       wrap=tk.WORD, relief='solid', borderwidth=1,
                                       bg='#f8f9fa', fg='#495057', state='disabled')
        self.description_text.pack(fill="x")
        
        # 状态和计时区域
        status_frame = ttk.LabelFrame(content_frame, text="检测状态", padding="15")
        status_frame.pack(fill="x", pady=(0, 15))
        
        # 状态标签
        self.status_label = ttk.Label(status_frame, text="⏸️ 等待开始", 
                                     font=('Microsoft YaHei UI', 14, 'bold'),
                                     foreground="#2196f3")
        self.status_label.pack(pady=(0, 10))
        
        # 时间显示
        time_frame = ttk.Frame(status_frame)
        time_frame.pack(fill="x")
        
        ttk.Label(time_frame, text="已用时间:", 
                 font=('Microsoft YaHei UI', 11)).pack(side="left")
        self.elapsed_label = ttk.Label(time_frame, text="00:00", 
                                      font=('Microsoft YaHei UI', 14, 'bold'),
                                      foreground="#ff5722")
        self.elapsed_label.pack(side="left", padx=(10, 30))
        
        ttk.Label(time_frame, text="剩余时间:", 
                 font=('Microsoft YaHei UI', 11)).pack(side="left")
        self.remaining_label = ttk.Label(time_frame, text="", 
                                        font=('Microsoft YaHei UI', 14, 'bold'),
                                        foreground="#4caf50")
        self.remaining_label.pack(side="left", padx=(10, 0))
        
        # 时间进度条
        self.time_progress = ttk.Progressbar(status_frame, mode='determinate', 
                                           length=500, style="TProgressbar")
        self.time_progress.pack(fill="x", pady=(10, 0))
        
        # 数据收集信息
        data_frame = ttk.LabelFrame(content_frame, text="数据记录", padding="10")
        data_frame.pack(fill="x", pady=(0, 10))
        
        self.data_info_label = ttk.Label(data_frame, 
                                        text="📊 数据记录：未开始",
                                        font=('Microsoft YaHei UI', 10))
        self.data_info_label.pack()
        
        # 底部按钮区域 - 重新布局
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(fill="x", pady=(20, 0))
        
        # 单行按钮布局
        self.prev_btn = ttk.Button(button_frame, text="◀️ 上一步", 
                                  command=self.prev_step, state="disabled")
        self.prev_btn.pack(side="left", padx=(0, 10))
        
        self.next_btn = ttk.Button(button_frame, text="下一步 ▶️", 
                                  command=self.next_step, state="disabled")
        self.next_btn.pack(side="left", padx=(0, 50))  # 增加间距
        
        # 右侧按钮组
        self.start_btn = ttk.Button(button_frame, text="🚀 开始检测", 
                                   command=self.start_current_step,
                                   style="Success.TButton")
        self.start_btn.pack(side="right", padx=(10, 0))
        
        self.finish_btn = ttk.Button(button_frame, text="✅ 完成此步", 
                                    command=self.finish_current_step,
                                    state="disabled")
        self.finish_btn.pack(side="right")
    
    def update_step_content(self):
        """更新当前步骤的内容显示"""
        step_config = self.steps_config[self.current_step]
        
        # 更新进度标签
        self.progress_label.config(text=f"第 {self.current_step}/{self.total_steps} 步")
        self.step_progress['value'] = self.current_step
        
        # 更新步骤标题
        self.step_title.config(text=f"第{self.current_step}步：{step_config['name']}")
        
        # 更新设备和时长信息
        self.device_label.config(text=step_config['device'])
        self.duration_label.config(text=f"{step_config['duration']}秒")
        
        # 更新描述
        self.description_text.config(state='normal')
        self.description_text.delete(1.0, tk.END)
        self.description_text.insert(1.0, step_config['description'])
        self.description_text.config(state='disabled')
        
        # 重置状态
        self.status_label.config(text="⏸️ 等待开始", foreground="#2196f3")
        self.elapsed_label.config(text="00:00")
        self.remaining_label.config(text=f"{step_config['duration']//60:02d}:{step_config['duration']%60:02d}")
        self.time_progress['maximum'] = step_config['duration']
        self.time_progress['value'] = 0
        self.data_info_label.config(text="📊 数据记录：未开始")
        
        # 更新按钮状态
        self.prev_btn.config(state="normal" if self.current_step > 1 else "disabled")
        
        # 检查当前步骤是否已完成，决定下一步按钮状态
        if self.current_step in self.step_results and self.step_results[self.current_step]['status'] == 'completed':
            # 如果当前步骤已完成，可以进入下一步
            self.next_btn.config(state="normal" if self.current_step < self.total_steps else "disabled")
            self.start_btn.config(state="disabled", text="✅ 已完成")
            self.finish_btn.config(state="disabled")
            # 显示设备信息（已完成状态）
            current_device_type = step_config['device']
            self.device_label.config(text=f"{current_device_type} ✅", foreground="#4caf50")
        else:
            # 检查设备是否已配置
            device_configured = self.check_device_configured()
            current_device_type = step_config['device']
            
            if device_configured:
                # 设备已配置，正常状态
                self.next_btn.config(state="disabled")
                self.start_btn.config(state="normal", text="🚀 开始检测")
                self.finish_btn.config(state="disabled")
                # 更新设备标签显示配置状态
                self.device_label.config(text=f"{current_device_type} ✅", foreground="#4caf50")
            else:
                # 设备未配置，显示警告状态
                self.next_btn.config(state="disabled")
                self.start_btn.config(state="normal", text="⚠️ 需要配置设备")
                self.finish_btn.config(state="disabled")
                # 更新设备标签显示未配置状态
                self.device_label.config(text=f"{current_device_type} ❌", foreground="#f44336")
        
        # 重置运行状态
        self.is_running = False
        self.start_time = None
        self.auto_finish = step_config.get('auto_finish', False)
    
    def check_device_configured(self):
        """检查当前步骤所需设备是否已配置"""
        if not self.main_ui or not hasattr(self.main_ui, 'device_manager'):
            print(f"[INFO] 第{self.current_step}步：无法访问设备管理器，跳过设备检查")
            return True  # 如果无法访问设备管理器，则跳过检查
        
        current_device_type = self.steps_config[self.current_step]['device']
        device_manager = self.main_ui.device_manager
        
        print(f"[INFO] 第{self.current_step}步检查：需要【{current_device_type}】设备")
        
        # 设备类型映射
        device_type_mapping = {
            '坐垫': 'cushion',
            '脚垫': 'footpad', 
            '步道': 'walkway_dual'
        }
        
        required_device_key = device_type_mapping.get(current_device_type)
        if not required_device_key:
            print(f"[WARN] 第{self.current_step}步：未知设备类型 '{current_device_type}'，跳过检查")
            return True  # 未知设备类型，跳过检查
        
        # 检查设备是否已配置
        is_configured = required_device_key in device_manager.devices
        
        if is_configured:
            print(f"[INFO] 第{self.current_step}步：【{current_device_type}】设备已配置 ✅")
        else:
            print(f"[WARN] 第{self.current_step}步：【{current_device_type}】设备未配置 ❌")
        
        return is_configured
    
    def prompt_device_configuration(self):
        """提示用户配置设备"""
        current_device_type = self.steps_config[self.current_step]['device']
        
        result = messagebox.askyesno(
            "设备未配置",
            f"第{self.current_step}步检测需要使用【{current_device_type}】设备，但该设备尚未配置。\n\n"
            f"请确保：\n"
            f"1. {current_device_type}设备已正确连接到电脑\n"
            f"2. {current_device_type}设备已开机并正常工作\n\n"
            f"是否现在打开设备配置向导进行配置？\n\n"
            f"点击【是】：打开设备配置\n"
            f"点击【否】：返回检测向导"
        )
        
        if result:
            # 打开设备配置对话框
            try:
                from device_config import DeviceConfigDialog
                config_dialog = DeviceConfigDialog(self.main_ui.root)
                if config_dialog.result:
                    # 应用新的设备配置
                    self.main_ui.device_manager.setup_devices(config_dialog.result)
                    messagebox.showinfo(
                        "配置成功", 
                        f"{current_device_type}设备配置完成！\n现在可以开始检测了。"
                    )
                    return True
                else:
                    messagebox.showwarning(
                        "配置取消",
                        f"{current_device_type}设备配置被取消。\n请配置设备后再开始检测。"
                    )
                    return False
            except Exception as e:
                messagebox.showerror(
                    "配置失败",
                    f"打开设备配置时出错：{e}\n\n请手动配置设备后重试。"
                )
                return False
        return False
    
    def switch_to_required_device(self):
        """切换到当前步骤所需的设备"""
        if not self.main_ui or not hasattr(self.main_ui, 'device_manager'):
            return
        
        current_device_type = self.steps_config[self.current_step]['device']
        device_manager = self.main_ui.device_manager
        
        # 设备类型映射
        device_type_mapping = {
            '坐垫': 'cushion',
            '脚垫': 'footpad', 
            '步道': 'walkway_dual'
        }
        
        required_device_key = device_type_mapping.get(current_device_type)
        if required_device_key and required_device_key in device_manager.devices:
            # 切换到所需设备
            success = device_manager.switch_device(required_device_key)
            if success:
                print(f"[INFO] 检测向导已切换到{current_device_type}设备")
                
                # 更新主界面的串口接口
                if hasattr(self.main_ui, 'serial_interface'):
                    new_interface = device_manager.get_current_serial_interface()
                    if new_interface:
                        self.main_ui.serial_interface = new_interface
                        print(f"[INFO] 主界面串口接口已更新为{current_device_type}设备")
            else:
                print(f"[WARN] 切换到{current_device_type}设备失败")
    
    def start_current_step(self):
        """开始当前步骤"""
        try:
            # 检查设备是否已配置
            if not self.check_device_configured():
                if not self.prompt_device_configuration():
                    return  # 用户取消配置或配置失败，不开始检测
                
                # 重新检查设备是否已配置
                if not self.check_device_configured():
                    messagebox.showwarning(
                        "设备未配置",
                        f"第{self.current_step}步检测所需的【{self.steps_config[self.current_step]['device']}】设备仍未配置。\n"
                        "请先配置设备再开始检测。"
                    )
                    return
            
            # 自动切换到对应的设备
            self.switch_to_required_device()
            
            self.is_running = True
            self.start_time = datetime.now()
            
            # 更新数据库
            session_steps = db.get_session_steps(self.session_info['id'])
            step_id = None
            for step in session_steps:
                if step['step_number'] == self.current_step:
                    step_id = step['id']
                    break
            
            if step_id:
                db.update_test_step_status(
                    step_id, 
                    'in_progress', 
                    start_time=self.start_time.isoformat()
                )
            
            # 更新界面状态
            self.status_label.config(text="🔄 检测进行中", foreground="#ff9800")
            self.start_btn.config(state="disabled")
            self.finish_btn.config(state="normal")
            self.data_info_label.config(text="📊 数据记录：进行中...")
            
            # 创建数据文件
            self.create_data_file()
            
            # 告诉主界面当前步骤正在运行，需要记录数据
            self._recording_data = True
            
            # 启动计时器
            self.start_timer()
            
        except Exception as e:
            messagebox.showerror("错误", f"开始检测失败：{e}")
            print(f"[ERROR] 开始检测失败: {e}")
    
    def pause_current_step(self):
        """暂停当前步骤"""
        if self.is_running:
            self.is_running = False
            self.pause_btn.config(text="▶️ 继续")
            self.status_label.config(text="⏸️ 检测暂停", foreground="#2196f3")
            self.data_info_label.config(text="📊 数据记录：已暂停")
        else:
            self.is_running = True
            self.pause_btn.config(text="⏸️ 暂停")
            self.status_label.config(text="🔄 检测进行中", foreground="#ff9800")
            self.data_info_label.config(text="📊 数据记录：进行中...")
    
    def finish_current_step(self):
        """完成当前步骤"""
        try:
            self.is_running = False
            end_time = datetime.now()
            
            # 停止数据记录
            self._recording_data = False
            
            # 更新数据库
            session_steps = db.get_session_steps(self.session_info['id'])
            step_id = None
            for step in session_steps:
                if step['step_number'] == self.current_step:
                    step_id = step['id']
                    break
            
            if step_id:
                data_file_path = getattr(self, 'current_data_file', None)
                db.update_test_step_status(
                    step_id, 
                    'completed', 
                    data_file_path=data_file_path,
                    end_time=end_time.isoformat(),
                    notes=f"手动完成，用时：{(end_time - self.start_time).seconds}秒"
                )
            
            # 记录结果
            self.step_results[self.current_step] = {
                'status': 'completed',
                'start_time': self.start_time,
                'end_time': end_time,
                'data_file': getattr(self, 'current_data_file', None)
            }
            
            # 更新界面状态
            self.status_label.config(text="✅ 步骤完成", foreground="#4caf50")
            self.time_progress['value'] = self.time_progress['maximum']
            self.data_info_label.config(text=f"📊 数据记录：已保存 {getattr(self, 'current_data_file', 'N/A')}")
            
            # 更新按钮状态
            self.start_btn.config(state="disabled")
            self.finish_btn.config(state="disabled")
            
            # 启用下一步按钮或显示完成
            if self.current_step < self.total_steps:
                self.next_btn.config(state="normal")
                # 询问是否自动跳转到下一步
                if messagebox.askyesno("步骤完成", f"第{self.current_step}步检测完成！\n\n是否自动进入下一步？"):
                    # 延迟500ms后自动跳转到下一步
                    self.dialog.after(500, self.auto_next_step)
            else:
                messagebox.showinfo("检测完成", "🎉 所有检测步骤已完成！\n\n即将生成分析报告。")
                self.complete_all_steps()
            
        except Exception as e:
            messagebox.showerror("错误", f"完成步骤失败：{e}")
            print(f"[ERROR] 完成步骤失败: {e}")
    
    def skip_current_step(self):
        """跳过当前步骤"""
        if messagebox.askyesno("确认跳过", f"确定要跳过第{self.current_step}步检测吗？"):
            try:
                # 更新数据库
                session_steps = db.get_session_steps(self.session_info['id'])
                step_id = None
                for step in session_steps:
                    if step['step_number'] == self.current_step:
                        step_id = step['id']
                        break
                
                if step_id:
                    db.update_test_step_status(
                        step_id, 
                        'skipped', 
                        notes="用户选择跳过此步骤"
                    )
                
                # 记录结果
                self.step_results[self.current_step] = {
                    'status': 'skipped',
                    'start_time': None,
                    'end_time': None,
                    'data_file': None
                }
                
                # 停止当前计时
                self.is_running = False
                
                # 下一步或完成
                if self.current_step < self.total_steps:
                    self.next_step()
                else:
                    self.complete_all_steps()
                    
            except Exception as e:
                messagebox.showerror("错误", f"跳过步骤失败：{e}")
                print(f"[ERROR] 跳过步骤失败: {e}")
    
    def prev_step(self):
        """上一步"""
        if self.current_step > 1:
            if self.is_running:
                if not messagebox.askyesno("确认", "当前步骤正在进行中，确定要返回上一步吗？"):
                    return
                self.is_running = False
            
            old_step = self.current_step
            self.current_step -= 1
            print(f"[INFO] 步骤切换：第{old_step}步 → 第{self.current_step}步")
            self.update_step_content()
    
    def next_step(self):
        """下一步"""
        if self.current_step < self.total_steps:
            old_step = self.current_step
            self.current_step += 1
            print(f"[INFO] 步骤切换：第{old_step}步 → 第{self.current_step}步")
            self.update_step_content()
    
    def complete_all_steps(self):
        """完成所有步骤"""
        try:
            # 更新会话状态
            db.update_test_session_progress(
                self.session_info['id'], 
                self.total_steps, 
                'completed'
            )
            
            messagebox.showinfo("检测完成", 
                              f"患者 {self.patient_info['name']} 的检测已全部完成！\n\n"
                              f"完成步骤：{len([r for r in self.step_results.values() if r['status'] == 'completed'])}/{self.total_steps}\n"
                              "是否要进行AI分析并生成报告？")
            
            self.dialog.destroy()
            
        except Exception as e:
            messagebox.showerror("错误", f"完成检测失败：{e}")
            print(f"[ERROR] 完成检测失败: {e}")
    
    def exit_wizard(self):
        """退出向导"""
        if self.is_running:
            if not messagebox.askyesno("确认退出", "检测正在进行中，确定要退出吗？\n\n已完成的步骤将被保存。"):
                return
        
        try:
            # 保存当前进度
            if self.step_results:
                db.update_test_session_progress(
                    self.session_info['id'], 
                    max(self.step_results.keys()) if self.step_results else 0, 
                    'interrupted'
                )
            
            self.is_running = False
            self.dialog.destroy()
            
        except Exception as e:
            print(f"[ERROR] 退出向导失败: {e}")
            self.dialog.destroy()
    
    def create_data_file(self):
        """创建当前步骤的数据文件"""
        try:
            import csv
            
            # 创建按日期组织的数据目录
            today = datetime.now().strftime("%Y-%m-%d")
            data_dir = os.path.join("tmp", today, "detection_data")
            os.makedirs(data_dir, exist_ok=True)
            
            # 生成文件名 - 使用患者姓名
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            step_config = self.steps_config[self.current_step]
            patient_name = self.patient_info['name']
            filename = f"{patient_name}-第{self.current_step}步-{step_config['name']}-{timestamp}.csv"
            self.current_data_file = os.path.join(data_dir, filename)
            
            # 创建CSV文件并写入正确的头格式
            with open(self.current_data_file, 'w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                # 写入CSV头：time,max,timestamp,area,press,data
                writer.writerow(['time', 'max', 'timestamp', 'area', 'press', 'data'])
            
            # 初始化CSV相关变量
            self._csv_start_time = datetime.now()
            
        except Exception as e:
            print(f"[ERROR] 创建数据文件失败: {e}")
            self.current_data_file = None
    
    def write_csv_data_row(self, processed_data):
        """写入CSV数据行"""
        try:
            # 只有在记录状态且有数据文件时才写入
            if not getattr(self, '_recording_data', False):
                return
            if not hasattr(self, 'current_data_file') or not self.current_data_file:
                return
            
            import csv
            import time
            
            # 计算经过时间
            if hasattr(self, '_csv_start_time'):
                elapsed_time = (datetime.now() - self._csv_start_time).total_seconds()
            else:
                elapsed_time = 0
            
            # 提取数据
            stats = processed_data['statistics']
            matrix_data = processed_data['matrix_2d']
            frame_info = processed_data['original_frame']
            
            max_value = stats['max_value']
            # 格式化timestamp为 2025/6/17 14:43:28:219 格式
            if 'timestamp' in frame_info and frame_info['timestamp']:
                # 如果是datetime对象
                if hasattr(frame_info['timestamp'], 'strftime'):
                    timestamp = frame_info['timestamp'].strftime("%Y/%m/%d %H:%M:%S:%f")[:-3]
                else:
                    # 如果是字符串，尝试解析然后重新格式化
                    try:
                        if isinstance(frame_info['timestamp'], str):
                            # 尝试解析现有的时间戳格式
                            dt = datetime.strptime(frame_info['timestamp'], "%H:%M:%S.%f")
                            # 添加当前日期
                            dt = dt.replace(year=datetime.now().year, month=datetime.now().month, day=datetime.now().day)
                            timestamp = dt.strftime("%Y/%m/%d %H:%M:%S:%f")[:-3]
                        else:
                            timestamp = str(frame_info['timestamp'])
                    except:
                        timestamp = datetime.now().strftime("%Y/%m/%d %H:%M:%S:%f")[:-3]
            else:
                # 使用当前时间
                timestamp = datetime.now().strftime("%Y/%m/%d %H:%M:%S:%f")[:-3]
            
            area = stats.get('contact_area', 0)
            press = stats['sum_value']
            
            # 将2D矩阵转换为1D数组字符串，去掉空格
            data_array = matrix_data.flatten().tolist()
            data_str = str(data_array).replace(' ', '')
            
            # 写入CSV行
            with open(self.current_data_file, 'a', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                writer.writerow([elapsed_time, max_value, timestamp, area, press, data_str])
                
        except Exception as e:
            print(f"[ERROR] 写入CSV数据失败: {e}")
            import traceback
            traceback.print_exc()
    
    def start_timer(self):
        """启动计时器"""
        def timer_thread():
            while self.is_running and self.start_time:
                try:
                    # 计算已用时间
                    elapsed = (datetime.now() - self.start_time).seconds
                    elapsed_minutes = elapsed // 60
                    elapsed_seconds = elapsed % 60
                    
                    # 计算剩余时间
                    step_config = self.steps_config[self.current_step]
                    total_duration = step_config['duration']
                    remaining = max(0, total_duration - elapsed)
                    remaining_minutes = remaining // 60
                    remaining_seconds = remaining % 60
                    
                    # 在主线程中更新界面
                    self.dialog.after(0, lambda: self.update_timer_display(
                        elapsed_minutes, elapsed_seconds, remaining_minutes, remaining_seconds, elapsed, total_duration
                    ))
                    
                    # 检查是否到时间且需要自动结束
                    if elapsed >= total_duration and self.auto_finish:
                        self.dialog.after(0, self.auto_finish_step)
                        break
                    
                    time.sleep(1)
                    
                except Exception as e:
                    print(f"[ERROR] 计时器错误: {e}")
                    break
        
        self.timer_thread = threading.Thread(target=timer_thread, daemon=True)
        self.timer_thread.start()
    
    def update_timer_display(self, elapsed_min, elapsed_sec, remaining_min, remaining_sec, elapsed, total):
        """更新计时器显示"""
        try:
            self.elapsed_label.config(text=f"{elapsed_min:02d}:{elapsed_sec:02d}")
            self.remaining_label.config(text=f"{remaining_min:02d}:{remaining_sec:02d}")
            
            # 更新进度条
            if total > 0:
                progress = min(total, elapsed)
                self.time_progress['value'] = progress
            
            # 如果时间到了，提示
            if elapsed >= total:
                self.status_label.config(text="⏰ 时间已到", foreground="#ff5722")
                if not self.auto_finish:
                    self.data_info_label.config(text="📊 数据记录：时间已到，可手动完成")
            
        except Exception as e:
            print(f"[ERROR] 更新计时器显示失败: {e}")
    
    def auto_finish_step(self):
        """自动完成步骤（用于定时步骤）"""
        if self.is_running:
            # 直接完成当前步骤，不弹出确认对话框
            self.finish_current_step()
            
            # 如果不是最后一步，自动跳转到下一步
            if self.current_step < self.total_steps:
                # 延迟500ms后自动跳转到下一步
                self.dialog.after(500, self.auto_next_step)
    
    def auto_next_step(self):
        """自动跳转到下一步"""
        try:
            if self.current_step < self.total_steps:
                self.next_step()
        except Exception as e:
            print(f"[ERROR] 自动跳转下一步失败: {e}")
    
    def on_closing(self):
        """窗口关闭事件"""
        self.exit_wizard()


# 测试代码
if __name__ == "__main__":
    from sarcopenia_database import db
    
    root = tk.Tk()
    root.withdraw()  # 隐藏主窗口
    
    # 测试数据
    patient_info = {
        'id': 1,
        'name': '测试患者',
        'gender': '男',
        'age': 65
    }
    
    session_info = {
        'id': 1,
        'name': '测试会话'
    }
    
    # 创建检测向导
    wizard = DetectionWizardDialog(root, patient_info, session_info)
    
    root.destroy()