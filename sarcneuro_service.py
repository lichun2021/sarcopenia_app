"""
SarcNeuro Edge 服务管理器
负责启动、管理和与 SarcNeuro Edge 独立服务通信
"""
import subprocess
import requests
import time
import os
import sys
import threading
import logging
import json
import signal
from pathlib import Path
from typing import Dict, Any, Optional, List
from datetime import datetime

# 配置文件读取
import configparser
import os

def load_config():
    """加载配置文件"""
    config = configparser.ConfigParser()
    
    # 默认配置
    defaults = {
        'enable_debug': 'false',
        'show_console': 'false', 
        'verbose_logging': 'false',
        'save_logs': 'true',
        'reports_dir': 'reports',
        'logs_dir': 'logs',
        'service_port': '8000',
        'startup_timeout': '60'
    }
    
    # 尝试读取配置文件
    config_file = 'config.ini'
    if os.path.exists(config_file):
        config.read(config_file, encoding='utf-8')
    
    # 获取配置值，如果不存在则使用默认值
    cfg = {}
    for key, default_value in defaults.items():
        if key.startswith('enable_') or key.startswith('show_') or key.startswith('verbose_') or key.startswith('save_'):
            cfg[key] = config.getboolean('DEBUG', key.replace('_', '_'), fallback=default_value.lower() == 'true')
        elif key.endswith('_port') or key.endswith('_timeout'):
            cfg[key] = config.getint('SARCNEURO' if 'service_' in key or 'startup_' in key else 'PATHS', 
                                   key, fallback=int(default_value))
        else:
            cfg[key] = config.get('PATHS', key, fallback=default_value)
    
    return cfg

# 加载配置
app_config = load_config()

# 配置日志
if app_config['save_logs']:
    log_dir = app_config['logs_dir']
    os.makedirs(log_dir, exist_ok=True)
    log_file = os.path.join(log_dir, "sarcneuro_debug.log")
    
    handlers = [logging.FileHandler(log_file, encoding='utf-8')]
    if app_config['verbose_logging']:
        handlers.append(logging.StreamHandler())
    
    logging.basicConfig(
        level=logging.DEBUG if app_config['enable_debug'] else logging.INFO,
        format='%(asctime)s [%(levelname)s] %(message)s',
        handlers=handlers
    )
else:
    logging.basicConfig(level=logging.CRITICAL)  # 基本禁用日志

logger = logging.getLogger(__name__)

# 可配置的日志函数
def force_log(message):
    """可配置的日志记录 - 使用统一日志系统"""
    from logger_utils import log_info
    log_info(message, "SERVICE")

