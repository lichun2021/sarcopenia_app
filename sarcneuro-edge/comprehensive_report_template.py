"""
综合测试报告生成函数 - 使用医院标准模板
"""
from typing import List, Dict, Any
from core.analyzer import PatientInfo
from datetime import datetime
from jinja2 import Template

async def generate_comprehensive_report(patient: PatientInfo, all_results: List[dict], test_type: str, report_id: str) -> str:
    """生成综合测试报告 - 使用医院标准模板"""
    
    # 计算综合数据
    total_score = 0
    total_data_points = 0
    risk_levels = []
    all_abnormalities = []
    all_recommendations = set()
    
    # 收集所有测试的平均数据
    avg_walking_speed = 0
    avg_step_length = 0
    avg_cadence = 0
    avg_stance_phase = 0
    avg_cop_displacement = 0
    avg_sway_area = 0
    avg_fall_risk = 0
    
    # 收集每个测试的数据
    test_summaries = []
    
    for result in all_results:
        analysis = result['analysis']
        gait = analysis.gait_analysis
        balance = analysis.balance_analysis
        
        # 累加分数
        total_score += analysis.overall_score
        total_data_points += result['data_points']
        risk_levels.append(analysis.risk_level)
        all_abnormalities.extend(analysis.abnormalities)
        all_recommendations.update(analysis.recommendations)
        
        # 累加步态数据
        avg_walking_speed += gait.walking_speed
        avg_step_length += gait.step_length
        avg_cadence += gait.cadence
        avg_stance_phase += gait.stance_phase
        
        # 累加平衡数据
        avg_cop_displacement += balance.cop_displacement
        avg_sway_area += balance.sway_area
        avg_fall_risk += balance.fall_risk_score
        
        # 保存测试摘要
        test_summaries.append({
            'name': result['test_name'],
            'score': analysis.overall_score,
            'risk': analysis.risk_level
        })
    
    # 计算平均值
    num_tests = len(all_results)
    avg_score = total_score / num_tests if num_tests > 0 else 0
    avg_walking_speed /= num_tests if num_tests > 0 else 1
    avg_step_length /= num_tests if num_tests > 0 else 1
    avg_cadence /= num_tests if num_tests > 0 else 1
    avg_stance_phase /= num_tests if num_tests > 0 else 1
    avg_cop_displacement /= num_tests if num_tests > 0 else 1
    avg_sway_area /= num_tests if num_tests > 0 else 1
    avg_fall_risk /= num_tests if num_tests > 0 else 1
    
    # 确定最高风险等级
    risk_priority = {'LOW': 1, 'MEDIUM': 2, 'HIGH': 3, 'CRITICAL': 4}
    highest_risk = max(risk_levels, key=lambda x: risk_priority.get(x, 0)) if risk_levels else 'LOW'
    
    # 风险等级显示
    risk_level_display = {
        'LOW': '低风险',
        'MEDIUM': '中度风险', 
        'HIGH': '高风险',
        'CRITICAL': '严重风险'
    }.get(highest_risk, '未知')
    
    risk_level_class = {
        'LOW': 'normal',
        'MEDIUM': 'warning',
        'HIGH': 'danger',
        'CRITICAL': 'danger'
    }.get(highest_risk, 'normal')
    
    # 生成报告编号
    report_number = f"SNE-{report_id[:8].upper()}"
    generation_time = datetime.now().strftime('%Y-%m-%d %H:%M')
    
    # 测试类型显示
    test_type_display = "综合评估（多项测试）"
    
    # 生成综合解释
    interpretation = f"""基于{num_tests}项测试的综合分析，该患者的运动功能评估显示：
整体功能评分为{avg_score:.1f}分，风险等级为{risk_level_display}。"""
    
    if highest_risk in ['HIGH', 'CRITICAL']:
        interpretation += "存在明显的运动功能障碍，建议及时进行专业康复评估和干预。"
    elif highest_risk == 'MEDIUM':
        interpretation += "存在轻度运动功能异常，建议加强运动锻炼并定期复查。"
    else:
        interpretation += "运动功能基本正常，建议保持现有运动习惯。"
    
    # 使用医院标准模板
    template_content = '''
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>肌少症智能分析报告</title>
    <style>
        /* 医院报告样式 */
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
        
        /* 分析数据表格 */
        .analysis-table-section {
            margin: 30px 0;
        }
        
        .section-header {
            font-size: 14pt;
            font-weight: bold;
            margin-bottom: 15px;
            padding-bottom: 5px;
            border-bottom: 1px solid #333;
        }
        
        .analysis-table {
            width: 100%;
            border-collapse: collapse;
            font-size: 11pt;
        }
        
        .analysis-table th,
        .analysis-table td {
            border: 1px solid black;
            padding: 8px 6px;
            text-align: center;
            vertical-align: middle;
        }
        
        .analysis-table th {
            background-color: #f5f5f5;
            font-weight: bold;
        }
        
        .parameter-name {
            font-weight: bold;
            background-color: #f9f9f9;
        }
        
        .measured-value {
            font-weight: bold;
            color: #000;
        }
        
        .reference-range {
            color: #666;
            font-size: 10pt;
        }
        
        .status-normal {
            color: green;
        }
        
        .status-warning {
            color: orange;
        }
        
        .status-danger {
            color: red;
        }
        
        /* 测试项目汇总 */
        .test-summary-table {
            width: 100%;
            border-collapse: collapse;
            font-size: 11pt;
            margin-top: 20px;
        }
        
        .test-summary-table th,
        .test-summary-table td {
            border: 1px solid black;
            padding: 6px;
            text-align: center;
        }
        
        .test-summary-table th {
            background-color: #f5f5f5;
            font-weight: bold;
        }
        
        /* 评估结论 */
        .conclusion-section {
            margin: 30px 0;
            padding: 15px;
            background-color: #f9f9f9;
            border: 1px solid #ddd;
        }
        
        .conclusion-title {
            font-weight: bold;
            margin-bottom: 10px;
        }
        
        .conclusion-content p {
            margin: 5px 0;
            text-indent: 2em;
        }
        
        .conclusion-content ul {
            margin-left: 2em;
        }
        
        /* 建议区域 */
        .recommendations {
            margin: 30px 0;
            padding: 15px;
            background-color: #f0f8ff;
            border: 1px solid #4682b4;
        }
        
        .recommendations h4 {
            color: #4682b4;
            margin-bottom: 10px;
        }
        
        .recommendation-list {
            list-style: none;
            padding-left: 20px;
        }
        
        .recommendation-list li {
            margin: 8px 0;
            padding-left: 20px;
            position: relative;
        }
        
        .recommendation-list li:before {
            content: "•";
            position: absolute;
            left: 0;
            color: #4682b4;
            font-weight: bold;
        }
        
        /* 签名区域 */
        .signature-section {
            margin-top: 50px;
            display: flex;
            justify-content: space-between;
        }
        
        .signature-item {
            flex: 1;
            text-align: center;
        }
        
        .signature-line {
            border-bottom: 1px solid black;
            margin: 30px 40px 10px;
        }
        
        /* 打印样式 */
        @media print {
            body {
                background: white;
            }
            .medical-report {
                box-shadow: none;
                padding: 15mm;
            }
            .no-print {
                display: none;
            }
            .page-break {
                page-break-after: always;
            }
        }
        
        /* 工具栏 */
        .toolbar {
            position: fixed;
            top: 20px;
            right: 20px;
            z-index: 1000;
            display: flex;
            gap: 10px;
        }
        
        .btn {
            padding: 10px 20px;
            background: #007bff;
            color: white;
            border: none;
            border-radius: 5px;
            cursor: pointer;
            text-decoration: none;
            font-size: 14px;
        }
        
        .btn:hover {
            background: #0056b3;
        }
        
        .btn-secondary {
            background: #6c757d;
        }
        
        .btn-secondary:hover {
            background: #5a6268;
        }
    </style>
</head>
<body>
    <div class="toolbar no-print">
        <button onclick="window.print()" class="btn">打印报告</button>
        <button onclick="window.close()" class="btn btn-secondary">关闭窗口</button>
    </div>
    
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

        <!-- 测试项目汇总 -->
        <div class="analysis-table-section">
            <h3 class="section-header">测试项目汇总</h3>
            <table class="test-summary-table">
                <thead>
                    <tr>
                        <th>测试项目</th>
                        <th>评分</th>
                        <th>风险等级</th>
                        <th>状态</th>
                    </tr>
                </thead>
                <tbody>
                    {% for test in test_summaries %}
                    <tr>
                        <td>{{ test.name }}</td>
                        <td class="measured-value">{{ "%.1f"|format(test.score) }}</td>
                        <td>{{ test.risk }}</td>
                        <td>
                            {% if test.score >= 80 %}
                                <span class="status-normal">正常</span>
                            {% elif test.score >= 60 %}
                                <span class="status-warning">轻度异常</span>
                            {% else %}
                                <span class="status-danger">异常</span>
                            {% endif %}
                        </td>
                    </tr>
                    {% endfor %}
                </tbody>
            </table>
        </div>

        <!-- 综合评估结果 -->
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
                            <span class="status-{{ risk_level_class }}">
                                {{ '需关注' if highest_risk != 'LOW' else '正常' }}
                            </span>
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

        <!-- 步态分析结果（平均值） -->
        <div class="analysis-table-section">
            <h3 class="section-header">步态分析结果（平均值）</h3>
            <table class="analysis-table">
                <thead>
                    <tr>
                        <th>参数</th>
                        <th>数值</th>
                        <th>参考范围</th>
                        <th>单位</th>
                        <th>评估</th>
                    </tr>
                </thead>
                <tbody>
                    <tr>
                        <td class="parameter-name">步行速度</td>
                        <td class="measured-value">{{ "%.2f"|format(avg_walking_speed) }}</td>
                        <td class="reference-range">[1.0-1.6]</td>
                        <td>m/s</td>
                        <td>{{ '↓ 偏低' if avg_walking_speed < 1.0 else '正常' }}</td>
                    </tr>
                    <tr>
                        <td class="parameter-name">步长</td>
                        <td class="measured-value">{{ "%.1f"|format(avg_step_length) }}</td>
                        <td class="reference-range">[50-80]</td>
                        <td>cm</td>
                        <td>{{ '正常' if 50 <= avg_step_length <= 80 else '异常' }}</td>
                    </tr>
                    <tr>
                        <td class="parameter-name">步频</td>
                        <td class="measured-value">{{ "%.1f"|format(avg_cadence) }}</td>
                        <td class="reference-range">[90-120]</td>
                        <td>步/分钟</td>
                        <td>{{ '正常' if 90 <= avg_cadence <= 120 else '异常' }}</td>
                    </tr>
                    <tr>
                        <td class="parameter-name">站立相</td>
                        <td class="measured-value">{{ "%.1f"|format(avg_stance_phase) }}</td>
                        <td class="reference-range">[60-65]</td>
                        <td>%</td>
                        <td>{{ '↑ 延长' if avg_stance_phase > 65 else '正常' }}</td>
                    </tr>
                </tbody>
            </table>
        </div>

        <!-- 平衡分析结果（平均值） -->
        <div class="analysis-table-section">
            <h3 class="section-header">平衡分析结果（平均值）</h3>
            <table class="analysis-table">
                <thead>
                    <tr>
                        <th>参数</th>
                        <th>数值</th>
                        <th>参考范围</th>
                        <th>单位</th>
                        <th>评估</th>
                    </tr>
                </thead>
                <tbody>
                    <tr>
                        <td class="parameter-name">压力中心位移</td>
                        <td class="measured-value">{{ "%.1f"|format(avg_cop_displacement) }}</td>
                        <td class="reference-range">[<15]</td>
                        <td>mm</td>
                        <td>{{ '↑ 异常' if avg_cop_displacement > 15 else '正常' }}</td>
                    </tr>
                    <tr>
                        <td class="parameter-name">摆动面积</td>
                        <td class="measured-value">{{ "%.1f"|format(avg_sway_area) }}</td>
                        <td class="reference-range">[<300]</td>
                        <td>mm²</td>
                        <td>{{ '↑ 增大' if avg_sway_area > 300 else '正常' }}</td>
                    </tr>
                    <tr>
                        <td class="parameter-name">跌倒风险评分</td>
                        <td class="measured-value">{{ "%.2f"|format(avg_fall_risk) }}</td>
                        <td class="reference-range">[<0.3]</td>
                        <td>-</td>
                        <td>{{ '↑ 高风险' if avg_fall_risk > 0.3 else '低风险' }}</td>
                    </tr>
                </tbody>
            </table>
        </div>

        <!-- 评估结论 -->
        <div class="conclusion-section">
            <div class="conclusion-title">评估结论：</div>
            <div class="conclusion-content">
                <p>{{ interpretation }}</p>
                {% if all_abnormalities %}
                <p><strong>主要异常发现：</strong></p>
                <ul>
                {% for abnormality in set(all_abnormalities) %}
                    <li>{{ abnormality }}</li>
                {% endfor %}
                </ul>
                {% endif %}
            </div>
        </div>

        <!-- 医学建议 -->
        {% if all_recommendations %}
        <div class="recommendations">
            <h4>医学建议</h4>
            <ul class="recommendation-list">
            {% for recommendation in all_recommendations %}
                <li>{{ recommendation }}</li>
            {% endfor %}
            </ul>
        </div>
        {% endif %}

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
        test_summaries=test_summaries,
        avg_score=avg_score,
        risk_level_display=risk_level_display,
        risk_level_class=risk_level_class,
        highest_risk=highest_risk,
        num_tests=num_tests,
        avg_walking_speed=avg_walking_speed,
        avg_step_length=avg_step_length,
        avg_cadence=avg_cadence,
        avg_stance_phase=avg_stance_phase,
        avg_cop_displacement=avg_cop_displacement,
        avg_sway_area=avg_sway_area,
        avg_fall_risk=avg_fall_risk,
        interpretation=interpretation,
        all_abnormalities=all_abnormalities,
        all_recommendations=all_recommendations,
        set=set  # 传递set函数到模板
    )
    
    return html