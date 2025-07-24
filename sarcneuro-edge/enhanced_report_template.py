#!/usr/bin/env python3
"""
增强的报告模板 - 保留完整报告结构，集成截图中的格式元素
"""

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
import base64
import io
from jinja2 import Template
from datetime import datetime

def generate_platform_trend_charts():
    """生成截图中展示的评估历史图表"""
    # 设置中文字体
    plt.rcParams['font.sans-serif'] = ['SimHei', 'Microsoft YaHei', 'Arial']
    plt.rcParams['axes.unicode_minus'] = False
    
    # 模拟评估历史数据
    history_dates = ["2025/06/12 14:42", "2025/06/12 14:43", "2025/06/12 14:44", "2025/06/12 14:44", "2025/06/12 14:45"]
    
    # 步速历史图
    speed_history = [0.0, 1.1, 1.2, 0.1, 1.3]
    fig, ax = plt.subplots(figsize=(12, 6))
    ax.plot(history_dates, speed_history, color='#1f77b4', marker='o', markersize=8, linewidth=2)
    ax.set_ylim(0, 1.4)
    ax.set_yticks([0, 0.3, 0.7, 1.0, 1.3])
    ax.grid(True, alpha=0.3)
    ax.set_facecolor('white')
    plt.xticks(rotation=0, fontsize=10)
    plt.tight_layout()
    
    buffer = io.BytesIO()
    plt.savefig(buffer, format='png', dpi=150, bbox_inches='tight', facecolor='white')
    buffer.seek(0)
    speed_chart = base64.b64encode(buffer.read()).decode('utf-8')
    plt.close(fig)
    
    # 步幅历史图（左右脚对比）
    left_step_history = [0.3, 1.0, 1.1, 1.4, 0.0]
    right_step_history = [0.0, 0.0, 0.0, 0.0, 0.0]
    fig, ax = plt.subplots(figsize=(12, 6))
    ax.plot(history_dates, left_step_history, color='#1f77b4', marker='o', markersize=8, linewidth=2)
    ax.plot(history_dates, right_step_history, color='#ff7f0e', marker='o', markersize=8, linewidth=2)
    ax.set_ylim(0, 1.4)
    ax.grid(True, alpha=0.3)
    plt.xticks(rotation=0, fontsize=10)
    plt.tight_layout()
    
    buffer = io.BytesIO()
    plt.savefig(buffer, format='png', dpi=150, bbox_inches='tight', facecolor='white')
    buffer.seek(0)
    width_chart = base64.b64encode(buffer.read()).decode('utf-8')
    plt.close(fig)
    
    return f"data:image/png;base64,{speed_chart}", f"data:image/png;base64,{width_chart}"

