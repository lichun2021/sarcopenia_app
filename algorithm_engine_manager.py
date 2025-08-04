"""
算法引擎管理器 - 直接调用Python算法模块
替代原有的HTTP服务调用方式
"""
import os
import sys
import json
import time
import traceback
import logging
from pathlib import Path
from typing import Dict, Any, Optional, Union, List
from datetime import datetime
import threading
from queue import Queue, Empty
import configparser
import tempfile
import base64

# 设置日志
logger = logging.getLogger(__name__)

class MockPressureAnalysisCore:
    """模拟压力分析核心类"""
    
    def comprehensive_analysis(self, csv_path):
        """模拟综合分析"""
        return {
            'overall_score': 85.0,
            'balance_score': 85.0,
            'balance_metrics': {
                'scores': {
                    'overall': 85.0,
                    'stability': 80.0,
                    'symmetry': 90.0,
                    'mobility': 85.0
                }
            },
            'cop_metrics': {},
            'gait_events': []
        }
    
    def parse_csv_data(self, csv_content):
        """模拟CSV数据解析"""
        return {"timestamp": [], "pressure": []}
    
    def calculate_cop_metrics(self, pressure_data_list):
        """模拟COP指标计算"""
        return {"center_of_pressure": [0, 0]}
    
    def analyze_balance(self, pressure_data_list):
        """模拟平衡分析"""
        return {"balance_score": 85.0}

class MockReportGenerator:
    """模拟报告生成器"""
    
    def generate_report(self, report_data, options):
        """模拟生成HTML报告"""
        patient_name = report_data.get('patient_info', {}).get('name', '测试患者')
        score = report_data.get('analysis_result', {}).get('overall_score', 85.0)
        
        return f"""
        <html>
        <head><title>肌少症分析报告</title></head>
        <body>
            <h1>肌少症分析报告</h1>
            <h2>患者信息</h2>
            <p>姓名: {patient_name}</p>
            <h2>分析结果</h2>
            <p>综合评分: {score:.1f}/100</p>
            <p>风险等级: {'低风险' if score >= 70 else '高风险'}</p>
            <h2>建议</h2>
            <ul>
                <li>保持健康的生活方式</li>
                <li>定期进行体检</li>
                <li>适量运动</li>
            </ul>
        </body>
        </html>
        """

def load_config():
    """加载配置文件"""
    config = configparser.ConfigParser()
    
    # 默认配置 - 优先使用gemsage目录
    defaults = {
        'algorithms_dir': 'gemsage',
        'enable_async': 'false',
        'timeout': '300',
        'cache_results': 'false',
        'max_workers': '1'
    }
    
    # 尝试读取配置文件
    config_file = 'config.ini'
    if os.path.exists(config_file):
        config.read(config_file, encoding='utf-8')
    
    # 获取配置值
    cfg = {}
    for key, default_value in defaults.items():
        if key in ['enable_async', 'cache_results']:
            cfg[key] = config.getboolean('ALGORITHM', key, fallback=default_value.lower() == 'true')
        elif key in ['timeout', 'max_workers']:
            cfg[key] = config.getint('ALGORITHM', key, fallback=int(default_value))
        else:
            cfg[key] = config.get('ALGORITHM', key, fallback=default_value)
    
    return cfg

# 加载配置
app_config = load_config()

