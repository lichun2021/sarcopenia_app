#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
快速检查CSV数据长度的工具
"""

import csv
import ast
import sys
import math

def check_csv_data(csv_file):
    """检查CSV文件中data字段的长度"""
    print(f"\n正在检查文件: {csv_file}")
    print("="*60)
    
    with open(csv_file, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        
        # 只检查前5行作为样本
        for i, row in enumerate(reader):
            if i >= 5:
                break
                
            # 解析data字段
            data_str = row.get('data', '')
            if data_str:
                try:
                    # 移除引号并解析
                    data_str = data_str.strip('"')
                    data = ast.literal_eval(data_str)
                    length = len(data)
                    
                    # 计算可能的矩阵维度
                    sqrt_len = math.sqrt(length)
                    
                    print(f"第{i+1}行:")
                    print(f"  - 数据长度: {length}")
                    
                    if sqrt_len == int(sqrt_len):
                        dim = int(sqrt_len)
                        print(f"  - 矩阵维度: {dim}x{dim} ✓")
                    else:
                        print(f"  - 非正方形矩阵 (√{length} = {sqrt_len:.2f})")
                        
                        # 尝试找出可能的矩阵维度
                        factors = []
                        for j in range(1, int(sqrt_len) + 2):
                            if length % j == 0:
                                factors.append((j, length // j))
                        print(f"  - 可能的维度: {factors[:5]}")
                    
                except Exception as e:
                    print(f"第{i+1}行解析失败: {e}")

def check_data_string(data_str):
    """直接检查数据字符串"""
    try:
        # 如果输入包含引号，去掉它们
        data_str = data_str.strip('"')
        
        # 解析数据
        data = ast.literal_eval(data_str)
        length = len(data)
        sqrt_len = math.sqrt(length)
        
        print(f"\n数据长度: {length}")
        
        if sqrt_len == int(sqrt_len):
            dim = int(sqrt_len)
            print(f"矩阵维度: {dim}x{dim} ✓")
        else:
            print(f"非正方形矩阵 (√{length} = {sqrt_len:.2f})")
            
        # 显示前10个和后10个元素
        print(f"前10个元素: {data[:10]}")
        print(f"后10个元素: {data[-10:]}")
        
        # 统计非零元素
        non_zero = sum(1 for x in data if x != 0)
        print(f"非零元素: {non_zero}/{length} ({100*non_zero/length:.1f}%)")
        
    except Exception as e:
        print(f"解析失败: {e}")

if __name__ == "__main__":
    if len(sys.argv) > 1:
        arg = sys.argv[1]
        
        # 检查是文件还是数据字符串
        if arg.endswith('.csv'):
            check_csv_data(arg)
        else:
            check_data_string(arg)
    else:
        print("使用方法:")
        print("  python check_data_length.py <CSV文件>")
        print("  python check_data_length.py '[数据数组]'")
        print("\n示例:")
        print("  python check_data_length.py detection_data.csv")
        print("  python check_data_length.py '[0,0,1,2,3,...]'")