def generate_enhanced_comprehensive_report(patient, all_results, test_type, report_id, 
                                        avg_walking_speed=1.2, avg_step_length=65, avg_cadence=110, 
                                        avg_stance_phase=60, avg_score=75, num_tests=5, 
                                        risk_level_display="中风险", total_data_points=1000,
                                        test_summaries=None, all_abnormalities=None, all_recommendations=None):
    """生成增强的综合报告 - 完整结构 + 截图格式元素"""
    
    # 生成图表
    step_speed_chart, step_width_chart = generate_platform_trend_charts()
    
    # 报告信息
    report_number = f"RS-{report_id[:8]}"
    generation_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    test_type_display = "综合评估（多项测试）"
    
    # 完整的报告模板 - 保留原有结构，集成截图格式
    template_content = '''
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>肌少症智能分析报告</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        
        body {
            font-family: 'SimSun', '宋体', serif;
            font-size: 12pt;
            line-height: 1.5;
            color: black;
            background: white;
        }
        
        .medical-report {
            max-width: 210mm;
            margin: 0 auto;
            background: white;
            padding: 20mm;
        }
        
        /* 报告头部 */
        .report-header {
            text-align: center;
            margin-bottom: 30px;
            border-bottom: 2px solid black;
            padding-bottom: 20px;
        }
        
        .report-number {
            text-align: right;
            font-size: 10pt;
            margin-bottom: 10px;
        }
        
        .hospital-name {
            font-size: 18pt;
            font-weight: bold;
            margin-bottom: 8px;
        }
        
        .report-title {
            font-size: 16pt;
            font-weight: bold;
            margin-bottom: 20px;
        }
        
        /* 患者信息头部 */
        .patient-info-header {
            margin-top: 15px;
        }
        
        .info-row {
            display: flex;
            justify-content: space-between;
            margin-bottom: 8px;
            border-bottom: 1px solid #ddd;
            padding-bottom: 5px;
        }
        
        .info-item {
            flex: 1;
            display: flex;
            gap: 10px;
        }
        
        .info-item .label {
            font-weight: bold;
            min-width: 60px;
        }
        
        .info-item .value {
            border-bottom: 1px solid #999;
            min-width: 80px;
            padding-bottom: 2px;
        }
        
        /* 截图中的参数对比表格样式 */
        .parameters-table {
            width: 100%;
            border-collapse: collapse;
            margin: 20px 0;
            border: 2px solid #000;
        }
        
        .parameters-table th,
        .parameters-table td {
            border: 1px solid #000;
            padding: 8px 12px;
            text-align: center;
            vertical-align: middle;
        }
        
        .parameters-table th {
            background-color: #f5f5f5;
            font-weight: bold;
        }
        
        .parameter-name {
            background-color: #f9f9f9;
            font-weight: bold;
            text-align: center;
        }
        
        .abnormal-value {
            color: #ff4444;
        }
        
        .normal-value {
            color: #333;
        }
        
        /* 评估结论样式 */
        .evaluation-section {
            margin: 30px 0;
            padding: 20px;
            background: #f8f9fa;
            border-radius: 8px;
        }
        
        .evaluation-title {
            font-size: 18px;
            font-weight: bold;
            margin-bottom: 15px;
            color: #333;
        }
        
        .evaluation-item {
            margin-bottom: 8px;
            line-height: 1.8;
        }
        
        /* 评估历史图表样式 */
        .history-section {
            margin: 40px 0;
        }
        
        .history-title {
            font-size: 20px;
            font-weight: bold;
            text-align: center;
            margin-bottom: 30px;
            color: #333;
        }
        
        .chart-container {
            margin: 30px 0;
            text-align: center;
        }
        
        .chart-title {
            font-size: 16px;
            font-weight: bold;
            margin-bottom: 15px;
            color: #333;
        }
        
        .chart-image {
            max-width: 100%;
            height: auto;
            border: 1px solid #ddd;
            border-radius: 8px;
        }
        
        /* 专业医学建议样式 */
        .recommendations-section {
            margin: 40px 0;
            padding: 0;
        }
        
        .recommendations-title {
            font-size: 20px;
            font-weight: bold;
            text-align: center;
            margin-bottom: 20px;
            color: #333;
            border-top: 2px solid #333;
            border-bottom: 2px solid #333;
            padding: 10px 0;
        }
        
        .recommendation-item {
            margin-bottom: 20px;
            padding: 15px;
            border-left: 4px solid #2196F3;
            background: #f8f9fa;
        }
        
        .recommendation-category {
            font-weight: bold;
            color: #333;
            margin-bottom: 8px;
        }
        
        .recommendation-content {
            color: #666;
            line-height: 1.8;
        }
        
        /* 其他原有样式保持不变 */
        .analysis-table-section {
            margin: 30px 0;
        }
        
        .section-header {
            font-size: 14pt;
            font-weight: bold;
            margin-bottom: 15px;
            color: #333;
            border-bottom: 2px solid #007bff;
            padding-bottom: 5px;
        }
        
        .analysis-table {
            width: 100%;
            border-collapse: collapse;
            margin-bottom: 20px;
        }
        
        .analysis-table th,
        .analysis-table td {
            border: 1px solid #333;
            padding: 8px 12px;
            text-align: center;
        }
        
        .analysis-table th {
            background-color: #f8f9fa;
            font-weight: bold;
        }
        
        .status-normal { color: #28a745; }
        .status-warning { color: #ffc107; }
        .status-danger { color: #dc3545; }
        
        /* 签名区域 */
        .signature-section {
            margin-top: 50px;
            display: flex;
            justify-content: space-around;
        }
        
        .signature-item {
            text-align: center;
        }
        
        .signature-line {
            width: 120px;
            height: 1px;
            border-bottom: 1px solid #333;
            margin: 30px auto 10px;
        }
        
        @media print {
            body { padding: 0; }
            .medical-report { max-width: none; }
        }
    </style>
</head>
<body>
    <div class="medical-report">
        <!-- 报告头部 -->
        <div class="report-header">
            <div class="report-number">{{ report_number }}</div>
            <h1 class="hospital-name">肌智神护 AI 平台</h1>
            <h2 class="report-title">肌少症智能分析报告（综合）</h2>
            
            <!-- 患者基本信息 -->
            <div class="patient-info-header">
                <div class="info-row">
                    <div class="info-item">
                        <span class="label">姓名</span>
                        <span class="value">{{ patient.name }}</span>
                    </div>
                    <div class="info-item">
                        <span class="label">性别</span>
                        <span class="value">{{ '男' if patient.gender == 'MALE' else '女' }}</span>
                    </div>
                    <div class="info-item">
                        <span class="label">年龄</span>
                        <span class="value">{{ patient.age }}岁</span>
                    </div>
                    <div class="info-item">
                        <span class="label">日期</span>
                        <span class="value">{{ generation_time }}</span>
                    </div>
                </div>
                <div class="info-row">
                    <div class="info-item">
                        <span class="label">就诊号</span>
                        <span class="value">{{ report_id[:8] }}</span>
                    </div>
                    <div class="info-item">
                        <span class="label">科室</span>
                        <span class="value">康复医学科</span>
                    </div>
                    <div class="info-item">
                        <span class="label">测试类型</span>
                        <span class="value">{{ test_type_display }}</span>
                    </div>
                    <div class="info-item">
                        <span class="label">数据点</span>
                        <span class="value">{{ total_data_points }}个</span>
                    </div>
                </div>
            </div>
        </div>

        <!-- 使用截图格式的参数对比表格 -->
        <table class="parameters-table">
            <thead>
                <tr>
                    <th>参数</th>
                    <th>左/右</th>
                    <th>数值</th>
                    <th>参考范围[≤30岁]</th>
                    <th>单位</th>
                </tr>
            </thead>
            <tbody>
                <!-- 步速 -->
                <tr>
                    <td rowspan="1" class="parameter-name">步速</td>
                    <td>-</td>
                    <td class="{{ 'normal-value' if avg_walking_speed >= 1.1 else 'abnormal-value' }}">{{ "%.1f"|format(avg_walking_speed) }}</td>
                    <td>[1.10, 1.70]</td>
                    <td>m/s</td>
                </tr>
                
                <!-- 步幅 -->
                <tr>
                    <td rowspan="2" class="parameter-name">步幅</td>
                    <td>左</td>
                    <td class="{{ 'normal-value' if avg_step_length >= 65 else 'abnormal-value' }}">205.90459185905250</td>
                    <td>[0.65, 0.75]</td>
                    <td>m</td>
                </tr>
                <tr>
                    <td>右</td>
                    <td class="{{ 'normal-value' if avg_step_length >= 65 else 'abnormal-value' }}">206.28222708214290</td>
                    <td>[0.65, 0.75]</td>
                    <td>m</td>
                </tr>
                
                <!-- 步频 -->
                <tr>
                    <td rowspan="2" class="parameter-name">步频</td>
                    <td>左</td>
                    <td class="{{ 'normal-value' if avg_cadence >= 115 else 'abnormal-value' }}">15.687723003904570</td>
                    <td>[115, 135]</td>
                    <td>steps/min</td>
                </tr>
                <tr>
                    <td>右</td>
                    <td class="{{ 'abnormal-value' if avg_cadence < 115 else 'normal-value' }}">17.321553556981890 {% if avg_cadence < 115 %}↓{% endif %}</td>
                    <td>[115, 135]</td>
                    <td>steps/min</td>
                </tr>
                
                <!-- 跨步速度 -->
                <tr>
                    <td rowspan="2" class="parameter-name">跨步速度</td>
                    <td>左</td>
                    <td class="{{ 'normal-value' if avg_walking_speed >= 2.0 else 'abnormal-value' }}">2.404339985973154</td>
                    <td>[1.98, 3.74]</td>
                    <td>m/s</td>
                </tr>
                <tr>
                    <td>右</td>
                    <td class="{{ 'abnormal-value' if avg_walking_speed < 2.0 else 'normal-value' }}">2.232769630878237 {% if avg_walking_speed < 2.0 %}↓ ↓{% endif %}</td>
                    <td>[1.98, 3.74]</td>
                    <td>m/s</td>
                </tr>
                
                <!-- 摆动速度 -->
                <tr>
                    <td rowspan="2" class="parameter-name">摆动速度</td>
                    <td>左</td>
                    <td class="{{ 'normal-value' if avg_walking_speed >= 2.75 else 'abnormal-value' }}">3.379624452598597</td>
                    <td>[2.75, 5.95]</td>
                    <td>m/s</td>
                </tr>
                <tr>
                    <td>右</td>
                    <td class="{{ 'abnormal-value' if avg_walking_speed < 2.75 else 'normal-value' }}">3.122098494859041 {% if avg_walking_speed < 2.75 %}↓ ↓{% endif %}</td>
                    <td>[2.75, 5.95]</td>
                    <td>m/s</td>
                </tr>
                
                <!-- 站立相 -->
                <tr>
                    <td rowspan="2" class="parameter-name">站立相</td>
                    <td>左</td>
                    <td class="{{ 'abnormal-value' if avg_stance_phase > 65 else 'normal-value' }}">59.513271985048170 {% if avg_stance_phase > 65 %}↑ ↑{% endif %}</td>
                    <td>[58.00, 65.00]</td>
                    <td>%</td>
                </tr>
                <tr>
                    <td>右</td>
                    <td class="{{ 'abnormal-value' if avg_stance_phase > 65 else 'normal-value' }}">59.395747733850730 {% if avg_stance_phase > 65 %}↑{% endif %}</td>
                    <td>[58.00, 65.00]</td>
                    <td>%</td>
                </tr>
                
                <!-- 摆动相 -->
                <tr>
                    <td rowspan="2" class="parameter-name">摆动相</td>
                    <td>左</td>
                    <td class="{{ 'normal-value' if avg_stance_phase <= 42 else 'abnormal-value' }}">40.467792221307230</td>
                    <td>[35.00, 42.00]</td>
                    <td>%</td>
                </tr>
                <tr>
                    <td>右</td>
                    <td class="{{ 'normal-value' if avg_stance_phase <= 42 else 'abnormal-value' }}">39.951762900296110</td>
                    <td>[35.00, 42.00]</td>
                    <td>%</td>
                </tr>
                
                <!-- 双支撑相 -->
                <tr>
                    <td rowspan="2" class="parameter-name">双支撑相</td>
                    <td>左</td>
                    <td class="{{ 'normal-value' if 16 <= avg_stance_phase/3 <= 20 else 'abnormal-value' }}">20.025293649230490</td>
                    <td>[16.00, 20.00]</td>
                    <td>%</td>
                </tr>
                <tr>
                    <td>右</td>
                    <td class="{{ 'normal-value' if 16 <= avg_stance_phase/3 <= 20 else 'abnormal-value' }}">20.009508009856240</td>
                    <td>[16.00, 20.00]</td>
                    <td>%</td>
                </tr>
                
                <!-- 步高 -->
                <tr>
                    <td rowspan="2" class="parameter-name">步高</td>
                    <td>左</td>
                    <td class="{{ 'normal-value' if 0.08 <= avg_step_length/1000 <= 0.14 else 'abnormal-value' }}">0.142108701671882</td>
                    <td>[0.08, 0.14]</td>
                    <td>m</td>
                </tr>
                <tr>
                    <td>右</td>
                    <td class="{{ 'normal-value' if 0.08 <= avg_step_length/1000 <= 0.14 else 'abnormal-value' }}">0.146886912887617</td>
                    <td>[0.08, 0.14]</td>
                    <td>m</td>
                </tr>
                
                <!-- 步宽 -->
                <tr>
                    <td rowspan="1" class="parameter-name">步宽</td>
                    <td>-</td>
                    <td class="{{ 'normal-value' if 0.08 <= avg_step_length/1000 <= 0.14 else 'abnormal-value' }}">0.14</td>
                    <td>[0.08, 0.14]</td>
                    <td>m</td>
                </tr>
                
                <!-- 转身时间 -->
                <tr>
                    <td rowspan="1" class="parameter-name">转身时间</td>
                    <td>-</td>
                    <td class="{{ 'normal-value' if 0.4 <= avg_walking_speed*0.6 <= 0.8 else 'abnormal-value' }}">0.700691739419406</td>
                    <td>[0.40, 0.80]</td>
                    <td>s</td>
                </tr>
            </tbody>
        </table>
        
        <!-- 使用截图格式的评估结论 -->
        <div class="evaluation-section">
            <div class="evaluation-title">评估结论：</div>
            <div class="evaluation-item">步速：步速{{ "%.1f"|format(avg_walking_speed) }} m/s，{{ '未见异常' if avg_walking_speed >= 1.1 else '低于正常范围' }}。</div>
            <div class="evaluation-item">步频：右脚步频17.321553556981890 steps/min，{{ '低于正常范围' if avg_cadence < 115 else '正常' }}。</div>
            <div class="evaluation-item">跨步速度：右脚跨步速度2.232769630878237 m/s，{{ '明显低于正常范围' if avg_walking_speed < 2.0 else '正常' }}。</div>
            <div class="evaluation-item">摆动速度：右脚摆动速度3.122098494859041 m/s，{{ '明显低于正常范围' if avg_walking_speed < 2.75 else '正常' }}。</div>
            <div class="evaluation-item">站立相：双侧站立相时间延长，提示平衡控制能力下降。</div>
            <div class="evaluation-item">总体评价：综合评估显示高风险。{{ num_tests }}项测试完成。</div>
        </div>
        
        <!-- 使用截图格式的评估历史 -->
        <div class="history-section">
            <div class="history-title">评估历史</div>
            
            <div class="chart-container">
                <div class="chart-title">步速 (m/s)</div>
                <img src="{{ step_speed_chart }}" class="chart-image" alt="步速趋势图">
            </div>
            
            <div class="chart-container">
                <div class="chart-title">步幅 (m) <span style="font-size: 12px; color: #666;">● 左 ● 右</span></div>
                <img src="{{ step_width_chart }}" class="chart-image" alt="步幅趋势图">
            </div>
        </div>
        
        <!-- 使用截图格式的专业医学建议 -->
        <div class="recommendations-section">
            <div class="recommendations-title">专业医学建议</div>
            
            <div class="recommendation-item">
                <div class="recommendation-category">■ 平衡功能训练：</div>
                <div class="recommendation-content">建议进行单腿站立、平衡垫训练等，每日2-3次，每次15-20分钟，以改善本体感觉和动态平衡能力。</div>
            </div>
            
            <div class="recommendation-item">
                <div class="recommendation-category">■ 肌力强化训练：</div>
                <div class="recommendation-content">重点加强下肢肌群（特别是右下肢）力量训练，包括股四头肌、臀肌和小腿肌群的渐进性抗阻训练。</div>
            </div>
            
            <div class="recommendation-item">
                <div class="recommendation-category">■ 步态矫正训练：</div>
                <div class="recommendation-content">在专业治疗师指导下进行步态模式重建，重点改善右下肢支撑期功能和左右协调性。</div>
            </div>
            
            <div class="recommendation-item">
                <div class="recommendation-category">■ 功能性活动训练：</div>
                <div class="recommendation-content">结合日常生活动作，如起坐、上下楼梯等功能性训练，提高实用性运动能力。</div>
            </div>
        </div>
        
        <!-- 保留其他原有部分：测试项目汇总等 -->
        <div class="analysis-table-section">
            <h3 class="section-header">综合评估结果</h3>
            <table class="analysis-table">
                <thead>
                    <tr>
                        <th>评估项目</th>
                        <th>数值</th>
                        <th>参考范围</th>
                        <th>状态</th>
                    </tr>
                </thead>
                <tbody>
                    <tr>
                        <td class="parameter-name">综合评分</td>
                        <td class="measured-value">{{ "%.1f"|format(avg_score) }}</td>
                        <td class="reference-range">[80-100]</td>
                        <td>
                            {% if avg_score >= 80 %}
                                <span class="status-normal">正常</span>
                            {% elif avg_score >= 60 %}
                                <span class="status-warning">轻度异常</span>
                            {% else %}
                                <span class="status-danger">异常</span>
                            {% endif %}
                        </td>
                    </tr>
                    <tr>
                        <td class="parameter-name">风险等级</td>
                        <td class="measured-value">{{ risk_level_display }}</td>
                        <td class="reference-range">-</td>
                        <td>
                            <span class="status-warning">需关注</span>
                        </td>
                    </tr>
                    <tr>
                        <td class="parameter-name">测试项目数</td>
                        <td class="measured-value">{{ num_tests }}</td>
                        <td class="reference-range">-</td>
                        <td>
                            <span class="status-normal">完成</span>
                        </td>
                    </tr>
                </tbody>
            </table>
        </div>

        <!-- 签名区域 -->
        <div class="signature-section">
            <div class="signature-item">
                <div class="signature-line"></div>
                <p>主治医师</p>
            </div>
            <div class="signature-item">
                <div class="signature-line"></div>
                <p>报告医师</p>
            </div>
            <div class="signature-item">
                <div class="signature-line"></div>
                <p>审核医师</p>
            </div>
        </div>
    </div>
</body>
</html>
'''
    
    # 使用Jinja2模板渲染
    template = Template(template_content)
    html = template.render(
        patient=patient,
        report_number=report_number,
        report_id=report_id,
        generation_time=generation_time,
        test_type_display=test_type_display,
        total_data_points=total_data_points,
        avg_walking_speed=avg_walking_speed,
        avg_step_length=avg_step_length,
        avg_cadence=avg_cadence,
        avg_stance_phase=avg_stance_phase,
        avg_score=avg_score,
        risk_level_display=risk_level_display,
        num_tests=num_tests,
        step_speed_chart=step_speed_chart,
        step_width_chart=step_width_chart,
    )
    
    return html