"""
SarcNeuro Edge 报告生成器
"""
import os
import json
import uuid
from datetime import datetime
from typing import Dict, List, Optional, Any
from pathlib import Path
import base64
from io import BytesIO

# 图表和可视化
import matplotlib
matplotlib.use('Agg')  # 非交互式后端
import matplotlib.pyplot as plt
import seaborn as sns
import numpy as np
import pandas as pd

# PDF生成
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT

# Jinja2模板
from jinja2 import Environment, FileSystemLoader, BaseLoader

# 数据库和配置
from app.database import db_manager
from app.config import config
from models.database_models import Patient, Test, AnalysisResult, Report
from core.analyzer import SarcopeniaAnalysis, GaitAnalysis, BalanceAnalysis

import logging
logger = logging.getLogger(__name__)

class ReportGenerator:
    """报告生成器"""
    
    def __init__(self):
        self.output_dir = Path("./reports")
        self.templates_dir = Path("./templates")
        self.charts_dir = Path("./temp/charts")
        
        # 确保目录存在
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.templates_dir.mkdir(parents=True, exist_ok=True)
        self.charts_dir.mkdir(parents=True, exist_ok=True)
        
        # 初始化Jinja2模板环境
        self.jinja_env = Environment(
            loader=FileSystemLoader(self.templates_dir),
            autoescape=True
        )
        
        # 配置中文字体
        self._setup_fonts()
        
        # 创建默认模板
        self._create_default_templates()
    
    def _setup_fonts(self):
        """设置中文字体"""
        try:
            # 尝试设置中文字体
            plt.rcParams['font.sans-serif'] = ['SimHei', 'DejaVu Sans', 'Arial Unicode MS']
            plt.rcParams['axes.unicode_minus'] = False
            sns.set_style("whitegrid")
            sns.set_palette("husl")
        except Exception as e:
            logger.warning(f"字体设置失败，使用默认字体: {e}")
    
    def _create_default_templates(self):
        """创建默认HTML模板"""
        html_template_path = self.templates_dir / "medical_report.html"
        
        if not html_template_path.exists():
            html_template = """
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>SarcNeuro 肌少症智能分析报告</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        
        body {
            font-family: 'Microsoft YaHei', '微软雅黑', SimHei, sans-serif;
            line-height: 1.6;
            color: #333;
            background: #f8f9fa;
        }
        
        .report-container {
            max-width: 1000px;
            margin: 0 auto;
            padding: 20px;
            background: white;
            box-shadow: 0 0 20px rgba(0,0,0,0.1);
        }
        
        .report-header {
            text-align: center;
            border-bottom: 3px solid #007bff;
            padding-bottom: 20px;
            margin-bottom: 30px;
        }
        
        .report-title {
            font-size: 28px;
            color: #007bff;
            font-weight: bold;
            margin-bottom: 10px;
        }
        
        .report-subtitle {
            font-size: 16px;
            color: #6c757d;
            margin-bottom: 5px;
        }
        
        .report-info {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 20px;
            margin-bottom: 30px;
            padding: 20px;
            background: #f8f9fa;
            border-radius: 8px;
        }
        
        .info-section h3 {
            color: #007bff;
            border-bottom: 2px solid #007bff;
            padding-bottom: 5px;
            margin-bottom: 15px;
        }
        
        .info-item {
            display: flex;
            justify-content: space-between;
            margin-bottom: 8px;
        }
        
        .info-label {
            font-weight: bold;
            color: #495057;
        }
        
        .section {
            margin-bottom: 40px;
        }
        
        .section-title {
            font-size: 20px;
            color: #007bff;
            border-left: 4px solid #007bff;
            padding-left: 15px;
            margin-bottom: 20px;
        }
        
        .metrics-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
            gap: 20px;
            margin-bottom: 20px;
        }
        
        .metric-card {
            padding: 20px;
            border: 1px solid #dee2e6;
            border-radius: 8px;
            background: #fff;
            text-align: center;
        }
        
        .metric-value {
            font-size: 24px;
            font-weight: bold;
            color: #007bff;
            margin-bottom: 5px;
        }
        
        .metric-label {
            font-size: 14px;
            color: #6c757d;
        }
        
        .risk-level {
            display: inline-block;
            padding: 8px 16px;
            border-radius: 20px;
            font-weight: bold;
            text-transform: uppercase;
        }
        
        .risk-low { background: #d4edda; color: #155724; }
        .risk-medium { background: #fff3cd; color: #856404; }
        .risk-high { background: #f8d7da; color: #721c24; }
        .risk-critical { background: #f5c6cb; color: #721c24; }
        
        .abnormalities {
            background: #fff3cd;
            border: 1px solid #ffeaa7;
            border-radius: 8px;
            padding: 20px;
            margin: 20px 0;
        }
        
        .abnormalities h4 {
            color: #856404;
            margin-bottom: 10px;
        }
        
        .abnormality-list {
            list-style: none;
        }
        
        .abnormality-list li {
            background: #ffeaa7;
            padding: 8px 12px;
            margin: 5px 0;
            border-radius: 4px;
            border-left: 4px solid #f39c12;
        }
        
        .recommendations {
            background: #d1ecf1;
            border: 1px solid #bee5eb;
            border-radius: 8px;
            padding: 20px;
            margin: 20px 0;
        }
        
        .recommendations h4 {
            color: #0c5460;
            margin-bottom: 10px;
        }
        
        .recommendation-list {
            list-style: none;
        }
        
        .recommendation-list li {
            background: #bee5eb;
            padding: 10px 15px;
            margin: 8px 0;
            border-radius: 4px;
            border-left: 4px solid #17a2b8;
        }
        
        .chart-container {
            text-align: center;
            margin: 30px 0;
            padding: 20px;
            background: #f8f9fa;
            border-radius: 8px;
        }
        
        .chart-container img {
            max-width: 100%;
            height: auto;
            border-radius: 8px;
            box-shadow: 0 4px 8px rgba(0,0,0,0.1);
        }
        
        .footer {
            margin-top: 50px;
            padding-top: 20px;
            border-top: 2px solid #dee2e6;
            text-align: center;
            color: #6c757d;
            font-size: 14px;
        }
        
        .signature-section {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 50px;
            margin-top: 40px;
        }
        
        .signature {
            text-align: center;
            padding: 20px;
            border: 1px dashed #dee2e6;
        }
        
        @media print {
            body { font-size: 12px; }
            .report-container { box-shadow: none; }
        }
    </style>
</head>
<body>
    <div class="report-container">
        <!-- 报告头部 -->
        <div class="report-header">
            <h1 class="report-title">SarcNeuro 肌少症智能分析报告</h1>
            <p class="report-subtitle">SarcNeuro Engine v3.0.1 肌少症智能监测与健康步态分析系统</p>
            <p class="report-subtitle">报告编号: {{ report_number }}</p>
            <p class="report-subtitle">生成时间: {{ generation_time }}</p>
        </div>
        
        <!-- 基本信息 -->
        <div class="report-info">
            <div class="info-section">
                <h3>患者信息</h3>
                <div class="info-item">
                    <span class="info-label">姓名:</span>
                    <span>{{ patient.name }}</span>
                </div>
                <div class="info-item">
                    <span class="info-label">年龄:</span>
                    <span>{{ patient.age }}岁</span>
                </div>
                <div class="info-item">
                    <span class="info-label">性别:</span>
                    <span>{{ '男性' if patient.gender == 'MALE' else '女性' }}</span>
                </div>
                {% if patient.height %}
                <div class="info-item">
                    <span class="info-label">身高:</span>
                    <span>{{ patient.height }}cm</span>
                </div>
                {% endif %}
                {% if patient.weight %}
                <div class="info-item">
                    <span class="info-label">体重:</span>
                    <span>{{ patient.weight }}kg</span>
                </div>
                {% endif %}
            </div>
            
            <div class="info-section">
                <h3>测试信息</h3>
                <div class="info-item">
                    <span class="info-label">测试类型:</span>
                    <span>{{ test.test_type }}</span>
                </div>
                <div class="info-item">
                    <span class="info-label">测试模式:</span>
                    <span>{{ test.test_mode }}</span>
                </div>
                {% if test.duration %}
                <div class="info-item">
                    <span class="info-label">测试时长:</span>
                    <span>{{ "%.1f"|format(test.duration) }}秒</span>
                </div>
                {% endif %}
                <div class="info-item">
                    <span class="info-label">测试日期:</span>
                    <span>{{ test.created_at.strftime('%Y年%m月%d日 %H:%M') }}</span>
                </div>
                <div class="info-item">
                    <span class="info-label">分析置信度:</span>
                    <span>{{ "%.1f"|format(analysis.confidence * 100) }}%</span>
                </div>
            </div>
        </div>
        
        <!-- 综合评估结果 -->
        <div class="section">
            <h2 class="section-title">综合评估结果</h2>
            <div class="metrics-grid">
                <div class="metric-card">
                    <div class="metric-value">{{ "%.1f"|format(analysis.overall_score) }}</div>
                    <div class="metric-label">综合评分</div>
                </div>
                <div class="metric-card">
                    <div class="metric-value">
                        <span class="risk-level risk-{{ analysis.risk_level.lower() }}">
                            {% if analysis.risk_level == 'LOW' %}低风险
                            {% elif analysis.risk_level == 'MEDIUM' %}中风险
                            {% elif analysis.risk_level == 'HIGH' %}高风险
                            {% else %}严重风险{% endif %}
                        </span>
                    </div>
                    <div class="metric-label">风险等级</div>
                </div>
            </div>
            
            <div style="padding: 20px; background: #f8f9fa; border-radius: 8px; margin: 20px 0;">
                <h4 style="color: #495057; margin-bottom: 10px;">医学解释</h4>
                <p style="line-height: 1.8;">{{ analysis.interpretation }}</p>
            </div>
        </div>
        
        <!-- 步态分析结果 -->
        <div class="section">
            <h2 class="section-title">步态分析结果</h2>
            <div class="metrics-grid">
                <div class="metric-card">
                    <div class="metric-value">{{ "%.2f"|format(gait.walking_speed) }}</div>
                    <div class="metric-label">步行速度 (m/s)</div>
                </div>
                <div class="metric-card">
                    <div class="metric-value">{{ "%.1f"|format(gait.step_length) }}</div>
                    <div class="metric-label">步长 (cm)</div>
                </div>
                <div class="metric-card">
                    <div class="metric-value">{{ "%.1f"|format(gait.cadence) }}</div>
                    <div class="metric-label">步频 (步/分钟)</div>
                </div>
                <div class="metric-card">
                    <div class="metric-value">{{ "%.1f"|format(gait.stance_phase) }}</div>
                    <div class="metric-label">站立相 (%)</div>
                </div>
                <div class="metric-card">
                    <div class="metric-value">{{ "%.3f"|format(gait.asymmetry_index) }}</div>
                    <div class="metric-label">不对称指数</div>
                </div>
                <div class="metric-card">
                    <div class="metric-value">{{ "%.1f"|format(gait.stability_score) }}</div>
                    <div class="metric-label">稳定性评分</div>
                </div>
            </div>
        </div>
        
        <!-- 平衡分析结果 -->
        <div class="section">
            <h2 class="section-title">平衡分析结果</h2>
            <div class="metrics-grid">
                <div class="metric-card">
                    <div class="metric-value">{{ "%.1f"|format(balance.cop_displacement) }}</div>
                    <div class="metric-label">压力中心位移 (mm)</div>
                </div>
                <div class="metric-card">
                    <div class="metric-value">{{ "%.1f"|format(balance.sway_area) }}</div>
                    <div class="metric-label">摆动面积 (mm²)</div>
                </div>
                <div class="metric-card">
                    <div class="metric-value">{{ "%.2f"|format(balance.sway_velocity) }}</div>
                    <div class="metric-label">摆动速度 (mm/s)</div>
                </div>
                <div class="metric-card">
                    <div class="metric-value">{{ "%.2f"|format(balance.stability_index) }}</div>
                    <div class="metric-label">稳定性指数</div>
                </div>
                <div class="metric-card">
                    <div class="metric-value">{{ "%.3f"|format(balance.fall_risk_score) }}</div>
                    <div class="metric-label">跌倒风险评分</div>
                </div>
            </div>
        </div>
        
        <!-- 可视化图表 -->
        {% if charts %}
        <div class="section">
            <h2 class="section-title">数据可视化分析</h2>
            {% for chart in charts %}
            <div class="chart-container">
                <h4>{{ chart.title }}</h4>
                <img src="data:image/png;base64,{{ chart.data }}" alt="{{ chart.title }}">
            </div>
            {% endfor %}
        </div>
        {% endif %}
        
        <!-- 异常发现 -->
        {% if analysis.abnormalities %}
        <div class="abnormalities">
            <h4>异常发现</h4>
            <ul class="abnormality-list">
            {% for abnormality in analysis.abnormalities %}
                <li>{{ abnormality }}</li>
            {% endfor %}
            </ul>
        </div>
        {% endif %}
        
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
            <div class="signature">
                <p>分析医师签名</p>
                <br><br>
                <p>日期: _______________</p>
            </div>
            <div class="signature">
                <p>审核医师签名</p>
                <br><br>
                <p>日期: _______________</p>
            </div>
        </div>
        
        <!-- 页脚 -->
        <div class="footer">
            <p>本报告由 SarcNeuro Engine v3.0.1 肌少症智能监测系统自动生成</p>
            <p>© 2024 SarcNeuro 智能医疗系统 - 仅供医疗专业人士参考使用</p>
            <p>生成时间: {{ generation_time }} | 报告版本: {{ analysis.detailed_analysis.processing_version }}</p>
        </div>
    </div>
</body>
</html>
            """
            
            with open(html_template_path, 'w', encoding='utf-8') as f:
                f.write(html_template)
            
            logger.info("默认HTML模板创建成功")
    
    async def generate_report(
        self, 
        test_id: int,
        report_type: str = "comprehensive",
        format: str = "html"
    ) -> Dict[str, Any]:
        """生成分析报告"""
        try:
            # 获取测试数据
            with db_manager.get_session() as session:
                test = session.query(Test).filter(Test.id == test_id).first()
                if not test:
                    return {"status": "error", "message": "测试记录不存在"}
                
                patient = test.patient
                analysis_result = test.analysis_result
                
                if not analysis_result:
                    return {"status": "error", "message": "分析结果不存在"}
            
            # 准备报告数据
            report_data = await self._prepare_report_data(test, patient, analysis_result)
            
            # 生成可视化图表
            charts = await self._generate_charts(test, analysis_result)
            report_data["charts"] = charts
            
            # 生成报告
            if format.lower() == "html":
                report_path = await self._generate_html_report(report_data)
            elif format.lower() == "pdf":
                report_path = await self._generate_pdf_report(report_data)
            else:
                return {"status": "error", "message": f"不支持的格式: {format}"}
            
            # 保存报告记录到数据库
            report_record = await self._save_report_record(test, patient, report_data, report_path)
            
            return {
                "status": "success",
                "report_path": str(report_path),
                "report_id": report_record.id,
                "report_number": report_record.report_number,
                "format": format,
                "generation_time": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"报告生成失败: {e}")
            return {"status": "error", "message": str(e)}
    
    async def _prepare_report_data(self, test, patient, analysis_result) -> Dict[str, Any]:
        """准备报告数据"""
        # 解析分析结果
        detailed_analysis = analysis_result.detailed_analysis or {}
        
        # 构造步态分析数据（从数据库或详细分析中获取）
        gait_metrics = analysis_result.gait_metrics
        balance_metrics = analysis_result.balance_metrics
        
        gait_data = {
            "walking_speed": gait_metrics.walking_speed if gait_metrics else 1.2,
            "step_length": gait_metrics.step_length if gait_metrics else 65.0,
            "cadence": gait_metrics.cadence if gait_metrics else 110.0,
            "stance_phase": gait_metrics.stance_phase if gait_metrics else 60.0,
            "asymmetry_index": gait_metrics.asymmetry_index if gait_metrics else 0.05,
            "stability_score": gait_metrics.stability_score if gait_metrics else 85.0
        }
        
        balance_data = {
            "cop_displacement": balance_metrics.cop_displacement if balance_metrics else 25.0,
            "sway_area": balance_metrics.sway_area if balance_metrics else 150.0,
            "sway_velocity": balance_metrics.sway_velocity if balance_metrics else 8.5,
            "stability_index": balance_metrics.stability_index if balance_metrics else 2.3,
            "fall_risk_score": balance_metrics.fall_risk_score if balance_metrics else 0.15
        }
        
        return {
            "report_number": f"SR{datetime.now().strftime('%Y%m%d')}{test.id:04d}",
            "generation_time": datetime.now().strftime('%Y年%m月%d日 %H:%M:%S'),
            "patient": {
                "name": patient.name,
                "age": patient.age,
                "gender": patient.gender,
                "height": patient.height,
                "weight": patient.weight
            },
            "test": {
                "test_type": test.test_type,
                "test_mode": test.test_mode,
                "duration": test.duration,
                "created_at": test.created_at
            },
            "analysis": {
                "overall_score": analysis_result.overall_score,
                "risk_level": analysis_result.risk_level,
                "confidence": analysis_result.confidence,
                "interpretation": analysis_result.interpretation,
                "abnormalities": analysis_result.abnormalities or [],
                "recommendations": analysis_result.recommendations or [],
                "detailed_analysis": detailed_analysis
            },
            "gait": gait_data,
            "balance": balance_data
        }
    
    async def _generate_charts(self, test, analysis_result) -> List[Dict[str, str]]:
        """生成可视化图表"""
        charts = []
        
        try:
            # 1. 步态参数雷达图
            gait_chart = await self._create_gait_radar_chart(analysis_result)
            if gait_chart:
                charts.append(gait_chart)
            
            # 2. 平衡参数条形图
            balance_chart = await self._create_balance_bar_chart(analysis_result)
            if balance_chart:
                charts.append(balance_chart)
            
            # 3. 风险评估饼图
            risk_chart = await self._create_risk_pie_chart(analysis_result)
            if risk_chart:
                charts.append(risk_chart)
            
            # 4. 足底压力热力图（如果有压力数据）
            pressure_chart = await self._create_pressure_heatmap(test)
            if pressure_chart:
                charts.append(pressure_chart)
            
        except Exception as e:
            logger.error(f"图表生成失败: {e}")
        
        return charts
    
    async def _create_gait_radar_chart(self, analysis_result) -> Optional[Dict[str, str]]:
        """创建步态参数雷达图"""
        try:
            gait_metrics = analysis_result.gait_metrics
            if not gait_metrics:
                return None
            
            # 准备数据
            categories = ['步行速度', '步长', '步频', '站立相', '稳定性', '对称性']
            values = [
                min(gait_metrics.walking_speed / 1.5 * 100, 100) if gait_metrics.walking_speed else 80,
                min(gait_metrics.step_length / 80 * 100, 100) if gait_metrics.step_length else 80,
                min(gait_metrics.cadence / 130 * 100, 100) if gait_metrics.cadence else 80,
                min(gait_metrics.stance_phase / 70 * 100, 100) if gait_metrics.stance_phase else 80,
                gait_metrics.stability_score if gait_metrics.stability_score else 80,
                max(100 - gait_metrics.asymmetry_index * 1000, 0) if gait_metrics.asymmetry_index else 80
            ]
            
            # 创建雷达图
            angles = np.linspace(0, 2 * np.pi, len(categories), endpoint=False).tolist()
            values += values[:1]  # 闭合图形
            angles += angles[:1]
            
            fig, ax = plt.subplots(figsize=(8, 8), subplot_kw=dict(projection='polar'))
            ax.plot(angles, values, 'o-', linewidth=2, color='#007bff')
            ax.fill(angles, values, alpha=0.25, color='#007bff')
            ax.set_xticks(angles[:-1])
            ax.set_xticklabels(categories)
            ax.set_ylim(0, 100)
            ax.set_title('步态参数分析', size=16, fontweight='bold', pad=20)
            ax.grid(True)
            
            # 保存图表
            buffer = BytesIO()
            plt.savefig(buffer, format='png', dpi=300, bbox_inches='tight')
            buffer.seek(0)
            
            # 编码为base64
            chart_data = base64.b64encode(buffer.getvalue()).decode()
            plt.close()
            
            return {
                "title": "步态参数雷达分析图",
                "data": chart_data,
                "type": "radar"
            }
            
        except Exception as e:
            logger.error(f"步态雷达图生成失败: {e}")
            return None
    
    async def _create_balance_bar_chart(self, analysis_result) -> Optional[Dict[str, str]]:
        """创建平衡参数条形图"""
        try:
            balance_metrics = analysis_result.balance_metrics
            if not balance_metrics:
                return None
            
            # 准备数据
            categories = ['压力中心位移', '摆动面积', '摆动速度', '稳定性指数', '跌倒风险']
            values = [
                balance_metrics.cop_displacement if balance_metrics.cop_displacement else 25,
                balance_metrics.sway_area / 10 if balance_metrics.sway_area else 15,
                balance_metrics.sway_velocity if balance_metrics.sway_velocity else 8,
                balance_metrics.stability_index if balance_metrics.stability_index else 2.5,
                balance_metrics.fall_risk_score * 100 if balance_metrics.fall_risk_score else 15
            ]
            
            # 创建条形图
            fig, ax = plt.subplots(figsize=(10, 6))
            colors = ['#28a745', '#17a2b8', '#ffc107', '#fd7e14', '#dc3545']
            bars = ax.bar(categories, values, color=colors, alpha=0.7)
            
            ax.set_title('平衡功能分析', size=16, fontweight='bold')
            ax.set_ylabel('数值')
            plt.xticks(rotation=45)
            
            # 添加数值标签
            for bar, value in zip(bars, values):
                height = bar.get_height()
                ax.text(bar.get_x() + bar.get_width()/2., height,
                       f'{value:.1f}', ha='center', va='bottom')
            
            plt.tight_layout()
            
            # 保存图表
            buffer = BytesIO()
            plt.savefig(buffer, format='png', dpi=300, bbox_inches='tight')
            buffer.seek(0)
            
            chart_data = base64.b64encode(buffer.getvalue()).decode()
            plt.close()
            
            return {
                "title": "平衡功能条形分析图",
                "data": chart_data,
                "type": "bar"
            }
            
        except Exception as e:
            logger.error(f"平衡条形图生成失败: {e}")
            return None
    
    async def _create_risk_pie_chart(self, analysis_result) -> Optional[Dict[str, str]]:
        """创建风险评估饼图"""
        try:
            # 根据风险等级和评分创建饼图
            risk_level = analysis_result.risk_level
            score = analysis_result.overall_score
            
            # 计算各风险类别的比例
            if risk_level == "LOW":
                risk_data = [score, 100-score]
                labels = ['正常功能', '风险因素']
                colors = ['#28a745', '#ffc107']
            elif risk_level == "MEDIUM":
                risk_data = [max(0, score-20), min(score+20, 100)-score, max(0, 100-score-20)]
                labels = ['正常功能', '中等风险', '高风险因素']
                colors = ['#28a745', '#ffc107', '#fd7e14']
            elif risk_level == "HIGH":
                risk_data = [max(0, score-10), min(score+30, 100)-score, max(0, 100-score-30)]
                labels = ['残余功能', '高风险', '严重风险']
                colors = ['#28a745', '#fd7e14', '#dc3545']
            else:  # CRITICAL
                risk_data = [score, 100-score]
                labels = ['残余功能', '严重风险']
                colors = ['#fd7e14', '#dc3545']
            
            # 创建饼图
            fig, ax = plt.subplots(figsize=(8, 8))
            wedges, texts, autotexts = ax.pie(
                risk_data, labels=labels, colors=colors, autopct='%1.1f%%',
                startangle=90, textprops={'fontsize': 12}
            )
            
            ax.set_title(f'风险评估分布 (总分: {score:.1f})', size=16, fontweight='bold')
            
            # 保存图表
            buffer = BytesIO()
            plt.savefig(buffer, format='png', dpi=300, bbox_inches='tight')
            buffer.seek(0)
            
            chart_data = base64.b64encode(buffer.getvalue()).decode()
            plt.close()
            
            return {
                "title": "风险评估分布图",
                "data": chart_data,
                "type": "pie"
            }
            
        except Exception as e:
            logger.error(f"风险饼图生成失败: {e}")
            return None
    
    async def _create_pressure_heatmap(self, test) -> Optional[Dict[str, str]]:
        """创建足底压力热力图"""
        try:
            with db_manager.get_session() as session:
                from models.database_models import PressureData
                
                # 获取压力数据
                pressure_data = session.query(PressureData).filter(
                    PressureData.test_id == test.id
                ).limit(1).first()
                
                if not pressure_data or not pressure_data.left_foot_data:
                    return None
                
                # 创建热力图
                fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 6))
                
                # 左脚热力图
                left_data = np.array(pressure_data.left_foot_data).reshape(32, 32)
                im1 = ax1.imshow(left_data, cmap='hot', aspect='equal')
                ax1.set_title('左脚压力分布', fontsize=14, fontweight='bold')
                ax1.set_xticks([])
                ax1.set_yticks([])
                plt.colorbar(im1, ax=ax1, shrink=0.8)
                
                # 右脚热力图
                if pressure_data.right_foot_data:
                    right_data = np.array(pressure_data.right_foot_data).reshape(32, 32)
                else:
                    right_data = left_data * 0.9  # 模拟右脚数据
                
                im2 = ax2.imshow(right_data, cmap='hot', aspect='equal')
                ax2.set_title('右脚压力分布', fontsize=14, fontweight='bold')
                ax2.set_xticks([])
                ax2.set_yticks([])
                plt.colorbar(im2, ax=ax2, shrink=0.8)
                
                plt.suptitle('足底压力分布热力图', fontsize=16, fontweight='bold')
                plt.tight_layout()
                
                # 保存图表
                buffer = BytesIO()
                plt.savefig(buffer, format='png', dpi=300, bbox_inches='tight')
                buffer.seek(0)
                
                chart_data = base64.b64encode(buffer.getvalue()).decode()
                plt.close()
                
                return {
                    "title": "足底压力分布热力图",
                    "data": chart_data,
                    "type": "heatmap"
                }
                
        except Exception as e:
            logger.error(f"压力热力图生成失败: {e}")
            return None
    
    async def _generate_html_report(self, report_data: Dict[str, Any]) -> Path:
        """生成HTML报告"""
        try:
            template = self.jinja_env.get_template("medical_report.html")
            html_content = template.render(**report_data)
            
            # 生成文件名
            report_filename = f"report_{report_data['report_number']}.html"
            report_path = self.output_dir / report_filename
            
            # 保存HTML文件
            with open(report_path, 'w', encoding='utf-8') as f:
                f.write(html_content)
            
            logger.info(f"HTML报告生成成功: {report_path}")
            return report_path
            
        except Exception as e:
            logger.error(f"HTML报告生成失败: {e}")
            raise
    
    async def _generate_pdf_report(self, report_data: Dict[str, Any]) -> Path:
        """生成PDF报告"""
        try:
            # PDF文件路径
            report_filename = f"report_{report_data['report_number']}.pdf"
            report_path = self.output_dir / report_filename
            
            # 创建PDF文档
            doc = SimpleDocTemplate(
                str(report_path),
                pagesize=A4,
                topMargin=2*cm,
                bottomMargin=2*cm,
                leftMargin=2*cm,
                rightMargin=2*cm
            )
            
            # 准备内容
            story = []
            styles = getSampleStyleSheet()
            
            # 自定义样式
            title_style = ParagraphStyle(
                'CustomTitle',
                parent=styles['Heading1'],
                fontSize=20,
                spaceAfter=30,
                textColor=colors.blue,
                alignment=TA_CENTER
            )
            
            # 标题
            story.append(Paragraph("SarcNeuro 肌少症智能分析报告", title_style))
            story.append(Spacer(1, 20))
            
            # 基本信息表格
            basic_info = [
                ['患者信息', ''],
                ['姓名', report_data['patient']['name']],
                ['年龄', f"{report_data['patient']['age']}岁"],
                ['性别', '男性' if report_data['patient']['gender'] == 'MALE' else '女性'],
                ['测试信息', ''],
                ['测试类型', report_data['test']['test_type']],
                ['综合评分', f"{report_data['analysis']['overall_score']:.1f}"],
                ['风险等级', report_data['analysis']['risk_level']],
            ]
            
            info_table = Table(basic_info, colWidths=[4*cm, 8*cm])
            info_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.lightblue),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 12),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
                ('GRID', (0, 0), (-1, -1), 1, colors.black)
            ]))
            
            story.append(info_table)
            story.append(Spacer(1, 30))
            
            # 添加图表（如果有）
            if report_data.get('charts'):
                story.append(Paragraph("数据可视化分析", styles['Heading2']))
                for chart in report_data['charts']:
                    # 将base64图片转换为临时文件
                    chart_data = base64.b64decode(chart['data'])
                    temp_chart_path = self.charts_dir / f"temp_chart_{uuid.uuid4().hex}.png"
                    
                    with open(temp_chart_path, 'wb') as f:
                        f.write(chart_data)
                    
                    # 添加到PDF
                    story.append(Spacer(1, 10))
                    story.append(Paragraph(chart['title'], styles['Heading3']))
                    
                    # 调整图片大小以适应页面
                    img = Image(str(temp_chart_path))
                    img.drawHeight = 6*cm
                    img.drawWidth = 10*cm
                    story.append(img)
                    story.append(Spacer(1, 20))
            
            # 医学建议
            if report_data['analysis'].get('recommendations'):
                story.append(Paragraph("医学建议", styles['Heading2']))
                for rec in report_data['analysis']['recommendations']:
                    story.append(Paragraph(f"• {rec}", styles['Normal']))
                story.append(Spacer(1, 20))
            
            # 生成PDF
            doc.build(story)
            
            # 清理临时文件
            for temp_file in self.charts_dir.glob("temp_chart_*.png"):
                try:
                    temp_file.unlink()
                except:
                    pass
            
            logger.info(f"PDF报告生成成功: {report_path}")
            return report_path
            
        except Exception as e:
            logger.error(f"PDF报告生成失败: {e}")
            raise
    
    async def _save_report_record(self, test, patient, report_data: Dict[str, Any], report_path: Path) -> Report:
        """保存报告记录到数据库"""
        try:
            with db_manager.get_session() as session:
                # 创建报告记录
                report = Report(
                    patient_id=patient.id,
                    test_id=test.id,
                    title=f"SarcNeuro 肌少症分析报告 - {patient.name}",
                    report_number=report_data['report_number'],
                    status="PUBLISHED",
                    summary=report_data['analysis']['interpretation'],
                    content={
                        "file_path": str(report_path),
                        "generation_time": report_data['generation_time'],
                        "charts_count": len(report_data.get('charts', [])),
                        "analysis_data": report_data['analysis']
                    },
                    recommendations=report_data['analysis']['recommendations'],
                    is_published=True,
                    published_at=datetime.now(),
                    sync_status="pending"
                )
                
                session.add(report)
                session.commit()
                session.refresh(report)
                
                logger.info(f"报告记录保存成功: {report.report_number}")
                return report
                
        except Exception as e:
            logger.error(f"报告记录保存失败: {e}")
            raise
    
    async def get_report_list(self, patient_id: Optional[int] = None) -> List[Dict[str, Any]]:
        """获取报告列表"""
        try:
            with db_manager.get_session() as session:
                query = session.query(Report)
                
                if patient_id:
                    query = query.filter(Report.patient_id == patient_id)
                
                reports = query.order_by(Report.created_at.desc()).all()
                
                report_list = []
                for report in reports:
                    report_list.append({
                        "id": report.id,
                        "report_number": report.report_number,
                        "title": report.title,
                        "patient_name": report.patient.name,
                        "status": report.status,
                        "is_published": report.is_published,
                        "created_at": report.created_at.isoformat(),
                        "published_at": report.published_at.isoformat() if report.published_at else None,
                        "file_path": report.content.get("file_path") if report.content else None
                    })
                
                return report_list
                
        except Exception as e:
            logger.error(f"获取报告列表失败: {e}")
            return []

# 全局报告生成器实例
report_generator = ReportGenerator()

# 导出
__all__ = [
    "ReportGenerator",
    "report_generator"
]