class AlgorithmEngineManager:
    """算法引擎管理器"""
    
    def __init__(self, algorithms_dir: str = None):
        """
        初始化算法引擎管理器
        
        Args:
            algorithms_dir: 算法模块目录路径
        """
        self.algorithms_dir = Path(algorithms_dir or app_config['algorithms_dir'])
        self.is_initialized = False
        self.analyzer = None
        self.ai_engine = None  # gemsage AI评估引擎
        self.report_generator = None
        self.async_client = None
        self.cache = {} if app_config['cache_results'] else None
        self.timeout = app_config['timeout']
        
        # 初始化算法模块
        self._initialize_modules()
    
    def _initialize_modules(self):
        """初始化算法模块"""
        try:
            # 添加算法目录到Python路径
            algorithms_path = str(self.algorithms_dir.absolute())
            if algorithms_path not in sys.path:
                sys.path.insert(0, algorithms_path)
            
            # 优先尝试导入gemsage，即使算法目录不存在
            
            # 优先尝试导入gemsage模块
            logger.info(f"尝试导入gemsage分析引擎")
            try:
                # 添加gemsage目录到路径
                gemsage_path = os.path.join(os.path.dirname(__file__), 'gemsage')
                if gemsage_path not in sys.path:
                    sys.path.insert(0, gemsage_path)
                
                from gemsage.core_calculator import PressureAnalysisCore
                self.analyzer = PressureAnalysisCore()
                logger.info("成功导入gemsage.core_calculator.PressureAnalysisCore")
                
                # 导入报告生成器
                try:
                    from gemsage.ai_assessment_engine import AIAssessmentEngine
                    self.ai_engine = AIAssessmentEngine()
                    logger.info("成功导入gemsage.ai_assessment_engine.AIAssessmentEngine")
                except ImportError as e:
                    logger.warning(f"无法导入AI评估引擎: {e}")
                    self.ai_engine = None
                
                # 尝试导入报告生成器
                try:
                    from full_medical_report_generator import FullMedicalReportGenerator
                    self.report_generator = FullMedicalReportGenerator()
                except ImportError:
                    self.report_generator = MockReportGenerator()
                    
            except ImportError as e:
                logger.warning(f"无法导入gemsage模块: {e}")
                # 回退到传统算法目录
                logger.info(f"从 {algorithms_path} 导入算法模块")
                try:
                    from core_calculator import PressureAnalysisCore
                    self.analyzer = PressureAnalysisCore()
                    
                    # 导入报告生成器
                    from full_medical_report_generator import FullMedicalReportGenerator
                    self.report_generator = FullMedicalReportGenerator()
                except ImportError as e2:
                    logger.warning(f"无法导入传统算法模块: {e2}")
                    # 使用模拟模块
                    self.analyzer = MockPressureAnalysisCore()
                    self.report_generator = MockReportGenerator()
            
            # 如果analyzer仍为None，使用mock
            if self.analyzer is None:
                logger.warning("所有算法引擎导入失败，使用模拟引擎")
                self.analyzer = MockPressureAnalysisCore()
                self.report_generator = MockReportGenerator()
            
            # 如果启用异步，导入异步客户端
            if app_config['enable_async']:
                try:
                    from async_analyzer import AlgorithmClient
                    self.async_client = AlgorithmClient()
                    logger.info("异步分析客户端已初始化")
                except ImportError:
                    logger.warning("无法导入异步分析模块，将使用同步模式")
                except Exception as e:
                    logger.warning(f"异步客户端初始化失败: {e}")
            
            self.is_initialized = True
            logger.info("算法引擎初始化成功")
            
        except Exception as e:
            logger.error(f"算法引擎初始化失败: {e}")
            logger.error(traceback.format_exc())
            raise
    
    def analyze_data(
        self,
        csv_data: str,
        patient_info: Dict[str, Any],
        test_type: str = "COMPREHENSIVE",
        generate_report: bool = True
    ) -> Optional[Dict[str, Any]]:
        """
        分析压力数据
        
        Args:
            csv_data: CSV格式的压力数据
            patient_info: 患者信息字典
            test_type: 测试类型
            generate_report: 是否生成报告
            
        Returns:
            分析结果字典或None
        """
        if not self.is_initialized:
            logger.error("算法引擎未初始化")
            return None
        
        try:
            start_time = time.time()
            logger.info(f"开始分析数据 - 患者: {patient_info.get('name', '未知')}")
            
            # 检查缓存
            if self.cache is not None:
                cache_key = self._generate_cache_key(csv_data, patient_info, test_type)
                if cache_key in self.cache:
                    logger.info("使用缓存的分析结果")
                    return self.cache[cache_key]
            
            # 选择分析方式
            if app_config['enable_async'] and self.async_client:
                result = self._analyze_async(csv_data, patient_info, test_type)
            else:
                result = self._analyze_sync(csv_data, patient_info, test_type)
            
            if result and generate_report:
                # 暂时跳过PDF生成，直接保存AI评估结果
                if 'ai_assessment' in result:
                    # 保存AI评估结果到文件
                    import json
                    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                    patient_name = patient_info.get('name', 'Unknown').replace(' ', '_')
                    ai_result_path = f"ai_assessment_{patient_name}_{timestamp}.json"
                    
                    with open(ai_result_path, 'w', encoding='utf-8') as f:
                        json.dump(result['ai_assessment'], f, ensure_ascii=False, indent=2, default=str)
                    
                    logger.info(f"AI评估结果已保存到: {ai_result_path}")
                
                # 生成报告HTML (跳过PDF转换)
                try:
                    report_html = self._generate_report(result, patient_info)
                    if report_html:
                        result['report_html'] = report_html
                except Exception as pdf_error:
                    logger.warning(f"跳过PDF生成: {pdf_error}")
                    pass
            
            # 添加元数据
            if result:
                result['metadata'] = {
                    'analysis_time': time.time() - start_time,
                    'engine_type': 'direct_python',
                    'async_mode': app_config['enable_async'] and self.async_client is not None
                }
                
                # 缓存结果
                if self.cache is not None:
                    self.cache[cache_key] = result
            
            logger.info(f"分析完成，耗时: {time.time() - start_time:.2f}秒")
            return result
            
        except Exception as e:
            logger.error(f"分析过程出错: {e}")
            logger.error(traceback.format_exc())
            return None
    
    def _analyze_sync(
        self,
        csv_data: str,
        patient_info: Dict[str, Any],
        test_type: str
    ) -> Optional[Dict[str, Any]]:
        """同步分析模式"""
        try:
            # 保存临时CSV文件
            temp_csv_path = self._save_temp_csv(csv_data)
            
            # 执行分析
            if test_type.upper() == "COMPREHENSIVE":
                logger.info("执行综合分析...")
                logger.info(f"CSV文件路径: {temp_csv_path}")
                
                # 使用 multi_file_workflow 的两个方法
                # 导入 multi_file_workflow 模块
                from gemsage.multi_file_workflow import analyze_multiple_files, generate_reports_from_analyses
                
                # 第一步：使用 analyze_multiple_files 分析文件（使用日期目录）
                csv_files = [str(temp_csv_path)]
                today = datetime.now().strftime("%Y-%m-%d")
                temp_analysis_dir = os.path.join("tmp", today, "temp_analysis_results")
                analysis_results, analysis_dir = analyze_multiple_files(csv_files, temp_analysis_dir)
                
                # 获取第一个（也是唯一的）分析结果
                raw_result = analysis_results[0]
                logger.info(f"multi_file_workflow分析返回结果: {raw_result}")
                
                # 将原始患者信息保存到分析结果中，以便 generate_reports_from_analyses 使用
                if analysis_results:
                    analysis_results[0]['original_patient_info'] = patient_info
                    
                    # 重新保存包含患者信息的分析结果
                    import json
                    summary_file = os.path.join(analysis_dir, "analysis_summary.json")
                    if os.path.exists(summary_file):
                        with open(summary_file, 'r', encoding='utf-8') as f:
                            summary = json.load(f)
                        summary['results'][0]['original_patient_info'] = patient_info
                        with open(summary_file, 'w', encoding='utf-8') as f:
                            json.dump(summary, f, ensure_ascii=False, indent=2, default=str)
                
                # 第二步：使用 generate_reports_from_analyses 生成报告（默认combined模式）
                logger.info("生成综合报告...")
                report_success = generate_reports_from_analyses(analysis_dir, "combined")
                if report_success:
                    logger.info("✅ 报告生成成功")
                else:
                    logger.error("❌ 报告生成失败")
                
                logger.info(f"最终分析结果: {raw_result}")
                
                # 如果有gemsage AI引擎，进行AI评估
                if self.ai_engine:
                    logger.info("调用gemsage AI评估引擎...")
                    try:
                        # 使用AI引擎进行综合评估
                        from gemsage.ai_assessment_engine import ComprehensiveMetrics
                        
                        # 构建综合指标数据结构 - 直接传递原始数据，不做任何适配
                        logger.info(f"构建ComprehensiveMetrics，数据结构:")
                        gait_data = raw_result.get('gait_analysis', {})
                        balance_data = raw_result.get('balance_analysis', {})
                        logger.info(f"  gait_analysis: {gait_data}")
                        logger.info(f"  balance_analysis: {balance_data}")
                        logger.info(f"  patient_info: {patient_info}")
                        
                        # 将numpy类型转换为标准Python类型
                        def convert_numpy_types(data):
                            if isinstance(data, dict):
                                return {k: convert_numpy_types(v) for k, v in data.items()}
                            elif isinstance(data, list):
                                return [convert_numpy_types(item) for item in data]
                            elif hasattr(data, 'item'):  # numpy类型
                                return data.item()
                            else:
                                return data
                        
                        # 转换数据类型
                        converted_gait_data = convert_numpy_types(gait_data)
                        converted_balance_data = convert_numpy_types(balance_data)
                        
                        # 转换patient_info中的数字字段
                        converted_patient_info = patient_info.copy()
                        for key in ['age', 'weight', 'height']:
                            if key in converted_patient_info:
                                try:
                                    converted_patient_info[key] = float(converted_patient_info[key])
                                except (ValueError, TypeError):
                                    # 如果转换失败，使用默认值
                                    defaults = {'age': 65, 'weight': 70, 'height': 170}
                                    converted_patient_info[key] = defaults.get(key, 0)
                        
                        comprehensive_metrics = ComprehensiveMetrics(
                            gait_metrics=converted_gait_data,
                            temporal_metrics={},
                            joint_metrics={},
                            power_metrics={},
                            posture_metrics=converted_balance_data,
                            grf_metrics={},
                            patient_info=converted_patient_info
                        )
                        
                        logger.info("开始调用AI评估引擎...")
                        logger.info(f"传递给AI引擎的数据类型检查:")
                        logger.info(f"  gait_metrics类型: {type(converted_gait_data)}")
                        logger.info(f"  posture_metrics类型: {type(converted_balance_data)}")
                        logger.info(f"  converted_patient_info: {converted_patient_info}")
                        
                        # 调用正确的方法名
                        ai_assessment = self.ai_engine.calculate_comprehensive_assessment(comprehensive_metrics)
                        
                        # 生成诊断建议
                        logger.info("生成AI诊断建议...")
                        diagnostic_suggestions = self.ai_engine.generate_diagnostic_suggestions(ai_assessment, comprehensive_metrics)
                        
                        # 生成详细评估报告
                        logger.info("生成AI详细评估报告...")
                        detailed_report = self.ai_engine.generate_detailed_report(ai_assessment, comprehensive_metrics)
                        
                        # 将AI评估结果合并到原始结果中
                        raw_result['ai_assessment'] = ai_assessment
                        raw_result['ai_diagnostic_suggestions'] = diagnostic_suggestions
                        raw_result['ai_detailed_report'] = detailed_report
                        
                        logger.info("🎉 gemsage AI评估完成!")
                        logger.info(f"AI评估结果类型: {type(ai_assessment)}")
                        logger.info(f"AI评估结果: {ai_assessment}")
                        logger.info(f"生成了 {len(diagnostic_suggestions)} 条诊断建议")
                        logger.info(f"详细报告包含 {len(detailed_report.评估明细)} 条评估明细")
                        
                        # 生成AI评估文本摘要，用于集成到现有医疗报告中
                        ai_summary = self._generate_ai_summary(ai_assessment, diagnostic_suggestions, detailed_report)
                        raw_result['ai_summary'] = ai_summary
                        logger.info("✅ AI评估摘要已生成，将集成到医疗报告中")
                        
                    except Exception as ai_error:
                        import traceback
                        logger.error(f"gemsage AI评估失败: {ai_error}")
                        logger.error(f"详细错误信息: {traceback.format_exc()}")
                        # AI评估失败不影响基础分析结果
                        
            else:
                # 其他分析类型
                pressure_data = self.analyzer.parse_csv_data(csv_data)
                raw_result = {
                    'cop_metrics': self.analyzer.calculate_cop_metrics([pressure_data]),
                    'balance_metrics': self.analyzer.analyze_balance([pressure_data])
                }
            
            # 清理临时文件
            if temp_csv_path.exists():
                temp_csv_path.unlink()
            
            # 格式化结果
            return self._format_result(raw_result, patient_info)
            
        except Exception as e:
            logger.error(f"同步分析失败: {e}")
            return None
    
    def _analyze_async(
        self,
        csv_data: str,
        patient_info: Dict[str, Any],
        test_type: str
    ) -> Optional[Dict[str, Any]]:
        """异步分析模式"""
        try:
            # 保存临时CSV文件
            temp_csv_path = self._save_temp_csv(csv_data)
            
            # 提交异步任务
            task_id = self.async_client.analyze_file_async(
                str(temp_csv_path),
                test_type.lower()
            )
            
            # 等待结果
            raw_result = self.async_client.service.get_result(
                task_id,
                timeout=self.timeout
            )
            
            # 清理临时文件
            if temp_csv_path.exists():
                temp_csv_path.unlink()
            
            # 格式化结果
            return self._format_result(raw_result, patient_info)
            
        except Exception as e:
            logger.error(f"异步分析失败: {e}")
            return None
    
    def _save_temp_csv(self, csv_data: str) -> Path:
        """保存临时CSV文件到tmp/日期目录"""
        today = datetime.now().strftime("%Y-%m-%d")
        temp_dir = Path("tmp") / today / "temp_csv"
        temp_dir.mkdir(parents=True, exist_ok=True)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        temp_csv_path = temp_dir / f"pressure_data_{timestamp}.csv"
        
        with open(temp_csv_path, 'w', encoding='utf-8') as f:
            f.write(csv_data)
        
        return temp_csv_path
    
    
    def _format_result(
        self,
        raw_result: Dict[str, Any],
        patient_info: Dict[str, Any]
    ) -> Dict[str, Any]:
        """格式化分析结果为统一格式"""
        try:
            # 提取评分
            overall_score = 100
            sub_scores = {}
            
            if 'balance_score' in raw_result:
                overall_score = raw_result['balance_score']
            elif 'balance_metrics' in raw_result:
                balance_metrics = raw_result['balance_metrics']
                if 'scores' in balance_metrics:
                    scores = balance_metrics['scores']
                    overall_score = scores.get('overall', 100)
                    sub_scores = {
                        'stability': scores.get('stability', 100),
                        'symmetry': scores.get('symmetry', 100),
                        'mobility': scores.get('mobility', 100)
                    }
            
            # 构建统一格式的结果
            formatted_result = {
                'status': 'success',
                'data': {
                    'overall_score': overall_score,
                    'sub_scores': sub_scores,
                    'metrics': raw_result,
                    'patient_info': patient_info,
                    'test_time': datetime.now().isoformat(),
                    'suggestions': self._generate_suggestions(overall_score)
                }
            }
            
            return formatted_result
            
        except Exception as e:
            logger.error(f"格式化结果失败: {e}")
            return {
                'status': 'error',
                'error': str(e),
                'data': raw_result
            }
    
    def _generate_report(
        self,
        analysis_result: Dict[str, Any],
        patient_info: Dict[str, Any]
    ) -> Optional[str]:
        """生成分析报告HTML - 集成AI评估结果"""
        try:
            if not self.report_generator:
                logger.warning("报告生成器未初始化")
                return None
            
            # 提取分析数据
            data = analysis_result.get('data', {})
            metrics = data.get('metrics', {})
            
            # 转换性别为中文
            gender_map = {'MALE': '男', 'FEMALE': '女', 'male': '男', 'female': '女'}
            original_gender = patient_info.get('gender', '未知')
            chinese_gender = gender_map.get(original_gender, original_gender)
            
            # 准备基础报告数据 - 提供所有必需字段
            report_data = {
                # 患者信息
                'patient_name': patient_info.get('name', '未知'),
                'patient_gender': chinese_gender,
                'patient_age': str(patient_info.get('age', '未知')),
                'test_date': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'report_number': f"AI-{datetime.now().strftime('%Y%m%d-%H%M%S')}",
                'medical_record_number': patient_info.get('id', f"MR{datetime.now().strftime('%Y%m%d')}"),
                'department': '智能肌少症检测系统',
                'age_group': self._get_age_group(patient_info.get('age', 65)),
                'age_range': self._get_age_range(patient_info.get('age', 65)),
                
                # 步态分析数据 - 基于实际分析结果或默认值
                'walking_speed': self._get_gait_value(metrics, 'walking_speed', '数据不足'),
                'left_step_length': self._get_gait_value(metrics, 'left_step_length', '数据不足'),
                'right_step_length': self._get_gait_value(metrics, 'right_step_length', '数据不足'),
                'left_stride_length': self._get_gait_value(metrics, 'left_stride_length', '数据不足'),
                'right_stride_length': self._get_gait_value(metrics, 'right_stride_length', '数据不足'),
                'left_cadence': self._get_gait_value(metrics, 'left_cadence', '数据不足'),
                'right_cadence': self._get_gait_value(metrics, 'right_cadence', '数据不足'),
                'left_stride_speed': self._get_gait_value(metrics, 'left_stride_speed', '数据不足'),
                'right_stride_speed': self._get_gait_value(metrics, 'right_stride_speed', '数据不足'),
                'left_swing_speed': self._get_gait_value(metrics, 'left_swing_speed', '数据不足'),
                'right_swing_speed': self._get_gait_value(metrics, 'right_swing_speed', '数据不足'),
                'left_stance_phase': self._get_gait_value(metrics, 'left_stance_phase', '数据不足'),
                'right_stance_phase': self._get_gait_value(metrics, 'right_stance_phase', '数据不足'),
                'left_swing_phase': self._get_gait_value(metrics, 'left_swing_phase', '数据不足'),
                'right_swing_phase': self._get_gait_value(metrics, 'right_swing_phase', '数据不足'),
                'left_double_support': self._get_gait_value(metrics, 'left_double_support', '数据不足'),
                'right_double_support': self._get_gait_value(metrics, 'right_double_support', '数据不足'),
                'left_step_height': self._get_gait_value(metrics, 'left_step_height', '数据不足'),
                'right_step_height': self._get_gait_value(metrics, 'right_step_height', '数据不足'),
                'step_width': self._get_gait_value(metrics, 'step_width', '数据不足'),
                'turn_time': self._get_gait_value(metrics, 'turn_time', '数据不足'),
                
                # 平衡分析数据 - 确保提供数值类型的数据
                'balance_analysis': self._prepare_balance_analysis(metrics.get('balance_analysis', {})),
                
                # 足底压力数据 - 基于可用数据或默认值
                'left_max_pressure': self._get_pressure_value(metrics, 'left_max_pressure', '数据不足'),
                'left_avg_pressure': self._get_pressure_value(metrics, 'left_avg_pressure', '数据不足'),
                'left_contact_area': self._get_pressure_value(metrics, 'left_contact_area', '数据不足'),
                'right_max_pressure': self._get_pressure_value(metrics, 'right_max_pressure', '数据不足'),
                'right_avg_pressure': self._get_pressure_value(metrics, 'right_avg_pressure', '数据不足'),
                'right_contact_area': self._get_pressure_value(metrics, 'right_contact_area', '数据不足'),
                
                # 评估结论
                'speed_assessment': self._get_speed_assessment(metrics),
                'overall_assessment': f"综合评分: {data.get('overall_score', 'N/A')}分"
            }
            
            # 如果有AI评估摘要，添加到报告的总体评估中
            if 'ai_summary' in analysis_result:
                ai_summary = analysis_result['ai_summary']
                logger.info("📊 集成AI评估摘要到医疗报告...")
                
                # 将AI摘要追加到总体评估中
                current_assessment = report_data.get('overall_assessment', '')
                report_data['overall_assessment'] = f"{current_assessment}\n\n{ai_summary}"
            
            # 生成报告选项 - 显示所有模块
            options = {
                'show_history_charts': True,
                'show_cop_analysis': True,
                'show_recommendations': True,
                'show_foot_pressure': True
            }
            
            # 生成HTML报告
            html_report = self.report_generator.generate_report(
                report_data,
                options
            )
            
            logger.info("✅ 医疗报告生成完成，已集成AI评估结果")
            
            # 保存HTML报告到日期目录
            try:
                import os
                
                # 创建按日期组织的目录结构（与现有逻辑一致）
                today = datetime.now().strftime("%Y-%m-%d")
                report_dir = os.path.join(os.getcwd(), "tmp", today, "reports")
                os.makedirs(report_dir, exist_ok=True)
                
                # 生成文件名（与现有逻辑一致）
                patient_name = patient_info.get('name', '未知患者')
                test_type = '综合分析'
                timestamp = datetime.now().strftime("%H%M%S")
                filename = f"{patient_name}-{test_type}-AI智能报告-{timestamp}.html"
                
                # 保存到本地
                html_report_path = os.path.join(report_dir, filename)
                with open(html_report_path, 'w', encoding='utf-8') as f:
                    f.write(html_report)
                
                logger.info(f"📄 HTML医疗报告已保存到: {html_report_path}")
                
                # 尝试将HTML转换为PDF
                try:
                    pdf_path = self.convert_html_to_pdf(html_report, html_report_path.replace('.html', '.pdf'))
                    if pdf_path and os.path.exists(pdf_path):
                        logger.info(f"📄 PDF报告已生成: {pdf_path}")
                        return html_report, pdf_path
                    else:
                        logger.warning("PDF转换失败，返回HTML报告")
                        return html_report, html_report_path
                except Exception as pdf_error:
                    logger.warning(f"PDF转换异常: {pdf_error}，返回HTML报告")
                    return html_report, html_report_path
                
            except Exception as save_error:
                logger.error(f"保存HTML报告失败: {save_error}")
                return html_report, None
            
        except Exception as e:
            logger.error(f"生成报告失败: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return None
    
    def generate_pdf_report(
        self,
        analysis_result: Dict[str, Any],
        patient_info: Dict[str, Any],
        output_path: str = None
    ) -> Optional[str]:
        """生成PDF格式的分析报告"""
        try:
            # 先生成HTML报告
            html_content = self._generate_report(analysis_result, patient_info)
            if not html_content:
                raise Exception("HTML报告生成失败")
            
            # 如果未指定输出路径，生成默认路径
            if output_path is None:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                patient_name = patient_info.get('name', 'Unknown').replace(' ', '_')
                filename = f"肌少症分析报告_{patient_name}_{timestamp}.pdf"
                
                # 创建日期目录
                today = datetime.now().strftime("%Y-%m-%d")
                date_dir = Path.cwd() / today
                date_dir.mkdir(exist_ok=True)
                
                output_path = str(date_dir / filename)
            
            # 转换HTML为PDF
            pdf_path = self.convert_html_to_pdf(html_content, output_path)
            logger.info(f"PDF报告生成成功: {pdf_path}")
            
            return pdf_path
            
        except Exception as e:
            logger.error(f"PDF报告生成失败: {e}")
            return None
    
    def _generate_suggestions(self, score: float) -> list:
        """根据评分生成建议"""
        suggestions = []
        
        if score >= 90:
            suggestions.append("保持良好的运动习惯")
            suggestions.append("定期进行平衡训练")
        elif score >= 70:
            suggestions.append("加强下肢力量训练")
            suggestions.append("进行平衡性练习")
            suggestions.append("注意预防跌倒")
        elif score >= 50:
            suggestions.append("建议进行专业康复训练")
            suggestions.append("使用辅助行走工具")
            suggestions.append("定期复查")
        else:
            suggestions.append("立即就医评估")
            suggestions.append("避免独自活动")
            suggestions.append("进行全面检查")
        
        return suggestions
    
    def _generate_ai_summary(self, ai_assessment, diagnostic_suggestions: List, detailed_report) -> str:
        """生成AI评估文本摘要，用于集成到现有医疗报告中"""
        try:
            risk_map = {'low': '低风险', 'moderate': '中等风险', 'high': '高风险', 'severe': '严重风险'}
            risk_text = risk_map.get(ai_assessment.risk_level.value, '未知') if ai_assessment.risk_level else '未知'
            
            # 生成6维度评分摘要
            dimensions = {
                '步态时间': ai_assessment.步态时间,
                '步态时域': ai_assessment.步态时域,
                '关节角域': ai_assessment.关节角域,
                '关节力能': ai_assessment.关节力能,
                '姿态': ai_assessment.姿态,
                '地返力': ai_assessment.地返力
            }
            
            dimension_text = ", ".join([f"{k}:{v:.1f}分" for k, v in dimensions.items()])
            
            # 生成主要建议摘要
            high_priority_suggestions = [s for s in diagnostic_suggestions if s.priority.value == 'high']
            suggestion_text = ""
            if high_priority_suggestions:
                suggestion_text = f"主要建议: {high_priority_suggestions[0].suggestion}"
            
            # 组装完整摘要
            summary = f"""
AI智能评估结果:
• 综合评分: {ai_assessment.overall_score:.1f}/100 分
• 风险等级: {risk_text}
• AI置信度: {ai_assessment.confidence:.1f}%
• 六维度评分: {dimension_text}
• 评估明细: {len(detailed_report.评估明细)} 项发现
• 诊断建议: {len(diagnostic_suggestions)} 条建议
{suggestion_text}

功能评估: 活动能力{detailed_report.functional_capacity.get('mobility_score', 0)}分, 稳定性{detailed_report.functional_capacity.get('stability_score', 0)}分
疾病风险: 肌少症风险{detailed_report.disease_risk.get('sarcopenia_risk', 0)}%, 跌倒风险{detailed_report.disease_risk.get('fall_risk', 0)}%
"""
            return summary.strip()
            
        except Exception as e:
            logger.error(f"生成AI摘要失败: {e}")
            return f"AI评估完成，综合评分: {getattr(ai_assessment, 'overall_score', 'N/A')}分"
    
    def _get_age_group(self, age: int) -> str:
        """根据年龄获取年龄组"""
        try:
            age = int(age)
            if age < 18:
                return "儿童组 (<18岁)"
            elif age <= 30:
                return "青年组 (18-30岁)"
            elif age <= 50:
                return "中年组 (31-50岁)"
            elif age <= 70:
                return "中老年组 (51-70岁)"
            else:
                return "老年组 (>70岁)"
        except:
            return "未知年龄组"
    
    def _get_age_range(self, age: int) -> str:
        """根据年龄获取年龄范围"""
        try:
            age = int(age)
            if age < 18:
                return "<18岁"
            elif age <= 30:
                return "18-30岁"
            elif age <= 50:
                return "31-50岁"
            elif age <= 70:
                return "51-70岁"
            else:
                return ">70岁"
        except:
            return "未知"
    
    def _get_gait_value(self, metrics: Dict, key: str, default: str) -> str:
        """获取步态分析值，如果不存在则返回标注的默认值"""
        # 检查是否有步态分析错误
        gait_analysis = metrics.get('gait_analysis', {})
        balance_analysis = metrics.get('balance_analysis', {})
        
        # 如果有具体的数值，返回该数值
        if key in gait_analysis and not isinstance(gait_analysis[key], str):
            return str(gait_analysis[key])
        
        if key in balance_analysis and not isinstance(balance_analysis[key], str):
            return str(balance_analysis[key])
        
        # 如果分析失败，返回标注的默认值
        if 'error' in gait_analysis or 'error' in balance_analysis:
            return default
        
        # 其他情况返回默认值
        return default
    
    def _get_speed_assessment(self, metrics: Dict) -> str:
        """获取步速评估"""
        gait_analysis = metrics.get('gait_analysis', {})
        
        # 如果有步态分析错误
        if 'error' in gait_analysis:
            return "数据不足，无法进行步速评估"
        
        # 如果有实际数据
        if 'average_velocity' in gait_analysis:
            velocity = gait_analysis['average_velocity']
            if velocity > 1.2:
                return "步速正常"
            elif velocity > 0.8:
                return "步速略慢"
            else:
                return "步速明显偏慢"
        
        return "基于AI智能分析"
    
    def _prepare_balance_analysis(self, balance_data: Dict) -> Dict:
        """准备平衡分析数据，确保模板需要的字段都是数值类型"""
        # 如果有错误信息，提供默认的数值数据
        if 'error' in balance_data:
            return {
                'copArea': 0.0,                     # COP轨迹面积 (cm²)
                'copPathLength': 0.0,               # 轨迹总长度 (cm)
                'copComplexity': 0.0,               # 轨迹复杂度 (/10)
                'anteroPosteriorRange': 0.0,        # 前后摆动范围 (cm)
                'medioLateralRange': 0.0,           # 左右摆动范围 (cm)
                'stabilityIndex': 0.0,              # 稳定性指数 (%)
                'data_available': False             # 标记数据不可用
            }
        
        # 确保所有字段都有数值，没有的话提供默认值
        return {
            'copArea': float(balance_data.get('copArea', 0.0)),
            'copPathLength': float(balance_data.get('copPathLength', 0.0)),
            'copComplexity': float(balance_data.get('copComplexity', 0.0)),
            'anteroPosteriorRange': float(balance_data.get('anteroPosteriorRange', 0.0)),
            'medioLateralRange': float(balance_data.get('medioLateralRange', 0.0)),
            'stabilityIndex': float(balance_data.get('stabilityIndex', 0.0)),
            'data_available': True
        }
    
    def _get_pressure_value(self, metrics: Dict, key: str, default: str) -> str:
        """获取足底压力值"""
        # 检查是否有具体数据
        if key in metrics:
            return str(metrics[key])
        
        # 检查是否有分析错误
        gait_analysis = metrics.get('gait_analysis', {})
        balance_analysis = metrics.get('balance_analysis', {})
        
        if 'error' in gait_analysis or 'error' in balance_analysis:
            return default
        
        return default
    
    def _generate_cache_key(
        self,
        csv_data: str,
        patient_info: Dict[str, Any],
        test_type: str
    ) -> str:
        """生成缓存键"""
        import hashlib
        content = f"{csv_data}_{json.dumps(patient_info)}_{test_type}"
        return hashlib.md5(content.encode()).hexdigest()
    
    def get_status(self) -> Dict[str, Any]:
        """获取引擎状态"""
        status = {
            'is_initialized': self.is_initialized,
            'algorithms_dir': str(self.algorithms_dir),
            'async_enabled': app_config['enable_async'] and self.async_client is not None,
            'cache_enabled': self.cache is not None,
            'timeout': self.timeout
        }
        
        if self.is_initialized:
            status['modules'] = {
                'analyzer': self.analyzer is not None,
                'report_generator': self.report_generator is not None,
                'async_client': self.async_client is not None
            }
        
        if self.cache is not None:
            status['cache_size'] = len(self.cache)
        
        return status
    
    def convert_html_to_pdf(self, html_content: str, output_path: str = None) -> str:
        """将HTML内容转换为PDF文件"""
        try:
            # 为了解决中文问题，我们需要注册字体
            from xhtml2pdf import pisa
            from reportlab.pdfbase import pdfmetrics
            from reportlab.pdfbase.cidfonts import UnicodeCIDFont
            
            # 注册中文字体
            try:
                pdfmetrics.registerFont(UnicodeCIDFont('STSong-Light'))
                logger.info("注册中文字体成功")
            except Exception as e:
                logger.warning(f"注册中文字体失败: {e}")
            
            if output_path is None:
                temp_fd, output_path = tempfile.mkstemp(suffix='.pdf')
                os.close(temp_fd)
            
            # 为HTML添加最小的字体声明（只在内存中修改）
            # 在HTML的<head>中插入字体CSS
            import re
            
            # 查找</head>标签的位置
            head_end = html_content.find('</head>')
            if head_end > 0:
                # 插入字体样式
                font_style = """
                <style>
                    body { font-family: STSong-Light, sans-serif; }
                    * { font-family: STSong-Light, sans-serif; }
                </style>
                """
                # 在</head>之前插入样式
                modified_html = html_content[:head_end] + font_style + html_content[head_end:]
            else:
                # 如果没有head标签，尝试在<html>后面添加
                html_start = html_content.find('<html')
                if html_start >= 0:
                    html_tag_end = html_content.find('>', html_start)
                    if html_tag_end > 0:
                        font_style = """
                        <head>
                        <style>
                            body { font-family: STSong-Light, sans-serif; }
                            * { font-family: STSong-Light, sans-serif; }
                        </style>
                        </head>
                        """
                        modified_html = html_content[:html_tag_end+1] + font_style + html_content[html_tag_end+1:]
                    else:
                        modified_html = html_content
                else:
                    modified_html = html_content
            
            # 创建PDF
            with open(output_path, "wb") as result_file:
                pisa_status = pisa.CreatePDF(
                    modified_html,
                    dest=result_file,
                    encoding='utf-8'
                )
            
            if not pisa_status.err:
                logger.info(f"PDF生成成功: {output_path}")
                return output_path
            else:
                logger.warning(f"PDF生成失败: {pisa_status.err}")
                # 如果PDF生成失败，返回HTML
                html_path = output_path.replace('.pdf', '.html')
                with open(html_path, 'w', encoding='utf-8') as f:
                    f.write(html_content)  # 保存原始HTML，不是修改后的
                logger.info(f"PDF生成失败，已保存HTML: {html_path}")
                return html_path
                
                # 尝试使用weasyprint
                try:
                    from weasyprint import HTML, CSS
                    
                    if output_path is None:
                        temp_fd, output_path = tempfile.mkstemp(suffix='.pdf')
                        os.close(temp_fd)
                    
                    # 基本CSS样式
                    css = CSS(string='''
                        @page {
                            size: A4;
                            margin: 2cm;
                        }
                        body {
                            font-family: Arial, "Microsoft YaHei", sans-serif;
                            font-size: 12px;
                            line-height: 1.6;
                        }
                        h1, h2, h3 {
                            color: #333;
                        }
                        table {
                            border-collapse: collapse;
                            width: 100%;
                        }
                        table, th, td {
                            border: 1px solid #ddd;
                        }
                        th, td {
                            padding: 8px;
                            text-align: left;
                        }
                    ''')
                    
                    # 生成PDF
                    HTML(string=html_content).write_pdf(output_path, stylesheets=[css])
                    logger.info(f"PDF生成成功 (weasyprint): {output_path}")
                    return output_path
                    
                except ImportError:
                    logger.warning("weasyprint未安装，尝试使用reportlab")
                    
                    # 使用reportlab作为后备方案
                    try:
                        from reportlab.pdfgen import canvas
                        from reportlab.lib.pagesizes import A4
                        from reportlab.lib import colors
                        from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
                        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
                        from reportlab.lib.units import inch
                        from bs4 import BeautifulSoup
                        import re
                        
                        if output_path is None:
                            temp_fd, output_path = tempfile.mkstemp(suffix='.pdf')
                            os.close(temp_fd)
                        
                        # 解析HTML内容
                        soup = BeautifulSoup(html_content, 'html.parser')
                        
                        # 创建PDF文档
                        doc = SimpleDocTemplate(output_path, pagesize=A4)
                        styles = getSampleStyleSheet()
                        story = []
                        
                        # 提取文本内容并格式化
                        for element in soup.find_all(['h1', 'h2', 'h3', 'p', 'div', 'table']):
                            text = element.get_text().strip()
                            if text:
                                if element.name in ['h1', 'h2', 'h3']:
                                    style = styles['Heading1'] if element.name == 'h1' else styles['Heading2']
                                else:
                                    style = styles['Normal']
                                
                                para = Paragraph(text, style)
                                story.append(para)
                                story.append(Spacer(1, 12))
                        
                        # 构建PDF
                        doc.build(story)
                        logger.info(f"PDF生成成功 (reportlab): {output_path}")
                        return output_path
                        
                    except ImportError:
                        logger.warning("没有可用的PDF生成库，生成文本格式报告")
                        
                        # 使用简单的文本格式作为后备
                        if output_path is None:
                            temp_fd, output_path = tempfile.mkstemp(suffix='.txt')
                            os.close(temp_fd)
                        
                        # 解析HTML内容生成文本
                        try:
                            from bs4 import BeautifulSoup
                            soup = BeautifulSoup(html_content, 'html.parser')
                            text_content = soup.get_text()
                        except ImportError:
                            # 简单的HTML标签移除
                            import re
                            text_content = re.sub(r'<[^>]+>', '', html_content)
                            text_content = re.sub(r'\s+', ' ', text_content).strip()
                        
                        with open(output_path, 'w', encoding='utf-8') as f:
                            f.write("肌少症分析报告\n" + "="*50 + "\n\n")
                            f.write(text_content)
                            f.write("\n\n" + "="*50)
                            f.write("\n报告生成时间: " + datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
                        
                        logger.info(f"文本报告生成成功: {output_path}")
                        return output_path
                        
        except Exception as e:
            logger.error(f"HTML到PDF转换失败: {e}")
            raise Exception(f"PDF转换失败: {e}")
    

    def clear_cache(self):
        """清空缓存"""
        if self.cache is not None:
            self.cache.clear()
            logger.info("缓存已清空")
    
    def __enter__(self):
        """上下文管理器入口"""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """上下文管理器退出"""
        pass

# 全局引擎实例
_engine_instance = None

def get_algorithm_engine(algorithms_dir: str = None) -> AlgorithmEngineManager:
    """获取全局算法引擎实例"""
    global _engine_instance
    
    # 强制重新创建引擎实例以应用最新配置
    _engine_instance = AlgorithmEngineManager(algorithms_dir)
    
    return _engine_instance

def test_engine():
    """测试算法引擎"""
    print("测试算法引擎管理器...")
    
    try:
        # 创建引擎
        engine = AlgorithmEngineManager()
        
        # 检查状态
        status = engine.get_status()
        print(f"引擎状态: {json.dumps(status, indent=2, ensure_ascii=False)}")
        
        # 测试数据
        test_csv = "timestamp,x1,y1,x2,y2\n1,10,20,30,40\n2,15,25,35,45"
        test_patient = {
            'name': '测试患者',
            'age': 65,
            'gender': '男',
            'height': 170,
            'weight': 70
        }
        
        # 执行分析
        print("\n执行分析测试...")
        result = engine.analyze_data(
            test_csv,
            test_patient,
            'COMPREHENSIVE'
        )
        
        if result:
            print("✅ 分析成功")
            print(f"总体评分: {result.get('data', {}).get('overall_score', 'N/A')}")
        else:
            print("❌ 分析失败")
        
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        traceback.print_exc()

if __name__ == "__main__":
    test_engine()