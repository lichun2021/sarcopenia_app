# 独立算法模块

## 📝 概述
此文件夹包含完全独立于HTTP服务的Python算法模块，支持多种调用方式。

## 🔧 核心文件

### 1. **core_calculator.py**
**核心算法引擎** - 零依赖的纯Python实现
```python
from core_calculator import PressureAnalysisCore

analyzer = PressureAnalysisCore()
result = analyzer.comprehensive_analysis('data.csv')
```

**功能**:
- COP压力中心计算
- 步态参数分析（步长、步频、速度）
- 平衡指标计算（摆动面积、位移距离）
- 基于物理尺寸的精确计算

### 2. **async_analyzer.py**
**异步任务服务** - 基于Redis消息队列的高并发处理
```python
from async_analyzer import AlgorithmClient

client = AlgorithmClient()
result = client.analyze_file('data.csv', 'comprehensive')
```

**功能**:
- Redis消息队列任务调度
- 支持优先级处理
- 异步结果获取
- 工作进程管理

### 3. **full_medical_report_generator.py**
**医疗报告生成器** - 与平台报告100%一致的HTML报告
```python
from full_medical_report_generator import FullMedicalReportGenerator

generator = FullMedicalReportGenerator()
html_report = generator.generate_report(data, options)
```

**功能**:
- 完整医疗报告HTML模板
- 模块化显示控制
- 患者信息、步态数据、医学建议
- 可直接打印为PDF

### 4. **requirements.txt**
Python依赖包列表

## 📚 知识库文档
算法相关的知识库和文档已移动到 `/docs/` 文件夹：
- `MULTI_DEVICE_KNOWLEDGE_BASE.md` - 多设备算法知识库
- `平台报告PDF解决方案.md` - PDF生成方案
- `独立报告生成方案.md` - 独立报告方案

## 🗂️ 归档文件
过时的测试文件、示例代码和重复的报告生成器已移动到 `archive/` 文件夹。

## 🚀 使用方式

### 方式1: 直接调用（推荐）

**适用场景**: 简单集成，性能要求高

```python
from core_calculator import PressureAnalysisCore

# 创建分析器
analyzer = PressureAnalysisCore()

# 分析CSV文件
result = analyzer.comprehensive_analysis("data.csv")

# 单独分析步态
pressure_data = analyzer.parse_csv_data(csv_content)
gait_events = analyzer.detect_gait_events([pressure_data])
step_metrics = analyzer.calculate_step_metrics(gait_events)

# 单独分析平衡
balance_metrics = analyzer.analyze_balance([pressure_data])
```

### 方式2: 异步队列（适合Web应用）

**适用场景**: Web应用，大数据处理，需要解耦

```python
from async_analyzer import AlgorithmClient

# 创建客户端
client = AlgorithmClient()

# 同步分析（等待结果）
result = client.analyze_file("data.csv", "comprehensive", timeout=300)

# 异步分析（立即返回任务ID）
task_id = client.analyze_file_async("data.csv", "comprehensive")
result = client.service.get_result(task_id, timeout=300)
```

### 方式3: 命令行调用

```bash
# 直接分析
python core_calculator.py data.csv

# 启动异步工作进程
python async_analyzer.py --mode worker

# 客户端提交任务
python async_analyzer.py --mode client --csv-file data.csv

# 查看队列状态
python async_analyzer.py --mode status
```

## 🛠 安装和部署

### 1. 安装依赖

```bash
# 创建虚拟环境
python -m venv venv
source venv/bin/activate  # Linux/Mac
# venv\Scripts\activate   # Windows

# 安装依赖
pip install numpy pandas redis
```

### 2. 直接调用部署

无需额外配置，直接导入使用：

```python
# 单文件部署，零配置
from algorithms.core_calculator import PressureAnalysisCore
analyzer = PressureAnalysisCore()
```

### 3. 异步服务部署

#### 启动Redis
```bash
# 安装Redis（Ubuntu）
sudo apt install redis-server

# 启动Redis
redis-server

# 或使用Docker
docker run -d -p 6379:6379 redis:alpine
```

#### 启动算法工作进程
```bash
cd algorithms
python async_analyzer.py --mode worker --redis-host localhost
```

#### 多进程部署
```bash
# 启动多个worker进程处理不同类型任务
python async_analyzer.py --mode worker &
python async_analyzer.py --mode worker &
python async_analyzer.py --mode worker &
```

### 4. 生产环境部署

#### Docker部署
```dockerfile
# Dockerfile
FROM python:3.9-slim

WORKDIR /app
COPY algorithms/ ./algorithms/
COPY requirements.txt .

RUN pip install -r requirements.txt

# 启动worker
CMD ["python", "algorithms/async_analyzer.py", "--mode", "worker"]
```

