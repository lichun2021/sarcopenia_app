#!/usr/bin/env python3
"""
SarcNeuro Edge 测试启动脚本
"""
import sys
import os
from pathlib import Path

# 设置Python路径
sys.path.insert(0, str(Path(__file__).parent))

def test_imports():
    """测试各模块导入"""
    print("🔧 测试模块导入...")
    
    try:
        from app.config import config
        print(f"✅ 配置模块导入成功: {config.app.name} v{config.app.version}")
    except Exception as e:
        print(f"❌ 配置模块导入失败: {e}")
        return False
    
    try:
        from core.analyzer import SarcNeuroAnalyzer
        print("✅ 分析引擎导入成功")
    except Exception as e:
        print(f"❌ 分析引擎导入失败: {e}")
        return False
    
    try:
        from app.database import DatabaseManager
        print("✅ 数据库管理器导入成功")
    except Exception as e:
        print(f"❌ 数据库管理器导入失败: {e}")
        return False
    
    return True

def test_database():
    """测试数据库连接"""
    print("\n💾 测试数据库连接...")
    
    try:
        from app.database import DatabaseManager
        from app.config import config
        
        db_manager = DatabaseManager()
        print(f"✅ 数据库引擎创建成功: {config.database.url}")
        
        # 创建表
        db_manager.create_tables()
        print("✅ 数据库表创建成功")
        
        # 测试连接
        if db_manager.check_connection():
            print("✅ 数据库连接测试通过")
        else:
            print("❌ 数据库连接测试失败")
            return False
            
    except Exception as e:
        print(f"❌ 数据库测试失败: {e}")
        return False
    
    return True

def test_analyzer():
    """测试分析引擎"""
    print("\n🧠 测试分析引擎...")
    
    try:
        from core.analyzer import SarcNeuroAnalyzer, PatientInfo, PressurePoint
        
        analyzer = SarcNeuroAnalyzer()
        print("✅ 分析器实例化成功")
        
        # 创建测试数据
        patient = PatientInfo(
            name="测试患者",
            age=65,
            gender="MALE",
            height=170,
            weight=70
        )
        
        # 创建模拟压力数据
        pressure_points = [
            PressurePoint(
                time=i * 0.1,
                max_pressure=100 + i * 10,
                timestamp=f"2025-01-01 12:00:{i:02d}",
                contact_area=50 + i,
                total_pressure=1000 + i * 100,
                data=[50 + (i % 10)] * 1024  # 32x32 = 1024
            )
            for i in range(100)  # 100个数据点
        ]
        
        print(f"✅ 创建测试数据: {len(pressure_points)}个压力点")
        
        # 运行分析
        result = analyzer.comprehensive_analysis(pressure_points, patient)
        print(f"✅ 分析完成 - 评分: {result.overall_score:.1f}, 风险: {result.risk_level}")
        
    except Exception as e:
        print(f"❌ 分析引擎测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    return True

def test_api():
    """测试API服务"""
    print("\n🌐 测试API服务...")
    
    try:
        from app.main import app
        print("✅ FastAPI应用创建成功")
        
        # 检查路由
        routes = [route.path for route in app.routes]
        print(f"✅ 注册的路由: {len(routes)}个")
        for route in routes[:5]:  # 显示前5个路由
            print(f"   - {route}")
        
    except Exception as e:
        print(f"❌ API服务测试失败: {e}")
        return False
    
    return True

def main():
    """主测试函数"""
    print("🧪 SarcNeuro Edge 系统测试")
    print("=" * 50)
    
    all_tests_passed = True
    
    # 运行所有测试
    tests = [
        ("模块导入", test_imports),
        ("数据库连接", test_database),
        ("分析引擎", test_analyzer),
        ("API服务", test_api)
    ]
    
    for test_name, test_func in tests:
        try:
            if not test_func():
                all_tests_passed = False
        except Exception as e:
            print(f"❌ {test_name}测试异常: {e}")
            all_tests_passed = False
    
    print("\n" + "=" * 50)
    if all_tests_passed:
        print("🎉 所有测试通过！SarcNeuro Edge 运行正常")
        return 0
    else:
        print("⚠️  部分测试失败，请检查错误信息")
        return 1

if __name__ == "__main__":
    exit(main())