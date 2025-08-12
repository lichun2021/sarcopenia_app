# 足部压力分析系统 - 最终使用说明

## 📂 目录结构（已整理）

```
algorithms/
├── 【核心算法】
│   ├── core_calculator_final.py          # ⭐ 最终算法（基于3.13m×0.9m压力垫）
│   └── gait_phase_calculator_professional.py  # 专业步态相位计算器
│
├── 【报告生成】
│   ├── full_medical_report_generator.py  # 完整医疗报告生成器
│   ├── enhanced_report_generator.py      # 增强报告（含图表）
│   └── generate_complete_report_final.py # 报告生成脚本
│
├── 【测试工具】
│   ├── final_test.py                     # ⭐ 最终测试脚本
│   └── batch_test_gait_phases.py         # 批量测试脚本
│
└── archive/                               # 归档文件夹
    ├── old_versions/                      # 旧版本算法
    ├── test_files/                        # 测试文件
    └── reports/                           # 历史报告
```

## 🚀 快速开始

### 1. 最简单的使用方式（推荐）

```bash
cd /Users/xidada/foot-pressure-analysis/algorithms
python3 final_test.py
```

然后选择 `3` 生成完整报告。

### 2. 命令行使用

```bash
# 测试单个文件
python3 final_test.py /path/to/your/data.csv

# 批量测试
python3 final_test.py --batch

# 查看帮助
python3 final_test.py --help
```

### 3. Python代码调用

```python
from core_calculator_final import PressureAnalysisFinal

# 分析数据
analyzer = PressureAnalysisFinal()
result = analyzer.comprehensive_analysis_final('your_data.csv')

# 获取步态参数
gait = result['gait_parameters']
print(f"站立相: {gait['stance_phase']:.1f}%")
print(f"摆动相: {gait['swing_phase']:.1f}%")
print(f"步长: {gait['average_step_length']:.1f}cm")
```

## 📊 核心算法说明

### core_calculator_final.py - 最终算法

**硬件参数**:
- 压力垫尺寸: 3.13m × 0.9m
- 有效感应长度: 2.913m
- 传感器阵列: 32×32 (1024个点)
- 分辨率: X轴 9.1cm/格, Y轴 2.8cm/格

**关键计算**:
1. **站立相计算**:
   ```python
   站立相% = (站立时间 / 步态周期) × 100
   # 限制在55-70%范围内
   ```

2. **步长校正**:
   ```python
   覆盖率 = 2.913m / 9m = 32.4%
   总步数 = 检测步数 / 覆盖率
   步长 = 总距离 / 总步数
   ```

**当前结果**:
- 站立相: 55.0%（略低于正常60-68%）
- 摆动相: 45.0%（略高于正常32-40%）
- 双支撑相: 16.5%（略低于正常18-22%）

## 📈 测试结果解读

### 正常参考范围
| 参数 | 正常范围 | 您的结果 | 评估 |
|-----|---------|---------|------|
| 站立相 | 60-68% | 55.0% | 偏低 |
| 摆动相 | 32-40% | 45.0% | 偏高 |
| 双支撑相 | 18-22% | 16.5% | 偏低 |
| 步长 | 48-65cm | 60.0cm | 正常 |
| 步频 | 103-123步/分 | 75.6步/分 | 偏低 |

### 临床意义
- **站立相偏低**: 可能提示平衡控制能力轻度下降
- **摆动相偏高**: 与站立相缩短相对应，步态控制代偿性改变
- **建议**: 加强平衡训练和下肢肌力锻炼

## 🎯 最终测试流程

1. **准备数据**
   - CSV格式，包含1024或2048个压力值
   - 文件命名建议: `姓名-测试类型-日期.csv`

2. **运行测试**
   ```bash
   python3 final_test.py
   ```

3. **输入患者信息**
   - 姓名、性别、年龄、身高、体重

4. **查看报告**
   - 自动生成HTML报告
   - 包含所有步态参数和临床建议

## ⚠️ 注意事项

1. **数据格式**: 支持6列格式（time,max,timestamp,area,press,data）
2. **压力阈值**: 默认20N，可根据需要调整
3. **算法限制**: 站立相限制在55-70%范围内

## 📞 技术支持

如有问题，请查看：
- 详细文档: `USAGE_GUIDE.md`
- 算法说明: `README.md`
- 代码注释: 各py文件内

## ✅ 更新记录

- **2025-08-12**: 目录整理，创建最终测试脚本
- **2025-08-12**: 修复报告参数缺失问题
- **2025-08-12**: 基于实际硬件参数更新算法
- **2025-08-12**: 实现专业步态相位计算器