```yaml
# docker-compose.yml
version: '3.8'
services:
  redis:
    image: redis:alpine
    ports:
      - "6379:6379"
  
  algorithm-worker-1:
    build: .
    depends_on:
      - redis
    environment:
      - REDIS_HOST=redis
    
  algorithm-worker-2:
    build: .
    depends_on:
      - redis
    environment:
      - REDIS_HOST=redis
```

#### 启动服务
```bash
docker-compose up -d
```

## 📊 性能对比

| 方式 | 响应时间 | 并发能力 | 资源占用 | 适用场景 |
|------|----------|----------|----------|----------|
| HTTP调用 | 2-5秒 | 低（阻塞） | 高 | 原有方式 |
| 直接调用 | 0.1-0.5秒 | 中等 | 低 | 简单集成 |
| 异步队列 | 立即返回 | 高 | 中等 | Web应用 |

## 🔧 配置选项

### 核心算法配置
```python
analyzer = PressureAnalysisCore()

# 修改物理参数
analyzer.PRESSURE_MAT_WIDTH = 1.65   # 压力垫宽度(米)
analyzer.PRESSURE_MAT_HEIGHT = 0.95  # 压力垫高度(米)
analyzer.PRESSURE_THRESHOLD = 20     # 压力阈值
```

### 异步服务配置
```python
# Redis连接配置
service = AsyncAlgorithmService(
    redis_host='localhost',
    redis_port=6379,
    redis_db=0
)

# 任务超时配置
result = client.get_result(task_id, timeout=600)  # 10分钟超时
```

## 🧪 测试和验证

### 运行测试套件
```bash
cd algorithms
python example_usage.py
```

### 功能测试
```bash
# 测试核心算法
python -c "
from core_calculator import PressureAnalysisCore
analyzer = PressureAnalysisCore()
print('算法核心加载成功')
"

# 测试异步服务（需要Redis）
python -c "
from async_analyzer import AlgorithmClient
client = AlgorithmClient()
status = client.service.get_queue_status()
print('异步服务连接成功:', status)
"
```

### 性能测试
```bash
# 创建测试数据并运行性能对比
python example_usage.py 2>&1 | grep "耗时"
```

## 🔄 集成到现有系统

### 替换现有HTTP调用

**原有方式:**
```typescript
// 原有的HTTP API调用
const response = await fetch('/api/analysis/sarcopenia', {
  method: 'POST',
  body: formData
});
```

**新方式1: 直接调用Python**
```typescript
// 通过child_process调用Python
import { spawn } from 'child_process';

const python = spawn('python', ['algorithms/core_calculator.py', csvPath]);
python.stdout.on('data', (data) => {
  const result = JSON.parse(data.toString());
  // 处理结果
});
```

**新方式2: 异步队列**
```typescript
// 通过Redis队列
import Redis from 'ioredis';
const redis = new Redis();

// 提交任务
const taskId = uuidv4();
await redis.rpush('analysis_tasks', JSON.stringify({
  id: taskId,
  type: 'comprehensive',
  data: { csv_path: csvPath }
}));

// 轮询结果
const result = await redis.get(`result:${taskId}`);
```

## 🚨 故障排除

### 常见问题

1. **Redis连接失败**
   ```bash
   # 检查Redis状态
   redis-cli ping
   
   # 如果无响应，重启Redis
   sudo systemctl restart redis
   ```

2. **Python依赖缺失**
   ```bash
   # 安装缺失的包
   pip install numpy pandas redis
   ```

3. **CSV文件格式错误**
   ```python
   # 检查CSV格式
   analyzer = PressureAnalysisCore()
   data = analyzer.parse_csv_data(csv_content)
   print(f"解析到 {len(data)} 行数据")
   ```

4. **内存不足**
   ```bash
   # 监控内存使用
   top -p $(pgrep -f async_analyzer)
   
   # 调整worker进程数量
   # 减少并发worker数量
   ```

### 日志查看
```bash
# 查看worker日志
python async_analyzer.py --mode worker 2>&1 | tee worker.log

# 查看Redis日志
tail -f /var/log/redis/redis-server.log
```

## 📈 扩展计划

### 短期优化（1-2周）
- [ ] 添加GPU加速支持
- [ ] 实现结果缓存机制  
- [ ] 添加监控和指标

### 中期扩展（1个月）
- [ ] 支持更多分析类型
- [ ] 实现算法版本管理
- [ ] 添加A/B测试功能

### 长期规划（3个月）
- [ ] 微服务架构完整实现
- [ ] 机器学习模型在线更新
- [ ] 分布式处理支持

## 📞 技术支持

如有问题或建议，请：
1. 查看本文档的故障排除部分
2. 运行 `python example_usage.py` 进行测试
3. 检查系统日志和错误信息

---

**🎉 通过算法独立化，系统性能和可维护性得到显著提升！**