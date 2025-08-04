#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试gemsage算法引擎是否正确加载
"""

import sys
import os

def test_gemsage_import():
    """测试gemsage模块导入"""
    print("=== 测试gemsage模块导入 ===")
    
    try:
        # 添加gemsage目录到路径
        gemsage_path = os.path.join(os.path.dirname(__file__), 'gemsage')
        if gemsage_path not in sys.path:
            sys.path.insert(0, gemsage_path)
        
        print(f"gemsage路径: {gemsage_path}")
        print(f"gemsage目录存在: {os.path.exists(gemsage_path)}")
        
        # 测试导入core_calculator
        from gemsage.core_calculator import PressureAnalysisCore
        analyzer = PressureAnalysisCore()
        print("✅ 成功导入gemsage.core_calculator.PressureAnalysisCore")
        
        # 测试导入AI评估引擎
        from gemsage.ai_assessment_engine import AIAssessmentEngine
        ai_engine = AIAssessmentEngine()
        print("✅ 成功导入gemsage.ai_assessment_engine.AIAssessmentEngine")
        
        return True
        
    except ImportError as e:
        print(f"❌ gemsage模块导入失败: {e}")
        return False

def test_algorithm_engine():
    """测试算法引擎管理器"""
    print("\n=== 测试算法引擎管理器 ===")
    
    try:
        from algorithm_engine_manager import get_algorithm_engine
        
        # 获取算法引擎
        engine = get_algorithm_engine()
        print(f"算法引擎初始化状态: {engine.is_initialized}")
        
        # 检查引擎类型
        if hasattr(engine, 'analyzer') and engine.analyzer:
            analyzer_type = type(engine.analyzer).__name__
            print(f"分析器类型: {analyzer_type}")
            
            if analyzer_type == "MockPressureAnalysisCore":
                print("⚠️  仍在使用模拟分析器")
                return False
            else:
                print("✅ 使用真实分析器")
                
        if hasattr(engine, 'ai_engine') and engine.ai_engine:
            ai_engine_type = type(engine.ai_engine).__name__
            print(f"AI引擎类型: {ai_engine_type}")
            print("✅ AI引擎已加载")
        else:
            print("⚠️  AI引擎未加载")
            
        return True
        
    except Exception as e:
        print(f"❌ 算法引擎测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("开始测试gemsage算法引擎...")
    
    # 测试gemsage模块导入
    gemsage_ok = test_gemsage_import()
    
    # 测试算法引擎管理器
    engine_ok = test_algorithm_engine()
    
    print(f"\n=== 测试结果 ===")
    print(f"gemsage模块导入: {'✅ 成功' if gemsage_ok else '❌ 失败'}")
    print(f"算法引擎管理器: {'✅ 成功' if engine_ok else '❌ 失败'}")
    
    if gemsage_ok and engine_ok:
        print("🎉 gemsage算法引擎测试通过！")
    else:
        print("🚨 gemsage算法引擎测试失败！")