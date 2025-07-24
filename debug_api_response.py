#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
调试API响应格式
"""
import requests
import json
from sarcneuro_service import SarcNeuroEdgeService
from data_converter import SarcopeniaDataConverter

def debug_api_response():
    """调试API响应的具体格式"""
    print("=== 调试API响应格式 ===")
    
    service = SarcNeuroEdgeService(port=8000)
    
    try:
        # 启动服务
        print("1. 启动服务...")
        if not service.start_service():
            print("❌ 服务启动失败")
            return
        
        print("✅ 服务启动成功")
        
        # 创建简单测试数据
        test_csv_data = """time,max_pressure,timestamp,contact_area,total_pressure,data
0.1,100,2024-07-23T15:00:00Z,50,500,"[1,2,3,4,5]"
0.2,105,2024-07-23T15:00:00Z,52,520,"[2,3,4,5,6]"
0.3,102,2024-07-23T15:00:00Z,48,480,"[1,3,4,5,6]" """
        
        patient_info = {
            'name': '调试测试',
            'age': 30,
            'gender': 'MALE',
            'height': 175.0,
            'weight': 70.0,
            'test_date': '2025-07-23',
            'test_type': '综合分析',
            'notes': 'API响应调试',
            'created_time': '2025-07-23T15:00:00'
        }
        
        print("2. 发送分析请求...")
        result = service.analyze_data(test_csv_data, patient_info, "COMPREHENSIVE")
        
        print("3. 检查API响应格式:")
        print(f"🔍 原始结果类型: {type(result)}")
        print(f"🔍 原始结果内容: {json.dumps(result, indent=2, ensure_ascii=False)}")
        
        if result:
            print(f"🔍 status字段: '{result.get('status')}' (类型: {type(result.get('status'))})")
            print(f"🔍 message字段: '{result.get('message')}' (类型: {type(result.get('message'))})")
            
            # 测试各种判断方式
            print(f"🔍 result.get('status') == 'success': {result.get('status') == 'success'}")
            print(f"🔍 result.get('status') != 'success': {result.get('status') != 'success'}")
            print(f"🔍 'status' in result: {'status' in result}")
            print(f"🔍 result['status'] == 'success': {result['status'] == 'success' if 'status' in result else 'status字段不存在'}")
            
            # 检查是否有其他字段表示成功
            print(f"🔍 所有字段: {list(result.keys())}")
            
            # 检查是否是success的变体
            status_val = result.get('status', '')
            print(f"🔍 status值的字符编码: {[ord(c) for c in str(status_val)]}")
            print(f"🔍 'success'的字符编码: {[ord(c) for c in 'success']}")
            
        else:
            print("❌ 结果为None")
            
    except Exception as e:
        print(f"❌ 调试过程出错: {e}")
        import traceback
        traceback.print_exc()
        
    finally:
        print("4. 停止服务...")
        service.stop_service()
        print("✅ 服务已停止")

if __name__ == "__main__":
    debug_api_response()
    print("\n=== 调试完成 ===")