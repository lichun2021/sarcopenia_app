"""
窗口管理器 - 统一的三级窗口适配方案
实现全屏、管理界面、小窗口三种规格的统一管理
"""

import tkinter as tk
from tkinter import ttk
from enum import Enum
from typing import Optional, Tuple, Callable


class WindowLevel(Enum):
    """窗口级别枚举"""
    FULLSCREEN = "fullscreen"  # 主UI全屏（100%）
    MANAGEMENT = "management"  # 管理UI（80%）
    DIALOG = "dialog"         # 其他窗口（不限制大小，但最大80%）


class WindowManager:
    """窗口管理器 - 处理窗口适配和定位"""
    
    # 各级别窗口占屏幕的比例
    FULLSCREEN_RATIO = 1.0      # 100% - 主UI
    MANAGEMENT_RATIO = 0.8      # 80% - 管理UI
    DIALOG_MAX_RATIO = 0.8      # 对话框最大80%
    
    # 全屏模式配置
    USE_TRUE_FULLSCREEN = False  # 是否使用真正的无边框全屏
    
    # 真实可用区域尺寸（最大化后的实际尺寸）
    _real_available_width = None
    _real_available_height = None
    
    @classmethod
    def setup_window(cls, window: tk.Tk | tk.Toplevel, 
                    level: WindowLevel,
                    title: str = "",
                    custom_size: Optional[Tuple[int, int]] = None) -> None:
        """
        设置窗口的统一适配
        
        Args:
            window: Tkinter窗口对象
            level: 窗口级别
            title: 窗口标题
            custom_size: 自定义尺寸 (width, height)，仅用于DIALOG级别
        """
        if title:
            window.title(title)
            
        # 获取屏幕尺寸
        screen_width = window.winfo_screenwidth()
        screen_height = window.winfo_screenheight()
        
        # 根据级别设置窗口
        if level == WindowLevel.FULLSCREEN:
            # 全屏模式 - 使用Windows最大化自动适配任务栏
            cls._setup_fullscreen(window, screen_width, screen_height)
            
        elif level == WindowLevel.MANAGEMENT:
            # 管理界面 - 等待获取真实尺寸后计算80%
            def setup_mgmt_delayed():
                width, height = cls.get_management_size(window)
                cls._setup_management_window(window, width, height, 
                                           screen_width, screen_height)
            
            if cls._real_available_width and cls._real_available_height:
                # 已经有真实尺寸，直接使用
                setup_mgmt_delayed()
            else:
                # 延迟设置，等待真实尺寸获取完成
                window.after(300, setup_mgmt_delayed)
            
        elif level == WindowLevel.DIALOG:
            # 对话框 - 使用自定义尺寸，但限制最大80%
            def setup_dialog_delayed():
                if custom_size:
                    width, height = custom_size
                else:
                    # 默认尺寸 (600x400)
                    width, height = 600, 400
                    
                # 确保不超过80%可用区域
                width, height = cls.validate_dialog_size(window, width, height)
                cls._setup_dialog_window(window, width, height, 
                                       screen_width, screen_height)
            
            if cls._real_available_width and cls._real_available_height:
                # 已经有真实尺寸，直接使用
                setup_dialog_delayed()
            else:
                # 延迟设置，等待真实尺寸获取完成
                window.after(300, setup_dialog_delayed)
    
    @classmethod
    def _setup_fullscreen(cls, window: tk.Tk | tk.Toplevel, 
                         screen_width: int, screen_height: int) -> None:
        """设置全屏窗口"""
        window.resizable(True, True)
        
        if cls.USE_TRUE_FULLSCREEN:
            # 真正的无边框全屏（撑满整个屏幕）
            window.geometry(f"{screen_width}x{screen_height}+0+0")
            try:
                window.attributes('-fullscreen', True)
                # 添加ESC键退出全屏的绑定
                window.bind('<Escape>', lambda e: window.attributes('-fullscreen', False))
            except:
                # 降级到最大化
                cls._setup_maximized(window, screen_width, screen_height)
        else:
            # 最大化模式（获取真实可用区域）
            cls._setup_maximized_with_real_size(window, screen_width, screen_height)
    
    @staticmethod
    def _setup_maximized(window: tk.Tk | tk.Toplevel,
                        screen_width: int, screen_height: int) -> None:
        """设置最大化窗口 - 使用简单直接的方法"""
        print(f"[DEBUG] 开始最大化窗口，目标屏幕尺寸: {screen_width}x{screen_height}")
        
        # 使用最直接的方法设置最大化
        window.state("zoomed")
        print(f"[DEBUG] 使用 window.state('zoomed') 最大化")
        
        # 强制更新窗口
        window.update_idletasks()
        window.update()
        
        # 验证最大化是否成功
        actual_width = window.winfo_width()
        actual_height = window.winfo_height()
        print(f"[DEBUG] 最大化后实际尺寸: {actual_width}x{actual_height}")
        print(f"[DEBUG] 最大化成功，占用了 {actual_width/screen_width:.1%} x {actual_height/screen_height:.1%} 的屏幕空间")
    
    @classmethod
    def _setup_maximized_with_real_size(cls, window: tk.Tk | tk.Toplevel,
                                       screen_width: int, screen_height: int) -> None:
        """设置最大化窗口并获取真实可用尺寸"""
        # 先最大化窗口
        cls._setup_maximized(window, screen_width, screen_height)
        
        # 多次尝试获取真实尺寸，确保准确性
        def get_real_size(attempt=0):
            window.update_idletasks()
            real_width = window.winfo_width()
            real_height = window.winfo_height()
            
            # 检查尺寸是否已经稳定（连续两次获取相同）
            if hasattr(cls, '_last_measured_size'):
                last_width, last_height = cls._last_measured_size
                if real_width == last_width and real_height == last_height:
                    # 尺寸已稳定，确认保存
                    cls._real_available_width = real_width
                    cls._real_available_height = real_height
                    
                    print(f"[INFO] 窗口尺寸获取完成:")
                    print(f"[INFO] 屏幕分辨率: {screen_width}x{screen_height}")
                    print(f"[INFO] 最大化后实际尺寸: {real_width}x{real_height}")
                    print(f"[INFO] 任务栏占用空间: {screen_width-real_width}x{screen_height-real_height}")
                    print(f"[INFO] 可用区域比例: {real_width/screen_width:.1%} x {real_height/screen_height:.1%}")
                    return
            
            # 记录本次测量结果
            cls._last_measured_size = (real_width, real_height)
            
            # 如果尺寸还在变化或者是第一次测量，继续等待
            if attempt < 10:  # 最多尝试10次
                window.after(50, lambda: get_real_size(attempt + 1))
            else:
                # 超时后使用最后测量的结果
                cls._real_available_width = real_width
                cls._real_available_height = real_height
                print(f"[WARN] 窗口尺寸获取超时，使用最后测量结果: {real_width}x{real_height}")
        
        # 延迟执行以确保窗口完全最大化
        window.after(100, get_real_size)
    
    @classmethod
    def _setup_management_window(cls, window: tk.Tk | tk.Toplevel,
                               width: int, height: int,
                               screen_width: int, screen_height: int) -> None:
        """设置管理界面窗口 - 80%"""
        # 计算居中位置
        x = (screen_width - width) // 2
        y = (screen_height - height) // 2
        
        # 设置窗口位置和大小
        window.geometry(f"{width}x{height}+{x}+{y}")
        window.resizable(True, True)  # 管理界面允许调整大小
        
        # 设置最小尺寸为屏幕的60%
        min_width = int(screen_width * 0.6)
        min_height = int(screen_height * 0.6)
        window.minsize(min_width, min_height)
        
        # 设置最大尺寸不超过屏幕尺寸
        window.maxsize(screen_width, screen_height)
    
    
    @classmethod
    def _setup_dialog_window(cls, window: tk.Tk | tk.Toplevel,
                           width: int, height: int,
                           screen_width: int, screen_height: int) -> None:
        """设置对话框窗口 - 最大不超过80%"""
        # 计算居中位置
        x = (screen_width - width) // 2
        y = (screen_height - height) // 2
        
        # 设置窗口位置和大小
        window.geometry(f"{width}x{height}+{x}+{y}")
        window.resizable(True, True)  # 允许调整大小
        
        # 设置最大尺寸为80%
        max_width = int(screen_width * cls.DIALOG_MAX_RATIO)
        max_height = int(screen_height * cls.DIALOG_MAX_RATIO)
        window.maxsize(max_width, max_height)
    
    @classmethod
    def center_window(cls, window: tk.Tk | tk.Toplevel,
                     width: Optional[int] = None, 
                     height: Optional[int] = None) -> None:
        """居中显示窗口"""
        window.update_idletasks()
        
        # 获取窗口尺寸
        if width is None:
            width = window.winfo_width()
        if height is None:
            height = window.winfo_height()
            
        # 获取屏幕尺寸
        screen_width = window.winfo_screenwidth()
        screen_height = window.winfo_screenheight()
        
        # 计算居中位置
        x = (screen_width - width) // 2
        y = (screen_height - height) // 2
        
        window.geometry(f"{width}x{height}+{x}+{y}")
    
    @classmethod
    def create_managed_window(cls, parent: Optional[tk.Tk] = None,
                            level: WindowLevel = WindowLevel.DIALOG,
                            title: str = "",
                            custom_size: Optional[Tuple[int, int]] = None) -> tk.Toplevel:
        """创建一个受管理的窗口"""
        if parent is None:
            window = tk.Tk()
        else:
            window = tk.Toplevel(parent)
            
        cls.setup_window(window, level, title, custom_size)
        return window
    
    @classmethod
    def apply_management_theme(cls, window: tk.Tk | tk.Toplevel) -> None:
        """应用管理界面的统一主题"""
        # 设置统一的背景色
        window.configure(bg='#f0f0f0')
        
        # 设置统一的字体样式
        style = ttk.Style()
        style.configure('Title.TLabel', font=('Arial', 16, 'bold'))
        style.configure('Subtitle.TLabel', font=('Arial', 12))
        style.configure('Management.TFrame', background='#f0f0f0')
    
    @classmethod
    def create_standard_frame(cls, parent: tk.Widget, 
                            title: str = "",
                            padding: int = 20) -> ttk.Frame:
        """创建标准化的框架布局"""
        # 主框架
        main_frame = ttk.Frame(parent, style='Management.TFrame')
        main_frame.pack(fill=tk.BOTH, expand=True, padx=padding, pady=padding)
        
        # 标题框架
        if title:
            title_frame = ttk.Frame(main_frame, style='Management.TFrame')
            title_frame.pack(fill=tk.X, pady=(0, 10))
            
            title_label = ttk.Label(title_frame, text=title, style='Title.TLabel')
            title_label.pack(side=tk.LEFT)
            
            # 分隔线
            separator = ttk.Separator(main_frame, orient='horizontal')
            separator.pack(fill=tk.X, pady=(0, 10))
        
        # 内容框架
        content_frame = ttk.Frame(main_frame, style='Management.TFrame')
        content_frame.pack(fill=tk.BOTH, expand=True)
        
        return content_frame
    
    @classmethod
    def get_screen_size(cls, window: tk.Tk | tk.Toplevel) -> Tuple[int, int]:
        """获取屏幕分辨率"""
        return window.winfo_screenwidth(), window.winfo_screenheight()
    
    @classmethod
    def get_available_size(cls, window: tk.Tk | tk.Toplevel) -> Tuple[int, int]:
        """获取实际可用区域尺寸（考虑任务栏）"""
        if cls._real_available_width and cls._real_available_height:
            return cls._real_available_width, cls._real_available_height
        else:
            # 如果还没有获取到真实尺寸，返回屏幕尺寸
            return cls.get_screen_size(window)
    
    @classmethod
    def get_management_size(cls, window: tk.Tk | tk.Toplevel) -> Tuple[int, int]:
        """获取管理界面的推荐尺寸（可用区域的80%）"""
        available_width, available_height = cls.get_available_size(window)
        width = int(available_width * cls.MANAGEMENT_RATIO)
        height = int(available_height * cls.MANAGEMENT_RATIO)
        return width, height
    
    
    @classmethod
    def get_dialog_max_size(cls, window: tk.Tk | tk.Toplevel) -> Tuple[int, int]:
        """获取对话框的建议尺寸（不限制，返回屏幕尺寸）"""
        return cls.get_screen_size(window)
    
    @classmethod
    def validate_dialog_size(cls, window: tk.Tk | tk.Toplevel, 
                           width: int, height: int) -> Tuple[int, int]:
        """验证对话框尺寸（确保不超过80%）"""
        available_width, available_height = cls.get_available_size(window)
        max_width = int(available_width * cls.DIALOG_MAX_RATIO)
        max_height = int(available_height * cls.DIALOG_MAX_RATIO)
        return min(width, max_width), min(height, max_height)
    
    @classmethod
    def enable_true_fullscreen(cls, enable: bool = True) -> None:
        """启用或禁用真正的无边框全屏模式"""
        cls.USE_TRUE_FULLSCREEN = enable
    
    @classmethod
    def is_real_size_available(cls) -> bool:
        """检查是否已获取到真实可用尺寸"""
        return cls._real_available_width is not None and cls._real_available_height is not None
    
    @classmethod
    def wait_for_real_size(cls, callback: Callable, window: tk.Tk | tk.Toplevel, max_wait_ms: int = 2000) -> None:
        """等待真实尺寸获取完成后执行回调"""
        def check_and_call(elapsed_ms=0):
            if cls.is_real_size_available():
                callback()
            elif elapsed_ms < max_wait_ms:
                window.after(100, lambda: check_and_call(elapsed_ms + 100))
            else:
                print(f"[WARN] 等待真实尺寸获取超时({max_wait_ms}ms)，强制执行回调")
                callback()
        
        check_and_call()
    
    @classmethod
    def toggle_fullscreen(cls, window: tk.Tk | tk.Toplevel) -> None:
        """切换窗口的全屏状态"""
        try:
            current_state = window.attributes('-fullscreen')
            window.attributes('-fullscreen', not current_state)
        except:
            # 如果不支持fullscreen属性，尝试在zoomed和normal之间切换
            try:
                current_state = window.state()
                if current_state == 'zoomed':
                    window.state('normal')
                else:
                    window.state('zoomed')
            except:
                pass


