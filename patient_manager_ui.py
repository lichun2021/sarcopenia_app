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

class PatientManagerDialog:
    """患者档案管理对话框"""
    
    def __init__(self, parent, title="患者档案管理", select_mode=False):
        self.parent = parent
        self.select_mode = select_mode  # 是否为选择模式
        self.selected_patient = None
        
        # 创建对话框窗口
        self.dialog = tk.Toplevel(parent)
        self.dialog.title(f"👥 {title}")
        self.dialog.geometry("800x600")
        self.dialog.resizable(True, True)
        self.dialog.grab_set()  # 模态对话框
        
        # 居中显示
        self.dialog.transient(parent)
        self.center_window()
        
        # 设置图标
        try:
            self.dialog.iconbitmap("icon.ico")
        except:
            pass
        
        # 创建界面
        self.create_ui()
        
        # 加载患者数据
        self.refresh_patient_list()
        
        # 等待对话框关闭
        self.dialog.wait_window()
    
    def center_window(self):
        """居中显示窗口"""
        self.dialog.update_idletasks()
        screen_width = self.dialog.winfo_screenwidth()
        screen_height = self.dialog.winfo_screenheight()
        x = (screen_width - 800) // 2
        y = (screen_height - 600) // 2
        self.dialog.geometry(f"800x600+{x}+{y}")
    
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
        
        ttk.Label(search_frame, text="🔍 搜索患者:").pack(side="left", padx=(0, 5))
        self.search_var = tk.StringVar()
        self.search_entry = ttk.Entry(search_frame, textvariable=self.search_var, width=20)
        self.search_entry.pack(side="left", padx=(0, 10))
        self.search_entry.bind('<KeyRelease>', self.on_search_change)
        
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
        list_frame = ttk.LabelFrame(main_frame, text="患者档案列表 (支持多选：Ctrl+点击 或 Shift+点击)", padding="5")
        list_frame.pack(fill="both", expand=True, pady=(0, 10))
        
        # 创建树状视图 - 支持多选
        columns = ("ID", "姓名", "性别", "年龄", "身高", "体重", "电话", "创建时间")
        self.patient_tree = ttk.Treeview(list_frame, columns=columns, show="headings", height=15, selectmode="extended")
        
        # 设置列标题和宽度
        column_widths = {"ID": 50, "姓名": 100, "性别": 60, "年龄": 60, "身高": 80, "体重": 80, "电话": 120, "创建时间": 150}
        for col in columns:
            self.patient_tree.heading(col, text=col)
            self.patient_tree.column(col, width=column_widths.get(col, 100), minwidth=50)
        
        # 滚动条
        tree_scrollbar_v = ttk.Scrollbar(list_frame, orient="vertical", command=self.patient_tree.yview)
        tree_scrollbar_h = ttk.Scrollbar(list_frame, orient="horizontal", command=self.patient_tree.xview)
        self.patient_tree.configure(yscrollcommand=tree_scrollbar_v.set, xscrollcommand=tree_scrollbar_h.set)
        
        # 布局
        self.patient_tree.grid(row=0, column=0, sticky="nsew")
        tree_scrollbar_v.grid(row=0, column=1, sticky="ns")
        tree_scrollbar_h.grid(row=1, column=0, sticky="ew")
        
        list_frame.grid_rowconfigure(0, weight=1)
        list_frame.grid_columnconfigure(0, weight=1)
        
        # 绑定选择事件
        self.patient_tree.bind("<<TreeviewSelect>>", self.on_patient_select)
        self.patient_tree.bind("<Double-1>", self.on_patient_double_click)
        
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
            close_btn.pack(side="right")
    
    def refresh_patient_list(self):
        """刷新患者列表"""
        # 清空现有数据
        for item in self.patient_tree.get_children():
            self.patient_tree.delete(item)
        
        # 获取患者数据
        keyword = self.search_var.get().strip()
        if keyword:
            patients = db.search_patients(keyword)
        else:
            patients = db.get_all_patients()
        
        # 填充数据
        for patient in patients:
            values = (
                patient['id'],
                patient['name'],
                patient['gender'],
                f"{patient['age']}岁",
                f"{patient['height']:.1f}cm" if patient['height'] else "-",
                f"{patient['weight']:.1f}kg" if patient['weight'] else "-",
                patient['phone'] or "-",
                patient['created_time'][:19].replace('T', ' ')
            )
            self.patient_tree.insert("", "end", values=values)
    
    def on_search_change(self, event=None):
        """搜索框内容变化事件"""
        # 延迟搜索，避免频繁查询
        if hasattr(self, '_search_after_id'):
            self.dialog.after_cancel(self._search_after_id)
        self._search_after_id = self.dialog.after(300, self.refresh_patient_list)
    
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
                    patient_name = item['values'][1]
                    patient_gender = item['values'][2]
                    patient_age = item['values'][3]
                    self.detail_text.insert(tk.END, f"{i}. {patient_name} ({patient_gender}, {patient_age})\n")
                
                self.detail_text.config(state='disabled')
                
                # 按钮状态
                self.edit_btn.config(state="disabled")  # 多选时不能编辑
                self.delete_btn.config(state="normal", text=f"🗑️ 删除 ({len(selection)})")
                if self.select_mode:
                    self.select_btn.config(state="disabled")  # 多选时不能选择
                    self.selected_patient = None
                    
            else:
                # 单选状态
                item = self.patient_tree.item(selection[0])
                patient_id = item['values'][0]
                
                # 获取患者详细信息
                patient = db.get_patient_by_id(patient_id)
                if patient:
                    # 显示详情
                    self.show_patient_detail(patient)
                    
                    # 启用按钮
                    self.edit_btn.config(state="normal")
                    self.delete_btn.config(state="normal", text="🗑️ 删除")
                    if self.select_mode:
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
            if self.select_mode:
                self.select_btn.config(state="disabled")
                self.selected_patient = None
    
    def show_patient_detail(self, patient):
        """显示患者详情"""
        height_str = f"{patient['height']:.1f}cm" if patient['height'] else "未填写"
        weight_str = f"{patient['weight']:.1f}kg" if patient['weight'] else "未填写"
        
        detail_text = f"""基本信息:
• 姓名: {patient['name']}
• 性别: {patient['gender']}
• 年龄: {patient['age']}岁
• 身高: {height_str}
• 体重: {weight_str}
• 电话: {patient['phone'] or "未填写"}

档案信息:
• 创建时间: {patient['created_time'][:19].replace('T', ' ')}
• 更新时间: {patient['updated_time'][:19].replace('T', ' ')}

备注信息:
{patient['notes'] or "无"}"""

        self.detail_text.config(state='normal')
        self.detail_text.delete(1.0, tk.END)  
        self.detail_text.insert(1.0, detail_text)
        self.detail_text.config(state='disabled')
    
    def on_patient_double_click(self, event=None):
        """患者双击事件"""
        if self.select_mode:
            self.select_patient()
        else:
            self.edit_patient()
    
    def new_patient(self):
        """新建患者"""
        dialog = PatientEditDialog(self.dialog, title="新建患者档案")
        if dialog.result:
            patient_id = db.add_patient(**dialog.result)
            if patient_id > 0:
                messagebox.showinfo("成功", f"患者档案创建成功！\n患者ID: {patient_id}")
                self.refresh_patient_list()
            else:
                messagebox.showerror("错误", "患者档案创建失败！")
    
    def edit_patient(self):
        """编辑患者"""
        selection = self.patient_tree.selection()
        if not selection:
            return
        
        item = self.patient_tree.item(selection[0])
        patient_id = item['values'][0]
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
            patient_id = item['values'][0]
            patient_name = item['values'][1]
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
            self.dialog.destroy()
    
    def cancel(self):
        """取消选择"""
        self.selected_patient = None
        self.dialog.destroy()
    
    def close_dialog(self):
        """关闭对话框"""
        self.dialog.destroy()


