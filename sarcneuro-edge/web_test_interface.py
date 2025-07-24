#!/usr/bin/env python3
"""
SarcNeuro Edge Web测试界面
支持CSV文件上传和报告生成
"""
import sys
import os
import json
import uuid
from pathlib import Path
from datetime import datetime
from typing import Optional

# 设置Python路径
sys.path.insert(0, str(Path(__file__).parent))

import uvicorn
from fastapi import FastAPI, File, UploadFile, Form, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from app.config import config
from core.analyzer import SarcNeuroAnalyzer, PatientInfo, PressurePoint
from core.report_generator import ReportGenerator

# 创建应用
app = FastAPI(
    title="SarcNeuro Edge - 测试界面",
    description="肌少症智能分析系统 - 文件上传测试功能",
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

@app.get("/", response_class=HTMLResponse)
async def test_interface(request: Request):
    """测试界面首页"""
    return templates.TemplateResponse("test_interface.html", {"request": request})

@app.post("/upload")
async def upload_file(
    file: UploadFile = File(...),
    patient_name: str = Form(...),
    patient_age: int = Form(...),
    patient_gender: str = Form(...),
    patient_height: Optional[float] = Form(None),
    patient_weight: Optional[float] = Form(None),
    test_type: str = Form("COMPREHENSIVE")
):
    """处理文件上传和分析"""
    try:
        # 验证文件类型
        if not file.filename.endswith('.csv'):
            raise HTTPException(status_code=400, detail="只支持CSV文件格式")
        
        # 读取文件内容
        content = await file.read()
        csv_content = content.decode('utf-8')
        
        # 创建患者信息
        patient = PatientInfo(
            name=patient_name,
            age=patient_age,
            gender=patient_gender.upper(),
            height=patient_height,
            weight=patient_weight
        )
        
        # 解析CSV数据
        pressure_points = analyzer.parse_csv_data(csv_content)
        
        # 执行分析
        analysis_result = analyzer.comprehensive_analysis(
            pressure_points, 
            patient, 
            test_type
        )
        
        # 生成报告ID
        report_id = str(uuid.uuid4())
        
        # 生成HTML报告
        report_html = await report_generator.generate_html_report(
            analysis_result,
            patient,
            {
                "test_type": test_type,
                "data_points": len(pressure_points),
                "test_duration": pressure_points[-1].time - pressure_points[0].time,
                "report_id": report_id
            }
        )
        
        # 保存报告文件
        report_file = f"reports/report_{report_id}.html"
        with open(report_file, 'w', encoding='utf-8') as f:
            f.write(report_html)
        
        return {
            "status": "success",
            "message": "文件上传并分析成功",
            "report_id": report_id,
            "data_points": len(pressure_points),
            "analysis_summary": {
                "overall_score": analysis_result.overall_score,
                "risk_level": analysis_result.risk_level,
                "confidence": analysis_result.confidence
            },
            "report_url": f"/reports/report_{report_id}.html"
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"分析失败: {str(e)}")

@app.get("/demo-data")
async def generate_demo_data():
    """生成演示CSV数据"""
    try:
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
            "csv_content": "\n".join(demo_data),
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
        "version": "1.0.0",
        "analyzer": "ready",
        "timestamp": datetime.now().isoformat()
    }

