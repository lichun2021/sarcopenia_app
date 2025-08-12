#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Windows系统报告生成启动脚本
解决路径和编码问题
"""

import sys
import os
from pathlib import Path

# 确保正确的编码
if sys.platform == 'win32':
    import locale
    if locale.getpreferredencoding().upper() != 'UTF-8':
        os.environ['PYTHONIOENCODING'] = 'utf-8'

# 添加当前目录到Python路径
current_dir = Path(__file__).parent.absolute()
sys.path.insert(0, str(current_dir))

# 设置matplotlib中文支持
try:
    import matplotlib
    matplotlib.use('Agg')  # 使用非GUI后端
    import matplotlib.pyplot as plt
    
    # Windows中文字体设置
    if sys.platform == 'win32':
        # 尝试多个中文字体
        chinese_fonts = ['SimHei', 'Microsoft YaHei', 'SimSun', 'KaiTi']
        available_font = None
        for font in chinese_fonts:
            try:
                plt.rcParams['font.sans-serif'] = [font]
                available_font = font
                break
            except:
                continue
        if not available_font:
            print("⚠️ 未找到中文字体，图表可能显示方块")
    else:
        plt.rcParams['font.sans-serif'] = ['DejaVu Sans']
    plt.rcParams['axes.unicode_minus'] = False
except ImportError:
    print("⚠️ matplotlib未安装，图表功能将不可用")
    print("   请运行: pip install matplotlib")

# 导入核心模块
try:
    from core_calculator_final import PressureAnalysisFinal
    from generate_complete_report_final import generate_report_with_final_algorithm
    from full_medical_report_generator import FullMedicalReportGenerator
    print("✅ 核心模块导入成功")
except ImportError as e:
    print(f"❌ 模块导入失败: {e}")
    print("请确保以下文件在同一目录下：")
    print("  - core_calculator_final.py")
    print("  - generate_complete_report_final.py")
    print("  - full_medical_report_generator.py")
    sys.exit(1)

def find_test_file():
    """查找可用的测试文件"""
    # 可能的测试文件路径
    possible_paths = [
        # 相对路径
        Path("数据") / "2025-08-09 2" / "detection_data",
        Path("数据") / "2025-08-09 3" / "detection_data",
        Path("数据") / "2025-08-09 4" / "detection_data",
        Path("archive") / "detection_data",
        # 当前目录
        Path("."),
    ]
    
    # 查找CSV文件
    for base_path in possible_paths:
        if base_path.exists():
            csv_files = list(base_path.glob("*第6步*4.5米步道折返*.csv"))
            if csv_files:
                return csv_files[0]
    
    # 让用户输入
    return None

def generate_report_windows(csv_file=None):
    """Windows系统生成报告主函数"""
    
    print("="*60)
    print("📊 足部压力分析报告生成系统 (Windows版)")
    print("="*60)
    
    # 1. 确定CSV文件
    if csv_file is None:
        # 自动查找
        csv_file = find_test_file()
        
        if csv_file is None:
            # 手动输入
            print("\n请输入CSV文件路径：")
            print("（可以拖拽文件到此窗口，或复制完整路径）")
            csv_path = input("> ").strip().strip('"')  # 去除可能的引号
            csv_file = Path(csv_path)
    else:
        csv_file = Path(csv_file)
    
    # 2. 检查文件存在
    if not csv_file.exists():
        print(f"❌ 文件不存在: {csv_file}")
        return None
    
    print(f"\n📁 使用数据文件: {csv_file.name}")
    print(f"   完整路径: {csv_file.absolute()}")
    
    # 3. 分析数据
    try:
        print("\n⏳ 正在分析数据...")
        analyzer = PressureAnalysisFinal()
        result = analyzer.comprehensive_analysis_final(str(csv_file))
        
        if 'error' in result:
            print(f"❌ 分析失败: {result['error']}")
            return None
        
        # 显示关键参数
        gait_params = result.get('gait_parameters', {})
        print(f"\n📊 分析结果:")
        print(f"   步数: {gait_params.get('step_count', 0)}")
        print(f"   平均步长: {gait_params.get('average_step_length', 0):.2f} cm")
        print(f"   步频: {gait_params.get('cadence', 0):.2f} 步/分")
        print(f"   速度: {gait_params.get('average_velocity', 0):.2f} m/s")
        
    except Exception as e:
        print(f"❌ 算法分析出错: {e}")
        import traceback
        traceback.print_exc()
        return None
    
    # 4. 生成报告
    try:
        print("\n⏳ 正在生成HTML报告...")
        
        # 直接调用生成函数
        report_path = generate_report_with_final_algorithm(str(csv_file))
        
        if report_path and Path(report_path).exists():
            print(f"\n✅ 报告生成成功！")
            print(f"   文件: {report_path}")
            
            # Windows下自动打开
            if sys.platform == 'win32':
                try:
                    os.startfile(report_path)
                    print("   已自动打开报告")
                except:
                    print("   请手动打开HTML文件查看")
            
            return report_path
        else:
            print(f"❌ 报告生成失败")
            return None
            
    except Exception as e:
        print(f"❌ 报告生成出错: {e}")
        import traceback
        traceback.print_exc()
        return None

def check_dependencies():
    """检查依赖库"""
    required = ['numpy', 'pandas', 'matplotlib', 'jinja2']
    missing = []
    
    for lib in required:
        try:
            __import__(lib)
        except ImportError:
            missing.append(lib)
    
    if missing:
        print("❌ 缺少依赖库，请安装：")
        print(f"   pip install {' '.join(missing)}")
        return False
    return True

def main():
    """主函数"""
    # 检查依赖
    if not check_dependencies():
        print("\n请先安装缺失的依赖库")
        input("按Enter键退出...")
        return
    
    # 处理命令行参数
    if len(sys.argv) > 1:
        csv_file = sys.argv[1]
    else:
        csv_file = None
    
    # 生成报告
    report = generate_report_windows(csv_file)
    
    if report:
        print("\n" + "="*60)
        print("✅ 任务完成！")
    else:
        print("\n" + "="*60)
        print("❌ 任务失败，请检查错误信息")
    
    # Windows下暂停
    if sys.platform == 'win32':
        input("\n按Enter键退出...")

if __name__ == "__main__":
    main()