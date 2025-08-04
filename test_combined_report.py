#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试 combined 模式报告生成
"""

import sys
import os

# 添加 gemsage 目录到路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'gemsage'))

from gemsage.multi_file_workflow import generate_reports_from_analyses

def test_combined_report():
    """测试 combined 模式报告生成"""
    
    # 分析结果目录（您之前生成的）
    analysis_dir = "tmp\\2025-08-04\\temp_analysis_results"  # 或者使用完整路径
    
    print("🧪 测试 combined 模式报告生成")
    print("=" * 50)
    print(f"分析目录: {analysis_dir}")
    
    # 检查目录是否存在
    if not os.path.exists(analysis_dir):
        print(f"❌ 分析目录不存在: {analysis_dir}")
        print("请先确保已经运行过分析并生成了分析结果")
        return False
    
    # 检查 analysis_summary.json 文件
    summary_file = os.path.join(analysis_dir, "analysis_summary.json")
    if not os.path.exists(summary_file):
        print(f"❌ 分析汇总文件不存在: {summary_file}")
        return False
    
    print(f"✅ 找到分析汇总文件: {summary_file}")
    
    try:
        # 调用 combined 模式
        print("\n🔄 生成 combined 模式报告...")
        success = generate_reports_from_analyses(analysis_dir, "combined")
        
        if success:
            print("\n🎉 combined 模式报告生成成功！")
            
            # 列出生成的文件
            print("\n📄 生成的报告文件:")
            for file in os.listdir("."):
                if file.endswith("_report.html") or "combined" in file:
                    print(f"   📄 {file}")
            
        else:
            print("\n❌ combined 模式报告生成失败")
            
        return success
        
    except Exception as e:
        print(f"\n❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    test_combined_report()