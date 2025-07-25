#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
调试报告生成 - 检查数据是否正确传递到模板
"""
import sys
import os
sys.path.append('./sarcneuro-edge')

async def debug_report_generation():
    """调试报告生成过程"""
    print("=== 调试报告生成过程 ===")
    
    try:
        from core.report_generator import ReportGenerator
        from pathlib import Path
        
        # 创建报告生成器
        generator = ReportGenerator()
        print("✅ 报告生成器创建成功")
        
        # 模拟数据（基于用户实际的分析结果）
        from datetime import datetime
        test_data = {
            'id': 5,
            'test_type': 'COMPREHENSIVE',
            'test_mode': 'UPLOAD',
            'duration': 30.0,
            'created_at': datetime.now(),  # 使用datetime对象而不是字符串
            'notes': 'CSV分析测试'
        }
        
        patient_data = {
            'id': 1,
            'name': '曾超',
            'age': 36,
            'gender': 'MALE',
            'height': 175.0,
            'weight': 70.0,
            'phone': None,
            'email': None
        }
        
        analysis_data = {
            'id': 5,
            'overall_score': 67.0,
            'risk_level': 'HIGH',
            'confidence': 0.85,
            'interpretation': '检测到肌少症风险，建议进一步检查和针对性训练',
            'abnormalities': ['步态不稳', '平衡能力下降'],
            'recommendations': ['增强肌力训练', '平衡训练', '定期监测'],
            'detailed_analysis': {},
            'processing_time': 45.0,
            'model_version': '3.0.1',
            'created_at': datetime.now()
        }
        
        gait_data = {
            'walking_speed': 1.1,
            'step_length': 60.5,
            'cadence': 105.0,
            'stance_phase': 62.0,
            'asymmetry_index': 0.08,
            'stability_score': 78.0
        }
        
        balance_data = {
            'cop_displacement': 28.5,
            'sway_area': 165.0,
            'sway_velocity': 9.2,
            'stability_index': 2.8,
            'fall_risk_score': 0.22
        }
        
        print("✅ 模拟数据准备完成")
        print(f"患者: {patient_data['name']}, 评分: {analysis_data['overall_score']}")
        
        # 准备报告数据
        print("📋 准备报告数据...")
        report_data = await generator._prepare_report_data(
            test_data, patient_data, analysis_data, gait_data, balance_data
        )
        
        print("✅ 报告数据准备成功")
        print(f"报告编号: {report_data.get('report_number', 'N/A')}")
        print(f"患者姓名: {report_data.get('patient', {}).get('name', 'N/A')}")
        print(f"分析评分: {report_data.get('analysis', {}).get('overall_score', 'N/A')}")
        
        # 生成HTML报告
        print("📄 生成HTML报告...")
        try:
            report_path = await generator._generate_html_report(report_data)
            print(f"✅ HTML报告生成成功: {report_path}")
            
            # 检查文件是否存在且有内容
            if report_path.exists():
                file_size = report_path.stat().st_size
                print(f"📁 报告文件大小: {file_size} 字节")
                
                if file_size > 100:  # 基本大小检查
                    print("✅ 报告文件生成成功且有内容")
                    
                    # 读取前几行检查内容
                    with open(report_path, 'r', encoding='utf-8') as f:
                        first_lines = [f.readline().strip() for _ in range(10)]
                    
                    print("📋 报告前几行内容:")
                    for i, line in enumerate(first_lines, 1):
                        if line:
                            print(f"  {i}: {line[:100]}...")
                else:
                    print("❌ 报告文件为空或过小")
            else:
                print("❌ 报告文件不存在")
                
        except Exception as e:
            print(f"❌ HTML报告生成失败: {e}")
            import traceback
            traceback.print_exc()
        
        # 尝试生成报告
        print("📄 生成报告...")
        try:
            pdf_path = await generator._generate_pdf_report(report_data)
            print(f"✅ 报告生成成功: {pdf_path}")
            
            if pdf_path.exists():
                file_size = pdf_path.stat().st_size
                print(f"📁 PDF文件大小: {file_size} 字节")
                
                if file_size > 1000:  # PDF基本大小检查
                    print("✅ 报告文件生成成功且有内容")
                else:
                    print("❌ 报告文件为空或过小")
            else:
                print("❌ 报告文件不存在")
                
        except Exception as e:
            print(f"❌ 报告生成失败: {e}")
            import traceback
            traceback.print_exc()
            
    except Exception as e:
        print(f"❌ 调试过程出错: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    import asyncio
    asyncio.run(debug_report_generation())
    print("\n=== 调试完成 ===")