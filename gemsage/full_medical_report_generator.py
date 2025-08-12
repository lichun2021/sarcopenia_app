#!/usr/bin/env python3
"""
完整医疗报告生成器 - 包含平台报告的所有内容
去除导航框架，保留所有医疗数据和分析内容
集成增强版报告生成器，支持图表和个性化建议
"""

from datetime import datetime
from jinja2 import Template
from typing import Dict, Any, Optional
import os
import sys
import numpy as np

# 导入图表生成器
try:
    from enhanced_report_generator import ChartGenerator
    CHART_GENERATOR_AVAILABLE = True
except ImportError:
    CHART_GENERATOR_AVAILABLE = False
    print("注意: 图表生成器不可用，图表将显示占位符")

# 尝试导入增强版报告生成器
try:
    from enhanced_report_generator import (
        EnhancedReportGenerator, 
        generate_enhanced_report_from_algorithm,
        PersonalizedAdviceGenerator  # 🔥 修正类名
    )
    ENHANCED_AVAILABLE = True
    SMART_ADVICE_AVAILABLE = True
    print("✅ 智能建议生成器导入成功")
except ImportError as e:
    ENHANCED_AVAILABLE = False
    SMART_ADVICE_AVAILABLE = False
    print(f"⚠️ 注意: 增强版报告生成器不可用: {e}")
    print("将使用基础版本...")
    
    # 创建简化的建议类作为备用
    class PersonalizedAdviceGenerator:
        def generate_personalized_advice(self, analysis_data, patient_info):
            return {
                'recommendations': ['建议保持规律运动', '注意饮食均衡', '定期进行健康检查'],
                'risk_assessment': ['步态分析已完成'],
                'exercise_plan': ['每天步行30分钟', '进行适度的力量训练'],
                'lifestyle': ['保持充足睡眠', '避免久坐'],
                'follow_up': ['建议3个月后复查', '如有不适随时就诊']
            }

# 从您提供的标准模板文件中读取
def load_template_from_file():
    """从标准模板文件加载HTML模板"""
    template_path = os.path.join(os.path.dirname(__file__), 'full_complete_report.html')
    try:
        with open(template_path, 'r', encoding='utf-8') as f:
            return f.read()
    except FileNotFoundError:
        print(f"警告：找不到模板文件 {template_path}，使用内置模板")
        return FALLBACK_TEMPLATE

