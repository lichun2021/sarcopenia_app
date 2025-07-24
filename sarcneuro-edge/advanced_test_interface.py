#!/usr/bin/env python3
"""
SarcNeuro Edge 高级测试界面
支持多文件上传、分析进度、批量处理等完整功能
"""
import sys
import os
import json
import uuid
import asyncio
from pathlib import Path
from datetime import datetime
from typing import Optional, List
import threading
import time

# 设置Python路径
sys.path.insert(0, str(Path(__file__).parent))

import uvicorn
from fastapi import FastAPI, File, UploadFile, Form, HTTPException, Request, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from app.config import config
from core.analyzer import SarcNeuroAnalyzer, PatientInfo, PressurePoint
from core.report_generator import ReportGenerator

# 创建应用
app = FastAPI(
    title="SarcNeuro Edge - 高级测试界面",
    description="肌少症智能分析系统 - 多文件批量处理功能",
    version="2.0.0"
)

# 添加CORS中间件
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 创建必要目录
os.makedirs("static", exist_ok=True)
os.makedirs("templates", exist_ok=True)
os.makedirs("uploads", exist_ok=True)
os.makedirs("reports", exist_ok=True)

# 静态文件和模板
app.mount("/static", StaticFiles(directory="static"), name="static")
app.mount("/reports", StaticFiles(directory="reports"), name="reports")
templates = Jinja2Templates(directory="templates")

# 全局分析器和报告生成器
analyzer = SarcNeuroAnalyzer()
report_generator = ReportGenerator()

# 全局分析任务存储
analysis_tasks = {}
task_results = {}

class AnalysisTask:
    def __init__(self, task_id: str, files: List[dict], patient: PatientInfo, test_type: str):
        self.task_id = task_id
        self.files = files
        self.patient = patient
        self.test_type = test_type
        self.status = "PENDING"  # PENDING, PROCESSING, COMPLETED, FAILED
        self.progress = 0
        self.current_file = 0
        self.total_files = len(files)
        self.results = []
        self.error_message = None
        self.start_time = datetime.now()
        self.end_time = None

async def process_analysis_task(task: AnalysisTask):
    """后台处理分析任务"""
    try:
        print(f"开始处理分析任务: {task.task_id}")
        task.status = "PROCESSING"
        analysis_tasks[task.task_id] = task
        
        for i, file_info in enumerate(task.files):
            task.current_file = i + 1
            task.progress = int((i / task.total_files) * 100)
            
            print(f"处理文件 {i+1}/{task.total_files}: {file_info['filename']}")
            
            # 减少处理时间，提高用户体验
            await asyncio.sleep(1)
            
            try:
                # 解析CSV数据
                print(f"解析CSV数据: {file_info['filename']}")
                pressure_points = analyzer.parse_csv_data(file_info['content'])
                print(f"解析得到 {len(pressure_points)} 个数据点")
                
                # 执行分析
                print(f"执行分析: {task.test_type}")
                analysis_result = analyzer.comprehensive_analysis(
                    pressure_points, 
                    task.patient, 
                    task.test_type
                )
                print(f"分析完成，评分: {analysis_result.overall_score}")
                
                # 生成报告ID
                report_id = str(uuid.uuid4())
                
                # 生成HTML报告
                print(f"生成报告: {report_id}")
                report_html = await report_generator.generate_html_report(
                    analysis_result,
                    task.patient,
                    {
                        "test_type": task.test_type,
                        "data_points": len(pressure_points),
                        "test_duration": pressure_points[-1].time - pressure_points[0].time if pressure_points else 0,
                        "report_id": report_id,
                        "filename": file_info['filename']
                    }
                )
                
                # 保存报告文件
                report_file = f"reports/report_{report_id}.html"
                with open(report_file, 'w', encoding='utf-8') as f:
                    f.write(report_html)
                
                print(f"报告已保存: {report_file}")
                
                # 保存结果
                task.results.append({
                    "filename": file_info['filename'],
                    "report_id": report_id,
                    "data_points": len(pressure_points),
                    "analysis_summary": {
                        "overall_score": analysis_result.overall_score,
                        "risk_level": analysis_result.risk_level,
                        "confidence": analysis_result.confidence
                    },
                    "report_url": f"/reports/report_{report_id}.html",
                    "status": "SUCCESS"
                })
                
                print(f"文件 {file_info['filename']} 处理成功")
                
            except Exception as e:
                print(f"文件 {file_info['filename']} 处理失败: {str(e)}")
                import traceback
                traceback.print_exc()
                
                task.results.append({
                    "filename": file_info['filename'],
                    "status": "FAILED",
                    "error": str(e)
                })
        
        task.progress = 100
        task.status = "COMPLETED"
        task.end_time = datetime.now()
        print(f"任务 {task.task_id} 处理完成")
        
    except Exception as e:
        print(f"任务 {task.task_id} 处理异常: {str(e)}")
        import traceback
        traceback.print_exc()
        
        task.status = "FAILED"
        task.error_message = str(e)
        task.end_time = datetime.now()

@app.get("/", response_class=HTMLResponse)
async def advanced_test_interface(request: Request):
    """高级测试界面首页"""
    return templates.TemplateResponse("advanced_test_interface.html", {"request": request})

