#!/usr/bin/env python3
"""
测试真实CSV文件可能遇到的各种问题
"""
import sys
from pathlib import Path

# 添加路径
sys.path.insert(0, str(Path(__file__).parent))

from core.analyzer import SarcNeuroAnalyzer, PatientInfo

def test_problematic_csv_formats():
    """测试各种可能有问题的CSV格式"""
    analyzer = SarcNeuroAnalyzer()
    
    # 测试案例1: 标题行不匹配
    test1 = """Time,MaxPressure,Timestamp,ContactArea,TotalPressure,Data
0.1,85,2025-01-24 12:00:01,45,3825,[1,2,3,4,5,6,7,8]"""
    
    print("🧪 测试1: 标题行不匹配")
    try:
        points = analyzer.parse_csv_data(test1)
        print(f"✅ 成功解析 {len(points)} 个数据点")
    except Exception as e:
        print(f"❌ 解析失败: {e}")
    
    # 测试案例2: 缺少字段
    test2 = """time,max_pressure,timestamp,contact_area,total_pressure,data
0.1,85,2025-01-24 12:00:01,45"""
    
    print("\n🧪 测试2: 缺少字段")
    try:
        points = analyzer.parse_csv_data(test2)
        print(f"✅ 成功解析 {len(points)} 个数据点")
    except Exception as e:
        print(f"❌ 解析失败: {e}")
    
    # 测试案例3: JSON数据有问题
    test3 = """time,max_pressure,timestamp,contact_area,total_pressure,data
0.1,85,2025-01-24 12:00:01,45,3825,[1,2,3,4,5
0.2,90,2025-01-24 12:00:02,50,4500,"[1,2,3,4,5,6,7,8]" """
    
    print("\n🧪 测试3: 混合JSON格式问题")
    try:
        points = analyzer.parse_csv_data(test3)
        print(f"✅ 成功解析 {len(points)} 个数据点")
    except Exception as e:
        print(f"❌ 解析失败: {e}")
    
    # 测试案例4: 空数据
    test4 = """time,max_pressure,timestamp,contact_area,total_pressure,data"""
    
    print("\n🧪 测试4: 只有标题行，无数据")
    try:
        points = analyzer.parse_csv_data(test4)
        print(f"✅ 成功解析 {len(points)} 个数据点")
    except Exception as e:
        print(f"❌ 解析失败: {e}")
    
    # 测试案例5: 正常但短数组
    test5 = """time,max_pressure,timestamp,contact_area,total_pressure,data
0.1,85,2025-01-24 12:00:01,45,3825,[1,2,3,4,5,6,7,8,9,10]
0.2,90,2025-01-24 12:00:02,50,4500,[11,12,13,14,15,16,17,18,19,20]"""
    
    print("\n🧪 测试5: 正常格式但数组长度不是1024")
    try:
        points = analyzer.parse_csv_data(test5)
        print(f"✅ 成功解析 {len(points)} 个数据点")
        if len(points) > 0:
            print(f"第一个数据点的数组长度: {len(points[0].data)}")
    except Exception as e:
        print(f"❌ 解析失败: {e}")

if __name__ == "__main__":
    test_problematic_csv_formats()