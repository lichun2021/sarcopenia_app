#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
渐进式硬件自适应服务 - Python版本
优先使用固定布局硬件，格式不匹配时自动降级到通用算法
确保系统永远不会因为硬件问题而卡住或报错

与平台算法(hardwareAdaptiveService.ts)完全同步
同步时间: 2025-08-04
"""

import numpy as np
from typing import Dict, List, Optional, Any
from enum import Enum
from dataclasses import dataclass
import logging

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class HardwareMatchResult(Enum):
    """硬件匹配结果"""
    EXACT_MATCH = "exact_match"        # 精确匹配已知硬件
    PARTIAL_MATCH = "partial_match"    # 部分匹配（尺寸相近）
    FALLBACK = "fallback"              # 使用通用算法
    ERROR_RECOVERY = "error_recovery"  # 错误恢复模式

@dataclass
class HardwareSpec:
    """硬件规格定义"""
    id: str
    name: str
    width: float        # 物理宽度(m)
    height: float       # 物理高度(m)
    grid_width: int     # 网格宽度
    grid_height: int    # 网格高度
    data_format: str    # 数据格式
    priority: int       # 优先级（数字越小优先级越高）
    threshold: float    # 压力阈值
    
    def __post_init__(self):
        self.grid_scale_x = self.width / self.grid_width
        self.grid_scale_y = self.height / self.grid_height
        self.total_sensors = self.grid_width * self.grid_height

@dataclass
class HardwareMatchInfo:
    """硬件匹配信息"""
    result: HardwareMatchResult
    hardware: Optional[HardwareSpec]
    confidence: float
    message: str

class HardwareAdaptiveService:
    """硬件自适应服务 - 与平台算法完全同步"""
    
    def __init__(self):
        """初始化硬件自适应服务"""
        self.fixed_hardware_database = self._initialize_hardware_database()
        self.fallback_spec = self._setup_fallback_spec()
        logger.info("🔧 硬件自适应服务初始化完成")
    
    def _initialize_hardware_database(self) -> List[HardwareSpec]:
        """初始化固定硬件数据库（与平台算法完全一致）"""
        
        hardware_list = [
            # 优先级1：当前系统的主要硬件
            # 双垫子步道配置（2个32x32传感器，共2048数据点）
            HardwareSpec(
                id="dual_walkway_pads",
                name="双垫子步道系统 3130×900mm",
                width=3.13,  # 两个垫子总宽度
                height=0.90,
                grid_width=64,  # 2个32列 = 64列
                grid_height=32,
                data_format="64col_2048",  # 新的数据格式
                priority=1,
                threshold=20
            ),
            HardwareSpec(
                id="gait_walkway_main",
                name="主步道压力垫 1565×900mm",
                width=1.565,
                height=0.90,
                grid_width=32,
                grid_height=32,
                data_format="32col",
                priority=2,  # 降低优先级
                threshold=20
            ),
            HardwareSpec(
                id="foot_pad_1100x650",
                name="足压感知垫 1100×650mm",
                width=1.10,
                height=0.65,
                grid_width=32,
                grid_height=32,
                data_format="32col",
                priority=1,
                threshold=20
            ),
            HardwareSpec(
                id="hip_pad_550x530",
                name="臀部压力垫 550×530mm",
                width=0.55,
                height=0.53,
                grid_width=32,
                grid_height=32,
                data_format="32col",
                priority=1,
                threshold=20
            ),
            
            # 优先级2：兼容的标准硬件
            HardwareSpec(
                id="standard_foot_pad",
                name="标准足压垫 1000×600mm",
                width=1.00,
                height=0.60,
                grid_width=32,
                grid_height=32,
                data_format="32col",
                priority=2,
                threshold=20
            ),
            HardwareSpec(
                id="large_walkway",
                name="大型步道 2000×1000mm",
                width=2.00,
                height=1.00,
                grid_width=32,
                grid_height=32,
                data_format="32col",
                priority=2,
                threshold=20
            ),
            
            # 优先级3：扩展硬件（为未来预留）
            HardwareSpec(
                id="multi_sensor_platform",
                name="多传感器平台 2000×2000mm",
                width=2.00,
                height=2.00,
                grid_width=64,
                grid_height=64,
                data_format="64col",
                priority=3,
                threshold=20
            )
        ]
        
        logger.info(f"📋 加载了 {len(hardware_list)} 种硬件规格")
        return hardware_list
    
    def _setup_fallback_spec(self) -> HardwareSpec:
        """设置通用回退参数（与平台算法一致）"""
        return HardwareSpec(
            id="fallback",
            name="通用算法模式",
            width=1.565,      # 默认宽度
            height=0.90,      # 默认高度
            grid_width=32,    # 默认网格宽度
            grid_height=32,   # 默认网格高度
            data_format="32col",
            priority=999,
            threshold=20
        )
    
    def match_hardware(self, data: Any, filename: str = "") -> HardwareMatchInfo:
        """
        智能硬件匹配 - 核心接口（与平台算法完全同步）
        
        Args:
            data: 数据（可以是列表、数组等）
            filename: 文件名（可选）
            
        Returns:
            HardwareMatchInfo: 匹配结果信息
        """
        try:
            logger.info("🔍 开始渐进式硬件匹配...")
            
            # 第一步：解析数据获取基本信息
            data_info = self._parse_data_info(data, filename)
            logger.info(f"📊 数据信息: {data_info['rows']}×{data_info['cols']} ({data_info['format']})")
            
            # 第二步：按优先级尝试匹配固定硬件
            for hardware in self._get_sorted_hardware():
                confidence = self._calculate_match_confidence(hardware, data_info, filename)
                
                if confidence >= 90:
                    logger.info(f"✅ 精确匹配: {hardware.name} (置信度: {confidence}%)")
                    return HardwareMatchInfo(
                        result=HardwareMatchResult.EXACT_MATCH,
                        hardware=hardware,
                        confidence=confidence,
                        message=f"精确匹配硬件: {hardware.name}"
                    )
                elif confidence >= 60:
                    logger.info(f"⚠️ 部分匹配: {hardware.name} (置信度: {confidence}%)")
                    return HardwareMatchInfo(
                        result=HardwareMatchResult.PARTIAL_MATCH,
                        hardware=hardware,
                        confidence=confidence,
                        message=f"部分匹配硬件: {hardware.name}"
                    )
            
            # 第三步：没有找到合适的固定硬件，使用通用算法
            logger.info("ℹ️ 未匹配固定硬件，使用通用算法")
            return HardwareMatchInfo(
                result=HardwareMatchResult.FALLBACK,
                hardware=self.fallback_spec,
                confidence=50,
                message="使用通用算法模式"
            )
            
        except Exception as e:
            logger.error(f"⚠️ 硬件匹配过程出错，启用错误恢复模式: {str(e)}")
            return HardwareMatchInfo(
                result=HardwareMatchResult.ERROR_RECOVERY,
                hardware=self.fallback_spec,
                confidence=0,
                message=f"错误恢复模式: {str(e)}"
            )
    
    def _parse_data_info(self, data: Any, filename: str) -> Dict:
        """解析数据信息（与平台算法同步）"""
        try:
            data_info = {
                'format': 'unknown',
                'cols': 0,
                'rows': 0,
                'total_points': 0,
                'filename': filename.lower()
            }
            
            if isinstance(data, list) and len(data) > 0:
                data_info['rows'] = len(data)
                
                # 检查第一行数据格式
                first_row = data[0]
                
                # 首先检查是否有data字段（字典格式）
                if isinstance(first_row, dict) and 'data' in first_row:
                    data_field = first_row['data']
                    if isinstance(data_field, list):
                        data_length = len(data_field)
                        if data_length == 2048:
                            data_info.update({
                                'format': '6col_2048',
                                'cols': 6,
                                'total_points': len(data)
                            })
                        elif data_length == 1024:
                            data_info.update({
                                'format': '6col_1024',
                                'cols': 6,
                                'total_points': len(data)
                            })
                elif hasattr(first_row, 'data') and hasattr(first_row.data, '__len__'):
                    # 对象格式（类似肌少症格式）
                    if len(first_row.data) == 2048:
                        data_info.update({
                            'format': '6col_2048',
                            'cols': 6,
                            'total_points': len(data)
                        })
                    elif len(first_row.data) == 1024:
                        data_info.update({
                            'format': '6col_1024',
                            'cols': 6,
                            'total_points': len(data)
                        })
                elif isinstance(first_row, (list, tuple, np.ndarray)):
                    # 数组格式
                    cols = len(first_row)
                    data_info['cols'] = cols
                    data_info['total_points'] = len(data)
                    
                    if cols >= 64:
                        data_info['format'] = '64col_2048'
                    elif cols >= 32:
                        data_info['format'] = '32col'
                    elif cols == 6:
                        # 检查是否是压缩的2048或1024数据
                        if isinstance(first_row, dict) and 'data' in first_row:
                            if len(first_row['data']) == 2048:
                                data_info['format'] = '6col_2048'
                            elif len(first_row['data']) == 1024:
                                data_info['format'] = '6col_1024'
                        else:
                            data_info['format'] = '6col_1024'
                elif hasattr(first_row, '__dict__'):
                    # 对象格式，尝试获取data属性
                    if hasattr(first_row, 'data') and isinstance(first_row.data, (list, np.ndarray)):
                        if len(first_row.data) == 2048:
                            data_info.update({
                                'format': '6col_2048',
                                'cols': 6,
                                'total_points': len(data)
                            })
                        elif len(first_row.data) == 1024:
                            data_info.update({
                                'format': '6col_1024',
                                'cols': 6,
                                'total_points': len(data)
                            })
            
            return data_info
            
        except Exception as e:
            logger.error(f"数据解析失败: {e}")
            raise ValueError(f"数据解析失败: {e}")
    
    def _calculate_match_confidence(self, hardware: HardwareSpec, data_info: Dict, filename: str) -> float:
        """计算硬件匹配置信度（与平台算法完全同步）"""
        confidence = 0.0
        
        # 数据格式匹配（权重40%）
        if hardware.data_format == data_info['format']:
            confidence += 40
        elif data_info['format'] == 'unknown' and hardware.data_format == '32col':
            confidence += 20  # 给默认格式一些分数
        
        # 网格尺寸匹配（权重30%）
        if hardware.data_format == '64col_2048' and data_info['format'] in ['64col_2048', '6col_2048']:
            confidence += 30
        elif hardware.data_format == '32col' and data_info['cols'] >= 32:
            confidence += 30
        elif hardware.data_format == '6col_1024' and data_info['format'] == '6col_1024':
            confidence += 30
        
        # 文件名线索（权重20%）
        filename_lower = filename.lower()
        if 'gait' in filename_lower or '步态' in filename_lower:
            if 'walkway' in hardware.id or 'gait' in hardware.id:
                confidence += 20
        elif 'foot' in filename_lower or '足' in filename_lower:
            if 'foot' in hardware.id:
                confidence += 20
        elif 'hip' in filename_lower or '臀' in filename_lower:
            if 'hip' in hardware.id:
                confidence += 20
        
        # 优先级加分（权重10%）
        if hardware.priority == 1:
            confidence += 10
        elif hardware.priority == 2:
            confidence += 5
        
        return min(100.0, confidence)
    
    def _get_sorted_hardware(self) -> List[HardwareSpec]:
        """获取按优先级排序的硬件列表"""
        return sorted(self.fixed_hardware_database, key=lambda x: x.priority)
    
    def get_physical_parameters(self, hardware: HardwareSpec) -> Dict:
        """获取硬件物理参数用于算法计算（与平台算法同步）"""
        return {
            'width': hardware.width,
            'height': hardware.height,
            'grid_width': hardware.grid_width,
            'grid_height': hardware.grid_height,
            'grid_scale_x': hardware.grid_scale_x,
            'grid_scale_y': hardware.grid_scale_y,
            'threshold': hardware.threshold,
            'name': hardware.name,
            'id': hardware.id
        }
    
    def get_available_hardware(self) -> List[HardwareSpec]:
        """获取所有可用硬件规格"""
        return self.fixed_hardware_database
    
    def get_fallback_spec(self) -> HardwareSpec:
        """获取回退规格"""
        return self.fallback_spec
    
    def get_system_status(self) -> Dict:
        """获取系统状态"""
        return {
            'available_hardware': len(self.fixed_hardware_database),
            'fallback_available': True,
            'error_recovery_available': True,
            'last_update': '2025-08-04',
            'sync_status': '与平台算法完全同步'
        }

# 单例导出（与平台算法保持一致）
hardware_adaptive_service = HardwareAdaptiveService()

def smart_hardware_match(data: Any, filename: str = "") -> HardwareMatchInfo:
    """
    智能硬件匹配 - 对外统一接口
    
    Args:
        data: 数据
        filename: 文件名
        
    Returns:
        HardwareMatchInfo: 匹配结果
    """
    return hardware_adaptive_service.match_hardware(data, filename)

def get_hardware_parameters(match_info: HardwareMatchInfo) -> Dict:
    """
    获取硬件参数 - 便捷接口
    
    Args:
        match_info: 硬件匹配信息
        
    Returns:
        Dict: 物理参数字典
    """
    if match_info.hardware:
        return hardware_adaptive_service.get_physical_parameters(match_info.hardware)
    else:
        fallback = hardware_adaptive_service.get_fallback_spec()
        return hardware_adaptive_service.get_physical_parameters(fallback)

# 测试和演示
if __name__ == "__main__":
    print("🔧 Python硬件自适应服务测试")
    
    service = HardwareAdaptiveService()
    
    # 显示系统状态
    status = service.get_system_status()
    print(f"\n📊 系统状态:")
    print(f"   可用硬件数量: {status['available_hardware']}")
    print(f"   回退算法: {'✅' if status['fallback_available'] else '❌'}")
    print(f"   错误恢复: {'✅' if status['error_recovery_available'] else '❌'}")
    print(f"   同步状态: {status['sync_status']}")
    
    # 显示固定硬件列表
    print(f"\n📋 固定硬件列表 (按优先级排序):")
    for hardware in service._get_sorted_hardware():
        print(f"   优先级{hardware.priority}: {hardware.name}")
        print(f"     尺寸: {hardware.width}m×{hardware.height}m")
        print(f"     格式: {hardware.data_format}")
        print()
    
    # 测试硬件匹配
    print("🧪 测试硬件匹配功能:")
    
    # 模拟32列数据
    test_data_32col = [[1.0] * 32 for _ in range(100)]
    match_result = service.match_hardware(test_data_32col, "步态测试.csv")
    print(f"\n32列数据匹配结果:")
    print(f"   硬件: {match_result.hardware.name if match_result.hardware else 'None'}")
    print(f"   置信度: {match_result.confidence}%")
    print(f"   消息: {match_result.message}")
    
    print("\n✅ 系统保证:")
    print("   1. 优先匹配固定硬件，确保最佳性能")
    print("   2. 格式不匹配时自动降级到通用算法") 
    print("   3. 任何情况下都不会报错或卡住")
    print("   4. 与平台算法(TypeScript)完全同步")
    print("   5. 为未来硬件扩展预留接口")