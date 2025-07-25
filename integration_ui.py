"""
集成 SarcNeuro Edge 服务的 UI 扩展模块
为主 UI 添加肌少症分析功能
"""
import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext, filedialog
import threading
import json
import time
from datetime import datetime
from pathlib import Path

from data_converter import SarcopeniaDataConverter
from sarcneuro_service import SarcNeuroEdgeService


class SarcopeniaAnalysisPanel:
    """肌少症分析面板"""
    
    def __init__(self, parent_frame, main_ui_instance):
        self.parent = parent_frame
        self.main_ui = main_ui_instance
        self.converter = SarcopeniaDataConverter()
        self.sarcneuro_service = None
        
        # 数据收集
        self.collected_frames = []
        self.is_collecting = False
        self.collection_start_time = None
        self.collection_duration = 30  # 默认30秒
        
        # 患者信息
        self.patient_info = {}
        
        # 创建UI
        self.create_analysis_panel()
        
        # 初始化服务
        self.init_service()
    
    def create_analysis_panel(self):
        """创建分析面板UI"""
        # 主框架
        analysis_frame = ttk.LabelFrame(self.parent, text="🧠 肌少症智能分析", padding="10")
        analysis_frame.pack(fill="both", expand=True, padx=5, pady=5)
        
        # 服务状态框架
        status_frame = ttk.LabelFrame(analysis_frame, text="服务状态", padding="5")
        status_frame.pack(fill="x", pady=(0, 10))
        
        self.service_status_var = tk.StringVar(value="🔴 服务未启动")
        ttk.Label(status_frame, textvariable=self.service_status_var, font=('Arial', 10)).pack(side="left")
        
        ttk.Button(status_frame, text="启动服务", command=self.start_service).pack(side="right", padx=(5, 0))
        ttk.Button(status_frame, text="重启服务", command=self.restart_service).pack(side="right", padx=(5, 0))
        
        # 患者信息框架
        patient_frame = ttk.LabelFrame(analysis_frame, text="患者信息", padding="5")
        patient_frame.pack(fill="x", pady=(0, 10))
        
        # 患者信息输入
        info_grid = ttk.Frame(patient_frame)
        info_grid.pack(fill="x")
        
        # 第一行
        ttk.Label(info_grid, text="姓名:").grid(row=0, column=0, sticky="w", padx=(0, 5))
        self.name_var = tk.StringVar(value="测试患者")
        ttk.Entry(info_grid, textvariable=self.name_var, width=15).grid(row=0, column=1, padx=(0, 10))
        
        ttk.Label(info_grid, text="年龄:").grid(row=0, column=2, sticky="w", padx=(0, 5))
        self.age_var = tk.StringVar(value="65")
        ttk.Entry(info_grid, textvariable=self.age_var, width=8).grid(row=0, column=3, padx=(0, 10))
        
        ttk.Label(info_grid, text="性别:").grid(row=0, column=4, sticky="w", padx=(0, 5))
        self.gender_var = tk.StringVar(value="男")
        gender_combo = ttk.Combobox(info_grid, textvariable=self.gender_var, values=["男", "女"], width=6)
        gender_combo.grid(row=0, column=5, padx=(0, 10))
        gender_combo.state(["readonly"])
        
        # 第二行
        ttk.Label(info_grid, text="身高(cm):").grid(row=1, column=0, sticky="w", padx=(0, 5), pady=(5, 0))
        self.height_var = tk.StringVar(value="170")
        ttk.Entry(info_grid, textvariable=self.height_var, width=10).grid(row=1, column=1, padx=(0, 10), pady=(5, 0))
        
        ttk.Label(info_grid, text="体重(kg):").grid(row=1, column=2, sticky="w", padx=(0, 5), pady=(5, 0))
        self.weight_var = tk.StringVar(value="70")
        ttk.Entry(info_grid, textvariable=self.weight_var, width=10).grid(row=1, column=3, padx=(0, 10), pady=(5, 0))
        
        # 数据收集框架
        collection_frame = ttk.LabelFrame(analysis_frame, text="数据收集", padding="5")
        collection_frame.pack(fill="x", pady=(0, 10))
        
        collect_grid = ttk.Frame(collection_frame)
        collect_grid.pack(fill="x")
        
        # 收集时长设置
        ttk.Label(collect_grid, text="收集时长(秒):").pack(side="left")
        self.duration_var = tk.StringVar(value="30")
        duration_spin = tk.Spinbox(collect_grid, from_=5, to=300, textvariable=self.duration_var, width=8)
        duration_spin.pack(side="left", padx=(5, 15))
        
        # 收集状态
        self.collection_status_var = tk.StringVar(value="准备收集")
        ttk.Label(collect_grid, textvariable=self.collection_status_var).pack(side="left", padx=(0, 15))
        
        # 收集按钮
        self.collect_btn = ttk.Button(collect_grid, text="开始收集", command=self.start_collection)
        self.collect_btn.pack(side="right", padx=(5, 0))
        
        ttk.Button(collect_grid, text="停止收集", command=self.stop_collection).pack(side="right", padx=(5, 0))
        
        # 进度条
        self.progress_var = tk.DoubleVar()
        self.progress_bar = ttk.Progressbar(collection_frame, variable=self.progress_var, maximum=100)
        self.progress_bar.pack(fill="x", pady=(5, 0))
        
        # 分析按钮框架
        action_frame = ttk.Frame(analysis_frame)
        action_frame.pack(fill="x", pady=(0, 10))
        
        ttk.Button(action_frame, text="立即分析", command=self.analyze_current_data, 
                  style="Accent.TButton").pack(side="left", padx=(0, 10))
        ttk.Button(action_frame, text="加载CSV", command=self.load_csv_file).pack(side="left", padx=(0, 10))
        ttk.Button(action_frame, text="保存数据", command=self.save_collected_data).pack(side="left", padx=(0, 10))
        
        # 结果显示框架
        result_frame = ttk.LabelFrame(analysis_frame, text="分析结果", padding="5")
        result_frame.pack(fill="both", expand=True)
        
        # 结果文本框
        self.result_text = scrolledtext.ScrolledText(
            result_frame, 
            height=15, 
            font=('Consolas', 10),
            wrap=tk.WORD
        )
        self.result_text.pack(fill="both", expand=True)
        
        # 初始提示
        self.result_text.insert(tk.END, """
🧠 肌少症智能分析系统已就绪

📋 使用步骤:
1. 填写患者基本信息
2. 启动 SarcNeuro Edge 分析服务
3. 开始数据收集 (建议30-60秒)
4. 点击"立即分析"进行智能评估

提示:
- 确保患者站立在压力传感器上
- 数据收集期间保持静止或正常步态
- 分析结果包含步态分析、平衡评估和风险等级
        """)
    
    def init_service(self):
        """初始化分析服务"""
        try:
            self.sarcneuro_service = SarcNeuroEdgeService(port=8000)
            self.update_service_status()
        except Exception as e:
            self.log_result(f"❌ 服务初始化失败: {e}")
    
    def start_service(self):
        """启动分析服务"""
        def start_in_thread():
            try:
                self.log_result("🚀 正在启动 SarcNeuro Edge 服务...")
                self.service_status_var.set("🟡 正在启动...")
                
                if self.sarcneuro_service.start_service():
                    self.service_status_var.set("🟢 服务运行中")
                    self.log_result("✅ SarcNeuro Edge 服务启动成功！")
                else:
                    self.service_status_var.set("🔴 启动失败")
                    self.log_result("❌ SarcNeuro Edge 服务启动失败")
                    
            except Exception as e:
                self.service_status_var.set("🔴 启动异常")
                self.log_result(f"❌ 服务启动异常: {e}")
        
        threading.Thread(target=start_in_thread, daemon=True).start()
    
    def restart_service(self):
        """重启分析服务"""
        def restart_in_thread():
            try:
                self.log_result("🔄 重启服务中...")
                self.service_status_var.set("🟡 重启中...")
                
                if self.sarcneuro_service:
                    self.sarcneuro_service.stop_service()
                    time.sleep(2)
                    
                    if self.sarcneuro_service.start_service():
                        self.service_status_var.set("🟢 服务运行中")
                        self.log_result("✅ 服务重启成功！")
                    else:
                        self.service_status_var.set("🔴 重启失败")
                        self.log_result("❌ 服务重启失败")
                        
            except Exception as e:
                self.service_status_var.set("🔴 重启异常")
                self.log_result(f"❌ 服务重启异常: {e}")
        
        threading.Thread(target=restart_in_thread, daemon=True).start()
    
    def update_service_status(self):
        """更新服务状态"""
        if self.sarcneuro_service and self.sarcneuro_service.is_running:
            self.service_status_var.set("🟢 服务运行中")
        else:
            self.service_status_var.set("🔴 服务未启动")
        
        # 定时更新
        self.parent.after(10000, self.update_service_status)  # 每10秒更新一次
    
    def start_collection(self):
        """开始数据收集"""
        if self.is_collecting:
            return
        
        try:
            self.collection_duration = int(self.duration_var.get())
            if self.collection_duration < 5 or self.collection_duration > 300:
                messagebox.showerror("参数错误", "收集时长应在5-300秒之间")
                return
        except ValueError:
            messagebox.showerror("参数错误", "请输入有效的收集时长")
            return
        
        # 检查主UI是否在运行
        if not self.main_ui.is_running:
            messagebox.showwarning("数据源未就绪", "请先启动压力传感器数据采集")
            return
        
        # 开始收集
        self.is_collecting = True
        self.collected_frames = []
        self.collection_start_time = time.time()
        self.progress_var.set(0)
        
        self.collection_status_var.set("正在收集数据...")
        self.collect_btn.config(state="disabled")
        
        self.log_result(f"开始收集数据，预计时长: {self.collection_duration}秒")
        
        # 启动收集线程
        threading.Thread(target=self.collection_worker, daemon=True).start()
    
    def collection_worker(self):
        """数据收集工作线程"""
        try:
            while self.is_collecting and time.time() - self.collection_start_time < self.collection_duration:
                # 从主UI获取最新的压力数据
                if (hasattr(self.main_ui, 'data_processor') and 
                    self.main_ui.data_processor and 
                    hasattr(self.main_ui.data_processor, 'latest_pressure_array')):
                    
                    latest_data = self.main_ui.data_processor.latest_pressure_array
                    if latest_data is not None and len(latest_data) > 0:
                        self.collected_frames.append(list(latest_data))
                
                # 更新进度
                elapsed = time.time() - self.collection_start_time
                progress = min((elapsed / self.collection_duration) * 100, 100)
                self.progress_var.set(progress)
                
                time.sleep(0.1)  # 100ms 间隔
            
            # 收集完成
            self.is_collecting = False
            self.collection_status_var.set(f"✅ 已收集 {len(self.collected_frames)} 帧")
            self.collect_btn.config(state="normal")
            self.progress_var.set(100)
            
            if len(self.collected_frames) > 0:
                quality = self.converter.estimate_quality_metrics(self.collected_frames)
                self.log_result(f"数据收集完成！")
                self.log_result(f"   - 总帧数: {len(self.collected_frames)}")
                self.log_result(f"   - 数据质量: {quality['quality']} ({quality['score']}分)")
                self.log_result(f"   - 有效帧率: {quality['validity_ratio']}%")
            else:
                self.log_result("未收集到有效数据，请检查传感器连接")
                
        except Exception as e:
            self.is_collecting = False
            self.collection_status_var.set("❌ 收集异常")
            self.collect_btn.config(state="normal")
            self.log_result(f"❌ 数据收集异常: {e}")
    
    def stop_collection(self):
        """停止数据收集"""
        if self.is_collecting:
            self.is_collecting = False
            self.collection_status_var.set("已停止收集")
            self.collect_btn.config(state="normal")
            self.log_result("数据收集已停止")
    
    def analyze_current_data(self):
        """分析当前收集的数据"""
        if not self.collected_frames:
            messagebox.showwarning("无数据", "请先收集压力数据或加载CSV文件")
            return
        
        if not self.sarcneuro_service or not self.sarcneuro_service.is_running:
            messagebox.showerror("服务未就绪", "请先启动 SarcNeuro Edge 分析服务")
            return
        
        # 获取患者信息
        try:
            patient_info = self.get_patient_info()
        except ValueError as e:
            messagebox.showerror("参数错误", str(e))
            return
        
        # 在后台线程中进行分析
        def analyze_in_thread():
            try:
                self.log_result("开始智能分析...")
                self.log_result(f"   - 患者: {patient_info['name']}, {patient_info['age']}岁")
                self.log_result(f"   - 数据帧数: {len(self.collected_frames)}")
                
                # 转换数据格式
                csv_data = self.converter.convert_frames_to_csv(self.collected_frames, frame_rate=10.0)
                
                # 发送分析请求
                result = self.sarcneuro_service.analyze_data(csv_data, patient_info)
                
                if result and result.get('status') == 'success':
                    self.display_analysis_result(result['data'])
                    self.log_result("✅ 分析完成！")
                else:
                    error_msg = result.get('message', '未知错误') if result else '服务无响应'
                    self.log_result(f"❌ 分析失败: {error_msg}")
                    
            except Exception as e:
                self.log_result(f"❌ 分析过程异常: {e}")
        
        threading.Thread(target=analyze_in_thread, daemon=True).start()
    
    def get_patient_info(self):
        """获取患者信息"""
        try:
            age = int(self.age_var.get())
            if age <= 0 or age > 120:
                raise ValueError("年龄应在1-120岁之间")
                
            height = float(self.height_var.get()) if self.height_var.get() else None
            if height is not None and (height < 50 or height > 250):
                raise ValueError("身高应在50-250cm之间")
                
            weight = float(self.weight_var.get()) if self.weight_var.get() else None
            if weight is not None and (weight < 10 or weight > 200):
                raise ValueError("体重应在10-200kg之间")
                
        except ValueError as e:
            raise ValueError(f"参数错误: {e}")
        
        return self.converter.create_patient_info_dict(
            name=self.name_var.get() or "未知患者",
            age=age,
            gender=self.gender_var.get(),
            height=height,
            weight=weight
        )
    
    def display_analysis_result(self, result_data):
        """显示分析结果"""
        try:
            # 清空之前的结果
            self.result_text.delete(1.0, tk.END)
            
            # 分析基本信息
            self.result_text.insert(tk.END, "🧠 肌少症智能分析报告\n")
            self.result_text.insert(tk.END, f"{'='*50}\n\n")
            
            # 患者信息
            self.result_text.insert(tk.END, f"👤 患者信息: {result_data.get('patient_name', 'N/A')}\n")
            self.result_text.insert(tk.END, f"📋 测试类型: {result_data.get('test_type', 'N/A')}\n")
            self.result_text.insert(tk.END, f"分析时间: {result_data.get('processing_time', 0):.0f}ms\n\n")
            
            # 核心评估结果
            overall_score = result_data.get('overall_score', 0)
            risk_level = result_data.get('risk_level', 'UNKNOWN')
            confidence = result_data.get('confidence', 0)
            
            # 风险等级颜色和描述
            risk_info = {
                'LOW': {'color': '🟢', 'desc': '低风险'},
                'MEDIUM': {'color': '🟡', 'desc': '中等风险'},
                'HIGH': {'color': '🟠', 'desc': '高风险'},
                'CRITICAL': {'color': '🔴', 'desc': '极高风险'}
            }
            
            risk_display = risk_info.get(risk_level, {'color': '⚪', 'desc': '未知'})
            
            self.result_text.insert(tk.END, f"综合评分: {overall_score:.1f}/100\n")
            self.result_text.insert(tk.END, f"风险等级: {risk_display['color']} {risk_display['desc']} ({risk_level})\n")
            self.result_text.insert(tk.END, f"置信度: {confidence:.1%}\n\n")
            
            # 医学解释
            interpretation = result_data.get('interpretation', '无解释信息')
            self.result_text.insert(tk.END, f"🏥 医学解释:\n{interpretation}\n\n")
            
            # 异常检测
            abnormalities = result_data.get('abnormalities', [])
            if abnormalities:
                self.result_text.insert(tk.END, f"检测到的异常 ({len(abnormalities)}项):\n")
                for i, abnormality in enumerate(abnormalities, 1):
                    self.result_text.insert(tk.END, f"   {i}. {abnormality}\n")
                self.result_text.insert(tk.END, "\n")
            
            # 详细分析数据
            detailed = result_data.get('detailed_analysis', {})
            if detailed:
                # 步态分析
                gait = detailed.get('gait_analysis', {})
                if gait:
                    self.result_text.insert(tk.END, "🚶 步态分析结果:\n")
                    self.result_text.insert(tk.END, f"   - 步行速度: {gait.get('walking_speed', 0):.3f} m/s\n")
                    self.result_text.insert(tk.END, f"   - 步长: {gait.get('step_length', 0):.1f} cm\n")
                    self.result_text.insert(tk.END, f"   - 步频: {gait.get('cadence', 0):.1f} 步/分钟\n")
                    self.result_text.insert(tk.END, f"   - 不对称指数: {gait.get('asymmetry_index', 0):.3f}\n")
                    self.result_text.insert(tk.END, f"   - 稳定性评分: {gait.get('stability_score', 0):.1f}\n\n")
                
                # 平衡分析
                balance = detailed.get('balance_analysis', {})
                if balance:
                    self.result_text.insert(tk.END, "平衡分析结果:\n")
                    self.result_text.insert(tk.END, f"   - 压力中心位移: {balance.get('cop_displacement', 0):.2f} mm\n")
                    self.result_text.insert(tk.END, f"   - 摆动面积: {balance.get('sway_area', 0):.2f} mm²\n")
                    self.result_text.insert(tk.END, f"   - 摆动速度: {balance.get('sway_velocity', 0):.2f} mm/s\n")
                    self.result_text.insert(tk.END, f"   - 稳定性指数: {balance.get('stability_index', 0):.2f}\n")
                    self.result_text.insert(tk.END, f"   - 跌倒风险: {balance.get('fall_risk_score', 0):.1%}\n\n")
            
            # 康复建议
            recommendations = result_data.get('recommendations', [])
            if recommendations:
                self.result_text.insert(tk.END, f"康复建议 ({len(recommendations)}项):\n")
                for i, recommendation in enumerate(recommendations, 1):
                    self.result_text.insert(tk.END, f"   {i}. {recommendation}\n")
                self.result_text.insert(tk.END, "\n")
            
            # 报告生成时间
            self.result_text.insert(tk.END, f"📅 报告生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            self.result_text.insert(tk.END, f"🔬 分析版本: SarcNeuro Edge v1.0.0\n")
            
        except Exception as e:
            self.log_result(f"❌ 结果显示异常: {e}")
    
    def load_csv_file(self):
        """加载CSV文件"""
        file_path = filedialog.askopenfilename(
            title="选择CSV数据文件",
            filetypes=[("CSV files", "*.csv"), ("All files", "*.*")]
        )
        
        if not file_path:
            return
        
        try:
            # 读取CSV文件并解析为压力帧数据
            import pandas as pd
            import json
            
            df = pd.read_csv(file_path)
            
            if 'data' not in df.columns:
                messagebox.showerror("文件格式错误", "CSV文件必须包含'data'列")
                return
            
            frames = []
            for _, row in df.iterrows():
                try:
                    data_array = json.loads(row['data'])
                    if len(data_array) in [1024, 2048, 3072]:
                        frames.append(data_array)
                except:
                    continue
            
            if frames:
                self.collected_frames = frames
                self.collection_status_var.set(f"已加载 {len(frames)} 帧")
                quality = self.converter.estimate_quality_metrics(frames)
                self.log_result(f"✅ 成功加载CSV文件: {Path(file_path).name}")
                self.log_result(f"   - 有效帧数: {len(frames)}")
                self.log_result(f"   - 数据质量: {quality['quality']} ({quality['score']}分)")
            else:
                messagebox.showerror("数据无效", "CSV文件中没有有效的压力数据")
                
        except Exception as e:
            messagebox.showerror("加载失败", f"无法加载CSV文件: {e}")
    
    def save_collected_data(self):
        """保存收集的数据"""
        if not self.collected_frames:
            messagebox.showwarning("无数据", "没有收集到的数据可保存")
            return
        
        file_path = filedialog.asksaveasfilename(
            title="保存数据文件",
            defaultextension=".csv",
            filetypes=[("CSV files", "*.csv"), ("All files", "*.*")]
        )
        
        if not file_path:
            return
        
        try:
            csv_data = self.converter.convert_frames_to_csv(self.collected_frames, frame_rate=10.0)
            
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(csv_data)
            
            self.log_result(f"数据已保存到: {Path(file_path).name}")
            messagebox.showinfo("保存成功", f"数据已保存到:\n{file_path}")
            
        except Exception as e:
            messagebox.showerror("保存失败", f"无法保存数据: {e}")
    
    def log_result(self, message):
        """记录结果日志"""
        try:
            timestamp = datetime.now().strftime("%H:%M:%S")
            log_message = f"[{timestamp}] {message}\n"
            
            # 插入到结果文本框
            self.result_text.insert(tk.END, log_message)
            self.result_text.see(tk.END)  # 滚动到底部
            
        except Exception:
            pass  # 忽略日志记录错误


def integrate_sarcneuro_analysis(main_ui_instance):
    """
    为主UI集成肌少症分析功能
    
    Args:
        main_ui_instance: 主UI实例
    """
    try:
        # 查找现有的notebook控件
        for child in main_ui_instance.root.winfo_children():
            if isinstance(child, ttk.Notebook):
                # 添加肌少症分析选项卡
                analysis_frame = ttk.Frame(child)
                child.add(analysis_frame, text="🧠 肌少症分析")
                
                # 创建分析面板
                analysis_panel = SarcopeniaAnalysisPanel(analysis_frame, main_ui_instance)
                
                # 将分析面板添加到主UI实例
                main_ui_instance.sarcneuro_panel = analysis_panel
                
                return analysis_panel
    
    except Exception as e:
        print(f"集成肌少症分析功能失败: {e}")
        return None


# 测试代码
if __name__ == "__main__":
    root = tk.Tk()
    
    # 创建测试框架
    test_frame = ttk.Frame(root)
    test_frame.pack(fill="both", expand=True, padx=10, pady=10)
    
    # 创建模拟的主UI实例
    class MockMainUI:
        def __init__(self):
            self.is_running = False
            self.data_processor = None
    
    mock_ui = MockMainUI()
    
    # 创建分析面板
    analysis_panel = SarcopeniaAnalysisPanel(test_frame, mock_ui)
    
    root.title("肌少症分析面板测试")
    root.geometry("800x900")
    
    # 设置窗口图标
    try:
        root.iconbitmap("icon.ico")
    except Exception:
        pass
    root.mainloop()