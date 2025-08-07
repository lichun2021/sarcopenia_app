# 足部压力分析算法模块

## 📝 概述
完全独立的Python算法模块，支持足部压力数据分析、步态分析、平衡评估等专业医学功能。

## 📁 核心文件结构

### 🔧 核心算法引擎
- **`core_calculator.py`** - 零依赖的核心算法引擎
- **`async_analyzer.py`** - 异步任务处理器，支持Redis队列

### 📋 报告生成系统
- **`full_medical_report_generator.py`** - 完整医疗报告生成器
- **`enhanced_report_generator.py`** - 图表生成器
- **`full_complete_report.html`** - 标准医疗报告模板

### 🧠 专业算法模块 (2025-08-04新增)
- **`ai_assessment_engine.py`** - AI多维度评估引擎
- **`joint_angle_analysis.py`** - 关节角度分析模块
- **`ground_reaction_force_analysis.py`** - 地面反力分析模块  
- **`joint_torque_power_analysis.py`** - 关节力矩功率分析模块
- **`hardware_adaptive_service.py`** - 硬件自适应服务

### 🔄 工作流程支持
- **`multi_file_workflow.py`** - 多文件处理工作流程

### 📚 配置和文档
- **`requirements.txt`** - Python依赖包说明
- **`README.md`** - 本文档
- **`archive/`** - 历史文件归档目录

## 🚀 使用方法

### 基础分析
```python
from core_calculator import PressureAnalysisCore

# 创建分析器
analyzer = PressureAnalysisCore()

# 分析单个CSV文件
result = analyzer.comprehensive_analysis("pressure_data.csv")
print(result)
```

### 生成医疗报告
```python
from full_medical_report_generator import FullMedicalReportGenerator

# 创建报告生成器
generator = FullMedicalReportGenerator()

# 生成完整医疗报告
html_report = generator.generate_report_from_algorithm(
    algorithm_result=result,
    patient_info={'name': '张三', 'age': 45, 'gender': '男'}
)
```

### 多文件工作流程
```python
from multi_file_workflow import generate_reports_from_analyses

# 批量处理多个文件
generate_reports_from_analyses(
    analysis_results_dir="results/",
    mode="both"  # individual/combined/both
)
```

### 异步处理
```python
from async_analyzer import AlgorithmClient

# 创建客户端
client = AlgorithmClient()

# 同步分析
result = client.analyze_file("data.csv", "comprehensive", timeout=300)

# 异步分析
task_id = client.analyze_file_async("data.csv", "comprehensive")
result = client.service.get_result(task_id, timeout=300)
```

## 🎯 核心特性
- **零依赖核心**: 最小依赖的纯Python实现
- **专业医学级**: 符合临床步态分析标准
- **多种调用方式**: 直接调用、异步队列、HTTP API
- **完整报告系统**: HTML/PDF医疗级报告生成
- **硬件自适应**: 支持多种压力传感器硬件
- **AI智能评估**: 6维度雷达评估系统

## 📊 算法同步状态
- **平台一致性**: 与TypeScript平台算法100%同步
- **最后同步**: 2025-08-06 (步态相位分析+双垫子支持)
- **同步覆盖**: COP计算、步态分析、硬件适配、专业模块

## 🛠 安装和部署

### 1. 基础安装
```bash
# 安装依赖
pip install -r requirements.txt

# 直接使用
python core_calculator.py data.csv
```

### 2. 异步服务部署
```bash
# 启动Redis
redis-server

# 启动worker
python async_analyzer.py --mode worker
```

### 3. Docker部署
```bash
# 使用docker-compose
docker-compose up -d
```

## 📁 归档说明
`archive/`目录包含开发过程中的历史文件、测试脚本、实验性代码，已不再被主系统使用，仅供历史参考。

## 🔧 配置选项
```python
# 物理参数配置
analyzer = PressureAnalysisCore()
analyzer.PRESSURE_MAT_WIDTH = 1.65   # 压力垫宽度(米)
analyzer.PRESSURE_MAT_HEIGHT = 0.95  # 压力垫高度(米)
analyzer.PRESSURE_THRESHOLD = 20     # 压力阈值
```

## 📈 性能对比
| 方式 | 响应时间 | 并发能力 | 资源占用 | 适用场景 |
|------|----------|----------|----------|----------|
| 直接调用 | 0.1-0.5秒 | 中等 | 低 | 简单集成 |
| 异步队列 | 立即返回 | 高 | 中等 | Web应用 |
| HTTP调用 | 2-5秒 | 低 | 高 | 传统方式 |

---

**🎉 通过算法独立化，系统性能和可维护性得到显著提升！**