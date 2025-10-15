#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
患者档案管理界面
包含患者查询、新建、选择等功能
"""

import tkinter as tk
from tkinter import ttk, messagebox
from datetime import datetime
from sarcopenia_database import db
from window_manager import WindowManager, WindowLevel, setup_management_window

class PatientManagerDialog:
    """患者档案管理对话框"""
    
    def __init__(self, parent, title="患者档案管理", select_mode=False, auto_close_on_new=False):
        self.parent = parent
        self.select_mode = select_mode  # 是否为选择模式
        self.auto_close_on_new = auto_close_on_new  # 新建后是否自动关闭
        self.selected_patient = None
        self.jump_to_step = None  # 用于存储跳转到检测步骤的信息
        
        # 创建对话框窗口 - 使用窗口管理器
        self.dialog = WindowManager.create_managed_window(parent, WindowLevel.MANAGEMENT, title)
        
        # 先隐藏窗口，避免初始化时的闪烁
        self.dialog.withdraw()
        
        self.dialog.grab_set()  # 模态对话框
        self.dialog.transient(parent)
        
        # 设置图标
        try:
            self.dialog.iconbitmap("icon.ico")
        except:
            pass
        
        # 创建界面
        self.create_ui()
        
        # 加载患者数据
        self.refresh_patient_list()
        
        # 启动刷新监听
        self.start_refresh_listener()
        
        # 显示窗口（已经居中）
        self.dialog.deiconify()
        
        # 等待对话框关闭
        self.dialog.wait_window()
    
    def create_ui(self):
        """创建用户界面"""
        # 主框架
        main_frame = ttk.Frame(self.dialog, padding="10")
        main_frame.pack(fill="both", expand=True)
        
        # 顶部工具栏
        toolbar_frame = ttk.Frame(main_frame)
        toolbar_frame.pack(fill="x", pady=(0, 10))
        
        # 搜索框
        search_frame = ttk.Frame(toolbar_frame)
        search_frame.pack(side="left", fill="x", expand=True)
        
        # 患者姓名搜索
        ttk.Label(search_frame, text="🔍 搜索患者:").pack(side="left", padx=(0, 5))
        self.search_var = tk.StringVar()
        self.search_entry = ttk.Entry(search_frame, textvariable=self.search_var, width=15)
        self.search_entry.pack(side="left", padx=(0, 10))
        self.search_entry.bind('<KeyRelease>', self.on_search_change)
        
        # 日期区间搜索
        ttk.Label(search_frame, text="📅 创建时间:").pack(side="left", padx=(10, 5))
        
        date_frame = ttk.Frame(search_frame)
        date_frame.pack(side="left", padx=(0, 5))
        
        # 直接使用 tkcalendar 的 DateEntry 组件
        try:
            from tkcalendar import DateEntry
            from datetime import datetime, timedelta
            
            # 开始日期
            ttk.Label(date_frame, text="从", font=("Microsoft YaHei UI", 8)).pack(side="left", padx=(0, 2))
            self.start_date_entry = DateEntry(
                date_frame,
                width=10,
                background='darkblue',
                foreground='white', 
                borderwidth=1,
                date_pattern='yyyy-mm-dd',
                font=("Microsoft YaHei UI", 8),
                state='readonly'
            )
            self.start_date_entry.pack(side="left")
            self.start_date_entry.bind('<<DateEntrySelected>>', self.on_date_range_changed)
            
            # 到
            ttk.Label(date_frame, text="到", font=("Microsoft YaHei UI", 8)).pack(side="left", padx=(5, 2))
            self.end_date_entry = DateEntry(
                date_frame,
                width=10,
                background='darkblue',
                foreground='white', 
                borderwidth=1,
                date_pattern='yyyy-mm-dd',
                font=("Microsoft YaHei UI", 8),
                state='readonly'
            )
            self.end_date_entry.pack(side="left")
            self.end_date_entry.bind('<<DateEntrySelected>>', self.on_date_range_changed)
            
            # 默认设置为最近一周
            today = datetime.now()
            week_ago = today - timedelta(days=7)
            self.start_date_entry.set_date(week_ago)
            self.end_date_entry.set_date(today)
            
            # 快捷按钮
            quick_frame = ttk.Frame(date_frame)
            quick_frame.pack(side="left", padx=(5, 0))
            
            ttk.Button(quick_frame, text="今天", width=4, 
                      command=self.set_date_today).pack(side="left", padx=(2, 1))
            ttk.Button(quick_frame, text="本周", width=4, 
                      command=self.set_date_this_week).pack(side="left", padx=(1, 0))
            
        except ImportError:
            # 后备方案：使用普通输入框
            self.date_var = tk.StringVar()
            self.date_entry = ttk.Entry(date_frame, textvariable=self.date_var, width=12)
            self.date_entry.pack(side="left")
            self.date_entry.bind('<KeyRelease>', self.on_search_change)
            
            # 日期选择按钮（仅在后备模式下显示）
            date_btn = ttk.Button(date_frame, text="📅", width=3, command=self.show_date_picker)
            date_btn.pack(side="left", padx=(2, 0))
            
            # 清空日期按钮（仅在后备模式下显示）
            clear_date_btn = ttk.Button(date_frame, text="✖", width=3, command=self.clear_date_filter)
            clear_date_btn.pack(side="left", padx=(2, 0))
        
        # 按钮区域
        button_frame = ttk.Frame(toolbar_frame)
        button_frame.pack(side="right")
        
        # 新建患者按钮
        self.new_btn = ttk.Button(button_frame, text="➕ 新建患者", command=self.new_patient)
        self.new_btn.pack(side="left", padx=(0, 5))
        
        # 编辑按钮
        self.edit_btn = ttk.Button(button_frame, text="✏️ 编辑", command=self.edit_patient, state="disabled")
        self.edit_btn.pack(side="left", padx=(0, 5))
        
        # 删除按钮
        self.delete_btn = ttk.Button(button_frame, text="🗑️ 删除", command=self.delete_patients, state="disabled")
        self.delete_btn.pack(side="left", padx=(0, 5))
        
        # 全选/取消全选按钮
        self.select_all_btn = ttk.Button(button_frame, text="✅ 全选", command=self.toggle_select_all)
        self.select_all_btn.pack(side="left", padx=(0, 5))
        
        # 刷新按钮
        refresh_btn = ttk.Button(button_frame, text="🔄 刷新", command=self.refresh_patient_list)
        refresh_btn.pack(side="left")
        
        # 患者列表
        list_frame = ttk.LabelFrame(main_frame, text="患者档案列表", padding="5")
        list_frame.pack(fill="both", expand=True, pady=(0, 10))
        
        # 创建树状视图 - 支持多选，添加检测状态列
        columns = ("姓名", "性别", "年龄", "身高", "体重", "电话", "教育程度", "检测状态", "创建时间")
        self.patient_tree = ttk.Treeview(list_frame, columns=columns, show="headings", height=15, selectmode="extended")
        
        # 设置列标题和宽度
        column_widths = {"姓名": 120, "性别": 80, "年龄": 80, "身高": 100, "体重": 100, "电话": 140, "教育程度": 120, "检测状态": 120, "创建时间": 170}
        for col in columns:
            self.patient_tree.heading(col, text=col)
            self.patient_tree.column(col, width=column_widths.get(col, 100), minwidth=50, anchor="center")
        
        # 滚动条
        tree_scrollbar_v = ttk.Scrollbar(list_frame, orient="vertical", command=self.patient_tree.yview)
        # tree_scrollbar_h = ttk.Scrollbar(list_frame, orient="horizontal", command=self.patient_tree.xview)
        self.patient_tree.configure(yscrollcommand=tree_scrollbar_v.set)
        
        # 布局
        self.patient_tree.grid(row=0, column=0, sticky="nsew")
        tree_scrollbar_v.grid(row=0, column=1, sticky="ns")
        # tree_scrollbar_h.grid(row=1, column=0, sticky="ew")
        
        list_frame.grid_rowconfigure(0, weight=1)
        list_frame.grid_columnconfigure(0, weight=1)
        
        # 绑定选择事件
        self.patient_tree.bind("<<TreeviewSelect>>", self.on_patient_select)
        self.patient_tree.bind("<Double-1>", self.on_patient_double_click)
        
        # 绑定右键菜单
        self.patient_tree.bind("<Button-3>", self.on_patient_right_click)
        
        # 患者详情区域
        detail_frame = ttk.LabelFrame(main_frame, text="患者详情", padding="10")
        detail_frame.pack(fill="x", pady=(0, 10))
        
        self.detail_text = tk.Text(detail_frame, height=4, width=70, font=('Microsoft YaHei UI', 9),
                                  wrap=tk.WORD, relief='solid', borderwidth=1, state='disabled')
        detail_scrollbar = ttk.Scrollbar(detail_frame, orient="vertical", command=self.detail_text.yview)
        self.detail_text.configure(yscrollcommand=detail_scrollbar.set)
        
        self.detail_text.pack(side="left", fill="both", expand=True)
        detail_scrollbar.pack(side="right", fill="y")
        
        # 底部按钮区域
        bottom_frame = ttk.Frame(main_frame)
        bottom_frame.pack(fill="x")
        
        if self.select_mode:
            # 选择模式下的按钮
            cancel_btn = ttk.Button(bottom_frame, text="❌ 取消", command=self.cancel)
            cancel_btn.pack(side="right", padx=(10, 0))
            
            self.select_btn = ttk.Button(bottom_frame, text="✅ 选择此患者", command=self.select_patient, 
                                        state="disabled", style="Accent.TButton")
            self.select_btn.pack(side="right")
        else:
            # 管理模式下的按钮
            close_btn = ttk.Button(bottom_frame, text="🚪 关闭", command=self.close_dialog)
            close_btn.pack(side="right", padx=(10, 0))
            
            # 选择此患者按钮
            self.select_btn = ttk.Button(bottom_frame, text="✅ 选择此患者", command=self.select_patient, 
                                        state="disabled", style="Accent.TButton")
            self.select_btn.pack(side="right")
    
    def refresh_patient_list(self):
        """刷新患者列表"""
        # 清空现有数据
        for item in self.patient_tree.get_children():
            self.patient_tree.delete(item)
        
        # 获取患者数据
        name_keyword = self.search_var.get().strip()
        
        # 处理日期区间，兼容新的区间选择和旧的单日期选择
        start_date = None
        end_date = None
        try:
            if hasattr(self, 'start_date_entry') and hasattr(self, 'end_date_entry'):
                # 新的日期区间模式
                start_date = self.start_date_entry.get().strip()
                end_date = self.end_date_entry.get().strip()
            elif hasattr(self, 'date_entry') and hasattr(self.date_entry, 'get'):
                # 后备模式：单日期
                single_date = self.date_entry.get().strip()
                if single_date:
                    start_date = end_date = single_date
            elif hasattr(self, 'date_var'):
                # 更旧的后备模式
                single_date = self.date_var.get().strip()
                if single_date:
                    start_date = end_date = single_date
        except:
            start_date = end_date = None
        
        if name_keyword or start_date or end_date:
            patients = db.search_patients_by_date_range(
                start_date=start_date,
                end_date=end_date,
                name_filter=name_keyword if name_keyword else None
            )
        else:
            patients = db.get_all_patients()
        
        # 填充数据
        for patient in patients:
            # 获取患者最新检测状态
            latest_session = db.get_patient_latest_session(patient['id'])
            if latest_session:
                if latest_session['status'] == 'completed':
                    # 检查是否有报告文件
                    reports = db.find_session_reports(latest_session['id'])
                    if reports:
                        detection_status = "✅ 已完成(有报告)"
                    else:
                        detection_status = "⚠️ 已完成(无报告)"
                elif latest_session['status'] == 'in_progress':
                    progress = f"{latest_session['current_step']}/{latest_session['total_steps']}"
                    detection_status = f"🔄 进行中({progress})"
                elif latest_session['status'] == 'interrupted':
                    detection_status = "❌ 已中断"
                else:
                    detection_status = "⏳ 未开始"
            else:
                detection_status = "⏳ 未检测"
            
            values = (
                patient['name'],
                patient['gender'],
                f"{patient['age']}岁",
                f"{patient['height']:.1f}cm" if patient['height'] else "-",
                f"{patient['weight']:.1f}kg" if patient['weight'] else "-",
                patient['phone'] or "-",
                patient.get('education', '大学') or '大学',
                detection_status,
                patient['created_time'][:19].replace('T', ' ')
            )
            # 将patient_id存储在tags中用于后续操作
            self.patient_tree.insert("", "end", values=values, tags=(patient['id'],))
    
    def on_search_change(self, event=None):
        """搜索框内容变化事件"""
        # 延迟搜索，避免频繁查询
        if hasattr(self, '_search_after_id'):
            self.dialog.after_cancel(self._search_after_id)
        self._search_after_id = self.dialog.after(300, self.refresh_patient_list)
    
    def on_date_selected(self, event=None):
        """日期选择事件处理（后备模式）"""
        if hasattr(self, 'date_entry'):
            selected_date = self.date_entry.get()
            print(f"[DATE_DEBUG] 选择的日期: {selected_date}")
            self.refresh_patient_list()
    
    def on_date_range_changed(self, event=None):
        """日期区间变化事件处理"""
        try:
            self.refresh_patient_list()
        except Exception as e:
            print(f"日期区间变化处理错误: {e}")
    
    def set_date_today(self):
        """设置为今天"""
        from datetime import datetime
        today = datetime.now()
        self.start_date_entry.set_date(today)
        self.end_date_entry.set_date(today)
        self.refresh_patient_list()
    
    def set_date_this_week(self):
        """设置为本周（最近7天）"""
        from datetime import datetime, timedelta
        today = datetime.now()
        week_ago = today - timedelta(days=7)
        self.start_date_entry.set_date(week_ago)
        self.end_date_entry.set_date(today)
        self.refresh_patient_list()
    
    def show_date_picker(self):
        """显示日期选择器 - 使用现代化的日历组件"""
        try:
            from tkcalendar import Calendar
            import tkinter as tk
            from datetime import datetime
            
            # 创建日期选择对话框
            date_dialog = tk.Toplevel(self.dialog)
            date_dialog.title("📅 选择检测日期")
            date_dialog.geometry("350x320")
            date_dialog.resizable(False, False)
            date_dialog.transient(self.dialog)
            date_dialog.grab_set()
            
            # 居中显示
            date_dialog.geometry("+%d+%d" % (
                self.dialog.winfo_rootx() + 50,
                self.dialog.winfo_rooty() + 50
            ))
            
            # 设置图标
            try:
                date_dialog.iconbitmap("icon.ico")
            except:
                pass
            
            main_frame = ttk.Frame(date_dialog)
            main_frame.pack(fill="both", expand=True, padx=15, pady=15)
            
            # 标题
            title_label = ttk.Label(main_frame, text="请选择检测日期", 
                                   font=("Microsoft YaHei UI", 12, "bold"))
            title_label.pack(pady=(0, 15))
            
            # 获取当前日期或已选择的日期
            current_date = datetime.now()
            if self.date_var.get():
                try:
                    current_date = datetime.strptime(self.date_var.get(), "%Y-%m-%d")
                except:
                    pass
            
            # 创建现代化日历组件
            cal = Calendar(main_frame, 
                          selectmode='day',
                          date_pattern='yyyy-mm-dd',
                          year=current_date.year,
                          month=current_date.month,
                          day=current_date.day,
                          # 美化样式
                          background="white",
                          foreground="black",
                          bordercolor="lightgray",
                          headersbackground="lightblue",
                          headersforeground="black",
                          selectbackground="blue",
                          selectforeground="white",
                          normalbackground="white",
                          normalforeground="black",
                          weekendbackground="lightgray",
                          weekendforeground="black",
                          othermonthforeground="gray",
                          othermonthbackground="white",
                          font=("Microsoft YaHei UI", 9),
                          showweeknumbers=False)
            cal.pack(pady=(0, 15))
            
            # 按钮区域
            button_frame = ttk.Frame(main_frame)
            button_frame.pack(fill="x")
            
            def confirm_date():
                """确认选择的日期"""
                selected_date = cal.get_date()
                # 转换为标准格式 yyyy-mm-dd
                try:
                    if selected_date:
                        # tkcalendar 可能返回不同格式，统一转换
                        date_obj = datetime.strptime(selected_date, cal.date_pattern)
                        formatted_date = date_obj.strftime("%Y-%m-%d")
                        self.date_var.set(formatted_date)
                        self.refresh_patient_list()
                        date_dialog.destroy()
                except Exception as e:
                    print(f"日期格式转换错误: {e}")
                    # 直接使用原始格式
                    self.date_var.set(selected_date)
                    self.refresh_patient_list()
                    date_dialog.destroy()
            
            def cancel_selection():
                """取消选择"""
                date_dialog.destroy()
            
            def select_today():
                """选择今天"""
                today = datetime.now()
                cal.selection_set(today)
                formatted_date = today.strftime("%Y-%m-%d")
                self.date_var.set(formatted_date)
                self.refresh_patient_list()
                date_dialog.destroy()
            
            def clear_date():
                """清空日期"""
                self.date_var.set("")
                self.refresh_patient_list()
                date_dialog.destroy()
            
            # 按钮布局
            ttk.Button(button_frame, text="📅 今天", command=select_today).pack(side="left")
            ttk.Button(button_frame, text="🗑️ 清空", command=clear_date).pack(side="left", padx=(5, 0))
            
            ttk.Button(button_frame, text="❌ 取消", command=cancel_selection).pack(side="right")
            ttk.Button(button_frame, text="✅ 确定", command=confirm_date).pack(side="right", padx=(0, 5))
            
        except ImportError:
            print("tkcalendar 模块未安装，使用简化版日期选择器")
            self._show_simple_date_picker()
        except Exception as e:
            print(f"显示日期选择器失败: {e}")
            self._show_simple_date_picker()
    
    def _show_simple_date_picker(self):
        """简化版日期选择器（后备方案）"""
        from tkinter import simpledialog
        from datetime import datetime
        
        current_date = self.date_var.get() or datetime.now().strftime("%Y-%m-%d")
        date_str = simpledialog.askstring(
            "输入日期", 
            "请输入检测日期 (格式: 2025-08-09):", 
            initialvalue=current_date
        )
        if date_str:
            self.date_var.set(date_str)
            self.refresh_patient_list()
    
    def clear_date_filter(self):
        """清空日期过滤"""
        try:
            if hasattr(self, 'start_date_entry') and hasattr(self, 'end_date_entry'):
                # 清空日期区间选择器
                self.start_date_entry.set_date(None)
                self.end_date_entry.set_date(None)
            elif hasattr(self, 'date_entry') and hasattr(self.date_entry, 'set_date'):
                # DateEntry 组件，设置为 None 清空
                self.date_entry.set_date(None)
            elif hasattr(self, 'date_var'):
                # 普通输入框
                self.date_var.set("")
        except Exception as e:
            print(f"清空日期过滤器时出错: {e}")
        
        self.refresh_patient_list()
    
    def on_patient_select(self, event=None):
        """患者选择事件"""
        selection = self.patient_tree.selection()
        
        # 更新全选按钮状态
        all_items = self.patient_tree.get_children()
        if len(selection) == len(all_items) and len(all_items) > 0:
            self.select_all_btn.config(text="❌ 取消全选")
        else:
            self.select_all_btn.config(text="✅ 全选")
        
        if selection:
            # 如果选中多个患者
            if len(selection) > 1:
                # 多选状态
                self.detail_text.config(state='normal')
                self.detail_text.delete(1.0, tk.END)
                self.detail_text.insert(1.0, f"已选择 {len(selection)} 位患者\n\n")
                
                # 显示所选患者列表
                for i, item_id in enumerate(selection, 1):
                    item = self.patient_tree.item(item_id)
                    patient_name = item['values'][0]  # 调整索引：姓名现在是第0列
                    patient_gender = item['values'][1]  # 性别现在是第1列
                    patient_age = item['values'][2]  # 年龄现在是第2列
                    self.detail_text.insert(tk.END, f"{i}. {patient_name} ({patient_gender}, {patient_age})\n")
                
                self.detail_text.config(state='disabled')
                
                # 按钮状态
                self.edit_btn.config(state="disabled")  # 多选时不能编辑
                self.delete_btn.config(state="normal", text=f"🗑️ 删除 ({len(selection)})")
                self.select_btn.config(state="disabled")  # 多选时不能选择
                self.selected_patient = None
                    
            else:
                # 单选状态
                item = self.patient_tree.item(selection[0])
                patient_id = int(item['tags'][0])  # 从tags中获取patient_id
                
                # 获取患者详细信息
                patient = db.get_patient_by_id(patient_id)
                if patient:
                    # 显示详情
                    self.show_patient_detail(patient)
                    
                    # 启用按钮
                    self.edit_btn.config(state="normal")
                    self.delete_btn.config(state="normal", text="🗑️ 删除")
                    self.select_btn.config(state="normal")
                    self.selected_patient = patient
        else:
            # 清空详情
            self.detail_text.config(state='normal')
            self.detail_text.delete(1.0, tk.END)
            self.detail_text.config(state='disabled')
            
            # 禁用按钮
            self.edit_btn.config(state="disabled")
            self.delete_btn.config(state="disabled", text="🗑️ 删除")
            self.select_btn.config(state="disabled")
            self.selected_patient = None
    
    def show_patient_detail(self, patient):
        """显示患者详情"""
        height_str = f"{patient['height']:.1f}cm" if patient['height'] else "未填写"
        weight_str = f"{patient['weight']:.1f}kg" if patient['weight'] else "未填写"
        
        # 获取检测状态详情
        latest_session = db.get_patient_latest_session(patient['id'])
        detection_status = "尚未检测"
        report_info = ""
        
        if latest_session:
            status_map = {
                'completed': '已完成',
                'in_progress': '进行中',
                'interrupted': '已中断'
            }
            detection_status = status_map.get(latest_session['status'], '未知状态')
            
            if latest_session['status'] == 'completed':
                reports = db.find_session_reports(latest_session['id'])
                if reports:
                    report_info = f" • 报告: {len(reports)}个"
                else:
                    report_info = " • 报告: 无"
            elif latest_session['status'] == 'in_progress':
                detection_status += f" ({latest_session['current_step']}/{latest_session['total_steps']})"
        
        # 简化显示内容
        detail_text = f"""基本信息: {patient['name']} ({patient['gender']}, {patient['age']}岁)
