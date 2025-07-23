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

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class SarcNeuroEdgeService:
    """SarcNeuro Edge 服务管理器"""
    
    def __init__(self, port: int = 8001, service_dir: str = "sarcneuro-edge"):
        self.port = port
        self.service_dir = Path(service_dir)
        self.process = None
        self.base_url = f"http://127.0.0.1:{port}"
        self.is_running = False
        self.startup_timeout = 60  # 60秒启动超时
        self.health_check_interval = 30  # 30秒健康检查间隔
        self._monitor_thread = None
        self._stop_monitor = False
        
        # 检查服务目录
        if not self.service_dir.exists():
            raise FileNotFoundError(f"SarcNeuro Edge 服务目录不存在: {self.service_dir}")
            
    def start_service(self) -> bool:
        """启动 SarcNeuro Edge 服务"""
        try:
            if self.is_running:
                logger.info("服务已在运行中")
                return True
                
            logger.info(f"正在启动 SarcNeuro Edge 服务 (端口 {self.port})...")
            
            # 检查端口是否被占用
            if self._is_port_in_use():
                logger.warning(f"端口 {self.port} 已被占用，尝试连接现有服务...")
                if self._check_service_health():
                    self.is_running = True
                    self._start_monitor()
                    return True
                else:
                    logger.error("现有服务无响应")
                    return False
            
            # 准备启动命令
            python_exe = sys.executable
            cmd = [python_exe, "-m", "app.main"]
            
            # 设置环境变量
            env = os.environ.copy()
            env["PYTHONPATH"] = str(self.service_dir)
            env["EDGE_PORT"] = str(self.port)
            env["EDGE_HOST"] = "127.0.0.1"
            
            # 启动子进程
            startupinfo = None
            if sys.platform.startswith('win'):
                # Windows下隐藏控制台窗口
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
            
            while time.time() - start_time < self.startup_timeout:
                if self.process.poll() is not None:
                    # 进程已退出
                    stdout, stderr = self.process.communicate()
                    logger.error(f"服务启动失败，进程已退出")
                    if stderr:
                        logger.error(f"错误输出: {stderr.decode('utf-8', errors='ignore')}")
                    return False
                
                if self._check_service_health():
                    logger.info("SarcNeuro Edge 服务启动成功!")
                    self.is_running = True
                    self._start_monitor()
                    return True
                
                time.sleep(2)
            
            # 启动超时
            logger.error(f"服务启动超时 ({self.startup_timeout}秒)")
            self.stop_service()
            return False
            
        except Exception as e:
            logger.error(f"启动服务时发生异常: {e}")
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
            response = requests.get(f"{self.base_url}/health", timeout=5)
            if response.status_code == 200:
                data = response.json()
                return data.get("status") == "healthy"
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
        max_failures = 3
        
        while not self._stop_monitor and self.is_running:
            try:
                time.sleep(self.health_check_interval)
                
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
                timeout=120,  # 2分钟超时
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

def get_sarcneuro_service(port: int = 8001) -> SarcNeuroEdgeService:
    """获取全局服务实例"""
    global _service_instance
    
    if _service_instance is None:
        _service_instance = SarcNeuroEdgeService(port=port)
    
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