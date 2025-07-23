"""
SarcNeuro Edge 服务管理器 - 修复版本
解决启动卡住和集成问题
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

# 配置日志
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

class SarcNeuroEdgeServiceFixed:
    """SarcNeuro Edge 服务管理器 - 修复版本"""
    
    def __init__(self, port: int = 8000, service_dir: str = "sarcneuro-edge"):
        self.port = port
        self.service_dir = Path(service_dir)
        self.process = None
        self.base_url = f"http://127.0.0.1:{port}"
        self.is_running = False
        self.startup_timeout = 30  # 减少到30秒
        self.health_check_interval = 30
        self._monitor_thread = None
        self._stop_monitor = False
        self._pause_monitoring = False
        
        # 检查服务目录
        if not self.service_dir.exists():
            logger.warning(f"SarcNeuro Edge 服务目录不存在: {self.service_dir}")
            logger.info("将使用简化版本的分析器")
            self.use_minimal_analyzer = True
        else:
            self.use_minimal_analyzer = False
            
    def start_service(self) -> bool:
        """启动 SarcNeuro Edge 服务"""
        try:
            if self.is_running:
                logger.info("服务已在运行中")
                return True
                
            # 如果使用简化分析器
            if self.use_minimal_analyzer:
                return self._start_minimal_analyzer()
                
            logger.info(f"正在启动 SarcNeuro Edge 服务 (端口 {self.port})...")
            
            # 检查端口是否被占用
            if self._is_port_in_use():
                logger.warning(f"端口 {self.port} 已被占用，尝试连接现有服务...")
                if self._check_service_health():
                    self.is_running = True
                    self._start_monitor()
                    return True
                else:
                    logger.error("现有服务无响应，尝试使用简化分析器")
                    return self._start_minimal_analyzer()
            
            # 准备启动命令
            return self._start_full_service()
            
        except Exception as e:
            logger.error(f"启动服务时发生异常: {e}")
            logger.info("尝试使用简化分析器")
            return self._start_minimal_analyzer()
    
    def _start_minimal_analyzer(self) -> bool:
        """启动简化分析器"""
        try:
            logger.info("启动简化版SarcNeuro分析器...")
            
            # 导入简化分析器
            try:
                from minimal_sarcneuro_analyzer import get_minimal_analyzer
                self.minimal_analyzer = get_minimal_analyzer()
                self.is_running = True
                self.use_minimal_analyzer = True
                logger.info("✅ 简化版SarcNeuro分析器启动成功！")
                return True
            except ImportError:
                logger.error("无法导入简化分析器")
                return False
                
        except Exception as e:
            logger.error(f"简化分析器启动失败: {e}")
            return False
    
    def _start_full_service(self) -> bool:
        """启动完整服务"""
        try:
            # 准备启动命令
            python_exe = sys.executable
            cmd = [python_exe, "-m", "app.main"]
            
            # 设置环境变量
            env = os.environ.copy()
            env["PYTHONPATH"] = str(self.service_dir)
            env["PYTHONUNBUFFERED"] = "1"  # 确保输出不被缓冲
            
            # 启动子进程
            startupinfo = None
            creation_flags = 0
            if sys.platform.startswith('win'):
                startupinfo = subprocess.STARTUPINFO()
                startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
                startupinfo.wShowWindow = subprocess.SW_HIDE
                creation_flags = subprocess.CREATE_NO_WINDOW
            
            logger.info(f"执行命令: {' '.join(cmd)}")
            logger.info(f"工作目录: {self.service_dir}")
            
            self.process = subprocess.Popen(
                cmd,
                cwd=str(self.service_dir),
                env=env,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,  # 合并stderr到stdout
                startupinfo=startupinfo,
                creationflags=creation_flags,
                text=True,
                bufsize=1,  # 行缓冲
                universal_newlines=True
            )
            
            # 等待服务启动
            return self._wait_for_service_startup()
            
        except Exception as e:
            logger.error(f"启动完整服务失败: {e}")
            return False
    
    def _wait_for_service_startup(self) -> bool:
        """等待服务启动"""
        logger.info("等待服务启动...")
        start_time = time.time()
        check_count = 0
        
        # 创建线程读取输出
        output_thread = threading.Thread(
            target=self._read_process_output, 
            daemon=True
        )
        output_thread.start()
        
        while time.time() - start_time < self.startup_timeout:
            check_count += 1
            elapsed = time.time() - start_time
            
            # 检查进程是否还在运行
            if self.process.poll() is not None:
                logger.error(f"服务启动失败，进程已退出，返回码: {self.process.returncode}")
                return False
            
            # 每5秒打印一次进度
            if check_count % 3 == 0:  # 每6秒打印一次
                logger.info(f"等待服务响应... ({elapsed:.1f}s/{self.startup_timeout}s)")
            
            # 检查服务健康状态
            if self._check_service_health():
                logger.info("SarcNeuro Edge 服务启动成功!")
                self.is_running = True
                self._start_monitor()
                return True
            
            time.sleep(2)
        
        # 启动超时
        logger.error(f"服务启动超时 ({self.startup_timeout}秒)")
        logger.info("正在停止进程...")
        self.stop_service()
        return False
    
    def _read_process_output(self):
        """读取进程输出"""
        try:
            while self.process and self.process.poll() is None:
                line = self.process.stdout.readline()
                if line:
                    logger.info(f"[服务输出] {line.strip()}")
                else:
                    time.sleep(0.1)
        except Exception as e:
            logger.error(f"读取进程输出失败: {e}")
    
    def _is_port_in_use(self) -> bool:
        """检查端口是否被占用"""
        try:
            import socket
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                result = s.connect_ex(('127.0.0.1', self.port))
                return result == 0
        except Exception:
            return False
    
    def _check_service_health(self) -> bool:
        """检查服务健康状态"""
        try:
            response = requests.get(f"{self.base_url}/health", timeout=5)
            return response.status_code == 200
        except:
            return False
    
    def _start_monitor(self):
        """启动监控线程"""
        if not self._monitor_thread or not self._monitor_thread.is_alive():
            self._stop_monitor = False
            self._monitor_thread = threading.Thread(target=self._monitor_service, daemon=True)
            self._monitor_thread.start()
    
    def _monitor_service(self):
        """监控服务状态"""
        while not self._stop_monitor and self.is_running:
            try:
                if not self._pause_monitoring:
                    if not self._check_service_health():
                        logger.warning("服务健康检查失败")
                        if not self.use_minimal_analyzer:
                            self.is_running = False
                            break
                time.sleep(self.health_check_interval)
            except Exception as e:
                logger.error(f"监控服务异常: {e}")
                time.sleep(5)
    
    def stop_service(self):
        """停止 SarcNeuro Edge 服务"""
        try:
            logger.info("正在停止 SarcNeuro Edge 服务...")
            
            # 停止监控线程
            self._stop_monitor = True
            
            # 停止进程
            if self.process:
                try:
                    # 尝试优雅关闭
                    self.process.terminate()
                    
                    # 等待最多5秒
                    try:
                        self.process.wait(timeout=5)
                    except subprocess.TimeoutExpired:
                        # 强制杀死进程
                        logger.warning("进程未响应，强制终止")
                        self.process.kill()
                        self.process.wait()
                        
                except Exception as e:
                    logger.error(f"停止进程时出错: {e}")
                finally:
                    self.process = None
            
            self.is_running = False
            logger.info("SarcNeuro Edge 服务已停止")
            
        except Exception as e:
            logger.error(f"停止服务时发生异常: {e}")
    
    def analyze_data(
        self, 
        csv_data: str, 
        patient_info: Dict[str, Any],
        test_type: str = "COMPREHENSIVE"
    ) -> Optional[Dict[str, Any]]:
        """发送数据进行分析"""
        if not self.is_running:
            logger.error("服务未运行，无法进行分析")
            return None
        
        try:
            logger.info(f"发送数据分析请求 - 患者: {patient_info.get('name', '未知')}")
            
            # 如果使用简化分析器
            if self.use_minimal_analyzer:
                return self._analyze_with_minimal_analyzer(csv_data, patient_info)
            
            # 使用完整服务进行分析
            return self._analyze_with_full_service(csv_data, patient_info, test_type)
            
        except Exception as e:
            logger.error(f"分析过程出错: {e}")
            return None
    
    def _analyze_with_minimal_analyzer(self, csv_data: str, patient_info: Dict[str, Any]) -> Dict[str, Any]:
        """使用简化分析器进行分析"""
        try:
            logger.info("使用简化分析器进行分析...")
            return self.minimal_analyzer.analyze_pressure_data(csv_data, patient_info)
        except Exception as e:
            logger.error(f"简化分析器分析失败: {e}")
            return {
                "success": False,
                "message": f"简化分析器分析失败: {e}",
                "data": None
            }
    
    def _analyze_with_full_service(self, csv_data: str, patient_info: Dict[str, Any], test_type: str) -> Dict[str, Any]:
        """使用完整服务进行分析"""
        try:
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
                timeout=180,  # 3分钟超时
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
        finally:
            # 恢复监控
            self._pause_monitoring = False
            logger.debug("已恢复服务监控")
    
    def get_service_status(self) -> Dict[str, Any]:
        """获取服务状态"""
        status = {
            "is_running": self.is_running,
            "port": self.port,
            "base_url": self.base_url,
            "process_id": self.process.pid if self.process else None,
            "use_minimal_analyzer": self.use_minimal_analyzer
        }
        
        if self.is_running and not self.use_minimal_analyzer:
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
        
        if self.use_minimal_analyzer:
            return True  # 简化分析器总是可用
        
        try:
            response = requests.get(f"{self.base_url}/health", timeout=5)
            return response.status_code == 200
        except:
            return False

# 全局服务实例
_service_instance = None

def get_sarcneuro_service_fixed(port: int = 8000) -> SarcNeuroEdgeServiceFixed:
    """获取修复版全局服务实例"""
    global _service_instance
    
    if _service_instance is None:
        _service_instance = SarcNeuroEdgeServiceFixed(port=port)
    
    return _service_instance

def test_fixed_service():
    """测试修复版服务功能"""
    print("测试修复版 SarcNeuro Edge 服务...")
    
    service = SarcNeuroEdgeServiceFixed(port=8000)  # 使用8000端口
    
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
    test_fixed_service() 