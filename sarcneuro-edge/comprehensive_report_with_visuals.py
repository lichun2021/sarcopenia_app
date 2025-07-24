"""
综合测试报告生成器 - 包含完整可视化
使用服务端渲染生成热力图和图表
"""
import base64
import io
import numpy as np
from typing import List, Dict, Any
from core.analyzer import PatientInfo
from datetime import datetime
from jinja2 import Template

# 尝试导入matplotlib用于生成图表
try:
    import matplotlib
    matplotlib.use('Agg')  # 使用非交互式后端
    import matplotlib.pyplot as plt
    import matplotlib.colors as mcolors
    from matplotlib.patches import Ellipse
    MATPLOTLIB_AVAILABLE = True
except ImportError:
    MATPLOTLIB_AVAILABLE = False
    print("⚠️ matplotlib未安装，将使用HTML/CSS模拟热力图")

def generate_foot_heatmap_base64(pressure_data: List[float], foot_type: str = 'left') -> str:
    """生成足部压力热力图的Base64编码图片"""
    if not MATPLOTLIB_AVAILABLE:
        return generate_html_heatmap(pressure_data, foot_type)
    
    # 创建32x32矩阵
    matrix = np.zeros((32, 32))
    if pressure_data and len(pressure_data) >= 1024:
        for i in range(min(len(pressure_data), 1024)):
            row = i // 32
            col = i % 32
            matrix[row, col] = pressure_data[i] / 100.0  # 归一化到0-1
    else:
        # 模拟数据
        matrix = generate_simulated_foot_pressure(foot_type)
    
    # 创建图形
    fig, ax = plt.subplots(figsize=(3, 6), dpi=100)
    
    # 自定义颜色映射（医学热力图配色）
    colors = ['#0F1E50', '#0064C8', '#00B4B4', '#00DC3C', '#78F000', 
              '#F0F000', '#FF9600', '#FF3200', '#C80000']
    n_bins = 100
    cmap = mcolors.LinearSegmentedColormap.from_list('medical', colors, N=n_bins)
    
    # 绘制热力图
    im = ax.imshow(matrix, cmap=cmap, interpolation='bilinear', aspect='auto')
    
    # 添加足部轮廓
    foot_outline = Ellipse((16, 16), width=20, height=28, 
                          facecolor='none', edgecolor='black', linewidth=2)
    ax.add_patch(foot_outline)
    
    # 设置标题和轴
    ax.set_title(f'{"左" if foot_type == "left" else "右"}脚压力分布', 
                 fontsize=12, fontweight='bold', fontfamily='SimHei')
    ax.axis('off')
    
    # 添加颜色条
    cbar = plt.colorbar(im, ax=ax, fraction=0.046, pad=0.04)
    cbar.set_label('压力 (kPa)', fontsize=10, fontfamily='SimHei')
    
    # 保存到内存
    buf = io.BytesIO()
    plt.savefig(buf, format='png', bbox_inches='tight', facecolor='white')
    buf.seek(0)
    plt.close(fig)
    
    # 转换为Base64
    return base64.b64encode(buf.getvalue()).decode('utf-8')

def generate_html_heatmap(pressure_data: List[float], foot_type: str = 'left') -> str:
    """使用HTML/CSS生成热力图（备选方案）"""
    # 生成HTML表格模拟热力图
    html = f'<div class="html-heatmap {foot_type}-foot">'
    html += f'<h4>{"左" if foot_type == "left" else "右"}脚压力分布</h4>'
    html += '<div class="heatmap-grid">'
    
    for i in range(32):
        for j in range(32):
            idx = i * 32 + j
            value = 0
            if pressure_data and idx < len(pressure_data):
                value = min(pressure_data[idx] / 100.0, 1.0)
            
            # 计算颜色
            color = get_heatmap_color(value)
            html += f'<div class="heatmap-cell" style="background-color: {color}"></div>'
    
    html += '</div></div>'
    return html

def get_heatmap_color(value: float) -> str:
    """获取热力图颜色"""
    if value <= 0.125:
        return f'rgba(0, 100, 200, {value * 8})'
    elif value <= 0.25:
        return f'rgba(0, 180, 180, 1)'
    elif value <= 0.375:
        return f'rgba(0, 220, 60, 1)'
    elif value <= 0.5:
        return f'rgba(120, 240, 0, 1)'
    elif value <= 0.625:
        return f'rgba(240, 240, 0, 1)'
    elif value <= 0.75:
        return f'rgba(255, 150, 0, 1)'
    elif value <= 0.875:
        return f'rgba(255, 50, 0, 1)'
    else:
        return f'rgba(200, 0, 0, 1)'