class SarcNeuroEdgeService:
    """SarcNeuro Edge 服务管理器"""
    
    def __init__(self, port: int = None, service_dir: str = "sarcneuro-edge"):
        self.port = port or app_config['service_port']
        
        # 处理打包后的路径问题
        if getattr(sys, 'frozen', False):
            # 打包后的环境
            base_path = Path(sys._MEIPASS)
            self.service_dir = base_path / service_dir
            # 在打包环境中，需要设置日志和数据目录到可写路径
            self.data_dir = Path.cwd() / "sarcneuro_data"
            self.data_dir.mkdir(exist_ok=True)
        else:
            # 开发环境
            self.service_dir = Path(service_dir)
            self.data_dir = self.service_dir
            
        self.process = None
        self.base_url = f"http://127.0.0.1:{self.port}"
        self.is_running = False
        self.startup_timeout = app_config['startup_timeout']
        self.health_check_interval = 30  # 30秒健康检查间隔
        self._monitor_thread = None
        self._stop_monitor = False
        self._pause_monitoring = False  # 暂停监控标志
        
        # 检查服务目录
        if not self.service_dir.exists():
            raise FileNotFoundError(f"SarcNeuro Edge 服务目录不存在: {self.service_dir}")
        
        # 检查关键文件
        standalone_script = self.service_dir / "standalone_upload.py"
        if not standalone_script.exists():
            raise FileNotFoundError(f"standalone_upload.py 不存在: {standalone_script}")
            
    def start_service(self) -> bool:
        """启动 SarcNeuro Edge 服务"""
        try:
            # 强制打印调试信息
            force_log(f"start_service called, is_running={self.is_running}")
            
            # 先进行健康检查，看服务是否已经在运行
            force_log(f"先检查服务健康状态...")
            if self._check_service_health():
                force_log(f"服务已在运行且健康，直接使用现有服务")
                self.is_running = True
                self._start_monitor()
                return True
            
            # 如果内部标记为运行中但健康检查失败，重置状态
            if self.is_running:
                force_log("服务标记为运行但健康检查失败，重置状态")
                self.is_running = False
                
            force_log(f"正在启动 SarcNeuro Edge 服务 (端口 {self.port})...")
            
            # 检查端口是否被占用（但服务不健康）
            if self._is_port_in_use():
                logger.warning(f"端口 {self.port} 已被占用但服务不健康")
                return False
            
            # 启动前检查
            force_log(f"服务目录: {self.service_dir}")
            force_log(f"数据目录: {getattr(self, 'data_dir', 'N/A')}")
            force_log(f"Python可执行文件: {sys.executable}")
            force_log(f"当前工作目录: {os.getcwd()}")
            force_log(f"是否打包环境: {getattr(sys, 'frozen', False)}")
            
            # 对于打包环境，尝试直接在主进程中启动服务
            if getattr(sys, 'frozen', False):
                force_log(f"打包环境：尝试在主进程中启动服务，端口: {self.port}")
                
                # 检查是否已有线程在运行
                if hasattr(self, 'process') and self.process and hasattr(self.process, 'is_alive') and self.process.is_alive():
                    force_log("服务线程已在运行，跳过重复启动")
                    return False
                
                try:
                    # 设置环境变量
                    os.environ["SARCNEURO_DATA_DIR"] = str(self.data_dir)
                    force_log(f"设置环境变量 SARCNEURO_DATA_DIR = {self.data_dir}")
                    
                    # 添加sarcneuro-edge到Python路径
                    if str(self.service_dir) not in sys.path:
                        sys.path.insert(0, str(self.service_dir))
                    
                    force_log(f"导入路径已添加: {self.service_dir}")
                    
                    # 在线程中启动FastAPI服务
                    import threading
                    def run_fastapi():
                        try:
                            force_log("开始导入standalone_upload...")
                            from standalone_upload import app
                            force_log("成功导入app")
                            
                            import uvicorn
                            force_log(f"启动uvicorn服务器在端口 {self.port}")
                            
                            # 在打包环境中禁用uvicorn的日志配置
                            if getattr(sys, 'frozen', False):
                                # 完全禁用uvicorn日志配置
                                uvicorn.run(
                                    app, 
                                    host="127.0.0.1", 
                                    port=self.port, 
                                    log_config=None,  # 禁用日志配置
                                    access_log=False,  # 禁用访问日志
                                    use_colors=False   # 禁用颜色
                                )
                            else:
                                # 开发环境正常启动
                                uvicorn.run(app, host="127.0.0.1", port=self.port, log_level="error")
                        except Exception as e:
                            force_log(f"FastAPI启动失败: {e}")
                            import traceback
                            error_trace = traceback.format_exc()
                            force_log(f"错误堆栈: {error_trace}")
                    
                    server_thread = threading.Thread(target=run_fastapi, daemon=True)
                    server_thread.start()
                    self.process = server_thread
                    force_log("FastAPI服务线程已启动")
                    
                except Exception as e:
                    force_log(f"主进程启动失败: {e}")
                    return False
                
            else:
                # 开发环境使用子进程
                logger.info(f"开发环境：使用子进程启动服务，端口: {self.port}")
                python_exe = sys.executable
                cmd = [python_exe, "standalone_upload.py"]
                
                # 设置环境变量
                env = os.environ.copy()
                env["PYTHONPATH"] = str(self.service_dir)
                
                # 启动子进程
                startupinfo = None
                if sys.platform.startswith('win'):
                    startupinfo = subprocess.STARTUPINFO()
                    startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
                    startupinfo.wShowWindow = subprocess.SW_HIDE
                
                self.process = subprocess.Popen(
                    cmd,
                    cwd=str(self.service_dir),
                    env=env,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    startupinfo=startupinfo,
                    creationflags=subprocess.CREATE_NO_WINDOW if sys.platform.startswith('win') else 0
                )
            
            # 等待服务启动
            logger.info("等待服务启动...")
            start_time = time.time()
            check_count = 0
            
            while time.time() - start_time < self.startup_timeout:
                check_count += 1
                elapsed = time.time() - start_time
                
                # 检查进程是否还在运行
                if getattr(sys, 'frozen', False):
                    # 打包环境检查线程状态
                    if hasattr(self.process, 'is_alive') and not self.process.is_alive():
                        logger.error("服务线程已退出")
                        return False
                else:
                    # 开发环境检查进程状态
                    if self.process.poll() is not None:
                        stdout, stderr = self.process.communicate()
                        exit_code = self.process.returncode
                        logger.error(f"服务启动失败，进程已退出 (退出码: {exit_code})")
                        logger.error(f"使用的命令: {' '.join(cmd)}")
                        logger.error(f"工作目录: {str(self.service_dir)}")
                        logger.error(f"环境变量 PYTHONPATH: {env.get('PYTHONPATH')}")
                        if stdout:
                            logger.info(f"标准输出: {stdout.decode('utf-8', errors='ignore')}")
                        if stderr:
                            logger.error(f"错误输出: {stderr.decode('utf-8', errors='ignore')}")
                        return False
                
                # 每10秒打印一次进度
                if check_count % 5 == 0:
                    logger.info(f"等待服务响应... ({elapsed:.1f}s/{self.startup_timeout}s)")
                
                # 检查服务健康状态
                if self._check_service_health():
                    logger.info("SarcNeuro Edge 服务启动成功!")
                    self.is_running = True
                    self._start_monitor()
                    return True
                
                time.sleep(2)
            
            # 启动超时，获取进程输出用于调试
            logger.error(f"服务启动超时 ({self.startup_timeout}秒)")
            if self.process and self.process.poll() is None:
                logger.info("进程仍在运行，尝试获取输出...")
                # 尝试获取部分输出（非阻塞）
                try:
                    if sys.platform != 'win32':
                        import select
                        ready, _, _ = select.select([self.process.stdout], [], [], 0.1)
                        if ready:
                            output = self.process.stdout.read(1024)
                            if output:
                                logger.info(f"进程输出: {output.decode('utf-8', errors='ignore')}")
                except:
                    pass
            
            self.stop_service()
            return False
            
        except Exception as e:
            force_log(f"启动服务时发生异常: {e}")
            import traceback
            force_log(f"异常堆栈: {traceback.format_exc()}")
            return False
    
    def stop_service(self):
        """停止 SarcNeuro Edge 服务"""
        try:
            logger.info("正在停止 SarcNeuro Edge 服务...")
            
            # 停止监控线程
            self._stop_monitor = True
            if self._monitor_thread and self._monitor_thread.is_alive():
                self._monitor_thread.join(timeout=5)
            
            # 尝试优雅关闭
            try:
                response = requests.post(f"{self.base_url}/system/shutdown", timeout=5)
                if response.status_code == 200:
                    logger.info("服务已优雅关闭")
                    time.sleep(2)
            except:
                pass
            
            # 强制终止进程
            if self.process and self.process.poll() is None:
                if sys.platform.startswith('win'):
                    # Windows
                    self.process.terminate()
                else:
                    # Unix/Linux
                    self.process.send_signal(signal.SIGTERM)
                
                # 等待进程退出
                try:
                    self.process.wait(timeout=10)
                except subprocess.TimeoutExpired:
                    # 强制杀死
                    self.process.kill()
                    self.process.wait()
                
                logger.info("服务进程已终止")
            
            self.is_running = False
            self.process = None
            
        except Exception as e:
            logger.error(f"停止服务时发生异常: {e}")
    
    def _is_port_in_use(self) -> bool:
        """检查端口是否被占用"""
        try:
            response = requests.get(f"{self.base_url}/health", timeout=2)
            return response.status_code == 200
        except:
            return False
    
    def _check_service_health(self) -> bool:
        """检查服务健康状态"""
        try:
            logger.debug(f"检查服务健康状态: {self.base_url}/health")
            # 缩短健康检查的超时时间到5秒
            response = requests.get(f"{self.base_url}/health", timeout=5)
            logger.debug(f"健康检查响应: 状态码={response.status_code}")
            
            if response.status_code == 200:
                data = response.json()
                logger.debug(f"健康检查数据: {data}")
                is_healthy = data.get("status") == "healthy"
                if not is_healthy:
                    logger.warning(f"服务状态不健康: {data.get('status')}")
                return is_healthy
            else:
                logger.warning(f"健康检查返回错误状态码: {response.status_code}")
                return False
                
        except requests.exceptions.ConnectionError as e:
            logger.debug(f"连接错误: {e}")
            return False
        except requests.exceptions.Timeout as e:
            logger.debug(f"请求超时: {e}")
            return False
        except Exception as e:
            logger.debug(f"健康检查失败: {e}")
            return False
    
    def _start_monitor(self):
        """启动服务监控线程"""
        if self._monitor_thread and self._monitor_thread.is_alive():
            return
        
        self._stop_monitor = False
        self._monitor_thread = threading.Thread(target=self._monitor_service, daemon=True)
        self._monitor_thread.start()
    
    def _monitor_service(self):
        """监控服务状态"""
        consecutive_failures = 0
        max_failures = 5  # 增加到5次失败才标记为不可用
        
        while not self._stop_monitor and self.is_running:
            try:
                time.sleep(self.health_check_interval)
                
                # 如果监控被暂停，跳过健康检查
                if self._pause_monitoring:
                    logger.debug("监控已暂停，跳过健康检查")
                    continue
                
                if self._check_service_health():
                    consecutive_failures = 0
                else:
                    consecutive_failures += 1
                    logger.warning(f"服务健康检查失败 ({consecutive_failures}/{max_failures})")
                    
                    if consecutive_failures >= max_failures:
                        logger.error("服务连续健康检查失败，标记为不可用")
                        self.is_running = False
                        break
                        
            except Exception as e:
                logger.error(f"监控服务时出错: {e}")
                consecutive_failures += 1
    
    def analyze_data(
        self, 
        csv_data: str, 
        patient_info: Dict[str, Any],
        test_type: str = "COMPREHENSIVE"
    ) -> Optional[Dict[str, Any]]:
        """
        发送数据进行分析
        
        Args:
            csv_data: CSV格式的压力数据
            patient_info: 患者信息字典
            test_type: 测试类型
            
        Returns:
            分析结果字典或None
        """
        if not self.is_running:
            logger.error("服务未运行，无法进行分析")
            return None
        
        try:
            logger.info(f"发送数据分析请求 - 患者: {patient_info.get('name', '未知')}")
            
            # 暂停监控，避免在AI分析期间进行健康检查
            self._pause_monitoring = True
            logger.debug("已暂停服务监控，开始AI分析")
            
            # 构建请求数据
            request_data = {
                "patient_info": patient_info,
                "test_type": test_type,
                "test_mode": "UPLOAD",
                "csv_data": csv_data
            }
            
            # 发送请求
            response = requests.post(
                f"{self.base_url}/api/analysis/analyze",
                json=request_data,
                timeout=180,  # 增加到3分钟超时
                headers={"Content-Type": "application/json"}
            )
            
            if response.status_code == 200:
                result = response.json()
                logger.info(f"分析完成 - 评分: {result.get('data', {}).get('overall_score', 'N/A')}")
                return result
            else:
                logger.error(f"分析请求失败: HTTP {response.status_code}")
                logger.error(f"响应内容: {response.text}")
                return None
                
        except requests.exceptions.Timeout:
            logger.error("分析请求超时")
            return None
        except requests.exceptions.RequestException as e:
            logger.error(f"分析请求异常: {e}")
            return None
        except Exception as e:
            logger.error(f"分析过程出错: {e}")
            return None
        finally:
            # 恢复监控
            self._pause_monitoring = False
            logger.debug("已恢复服务监控")
    
    def get_analysis_result(self, analysis_id: int) -> Optional[Dict[str, Any]]:
        """获取分析结果详情"""
        if not self.is_running:
            return None
        
        try:
            response = requests.get(
                f"{self.base_url}/api/analysis/results/{analysis_id}",
                timeout=10
            )
            
            if response.status_code == 200:
                return response.json()
            else:
                logger.error(f"获取分析结果失败: HTTP {response.status_code}")
                return None
                
        except Exception as e:
            logger.error(f"获取分析结果出错: {e}")
            return None
    
    def get_service_status(self) -> Dict[str, Any]:
        """获取服务状态"""
        status = {
            "is_running": self.is_running,
            "port": self.port,
            "base_url": self.base_url,
            "process_id": self.process.pid if self.process else None
        }
        
        if self.is_running:
            try:
                response = requests.get(f"{self.base_url}/system/status", timeout=5)
                if response.status_code == 200:
                    status["service_info"] = response.json()
            except:
                pass
        
        return status
    
    def test_connection(self) -> bool:
        """测试服务连接"""
        if not self.is_running:
            return False
        
        try:
            response = requests.get(f"{self.base_url}/health", timeout=5)
            return response.status_code == 200
        except:
            return False
    
    def __enter__(self):
        """上下文管理器入口"""
        self.start_service()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """上下文管理器退出"""
        self.stop_service()

