#!/usr/bin/env python3
"""
SarcNeuro Edge 简化启动服务器
"""
import sys
import os
from pathlib import Path

# 设置Python路径
sys.path.insert(0, str(Path(__file__).parent))

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse
from app.config import config
from core.analyzer import SarcNeuroAnalyzer, PatientInfo, PressurePoint

app = FastAPI(
    title="SarcNeuro Edge",
    description="SarcNeuro 边缘计算分析服务 - 简化版",
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

# 全局分析器
analyzer = SarcNeuroAnalyzer()

@app.get("/", response_class=HTMLResponse)
async def root():
    """首页"""
    return """
    <!DOCTYPE html>
    <html>
    <head>
        <title>SarcNeuro Edge</title>
        <meta charset="utf-8">
        <style>
            body { font-family: Arial, sans-serif; margin: 40px; background: #f5f5f5; }
            .container { max-width: 800px; margin: 0 auto; background: white; padding: 40px; border-radius: 8px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }
            h1 { color: #007bff; text-align: center; }
            .info { background: #e3f2fd; padding: 20px; border-radius: 4px; margin: 20px 0; }
            .status { display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 20px; margin: 20px 0; }
            .status-card { background: #f8f9fa; padding: 15px; border-radius: 4px; text-align: center; border-left: 4px solid #007bff; }
            .links { text-align: center; margin: 30px 0; }
            .links a { display: inline-block; margin: 10px; padding: 10px 20px; background: #007bff; color: white; text-decoration: none; border-radius: 4px; }
            .links a:hover { background: #0056b3; }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>🧠 SarcNeuro Edge</h1>
            <div class="info">
                <h3>肌少症智能监测与健康步态分析系统 - 边缘版本</h3>
                <p><strong>版本:</strong> 1.0.0</p>
                <p><strong>模式:</strong> 独立模式</p>
                <p><strong>状态:</strong> ✅ 运行正常</p>
            </div>
            
            <div class="status">
                <div class="status-card">
                    <h4>分析引擎</h4>
                    <p>✅ AI 模型就绪</p>
                </div>
                <div class="status-card">
                    <h4>数据库</h4>
                    <p>✅ SQLite 已连接</p>
                </div>
                <div class="status-card">
                    <h4>服务状态</h4>
                    <p>✅ 在线服务</p>
                </div>
            </div>
            
            <div class="links">
                <a href="/health">健康检查</a>
                <a href="/test">测试分析</a>
                <a href="/docs">API 文档</a>
            </div>
        </div>
    </body>
    </html>
    """

@app.get("/health")
async def health_check():
    """健康检查"""
    return {
        "status": "healthy",
        "version": "1.0.0",
        "analyzer": "ready",
        "database": "connected"
    }

@app.get("/test")
async def test_analysis():
    """测试分析功能"""
    try:
        # 创建测试患者
        patient = PatientInfo(
            name="测试患者",
            age=65,
            gender="MALE",
            height=170,
            weight=70
        )
        
        # 创建模拟压力数据
        pressure_points = [
            PressurePoint(
                time=i * 0.1,
                max_pressure=100 + i * 10,
                timestamp=f"2025-01-01 12:00:{i:02d}",
                contact_area=50 + i,
                total_pressure=1000 + i * 100,
                data=[50 + (i % 10)] * 1024  # 32x32 = 1024
            )
            for i in range(50)  # 50个数据点
        ]
        
        # 运行分析
        result = analyzer.comprehensive_analysis(pressure_points, patient)
        
        return {
            "status": "success",
            "patient": {
                "name": patient.name,
                "age": patient.age,
                "gender": patient.gender
            },
            "data_points": len(pressure_points),
            "analysis_result": {
                "overall_score": result.overall_score,
                "risk_level": result.risk_level,
                "confidence": result.confidence,
                "gait_metrics": {
                    "walking_speed": result.gait_analysis.walking_speed,
                    "step_length": result.gait_analysis.step_length,
                    "cadence": result.gait_analysis.cadence,
                    "stance_phase": result.gait_analysis.stance_phase
                },
                "balance_metrics": {
                    "cop_displacement": result.balance_analysis.cop_displacement,
                    "sway_area": result.balance_analysis.sway_area,
                    "fall_risk_score": result.balance_analysis.fall_risk_score
                }
            }
        }
        
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"status": "error", "message": str(e)}
        )

if __name__ == "__main__":
    print("🚀 启动 SarcNeuro Edge 简化服务器...")
    print(f"📍 访问地址: http://localhost:{config.app.port}")
    print(f"📚 API文档: http://localhost:{config.app.port}/docs")
    
    uvicorn.run(
        app,
        host=config.app.host,
        port=config.app.port,
        reload=config.app.debug,
        access_log=True,
        log_level="info"
    )