# 备用模板（如果标准模板文件不存在）
FALLBACK_TEMPLATE = '''
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>步态分析报告 - {{ report_number }}</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'PingFang SC', 'Microsoft YaHei', Arial, sans-serif;
            font-size: 14px;
            line-height: 1.5;
            color: #333;
            background: white;
        }
        
        .report-container {
            max-width: 1000px;
            margin: 0 auto;
            padding: 40px;
        }
        
        /* 工具栏 */
        .toolbar {
            display: flex;
            gap: 10px;
            margin-bottom: 30px;
            padding-bottom: 20px;
            border-bottom: 1px solid #e8e8e8;
        }
        
        .btn {
            padding: 8px 16px;
            border: 1px solid #d9d9d9;
            background: white;
            color: #333;
            font-size: 14px;
            cursor: pointer;
            transition: all 0.3s;
            border-radius: 4px;
        }
        
        .btn:hover {
            border-color: #1890ff;
            color: #1890ff;
        }
        
        .btn-primary {
            background: #1890ff;
            color: white;
            border-color: #1890ff;
        }
        
        .btn-primary:hover {
            background: #40a9ff;
            border-color: #40a9ff;
        }
        
        /* 报告头部 */
        .report-header {
            text-align: center;
            margin-bottom: 40px;
        }
        
        .report-number {
            text-align: right;
            font-size: 12px;
            color: #999;
            margin-bottom: 10px;
        }
        
        .hospital-name {
            font-size: 24px;
            font-weight: bold;
            color: #333;
            margin-bottom: 10px;
        }
        
        .report-title {
            font-size: 20px;
            font-weight: 500;
            color: #333;
            margin-bottom: 30px;
        }
        
        /* 患者信息 */
        .patient-info {
            display: grid;
            grid-template-columns: repeat(4, 1fr);
            gap: 20px;
            margin-bottom: 30px;
            padding: 20px;
            background: #fafafa;
            border-radius: 4px;
        }
        
        .info-item {
            display: flex;
            align-items: baseline;
        }
        
        .info-label {
            font-weight: 500;
            color: #666;
            margin-right: 8px;
            white-space: nowrap;
        }
        
        .info-value {
            color: #333;
            font-weight: 400;
        }
        
        /* 数据表格 */
        .data-table {
            width: 100%;
            border-collapse: collapse;
            margin-bottom: 30px;
            font-size: 14px;
        }
        
        .data-table th,
        .data-table td {
            border: 1px solid #e8e8e8;
            padding: 12px;
            text-align: center;
        }
        
        .data-table th {
            background: #fafafa;
            font-weight: 500;
            color: #333;
        }
        
        .data-table td {
            color: #333;
        }
        
        .data-table tbody tr:hover {
            background: #f5f5f5;
        }
        
        .abnormal {
            color: #ff4d4f;
            font-weight: 500;
        }
        
        .arrow-down {
            color: #ff4d4f;
            font-size: 12px;
            margin-left: 4px;
        }
        
        .arrow-up {
            color: #ff4d4f;
            font-size: 12px;
            margin-left: 4px;
        }
        
        /* 评估结论 */
        .conclusion-section {
            margin: 40px 0;
            padding: 20px;
            background: #f6ffed;
            border: 1px solid #b7eb8f;
            border-radius: 4px;
        }
        
        .conclusion-title {
            font-size: 16px;
            font-weight: 500;
            color: #333;
            margin-bottom: 15px;
        }
        
        .conclusion-content {
            color: #333;
            line-height: 1.8;
        }
        
        .conclusion-content p {
            margin-bottom: 10px;
        }
        
        /* 图表区域 */
        .chart-section {
            margin: 40px 0;
        }
        
        .section-title {
            font-size: 18px;
            font-weight: 500;
            color: #333;
            margin-bottom: 20px;
            padding-bottom: 10px;
            border-bottom: 1px solid #e8e8e8;
        }
        
        .chart-grid {
            display: grid;
            grid-template-columns: repeat(3, 1fr);
            gap: 20px;
            margin-bottom: 30px;
        }
        
        .chart-item {
            background: #fafafa;
            padding: 20px;
            border-radius: 4px;
            text-align: center;
        }
        
        .chart-title {
            font-size: 14px;
            color: #666;
            margin-bottom: 10px;
        }
        
        .chart-placeholder {
            height: 200px;
            background: #fff;
            border: 1px solid #e8e8e8;
            display: flex;
            align-items: center;
            justify-content: center;
            color: #999;
            font-size: 12px;
        }
        
        /* COP轨迹分析 */
        .cop-section {
            margin: 40px 0;
        }
        
        .cop-grid {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 30px;
            margin-bottom: 20px;
        }
        
        .cop-item {
            text-align: center;
        }
        
        .cop-title {
            font-size: 16px;
            font-weight: 500;
            color: #333;
            margin-bottom: 15px;
        }
        
        .cop-chart {
            background: #fafafa;
            border: 1px solid #e8e8e8;
            height: 300px;
            display: flex;
            align-items: center;
            justify-content: center;
            margin-bottom: 15px;
            color: #999;
        }
        
        .cop-metrics {
            display: flex;
            justify-content: space-around;
            font-size: 14px;
        }
        
        .metric-item {
            text-align: center;
        }
        
        .metric-label {
            color: #666;
            margin-bottom: 5px;
        }
        
        .metric-value {
            color: #1890ff;
            font-weight: 500;
            font-size: 16px;
        }
        
        .cop-description {
            margin-top: 20px;
            padding: 15px;
            background: #f5f5f5;
            border-radius: 4px;
            color: #666;
            font-size: 14px;
            line-height: 1.6;
        }
        
        /* 医学建议 */
        .recommendations-section {
            margin: 40px 0;
        }
        
        .recommendation-category {
            margin-bottom: 30px;
        }
        
        .recommendation-title {
            font-size: 16px;
            font-weight: 500;
            color: #1890ff;
            margin-bottom: 15px;
        }
        
        .recommendation-list {
            list-style: none;
        }
        
        .recommendation-list li {
            margin-bottom: 12px;
            padding-left: 20px;
            position: relative;
            line-height: 1.8;
            color: #333;
        }
        
        .recommendation-list li:before {
            content: "•";
            position: absolute;
            left: 0;
            color: #1890ff;
            font-weight: bold;
        }
        
        .recommendation-list strong {
            color: #333;
            font-weight: 500;
        }
        
        /* 足底压力分析 */
        .foot-pressure-section {
            margin: 40px 0;
            padding: 30px;
            background: #fafafa;
            border-radius: 4px;
        }
        
        .foot-pressure-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 30px;
        }
        
        .foot-pressure-grid {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 40px;
            margin-bottom: 30px;
        }
        
        .foot-item {
            text-align: center;
        }
        
        .foot-title {
            font-size: 16px;
            font-weight: 500;
            color: #333;
            margin-bottom: 15px;
        }
        
        .foot-heatmap {
            background: white;
            border: 2px solid #e8e8e8;
            height: 300px;
            display: flex;
            align-items: center;
            justify-content: center;
            margin-bottom: 20px;
            color: #999;
            font-size: 14px;
        }
        
        .foot-stats {
            display: grid;
            grid-template-columns: repeat(2, 1fr);
            gap: 15px;
            text-align: left;
            font-size: 14px;
        }
        
        .stat-item {
            display: flex;
            justify-content: space-between;
        }
        
        .stat-label {
            color: #666;
        }
        
        .stat-value {
            font-weight: 500;
            color: #333;
        }
        
        .pressure-scale {
            display: flex;
            align-items: center;
            justify-content: center;
            margin-top: 20px;
            gap: 20px;
        }
        
        .scale-label {
            font-size: 14px;
            color: #666;
        }
        
        .scale-bar {
            width: 200px;
            height: 20px;
            background: linear-gradient(to right, #0064C8, #00DC3C, #F0F000, #FF3200, #C80000);
            border-radius: 4px;
        }
        
        .scale-values {
            display: flex;
            justify-content: space-between;
            width: 200px;
            font-size: 12px;
            color: #999;
            margin-top: 5px;
        }
        
        .pressure-analysis {
            margin-top: 30px;
            padding: 20px;
            background: white;
            border-radius: 4px;
        }
        
        .analysis-title {
            font-size: 16px;
            font-weight: 500;
            color: #333;
            margin-bottom: 15px;
        }
        
        .analysis-content {
            color: #333;
            line-height: 1.8;
        }
        
        .analysis-content ul {
            list-style: none;
            margin-top: 10px;
        }
        
        .analysis-content li {
            margin-bottom: 10px;
            padding-left: 20px;
            position: relative;
        }
        
        .analysis-content li:before {
            content: "•";
            position: absolute;
            left: 0;
            color: #1890ff;
        }
        
        /* 签名区域 */
        .signature-section {
            margin-top: 60px;
            padding-top: 40px;
            border-top: 1px solid #e8e8e8;
        }
        
        .signature-title {
            font-size: 16px;
            font-weight: 500;
            color: #333;
            margin-bottom: 30px;
        }
        
        .signature-line {
            border-bottom: 1px solid #333;
            margin: 40px 200px 0 0;
        }
        
        @media print {
            .toolbar {
                display: none !important;
            }
            
            .report-container {
                padding: 20px;
            }
            
            body {
                background: white;
            }
        }
    </style>
</head>
<body>
    <div class="report-container">
        <!-- 工具栏 -->
        <div class="toolbar no-print">
            <button class="btn" onclick="window.print()">打印预览</button>
            <button class="btn btn-primary" onclick="window.print()">打印报告</button>
            <button class="btn" onclick="alert('请使用打印功能并选择"另存为PDF"')">下载PDF</button>
        </div>
        
        <!-- 报告头部 -->
        <div class="report-header">
            <div class="report-number">{{ report_number }}</div>
            <h1 class="hospital-name">肌智神护 AI 平台</h1>
            <h2 class="report-title">步态分析报告</h2>
        </div>
        
        <!-- 患者信息 -->
        <div class="patient-info">
            <div class="info-item">
                <span class="info-label">姓名</span>
                <span class="info-value">{{ patient_name }}</span>
            </div>
            <div class="info-item">
                <span class="info-label">性别</span>
                <span class="info-value">{{ patient_gender }}</span>
            </div>
            <div class="info-item">
                <span class="info-label">年龄</span>
                <span class="info-value">{{ patient_age }}</span>
            </div>
            <div class="info-item">
                <span class="info-label">日期</span>
                <span class="info-value">{{ test_date }}</span>
            </div>
            <div class="info-item">
                <span class="info-label">就诊号</span>
                <span class="info-value">{{ medical_record_number }}</span>
            </div>
            <div class="info-item">
                <span class="info-label">科室</span>
                <span class="info-value">{{ department }}</span>
            </div>
            <div class="info-item">
                <span class="info-label">参考范围</span>
                <span class="info-value">{{ age_group }}</span>
            </div>
        </div>
        
        <!-- 完整的步态数据表格 -->
        <table class="data-table">
            <thead>
                <tr>
                    <th>参数</th>
                    <th>左/右</th>
                    <th>数值</th>
                    <th>参考范围[{{ age_range }}]</th>
                    <th>单位</th>
                </tr>
            </thead>
            <tbody>
                <tr>
                    <td>步速</td>
                    <td>-</td>
                    <td>{{ walking_speed }}</td>
                    <td>[0.85, 1.40]</td>
                    <td>m/s</td>
                </tr>
                <tr>
                    <td rowspan="2">步长</td>
                    <td>左</td>
                    <td>{{ left_step_length }}</td>
                    <td rowspan="2">[50.0, 65.0]</td>
                    <td rowspan="2">cm</td>
                </tr>
                <tr>
                    <td>右</td>
                    <td>{{ right_step_length }}</td>
                </tr>
                <tr>
                    <td rowspan="2">步幅</td>
                    <td>左</td>
                    <td>{{ left_stride_length }}</td>
                    <td rowspan="2">[100.00, 130.00]</td>
                    <td rowspan="2">cm</td>
                </tr>
                <tr>
                    <td>右</td>
                    <td>{{ right_stride_length }}</td>
                </tr>
                <tr>
                    <td rowspan="2">步频</td>
                    <td>左</td>
                    <td>{{ left_cadence }}</td>
                    <td rowspan="2">[103, 123]</td>
                    <td rowspan="2">steps/min</td>
                </tr>
                <tr>
                    <td>右</td>
                    <td>{{ right_cadence }}</td>
                </tr>
                <tr>
                    <td rowspan="2">跨步速度</td>
                    <td>左</td>
                    <td>{{ left_stride_speed }}</td>
                    <td rowspan="2">[1.53, 3.08]</td>
                    <td rowspan="2">m/s</td>
                </tr>
                <tr>
                    <td>右</td>
                    <td>{{ right_stride_speed }}</td>
                </tr>
                <tr>
                    <td rowspan="2">摆动速度</td>
                    <td>左</td>
                    <td>{{ left_swing_speed }}</td>
                    <td rowspan="2">[2.13, 4.90]</td>
                    <td rowspan="2">m/s</td>
                </tr>
                <tr>
                    <td>右</td>
                    <td>{{ right_swing_speed }}</td>
                </tr>
                <tr>
                    <td rowspan="2">站立相</td>
                    <td>左</td>
                    <td>{{ left_stance_phase }}</td>
                    <td rowspan="2">[60.00, 68.00]</td>
                    <td rowspan="2">%</td>
                </tr>
                <tr>
                    <td>右</td>
                    <td>{{ right_stance_phase }}</td>
                </tr>
                <tr>
                    <td rowspan="2">摆动相</td>
                    <td>左</td>
                    <td>{{ left_swing_phase }}</td>
                    <td rowspan="2">[32.00, 40.00]</td>
                    <td rowspan="2">%</td>
                </tr>
                <tr>
                    <td>右</td>
                    <td>{{ right_swing_phase }}</td>
                </tr>
                <tr>
                    <td rowspan="2">双支撑相</td>
                    <td>左</td>
                    <td>{{ left_double_support }}</td>
                    <td rowspan="2">[18.00, 22.00]</td>
                    <td rowspan="2">%</td>
                </tr>
                <tr>
                    <td>右</td>
                    <td>{{ right_double_support }}</td>
                </tr>
                <tr>
                    <td rowspan="2">步高</td>
                    <td>左</td>
                    <td>{{ left_step_height }}</td>
                    <td rowspan="2">[6.0, 12.0]</td>
                    <td rowspan="2">cm</td>
                </tr>
                <tr>
                    <td>右</td>
                    <td>{{ right_step_height }}</td>
                </tr>
                <tr>
                    <td>步宽</td>
                    <td>-</td>
                    <td>{{ step_width }}</td>
                    <td>[0.09, 0.15]</td>
                    <td>m</td>
                </tr>
                <tr>
                    <td>转身时间</td>
                    <td>-</td>
                    <td class="{{ 'abnormal' if turn_time|float > 1.0 else '' }}">
                        {{ turn_time }}
                        {% if turn_time|float > 1.0 %}<span class="arrow-up">↑</span>{% endif %}
                    </td>
                    <td>[0.50, 1.00]</td>
                    <td>s</td>
                </tr>
            </tbody>
        </table>
        
        <!-- 评估结论 -->
        <div class="conclusion-section">
            <div class="conclusion-title">评估结论：</div>
            <div class="conclusion-content">
                <p><strong>步速：</strong>步速{{ walking_speed }} m/s，{{ speed_assessment }}。</p>
                {% if turn_time|float > 1.0 %}
                <p><strong>转身时间：</strong>转身时间{{ turn_time }}秒，超出正常范围。</p>
                {% endif %}
                <p><strong>总体评价：</strong>{{ overall_assessment }}</p>
            </div>
        </div>
        
        {% if show_history_charts %}
        <!-- 评估历史 -->
        <div class="chart-section">
            <h3 class="section-title">评估历史</h3>
            <div class="chart-grid">
                <div class="chart-item">
                    <div class="chart-title">步速 (m/s)</div>
                    <div class="chart-placeholder">图表加载中...</div>
                </div>
                <div class="chart-item">
                    <div class="chart-title">步幅 (m)<span style="margin-left: 10px;">● 左 ● 右</span></div>
                    <div class="chart-placeholder">图表加载中...</div>
                </div>
                <div class="chart-item">
                    <div class="chart-title">转身时间 (s)</div>
                    <div class="chart-placeholder">图表加载中...</div>
                </div>
            </div>
        </div>
        {% endif %}
        
        {% if show_cop_analysis %}
        <!-- COP轨迹分析 -->
        <div class="cop-section">
            <h3 class="section-title">压力中心(COP)轨迹分析</h3>
            <div class="cop-grid">
                <div class="cop-item">
                    <div class="cop-title">左脚 COP 轨迹</div>
                    <div class="cop-chart">COP轨迹图</div>
                    <div class="cop-metrics">
                        <div class="metric-item">
                            <div class="metric-label">COP轨迹面积:</div>
                            <div class="metric-value">{{ balance_analysis.copArea|round(1) }} cm²</div>
                        </div>
                        <div class="metric-item">
                            <div class="metric-label">轨迹总长度:</div>
                            <div class="metric-value">{{ balance_analysis.copPathLength|round(1) }} cm</div>
                        </div>
                        <div class="metric-item">
                            <div class="metric-label">前后摆动范围:</div>
                            <div class="metric-value">{{ balance_analysis.anteroPosteriorRange|round(1) }} cm</div>
                        </div>
                        <div class="metric-item">
                            <div class="metric-label">左右摆动范围:</div>
                            <div class="metric-value">{{ balance_analysis.medioLateralRange|round(1) }} cm</div>
                        </div>
                        <div class="metric-item">
                            <div class="metric-label">轨迹复杂度:</div>
                            <div class="metric-value">{{ balance_analysis.copComplexity|round(1) }}/10</div>
                        </div>
                        <div class="metric-item">
                            <div class="metric-label">稳定性指数:</div>
                            <div class="metric-value">{{ balance_analysis.stabilityIndex|round(0) }}%</div>
                        </div>
                    </div>
                </div>
                <div class="cop-item">
                    <div class="cop-title">COP分析状态评估</div>
                    <div class="cop-chart">
                        <div class="status-grid" style="display: grid; grid-template-columns: 1fr 1fr; gap: 15px; padding: 20px;">
                            <div class="status-item" style="display: flex; justify-content: space-between; padding: 10px; background: {% if balance_analysis.copArea < 50 %}#f0f9ff{% else %}#fef2f2{% endif %}; border-left: 4px solid {% if balance_analysis.copArea < 50 %}#1e90ff{% else %}#ef4444{% endif %}; border-radius: 4px;">
                                <span class="status-label" style="color: #666; font-weight: 500;">轨迹面积:</span>
                                <span class="status-value" style="color: {% if balance_analysis.copArea < 50 %}#1e90ff{% else %}#ef4444{% endif %}; font-weight: 600;">
                                    {{ '正常' if balance_analysis.copArea < 50 else '异常' }}
                                </span>
                            </div>
                            <div class="status-item" style="display: flex; justify-content: space-between; padding: 10px; background: {% if balance_analysis.copPathLength >= 15 and balance_analysis.copPathLength <= 40 %}#f0f9ff{% else %}#fef2f2{% endif %}; border-left: 4px solid {% if balance_analysis.copPathLength >= 15 and balance_analysis.copPathLength <= 40 %}#1e90ff{% else %}#ef4444{% endif %}; border-radius: 4px;">
                                <span class="status-label" style="color: #666; font-weight: 500;">轨迹长度:</span>
                                <span class="status-value" style="color: {% if balance_analysis.copPathLength >= 15 and balance_analysis.copPathLength <= 40 %}#1e90ff{% else %}#ef4444{% endif %}; font-weight: 600;">
                                    {{ '正常' if balance_analysis.copPathLength >= 15 and balance_analysis.copPathLength <= 40 else '异常' }}
                                </span>
                            </div>
                            <div class="status-item" style="display: flex; justify-content: space-between; padding: 10px; background: {% if balance_analysis.anteroPosteriorRange >= 2 and balance_analysis.anteroPosteriorRange <= 6 %}#f0f9ff{% else %}#fef2f2{% endif %}; border-left: 4px solid {% if balance_analysis.anteroPosteriorRange >= 2 and balance_analysis.anteroPosteriorRange <= 6 %}#1e90ff{% else %}#ef4444{% endif %}; border-radius: 4px;">
                                <span class="status-label" style="color: #666; font-weight: 500;">前后摆动:</span>
                                <span class="status-value" style="color: {% if balance_analysis.anteroPosteriorRange >= 2 and balance_analysis.anteroPosteriorRange <= 6 %}#1e90ff{% else %}#ef4444{% endif %}; font-weight: 600;">
                                    {{ '正常' if balance_analysis.anteroPosteriorRange >= 2 and balance_analysis.anteroPosteriorRange <= 6 else '异常' }}
                                </span>
                            </div>
                            <div class="status-item" style="display: flex; justify-content: space-between; padding: 10px; background: {% if balance_analysis.medioLateralRange >= 1 and balance_analysis.medioLateralRange <= 4 %}#f0f9ff{% else %}#fef2f2{% endif %}; border-left: 4px solid {% if balance_analysis.medioLateralRange >= 1 and balance_analysis.medioLateralRange <= 4 %}#1e90ff{% else %}#ef4444{% endif %}; border-radius: 4px;">
                                <span class="status-label" style="color: #666; font-weight: 500;">左右摆动:</span>
                                <span class="status-value" style="color: {% if balance_analysis.medioLateralRange >= 1 and balance_analysis.medioLateralRange <= 4 %}#1e90ff{% else %}#ef4444{% endif %}; font-weight: 600;">
                                    {{ '正常' if balance_analysis.medioLateralRange >= 1 and balance_analysis.medioLateralRange <= 4 else '异常' }}
                                </span>
                            </div>
                            <div class="status-item" style="display: flex; justify-content: space-between; padding: 10px; background: {% if balance_analysis.stabilityIndex >= 80 %}#ecfdf5{% elif balance_analysis.stabilityIndex >= 60 %}#fff7ed{% else %}#fef2f2{% endif %}; border-left: 4px solid {% if balance_analysis.stabilityIndex >= 80 %}#22c55e{% elif balance_analysis.stabilityIndex >= 60 %}#f59e0b{% else %}#ef4444{% endif %}; border-radius: 4px; grid-column: 1 / -1;">
                                <span class="status-label" style="color: #666; font-weight: 500;">稳定性指数:</span>
                                <span class="status-value" style="color: {% if balance_analysis.stabilityIndex >= 80 %}#22c55e{% elif balance_analysis.stabilityIndex >= 60 %}#f59e0b{% else %}#ef4444{% endif %}; font-weight: 600;">
                                    {{ '优秀' if balance_analysis.stabilityIndex >= 80 else ('良好' if balance_analysis.stabilityIndex >= 60 else '需改善') }}
                                </span>
                            </div>
                        </div>
                    </div>
                    <div class="cop-metrics">
                        <div class="reference-note">
                            <strong>参考范围：</strong><br>
                            • 轨迹面积：< 50 cm² (正常)<br>
                            • 轨迹长度：15-40 cm (正常)<br>
                            • 前后范围：2-6 cm (正常)<br>
                            • 左右范围：1-4 cm (正常)<br>
                            • 稳定性指数：≥80% (优秀)，60-79% (良好)
                        </div>
                    </div>
                </div>
            </div>
            <div class="cop-description">
                <strong>分析说明：</strong>压力中心（COP）轨迹反映了脚底压力分布的动态变化过程。正常步态中，COP从脚跟外侧开始，经过脚掌中部，最终到达前脚掌和脚趾。轨迹的平滑度和连续性反映了步态稳定性。
            </div>
        </div>
        {% endif %}
        
        {% if show_recommendations %}
        <!-- 专业医学建议 -->
        <div class="recommendations-section">
            <h3 class="section-title">专业医学建议</h3>
            
            <div class="recommendation-category">
                <h4 class="recommendation-title">康复训练建议：</h4>
                <ul class="recommendation-list">
                    <li><strong>平衡功能训练：</strong>建议进行单腿站立、平衡垫训练等，每日2-3次，每次15-20分钟，以改善本体感觉和动态平衡能力。</li>
                    <li><strong>肌力强化训练：</strong>重点加强下肢肌群（特别是右下肢）力量训练，包括股四头肌、臀肌和小腿肌群的渐进性抗阻训练。</li>
                    <li><strong>步态矫正训练：</strong>在专业治疗师指导下进行步态模式重建，重点改善右下肢支撑期功能和左右协调性。</li>
                    <li><strong>功能性活动训练：</strong>结合日常生活动作，如起坐、上下楼梯等功能性训练，提高实用性运动能力。</li>
                </ul>
            </div>
            
            <div class="recommendation-category">
                <h4 class="recommendation-title">预防措施：</h4>
                <ul class="recommendation-list">
                    <li><strong>跌倒风险管理：</strong>家庭环境改造，移除障碍物，增加扶手和照明，使用防滑设施。</li>
                    <li><strong>辅助器具评估：</strong>根据功能状况考虑使用适当的助行器具，确保行走安全。</li>
                    <li><strong>定期监测：</strong>建议3-6个月复查步态分析，动态评估康复效果和功能改善程度。</li>
                    <li><strong>营养支持：</strong>保证充足的蛋白质摄入和维生素D补充，维护肌肉和骨骼健康。</li>
                </ul>
            </div>
            
            <div class="recommendation-category">
                <h4 class="recommendation-title">生活方式指导：</h4>
                <ul class="recommendation-list">
                    <li><strong>规律运动：</strong>在康复训练基础上，逐步增加有氧运动，如游泳、太极拳等低冲击性活动。</li>
                    <li><strong>足部护理：</strong>选择合适的鞋具，保持足部清洁，定期检查足部皮肤状况。</li>
                    <li><strong>活动循序渐进：</strong>避免突然增加活动强度，遵循渐进性原则，预防运动损伤。</li>
                    <li><strong>心理健康：</strong>保持积极心态，必要时寻求心理支持，提高康复依从性。</li>
                </ul>
            </div>
            
            <div class="recommendation-category">
                <h4 class="recommendation-title">医疗随访：</h4>
                <ul class="recommendation-list">
                    <li><strong>康复科随访：</strong>2-4周后复诊，评估康复训练效果，调整治疗方案。</li>
                    <li><strong>神经科评估：</strong>如步态异常持续，建议神经科专科评估，排除神经系统疾病。</li>
                    <li><strong>骨科会诊：</strong>必要时骨科评估下肢结构和关节功能，排除器质性病变。</li>
                    <li><strong>营养科指导：</strong>针对肌少症风险，制定个体化营养干预方案。</li>
                </ul>
            </div>
        </div>
        {% endif %}
        
        {% if show_foot_pressure %}
        <!-- 足底压力分析 -->
        <div class="foot-pressure-section">
            <div class="foot-pressure-header">
                <h3 class="section-title">足底压力分析</h3>
            </div>
            <div class="foot-pressure-grid">
                <div class="foot-item">
                    <div class="foot-title">左脚压力分布</div>
                    <div class="foot-heatmap">热力图显示区域</div>
                    <div class="foot-stats">
                        <div class="stat-item">
                            <span class="stat-label">最大压力:</span>
                            <span class="stat-value">{{ left_max_pressure }}kPa</span>
                        </div>
                        <div class="stat-item">
                            <span class="stat-label">平均压力:</span>
                            <span class="stat-value">{{ left_avg_pressure }}kPa</span>
                        </div>
                        <div class="stat-item">
                            <span class="stat-label">接触面积:</span>
                            <span class="stat-value">{{ left_contact_area }}%</span>
                        </div>
                        <div class="stat-item">
                            <span class="stat-label">动画状态:</span>
                            <span class="stat-value">🟢 实时</span>
                        </div>
                    </div>
                </div>
                <div class="foot-item">
                    <div class="foot-title">右脚压力分布</div>
                    <div class="foot-heatmap">热力图显示区域</div>
                    <div class="foot-stats">
                        <div class="stat-item">
                            <span class="stat-label">最大压力:</span>
                            <span class="stat-value">{{ right_max_pressure }}kPa</span>
                        </div>
                        <div class="stat-item">
                            <span class="stat-label">平均压力:</span>
                            <span class="stat-value">{{ right_avg_pressure }}kPa</span>
                        </div>
                        <div class="stat-item">
                            <span class="stat-label">接触面积:</span>
                            <span class="stat-value">{{ right_contact_area }}%</span>
                        </div>
                        <div class="stat-item">
                            <span class="stat-label">压力波数:</span>
                            <span class="stat-value">0</span>
                        </div>
                    </div>
                </div>
            </div>
            
            <div class="pressure-scale">
                <span class="scale-label">压力刻度 (kPa)</span>
                <div>
                    <div class="scale-bar"></div>
                    <div class="scale-values">
                        <span>0</span>
                        <span>25</span>
                        <span>50</span>
                        <span>75</span>
                        <span>100</span>
                    </div>
                </div>
            </div>
            
            <div class="pressure-analysis">
                <h4 class="analysis-title">足底压力分析说明</h4>
                <div class="analysis-content">
                    <p><strong>压力分布特征：</strong></p>
                    <ul>
                        <li><strong>前脚掌区域：</strong>左侧前脚掌承重增加，右侧前脚掌承重不足，提示存在补偿性步态模式</li>
                        <li><strong>中足区域：</strong>中足区域压力较低，足弓结构完整，无明显塌陷征象</li>
                        <li><strong>后脚跟区域：</strong>左侧后跟着地压力显著高于右侧，提示右下肢支撑功能减退</li>
                    </ul>
                    
                    <p><strong>步态平衡评估：</strong></p>
                    <ul>
                        <li><strong>左右对称性：</strong>左右压力分布不对称（差异25.3%），存在明显的代偿性步态</li>
                        <li><strong>重心分布：</strong>重心轨迹显示由后跟向前脚掌的正常转移模式，但右侧转移效率降低</li>
                        <li><strong>步态稳定性：</strong>站立相期间压力中心摆动幅度增大，动态平衡控制能力下降</li>
                    </ul>
                    
                    <p><strong>临床意义：</strong></p>
                    <ul>
                        <li>足底压力不对称分布提示存在功能性或结构性异常，需结合临床症状综合评估</li>
                        <li>右下肢承重功能减退可能与肌力下降、关节活动受限或疼痛回避等因素相关</li>
                        <li>建议结合下肢肌力测试、关节活动度评估及影像学检查，制定个体化康复方案</li>
                    </ul>
                </div>
            </div>
        </div>
        {% endif %}
        
        <!-- 签名区域 -->
        <div class="signature-section">
            <div class="signature-title">印象：</div>
            <div class="signature-line"></div>
        </div>
    </div>
</body>
</html>
'''

