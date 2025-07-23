# SarcNeuro Edge - 独立分析服务

## 概述
SarcNeuro Edge是肌智神护AI平台的边缘计算版本，专为硬件设备本地部署设计。支持离线运行和云端同步。

## 特性
- 🔧 **独立运行** - 纯Python实现，无需Node.js或其他依赖
- 💾 **本地存储** - SQLite数据库，支持完全离线运行
- 📊 **离线报告** - 完整的HTML/PDF报告生成
- 🔄 **智能同步** - 自动检测网络，双向数据同步
- 🤖 **模型更新** - 联网时自动下载最新AI模型
- 📦 **轻量部署** - Docker容器或单一可执行文件

## 架构设计

```
sarcneuro-edge/
├── app/                    # 主应用
│   ├── __init__.py
│   ├── main.py            # FastAPI应用入口
│   ├── config.py          # 配置管理
│   └── database.py        # 数据库连接
├── core/                  # 核心功能
│   ├── __init__.py
│   ├── analyzer.py        # 分析引擎
│   ├── report_generator.py # 报告生成器
│   └── sync_manager.py    # 同步管理器
├── models/                # 数据模型
│   ├── __init__.py
│   ├── schemas.py         # Pydantic模型
│   └── database_models.py # SQLAlchemy模型
├── api/                   # API路由
│   ├── __init__.py
│   ├── analysis.py        # 分析接口
│   ├── patients.py        # 患者管理
│   ├── reports.py         # 报告接口
│   └── sync.py           # 同步接口
├── ml/                    # 机器学习模型
│   ├── __init__.py
│   ├── model_manager.py   # 模型管理器
│   └── models/           # 模型文件目录
├── templates/             # 报告模板
│   └── report.html       # HTML报告模板
├── data/                  # 数据目录
│   └── sarcneuro.db      # SQLite数据库
├── logs/                  # 日志目录
├── requirements.txt       # Python依赖
├── Dockerfile            # Docker配置
└── deploy.py             # 部署脚本
```

## 快速开始

### 1. 安装依赖
```bash
cd sarcneuro-edge
pip install -r requirements.txt
```

### 2. 初始化数据库
```bash
python -m app.database init
```

### 3. 启动服务
```bash
python -m app.main
```

服务将运行在 `http://localhost:8000`

### 4. Docker部署
```bash
docker build -t sarcneuro-edge .
docker run -p 8000:8000 -v ./data:/app/data sarcneuro-edge
```

## API接口

### 分析接口
- `POST /api/analysis/analyze` - 提交分析任务
- `GET /api/analysis/status/{task_id}` - 查询分析状态
- `GET /api/analysis/result/{task_id}` - 获取分析结果

### 患者管理
- `GET /api/patients` - 获取患者列表
- `POST /api/patients` - 创建患者
- `GET /api/patients/{patient_id}` - 获取患者详情

### 报告管理  
- `GET /api/reports` - 获取报告列表
- `GET /api/reports/{report_id}` - 获取报告详情
- `GET /api/reports/{report_id}/html` - 获取HTML报告
- `GET /api/reports/{report_id}/pdf` - 下载PDF报告

### 同步管理
- `POST /api/sync/check` - 检查同步状态
- `POST /api/sync/upload` - 上传本地数据到云端
- `POST /api/sync/download` - 从云端下载数据
- `POST /api/sync/models` - 同步AI模型

## 配置说明

### 环境变量
- `EDGE_MODE` - 运行模式 (standalone/connected)
- `CLOUD_API_URL` - 云端API地址
- `CLOUD_API_KEY` - 云端API密钥
- `DB_PATH` - SQLite数据库路径
- `LOG_LEVEL` - 日志级别

### 配置文件 (config.json)
```json
{
  "app": {
    "name": "SarcNeuro Edge",
    "version": "1.0.0",
    "debug": false
  },
  "database": {
    "url": "sqlite:///./data/sarcneuro.db"
  },
  "sync": {
    "enabled": true,
    "interval": 300,
    "cloud_url": "https://api.sarcneuro.com",
    "retry_count": 3
  },
  "models": {
    "cache_path": "./ml/models",
    "update_interval": 3600
  }
}
```

## 同步机制

### 数据同步
1. **增量同步** - 只同步变更的数据
2. **冲突解决** - 时间戳优先原则
3. **断点续传** - 网络中断后自动续传
4. **数据压缩** - 减少传输数据量

### 模型同步
1. **版本检查** - 定期检查模型版本
2. **热更新** - 不中断服务更新模型
3. **回滚机制** - 新模型异常时自动回滚
4. **差量更新** - 只下载模型差异部分

## 部署方案

### 硬件要求
- **最低配置**: 2GB RAM, 8GB存储, ARM64/x86_64
- **推荐配置**: 4GB RAM, 16GB存储, GPU可选

### 部署选项
1. **Docker容器** - 跨平台，易管理
2. **PyInstaller打包** - 单一可执行文件
3. **系统服务** - systemd服务方式运行

## 监控和维护

### 日志管理
- 应用日志：`logs/app.log`
- 分析日志：`logs/analysis.log` 
- 同步日志：`logs/sync.log`
- 错误日志：`logs/error.log`

### 健康检查
- `GET /health` - 服务健康状态
- `GET /health/db` - 数据库连接状态
- `GET /health/sync` - 同步服务状态
- `GET /health/models` - AI模型状态

## 开发指南

### 添加新的分析算法
1. 在 `core/analyzer.py` 中添加分析方法
2. 更新 `models/schemas.py` 中的数据模型
3. 在 `api/analysis.py` 中添加API接口
4. 编写单元测试

### 自定义报告模板
1. 修改 `templates/report.html`
2. 更新 `core/report_generator.py`
3. 测试报告生成功能

## 故障排除

### 常见问题
1. **数据库初始化失败** - 检查磁盘空间和权限
2. **模型加载失败** - 检查模型文件完整性
3. **同步连接超时** - 检查网络连接和云端服务状态
4. **内存不足** - 调整并发分析任务数量

### 诊断命令
```bash
# 检查服务状态
python -m app.main --check

# 数据库诊断
python -m app.database diagnose

# 模型验证  
python -m core.analyzer validate

# 同步测试
python -m core.sync_manager test
```

## 版本历史
- v1.0.0 - 初始版本，基础功能完成
- v1.0.1 - 添加同步功能
- v1.0.2 - 优化模型更新机制