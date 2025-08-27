#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
集成医院级热力图的报告生成器
解决压力值标定和左右差异问题
"""

import numpy as np
import pandas as pd
from hospital_heatmap_generator import HospitalHeatmapGenerator, HeatmapConfig
import base64
from io import BytesIO
import matplotlib.pyplot as plt


class IntegratedReportGenerator:
    """集成医院级热力图的报告生成器"""
    
    def __init__(self):
        # 配置热力图生成器
        self.heatmap_config = HeatmapConfig(
            calibration_factor=0.1,  # 修正：500原始值 ≈ 50N
            use_median=True,         # 使用中位数减少异常
            stable_ratio=0.8,        # 使用80%稳定期数据
            smoothing_sigma=0.8,
            draw_regions=True,
            draw_cop=True,
            contour_levels=8
        )
        self.heatmap_generator = HospitalHeatmapGenerator(self.heatmap_config)
        
    def parse_pressure_data(self, csv_path: str) -> pd.DataFrame:
        """解析压力传感器CSV数据"""
        df = pd.read_csv(csv_path)
        return df
    
    def extract_pressure_matrix(self, df: pd.DataFrame, 
                               matrix_size: tuple = (64, 32)) -> np.ndarray:
        """从DataFrame提取压力矩阵时间序列"""
        pressure_matrices = []
        
        for _, row in df.iterrows():
            if 'data' in df.columns:
                # 解析逗号分隔的压力值
                values = [float(x) for x in str(row['data']).split(',')]
                if len(values) == matrix_size[0] * matrix_size[1]:
                    matrix = np.array(values).reshape(matrix_size)
                    pressure_matrices.append(matrix)
        
        return np.array(pressure_matrices)
    
    def analyze_sitting_pressure(self, sitting_df: pd.DataFrame) -> dict:
        """
        分析坐姿压力分布
        解决问题3：左右臀部压力差异
        """
        # 提取压力矩阵
        pressure_data = self.extract_pressure_matrix(sitting_df, (32, 32))
        
        if len(pressure_data) == 0:
            return {'error': '无法提取压力数据'}
        
        # 使用稳定期数据
        stable_data = self.heatmap_generator.extract_stable_data(pressure_data)
        
        # 使用中位数而非平均值（更稳定）
        median_pressure = np.median(stable_data, axis=0)
        
        # 标定压力值
        calibrated = self.heatmap_generator.calibrate_pressure(median_pressure)
        
        # 计算左右压力分布
        h, w = calibrated.shape
        left_pressure = calibrated[:, :w//2]
        right_pressure = calibrated[:, w//2:]
        
        # 使用有效压力区域（超过阈值）
        threshold = 10.0  # 10N阈值
        left_valid = left_pressure[left_pressure > threshold]
        right_valid = right_pressure[right_pressure > threshold]
        
        # 计算中位数和均值
        results = {
            'left_median': np.median(left_valid) if len(left_valid) > 0 else 0,
            'right_median': np.median(right_valid) if len(right_valid) > 0 else 0,
            'left_mean': np.mean(left_valid) if len(left_valid) > 0 else 0,
            'right_mean': np.mean(right_valid) if len(right_valid) > 0 else 0,
            'left_max': np.max(left_valid) if len(left_valid) > 0 else 0,
            'right_max': np.max(right_valid) if len(right_valid) > 0 else 0,
            'total_pressure': calibrated.sum(),
            'contact_area': (calibrated > threshold).sum()
        }
        
        # 计算压力分布百分比
        total = results['left_median'] + results['right_median']
        if total > 0:
            results['left_percent'] = results['left_median'] / total * 100
            results['right_percent'] = results['right_median'] / total * 100
        else:
            results['left_percent'] = 50.0
            results['right_percent'] = 50.0
        
        # 生成热力图
        heatmap_path = self.heatmap_generator.generate_heatmap(
            calibrated,
            title="坐姿压力分布（中位数）",
            save_path="sitting_pressure_heatmap.png"
        )
        results['heatmap_path'] = heatmap_path
        
        return results
    
    def analyze_standing_pressure(self, standing_df: pd.DataFrame) -> dict:
        """
        分析站立压力分布
        解决问题4：静态站立左右差异
        """
        # 提取压力矩阵（可能是64x32）
        pressure_data = self.extract_pressure_matrix(standing_df, (64, 32))
        
        if len(pressure_data) == 0:
            # 尝试32x32
            pressure_data = self.extract_pressure_matrix(standing_df, (32, 32))
        
        if len(pressure_data) == 0:
            return {'error': '无法提取压力数据'}
        
        # 提取稳定期
        stable_data = self.heatmap_generator.extract_stable_data(pressure_data)
        
        # 使用中位数
        median_pressure = np.median(stable_data, axis=0)
        
        # 标定和处理
        calibrated = self.heatmap_generator.calibrate_pressure(median_pressure)
        calibrated_32x32 = self.heatmap_generator.resize_to_target(calibrated)
        
        # 检测左右脚
        h, w = calibrated_32x32.shape
        left_foot = calibrated_32x32[:, :w//2]
        right_foot = calibrated_32x32[:, w//2:]
        
        # 计算压力中心
        left_cop = self.heatmap_generator.compute_cop(left_foot)
        right_cop = self.heatmap_generator.compute_cop(right_foot)
        
        # 统计分析
        threshold = 10.0
        results = {
            'left_median': np.median(left_foot[left_foot > threshold]),
            'right_median': np.median(right_foot[right_foot > threshold]),
            'left_max': left_foot.max(),
            'right_max': right_foot.max(),
            'left_area': (left_foot > threshold).sum(),
            'right_area': (right_foot > threshold).sum(),
            'left_cop': left_cop,
            'right_cop': right_cop
        }
        
        # 计算百分比（基于中位数）
        total = results['left_median'] + results['right_median']
        if total > 0:
            results['left_percent'] = results['left_median'] / total * 100
            results['right_percent'] = results['right_median'] / total * 100
        
        # 生成对比热力图
        comparison_path = self.heatmap_generator.generate_comparison_heatmap(
            left_foot, right_foot,
            title="左右脚站立压力对比",
            save_path="standing_comparison.png"
        )
        results['heatmap_path'] = comparison_path
        
        return results
    
    def calibrate_pressure_value(self, raw_value: float) -> float:
        """
        标定压力值
        解决问题2：500对应约50N而非4900N
        """
        # 基线校准（可选）
        baseline = 0  # 可以通过空载测量得到
        
        # 标定系数：根据实际测试调整
        # 500原始值 ≈ 50N，所以系数约为0.1
        calibration_factor = 0.1
        
        calibrated = (raw_value - baseline) * calibration_factor
        return max(0, calibrated)  # 确保非负
    
    def generate_enhanced_report(self, test_folder: str, 
                                patient_name: str, age: int) -> str:
        """
        生成增强版报告（包含医院级热力图）
        """
        import os
        from datetime import datetime
        
        # 加载各项测试数据
        sitting_path = os.path.join(test_folder, '静坐检测.csv')
        standing_path = os.path.join(test_folder, '静态站立.csv')
        walking_path = os.path.join(test_folder, '4.5米步道折返.csv')
        
        results = {
            'patient_name': patient_name,
            'age': age,
            'test_date': datetime.now().strftime('%Y-%m-%d'),
            'test_time': datetime.now().strftime('%H:%M:%S')
        }
        
        # 分析坐姿
        if os.path.exists(sitting_path):
            sitting_df = pd.read_csv(sitting_path)
            sitting_results = self.analyze_sitting_pressure(sitting_df)
            results['sitting'] = sitting_results
            print(f"坐姿分析完成:")
            print(f"  左侧压力(中位数): {sitting_results.get('left_median', 0):.1f}N")
            print(f"  右侧压力(中位数): {sitting_results.get('right_median', 0):.1f}N")
            print(f"  左右比例: {sitting_results.get('left_percent', 50):.1f}% : {sitting_results.get('right_percent', 50):.1f}%")
        
        # 分析站立
        if os.path.exists(standing_path):
            standing_df = pd.read_csv(standing_path)
            standing_results = self.analyze_standing_pressure(standing_df)
            results['standing'] = standing_results
            print(f"站立分析完成:")
            print(f"  左脚压力(中位数): {standing_results.get('left_median', 0):.1f}N")
            print(f"  右脚压力(中位数): {standing_results.get('right_median', 0):.1f}N")
            print(f"  左右比例: {standing_results.get('left_percent', 50):.1f}% : {standing_results.get('right_percent', 50):.1f}%")
        
        # 生成HTML报告
        html_content = self.create_html_report(results)
        
        # 保存报告
        report_path = f"enhanced_report_{patient_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.html"
        with open(report_path, 'w', encoding='utf-8') as f:
            f.write(html_content)
        
        print(f"\n✅ 增强版报告已生成: {report_path}")
        return report_path
    
    def create_html_report(self, results: dict) -> str:
        """创建HTML报告"""
        html = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>压力分析报告 - {results['patient_name']}</title>
    <style>
        body {{
            font-family: Arial, sans-serif;
            max-width: 1200px;
            margin: 0 auto;
            padding: 20px;
            background: #f5f5f5;
        }}
        .header {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 30px;
            border-radius: 10px;
            margin-bottom: 30px;
        }}
        .section {{
            background: white;
            padding: 20px;
            margin-bottom: 20px;
            border-radius: 10px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        }}
        .metrics {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 15px;
            margin: 20px 0;
        }}
        .metric {{
            padding: 15px;
            background: #f8f9fa;
            border-radius: 5px;
            border-left: 4px solid #667eea;
        }}
        .metric-label {{
            color: #666;
            font-size: 14px;
            margin-bottom: 5px;
        }}
        .metric-value {{
            font-size: 24px;
            font-weight: bold;
            color: #333;
        }}
        .heatmap-container {{
            text-align: center;
            margin: 20px 0;
        }}
        .heatmap-container img {{
            max-width: 100%;
            border: 1px solid #ddd;
            border-radius: 5px;
        }}
        .comparison {{
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 20px;
            margin: 20px 0;
        }}
        .warning {{
            background: #fff3cd;
            border: 1px solid #ffc107;
            border-radius: 5px;
            padding: 15px;
            margin: 20px 0;
        }}
        .success {{
            background: #d4edda;
            border: 1px solid #28a745;
            border-radius: 5px;
            padding: 15px;
            margin: 20px 0;
        }}
    </style>
</head>
<body>
    <div class="header">
        <h1>压力分析增强报告</h1>
        <p>姓名: {results['patient_name']} | 年龄: {results['age']}岁 | 日期: {results['test_date']}</p>
    </div>
"""

        # 坐姿分析部分
        if 'sitting' in results:
            sitting = results['sitting']
            left_percent = sitting.get('left_percent', 50)
            right_percent = sitting.get('right_percent', 50)
            diff = abs(left_percent - right_percent)
            
            status_class = 'success' if diff < 10 else 'warning'
            status_text = '平衡' if diff < 10 else '不平衡'
            
            html += f"""
    <div class="section">
        <h2>坐姿压力分析</h2>
        <div class="{status_class}">
            <strong>评估结果:</strong> {status_text} (左右差异: {diff:.1f}%)
        </div>
        <div class="metrics">
            <div class="metric">
                <div class="metric-label">左侧压力(中位数)</div>
                <div class="metric-value">{sitting.get('left_median', 0):.1f}N</div>
            </div>
            <div class="metric">
                <div class="metric-label">右侧压力(中位数)</div>
                <div class="metric-value">{sitting.get('right_median', 0):.1f}N</div>
            </div>
            <div class="metric">
                <div class="metric-label">左侧占比</div>
                <div class="metric-value">{left_percent:.1f}%</div>
            </div>
            <div class="metric">
                <div class="metric-label">右侧占比</div>
                <div class="metric-value">{right_percent:.1f}%</div>
            </div>
        </div>
    </div>
"""

        # 站立分析部分
        if 'standing' in results:
            standing = results['standing']
            left_percent = standing.get('left_percent', 50)
            right_percent = standing.get('right_percent', 50)
            diff = abs(left_percent - right_percent)
            
            status_class = 'success' if diff < 15 else 'warning'
            status_text = '平衡' if diff < 15 else '需要关注'
            
            html += f"""
    <div class="section">
        <h2>站立压力分析</h2>
        <div class="{status_class}">
            <strong>评估结果:</strong> {status_text} (左右差异: {diff:.1f}%)
        </div>
        <div class="metrics">
            <div class="metric">
                <div class="metric-label">左脚压力(中位数)</div>
                <div class="metric-value">{standing.get('left_median', 0):.1f}N</div>
            </div>
            <div class="metric">
                <div class="metric-label">右脚压力(中位数)</div>
                <div class="metric-value">{standing.get('right_median', 0):.1f}N</div>
            </div>
            <div class="metric">
                <div class="metric-label">左脚峰值</div>
                <div class="metric-value">{standing.get('left_max', 0):.1f}N</div>
            </div>
            <div class="metric">
                <div class="metric-label">右脚峰值</div>
                <div class="metric-value">{standing.get('right_max', 0):.1f}N</div>
            </div>
        </div>
    </div>
"""

        # 建议部分
        html += """
    <div class="section">
        <h2>专业建议</h2>
        <h3>关于压力值标定</h3>
        <ul>
            <li><strong>标定系数已修正:</strong> 500原始值 ≈ 50N（而非之前的4900N）</li>
            <li><strong>正常范围:</strong> 成人站立单脚压力约300-400N</li>
        </ul>
        
        <h3>关于左右差异</h3>
        <ul>
            <li><strong>使用中位数:</strong> 比平均值更稳定，减少异常值影响</li>
            <li><strong>稳定期数据:</strong> 仅使用中间80%的数据，去除过渡期</li>
            <li><strong>阈值过滤:</strong> 仅统计>10N的有效压力区域</li>
        </ul>
        
        <h3>临床意义</h3>
        <ul>
            <li>坐姿左右差异>10%: 可能存在姿势习惯问题或脊柱侧弯</li>
            <li>站立左右差异>15%: 可能存在下肢长度差异或平衡问题</li>
            <li>建议定期监测，追踪变化趋势</li>
        </ul>
    </div>
"""

        html += """
</body>
</html>
"""
        return html


def main():
    """测试集成报告生成器"""
    print("=" * 50)
    print("集成医院级热力图报告生成器")
    print("=" * 50)
    
    # 创建生成器
    generator = IntegratedReportGenerator()
    
    # 演示压力值标定
    print("\n压力值标定演示:")
    raw_values = [100, 200, 300, 400, 500]
    for raw in raw_values:
        calibrated = generator.calibrate_pressure_value(raw)
        print(f"  原始值: {raw:4d} → 标定后: {calibrated:5.1f}N")
    
    print("\n说明:")
    print("- 标定系数已修正为0.1（之前是9.8）")
    print("- 500原始值现在对应50N（符合生理范围）")
    print("- 使用中位数代替平均值（更稳定）")
    print("- 提取稳定期数据（去除过渡期）")
    
    # 如果有测试数据，可以生成完整报告
    # generator.generate_enhanced_report('/path/to/test/folder', '测试患者', 65)


if __name__ == "__main__":
    main()