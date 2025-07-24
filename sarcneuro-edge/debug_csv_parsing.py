#!/usr/bin/env python3
"""
调试CSV解析问题 - 查看具体的解析错误原因
"""
import sys
import json
from pathlib import Path

# 添加路径
sys.path.insert(0, str(Path(__file__).parent))

def debug_csv_line(line, line_number):
    """调试单行CSV解析"""
    print(f"\n🔍 调试第{line_number}行:")
    print(f"原始行长度: {len(line)}")
    print(f"原始行前100字符: {line[:100]}")
    
    # 找到前5个逗号的位置
    comma_positions = []
    for pos, char in enumerate(line):
        if char == ',' and len(comma_positions) < 5:
            comma_positions.append(pos)
    
    print(f"前5个逗号位置: {comma_positions}")
    
    if len(comma_positions) < 5:
        print(f"❌ 错误: 只找到{len(comma_positions)}个逗号，期望至少5个")
        return False
    
    # 提取各字段
    try:
        time_val = line[:comma_positions[0]]
        max_pressure = line[comma_positions[0]+1:comma_positions[1]]
        timestamp = line[comma_positions[1]+1:comma_positions[2]]
        contact_area = line[comma_positions[2]+1:comma_positions[3]]
        total_pressure = line[comma_positions[3]+1:comma_positions[4]]
        json_data = line[comma_positions[4]+1:].strip()
        
        print(f"时间: '{time_val}'")
        print(f"最大压力: '{max_pressure}'")
        print(f"时间戳: '{timestamp}'")
        print(f"接触面积: '{contact_area}'")
        print(f"总压力: '{total_pressure}'")
        print(f"JSON数据长度: {len(json_data)}")
        print(f"JSON数据前50字符: {json_data[:50]}")
        print(f"JSON数据后50字符: {json_data[-50:]}")
        
        # 尝试解析JSON
        try:
            data_array = json.loads(json_data)
            print(f"✅ JSON解析成功，数组长度: {len(data_array)}")
            if len(data_array) != 1024:
                print(f"⚠️  警告: 数组长度{len(data_array)}，期望1024")
            return True
        except json.JSONDecodeError as e:
            print(f"❌ JSON解析失败: {e}")
            print(f"错误位置: {e.pos}")
            if e.pos < len(json_data):
                print(f"错误附近内容: {json_data[max(0, e.pos-10):e.pos+10]}")
            return False
            
    except Exception as e:
        print(f"❌ 字段提取失败: {e}")
        return False

def debug_csv_content(csv_content):
    """调试整个CSV内容"""
    print("🧪 开始调试CSV解析...")
    
    lines = csv_content.strip().split('\n')
    print(f"总行数: {len(lines)}")
    
    if len(lines) < 2:
        print("❌ 错误: CSV数据行数不足")
        return
    
    # 检查标题行
    header = lines[0]
    print(f"\n📋 标题行: {header}")
    
    # 调试前几行数据
    success_count = 0
    for i, line in enumerate(lines[1:min(4, len(lines))], 1):
        if debug_csv_line(line, i):
            success_count += 1
    
    print(f"\n📊 调试结果: {success_count}/{min(3, len(lines)-1)} 行解析成功")

# 测试不同的CSV格式
def test_different_formats():
    """测试不同的CSV格式"""
    print("🔬 测试不同CSV格式...")
    
    # 格式1: JSON无引号
    format1 = """time,max_pressure,timestamp,contact_area,total_pressure,data
0.1,85,2025-01-24 12:00:01,45,3825,[1,2,3,4,5]"""
    
    print("\n=== 格式1: JSON无引号 ===")
    debug_csv_content(format1)
    
    # 格式2: JSON有双引号
    format2 = """time,max_pressure,timestamp,contact_area,total_pressure,data
0.1,85,2025-01-24 12:00:01,45,3825,"[1,2,3,4,5]" """
    
    print("\n=== 格式2: JSON有双引号 ===")
    debug_csv_content(format2)
    
    # 格式3: 空数据
    format3 = """time,max_pressure,timestamp,contact_area,total_pressure,data
0.1,85,2025-01-24 12:00:01,45,3825,[]"""
    
    print("\n=== 格式3: 空JSON数组 ===")
    debug_csv_content(format3)
    
    # 格式4: 非法JSON
    format4 = """time,max_pressure,timestamp,contact_area,total_pressure,data
0.1,85,2025-01-24 12:00:01,45,3825,[1,2,3,4,5"""
    
    print("\n=== 格式4: 非法JSON ===")
    debug_csv_content(format4)

if __name__ == "__main__":
    test_different_formats()