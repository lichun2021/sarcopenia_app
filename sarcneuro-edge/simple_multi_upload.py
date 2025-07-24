#!/usr/bin/env python3
"""
SarcNeuro Edge 简化多文件上传界面
确保稳定性的基础版本
"""
import sys
import os
import json
import uuid
import asyncio
import math
from pathlib import Path
from datetime import datetime
from typing import Optional, List

# 设置Python路径
sys.path.insert(0, str(Path(__file__).parent))

import uvicorn
from fastapi import FastAPI, File, UploadFile, Form, HTTPException, Request, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse

try:
    from app.config import config
    from core.analyzer import SarcNeuroAnalyzer, PatientInfo, PressurePoint
    from core.report_generator import ReportGenerator
except ImportError as e:
    print(f"导入警告: {e}")
    # 创建简化配置
    class SimpleConfig:
        class App:
            host = "0.0.0.0"
            port = 3001
            debug = True
        app = App()
    config = SimpleConfig()

# 创建应用
app = FastAPI(
    title="SarcNeuro Edge - 简化多文件上传",
    description="稳定版多文件上传测试界面",
    version="1.0.0"
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
os.makedirs("uploads", exist_ok=True)
os.makedirs("reports", exist_ok=True)

# 尝试初始化分析器
try:
    analyzer = SarcNeuroAnalyzer()
    report_generator = ReportGenerator()
    ANALYZER_READY = True
except Exception as e:
    print(f"分析器初始化失败: {e}")
    analyzer = None
    report_generator = None
    ANALYZER_READY = False

# 全局任务存储
analysis_tasks = {}

class SimpleTask:
    def __init__(self, task_id: str, files: List[dict], patient_info: dict, test_type: str):
        self.task_id = task_id
        self.files = files
        self.patient_info = patient_info
        self.test_type = test_type
        self.status = "PENDING"
        self.progress = 0
        self.current_file = 0
        self.total_files = len(files)
        self.results = []
        self.start_time = datetime.now()
        self.end_time = None

async def simple_process_task(task: SimpleTask):
    """简化的任务处理"""
    try:
        task.status = "PROCESSING"
        analysis_tasks[task.task_id] = task
        
        for i, file_info in enumerate(task.files):
            task.current_file = i + 1
            task.progress = int((i / task.total_files) * 100)
            
            # 模拟处理时间
            await asyncio.sleep(1)
            
            try:
                if ANALYZER_READY:
                    # 创建患者信息
                    patient = PatientInfo(
                        name=task.patient_info['name'],
                        age=int(task.patient_info['age']),
                        gender=task.patient_info['gender'].upper(),
                        height=float(task.patient_info.get('height')) if task.patient_info.get('height') else None,
                        weight=float(task.patient_info.get('weight')) if task.patient_info.get('weight') else None
                    )
                    
                    # 解析CSV数据
                    pressure_points = analyzer.parse_csv_data(file_info['content'])
                    
                    # 执行分析
                    analysis_result = analyzer.comprehensive_analysis(
                        pressure_points, 
                        patient, 
                        task.test_type
                    )
                    
                    # 生成报告
                    report_id = str(uuid.uuid4())
                    report_html = await report_generator.generate_html_report(
                        analysis_result,
                        patient,
                        {
                            "test_type": task.test_type,
                            "data_points": len(pressure_points),
                            "test_duration": pressure_points[-1].time - pressure_points[0].time if pressure_points else 0,
                            "report_id": report_id,
                            "filename": file_info['filename']
                        }
                    )
                    
                    # 保存报告
                    report_file = f"reports/report_{report_id}.html"
                    with open(report_file, 'w', encoding='utf-8') as f:
                        f.write(report_html)
                    
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
                else:
                    # 模拟结果
                    task.results.append({
                        "filename": file_info['filename'],
                        "report_id": "demo-" + str(uuid.uuid4())[:8],
                        "data_points": 200,
                        "analysis_summary": {
                            "overall_score": 85.5,
                            "risk_level": "LOW",
                            "confidence": 0.92
                        },
                        "report_url": "#",
                        "status": "SUCCESS"
                    })
                
            except Exception as e:
                task.results.append({
                    "filename": file_info['filename'],
                    "status": "FAILED",
                    "error": str(e)
                })
        
        task.progress = 100
        task.status = "COMPLETED"
        task.end_time = datetime.now()
        
    except Exception as e:
        task.status = "FAILED"
        task.end_time = datetime.now()

@app.get("/", response_class=HTMLResponse)
async def index():
    """主页"""
    return """
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>SarcNeuro Edge - 简化多文件上传</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { font-family: Arial, sans-serif; background: #f5f5f5; padding: 20px; }
        .container { max-width: 800px; margin: 0 auto; background: white; padding: 30px; border-radius: 10px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }
        h1 { color: #333; text-align: center; margin-bottom: 30px; }
        .form-group { margin-bottom: 20px; }
        label { display: block; margin-bottom: 5px; font-weight: bold; }
        input, select { width: 100%; padding: 10px; border: 1px solid #ddd; border-radius: 5px; }
        .file-area { border: 2px dashed #007bff; border-radius: 10px; padding: 40px; text-align: center; background: #f8f9ff; margin: 20px 0; cursor: pointer; }
        .file-area:hover { background: #e8f0fe; }
        .file-list { margin-top: 20px; }
        .file-item { display: flex; justify-content: space-between; align-items: center; padding: 10px; background: #f8f9fa; border: 1px solid #ddd; border-radius: 5px; margin-bottom: 5px; }
        .btn { padding: 12px 25px; background: #007bff; color: white; border: none; border-radius: 5px; cursor: pointer; margin-right: 10px; }
        .btn:hover { background: #0056b3; }
        .btn:disabled { background: #ccc; cursor: not-allowed; }
        .progress { display: none; margin-top: 20px; padding: 20px; background: #e3f2fd; border-radius: 10px; }
        .progress-bar { width: 100%; height: 20px; background: #ddd; border-radius: 10px; overflow: hidden; margin: 10px 0; }
        .progress-fill { height: 100%; background: #007bff; transition: width 0.3s; width: 0%; }
        .results { display: none; margin-top: 20px; padding: 20px; background: #d4edda; border-radius: 10px; }
        .result-item { background: white; padding: 15px; margin: 10px 0; border-radius: 5px; border-left: 4px solid #28a745; }
        .result-item.error { border-left-color: #dc3545; }
        .form-row { display: grid; grid-template-columns: 1fr 1fr; gap: 15px; }
        .demo-section { background: #fff3cd; padding: 15px; border-radius: 5px; margin-bottom: 20px; }
    </style>
</head>
<body>
    <div class="container">
        <h1>🧠 SarcNeuro Edge - 简化多文件上传</h1>
        
        <div class="demo-section">
            <h3>🎯 演示数据</h3>
            <p>生成多个演示CSV文件进行测试</p>
            <button class="btn" onclick="generateDemoFiles()">生成演示文件</button>
        </div>
        
        <form id="uploadForm">
            <div class="form-row">
                <div class="form-group">
                    <label>患者姓名 *</label>
                    <input type="text" id="patientName" required>
                </div>
                <div class="form-group">
                    <label>年龄 *</label>
                    <input type="number" id="patientAge" min="1" max="120" required>
                </div>
            </div>
            
            <div class="form-row">
                <div class="form-group">
                    <label>性别 *</label>
                    <select id="patientGender" required>
                        <option value="">请选择</option>
                        <option value="MALE">男</option>
                        <option value="FEMALE">女</option>
                    </select>
                </div>
                <div class="form-group">
                    <label>测试类型</label>
                    <select id="testType">
                        <option value="COMPREHENSIVE">综合评估</option>
                        <option value="WALK_4_LAPS">步道4圈</option>
                        <option value="WALK_7_LAPS">步道7圈</option>
                    </select>
                </div>
            </div>
            
            <div class="form-group">
                <label>选择多个CSV文件 *</label>
                <div class="file-area" onclick="document.getElementById('files').click()">
                    <input type="file" id="files" multiple accept=".csv" style="display:none">
                    <h3>📁 点击选择多个CSV文件</h3>
                    <p>支持同时选择多个文件进行批量分析</p>
                </div>
                <div id="fileList" class="file-list"></div>
            </div>
            
            <button type="submit" class="btn" id="submitBtn">🚀 开始批量分析</button>
            <button type="button" class="btn" onclick="resetForm()" style="background:#6c757d;">重置</button>
        </form>
        
        <div id="progress" class="progress">
            <h3>📊 分析进度</h3>
            <div class="progress-bar">
                <div class="progress-fill" id="progressFill"></div>
            </div>
            <p>状态: <span id="status">等待中</span> | 进度: <span id="progressText">0%</span> | 文件: <span id="fileProgress">0/0</span></p>
        </div>
        
        <div id="results" class="results">
            <h3>✅ 分析完成</h3>
            <div id="resultList"></div>
        </div>
    </div>
    
    <script>
        let selectedFiles = [];
        let currentTaskId = null;
        let progressInterval = null;
        
        document.getElementById('files').addEventListener('change', function(e) {
            selectedFiles = Array.from(e.target.files);
            updateFileList();
        });
        
        function updateFileList() {
            const fileList = document.getElementById('fileList');
            fileList.innerHTML = '';
            
            selectedFiles.forEach((file, index) => {
                const div = document.createElement('div');
                div.className = 'file-item';
                div.innerHTML = `
                    <div>
                        <strong>${file.name}</strong>
                        <span style="color:#666; margin-left:10px;">${(file.size/1024).toFixed(1)} KB</span>
                    </div>
                    <button type="button" onclick="removeFile(${index})" style="background:#dc3545; color:white; border:none; padding:5px 10px; border-radius:3px;">删除</button>
                `;
                fileList.appendChild(div);
            });
        }
        
        function removeFile(index) {
            selectedFiles.splice(index, 1);
            updateFileList();
        }
        
        document.getElementById('uploadForm').addEventListener('submit', async function(e) {
            e.preventDefault();
            
            if (selectedFiles.length === 0) {
                alert('请选择至少一个文件');
                return;
            }
            
            const formData = new FormData();
            selectedFiles.forEach(file => formData.append('files', file));
            formData.append('patient_name', document.getElementById('patientName').value);
            formData.append('patient_age', document.getElementById('patientAge').value);
            formData.append('patient_gender', document.getElementById('patientGender').value);
            formData.append('test_type', document.getElementById('testType').value);
            
            try {
                document.getElementById('submitBtn').disabled = true;
                document.getElementById('submitBtn').textContent = '提交中...';
                
                const response = await fetch('/upload-multiple', {
                    method: 'POST',
                    body: formData
                });
                
                const data = await response.json();
                
                if (response.ok && data.status === 'success') {
                    currentTaskId = data.task_id;
                    showProgress();
                    startProgressMonitoring();
                    alert(`成功提交 ${data.total_files} 个文件！`);
                } else {
                    throw new Error(data.detail || '提交失败');
                }
            } catch (error) {
                alert('提交失败: ' + error.message);
            } finally {
                document.getElementById('submitBtn').disabled = false;
                document.getElementById('submitBtn').textContent = '🚀 开始批量分析';
            }
        });
        
        function showProgress() {
            document.getElementById('progress').style.display = 'block';
            document.getElementById('results').style.display = 'none';
        }
        
        function showResults(data) {
            document.getElementById('progress').style.display = 'none';
            document.getElementById('results').style.display = 'block';
            
            const resultList = document.getElementById('resultList');
            resultList.innerHTML = '';
            
            data.results.forEach(result => {
                const div = document.createElement('div');
                div.className = `result-item ${result.status === 'SUCCESS' ? '' : 'error'}`;
                
                if (result.status === 'SUCCESS') {
                    div.innerHTML = `
                        <h4>${result.filename}</h4>
                        <p>数据点: ${result.data_points} | 评分: ${result.analysis_summary.overall_score.toFixed(1)} | 风险: ${result.analysis_summary.risk_level}</p>
                        ${result.report_url !== '#' ? `<a href="${result.report_url}" target="_blank" style="color:#007bff;">查看报告</a>` : '<span style="color:#666;">演示模式</span>'}
                    `;
                } else {
                    div.innerHTML = `
                        <h4>${result.filename} - 处理失败</h4>
                        <p style="color:#dc3545;">${result.error}</p>
                    `;
                }
                
                resultList.appendChild(div);
            });
        }
        
        function startProgressMonitoring() {
            progressInterval = setInterval(async () => {
                if (currentTaskId) {
                    try {
                        const response = await fetch(`/task-status/${currentTaskId}`);
                        const data = await response.json();
                        
                        if (response.ok) {
                            updateProgressDisplay(data);
                            
                            if (data.status === 'COMPLETED' || data.status === 'FAILED') {
                                clearInterval(progressInterval);
                                if (data.status === 'COMPLETED') {
                                    showResults(data);
                                } else {
                                    alert('分析失败: ' + (data.error_message || '未知错误'));
                                }
                            }
                        }
                    } catch (error) {
                        console.error('更新进度失败:', error);
                    }
                }
            }, 1000);
        }
        
        function updateProgressDisplay(data) {
            const statusMap = {
                'PENDING': '等待中',
                'PROCESSING': '处理中',
                'COMPLETED': '已完成',
                'FAILED': '失败'
            };
            
            document.getElementById('status').textContent = statusMap[data.status] || data.status;
            document.getElementById('progressText').textContent = data.progress + '%';
            document.getElementById('fileProgress').textContent = `${data.current_file}/${data.total_files}`;
            document.getElementById('progressFill').style.width = data.progress + '%';
        }
        
        async function generateDemoFiles() {
            try {
                const count = parseInt(prompt('生成文件数量 (1-10):', '3'));
                if (!count || count < 1 || count > 10) {
                    alert('请输入1-10之间的数字');
                    return;
                }
                
                const response = await fetch('/demo-data');
                const data = await response.json();
                
                if (data.status === 'success') {
                    selectedFiles = [];
                    
                    for (let i = 1; i <= count; i++) {
                        const blob = new Blob([data.csv_content], { type: 'text/csv' });
                        const file = new File([blob], `demo_data_${i}.csv`, { type: 'text/csv' });
                        selectedFiles.push(file);
                    }
                    
                    updateFileList();
                    alert(`已生成 ${count} 个演示文件！`);
                } else {
                    alert('生成失败: ' + data.message);
                }
            } catch (error) {
                alert('生成失败: ' + error.message);
            }
        }
        
        function resetForm() {
            document.getElementById('uploadForm').reset();
            selectedFiles = [];
            updateFileList();
            document.getElementById('progress').style.display = 'none';
            document.getElementById('results').style.display = 'none';
            if (progressInterval) clearInterval(progressInterval);
            currentTaskId = null;
        }
    </script>
</body>
</html>
    """

@app.post("/upload-multiple")
async def upload_multiple_files(
    background_tasks: BackgroundTasks,
    files: List[UploadFile] = File(...),
    patient_name: str = Form(...),
    patient_age: int = Form(...),
    patient_gender: str = Form(...),
    test_type: str = Form("COMPREHENSIVE")
):
    """处理多文件上传"""
    try:
        print(f"收到上传请求: {len(files)} 个文件")
        
        if not files:
            raise HTTPException(status_code=400, detail="请选择文件")
        
        # 读取文件内容
        file_data = []
        for file in files:
            if file.filename.endswith('.csv'):
                content = await file.read()
                file_data.append({
                    'filename': file.filename,
                    'content': content.decode('utf-8', errors='ignore')
                })
        
        if not file_data:
            raise HTTPException(status_code=400, detail="没有有效的CSV文件")
        
        # 创建任务
        task_id = str(uuid.uuid4())
        patient_info = {
            'name': patient_name,
            'age': patient_age,
            'gender': patient_gender
        }
        
        task = SimpleTask(task_id, file_data, patient_info, test_type)
        
        # 启动后台处理
        background_tasks.add_task(simple_process_task, task)
        
        return {
            "status": "success",
            "task_id": task_id,
            "total_files": len(file_data),
            "message": f"已提交 {len(file_data)} 个文件"
        }
        
    except Exception as e:
        print(f"上传错误: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/task-status/{task_id}")
async def get_task_status(task_id: str):
    """获取任务状态"""
    if task_id not in analysis_tasks:
        raise HTTPException(status_code=404, detail="任务不存在")
    
    task = analysis_tasks[task_id]
    return {
        "task_id": task_id,
        "status": task.status,
        "progress": task.progress,
        "current_file": task.current_file,
        "total_files": task.total_files,
        "results": task.results
    }

@app.get("/demo-data")
async def generate_demo_data():
    """生成演示数据"""
    try:
        demo_data = ["time,max_pressure,timestamp,contact_area,total_pressure,data"]
        
        for i in range(200):
            time_val = i * 0.1
            timestamp = f"2025-01-24 12:{(i//10)%60:02d}:{(i*10)%60:02d}"
            base_pressure = 50 + 30 * abs(math.sin(i * 0.1))
            max_pressure = int(base_pressure + 20 * (i % 10) / 10)
            contact_area = int(40 + 20 * abs(math.cos(i * 0.05)))
            total_pressure = max_pressure * contact_area
            
            # 生成32x32矩阵
            pressure_matrix = []
            for row in range(32):
                for col in range(32):
                    center_x, center_y = 16, 16
                    distance = ((row - center_x) ** 2 + (col - center_y) ** 2) ** 0.5
                    pressure_val = max(0, int(base_pressure * (1 - distance / 20)))
                    if distance < 10:
                        pressure_val += (i + row + col) % 15
                    pressure_matrix.append(pressure_val)
            
            data_json = json.dumps(pressure_matrix)
            demo_data.append(f"{time_val},{max_pressure},{timestamp},{contact_area},{total_pressure},\"{data_json}\"")
        
        return {
            "status": "success",
            "csv_content": "\\n".join(demo_data),
            "data_points": 200
        }
        
    except Exception as e:
        return {"status": "error", "message": str(e)}

@app.get("/health")
async def health_check():
    """健康检查"""
    return {
        "status": "healthy",
        "analyzer_ready": ANALYZER_READY,
        "timestamp": datetime.now().isoformat()
    }

if __name__ == "__main__":
    PORT = 3001
    print("🚀 启动 SarcNeuro Edge 简化多文件上传界面...")
    print(f"📍 访问地址: http://localhost:{PORT}")
    print(f"🔧 分析器状态: {'就绪' if ANALYZER_READY else '演示模式'}")
    
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=PORT,
        reload=False,
        access_log=True,
        log_level="info"
    )