# 创建HTML模板
html_template = """
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>SarcNeuro Edge - 测试界面</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        
        body {
            font-family: 'Microsoft YaHei', Arial, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            padding: 20px;
        }
        
        .container {
            max-width: 1000px;
            margin: 0 auto;
            background: white;
            border-radius: 15px;
            box-shadow: 0 20px 40px rgba(0,0,0,0.1);
            overflow: hidden;
        }
        
        .header {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 30px;
            text-align: center;
        }
        
        .header h1 {
            font-size: 2.5em;
            margin-bottom: 10px;
        }
        
        .header p {
            font-size: 1.1em;
            opacity: 0.9;
        }
        
        .content {
            padding: 40px;
        }
        
        .upload-section {
            background: #f8f9ff;
            border-radius: 10px;
            padding: 30px;
            margin-bottom: 30px;
            border: 2px dashed #667eea;
        }
        
        .form-group {
            margin-bottom: 20px;
        }
        
        .form-group label {
            display: block;
            margin-bottom: 8px;
            font-weight: bold;
            color: #333;
        }
        
        .form-group input,
        .form-group select {
            width: 100%;
            padding: 12px;
            border: 2px solid #e1e5e9;
            border-radius: 8px;
            font-size: 16px;
            transition: border-color 0.3s;
        }
        
        .form-group input:focus,
        .form-group select:focus {
            outline: none;
            border-color: #667eea;
        }
        
        .form-row {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 20px;
        }
        
        .file-upload {
            position: relative;
            display: inline-block;
            width: 100%;
        }
        
        .file-upload input[type=file] {
            position: absolute;
            opacity: 0;
            width: 100%;
            height: 100%;
            cursor: pointer;
        }
        
        .file-upload-label {
            display: block;
            padding: 20px;
            background: #667eea;
            color: white;
            text-align: center;
            border-radius: 8px;
            cursor: pointer;
            transition: background 0.3s;
        }
        
        .file-upload-label:hover {
            background: #5a67d8;
        }
        
        .btn {
            padding: 15px 30px;
            background: #667eea;
            color: white;
            border: none;
            border-radius: 8px;
            font-size: 16px;
            cursor: pointer;
            transition: background 0.3s;
            margin-right: 10px;
        }
        
        .btn:hover {
            background: #5a67d8;
        }
        
        .btn-secondary {
            background: #6c757d;
        }
        
        .btn-secondary:hover {
            background: #5a6268;
        }
        
        .result-section {
            margin-top: 30px;
            padding: 20px;
            background: #f8f9fa;
            border-radius: 10px;
            display: none;
        }
        
        .result-success {
            color: #28a745;
            background: #d4edda;
            border: 1px solid #c3e6cb;
        }
        
        .result-error {
            color: #dc3545;
            background: #f8d7da;
            border: 1px solid #f5c6cb;
        }
        
        .loading {
            display: none;
            text-align: center;
            margin: 20px 0;
        }
        
        .spinner {
            border: 4px solid #f3f3f3;
            border-top: 4px solid #667eea;
            border-radius: 50%;
            width: 40px;
            height: 40px;
            animation: spin 1s linear infinite;
            margin: 0 auto;
        }
        
        @keyframes spin {
            0% { transform: rotate(0deg); }
            100% { transform: rotate(360deg); }
        }
        
        .demo-section {
            background: #fff3cd;
            border: 1px solid #ffeaa7;
            border-radius: 10px;
            padding: 20px;
            margin-bottom: 30px;
        }
        
        .demo-section h3 {
            color: #856404;
            margin-bottom: 15px;
        }
        
        .instructions {
            background: #e3f2fd;
            border-radius: 10px;
            padding: 20px;
            margin-bottom: 30px;
        }
        
        .instructions h3 {
            color: #1976d2;
            margin-bottom: 15px;
        }
        
        .instructions ol {
            margin-left: 20px;
        }
        
        .instructions li {
            margin-bottom: 10px;
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🧠 SarcNeuro Edge</h1>
            <p>肌少症智能分析系统 - 文件上传测试功能</p>
        </div>
        
        <div class="content">
            <!-- 使用说明 -->
            <div class="instructions">
                <h3>📋 使用说明</h3>
                <ol>
                    <li>填写患者基本信息（姓名、年龄、性别为必填项）</li>
                    <li>上传CSV格式的压力数据文件，或使用演示数据</li>
                    <li>点击"开始分析"进行智能分析</li>
                    <li>系统将生成专业的医疗分析报告</li>
                    <li>可在线查看报告或下载PDF版本</li>
                </ol>
            </div>
            
            <!-- 演示数据 -->
            <div class="demo-section">
                <h3>🎯 演示数据</h3>
                <p>如果您没有测试数据，可以使用我们生成的演示数据来体验系统功能。</p>
                <button type="button" class="btn btn-secondary" onclick="generateDemoData()">
                    生成演示数据
                </button>
            </div>
            
            <!-- 上传表单 -->
            <div class="upload-section">
                <form id="uploadForm" enctype="multipart/form-data">
                    <div class="form-row">
                        <div class="form-group">
                            <label for="patient_name">患者姓名 *</label>
                            <input type="text" id="patient_name" name="patient_name" required>
                        </div>
                        <div class="form-group">
                            <label for="patient_age">年龄 *</label>
                            <input type="number" id="patient_age" name="patient_age" min="1" max="120" required>
                        </div>
                    </div>
                    
                    <div class="form-row">
                        <div class="form-group">
                            <label for="patient_gender">性别 *</label>
                            <select id="patient_gender" name="patient_gender" required>
                                <option value="">请选择</option>
                                <option value="MALE">男</option>
                                <option value="FEMALE">女</option>
                            </select>
                        </div>
                        <div class="form-group">
                            <label for="test_type">测试类型</label>
                            <select id="test_type" name="test_type">
                                <option value="COMPREHENSIVE">综合评估</option>
                                <option value="WALK_4_LAPS">步道4圈</option>
                                <option value="WALK_7_LAPS">步道7圈</option>
                                <option value="STAND_LEFT">左脚站立</option>
                                <option value="STAND_RIGHT">右脚站立</option>
                                <option value="SIT_TO_STAND_5">起坐5次</option>
                            </select>
                        </div>
                    </div>
                    
                    <div class="form-row">
                        <div class="form-group">
                            <label for="patient_height">身高 (cm)</label>
                            <input type="number" id="patient_height" name="patient_height" min="50" max="250" step="0.1">
                        </div>
                        <div class="form-group">
                            <label for="patient_weight">体重 (kg)</label>
                            <input type="number" id="patient_weight" name="patient_weight" min="10" max="300" step="0.1">
                        </div>
                    </div>
                    
                    <div class="form-group">
                        <label>压力数据文件 (CSV格式) *</label>
                        <div class="file-upload">
                            <input type="file" id="file" name="file" accept=".csv" required>
                            <label for="file" class="file-upload-label">
                                <span id="file-label">点击选择CSV文件或拖拽文件到此处</span>
                            </label>
                        </div>
                    </div>
                    
                    <button type="submit" class="btn">🚀 开始分析</button>
                    <button type="button" class="btn btn-secondary" onclick="resetForm()">重置表单</button>
                </form>
            </div>
            
            <!-- 加载状态 -->
            <div id="loading" class="loading">
                <div class="spinner"></div>
                <p>正在分析中，请稍候...</p>
            </div>
            
            <!-- 结果显示 -->
            <div id="result" class="result-section"></div>
        </div>
    </div>
    
    <script>
        // 文件选择处理
        document.getElementById('file').addEventListener('change', function(e) {
            const fileName = e.target.files[0]?.name || '点击选择CSV文件或拖拽文件到此处';
            document.getElementById('file-label').textContent = fileName;
        });
        
        // 表单提交
        document.getElementById('uploadForm').addEventListener('submit', async function(e) {
            e.preventDefault();
            
            const formData = new FormData(this);
            const loading = document.getElementById('loading');
            const result = document.getElementById('result');
            
            // 显示加载状态
            loading.style.display = 'block';
            result.style.display = 'none';
            
            try {
                const response = await fetch('/upload', {
                    method: 'POST',
                    body: formData
                });
                
                const data = await response.json();
                
                loading.style.display = 'none';
                result.style.display = 'block';
                
                if (response.ok && data.status === 'success') {
                    result.className = 'result-section result-success';
                    result.innerHTML = `
                        <h3>✅ 分析完成！</h3>
                        <p><strong>报告ID:</strong> ${data.report_id}</p>
                        <p><strong>数据点数:</strong> ${data.data_points}</p>
                        <p><strong>综合评分:</strong> ${data.analysis_summary.overall_score.toFixed(1)}</p>
                        <p><strong>风险等级:</strong> ${data.analysis_summary.risk_level}</p>
                        <p><strong>置信度:</strong> ${(data.analysis_summary.confidence * 100).toFixed(1)}%</p>
                        <div style="margin-top: 20px;">
                            <a href="${data.report_url}" target="_blank" class="btn">📊 查看完整报告</a>
                        </div>
                    `;
                } else {
                    throw new Error(data.detail || '分析失败');
                }
            } catch (error) {
                loading.style.display = 'none';
                result.style.display = 'block';
                result.className = 'result-section result-error';
                result.innerHTML = `
                    <h3>❌ 分析失败</h3>
                    <p>${error.message}</p>
                `;
            }
        });
        
        // 生成演示数据
        async function generateDemoData() {
            try {
                const response = await fetch('/demo-data');
                const data = await response.json();
                
                if (data.status === 'success') {
                    // 创建CSV文件并自动下载
                    const blob = new Blob([data.csv_content], { type: 'text/csv' });
                    const url = window.URL.createObjectURL(blob);
                    const a = document.createElement('a');
                    a.style.display = 'none';
                    a.href = url;
                    a.download = 'demo_pressure_data.csv';
                    document.body.appendChild(a);
                    a.click();
                    window.URL.revokeObjectURL(url);
                    
                    alert(`演示数据已生成并下载！\\n数据点数: ${data.data_points}\\n描述: ${data.description}`);
                } else {
                    alert('生成演示数据失败: ' + data.message);
                }
            } catch (error) {
                alert('生成演示数据失败: ' + error.message);
            }
        }
        
        // 重置表单
        function resetForm() {
            document.getElementById('uploadForm').reset();
            document.getElementById('file-label').textContent = '点击选择CSV文件或拖拽文件到此处';
            document.getElementById('result').style.display = 'none';
        }
        
        // 拖拽上传
        const uploadSection = document.querySelector('.upload-section');
        
        uploadSection.addEventListener('dragover', function(e) {
            e.preventDefault();
            uploadSection.style.backgroundColor = '#e8f0fe';
        });
        
        uploadSection.addEventListener('dragleave', function(e) {
            e.preventDefault();
            uploadSection.style.backgroundColor = '#f8f9ff';
        });
        
        uploadSection.addEventListener('drop', function(e) {
            e.preventDefault();
            uploadSection.style.backgroundColor = '#f8f9ff';
            
            const files = e.dataTransfer.files;
            if (files.length > 0 && files[0].name.endsWith('.csv')) {
                document.getElementById('file').files = files;
                document.getElementById('file-label').textContent = files[0].name;
            } else {
                alert('请上传CSV格式的文件');
            }
        });
    </script>
</body>
</html>
"""

# 写入HTML模板文件
with open("templates/test_interface.html", "w", encoding="utf-8") as f:
    f.write(html_template)

if __name__ == "__main__":
    import math  # 导入math模块用于演示数据生成
    
    print("🚀 启动 SarcNeuro Edge 测试界面...")
    print(f"📍 访问地址: http://localhost:{config.app.port}")
    print(f"📊 测试界面: http://localhost:{config.app.port}")
    print(f"📚 API文档: http://localhost:{config.app.port}/docs")
    
    uvicorn.run(
        app,
        host=config.app.host,
        port=config.app.port,
        reload=config.app.debug,
        access_log=True,
        log_level="info"
    )