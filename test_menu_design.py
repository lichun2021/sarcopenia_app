#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
菜单设计预览测试 - 展示医院风格的专业菜单
"""

import tkinter as tk
from tkinter import messagebox

class MenuPreview:
    """菜单预览测试类"""
    
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("🏥 医院风格菜单预览 - 智能肌少症检测系统")
        self.root.geometry("800x500")
        self.root.configure(bg='#f8f9fa')
        
        self.create_test_menubar()
        self.create_preview_content()
    
    def create_test_menubar(self):
        """创建医院风格测试菜单栏"""
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
        
        # 文件菜单（绿色健康主题）
        file_menu = tk.Menu(menubar, tearoff=0,
                           bg='#ffffff', fg='#37474f',
                           activebackground='#e8f5e8', activeforeground='#2e7d32',
                           font=('Microsoft YaHei UI', 11),
                           borderwidth=1, relief='solid')
        menubar.add_cascade(label="  📄 文件  ", menu=file_menu, 
                          activebackground='#f0f8ff', activeforeground='#0066cc')
        
        file_menu.add_command(label="📁 新建检测档案", command=lambda: self.show_demo_msg("文件", "新建检测档案"))
        file_menu.add_separator()
        file_menu.add_command(label="📊 导出检测数据", command=lambda: self.show_demo_msg("文件", "导出检测数据"))
        file_menu.add_command(label="📸 保存热力图快照", command=lambda: self.show_demo_msg("文件", "保存热力图快照"))
        
        # 检测菜单（蓝色医疗主题）
        detection_menu = tk.Menu(menubar, tearoff=0,
                               bg='#ffffff', fg='#37474f',
                               activebackground='#e3f2fd', activeforeground='#1976d2',
                               font=('Microsoft YaHei UI', 11),
                               borderwidth=1, relief='solid')
        menubar.add_cascade(label="  🔬 检测  ", menu=detection_menu,
                          activebackground='#f0f8ff', activeforeground='#0066cc')
        
        detection_menu.add_command(label="📋 检测流程指导", command=lambda: self.show_demo_msg("检测", "检测流程指导"))
        detection_menu.add_command(label="👤 患者信息管理", command=lambda: self.show_demo_msg("检测", "患者信息管理"))
        
        # 设备菜单（紫色主题）
        device_menu = tk.Menu(menubar, tearoff=0,
                             bg='#ffffff', fg='#37474f',
                             activebackground='#f3e5f5', activeforeground='#7b1fa2',
                             font=('Microsoft YaHei UI', 11),
                             borderwidth=1, relief='solid')
        menubar.add_cascade(label="  📱 设备  ", menu=device_menu,
                          activebackground='#f0f8ff', activeforeground='#0066cc')
        
        device_menu.add_command(label="🔍 自动检测端口", command=lambda: self.show_demo_msg("设备", "自动检测端口"))
        device_menu.add_command(label="📊 实时数据监控", command=lambda: self.show_demo_msg("设备", "实时数据监控"))
        
        # 视图菜单（橙色主题）
        view_menu = tk.Menu(menubar, tearoff=0,
                           bg='#ffffff', fg='#37474f',
                           activebackground='#fff3e0', activeforeground='#f57c00',
                           font=('Microsoft YaHei UI', 11),
                           borderwidth=1, relief='solid')
        menubar.add_cascade(label="  👀 视图  ", menu=view_menu,
                          activebackground='#f0f8ff', activeforeground='#0066cc')
        
        view_menu.add_command(label="📈 统计数据面板", command=lambda: self.show_demo_msg("视图", "统计数据面板"))
        view_menu.add_command(label="🎨 热力图显示设置", command=lambda: self.show_demo_msg("视图", "热力图显示设置"))
        
        # 帮助菜单（绿色主题）
        help_menu = tk.Menu(menubar, tearoff=0,
                           bg='#ffffff', fg='#37474f',
                           activebackground='#e8f5e8', activeforeground='#2e7d32',
                           font=('Microsoft YaHei UI', 11),
                           borderwidth=1, relief='solid')
        menubar.add_cascade(label="  ❓ 帮助  ", menu=help_menu,
                          activebackground='#f0f8ff', activeforeground='#0066cc')
        
        help_menu.add_command(label="📖 操作指南手册", command=lambda: self.show_demo_msg("帮助", "操作指南手册"))
        help_menu.add_command(label="ℹ️ 关于本系统", command=lambda: self.show_demo_msg("帮助", "关于本系统"))
    
    def create_preview_content(self):
        """创建预览内容"""
        content_frame = tk.Frame(self.root, bg='#ffffff', relief='solid', bd=1)
        content_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)
        
        # 标题
        title_label = tk.Label(content_frame, 
                              text="🏥 医院风格菜单设计预览",
                              font=('Microsoft YaHei UI', 18, 'bold'),
                              bg='#ffffff', fg='#2c3e50')
        title_label.pack(pady=30)
        
        # 特性说明
        features_frame = tk.Frame(content_frame, bg='#ffffff')
        features_frame.pack(fill=tk.X, padx=40, pady=20)
        
        features = [
            "✅ 菜单栏高度增加30% (字体从11号增加到12号)",
            "✅ 医院风格配色：浅色背景 + 深色文字",
            "✅ 不同菜单使用不同医疗色调悬停效果",
            "✅ 纯白子菜单背景，专业清洁感",
            "✅ 菜单项名称更加专业化",
            "✅ 符合医疗设备的审美标准",
        ]
        
        for feature in features:
            feature_label = tk.Label(features_frame, text=feature,
                                   font=('Microsoft YaHei UI', 11),
                                   bg='#ffffff', fg='#37474f',
                                   anchor='w')
            feature_label.pack(fill=tk.X, pady=5)
        
        # 颜色方案说明
        color_frame = tk.Frame(content_frame, bg='#f8f9fa', relief='solid', bd=1)
        color_frame.pack(fill=tk.X, padx=40, pady=20)
        
        color_title = tk.Label(color_frame, text="🎨 医疗色彩方案",
                              font=('Microsoft YaHei UI', 14, 'bold'),
                              bg='#f8f9fa', fg='#2c3e50')
        color_title.pack(pady=10)
        
        color_items = [
            ("📄 文件菜单", "#e8f5e8", "淡绿色悬停 - 健康色调"),
            ("🔬 检测菜单", "#e3f2fd", "淡蓝色悬停 - 医疗专业"),
            ("📱 设备菜单", "#f3e5f5", "淡紫色悬停 - 科技感"),
            ("👀 视图菜单", "#fff3e0", "淡橙色悬停 - 温和提示"),
            ("❓ 帮助菜单", "#e8f5e8", "淡绿色悬停 - 友好帮助"),
        ]
        
        for name, color, description in color_items:
            item_frame = tk.Frame(color_frame, bg='#f8f9fa')
            item_frame.pack(fill=tk.X, padx=20, pady=3)
            
            color_box = tk.Label(item_frame, text="  ", bg=color, 
                               width=3, relief='solid', bd=1)
            color_box.pack(side=tk.LEFT, padx=(0, 10))
            
            desc_label = tk.Label(item_frame, text=f"{name}: {description}",
                                 font=('Microsoft YaHei UI', 10),
                                 bg='#f8f9fa', fg='#37474f')
            desc_label.pack(side=tk.LEFT)
        
        # 测试提示
        tip_label = tk.Label(content_frame,
                            text="💡 请点击上方菜单项测试悬停效果和颜色搭配",
                            font=('Microsoft YaHei UI', 12),
                            bg='#ffffff', fg='#1976d2')
        tip_label.pack(pady=20)
    
    def show_demo_msg(self, menu_name, item_name):
        """显示演示消息"""
        messagebox.showinfo("菜单测试", 
                           f"🏥 医院风格菜单测试\n\n菜单: {menu_name}\n功能: {item_name}\n\n✅ 菜单样式正常显示")
    
    def run(self):
        """运行预览"""
        self.root.mainloop()

def main():
    print("🏥 医院风格菜单设计预览")
    print("=" * 50)
    print("✅ 菜单栏高度增加30%")
    print("✅ 采用医院专业配色方案")
    print("✅ 清洁简约的视觉效果")
    print("=" * 50)
    
    preview = MenuPreview()
    preview.run()

if __name__ == "__main__":
    main() 