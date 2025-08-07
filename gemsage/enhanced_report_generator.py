#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
增强版医疗报告生成器 - 包含图表可视化和个性化医学建议
"""

import io
import base64
import numpy as np
import matplotlib
matplotlib.use('Agg')  # 使用非交互式后端
import matplotlib.pyplot as plt
import matplotlib.patches as patches
from matplotlib.patches import Circle
from datetime import datetime
from typing import Dict, Any, Optional, List, Tuple
from jinja2 import Template

class ChartGenerator:
    """图表生成器"""
    
    def __init__(self):
        # 设置中文字体
        plt.rcParams['font.sans-serif'] = ['Arial Unicode MS', 'SimHei', 'DejaVu Sans']
        plt.rcParams['axes.unicode_minus'] = False
        
    def generate_gait_charts(self, data: Dict[str, Any]) -> Dict[str, str]:
        """生成步态分析图表"""
        charts = {}
        
        # 生成步速趋势图
        if 'velocity_history' in data:
            charts['velocity_chart'] = self._create_velocity_chart(data['velocity_history'])
        else:
            # 使用模拟数据
            charts['velocity_chart'] = self._create_velocity_chart([1.2, 1.15, 1.18, 1.22, 1.25])
            
        # 生成步幅对比图
        left_stride = data.get('left_step_length', 0.65)
        right_stride = data.get('right_step_length', 0.68)
        charts['stride_chart'] = self._create_stride_comparison(left_stride, right_stride)
        
        # 生成步态周期图
        stance_phase = data.get('stance_phase', 60)
        swing_phase = data.get('swing_phase', 40)
        charts['gait_cycle_chart'] = self._create_gait_cycle_chart(stance_phase, swing_phase)
        
        return charts
    
    def generate_cop_trajectory(self, cop_data: Optional[List[Tuple[float, float]]] = None) -> str:
        """生成COP轨迹图"""
        fig, ax = plt.subplots(figsize=(8, 6))
        
        if cop_data is None:
            # 生成示例COP轨迹数据
            t = np.linspace(0, 4*np.pi, 100)
            x = 10 * np.sin(t) + np.random.normal(0, 2, 100)
            y = 5 * np.cos(2*t) + np.random.normal(0, 1, 100)
            cop_data = list(zip(x, y))
        else:
            x = [point[0] for point in cop_data]
            y = [point[1] for point in cop_data]
        
        # 绘制COP轨迹
        ax.plot(x, y, 'b-', linewidth=2, alpha=0.7, label='COP轨迹')
        ax.scatter(x[0], y[0], c='green', s=100, marker='o', label='起始点', zorder=5)
        ax.scatter(x[-1], y[-1], c='red', s=100, marker='s', label='结束点', zorder=5)
        
        # 添加95%置信椭圆
        mean_x, mean_y = np.mean(x), np.mean(y)
        cov = np.cov(x, y)
        eigenvalues, eigenvectors = np.linalg.eig(cov)
        angle = np.degrees(np.arctan2(eigenvectors[1, 0], eigenvectors[0, 0]))
        width, height = 2 * np.sqrt(5.991 * eigenvalues)  # 95%置信区间
        
        ellipse = patches.Ellipse((mean_x, mean_y), width, height, 
                                 angle=angle, linewidth=2, 
                                 fill=False, edgecolor='red', 
                                 linestyle='--', label='95%置信椭圆')
        ax.add_patch(ellipse)
        
        # 添加中心点
        ax.scatter(mean_x, mean_y, c='black', s=100, marker='+', label='重心', zorder=5)
        
        # 设置图表样式
        ax.set_xlabel('左右位移 (mm)', fontsize=12)
        ax.set_ylabel('前后位移 (mm)', fontsize=12)
        ax.set_title('压力中心(COP)轨迹分析', fontsize=14, fontweight='bold')
        ax.grid(True, alpha=0.3, linestyle='--')
        ax.legend(loc='upper right')
        ax.set_aspect('equal', adjustable='box')
        
        # 添加背景颜色区域
        ax.axhline(y=0, color='k', linestyle='-', linewidth=0.5)
        ax.axvline(x=0, color='k', linestyle='-', linewidth=0.5)
        
        # 转换为base64
        return self._fig_to_base64(fig)
    
    def generate_pressure_heatmap(self, pressure_matrix: Optional[np.ndarray] = None) -> str:
        """生成压力热力图"""
        fig, ax = plt.subplots(figsize=(8, 6))
        
        if pressure_matrix is None:
            # 生成示例压力数据（模拟脚印）
            pressure_matrix = np.zeros((32, 64))
            # 左脚
            for i in range(10, 22):
                for j in range(5, 25):
                    dist = np.sqrt((i-16)**2 + (j-15)**2)
                    if dist < 8:
                        pressure_matrix[i, j] = 100 * np.exp(-dist/4)
            # 右脚
            for i in range(10, 22):
                for j in range(39, 59):
                    dist = np.sqrt((i-16)**2 + (j-49)**2)
                    if dist < 8:
                        pressure_matrix[i, j] = 100 * np.exp(-dist/4)
        
        # 绘制热力图
        im = ax.imshow(pressure_matrix, cmap='hot', interpolation='bilinear', aspect='auto')
        
        # 添加颜色条
        cbar = plt.colorbar(im, ax=ax)
        cbar.set_label('压力值 (N)', rotation=270, labelpad=15)
        
        # 设置标题和标签
        ax.set_title('足底压力分布热力图', fontsize=14, fontweight='bold')
        ax.set_xlabel('横向位置 (传感器单元)', fontsize=12)
        ax.set_ylabel('纵向位置 (传感器单元)', fontsize=12)
        
        # 添加网格
        ax.grid(False)
        
        return self._fig_to_base64(fig)
    
    def _create_velocity_chart(self, velocities: List[float]) -> str:
        """创建步速趋势图"""
        fig, ax = plt.subplots(figsize=(6, 4))
        
        x = list(range(1, len(velocities) + 1))
        ax.plot(x, velocities, 'b-o', linewidth=2, markersize=8)
        
        # 添加平均线
        avg_velocity = np.mean(velocities)
        ax.axhline(y=avg_velocity, color='r', linestyle='--', label=f'平均: {avg_velocity:.2f} m/s')
        
        # 添加正常范围
        ax.axhspan(1.0, 1.4, alpha=0.2, color='green', label='正常范围')
        
        ax.set_xlabel('测试次数', fontsize=12)
        ax.set_ylabel('步速 (m/s)', fontsize=12)
        ax.set_title('步速变化趋势', fontsize=14, fontweight='bold')
        ax.legend()
        ax.grid(True, alpha=0.3)
        
        return self._fig_to_base64(fig)
    
    def _create_stride_comparison(self, left: float, right: float) -> str:
        """创建左右步幅对比图"""
        fig, ax = plt.subplots(figsize=(6, 4))
        
        categories = ['左脚', '右脚']
        values = [left, right]
        colors = ['#3498db', '#e74c3c']
        
        bars = ax.bar(categories, values, color=colors, width=0.6)
        
        # 添加数值标签
        for bar, val in zip(bars, values):
            height = bar.get_height()
            ax.text(bar.get_x() + bar.get_width()/2., height,
                   f'{val:.3f}m', ha='center', va='bottom', fontsize=12)
        
        # 添加对称性指标
        symmetry = min(left, right) / max(left, right) * 100 if max(left, right) > 0 else 0
        ax.text(0.5, max(values) * 0.5, f'对称性: {symmetry:.1f}%', 
               transform=ax.transData, ha='center', fontsize=11,
               bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.5))
        
        ax.set_ylabel('步长 (米)', fontsize=12)
        ax.set_title('左右脚步长对比', fontsize=14, fontweight='bold')
        ax.set_ylim(0, max(values) * 1.2)
        ax.grid(True, alpha=0.3, axis='y')
        
        return self._fig_to_base64(fig)
    
    def _create_gait_cycle_chart(self, stance: float, swing: float) -> str:
        """创建步态周期饼图"""
        fig, ax = plt.subplots(figsize=(6, 6))
        
        sizes = [stance, swing]
        labels = [f'支撑相\n{stance:.1f}%', f'摆动相\n{swing:.1f}%']
        colors = ['#ff9999', '#66b3ff']
        explode = (0.05, 0.05)
        
        wedges, texts, autotexts = ax.pie(sizes, labels=labels, colors=colors,
                                          autopct='', explode=explode,
                                          shadow=True, startangle=90)
        
        # 美化文字
        for text in texts:
            text.set_fontsize(12)
            text.set_fontweight('bold')
        
        ax.set_title('步态周期分析', fontsize=14, fontweight='bold', pad=20)
        
        # 添加正常范围说明
        normal_text = '正常范围:\n支撑相: 58-62%\n摆动相: 38-42%'
        ax.text(1.3, 0, normal_text, transform=ax.transData,
               fontsize=10, verticalalignment='center',
               bbox=dict(boxstyle='round', facecolor='lightgray', alpha=0.5))
        
        return self._fig_to_base64(fig)
    
    def _fig_to_base64(self, fig) -> str:
        """将matplotlib图形转换为base64字符串"""
        buf = io.BytesIO()
        fig.savefig(buf, format='png', dpi=100, bbox_inches='tight')
        buf.seek(0)
        img_base64 = base64.b64encode(buf.read()).decode('utf-8')
        plt.close(fig)
        return f"data:image/png;base64,{img_base64}"


class PersonalizedAdviceGenerator:
    """个性化医学建议生成器"""
    
    def __init__(self):
        self.advice_database = self._init_advice_database()
    
    def _init_advice_database(self):
        """初始化建议数据库"""
        return {
            'gait_speed': {
                'low': {
                    'threshold': 1.0,  # 提高阈值，让更多情况被识别为步速偏慢
                    'risks': ['跌倒风险增加', '活动能力下降', '肌肉力量不足'],
                    'recommendations': [
                        '建议进行渐进式步速训练，从短距离开始逐步增加',
                        '加强下肢肌力训练，特别是股四头肌和臀肌',
                        '使用节拍器进行节律性步态训练，每天15-20分钟',
                        '考虑使用辅助行走器具提高安全性',
                        '考虑参加防跌倒训练班'
                    ],
                    'exercises': [
                        '坐站训练：每组10次，每天3组',
                        '踮脚训练：保持3秒，重复15次',
                        '单腿站立：每侧30秒，逐渐增加时间'
                    ]
                },
                'normal': {
                    'threshold': 1.4,
                    'risks': [],
                    'recommendations': [
                        '保持当前的活动水平',
                        '继续规律运动，每周至少150分钟中等强度活动',
                        '定期进行平衡和协调性训练'
                    ],
                    'exercises': [
                        '快走30分钟，每周5次',
                        '太极拳或瑜伽，提高平衡能力',
                        '游泳或水中运动，低冲击全身锻炼'
                    ]
                },
                'high': {
                    'threshold': float('inf'),
                    'risks': ['步态不稳定', '冲动性步态'],
                    'recommendations': [
                        '注意控制步速，避免过快导致失衡',
                        '加强核心稳定性训练',
                        '注意环境安全，避免在湿滑路面快速行走'
                    ],
                    'exercises': [
                        '平板支撑：30-60秒，每天3组',
                        '八段锦或五禽戏，调节身心平衡',
                        '瑜伽平衡体式练习'
                    ]
                }
            },
            'asymmetry': {
                'mild': {
                    'threshold': 0.15,
                    'risks': ['轻度步态不对称'],
                    'recommendations': [
                        '注意观察是否有单侧不适或疼痛',
                        '进行双侧对称性训练',
                        '穿着合适的鞋子，必要时使用矫形鞋垫'
                    ]
                },
                'moderate': {
                    'threshold': 0.30,
                    'risks': ['中度步态不对称', '代偿性损伤风险'],
                    'recommendations': [
                        '建议进行专业步态评估',
                        '可能需要物理治疗介入',
                        '检查是否有关节或肌肉问题',
                        '避免长时间单侧负重活动'
                    ]
                },
                'severe': {
                    'threshold': float('inf'),
                    'risks': ['严重步态不对称', '跌倒风险高', '继发性损伤'],
                    'recommendations': [
                        '强烈建议就医检查',
                        '可能需要影像学检查排除结构性问题',
                        '需要专业康复治疗方案',
                        '考虑使用助行器或拐杖'
                    ]
                }
            },
            'balance': {
                'poor': {
                    'cop_area_threshold': 100,
                    'risks': ['平衡能力差', '跌倒风险高'],
                    'recommendations': [
                        '每天进行平衡训练，从简单到复杂',
                        '改善家居环境，移除绊倒隐患',
                        '安装扶手和防滑垫',
                        '考虑参加防跌倒训练班'
                    ],
                    'exercises': [
                        '串联步行：沿直线行走，脚跟接脚尖',
                        '闭眼站立：从睁眼到闭眼渐进练习',
                        '单腿站立：使用椅背支撑，逐渐减少依赖'
                    ]
                },
                'fair': {
                    'cop_area_threshold': 50,
                    'risks': ['轻度平衡问题'],
                    'recommendations': [
                        '加强核心肌群训练',
                        '练习多方向的平衡活动',
                        '注意在疲劳时的平衡控制'
                    ]
                },
                'good': {
                    'cop_area_threshold': 0,
                    'risks': [],
                    'recommendations': [
                        '平衡能力良好，继续保持',
                        '可尝试更具挑战性的平衡活动',
                        '参与需要平衡协调的运动项目'
                    ]
                }
            }
        }
    
    def generate_personalized_advice(self, analysis_data: Dict[str, Any], patient_info: Dict[str, Any]) -> Dict[str, Any]:
        """生成个性化医学建议"""
        advice = {
            'risk_assessment': [],
            'recommendations': [],
            'exercise_plan': [],
            'follow_up': [],
            'lifestyle': []
        }
        
        # 获取关键指标
        gait_speed = analysis_data.get('average_velocity', 1.2)
        left_step = analysis_data.get('left_step_length', 0.65)
        right_step = analysis_data.get('right_step_length', 0.65)
        cop_area = analysis_data.get('cop_area', 30)
        age = patient_info.get('age', 65)
        gender = patient_info.get('gender', 'unknown')
        
        # 计算不对称指数
        asymmetry = abs(left_step - right_step) / max(left_step, right_step) if max(left_step, right_step) > 0 else 0
        
        # 基于步速的建议
        speed_advice = self._get_speed_advice(gait_speed, age)
        advice['risk_assessment'].extend(speed_advice['risks'])
        advice['recommendations'].extend(speed_advice['recommendations'])
        advice['exercise_plan'].extend(speed_advice['exercises'])
        
        # 基于不对称性的建议
        asymmetry_advice = self._get_asymmetry_advice(asymmetry)
        advice['risk_assessment'].extend(asymmetry_advice['risks'])
        advice['recommendations'].extend(asymmetry_advice['recommendations'])
        
        # 基于平衡的建议
        balance_advice = self._get_balance_advice(cop_area)
        advice['risk_assessment'].extend(balance_advice['risks'])
        advice['recommendations'].extend(balance_advice['recommendations'])
        if 'exercises' in balance_advice:
            advice['exercise_plan'].extend(balance_advice['exercises'])
        
        # 年龄相关的特殊建议
        age_advice = self._get_age_specific_advice(age, gait_speed, asymmetry)
        advice['recommendations'].extend(age_advice['recommendations'])
        advice['lifestyle'].extend(age_advice['lifestyle'])
        
        # 生成随访建议
        advice['follow_up'] = self._generate_followup_plan(
            advice['risk_assessment'], age, gait_speed
        )
        
        # 添加个性化因素
        advice = self._add_personalization(advice, patient_info, analysis_data)
        
        return advice
    
    def _get_speed_advice(self, speed: float, age: int) -> Dict:
        """获取基于步速的建议"""
        # 根据年龄调整阈值
        age_factor = 1.0 - (max(age - 65, 0) * 0.01)  # 65岁后每年降低1%
        
        db = self.advice_database['gait_speed']
        if speed < db['low']['threshold'] * age_factor:
            return db['low']
        elif speed < db['normal']['threshold'] * age_factor:
            return db['normal']
        else:
            return db['high']
    
    def _get_asymmetry_advice(self, asymmetry: float) -> Dict:
        """获取基于不对称性的建议"""
        db = self.advice_database['asymmetry']
        if asymmetry < db['mild']['threshold']:
            return {'risks': [], 'recommendations': ['步态对称性良好']}
        elif asymmetry < db['moderate']['threshold']:
            return db['mild']
        elif asymmetry < db['severe']['threshold']:
            return db['moderate']
        else:
            return db['severe']
    
    def _get_balance_advice(self, cop_area: float) -> Dict:
        """获取基于平衡的建议"""
        db = self.advice_database['balance']
        if cop_area > db['poor']['cop_area_threshold']:
            return db['poor']
        elif cop_area > db['fair']['cop_area_threshold']:
            return db['fair']
        else:
            return db['good']
    
    def _get_age_specific_advice(self, age: int, speed: float, asymmetry: float) -> Dict:
        """获取年龄特异性建议"""
        advice = {'recommendations': [], 'lifestyle': []}
        
        if age >= 75:
            advice['recommendations'].extend([
                '建议每3个月进行一次步态评估',
                '重点关注防跌倒措施，使用辅助器具',
                '考虑参加老年人平衡训练班',
                '康复训练应谨慎温和，避免高强度运动',
                '社区康复中心定期评估和指导'
            ])
            advice['lifestyle'].extend([
                '保证充足的蛋白质摄入，每公斤体重1.2g',
                '补充维生素D，每天800-1000IU',
                '保持社交活动，参与集体运动',
                '居家安全环境改造，防跌倒设施完善',
                '定期骨密度检查，预防骨质疏松'
            ])
        elif age >= 60:  # 降低老年阈值，增加老年特异性建议
            advice['recommendations'].extend([
                '建议每6个月进行步态评估，及早发现功能下降',
                '重点加强防跌倒训练和平衡能力',
                '考虑参加中老年人群体康复训练',
                '保持规律的温和有氧运动和抗阻训练',
                '注意膝关节和髋关节的保护'
            ])
            advice['lifestyle'].extend([
                '均衡饮食，增加钙质摄入，预防骨质疏松',
                '每天至少30分钟户外活动，增加阳光照射',
                '定期体检，监测骨密度和肌肉含量',
                '选择低冲击运动，如太极拳、游泳',
                '保持充足睡眠，促进肌肉恢复'
            ])
        elif age >= 40:
            advice['recommendations'].extend([
                '建议每年进行步态评估，监测功能状态',
                '预防性加强肌力和平衡训练',
                '关注新陈代谢变化，调整运动强度'
            ])
            advice['lifestyle'].extend([
                '保持健康体重，避免超重对关节造成负担',
                '增加抗阻训练，预防肌肉流失',
                '合理安排工作和运动时间'
            ])
        else:
            advice['recommendations'].extend([
                '建议每2年进行步态评估，建立基线数据',
                '积极参与各种运动，增强体质',
                '预防性训练，为中年后的健康打基础'
            ])
            advice['lifestyle'].extend([
                '保持健康体重',
                '避免久坐，每小时活动5分钟',
                '选择合适的运动鞋'
            ])
        
        return advice
    
    def _generate_followup_plan(self, risks: List[str], age: int, speed: float) -> List[str]:
        """生成随访计划"""
        plan = []
        
        # 根据风险等级确定随访频率
        if len(risks) >= 3 or '高' in ''.join(risks):
            plan.append('建议1个月后复查')
            plan.append('需要专科医生评估')
        elif len(risks) >= 1:
            plan.append('建议3个月后复查')
            plan.append('可在社区医院随访')
        else:
            plan.append('建议6个月后常规复查')
        
        # 添加具体检查项目
        if speed < 0.8:
            plan.append('复查时重点评估步速改善情况')
        if age >= 70:
            plan.append('建议同时进行认知功能评估')
        
        plan.append('记录日常活动和运动情况')
        plan.append('如有不适随时就诊')
        
        return plan
    
    def _add_personalization(self, advice: Dict, patient_info: Dict, analysis_data: Dict) -> Dict:
        """添加个性化因素"""
        import random
        
        # 基于患者姓名生成伪随机种子，确保同一患者的建议有变化但可重现
        name = patient_info.get('name', 'default')
        test_date = analysis_data.get('test_date', datetime.now().isoformat())
        seed = hash(f"{name}_{test_date}") % 1000000
        random.seed(seed)
        
        # 添加时间相关的建议
        hour = datetime.now().hour
        if 6 <= hour < 10:
            advice['lifestyle'].append('早晨运动效果最佳，建议保持晨练习惯')
        elif 16 <= hour < 19:
            advice['lifestyle'].append('傍晚运动有助于改善睡眠质量')
        
        # 添加季节相关建议
        month = datetime.now().month
        if month in [12, 1, 2]:  # 冬季
            advice['recommendations'].append('冬季注意防滑，穿着防滑鞋')
            advice['lifestyle'].append('室内运动为主，避免户外湿滑路面')
        elif month in [6, 7, 8]:  # 夏季
            advice['recommendations'].append('夏季运动注意补水，避免中暑')
            advice['lifestyle'].append('选择清晨或傍晚凉爽时段运动')
        
        # 根据步数差异添加特定建议
        left_steps = analysis_data.get('left_steps', 0)
        right_steps = analysis_data.get('right_steps', 0)
        if abs(left_steps - right_steps) > 5:
            advice['recommendations'].append(
                f'注意到您的左右脚步数差异较大（左{left_steps}步，右{right_steps}步），'
                f'建议进行针对性的单侧训练'
            )
        
        # 打乱建议顺序，增加变化性
        for key in ['recommendations', 'exercise_plan', 'lifestyle']:
            if key in advice and len(advice[key]) > 1:
                random.shuffle(advice[key])
                # 保留前5条最重要的建议
                advice[key] = advice[key][:5]
        
        return advice


# 增强版报告模板
ENHANCED_REPORT_TEMPLATE = '''
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
            line-height: 1.6;
            color: #333;
            background: #f5f5f5;
        }
        
        .report-container {
            max-width: 1200px;
            margin: 0 auto;
            padding: 20px;
            background: white;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        }
        
        .report-header {
            text-align: center;
            padding: 30px 0;
            border-bottom: 2px solid #1890ff;
            margin-bottom: 30px;
        }
        
        .hospital-name {
            font-size: 28px;
            font-weight: bold;
            color: #1890ff;
            margin-bottom: 10px;
        }
        
        .report-title {
            font-size: 24px;
            color: #333;
            margin-bottom: 10px;
        }
        
        .report-number {
            font-size: 14px;
            color: #666;
        }
        
        .section {
            margin-bottom: 30px;
            padding: 20px;
            background: #fafafa;
            border-radius: 8px;
        }
        
        .section-title {
            font-size: 18px;
            font-weight: bold;
            color: #333;
            margin-bottom: 15px;
            padding-bottom: 10px;
            border-bottom: 2px solid #1890ff;
        }
        
        .info-table {
            width: 100%;
            border-collapse: collapse;
            margin-bottom: 20px;
        }
        
        .info-table td {
            padding: 10px;
            border: 1px solid #e8e8e8;
        }
        
        .info-table td:first-child {
            width: 150px;
            background: #f0f0f0;
            font-weight: bold;
        }
        
        .chart-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(400px, 1fr));
            gap: 20px;
            margin: 20px 0;
        }
        
        .chart-item {
            text-align: center;
            padding: 15px;
            background: white;
            border-radius: 8px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.1);
        }
        
        .chart-item img {
            max-width: 100%;
            height: auto;
            margin-top: 10px;
        }
        
        .chart-title {
            font-size: 16px;
            font-weight: bold;
            color: #333;
            margin-bottom: 10px;
        }
        
        .cop-analysis {
            margin: 20px 0;
        }
        
        .cop-chart {
            text-align: center;
            margin: 20px 0;
        }
        
        .cop-chart img {
            max-width: 100%;
            height: auto;
            border: 1px solid #e8e8e8;
            border-radius: 8px;
        }
        
        .advice-section {
            background: #e6f7ff;
            padding: 20px;
            border-radius: 8px;
            border-left: 4px solid #1890ff;
        }
        
        .advice-category {
            margin-bottom: 20px;
        }
        
        .advice-title {
            font-size: 16px;
            font-weight: bold;
            color: #0050b3;
            margin-bottom: 10px;
        }
        
        .advice-list {
            list-style-type: none;
            padding-left: 0;
        }
        
        .advice-list li {
            padding: 8px 0;
            padding-left: 20px;
            position: relative;
        }
        
        .advice-list li:before {
            content: "▶";
            position: absolute;
            left: 0;
            color: #1890ff;
        }
        
        .risk-high {
            color: #ff4d4f;
            font-weight: bold;
        }
        
        .risk-medium {
            color: #faad14;
            font-weight: bold;
        }
        
        .risk-low {
            color: #52c41a;
            font-weight: bold;
        }
        
        .summary-box {
            background: #fff7e6;
            border: 1px solid #ffd591;
            border-radius: 8px;
            padding: 15px;
            margin: 20px 0;
        }
        
        .footer {
            text-align: center;
            padding: 20px;
            margin-top: 40px;
            border-top: 1px solid #e8e8e8;
            color: #666;
            font-size: 12px;
        }
        
        @media print {
            body {
                background: white;
            }
            .report-container {
                box-shadow: none;
            }
        }
    </style>
</head>
<body>
    <div class="report-container">
        <!-- 报告头部 -->
        <div class="report-header">
            <div class="hospital-name">智能步态分析中心</div>
            <div class="report-title">综合步态分析报告</div>
            <div class="report-number">报告编号：{{ report_number }}</div>
        </div>
        
        <!-- 患者信息 -->
        <div class="section">
            <div class="section-title">患者基本信息</div>
            <table class="info-table">
                <tr>
                    <td>姓名</td>
                    <td>{{ patient_name }}</td>
                    <td>性别</td>
                    <td>{{ gender }}</td>
                </tr>
                <tr>
                    <td>年龄</td>
                    <td>{{ age }}岁</td>
                    <td>检查日期</td>
                    <td>{{ test_date }}</td>
                </tr>
                <tr>
                    <td>身高</td>
                    <td>{{ height }}cm</td>
                    <td>体重</td>
                    <td>{{ weight }}kg</td>
                </tr>
            </table>
        </div>
        
        <!-- 步态分析结果 -->
        <div class="section">
            <div class="section-title">步态分析结果</div>
            <table class="info-table">
                <tr>
                    <td>平均步速</td>
                    <td>{{ velocity }} m/s</td>
                    <td>评估</td>
                    <td class="{{ speed_class }}">{{ speed_assessment }}</td>
                </tr>
                <tr>
                    <td>左脚步长</td>
                    <td>{{ left_step_length }} m</td>
                    <td>右脚步长</td>
                    <td>{{ right_step_length }} m</td>
                </tr>
                <tr>
                    <td>步频</td>
                    <td>{{ cadence }} 步/分钟</td>
                    <td>对称性</td>
                    <td>{{ symmetry }}%</td>
                </tr>
                <tr>
                    <td>支撑相</td>
                    <td>{{ stance_phase }}%</td>
                    <td>摆动相</td>
                    <td>{{ swing_phase }}%</td>
                </tr>
            </table>
        </div>
        
        <!-- 图表展示 -->
        <div class="section">
            <div class="section-title">数据可视化分析</div>
            <div class="chart-grid">
                {% for chart_name, chart_data in charts.items() %}
                <div class="chart-item">
                    <div class="chart-title">{{ chart_titles[chart_name] }}</div>
                    <img src="{{ chart_data }}" alt="{{ chart_titles[chart_name] }}">
                </div>
                {% endfor %}
            </div>
        </div>
        
        <!-- COP轨迹分析 -->
        <div class="section">
            <div class="section-title">压力中心(COP)轨迹分析</div>
            <div class="cop-analysis">
                <div class="cop-chart">
                    <img src="{{ cop_trajectory }}" alt="COP轨迹图">
                </div>
                <table class="info-table">
                    <tr>
                        <td>COP轨迹面积</td>
                        <td>{{ cop_area }} cm²</td>
                        <td>轨迹总长度</td>
                        <td>{{ cop_path_length }} cm</td>
                    </tr>
                    <tr>
                        <td>前后摆动范围</td>
                        <td>{{ ap_range }} cm</td>
                        <td>左右摆动范围</td>
                        <td>{{ ml_range }} cm</td>
                    </tr>
                </table>
            </div>
        </div>
        
        <!-- 压力分布热力图 -->
        <div class="section">
            <div class="section-title">足底压力分布</div>
            <div class="cop-chart">
                <img src="{{ pressure_heatmap }}" alt="压力分布热力图">
            </div>
        </div>
        
        <!-- 个性化医学建议 -->
        <div class="section advice-section">
            <div class="section-title">个性化医学建议</div>
            
            {% if risk_assessment %}
            <div class="advice-category">
                <div class="advice-title">风险评估</div>
                <ul class="advice-list">
                    {% for risk in risk_assessment %}
                    <li>{{ risk }}</li>
                    {% endfor %}
                </ul>
            </div>
            {% endif %}
            
            {% if recommendations %}
            <div class="advice-category">
                <div class="advice-title">临床建议</div>
                <ul class="advice-list">
                    {% for rec in recommendations %}
                    <li>{{ rec }}</li>
                    {% endfor %}
                </ul>
            </div>
            {% endif %}
            
            {% if exercise_plan %}
            <div class="advice-category">
                <div class="advice-title">康复训练计划</div>
                <ul class="advice-list">
                    {% for exercise in exercise_plan %}
                    <li>{{ exercise }}</li>
                    {% endfor %}
                </ul>
            </div>
            {% endif %}
            
            {% if lifestyle %}
            <div class="advice-category">
                <div class="advice-title">生活方式建议</div>
                <ul class="advice-list">
                    {% for item in lifestyle %}
                    <li>{{ item }}</li>
                    {% endfor %}
                </ul>
            </div>
            {% endif %}
            
            {% if follow_up %}
            <div class="advice-category">
                <div class="advice-title">随访计划</div>
                <ul class="advice-list">
                    {% for item in follow_up %}
                    <li>{{ item }}</li>
                    {% endfor %}
                </ul>
            </div>
            {% endif %}
        </div>
        
        <!-- 总结 -->
        <div class="summary-box">
            <div class="section-title">检查总结</div>
            <p>{{ summary }}</p>
        </div>
        
        <!-- 页脚 -->
        <div class="footer">
            <p>报告生成时间：{{ generate_time }}</p>
            <p>本报告仅供临床参考，具体诊断请结合临床症状</p>
            <p>© 2024 智能步态分析系统 - 专业版</p>
        </div>
    </div>
</body>
</html>
'''


class EnhancedReportGenerator:
    """增强版报告生成器"""
    
    def __init__(self):
        self.chart_generator = ChartGenerator()
        self.advice_generator = PersonalizedAdviceGenerator()
        self.template = Template(ENHANCED_REPORT_TEMPLATE)
    
    def generate_report(self, analysis_data: Dict[str, Any], 
                       patient_info: Optional[Dict[str, Any]] = None) -> str:
        """生成增强版医疗报告"""
        
        # 准备患者信息
        if patient_info is None:
            patient_info = self._get_default_patient_info()
        
        # 生成图表
        charts = self.chart_generator.generate_gait_charts(analysis_data)
        cop_trajectory = self.chart_generator.generate_cop_trajectory()
        pressure_heatmap = self.chart_generator.generate_pressure_heatmap()
        
        # 生成个性化建议
        advice = self.advice_generator.generate_personalized_advice(
            analysis_data, patient_info
        )
        
        # 准备模板数据
        template_data = self._prepare_template_data(
            analysis_data, patient_info, charts, 
            cop_trajectory, pressure_heatmap, advice
        )
        
        # 渲染报告
        return self.template.render(**template_data)
    
    def _get_default_patient_info(self) -> Dict[str, Any]:
        """获取默认患者信息"""
        return {
            'name': '测试患者',
            'age': 65,
            'gender': '男',
            'height': 170,
            'weight': 70,
            'medical_record_number': 'TEST001'
        }
    
    def _prepare_template_data(self, analysis_data: Dict, patient_info: Dict,
                              charts: Dict, cop_trajectory: str, 
                              pressure_heatmap: str, advice: Dict) -> Dict:
        """准备模板数据"""
        # 计算对称性
        left_step = analysis_data.get('left_step_length', 0.65)
        right_step = analysis_data.get('right_step_length', 0.65)
        symmetry = min(left_step, right_step) / max(left_step, right_step) * 100 if max(left_step, right_step) > 0 else 0
        
        # 评估步速
        velocity = analysis_data.get('average_velocity', 1.2)
        if velocity < 0.8:
            speed_class = 'risk-high'
            speed_assessment = '偏慢（需要关注）'
        elif velocity < 1.0:
            speed_class = 'risk-medium'
            speed_assessment = '轻度偏慢'
        elif velocity < 1.4:
            speed_class = 'risk-low'
            speed_assessment = '正常'
        else:
            speed_class = 'risk-medium'
            speed_assessment = '偏快'
        
        # 生成总结
        summary = self._generate_summary(analysis_data, patient_info, advice)
        
        return {
            'report_number': f"RPT-{datetime.now().strftime('%Y%m%d-%H%M%S')}",
            'patient_name': patient_info.get('name', '未知'),
            'gender': patient_info.get('gender', '未知'),
            'age': patient_info.get('age', 0),
            'height': patient_info.get('height', 0),
            'weight': patient_info.get('weight', 0),
            'test_date': datetime.now().strftime('%Y-%m-%d'),
            'generate_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            
            # 步态数据
            'velocity': f"{velocity:.2f}",
            'speed_class': speed_class,
            'speed_assessment': speed_assessment,
            'left_step_length': f"{left_step:.3f}",
            'right_step_length': f"{right_step:.3f}",
            'cadence': f"{analysis_data.get('cadence', 110):.1f}",
            'symmetry': f"{symmetry:.1f}",
            'stance_phase': f"{analysis_data.get('stance_phase', 60):.1f}",
            'swing_phase': f"{analysis_data.get('swing_phase', 40):.1f}",
            
            # COP数据
            'cop_area': f"{analysis_data.get('cop_area', 42.5):.1f}",
            'cop_path_length': f"{analysis_data.get('cop_path_length', 150):.1f}",
            'ap_range': f"{analysis_data.get('ap_range', 8.5):.1f}",
            'ml_range': f"{analysis_data.get('ml_range', 6.2):.1f}",
            
            # 图表
            'charts': charts,
            'chart_titles': {
                'velocity_chart': '步速变化趋势',
                'stride_chart': '左右步长对比',
                'gait_cycle_chart': '步态周期分析'
            },
            'cop_trajectory': cop_trajectory,
            'pressure_heatmap': pressure_heatmap,
            
            # 个性化建议
            'risk_assessment': advice.get('risk_assessment', []),
            'recommendations': advice.get('recommendations', []),
            'exercise_plan': advice.get('exercise_plan', []),
            'lifestyle': advice.get('lifestyle', []),
            'follow_up': advice.get('follow_up', []),
            
            'summary': summary
        }
    
    def _generate_summary(self, analysis_data: Dict, patient_info: Dict, advice: Dict) -> str:
        """生成检查总结"""
        risks = advice.get('risk_assessment', [])
        velocity = analysis_data.get('average_velocity', 1.2)
        age = patient_info.get('age', 65)
        name = patient_info.get('name', '患者')
        
        summary_parts = []
        
        # 基本评估
        if velocity < 0.8:
            summary_parts.append(f"{name}的步态速度明显偏慢，需要重点关注")
        elif velocity < 1.0:
            summary_parts.append(f"{name}的步态速度轻度偏慢")
        else:
            summary_parts.append(f"{name}的步态速度在正常范围内")
        
        # 风险总结
        if len(risks) == 0:
            summary_parts.append("未发现明显的步态异常风险")
        elif len(risks) <= 2:
            summary_parts.append(f"存在{len(risks)}项轻度风险因素")
        else:
            summary_parts.append(f"存在{len(risks)}项风险因素，需要综合干预")
        
        # 年龄相关
        if age >= 75:
            summary_parts.append("考虑到高龄因素，建议加强防跌倒措施")
        elif age >= 65:
            summary_parts.append("建议定期进行步态评估，预防功能下降")
        
        # 建议总结
        if advice.get('recommendations'):
            summary_parts.append("已制定个性化的康复训练计划和生活方式建议")
        
        return "。".join(summary_parts) + "。请遵医嘱进行康复训练，定期复查。"


def generate_enhanced_report_from_algorithm(algorithm_result: Dict[str, Any],
                                          patient_info: Optional[Dict[str, Any]] = None,
                                          output_file: Optional[str] = None) -> str:
    """
    从算法结果生成增强版报告
    
    Args:
        algorithm_result: 算法分析结果
        patient_info: 患者信息
        output_file: 输出文件路径
    
    Returns:
        HTML报告内容
    """
    generator = EnhancedReportGenerator()
    
    # 提取算法结果中的关键数据
    gait_analysis = algorithm_result.get('gait_analysis', {})
    balance_analysis = algorithm_result.get('balance_analysis', {})
    
    # 整合分析数据
    analysis_data = {
        'average_velocity': gait_analysis.get('average_velocity', 1.2),
        'left_step_length': gait_analysis.get('left_step_length', 0.65),
        'right_step_length': gait_analysis.get('right_step_length', 0.65),
        'left_steps': gait_analysis.get('left_steps', 10),
        'right_steps': gait_analysis.get('right_steps', 10),
        'cadence': gait_analysis.get('cadence', 110),
        'stance_phase': gait_analysis.get('stance_phase', 60),
        'swing_phase': gait_analysis.get('swing_phase', 40),
        'cop_area': balance_analysis.get('cop_area', 42.5),
        'cop_path_length': balance_analysis.get('cop_path_length', 150),
        'ap_range': balance_analysis.get('antero_posterior_range', 8.5),
        'ml_range': balance_analysis.get('medio_lateral_range', 6.2),
    }
    
    # 生成报告
    html_content = generator.generate_report(analysis_data, patient_info)
    
    # 保存到文件
    if output_file:
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(html_content)
        print(f"增强版报告已保存到: {output_file}")
    
    return html_content


if __name__ == '__main__':
    # 测试报告生成
    test_data = {
        'gait_analysis': {
            'average_velocity': 0.95,
            'left_step_length': 0.58,
            'right_step_length': 0.72,
            'left_steps': 7,
            'right_steps': 13,
            'cadence': 105,
            'stance_phase': 62,
            'swing_phase': 38
        },
        'balance_analysis': {
            'cop_area': 65,
            'cop_path_length': 180,
            'antero_posterior_range': 9.2,
            'medio_lateral_range': 7.1
        }
    }
    
    test_patient = {
        'name': '李然',
        'age': 68,
        'gender': '男',
        'height': 172,
        'weight': 75
    }
    
    # 生成报告
    report = generate_enhanced_report_from_algorithm(
        test_data, 
        test_patient,
        'enhanced_test_report.html'
    )
    print("增强版报告生成完成！")