class PatientEditDialog:
    """患者编辑对话框"""
    
    def __init__(self, parent, title="患者档案", patient_data=None):
        self.result = None
        self.patient_data = patient_data or {}
        
        # 创建对话框窗口 - 增加窗口大小
        self.dialog = tk.Toplevel(parent)
        self.dialog.title(f"📋 {title}")
        self.dialog.geometry("700x650")  # 增加窗口大小
        self.dialog.resizable(True, True)
        self.dialog.minsize(650, 600)  # 增加最小尺寸
        self.dialog.grab_set()  # 模态对话框
        
        # 居中显示
        self.dialog.transient(parent)
        self.center_window()
        
        # 设置图标
        try:
            self.dialog.iconbitmap("icon.ico")
        except:
            pass
        
        # 创建界面
        self.create_ui()
        
        # 等待对话框关闭
        self.dialog.wait_window()
    
    def center_window(self):
        """居中显示窗口"""
        self.dialog.update_idletasks()
        x = (self.dialog.winfo_screenwidth() // 2) - (700 // 2)  # 更新居中计算
        y = (self.dialog.winfo_screenheight() // 2) - (650 // 2)
        self.dialog.geometry(f"700x650+{x}+{y}")
    
    def create_ui(self):
        """创建用户界面"""
        # 设置窗口样式
        style = ttk.Style()
        style.configure('Title.TLabel', font=('Microsoft YaHei UI', 16, 'bold'))
        style.configure('Section.TLabelframe.Label', font=('Microsoft YaHei UI', 11, 'bold'))
        
        # 主框架 - 使用滚动区域以防内容过多
        main_canvas = tk.Canvas(self.dialog, bg='white')
        scrollbar = ttk.Scrollbar(self.dialog, orient="vertical", command=main_canvas.yview)
        scrollable_frame = ttk.Frame(main_canvas)
        
        scrollable_frame.bind(
            "<Configure>",
            lambda e: main_canvas.configure(scrollregion=main_canvas.bbox("all"))
        )
        
        main_canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        main_canvas.configure(yscrollcommand=scrollbar.set)
        
        # 打包滚动组件
        main_canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        
        # 内容框架 - 增加内边距
        content_frame = ttk.Frame(scrollable_frame, padding="30")
        content_frame.pack(fill="both", expand=True)
        
        # 标题区域
        title_frame = ttk.Frame(content_frame)
        title_frame.pack(fill="x", pady=(0, 30))
        
        title_label = ttk.Label(title_frame, text="🏥 患者档案信息", style='Title.TLabel')
        title_label.pack()
        
        subtitle_label = ttk.Label(title_frame, text="请填写患者的基本信息", 
                                 font=('Microsoft YaHei UI', 10), foreground='#666666')
        subtitle_label.pack(pady=(5, 0))
        
        # 基本信息区域 - 使用更好的布局
        info_frame = ttk.LabelFrame(content_frame, text=" 📋 基本信息 ", 
                                   style='Section.TLabelframe', padding="25")
        info_frame.pack(fill="x", pady=(0, 25))
        
        # 第一行：姓名和性别
        row1_frame = ttk.Frame(info_frame)
        row1_frame.pack(fill="x", pady=(0, 20))
        
        # 姓名 (左半边)
        name_frame = ttk.Frame(row1_frame)
        name_frame.pack(side="left", fill="x", expand=True, padx=(0, 15))
        
        ttk.Label(name_frame, text="患者姓名 *", font=('Microsoft YaHei UI', 10, 'bold')).pack(anchor="w")
        self.name_var = tk.StringVar(value=self.patient_data.get('name', ''))
        name_entry = ttk.Entry(name_frame, textvariable=self.name_var, font=('Microsoft YaHei UI', 11))
        name_entry.pack(fill="x", pady=(8, 0))
        name_entry.focus()
        
        # 性别 (右半边)
        gender_frame = ttk.Frame(row1_frame)
        gender_frame.pack(side="right", fill="x", expand=True, padx=(15, 0))
        
        ttk.Label(gender_frame, text="性别 *", font=('Microsoft YaHei UI', 10, 'bold')).pack(anchor="w")
        self.gender_var = tk.StringVar(value=self.patient_data.get('gender', '男'))
        gender_combo = ttk.Combobox(gender_frame, textvariable=self.gender_var, 
                                   values=["男", "女"], font=('Microsoft YaHei UI', 11), state="readonly")
        gender_combo.pack(fill="x", pady=(8, 0))
        
        # 第二行：年龄和电话
        row2_frame = ttk.Frame(info_frame)
        row2_frame.pack(fill="x", pady=(0, 20))
        
        # 年龄 (左半边)
        age_frame = ttk.Frame(row2_frame)
        age_frame.pack(side="left", fill="x", expand=True, padx=(0, 15))
        
        ttk.Label(age_frame, text="年龄 *", font=('Microsoft YaHei UI', 10, 'bold')).pack(anchor="w")
        self.age_var = tk.StringVar(value=str(self.patient_data.get('age', '')))
        age_entry = ttk.Entry(age_frame, textvariable=self.age_var, font=('Microsoft YaHei UI', 11))
        age_entry.pack(fill="x", pady=(8, 0))
        
        # 电话 (右半边)
        phone_frame = ttk.Frame(row2_frame)
        phone_frame.pack(side="right", fill="x", expand=True, padx=(15, 0))
        
        ttk.Label(phone_frame, text="联系电话", font=('Microsoft YaHei UI', 10)).pack(anchor="w")
        self.phone_var = tk.StringVar(value=self.patient_data.get('phone', '') or '')
        phone_entry = ttk.Entry(phone_frame, textvariable=self.phone_var, font=('Microsoft YaHei UI', 11))
        phone_entry.pack(fill="x", pady=(8, 0))
        
        # 第三行：身高和体重
        row3_frame = ttk.Frame(info_frame)
        row3_frame.pack(fill="x")
        
        # 身高 (左半边)
        height_frame = ttk.Frame(row3_frame)
        height_frame.pack(side="left", fill="x", expand=True, padx=(0, 15))
        
        ttk.Label(height_frame, text="身高 (cm)", font=('Microsoft YaHei UI', 10)).pack(anchor="w")
        self.height_var = tk.StringVar(value=str(self.patient_data.get('height', '') or ''))
        height_entry = ttk.Entry(height_frame, textvariable=self.height_var, font=('Microsoft YaHei UI', 11))
        height_entry.pack(fill="x", pady=(8, 0))
        
        # 体重 (右半边)
        weight_frame = ttk.Frame(row3_frame)
        weight_frame.pack(side="right", fill="x", expand=True, padx=(15, 0))
        
        ttk.Label(weight_frame, text="体重 (kg)", font=('Microsoft YaHei UI', 10)).pack(anchor="w")
        self.weight_var = tk.StringVar(value=str(self.patient_data.get('weight', '') or ''))
        weight_entry = ttk.Entry(weight_frame, textvariable=self.weight_var, font=('Microsoft YaHei UI', 11))
        weight_entry.pack(fill="x", pady=(8, 0))
        
        # 备注区域 - 增加高度
        notes_frame = ttk.LabelFrame(content_frame, text=" 📝 备注信息 ", 
                                    style='Section.TLabelframe', padding="25")
        notes_frame.pack(fill="both", expand=True, pady=(0, 25))
        
        # 备注输入 - 增加文本框高度
        notes_container = ttk.Frame(notes_frame)
        notes_container.pack(fill="both", expand=True)
        
        self.notes_text = tk.Text(notes_container, height=8, font=('Microsoft YaHei UI', 10),  # 增加高度
                                 wrap=tk.WORD, relief='solid', borderwidth=1,
                                 bg='#fafafa', selectbackground='#e3f2fd')
        notes_scrollbar = ttk.Scrollbar(notes_container, orient="vertical", command=self.notes_text.yview)
        self.notes_text.configure(yscrollcommand=notes_scrollbar.set)
        
        # 填入现有备注
        if self.patient_data.get('notes'):
            self.notes_text.insert(1.0, self.patient_data['notes'])
        
        self.notes_text.pack(side="left", fill="both", expand=True)
        notes_scrollbar.pack(side="right", fill="y")
        
        # 底部信息和按钮区域
        bottom_frame = ttk.Frame(content_frame)
        bottom_frame.pack(fill="x", pady=(15, 0))
        
        # 必填项提示
        tip_frame = ttk.Frame(bottom_frame)
        tip_frame.pack(fill="x", pady=(0, 25))
        
        tip_label = ttk.Label(tip_frame, text="* 标记为必填项", 
                             font=('Microsoft YaHei UI', 9), foreground='#d32f2f')
        tip_label.pack(anchor="w")
        
        help_label = ttk.Label(tip_frame, text="💡 提示：身高体重信息有助于更准确的分析结果", 
                              font=('Microsoft YaHei UI', 9), foreground='#1976d2')
        help_label.pack(anchor="w", pady=(5, 0))
        
        # 按钮区域
        button_frame = ttk.Frame(bottom_frame)
        button_frame.pack(fill="x")
        
        # 左侧状态信息
        status_frame = ttk.Frame(button_frame)
        status_frame.pack(side="left", fill="x", expand=True)
        
        if self.patient_data:
            status_text = f"编辑模式 - 修改患者 {self.patient_data.get('name', '未知')} 的信息"
        else:
            status_text = "新建模式 - 创建新的患者档案"
        
        status_label = ttk.Label(status_frame, text=status_text, 
                                font=('Microsoft YaHei UI', 9), foreground='#666666')
        status_label.pack(anchor="w")
        
        # 右侧按钮
        btn_container = ttk.Frame(button_frame)
        btn_container.pack(side="right")
        
        # 取消按钮
        cancel_btn = ttk.Button(btn_container, text="❌ 取消", command=self.cancel,
                               style='Outline.TButton')
        cancel_btn.pack(side="right", padx=(15, 0))
        
        # 确认按钮
        confirm_text = "💾 保存修改" if self.patient_data else "➕ 创建档案"
        confirm_btn = ttk.Button(btn_container, text=confirm_text, command=self.confirm)
        confirm_btn.pack(side="right")
        
        # 绑定快捷键
        self.dialog.bind('<Return>', lambda e: self.confirm())
        self.dialog.bind('<Escape>', lambda e: self.cancel())
        self.dialog.bind('<Control-s>', lambda e: self.confirm())
        
        # 鼠标滚轮绑定
        def _on_mousewheel(event):
            main_canvas.yview_scroll(int(-1*(event.delta/120)), "units")
        
        self.dialog.bind("<MouseWheel>", _on_mousewheel)
    
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