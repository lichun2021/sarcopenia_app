#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
患者信息输入对话框
用于AI分析前收集患者基本信息
"""

import tkinter as tk
from tkinter import ttk, messagebox
from datetime import datetime

class PatientInfoDialog:
    """患者信息输入对话框"""
    
    def __init__(self, parent):
        self.result = None
        
        # 创建对话框窗口 - 优化显示避免闪烁
        self.dialog = tk.Toplevel(parent)
        self.dialog.title("📋 患者信息录入")
        
        # 先隐藏窗口，避免初始化时的闪烁
        self.dialog.withdraw()
        
        self.dialog.geometry("450x400")
        self.dialog.resizable(False, False)
        self.dialog.grab_set()  # 模态对话框
        
        # 居中显示
        self.dialog.transient(parent)
        
        # 设置图标
        try:
            self.dialog.iconbitmap("icon.ico")
        except:
            pass
        
        # 创建界面
        self.create_ui()
        
        # 居中显示并显示窗口
        self.center_window()
        self.dialog.deiconify()
        
        # 等待对话框关闭
        self.dialog.wait_window()
    
    def center_window(self):
        """居中显示窗口"""
        self.dialog.update_idletasks()
        x = (self.dialog.winfo_screenwidth() // 2) - (450 // 2)
        y = (self.dialog.winfo_screenheight() // 2) - (400 // 2)
        self.dialog.geometry(f"450x400+{x}+{y}")
    
    def create_ui(self):
        """创建用户界面"""
        # 主框架
        main_frame = ttk.Frame(self.dialog, padding="20")
        main_frame.pack(fill="both", expand=True)
        
        # 标题
        title_label = ttk.Label(main_frame, text="🏥 患者基本信息", 
                               font=('Microsoft YaHei UI', 14, 'bold'))
        title_label.pack(pady=(0, 20))
        
        # 信息输入区域
        info_frame = ttk.LabelFrame(main_frame, text="基本信息", padding="15")
        info_frame.pack(fill="x", pady=(0, 20))
        
        # 姓名
        ttk.Label(info_frame, text="患者姓名 *:").grid(row=0, column=0, sticky="w", pady=5)
        self.name_var = tk.StringVar(value="")
        name_entry = ttk.Entry(info_frame, textvariable=self.name_var, width=25, font=('Microsoft YaHei UI', 10))
        name_entry.grid(row=0, column=1, sticky="ew", padx=(10, 0), pady=5)
        name_entry.focus()
        
        # 年龄
        ttk.Label(info_frame, text="年龄 *:").grid(row=1, column=0, sticky="w", pady=5)
        self.age_var = tk.StringVar(value="")
        age_entry = ttk.Entry(info_frame, textvariable=self.age_var, width=25, font=('Microsoft YaHei UI', 10))
        age_entry.grid(row=1, column=1, sticky="ew", padx=(10, 0), pady=5)
        
        # 性别
        ttk.Label(info_frame, text="性别 *:").grid(row=2, column=0, sticky="w", pady=5)
        self.gender_var = tk.StringVar(value="男")
        gender_combo = ttk.Combobox(info_frame, textvariable=self.gender_var, 
                                   values=["男", "女"], width=22, font=('Microsoft YaHei UI', 10))
        gender_combo.grid(row=2, column=1, sticky="ew", padx=(10, 0), pady=5)
        gender_combo.state(['readonly'])
        
        # 身高
        ttk.Label(info_frame, text="身高 (cm):").grid(row=3, column=0, sticky="w", pady=5)
        self.height_var = tk.StringVar(value="")
        height_entry = ttk.Entry(info_frame, textvariable=self.height_var, width=25, font=('Microsoft YaHei UI', 10))
        height_entry.grid(row=3, column=1, sticky="ew", padx=(10, 0), pady=5)
        
        # 体重
        ttk.Label(info_frame, text="体重 (kg):").grid(row=4, column=0, sticky="w", pady=5)
        self.weight_var = tk.StringVar(value="")
        weight_entry = ttk.Entry(info_frame, textvariable=self.weight_var, width=25, font=('Microsoft YaHei UI', 10))
        weight_entry.grid(row=4, column=1, sticky="ew", padx=(10, 0), pady=5)
        
        # 配置列权重
        info_frame.columnconfigure(1, weight=1)
        
        # 检测信息区域
        test_frame = ttk.LabelFrame(main_frame, text="检测信息", padding="15")
        test_frame.pack(fill="x", pady=(0, 20))
        
        # 检测日期
        ttk.Label(test_frame, text="检测日期:").grid(row=0, column=0, sticky="w", pady=5)
        self.date_var = tk.StringVar(value=datetime.now().strftime("%Y-%m-%d"))
        date_entry = ttk.Entry(test_frame, textvariable=self.date_var, width=25, font=('Microsoft YaHei UI', 10))
        date_entry.grid(row=0, column=1, sticky="ew", padx=(10, 0), pady=5)
        date_entry.config(state='readonly')
        
        # 检测类型
        ttk.Label(test_frame, text="检测类型:").grid(row=1, column=0, sticky="w", pady=5)
        self.test_type_var = tk.StringVar(value="综合分析")
        test_type_combo = ttk.Combobox(test_frame, textvariable=self.test_type_var,
                                      values=["综合分析", "步态分析", "平衡测试", "肌力评估"], 
                                      width=22, font=('Microsoft YaHei UI', 10))
        test_type_combo.grid(row=1, column=1, sticky="ew", padx=(10, 0), pady=5)
        test_type_combo.state(['readonly'])
        
        # 配置列权重
        test_frame.columnconfigure(1, weight=1)
        
        # 备注区域
        notes_frame = ttk.LabelFrame(main_frame, text="备注信息", padding="15")
        notes_frame.pack(fill="both", expand=True, pady=(0, 20))
        
        self.notes_text = tk.Text(notes_frame, height=4, width=40, font=('Microsoft YaHei UI', 9),
                                 wrap=tk.WORD, relief='solid', borderwidth=1)
        notes_scrollbar = ttk.Scrollbar(notes_frame, orient="vertical", command=self.notes_text.yview)
        self.notes_text.configure(yscrollcommand=notes_scrollbar.set)
        
        self.notes_text.pack(side="left", fill="both", expand=True)
        notes_scrollbar.pack(side="right", fill="y")
        
        # 按钮区域
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(fill="x")
        
        # 取消按钮
        cancel_btn = ttk.Button(button_frame, text="❌ 取消", command=self.cancel)
        cancel_btn.pack(side="right", padx=(10, 0))
        
        # 确认按钮
        confirm_btn = ttk.Button(button_frame, text="✅ 确认", command=self.confirm, 
                                style="Accent.TButton")
        confirm_btn.pack(side="right")
        
        # 必填项提示
        tip_label = ttk.Label(main_frame, text="* 为必填项", 
                             font=('Microsoft YaHei UI', 8), foreground='#666666')
        tip_label.pack(anchor="w", pady=(10, 0))
        
        # 绑定回车键确认
        self.dialog.bind('<Return>', lambda e: self.confirm())
        self.dialog.bind('<Escape>', lambda e: self.cancel())
    
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
            'age': int(self.age_var.get()),
            'gender': self.gender_var.get(),
            'height': float(self.height_var.get()) if self.height_var.get().strip() else None,
            'weight': float(self.weight_var.get()) if self.weight_var.get().strip() else None,
            'test_date': self.date_var.get(),
            'test_type': self.test_type_var.get(),
            'notes': self.notes_text.get(1.0, tk.END).strip(),
            'created_time': datetime.now().isoformat()
        }
        
        self.dialog.destroy()
    
    def cancel(self):
        """取消按钮事件"""
        self.result = None
        self.dialog.destroy()

# 测试代码
if __name__ == "__main__":
    root = tk.Tk()
    root.withdraw()  # 隐藏主窗口
    
    dialog = PatientInfoDialog(root)
    
    if dialog.result:
        print("患者信息:")
        for key, value in dialog.result.items():
            print(f"  {key}: {value}")
    else:
        print("用户取消了输入")
    
    root.destroy()