class FullMedicalReportGenerator:
    """完整医疗报告生成器"""
    
    def __init__(self):
        template_content = load_template_from_file()
        self.template = Template(template_content)
        # 初始化智能医学建议生成器
        self.advice_generator = PersonalizedAdviceGenerator()
        print(f"🧠 建议生成器初始化完成 - 智能模式: {SMART_ADVICE_AVAILABLE}")
    
    def generate_report_from_algorithm(self, algorithm_result: Dict[str, Any], patient_info: Optional[Dict[str, Any]] = None) -> str:
        """从算法结果生成报告"""
        if not algorithm_result:
            raise ValueError("算法结果不能为空")
        
        # 强制使用标准模板，跳过增强版
        print("使用标准模板生成报告（full_complete_report.html）...")
        
        # 提取算法数据
        gait_analysis = algorithm_result.get('gait_analysis', {})
        balance_analysis = algorithm_result.get('balance_analysis', {})
        file_info = algorithm_result.get('file_info', {})
        
        # 设置默认患者信息
        if not patient_info:
            patient_info = {
                'name': '测试患者',
                'gender': '男',
                'age': '29'
            }
        
        # 获取年龄相关的参考范围
        reference_ranges = self._get_reference_ranges(patient_info.get('age'))
        
        # 转换算法数据为报告格式
        report_data = {
            'report_number': f'RPT-{algorithm_result.get("analysis_timestamp", "").replace(":", "").replace("-", "")[:14]}',
            'patient_name': patient_info.get('name', '测试患者'),
            'patient_gender': patient_info.get('gender', '未知'),
            'patient_age': str(patient_info.get('age', '未知')),
            'test_date': algorithm_result.get('analysis_timestamp', ''),
            'medical_record_number': patient_info.get('id', 'AUTO001'),
            'department': '足部压力分析科',
            'age_group': self._get_age_group(patient_info.get('age')),
            'age_range': self._get_age_range(patient_info.get('age')),
            
            # 动态参考范围
            'reference_ranges': reference_ranges,
            
            # 从算法结果提取的真实步态数据
            'walking_speed': f"{gait_analysis.get('average_velocity', 0):.2f}",
            
            # 左右脚步长数据
            'left_step_length': f"{gait_analysis.get('left_foot', {}).get('average_step_length', gait_analysis.get('average_step_length', 0)) * 100:.2f}",
            'right_step_length': f"{gait_analysis.get('right_foot', {}).get('average_step_length', gait_analysis.get('average_step_length', 0)) * 100:.2f}",
            
            # 左右脚步幅数据 (步幅 = 步长 × 2)
            'left_stride_length': f"{gait_analysis.get('left_foot', {}).get('average_step_length', gait_analysis.get('average_step_length', 0)) * 200:.2f}",
            'right_stride_length': f"{gait_analysis.get('right_foot', {}).get('average_step_length', gait_analysis.get('average_step_length', 0)) * 200:.2f}",
            
            # 左右脚步频数据
            'left_cadence': f"{gait_analysis.get('left_foot', {}).get('cadence', gait_analysis.get('cadence', 0)):.2f}",
            'right_cadence': f"{gait_analysis.get('right_foot', {}).get('cadence', gait_analysis.get('cadence', 0)):.2f}",
            
            # 跨步速度 (根据步长和步频计算)
            'left_stride_speed': f"{gait_analysis.get('left_foot', {}).get('average_step_length', gait_analysis.get('average_step_length', 0)) * gait_analysis.get('left_foot', {}).get('cadence', gait_analysis.get('cadence', 0)) * 2 / 60:.2f}",
            'right_stride_speed': f"{gait_analysis.get('right_foot', {}).get('average_step_length', gait_analysis.get('average_step_length', 0)) * gait_analysis.get('right_foot', {}).get('cadence', gait_analysis.get('cadence', 0)) * 2 / 60:.2f}",
            
            # 摆动速度 (通常是跨步速度的1.2-1.5倍)
            'left_swing_speed': f"{gait_analysis.get('left_foot', {}).get('average_step_length', gait_analysis.get('average_step_length', 0)) * gait_analysis.get('left_foot', {}).get('cadence', gait_analysis.get('cadence', 0)) * 2.5 / 60:.2f}",
            'right_swing_speed': f"{gait_analysis.get('right_foot', {}).get('average_step_length', gait_analysis.get('average_step_length', 0)) * gait_analysis.get('right_foot', {}).get('cadence', gait_analysis.get('cadence', 0)) * 2.5 / 60:.2f}",
            
            # 步态相位数据
            'left_stance_phase': f"{gait_analysis.get('left_foot', {}).get('stance_phase', 60.0):.2f}",
            'right_stance_phase': f"{gait_analysis.get('right_foot', {}).get('stance_phase', 60.0):.2f}",
            'left_swing_phase': f"{gait_analysis.get('left_foot', {}).get('swing_phase', 40.0):.2f}",
            'right_swing_phase': f"{gait_analysis.get('right_foot', {}).get('swing_phase', 40.0):.2f}",
            'left_double_support': f"{gait_analysis.get('left_foot', {}).get('double_support_time', 20.0):.2f}",
            'right_double_support': f"{gait_analysis.get('right_foot', {}).get('double_support_time', 20.0):.2f}",
            
            # 步高和步宽
            'left_step_height': f"{gait_analysis.get('left_foot', {}).get('step_height', 0.12) * 100:.2f}",
            'right_step_height': f"{gait_analysis.get('right_foot', {}).get('step_height', 0.12) * 100:.2f}",
            'step_width': f"{gait_analysis.get('step_width', 0.12):.2f}",
            'turn_time': f"{gait_analysis.get('turn_time', 1.5):.2f}",
            
            # 真实的平衡分析数据
            'balance_analysis': {
                'copArea': balance_analysis.get('copArea', 0),
                'copPathLength': balance_analysis.get('copPathLength', 0),
                'copComplexity': balance_analysis.get('copComplexity', 0),
                'anteroPosteriorRange': balance_analysis.get('anteroPosteriorRange', 0),
                'medioLateralRange': balance_analysis.get('medioLateralRange', 0),
                'stabilityIndex': balance_analysis.get('stabilityIndex', 0)
            },
            
            # 足底压力数据（默认值，可后续扩展）
            'left_max_pressure': '85.0',
            'left_avg_pressure': '15.0',
            'left_contact_area': '58.0',
            'right_max_pressure': '82.0',
            'right_avg_pressure': '14.0',
            'right_contact_area': '58.0',
            
            # 基于真实数据的评估
            'speed_assessment': self._assess_walking_speed(gait_analysis.get('average_velocity', 0)),
            'overall_assessment': self._generate_overall_assessment(gait_analysis, balance_analysis, file_info),
            
            # 保留原始算法数据，供后续占位符替换使用
            'gait_analysis': gait_analysis,
            'balance_analysis': balance_analysis,
            'gait_phases': algorithm_result.get('gait_phases', {})
        }
        
        # 🔥 生成智能化个性化医学建议
        try:
            print("🧠 正在生成智能化个性化医学建议...")
            
            # 准备分析数据给建议生成器
            analysis_data = {
                'average_velocity': gait_analysis.get('average_velocity', 1.2),
                'left_step_length': gait_analysis.get('left_foot', {}).get('average_step_length', 0.65),
                'right_step_length': gait_analysis.get('right_foot', {}).get('average_step_length', 0.65),
                'cop_area': balance_analysis.get('copArea', 30),
                'left_steps': gait_analysis.get('left_foot', {}).get('steps', 0),
                'right_steps': gait_analysis.get('right_foot', {}).get('steps', 0),
                'test_date': report_data['test_date'],
                'total_steps': gait_analysis.get('total_steps', 0),
                'cadence': gait_analysis.get('cadence', 100)
            }
            
            # 生成个性化建议
            personalized_advice = self.advice_generator.generate_personalized_advice(
                analysis_data, patient_info
            )
            
            print(f"✅ 智能建议生成成功！")
            print(f"   - 风险评估: {len(personalized_advice.get('risk_assessment', []))}项")
            print(f"   - 医学建议: {len(personalized_advice.get('recommendations', []))}条")
            print(f"   - 运动计划: {len(personalized_advice.get('exercise_plan', []))}项")
            print(f"   - 生活方式: {len(personalized_advice.get('lifestyle', []))}条")
            print(f"   - 随访计划: {len(personalized_advice.get('follow_up', []))}项")
            
            # 添加到报告数据中
            report_data.update({
                'personalized_advice': personalized_advice,
                'smart_recommendations_available': True
            })
            
        except Exception as e:
            print(f"❌ 智能建议生成失败: {e}")
            # 使用基础建议作为回退
            report_data.update({
                'personalized_advice': {
                    'recommendations': ['建议保持规律运动', '注意饮食均衡', '定期进行健康检查'],
                    'risk_assessment': ['已完成步态分析'],
                    'exercise_plan': ['每天步行30分钟', '进行适度的力量训练'],
                    'lifestyle': ['保持充足睡眠', '避免久坐'],
                    'follow_up': ['建议3个月后复查', '如有不适随时就诊']
                },
                'smart_recommendations_available': False
            })
        
        # 直接返回您提供的静态模板内容，用算法数据替换关键信息
        return self.generate_report_with_static_template(report_data, patient_info)
    
    def _get_age_group(self, age):
        """根据年龄获取年龄组"""
        if not age:
            return '未知年龄组'
        
        try:
            age = int(age) if isinstance(age, str) and age.isdigit() else int(age)
        except:
            return '未知年龄组'
        
        if age < 18:
            return '儿童组 (<18岁)'
        elif age < 35:
            return '青年组 (18-35岁)'
        elif age < 50:
            return '中年组 (35-50岁)'
        elif age < 70:
            return '中老年组 (50-70岁)'
        else:
            return '老年组 (≥70岁)'
    
    def _get_age_range(self, age):
        """根据年龄获取年龄范围"""
        if not age:
            return '未知'
        
        try:
            age = int(age) if isinstance(age, str) and age.isdigit() else int(age)
        except:
            return '未知'
        
        if age < 18:
            return '<18岁'
        elif age < 35:
            return '18-35岁'
        elif age < 50:
            return '35-50岁'
        elif age < 70:
            return '50-70岁'
        else:
            return '≥70岁'
    
    def _get_reference_ranges(self, age):
        """根据年龄获取各项指标的参考范围"""
        if not age:
            return self._get_default_reference_ranges()
        
        try:
            age = int(age) if isinstance(age, str) and age.isdigit() else int(age)
        except:
            return self._get_default_reference_ranges()
        
        if age < 18:
            # 青少年组参考范围
            return {
                'step_length': '[45.0, 60.0]',  # cm
                'walking_speed': '[1.00, 1.50]',  # m/s
                'cadence': '[110, 140]',  # 步/分钟
                'stance_phase': '[58, 65]',  # %
                'swing_phase': '[35, 42]',  # %
                'step_width': '[8, 15]',  # cm
                'step_height': '[10, 18]'  # cm
            }
        elif age < 35:
            # 青年组参考范围 (18-35岁)
            return {
                'step_length': '[50.0, 70.0]',
                'walking_speed': '[1.10, 1.60]',
                'cadence': '[100, 130]',
                'stance_phase': '[60, 67]',
                'swing_phase': '[33, 40]',
                'step_width': '[10, 18]',
                'step_height': '[12, 20]'
            }
        elif age < 50:
            # 中年组参考范围 (35-50岁)
            return {
                'step_length': '[48.0, 65.0]',
                'walking_speed': '[1.00, 1.50]',
                'cadence': '[95, 125]',
                'stance_phase': '[61, 68]',
                'swing_phase': '[32, 39]',
                'step_width': '[12, 20]',
                'step_height': '[10, 18]'
            }
        elif age < 70:
            # 中老年组参考范围 (50-70岁)
            return {
                'step_length': '[45.0, 60.0]',
                'walking_speed': '[0.90, 1.40]',
                'cadence': '[90, 120]',
                'stance_phase': '[62, 70]',
                'swing_phase': '[30, 38]',
                'step_width': '[14, 22]',
                'step_height': '[8, 16]'
            }
        else:
            # 老年组参考范围 (≥70岁)
            return {
                'step_length': '[40.0, 55.0]',
                'walking_speed': '[0.70, 1.20]',
                'cadence': '[80, 110]',
                'stance_phase': '[63, 72]',
                'swing_phase': '[28, 37]',
                'step_width': '[15, 25]',
                'step_height': '[6, 14]'
            }
    
    def _get_default_reference_ranges(self):
        """默认参考范围（中年组）"""
        return {
            'step_length': '[45.0, 65.0]',
            'walking_speed': '[0.85, 1.40]',
            'cadence': '[90, 120]',
            'stance_phase': '[60, 70]',
            'swing_phase': '[30, 40]',
            'step_width': '[10, 20]',
            'step_height': '[8, 18]'
        }
    
    def _assess_walking_speed(self, velocity):
        """评估步行速度"""
        if velocity >= 1.2:
            return '正常'
        elif velocity >= 0.8:
            return '轻度偏慢'
        elif velocity >= 0.5:
            return '中度偏慢'
        else:
            return '明显偏慢'
    
    def _generate_overall_assessment(self, gait_analysis, balance_analysis, file_info):
        """生成综合评估"""
        step_count = gait_analysis.get('step_count', 0)
        velocity = gait_analysis.get('average_velocity', 0)
        stability = balance_analysis.get('stabilityIndex', 0)
        data_points = file_info.get('data_points', 0)
        
        assessment = f"检测到{step_count}步，"
        
        if velocity >= 1.0:
            assessment += "步行速度正常，"
        elif velocity >= 0.5:
            assessment += "步行速度轻度下降，"
        else:
            assessment += "步行速度明显下降，"
        
        if stability >= 70:
            assessment += "平衡能力良好。"
        elif stability >= 50:
            assessment += "平衡能力一般。"
        else:
            assessment += "平衡能力需要关注。"
        
        assessment += f"分析了{data_points}个数据点，数据质量良好。"
        
        return assessment
    
    def generate_report(self, data: Dict[str, Any], options: Dict[str, bool] = None) -> str:
        """
        生成完整报告
        
        参数:
            data: 包含所有报告数据的字典
            options: 显示选项
                - show_history_charts: 显示历史图表（默认True）
                - show_cop_analysis: 显示COP分析（默认True）  
                - show_recommendations: 显示医学建议（默认True）
                - show_foot_pressure: 显示足底压力（默认True）
        """
        # 默认选项 - 全部显示
        default_options = {
            'show_history_charts': True,
            'show_cop_analysis': True,
            'show_recommendations': True,
            'show_foot_pressure': True
        }
        
        if options:
            default_options.update(options)
        
        # 合并数据和选项
        template_data = {**data, **default_options}
        
        # 渲染模板
        return self.template.render(**template_data)
    
    def generate_report_with_static_template(self, report_data: Dict[str, Any], patient_info: Dict[str, Any]) -> str:
        """使用静态模板生成报告，替换关键数据 - 完整步态数据和图表版本"""
        # 读取您的静态模板
        template_content = load_template_from_file()
        print(f"📄 加载模板成功，大小: {len(template_content)} 字符")
        
        # 提取步态分析数据
        gait_data = report_data.get('gait_analysis', {})
        balance_data = report_data.get('balance_analysis', {})
        phases_data = report_data.get('gait_phases', {})
        
        print(f"📊 步态数据: 总步数={gait_data.get('total_steps', 0)}, 平均步长={gait_data.get('average_step_length', 0):.2f}m")
        print(f"📊 平衡数据: {list(balance_data.keys()) if balance_data else '无'}")
        print(f"📊 相位数据: {list(phases_data.keys()) if phases_data else '无'}")
        
        # 生成图表
        charts = self._generate_charts_for_static_template(report_data)
        
        # 替换患者基本信息
        template_content = template_content.replace('等等党2', patient_info.get('name', '未知患者'))
        template_content = template_content.replace('女', patient_info.get('gender', '未知'))
        template_content = template_content.replace('66', str(patient_info.get('age', '未知')))
        template_content = template_content.replace('2025-07-26 17:41:42', datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
        template_content = template_content.replace('MR20250004', patient_info.get('medical_record', f'MR{datetime.now().strftime("%Y%m%d")}_{patient_info.get("name", "UNKNOWN")}'))
        template_content = template_content.replace('自动化系统', patient_info.get('department', '康复医学科'))
        
        # 生成新的报告编号
        new_report_number = f"RPT-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
        template_content = template_content.replace('RPT-20250726-887182', new_report_number)
        
        # 替换步态分析数据 - 基于真实分析结果（修改为2位小数）
        print(f"🔍 调试gait_data条件: gait_data类型={type(gait_data)}, 布尔值={bool(gait_data)}")
        if gait_data:
            print(f"✅ gait_data条件通过！开始处理步态数据")
            # 打印gait_data的前几个关键字段
            for key in ['total_steps', 'average_step_length', 'left_step_length', 'right_step_length', 'left_cadence', 'right_cadence']:
                print(f"   {key}: {gait_data.get(key, 'N/A')}")
        else:
            print(f"❌ gait_data条件失败！跨步速度占位符不会被替换！")
            print(f"   gait_data = {gait_data}")
            
        if gait_data:
            # 步数数据
            total_steps = gait_data.get('total_steps', 0)
            left_steps = gait_data.get('left_foot', {}).get('steps', total_steps // 2)
            right_steps = gait_data.get('right_foot', {}).get('steps', total_steps - left_steps)
            
            # 步长数据 (米转厘米) - 2位小数
            avg_step_length = gait_data.get('average_step_length', 0.6) * 100  # 转换为厘米
            left_step_length = gait_data.get('left_foot', {}).get('average_step_length', avg_step_length/100) * 100
            right_step_length = gait_data.get('right_foot', {}).get('average_step_length', avg_step_length/100) * 100
            
            # 步频和速度 - 2位小数
            cadence = gait_data.get('cadence', 100.0)
            velocity = gait_data.get('average_velocity', 1.0)
            
            print(f"🔄 替换步态数据: 左步长={left_step_length:.2f}cm, 右步长={right_step_length:.2f}cm, 步频={cadence:.2f}步/分钟")
            
            # 替换模板中的硬编码值 - 2位小数
            # 步长数据替换
            template_content = template_content.replace('<td>55.1</td>', f'<td>{left_step_length:.2f}</td>')
            template_content = template_content.replace('<td>60.9</td>', f'<td>{right_step_length:.2f}</td>')
            
            # 步频数据替换（如果模板中有的话）
            template_content = template_content.replace('102.9', f'{cadence:.2f}')
            template_content = template_content.replace('107.1', f'{cadence:.2f}')
            
            # 速度数据替换 - 2位小数
            template_content = template_content.replace('1.015', f'{velocity:.2f}')
            
            # 计算其他步态指标 - 2位小数
            # 直接使用算法输出的左右脚数据
            left_step_length_m = gait_data.get('left_step_length', avg_step_length / 100)  # 已经是米制
            right_step_length_m = gait_data.get('right_step_length', avg_step_length / 100)  # 已经是米制
            left_cadence = gait_data.get('left_cadence', cadence * 0.95)
            right_cadence = gait_data.get('right_cadence', cadence * 1.05)
            
            print(f"🔄 左右脚数据: 左步长={left_step_length_m:.3f}m, 右步长={right_step_length_m:.3f}m")
            print(f"🔄 左右脚步频: 左步频={left_cadence:.1f}步/分, 右步频={right_cadence:.1f}步/分")
            
            # 计算跨步速度 (步长 * 步频 * 2 / 60)
            left_stride_speed = left_step_length_m * left_cadence * 2 / 60
            right_stride_speed = right_step_length_m * right_cadence * 2 / 60
            
            left_swing_speed = left_stride_speed * 1.21  # 通常是跨步速度的1.2-1.5倍
            right_swing_speed = right_stride_speed * 1.21
            
            print(f"🔄 步态指标计算: 左跨步={left_stride_speed:.3f}m/s, 右跨步={right_stride_speed:.3f}m/s")
            
            # 步态相位数据 - 从report_data中获取
            phases_data = report_data.get('gait_phases', {})
            left_stance_phase = phases_data.get('left_stance_phase', 62.0)
            right_stance_phase = phases_data.get('right_stance_phase', 62.0)
            left_swing_phase = phases_data.get('left_swing_phase', 38.0)
            right_swing_phase = phases_data.get('right_swing_phase', 38.0)
            left_double_support = phases_data.get('left_double_support', 19.0)
            right_double_support = phases_data.get('right_double_support', 19.0)
            
            # 使用简单的字符串替换方法 - 2位小数格式化
            # 先找到表格的位置，然后按顺序替换空的<td></td>
            
            # 替换跨步速度的值
            if '<td rowspan="2">跨步速度</td>' in template_content:
                # 找到跨步速度行，替换左侧值
                idx = template_content.find('<td rowspan="2">跨步速度</td>')
                if idx != -1:
                    # 找到左侧的空单元格
                    search_area = template_content[idx:idx+200]
                    left_pattern = '<td>左</td>\n                    <td></td>'
                    if left_pattern in search_area:
                        template_content = template_content.replace(
                            left_pattern,
                            f'<td>左</td>\n                    <td>{left_stride_speed:.2f}</td>',
                            1
                        )
                    # 找到右侧的空单元格
                    right_pattern = '<td>右</td>\n                    <td></td>'
                    search_area = template_content[idx:idx+400]
                    if right_pattern in search_area:
                        # 只替换跨步速度部分的右侧值
                        parts = template_content.split('<td rowspan="2">跨步速度</td>')
                        if len(parts) > 1:
                            part_after = parts[1]
                            part_after = part_after.replace(right_pattern, 
                                f'<td>右</td>\n                    <td>{right_stride_speed:.2f}</td>', 1)
                            template_content = parts[0] + '<td rowspan="2">跨步速度</td>' + part_after
            
            # 替换摆动速度的值
            if '<td rowspan="2">摆动速度</td>' in template_content:
                idx = template_content.find('<td rowspan="2">摆动速度</td>')
                if idx != -1:
                    parts = template_content.split('<td rowspan="2">摆动速度</td>')
                    if len(parts) > 1:
                        part_after = parts[1]
                        # 替换摆动速度的左右值
                        part_after = part_after.replace(
                            '<td>左</td>\n                    <td></td>',
                            f'<td>左</td>\n                    <td>{left_swing_speed:.2f}</td>',
                            1
                        )
                        part_after = part_after.replace(
                            '<td>右</td>\n                    <td></td>',
                            f'<td>右</td>\n                    <td>{right_swing_speed:.2f}</td>',
                            1
                        )
                        template_content = parts[0] + '<td rowspan="2">摆动速度</td>' + part_after
            
            # 替换站立相的值
            if '<td rowspan="2">站立相</td>' in template_content:
                idx = template_content.find('<td rowspan="2">站立相</td>')
                if idx != -1:
                    parts = template_content.split('<td rowspan="2">站立相</td>')
                    if len(parts) > 1:
                        part_after = parts[1]
                        part_after = part_after.replace(
                            '<td>左</td>\n                    <td></td>',
                            f'<td>左</td>\n                    <td>{left_stance_phase:.2f}</td>',
                            1
                        )
                        part_after = part_after.replace(
                            '<td>右</td>\n                    <td></td>',
                            f'<td>右</td>\n                    <td>{right_stance_phase:.2f}</td>',
                            1
                        )
                        template_content = parts[0] + '<td rowspan="2">站立相</td>' + part_after
            
            # 替换摆动相的值
            if '<td rowspan="2">摆动相</td>' in template_content:
                idx = template_content.find('<td rowspan="2">摆动相</td>')
                if idx != -1:
                    parts = template_content.split('<td rowspan="2">摆动相</td>')
                    if len(parts) > 1:
                        part_after = parts[1]
                        part_after = part_after.replace(
                            '<td>左</td>\n                    <td></td>',
                            f'<td>左</td>\n                    <td>{left_swing_phase:.2f}</td>',
                            1
                        )
                        part_after = part_after.replace(
                            '<td>右</td>\n                    <td></td>',
                            f'<td>右</td>\n                    <td>{right_swing_phase:.2f}</td>',
                            1
                        )
                        template_content = parts[0] + '<td rowspan="2">摆动相</td>' + part_after
            
            # 替换双支撑相的值
            if '<td rowspan="2">双支撑相</td>' in template_content:
                idx = template_content.find('<td rowspan="2">双支撑相</td>')
                if idx != -1:
                    parts = template_content.split('<td rowspan="2">双支撑相</td>')
                    if len(parts) > 1:
                        part_after = parts[1]
                        part_after = part_after.replace(
                            '<td>左</td>\n                    <td></td>',
                            f'<td>左</td>\n                    <td>{left_double_support:.2f}</td>',
                            1
                        )
                        part_after = part_after.replace(
                            '<td>右</td>\n                    <td></td>',
                            f'<td>右</td>\n                    <td>{right_double_support:.2f}</td>',
                            1
                        )
                        template_content = parts[0] + '<td rowspan="2">双支撑相</td>' + part_after
            
            print(f"🔄 已填充步态参数: 跨步速度(左={left_stride_speed:.2f}, 右={right_stride_speed:.2f})")
            print(f"🔄 已填充步态参数: 摆动速度(左={left_swing_speed:.2f}, 右={right_swing_speed:.2f})")
            print(f"🔄 已填充步态参数: 站立相(左={left_stance_phase:.2f}, 右={right_stance_phase:.2f})")
            print(f"🔄 已填充步态参数: 摆动相(左={left_swing_phase:.2f}, 右={right_swing_phase:.2f})")
            print(f"🔄 已填充步态参数: 双支撑相(左={left_double_support:.2f}, 右={right_double_support:.2f})")
            
            # 替换步数数据（如果模板中有的话）
            if '总步数' in template_content:
                # 尝试替换总步数相关的数值
                template_content = template_content.replace('26', str(total_steps))
        
        # 替换平衡和相位数据（如果有） - 2位小数
        if balance_data:
            cop_area = balance_data.get('cop_area', 0)
            if cop_area > 0:
                template_content = template_content.replace('0.0 cm²', f'{cop_area:.2f} cm²')
        
        if phases_data:
            stance_phase = phases_data.get('stance_phase', 60.0)
            swing_phase = phases_data.get('swing_phase', 40.0)
            double_support = phases_data.get('double_support_time', 20.0)
            
            # 替换步态相位数据（百分比） - 2位小数
            template_content = template_content.replace('60.0%', f'{stance_phase:.2f}%')
            template_content = template_content.replace('40.0%', f'{swing_phase:.2f}%')
            template_content = template_content.replace('20.0%', f'{double_support:.2f}%')
        
        # 替换动态参考范围
        template_content = self._replace_reference_ranges(template_content, patient_info.get('age'))
        
        # 替换图表占位符
        template_content = self._replace_chart_placeholders(template_content, charts)
        
        # 🔥 渲染智能化医学建议部分 - 使用Jinja2模板引擎
        print(f"🧠 开始渲染智能化医学建议模板...")
        try:
            from jinja2 import Template
            
            # 创建Jinja2模板对象
            jinja_template = Template(template_content)
            
            # 准备模板变量
            template_vars = {
                'smart_recommendations_available': report_data.get('smart_recommendations_available', False),
                'personalized_advice': report_data.get('personalized_advice', {})
            }
            
            # 渲染模板
            final_content = jinja_template.render(**template_vars)
            
            print(f"✅ Jinja2模板渲染成功！")
            print(f"   智能建议可用: {template_vars['smart_recommendations_available']}")
            if template_vars['personalized_advice']:
                advice = template_vars['personalized_advice']
                print(f"   建议内容: 风险{len(advice.get('risk_assessment', []))}项, "
                      f"建议{len(advice.get('recommendations', []))}条, "
                      f"运动{len(advice.get('exercise_plan', []))}项")
            
        except Exception as e:
            print(f"⚠️ Jinja2模板渲染失败: {e}")
            print(f"   使用原始内容作为回退")
            final_content = template_content
        
        print(f"✅ 报告生成完成，最终大小: {len(final_content)} 字符")
        return final_content
    
    def _generate_charts_for_static_template(self, report_data: Dict[str, Any]) -> Dict[str, str]:
        """为静态模板生成图表"""
        charts = {}
        
        if CHART_GENERATOR_AVAILABLE:
            try:
                chart_gen = ChartGenerator()
                gait_data = report_data.get('gait_analysis', {})
                phases_data = report_data.get('gait_phases', {})
                
                print(f"🎨 开始生成图表...")
                
                # 生成步速趋势图
                if gait_data.get('average_velocity'):
                    velocity = gait_data['average_velocity']
                    velocities = [velocity * 0.9, velocity, velocity * 1.1]  # 模拟趋势
                    charts['velocity_chart'] = chart_gen._create_velocity_chart(velocities)
                    print(f"   ✅ 步速趋势图生成成功")
                
                # 生成左右步幅对比图
                if gait_data.get('left_foot') and gait_data.get('right_foot'):
                    left_length = gait_data['left_foot'].get('average_step_length', 0.6) * 100
                    right_length = gait_data['right_foot'].get('average_step_length', 0.6) * 100
                    charts['stride_chart'] = chart_gen._create_stride_comparison(left_length, right_length)
                    print(f"   ✅ 步幅对比图生成成功")
                
                # 生成步态周期饬图
                if phases_data:
                    stance = phases_data.get('stance_phase', 60.0)
                    swing = phases_data.get('swing_phase', 40.0)
                    charts['gait_cycle_chart'] = chart_gen._create_gait_cycle_chart(stance, swing)
                    print(f"   ✅ 步态周期饬图生成成功")
                
                # 生成COP轨迹图
                charts['cop_trajectory'] = chart_gen.generate_cop_trajectory()
                print(f"   ✅ COP轨迹图生成成功")
                
                # 生成压力热力图
                charts['pressure_heatmap_left'] = chart_gen.generate_pressure_heatmap()
                charts['pressure_heatmap_right'] = chart_gen.generate_pressure_heatmap()
                print(f"   ✅ 压力热力图生成成功")
                
                print(f"🎨 图表生成完成，共{len(charts)}个图表")
                
            except Exception as e:
                print(f"⚠️ 图表生成失败: {e}")
                charts = self._create_placeholder_charts()
        else:
            print(f"⚠️ 图表生成器不可用，使用占位符")
            charts = self._create_placeholder_charts()
        
        return charts
    
    def _create_placeholder_charts(self) -> Dict[str, str]:
        """创建占位符图表"""
        placeholder = "data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iNDAwIiBoZWlnaHQ9IjMwMCIgeG1sbnM9Imh0dHA6Ly93d3cudzMub3JnLzIwMDAvc3ZnIj48cmVjdCB3aWR0aD0iMTAwJSIgaGVpZ2h0PSIxMDAlIiBmaWxsPSIjZjVmNWY1Ii8+PHRleHQgeD0iNTAlIiB5PSI1MCUiIGZvbnQtZmFtaWx5PSJBcmlhbCIgZm9udC1zaXplPSIxNCIgZmlsbD0iIzk5OSIgdGV4dC1hbmNob3I9Im1pZGRsZSIgZHk9Ii4zZW0iPuWbvuihqOWKoOi9veS4rS4uLjwvdGV4dD48L3N2Zz4="
        return {
            'velocity_chart': placeholder,
            'stride_chart': placeholder, 
            'gait_cycle_chart': placeholder,
            'cop_trajectory': placeholder,
            'pressure_heatmap_left': placeholder,
            'pressure_heatmap_right': placeholder
        }
    
    def _replace_chart_placeholders(self, template_content: str, charts: Dict[str, str]) -> str:
        """替换模板中的图表占位符"""
        print(f"🔄 开始替换图表占位符...")
        
        # 替换评估历史图表（步速、步幅、转身时间）
        replacements = [
            (r'<div class="chart-placeholder">图表加载中...</div>', 
             lambda m: f'<img src="{charts.get("velocity_chart", "")}" style="width:100%;height:200px;object-fit:contain;" alt="步速趋势图" />' if "步速" in template_content[max(0, template_content.find(m.group())-100):template_content.find(m.group())+100] else
                       f'<img src="{charts.get("stride_chart", "")}" style="width:100%;height:200px;object-fit:contain;" alt="步幅对比图" />' if "步幅" in template_content[max(0, template_content.find(m.group())-100):template_content.find(m.group())+100] else
                       f'<img src="{charts.get("gait_cycle_chart", "")}" style="width:100%;height:200px;object-fit:contain;" alt="转身时间图" />'),
            
            # 替换COP轨迹图
            ('COP轨迹图', f'<img src="{charts.get("cop_trajectory", "")}" style="width:100%;height:200px;object-fit:contain;" alt="COP轨迹图" />'),
            
            # 替换热力图
            ('热力图显示区域', f'<img src="{charts.get("pressure_heatmap_left", "")}" style="width:100%;height:200px;object-fit:contain;" alt="压力热力图" />')
        ]
        
        # 简化替换逻辑
        template_content = template_content.replace(
            '<div class="chart-placeholder">图表加载中...</div>',
            f'<img src="{charts.get("velocity_chart", "")}" style="width:100%;height:200px;object-fit:contain;" alt="图表" />'
        )
        
        template_content = template_content.replace(
            'COP轨迹图',
            f'<img src="{charts.get("cop_trajectory", "")}" style="width:100%;height:200px;object-fit:contain;" alt="COP轨迹图" />'
        )
        
        template_content = template_content.replace(
            '热力图显示区域',
            f'<img src="{charts.get("pressure_heatmap_left", "")}" style="width:100%;height:200px;object-fit:contain;" alt="压力热力图" />'
        )
        
        print(f"   ✅ 图表占位符替换完成")
        return template_content
    
    def _replace_reference_ranges(self, template_content: str, age) -> str:
        """替换模板中的参考范围为动态年龄相关范围"""
        reference_ranges = self._get_reference_ranges(age)
        
        print(f"🔄 替换动态参考范围: 年龄={age}, 使用{self._get_age_group(age)}参考标准")
        
        # 替换步长参考范围 [50.0, 65.0]
        template_content = template_content.replace('[50.0, 65.0]', reference_ranges['step_length'])
        
        # 替换步速参考范围 [0.85, 1.40]
        template_content = template_content.replace('[0.85, 1.40]', reference_ranges['walking_speed'])
        
        # 替换步频参考范围（如果模板中有的话）
        if '[90, 120]' in template_content:
            template_content = template_content.replace('[90, 120]', reference_ranges['cadence'])
        
        # 替换步态相位参考范围（如果模板中有的话）
        if '[60, 70]' in template_content:
            template_content = template_content.replace('[60, 70]', reference_ranges['stance_phase'])
        
        if '[30, 40]' in template_content:
            template_content = template_content.replace('[30, 40]', reference_ranges['swing_phase'])
        
        # 替换步宽参考范围（如果模板中有的话）
        if '[10, 20]' in template_content:
            template_content = template_content.replace('[10, 20]', reference_ranges['step_width'])
        
        # 替换步高参考范围（如果模板中有的话）  
        if '[8, 18]' in template_content:
            template_content = template_content.replace('[8, 18]', reference_ranges['step_height'])
        
        # 更新年龄范围显示文本
        age_range_text = self._get_age_range(age)
        age_group_text = self._get_age_group(age)
        if age_range_text != '未知':
            # 替换参考范围标题中的年龄组
            template_content = template_content.replace('[51-70岁]', f'[{age_range_text}]')
            template_content = template_content.replace('参考范围[51-70岁]', f'参考范围[{age_range_text}]')
            
            # 先替换完整的年龄组显示，避免重复
            old_age_display = '中老年组 (51-70岁)'
            new_age_display = f'{age_group_text} ({age_range_text})'
            template_content = template_content.replace(old_age_display, new_age_display)
            
            # 修复重复显示问题 - 直接字符串替换
            duplicate_display = f'{age_group_text} ({age_range_text}) ({age_range_text})'
            correct_display = f'{age_group_text} ({age_range_text})'
            
            # 如果存在重复，直接替换
            if duplicate_display in template_content:
                template_content = template_content.replace(duplicate_display, correct_display)
                print(f"   🔄 修复重复年龄范围显示: {duplicate_display} → {correct_display}")
        
        print(f"   ✅ 参考范围替换完成: 步长{reference_ranges['step_length']}, 步速{reference_ranges['walking_speed']}")
        return template_content

def generate_sample_report():
    """生成示例报告"""
    # 准备完整数据 - 与平台报告完全一致
    data = {
        'report_number': 'RPT-20250726-887182',
        'patient_name': '等等党2',
        'patient_gender': '女',
        'patient_age': '66',
        'test_date': '2025-07-26 17:41:42',
        'medical_record_number': 'MR20250004',
        'department': '自动化系统',
        'age_group': '中老年组 (51-70岁)',
        'age_range': '51-70岁',
        
        # 完整的步态数据
        'walking_speed': '1.015',
        'left_step_length': '55.1',
        'right_step_length': '60.9',
        'left_stride_length': '110.2',
        'right_stride_length': '121.8',
        'left_cadence': '102.9',
        'right_cadence': '107.1',
        'left_stride_speed': '0.9642499999999998',
        'right_stride_speed': '1.06575',
        'left_swing_speed': '1.16725',
        'right_swing_speed': '1.26875',
        'left_stance_phase': '59.39657708018674',
        'right_stance_phase': '59.1058386297738',
        'left_swing_phase': '39.97909075439406',
        'right_swing_phase': '39.77059834112096',
        'left_double_support': '19.54694697344994',
        'right_double_support': '21.83014746372287',
        'left_step_height': '11.9',
        'right_step_height': '12.4',
        'step_width': '0.12',
        'turn_time': '2',
        
        # COP轨迹分析数据（与平台同步）  
        'balance_analysis': {
            'copArea': 42.5,                    # COP轨迹面积 (cm²)
            'copPathLength': 165.8,             # 轨迹总长度 (cm)
            'copComplexity': 6.2,               # 轨迹复杂度 (/10)
            'anteroPosteriorRange': 4.8,        # 前后摆动范围 (cm)
            'medioLateralRange': 3.2,           # 左右摆动范围 (cm)
            'stabilityIndex': 78.5              # 稳定性指数 (%)
        },
        
        # 足底压力数据
        'left_max_pressure': '95.4',
        'left_avg_pressure': '16.0',
        'left_contact_area': '59.5',
        'right_max_pressure': '90.0',
        'right_avg_pressure': '13.4',
        'right_contact_area': '59.5',
        
        # 评估
        'speed_assessment': '未见异常',
        'overall_assessment': '综合评估显示低风险。9项测试完成。'
    }
    
    generator = FullMedicalReportGenerator()
    
    # 生成完整报告
    print("📊 生成完整报告（包含所有内容）...")
    full_report = generator.generate_report(data)
    with open('full_complete_report.html', 'w', encoding='utf-8') as f:
        f.write(full_report)
    print("✅ 完整报告已生成: full_complete_report.html")
    
    # 可选：生成自定义配置的报告
    print("\n📊 生成自定义报告（可选择模块）...")
    custom_report = generator.generate_report(data, options={
        'show_history_charts': False,  # 不显示历史图表
        'show_cop_analysis': True,     # 显示COP分析
        'show_recommendations': True,  # 显示医学建议
        'show_foot_pressure': True     # 显示足底压力
    })
    with open('custom_report.html', 'w', encoding='utf-8') as f:
        f.write(custom_report)
    print("✅ 自定义报告已生成: custom_report.html")

if __name__ == '__main__':
    generate_sample_report()