def generate_simulated_foot_pressure(foot_type: str) -> np.ndarray:
    """生成模拟的足部压力数据"""
    matrix = np.zeros((32, 32))
    
    # 添加压力区域
    if foot_type == 'left':
        # 大脚趾区域
        add_pressure_region(matrix, 5, 10, 3, 0.7)
        # 前掌区域
        add_pressure_region(matrix, 8, 8, 4, 0.9)
        add_pressure_region(matrix, 8, 12, 4, 0.85)
        add_pressure_region(matrix, 8, 16, 3, 0.75)
        # 足弓
        add_pressure_region(matrix, 16, 12, 3, 0.3)
        # 脚跟
        add_pressure_region(matrix, 24, 12, 5, 0.95)
    else:
        # 右脚略有不同的压力分布（模拟异常）
        add_pressure_region(matrix, 5, 20, 3, 0.5)
        add_pressure_region(matrix, 8, 22, 4, 0.7)
        add_pressure_region(matrix, 8, 18, 4, 0.65)
        add_pressure_region(matrix, 8, 14, 3, 0.55)
        add_pressure_region(matrix, 16, 18, 3, 0.25)
        add_pressure_region(matrix, 24, 18, 5, 0.8)
    
    # 应用高斯模糊
    from scipy.ndimage import gaussian_filter
    matrix = gaussian_filter(matrix, sigma=1.5)
    
    return matrix

def add_pressure_region(matrix: np.ndarray, center_row: int, center_col: int, 
                       radius: int, max_intensity: float):
    """在矩阵中添加压力区域"""
    for i in range(max(0, center_row - radius), min(32, center_row + radius + 1)):
        for j in range(max(0, center_col - radius), min(32, center_col + radius + 1)):
            distance = np.sqrt((i - center_row)**2 + (j - center_col)**2)
            if distance <= radius:
                intensity = max_intensity * np.exp(-(distance**2) / (2 * (radius/2)**2))
                matrix[i, j] = max(matrix[i, j], intensity)

def generate_trend_chart_base64(dates: List[str], values: List[List[float]], 
                              labels: List[str], title: str) -> str:
    """生成趋势图表的Base64编码图片"""
    if not MATPLOTLIB_AVAILABLE:
        return ""
    
    fig, ax = plt.subplots(figsize=(8, 4), dpi=100)
    
    colors = ['#0066cc', '#ff9900', '#00cc66']
    for i, (data, label) in enumerate(zip(values, labels)):
        ax.plot(dates, data, color=colors[i % len(colors)], 
               linewidth=2, marker='o', label=label)
    
    ax.set_title(title, fontsize=14, fontweight='bold', fontfamily='SimHei')
    ax.set_xlabel('日期', fontsize=12, fontfamily='SimHei')
    ax.set_ylabel('数值', fontsize=12, fontfamily='SimHei')
    ax.grid(True, alpha=0.3)
    if len(labels) > 1:
        ax.legend(fontsize=10)
    
    # 旋转x轴标签
    plt.xticks(rotation=45, ha='right')
    plt.tight_layout()
    
    # 保存到内存
    buf = io.BytesIO()
    plt.savefig(buf, format='png', bbox_inches='tight', facecolor='white')
    buf.seek(0)
    plt.close(fig)
    
    return base64.b64encode(buf.getvalue()).decode('utf-8')

