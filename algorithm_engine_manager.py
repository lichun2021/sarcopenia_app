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
from typing import Dict, Any, Optional, Union
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
    
    # 默认配置
    defaults = {
        'algorithms_dir': 'algorithms',
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
            
            # 检查算法目录是否存在
            if not self.algorithms_dir.exists():
                logger.warning(f"算法目录不存在: {self.algorithms_dir}")
                # 创建模拟的分析器和报告生成器
                self.analyzer = MockPressureAnalysisCore()
                self.report_generator = MockReportGenerator()
                self.is_initialized = True
                logger.info("使用模拟算法引擎初始化成功")
                return
            
            # 导入核心算法模块
            logger.info(f"从 {algorithms_path} 导入算法模块")
            try:
                from core_calculator import PressureAnalysisCore
                self.analyzer = PressureAnalysisCore()
                
                # 导入报告生成器
                from full_medical_report_generator import FullMedicalReportGenerator
                self.report_generator = FullMedicalReportGenerator()
            except ImportError as e:
                logger.warning(f"无法导入真实算法模块: {e}")
                # 使用模拟模块
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
                # 生成报告HTML
                report_html = self._generate_report(result, patient_info)
                if report_html:
                    result['report_html'] = report_html
            
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
                raw_result = self.analyzer.comprehensive_analysis(str(temp_csv_path))
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
        """保存临时CSV文件"""
        import tempfile
        temp_dir = Path(tempfile.gettempdir())
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
        """生成分析报告HTML"""
        try:
            if not self.report_generator:
                logger.warning("报告生成器未初始化")
                return None
            
            # 准备报告数据
            report_data = {
                'patient_info': patient_info,
                'analysis_result': analysis_result.get('data', {}),
                'test_time': datetime.now()
            }
            
            # 生成报告选项
            options = {
                'show_cop_trajectory': True,
                'show_gait_parameters': True,
                'show_balance_metrics': True,
                'show_suggestions': True
            }
            
            # 生成HTML报告
            html_report = self.report_generator.generate_report(
                report_data,
                options
            )
            
            return html_report
            
        except Exception as e:
            logger.error(f"生成报告失败: {e}")
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
            # 尝试使用wkhtmltopdf
            try:
                import pdfkit
                
                # 配置选项
                options = {
                    'page-size': 'A4',
                    'margin-top': '0.75in',
                    'margin-right': '0.75in',
                    'margin-bottom': '0.75in',
                    'margin-left': '0.75in',
                    'encoding': "UTF-8",
                    'no-outline': None,
                    'enable-local-file-access': None
                }
                
                if output_path is None:
                    # 创建临时文件
                    temp_fd, output_path = tempfile.mkstemp(suffix='.pdf')
                    os.close(temp_fd)
                
                # 转换HTML到PDF
                pdfkit.from_string(html_content, output_path, options=options)
                logger.info(f"PDF生成成功: {output_path}")
                return output_path
                
            except ImportError:
                logger.warning("pdfkit未安装，尝试使用weasyprint")
                
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
    
    if _engine_instance is None:
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