@app.post("/upload-multiple")
async def upload_multiple_files(
    background_tasks: BackgroundTasks,
    files: List[UploadFile] = File(...),
    patient_name: str = Form(...),
    patient_age: int = Form(...),
    patient_gender: str = Form(...),
    patient_height: Optional[float] = Form(None),
    patient_weight: Optional[float] = Form(None),
    test_type: str = Form("COMPREHENSIVE")
):
    """处理多文件上传和批量分析"""
    try:
        print(f"收到上传请求: {len(files)} 个文件")
        
        # 验证文件
        if not files or len(files) == 0:
            raise HTTPException(status_code=400, detail="请选择至少一个文件")
        
        print(f"文件列表: {[f.filename for f in files]}")
        
        # 检查文件类型和内容
        valid_files = []
        for file in files:
            if not file.filename or not file.filename.endswith('.csv'):
                print(f"跳过非CSV文件: {file.filename}")
                continue
            
            # 检查文件大小
            if file.size and file.size > 50 * 1024 * 1024:  # 50MB限制
                raise HTTPException(status_code=400, detail=f"文件 {file.filename} 过大 (>50MB)")
            
            valid_files.append(file)
        
        if not valid_files:
            raise HTTPException(status_code=400, detail="没有找到有效的CSV文件")
        
        print(f"有效文件数量: {len(valid_files)}")
        
        # 创建患者信息
        try:
            patient = PatientInfo(
                name=patient_name,
                age=int(patient_age),
                gender=patient_gender.upper(),
                height=float(patient_height) if patient_height else None,
                weight=float(patient_weight) if patient_weight else None
            )
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"患者信息格式错误: {str(e)}")
        
        # 读取文件内容
        file_data = []
        for file in valid_files:
            try:
                content = await file.read()
                csv_content = content.decode('utf-8', errors='ignore')
                
                # 基本验证CSV格式
                if not csv_content.strip():
                    print(f"文件 {file.filename} 为空，跳过")
                    continue
                
                file_data.append({
                    'filename': file.filename,
                    'content': csv_content,
                    'size': len(csv_content)
                })
                print(f"成功读取文件: {file.filename}, 大小: {len(csv_content)} 字符")
                
            except Exception as e:
                print(f"读取文件 {file.filename} 失败: {str(e)}")
                continue
        
        if not file_data:
            raise HTTPException(status_code=400, detail="所有文件都无法读取或为空")
        
        # 创建分析任务
        task_id = str(uuid.uuid4())
        task = AnalysisTask(task_id, file_data, patient, test_type)
        
        print(f"创建分析任务: {task_id}, 文件数量: {len(file_data)}")
        
        # 启动后台分析任务
        background_tasks.add_task(process_analysis_task, task)
        
        return {
            "status": "success",
            "message": f"已提交 {len(file_data)} 个文件进行批量分析",
            "task_id": task_id,
            "total_files": len(file_data),
            "patient_name": patient_name
        }
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"上传处理异常: {str(e)}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"服务器内部错误: {str(e)}")

@app.get("/task-status/{task_id}")
async def get_task_status(task_id: str):
    """获取分析任务状态"""
    if task_id not in analysis_tasks:
        raise HTTPException(status_code=404, detail="任务不存在")
    
    task = analysis_tasks[task_id]
    
    return {
        "task_id": task_id,
        "status": task.status,
        "progress": task.progress,
        "current_file": task.current_file,
        "total_files": task.total_files,
        "start_time": task.start_time.isoformat(),
        "end_time": task.end_time.isoformat() if task.end_time else None,
        "results": task.results,
        "error_message": task.error_message
    }

@app.get("/demo-data")
async def generate_demo_data():
    """生成演示CSV数据"""
    try:
        import math
        
        # 生成模拟的压力数据
        demo_data = []
        demo_data.append("time,max_pressure,timestamp,contact_area,total_pressure,data")
        
        for i in range(200):  # 200个数据点，模拟20秒的数据
            time_val = i * 0.1
            timestamp = f"2025-01-24 {12 + i//600:02d}:{(i//10)%60:02d}:{(i*10)%60:02d}"
            
            # 模拟真实的压力数据变化
            base_pressure = 50 + 30 * abs(math.sin(i * 0.1))  # 基础压力波动
            max_pressure = int(base_pressure + 20 * (i % 10) / 10)
            contact_area = int(40 + 20 * abs(math.cos(i * 0.05)))
            total_pressure = max_pressure * contact_area
            
            # 生成32x32的压力矩阵数据
            pressure_matrix = []
            for row in range(32):
                for col in range(32):
                    # 模拟足底压力分布：中心区域压力较大
                    center_x, center_y = 16, 16
                    distance = ((row - center_x) ** 2 + (col - center_y) ** 2) ** 0.5
                    pressure_val = max(0, int(base_pressure * (1 - distance / 20)))
                    
                    # 添加一些随机变化
                    if distance < 10:  # 足底中心区域
                        pressure_val += (i + row + col) % 15
                    
                    pressure_matrix.append(pressure_val)
            
            data_json = json.dumps(pressure_matrix)
            demo_data.append(f"{time_val},{max_pressure},{timestamp},{contact_area},{total_pressure},\"{data_json}\"")
        
        return {
            "status": "success",
            "csv_content": "\\n".join(demo_data),
            "data_points": 200,
            "description": "模拟20秒步态测试数据，包含32x32压力传感器矩阵"
        }
        
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"status": "error", "message": f"生成演示数据失败: {str(e)}"}
        )

@app.get("/health")
async def health_check():
    """健康检查"""
    return {
        "status": "healthy",
        "version": "2.0.0",
        "analyzer": "ready",
        "active_tasks": len(analysis_tasks),
        "timestamp": datetime.now().isoformat()
    }

if __name__ == "__main__":
    import math  # 导入math模块用于演示数据生成
    
    print("🚀 启动 SarcNeuro Edge 高级测试界面...")
    print(f"📍 访问地址: http://localhost:{config.app.port}")
    print(f"📊 高级界面: http://localhost:{config.app.port}")
    print(f"📚 API文档: http://localhost:{config.app.port}/docs")
    
    uvicorn.run(
        app,
        host=config.app.host,
        port=config.app.port,
        reload=config.app.debug,
        access_log=True,
        log_level="info"
    )