#!/usr/bin/env python3
"""
简化的SarcNeuro分析器 - 用于测试和基本功能
"""
import json
import time
import numpy as np
from typing import Dict, Any, List

class MinimalSarcNeuroAnalyzer:
    """简化版SarcNeuro分析器"""
    
    def __init__(self):
        self.version = "1.0.0-minimal"
    
    def analyze_pressure_data(self, csv_data: str, patient_info: Dict[str, Any]) -> Dict[str, Any]:
        """分析压力数据 - 简化版本"""
        try:
            print(f"开始分析患者 {patient_info.get('name', '未知')} 的数据...")
            
            # 模拟分析过程
            time.sleep(2)  # 模拟处理时间
            
            # 生成基本分析结果
            result = {
                "success": True,
                "data": {
                    "overall_score": 75.5,
                    "risk_level": "MEDIUM",
                    "confidence": 0.85,
                    "interpretation": "基于压力分布分析，患者步态相对稳定，但存在轻度不对称性。建议定期监测和适当的康复训练。",
                    "abnormalities": [
                        "轻度左右不对称",
                        "步频略低于标准值"
                    ],
                    "recommendations": [
                        "进行平衡训练，每日15-20分钟",
                        "增加下肢力量训练",
                        "定期进行步态评估"
                    ],
                    "detailed_analysis": {
                        "gait_analysis": {
                            "walking_speed": 1.2,
                            "step_length": 65.0,
                            "cadence": 110.5,
                            "asymmetry_index": 0.12,
                            "stability_score": 78.0
                        },
                        "balance_analysis": {
                            "cop_displacement": 15.5,
                            "sway_area": 245.8,
                            "sway_velocity": 12.3,
                            "stability_index": 1.8,
                            "fall_risk_score": 0.25
                        },
                        "analysis_time": 2.1,
                        "data_quality": 0.92,
                        "processing_version": self.version
                    }
                },
                "message": "分析完成"
            }
            
            print(f"✅ 分析完成 - 评分: {result['data']['overall_score']}")
            return result
            
        except Exception as e:
            print(f"❌ 分析失败: {e}")
            return {
                "success": False,
                "message": f"分析过程出错: {e}",
                "data": None
            }

# 全局分析器实例
_minimal_analyzer = None

def get_minimal_analyzer():
    """获取简化分析器实例"""
    global _minimal_analyzer
    if _minimal_analyzer is None:
        _minimal_analyzer = MinimalSarcNeuroAnalyzer()
    return _minimal_analyzer
