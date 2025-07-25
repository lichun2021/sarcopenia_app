"""
SarcNeuro Edge 报告生成器
"""
import os
import json
from datetime import datetime
from typing import Dict, Any, Optional
from jinja2 import Template
from pathlib import Path

from core.analyzer import SarcopeniaAnalysis, PatientInfo

class ReportGenerator:
    """专业医疗报告生成器"""
    
    def __init__(self):
        self.template_dir = Path(__file__).parent.parent / "templates"
        self.template_dir.mkdir(exist_ok=True)
    
    async def generate_html_report(
        self, 
        analysis: SarcopeniaAnalysis,
        patient: PatientInfo,
        test_info: Dict[str, Any]
    ) -> str:
        """生成HTML医疗报告"""
        
        # 报告模板
        template_content = """
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
            <h2 class="report-title">肌少症智能分析报告</h2>
            
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
                        <span class="value">{{ test_info.report_id[:8] }}</span>
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
                        <span class="value">{{ test_info.data_points }}个</span>
                    </div>
                </div>
            </div>
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
                        <td class="measured-value">{{ "%.1f"|format(analysis.overall_score) }}</td>
                        <td class="reference-range">[80-100]</td>
                        <td>
                            {% if analysis.overall_score >= 80 %}
                                <span class="status-normal">正常</span>
                            {% elif analysis.overall_score >= 60 %}
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
                                {{ '需关注' if analysis.risk_level != 'LOW' else '正常' }}
                            </span>
                        </td>
                    </tr>
                    <tr>
                        <td class="parameter-name">分析置信度</td>
                        <td class="measured-value">{{ "%.1f"|format(analysis.confidence * 100) }}%</td>
                        <td class="reference-range">[>90%]</td>
                        <td>
                            <span class="status-normal">可靠</span>
                        </td>
                    </tr>
                </tbody>
            </table>
        </div>

        <!-- 步态分析结果 -->
        <div class="analysis-table-section">
            <h3 class="section-header">步态分析结果</h3>
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
                        <td class="measured-value">{{ "%.2f"|format(gait.walking_speed) }}</td>
                        <td class="reference-range">[0.8-1.6]</td>
                        <td>m/s</td>
                        <td>{{ '↓ 偏低' if gait.walking_speed < 0.8 else ('↑ 偏高' if gait.walking_speed > 1.8 else '正常') }}</td>
                    </tr>
                    <tr>
                        <td class="parameter-name">步长</td>
                        <td class="measured-value">{{ "%.1f"|format(gait.step_length) }}</td>
                        <td class="reference-range">[45-85]</td>
                        <td>cm</td>
                        <td>{{ '↓ 偏短' if gait.step_length < 45 else ('↑ 偏长' if gait.step_length > 85 else '正常') }}</td>
                    </tr>
                    <tr>
                        <td class="parameter-name">步频</td>
                        <td class="measured-value">{{ "%.1f"|format(gait.cadence) }}</td>
                        <td class="reference-range">[80-130]</td>
                        <td>步/分钟</td>
                        <td>{{ '↓ 偏低' if gait.cadence < 80 else ('↑ 偏高' if gait.cadence > 130 else '正常') }}</td>
                    </tr>
                    <tr>
                        <td class="parameter-name">站立相</td>
                        <td class="measured-value">{{ "%.1f"|format(gait.stance_phase) }}</td>
                        <td class="reference-range">[58-65]</td>
                        <td>%</td>
                        <td>{{ '↓ 偏短' if gait.stance_phase < 58 else ('↑ 延长' if gait.stance_phase > 68 else '正常') }}</td>
                    </tr>
                    {% if gait.left_step_height %}
                    <tr>
                        <td class="parameter-name">左脚步高</td>
                        <td class="measured-value">{{ "%.1f"|format(gait.left_step_height * 100) }}</td>
                        <td class="reference-range">[10-15]</td>
                        <td>cm</td>
                        <td>{{ '正常' if 0.10 <= gait.left_step_height <= 0.15 else '异常' }}</td>
                    </tr>
                    {% endif %}
                    {% if gait.right_step_height %}
                    <tr>
                        <td class="parameter-name">右脚步高</td>
                        <td class="measured-value">{{ "%.1f"|format(gait.right_step_height * 100) }}</td>
                        <td class="reference-range">[10-15]</td>
                        <td>cm</td>
                        <td>{{ '正常' if 0.10 <= gait.right_step_height <= 0.15 else '异常' }}</td>
                    </tr>
                    {% endif %}
                    <tr>
                        <td class="parameter-name">不对称指数</td>
                        <td class="measured-value">{{ "%.3f"|format(gait.asymmetry_index) }}</td>
                        <td class="reference-range">[<0.08]</td>
                        <td>-</td>
                        <td>{{ '↑ 异常' if gait.asymmetry_index > 0.08 else '正常' }}</td>
                    </tr>
                </tbody>
            </table>
        </div>

        <!-- 平衡分析结果 -->
        <div class="analysis-table-section">
            <h3 class="section-header">平衡分析结果</h3>
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
                        <td class="measured-value">{{ "%.1f"|format(balance.cop_displacement) }}</td>
                        <td class="reference-range">[<15]</td>
                        <td>mm</td>
                        <td>{{ '↑ 异常' if balance.cop_displacement > 15 else '正常' }}</td>
                    </tr>
                    <tr>
                        <td class="parameter-name">摆动面积</td>
                        <td class="measured-value">{{ "%.1f"|format(balance.sway_area) }}</td>
                        <td class="reference-range">[<300]</td>
                        <td>mm²</td>
                        <td>{{ '↑ 增大' if balance.sway_area > 300 else '正常' }}</td>
                    </tr>
                    <tr>
                        <td class="parameter-name">跌倒风险评分</td>
                        <td class="measured-value">{{ "%.3f"|format(balance.fall_risk_score) }}</td>
                        <td class="reference-range">[<0.3]</td>
                        <td>-</td>
                        <td>{{ '↑ 高风险' if balance.fall_risk_score > 0.3 else '低风险' }}</td>
                    </tr>
                </tbody>
            </table>
        </div>

        <!-- 评估结论 -->
        <div class="conclusion-section">
            <div class="conclusion-title">评估结论：</div>
            <div class="conclusion-content">
                <p>{{ analysis.interpretation }}</p>
                {% if analysis.abnormalities %}
                <p><strong>主要异常发现：</strong></p>
                <ul>
                {% for abnormality in analysis.abnormalities %}
                    <li>{{ abnormality }}</li>
                {% endfor %}
                </ul>
                {% endif %}
            </div>
        </div>

        <!-- 医学建议 -->
        {% if analysis.recommendations %}
        <div class="recommendations">
            <h4>医学建议</h4>
            <ul class="recommendation-list">
            {% for recommendation in analysis.recommendations %}
                <li>{{ recommendation }}</li>
            {% endfor %}
            </ul>
        </div>
        {% endif %}

        <!-- 签名区域 -->
        <div class="signature-section">
            <div class="signature-item">
                <div class="signature-line"></div>
                <p>检查医师：AI智能分析</p>
            </div>
            <div class="signature-item">
                <div class="signature-line"></div>
                <p>审核医师：</p>
            </div>
            <div class="signature-item">
                <div class="signature-line"></div>
                <p>报告日期：{{ generation_time }}</p>
            </div>
        </div>
    </div>
</body>
</html>
        """
        
        # 准备模板数据
        template_data = {
            "report_number": test_info.get("report_id", "R2025001"),
            "patient": patient,
            "analysis": analysis,
            "gait": analysis.gait_analysis,
            "balance": analysis.balance_analysis,
            "test_info": test_info,
            "generation_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "test_type_display": self._get_test_type_display(test_info.get("test_type", "COMPREHENSIVE")),
            "risk_level_display": self._get_risk_level_display(analysis.risk_level),
            "risk_level_class": self._get_risk_level_class(analysis.risk_level)
        }
        
        # 渲染模板
        template = Template(template_content)
        return template.render(**template_data)
    
    def _get_test_type_display(self, test_type: str) -> str:
        """获取测试类型显示名称"""
        type_map = {
            "COMPREHENSIVE": "综合评估",
            "WALK_4_LAPS": "步道4圈",
            "WALK_7_LAPS": "步道7圈",
            "STAND_LEFT": "左脚站立",
            "STAND_RIGHT": "右脚站立",
            "TANDEM_STANCE": "前后脚站立",
            "HEEL_TOE": "脚跟脚尖",
            "SIT_TO_STAND_5": "起坐5次",
            "STATIC_SITTING": "静坐10s"
        }
        return type_map.get(test_type, test_type)
    
    def _get_risk_level_display(self, risk_level: str) -> str:
        """获取风险等级显示"""
        level_map = {
            "LOW": "低风险",
            "MEDIUM": "中风险", 
            "HIGH": "高风险",
            "CRITICAL": "严重风险"
        }
        return level_map.get(risk_level.upper(), risk_level)
    
    def _get_risk_level_class(self, risk_level: str) -> str:
        """获取风险等级样式类"""
        class_map = {
            "LOW": "normal",
            "MEDIUM": "warning",
            "HIGH": "danger",
            "CRITICAL": "danger"
        }
        return class_map.get(risk_level.upper(), "normal")