# 全局服务实例
_service_instance = None
_service_started = False  # 添加标记，表示是否已尝试启动服务

def get_sarcneuro_service(port: int = 8000) -> SarcNeuroEdgeService:
    """获取全局服务实例"""
    global _service_instance, _service_started
    
    if _service_instance is None:
        _service_instance = SarcNeuroEdgeService(port=port)
    
    # 如果服务实例存在但未启动过，尝试启动
    if not _service_started and not _service_instance.is_running:
        logger.info("首次获取服务实例，尝试启动服务...")
        _service_started = _service_instance.start_service()
    
    return _service_instance

def test_service():
    """测试服务功能"""
    print("测试 SarcNeuro Edge 服务...")
    
    service = SarcNeuroEdgeService(port=8001)
    
    try:
        # 启动服务
        print("启动服务...")
        if service.start_service():
            print("✅ 服务启动成功")
            
            # 测试连接
            print("测试连接...")
            if service.test_connection():
                print("✅ 服务连接正常")
                
                # 获取状态
                status = service.get_service_status()
                print(f"✅ 服务状态: {json.dumps(status, indent=2, ensure_ascii=False)}")
                
            else:
                print("❌ 服务连接失败")
        else:
            print("❌ 服务启动失败")
            
    except Exception as e:
        print(f"❌ 测试过程出错: {e}")
        
    finally:
        # 停止服务
        print("停止服务...")
        service.stop_service()
        print("✅ 服务已停止")

if __name__ == "__main__":
    test_service()