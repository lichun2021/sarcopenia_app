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
import importlib.util
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
            
            # 检查GemSage单文件是否存在
            logger.info(f"检查GemSage单文件分析引擎")
            
            # 获取正确的基础目录（处理打包环境）
            if getattr(sys, 'frozen', False):
                # 打包后的exe环境
                base_dir = os.path.dirname(sys.executable)
            else:
                # 开发环境
                base_dir = os.path.dirname(__file__)
            
            gemsage_path = os.path.join(base_dir, 'gemsage', 'GemSage_GaitAnalysis_Professional.py')
            logger.info(f"GemSage路径: {gemsage_path}")
            
            if os.path.exists(gemsage_path):
                logger.info("找到GemSage单文件分析引擎")
                self.gemsage_script_path = gemsage_path
                
                # 导入GemSage单文件中的类
                try:
                    # 添加gemsage目录到Python路径
                    gemsage_dir = os.path.dirname(gemsage_path)
                    if gemsage_dir not in sys.path:
                        sys.path.insert(0, gemsage_dir)
                    
                    # 直接导入单文件模块
                    spec = importlib.util.spec_from_file_location("gemsage_professional", gemsage_path)
                    gemsage_module = importlib.util.module_from_spec(spec)
                    
                    # 关键修复：将模块注册到 sys.modules 中，避免 dataclass 装饰器错误
                    sys.modules["gemsage_professional"] = gemsage_module
                    
                    spec.loader.exec_module(gemsage_module)
                    
                    # 获取类引用
                    self.UltimateFixReportGenerator = gemsage_module.UltimateFixReportGenerator
                    logger.info("成功导入GemSage单文件类")
                    
                except Exception as e:
                    logger.error(f"导入GemSage单文件失败: {e}")
                    # 如果导入失败，抛出异常终止初始化
                    self.UltimateFixReportGenerator = None
                    raise ImportError(f"GemSage单文件类导入失败: {e}")
                
                self.analyzer = None  
                self.report_generator_new = None  
                self.ai_engine = None
                self.report_generator = None
            else:
                logger.error(f"GemSage单文件不存在: {gemsage_path}")
                raise ImportError(f"必需的GemSage单文件不存在: {gemsage_path}")
            
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
    
    def analyze_multiple_csv_files(
        self,
        csv_files: List[str],  # CSV文件路径列表
        patient_info: Dict[str, Any],
        generate_report: bool = True
    ) -> Optional[Dict[str, Any]]:
        """
        分析多个CSV文件并生成综合报告
        
        Args:
            csv_files: CSV文件路径列表
            patient_info: 患者信息字典
            generate_report: 是否生成报告
            
        Returns:
            分析结果字典或None
        """
        if not self.is_initialized:
            logger.error("算法引擎未初始化")
            return None
        
        if not csv_files:
            logger.error("没有提供CSV文件")
            return None
            
        try:
            start_time = time.time()
            logger.info(f"开始分析 {len(csv_files)} 个CSV文件 - 患者: {patient_info.get('name', '未知')}")
            
            # 创建临时目录存放CSV文件
            today = datetime.now().strftime("%Y-%m-%d")
            temp_dir = os.path.join("tmp", today, "multi_csv_analysis")
            os.makedirs(temp_dir, exist_ok=True)
            
            # 复制CSV文件到临时目录
            temp_csv_paths = []
            for i, csv_file in enumerate(csv_files):
                # 保留原文件名以便分类
                original_name = os.path.basename(csv_file)
                temp_path = os.path.join(temp_dir, original_name)
                
                # 如果是文件路径，直接复制
                if os.path.exists(csv_file):
                    import shutil
                    shutil.copy2(csv_file, temp_path)
                else:
                    # 如果是CSV内容，写入文件
                    with open(temp_path, 'w', encoding='utf-8') as f:
                        f.write(csv_file)
                
                temp_csv_paths.append(temp_path)
                logger.info(f"  文件 {i+1}: {original_name}")
            
            # 使用GemSage单文件处理多文件
            patient_name = patient_info.get('name', '测试者')
            patient_age = patient_info.get('age', 65)
            # 性别参数映射：将英文映射为中文
            raw_gender = patient_info.get('gender', '男')
            gender_mapping = {
                'MALE': '男',
                'FEMALE': '女', 
                'male': '男',
                'female': '女',
                '男': '男',
                '女': '女'
            }
            patient_gender = gender_mapping.get(raw_gender, '男')
            
            if self.UltimateFixReportGenerator:
                # 方式1：直接调用类方法生成完整报告
                try:
                    generator = self.UltimateFixReportGenerator()
                    
                    # 准备输出路径（使用绝对路径）
                    # 获取程序运行目录
                    if getattr(sys, 'frozen', False):
                        # 打包后的exe
                        base_dir = os.path.dirname(sys.executable)
                    else:
                        # 开发环境
                        base_dir = os.path.dirname(os.path.abspath(__file__))
                    
                    reports_dir = os.path.join(base_dir, "tmp", today, "reports")
                    os.makedirs(reports_dir, exist_ok=True)
                    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                    output_filename = f"{patient_name}_综合报告_{timestamp}.html"
                    output_path = os.path.join(reports_dir, output_filename)
                    logger.info(f"报告将生成到: {output_path}")
                    
                    # 直接生成完整报告
                    generator.generate_ultimate_report(
                        folder_path=temp_dir,
                        group_name=patient_name,
                        age=patient_age,
                        output_path=output_path,
                        gender=patient_gender
                    )
                    
                    # 读取生成的HTML文件内容
                    if os.path.exists(output_path):
                        with open(output_path, 'r', encoding='utf-8') as f:
                            report_html = f.read()
                        combined_result = {
                            'success': True,
                            'report_path': output_path,
                            'report_html': report_html,
                            'message': '报告生成成功'
                        }
                    else:
                        combined_result = {
                            'success': False,
                            'error': f'报告文件未生成: {output_path}',
                            'report_path': output_path
                        }
                    logger.info("通过类方法调用GemSage分析完成")
                except Exception as e:
                    logger.error(f"类方法调用失败: {e}")
                    combined_result = {'error': str(e), 'success': False}
            else:
                # 方式2：使用subprocess调用命令行
                try:
                    # 获取程序运行目录
                    if getattr(sys, 'frozen', False):
                        # 打包后的exe
                        base_dir = os.path.dirname(sys.executable)
                    else:
                        # 开发环境
                        base_dir = os.path.dirname(os.path.abspath(__file__))
                    
                    reports_dir = os.path.join(base_dir, "tmp", today, "reports")
                    os.makedirs(reports_dir, exist_ok=True)
                    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                    output_filename = f"{patient_name}_综合报告_{timestamp}.html"
                    output_path = os.path.join(reports_dir, output_filename)
                    logger.info(f"[subprocess] 报告将生成到: {output_path}")
                    
                    import subprocess
                    # 判断是否是打包后的exe
                    if getattr(sys, 'frozen', False):
                        # 打包后，使用python命令（需要系统安装Python）或直接导入模块
                        # 最好直接使用类方法，避免subprocess
                        logger.error("打包环境下subprocess调用不可用，请使用类方法调用")
                        combined_result = {'error': 'Subprocess not available in frozen mode', 'success': False}
                        return combined_result
                    else:
                        # 开发环境，使用Python解释器
                        cmd = [
                            sys.executable, self.gemsage_script_path,
                            '--data_folder', temp_dir,
                            '--name', patient_name,
                            '--age', str(patient_age),
                            '--gender', patient_gender,
                            '--output', output_path
                        ]
                    
                    logger.info(f"执行GemSage命令: {' '.join(cmd)}")
                    
                    # 设置环境变量以支持UTF-8编码
                    env = os.environ.copy()
                    env['PYTHONIOENCODING'] = 'utf-8'
                    
                    result = subprocess.run(cmd, capture_output=True, text=True, timeout=300, env=env, encoding='utf-8')
                    
                    if result.returncode == 0:
                        logger.info("subprocess调用GemSage分析完成")
                        # 读取生成的HTML文件内容
                        if os.path.exists(output_path):
                            with open(output_path, 'r', encoding='utf-8') as f:
                                report_html = f.read()
                            combined_result = {
                                'report_html': report_html,
                                'report_path': output_path,
                                'success': True
                            }
                        else:
                            combined_result = {'success': True, 'report_path': output_path}
                    else:
                        logger.error(f"GemSage执行失败: {result.stderr}")
                        combined_result = {'error': result.stderr, 'success': False}
                        
                except subprocess.TimeoutExpired:
                    logger.error("GemSage执行超时")
                    combined_result = {'error': 'Analysis timeout', 'success': False}
                except Exception as e:
                    logger.error(f"subprocess调用异常: {e}")
                    combined_result = {'error': str(e), 'success': False}
            
            # 处理报告生成
            if generate_report:
                # 检查是否已经有报告路径（subprocess方式生成的）
                if 'report_path' in combined_result and os.path.exists(combined_result['report_path']):
                    logger.info(f"报告已生成: {combined_result['report_path']}")
                    # 读取报告内容
                    with open(combined_result['report_path'], 'r', encoding='utf-8') as f:
                        combined_result['report_html'] = f.read()
                elif self.UltimateFixReportGenerator and 'error' not in combined_result:
                    # 如果使用类方法调用成功，需要手动生成HTML报告
                    try:
                        generator = self.UltimateFixReportGenerator()
                        template = generator.generate_ultimate_html_template()
                        
                        # 替换模板变量
                        for k, v in combined_result.items():
                            placeholder = f"{{{{{k}}}}}"
                            template = template.replace(placeholder, str(v))
                        
                        # 保存HTML报告
                        reports_dir = os.path.join("tmp", today, "reports")
                        os.makedirs(reports_dir, exist_ok=True)
                        
                        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                        safe_patient_name = patient_info.get('name', '未知').replace(' ', '_')
                        report_filename = f"{safe_patient_name}_综合报告_{timestamp}.html"
                        report_path = os.path.join(reports_dir, report_filename)
                        
                        with open(report_path, 'w', encoding='utf-8') as f:
                            f.write(template)
                        
                        logger.info(f"报告已保存: {report_path}")
                        
                        combined_result['report_html'] = template
                        combined_result['report_path'] = report_path
                        
                    except Exception as e:
                        logger.error(f"生成HTML报告失败: {e}")
                        combined_result['report_error'] = str(e)
            
            # 清理临时文件（可选）
            # import shutil
            # shutil.rmtree(temp_dir)
            
            logger.info(f"分析完成，耗时: {time.time() - start_time:.2f}秒")
            
            # 提取关键指标用于UI显示
            gait_params = combined_result.get('gait_parameters', {})
            overall_score = 85.0  # 默认分数
            
            # 基于步态参数计算综合评分
            if gait_params:
                velocity = gait_params.get('average_velocity', 0)
                step_count = gait_params.get('step_count', 0)
                # 简单的评分逻辑
                if velocity >= 1.0 and step_count > 0:
                    overall_score = 90.0
                elif velocity >= 0.5:
                    overall_score = 75.0
                else:
                    overall_score = 60.0
            
            # 返回UI期望的格式
            return {
                'status': 'success',
                'data': {
                    'overall_score': overall_score,
                    'risk_level': 'LOW' if overall_score >= 70 else 'HIGH',
                    'confidence': 0.85,
                    'analysis_summary': f'综合分析{len(csv_files)}个文件完成',
                    'gait_parameters': gait_params,
                    'balance_analysis': combined_result.get('balance_analysis', {}),
                    'metrics': {}
                },
                'analysis_result': combined_result,
                'report_html': combined_result.get('report_html', ''),
                'report_path': combined_result.get('report_path', ''),
                'patient_info': patient_info,
                'metadata': {
                    'analysis_time': time.time() - start_time,
                    'files_count': len(csv_files),
                    'engine_type': 'multi_file_analysis'
                }
            }
            
        except Exception as e:
            logger.error(f"分析多个CSV文件时出错: {e}")
            logger.error(traceback.format_exc())
            return {
                'status': 'error',
                'error': str(e),
                'message': f'分析失败: {str(e)}'
            }

    def analyze_data(
        self,
        csv_data: str,
        patient_info: Dict[str, Any],
        test_type: str = "COMPREHENSIVE",  # 默认综合分析
        generate_report: bool = True
    ) -> Optional[Dict[str, Any]]:
        """
        分析压力数据（单个文件）
        
        Args:
            csv_data: CSV格式的压力数据
            patient_info: 患者信息字典
            test_type: 测试类型（默认COMPREHENSIVE综合分析）
            generate_report: 是否生成报告
            
        Returns:
            分析结果字典或None
        """
        # 强制使用综合分析
        test_type = "COMPREHENSIVE"
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
                # 对于综合分析，report_html 已经在 _analyze_sync 中生成
                # 其他分析类型才需要在这里生成报告
                if test_type.upper() != "COMPREHENSIVE":
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
            
            # 调试：检查结果中是否包含报告
            logger.info(f"分析完成，耗时: {time.time() - start_time:.2f}秒")
            if result:
                logger.info(f"返回结果包含的键: {list(result.keys())}")
                logger.info(f"report_html 存在: {'report_html' in result}")
                logger.info(f"report_path: {result.get('report_path', 'None')}")
            
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
                
                # 使用GemSage单文件处理单个文件
                csv_dir = os.path.dirname(temp_csv_path)
                patient_name = patient_info.get('name', '测试者')
                patient_age = patient_info.get('age', 65)
                # 性别参数映射：将英文映射为中文
                raw_gender = patient_info.get('gender', '男')
                gender_mapping = {
                    'MALE': '男',
                    'FEMALE': '女', 
                    'male': '男',
                    'female': '女',
                    '男': '男',
                    '女': '女'
                }
                patient_gender = gender_mapping.get(raw_gender, '男')
                
                if self.UltimateFixReportGenerator:
                    # 方式1：直接调用类方法
                    try:
                        generator = self.UltimateFixReportGenerator()
                        analysis_results = generator.process_test_data_with_ultimate_fixes(
                            folder_path=csv_dir,
                            group_name=patient_name, 
                            age=patient_age,
                            gender=patient_gender
                        )
                    except Exception as e:
                        logger.error(f"单文件分析失败: {e}")
                        analysis_results = {'error': str(e)}
                else:
                    logger.error("GemSage类未正确导入，无法进行单文件分析")
                    analysis_results = {'error': 'GemSage not available'}
                
                # 打印JSON格式的分析结果
                import json
                # 分析结果处理完成
                
                # 分析结果直接从generator返回
                raw_result = analysis_results
                logger.info(f"ultimate_fix分析返回结果: {raw_result}")
                
                # 将患者信息保存到分析结果中（转换性别为中文）
                if raw_result:
                    # 复制患者信息并转换性别
                    processed_patient_info = patient_info.copy()
                    gender_map = {'MALE': '男', 'FEMALE': '女', 'male': '男', 'female': '女'}
                    if 'gender' in processed_patient_info:
                        original_gender = processed_patient_info['gender']
                        processed_patient_info['gender'] = gender_map.get(original_gender, original_gender)
                        logger.info(f"性别转换: {original_gender} -> {processed_patient_info['gender']}")
                    
                    raw_result['original_patient_info'] = processed_patient_info
                    logger.info(f"保存处理后的患者信息到分析结果: {processed_patient_info}")
                
                # 第二步：使用 generate_reports_from_analyses_json 生成报告（直接传递JSON数据）
                logger.info("生成综合报告...")
                try:
                    # 准备分析结果
                    if 'original_patient_info' not in raw_result:
                        # 补充患者信息时也要转换性别
                        processed_patient_info = patient_info.copy()
                        gender_map = {'MALE': '男', 'FEMALE': '女', 'male': '男', 'female': '女'}
                        if 'gender' in processed_patient_info:
                            original_gender = processed_patient_info['gender']
                            processed_patient_info['gender'] = gender_map.get(original_gender, original_gender)
                            logger.info(f"补充时性别转换: {original_gender} -> {processed_patient_info['gender']}")
                        
                        raw_result['original_patient_info'] = processed_patient_info
                        logger.info(f"补充处理后的患者信息到分析结果: {processed_patient_info}")
                    else:
                        logger.info(f"分析结果中已存在患者信息: {raw_result['original_patient_info']}")
                    
                    # 生成HTML报告模板
                    report_html = generator.generate_corrected_html_template()
                    # 替换模板变量
                    for k, v in raw_result.items():
                        report_html = report_html.replace(f"{{{{{k}}}}}", str(v))
                    
                    # 保存HTML报告到文件
                    today = datetime.now().strftime("%Y-%m-%d")
                    reports_dir = os.path.join("tmp", today, "reports")
                    os.makedirs(reports_dir, exist_ok=True)
                    
                    # 生成报告文件名：名字_性别_年龄_当天日期
                    patient_name = patient_info.get('name', '未知患者')
                    patient_gender_raw = patient_info.get('gender', '未知')
                    patient_age = patient_info.get('age', '未知')
                    today_date = datetime.now().strftime("%Y%m%d")
                    
                    # 转换性别为中文
                    gender_map = {'MALE': '男', 'FEMALE': '女', 'male': '男', 'female': '女'}
                    patient_gender = gender_map.get(patient_gender_raw, patient_gender_raw)
                    
                    report_filename = f"{patient_name}_{patient_gender}_{patient_age}岁_{today_date}.html"
                    report_path = os.path.join(reports_dir, report_filename)
                    
                    # 写入报告文件
                    with open(report_path, 'w', encoding='utf-8') as f:
                        f.write(report_html)
                    
                    logger.info(f"✅ 报告生成成功: {report_path}")
                    report_success = True
                    
                    # 将生成的HTML添加到结果中
                    raw_result['report_html'] = report_html
                    raw_result['report_path'] = report_path
                    
                    # 清理临时文件（如果有的话）
                    pass
                    
                except Exception as e:
                    logger.error(f"❌ 报告生成失败: {e}")
                    import traceback
                    traceback.print_exc()
                    report_success = False
                
                logger.info(f"最终分析结果: {raw_result}")
                
                # AI引擎已移除，跳过AI评估
                        
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
            
            # 传递报告相关字段
            if 'report_html' in raw_result:
                formatted_result['report_html'] = raw_result['report_html']
            if 'report_path' in raw_result:
                formatted_result['report_path'] = raw_result['report_path']
            
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
            
            # AI评估已移除
            
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
            # 检查是否已有HTML报告
            data = analysis_result.get('data', {})
            metrics = data.get('metrics', {})
            html_content = metrics.get('report_html') or data.get('report_html') or analysis_result.get('report_html')
            
            # 如果没有现成的HTML，才生成新的
            if not html_content:
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
    
    def _clean_problematic_images(self, html_content: str) -> str:
        """清理HTML中有问题的base64图片数据"""
        import re
        import base64
        
        try:
            logger.info("开始清理HTML中的图片数据...")
            
            # 查找所有base64图片
            img_pattern = r'<img[^>]+src="data:image/[^"]*"[^>]*>'
            imgs = re.findall(img_pattern, html_content)
            
            logger.info(f"找到 {len(imgs)} 个图片标签")
            
            replaced_count = 0
            for i, img_tag in enumerate(imgs):
                try:
                    # 提取base64数据部分
                    src_match = re.search(r'src="data:image/[^;]+;base64,([^"]+)"', img_tag)
                    if src_match:
                        base64_data = src_match.group(1)
                        logger.info(f"处理图片 {i+1}: base64数据长度 {len(base64_data)}")
                        
                        # 尝试解码验证base64数据
                        try:
                            decoded_data = base64.b64decode(base64_data)
                            logger.info(f"图片 {i+1}: 解码后数据长度 {len(decoded_data)}")
                            
                            # 简单验证：检查是否是有效的图片头部
                            if len(decoded_data) < 10:
                                raise ValueError("图片数据太短")
                            
                            # 检查是否包含常见图片格式头部
                            valid_headers = [
                                b'\x89PNG',  # PNG
                                b'\xff\xd8\xff',  # JPEG  
                                b'GIF8',  # GIF
                                b'<svg',  # SVG
                            ]
                            
                            # 显示前20个字节用于调试
                            header_bytes = decoded_data[:20]
                            logger.info(f"图片 {i+1}: 头部字节 {header_bytes}")
                            
                            is_valid = any(decoded_data.startswith(header) for header in valid_headers)
                            if not is_valid:
                                logger.warning(f"图片 {i+1}: 发现无效的图片数据，将替换为占位符")
                                raise ValueError("无效的图片格式")
                            else:
                                logger.info(f"图片 {i+1}: 验证通过")
                                
                        except Exception as e:
                            # 如果base64解码失败或数据无效，直接移除该图片
                            logger.warning(f"图片 {i+1}: 清理有问题的图片数据: {e}")
                            # 直接移除有问题的图片标签
                            html_content = html_content.replace(img_tag, 
                                '<div style="text-align:center;padding:20px;border:1px solid #ccc;">图表暂时无法显示</div>')
                            replaced_count += 1
                            
                except Exception as e:
                    logger.warning(f"处理图片标签 {i+1} 时出错: {e}")
                    continue
            
            logger.info(f"图片清理完成: 替换了 {replaced_count} 个有问题的图片")
            return html_content
            
        except Exception as e:
            logger.warning(f"清理图片数据时出错: {e}，返回原始HTML")
            return html_content
    
    def _fix_css_for_pdf(self, html_content: str) -> str:
        """修复HTML中的CSS以兼容PDF转换"""
        import re
        try:
            # 替换有问题的CSS属性
            # 将 width: 100% 替换为具体像素值或移除
            html_content = re.sub(r'width:\s*100%', 'width: 800px', html_content)
            html_content = re.sub(r'height:\s*100%', 'height: 600px', html_content)
            html_content = re.sub(r'max-width:\s*100%', 'max-width: 800px', html_content)
            html_content = re.sub(r'max-height:\s*100%', 'max-height: 600px', html_content)
            
            # 修复img标签的样式属性
            html_content = re.sub(r'style="[^"]*width:\s*100%[^"]*"', 'style="width:100%;height:auto;"', html_content)
            
            # 移除一些可能有问题的CSS属性
            html_content = re.sub(r'object-fit:\s*[^;]+;?', '', html_content)
            
            return html_content
        except Exception as e:
            logger.warning(f"修复CSS时出错: {e}")
            return html_content
    
    def _create_placeholder_svg(self) -> str:
        """创建占位符SVG图片"""
        placeholder_svg = '''<img src="data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iNDAwIiBoZWlnaHQ9IjMwMCIgeG1sbnM9Imh0dHA6Ly93d3cudzMub3JnLzIwMDAvc3ZnIj48cmVjdCB3aWR0aD0iMTAwJSIgaGVpZ2h0PSIxMDAlIiBmaWxsPSIjZjVmNWY1IiBzdHJva2U9IiNjY2MiIHN0cm9rZS13aWR0aD0iMSIvPjx0ZXh0IHg9IjUwJSIgeT0iNTAlIiBmb250LWZhbWlseT0iQXJpYWwiIGZvbnQtc2l6ZT0iMTQiIGZpbGw9IiM5OTkiIHRleHQtYW5jaG9yPSJtaWRkbGUiIGR5PSIuM2VtIj7lm77ooajotJ/ovb3kuK0uLi48L3RleHQ+PC9zdmc+" style="width:100%;height:200px;object-fit:contain;" alt="图表加载失败" />'''
        return placeholder_svg
    
    def convert_html_to_pdf(self, html_content: str, output_path: str = None) -> str:
        """将HTML内容转换为PDF文件 - 使用Playwright方案"""
        try:
            # 导入新的HTML转PDF模块
            from html_to_pdf import convert_html_to_pdf
            from pathlib import Path
            import asyncio
            
            if output_path is None:
                temp_fd, output_path = tempfile.mkstemp(suffix='.pdf')
                os.close(temp_fd)
            
            # 先保存HTML到临时文件
            temp_html_fd, temp_html_path = tempfile.mkstemp(suffix='.html')
            os.close(temp_html_fd)
            
            # 处理HTML内容，清理有问题的图片
            modified_html = self._clean_problematic_images(html_content)
            modified_html = self._fix_css_for_pdf(modified_html)
            
            # 保存HTML内容到临时文件
            with open(temp_html_path, 'w', encoding='utf-8') as f:
                f.write(modified_html)
            
            # 创建PDF - 使用Playwright方案
            try:
                # 确保目录存在
                output_dir = os.path.dirname(output_path)
                if output_dir:
                    os.makedirs(output_dir, exist_ok=True)
                
                # 如果文件已存在，尝试删除（可能被占用）
                if os.path.exists(output_path):
                    try:
                        os.remove(output_path)
                        logger.info(f"删除已存在的PDF文件: {output_path}")
                    except PermissionError:
                        # 文件被占用，生成新的文件名
                        import time
                        timestamp = int(time.time())
                        base_name = output_path.replace('.pdf', '')
                        output_path = f"{base_name}_{timestamp}.pdf"
                        logger.warning(f"原文件被占用，使用新文件名: {output_path}")
                
                logger.info(f"📥 转换为PDF格式...")
                
                # 使用新的HTML转PDF转换器
                asyncio.run(convert_html_to_pdf(
                    input_html_path=Path(temp_html_path),
                    output_pdf_path=Path(output_path),
                    media="screen",
                    wait_state="networkidle",
                    page_format="A4"
                ))
                
                logger.info(f"PDF生成成功: {output_path}")
                return output_path
                
            except Exception as e:
                logger.warning(f"[WARN] PDF转换异常: {e}，使用HTML报告")
                # 如果PDF生成失败，返回HTML文件
                html_path = output_path.replace('.pdf', '.html')
                with open(html_path, 'w', encoding='utf-8') as f:
                    f.write(html_content)
                logger.info(f"PDF生成失败，已保存HTML: {html_path}")
                return html_path
            
            finally:
                # 清理临时HTML文件
                if os.path.exists(temp_html_path):
                    try:
                        os.remove(temp_html_path)
                    except:
                        pass
                        
        except Exception as e:
            logger.error(f"HTML到PDF转换失败: {e}")
            # 如果转换失败，返回HTML文件
            if output_path:
                html_path = output_path.replace('.pdf', '.html')
                with open(html_path, 'w', encoding='utf-8') as f:
                    f.write(html_content)
                logger.info(f"PDF转换失败，返回HTML: {html_path}")
                return html_path
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
    try:
        # 创建引擎
        engine = AlgorithmEngineManager()
        
        # 检查状态
        status = engine.get_status()
        logger.info(f"引擎状态: {status}")
        
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
        result = engine.analyze_data(
            test_csv,
            test_patient,
            'COMPREHENSIVE'
        )
        
        if result:
            logger.info("测试成功")
        else:
            logger.error("测试失败")
        
    except Exception as e:
        logger.error(f"测试失败: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_engine()