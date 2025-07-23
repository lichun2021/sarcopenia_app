#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
集成测试脚本
测试 SarcNeuro Edge 服务集成和数据转换功能
"""

import sys
import time
import traceback
from datetime import datetime
from pathlib import Path

# 添加当前目录到路径
sys.path.insert(0, str(Path(__file__).parent))

def test_data_converter():
    """测试数据转换器"""
    print("🔄 测试数据转换器...")
    
    try:
        from data_converter import SarcopeniaDataConverter
        
        converter = SarcopeniaDataConverter()
        
        # 创建模拟数据
        import numpy as np
        test_frames = []
        for i in range(50):  # 50帧数据，5秒钟
            frame = [max(0, int(100 + 50 * np.sin(i * 0.1 + j * 0.01))) for j in range(1024)]
            test_frames.append(frame)
        
        # 测试转换
        csv_data = converter.convert_frames_to_csv(test_frames, frame_rate=10.0)
        
        # 测试患者信息创建
        patient_info = converter.create_patient_info_dict(
            name="测试患者",
            age=65,
            gender="男",
            height=170.0,
            weight=70.0
        )
        
        # 测试质量评估
        quality = converter.estimate_quality_metrics(test_frames)
        
        print(f"✅ 数据转换器测试通过")
        print(f"   - 转换帧数: {len(test_frames)}")
        print(f"   - CSV长度: {len(csv_data)} 字符")
        print(f"   - 数据质量: {quality['quality']} ({quality['score']}分)")
        print(f"   - 患者信息: {patient_info['name']}, {patient_info['age']}岁")
        
        return True, csv_data, patient_info
        
    except Exception as e:
        print(f"❌ 数据转换器测试失败: {e}")
        traceback.print_exc()
        return False, None, None

def test_sarcneuro_service():
    """测试 SarcNeuro Edge 服务"""
    print("🔄 测试 SarcNeuro Edge 服务...")
    
    try:
        from sarcneuro_service import SarcNeuroEdgeService
        
        # 检查服务目录
        if not Path("sarcneuro-edge").exists():
            print("❌ SarcNeuro Edge 服务目录不存在")
            return False, None
        
        service = SarcNeuroEdgeService(port=8001)
        
        # 测试启动服务
        print("🚀 启动服务中...")
        if not service.start_service():
            print("❌ 服务启动失败")
            return False, None
        
        print("✅ 服务启动成功")
        
        # 测试连接
        if service.test_connection():
            print("✅ 服务连接正常")
        else:
            print("❌ 服务连接失败")
            return False, service
        
        # 获取服务状态
        status = service.get_service_status()
        print(f"📊 服务状态: 运行中 (PID: {status.get('process_id', 'N/A')})")
        
        return True, service
        
    except Exception as e:
        print(f"❌ SarcNeuro Edge 服务测试失败: {e}")
        traceback.print_exc()
        return False, None

def test_analysis_integration(service, csv_data, patient_info):
    """测试分析集成"""
    print("🔄 测试分析集成...")
    
    try:
        if not service or not csv_data or not patient_info:
            print("❌ 缺少测试数据")
            return False
        
        print(f"🎯 发送分析请求 - 患者: {patient_info['name']}")
        
        # 发送分析请求
        result = service.analyze_data(csv_data, patient_info)
        
        if not result:
            print("❌ 分析请求失败")
            return False
        
        if not result.get('success'):
            print(f"❌ 分析失败: {result.get('message', '未知错误')}")
            return False
        
        # 解析结果
        data = result.get('data', {})
        print("✅ 分析成功")
        print(f"   - 综合评分: {data.get('overall_score', 'N/A')}")
        print(f"   - 风险等级: {data.get('risk_level', 'N/A')}")
        print(f"   - 置信度: {data.get('confidence', 0):.1%}")
        print(f"   - 处理时间: {data.get('processing_time', 0):.0f}ms")
        
        # 检查详细结果
        if 'detailed_analysis' in data:
            detailed = data['detailed_analysis']
            gait = detailed.get('gait_analysis', {})
            balance = detailed.get('balance_analysis', {})
            
            if gait:
                print(f"   - 步行速度: {gait.get('walking_speed', 0):.3f} m/s")
                print(f"   - 步频: {gait.get('cadence', 0):.1f} 步/分钟")
            
            if balance:
                print(f"   - 跌倒风险: {balance.get('fall_risk_score', 0):.1%}")
        
        return True
        
    except Exception as e:
        print(f"❌ 分析集成测试失败: {e}")
        traceback.print_exc()
        return False

def test_ui_integration():
    """测试UI集成"""
    print("🔄 测试UI集成...")
    
    try:
        # 检查主要模块是否可导入
        modules_to_test = [
            'pressure_sensor_ui',
            'integration_ui',
            'serial_interface',
            'data_processor',
            'visualization',
            'device_config'
        ]
        
        for module_name in modules_to_test:
            try:
                __import__(module_name)
                print(f"✅ {module_name} 模块导入成功")
            except ImportError as e:
                print(f"❌ {module_name} 模块导入失败: {e}")
                return False
        
        print("✅ UI集成测试通过")
        return True
        
    except Exception as e:
        print(f"❌ UI集成测试失败: {e}")
        traceback.print_exc()
        return False

def main():
    """主测试函数"""
    print("🧪 肌少症检测系统集成测试")
    print("=" * 50)
    print(f"📅 测试时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    test_results = []
    service = None
    
    try:
        # 1. 测试数据转换器
        success, csv_data, patient_info = test_data_converter()
        test_results.append(("数据转换器", success))
        print()
        
        # 2. 测试 SarcNeuro Edge 服务
        success, service = test_sarcneuro_service()
        test_results.append(("SarcNeuro Edge 服务", success))
        print()
        
        # 3. 测试分析集成
        if success and csv_data and patient_info:
            success = test_analysis_integration(service, csv_data, patient_info)
            test_results.append(("分析集成", success))
            print()
        else:
            test_results.append(("分析集成", False))
            print("⏭️ 跳过分析集成测试（依赖测试失败）")
            print()
        
        # 4. 测试UI集成
        success = test_ui_integration()
        test_results.append(("UI集成", success))
        print()
        
    except KeyboardInterrupt:
        print("⏹️ 测试被用户中断")
    except Exception as e:
        print(f"❌ 测试过程异常: {e}")
        traceback.print_exc()
    
    finally:
        # 清理服务
        if service:
            print("🧹 清理测试服务...")
            try:
                service.stop_service()
                print("✅ 服务已停止")
            except:
                pass
    
    # 显示测试结果汇总
    print("📊 测试结果汇总")
    print("=" * 50)
    
    passed = 0
    total = len(test_results)
    
    for test_name, success in test_results:
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"{status} {test_name}")
        if success:
            passed += 1
    
    print()
    print(f"📈 总体结果: {passed}/{total} 通过 ({passed/total*100:.1f}%)")
    
    if passed == total:
        print("🎉 所有测试通过！系统集成准备就绪")
        return 0
    else:
        print("⚠️ 部分测试失败，请检查配置")
        return 1

if __name__ == "__main__":
    exit_code = main()
    print()
    print("⏸️ 按 Enter 键退出...")
    input()
    sys.exit(exit_code)