# 便捷函数
def setup_fullscreen(window: tk.Tk, title: str = "", true_fullscreen: bool = False) -> None:
    """快速设置全屏窗口
    
    Args:
        window: 主窗口对象
        title: 窗口标题
        true_fullscreen: 是否使用真正的无边框全屏（默认False，使用最大化）
    """
    if true_fullscreen:
        WindowManager.enable_true_fullscreen(True)
    WindowManager.setup_window(window, WindowLevel.FULLSCREEN, title)


def setup_management_window(window: tk.Tk | tk.Toplevel, title: str = "") -> None:
    """快速设置管理界面窗口（基于真实可用区域的80%）"""
    WindowManager.setup_window(window, WindowLevel.MANAGEMENT, title)
    WindowManager.apply_management_theme(window)



def setup_dialog(window: tk.Tk | tk.Toplevel, 
                title: str = "",
                width: int = 600, 
                height: int = 400) -> None:
    """快速设置对话框窗口（不限制大小）"""
    WindowManager.setup_window(window, WindowLevel.DIALOG, title, (width, height))


def create_management_window_when_ready(parent: tk.Tk, title: str, callback: Callable = None) -> None:
    """等待真实尺寸获取完成后创建管理界面"""
    def create_window():
        mgmt_window = WindowManager.create_managed_window(parent, WindowLevel.MANAGEMENT, title)
        WindowManager.apply_management_theme(mgmt_window)
        if callback:
            callback(mgmt_window)
        return mgmt_window
    
    if WindowManager.is_real_size_available():
        create_window()
    else:
        WindowManager.wait_for_real_size(create_window, parent)


