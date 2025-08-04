#!/usr/bin/env python3
"""
完整医疗报告生成器 - 包含平台报告的所有内容
去除导航框架，保留所有医疗数据和分析内容
"""

from datetime import datetime
from jinja2 import Template
from typing import Dict, Any, Optional

# 完整报告模板 - 包含所有平台报告内容
FULL_MEDICAL_REPORT_TEMPLATE = '''
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
        self.template = Template(FULL_MEDICAL_REPORT_TEMPLATE)
    
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