身高体重: {height_str} / {weight_str}  •  电话: {patient['phone'] or "未填写"}  •  教育程度: {patient.get('education', '大学') or '大学'}
检测状态: {detection_status}{report_info}
创建时间: {patient['created_time'][:16].replace('T', ' ')}"""
        
        if patient['notes']:
            detail_text += f"\n备注: {patient['notes'][:50]}{'...' if len(patient['notes']) > 50 else ''}"

        self.detail_text.config(state='normal')
        self.detail_text.delete(1.0, tk.END)  
        self.detail_text.insert(1.0, detail_text)
        self.detail_text.config(state='disabled')
    
    def on_patient_double_click(self, event=None):
        """患者双击事件 - 优先打开报告"""
        if self.select_mode:
            self.select_patient()
        else:
            # 检查是否有报告可以打开
            selection = self.patient_tree.selection()
            if selection:
                item = self.patient_tree.item(selection[0])
                patient_id = int(item['tags'][0])
                
                # 获取最新会话
                latest_session = db.get_patient_latest_session(patient_id)
                if latest_session and latest_session['status'] == 'completed':
                    reports = db.find_session_reports(latest_session['id'])
                    if reports:
                        # 优先选择PDF文件
                        pdf_reports = [r for r in reports if r.lower().endswith('.pdf')]
                        if pdf_reports:
                            self.open_report(pdf_reports[0])
                        else:
                            self.open_report(reports[0])
                        return
            
            # 如果没有报告，提示用户并询问是否编辑患者信息
            if messagebox.askyesno("没有报告", "该患者暂无检测报告。\n\n是否要编辑患者信息？"):
                self.edit_patient()
    
    def on_patient_right_click(self, event=None):
        """患者右键菜单事件"""
        # 获取点击的行
        item = self.patient_tree.identify_row(event.y)
        if item:
            # 选中该行
            self.patient_tree.selection_set(item)
            
            # 获取患者信息
            patient_id = int(self.patient_tree.item(item)['tags'][0])
            latest_session = db.get_patient_latest_session(patient_id)
            
            # 创建右键菜单
            context_menu = tk.Menu(self.dialog, tearoff=0)
            
            # 编辑患者信息
            context_menu.add_command(label="✏️ 编辑患者信息", command=self.edit_patient)
            
            # 如果有已完成的检测，添加查看报告选项
            if latest_session and latest_session['status'] == 'completed':
                reports = db.find_session_reports(latest_session['id'])
                if reports:
                    context_menu.add_separator()
                    # 优先选择PDF文件
                    pdf_reports = [r for r in reports if r.lower().endswith('.pdf')]
                    primary_report = pdf_reports[0] if pdf_reports else reports[0]
                    context_menu.add_command(label="📄 查看检测报告", 
                                          command=lambda: self.open_report(primary_report))
                    
                    # 如果有多个报告，添加子菜单
                    if len(reports) > 1:
                        report_submenu = tk.Menu(context_menu, tearoff=0)
                        for i, report_path in enumerate(reports):
                            report_name = f"报告 {i+1}: {report_path.split('/')[-1]}"
                            report_submenu.add_command(label=report_name,
                                                    command=lambda path=report_path: self.open_report(path))
                        context_menu.add_cascade(label="📁 所有报告", menu=report_submenu)
            
            context_menu.add_separator()
            context_menu.add_command(label="🗑️ 删除患者", command=self.delete_patients)
            
            # 显示菜单
            try:
                context_menu.tk_popup(event.x_root, event.y_root)
            finally:
                context_menu.grab_release()
    
    def open_report(self, report_path):
        """打开检测报告"""
        import os
        import webbrowser
        import subprocess
        import platform
        from tkinter import messagebox
        
        try:
            if os.path.exists(report_path):
                # 根据文件类型和操作系统选择打开方式
                file_ext = os.path.splitext(report_path)[1].lower()
                
                if file_ext == '.pdf':
                    # PDF文件使用系统默认应用程序打开
                    if platform.system() == "Windows":
                        os.startfile(report_path)
                    elif platform.system() == "Darwin":  # macOS
                        subprocess.run(['open', report_path])
                    else:  # Linux
                        subprocess.run(['xdg-open', report_path])
                    print(f"[INFO] 打开PDF报告: {report_path}")
                else:
                    # HTML文件使用浏览器打开
                    webbrowser.open(f'file:///{os.path.abspath(report_path)}')
                    print(f"[INFO] 打开HTML报告: {report_path}")
            else:
                messagebox.showerror("错误", f"报告文件不存在：\n{report_path}")
        except Exception as e:
            messagebox.showerror("错误", f"无法打开报告文件：\n{str(e)}")
            print(f"[ERROR] 打开报告失败: {e}")
    
    def new_patient(self):
        """新建患者"""
        dialog = PatientEditDialog(self.dialog, title="新建患者档案")
        if dialog.result:
            # 新建成功后清空搜索，确保能看到新记录
            try:
                self.search_var.set("")
                if hasattr(self, 'date_var'):
                    self.date_var.set("")
            except Exception:
                pass
            patient_id = db.add_patient(**dialog.result)
            if patient_id > 0:
                messagebox.showinfo("成功", f"患者档案创建成功！\n患者ID: {patient_id}")
                self.refresh_patient_list()
                # 在列表中选中新建的患者并滚动到可见
                try:
                    for item_id in self.patient_tree.get_children():
                        tags = self.patient_tree.item(item_id).get('tags', ())
                        if tags and int(tags[0]) == int(patient_id):
                            self.patient_tree.selection_set(item_id)
                            self.patient_tree.focus(item_id)
                            self.patient_tree.see(item_id)
                            break
                except Exception:
                    pass
                
                # 任何时候新建患者后都自动选择该患者
                new_patient = db.get_patient_by_id(patient_id)
                if new_patient:
                    self.selected_patient = new_patient
                    # 如果在选择模式下，直接关闭对话框
                    if self.select_mode:
                        self.dialog.destroy()
            else:
                messagebox.showerror("错误", "患者档案创建失败！")
    
    def edit_patient(self):
        """编辑患者"""
        selection = self.patient_tree.selection()
        if not selection:
            return
        
        item = self.patient_tree.item(selection[0])
        patient_id = int(item['tags'][0])  # 从tags中获取patient_id
        patient = db.get_patient_by_id(patient_id)
        
        if patient:
            dialog = PatientEditDialog(self.dialog, title="编辑患者档案", patient_data=patient)
            if dialog.result:
                success = db.update_patient(patient_id, **dialog.result)
                if success:
                    messagebox.showinfo("成功", "患者档案更新成功！")
                    self.refresh_patient_list()
                else:
                    messagebox.showerror("错误", "患者档案更新失败！")
    
    def delete_patients(self):
        """删除患者（支持批量删除）"""
        selection = self.patient_tree.selection()
        if not selection:
            return
        
        # 获取要删除的患者信息
        patients_to_delete = []
        for item_id in selection:
            item = self.patient_tree.item(item_id)
            patient_id = int(item['tags'][0])  # 从tags中获取patient_id
            patient_name = item['values'][0]  # 姓名现在是第0列
            patients_to_delete.append((patient_id, patient_name))
        
        # 确认删除
        if len(patients_to_delete) == 1:
            # 单个删除
            patient_id, patient_name = patients_to_delete[0]
            confirm_msg = f"确定要删除患者档案 [{patient_name}] 吗？\n\n⚠️ 注意：这将同时删除该患者的所有检测记录！"
        else:
            # 批量删除
            patient_names = [name for _, name in patients_to_delete]
            if len(patient_names) <= 5:
                names_list = "\n".join([f"• {name}" for name in patient_names])
            else:
                names_list = "\n".join([f"• {name}" for name in patient_names[:5]]) + f"\n• ... 等共 {len(patient_names)} 位患者"
            
            confirm_msg = f"确定要删除以下 {len(patients_to_delete)} 位患者的档案吗？\n\n{names_list}\n\n⚠️ 注意：这将同时删除这些患者的所有检测记录！"
        
        if messagebox.askyesno("确认删除", confirm_msg):
            # 执行删除
            success_count = 0
            failed_patients = []
            
            for patient_id, patient_name in patients_to_delete:
                success = db.delete_patient(patient_id)
                if success:
                    success_count += 1
                else:
                    failed_patients.append(patient_name)
            
            # 显示结果
            if failed_patients:
                failed_names = "、".join(failed_patients)
                messagebox.showwarning("部分删除失败", 
                                     f"成功删除 {success_count} 位患者档案\n"
                                     f"删除失败的患者：{failed_names}")
            else:
                if len(patients_to_delete) == 1:
                    messagebox.showinfo("删除成功", "患者档案删除成功！")
                else:
                    messagebox.showinfo("批量删除成功", f"成功删除 {success_count} 位患者档案！")
            
            # 刷新列表
            self.refresh_patient_list()
    
    def toggle_select_all(self):
        """切换全选/取消全选"""
        all_items = self.patient_tree.get_children()
        if not all_items:
            return
        
        current_selection = self.patient_tree.selection()
        
        if len(current_selection) == len(all_items):
            # 当前是全选状态，取消全选
            self.patient_tree.selection_remove(*all_items)
            self.select_all_btn.config(text="✅ 全选")
        else:
            # 当前不是全选状态，进行全选
            self.patient_tree.selection_set(all_items)
            self.select_all_btn.config(text="❌ 取消全选")
    
    def select_patient(self):
        """选择患者"""
        if self.selected_patient:
            # 检查患者是否有未完成的检测会话
            patient_id = self.selected_patient['id']
            patient_name = self.selected_patient['name']
            print(f"[SELECT_DEBUG] 开始检查患者 {patient_name} (ID: {patient_id}) 的检测会话")
            
            # 获取最新会话
            latest_session = db.get_patient_latest_session(patient_id)
            print(f"[SELECT_DEBUG] 最新会话: {latest_session}")
            
            if latest_session:
                print(f"[SELECT_DEBUG] 会话状态: {latest_session['status']}")
                if latest_session['status'] == 'in_progress':
                    print(f"[SELECT_DEBUG] 发现进行中的会话，准备显示跳转弹窗")
                else:
                    print(f"[SELECT_DEBUG] 会话状态不是in_progress，跳过跳转逻辑")
            else:
                print(f"[SELECT_DEBUG] 没有找到最新会话")
            
            if latest_session and latest_session['status'] == 'in_progress':
                # 有未完成的会话，询问是否直接跳转到检测步骤
                current_step = latest_session.get('current_step', 1)
                total_steps = latest_session.get('total_steps', 6)
                
                response = messagebox.askyesno(
                    "检测未完成",
                    f"患者 {patient_name} 有未完成的检测会话\n\n"
                    f"当前进度：{current_step}/{total_steps} 步\n\n"
                    f"是否直接跳转到第 {current_step} 步继续检测？\n"
                    f"选择'否'将选择该患者但不跳转。",
                    icon='question'
                )
                
                if response:
                    # 用户选择跳转，设置跳转信息
                    self.jump_to_step = {
                        'patient_id': patient_id,
                        'session_id': latest_session['id'],
                        'step_number': current_step,
                        'patient_name': patient_name
                    }
                    print(f"[PATIENT_SELECT] 用户选择跳转，设置jump_to_step: {self.jump_to_step}")
                    print(f"[INFO] 将跳转到患者 {patient_name} 的第 {current_step} 步检测")
                else:
                    print(f"[PATIENT_SELECT] 用户选择不跳转，继续正常选择流程")
            
            self.dialog.destroy()
    
    def check_patient_today_completed(self, patient_id: int) -> bool:
        """检查患者当日是否有已完成的检测会话"""
        from datetime import datetime
        today = datetime.now().strftime("%Y-%m-%d")
        
        # 获取患者所有会话
        sessions = db.get_patient_sessions(patient_id)
        
        for session in sessions:
            # 检查是否为当日创建且已完成的会话
            session_date = session['created_time'][:10]  # 提取日期部分
            if session_date == today and session['status'] == 'completed':
                return True
        
        return False
    
    def check_patient_today_has_records(self, patient_id: int) -> bool:
        """检查患者当日是否有任何检测记录（包括完成和未完成的）"""
        from datetime import datetime
        today = datetime.now().strftime("%Y-%m-%d")
        
        # 获取患者所有会话
        sessions = db.get_patient_sessions(patient_id)
        
        for session in sessions:
            # 检查是否为当日创建的会话
            session_date = session['created_time'][:10]  # 提取日期部分
            if session_date == today:
                return True
        
        return False
    
    def cancel(self):
        """取消选择"""
        self.selected_patient = None
        self.dialog.destroy()
    
    def start_refresh_listener(self):
        """启动刷新监听器，监听报告生成完成事件"""
        self.last_refresh_time = 0
        self.check_refresh_flag()
    
    def check_refresh_flag(self):
        """定期检查刷新标记文件"""
        try:
            import os
            import time
            refresh_flag_file = "patient_list_refresh.flag"
            
            if os.path.exists(refresh_flag_file):
                # 读取文件内容
                with open(refresh_flag_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                # 解析刷新时间
                for line in content.split('\n'):
                    if line.startswith('refresh_time:'):
                        refresh_time = float(line.split(':')[1])
                        
                        # 如果是新的刷新请求，执行刷新
                        if refresh_time > self.last_refresh_time:
                            self.last_refresh_time = refresh_time
                            self.refresh_patient_list()
                            print(f"[INFO] 检测到报告生成完成，已刷新患者列表")
                            break
            
        except Exception as e:
            # 静默处理错误，避免影响正常使用
            pass
        
        # 如果对话框还存在，继续监听（每2秒检查一次）
        if self.dialog.winfo_exists():
            self.dialog.after(2000, self.check_refresh_flag)
    
    def close_dialog(self):
        """关闭对话框"""
        self.dialog.destroy()


class PatientEditDialog:
    """患者编辑对话框"""
    
    def __init__(self, parent, title="患者档案", patient_data=None):
        self.result = None
        self.patient_data = patient_data or {}
        
        # 使用窗口管理器创建对话框（小窗口）
        self.dialog = WindowManager.create_managed_window(parent, WindowLevel.DIALOG, 
                                                        title, (700, 800))
        self.dialog.grab_set()  # 模态对话框
        self.dialog.transient(parent)
        
        # 设置图标
        try:
            self.dialog.iconbitmap("icon.ico")
        except:
            pass

        self.base_font_size = 10
        self.base_padding = 10
        self.notes_height = 3
        # 创建界面
        self.create_ui()
        
        # 等待对话框关闭
        self.dialog.wait_window()
    
    def update_layout(self, event=None):
        """根据窗口尺寸动态调整字体、间距和控件高度"""
        # 柔性防护：窗口可能在关闭过程中触发该回调
        try:
            if not self.dialog or not self.dialog.winfo_exists():
                return
            width = max(self.dialog.winfo_width(), 300)  # 防止过小
            height = max(self.dialog.winfo_height(), 350)  # 防止过小
        except Exception:
            return
        
        # 计算缩放因子，基于基准分辨率 400x500
        scale_factor = min(width / 400, height / 500, 1.5)
        self.base_font_size = max(6, int(9 * scale_factor))  # 最小字体6
        self.base_padding = max(3, int(10 * scale_factor))   # 最小间距3
        self.notes_height = max(1, int(3 * scale_factor))    # 备注高度动态调整
        
        # 更新样式
        style = ttk.Style()
        style.configure('Title.TLabel', font=('Microsoft YaHei UI', int(self.base_font_size * 1.3), 'bold'))
        style.configure('Section.TLabelframe.Label', font=('Microsoft YaHei UI', self.base_font_size, 'bold'))
        
        # 更新动态控件
        for widget in self.dynamic_widgets:
            if isinstance(widget, ttk.Label):
                widget.configure(font=('Microsoft YaHei UI', self.base_font_size))
            elif isinstance(widget, (ttk.Entry, ttk.Combobox)):
                widget.configure(font=('Microsoft YaHei UI', self.base_font_size))
            elif isinstance(widget, tk.Text):
                widget.configure(font=('Microsoft YaHei UI', self.base_font_size), height=self.notes_height)
            elif isinstance(widget, (ttk.Frame, ttk.LabelFrame)):
                widget.configure(padding=int(self.base_padding * 0.6))
        
        # 动态隐藏提示文本（在高度 < 400 时）
        if height < 400:
            if hasattr(self, 'tip_label'):
                self.tip_label.pack_forget()
            if hasattr(self, 'help_label'):
                self.help_label.pack_forget()
        else:
            if hasattr(self, 'tip_label'):
                self.tip_label.pack(anchor="w")
            if hasattr(self, 'help_label'):
                self.help_label.pack(anchor="w", pady=(3, 0))
                
    def create_ui(self):
        """创建用户界面"""
        # 设置最小窗口尺寸
        self.dialog.minsize(300, 350)
        
        # 存储动态控件
        self.dynamic_widgets = []
        
        # 主框架
        main_frame = ttk.Frame(self.dialog, padding=self.base_padding)
        main_frame.pack(fill="both", expand=True)
        self.dynamic_widgets.append(main_frame)
        
        # 绑定窗口大小变化
        self.dialog.bind('<Configure>', self.update_layout)
        
        # 标题区域
        title_frame = ttk.Frame(main_frame)
        title_frame.pack(fill="x", pady=(0, self.base_padding * 0.6))
        self.dynamic_widgets.append(title_frame)
        
        title_label = ttk.Label(title_frame, text="🏥 患者档案信息", style='Title.TLabel')
        title_label.pack()
        self.dynamic_widgets.append(title_label)
        
        subtitle_label = ttk.Label(title_frame, text="请填写患者的基本信息", 
                                 font=('Microsoft YaHei UI', self.base_font_size - 2), 
                                 foreground='#666666')
        subtitle_label.pack(pady=(2, 0))
        self.dynamic_widgets.append(subtitle_label)
        
        # 基本信息区域
        info_frame = ttk.LabelFrame(main_frame, text=" 📋 基本信息 ", 
                                   style='Section.TLabelframe', padding=self.base_padding * 0.6)
        info_frame.pack(fill="x", pady=(0, self.base_padding * 0.6))
        self.dynamic_widgets.append(info_frame)
        
        # 第一行：姓名和性别
        row1_frame = ttk.Frame(info_frame)
        row1_frame.pack(fill="x", pady=(0, self.base_padding * 0.4))
        self.dynamic_widgets.append(row1_frame)
        
        # 姓名
        name_frame = ttk.Frame(row1_frame)
        name_frame.pack(side="left", fill="x", expand=True, padx=(0, self.base_padding * 0.4))
        self.dynamic_widgets.append(name_frame)
        
        ttk.Label(name_frame, text="患者姓名 *", font=('Microsoft YaHei UI', self.base_font_size, 'bold')).pack(anchor="w")
        self.name_var = tk.StringVar(value=self.patient_data.get('name', ''))
        name_entry = ttk.Entry(name_frame, textvariable=self.name_var, font=('Microsoft YaHei UI', self.base_font_size))
        name_entry.pack(fill="x", pady=(2, 0))
        name_entry.focus()
        self.dynamic_widgets.append(name_entry)
        
        # 性别
        gender_frame = ttk.Frame(row1_frame)
        gender_frame.pack(side="right", fill="x", expand=True, padx=(self.base_padding * 0.4, 0))
        self.dynamic_widgets.append(gender_frame)
        
        ttk.Label(gender_frame, text="性别 *", font=('Microsoft YaHei UI', self.base_font_size, 'bold')).pack(anchor="w")
        self.gender_var = tk.StringVar(value=self.patient_data.get('gender', '男'))
        gender_combo = ttk.Combobox(gender_frame, textvariable=self.gender_var, 
                                   values=["男", "女"], font=('Microsoft YaHei UI', self.base_font_size), state="readonly")
        gender_combo.pack(fill="x", pady=(2, 0))
        self.dynamic_widgets.append(gender_combo)
        
        # 第二行：年龄和电话
        row2_frame = ttk.Frame(info_frame)
        row2_frame.pack(fill="x", pady=(0, self.base_padding * 0.4))
        self.dynamic_widgets.append(row2_frame)
        
        # 年龄
        age_frame = ttk.Frame(row2_frame)
        age_frame.pack(side="left", fill="x", expand=True, padx=(0, self.base_padding * 0.4))
        self.dynamic_widgets.append(age_frame)
        
        ttk.Label(age_frame, text="年龄 *", font=('Microsoft YaHei UI', self.base_font_size, 'bold')).pack(anchor="w")
        self.age_var = tk.StringVar(value=str(self.patient_data.get('age', '')))
        age_entry = ttk.Entry(age_frame, textvariable=self.age_var, font=('Microsoft YaHei UI', self.base_font_size))
        age_entry.pack(fill="x", pady=(2, 0))
        self.dynamic_widgets.append(age_entry)
        
        # 教育程度（新增下拉）
        edu_frame = ttk.Frame(row2_frame)
        edu_frame.pack(side="right", fill="x", expand=True, padx=(self.base_padding * 0.4, 0))
        self.dynamic_widgets.append(edu_frame)
        
        ttk.Label(edu_frame, text="受教育程度", font=('Microsoft YaHei UI', self.base_font_size)).pack(anchor="w")
        self.education_var = tk.StringVar(value=self.patient_data.get('education', '大学') or '大学')
        education_combo = ttk.Combobox(edu_frame, textvariable=self.education_var,
                                      values=["博士", "硕士", "大学", "大专", "高中", "初中", "小学"],
                                      font=('Microsoft YaHei UI', self.base_font_size), state="readonly")
        education_combo.pack(fill="x", pady=(2, 0))
        self.dynamic_widgets.append(education_combo)
        
        # 第三行：身高和体重与电话
        row3_frame = ttk.Frame(info_frame)
        row3_frame.pack(fill="x")
        self.dynamic_widgets.append(row3_frame)
        
        # 身高
        height_frame = ttk.Frame(row3_frame)
        height_frame.pack(side="left", fill="x", expand=True, padx=(0, self.base_padding * 0.4))
        self.dynamic_widgets.append(height_frame)
        
        ttk.Label(height_frame, text="身高 (cm)", font=('Microsoft YaHei UI', self.base_font_size)).pack(anchor="w")
        self.height_var = tk.StringVar(value=str(self.patient_data.get('height', '') or ''))
        height_entry = ttk.Entry(height_frame, textvariable=self.height_var, font=('Microsoft YaHei UI', self.base_font_size))
        height_entry.pack(fill="x", pady=(2, 0))
        self.dynamic_widgets.append(height_entry)
        
        # 体重
        weight_frame = ttk.Frame(row3_frame)
        weight_frame.pack(side="left", fill="x", expand=True, padx=(self.base_padding * 0.4, 0))
        self.dynamic_widgets.append(weight_frame)
        # 电话
        phone_frame = ttk.Frame(row3_frame)
        phone_frame.pack(side="right", fill="x", expand=True, padx=(self.base_padding * 0.4, 0))
        self.dynamic_widgets.append(phone_frame)
        
        ttk.Label(phone_frame, text="联系电话", font=('Microsoft YaHei UI', self.base_font_size)).pack(anchor="w")
        self.phone_var = tk.StringVar(value=self.patient_data.get('phone', '') or '')
        phone_entry = ttk.Entry(phone_frame, textvariable=self.phone_var, font=('Microsoft YaHei UI', self.base_font_size))
        phone_entry.pack(fill="x", pady=(2, 0))
        self.dynamic_widgets.append(phone_entry)
        
        ttk.Label(weight_frame, text="体重 (kg)", font=('Microsoft YaHei UI', self.base_font_size)).pack(anchor="w")
        self.weight_var = tk.StringVar(value=str(self.patient_data.get('weight', '') or ''))
        weight_entry = ttk.Entry(weight_frame, textvariable=self.weight_var, font=('Microsoft YaHei UI', self.base_font_size))
        weight_entry.pack(fill="x", pady=(2, 0))
        self.dynamic_widgets.append(weight_entry)
        
        # 备注区域
        notes_frame = ttk.LabelFrame(main_frame, text=" 📝 备注信息 ", 
                                    style='Section.TLabelframe', padding=self.base_padding * 0.6)
        notes_frame.pack(fill="x", pady=(0, self.base_padding * 0.6))
        self.dynamic_widgets.append(notes_frame)
        
        self.notes_text = tk.Text(notes_frame, height=self.notes_height, font=('Microsoft YaHei UI', self.base_font_size),
                                 wrap=tk.WORD, relief='solid', borderwidth=1,
                                 bg='#fafafa', selectbackground='#e3f2fd')
        if self.patient_data.get('notes'):
            self.notes_text.insert(1.0, self.patient_data['notes'])
        self.notes_text.pack(fill="x", expand=False)
        self.dynamic_widgets.append(self.notes_text)
        
        # 底部信息和按钮区域 - 使用 place 固定在底部
        bottom_frame = ttk.Frame(self.dialog)
        bottom_frame.place(relx=0, rely=1.0, relwidth=1.0, anchor='sw')
        self.dynamic_widgets.append(bottom_frame)
        
        # 必填项提示
        tip_frame = ttk.Frame(bottom_frame)
        tip_frame.pack(fill="x", pady=(0, self.base_padding * 0.4))
        self.dynamic_widgets.append(tip_frame)
        
        self.tip_label = ttk.Label(tip_frame, text="* 标记为必填项", 
                                  font=('Microsoft YaHei UI', self.base_font_size - 2), foreground='#d32f2f')
        self.tip_label.pack(anchor="w")
        self.dynamic_widgets.append(self.tip_label)
        
        self.help_label = ttk.Label(tip_frame, text="💡 提示：身高体重信息有助于更准确的分析结果", 
                                   font=('Microsoft YaHei UI', self.base_font_size - 2), foreground='#1976d2')
        self.help_label.pack(anchor="w", pady=(2, 0))
        self.dynamic_widgets.append(self.help_label)
        
        # 按钮区域
        button_frame = ttk.Frame(bottom_frame)
        button_frame.pack(fill="x")
        self.dynamic_widgets.append(button_frame)
        
        # 左侧状态信息
        status_frame = ttk.Frame(button_frame)
        status_frame.pack(side="left", fill="x", expand=True)
        self.dynamic_widgets.append(status_frame)
        
        status_text = (f"编辑模式 - 修改患者 {self.patient_data.get('name', '未知')} 的信息"
                      if self.patient_data else "新建模式 - 创建新的患者档案")
        status_label = ttk.Label(status_frame, text=status_text, 
                                font=('Microsoft YaHei UI', self.base_font_size - 2), foreground='#666666')
        status_label.pack(anchor="w")
        self.dynamic_widgets.append(status_label)
        
        # 右侧按钮
        btn_container = ttk.Frame(button_frame)
        btn_container.pack(side="right", pady=(self.base_padding * 0.4, 0))
        self.dynamic_widgets.append(btn_container)
        
        cancel_btn = ttk.Button(btn_container, text="❌ 取消", command=self.cancel)
        cancel_btn.pack(side="right", padx=(self.base_padding * 0.4, 0))
        
        confirm_text = "💾 保存修改" if self.patient_data else "➕ 创建档案"
        confirm_btn = ttk.Button(btn_container, text=confirm_text, command=self.confirm)
        confirm_btn.pack(side="right")
        
        # 绑定快捷键
        self.dialog.bind('<Return>', lambda e: self.confirm())
        self.dialog.bind('<Escape>', lambda e: self.cancel())
        self.dialog.bind('<Control-s>', lambda e: self.confirm())
        
        # 初始更新布局
        self.dialog.update()
        self.update_layout()
    
    def validate_input(self):
        """验证输入数据"""
        # 检查必填项
        if not self.name_var.get().strip():
            messagebox.showerror("输入错误", "请输入患者姓名")
            return False
        
        if not self.age_var.get().strip():
            messagebox.showerror("输入错误", "请输入患者年龄")
            return False
        
        # 验证年龄
        try:
            age = int(self.age_var.get())
            if age <= 0 or age > 120:
                messagebox.showerror("输入错误", "年龄应在1-120岁之间")
                return False
        except ValueError:
            messagebox.showerror("输入错误", "请输入有效的年龄数字")
            return False
        
        # 验证身高（可选）
        if self.height_var.get().strip():
            try:
                height = float(self.height_var.get())
                if height < 50 or height > 250:
                    messagebox.showerror("输入错误", "身高应在50-250cm之间")
                    return False
            except ValueError:
                messagebox.showerror("输入错误", "请输入有效的身高数字")
                return False
        
        # 验证体重（可选）
        if self.weight_var.get().strip():
            try:
                weight = float(self.weight_var.get())
                if weight < 10 or weight > 300:
                    messagebox.showerror("输入错误", "体重应在10-300kg之间")
                    return False
            except ValueError:
                messagebox.showerror("输入错误", "请输入有效的体重数字")
                return False
        
        return True
    
    def confirm(self):
        """确认按钮事件"""
        if not self.validate_input():
            return
        
        # 构建患者信息字典
        self.result = {
            'name': self.name_var.get().strip(),
            'gender': self.gender_var.get(),
            'age': int(self.age_var.get()),
            'height': float(self.height_var.get()) if self.height_var.get().strip() else None,
            'weight': float(self.weight_var.get()) if self.weight_var.get().strip() else None,
            'phone': self.phone_var.get().strip() or None,
            'education': self.education_var.get().strip() or '大学',
            'notes': self.notes_text.get(1.0, tk.END).strip() or None
        }
        
        self.dialog.destroy()
    
    def cancel(self):
        """取消按钮事件"""
        self.result = None
        self.dialog.destroy()


# 测试代码
if __name__ == "__main__":
    # 创建测试数据
    from sarcopenia_database import db
    
    root = tk.Tk()
    root.withdraw()  # 隐藏主窗口
    
    # 测试管理模式
    # manager = PatientManagerDialog(root, title="患者档案管理", select_mode=False)
    
    # 测试选择模式
    selector = PatientManagerDialog(root, title="选择患者档案", select_mode=True)
    if selector.selected_patient:
        print(f"选择的患者: {selector.selected_patient['name']}")
    else:
        print("未选择患者")
    
    root.destroy()