def create_dialog_when_ready(parent: tk.Tk, title: str, size: tuple = (600, 400), callback: Callable = None) -> None:
    """等待真实尺寸获取完成后创建对话框"""
    def create_dialog():
        dialog = WindowManager.create_managed_window(parent, WindowLevel.DIALOG, title, size)
        if callback:
            callback(dialog)
        return dialog
    
    if WindowManager.is_real_size_available():
        create_dialog()
    else:
        WindowManager.wait_for_real_size(create_dialog, parent)


def enable_true_fullscreen(enable: bool = True) -> None:
    """全局启用/禁用真正的无边框全屏模式"""
    WindowManager.enable_true_fullscreen(enable)


# 使用示例
if __name__ == "__main__":
    # 测试全屏窗口
    root = tk.Tk()
    setup_fullscreen(root, "全屏主界面 (100%)")
    
    # 添加测试按钮
    def open_management():
        mgmt = WindowManager.create_managed_window(root, WindowLevel.MANAGEMENT, "管理界面测试")
        WindowManager.apply_management_theme(mgmt)
        content = WindowManager.create_standard_frame(mgmt, "患者管理")
        
        # 显示当前尺寸信息
        screen_w, screen_h = WindowManager.get_screen_size(mgmt)
        mgmt_w, mgmt_h = WindowManager.get_management_size(mgmt)
        
        info_text = f"屏幕尺寸: {screen_w}x{screen_h}\n"
        info_text += f"管理界面尺寸: {mgmt_w}x{mgmt_h} (80%)\n"
        info_text += f"可调整范围: 60% - 100%"
        
        ttk.Label(content, text=info_text, style='Subtitle.TLabel').pack()
    
    def open_dialog():
        # 测试超大尺寸（会被限制在60%以内）
        dlg = WindowManager.create_managed_window(root, WindowLevel.DIALOG, 
                                                 "小窗口测试", (1000, 800))
        
        screen_w, screen_h = WindowManager.get_screen_size(dlg)
        max_w = int(screen_w * WindowManager.DIALOG_MAX_RATIO)
        max_h = int(screen_h * WindowManager.DIALOG_MAX_RATIO)
        
        info_text = f"请求尺寸: 1000x800\n"
        info_text += f"实际尺寸: 不超过 {max_w}x{max_h} (60%)\n"
        info_text += "固定尺寸，不可调整"
        
        ttk.Label(dlg, text=info_text).pack(pady=50)
    
    btn_frame = tk.Frame(root)
    btn_frame.pack(pady=50)
    
    tk.Button(btn_frame, text="打开管理界面 (80%)", command=open_management, 
              font=('Arial', 12)).pack(side=tk.LEFT, padx=10)
    tk.Button(btn_frame, text="打开小窗口 (≤60%)", command=open_dialog,
              font=('Arial', 12)).pack(side=tk.LEFT, padx=10)
    
    # 显示主窗口信息
    screen_w = root.winfo_screenwidth()
    screen_h = root.winfo_screenheight()
    info_label = tk.Label(root, text=f"主窗口: {screen_w}x{screen_h} (100%)", 
                         font=('Arial', 14))
    info_label.pack()
    
    root.mainloop()