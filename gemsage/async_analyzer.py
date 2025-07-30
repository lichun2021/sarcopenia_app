#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
异步算法处理服务
基于Redis消息队列的独立算法服务
"""

import redis
import json
import uuid
import time
import logging
from typing import Dict, Any, Optional
from pathlib import Path
import traceback
import os
from core_calculator import PressureAnalysisCore

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class AsyncAlgorithmService:
    """异步算法服务"""
    
    def __init__(self, redis_host='localhost', redis_port=6379, redis_db=0):
        """初始化服务"""
        self.redis_client = redis.Redis(
            host=redis_host, 
            port=redis_port, 
            db=redis_db,
            decode_responses=True
        )
        self.analyzer = PressureAnalysisCore()
        self.service_name = 'pressure-analysis-service'
        self.task_queue = 'analysis_tasks'
        self.result_prefix = 'result:'
        self.running = False
        
        logger.info(f"初始化 {self.service_name}")
    
    def submit_task(self, task_data: Dict[str, Any], priority: int = 0) -> str:
        """提交分析任务"""
        task_id = str(uuid.uuid4())
        
        task = {
            'id': task_id,
            'type': task_data.get('type', 'comprehensive'),
            'data': task_data,
            'submitted_at': time.time(),
            'priority': priority,
            'service': self.service_name
        }
        
        # 根据优先级选择队列操作
        if priority > 0:
            self.redis_client.lpush(self.task_queue, json.dumps(task))
        else:
            self.redis_client.rpush(self.task_queue, json.dumps(task))
        
        logger.info(f"任务已提交: {task_id}")
        return task_id
    
    def get_result(self, task_id: str, timeout: int = 300) -> Optional[Dict]:
        """获取分析结果（带超时）"""
        result_key = f"{self.result_prefix}{task_id}"
        
        # 轮询检查结果
        start_time = time.time()
        while time.time() - start_time < timeout:
            result_data = self.redis_client.get(result_key)
            if result_data:
                try:
                    result = json.loads(result_data)
                    logger.info(f"结果已获取: {task_id}")
                    return result
                except json.JSONDecodeError:
                    logger.error(f"结果解析失败: {task_id}")
                    return None
            
            time.sleep(0.5)  # 500ms轮询间隔
        
        logger.warning(f"任务超时: {task_id}")
        return None
    
    def process_task(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """处理单个任务"""
        task_id = task['id']
        task_type = task['type']
        task_data = task['data']
        
        logger.info(f"开始处理任务: {task_id} (类型: {task_type})")
        
        try:
            start_time = time.time()
            
            if task_type == 'comprehensive':
                # 综合分析
                csv_path = task_data.get('csv_path')
                if not csv_path or not Path(csv_path).exists():
                    raise FileNotFoundError(f"CSV文件不存在: {csv_path}")
                
                result = self.analyzer.comprehensive_analysis(csv_path)
                
            elif task_type == 'gait_only':
                # 仅步态分析
                csv_path = task_data.get('csv_path')
                pressure_data = self.analyzer.parse_csv_data(
                    open(csv_path).read()
                )
                gait_events = self.analyzer.detect_gait_events([pressure_data])
                result = self.analyzer.calculate_step_metrics(gait_events)
                
            elif task_type == 'balance_only':
                # 仅平衡分析
                csv_path = task_data.get('csv_path')
                pressure_data = self.analyzer.parse_csv_data(
                    open(csv_path).read()
                )
                result = self.analyzer.analyze_balance([pressure_data])
                
            else:
                raise ValueError(f"不支持的任务类型: {task_type}")
            
            processing_time = time.time() - start_time
            
            # 构建响应
            response = {
                'task_id': task_id,
                'status': 'success',
                'result': result,
                'processing_time': processing_time,
                'processed_at': time.time(),
                'service': self.service_name
            }
            
            logger.info(f"任务完成: {task_id} (耗时: {processing_time:.2f}s)")
            return response
            
        except Exception as e:
            error_msg = str(e)
            error_trace = traceback.format_exc()
            
            logger.error(f"任务失败: {task_id} - {error_msg}")
            logger.debug(f"错误详情: {error_trace}")
            
            return {
                'task_id': task_id,
                'status': 'error',
                'error': error_msg,
                'error_trace': error_trace,
                'processed_at': time.time(),
                'service': self.service_name
            }
    
    def run_worker(self):
        """运行工作进程"""
        self.running = True
        logger.info(f"{self.service_name} 工作进程启动")
        
        while self.running:
            try:
                # 阻塞式获取任务（超时5秒）
                task_data = self.redis_client.blpop(self.task_queue, timeout=5)
                
                if task_data:
                    _, task_json = task_data
                    task = json.loads(task_json)
                    
                    # 处理任务
                    result = self.process_task(task)
                    
                    # 存储结果（1小时过期）
                    result_key = f"{self.result_prefix}{task['id']}"
                    self.redis_client.setex(
                        result_key, 
                        3600, 
                        json.dumps(result, default=str)
                    )
                    
                    # 可选：发送完成通知
                    callback_url = task.get('callback_url')
                    if callback_url:
                        self.send_callback(callback_url, result)
                
            except KeyboardInterrupt:
                logger.info("收到中断信号，正在停止...")
                break
            except Exception as e:
                logger.error(f"工作进程错误: {e}")
                time.sleep(1)  # 错误后短暂休息
        
        self.running = False
        logger.info(f"{self.service_name} 工作进程已停止")
    
    def send_callback(self, callback_url: str, result: Dict):
        """发送回调通知（可选功能）"""
        try:
            import requests
            response = requests.post(
                callback_url, 
                json=result, 
                timeout=10
            )
            if response.status_code == 200:
                logger.info(f"回调通知成功: {callback_url}")
            else:
                logger.warning(f"回调通知失败: {callback_url} (状态码: {response.status_code})")
        except Exception as e:
            logger.error(f"回调通知异常: {callback_url} - {e}")
    
    def stop(self):
        """停止服务"""
        self.running = False
        logger.info("服务停止请求已发送")
    
    def get_queue_status(self) -> Dict:
        """获取队列状态"""
        return {
            'queue_length': self.redis_client.llen(self.task_queue),
            'service_name': self.service_name,
            'running': self.running
        }

class AlgorithmClient:
    """算法客户端（用于提交任务和获取结果）"""
    
    def __init__(self, redis_host='localhost', redis_port=6379, redis_db=0):
        self.service = AsyncAlgorithmService(redis_host, redis_port, redis_db)
    
    def analyze_file(self, csv_path: str, analysis_type: str = 'comprehensive', 
                     timeout: int = 300) -> Optional[Dict]:
        """分析文件（同步接口）"""
        task_data = {
            'type': analysis_type,
            'csv_path': csv_path
        }
        
        # 提交任务
        task_id = self.service.submit_task(task_data)
        
        # 等待结果
        result = self.service.get_result(task_id, timeout)
        return result
    
    def analyze_file_async(self, csv_path: str, analysis_type: str = 'comprehensive',
                          callback_url: str = None) -> str:
        """分析文件（异步接口）"""
        task_data = {
            'type': analysis_type,
            'csv_path': csv_path
        }
        
        if callback_url:
            task_data['callback_url'] = callback_url
        
        return self.service.submit_task(task_data)

def main():
    """命令行接口"""
    import argparse
    
    parser = argparse.ArgumentParser(description='足部压力分析异步服务')
    parser.add_argument('--mode', choices=['worker', 'client', 'status'], 
                       default='worker', help='运行模式')
    parser.add_argument('--redis-host', default='localhost', help='Redis主机')
    parser.add_argument('--redis-port', type=int, default=6379, help='Redis端口')
    parser.add_argument('--csv-file', help='要分析的CSV文件（客户端模式）')
    parser.add_argument('--analysis-type', default='comprehensive',
                       choices=['comprehensive', 'gait_only', 'balance_only'],
                       help='分析类型')
    
    args = parser.parse_args()
    
    if args.mode == 'worker':
        # 运行工作进程
        service = AsyncAlgorithmService(args.redis_host, args.redis_port)
        try:
            service.run_worker()
        except KeyboardInterrupt:
            service.stop()
    
    elif args.mode == 'client':
        # 客户端模式
        if not args.csv_file:
            print("错误: 客户端模式需要指定 --csv-file")
            return
        
        client = AlgorithmClient(args.redis_host, args.redis_port)
        print(f"正在分析文件: {args.csv_file}")
        
        result = client.analyze_file(args.csv_file, args.analysis_type)
        if result:
            print("分析完成:")
            print(json.dumps(result, indent=2, default=str))
        else:
            print("分析失败或超时")
    
    elif args.mode == 'status':
        # 查看队列状态
        service = AsyncAlgorithmService(args.redis_host, args.redis_port)
        status = service.get_queue_status()
        print(json.dumps(status, indent=2))

if __name__ == "__main__":
    main()