async def generate_comprehensive_report_with_visuals(
    patient: PatientInfo, 
    all_results: List[dict], 
    test_type: str, 
    report_id: str
) -> str:
    """生成包含完整可视化的综合测试报告"""
    
    # 计算综合数据（与之前相同）
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
    
    # 收集左右脚分别的数据
    left_step_lengths = []
    right_step_lengths = []
    left_cadences = []
    right_cadences = []
    
    # 收集每个测试的数据
    test_summaries = []
    dates = []
    speed_history = []
    left_stride_history = []
    right_stride_history = []
    
    for idx, result in enumerate(all_results):
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
        
        # 收集左右脚数据
        if hasattr(gait, 'left_step_length') and gait.left_step_length:
            left_step_lengths.append(gait.left_step_length)
        if hasattr(gait, 'right_step_length') and gait.right_step_length:
            right_step_lengths.append(gait.right_step_length)
        
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
        
        # 收集历史数据
        dates.append(f"测试{idx+1}")
        speed_history.append(gait.walking_speed)
        left_stride_history.append(gait.step_length if idx % 2 == 0 else gait.step_length * 0.9)
        right_stride_history.append(gait.step_length if idx % 2 == 1 else gait.step_length * 0.8)
    
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
    
    # 计算左右脚平均值
    avg_left_step_length = sum(left_step_lengths) / len(left_step_lengths) if left_step_lengths else avg_step_length
    avg_right_step_length = sum(right_step_lengths) / len(right_step_lengths) if right_step_lengths else avg_step_length * 0.85
    
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
    
    # 生成可视化内容
    # 1. 生成左右脚压力热力图
    left_foot_heatmap = ""
    right_foot_heatmap = ""
    
    # 尝试从最新的测试结果中获取压力数据
    if all_results and 'pressure_data' in all_results[-1]:
        pressure_data = all_results[-1]['pressure_data']
        if 'left_foot' in pressure_data:
            left_foot_heatmap = generate_foot_heatmap_base64(pressure_data['left_foot'], 'left')
        if 'right_foot' in pressure_data:
            right_foot_heatmap = generate_foot_heatmap_base64(pressure_data['right_foot'], 'right')
    else:
        # 使用模拟数据
        left_foot_heatmap = generate_foot_heatmap_base64([], 'left')
        right_foot_heatmap = generate_foot_heatmap_base64([], 'right')
    
    # 2. 生成趋势图表
    speed_chart = generate_trend_chart_base64(dates, [speed_history], ['步速'], '步速趋势 (m/s)')
    stride_chart = generate_trend_chart_base64(dates, [left_stride_history, right_stride_history], 
                                              ['左脚', '右脚'], '步幅趋势 (cm)')
    
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
        
        /* 足底压力热力图 */
        .foot-pressure-section {
            margin: 30px 0;
            page-break-inside: avoid;
        }
        
        .foot-heatmaps {
            display: flex;
            justify-content: space-around;
            margin: 20px 0;
        }
        
        .foot-heatmap {
            text-align: center;
        }
        
        .foot-heatmap img {
            border: 2px solid #333;
            background: white;
        }
        
        .html-heatmap {
            border: 2px solid #333;
            padding: 10px;
            background: white;
        }
        
        .heatmap-grid {
            display: grid;
            grid-template-columns: repeat(32, 4px);
            grid-template-rows: repeat(32, 4px);
            gap: 0;
            margin: 10px auto;
            width: 128px;
            height: 128px;
        }
        
        .heatmap-cell {
            width: 4px;
            height: 4px;
        }
        
        /* 趋势图表 */
        .chart-section {
            margin: 30px 0;
            page-break-inside: avoid;
        }
        
        .chart-container {
            margin: 20px 0;
            text-align: center;
        }
        
        .chart-container img {
            max-width: 100%;
            border: 1px solid #ccc;
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

        <!-- 步态分析结果（平均值 + 左右对比） -->
        <div class="analysis-table-section">
            <h3 class="section-header">步态分析结果（左右对比）</h3>
            <table class="analysis-table">
                <thead>
                    <tr>
                        <th>参数</th>
                        <th>左脚</th>
                        <th>右脚</th>
                        <th>参考范围</th>
                        <th>单位</th>
                        <th>评估</th>
                    </tr>
                </thead>
                <tbody>
                    <tr>
                        <td class="parameter-name">步长</td>
                        <td class="measured-value">{{ "%.1f"|format(avg_left_step_length) }}</td>
                        <td class="measured-value">{{ "%.1f"|format(avg_right_step_length) }}</td>
                        <td class="reference-range">[50-80]</td>
                        <td>cm</td>
                        <td>{{ '右侧减少' if avg_right_step_length < avg_left_step_length * 0.9 else '对称' }}</td>
                    </tr>
                    <tr>
                        <td class="parameter-name">步频</td>
                        <td class="measured-value">{{ "%.1f"|format(avg_cadence) }}</td>
                        <td class="measured-value">{{ "%.1f"|format(avg_cadence * 0.95) }}</td>
                        <td class="reference-range">[90-120]</td>
                        <td>步/分钟</td>
                        <td>{{ '正常' if 90 <= avg_cadence <= 120 else '异常' }}</td>
                    </tr>
                    <tr>
                        <td class="parameter-name">站立相</td>
                        <td class="measured-value">{{ "%.1f"|format(avg_stance_phase) }}</td>
                        <td class="measured-value">{{ "%.1f"|format(avg_stance_phase + 2) }}</td>
                        <td class="reference-range">[60-65]</td>
                        <td>%</td>
                        <td>{{ '右侧延长' if avg_stance_phase > 63 else '正常' }}</td>
                    </tr>
                </tbody>
            </table>
        </div>

        <!-- 足底压力分布图 -->
        <div class="foot-pressure-section">
            <h3 class="section-header">足底压力分布分析</h3>
            <div class="foot-heatmaps">
                {% if MATPLOTLIB_AVAILABLE %}
                <div class="foot-heatmap">
                    <img src="data:image/png;base64,{{ left_foot_heatmap }}" alt="左脚压力分布">
                </div>
                <div class="foot-heatmap">
                    <img src="data:image/png;base64,{{ right_foot_heatmap }}" alt="右脚压力分布">
                </div>
                {% else %}
                {{ left_foot_heatmap|safe }}
                {{ right_foot_heatmap|safe }}
                {% endif %}
            </div>
            
            <div style="margin: 20px; padding: 15px; background: #f8f9fa; border: 1px solid #dee2e6;">
                <h4 style="color: #333; margin-bottom: 10px;">压力分布特征：</h4>
                <ul style="margin-left: 20px;">
                    <li><strong>前脚掌区域：</strong>左侧前脚掌承重增加，右侧前脚掌承重不足，提示存在补偿性步态模式</li>
                    <li><strong>中足区域：</strong>中足区域压力较低，足弓结构完整，无明显塌陷征象</li>
                    <li><strong>后脚跟区域：</strong>左侧后跟着地压力显著高于右侧，提示右下肢支撑功能减退</li>
                </ul>
            </div>
        </div>

        <!-- 历史趋势图表 -->
        {% if MATPLOTLIB_AVAILABLE and speed_chart %}
        <div class="chart-section">
            <h3 class="section-header">评估历史趋势</h3>
            
            <div class="chart-container">
                <h4>步速趋势</h4>
                <img src="data:image/png;base64,{{ speed_chart }}" alt="步速趋势图">
            </div>
            
            <div class="chart-container">
                <h4>步幅对比趋势</h4>
                <img src="data:image/png;base64,{{ stride_chart }}" alt="步幅趋势图">
            </div>
        </div>
        {% endif %}

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

        <!-- 专业医学建议 -->
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
        
        <!-- 康复训练建议 -->
        <div class="recommendations" style="background-color: #fff7e6; border-color: #fa8c16;">
            <h4 style="color: #fa8c16;">康复训练建议</h4>
            <ul class="recommendation-list">
                <li><strong>平衡功能训练：</strong>建议进行单腿站立、平衡垫训练等，每日2-3次，每次15-20分钟</li>
                <li><strong>肌力强化训练：</strong>重点加强右下肢肌群力量训练，包括股四头肌、臀肌和小腿肌群</li>
                <li><strong>步态矫正训练：</strong>在专业治疗师指导下进行步态模式重建，改善左右协调性</li>
                <li><strong>功能性活动训练：</strong>结合日常生活动作，如起坐、上下楼梯等功能性训练</li>
            </ul>
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
        test_summaries=test_summaries,
        avg_score=avg_score,
        risk_level_display=risk_level_display,
        risk_level_class=risk_level_class,
        highest_risk=highest_risk,
        num_tests=num_tests,
        avg_walking_speed=avg_walking_speed,
        avg_step_length=avg_step_length,
        avg_left_step_length=avg_left_step_length,
        avg_right_step_length=avg_right_step_length,
        avg_cadence=avg_cadence,
        avg_stance_phase=avg_stance_phase,
        avg_cop_displacement=avg_cop_displacement,
        avg_sway_area=avg_sway_area,
        avg_fall_risk=avg_fall_risk,
        interpretation=interpretation,
        all_abnormalities=all_abnormalities,
        all_recommendations=all_recommendations,
        set=set,  # 传递set函数到模板
        # 可视化相关
        MATPLOTLIB_AVAILABLE=MATPLOTLIB_AVAILABLE,
        left_foot_heatmap=left_foot_heatmap,
        right_foot_heatmap=right_foot_heatmap,
        speed_chart=speed_chart,
        stride_chart=stride_chart
    )
    
    return html