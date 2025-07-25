# 多COM口步道设备兼容配置说明

## 功能概述

为了兼容不同类型的步道设备，系统现已支持：
- **单COM口步道设备**：1个COM口，输出3×1024字节数据（原有功能）
- **双COM口步道设备**：2个COM口，各输出1×1024字节数据，系统自动合并为2×1024字节
- **三COM口步道设备**：3个COM口，各输出1×1024字节数据，系统自动合并为3×1024字节

## 新增文件

### 1. `multi_port_interface.py`
多串口接口模块，负责：
- 管理多个COM口的连接
- 同步多个设备的数据
- 合并多个1024字节数据帧
- 提供统一的数据接口

### 2. `test_multi_device.py`
多设备兼容性测试程序，提供：
- 图形化测试界面
- 单/双/三COM口设备测试
- 实时数据接收验证
- 设备配置向导集成

## 核心更新

### `serial_interface.py` 更新
```python
# 新增设备模式设置
def set_device_mode(self, device_type):
    """设置设备模式
    Args:
        device_type (str): 
            - "single": 单设备，1x1024字节
            - "dual_1024": 双设备，2x1024字节  
            - "triple_1024": 三设备，3x1024字节
            - "walkway": 步道设备，3x1024字节（向后兼容）
    """
```

### `device_config.py` 更新
```python
# 扩展的设备类型定义
self.device_types = {
    'footpad': {'name': '脚垫', 'icon': '👣', 'array_size': '32x32', 'com_ports': 1},
    'cushion': {'name': '坐垫', 'icon': '🪑', 'array_size': '32x32', 'com_ports': 1}, 
    'walkway': {'name': '步道(单口)', 'icon': '🚶', 'array_size': '32x96', 'com_ports': 1},
    'walkway_dual': {'name': '步道(双口)', 'icon': '🚶‍♂️', 'array_size': '32x64', 'com_ports': 2},
    'walkway_triple': {'name': '步道(三口)', 'icon': '🚶‍♀️', 'array_size': '32x96', 'com_ports': 3}
}
```

## 使用方法

### 1. 测试多设备兼容性（推荐）
```bash
python test_multi_device.py
```
- 打开图形化测试界面
- 使用设备配置向导配置COM口
- 选择相应的测试类型进行验证

### 2. 直接使用多端口接口
```python
from multi_port_interface import create_multi_port_interface

# 创建双设备接口
ports = ["COM3", "COM4"]
multi_interface = create_multi_port_interface("dual_1024", ports)

# 连接所有端口
if multi_interface.connect_all_ports():
    # 获取合并后的数据
    while True:
        combined_data = multi_interface.get_combined_data()
        if combined_data:
            print(f"合并数据: {combined_data['data_length']}字节")
```

### 3. 设备配置向导
```python
from device_config import DeviceConfigDialog

# 在主窗口中调用
config_dialog = DeviceConfigDialog(parent_window)
result = config_dialog.show_dialog()

if result:
    for device_id, config in result.items():
        if config['com_ports'] > 1:
            # 多端口设备
            ports = config['ports']  # 端口列表
            device_type = config['device_type']  # dual_1024 或 triple_1024
        else:
            # 单端口设备
            port = config['port']
```

## 设备配置格式

### 单端口设备配置
```python
{
    'walkway': {
        'port': 'COM3',
        'ports': ['COM3'],
        'name': '步道(单口)',
        'icon': '🚶',
        'array_size': '32x96',
        'com_ports': 1,
        'device_type': 'walkway'
    }
}
```

### 多端口设备配置
```python
{
    'walkway_dual': {
        'ports': ['COM3', 'COM4'],
        'port': None,  # 多端口时为None
        'name': '步道(双口)',
        'icon': '🚶‍♂️',
        'array_size': '32x64',
        'com_ports': 2,
        'device_type': 'dual_1024'
    }
}
```

## 数据格式

### 单设备数据帧
```python
frame_data = {
    'data': bytes(1024),           # 原始1024字节数据
    'timestamp': '14:30:25.123',
    'frame_number': 1001,
    'data_length': 1024
}
```

### 多设备合并数据帧
```python
combined_frame = {
    'data': bytes(2048),           # 合并后数据 (2x1024 或 3x1024)
    'timestamp': '14:30:25.123',
    'frame_number': 1001,
    'data_length': 2048,
    'device_frames': 2,            # 合并的设备数量
    'device_type': 'dual_1024',    # 设备类型
    'source_devices': [0, 1]       # 数据来源设备ID
}
```

## 向后兼容性

- 现有的单COM口步道设备代码无需修改
- `is_walkway_mode` 和相关变量保持兼容
- 原有的步道模式 (walkway) 继续支持
- 数据处理接口保持一致

## 故障排除

### 1. 端口连接失败
- 检查COM口是否被其他程序占用
- 确认设备驱动正确安装
- 验证波特率设置 (1000000 bps)

### 2. 数据同步问题
- 确保所有设备时钟同步
- 检查设备间的信号线连接
- 验证帧头格式 (AA 55 03 99)

### 3. 配置保存失败
- 检查 `device_config.db` 文件权限
- 确保程序具有写入权限
- 清理损坏的配置文件

## 性能优化

- 多端口接口使用独立线程处理数据合并
- 减少不必要的数据复制操作
- 支持批量数据获取 (`get_multiple_data`)
- 自动清理超时的数据缓冲区

## 注意事项

1. **端口数量匹配**：配置的端口数量必须与设备类型匹配
2. **数据帧大小**：每个端口必须输出标准的1024字节数据帧
3. **帧头格式**：所有设备必须使用相同的帧头格式
4. **时钟同步**：多设备间需要良好的时钟同步
5. **资源管理**：及时释放不用的串口连接

通过以上配置，系统现在可以灵活支持各种类型的步道设备，无论是单COM口还是多COM口配置。